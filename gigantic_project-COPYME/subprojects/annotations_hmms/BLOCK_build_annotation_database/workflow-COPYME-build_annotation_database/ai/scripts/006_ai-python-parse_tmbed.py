#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Parse TMBed consolidated per-species TSV into standardized 7-column annotation database rows
# Human: Eric Edsinger

"""
006_ai-python-parse_tmbed.py

Parses the per-species consolidated TMBed TSV files produced by
BLOCK_tmbed/workflow-*/ai/scripts/003_ai-python-consolidate_tmbed_outputs.py
into the standardized 7-column GIGANTIC annotation database format.

Input file naming ( one per species ):
    <phyloname>_tmbed_predictions.tsv

Input column schema ( 14 columns; descriptive GIGANTIC header ):
    Protein_Identifier
    Sequence_Length
    TM_Helix_Count
    TM_Helix_Identifiers     ( comma list: tm_helix_1,tm_helix_2,... or None )
    TM_Helix_Starts          ( comma int list or None )
    TM_Helix_Ends            ( comma int list or None )
    Beta_Barrel_Count
    Beta_Barrel_Identifiers
    Beta_Barrel_Starts
    Beta_Barrel_Ends
    Signal_Peptide_Count
    Signal_Peptide_Identifiers
    Signal_Peptide_Starts
    Signal_Peptide_Ends

Output standardized 7-column schema:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Output layout:
    database_tmbed/
        gigantic_annotations-database_tmbed-<phyloname>.tsv

Mapping rules:
    - For each region type ( TM helix, beta barrel, signal peptide ) the
      protein has, emit one annotation row per region:
        Domain_Start          = <region_type>_Starts[ i ]
        Domain_Stop           = <region_type>_Ends[ i ]
        Database_Name         = tmbed
        Annotation_Identifier = <region_type>_Identifiers[ i ]    ( e.g. tm_helix_1 )
        Annotation_Details    = <region description>
            'transmembrane alpha helix' | 'transmembrane beta barrel' |
            'signal peptide'
    - Protein with 0 regions across ALL three types: emit 1 unannotated row
        Domain_Start          = 0
        Domain_Stop           = 0
        Database_Name         = tmbed
        Annotation_Identifier = unannotated_tmbed-N        ( global counter )
        Annotation_Details    = no annotation
"""

import argparse
import logging
import sys
from pathlib import Path


# Region type metadata: ( column-name prefix in consolidated TSV, annotation description )
REGION_TYPES = [
    ( "TM_Helix",       "transmembrane alpha helix" ),
    ( "Beta_Barrel",    "transmembrane beta barrel" ),
    ( "Signal_Peptide", "signal peptide" ),
]


# =============================================================================
# LOGGING
# =============================================================================

def setup_logging( output_directory ):
    logger = logging.getLogger( "006_parse_tmbed" )
    logger.setLevel( logging.DEBUG )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    log_file = output_directory / "6_ai-log-parse_tmbed.log"
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


# =============================================================================
# DISCOVERY MANIFEST LOAD
# =============================================================================

def load_tmbed_discovery_record( discovery_manifest_path, annotations_directory, logger ):
    if not discovery_manifest_path.exists():
        logger.error( f"CRITICAL ERROR: discovery manifest not found: {discovery_manifest_path}" )
        sys.exit( 1 )

    tmbed_record = None
    is_header = True
    with open( discovery_manifest_path, "r" ) as input_discovery_manifest:
        for line in input_discovery_manifest:
            line = line.rstrip( "\n" )
            if not line or line.startswith( "#" ):
                continue
            if is_header:
                is_header = False
                continue
            parts = line.split( "\t" )
            if len( parts ) < 5:
                continue
            tool_name = parts[ 0 ]
            tool_available = parts[ 1 ]
            output_directory_relative = parts[ 2 ]
            file_pattern = parts[ 4 ]
            if tool_name == "tmbed":
                tmbed_record = {
                    "tool_name":         tool_name,
                    "tool_available":    tool_available,
                    "output_directory":  annotations_directory / output_directory_relative,
                    "file_pattern":      file_pattern,
                }
                break

    if tmbed_record is None:
        logger.error( "CRITICAL ERROR: tmbed record not found in discovery manifest" )
        sys.exit( 1 )

    if tmbed_record[ "tool_available" ] != "yes":
        logger.info( "tmbed not marked available in discovery manifest - skipping" )
        return None

    return tmbed_record


# =============================================================================
# FILENAME PARSING
# =============================================================================

def extract_phyloname( filename, logger ):
    """
    Parse <phyloname>_tmbed_predictions.tsv -> phyloname.
    """
    suffix = "_tmbed_predictions.tsv"
    if not filename.endswith( suffix ):
        logger.error( f"CRITICAL ERROR: filename does not match expected pattern <phyloname>_tmbed_predictions.tsv" )
        logger.error( f"  filename: {filename}" )
        sys.exit( 1 )
    return filename[ : -len( suffix ) ]


