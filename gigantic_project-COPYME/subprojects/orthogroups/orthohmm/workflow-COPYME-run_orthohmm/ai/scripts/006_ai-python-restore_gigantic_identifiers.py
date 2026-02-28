#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 27 | Purpose: Restore full GIGANTIC identifiers in OrthoHMM output
# Human: Eric Edsinger

"""
006_ai-python-restore_gigantic_identifiers.py

Restores full GIGANTIC protein identifiers in OrthoHMM output files.
This enables downstream subprojects to work with standard GIGANTIC naming.
Also generates per-species orthogroup assignment files for QC and exploration.

Input:
    --header-mapping: Path to 2_ai-header_mapping.tsv from script 002
    --orthohmm-dir: Path to OrthoHMM output directory from script 003

Output:
    OUTPUT_pipeline/6-output/6_ai-orthogroups_gigantic_ids.txt
        Orthogroups with full GIGANTIC identifiers

    OUTPUT_pipeline/6-output/6_ai-gene_count_gigantic_ids.tsv
        Gene counts with full species phylonames

    OUTPUT_pipeline/6-output/orthogroup_fastas/
        FASTA files per orthogroup with restored headers

    OUTPUT_pipeline/6-output/6_ai-per_species/
        Per-species TSV files listing orthogroup assignment for each sequence.
        NOTE: These per-species files may be removed in future versions if not
        needed by downstream subprojects. They are included for QC and exploration.

Usage:
    python3 006_ai-python-restore_gigantic_identifiers.py \\
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

    logger = logging.getLogger( '006_restore_identifiers' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '6_ai-log-restore_gigantic_identifiers.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Restore full GIGANTIC identifiers in OrthoHMM output'
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
        default = 'OUTPUT_pipeline/6-output',
        help = 'Output directory (default: OUTPUT_pipeline/6-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    header_mapping_path = Path( arguments.header_mapping )
    orthohmm_directory = Path( arguments.orthohmm_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directories
    output_directory.mkdir( parents = True, exist_ok = True )
    fasta_output_directory = output_directory / 'orthogroup_fastas'
    fasta_output_directory.mkdir( parents = True, exist_ok = True )
    per_species_directory = output_directory / '6_ai-per_species'
    per_species_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 006: Restore GIGANTIC Identifiers" )
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
    # Short_ID (short header for OrthoHMM format Genus_species-N)	Original_Header (full GIGANTIC protein identifier)	Genus_Species (species name)	Original_Filename (source proteome file)
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

    # Track per-sequence orthogroup assignments for per-species files
    short_ids___orthogroup_ids = {}

    # Process orthogroups file
    # Input format: OG_ID: gene1 gene2 gene3 ...
    # Output format: OG_ID: original_header1 original_header2 ...

    orthogroups_output_path = output_directory / '6_ai-orthogroups_gigantic_ids.txt'
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

                # Restore original headers and track assignments
                restored_genes = []
                for gene in genes:
                    # Track orthogroup assignment for per-species files
                    short_ids___orthogroup_ids[ gene ] = orthogroup_id

                    if gene in short_ids___original_headers:
                        original_header = short_ids___original_headers[ gene ]
                        restored_genes.append( original_header )
                        total_genes_restored += 1
                    else:
                        # Keep original if no mapping found
                        restored_genes.append( gene )
                        missing_mappings.add( gene )

                # Write restored orthogroup
                output = orthogroup_id + ': ' + ' '.join( restored_genes ) + '\n'
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
    if gene_count_input.exists():
        logger.info( "Processing gene count file..." )

        gene_count_output = output_directory / '6_ai-gene_count_gigantic_ids.tsv'

        # The gene count file typically has species as columns
        # We'll just copy it since species names should already be in Genus_species format
        with open( gene_count_input, 'r' ) as input_gene_count:
            with open( gene_count_output, 'w' ) as output_gene_count:
                for line in input_gene_count:
                    output_gene_count.write( line )

        logger.info( f"Wrote gene counts to: {gene_count_output}" )
    else:
        logger.info( "No gene count file found (orthohmm_gene_count.txt)" )

    # Process orthogroup FASTA files if they exist
    orthogroup_fasta_directory = orthohmm_directory / 'orthohmm_orthogroups'
    if orthogroup_fasta_directory.exists() and orthogroup_fasta_directory.is_dir():
        logger.info( "Processing orthogroup FASTA files..." )

        fasta_files = list( orthogroup_fasta_directory.glob( '*.fa' ) )
        fasta_files.extend( list( orthogroup_fasta_directory.glob( '*.fasta' ) ) )
        fasta_files.extend( list( orthogroup_fasta_directory.glob( '*.aa' ) ) )

        logger.info( f"Found {len( fasta_files )} orthogroup FASTA files" )

        for fasta_file in fasta_files:
            output_fasta = fasta_output_directory / fasta_file.name

            with open( fasta_file, 'r' ) as input_fasta:
                with open( output_fasta, 'w' ) as output_fasta_file:

                    for line in input_fasta:
                        if line.startswith( '>' ):
                            short_id = line[ 1: ].strip()
                            # Remove any description after space
                            if ' ' in short_id:
                                short_id = short_id.split()[ 0 ]

                            if short_id in short_ids___original_headers:
                                original_header = short_ids___original_headers[ short_id ]
                                output = '>' + original_header + '\n'
                                output_fasta_file.write( output )
                            else:
                                output_fasta_file.write( line )
                        else:
                            output_fasta_file.write( line )

        logger.info( f"Wrote {len( fasta_files )} FASTA files to: {fasta_output_directory}" )
    else:
        logger.info( "No orthogroup FASTA directory found" )

    # =========================================================================
    # Generate per-species orthogroup assignment files
    # =========================================================================
    # NOTE: These per-species files may be removed in future versions if not
    # needed by downstream subprojects. Included for QC and exploration.

    logger.info( "Generating per-species orthogroup assignment files..." )

    # Group short IDs by species
    species___short_ids = defaultdict( list )
    for short_id in short_ids___original_headers:
        if '-' in short_id:
            species = short_id.rsplit( '-', 1 )[ 0 ]
            species___short_ids[ species ].append( short_id )

    per_species_file_count = 0
    for genus_species in sorted( species___short_ids.keys() ):
        short_ids = species___short_ids[ genus_species ]

        per_species_file = per_species_directory / f'6_ai-{genus_species}-orthogroups_per_sequence.tsv'

        with open( per_species_file, 'w' ) as output_per_species:
            # Write header
            header = 'Short_ID (short header used in OrthoHMM format Genus_species-N)' + '\t'
            header += 'Original_Header (full GIGANTIC protein identifier)' + '\t'
            header += 'Orthogroup_ID (orthogroup assignment or NONE if unassigned)' + '\n'
            output_per_species.write( header )

            # Write data rows for each sequence in this species
            for short_id in sorted( short_ids ):
                original_header = short_ids___original_headers[ short_id ]
                orthogroup_id = short_ids___orthogroup_ids.get( short_id, 'NONE' )

                output = short_id + '\t'
                output += original_header + '\t'
                output += orthogroup_id + '\n'
                output_per_species.write( output )

        per_species_file_count += 1

    logger.info( f"Wrote {per_species_file_count} per-species files to: {per_species_directory}" )

    # =========================================================================
    # Ensure all expected output files exist (for NextFlow output declarations)
    # =========================================================================

    gene_count_output_path = output_directory / '6_ai-gene_count_gigantic_ids.tsv'
    if not gene_count_output_path.exists():
        # Create empty gene count file with header only
        with open( gene_count_output_path, 'w' ) as output_gene_count:
            output_gene_count.write( '# No gene count data available from OrthoHMM\n' )
        logger.info( "NOTE: Created empty gene count file (OrthoHMM did not produce one)" )

    # Create summary of output files for output_to_input
    summary_file = output_directory / '6_ai-output_summary.txt'

    with open( summary_file, 'w' ) as output_summary:
        output_summary.write( "OrthoHMM Workflow Output Summary\n" )
        output_summary.write( "=" * 50 + "\n\n" )
        output_summary.write( f"Orthogroups file: {orthogroups_output_path}\n" )
        output_summary.write( f"Orthogroup count: {orthogroup_count}\n" )
        output_summary.write( f"Total genes: {total_genes_restored}\n" )

        if ( output_directory / '6_ai-gene_count_gigantic_ids.tsv' ).exists():
            output_summary.write( f"Gene count file: {output_directory / '6_ai-gene_count_gigantic_ids.tsv'}\n" )

        if fasta_output_directory.exists():
            output_summary.write( f"FASTA directory: {fasta_output_directory}\n" )

        output_summary.write( f"Per-species files: {per_species_directory}\n" )
        output_summary.write( f"Per-species file count: {per_species_file_count}\n" )

    logger.info( f"Wrote output summary to: {summary_file}" )
    logger.info( "Script 006 completed successfully" )


if __name__ == '__main__':
    main()
