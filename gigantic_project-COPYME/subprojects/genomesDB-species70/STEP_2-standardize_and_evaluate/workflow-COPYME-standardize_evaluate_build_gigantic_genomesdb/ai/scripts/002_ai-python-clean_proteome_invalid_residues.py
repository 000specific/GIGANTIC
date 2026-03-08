#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 27 00:30 | Purpose: Clean proteome FASTA files by replacing invalid residues with X
# Human: Eric Edsinger

"""
002_ai-python-clean_proteome_invalid_residues.py

Clean proteome FASTA files by replacing invalid amino acid characters (like '.')
with 'X' (unknown residue). Generate a correction map documenting all changes.

Some proteome sources use '.' to represent stop codons or unknown residues,
but BLAST requires 'X' for unknown amino acids. This script:
1. Reads all proteomes from a directory
2. Replaces invalid characters with 'X'
3. Writes cleaned proteomes back (in-place or to output directory)
4. Generates a detailed correction map TSV file

Inputs:
    - Proteomes directory (FASTA files ending in -T1-proteome.aa)

Outputs:
    - Cleaned proteome files (overwrites originals or writes to output dir)
    - Correction map TSV: sequence_header, position, original_character, replacement_character

Usage:
    python3 002_ai-python-clean_proteome_invalid_residues.py \\
        --proteomes-dir PATH_TO_PROTEOMES \\
        --output-dir OUTPUT_pipeline/2-output
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime


# ============================================================================
# CONSTANTS
# ============================================================================

# Valid standard amino acid characters (20 standard + selenocysteine U + pyrrolysine O)
# Plus common placeholders: X (unknown), * (stop)
VALID_AMINO_ACIDS = set( 'ACDEFGHIKLMNPQRSTUVWXY*' )

# Characters to replace with X
INVALID_CHARACTERS = set( '.' )


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging( log_file_path: Path ) -> logging.Logger:
    """
    Configure logging to both file and console.

    Args:
        log_file_path: Path to the log file

    Returns:
        Configured logger instance
    """

    logger = logging.getLogger( 'clean_proteome_invalid_residues' )
    logger.setLevel( logging.DEBUG )

    # File handler
    file_handler = logging.FileHandler( log_file_path, mode = 'w' )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s | %(levelname)-8s | %(message)s', datefmt = '%Y-%m-%d %H:%M:%S' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    # Console handler
    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(levelname)-8s | %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    return logger


# ============================================================================
# PROTEOME CLEANING
# ============================================================================

def clean_proteome_file(
    input_proteome_path: Path,
    output_proteome_path: Path,
    correction_records: list,
    logger: logging.Logger
) -> dict:
    """
    Clean a single proteome FASTA file by replacing invalid residues.

    Args:
        input_proteome_path: Path to input proteome FASTA
        output_proteome_path: Path for cleaned output
        correction_records: List to append correction records to
        logger: Logger instance

    Returns:
        Dictionary with cleaning statistics
    """

    proteome_name = input_proteome_path.stem
    total_sequences = 0
    sequences_with_corrections = 0
    total_corrections = 0

    cleaned_lines = []
    current_header = ""
    current_sequence_position = 0

    with open( input_proteome_path, 'r' ) as input_proteome:
        for line in input_proteome:
            line = line.rstrip( '\n' )

            if line.startswith( '>' ):
                # Header line - keep as is
                current_header = line[ 1: ]  # Remove leading >
                current_sequence_position = 0
                total_sequences += 1
                cleaned_lines.append( line )

            else:
                # Sequence line - check for invalid characters
                cleaned_sequence = []
                line_had_corrections = False

                for character in line:
                    current_sequence_position += 1

                    if character in INVALID_CHARACTERS:
                        # Record the correction
                        correction_record = {
                            'proteome': proteome_name,
                            'sequence_header': current_header,
                            'position': current_sequence_position,
                            'original_character': character,
                            'replacement_character': 'X'
                        }
                        correction_records.append( correction_record )
                        cleaned_sequence.append( 'X' )
                        total_corrections += 1
                        line_had_corrections = True

                    else:
                        cleaned_sequence.append( character )

                if line_had_corrections:
                    sequences_with_corrections += 1

                cleaned_lines.append( ''.join( cleaned_sequence ) )

    # Write cleaned proteome
    with open( output_proteome_path, 'w' ) as output_proteome:
        for cleaned_line in cleaned_lines:
            output = cleaned_line + '\n'
            output_proteome.write( output )

    return {
        'proteome': proteome_name,
        'total_sequences': total_sequences,
        'sequences_with_corrections': sequences_with_corrections,
        'total_corrections': total_corrections
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: clean proteome files and generate correction map.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Clean proteome FASTA files by replacing invalid residues with X.',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--proteomes-dir',
        type = str,
        default = '../../output_to_input/gigantic_proteomes',
        help = 'Path to proteomes directory (default: ../../output_to_input/gigantic_proteomes)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/2-output',
        help = 'Base output directory for logs and correction map (default: OUTPUT_pipeline/2-output)'
    )

    parser.add_argument(
        '--in-place',
        action = 'store_true',
        default = True,
        help = 'Modify proteome files in place (default: True)'
    )

    arguments = parser.parse_args()

    # ========================================================================
    # PATH SETUP
    # ========================================================================

    proteomes_directory = Path( arguments.proteomes_dir )
    output_base_directory = Path( arguments.output_dir )

    output_correction_map_path = output_base_directory / '2_ai-proteome_residue_corrections.tsv'
    output_summary_path = output_base_directory / '2_ai-proteome_cleaning_summary.tsv'
    output_log_path = output_base_directory / '2_ai-log-clean_proteome_invalid_residues.log'

    # Create output directory
    output_base_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC genomesDB STEP_2 - Clean Proteome Invalid Residues" )
    logger.info( "Script: 002_ai-python-clean_proteome_invalid_residues.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Proteomes directory: {proteomes_directory}" )
    logger.info( f"Output directory: {output_base_directory}" )
    logger.info( f"In-place modification: {arguments.in_place}" )
    logger.info( "" )

    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================

    if not proteomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Proteomes directory not found: {proteomes_directory}" )
        sys.exit( 1 )

    # Find all proteome files
    proteome_files = sorted( proteomes_directory.glob( '*-T1-proteome.aa' ) )

    if not proteome_files:
        logger.error( f"CRITICAL ERROR: No proteome files found in {proteomes_directory}" )
        logger.error( "Expected files matching pattern: *-T1-proteome.aa" )
        sys.exit( 1 )

    logger.info( f"Found {len( proteome_files )} proteome files" )
    logger.info( "" )

    # ========================================================================
    # PROCESS PROTEOMES
    # ========================================================================

    logger.info( "Processing proteomes..." )
    logger.info( "" )

    all_correction_records = []
    proteome_summaries = []
    proteomes_with_corrections = 0
    total_corrections_all = 0

    for proteome_file in proteome_files:
        # For in-place, output = input
        output_path = proteome_file

        result = clean_proteome_file(
            input_proteome_path = proteome_file,
            output_proteome_path = output_path,
            correction_records = all_correction_records,
            logger = logger
        )

        proteome_summaries.append( result )

        if result[ 'total_corrections' ] > 0:
            proteomes_with_corrections += 1
            total_corrections_all += result[ 'total_corrections' ]
            logger.info( f"  CLEANED: {result[ 'proteome' ]} - {result[ 'total_corrections' ]} corrections" )
        else:
            logger.debug( f"  OK: {result[ 'proteome' ]} - no corrections needed" )

    # ========================================================================
    # WRITE CORRECTION MAP
    # ========================================================================

    logger.info( "" )
    logger.info( f"Writing correction map to: {output_correction_map_path}" )

    with open( output_correction_map_path, 'w' ) as output_correction_map:
        # Header
        header = "Proteome_Name (proteome file name without extension)\t"
        header += "Sequence_Header (FASTA header line without leading >)\t"
        header += "Position (1-indexed position in sequence)\t"
        header += "Original_Character (character that was replaced)\t"
        header += "Replacement_Character (character used as replacement)\n"
        output_correction_map.write( header )

        # Data rows
        for record in all_correction_records:
            output = record[ 'proteome' ] + '\t'
            output += record[ 'sequence_header' ] + '\t'
            output += str( record[ 'position' ] ) + '\t'
            output += record[ 'original_character' ] + '\t'
            output += record[ 'replacement_character' ] + '\n'
            output_correction_map.write( output )

    logger.info( f"  Wrote {len( all_correction_records )} correction records" )

    # ========================================================================
    # WRITE SUMMARY
    # ========================================================================

    logger.info( f"Writing summary to: {output_summary_path}" )

    with open( output_summary_path, 'w' ) as output_summary:
        # Header
        header = "Proteome_Name (proteome file name without extension)\t"
        header += "Total_Sequences (number of sequences in proteome)\t"
        header += "Sequences_With_Corrections (sequences that had invalid residues)\t"
        header += "Total_Corrections (total number of residues replaced)\n"
        output_summary.write( header )

        # Data rows - only proteomes with corrections
        for summary in proteome_summaries:
            if summary[ 'total_corrections' ] > 0:
                output = summary[ 'proteome' ] + '\t'
                output += str( summary[ 'total_sequences' ] ) + '\t'
                output += str( summary[ 'sequences_with_corrections' ] ) + '\t'
                output += str( summary[ 'total_corrections' ] ) + '\n'
                output_summary.write( output )

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================

    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Total proteomes processed: {len( proteome_files )}" )
    logger.info( f"Proteomes with corrections: {proteomes_with_corrections}" )
    logger.info( f"Proteomes unchanged: {len( proteome_files ) - proteomes_with_corrections}" )
    logger.info( f"Total corrections made: {total_corrections_all}" )
    logger.info( "" )
    logger.info( f"Correction map: {output_correction_map_path}" )
    logger.info( f"Summary: {output_summary_path}" )
    logger.info( f"Log: {output_log_path}" )

    # NOTE: output_to_input is populated by STEP_4, not STEP_2.
    # STEP_2 produces cleaned proteomes in OUTPUT_pipeline/2-output/ for user
    # evaluation. STEP_4 then copies the selected species to output_to_input/.

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================

    logger.info( "" )
    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )
    logger.info( "COMPLETE" )
    logger.info( "=" * 80 )

    print( "" )
    print( f"Done! Cleaned {proteomes_with_corrections} proteomes with {total_corrections_all} total corrections." )
    print( f"Correction map: {output_correction_map_path}" )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()
