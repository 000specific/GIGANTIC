#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 002: Generate BLASTP Commands for Project Database
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 02:15 | Purpose: Generate BLASTP commands for searching RGS against project databases
# Human: Eric Edsinger

"""
Generate BLASTP commands for project database search.

This script reads a list of BLAST database files from the project database,
extracts species names from the file paths, and generates BLASTP commands
to search the Reference Gene Set (RGS) against each database.

Input:
    - output/1-output/1_ai-list-projectdb-blastdbs: List of BLAST database file paths
    - RGS FASTA file (command-line argument or from config)

Output:
    - output/3-output/3_ai-blastp-project_database.sh: Shell script with BLASTP commands (combined with script 003)

Log:
    - Logs to file and console

Requirements:
    - Python 3.10+
    - Conda environment: blast (for subsequent BLASTP execution)
"""

from pathlib import Path
from typing import List, Tuple
import argparse
import logging
from datetime import datetime
import sys


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


def extract_species_from_database_path( database_path: str ) -> str:
    """
    Extract genus and species name from database file path.
    
    The path format is expected to be:
    Taxon_Group_Family_Genus_species___accession-source-details.aa
    
    Args:
        database_path: Path to BLAST database file
        
    Returns:
        Species name in format "Genus_species"
    """
    # Extract phyloname (everything before '___')
    phyloname = database_path.split( '___' )[ 0 ]
    
    # Split by underscore
    parts = phyloname.split( '_' )
    
    # Extract genus (position 5) and species (position 6 onward)
    if len( parts ) >= 7:
        genus = parts[ 5 ]
        species = '_'.join( parts[ 6: ] )
        genus_species = f"{genus}_{species}"
    else:
        # Fallback: use last two components
        genus_species = '_'.join( parts[ -2: ] )
    
    return genus_species


def generate_blastp_commands(
    database_list_file: Path,
    rgs_fasta_file: Path,
    output_directory: Path,
    evalue: str = "1e-3",
    max_hsps: int = 1,
    outfmt: int = 6,
    threads: int = 30,
    logger: logging.Logger = None
) -> List[str]:
    """
    Generate BLASTP commands for each database.
    
    Args:
        database_list_file: File containing list of BLAST database paths
        rgs_fasta_file: Reference Gene Set FASTA file
        output_directory: Directory for BLAST output files
        evalue: E-value threshold for BLAST
        max_hsps: Maximum HSPs per subject sequence
        outfmt: BLAST output format
        threads: Number of threads for BLAST
        logger: Logger instance
        
    Returns:
        List of BLASTP command strings
    """
    commands = []
    
    # Create script output directory
    script_output_dir = output_directory / "3-output"
    script_output_dir.mkdir( parents=True, exist_ok=True )
    
    if logger:
        logger.info( f"Reading database list from: {database_list_file}" )
    
    with open( database_list_file, 'r' ) as input_list:
        for line in input_list:
            database_path = line.strip()
            
            if not database_path:
                continue
            
            # Extract species name
            genus_species = extract_species_from_database_path( database_path )
            
            # Generate output file path
            output_file = script_output_dir / f"3_ai-blast-report-rgs-versus-projectdb-{genus_species}.blastp"
            
            # Build BLASTP command
            command = (
                f"blastp "
                f"-db {database_path} "
                f"-query {rgs_fasta_file} "
                f"-out {output_file} "
                f"-outfmt {outfmt} "
                f"-evalue {evalue} "
                f"-max_hsps {max_hsps} "
                f"-num_threads {threads} &"
            )
            
            commands.append( command )
            
            if logger:
                logger.debug( f"Generated command for: {genus_species}" )
    
    # Add wait command at end
    commands.append( "wait" )
    commands.append( "echo 'All BLASTP jobs completed'" )
    
    if logger:
        logger.info( f"Generated {len(commands) - 2} BLASTP commands" )
    
    return commands


