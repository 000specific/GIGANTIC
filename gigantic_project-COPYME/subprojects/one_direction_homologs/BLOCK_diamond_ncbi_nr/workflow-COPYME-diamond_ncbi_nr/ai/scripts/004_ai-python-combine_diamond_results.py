#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Combine DIAMOND results from N parts into per-species files
# Human: Eric Edsinger

"""
004_ai-python-combine_diamond_results.py

Combines the N split DIAMOND result files for a single species into one
combined file. This reverses the split from script 002.

Input:
    Multiple DIAMOND result files for one species (from script 003)

Output:
    combined_{species_name}.tsv (all DIAMOND hits for this species)

Usage:
    python3 004_ai-python-combine_diamond_results.py \\
        --species-name Homo_sapiens \\
        --input-files part_001_diamond.tsv part_002_diamond.tsv ... \\
        --output-dir OUTPUT_pipeline/4-output
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir ):
    """Configure logging to both console and file."""

    log_file = Path( output_dir ) / "4_ai-log-combine_diamond_results.log"

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

    parser = argparse.ArgumentParser( description = "Combine DIAMOND results for one species" )
    parser.add_argument( "--species-name", required = True, help = "Species name (Genus_species)" )
    parser.add_argument( "--input-files", nargs = '+', required = True, help = "DIAMOND result files to combine" )
    parser.add_argument( "--output-dir", required = True, help = "Output directory" )
    arguments = parser.parse_args()

    species_name = arguments.species_name
    input_file_paths = [ Path( f ) for f in arguments.input_files ]
    output_directory = Path( arguments.output_dir )
    output_directory.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_directory )
    logger.info( "=" * 72 )
    logger.info( f"Script 004: Combine DIAMOND Results - {species_name}" )
    logger.info( "=" * 72 )
    logger.info( f"Species: {species_name}" )
    logger.info( f"Input files: {len( input_file_paths )}" )

    # ========================================================================
    # Validate input files
    # ========================================================================

    existing_files = []
    for input_file_path in sorted( input_file_paths ):
        if input_file_path.exists():
            existing_files.append( input_file_path )
        else:
            logger.warning( f"  File not found (skipping): {input_file_path}" )

    if len( existing_files ) == 0:
        logger.error( f"CRITICAL ERROR: No DIAMOND result files found for {species_name}" )
        sys.exit( 1 )

    # ========================================================================
    # Combine all part files
    # ========================================================================

    output_file_path = output_directory / f"combined_{species_name}.tsv"
    total_hits = 0
    non_empty_parts = 0

    with open( output_file_path, 'w' ) as output_combined:
        for input_file_path in sorted( existing_files ):

            file_size = input_file_path.stat().st_size
            if file_size == 0:
                logger.info( f"  Empty file (skipping): {input_file_path.name}" )
                continue

            non_empty_parts += 1
            part_hits = 0

            with open( input_file_path, 'r' ) as input_part:
                for line in input_part:
                    output_combined.write( line )
                    part_hits += 1

            total_hits += part_hits

    # ========================================================================
    # Summary
    # ========================================================================

    logger.info( "" )
    logger.info( f"Combined results for {species_name}:" )
    logger.info( f"  Non-empty parts: {non_empty_parts} / {len( existing_files )}" )
    logger.info( f"  Total hits: {total_hits}" )
    logger.info( f"  Output: {output_file_path}" )
    logger.info( "Script 004 complete." )


if __name__ == "__main__":
    main()
