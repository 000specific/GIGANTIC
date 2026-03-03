#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Combine InterProScan chunk results into a single per-species annotation file
# Human: Eric Edsinger

"""
004_ai-python-combine_interproscan_results.py

Combines InterProScan results from multiple chunk TSV files back into a single
per-species annotation file. After InterProScan runs on individual proteome chunks
in parallel, this script merges all chunk outputs for one species and sorts
by protein identifier for reproducibility.

InterProScan produces a 15-column TSV with no header. The columns are:
    protein_id  md5  length  analysis_db  signature_id  signature_desc
    start  stop  score  status  date  interpro_id  interpro_desc  go_terms  pathway

This script concatenates all chunk files and sorts by the first column (protein_id)
to ensure reproducible output regardless of chunk processing order.

Input:
    --input-dir: Directory containing chunk result TSV files (passed by Nextflow)
    --output-dir: Directory for the combined output file
    --phyloname: GIGANTIC phyloname for the species (used in output naming)

Output:
    {phyloname}_interproscan_results.tsv
        Combined InterProScan results for all chunks, sorted by protein identifier.
        Same 15-column TSV format as InterProScan output (no header added,
        since InterProScan native format has no header).

    4_ai-log-combine_interproscan_results_{phyloname}.log

Usage:
    python3 004_ai-python-combine_interproscan_results.py \\
        --input-dir . \\
        --output-dir . \\
        --phyloname Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path, phyloname: str ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( f'004_combine_interproscan_results_{phyloname}' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / f'4_ai-log-combine_interproscan_results_{phyloname}.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def combine_chunk_results( input_directory: Path, output_directory: Path, phyloname: str, logger: logging.Logger ) -> None:
    """
    Find all InterProScan chunk result TSV files for the given species,
    concatenate them, sort by protein identifier, and write a single output file.
    """

    logger.info( f"Combining InterProScan chunk results for: {phyloname}" )
    logger.info( f"Input directory: {input_directory}" )
    logger.info( f"Output directory: {output_directory}" )

    # =========================================================================
    # Find all chunk result files
    # =========================================================================
    # Chunk result files follow the pattern:
    #   {phyloname}_chunk_NNN_interproscan.tsv
    # They are placed in the input directory by Nextflow's groupTuple
    # =========================================================================

    chunk_result_files = sorted( input_directory.glob( f"{phyloname}_chunk_*_interproscan.tsv" ) )

    if len( chunk_result_files ) == 0:
        # Also try without the phyloname prefix in case Nextflow staging renamed them
        chunk_result_files = sorted( input_directory.glob( "*_interproscan.tsv" ) )

    if len( chunk_result_files ) == 0:
        logger.error( "CRITICAL ERROR: No InterProScan chunk result files found!" )
        logger.error( f"Searched directory: {input_directory}" )
        logger.error( f"Expected files matching: {phyloname}_chunk_*_interproscan.tsv" )
        logger.error( "Ensure InterProScan (script 003) completed successfully for all chunks." )
        sys.exit( 1 )

    logger.info( f"Found {len( chunk_result_files )} chunk result file(s):" )
    for chunk_result_file in chunk_result_files:
        logger.debug( f"  {chunk_result_file.name}" )

    # =========================================================================
    # Read all annotation lines from all chunk files
    # =========================================================================

    all_annotation_lines = []
    files___line_counts = {}

    for chunk_result_file in chunk_result_files:
        chunk_line_count = 0

        with open( chunk_result_file, 'r' ) as input_chunk_results:
            for line in input_chunk_results:
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                all_annotation_lines.append( line )
                chunk_line_count += 1

        files___line_counts[ chunk_result_file.name ] = chunk_line_count
        logger.debug( f"  {chunk_result_file.name}: {chunk_line_count} annotations" )

    logger.info( f"Total annotations collected from all chunks: {len( all_annotation_lines )}" )

    # =========================================================================
    # Sort by protein identifier (column 0) for reproducibility
    # =========================================================================
    # InterProScan TSV is tab-separated. Sorting by the first column ensures
    # consistent output regardless of which chunk finished first.
    # =========================================================================

    logger.info( "Sorting annotations by protein identifier for reproducibility..." )

    all_annotation_lines.sort( key = lambda annotation_line: annotation_line.split( '\t' )[ 0 ] if '\t' in annotation_line else annotation_line )

    # =========================================================================
    # Write combined output
    # =========================================================================

    output_directory.mkdir( parents = True, exist_ok = True )

    output_file = output_directory / f"{phyloname}_interproscan_results.tsv"

    with open( output_file, 'w' ) as output_combined_results:
        for annotation_line in all_annotation_lines:
            output = annotation_line + '\n'
            output_combined_results.write( output )

    logger.info( f"Wrote combined results to: {output_file}" )

    # =========================================================================
    # Calculate statistics
    # =========================================================================

    # Count unique proteins with annotations
    unique_protein_identifiers = set()
    analysis_databases___counts = {}

    for annotation_line in all_annotation_lines:
        parts = annotation_line.split( '\t' )

        if len( parts ) >= 1:
            unique_protein_identifiers.add( parts[ 0 ] )

        # Column 3 (index 3) is the analysis database name
        if len( parts ) >= 4:
            analysis_database = parts[ 3 ]
            if analysis_database in analysis_databases___counts:
                analysis_databases___counts[ analysis_database ] += 1
            else:
                analysis_databases___counts[ analysis_database ] = 1

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( f"Script 004 completed successfully for: {phyloname}" )
    logger.info( "========================================" )
    logger.info( f"  Chunk files combined: {len( chunk_result_files )}" )
    logger.info( f"  Total annotation lines: {len( all_annotation_lines )}" )
    logger.info( f"  Unique proteins with annotations: {len( unique_protein_identifiers )}" )
    logger.info( f"  Output file: {output_file}" )

    if analysis_databases___counts:
        logger.info( "" )
        logger.info( "Annotations per analysis database:" )
        for analysis_database in sorted( analysis_databases___counts.keys() ):
            count = analysis_databases___counts[ analysis_database ]
            logger.info( f"  {analysis_database}: {count}" )

    # Per-chunk breakdown
    logger.info( "" )
    logger.info( "Per-chunk annotation counts:" )
    for filename in sorted( files___line_counts.keys() ):
        line_count = files___line_counts[ filename ]
        logger.info( f"  {filename}: {line_count}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Combine InterProScan chunk results into a single per-species annotation file'
    )

    parser.add_argument(
        '--input-dir',
        type = str,
        required = True,
        help = 'Directory containing InterProScan chunk result TSV files'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Directory for the combined output file (default: current directory)'
    )

    parser.add_argument(
        '--phyloname',
        type = str,
        required = True,
        help = 'GIGANTIC phyloname for the species (used in output file naming)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    input_directory = Path( arguments.input_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory, arguments.phyloname )

    logger.info( "=" * 70 )
    logger.info( "Script 004: Combine InterProScan Chunk Results" )
    logger.info( "=" * 70 )

    # Run combination
    combine_chunk_results( input_directory, output_directory, arguments.phyloname, logger )


if __name__ == '__main__':
    main()
