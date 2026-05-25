#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Parse MetaPredict consolidated per-species TSV into standardized 7-column annotation database rows
# Human: Eric Edsinger

"""
007_ai-python-parse_metapredict.py

Parses the per-species consolidated MetaPredict TSV files produced by
BLOCK_metapredict/workflow-*/ai/scripts/003_ai-python-consolidate_metapredict_outputs.py
into the standardized 7-column GIGANTIC annotation database format.

Input file naming ( one per species ):
    <phyloname>_metapredict_predictions.tsv

Input column schema ( descriptive GIGANTIC header ):
    Protein_Identifier
    Sequence_Length
    IDR_Count
    IDR_Identifiers     ( comma-delim list of idr_1,idr_2,... or None )
    IDR_Starts          ( comma-delim int list or None )
    IDR_Ends            ( comma-delim int list or None, 1:1 with IDR_Starts )

Output standardized 7-column schema:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Output layout:
    database_metapredict/
        gigantic_annotations-database_metapredict-<phyloname>.tsv

Mapping rules:
    - Protein with N IDRs ( N > 0 ): emit N rows, one per IDR
        Domain_Start          = IDR_Starts[ i ]
        Domain_Stop           = IDR_Ends[ i ]
        Database_Name         = metapredict
        Annotation_Identifier = IDR_Identifiers[ i ]    ( e.g. idr_1 )
        Annotation_Details    = intrinsically disordered region
    - Protein with 0 IDRs: emit 1 unannotated row
        Domain_Start          = 0
        Domain_Stop           = 0
        Database_Name         = metapredict
        Annotation_Identifier = unannotated_metapredict-N  ( global counter )
        Annotation_Details    = no annotation
"""

import argparse
import logging
import sys
from pathlib import Path


# =============================================================================
# LOGGING
# =============================================================================

def setup_logging( output_directory ):
    logger = logging.getLogger( "007_parse_metapredict" )
    logger.setLevel( logging.DEBUG )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    log_file = output_directory / "7_ai-log-parse_metapredict.log"
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


# =============================================================================
# DISCOVERY MANIFEST LOAD
# =============================================================================

def load_metapredict_discovery_record( discovery_manifest_path, annotations_directory, logger ):
    if not discovery_manifest_path.exists():
        logger.error( f"CRITICAL ERROR: discovery manifest not found: {discovery_manifest_path}" )
        sys.exit( 1 )

    metapredict_record = None
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
            if tool_name == "metapredict":
                metapredict_record = {
                    "tool_name":         tool_name,
                    "tool_available":    tool_available,
                    "output_directory":  annotations_directory / output_directory_relative,
                    "file_pattern":      file_pattern,
                }
                break

    if metapredict_record is None:
        logger.error( "CRITICAL ERROR: metapredict record not found in discovery manifest" )
        sys.exit( 1 )

    if metapredict_record[ "tool_available" ] != "yes":
        logger.info( "metapredict not marked available in discovery manifest - skipping" )
        return None

    return metapredict_record


# =============================================================================
# FILENAME PARSING
# =============================================================================

def extract_phyloname( filename, logger ):
    """
    Parse <phyloname>_metapredict_predictions.tsv -> phyloname.
    """
    suffix = "_metapredict_predictions.tsv"
    if not filename.endswith( suffix ):
        logger.error( f"CRITICAL ERROR: filename does not match expected pattern <phyloname>_metapredict_predictions.tsv" )
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
        + "Domain_Start (start position of intrinsically disordered region; 0 if unannotated)" + "\t"
        + "Domain_Stop (stop position of intrinsically disordered region; 0 if unannotated)" + "\t"
        + "Database_Name (annotation database name; metapredict)" + "\t"
        + "Annotation_Identifier (per-protein IDR label of the form idr_N; or unannotated_metapredict-N)" + "\t"
        + "Annotation_Details (description of the annotation; 'intrinsically disordered region' or 'no annotation')" + "\n"
    )
    return header


# =============================================================================
# PER-FILE PARSE
# =============================================================================

CONSOLIDATED_COLUMN_INDEX = {
    "Protein_Identifier":  0,
    "Sequence_Length":     1,
    "IDR_Count":           2,
    "IDR_Identifiers":     3,
    "IDR_Starts":          4,
    "IDR_Ends":            5,
}