# =============================================================================
# OUTPUT HEADER
# =============================================================================

def write_standardized_header():
    header = (
        "Phyloname (GIGANTIC phyloname for the species)" + "\t"
        + "Sequence_Identifier (protein identifier from proteome)" + "\t"
        + "Domain_Start (start position of TM/signal-peptide region; 0 if unannotated)" + "\t"
        + "Domain_Stop (stop position of TM/signal-peptide region; 0 if unannotated)" + "\t"
        + "Database_Name (annotation database name; tmbed)" + "\t"
        + "Annotation_Identifier (per-protein region label of the form tm_helix_N / beta_barrel_N / signal_peptide_N; or unannotated_tmbed-N)" + "\t"
        + "Annotation_Details (description of region: 'transmembrane alpha helix' or 'transmembrane beta barrel' or 'signal peptide'; or 'no annotation')" + "\n"
    )
    return header


# =============================================================================
# PER-FILE PARSE
# =============================================================================

CONSOLIDATED_HEADERS_EXPECTED = [
    "Protein_Identifier",
    "Sequence_Length",
    "TM_Helix_Count",
    "TM_Helix_Identifiers",
    "TM_Helix_Starts",
    "TM_Helix_Ends",
    "Beta_Barrel_Count",
    "Beta_Barrel_Identifiers",
    "Beta_Barrel_Starts",
    "Beta_Barrel_Ends",
    "Signal_Peptide_Count",
    "Signal_Peptide_Identifiers",
    "Signal_Peptide_Starts",
    "Signal_Peptide_Ends",
]


# Indices into the 14-column consolidated TSV row
COLUMN_INDEX = { header_name: i for i, header_name in enumerate( CONSOLIDATED_HEADERS_EXPECTED ) }


def parse_one_consolidated_file( consolidated_path, phyloname, unannotated_counter, logger ):
    database_name = "tmbed"
    annotation_rows = []
    proteins_read = 0
    proteins_with_any_region = 0
    region_counts_per_type = { region_type: 0 for ( region_type, _desc ) in REGION_TYPES }
    unannotated_count = 0

    with open( consolidated_path, "r" ) as input_consolidated:
        is_header = True
        for line in input_consolidated:
            line = line.rstrip( "\n" )
            if not line:
                continue
            if is_header:
                is_header = False
                continue
            parts = line.split( "\t" )
            if len( parts ) != 14:
                logger.error( f"CRITICAL ERROR: consolidated TSV row has {len( parts )} columns, expected 14" )
                logger.error( f"  file: {consolidated_path}" )
                logger.error( f"  line: {line[ :200 ]}" )
                sys.exit( 1 )

            proteins_read += 1
            protein_identifier = parts[ COLUMN_INDEX[ "Protein_Identifier" ] ]

            had_any_region_this_protein = False

            for ( region_type, region_description ) in REGION_TYPES:
                count_string       = parts[ COLUMN_INDEX[ f"{region_type}_Count"       ] ]
                identifiers_string = parts[ COLUMN_INDEX[ f"{region_type}_Identifiers" ] ]
                starts_string      = parts[ COLUMN_INDEX[ f"{region_type}_Starts"      ] ]
                ends_string        = parts[ COLUMN_INDEX[ f"{region_type}_Ends"        ] ]

                # Special case: when the entire .3line lacked this protein,
                # script 003 emits 'None' in the Count cell. Treat as 0.
                if count_string == "None":
                    region_count = 0
                else:
                    try:
                        region_count = int( count_string )
                    except ValueError:
                        logger.error( f"CRITICAL ERROR: non-integer {region_type}_Count value: '{count_string}' for {protein_identifier}" )
                        sys.exit( 1 )

                if region_count == 0:
                    continue

                parts_identifiers = identifiers_string.split( "," )
                parts_starts      = starts_string.split( "," )
                parts_ends        = ends_string.split( "," )

                if len( parts_identifiers ) != region_count or len( parts_starts ) != region_count or len( parts_ends ) != region_count:
                    logger.error( f"CRITICAL ERROR: {region_type} list-length mismatch for {protein_identifier}" )
                    logger.error( f"  {region_type}_Count = {region_count}" )
                    logger.error( f"  identifiers ({len( parts_identifiers )}): {identifiers_string}" )
                    logger.error( f"  starts ({len( parts_starts )}): {starts_string}" )
                    logger.error( f"  ends ({len( parts_ends )}): {ends_string}" )
                    sys.exit( 1 )

                for i in range( region_count ):
                    annotation_rows.append( (
                        phyloname,
                        protein_identifier,
                        parts_starts[ i ],
                        parts_ends[ i ],
                        database_name,
                        parts_identifiers[ i ],
                        region_description,
                    ) )
                region_counts_per_type[ region_type ] += region_count
                had_any_region_this_protein = True

            if not had_any_region_this_protein:
                unannotated_counter += 1
                annotation_rows.append( (
                    phyloname,
                    protein_identifier,
                    "0",
                    "0",
                    database_name,
                    f"unannotated_{database_name}-{unannotated_counter}",
                    "no annotation",
                ) )
                unannotated_count += 1
            else:
                proteins_with_any_region += 1

    logger.info( f"    Proteins parsed: {proteins_read}  with regions: {proteins_with_any_region}  unannotated: {unannotated_count}" )
    for ( region_type, _desc ) in REGION_TYPES:
        logger.info( f"      {region_type} regions: {region_counts_per_type[ region_type ]}" )
    return annotation_rows, unannotated_counter


