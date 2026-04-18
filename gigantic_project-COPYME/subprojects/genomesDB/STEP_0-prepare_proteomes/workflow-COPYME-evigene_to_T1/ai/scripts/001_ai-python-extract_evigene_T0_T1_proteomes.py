#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 (1M context) | 2026 April 18 | Purpose: Extract T0 and T1 proteomes from EvidentialGene okayset output
# Human: Eric Edsinger

"""
001_ai-python-extract_evigene_T0_T1_proteomes.py

Extract T0 (main + alt) and T1 (main only) proteomes from an EvidentialGene
okayset okay.aa file by parsing the evgclass= tag in FASTA headers.

EvidentialGene classifies transcripts into three categories:
    - main:    Best representative transcript per locus (one per gene)
    - alt:     Alternative transcripts (splice variants, alternate assemblies)
    - noclass: Transcripts that failed quality filters

Output proteome levels:
    - T1 = main only (one protein per locus -- standard for GIGANTIC analyses)
    - T0 = main + alt (all non-redundant transcripts, excluding noclass)

Inputs:
    - EvidentialGene okayset okay.aa file (FASTA with evgclass= headers)

Outputs:
    - {species_name}-T1.aa: Main transcripts only
    - {species_name}-T0.aa: Main + alt transcripts (deduplicated)
    - 1_ai-summary-evigene_extraction.tsv: Summary report with counts per class

Usage:
    python3 001_ai-python-extract_evigene_T0_T1_proteomes.py \\
        --input-fasta /path/to/okayset/species.okay.aa \\
        --species-name Genus_species \\
        --output-dir OUTPUT_pipeline/1-output
"""

import argparse
import sys
import os
import logging
import re
from pathlib import Path
from datetime import datetime


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging( output_directory: Path ) -> logging.Logger:
    """
    Configure logging to both file and console.

    Args:
        output_directory: Directory where log file will be written

    Returns:
        Configured logger instance
    """

    logger = logging.getLogger( 'extract_evigene_T0_T1_proteomes' )
    logger.setLevel( logging.DEBUG )

    # File handler - captures everything including DEBUG
    log_file_path = output_directory / '1_ai-log-extract_evigene_T0_T1_proteomes.log'
    file_handler = logging.FileHandler( log_file_path, mode = 'w' )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt = '%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    # Console handler - INFO and above
    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(levelname)-8s | %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    return logger


# ============================================================================
# EVIGENE CLASSIFICATION PARSING
# ============================================================================

def parse_evigene_class( header_line: str ) -> str:
    """
    Extract the evgclass classification from a FASTA header line.

    Parses the evgclass= tag to determine if a sequence is main, alt, or noclass.
    The evgclass tag format is typically:
        evgclass=main,okay,...
        evgclass=alt,okay,...
        evgclass=noclass,...

    Args:
        header_line: The full FASTA header line (starting with >)

    Returns:
        Classification string: 'main', 'alt', 'noclass', or 'unknown'
    """

    # Search for evgclass= tag in the header
    evgclass_match = re.search( r'evgclass=(\S+)', header_line )

    if not evgclass_match:
        return 'unknown'

    evgclass_value = evgclass_match.group( 1 )

    # The first comma-separated field is the classification
    # e.g., "main,okay,match:Mlig000002t2,pct:90/85" -> "main"
    parts_evgclass_value = evgclass_value.split( ',' )
    classification = parts_evgclass_value[ 0 ].strip().lower()

    if classification in [ 'main', 'alt', 'noclass' ]:
        return classification
    else:
        return 'unknown'


# ============================================================================
# FASTA PARSING AND CLASSIFICATION
# ============================================================================

