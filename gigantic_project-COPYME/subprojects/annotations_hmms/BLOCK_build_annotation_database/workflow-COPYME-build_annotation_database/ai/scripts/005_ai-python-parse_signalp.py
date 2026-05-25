#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Parse SignalP6 consolidated per-species TSV into standardized 7-column annotation database rows
# Human: Eric Edsinger

"""
005_ai-python-parse_signalp.py

Parses the per-species consolidated SignalP6 TSV files produced by
BLOCK_signalp/workflow-*/ai/scripts/003_ai-python-consolidate_signalp_outputs.py
into the standardized 7-column GIGANTIC annotation database format.

Input file naming ( one or both modes per species, mode-tagged ):
    <phyloname>_signalp_FAST_predictions.tsv
    <phyloname>_signalp_SLOW_predictions.tsv

Input column schema ( descriptive GIGANTIC header ):
    Protein_Identifier
    Sequence_Length
    Signal_Peptide_Call    ( Sec/SPI | Sec/SPII | Tat/SPI | None )
                           ( None when SignalP6 called OTHER OR the protein
                             was not annotated by SignalP6 )
    Signal_Peptide_Start
    Signal_Peptide_End
    OTHER_Probability
    SP_Probability
    LIPO_Probability
    TAT_Probability
    Cleavage_Site_String

Output standardized 7-column schema:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Output layout ( one subdir per mode so fast and slow stay separate ):
    database_signalp_fast/
        gigantic_annotations-database_signalp_fast-<phyloname>.tsv
    database_signalp_slow/
        gigantic_annotations-database_signalp_slow-<phyloname>.tsv

Mapping rules:
    - SP-positive rows ( Signal_Peptide_Call in {Sec/SPI, Sec/SPII, Tat/SPI} ):
        Domain_Start          = Signal_Peptide_Start              ( 1 )
        Domain_Stop           = Signal_Peptide_End                ( cleavage site )
        Annotation_Identifier = Signal_Peptide_Call               ( e.g. Sec/SPI )
        Annotation_Details    = probability=<matching prob>,cleavage_site=<raw string>
    - SP-negative rows ( Signal_Peptide_Call = None ):
        Domain_Start          = 0
        Domain_Stop           = 0
        Annotation_Identifier = unannotated_signalp_<mode>-N      ( N is global counter per mode )
        Annotation_Details    = no annotation
        ( These come from BOTH SignalP6 OTHER predictions AND proteins the
          tool did not annotate at all. The consolidated TSV from script 003
          already includes both kinds with Signal_Peptide_Call = None. )
"""

import argparse
import logging
import re
import sys
from pathlib import Path


VALID_SIGNAL_PEPTIDE_CALLS = { "Sec/SPI", "Sec/SPII", "Tat/SPI" }


# =============================================================================
# LOGGING
# =============================================================================

def setup_logging( output_directory ):
    logger = logging.getLogger( "005_parse_signalp" )
    logger.setLevel( logging.DEBUG )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    log_file = output_directory / "5_ai-log-parse_signalp.log"
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


# =============================================================================
# DISCOVERY MANIFEST LOAD
# =============================================================================

def load_signalp_discovery_record( discovery_manifest_path, annotations_directory, logger ):
    """
    Read the discovery manifest produced by 001 and return the signalp record.
    Manifest columns ( from script 001 ):
        Tool_Name  Tool_Available  Output_Directory  File_Count  File_Pattern
    """
    if not discovery_manifest_path.exists():
        logger.error( f"CRITICAL ERROR: discovery manifest not found: {discovery_manifest_path}" )
        sys.exit( 1 )

    signalp_record = None
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
            if tool_name == "signalp":
                signalp_record = {
                    "tool_name":         tool_name,
                    "tool_available":    tool_available,
                    "output_directory":  annotations_directory / output_directory_relative,
                    "file_pattern":      file_pattern,
                }
                break

    if signalp_record is None:
        logger.error( "CRITICAL ERROR: signalp record not found in discovery manifest" )
        logger.error( f"Manifest: {discovery_manifest_path}" )
        sys.exit( 1 )

    if signalp_record[ "tool_available" ] != "yes":
        logger.info( "signalp not marked available in discovery manifest - skipping ( no consolidated TSVs to parse )" )
        return None

    return signalp_record


# =============================================================================
# FILENAME PARSING
# =============================================================================

FILENAME_PATTERN = re.compile( r"^(?P<phyloname>.+)_signalp_(?P<mode>FAST|SLOW)_predictions\.tsv$" )


