#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Copy selected species files with speciesN naming
# Human: Eric Edsinger

"""
GIGANTIC genomesDB STEP_4 - Script 002: Copy Selected Files

Purpose:
    Copies proteomes from STEP_2 and BLAST databases from STEP_3 for the
    validated species selection. Creates output directories with speciesN_
    naming convention (e.g., species69_gigantic_T1_proteomes).

Inputs:
    --validated-species: Path to validated species list from Script 001
    --species-count: Path to species count file from Script 001
    --step2-proteomes: Path to STEP_2 cleaned proteomes directory
    --step3-blastp: Path to STEP_3 BLAST databases directory
    --output-dir: Output directory

Outputs:
    2-output/speciesN_gigantic_T1_proteomes/ - Copied proteome files
    2-output/speciesN_gigantic_T1_blastp/ - Copied BLAST database files
    2-output/2_ai-copy_manifest.tsv - Manifest of all copied files
    2-output/2_ai-log-copy_selected_files.log - Execution log
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( 'copy_selected_files' )
    logger.setLevel( logging.INFO )

    # File handler
    log_file = output_dir / '2_ai-log-copy_selected_files.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.INFO )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    # Formatter
    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


def load_validated_species( validated_species_file: Path ) -> list:
    """Load validated species list."""
    species_names = []
    with open( validated_species_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if line:
                species_names.append( line )
    return species_names


def load_species_count( species_count_file: Path ) -> int:
    """Load species count."""
    with open( species_count_file, 'r' ) as input_file:
        count = int( input_file.read().strip() )
    return count


def find_proteome_file( proteomes_dir: Path, genus_species: str ) -> Path:
    """Find proteome file for a given species."""
    # Search for file containing the genus_species in the phyloname portion
    for proteome_file in proteomes_dir.glob( '*.aa' ):
        filename = proteome_file.stem
        parts_filename = filename.split( '___' )
        if len( parts_filename ) >= 1:
            phyloname = parts_filename[ 0 ]
            parts_phyloname = phyloname.split( '_' )
            if len( parts_phyloname ) >= 7:
                genus = parts_phyloname[ 5 ]
                species = '_'.join( parts_phyloname[ 6: ] )
                file_genus_species = genus + '_' + species
                if file_genus_species == genus_species:
                    return proteome_file
    return None


def find_blastp_files( blastp_dir: Path, genus_species: str ) -> list:
    """Find all BLAST database files for a given species."""
    # BLAST databases have multiple extensions: .phr, .pin, .psq, etc.
    db_files = []
    for db_file in blastp_dir.glob( '*' ):
        if db_file.is_file():
            # Get base name without BLAST extension
            filename = db_file.name
            # Check if this file belongs to the species
            base_name = db_file.stem
            # Handle multi-extension files like .aa.phr
            if '.' in base_name:
                base_name = base_name.split( '.' )[ 0 ]

            parts_filename = base_name.split( '___' )
            if len( parts_filename ) >= 1:
                phyloname = parts_filename[ 0 ]
                parts_phyloname = phyloname.split( '_' )
                if len( parts_phyloname ) >= 7:
                    genus = parts_phyloname[ 5 ]
                    species = '_'.join( parts_phyloname[ 6: ] )
                    file_genus_species = genus + '_' + species
                    if file_genus_species == genus_species:
                        db_files.append( db_file )
    return db_files


def main():
    parser = argparse.ArgumentParser(
        description = 'Copy selected species files with speciesN naming'
    )
    parser.add_argument( '--validated-species', required = True,
                        help = 'Path to validated species list' )
    parser.add_argument( '--species-count', required = True,
                        help = 'Path to species count file' )
    parser.add_argument( '--step2-proteomes', required = True,
                        help = 'Path to STEP_2 cleaned proteomes directory' )
    parser.add_argument( '--step3-blastp', required = True,
                        help = 'Path to STEP_3 BLAST databases directory' )
    parser.add_argument( '--output-dir', required = True,
                        help = 'Output directory' )

    args = parser.parse_args()

    # Convert paths
    validated_species_file = Path( args.validated_species )
    species_count_file = Path( args.species_count )
    step2_proteomes_dir = Path( args.step2_proteomes )
    step3_blastp_dir = Path( args.step3_blastp )
    output_dir = Path( args.output_dir )

    # Ensure output directory exists
    output_dir.mkdir( parents = True, exist_ok = True )

    # Set up logging
    logger = setup_logging( output_dir )

    logger.info( '=' * 70 )
    logger.info( 'GIGANTIC genomesDB STEP_4 - Copy Selected Files' )
    logger.info( '=' * 70 )

    # Load inputs
    validated_species = load_validated_species( validated_species_file )
    species_count = load_species_count( species_count_file )

    logger.info( f'Species to copy: {species_count}' )

    # Create output directories with speciesN naming
    proteomes_output_dir = output_dir / f'species{species_count}_gigantic_T1_proteomes'
    blastp_output_dir = output_dir / f'species{species_count}_gigantic_T1_blastp'

    proteomes_output_dir.mkdir( parents = True, exist_ok = True )
    blastp_output_dir.mkdir( parents = True, exist_ok = True )

    logger.info( f'Proteomes output: {proteomes_output_dir}' )
    logger.info( f'BLASTP output: {blastp_output_dir}' )

    # Prepare manifest
    manifest_entries = []
    manifest_header = 'Source_Type (source step)\tGenus_Species (species name)\tSource_Path (original file path)\tDestination_Path (copied file path)'
    manifest_entries.append( manifest_header )

    # Copy proteomes
    logger.info( '' )
    logger.info( 'Copying proteomes from STEP_2...' )
    proteomes_copied = 0
    for genus_species in validated_species:
        proteome_file = find_proteome_file( step2_proteomes_dir, genus_species )
        if proteome_file:
            dest_file = proteomes_output_dir / proteome_file.name
            shutil.copy2( proteome_file, dest_file )
            proteomes_copied += 1

            output = 'proteome' + '\t' + genus_species + '\t' + str( proteome_file ) + '\t' + str( dest_file )
            manifest_entries.append( output )

            if proteomes_copied % 10 == 0:
                logger.info( f'  Copied {proteomes_copied} proteomes...' )
        else:
            logger.error( f'CRITICAL ERROR: Proteome not found for {genus_species}' )
            sys.exit( 1 )

    logger.info( f'  Copied {proteomes_copied} proteomes' )

    # Copy BLAST databases
    logger.info( '' )
    logger.info( 'Copying BLAST databases from STEP_3...' )
    blastp_species_copied = 0
    blastp_files_copied = 0
    for genus_species in validated_species:
        db_files = find_blastp_files( step3_blastp_dir, genus_species )
        if db_files:
            for db_file in db_files:
                dest_file = blastp_output_dir / db_file.name
                shutil.copy2( db_file, dest_file )
                blastp_files_copied += 1

                output = 'blastp' + '\t' + genus_species + '\t' + str( db_file ) + '\t' + str( dest_file )
                manifest_entries.append( output )

            blastp_species_copied += 1
            if blastp_species_copied % 10 == 0:
                logger.info( f'  Copied databases for {blastp_species_copied} species...' )
        else:
            logger.error( f'CRITICAL ERROR: BLAST databases not found for {genus_species}' )
            sys.exit( 1 )

    logger.info( f'  Copied {blastp_files_copied} BLAST database files for {blastp_species_copied} species' )

    # Write manifest
    manifest_file = output_dir / '2_ai-copy_manifest.tsv'
    with open( manifest_file, 'w' ) as output_file:
        for entry in manifest_entries:
            output = entry + '\n'
            output_file.write( output )
    logger.info( '' )
    logger.info( f'Wrote copy manifest: {manifest_file}' )

    logger.info( '' )
    logger.info( '=' * 70 )
    logger.info( f'SUCCESS: Created species{species_count}_gigantic_T1_proteomes/' )
    logger.info( f'SUCCESS: Created species{species_count}_gigantic_T1_blastp/' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
