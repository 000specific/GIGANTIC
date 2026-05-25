#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Consolidate per-species TMBed .3line raw outputs into a single descriptive-header TSV per species
# Human: Eric Edsinger

"""
003_ai-python-consolidate_tmbed_outputs.py

For one species ( one RUN's subset ): reads the canonical proteome FASTA
plus the per-species TMBed .3line raw output and writes a single
consolidated TSV with the GIGANTIC self-documenting header style.

Per-RUN scope: this script ONLY consolidates the proteins TMBed processed
in THIS RUN. ( RUN_1 = full set for 5 species. RUN_2 = short proteins
<=4000 aa. RUN_3 = long proteins >4000 aa. ) A separate cross-RUN union
step is planned for later.

Output schema ( one row per protein in proteome FASTA; tool-not-annotated
proteins get None values ):
    Protein_Identifier
    Sequence_Length
    TM_Helix_Count
    TM_Helix_Identifiers     ( tm_helix_1,tm_helix_2,... or None )
    TM_Helix_Starts          ( comma-delim int list or None )
    TM_Helix_Ends            ( comma-delim int list or None, 1:1 with starts )
    Beta_Barrel_Count
    Beta_Barrel_Identifiers
    Beta_Barrel_Starts
    Beta_Barrel_Ends
    Signal_Peptide_Count
    Signal_Peptide_Identifiers
    Signal_Peptide_Starts
    Signal_Peptide_Ends

Topology string codes ( TMBed native ):
    H or h  = alpha-helix transmembrane segment
    B or b  = beta-barrel transmembrane segment
    S       = signal peptide
    .       = other ( non-transmembrane / non-SP )

A "region" is one maximal run of consecutive characters from the same
category. The three categories collapsed are:
    TM helix:      H | h   ( inside-out vs outside-in same region type )
    Beta barrel:   B | b
    Signal peptide: S
"""

import argparse
import logging
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Consolidate per-species TMBed .3line raw outputs into one descriptive-header TSV ( per-RUN scope )."
    )
    parser.add_argument(
        "--input-fasta",
        required = True,
        help = "Path to the proteome FASTA file used as TMBed input for this species ( canonical full set of proteins for THIS RUN )",
    )
    parser.add_argument(
        "--input-3line",
        required = True,
        help = "Path to <phyloname>_tmbed_predictions.3line file ( TMBed native raw output for this species )",
    )
    parser.add_argument(
        "--output-dir",
        required = True,
        help = "Directory where <phyloname>_tmbed_predictions.tsv + log are written",
    )
    parser.add_argument(
        "--phyloname",
        required = True,
        help = "GIGANTIC phyloname for the species ( used in output naming )",
    )
    return parser.parse_args()


def read_proteome_protein_ids_and_lengths( input_fasta_path, logger ):
    protein_ids_with_lengths = []
    current_identifier = None
    current_sequence_parts = []

    input_fasta = open( input_fasta_path, "r" )
    for line in input_fasta:
        line = line.rstrip( "\n" )
        if not line:
            continue
        if line.startswith( ">" ):
            if current_identifier is not None:
                sequence_length = sum( len( part ) for part in current_sequence_parts )
                protein_ids_with_lengths.append( ( current_identifier, sequence_length ) )
            current_identifier = line[ 1: ].split()[ 0 ]
            current_sequence_parts = []
        else:
            current_sequence_parts.append( line )
    if current_identifier is not None:
        sequence_length = sum( len( part ) for part in current_sequence_parts )
        protein_ids_with_lengths.append( ( current_identifier, sequence_length ) )
    input_fasta.close()

    logger.info( f"Proteome FASTA: read {len( protein_ids_with_lengths )} proteins" )
    return protein_ids_with_lengths


