#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Consolidate per-species MetaPredict raw outputs into a single descriptive-header TSV per species
# Human: Eric Edsinger

"""
003_ai-python-consolidate_metapredict_outputs.py

For one species: reads the canonical proteome FASTA plus the per-species
MetaPredict raw output directory ( metapredict_raw_output_<phyloname>/ )
and writes a single per-species consolidated TSV with the GIGANTIC self-
documenting header style.

Output schema ( one row per protein in proteome FASTA; missing IDR data
becomes None ):
    Protein_Identifier
    Sequence_Length
    IDR_Count
    IDR_Identifiers     ( idr_1,idr_2,...,idr_N or None )
    IDR_Starts          ( comma-delim int list or None )
    IDR_Ends            ( comma-delim int list or None, matched 1:1 with IDR_Starts )

Raw input read:
    <raw-output-dir>/idrs.fasta
        FASTA records with headers like:
            >protein_id IDR_START=10 IDR_END=45
        One record per IDR. Proteins with 0 IDRs get NO record in idrs.fasta.
"""

import argparse
import logging
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Consolidate per-species MetaPredict raw outputs into one descriptive-header TSV."
    )
    parser.add_argument(
        "--input-fasta",
        required = True,
        help = "Path to the proteome FASTA file used as MetaPredict input for this species ( canonical full set of proteins for this RUN )",
    )
    parser.add_argument(
        "--raw-output-dir",
        required = True,
        help = "Path to metapredict_raw_output_<phyloname>/ directory containing idrs.fasta ( and disorder.csv + pLDDT_scores.csv, unused here )",
    )
    parser.add_argument(
        "--output-dir",
        required = True,
        help = "Directory where <phyloname>_metapredict_predictions.tsv + log are written",
    )
    parser.add_argument(
        "--phyloname",
        required = True,
        help = "GIGANTIC phyloname for the species ( used in output naming )",
    )
    return parser.parse_args()


def read_proteome_protein_ids_and_lengths( input_fasta_path, logger ):
    """
    Walk the proteome FASTA and return an ordered list of ( protein_identifier, sequence_length )
    tuples. Preserves FASTA record order so the consolidated TSV reflects proteome order.
    """
    protein_ids_with_lengths = []
    current_identifier = None
    current_sequence_parts = []

    input_fasta = open( input_fasta_path, "r" )
    for line in input_fasta:
        line = line.rstrip( "\n" )
        if not line:
            continue
        if line.startswith( ">" ):
            # Flush the previous record
            if current_identifier is not None:
                sequence_length = sum( len( part ) for part in current_sequence_parts )
                protein_ids_with_lengths.append( ( current_identifier, sequence_length ) )
            # MetaPredict + most tools split header on whitespace and keep only the first token.
            current_identifier = line[ 1: ].split()[ 0 ]
            current_sequence_parts = []
        else:
            current_sequence_parts.append( line )
    # Last record
    if current_identifier is not None:
        sequence_length = sum( len( part ) for part in current_sequence_parts )
        protein_ids_with_lengths.append( ( current_identifier, sequence_length ) )
    input_fasta.close()

    logger.info( f"Proteome FASTA: read {len( protein_ids_with_lengths )} proteins" )
    return protein_ids_with_lengths


def read_idrs_fasta( idrs_fasta_path, logger ):
    """
    Parse metapredict-predict-idrs default fasta-mode output.
    Returns dict: protein_id -> list of ( idr_start, idr_end ) tuples ( ints ).
    Proteins with 0 IDRs are absent from the dict ( handled as None downstream ).

    Expected header format ( from metapredict-predict-idrs --mode fasta ):
        >protein_id IDR_START=10 IDR_END=45
    Header tokens are whitespace-separated. We extract the first token as the
    protein_id and pull IDR_START / IDR_END from the remaining tokens.
    """
    protein_ids___idr_region_lists = {}

    if not idrs_fasta_path.exists():
        logger.warning( f"idrs.fasta not found at {idrs_fasta_path} - treating as no IDRs for any protein" )
        return protein_ids___idr_region_lists

    input_idrs_fasta = open( idrs_fasta_path, "r" )
    record_count = 0
    for line in input_idrs_fasta:
        line = line.rstrip( "\n" )
        if not line.startswith( ">" ):
            continue
        # Header line. Parse out protein_id + IDR_START + IDR_END
        # Example: >g_Patl_g100-...-Parvularia_atlantis IDR_START=0 IDR_END=94
        header_payload = line[ 1: ]
        parts_header = header_payload.split()
        if len( parts_header ) < 1:
            continue
        protein_identifier = parts_header[ 0 ]
        idr_start = None
        idr_end = None
        for token in parts_header[ 1: ]:
            if token.startswith( "IDR_START=" ):
                try:
                    idr_start = int( token.split( "=", 1 )[ 1 ] )
                except ValueError:
                    pass
            elif token.startswith( "IDR_END=" ):
                try:
                    idr_end = int( token.split( "=", 1 )[ 1 ] )
                except ValueError:
                    pass
        if idr_start is None or idr_end is None:
            logger.error( f"CRITICAL ERROR: idrs.fasta header missing IDR_START / IDR_END tokens" )
            logger.error( f"  header: {line}" )
            logger.error( f"  source: {idrs_fasta_path}" )
            sys.exit( 1 )
        if protein_identifier not in protein_ids___idr_region_lists:
            protein_ids___idr_region_lists[ protein_identifier ] = []
        protein_ids___idr_region_lists[ protein_identifier ].append( ( idr_start, idr_end ) )
        record_count += 1
    input_idrs_fasta.close()

    logger.info( f"idrs.fasta: read {record_count} IDR records covering {len( protein_ids___idr_region_lists )} proteins" )
    return protein_ids___idr_region_lists


