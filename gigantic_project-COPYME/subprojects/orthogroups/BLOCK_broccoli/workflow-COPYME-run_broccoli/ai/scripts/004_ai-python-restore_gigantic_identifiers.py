#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 29 | Purpose: Restore full GIGANTIC identifiers in Broccoli orthologous_groups output
# Human: Eric Edsinger

"""
004_ai-python-restore_gigantic_identifiers.py

Restores full GIGANTIC protein identifiers in Broccoli's orthologous_groups
file by replacing short IDs (Genus_species-N) with the original headers
recorded by script 002.

Fail-fast: every short_id appearing in broccoli's output MUST be in the
mapping by construction (script 002 wrote one mapping entry per protein in
the input proteomes; broccoli only sees those short_ids). Any mismatch is
a real bug, not a recoverable condition.

Note on broccoli's other step 3 outputs (table_OGs_protein_counts.txt,
table_OGs_protein_names.txt, statistics_*, chimeric_proteins.txt, etc.):
those have already been copied to OUTPUT_pipeline/3-output/ by script 003
with `3_ai-` prefix. The count and name matrices reference species names
(not protein IDs), so no translation is needed. Only the orthogroups file
contains short_ids that need restoration.

Input:
    --header-mapping:   Path to 2_ai-header_mapping.tsv from script 002
    --orthogroups-file: Path to 3_ai-orthologous_groups.txt from script 003

Output:
    OUTPUT_pipeline/4-output/4_ai-orthologous_groups-gigantic_ids.tsv
        Tab-separated: OG_id, gene1, gene2, ... with full GIGANTIC headers

Usage:
    python3 004_ai-python-restore_gigantic_identifiers.py \\
        --header-mapping   OUTPUT_pipeline/2-output/2_ai-header_mapping.tsv \\
        --orthogroups-file OUTPUT_pipeline/3-output/3_ai-orthologous_groups.txt
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '004_restore_identifiers' )
    logger.setLevel( logging.DEBUG )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

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
        description = 'Restore full GIGANTIC identifiers in Broccoli orthologous_groups output'
    )

    parser.add_argument(
        '--header-mapping',
        type = str,
        required = True,
        help = 'Path to 2_ai-header_mapping.tsv from script 002'
    )

    parser.add_argument(
        '--orthogroups-file',
        type = str,
        required = True,
        help = 'Path to 3_ai-orthologous_groups.txt from script 003'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/4-output',
        help = 'Output directory (default: OUTPUT_pipeline/4-output)'
    )

    arguments = parser.parse_args()

    header_mapping_path = Path( arguments.header_mapping )
    orthogroups_path = Path( arguments.orthogroups_file )
    output_directory = Path( arguments.output_dir )

    output_directory.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 004: Restore GIGANTIC Identifiers (Broccoli orthologous_groups)" )
    logger.info( "=" * 70 )

    # Validate inputs (fail-fast)
    if not header_mapping_path.exists():
        logger.error( f"CRITICAL ERROR: Header mapping not found: {header_mapping_path}" )
        logger.error( "Script 002 must complete before script 004." )
        sys.exit( 1 )

    if not orthogroups_path.exists():
        logger.error( f"CRITICAL ERROR: Broccoli orthologous_groups file not found: {orthogroups_path}" )
        logger.error( "Script 003 (run_broccoli) must complete before script 004." )
        sys.exit( 1 )

    # Load header mapping
    # Short_ID (short header format Genus_species-N)	Original_Header (full GIGANTIC protein identifier)	Genus_Species (species name)	Original_Filename (source proteome file)
    # Homo_sapiens-1	NP_000001.1 protein description	Homo_sapiens	filename.aa

    short_ids___original_headers = {}

    logger.info( f"Loading header mapping from: {header_mapping_path}" )

    with open( header_mapping_path, 'r' ) as input_mapping:
        header_line = input_mapping.readline()  # skip self-documenting header

        for line in input_mapping:
            line = line.rstrip( '\r\n' )
            if not line:
                continue

            parts = line.split( '\t' )
            short_id = parts[ 0 ]
            original_header = parts[ 1 ]

            short_ids___original_headers[ short_id ] = original_header

    logger.info( f"Loaded {len( short_ids___original_headers )} header mappings" )

    # Translate broccoli's orthologous_groups file
    # Broccoli format (per broccoli_step3.py source):
    #   OG_NNNNNNN<TAB>gene1<TAB>gene2<TAB>...
    # First column is the OG identifier (assigned by broccoli, NOT a short_id);
    # remaining columns are short_ids that we restore to full GIGANTIC headers.

    orthogroups_output_path = output_directory / '4_ai-orthologous_groups-gigantic_ids.tsv'
    orthogroup_count = 0
    total_genes_restored = 0
    unmapped_genes = []

    logger.info( "Translating broccoli orthologous_groups to GIGANTIC identifiers..." )

    with open( orthogroups_path, 'r' ) as input_orthogroups:
        with open( orthogroups_output_path, 'w' ) as output_orthogroups:

            for line in input_orthogroups:
                line = line.rstrip( '\r\n' )
                if not line or line.startswith( '#' ):
                    continue

                parts = line.split( '\t' )

                if len( parts ) < 2:
                    logger.error( f"CRITICAL ERROR: malformed broccoli line (need OG_id + ≥1 gene, got {len( parts )} fields)" )
                    logger.error( f"Line: {line!r}" )
                    sys.exit( 1 )

                orthogroup_id = parts[ 0 ]
                genes = parts[ 1: ]

                restored_genes = []
                for gene in genes:
                    gene = gene.strip()
                    if not gene:
                        continue

                    if gene not in short_ids___original_headers:
                        unmapped_genes.append( ( orthogroup_id, gene ) )
                        continue

                    original_header = short_ids___original_headers[ gene ]
                    restored_genes.append( original_header )
                    total_genes_restored += 1

                output = orthogroup_id + '\t' + '\t'.join( restored_genes ) + '\n'
                output_orthogroups.write( output )

                orthogroup_count += 1

    # Fail-fast on any unmapped gene. By construction (script 002 wrote
    # every protein's short_id to the mapping), this should be impossible.
    # If it happens, there is a real bug in script 002, script 003, or
    # broccoli's output handling — NOT a recoverable condition.
    if unmapped_genes:
        logger.error( "CRITICAL ERROR: short_ids in broccoli output not found in header mapping." )
        logger.error( f"Total unmapped: {len( unmapped_genes )}" )
        logger.error( "First 10 examples (orthogroup_id, short_id):" )
        for og_id, gene in unmapped_genes[ :10 ]:
            logger.error( f"  {og_id}\t{gene}" )
        logger.error( "By construction, every short_id in broccoli's output must be in the script-002 mapping." )
        logger.error( "An unmapped short_id means: (a) script 002 missed proteins, (b) script 003 introduced extraneous IDs, or (c) the FASTAs broccoli read differ from the FASTAs script 002 wrote." )
        sys.exit( 1 )

    logger.info( f"Translated {orthogroup_count} orthogroups; restored {total_genes_restored} gene identifiers" )
    logger.info( f"Wrote: {orthogroups_output_path}" )
    logger.info( "Script 004 completed successfully" )


if __name__ == '__main__':
    main()
