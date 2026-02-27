#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 27 | Purpose: Validate proteome directory and create input list for OrthoHMM
# Human: Eric Edsinger

"""
001_ai-python-validate_and_list_proteomes.py

Validates the input proteome directory from genomesDB and creates a list of
proteome files for the OrthoHMM workflow.

Input:
    --proteomes-dir: Path to gigantic_proteomes directory from genomesDB STEP_2

Output:
    OUTPUT_pipeline/1-output/1_ai-proteome_list.txt
        Tab-separated file with columns:
        - Proteome_Filename (name of the .aa file)
        - Full_Path (absolute path to the file)
        - Genus_Species (extracted from phyloname in filename)
        - Sequence_Count (number of sequences in the file)

Usage:
    python3 001_ai-python-validate_and_list_proteomes.py \\
        --proteomes-dir ../../genomesDB/STEP_2-standardize_and_evaluate/output_to_input/gigantic_proteomes
"""

import argparse
import logging
import os
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '001_validate_proteomes' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '1_ai-log-validate_and_list_proteomes.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def count_sequences_in_fasta( fasta_path: Path ) -> int:
    """Count the number of sequences in a FASTA file."""

    sequence_count = 0
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            if line.startswith( '>' ):
                sequence_count += 1

    return sequence_count


def extract_genus_species_from_filename( filename: str ) -> str:
    """
    Extract Genus_species from GIGANTIC proteome filename.

    Filename format: phyloname___ncbi_taxonomy_id-genome_assembly_id-download_date-data_type.aa
    Phyloname format: Kingdom_Phylum_Class_Order_Family_Genus_species

    Example input: Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens___9606-ncbi_GCF_000001.aa
    Example output: Homo_sapiens
    """

    # Split on ___ to get phyloname portion
    parts_filename = filename.split( '___' )
    phyloname = parts_filename[ 0 ]

    # Split phyloname on underscore
    parts_phyloname = phyloname.split( '_' )

    # Genus is at index 5, species is everything from index 6 onward
    if len( parts_phyloname ) >= 7:
        genus = parts_phyloname[ 5 ]
        species = '_'.join( parts_phyloname[ 6: ] )
        genus_species = genus + '_' + species
    else:
        # Fallback: use last two parts
        genus_species = '_'.join( parts_phyloname[ -2: ] )

    return genus_species


def validate_and_list_proteomes( proteomes_directory: Path, output_directory: Path, logger: logging.Logger ) -> None:
    """
    Validate proteome directory and create list of proteome files.
    """

    logger.info( f"Validating proteomes directory: {proteomes_directory}" )

    # Validate directory exists
    if not proteomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Proteomes directory does not exist!" )
        logger.error( f"Expected path: {proteomes_directory}" )
        logger.error( "Ensure genomesDB STEP_2 has completed and output_to_input is populated." )
        sys.exit( 1 )

    if not proteomes_directory.is_dir():
        logger.error( f"CRITICAL ERROR: Path is not a directory: {proteomes_directory}" )
        sys.exit( 1 )

    # Find all proteome files with valid extensions
    valid_extensions = [ '.aa', '.pep', '.fasta', '.fa' ]
    proteome_files = []

    for extension in valid_extensions:
        proteome_files.extend( list( proteomes_directory.glob( f'*{extension}' ) ) )

    # Remove duplicates and sort
    proteome_files = sorted( set( proteome_files ) )

    logger.info( f"Found {len( proteome_files )} proteome files" )

    if len( proteome_files ) == 0:
        logger.error( "CRITICAL ERROR: No proteome files found!" )
        logger.error( f"Searched directory: {proteomes_directory}" )
        logger.error( f"Valid extensions: {valid_extensions}" )
        sys.exit( 1 )

    # Process each proteome file
    proteome_records = []
    total_sequences = 0

    for proteome_path in proteome_files:
        filename = proteome_path.name
        full_path = proteome_path.resolve()
        genus_species = extract_genus_species_from_filename( filename )
        sequence_count = count_sequences_in_fasta( proteome_path )

        proteome_records.append( {
            'filename': filename,
            'full_path': str( full_path ),
            'genus_species': genus_species,
            'sequence_count': sequence_count
        } )

        total_sequences += sequence_count
        logger.debug( f"  {genus_species}: {sequence_count} sequences" )

    logger.info( f"Total sequences across all proteomes: {total_sequences}" )

    # Write output file
    output_file = output_directory / '1_ai-proteome_list.txt'

    with open( output_file, 'w' ) as output_proteome_list:
        # Write header
        header = 'Proteome_Filename (proteome file name)' + '\t'
        header += 'Full_Path (absolute path to proteome file)' + '\t'
        header += 'Genus_Species (extracted from phyloname)' + '\t'
        header += 'Sequence_Count (number of protein sequences in file)' + '\n'
        output_proteome_list.write( header )

        # Write data rows
        for record in proteome_records:
            output = record[ 'filename' ] + '\t'
            output += record[ 'full_path' ] + '\t'
            output += record[ 'genus_species' ] + '\t'
            output += str( record[ 'sequence_count' ] ) + '\n'
            output_proteome_list.write( output )

    logger.info( f"Wrote proteome list to: {output_file}" )
    logger.info( f"Script 001 completed successfully" )
    logger.info( f"  Species count: {len( proteome_records )}" )
    logger.info( f"  Total sequences: {total_sequences}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Validate proteome directory and create input list for OrthoHMM workflow'
    )

    parser.add_argument(
        '--proteomes-dir',
        type = str,
        required = True,
        help = 'Path to gigantic_proteomes directory from genomesDB STEP_2'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/1-output',
        help = 'Output directory (default: OUTPUT_pipeline/1-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    proteomes_directory = Path( arguments.proteomes_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 001: Validate and List Proteomes" )
    logger.info( "=" * 70 )

    # Run validation and listing
    validate_and_list_proteomes( proteomes_directory, output_directory, logger )


if __name__ == '__main__':
    main()