def parse_and_classify_sequences(
    input_fasta_path: Path,
    logger: logging.Logger
) -> tuple:
    """
    Read an evigene okay.aa FASTA file and classify all sequences.

    Args:
        input_fasta_path: Path to the evigene okay.aa FASTA file
        logger: Logger instance

    Returns:
        Tuple of:
            - sequence_identifiers___headers: dict mapping sequence ID to full header
            - sequence_identifiers___sequences: dict mapping sequence ID to amino acid sequence
            - sequence_identifiers___classifications: dict mapping sequence ID to classification
    """

    sequence_identifiers___headers = {}
    sequence_identifiers___sequences = {}
    sequence_identifiers___classifications = {}

    current_identifier = None
    current_header = None
    current_sequence_lines = []

    logger.info( f"Reading input FASTA: {input_fasta_path}" )

    with open( input_fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.rstrip( '\n' )

            if line.startswith( '>' ):
                # Save previous sequence if exists
                if current_identifier is not None:
                    sequence_identifiers___sequences[ current_identifier ] = ''.join( current_sequence_lines )

                # Parse new header
                current_header = line
                # Extract sequence identifier (first whitespace-delimited token after >)
                parts_header = line[ 1: ].split()
                current_identifier = parts_header[ 0 ]

                # Classify this sequence
                classification = parse_evigene_class( line )

                sequence_identifiers___headers[ current_identifier ] = current_header
                sequence_identifiers___classifications[ current_identifier ] = classification

                current_sequence_lines = []

                logger.debug(
                    f"Sequence: {current_identifier} | class: {classification}"
                )
            else:
                if line.strip():
                    current_sequence_lines.append( line.strip() )

    # Save the last sequence
    if current_identifier is not None:
        sequence_identifiers___sequences[ current_identifier ] = ''.join( current_sequence_lines )

    total_count = len( sequence_identifiers___headers )
    logger.info( f"Total sequences parsed: {total_count}" )

    return (
        sequence_identifiers___headers,
        sequence_identifiers___sequences,
        sequence_identifiers___classifications
    )


# ============================================================================
# WRITE PROTEOME FILES
# ============================================================================

def write_proteome_file(
    output_file_path: Path,
    sequence_identifiers: list,
    sequence_identifiers___headers: dict,
    sequence_identifiers___sequences: dict,
    logger: logging.Logger
) -> int:
    """
    Write a subset of sequences to a FASTA file.

    Args:
        output_file_path: Path to the output FASTA file
        sequence_identifiers: List of sequence IDs to include
        sequence_identifiers___headers: Dict mapping sequence ID to full header
        sequence_identifiers___sequences: Dict mapping sequence ID to amino acid sequence
        logger: Logger instance

    Returns:
        Number of sequences written
    """

    sequence_count = 0

    with open( output_file_path, 'w' ) as output_fasta:
        for sequence_identifier in sequence_identifiers:
            header = sequence_identifiers___headers[ sequence_identifier ]
            sequence = sequence_identifiers___sequences[ sequence_identifier ]

            output = header + '\n' + sequence + '\n'
            output_fasta.write( output )

            sequence_count += 1

    logger.info( f"Wrote {sequence_count} sequences to: {output_file_path}" )

    return sequence_count


# ============================================================================
# WRITE SUMMARY REPORT
# ============================================================================

def write_summary_report(
    output_summary_path: Path,
    species_name: str,
    input_fasta_path: Path,
    classification_counts: dict,
    t1_count: int,
    t0_count: int,
    logger: logging.Logger
) -> None:
    """
    Write a TSV summary report of the extraction.

    Args:
        output_summary_path: Path to the output summary TSV
        species_name: Species name
        input_fasta_path: Path to the input FASTA file
        classification_counts: Dict of classification -> count
        t1_count: Number of T1 sequences written
        t0_count: Number of T0 sequences written
        logger: Logger instance
    """

    total_input_count = sum( classification_counts.values() )

    with open( output_summary_path, 'w' ) as output_summary:

        # Header
        output = (
            'Metric (description of measurement or count)'
            + '\t' +
            'Value (value for this species)'
            + '\n'
        )
        output_summary.write( output )

        # Data rows
        output = 'Species_Name (species in Genus_species format)' + '\t' + species_name + '\n'
        output_summary.write( output )

        output = 'Input_File (path to evigene okayset okay.aa file)' + '\t' + str( input_fasta_path ) + '\n'
        output_summary.write( output )

        output = 'Total_Input_Sequences (total sequences in okay.aa file)' + '\t' + str( total_input_count ) + '\n'
        output_summary.write( output )

        output = 'Main_Sequences (sequences classified as main by evigene)' + '\t' + str( classification_counts.get( 'main', 0 ) ) + '\n'
        output_summary.write( output )

        output = 'Alt_Sequences (sequences classified as alt by evigene)' + '\t' + str( classification_counts.get( 'alt', 0 ) ) + '\n'
        output_summary.write( output )

        output = 'Noclass_Sequences (sequences classified as noclass by evigene)' + '\t' + str( classification_counts.get( 'noclass', 0 ) ) + '\n'
        output_summary.write( output )

        output = 'Unknown_Sequences (sequences without recognized evgclass tag)' + '\t' + str( classification_counts.get( 'unknown', 0 ) ) + '\n'
        output_summary.write( output )

        output = 'T1_Output_Sequences (main only proteome sequence count)' + '\t' + str( t1_count ) + '\n'
        output_summary.write( output )

        output = 'T0_Output_Sequences (main plus alt proteome sequence count)' + '\t' + str( t0_count ) + '\n'
        output_summary.write( output )

        output = 'Extraction_Timestamp (date and time of extraction)' + '\t' + datetime.now().strftime( '%Y-%m-%d %H:%M:%S' ) + '\n'
        output_summary.write( output )

    logger.info( f"Summary report written to: {output_summary_path}" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: parse arguments, classify sequences, write T0 and T1 proteomes.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = (
            'Extract T0 (main+alt) and T1 (main only) proteomes '
            'from an EvidentialGene okayset okay.aa file.'
        ),
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = (
            'Examples:\n'
            '  python3 001_ai-python-extract_evigene_T0_T1_proteomes.py \\\n'
            '      --input-fasta okayset/species.okay.aa \\\n'
            '      --species-name Mnemiopsis_leidyi \\\n'
            '      --output-dir OUTPUT_pipeline/1-output\n'
        )
    )

    parser.add_argument(
        '--input-fasta',
        type = str,
        required = True,
        help = 'Path to EvidentialGene okayset okay.aa file'
    )

    parser.add_argument(
        '--species-name',
        type = str,
        required = True,
        help = 'Species name in Genus_species format (e.g., Mnemiopsis_leidyi)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        required = True,
        help = 'Output directory for T0, T1, and summary files'
    )

    arguments = parser.parse_args()

    input_fasta_path = Path( arguments.input_fasta )
    species_name = arguments.species_name
    output_directory = Path( arguments.output_dir )

    # ========================================================================
    # CREATE OUTPUT DIRECTORY
    # ========================================================================

    output_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # SETUP LOGGING
    # ========================================================================

    logger = setup_logging( output_directory )

    logger.info( '=' * 72 )
    logger.info( 'EvidentialGene T0/T1 Proteome Extraction' )
    logger.info( '=' * 72 )
    logger.info( f'Script: 001_ai-python-extract_evigene_T0_T1_proteomes.py' )
    logger.info( f'Started: {datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )}' )
    logger.info( f'Species: {species_name}' )
    logger.info( f'Input FASTA: {input_fasta_path}' )
    logger.info( f'Output directory: {output_directory}' )
    logger.info( '' )

    # ========================================================================
    # FAIL-FAST VALIDATION
    # ========================================================================

    if not input_fasta_path.exists():
        logger.error( f"CRITICAL ERROR: Input FASTA file not found: {input_fasta_path}" )
        logger.error( "The EvidentialGene okayset okay.aa file must exist." )
        logger.error( "Check the path in START_HERE-user_config.yaml" )
        sys.exit( 1 )

    if not input_fasta_path.is_file():
        logger.error( f"CRITICAL ERROR: Input path is not a file: {input_fasta_path}" )
        sys.exit( 1 )

    if input_fasta_path.stat().st_size == 0:
        logger.error( f"CRITICAL ERROR: Input FASTA file is empty: {input_fasta_path}" )
        logger.error( "The okay.aa file must contain protein sequences." )
        sys.exit( 1 )

    # Validate species name format
    if '_' not in species_name:
        logger.error( f"CRITICAL ERROR: Species name must be in Genus_species format: {species_name}" )
        logger.error( "Example: Mnemiopsis_leidyi" )
        sys.exit( 1 )

    # ========================================================================
    # PARSE AND CLASSIFY SEQUENCES
    # ========================================================================

    logger.info( 'Parsing and classifying sequences...' )

    (
        sequence_identifiers___headers,
        sequence_identifiers___sequences,
        sequence_identifiers___classifications
    ) = parse_and_classify_sequences( input_fasta_path, logger )

    # ========================================================================
    # COUNT CLASSIFICATIONS
    # ========================================================================

    classification_counts = {}
    for sequence_identifier in sequence_identifiers___classifications:
        classification = sequence_identifiers___classifications[ sequence_identifier ]
        if classification not in classification_counts:
            classification_counts[ classification ] = 0
        classification_counts[ classification ] += 1

    logger.info( '' )
    logger.info( 'Classification counts:' )
    for classification in sorted( classification_counts.keys() ):
        count = classification_counts[ classification ]
        logger.info( f'  {classification}: {count}' )
    logger.info( '' )

    # Validate that we found at least some main sequences
    main_count = classification_counts.get( 'main', 0 )
    if main_count == 0:
        logger.error( "CRITICAL ERROR: No sequences classified as 'main' found!" )
        logger.error( "This file may not be a valid EvidentialGene okayset okay.aa file." )
        logger.error( "Check that FASTA headers contain evgclass=main tags." )
        sys.exit( 1 )

    # Warn about unknown classifications
    unknown_count = classification_counts.get( 'unknown', 0 )
    if unknown_count > 0:
        logger.warning(
            f"{unknown_count} sequences had no recognized evgclass= tag. "
            f"These are EXCLUDED from both T0 and T1 output."
        )

    # ========================================================================
    # BUILD T1 AND T0 SEQUENCE LISTS
    # ========================================================================

    # T1 = main only
    t1_sequence_identifiers = [
        sequence_identifier
        for sequence_identifier in sequence_identifiers___classifications
        if sequence_identifiers___classifications[ sequence_identifier ] == 'main'
    ]

    # T0 = main + alt (deduplicated by virtue of dict keys being unique)
    t0_sequence_identifiers = [
        sequence_identifier
        for sequence_identifier in sequence_identifiers___classifications
        if sequence_identifiers___classifications[ sequence_identifier ] in [ 'main', 'alt' ]
    ]

    logger.info( f'T1 sequences (main only): {len( t1_sequence_identifiers )}' )
    logger.info( f'T0 sequences (main + alt): {len( t0_sequence_identifiers )}' )
    logger.info( '' )

    # ========================================================================
    # WRITE T1 PROTEOME
    # ========================================================================

    output_t1_path = output_directory / f'{species_name}-T1.aa'
    t1_count = write_proteome_file(
        output_t1_path,
        t1_sequence_identifiers,
        sequence_identifiers___headers,
        sequence_identifiers___sequences,
        logger
    )

    # ========================================================================
    # WRITE T0 PROTEOME
    # ========================================================================

    output_t0_path = output_directory / f'{species_name}-T0.aa'
    t0_count = write_proteome_file(
        output_t0_path,
        t0_sequence_identifiers,
        sequence_identifiers___headers,
        sequence_identifiers___sequences,
        logger
    )

    # ========================================================================
    # WRITE SUMMARY REPORT
    # ========================================================================

    output_summary_path = output_directory / '1_ai-summary-evigene_extraction.tsv'
    write_summary_report(
        output_summary_path,
        species_name,
        input_fasta_path,
        classification_counts,
        t1_count,
        t0_count,
        logger
    )

    # ========================================================================
    # FINAL VALIDATION
    # ========================================================================

    # Verify output files were created and are non-empty
    for output_path in [ output_t1_path, output_t0_path, output_summary_path ]:
        if not output_path.exists():
            logger.error( f"CRITICAL ERROR: Expected output file was not created: {output_path}" )
            sys.exit( 1 )
        if output_path.stat().st_size == 0:
            logger.error( f"CRITICAL ERROR: Output file is empty: {output_path}" )
            sys.exit( 1 )

    # ========================================================================
    # COMPLETION
    # ========================================================================

    logger.info( '' )
    logger.info( '=' * 72 )
    logger.info( 'EXTRACTION COMPLETE' )
    logger.info( '=' * 72 )
    logger.info( f'T1 proteome ({t1_count} sequences): {output_t1_path}' )
    logger.info( f'T0 proteome ({t0_count} sequences): {output_t0_path}' )
    logger.info( f'Summary report: {output_summary_path}' )
    logger.info( f'Log file: {output_directory / "1_ai-log-extract_evigene_T0_T1_proteomes.log"}' )
    logger.info( '' )
    logger.info( f'Completed: {datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )}' )


if __name__ == '__main__':
    main()