def extract_phyloname_and_mode( filename, logger ):
    """
    Parse <phyloname>_signalp_<MODE>_predictions.tsv -> ( phyloname, mode_lower ).
    mode_lower is 'fast' or 'slow' ( lowercased for Database_Name ).
    """
    match = FILENAME_PATTERN.match( filename )
    if match is None:
        logger.error( f"CRITICAL ERROR: filename does not match expected pattern <phyloname>_signalp_<FAST|SLOW>_predictions.tsv" )
        logger.error( f"  filename: {filename}" )
        sys.exit( 1 )
    phyloname = match.group( "phyloname" )
    mode_lower = match.group( "mode" ).lower()
    return phyloname, mode_lower


# =============================================================================
# OUTPUT HEADER
# =============================================================================

def write_standardized_header():
    header = (
        "Phyloname (GIGANTIC phyloname for the species)" + "\t"
        + "Sequence_Identifier (protein identifier from proteome)" + "\t"
        + "Domain_Start (start position of signal peptide region; 0 if unannotated)" + "\t"
        + "Domain_Stop (stop position of signal peptide region at cleavage site; 0 if unannotated)" + "\t"
        + "Database_Name (annotation database name; signalp_fast or signalp_slow)" + "\t"
        + "Annotation_Identifier (signal peptide call e.g. Sec/SPI Sec/SPII Tat/SPI; or unannotated_<database>-N)" + "\t"
        + "Annotation_Details (probability of the called type and raw cleavage site string; or 'no annotation')" + "\n"
    )
    return header


# =============================================================================
# PER-FILE PARSE
# =============================================================================

CONSOLIDATED_COLUMN_INDEX = {
    "Protein_Identifier":     0,
    "Sequence_Length":        1,
    "Signal_Peptide_Call":    2,
    "Signal_Peptide_Start":   3,
    "Signal_Peptide_End":     4,
    "OTHER_Probability":      5,
    "SP_Probability":         6,
    "LIPO_Probability":       7,
    "TAT_Probability":        8,
    "Cleavage_Site_String":   9,
}

CALL_TO_PROBABILITY_COLUMN = {
    "Sec/SPI":  "SP_Probability",
    "Sec/SPII": "LIPO_Probability",
    "Tat/SPI":  "TAT_Probability",
}


def parse_one_consolidated_file( consolidated_path, phyloname, mode_lower, unannotated_counter, logger ):
    """
    Read one consolidated TSV and return a list of standardized 7-column rows
    plus updated unannotated_counter.

    Each row is a tuple of 7 strings ready to be written to the output TSV.
    """
    database_name = f"signalp_{mode_lower}"
    annotation_rows = []
    proteins_read = 0
    sp_positive_count = 0
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
            if len( parts ) != 10:
                logger.error( f"CRITICAL ERROR: consolidated TSV row has {len( parts )} columns, expected 10" )
                logger.error( f"  file: {consolidated_path}" )
                logger.error( f"  line: {line[ :200 ]}" )
                sys.exit( 1 )

            proteins_read += 1
            protein_identifier   = parts[ CONSOLIDATED_COLUMN_INDEX[ "Protein_Identifier"     ] ]
            signal_peptide_call  = parts[ CONSOLIDATED_COLUMN_INDEX[ "Signal_Peptide_Call"    ] ]
            signal_peptide_start = parts[ CONSOLIDATED_COLUMN_INDEX[ "Signal_Peptide_Start"   ] ]
            signal_peptide_end   = parts[ CONSOLIDATED_COLUMN_INDEX[ "Signal_Peptide_End"     ] ]
            cleavage_site_string = parts[ CONSOLIDATED_COLUMN_INDEX[ "Cleavage_Site_String"   ] ]

            if signal_peptide_call in VALID_SIGNAL_PEPTIDE_CALLS:
                # SP-positive row
                probability_column_name = CALL_TO_PROBABILITY_COLUMN[ signal_peptide_call ]
                probability_value = parts[ CONSOLIDATED_COLUMN_INDEX[ probability_column_name ] ]
                annotation_details = (
                    f"probability={probability_value}"
                    + f",cleavage_site={cleavage_site_string}"
                )
                annotation_row = (
                    phyloname,
                    protein_identifier,
                    signal_peptide_start,
                    signal_peptide_end,
                    database_name,
                    signal_peptide_call,
                    annotation_details,
                )
                sp_positive_count += 1
            elif signal_peptide_call == "None":
                # Unannotated row ( OTHER or not in SignalP6 output ).
                # Per the standardized convention, unannotated entries use:
                #   Domain_Start = 0, Domain_Stop = 0
                #   Annotation_Identifier = unannotated_<database>-N  ( N global per mode )
                #   Annotation_Details    = no annotation
                unannotated_counter += 1
                annotation_row = (
                    phyloname,
                    protein_identifier,
                    "0",
                    "0",
                    database_name,
                    f"unannotated_{database_name}-{unannotated_counter}",
                    "no annotation",
                )
                unannotated_count += 1
            else:
                logger.error( f"CRITICAL ERROR: unrecognized Signal_Peptide_Call value: '{signal_peptide_call}'" )
                logger.error( f"  expected one of: Sec/SPI, Sec/SPII, Tat/SPI, None" )
                logger.error( f"  file:  {consolidated_path}" )
                logger.error( f"  line:  {line[ :200 ]}" )
                sys.exit( 1 )

            annotation_rows.append( annotation_row )

    logger.info( f"    Proteins parsed: {proteins_read}  SP-positive: {sp_positive_count}  unannotated: {unannotated_count}" )
    return annotation_rows, unannotated_counter


