#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 06 00:00 | Purpose: Build per-genome BLAST databases for all species from STEP_2
# Human: Eric Edsinger

"""
001_ai-python-build_per_genome_blastdbs.py

Build individual BLAST protein databases for ALL species from STEP_2.
Each species gets its own BLAST database (not a single concatenated database).

Inputs:
    - Cleaned proteomes directory from STEP_2's output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/
    - All .aa files in the directory are processed (no filtering)

Outputs:
    - Per-genome BLAST databases in 1-output/gigantic-T1-blastp/
    - makeblastdb command log
    # NOTE: RUN-workflow.sh creates symlinks in output_to_input/ after pipeline completes

Usage:
    python3 001_ai-python-build_per_genome_blastdbs.py \\
        --proteomes-dir PATH_TO_PROTEOMES \\
        --output-dir 1-output
"""

import argparse
import sys
import logging
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging( log_file_path: Path ) -> logging.Logger:
    """
    Configure logging to both file and console.

    Args:
        log_file_path: Path to the log file

    Returns:
        Configured logger instance
    """

    logger = logging.getLogger( 'build_per_genome_blastdbs' )
    logger.setLevel( logging.DEBUG )

    # File handler
    file_handler = logging.FileHandler( log_file_path, mode = 'w' )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s | %(levelname)-8s | %(message)s', datefmt = '%Y-%m-%d %H:%M:%S' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    # Console handler
    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(levelname)-8s | %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    return logger


# ============================================================================
# BUILD SINGLE BLAST DATABASE
# ============================================================================

