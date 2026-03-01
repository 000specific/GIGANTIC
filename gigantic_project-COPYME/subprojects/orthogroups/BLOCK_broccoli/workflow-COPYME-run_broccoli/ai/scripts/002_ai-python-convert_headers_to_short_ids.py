#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Convert FASTA headers to short IDs for orthogroup detection
# Human: Eric Edsinger

"""
002_ai-python-convert_headers_to_short_ids.py

Converts GIGANTIC proteome FASTA headers to short sequential IDs.
OrthoHMM requires simple headers; this script creates them while maintaining
a mapping for downstream reconstruction of full GIGANTIC identifiers.

Input:
    --proteome-list: Path to 1_ai-proteome_list.tsv from script 001

Output:
    OUTPUT_pipeline/2-output/short_header_proteomes/
        FASTA files with short headers (Genus_species-1, Genus_species-2, etc.)
        Named as Genus_species.aa

    OUTPUT_pipeline/2-output/2_ai-header_mapping.tsv
        Tab-separated mapping file with columns:
        - Short_ID (the short header used for orthogroup detection)
        - Original_Header (the full GIGANTIC identifier)
        - Genus_Species (species name)
        - Original_Filename (source proteome file)

Usage:
    python3 002_ai-python-convert_headers_to_short_ids.py \\
        --proteome-list OUTPUT_pipeline/1-output/1_ai-proteome_list.tsv
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '002_convert_headers' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '2_ai-log-convert_headers_to_short_ids.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def convert_proteome_headers(
    proteome_path: Path,
    genus_species: str,
    output_directory: Path,
    original_filename: str,
    logger: logging.Logger
) -> list:
    """
    Convert a single proteome file to short header format.

    Returns list of mapping records.
    """

    mapping_records = []
    sequence_index = 0
    current_header = None
    current_sequence_lines = []

    output_file = output_directory / f'{genus_species}.aa'

    with open( proteome_path, 'r' ) as input_fasta:
        with open( output_file, 'w' ) as output_fasta:

            for line in input_fasta:
                line = line.rstrip( '\n' )

                if line.startswith( '>' ):
                    # Write previous sequence if exists
                    if current_header is not None:
                        sequence_index += 1
                        short_id = f'{genus_species}-{sequence_index}'

                        # Write to output FASTA
                        output = '>' + short_id + '\n'
                        output_fasta.write( output )

                        for sequence_line in current_sequence_lines:
                            output = sequence_line + '\n'
                            output_fasta.write( output )

                        # Record mapping
                        mapping_records.append( {
                            'short_id': short_id,
                            'original_header': current_header,
                            'genus_species': genus_species,
                            'original_filename': original_filename
                        } )

                    # Start new sequence
                    current_header = line[ 1: ]  # Remove '>'
                    current_sequence_lines = []

                else:
                    # Sequence line
                    current_sequence_lines.append( line )

            # Write final sequence
            if current_header is not None:
                sequence_index += 1
                short_id = f'{genus_species}-{sequence_index}'

                output = '>' + short_id + '\n'
                output_fasta.write( output )

                for sequence_line in current_sequence_lines:
                    output = sequence_line + '\n'
                    output_fasta.write( output )

                mapping_records.append( {
                    'short_id': short_id,
                    'original_header': current_header,
                    'genus_species': genus_species,
                    'original_filename': original_filename
                } )

    logger.debug( f"  {genus_species}: {sequence_index} sequences converted" )

    return mapping_records


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Convert FASTA headers to short IDs for orthogroup detection'
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
    short_header_directory = output_directory / 'short_header_proteomes'
    short_header_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 002: Convert Headers to Short IDs" )
    logger.info( "=" * 70 )

    # Validate input file exists
    if not proteome_list_path.exists():
        logger.error( f"CRITICAL ERROR: Proteome list file not found!" )
        logger.error( f"Expected path: {proteome_list_path}" )
        logger.error( "Run script 001 first to generate the proteome list." )
        sys.exit( 1 )

    # Read proteome list
    # Proteome_Filename (proteome file name)	Full_Path (absolute path to proteome file)	Genus_Species (extracted from phyloname)	Sequence_Count (number of protein sequences in file)
    # Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens___9606-ncbi_GCF_000001.aa	/full/path/to/file.aa	Homo_sapiens	20000

    all_mapping_records = []
    proteome_count = 0
    total_sequences = 0

    logger.info( f"Reading proteome list from: {proteome_list_path}" )

    with open( proteome_list_path, 'r' ) as input_proteome_list:
        # Skip header
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

            proteome_path = Path( full_path )

            # Validate file exists
            if not proteome_path.exists():
                logger.error( f"CRITICAL ERROR: Proteome file not found: {proteome_path}" )
                sys.exit( 1 )

            # Convert headers
            mapping_records = convert_proteome_headers(
                proteome_path = proteome_path,
                genus_species = genus_species,
                output_directory = short_header_directory,
                original_filename = filename,
                logger = logger
            )

            all_mapping_records.extend( mapping_records )
            proteome_count += 1
            total_sequences += len( mapping_records )

    logger.info( f"Processed {proteome_count} proteomes" )
    logger.info( f"Total sequences converted: {total_sequences}" )

    # Write mapping file
    mapping_file = output_directory / '2_ai-header_mapping.tsv'

    with open( mapping_file, 'w' ) as output_mapping:
        # Write header
        header = 'Short_ID (short header format Genus_species-N)' + '\t'
        header += 'Original_Header (full GIGANTIC protein identifier)' + '\t'
        header += 'Genus_Species (species name)' + '\t'
        header += 'Original_Filename (source proteome file)' + '\n'
        output_mapping.write( header )

        # Write data rows
        for record in all_mapping_records:
            output = record[ 'short_id' ] + '\t'
            output += record[ 'original_header' ] + '\t'
            output += record[ 'genus_species' ] + '\t'
            output += record[ 'original_filename' ] + '\n'
            output_mapping.write( output )

    logger.info( f"Wrote header mapping to: {mapping_file}" )
    logger.info( f"Short-header proteomes written to: {short_header_directory}" )
    logger.info( f"Script 002 completed successfully" )


if __name__ == '__main__':
    main()
