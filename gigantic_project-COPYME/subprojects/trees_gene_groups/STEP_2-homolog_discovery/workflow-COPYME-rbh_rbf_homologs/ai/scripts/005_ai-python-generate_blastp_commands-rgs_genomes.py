#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 005: Generate BLASTP Commands for RGS Genomes
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 03:20 | Purpose: Generate BLASTP commands for searching RGS against RGS genomes
# Human: Eric Edsinger

"""
Generate BLASTP commands for RGS genome search.

This script reads the RGS FASTA file and generates BLASTP commands to search
the RGS sequences against the genomes that RGS sequences came from (for reciprocal
best hit analysis).

Input:
    - RGS FASTA file (command-line argument or from config)
    - RGS genomes directory (command-line argument)

Output:
    - output/6-output/6_ai-blastp-rgs_genomes.sh: Shell script with BLASTP commands (combined with script 006)

Log:
    - Logs to file and console

Requirements:
    - Python 3.10+
    - Conda environment: blast (for subsequent BLASTP execution)
"""

from pathlib import Path
from typing import List, Set, Dict
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


def load_species_map( species_map_file: Path, logger: logging.Logger = None ) -> Dict[str, str]:
    """
    Load RGS species mapping from short names to GIGANTIC Genus_species.
    
    Args:
        species_map_file: TSV file with short_name\tGenus_species
        logger: Logger instance
        
    Returns:
        Dictionary mapping short names to Genus_species
    """
    species_map = {}
    
    with open( species_map_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split( '\t' )
            if len( parts ) >= 2:
                short_name = parts[0]
                genus_species = parts[1]
                species_map[short_name] = genus_species
    
    if logger:
        logger.info( f"Loaded {len(species_map)} species mappings" )
        for short_name, genus_species in species_map.items():
            logger.info( f"  {short_name} → {genus_species}" )
    
    return species_map


def extract_genome_identifiers_from_rgs(
    rgs_fasta: Path,
    logger: logging.Logger = None
) -> Set[str]:
    """
    Extract unique genome identifiers from RGS FASTA headers.
    
    RGS headers typically contain genome information in format:
    >rgs_id-Genus_species-...
    
    Args:
        rgs_fasta: Path to RGS FASTA file
        logger: Logger instance
        
    Returns:
        Set of unique genome identifiers (Genus_species)
    """
    genome_identifiers = set()
    
    with open( rgs_fasta, 'r' ) as input_fasta:
        for line in input_fasta:
            if line.startswith( '>' ):
                # Parse header to extract genome identifier
                header = line[1:].strip()
                
                # RGS header format: >rgsN-genome_id-other_info
                # The genome_id is typically the second part after first dash
                parts = header.split( '-' )
                
                if len( parts ) >= 2:
                    # The second part (index 1) is usually the genome identifier
                    genome_id = parts[1]
                    
                    # Valid genome IDs are non-empty alphabetic strings
                    # (simple names like "worm" or Genus_species like "Homo_sapiens")
                    if genome_id and genome_id[0].isalpha():
                        genome_identifiers.add( genome_id )
    
    if logger:
        logger.info( f"Extracted {len(genome_identifiers)} unique genome identifiers from RGS" )
    
    return genome_identifiers


def generate_blastp_commands(
    rgs_fasta: Path,
    rgs_genomes_directory: Path,
    output_directory: Path,
    genome_identifiers: Set[str],
    species_map: Dict[str, str],
    evalue: str = "1e-3",
    max_hsps: int = 1,
    outfmt: int = 6,
    threads: int = 30,
    logger: logging.Logger = None
) -> List[str]:
    """
    Generate BLASTP commands for RGS genome searches.
    
    Args:
        rgs_fasta: RGS FASTA file
        rgs_genomes_directory: Directory containing RGS genome databases
        output_directory: Directory for BLAST output files
        genome_identifiers: Set of genome identifiers (short names from RGS)
        species_map: Mapping from short names to Genus_species
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
    script_output_dir = output_directory / "6-output"
    script_output_dir.mkdir( parents=True, exist_ok=True )
    
    # Find databases for RGS genomes
    database_files = list( rgs_genomes_directory.glob( "*.aa" ) )
    
    if logger:
        logger.info( f"Found {len(database_files)} potential genome databases" )
    
    matched_databases = []
    for database_file in database_files:
        # Check if database matches any genome identifier
        database_name = database_file.name
        for short_name in genome_identifiers:
            # Map short name to Genus_species
            genus_species = species_map.get( short_name, short_name )
            
            # Check if Genus_species is in the filename
            if genus_species in database_name:
                matched_databases.append( ( short_name, database_file ) )
                if logger:
                    logger.info( f"Matched {short_name} ({genus_species}) to {database_file.name}" )
                break
    
    if logger:
        logger.info( f"Matched {len(matched_databases)} genome databases to RGS sequences" )
    
    for genome_id, database_file in matched_databases:
        # Generate output file path
        output_file = script_output_dir / f"6_ai-blast-report-rgs-versus-rgs_genome-{genome_id}.blastp"
        
        # Build BLASTP command
        command = (
            f"blastp "
            f"-db {database_file} "
            f"-query {rgs_fasta} "
            f"-out {output_file} "
            f"-outfmt {outfmt} "
            f"-evalue {evalue} "
            f"-max_hsps {max_hsps} "
            f"-num_threads {threads} &"
        )
        
        commands.append( command )
    
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
        output_file.write( "# AI: Claude Code | Sonnet 4.5 | 2025 November 07 | Purpose: Execute BLASTP searches against RGS genomes\n" )
        output_file.write( "# Human: Eric Edsinger\n" )
        output_file.write( "# Generated by: 005_ai-python-generate_blastp_commands-rgs_genomes.py\n\n" )
        
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
        description='Generate BLASTP commands for RGS genome search'
    )
    
    parser.add_argument(
        '--rgs-fasta',
        type=Path,
        required=True,
        help='Reference Gene Set (RGS) FASTA file'
    )
    
    parser.add_argument(
        '--rgs-genomes-dir',
        type=Path,
        required=True,
        help='Directory containing RGS genome database files'
    )
    
    parser.add_argument(
        '--rgs-species-map',
        type=Path,
        required=True,
        help='TSV file mapping RGS short names to GIGANTIC Genus_species'
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
        default=Path( '006-blastp-rgs_genomes.sh' ),
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
    log_file = Path( '005_ai-log-generate_blastp_commands-rgs_genomes.log' )
    logger = setup_logging( log_file )
    
    logger.info( "="*80 )
    logger.info( "Generate BLASTP Commands - RGS Genomes" )
    logger.info( "="*80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    
    # Validate inputs
    if not args.rgs_fasta.exists():
        logger.error( f"RGS FASTA file not found: {args.rgs_fasta}" )
        sys.exit( 1 )
    
    if not args.rgs_genomes_dir.exists():
        logger.error( f"RGS genomes directory not found: {args.rgs_genomes_dir}" )
        sys.exit( 1 )
    
    if not args.rgs_species_map.exists():
        logger.error( f"RGS species map file not found: {args.rgs_species_map}" )
        sys.exit( 1 )
    
    if not args.output_dir.exists():
        logger.info( f"Creating output directory: {args.output_dir}" )
        args.output_dir.mkdir( parents=True, exist_ok=True )
    
    # Load species mapping
    logger.info( "\nLoading RGS species mapping..." )
    species_map = load_species_map( args.rgs_species_map, logger )
    
    if not species_map:
        logger.error( "CRITICAL ERROR: No species mappings loaded!" )
        logger.error( f"Check format of: {args.rgs_species_map}" )
        sys.exit( 1 )
    
    # Extract genome identifiers from RGS
    logger.info( "\nExtracting genome identifiers from RGS..." )
    genome_identifiers = extract_genome_identifiers_from_rgs( args.rgs_fasta, logger )
    
    if not genome_identifiers:
        logger.error( "CRITICAL ERROR: No genome identifiers found in RGS headers!" )
        logger.error( "RGS headers must follow format: >rgsN-species-source-identifier" )
        logger.error( "Cannot proceed without genome identifiers for RGS genome BLAST." )
        sys.exit( 1 )  # FAIL - this is a critical error
    
    # Generate commands
    logger.info( "\nGenerating BLASTP commands..." )
    commands = generate_blastp_commands(
        rgs_fasta=args.rgs_fasta,
        rgs_genomes_directory=args.rgs_genomes_dir,
        output_directory=args.output_dir,
        genome_identifiers=genome_identifiers,
        species_map=species_map,
        evalue=args.evalue,
        threads=args.threads,
        logger=logger
    )
    
    # Validate that commands were generated (subtract 2 for 'wait' and 'echo' commands)
    num_blast_commands = len( commands ) - 2
    if num_blast_commands == 0:
        logger.error( "CRITICAL ERROR: No BLAST commands generated!" )
        logger.error( f"Genome identifiers found in RGS: {genome_identifiers}" )
        logger.error( f"RGS genomes directory: {args.rgs_genomes_dir}" )
        logger.error( "No genome databases matched the RGS species identifiers." )
        logger.error( "Check that genome files exist in the RGS genomes directory." )
        sys.exit( 1 )  # FAIL - this is a critical error
    
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