def main():
    args = parse_args()

    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    log_path = output_dir / f"3_ai-log-consolidate_metapredict_outputs_{args.phyloname}.log"
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
    logger.info( "Script 003: Consolidate MetaPredict raw outputs (per species)" )
    logger.info( "=" * 70 )
    logger.info( f"Phyloname: {args.phyloname}" )
    logger.info( f"Input FASTA: {args.input_fasta}" )
    logger.info( f"Raw output dir: {args.raw_output_dir}" )
    logger.info( f"Output dir: {output_dir}" )

    # --- Read proteome FASTA -------------------------------------------------
    protein_ids_with_lengths = read_proteome_protein_ids_and_lengths(
        Path( args.input_fasta ), logger,
    )
    if len( protein_ids_with_lengths ) == 0:
        logger.error( f"CRITICAL ERROR: proteome FASTA contained 0 proteins: {args.input_fasta}" )
        sys.exit( 1 )

    # --- Read idrs.fasta -----------------------------------------------------
    raw_output_dir = Path( args.raw_output_dir )
    idrs_fasta_path = raw_output_dir / "idrs.fasta"
    protein_ids___idr_region_lists = read_idrs_fasta( idrs_fasta_path, logger )

    # --- Cross-check: any protein in idrs.fasta NOT in proteome FASTA? -------
    # That should never happen ( crash if it does, per user spec ).
    proteome_protein_id_set = set( pid for ( pid, _ ) in protein_ids_with_lengths )
    foreign_protein_ids = [
        pid for pid in protein_ids___idr_region_lists.keys()
        if pid not in proteome_protein_id_set
    ]
    if len( foreign_protein_ids ) > 0:
        logger.error( "CRITICAL ERROR: idrs.fasta contains protein IDs that are NOT in the proteome FASTA!" )
        logger.error( f"  count: {len( foreign_protein_ids )}" )
        logger.error( f"  first few: {foreign_protein_ids[ :5 ]}" )
        logger.error( f"  proteome FASTA: {args.input_fasta}" )
        logger.error( f"  idrs.fasta:     {idrs_fasta_path}" )
        logger.error( "This indicates a mismatch between the proteome used by metapredict and the proteome passed to this consolidator." )
        sys.exit( 1 )

    # --- Write consolidated TSV ---------------------------------------------
    consolidated_path = output_dir / f"{args.phyloname}_metapredict_predictions.tsv"
    output_consolidated = open( consolidated_path, "w" )

    header = (
        "Protein_Identifier (canonical FASTA header from proteome)" + "\t"
        + "Sequence_Length (residue count from proteome FASTA)" + "\t"
        + "IDR_Count (number of intrinsically disordered regions detected by MetaPredict; 0 if none)" + "\t"
        + "IDR_Identifiers (comma delimited list of per-protein IDR labels of the form idr_N; None if no IDRs)" + "\t"
        + "IDR_Starts (comma delimited list of IDR start residue positions matched 1:1 with IDR_Identifiers; None if no IDRs)" + "\t"
        + "IDR_Ends (comma delimited list of IDR end residue positions matched 1:1 with IDR_Identifiers; None if no IDRs)" + "\n"
    )
    output_consolidated.write( header )

    proteins_with_idrs_count = 0
    proteins_without_idrs_count = 0
    total_idr_count = 0

    for ( protein_identifier, sequence_length ) in protein_ids_with_lengths:
        idr_region_list = protein_ids___idr_region_lists.get( protein_identifier, [] )
        idr_count = len( idr_region_list )

        if idr_count == 0:
            idr_identifiers_string = "None"
            idr_starts_string = "None"
            idr_ends_string = "None"
            proteins_without_idrs_count += 1
        else:
            idr_identifiers = [ f"idr_{i + 1}" for i in range( idr_count ) ]
            idr_starts = [ str( start ) for ( start, _end ) in idr_region_list ]
            idr_ends = [ str( end ) for ( _start, end ) in idr_region_list ]
            idr_identifiers_string = ",".join( idr_identifiers )
            idr_starts_string = ",".join( idr_starts )
            idr_ends_string = ",".join( idr_ends )
            proteins_with_idrs_count += 1
            total_idr_count += idr_count

        output = (
            protein_identifier + "\t"
            + str( sequence_length ) + "\t"
            + str( idr_count ) + "\t"
            + idr_identifiers_string + "\t"
            + idr_starts_string + "\t"
            + idr_ends_string + "\n"
        )
        output_consolidated.write( output )

    output_consolidated.close()

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Total proteins in consolidated TSV: {len( protein_ids_with_lengths )}" )
    logger.info( f"  with IDRs:    {proteins_with_idrs_count}" )
    logger.info( f"  without IDRs: {proteins_without_idrs_count}" )
    logger.info( f"Total IDR regions: {total_idr_count}" )
    logger.info( f"Consolidated TSV: {consolidated_path}" )


if __name__ == "__main__":
    main()