def read_3line_topology_strings( input_3line_path, logger ):
    """
    Parse TMBed .3line ( 3 lines per protein: header, sequence, topology ).
    Returns dict: protein_id -> topology_string ( str of same length as sequence ).
    """
    protein_ids___topology_strings = {}

    if not input_3line_path.exists():
        logger.error( f"CRITICAL ERROR: .3line file not found at {input_3line_path}" )
        sys.exit( 1 )

    input_3line = open( input_3line_path, "r" )
    record_lines = []
    for line in input_3line:
        line = line.rstrip( "\n" )
        record_lines.append( line )
        if len( record_lines ) == 3:
            header_line, sequence_line, topology_line = record_lines
            if not header_line.startswith( ">" ):
                logger.error( f"CRITICAL ERROR: expected header starting with '>' but got: {header_line[ :120 ]}" )
                logger.error( f"  source: {input_3line_path}" )
                sys.exit( 1 )
            if len( sequence_line ) != len( topology_line ):
                logger.error( f"CRITICAL ERROR: sequence/topology length mismatch in .3line" )
                logger.error( f"  header:   {header_line[ :120 ]}" )
                logger.error( f"  sequence length: {len( sequence_line )}" )
                logger.error( f"  topology length: {len( topology_line )}" )
                sys.exit( 1 )
            protein_identifier = header_line[ 1: ].split()[ 0 ]
            protein_ids___topology_strings[ protein_identifier ] = topology_line
            record_lines = []

    if len( record_lines ) != 0:
        logger.error( f"CRITICAL ERROR: .3line file ended mid-record ( {len( record_lines )} dangling lines )" )
        logger.error( f"  source: {input_3line_path}" )
        sys.exit( 1 )

    input_3line.close()

    logger.info( f".3line file: read {len( protein_ids___topology_strings )} topology records" )
    return protein_ids___topology_strings


def extract_regions_from_topology_string( topology_string ):
    """
    Walk topology_string and emit one region per maximal run of same category.
    Returns dict with keys 'tm_helix', 'beta_barrel', 'signal_peptide' each
    mapping to list of ( start_position, end_position ) tuples ( 1-based inclusive ).

    Categories:
        H or h -> tm_helix
        B or b -> beta_barrel
        S      -> signal_peptide
        .      -> other ( ignored )
    """
    category_runs = { "tm_helix": [], "beta_barrel": [], "signal_peptide": [] }

    def char_category( char ):
        if char in ( "H", "h" ):
            return "tm_helix"
        if char in ( "B", "b" ):
            return "beta_barrel"
        if char == "S":
            return "signal_peptide"
        return None

    current_category = None
    current_start = None
    for index in range( len( topology_string ) ):
        residue_position = index + 1   # 1-based
        char = topology_string[ index ]
        category = char_category( char )
        if category != current_category:
            # close out the previous region if any
            if current_category is not None:
                category_runs[ current_category ].append( ( current_start, residue_position - 1 ) )
            # start new region only if category is one of the three tracked
            if category is not None:
                current_start = residue_position
                current_category = category
            else:
                current_category = None
                current_start = None
    # End-of-string flush
    if current_category is not None:
        category_runs[ current_category ].append( ( current_start, len( topology_string ) ) )

    return category_runs


def format_region_columns( region_list, identifier_prefix ):
    """
    Given a list of ( start, end ) tuples, produce four strings:
        count, identifiers_string, starts_string, ends_string
    where empty list -> ( "0", "None", "None", "None" ).
    """
    count = len( region_list )
    if count == 0:
        return ( "0", "None", "None", "None" )
    identifiers = [ f"{identifier_prefix}_{i + 1}" for i in range( count ) ]
    starts = [ str( start ) for ( start, _end ) in region_list ]
    ends   = [ str( end )   for ( _start, end ) in region_list ]
    return ( str( count ), ",".join( identifiers ), ",".join( starts ), ",".join( ends ) )