def write_blast_script(
    commands: List[str],
    output_script_file: Path,
    conda_env: str = "blast",
    logger: logging.Logger = None
) -> None:
    """
    Write BLASTP commands to shell script.
    
    Args:
        commands: List of BLASTP command strings
        output_script_file: Path to output shell script
        conda_env: Name of conda environment to activate
        logger: Logger instance
    """
    with open( output_script_file, 'w' ) as output_file:
        # Write shebang and header
        output_file.write( "#!/bin/bash\n" )
        output_file.write( "# AI: Claude Code | Sonnet 4.5 | 2025 November 07 | Purpose: Execute BLASTP searches against project databases\n" )
        output_file.write( "# Human: Eric Edsinger\n" )
        output_file.write( "# Generated by: 002_ai-python-generate_blastp_commands-project_database.py\n\n" )
        
        # Write conda activation
        output_file.write( "# Activate conda environment\n" )
        output_file.write( "module load python\n" )
        output_file.write( "module load conda\n" )
        output_file.write( f"conda activate {conda_env}\n\n" )
        
        # Write commands
        output_file.write( "# BLASTP commands\n" )
        for command in commands:
            output_file.write( command + "\n" )
    
    # Make executable
    output_script_file.chmod( 0o755 )
    
    if logger:
        logger.info( f"Wrote executable script: {output_script_file}" )


def main():
    """
    Main execution function.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Generate BLASTP commands for project database search'
    )
    
    parser.add_argument(
        '--database-list',
        type=Path,
        default=Path( 'output/1-list-projectdb-blastdbs' ),
        help='File containing list of BLAST database paths'
    )
    
    parser.add_argument(
        '--rgs-fasta',
        type=Path,
        required=True,
        help='Reference Gene Set (RGS) FASTA file'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path( 'output' ),
        help='Output directory for BLAST results'
    )
    
    parser.add_argument(
        '--output-script',
        type=Path,
        default=Path( '3-blastp-project_database.sh' ),
        help='Output shell script file'
    )
    
    parser.add_argument(
        '--evalue',
        type=str,
        default='1e-3',
        help='E-value threshold for BLAST'
    )
    
    parser.add_argument(
        '--threads',
        type=int,
        default=30,
        help='Number of threads for BLAST'
    )
    
    parser.add_argument(
        '--conda-env',
        type=str,
        default='blast',
        help='Conda environment name for BLAST'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path( '002_ai-log-generate_blastp_commands.log' )
    logger = setup_logging( log_file )
    
    logger.info( "="*80 )
    logger.info( "Generate BLASTP Commands - Project Database" )
    logger.info( "="*80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    
    # Validate inputs
    if not args.database_list.exists():
        logger.error( f"Database list file not found: {args.database_list}" )
        sys.exit( 1 )
    
    if not args.rgs_fasta.exists():
        logger.error( f"RGS FASTA file not found: {args.rgs_fasta}" )
        sys.exit( 1 )
    
    if not args.output_dir.exists():
        logger.info( f"Creating output directory: {args.output_dir}" )
        args.output_dir.mkdir( parents=True, exist_ok=True )
    
    # Generate commands
    logger.info( "\nGenerating BLASTP commands..." )
    commands = generate_blastp_commands(
        database_list_file=args.database_list,
        rgs_fasta_file=args.rgs_fasta,
        output_directory=args.output_dir,
        evalue=args.evalue,
        threads=args.threads,
        logger=logger
    )
    
    # Write script
    logger.info( "\nWriting shell script..." )
    write_blast_script(
        commands=commands,
        output_script_file=args.output_script,
        conda_env=args.conda_env,
        logger=logger
    )
    
    logger.info( "\n" + "="*80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "="*80 )
    logger.info( f"\nGenerated script: {args.output_script}" )
    logger.info( f"Total BLASTP commands: {len(commands) - 2}" )
    logger.info( f"\nTo execute: ./{args.output_script}" )
    logger.info( f"Log file: {log_file}" )
    
    logger.info( f"\nScript completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == "__main__":
    main()

