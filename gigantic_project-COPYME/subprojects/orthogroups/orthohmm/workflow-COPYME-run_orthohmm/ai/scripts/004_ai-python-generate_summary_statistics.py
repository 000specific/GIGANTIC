#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 27 | Purpose: Generate summary statistics from OrthoHMM results
# Human: Eric Edsinger

"""
004_ai-python-generate_summary_statistics.py

Generates comprehensive summary statistics from OrthoHMM clustering results.

Input:
    --proteome-list: Path to 1_ai-proteome_list.txt from script 001
    --orthohmm-dir: Path to OrthoHMM output directory from script 003

Output:
    OUTPUT_pipeline/4-output/4_ai-orthohmm_summary_statistics.tsv
        Overall clustering statistics

    OUTPUT_pipeline/4-output/4_ai-orthogroup_size_distribution.tsv
        Distribution of orthogroup sizes

Usage:
    python3 004_ai-python-generate_summary_statistics.py \\
        --proteome-list OUTPUT_pipeline/1-output/1_ai-proteome_list.txt \\
        --orthohmm-dir OUTPUT_pipeline/3-output
"""

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '004_summary_statistics' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '4_ai-log-generate_summary_statistics.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def parse_orthogroups_file( orthogroups_path: Path, logger: logging.Logger ) -> dict:
    """
    Parse OrthoHMM orthogroups file.

    Expected format (tab-separated):
    OG_ID: gene1 gene2 gene3 ...

    Returns dictionary mapping orthogroup ID to list of genes.
    """

    orthogroups___genes = {}

    with open( orthogroups_path, 'r' ) as input_orthogroups:
        for line in input_orthogroups:
            line = line.strip()
            if not line:
                continue

            # Split on colon to get OG ID and genes
            if ':' in line:
                parts = line.split( ':', 1 )
                orthogroup_id = parts[ 0 ].strip()
                genes_string = parts[ 1 ].strip()
                genes = genes_string.split()
            else:
                # Alternative format: tab-separated
                parts = line.split( '\t' )
                orthogroup_id = parts[ 0 ]
                genes = parts[ 1: ]

            orthogroups___genes[ orthogroup_id ] = genes

    logger.info( f"Parsed {len( orthogroups___genes )} orthogroups" )

    return orthogroups___genes


