#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Standardize OrthoFinder output to GIGANTIC format
# Human: Eric Edsinger

"""
004_ai-python-standardize_output.py

Standardizes OrthoFinder output into the GIGANTIC orthogroup format.
OrthoFinder with the -X flag preserves original sequence identifiers,
so no header restoration is needed. This script converts OrthoFinder's
species-column matrix format into the standardized tab-separated format
used by scripts 005 and 006.

OrthoFinder Orthogroups.tsv format:
    Orthogroup<TAB>Species1_filename<TAB>Species2_filename<TAB>...
    OG0000000<TAB>gene1, gene2<TAB>gene3<TAB>...

GIGANTIC standardized format:
    OG_ID<TAB>gene1<TAB>gene2<TAB>gene3<TAB>...

Input:
    --orthofinder-dir: Path to OrthoFinder output directory from script 003
    --proteome-list: Path to 1_ai-proteome_list.tsv from script 001

Output:
    OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv
        Orthogroups with full GIGANTIC identifiers (standardized format)

    OUTPUT_pipeline/4-output/4_ai-gene_count_gigantic_ids.tsv
        Gene counts per orthogroup per species

Usage:
    python3 004_ai-python-standardize_output.py \\
        --orthofinder-dir OUTPUT_pipeline/3-output \\
        --proteome-list OUTPUT_pipeline/1-output/1_ai-proteome_list.tsv
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '004_standardize_output' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '4_ai-log-standardize_output.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Standardize OrthoFinder output to GIGANTIC format'
    )

    parser.add_argument(
        '--orthofinder-dir',
        type = str,
        required = True,
        help = 'Path to OrthoFinder output directory from script 003'
    )

    parser.add_argument(
        '--proteome-list',
        type = str,
        required = True,
        help = 'Path to 1_ai-proteome_list.tsv from script 001'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/4-output',
        help = 'Output directory (default: OUTPUT_pipeline/4-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    orthofinder_directory = Path( arguments.orthofinder_dir )
    proteome_list_path = Path( arguments.proteome_list )
    output_directory = Path( arguments.output_dir )

    # Create output directories
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 004: Standardize OrthoFinder Output" )
    logger.info( "=" * 70 )

    # Validate inputs
    if not proteome_list_path.exists():
        logger.error( f"CRITICAL ERROR: Proteome list not found: {proteome_list_path}" )
        sys.exit( 1 )

    # OrthoFinder produces Orthogroups.tsv
    orthogroups_path = orthofinder_directory / 'Orthogroups.tsv'
    if not orthogroups_path.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups.tsv not found: {orthogroups_path}" )
        sys.exit( 1 )

    # ==========================================================================
    # Parse OrthoFinder Orthogroups.tsv
    # ==========================================================================
    #
    # OrthoFinder format: species-column matrix
    # Header: Orthogroup\tSpecies1_filename\tSpecies2_filename\t...
    # Data: OG0000000\tgene1, gene2\tgene3\t...
    #
    # Genes within a cell are comma-separated
    # Empty cells mean no genes from that species in that orthogroup

    orthogroups_output_path = output_directory / '4_ai-orthogroups_gigantic_ids.tsv'
    orthogroup_count = 0
    total_genes = 0

    logger.info( f"Processing OrthoFinder Orthogroups.tsv..." )

    with open( orthogroups_path, 'r' ) as input_orthogroups:
        with open( orthogroups_output_path, 'w' ) as output_orthogroups:

            # Read header line to get species column names
            # Orthogroup	species1_filename.aa	species2_filename.aa	...
            header_line = input_orthogroups.readline().strip()
            parts_header = header_line.split( '\t' )
            species_columns = parts_header[ 1: ]

            logger.info( f"Species columns in OrthoFinder output: {len( species_columns )}" )

            for line in input_orthogroups:
                line = line.strip()
                if not line:
                    continue

                parts = line.split( '\t' )
                orthogroup_id = parts[ 0 ]

                # Collect all genes from all species columns
                all_genes = []
                for column_index in range( 1, len( parts ) ):
                    cell_value = parts[ column_index ].strip()
                    if not cell_value:
                        continue

                    # OrthoFinder uses comma+space to separate genes within a cell
                    genes_in_cell = cell_value.split( ', ' )
                    for gene in genes_in_cell:
                        gene = gene.strip()
                        if gene:
                            all_genes.append( gene )

                if not all_genes:
                    continue

                # Write standardized format: OG_ID\tgene1\tgene2\tgene3...
                output = orthogroup_id + '\t' + '\t'.join( all_genes ) + '\n'
                output_orthogroups.write( output )

                orthogroup_count += 1
                total_genes += len( all_genes )

    logger.info( f"Processed {orthogroup_count} orthogroups" )
    logger.info( f"Total genes in orthogroups: {total_genes}" )
    logger.info( f"Wrote orthogroups to: {orthogroups_output_path}" )

    # ==========================================================================
    # Process gene count file
    # ==========================================================================

    gene_count_input = orthofinder_directory / 'Orthogroups.GeneCount.tsv'
    gene_count_output_path = output_directory / '4_ai-gene_count_gigantic_ids.tsv'

    if gene_count_input.exists():
        logger.info( "Processing gene count file..." )

        with open( gene_count_input, 'r' ) as input_gene_count:
            with open( gene_count_output_path, 'w' ) as output_gene_count:
                for line in input_gene_count:
                    output_gene_count.write( line )

        logger.info( f"Wrote gene counts to: {gene_count_output_path}" )
    else:
        logger.info( "No gene count file found (Orthogroups.GeneCount.tsv)" )
        with open( gene_count_output_path, 'w' ) as output_gene_count:
            output_gene_count.write( '# No gene count data available from OrthoFinder\n' )
        logger.info( "Created placeholder gene count file" )

    # ==========================================================================
    # Validation
    # ==========================================================================

    if orthogroup_count == 0:
        logger.error( "CRITICAL ERROR: No orthogroups were parsed!" )
        logger.error( "Check Orthogroups.tsv format." )
        sys.exit( 1 )

    logger.info( "" )
    logger.info( "Script 004 completed successfully" )
    logger.info( f"  Orthogroups standardized: {orthogroup_count}" )
    logger.info( f"  Total genes: {total_genes}" )
    logger.info( f"  Output: {orthogroups_output_path}" )


if __name__ == '__main__':
    main()
