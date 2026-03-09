#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 001: Setup Block Directories
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 03:00 | Purpose: Setup Block 2 directory structure and initialize input files
# Human: Eric Edsinger

"""
Setup Block 2 directory structure for gene family analysis.

This script creates the necessary directories, copies input files (RGS and species lists),
and generates the initial BLAST database list for homolog discovery.

Input:
    - RGS FASTA file (command-line argument)
    - Species keeper list (command-line argument)
    - BLAST databases directory (command-line argument)

Output:
    - block_2-homologs/job_1/ directory structure
    - input/rgs.aa - copied RGS file
    - input/species-keeper-list - copied species list
    - output/1-output/1_ai-list-projectdb-blastdbs - list of BLAST databases

Log:
    - 001_ai-log-setup_block_directories.log

Requirements:
    - Python 3.10+
    - Access to project BLAST databases
"""

from pathlib import Path
from typing import List
import argparse
import logging
from datetime import datetime
import sys
import shutil


def setup_logging( log_file_path: Path ) -> logging.Logger:
    """
    Configure logging for the script.
    
    Args:
        log_file_path: Path to log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger( __name__ )
    logger.setLevel( logging.INFO )
    
    # File handler
    file_handler = logging.FileHandler( log_file_path )
    file_handler.setLevel( logging.INFO )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )
    
    logger.addHandler( file_handler )
    logger.addHandler( console_handler )
    
    return logger


def create_directory_structure( base_directory: Path, logger: logging.Logger = None ) -> Path:
    """
    Create Block 2 directory structure.
    
    Args:
        base_directory: Base directory for gene family
        logger: Logger instance
        
    Returns:
        Path to job_1 directory
    """
    job_directory = base_directory / "block_2-homologs" / "job_1"
    input_directory = job_directory / "input"
    output_directory = job_directory / "output"
    
    # Create directories
    for directory in [ job_directory, input_directory, output_directory ]:
        directory.mkdir( parents=True, exist_ok=True )
        if logger:
            logger.info( f"Created directory: {directory}" )
    
    return job_directory


def copy_input_files(
    rgs_file: Path,
    species_list: Path,
    job_directory: Path,
    logger: logging.Logger = None
) -> None:
    """
    Copy RGS and species list files to input directory.
    
    Args:
        rgs_file: Source RGS FASTA file
        species_list: Source species keeper list file
        job_directory: Target job directory
        logger: Logger instance
    """
    input_directory = job_directory / "input"
    
    # Copy RGS file
    target_rgs = input_directory / "rgs.aa"
    shutil.copy2( rgs_file, target_rgs )
    if logger:
        logger.info( f"Copied RGS file: {rgs_file} -> {target_rgs}" )
    
    # Copy species list
    target_species = input_directory / "species-keeper-list"
    shutil.copy2( species_list, target_species )
    if logger:
        logger.info( f"Copied species list: {species_list} -> {target_species}" )


def generate_blast_database_list(
    blast_databases_directory: Path,
    output_file: Path,
    pattern: str = "*.aa",
    logger: logging.Logger = None
) -> int:
    """
    Generate list of BLAST database files.
    
    Args:
        blast_databases_directory: Directory containing BLAST databases
        output_file: Output file path
        pattern: File pattern to match (default: *.aa)
        logger: Logger instance
        
    Returns:
        Number of databases found
    """
    # Find all matching database files
    database_files = sorted( blast_databases_directory.glob( pattern ) )
    
    if not database_files:
        if logger:
            logger.warning( f"No database files found matching pattern '{pattern}' in {blast_databases_directory}" )
        return 0
    
    # Write database list
    with open( output_file, 'w' ) as output_handle:
        for database_file in database_files:
            output_handle.write( str( database_file ) + '\n' )
    
    if logger:
        logger.info( f"Generated database list: {output_file}" )
        logger.info( f"Found {len(database_files)} BLAST databases" )
    
    return len( database_files )


def main():
    """
    Main execution function.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Setup Block 2 directory structure for gene family analysis'
    )
    
    parser.add_argument(
        '--gene-family',
        type=str,
        required=True,
        help='Gene family name'
    )
    
    parser.add_argument(
        '--rgs-file',
        type=Path,
        required=True,
        help='Path to RGS FASTA file'
    )
    
    parser.add_argument(
        '--species-list',
        type=Path,
        required=True,
        help='Path to species keeper list file'
    )
    
    parser.add_argument(
        '--blast-databases',
        type=Path,
        required=True,
        help='Directory containing BLAST databases'
    )
    
    parser.add_argument(
        '--output-base',
        type=Path,
        default=Path( 'OUTPUT_pipeline' ),
        help='Base output directory (default: OUTPUT_pipeline)'
    )
    
    parser.add_argument(
        '--database-pattern',
        type=str,
        default='*.aa',
        help='Pattern for BLAST database files (default: *.aa)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path( '001_ai-log-setup_block_directories.log' )
    logger = setup_logging( log_file )
    
    logger.info( "="*80 )
    logger.info( "Setup Block 2 Directory Structure" )
    logger.info( "="*80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Gene family: {args.gene_family}" )
    
    # Validate inputs
    if not args.rgs_file.exists():
        logger.error( f"RGS file not found: {args.rgs_file}" )
        sys.exit( 1 )
    
    if not args.species_list.exists():
        logger.error( f"Species list file not found: {args.species_list}" )
        sys.exit( 1 )
    
    if not args.blast_databases.exists():
        logger.error( f"BLAST databases directory not found: {args.blast_databases}" )
        sys.exit( 1 )
    
    # Create directory structure
    logger.info( "\nCreating directory structure..." )
    base_directory = args.output_base / args.gene_family
    job_directory = create_directory_structure( base_directory, logger )
    
    # Copy input files
    logger.info( "\nCopying input files..." )
    copy_input_files( args.rgs_file, args.species_list, job_directory, logger )
    
    # Generate BLAST database list
    logger.info( "\nGenerating BLAST database list..." )
    output_directory = job_directory / "output"
    script_output_dir = output_directory / "1-output"
    script_output_dir.mkdir( parents=True, exist_ok=True )
    database_list_file = script_output_dir / "1_ai-list-projectdb-blastdbs"
    database_count = generate_blast_database_list(
        args.blast_databases,
        database_list_file,
        args.database_pattern,
        logger
    )
    
    logger.info( "\n" + "="*80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "="*80 )
    logger.info( f"\nJob directory: {job_directory}" )
    logger.info( f"RGS file: {job_directory / 'input' / 'rgs.aa'}" )
    logger.info( f"Species list: {job_directory / 'input' / 'species-keeper-list'}" )
    logger.info( f"Database list: {database_list_file}" )
    logger.info( f"Total databases: {database_count}" )
    logger.info( f"\nLog file: {log_file}" )
    logger.info( f"\nScript completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == "__main__":
    main()

