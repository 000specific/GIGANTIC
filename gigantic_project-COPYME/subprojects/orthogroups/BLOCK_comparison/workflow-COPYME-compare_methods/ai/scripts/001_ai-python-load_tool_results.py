#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Load standardized orthogroup results from all tool projects
# Human: Eric Edsinger

"""
001_ai-python-load_tool_results.py

Loads standardized orthogroup results from each tool project's output_to_input/
directory. Validates that all expected files are present and creates a unified
dataset for cross-method comparison in script 002.

Each tool project produces identical output_to_input/ contents:
    - orthogroups_gigantic_ids.tsv (orthogroup assignments)
    - gene_count_gigantic_ids.tsv (gene counts per species per orthogroup)
    - summary_statistics.tsv (overall clustering statistics)
    - per_species_summary.tsv (per-species orthogroup statistics)

Input:
    --orthofinder-dir: Path to BLOCK_orthofinder/output_to_input/
    --orthohmm-dir: Path to BLOCK_orthohmm/output_to_input/
    --broccoli-dir: Path to BLOCK_broccoli/output_to_input/

Output:
    OUTPUT_pipeline/1-output/1_ai-loaded_tool_results_summary.tsv
        Summary of loaded results from each tool

    OUTPUT_pipeline/1-output/tool_orthogroups/
        Copies of orthogroup files from each tool (for script 002)

Usage:
    python3 001_ai-python-load_tool_results.py \\
        --orthofinder-dir ../../BLOCK_orthofinder/output_to_input \\
        --orthohmm-dir ../../BLOCK_orthohmm/output_to_input \\
        --broccoli-dir ../../BLOCK_broccoli/output_to_input
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '001_load_tool_results' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '1_ai-log-load_tool_results.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_tool_results( tool_name: str, tool_directory: Path, output_tool_directory: Path, logger: logging.Logger ) -> dict:
    """
    Load and validate results from one tool project's output_to_input/ directory.

    Returns dictionary with tool summary information.
    """

    logger.info( f"Loading results for: {tool_name}" )
    logger.info( f"  Source directory: {tool_directory}" )

    # Expected standardized output files
    expected_files = {
        'orthogroups': 'orthogroups_gigantic_ids.tsv',
        'gene_count': 'gene_count_gigantic_ids.tsv',
        'summary_statistics': 'summary_statistics.tsv',
        'per_species_summary': 'per_species_summary.tsv'
    }

    tool_summary = {
        'tool_name': tool_name,
        'source_directory': str( tool_directory ),
        'files_found': 0,
        'files_missing': 0,
        'orthogroup_count': 0,
        'total_genes': 0
    }

    missing_files = []

    for file_key in expected_files:
        filename = expected_files[ file_key ]
        file_path = tool_directory / filename

        if file_path.exists():
            tool_summary[ 'files_found' ] += 1

            # Copy to comparison working directory
            destination = output_tool_directory / f"{tool_name}_{filename}"
            shutil.copy2( str( file_path ), str( destination ) )
            logger.debug( f"  Copied: {filename} -> {destination.name}" )
        else:
            tool_summary[ 'files_missing' ] += 1
            missing_files.append( filename )
            logger.warning( f"  Missing: {filename}" )

    # Parse orthogroups file to get counts
    orthogroups_path = tool_directory / expected_files[ 'orthogroups' ]

    if orthogroups_path.exists():
        orthogroup_count = 0
        total_genes = 0

        # OG_ID	gene1	gene2	gene3
        # OG0000001	g_123-t_1-p_1-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	g_456-t_1-p_1-n_...

        with open( orthogroups_path, 'r' ) as input_orthogroups:
            for line in input_orthogroups:
                line = line.strip()
                if not line:
                    continue

                parts = line.split( '\t' )
                genes = [ gene for gene in parts[ 1: ] if gene ]

                orthogroup_count += 1
                total_genes += len( genes )

        tool_summary[ 'orthogroup_count' ] = orthogroup_count
        tool_summary[ 'total_genes' ] = total_genes

        logger.info( f"  Orthogroups: {orthogroup_count}" )
        logger.info( f"  Total genes: {total_genes}" )

    if missing_files:
        logger.warning( f"  {tool_name} has {len( missing_files )} missing files" )

    return tool_summary


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Load standardized orthogroup results from all tool projects'
    )

    parser.add_argument(
        '--orthofinder-dir',
        type = str,
        default = '../../BLOCK_orthofinder/output_to_input',
        help = 'Path to BLOCK_orthofinder/output_to_input/ (default: ../../BLOCK_orthofinder/output_to_input)'
    )

    parser.add_argument(
        '--orthohmm-dir',
        type = str,
        default = '../../BLOCK_orthohmm/output_to_input',
        help = 'Path to BLOCK_orthohmm/output_to_input/ (default: ../../BLOCK_orthohmm/output_to_input)'
    )

    parser.add_argument(
        '--broccoli-dir',
        type = str,
        default = '../../BLOCK_broccoli/output_to_input',
        help = 'Path to BLOCK_broccoli/output_to_input/ (default: ../../BLOCK_broccoli/output_to_input)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/1-output',
        help = 'Output directory (default: OUTPUT_pipeline/1-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    orthofinder_directory = Path( arguments.orthofinder_dir )
    orthohmm_directory = Path( arguments.orthohmm_dir )
    broccoli_directory = Path( arguments.broccoli_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directories
    output_directory.mkdir( parents = True, exist_ok = True )
    output_tool_directory = output_directory / 'tool_orthogroups'
    output_tool_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 001: Load Tool Results for Comparison" )
    logger.info( "=" * 70 )

    # Define tools to load
    tools___directories = {
        'orthofinder': orthofinder_directory,
        'orthohmm': orthohmm_directory,
        'broccoli': broccoli_directory
    }

    # Track which tools have data available
    tool_summaries = []
    tools_with_data = 0
    tools_missing = 0

    for tool_name in tools___directories:
        tool_directory = tools___directories[ tool_name ]

        if not tool_directory.exists():
            logger.warning( f"Tool directory not found: {tool_directory}" )
            logger.warning( f"  {tool_name} results not available yet." )
            tools_missing += 1
            tool_summaries.append( {
                'tool_name': tool_name,
                'source_directory': str( tool_directory ),
                'files_found': 0,
                'files_missing': 4,
                'orthogroup_count': 0,
                'total_genes': 0
            } )
            continue

        tool_summary = load_tool_results(
            tool_name = tool_name,
            tool_directory = tool_directory,
            output_tool_directory = output_tool_directory,
            logger = logger
        )
        tool_summaries.append( tool_summary )

        if tool_summary[ 'files_found' ] > 0:
            tools_with_data += 1

    # Validate: at least 2 tools must have data for comparison
    logger.info( "" )
    logger.info( f"Tools with data: {tools_with_data}" )
    logger.info( f"Tools missing: {tools_missing}" )

    if tools_with_data < 2:
        logger.error( "CRITICAL ERROR: Need at least 2 tools with results for comparison!" )
        logger.error( f"Only {tools_with_data} tool(s) have data available." )
        logger.error( "Run the tool pipelines first to generate results." )
        sys.exit( 1 )

    # Write summary file
    summary_file = output_directory / '1_ai-loaded_tool_results_summary.tsv'

    with open( summary_file, 'w' ) as output_summary:
        # Write header
        header = 'Tool_Name (orthogroup detection tool)' + '\t'
        header += 'Source_Directory (path to output_to_input directory)' + '\t'
        header += 'Files_Found (number of expected files present)' + '\t'
        header += 'Files_Missing (number of expected files missing)' + '\t'
        header += 'Orthogroup_Count (number of orthogroups detected)' + '\t'
        header += 'Total_Genes (total genes assigned to orthogroups)' + '\n'
        output_summary.write( header )

        for tool_summary in tool_summaries:
            output = tool_summary[ 'tool_name' ] + '\t'
            output += tool_summary[ 'source_directory' ] + '\t'
            output += str( tool_summary[ 'files_found' ] ) + '\t'
            output += str( tool_summary[ 'files_missing' ] ) + '\t'
            output += str( tool_summary[ 'orthogroup_count' ] ) + '\t'
            output += str( tool_summary[ 'total_genes' ] ) + '\n'
            output_summary.write( output )

    logger.info( f"Wrote summary to: {summary_file}" )
    logger.info( "Script 001 completed successfully" )


if __name__ == '__main__':
    main()