# =============================================================================
# DRIVER
# =============================================================================

def parse_all_tmbed_consolidated_files( tmbed_record, output_directory, logger ):
    tmbed_output_directory = tmbed_record[ "output_directory" ]
    file_pattern = tmbed_record[ "file_pattern" ]

    consolidated_files = sorted( tmbed_output_directory.glob( file_pattern ) )
    if len( consolidated_files ) == 0:
        logger.error( "CRITICAL ERROR: no consolidated tmbed TSVs found" )
        logger.error( f"  dir:     {tmbed_output_directory}" )
        logger.error( f"  pattern: {file_pattern}" )
        sys.exit( 1 )

    logger.info( f"Found {len( consolidated_files )} consolidated tmbed TSV(s)" )

    database_output_directory = output_directory / "database_tmbed"
    database_output_directory.mkdir( parents = True, exist_ok = True )

    unannotated_counter = 0
    total_annotation_rows = 0

    for consolidated_path in consolidated_files:
        phyloname = extract_phyloname( consolidated_path.name, logger )
        logger.info( f"  {consolidated_path.name} -> phyloname={phyloname}" )

        annotation_rows, unannotated_counter = parse_one_consolidated_file(
            consolidated_path, phyloname, unannotated_counter, logger,
        )

        if len( annotation_rows ) == 0:
            logger.warning( f"    WARNING: zero rows produced for {phyloname}" )
            continue

        output_file_path = database_output_directory / f"gigantic_annotations-database_tmbed-{phyloname}.tsv"
        with open( output_file_path, "w" ) as output_database_file:
            output_database_file.write( write_standardized_header() )
            for annotation_row in annotation_rows:
                output = (
                    annotation_row[ 0 ] + "\t"
                    + annotation_row[ 1 ] + "\t"
                    + annotation_row[ 2 ] + "\t"
                    + annotation_row[ 3 ] + "\t"
                    + annotation_row[ 4 ] + "\t"
                    + annotation_row[ 5 ] + "\t"
                    + annotation_row[ 6 ] + "\n"
                )
                output_database_file.write( output )
        total_annotation_rows += len( annotation_rows )

    logger.info( "" )
    logger.info( "=" * 50 )
    logger.info( "Script 006 SUMMARY" )
    logger.info( "=" * 50 )
    logger.info( f"  Output dir:                       {database_output_directory}" )
    logger.info( f"  Unannotated entries assigned:     {unannotated_counter}" )
    logger.info( f"  Total standardized rows written:  {total_annotation_rows}" )

    if total_annotation_rows == 0:
        logger.error( "CRITICAL ERROR: no annotation rows written across all files" )
        sys.exit( 1 )


def main():
    parser = argparse.ArgumentParser(
        description = "Parse consolidated TMBed per-species TSVs into standardized 7-column annotation database rows."
    )
    parser.add_argument(
        "--discovery-manifest",
        required = True,
        help = "Path to 1_ai-tool_discovery_manifest.tsv from script 001",
    )
    parser.add_argument(
        "--annotations-dir",
        required = True,
        help = "Path to annotations_hmms root directory ( parent of output_to_input/ )",
    )
    parser.add_argument(
        "--output-dir",
        required = True,
        help = "Output directory for database_tmbed/ subdir",
    )
    args = parser.parse_args()

    output_directory = Path( args.output_dir ).resolve()
    output_directory.mkdir( parents = True, exist_ok = True )
    annotations_directory = Path( args.annotations_dir ).resolve()

    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 006: Parse TMBed consolidated TSVs" )
    logger.info( "=" * 70 )
    logger.info( f"Discovery manifest: {args.discovery_manifest}" )
    logger.info( f"Annotations dir:    {annotations_directory}" )
    logger.info( f"Output dir:         {output_directory}" )

    tmbed_record = load_tmbed_discovery_record(
        Path( args.discovery_manifest ).resolve(),
        annotations_directory,
        logger,
    )
    if tmbed_record is None:
        logger.info( "No tmbed data available - exiting cleanly" )
        return

    parse_all_tmbed_consolidated_files( tmbed_record, output_directory, logger )


if __name__ == "__main__":
    main()
