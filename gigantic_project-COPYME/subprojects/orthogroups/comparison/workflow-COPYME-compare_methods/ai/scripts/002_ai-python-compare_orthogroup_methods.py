#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Cross-method comparison of orthogroup detection results
# Human: Eric Edsinger

"""
002_ai-python-compare_orthogroup_methods.py

Performs cross-method comparison of orthogroup detection results from
OrthoFinder, OrthoHMM, and Broccoli. Compares orthogroup sizes, species
coverage, gene assignment overlap, and method-specific statistics.

Input:
    --tool-results-dir: Path to 1-output/tool_orthogroups/ from script 001

Output:
    OUTPUT_pipeline/2-output/2_ai-method_comparison_summary.tsv
        Side-by-side comparison of key statistics

    OUTPUT_pipeline/2-output/2_ai-gene_overlap_between_methods.tsv
        Gene-level overlap between tools

    OUTPUT_pipeline/2-output/2_ai-orthogroup_size_comparison.tsv
        Size distribution comparison across methods

Usage:
    python3 002_ai-python-compare_orthogroup_methods.py \\
        --tool-results-dir OUTPUT_pipeline/1-output/tool_orthogroups
"""

import argparse
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '002_compare_methods' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '2_ai-log-compare_orthogroup_methods.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def parse_orthogroups( orthogroups_path: Path, logger: logging.Logger ) -> dict:
    """
    Parse standardized orthogroups file.

    Returns dictionary mapping orthogroup ID to set of genes.
    """

    orthogroups___genes = {}

    # OG0000001	gene_header_1	gene_header_2	gene_header_3
    # OG0000002	gene_header_4	gene_header_5

    with open( orthogroups_path, 'r' ) as input_orthogroups:
        for line in input_orthogroups:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            orthogroup_id = parts[ 0 ]
            genes = set( gene for gene in parts[ 1: ] if gene )

            orthogroups___genes[ orthogroup_id ] = genes

    logger.debug( f"  Parsed {len( orthogroups___genes )} orthogroups from {orthogroups_path.name}" )

    return orthogroups___genes


