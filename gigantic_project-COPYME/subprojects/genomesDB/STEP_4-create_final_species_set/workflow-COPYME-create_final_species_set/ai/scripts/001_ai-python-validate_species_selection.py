#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Validate species selection against STEP_2 and STEP_3 outputs
# Human: Eric Edsinger

"""
GIGANTIC genomesDB STEP_4 - Script 001: Validate Species Selection

Purpose:
    Validates that all species in the user's selection exist in both STEP_2
    (cleaned proteomes) and STEP_3 (BLAST databases). If no selection file
    is provided, defaults to all species found in STEP_2.

Inputs:
    --step2-proteomes: Path to STEP_2 cleaned proteomes directory
    --step3-blastp: Path to STEP_3 BLAST databases directory
    --selected-species: Path to user's species selection file (optional)
    --output-dir: Output directory for validated list and count

Outputs:
    1-output/1_ai-validated_species_list.txt - One species per line
    1-output/1_ai-species_count.txt - Single number (count of species)
    1-output/1_ai-log-validate_species_selection.log - Execution log
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( 'validate_species_selection' )
    logger.setLevel( logging.INFO )

    # File handler
    log_file = output_dir / '1_ai-log-validate_species_selection.log'
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


def get_species_from_proteomes( proteomes_dir: Path ) -> set:
    """Extract species names from proteome filenames."""
    species_names = set()

    if not proteomes_dir.exists():
        return species_names

    for proteome_file in proteomes_dir.glob( '*.aa' ):
        # Extract genus_species from GIGANTIC filename
        # Format: phyloname___taxid-assembly-date-type.aa
        filename = proteome_file.stem
        parts_filename = filename.split( '___' )
        if len( parts_filename ) >= 1:
            phyloname = parts_filename[ 0 ]
            parts_phyloname = phyloname.split( '_' )
            if len( parts_phyloname ) >= 7:
                genus = parts_phyloname[ 5 ]
                species = '_'.join( parts_phyloname[ 6: ] )
                genus_species = genus + '_' + species
                species_names.add( genus_species )

    return species_names


def get_species_from_blastp( blastp_dir: Path ) -> set:
    """Extract species names from BLAST database filenames."""
    species_names = set()

    if not blastp_dir.exists():
        return species_names

    # Look for .phr files (BLAST protein header files)
    for db_file in blastp_dir.glob( '*.phr' ):
        # Extract genus_species from GIGANTIC filename
        filename = db_file.stem
        parts_filename = filename.split( '___' )
        if len( parts_filename ) >= 1:
            phyloname = parts_filename[ 0 ]
            parts_phyloname = phyloname.split( '_' )
            if len( parts_phyloname ) >= 7:
                genus = parts_phyloname[ 5 ]
                species = '_'.join( parts_phyloname[ 6: ] )
                genus_species = genus + '_' + species
                species_names.add( genus_species )

    return species_names


def load_selected_species( selected_species_file: Path ) -> set:
    """Load user's species selection from file."""
    species_names = set()

    if not selected_species_file.exists():
        return species_names

    with open( selected_species_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith( '#' ):
                species_names.add( line )

    return species_names


def main():
    parser = argparse.ArgumentParser(
        description = 'Validate species selection against STEP_2 and STEP_3 outputs'
    )
    parser.add_argument( '--step2-proteomes', required = True,
                        help = 'Path to STEP_2 cleaned proteomes directory' )
    parser.add_argument( '--step3-blastp', required = True,
                        help = 'Path to STEP_3 BLAST databases directory' )
    parser.add_argument( '--selected-species', required = True,
                        help = 'Path to user species selection file' )
    parser.add_argument( '--output-dir', required = True,
                        help = 'Output directory' )

    args = parser.parse_args()

    # Convert paths
    step2_proteomes_dir = Path( args.step2_proteomes )
    step3_blastp_dir = Path( args.step3_blastp )
    selected_species_file = Path( args.selected_species )
    output_dir = Path( args.output_dir )

    # Ensure output directory exists
    output_dir.mkdir( parents = True, exist_ok = True )

    # Set up logging
    logger = setup_logging( output_dir )

    logger.info( '=' * 70 )
    logger.info( 'GIGANTIC genomesDB STEP_4 - Validate Species Selection' )
    logger.info( '=' * 70 )

    # Get species from STEP_2
    logger.info( f'Reading species from STEP_2: {step2_proteomes_dir}' )
    step2_species = get_species_from_proteomes( step2_proteomes_dir )
    logger.info( f'  Found {len( step2_species )} species in STEP_2' )

    if len( step2_species ) == 0:
        logger.error( 'CRITICAL ERROR: No species found in STEP_2 proteomes!' )
        logger.error( f'  Expected proteomes in: {step2_proteomes_dir}' )
        logger.error( '  Ensure STEP_2 has completed successfully.' )
        sys.exit( 1 )

    # Get species from STEP_3
    logger.info( f'Reading species from STEP_3: {step3_blastp_dir}' )
    step3_species = get_species_from_blastp( step3_blastp_dir )
    logger.info( f'  Found {len( step3_species )} species in STEP_3' )

    if len( step3_species ) == 0:
        logger.error( 'CRITICAL ERROR: No species found in STEP_3 BLAST databases!' )
        logger.error( f'  Expected databases in: {step3_blastp_dir}' )
        logger.error( '  Ensure STEP_3 has completed successfully.' )
        sys.exit( 1 )

    # Get user selection or default to all species
    logger.info( f'Reading species selection: {selected_species_file}' )
    selected_species = load_selected_species( selected_species_file )

    if len( selected_species ) == 0:
        logger.info( '  No selection file found - using all species from STEP_2' )
        selected_species = step2_species.copy()
    else:
        logger.info( f'  User selected {len( selected_species )} species' )

    # Validate selection against both STEP_2 and STEP_3
    logger.info( 'Validating species selection...' )

    missing_from_step2 = selected_species - step2_species
    missing_from_step3 = selected_species - step3_species

    if missing_from_step2:
        logger.error( f'CRITICAL ERROR: {len( missing_from_step2 )} species not found in STEP_2:' )
        for species_name in sorted( missing_from_step2 ):
            logger.error( f'  - {species_name}' )
        sys.exit( 1 )

    if missing_from_step3:
        logger.error( f'CRITICAL ERROR: {len( missing_from_step3 )} species not found in STEP_3:' )
        for species_name in sorted( missing_from_step3 ):
            logger.error( f'  - {species_name}' )
        sys.exit( 1 )

    # All species validated
    validated_species = sorted( selected_species )
    species_count = len( validated_species )

    logger.info( f'  All {species_count} species validated successfully!' )

    # Write validated species list
    output_validated_list = output_dir / '1_ai-validated_species_list.txt'
    with open( output_validated_list, 'w' ) as output_file:
        for species_name in validated_species:
            output = species_name + '\n'
            output_file.write( output )
    logger.info( f'Wrote validated species list: {output_validated_list}' )

    # Write species count
    output_species_count = output_dir / '1_ai-species_count.txt'
    with open( output_species_count, 'w' ) as output_file:
        output = str( species_count ) + '\n'
        output_file.write( output )
    logger.info( f'Wrote species count: {output_species_count}' )

    logger.info( '=' * 70 )
    logger.info( f'SUCCESS: {species_count} species validated' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