# =============================================================================
# DRIVER
# =============================================================================

def parse_all_signalp_consolidated_files( signalp_record, output_directory, logger ):
    """
    Process every <phyloname>_signalp_<MODE>_predictions.tsv in the signalp
    output_to_input directory. Writes one standardized TSV per ( species, mode )
    into database_signalp_<mode>/ subdirs.
    """
    signalp_output_directory = signalp_record[ "output_directory" ]
    file_pattern = signalp_record[ "file_pattern" ]

    consolidated_files = sorted( signalp_output_directory.glob( file_pattern ) )
    if len( consolidated_files ) == 0:
        logger.error( "CRITICAL ERROR: no consolidated signalp TSVs found" )
        logger.error( f"  dir:     {signalp_output_directory}" )
        logger.error( f"  pattern: {file_pattern}" )
        sys.exit( 1 )

    logger.info( f"Found {len( consolidated_files )} consolidated signalp TSV(s)" )

    # Mode-separated output dirs ( created on first encounter )
    database_dirs_by_mode = {}
    # Global per-mode unannotated counter
    unannotated_counter_by_mode = {}
    # Stats
    total_annotation_rows = 0

    for consolidated_path in consolidated_files:
        phyloname, mode_lower = extract_phyloname_and_mode( consolidated_path.name, logger )
        logger.info( f"  {consolidated_path.name} -> phyloname={phyloname} mode={mode_lower}" )

        if mode_lower not in database_dirs_by_mode:
            database_dir = output_directory / f"database_signalp_{mode_lower}"
            database_dir.mkdir( parents = True, exist_ok = True )
            database_dirs_by_mode[ mode_lower ] = database_dir
            unannotated_counter_by_mode[ mode_lower ] = 0

        unannotated_counter_in = unannotated_counter_by_mode[ mode_lower ]
        annotation_rows, unannotated_counter_out = parse_one_consolidated_file(
            consolidated_path, phyloname, mode_lower, unannotated_counter_in, logger,
        )
        unannotated_counter_by_mode[ mode_lower ] = unannotated_counter_out

        if len( annotation_rows ) == 0:
            logger.warning( f"    WARNING: zero annotation rows produced for {phyloname} (mode {mode_lower})" )
            continue

        output_file_path = database_dirs_by_mode[ mode_lower ] / f"gigantic_annotations-database_signalp_{mode_lower}-{phyloname}.tsv"
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
    logger.info( "Script 005 SUMMARY" )
    logger.info( "=" * 50 )
    for mode_lower in sorted( database_dirs_by_mode.keys() ):
        logger.info( f"  mode={mode_lower}: unannotated entries assigned = {unannotated_counter_by_mode[ mode_lower ]}" )
        logger.info( f"  mode={mode_lower}: output dir = {database_dirs_by_mode[ mode_lower ]}" )
    logger.info( f"  Total standardized annotation rows written: {total_annotation_rows}" )

    if total_annotation_rows == 0:
        logger.error( "CRITICAL ERROR: no annotation rows written across all files" )
        sys.exit( 1 )


def main():
    parser = argparse.ArgumentParser(
        description = "Parse consolidated SignalP6 per-species TSVs into standardized 7-column annotation database rows."
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
        help = "Output directory for database_signalp_<mode>/ subdirs",
    )
    args = parser.parse_args()

    output_directory = Path( args.output_dir ).resolve()
    output_directory.mkdir( parents = True, exist_ok = True )
    annotations_directory = Path( args.annotations_dir ).resolve()

    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 005: Parse SignalP6 consolidated TSVs (per-mode)" )
    logger.info( "=" * 70 )
    logger.info( f"Discovery manifest: {args.discovery_manifest}" )
    logger.info( f"Annotations dir:    {annotations_directory}" )
    logger.info( f"Output dir:         {output_directory}" )

    signalp_record = load_signalp_discovery_record(
        Path( args.discovery_manifest ).resolve(),
        annotations_directory,
        logger,
    )
    if signalp_record is None:
        logger.info( "No signalp data available - exiting cleanly" )
        return

    parse_all_signalp_consolidated_files( signalp_record, output_directory, logger )


if __name__ == "__main__":
    main()