def parse_summary_statistics( summary_path: Path, logger: logging.Logger ) -> dict:
    """
    Parse summary statistics file from a tool.

    Returns dictionary of statistic name to value.
    """

    statistics___values = {}

    # Statistic (description of metric)	Value (calculated value)
    # Species_Count (number of species in analysis)	67

    with open( summary_path, 'r' ) as input_summary:
        header_line = input_summary.readline()

        for line in input_summary:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            statistic_name = parts[ 0 ]
            value = parts[ 1 ]

            # Extract the short identifier from the self-documenting header
            parts_statistic_name = statistic_name.split( ' (' )
            short_name = parts_statistic_name[ 0 ]

            statistics___values[ short_name ] = value

    return statistics___values


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Cross-method comparison of orthogroup detection results'
    )

    parser.add_argument(
        '--tool-results-dir',
        type = str,
        required = True,
        help = 'Path to 1-output/tool_orthogroups/ from script 001'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/2-output',
        help = 'Output directory (default: OUTPUT_pipeline/2-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    tool_results_directory = Path( arguments.tool_results_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 002: Cross-Method Orthogroup Comparison" )
    logger.info( "=" * 70 )

    # Validate input
    if not tool_results_directory.exists():
        logger.error( f"CRITICAL ERROR: Tool results directory not found: {tool_results_directory}" )
        logger.error( "Run script 001 first to load tool results." )
        sys.exit( 1 )

    # ==========================================================================
    # Load orthogroups from each tool
    # ==========================================================================

    tool_names = [ 'orthofinder', 'orthohmm', 'broccoli' ]
    tools___orthogroups = {}
    tools___all_genes = {}
    tools___statistics = {}

    for tool_name in tool_names:
        orthogroups_file = tool_results_directory / f"{tool_name}_orthogroups_gigantic_ids.tsv"
        summary_file = tool_results_directory / f"{tool_name}_summary_statistics.tsv"

        if orthogroups_file.exists():
            logger.info( f"Loading {tool_name} orthogroups..." )
            orthogroups___genes = parse_orthogroups( orthogroups_file, logger )
            tools___orthogroups[ tool_name ] = orthogroups___genes

            # Collect all genes assigned by this tool
            all_genes = set()
            for orthogroup_id in orthogroups___genes:
                all_genes.update( orthogroups___genes[ orthogroup_id ] )
            tools___all_genes[ tool_name ] = all_genes

            logger.info( f"  {tool_name}: {len( orthogroups___genes )} orthogroups, {len( all_genes )} genes" )
        else:
            logger.warning( f"  {tool_name} orthogroups not available" )

        if summary_file.exists():
            tools___statistics[ tool_name ] = parse_summary_statistics( summary_file, logger )

    available_tools = list( tools___orthogroups.keys() )
    logger.info( f"Available tools for comparison: {available_tools}" )

    if len( available_tools ) < 2:
        logger.error( "CRITICAL ERROR: Need at least 2 tools with data for comparison!" )
        sys.exit( 1 )

    # ==========================================================================
    # Method comparison summary
    # ==========================================================================

    logger.info( "" )
    logger.info( "Generating method comparison summary..." )

    comparison_file = output_directory / '2_ai-method_comparison_summary.tsv'

    with open( comparison_file, 'w' ) as output_comparison:
        # Write header
        header = 'Metric (comparison metric description)' + '\t'
        header += '\t'.join( [ f"{tool_name} (value for {tool_name})" for tool_name in tool_names ] )
        header += '\n'
        output_comparison.write( header )

        # Orthogroup count
        output = 'Orthogroup_Count (total orthogroups detected)'
        for tool_name in tool_names:
            if tool_name in tools___orthogroups:
                output += '\t' + str( len( tools___orthogroups[ tool_name ] ) )
            else:
                output += '\t' + 'N/A'
        output += '\n'
        output_comparison.write( output )

        # Total genes assigned
        output = 'Genes_Assigned (total genes assigned to orthogroups)'
        for tool_name in tool_names:
            if tool_name in tools___all_genes:
                output += '\t' + str( len( tools___all_genes[ tool_name ] ) )
            else:
                output += '\t' + 'N/A'
        output += '\n'
        output_comparison.write( output )

        # Mean orthogroup size
        output = 'Mean_Orthogroup_Size (average genes per orthogroup)'
        for tool_name in tool_names:
            if tool_name in tools___orthogroups:
                sizes = [ len( genes ) for genes in tools___orthogroups[ tool_name ].values() ]
                mean_size = sum( sizes ) / len( sizes ) if sizes else 0
                output += '\t' + f"{mean_size:.2f}"
            else:
                output += '\t' + 'N/A'
        output += '\n'
        output_comparison.write( output )

        # Median orthogroup size
        output = 'Median_Orthogroup_Size (median genes per orthogroup)'
        for tool_name in tool_names:
            if tool_name in tools___orthogroups:
                sizes = sorted( [ len( genes ) for genes in tools___orthogroups[ tool_name ].values() ] )
                median_size = sizes[ len( sizes ) // 2 ] if sizes else 0
                output += '\t' + str( median_size )
            else:
                output += '\t' + 'N/A'
        output += '\n'
        output_comparison.write( output )

        # Max orthogroup size
        output = 'Max_Orthogroup_Size (largest orthogroup gene count)'
        for tool_name in tool_names:
            if tool_name in tools___orthogroups:
                sizes = [ len( genes ) for genes in tools___orthogroups[ tool_name ].values() ]
                max_size = max( sizes ) if sizes else 0
                output += '\t' + str( max_size )
            else:
                output += '\t' + 'N/A'
        output += '\n'
        output_comparison.write( output )

        # Singleton count
        output = 'Singleton_Orthogroups (orthogroups with single gene)'
        for tool_name in tool_names:
            if tool_name in tools___orthogroups:
                singleton_count = sum( 1 for genes in tools___orthogroups[ tool_name ].values() if len( genes ) == 1 )
                output += '\t' + str( singleton_count )
            else:
                output += '\t' + 'N/A'
        output += '\n'
        output_comparison.write( output )

        # Add summary statistics from individual tools if available
        if tools___statistics:
            for stat_key in [ 'Coverage_Percent', 'Genes_Not_In_Orthogroups' ]:
                output = f"{stat_key} (from individual tool statistics)"
                for tool_name in tool_names:
                    if tool_name in tools___statistics and stat_key in tools___statistics[ tool_name ]:
                        output += '\t' + tools___statistics[ tool_name ][ stat_key ]
                    else:
                        output += '\t' + 'N/A'
                output += '\n'
                output_comparison.write( output )

    logger.info( f"Wrote method comparison to: {comparison_file}" )

    # ==========================================================================
    # Gene overlap between methods
    # ==========================================================================

    logger.info( "Calculating gene overlap between methods..." )

    overlap_file = output_directory / '2_ai-gene_overlap_between_methods.tsv'

    with open( overlap_file, 'w' ) as output_overlap:
        # Write header
        header = 'Comparison (pair of tools being compared)' + '\t'
        header += 'Tool_A_Total_Genes (genes assigned by tool A)' + '\t'
        header += 'Tool_B_Total_Genes (genes assigned by tool B)' + '\t'
        header += 'Shared_Genes (genes assigned by both tools)' + '\t'
        header += 'Only_In_Tool_A (genes only in tool A)' + '\t'
        header += 'Only_In_Tool_B (genes only in tool B)' + '\t'
        header += 'Jaccard_Index (shared divided by union of gene sets)' + '\n'
        output_overlap.write( header )

        # Pairwise comparisons
        for index_a in range( len( available_tools ) ):
            for index_b in range( index_a + 1, len( available_tools ) ):
                tool_a = available_tools[ index_a ]
                tool_b = available_tools[ index_b ]

                genes_a = tools___all_genes[ tool_a ]
                genes_b = tools___all_genes[ tool_b ]

                shared_genes = genes_a.intersection( genes_b )
                only_in_a = genes_a.difference( genes_b )
                only_in_b = genes_b.difference( genes_a )
                union_genes = genes_a.union( genes_b )

                jaccard_index = len( shared_genes ) / len( union_genes ) if len( union_genes ) > 0 else 0.0

                output = f"{tool_a}_vs_{tool_b}" + '\t'
                output += str( len( genes_a ) ) + '\t'
                output += str( len( genes_b ) ) + '\t'
                output += str( len( shared_genes ) ) + '\t'
                output += str( len( only_in_a ) ) + '\t'
                output += str( len( only_in_b ) ) + '\t'
                output += f"{jaccard_index:.4f}" + '\n'
                output_overlap.write( output )

                logger.info( f"  {tool_a} vs {tool_b}: {len( shared_genes )} shared, Jaccard={jaccard_index:.4f}" )

        # All-three overlap (if all three tools have data)
        if len( available_tools ) == 3:
            all_three_genes = tools___all_genes[ available_tools[ 0 ] ]
            for tool_name in available_tools[ 1: ]:
                all_three_genes = all_three_genes.intersection( tools___all_genes[ tool_name ] )

            any_tool_genes = set()
            for tool_name in available_tools:
                any_tool_genes.update( tools___all_genes[ tool_name ] )

            output = 'all_three_tools' + '\t'
            output += str( len( any_tool_genes ) ) + '\t'
            output += str( len( any_tool_genes ) ) + '\t'
            output += str( len( all_three_genes ) ) + '\t'
            output += 'N/A' + '\t'
            output += 'N/A' + '\t'
            output += f"{len( all_three_genes ) / len( any_tool_genes ):.4f}" if len( any_tool_genes ) > 0 else '0.0000'
            output += '\n'
            output_overlap.write( output )

            logger.info( f"  All three tools: {len( all_three_genes )} genes shared by all" )

    logger.info( f"Wrote gene overlap to: {overlap_file}" )

    # ==========================================================================
    # Orthogroup size distribution comparison
    # ==========================================================================

    logger.info( "Comparing orthogroup size distributions..." )

    size_comparison_file = output_directory / '2_ai-orthogroup_size_comparison.tsv'

    # Collect all possible sizes across all tools
    all_sizes = set()
    tools___size_counts = {}

    for tool_name in available_tools:
        sizes = [ len( genes ) for genes in tools___orthogroups[ tool_name ].values() ]
        size_counts = Counter( sizes )
        tools___size_counts[ tool_name ] = size_counts
        all_sizes.update( sizes )

    with open( size_comparison_file, 'w' ) as output_size_comparison:
        # Write header
        header = 'Orthogroup_Size (number of genes in orthogroup)'
        for tool_name in available_tools:
            header += '\t' + f"{tool_name}_Count (number of orthogroups with this size in {tool_name})"
        header += '\n'
        output_size_comparison.write( header )

        for size in sorted( all_sizes ):
            output = str( size )
            for tool_name in available_tools:
                count = tools___size_counts[ tool_name ].get( size, 0 )
                output += '\t' + str( count )
            output += '\n'
            output_size_comparison.write( output )

    logger.info( f"Wrote size comparison to: {size_comparison_file}" )

    # ==========================================================================
    # Completion
    # ==========================================================================

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "Script 002 completed successfully" )
    logger.info( "=" * 70 )
    logger.info( f"Tools compared: {', '.join( available_tools )}" )
    logger.info( f"Output directory: {output_directory}" )


if __name__ == '__main__':
    main()
