#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Restore full GIGANTIC identifiers in orthogroup output
# Human: Eric Edsinger

"""
004_ai-python-restore_gigantic_identifiers.py

Restores full GIGANTIC protein identifiers in orthogroup output files,
replacing short IDs (Genus_species-N) with original GIGANTIC headers.
Produces standardized output format used by scripts 005 and 006.

Input:
    --header-mapping: Path to 2_ai-header_mapping.tsv from script 002
    --orthohmm-dir: Path to OrthoHMM output directory from script 003

Output:
    OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv
        Orthogroups with full GIGANTIC identifiers

    OUTPUT_pipeline/4-output/4_ai-gene_count_gigantic_ids.tsv
        Gene counts with full species phylonames

Usage:
    python3 004_ai-python-restore_gigantic_identifiers.py \\
        --header-mapping OUTPUT_pipeline/2-output/2_ai-header_mapping.tsv \\
        --orthohmm-dir OUTPUT_pipeline/3-output
"""

import argparse
import logging
import sys
from collections import defaultdict
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
        description = 'Restore full GIGANTIC identifiers in orthogroup output'
    )

    parser.add_argument(
        '--header-mapping',
        type = str,
        required = True,
        help = 'Path to 2_ai-header_mapping.tsv from script 002'
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
    header_mapping_path = Path( arguments.header_mapping )
    orthohmm_directory = Path( arguments.orthohmm_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directories
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 004: Restore GIGANTIC Identifiers" )
    logger.info( "=" * 70 )

    # Validate inputs
    if not header_mapping_path.exists():
        logger.error( f"CRITICAL ERROR: Header mapping not found: {header_mapping_path}" )
        sys.exit( 1 )

    orthogroups_path = orthohmm_directory / 'orthohmm_orthogroups.txt'
    if not orthogroups_path.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found: {orthogroups_path}" )
        sys.exit( 1 )

    # Load header mapping
    # Short_ID (short header format Genus_species-N)	Original_Header (full GIGANTIC protein identifier)	Genus_Species (species name)	Original_Filename (source proteome file)
    # Homo_sapiens-1	NP_000001.1 protein description	Homo_sapiens	filename.aa

    short_ids___original_headers = {}
    short_ids___filenames = {}

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
            original_filename = parts[ 3 ]

            short_ids___original_headers[ short_id ] = original_header
            short_ids___filenames[ short_id ] = original_filename

    logger.info( f"Loaded {len( short_ids___original_headers )} header mappings" )

    # Process orthogroups file
    # Input format: OG_ID: gene1 gene2 gene3 ...
    # Output format: OG_ID\toriginal_header1\toriginal_header2 ...

    orthogroups_output_path = output_directory / '4_ai-orthogroups_gigantic_ids.tsv'
    orthogroup_count = 0
    total_genes_restored = 0
    missing_mappings = set()

    logger.info( "Processing orthogroups file..." )

    with open( orthogroups_path, 'r' ) as input_orthogroups:
        with open( orthogroups_output_path, 'w' ) as output_orthogroups:

            for line in input_orthogroups:
                line = line.strip()
                if not line:
                    continue

                if ':' in line:
                    parts = line.split( ':', 1 )
                    orthogroup_id = parts[ 0 ].strip()
                    genes_string = parts[ 1 ].strip()
                    genes = genes_string.split()
                else:
                    parts = line.split( '\t' )
                    orthogroup_id = parts[ 0 ]
                    genes = parts[ 1: ]

                # Restore original headers
                restored_genes = []
                for gene in genes:
                    if gene in short_ids___original_headers:
                        original_header = short_ids___original_headers[ gene ]
                        restored_genes.append( original_header )
                        total_genes_restored += 1
                    else:
                        # Keep original if no mapping found
                        restored_genes.append( gene )
                        missing_mappings.add( gene )

                # Write restored orthogroup (tab-separated for standardized format)
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
    gene_count_input = orthohmm_directory / 'orthohmm_gene_count.txt'
    gene_count_output_path = output_directory / '4_ai-gene_count_gigantic_ids.tsv'

    if gene_count_input.exists():
        logger.info( "Processing gene count file..." )

        with open( gene_count_input, 'r' ) as input_gene_count:
            with open( gene_count_output_path, 'w' ) as output_gene_count:
                for line in input_gene_count:
                    output_gene_count.write( line )

        logger.info( f"Wrote gene counts to: {gene_count_output_path}" )
    else:
        logger.info( "No gene count file found (orthohmm_gene_count.txt)" )
        # Create empty gene count file with header only
        with open( gene_count_output_path, 'w' ) as output_gene_count:
            output_gene_count.write( '# No gene count data available from OrthoHMM\n' )
        logger.info( "Created placeholder gene count file" )

    logger.info( "Script 004 completed successfully" )


if __name__ == '__main__':
    main()
