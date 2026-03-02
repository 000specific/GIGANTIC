#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Compile per-species statistics into master summary table
# Human: Eric Edsinger

"""
006_ai-python-compile_statistics.py

Combines individual per-species statistics files (from script 005) into
a single master summary table covering all species.

Input:
    Individual {species}_statistics.tsv files (from script 005)

Output:
    6_ai-all_species_statistics.tsv (one row per species)

Usage:
    python3 006_ai-python-compile_statistics.py \\
        --input-files species1_statistics.tsv species2_statistics.tsv ... \\
        --output-dir OUTPUT_pipeline/6-output
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir ):
    """Configure logging to both console and file."""

    log_file = Path( output_dir ) / "6_ai-log-compile_statistics.log"

    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s | %(levelname)s | %(message)s",
        handlers = [
            logging.FileHandler( log_file ),
            logging.StreamHandler( sys.stdout )
        ]
    )

    return logging.getLogger( __name__ )


def main():

    parser = argparse.ArgumentParser( description = "Compile species statistics into master summary" )
    parser.add_argument( "--input-files", nargs = '+', required = True, help = "Per-species statistics files" )
    parser.add_argument( "--output-dir", required = True, help = "Output directory" )
    arguments = parser.parse_args()

    input_file_paths = [ Path( f ) for f in arguments.input_files ]
    output_directory = Path( arguments.output_dir )
    output_directory.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_directory )
    logger.info( "=" * 72 )
    logger.info( "Script 006: Compile All Species Statistics" )
    logger.info( "=" * 72 )
    logger.info( f"Input files: {len( input_file_paths )}" )

    # ========================================================================
    # Read all statistics files
    # ========================================================================

    header_row = None
    data_rows = []

    for input_file_path in sorted( input_file_paths ):

        if not input_file_path.exists():
            logger.warning( f"  File not found (skipping): {input_file_path}" )
            continue

        if input_file_path.stat().st_size == 0:
            logger.warning( f"  Empty file (skipping): {input_file_path}" )
            continue

        # Species_Name	Total_Queries_Processed	Self_Hits_Found	Non_Self_Hits_Found	...
        # Homo_sapiens	20000	18500	19200	800	1500
        with open( input_file_path, 'r' ) as input_statistics:
            lines = input_statistics.readlines()

            if len( lines ) < 2:
                logger.warning( f"  Incomplete file (skipping): {input_file_path}" )
                continue

            # Capture header from first file
            if header_row is None:
                header_row = lines[ 0 ].strip()

            # Capture data row
            data_row = lines[ 1 ].strip()
            if data_row:
                data_rows.append( data_row )
                species_name = data_row.split( '\t' )[ 0 ]
                logger.info( f"  Read: {species_name}" )

    # ========================================================================
    # Validate we have data
    # ========================================================================

    if len( data_rows ) == 0:
        logger.error( "CRITICAL ERROR: No statistics data found!" )
        logger.error( "Check that script 005 completed successfully for at least one species." )
        sys.exit( 1 )

    if header_row is None:
        logger.error( "CRITICAL ERROR: No header row found in any statistics file!" )
        sys.exit( 1 )

    # ========================================================================
    # Write master statistics file
    # ========================================================================

    output_statistics_path = output_directory / "6_ai-all_species_statistics.tsv"

    with open( output_statistics_path, 'w' ) as output_master:

        output = header_row + '\n'
        output_master.write( output )

        for data_row in data_rows:
            output = data_row + '\n'
            output_master.write( output )

    # ========================================================================
    # Summary
    # ========================================================================

    logger.info( "" )
    logger.info( "=" * 72 )
    logger.info( "Compilation Summary" )
    logger.info( "=" * 72 )
    logger.info( f"Species compiled: {len( data_rows )}" )
    logger.info( f"Master statistics: {output_statistics_path}" )
    logger.info( "Script 006 complete." )


if __name__ == "__main__":
    main()
