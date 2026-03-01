#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Restore full GIGANTIC identifiers in Broccoli output
# Human: Eric Edsinger

"""
004_ai-python-restore_gigantic_identifiers.py

Restores full GIGANTIC protein identifiers in Broccoli output files,
replacing short IDs (Genus_species-N) with original GIGANTIC headers.
Produces standardized output format used by scripts 005 and 006.

Input:
    --header-mapping: Path to 2_ai-header_mapping.tsv from script 002
    --broccoli-dir: Path to Broccoli output directory from script 003

Output:
    OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv
        Orthogroups with full GIGANTIC identifiers

    OUTPUT_pipeline/4-output/4_ai-gene_count_gigantic_ids.tsv
        Gene counts with full species phylonames

Usage:
    python3 004_ai-python-restore_gigantic_identifiers.py \\
        --header-mapping OUTPUT_pipeline/2-output/2_ai-header_mapping.tsv \\
        --broccoli-dir OUTPUT_pipeline/3-output
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '004_restore_identifiers' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '4_ai-log-restore_gigantic_identifiers.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Restore full GIGANTIC identifiers in Broccoli output'
    )

    parser.add_argument(
        '--header-mapping',
        type = str,
        required = True,
        help = 'Path to 2_ai-header_mapping.tsv from script 002'
    )

    parser.add_argument(
        '--broccoli-dir',
        type = str,
        required = True,
        help = 'Path to Broccoli output directory from script 003'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/4-output',
        help = 'Output directory (default: OUTPUT_pipeline/4-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    header_mapping_path = Path( arguments.header_mapping )
    broccoli_directory = Path( arguments.broccoli_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directories
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 004: Restore GIGANTIC Identifiers (Broccoli)" )
    logger.info( "=" * 70 )

    # Validate inputs
    if not header_mapping_path.exists():
        logger.error( f"CRITICAL ERROR: Header mapping not found: {header_mapping_path}" )
        sys.exit( 1 )

    # Broccoli produces orthologous_groups.txt
    orthogroups_path = broccoli_directory / 'orthologous_groups.txt'
    if not orthogroups_path.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found: {orthogroups_path}" )
        sys.exit( 1 )

    # Load header mapping
    # Short_ID (short header format Genus_species-N)	Original_Header (full GIGANTIC protein identifier)	Genus_Species (species name)	Original_Filename (source proteome file)
    # Homo_sapiens-1	NP_000001.1 protein description	Homo_sapiens	filename.aa

    short_ids___original_headers = {}

    logger.info( f"Loading header mapping from: {header_mapping_path}" )

    with open( header_mapping_path, 'r' ) as input_mapping:
        header_line = input_mapping.readline()

        for line in input_mapping:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            short_id = parts[ 0 ]
            original_header = parts[ 1 ]

            short_ids___original_headers[ short_id ] = original_header

    logger.info( f"Loaded {len( short_ids___original_headers )} header mappings" )

    # Process Broccoli orthogroups file
    # Broccoli format: OG_id\tgene1\tgene2\tgene3...
    # or: OG_id gene1 gene2 gene3... (space-separated within line)

    orthogroups_output_path = output_directory / '4_ai-orthogroups_gigantic_ids.tsv'
    orthogroup_count = 0
    total_genes_restored = 0
    missing_mappings = set()

    logger.info( "Processing Broccoli orthogroups file..." )

    with open( orthogroups_path, 'r' ) as input_orthogroups:
        with open( orthogroups_output_path, 'w' ) as output_orthogroups:

            for line in input_orthogroups:
                line = line.strip()
                if not line or line.startswith( '#' ):
                    continue

                # Parse Broccoli format (tab-separated)
                parts = line.split( '\t' )

                if len( parts ) < 2:
                    # Try space-separated
                    parts = line.split()

                orthogroup_id = parts[ 0 ]
                genes = parts[ 1: ]

                # Restore original headers
                restored_genes = []
                for gene in genes:
                    gene = gene.strip()
                    if not gene:
                        continue

                    if gene in short_ids___original_headers:
                        original_header = short_ids___original_headers[ gene ]
                        restored_genes.append( original_header )
                        total_genes_restored += 1
                    else:
                        restored_genes.append( gene )
                        missing_mappings.add( gene )

                # Write restored orthogroup (standardized tab-separated format)
                output = orthogroup_id + '\t' + '\t'.join( restored_genes ) + '\n'
                output_orthogroups.write( output )

                orthogroup_count += 1

    logger.info( f"Processed {orthogroup_count} orthogroups" )
    logger.info( f"Restored {total_genes_restored} gene identifiers" )

    if missing_mappings:
        logger.warning( f"Could not find mapping for {len( missing_mappings )} genes" )
        for gene in list( missing_mappings )[ :5 ]:
            logger.warning( f"  Missing: {gene}" )

    logger.info( f"Wrote orthogroups to: {orthogroups_output_path}" )

    # Process gene count file if it exists
    gene_count_input = broccoli_directory / 'table_OGs_protein_counts.txt'
    gene_count_output_path = output_directory / '4_ai-gene_count_gigantic_ids.tsv'

    if gene_count_input.exists():
        logger.info( "Processing gene count file..." )

        with open( gene_count_input, 'r' ) as input_gene_count:
            with open( gene_count_output_path, 'w' ) as output_gene_count:
                for line in input_gene_count:
                    output_gene_count.write( line )

        logger.info( f"Wrote gene counts to: {gene_count_output_path}" )
    else:
        logger.info( "No gene count file found (table_OGs_protein_counts.txt)" )
        with open( gene_count_output_path, 'w' ) as output_gene_count:
            output_gene_count.write( '# No gene count data available from Broccoli\n' )
        logger.info( "Created placeholder gene count file" )

    logger.info( "Script 004 completed successfully" )


if __name__ == '__main__':
    main()