def calculate_statistics(
    orthogroups___genes: dict,
    species_count: int,
    total_sequences: int,
    logger: logging.Logger
) -> dict:
    """
    Calculate summary statistics from orthogroup data.
    """

    statistics = {}

    # Basic counts
    statistics[ 'total_orthogroups' ] = len( orthogroups___genes )

    # Genes in orthogroups
    genes_in_orthogroups = set()
    for orthogroup_id in orthogroups___genes:
        genes = orthogroups___genes[ orthogroup_id ]
        for gene in genes:
            genes_in_orthogroups.add( gene )

    statistics[ 'genes_in_orthogroups' ] = len( genes_in_orthogroups )
    statistics[ 'genes_not_in_orthogroups' ] = total_sequences - len( genes_in_orthogroups )

    # Coverage percentage
    if total_sequences > 0:
        statistics[ 'coverage_percent' ] = ( len( genes_in_orthogroups ) / total_sequences ) * 100
    else:
        statistics[ 'coverage_percent' ] = 0.0

    # Orthogroup size statistics
    orthogroup_sizes = [ len( genes ) for genes in orthogroups___genes.values() ]

    if orthogroup_sizes:
        statistics[ 'min_orthogroup_size' ] = min( orthogroup_sizes )
        statistics[ 'max_orthogroup_size' ] = max( orthogroup_sizes )
        statistics[ 'mean_orthogroup_size' ] = sum( orthogroup_sizes ) / len( orthogroup_sizes )
        statistics[ 'median_orthogroup_size' ] = sorted( orthogroup_sizes )[ len( orthogroup_sizes ) // 2 ]
    else:
        statistics[ 'min_orthogroup_size' ] = 0
        statistics[ 'max_orthogroup_size' ] = 0
        statistics[ 'mean_orthogroup_size' ] = 0.0
        statistics[ 'median_orthogroup_size' ] = 0

    # Single-copy orthogroups (exactly one gene per species present)
    single_copy_count = 0
    for orthogroup_id in orthogroups___genes:
        genes = orthogroups___genes[ orthogroup_id ]

        # Extract species from gene IDs (format: Genus_species-N)
        species_in_orthogroup = set()
        for gene in genes:
            if '-' in gene:
                species = gene.rsplit( '-', 1 )[ 0 ]
                species_in_orthogroup.add( species )

        # Count genes per species
        species_gene_counts = Counter()
        for gene in genes:
            if '-' in gene:
                species = gene.rsplit( '-', 1 )[ 0 ]
                species_gene_counts[ species ] += 1

        # Check if single-copy (each species has exactly 1 gene)
        is_single_copy = all( count == 1 for count in species_gene_counts.values() )
        if is_single_copy and len( species_in_orthogroup ) > 1:
            single_copy_count += 1

    statistics[ 'single_copy_orthogroups' ] = single_copy_count

    # Universal orthogroups (present in all species)
    universal_count = 0
    for orthogroup_id in orthogroups___genes:
        genes = orthogroups___genes[ orthogroup_id ]

        species_in_orthogroup = set()
        for gene in genes:
            if '-' in gene:
                species = gene.rsplit( '-', 1 )[ 0 ]
                species_in_orthogroup.add( species )

        if len( species_in_orthogroup ) == species_count:
            universal_count += 1

    statistics[ 'universal_orthogroups' ] = universal_count

    return statistics


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Generate summary statistics from OrthoHMM results'
    )

    parser.add_argument(
        '--proteome-list',
        type = str,
        required = True,
        help = 'Path to 1_ai-proteome_list.txt from script 001'
    )

    parser.add_argument(
        '--orthohmm-dir',
        type = str,
        required = True,
        help = 'Path to OrthoHMM output directory from script 003'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/4-output',
        help = 'Output directory (default: OUTPUT_pipeline/4-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    proteome_list_path = Path( arguments.proteome_list )
    orthohmm_directory = Path( arguments.orthohmm_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 004: Generate Summary Statistics" )
    logger.info( "=" * 70 )

    # Validate inputs
    if not proteome_list_path.exists():
        logger.error( f"CRITICAL ERROR: Proteome list not found: {proteome_list_path}" )
        sys.exit( 1 )

    orthogroups_path = orthohmm_directory / 'orthohmm_orthogroups.txt'
    if not orthogroups_path.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found: {orthogroups_path}" )
        logger.error( "Ensure script 003 (OrthoHMM) completed successfully." )
        sys.exit( 1 )

    # Read proteome list to get species count and total sequences
    # Proteome_Filename (proteome file name)	Full_Path (absolute path to proteome file)	Genus_Species (extracted from phyloname)	Sequence_Count (number of protein sequences in file)
    # filename.aa	/path/to/file.aa	Homo_sapiens	20000

    species_count = 0
    total_sequences = 0

    with open( proteome_list_path, 'r' ) as input_proteome_list:
        header_line = input_proteome_list.readline()  # Skip header

        for line in input_proteome_list:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            sequence_count = int( parts[ 3 ] )

            species_count += 1
            total_sequences += sequence_count

    logger.info( f"Species count: {species_count}" )
    logger.info( f"Total sequences: {total_sequences}" )

    # Parse orthogroups
    orthogroups___genes = parse_orthogroups_file( orthogroups_path, logger )

    # Calculate statistics
    statistics = calculate_statistics(
        orthogroups___genes = orthogroups___genes,
        species_count = species_count,
        total_sequences = total_sequences,
        logger = logger
    )

    # Write summary statistics
    summary_file = output_directory / '4_ai-orthohmm_summary_statistics.tsv'

    with open( summary_file, 'w' ) as output_summary:
        # Write header
        header = 'Statistic (description of metric)' + '\t'
        header += 'Value (calculated value)' + '\n'
        output_summary.write( header )

        # Write statistics
        output = 'Species_Count (number of species in analysis)' + '\t' + str( species_count ) + '\n'
        output_summary.write( output )

        output = 'Total_Sequences (total protein sequences across all species)' + '\t' + str( total_sequences ) + '\n'
        output_summary.write( output )

        output = 'Total_Orthogroups (number of orthogroups identified)' + '\t' + str( statistics[ 'total_orthogroups' ] ) + '\n'
        output_summary.write( output )

        output = 'Genes_In_Orthogroups (sequences assigned to orthogroups)' + '\t' + str( statistics[ 'genes_in_orthogroups' ] ) + '\n'
        output_summary.write( output )

        output = 'Genes_Not_In_Orthogroups (sequences without orthogroup assignment)' + '\t' + str( statistics[ 'genes_not_in_orthogroups' ] ) + '\n'
        output_summary.write( output )

        output = 'Coverage_Percent (percent of sequences in orthogroups)' + '\t' + f"{statistics[ 'coverage_percent' ]:.2f}" + '\n'
        output_summary.write( output )

        output = 'Single_Copy_Orthogroups (orthogroups with exactly one gene per species)' + '\t' + str( statistics[ 'single_copy_orthogroups' ] ) + '\n'
        output_summary.write( output )

        output = 'Universal_Orthogroups (orthogroups present in all species)' + '\t' + str( statistics[ 'universal_orthogroups' ] ) + '\n'
        output_summary.write( output )

        output = 'Min_Orthogroup_Size (smallest orthogroup gene count)' + '\t' + str( statistics[ 'min_orthogroup_size' ] ) + '\n'
        output_summary.write( output )

        output = 'Max_Orthogroup_Size (largest orthogroup gene count)' + '\t' + str( statistics[ 'max_orthogroup_size' ] ) + '\n'
        output_summary.write( output )

        output = 'Mean_Orthogroup_Size (average genes per orthogroup)' + '\t' + f"{statistics[ 'mean_orthogroup_size' ]:.2f}" + '\n'
        output_summary.write( output )

        output = 'Median_Orthogroup_Size (median genes per orthogroup)' + '\t' + str( statistics[ 'median_orthogroup_size' ] ) + '\n'
        output_summary.write( output )

    logger.info( f"Wrote summary statistics to: {summary_file}" )

    # Write size distribution
    size_distribution_file = output_directory / '4_ai-orthogroup_size_distribution.tsv'

    orthogroup_sizes = [ len( genes ) for genes in orthogroups___genes.values() ]
    size_counts = Counter( orthogroup_sizes )

    with open( size_distribution_file, 'w' ) as output_distribution:
        header = 'Orthogroup_Size (number of genes in orthogroup)' + '\t'
        header += 'Count (number of orthogroups with this size)' + '\n'
        output_distribution.write( header )

        for size in sorted( size_counts.keys() ):
            output = str( size ) + '\t' + str( size_counts[ size ] ) + '\n'
            output_distribution.write( output )

    logger.info( f"Wrote size distribution to: {size_distribution_file}" )
    logger.info( "Script 004 completed successfully" )


if __name__ == '__main__':
    main()