def main():
    args = parse_args()

    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    log_path = output_dir / f"3_ai-log-consolidate_tmbed_outputs_{args.phyloname}.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [
            logging.FileHandler( log_path ),
            logging.StreamHandler( sys.stdout ),
        ],
    )
    logger = logging.getLogger( __name__ )

    logger.info( "=" * 70 )
    logger.info( "Script 003: Consolidate TMBed raw outputs (per species, per RUN)" )
    logger.info( "=" * 70 )
    logger.info( f"Phyloname: {args.phyloname}" )
    logger.info( f"Input FASTA: {args.input_fasta}" )
    logger.info( f"Input .3line: {args.input_3line}" )
    logger.info( f"Output dir: {output_dir}" )

    # --- Read proteome FASTA -------------------------------------------------
    protein_ids_with_lengths = read_proteome_protein_ids_and_lengths(
        Path( args.input_fasta ), logger,
    )
    if len( protein_ids_with_lengths ) == 0:
        logger.error( f"CRITICAL ERROR: proteome FASTA contained 0 proteins: {args.input_fasta}" )
        sys.exit( 1 )

    # --- Read .3line ---------------------------------------------------------
    protein_ids___topology_strings = read_3line_topology_strings(
        Path( args.input_3line ), logger,
    )

    # --- Cross-check: any .3line protein NOT in proteome FASTA? --------------
    proteome_protein_id_set = set( pid for ( pid, _ ) in protein_ids_with_lengths )
    foreign_protein_ids = [
        pid for pid in protein_ids___topology_strings.keys()
        if pid not in proteome_protein_id_set
    ]
    if len( foreign_protein_ids ) > 0:
        logger.error( "CRITICAL ERROR: .3line file contains protein IDs that are NOT in the proteome FASTA!" )
        logger.error( f"  count: {len( foreign_protein_ids )}" )
        logger.error( f"  first few: {foreign_protein_ids[ :5 ]}" )
        logger.error( f"  proteome FASTA: {args.input_fasta}" )
        logger.error( f"  .3line file:    {args.input_3line}" )
        sys.exit( 1 )

    # --- Also cross-check: topology length matches proteome sequence length --
    # ( catches the case where the FASTA we were given does not match what
    #   TMBed actually processed )
    protein_ids___proteome_lengths = { pid: length for ( pid, length ) in protein_ids_with_lengths }
    length_mismatches = []
    for ( protein_identifier, topology_string ) in protein_ids___topology_strings.items():
        proteome_length = protein_ids___proteome_lengths[ protein_identifier ]
        if len( topology_string ) != proteome_length:
            length_mismatches.append( ( protein_identifier, proteome_length, len( topology_string ) ) )
    if len( length_mismatches ) > 0:
        logger.error( "CRITICAL ERROR: topology length does not match proteome sequence length for some proteins!" )
        for ( pid, proteome_length, topology_length ) in length_mismatches[ :5 ]:
            logger.error( f"  {pid}: proteome={proteome_length} topology={topology_length}" )
        logger.error( f"  total mismatches: {len( length_mismatches )}" )
        sys.exit( 1 )

    # --- Write consolidated TSV ---------------------------------------------
    consolidated_path = output_dir / f"{args.phyloname}_tmbed_predictions.tsv"
    output_consolidated = open( consolidated_path, "w" )

    header = (
        "Protein_Identifier (canonical FASTA header from proteome)" + "\t"
        + "Sequence_Length (residue count from proteome FASTA)" + "\t"
        + "TM_Helix_Count (number of alpha-helix transmembrane regions detected by TMBed; 0 if none)" + "\t"
        + "TM_Helix_Identifiers (comma delimited list of per-protein TM helix labels of the form tm_helix_N; None if no TM helices)" + "\t"
        + "TM_Helix_Starts (comma delimited list of TM helix start residue positions matched 1:1 with TM_Helix_Identifiers; None if none)" + "\t"
        + "TM_Helix_Ends (comma delimited list of TM helix end residue positions matched 1:1 with TM_Helix_Identifiers; None if none)" + "\t"
        + "Beta_Barrel_Count (number of beta-barrel transmembrane regions detected by TMBed; 0 if none)" + "\t"
        + "Beta_Barrel_Identifiers (comma delimited list of per-protein beta barrel labels of the form beta_barrel_N; None if none)" + "\t"
        + "Beta_Barrel_Starts (comma delimited list of beta barrel start residue positions matched 1:1 with Beta_Barrel_Identifiers; None if none)" + "\t"
        + "Beta_Barrel_Ends (comma delimited list of beta barrel end residue positions matched 1:1 with Beta_Barrel_Identifiers; None if none)" + "\t"
        + "Signal_Peptide_Count (number of signal peptide regions detected by TMBed; 0 if none)" + "\t"
        + "Signal_Peptide_Identifiers (comma delimited list of per-protein signal peptide labels of the form signal_peptide_N; None if none)" + "\t"
        + "Signal_Peptide_Starts (comma delimited list of signal peptide start residue positions matched 1:1 with Signal_Peptide_Identifiers; None if none)" + "\t"
        + "Signal_Peptide_Ends (comma delimited list of signal peptide end residue positions matched 1:1 with Signal_Peptide_Identifiers; None if none)" + "\n"
    )
    output_consolidated.write( header )

    annotated_count = 0
    unannotated_count = 0
    total_tm_helix_regions = 0
    total_beta_barrel_regions = 0
    total_signal_peptide_regions = 0

    for ( protein_identifier, sequence_length ) in protein_ids_with_lengths:
        topology_string = protein_ids___topology_strings.get( protein_identifier )

        if topology_string is None:
            # Tool did not process this protein - all tmbed columns None
            tm_helix_columns       = ( "None", "None", "None", "None" )
            beta_barrel_columns    = ( "None", "None", "None", "None" )
            signal_peptide_columns = ( "None", "None", "None", "None" )
            unannotated_count += 1
        else:
            category_runs = extract_regions_from_topology_string( topology_string )
            tm_helix_columns       = format_region_columns( category_runs[ "tm_helix" ],       "tm_helix" )
            beta_barrel_columns    = format_region_columns( category_runs[ "beta_barrel" ],    "beta_barrel" )
            signal_peptide_columns = format_region_columns( category_runs[ "signal_peptide" ], "signal_peptide" )
            annotated_count += 1
            total_tm_helix_regions       += len( category_runs[ "tm_helix" ] )
            total_beta_barrel_regions    += len( category_runs[ "beta_barrel" ] )
            total_signal_peptide_regions += len( category_runs[ "signal_peptide" ] )

        output = (
            protein_identifier + "\t"
            + str( sequence_length ) + "\t"
            + tm_helix_columns[ 0 ] + "\t"
            + tm_helix_columns[ 1 ] + "\t"
            + tm_helix_columns[ 2 ] + "\t"
            + tm_helix_columns[ 3 ] + "\t"
            + beta_barrel_columns[ 0 ] + "\t"
            + beta_barrel_columns[ 1 ] + "\t"
            + beta_barrel_columns[ 2 ] + "\t"
            + beta_barrel_columns[ 3 ] + "\t"
            + signal_peptide_columns[ 0 ] + "\t"
            + signal_peptide_columns[ 1 ] + "\t"
            + signal_peptide_columns[ 2 ] + "\t"
            + signal_peptide_columns[ 3 ] + "\n"
        )
        output_consolidated.write( output )

    output_consolidated.close()

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Total proteins in consolidated TSV: {len( protein_ids_with_lengths )}" )
    logger.info( f"  TMBed-annotated:        {annotated_count}" )
    logger.info( f"  not annotated by tool:  {unannotated_count}" )
    logger.info( f"Region totals ( among annotated ):" )
    logger.info( f"  TM helices:      {total_tm_helix_regions}" )
    logger.info( f"  Beta barrels:    {total_beta_barrel_regions}" )
    logger.info( f"  Signal peptides: {total_signal_peptide_regions}" )
    logger.info( f"Consolidated TSV: {consolidated_path}" )


if __name__ == "__main__":
    main()