def build_single_blastdb(
    proteome_path: Path,
    blastdb_dir: Path,
    logger_name: str
) -> dict:
    """
    Build a BLAST database for a single proteome.

    Args:
        proteome_path: Path to the proteome FASTA file
        blastdb_dir: Directory for BLAST database output
        logger_name: Logger name for this process

    Returns:
        Dictionary with build results
    """

    logger = logging.getLogger( logger_name )

    proteome_filename = proteome_path.name

    # Copy FASTA to blastdb directory
    dest_fasta = blastdb_dir / proteome_filename

    try:
        shutil.copy2( proteome_path, dest_fasta )
    except Exception as error:
        return {
            'proteome_filename': proteome_filename,
            'success': False,
            'error': f"Failed to copy FASTA: {error}"
        }

    # Build BLAST database
    # Command: makeblastdb -in FASTA -dbtype prot -out FASTA
    # Note: We omit -parse_seqids because GIGANTIC sequence IDs exceed BLAST's
    # 50-character limit. BLAST searches still work correctly without this flag.
    makeblastdb_command = [
        'makeblastdb',
        '-in', str( dest_fasta ),
        '-dbtype', 'prot',
        '-out', str( dest_fasta )
    ]

    try:
        # Suppress stderr to avoid thousands of "invalid residue" warnings
        # (selenocysteine, pyrrolysine, etc.) which slow down execution
        result = subprocess.run(
            makeblastdb_command,
            stdout = subprocess.PIPE,
            stderr = subprocess.DEVNULL,
            text = True,
            check = True
        )

        return {
            'proteome_filename': proteome_filename,
            'success': True,
            'fasta_path': str( dest_fasta ),
            'command': ' '.join( makeblastdb_command ),
            'stdout': result.stdout
        }

    except subprocess.CalledProcessError as error:
        return {
            'proteome_filename': proteome_filename,
            'success': False,
            'error': f"makeblastdb failed: {error.stderr}",
            'command': ' '.join( makeblastdb_command )
        }

    except FileNotFoundError:
        return {
            'proteome_filename': proteome_filename,
            'success': False,
            'error': "makeblastdb not found. Is BLAST+ installed and in PATH?"
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: build per-genome BLAST databases for all species.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Build per-genome BLAST protein databases for all species from STEP_2.',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--proteomes-dir',
        type = str,
        required = True,
        help = 'Path to cleaned proteomes from STEP_2'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '1-output',
        help = 'Base output directory (default: 1-output)'
    )

    parser.add_argument(
        '--database-name',
        type = str,
        default = 'gigantic-T1-blastp',
        help = 'Name for the BLAST database directory (default: gigantic-T1-blastp)'
    )

    parser.add_argument(
        '--parallel',
        type = int,
        default = 4,
        help = 'Number of parallel makeblastdb jobs (default: 4)'
    )

    arguments = parser.parse_args()

    # ========================================================================
    # PATH SETUP
    # ========================================================================

    proteomes_directory = Path( arguments.proteomes_dir )
    output_base_directory = Path( arguments.output_dir )
    database_name = arguments.database_name

    blastdb_directory = output_base_directory / database_name
    output_commands_path = output_base_directory / '1_ai-makeblastdb_commands.sh'
    output_log_path = output_base_directory / '1_ai-log-build_per_genome_blastdbs.log'

    # Create output directories
    blastdb_directory.mkdir( parents = True, exist_ok = True )
    output_base_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC genomesDB STEP_3 - Build Per-Genome BLAST Databases" )
    logger.info( "Script: 001_ai-python-build_per_genome_blastdbs.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Proteomes directory: {proteomes_directory}" )
    logger.info( f"Database name: {database_name}" )
    logger.info( f"BLAST database directory: {blastdb_directory}" )
    logger.info( f"Parallel jobs: {arguments.parallel}" )
    logger.info( "" )

    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================

    if not proteomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Proteomes directory not found: {proteomes_directory}" )
        logger.error( "STEP_2 must be run before STEP_3." )
        logger.error( "Expected location: output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/" )
        sys.exit( 1 )

    # ========================================================================
    # FIND ALL PROTEOME FILES
    # ========================================================================

    proteome_files = sorted( proteomes_directory.glob( '*.aa' ) )

    if len( proteome_files ) == 0:
        logger.error( f"CRITICAL ERROR: No .aa proteome files found in: {proteomes_directory}" )
        logger.error( "STEP_2 must produce cleaned proteome files with .aa extension." )
        sys.exit( 1 )

    logger.info( f"Found {len( proteome_files )} proteome files to build BLAST databases" )
    logger.info( "" )

    # ========================================================================
    # BUILD DATABASES
    # ========================================================================

    logger.info( "Building per-genome BLAST databases..." )
    logger.info( "" )

    makeblastdb_commands = []
    successful_count = 0
    failed_count = 0

    with ProcessPoolExecutor( max_workers = arguments.parallel ) as executor:
        future_to_proteome = {}

        for proteome_file in proteome_files:
            future = executor.submit(
                build_single_blastdb,
                proteome_path = proteome_file,
                blastdb_dir = blastdb_directory,
                logger_name = 'build_per_genome_blastdbs'
            )
            future_to_proteome[ future ] = proteome_file

        for future in as_completed( future_to_proteome ):
            proteome_file = future_to_proteome[ future ]

            try:
                result = future.result()

                if result[ 'success' ]:
                    successful_count += 1
                    logger.info( f"  SUCCESS: {result[ 'proteome_filename' ]}" )
                    makeblastdb_commands.append( result.get( 'command', '' ) )
                else:
                    failed_count += 1
                    logger.error( f"  FAILED: {result[ 'proteome_filename' ]} - {result.get( 'error', 'Unknown error' )}" )

            except Exception as error:
                failed_count += 1
                logger.error( f"  FAILED: {proteome_file.name} - Exception: {error}" )

    # ========================================================================
    # WRITE MAKEBLASTDB COMMANDS LOG
    # ========================================================================

    logger.info( "" )
    logger.info( f"Writing makeblastdb commands to: {output_commands_path}" )

    with open( output_commands_path, 'w' ) as output_commands:
        for command in makeblastdb_commands:
            output = command + '\n'
            output_commands.write( output )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Proteome files found: {len( proteome_files )}" )
    logger.info( f"Successful builds: {successful_count}" )
    logger.info( f"Failed builds: {failed_count}" )
    logger.info( f"BLAST database directory: {blastdb_directory}" )
    logger.info( f"Commands log: {output_commands_path}" )
    logger.info( "" )
    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )

    if failed_count > 0:
        logger.error( "SOME DATABASES FAILED TO BUILD" )
        logger.info( "=" * 80 )
        sys.exit( 1 )
    else:
        logger.info( "COMPLETE" )
        logger.info( "=" * 80 )

    print( "" )
    print( f"Done! Built {successful_count} per-genome BLAST databases." )
    print( f"BLAST databases: {blastdb_directory}" )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()
