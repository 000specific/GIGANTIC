#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Prepare proteomes for OrthoFinder input
# Human: Eric Edsinger

"""
002_ai-python-prepare_proteomes.py

Prepares proteome files for OrthoFinder input. OrthoFinder supports the -X flag
which preserves original sequence identifiers, so no header conversion is needed.
This script copies validated proteomes to a clean input directory and verifies
they are in the correct format for OrthoFinder.

Input:
    --proteome-list: Path to 1_ai-proteome_list.tsv from script 001

Output:
    OUTPUT_pipeline/2-output/orthofinder_input_proteomes/
        Copies of proteome files ready for OrthoFinder

    OUTPUT_pipeline/2-output/2_ai-prepared_proteomes_summary.tsv
        Summary of prepared proteomes

Usage:
    python3 002_ai-python-prepare_proteomes.py \\
        --proteome-list OUTPUT_pipeline/1-output/1_ai-proteome_list.tsv
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '002_prepare_proteomes' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '2_ai-log-prepare_proteomes.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Prepare proteomes for OrthoFinder input'
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
        default = 'OUTPUT_pipeline/2-output',
        help = 'Output directory (default: OUTPUT_pipeline/2-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    proteome_list_path = Path( arguments.proteome_list )
    output_directory = Path( arguments.output_dir )

    # Create output directories
    output_directory.mkdir( parents = True, exist_ok = True )
    proteomes_output_directory = output_directory / 'orthofinder_input_proteomes'
    proteomes_output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 002: Prepare Proteomes for OrthoFinder" )
    logger.info( "=" * 70 )

    # Validate input
    if not proteome_list_path.exists():
        logger.error( f"CRITICAL ERROR: Proteome list not found: {proteome_list_path}" )
        logger.error( "Run script 001 first to validate and list proteomes." )
        sys.exit( 1 )

    # Read proteome list
    # Proteome_Filename (proteome file name)	Full_Path (absolute path to proteome file)	Genus_Species (extracted from phyloname)	Sequence_Count (number of protein sequences in file)
    # Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens___9606-ncbi_GCF_000001.aa	/path/to/file.aa	Homo_sapiens	20000

    proteome_records = []

    with open( proteome_list_path, 'r' ) as input_proteome_list:
        header_line = input_proteome_list.readline()

        for line in input_proteome_list:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            filename = parts[ 0 ]
            full_path = parts[ 1 ]
            genus_species = parts[ 2 ]
            sequence_count = int( parts[ 3 ] )

            proteome_records.append( {
                'filename': filename,
                'full_path': full_path,
                'genus_species': genus_species,
                'sequence_count': sequence_count
            } )

    logger.info( f"Read {len( proteome_records )} proteomes from list" )

    # Copy proteomes to OrthoFinder input directory
    # OrthoFinder expects FASTA files in a single directory
    # With -X flag, original sequence identifiers are preserved

    copied_count = 0
    total_sequences = 0
    summary_records = []

    for record in proteome_records:
        source_path = Path( record[ 'full_path' ] )

        if not source_path.exists():
            logger.error( f"CRITICAL ERROR: Proteome file not found: {source_path}" )
            logger.error( f"Species: {record[ 'genus_species' ]}" )
            sys.exit( 1 )

        # OrthoFinder identifies species by filename
        # Copy with original filename to preserve GIGANTIC naming
        destination_path = proteomes_output_directory / record[ 'filename' ]

        shutil.copy2( str( source_path ), str( destination_path ) )

        copied_count += 1
        total_sequences += record[ 'sequence_count' ]

        summary_records.append( {
            'filename': record[ 'filename' ],
            'genus_species': record[ 'genus_species' ],
            'sequence_count': record[ 'sequence_count' ],
            'destination': str( destination_path )
        } )

        logger.debug( f"  Copied: {record[ 'genus_species' ]} ({record[ 'sequence_count' ]} sequences)" )

    logger.info( f"Copied {copied_count} proteomes to: {proteomes_output_directory}" )
    logger.info( f"Total sequences: {total_sequences}" )

    # Write summary file
    summary_file = output_directory / '2_ai-prepared_proteomes_summary.tsv'

    with open( summary_file, 'w' ) as output_summary:
        # Write header
        header = 'Proteome_Filename (proteome file name)' + '\t'
        header += 'Genus_Species (species name extracted from phyloname)' + '\t'
        header += 'Sequence_Count (number of protein sequences)' + '\t'
        header += 'Destination_Path (path to copied proteome file)' + '\n'
        output_summary.write( header )

        for record in summary_records:
            output = record[ 'filename' ] + '\t'
            output += record[ 'genus_species' ] + '\t'
            output += str( record[ 'sequence_count' ] ) + '\t'
            output += record[ 'destination' ] + '\n'
            output_summary.write( output )

    logger.info( f"Wrote summary to: {summary_file}" )

    # Validate output
    output_files = list( proteomes_output_directory.glob( '*.aa' ) )
    if len( output_files ) == 0:
        logger.error( "CRITICAL ERROR: No proteome files in output directory!" )
        sys.exit( 1 )

    if len( output_files ) != len( proteome_records ):
        logger.error( f"CRITICAL ERROR: Expected {len( proteome_records )} files, found {len( output_files )}!" )
        sys.exit( 1 )

    logger.info( "" )
    logger.info( "Script 002 completed successfully" )
    logger.info( f"  Proteomes prepared: {copied_count}" )
    logger.info( f"  Total sequences: {total_sequences}" )
    logger.info( f"  Output directory: {proteomes_output_directory}" )
    logger.info( "" )
    logger.info( "NOTE: OrthoFinder will be run with the -X flag to preserve" )
    logger.info( "original GIGANTIC sequence identifiers. No header conversion needed." )


if __name__ == '__main__':
    main()