def parse_one_consolidated_file( consolidated_path, phyloname, unannotated_counter, logger ):
    database_name = "metapredict"
    annotation_rows = []
    proteins_read = 0
    proteins_with_idrs = 0
    total_idr_rows = 0
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
            if len( parts ) != 6:
                logger.error( f"CRITICAL ERROR: consolidated TSV row has {len( parts )} columns, expected 6" )
                logger.error( f"  file: {consolidated_path}" )
                logger.error( f"  line: {line[ :200 ]}" )
                sys.exit( 1 )

            proteins_read += 1
            protein_identifier  = parts[ CONSOLIDATED_COLUMN_INDEX[ "Protein_Identifier" ] ]
            idr_count_string    = parts[ CONSOLIDATED_COLUMN_INDEX[ "IDR_Count"          ] ]
            idr_identifiers_str = parts[ CONSOLIDATED_COLUMN_INDEX[ "IDR_Identifiers"    ] ]
            idr_starts_str      = parts[ CONSOLIDATED_COLUMN_INDEX[ "IDR_Starts"         ] ]
            idr_ends_str        = parts[ CONSOLIDATED_COLUMN_INDEX[ "IDR_Ends"           ] ]

            try:
                idr_count = int( idr_count_string )
            except ValueError:
                logger.error( f"CRITICAL ERROR: non-integer IDR_Count value: '{idr_count_string}' for {protein_identifier}" )
                sys.exit( 1 )

            if idr_count == 0:
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
                continue

            parts_identifiers = idr_identifiers_str.split( "," )
            parts_starts      = idr_starts_str.split( "," )
            parts_ends        = idr_ends_str.split( "," )

            if len( parts_identifiers ) != idr_count or len( parts_starts ) != idr_count or len( parts_ends ) != idr_count:
                logger.error( f"CRITICAL ERROR: IDR list-length mismatch for {protein_identifier}" )
                logger.error( f"  IDR_Count = {idr_count}" )
                logger.error( f"  identifiers ({len( parts_identifiers )}): {idr_identifiers_str}" )
                logger.error( f"  starts ({len( parts_starts )}): {idr_starts_str}" )
                logger.error( f"  ends ({len( parts_ends )}): {idr_ends_str}" )
                sys.exit( 1 )

            for i in range( idr_count ):
                annotation_rows.append( (
                    phyloname,
                    protein_identifier,
                    parts_starts[ i ],
                    parts_ends[ i ],
                    database_name,
                    parts_identifiers[ i ],
                    "intrinsically disordered region",
                ) )
            total_idr_rows += idr_count
            proteins_with_idrs += 1

    logger.info( f"    Proteins parsed: {proteins_read}  with IDRs: {proteins_with_idrs}  IDR rows: {total_idr_rows}  unannotated: {unannotated_count}" )
    return annotation_rows, unannotated_counter


# =============================================================================
# DRIVER
# =============================================================================

def parse_all_metapredict_consolidated_files( metapredict_record, output_directory, logger ):
    metapredict_output_directory = metapredict_record[ "output_directory" ]
    file_pattern = metapredict_record[ "file_pattern" ]

    consolidated_files = sorted( metapredict_output_directory.glob( file_pattern ) )
    if len( consolidated_files ) == 0:
        logger.error( "CRITICAL ERROR: no consolidated metapredict TSVs found" )
        logger.error( f"  dir:     {metapredict_output_directory}" )
        logger.error( f"  pattern: {file_pattern}" )
        sys.exit( 1 )

    logger.info( f"Found {len( consolidated_files )} consolidated metapredict TSV(s)" )

    database_output_directory = output_directory / "database_metapredict"
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

        output_file_path = database_output_directory / f"gigantic_annotations-database_metapredict-{phyloname}.tsv"
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
    logger.info( "Script 007 SUMMARY" )
    logger.info( "=" * 50 )
    logger.info( f"  Output dir:                       {database_output_directory}" )
    logger.info( f"  Unannotated entries assigned:     {unannotated_counter}" )
    logger.info( f"  Total standardized rows written:  {total_annotation_rows}" )

    if total_annotation_rows == 0:
        logger.error( "CRITICAL ERROR: no annotation rows written across all files" )
        sys.exit( 1 )


def main():
    parser = argparse.ArgumentParser(
        description = "Parse consolidated MetaPredict per-species TSVs into standardized 7-column annotation database rows."
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
        help = "Output directory for database_metapredict/ subdir",
    )
    args = parser.parse_args()

    output_directory = Path( args.output_dir ).resolve()
    output_directory.mkdir( parents = True, exist_ok = True )
    annotations_directory = Path( args.annotations_dir ).resolve()

    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 007: Parse MetaPredict consolidated TSVs" )
    logger.info( "=" * 70 )
    logger.info( f"Discovery manifest: {args.discovery_manifest}" )
    logger.info( f"Annotations dir:    {annotations_directory}" )
    logger.info( f"Output dir:         {output_directory}" )

    metapredict_record = load_metapredict_discovery_record(
        Path( args.discovery_manifest ).resolve(),
        annotations_directory,
        logger,
    )
    if metapredict_record is None:
        logger.info( "No metapredict data available - exiting cleanly" )
        return

    parse_all_metapredict_consolidated_files( metapredict_record, output_directory, logger )


if __name__ == "__main__":
    main()
