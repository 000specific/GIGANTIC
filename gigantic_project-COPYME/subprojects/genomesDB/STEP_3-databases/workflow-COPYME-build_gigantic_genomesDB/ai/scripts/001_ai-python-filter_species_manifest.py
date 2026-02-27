#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: Filter species selection manifest to Include=YES only
# Human: Eric Edsinger

"""
001_ai-python-filter_species_manifest.py

Filter the species selection manifest from STEP_2 to keep only species marked
with Include=YES. Creates a filtered manifest for BLAST database building.

Inputs:
    - Species selection manifest from STEP_2's output_to_input/
      (columns include: phyloname, Include, BUSCO scores, etc.)

Outputs:
    - Filtered manifest with only Include=YES species
    - Summary log with counts

Usage:
    python3 001_ai-python-filter_species_manifest.py \\
        --input-manifest PATH_TO_MANIFEST.tsv \\
        --output-dir OUTPUT_pipeline/1-output
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime


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

    logger = logging.getLogger( 'filter_species_manifest' )
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
# MANIFEST FILTERING
# ============================================================================

def filter_manifest(
    input_manifest_path: Path,
    output_manifest_path: Path,
    logger: logging.Logger
) -> dict:
    """
    Filter the species selection manifest to Include=YES only.

    Args:
        input_manifest_path: Path to input manifest from STEP_2
        output_manifest_path: Path for filtered manifest output
        logger: Logger instance

    Returns:
        Dictionary with filtering statistics
    """

    logger.info( f"Reading manifest from: {input_manifest_path}" )

    if not input_manifest_path.exists():
        logger.error( f"CRITICAL ERROR: Input manifest not found: {input_manifest_path}" )
        logger.error( "STEP_2 must be run before STEP_3." )
        logger.error( "Expected location: STEP_2/output_to_input/species_selection_manifest.tsv" )
        sys.exit( 1 )

    total_species = 0
    included_species = 0
    excluded_species = 0
    included_entries = []
    header_line = ""
    include_column_index = -1

    with open( input_manifest_path, 'r' ) as input_manifest:
        # Skip comment lines and find the actual header
        header_line = input_manifest.readline().strip()
        while header_line.startswith( '#' ) or not header_line:
            header_line = input_manifest.readline().strip()

        parts_header = header_line.split( '\t' )

        # Find the Include column (look for column containing "Include")
        for index, column_header in enumerate( parts_header ):
            if 'Include' in column_header:
                include_column_index = index
                break

        if include_column_index == -1:
            logger.error( "CRITICAL ERROR: No 'Include' column found in manifest!" )
            logger.error( f"Columns found: {parts_header}" )
            logger.error( "The manifest must have an 'Include' column with YES/NO values." )
            sys.exit( 1 )

        logger.info( f"Found Include column at index {include_column_index}" )

        # Process each species entry
        for line in input_manifest:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue

            total_species += 1
            parts = line.split( '\t' )

            if len( parts ) <= include_column_index:
                logger.warning( f"Line has fewer columns than expected: {line}" )
                excluded_species += 1
                continue

            include_value = parts[ include_column_index ].strip().upper()

            if include_value == 'YES':
                included_species += 1
                included_entries.append( line )
                logger.debug( f"INCLUDED: {parts[ 0 ]}" )
            else:
                excluded_species += 1
                logger.debug( f"EXCLUDED: {parts[ 0 ]} (Include={include_value})" )

    # Write filtered manifest
    logger.info( f"Writing filtered manifest to: {output_manifest_path}" )

    with open( output_manifest_path, 'w' ) as output_manifest:
        output = header_line + '\n'
        output_manifest.write( output )

        for entry in included_entries:
            output = entry + '\n'
            output_manifest.write( output )

    return {
        'total_species': total_species,
        'included_species': included_species,
        'excluded_species': excluded_species
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: filter species selection manifest.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Filter species selection manifest to Include=YES only.',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--input-manifest',
        type = str,
        default = '../../STEP_2-standardize_and_evaluate/output_to_input/species_selection_manifest.tsv',
        help = 'Path to species selection manifest from STEP_2 (default: ../../STEP_2-standardize_and_evaluate/output_to_input/species_selection_manifest.tsv)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/1-output',
        help = 'Base output directory (default: OUTPUT_pipeline/1-output)'
    )

    arguments = parser.parse_args()

    # ========================================================================
    # PATH SETUP
    # ========================================================================

    input_manifest_path = Path( arguments.input_manifest )
    output_base_directory = Path( arguments.output_dir )

    output_manifest_path = output_base_directory / '1_ai-filtered_species_manifest.tsv'
    output_log_path = output_base_directory / '1_ai-log-filter_species_manifest.log'

    # Create output directories
    output_base_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC genomesDB STEP_3 - Filter Species Manifest" )
    logger.info( "Script: 001_ai-python-filter_species_manifest.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Input manifest: {input_manifest_path}" )
    logger.info( f"Output directory: {output_base_directory}" )
    logger.info( "" )

    # ========================================================================
    # FILTER MANIFEST
    # ========================================================================

    result = filter_manifest(
        input_manifest_path = input_manifest_path,
        output_manifest_path = output_manifest_path,
        logger = logger
    )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Total species in manifest: {result[ 'total_species' ]}" )
    logger.info( f"Species with Include=YES: {result[ 'included_species' ]}" )
    logger.info( f"Species excluded: {result[ 'excluded_species' ]}" )
    logger.info( f"Filtered manifest: {output_manifest_path}" )
    logger.info( f"Log: {output_log_path}" )
    logger.info( "" )
    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )
    logger.info( "COMPLETE" )
    logger.info( "=" * 80 )

    print( "" )
    print( f"Done! Filtered manifest: {result[ 'included_species' ]} of {result[ 'total_species' ]} species selected." )
    print( f"Output: {output_manifest_path}" )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()
