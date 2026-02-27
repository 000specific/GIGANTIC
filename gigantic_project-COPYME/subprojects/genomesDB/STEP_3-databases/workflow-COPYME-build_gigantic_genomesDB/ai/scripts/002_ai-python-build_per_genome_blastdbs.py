#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: Build per-genome BLAST databases for each selected species
# Human: Eric Edsinger

"""
002_ai-python-build_per_genome_blastdbs.py

Build individual BLAST protein databases for each species marked Include=YES.
Each species gets its own BLAST database (not a single concatenated database).

Inputs:
    - Filtered species manifest from Script 001
    - Standardized proteomes from STEP_2's output_to_input/gigantic_proteomes/

Outputs:
    - Per-genome BLAST databases in OUTPUT_pipeline/2-output/blastdb/
    - FASTA files copied alongside BLAST databases
    - makeblastdb command log
    - Also copies to output_to_input/blastdb/ for downstream subproject access

Usage:
    python3 002_ai-python-build_per_genome_blastdbs.py \\
        --filtered-manifest OUTPUT_pipeline/1-output/1_ai-filtered_species_manifest.tsv \\
        --proteomes-dir PATH_TO_PROTEOMES \\
        --output-dir OUTPUT_pipeline/2-output

    # Run on SLURM:
    sbatch SLURM-002-build_blastdbs.sbatch
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
    phyloname = proteome_filename.replace( '-proteome.aa', '' )

    # Copy FASTA to blastdb directory
    dest_fasta = blastdb_dir / proteome_filename

    try:
        shutil.copy2( proteome_path, dest_fasta )
    except Exception as error:
        return {
            'phyloname': phyloname,
            'success': False,
            'error': f"Failed to copy FASTA: {error}"
        }

    # Build BLAST database
    # Command: makeblastdb -in FASTA -parse_seqids -dbtype prot -out FASTA
    makeblastdb_command = [
        'makeblastdb',
        '-in', str( dest_fasta ),
        '-parse_seqids',
        '-dbtype', 'prot',
        '-out', str( dest_fasta )
    ]

    try:
        result = subprocess.run(
            makeblastdb_command,
            capture_output = True,
            text = True,
            check = True
        )

        return {
            'phyloname': phyloname,
            'success': True,
            'fasta_path': str( dest_fasta ),
            'command': ' '.join( makeblastdb_command ),
            'stdout': result.stdout,
            'stderr': result.stderr
        }

    except subprocess.CalledProcessError as error:
        return {
            'phyloname': phyloname,
            'success': False,
            'error': f"makeblastdb failed: {error.stderr}",
            'command': ' '.join( makeblastdb_command )
        }

    except FileNotFoundError:
        return {
            'phyloname': phyloname,
            'success': False,
            'error': "makeblastdb not found. Is BLAST+ installed and in PATH?"
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: build per-genome BLAST databases.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Build per-genome BLAST protein databases for selected species.',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--filtered-manifest',
        type = str,
        default = 'OUTPUT_pipeline/1-output/1_ai-filtered_species_manifest.tsv',
        help = 'Path to filtered manifest from Script 001 (default: OUTPUT_pipeline/1-output/1_ai-filtered_species_manifest.tsv)'
    )

    parser.add_argument(
        '--proteomes-dir',
        type = str,
        default = '../../STEP_2-standardize_and_evaluate/output_to_input/gigantic_proteomes',
        help = 'Path to standardized proteomes from STEP_2 (default: ../../STEP_2-standardize_and_evaluate/output_to_input/gigantic_proteomes)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/2-output',
        help = 'Base output directory (default: OUTPUT_pipeline/2-output)'
    )

    parser.add_argument(
        '--output-to-input-dir',
        type = str,
        default = '../../output_to_input',
        help = 'output_to_input directory for downstream access (default: ../../output_to_input)'
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

    filtered_manifest_path = Path( arguments.filtered_manifest )
    proteomes_directory = Path( arguments.proteomes_dir )
    output_base_directory = Path( arguments.output_dir )
    output_to_input_directory = Path( arguments.output_to_input_dir )
    database_name = arguments.database_name

    # Use database name (e.g., gigantic-T1-blastp) for directory name
    blastdb_directory = output_base_directory / database_name
    output_to_input_blastdb = output_to_input_directory / database_name
    output_commands_path = output_base_directory / '2_ai-makeblastdb_commands.sh'
    output_log_path = output_base_directory / '2_ai-log-build_per_genome_blastdbs.log'

    # Create output directories
    blastdb_directory.mkdir( parents = True, exist_ok = True )
    output_to_input_blastdb.mkdir( parents = True, exist_ok = True )
    output_base_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC genomesDB STEP_3 - Build Per-Genome BLAST Databases" )
    logger.info( "Script: 002_ai-python-build_per_genome_blastdbs.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Filtered manifest: {filtered_manifest_path}" )
    logger.info( f"Proteomes directory: {proteomes_directory}" )
    logger.info( f"Database name: {database_name}" )
    logger.info( f"BLAST database directory: {blastdb_directory}" )
    logger.info( f"output_to_input: {output_to_input_blastdb}" )
    logger.info( f"Parallel jobs: {arguments.parallel}" )
    logger.info( "" )

    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================

    if not filtered_manifest_path.exists():
        logger.error( f"CRITICAL ERROR: Filtered manifest not found: {filtered_manifest_path}" )
        logger.error( "Run Script 001 first to create the filtered manifest." )
        sys.exit( 1 )

    if not proteomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Proteomes directory not found: {proteomes_directory}" )
        logger.error( "STEP_2 must be run before STEP_3." )
        logger.error( "Expected location: STEP_2/output_to_input/gigantic_proteomes/" )
        sys.exit( 1 )

    # ========================================================================
    # READ FILTERED MANIFEST
    # ========================================================================

    phylonames_to_include = []
    phyloname_column_index = -1

    with open( filtered_manifest_path, 'r' ) as input_manifest:
        # Parse header to find Phyloname column
        header_line = input_manifest.readline().strip()
        parts_header = header_line.split( '\t' )

        for index, column_header in enumerate( parts_header ):
            if 'Phyloname' in column_header and 'Taxonid' not in column_header:
                phyloname_column_index = index
                break

        if phyloname_column_index == -1:
            logger.error( "CRITICAL ERROR: No 'Phyloname' column found in manifest!" )
            logger.error( f"Columns found: {parts_header}" )
            sys.exit( 1 )

        # Read all phylonames (all entries in filtered manifest have Include=YES)
        for line in input_manifest:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )
            if len( parts ) > phyloname_column_index:
                phyloname = parts[ phyloname_column_index ]
                phylonames_to_include.append( phyloname )

    logger.info( f"Found {len( phylonames_to_include )} species to build BLAST databases" )
    logger.info( "" )

    # ========================================================================
    # BUILD DATABASES
    # ========================================================================

    logger.info( "Building per-genome BLAST databases..." )
    logger.info( "" )

    # Prepare jobs
    jobs_to_run = []
    makeblastdb_commands = []

    for phyloname in phylonames_to_include:
        proteome_filename = phyloname + '-proteome.aa'
        proteome_path = proteomes_directory / proteome_filename

        if not proteome_path.exists():
            logger.error( f"CRITICAL ERROR: Proteome file not found: {proteome_path}" )
            logger.error( f"Expected for phyloname: {phyloname}" )
            logger.error( "Check that STEP_2 completed successfully." )
            sys.exit( 1 )

        jobs_to_run.append( {
            'proteome_path': proteome_path,
            'phyloname': phyloname
        } )

    # Run makeblastdb in parallel
    successful_count = 0
    failed_count = 0
    results_list = []

    with ProcessPoolExecutor( max_workers = arguments.parallel ) as executor:
        future_to_job = {}

        for job in jobs_to_run:
            future = executor.submit(
                build_single_blastdb,
                proteome_path = job[ 'proteome_path' ],
                blastdb_dir = blastdb_directory,
                logger_name = 'build_per_genome_blastdbs'
            )
            future_to_job[ future ] = job

        for future in as_completed( future_to_job ):
            job = future_to_job[ future ]

            try:
                result = future.result()
                results_list.append( result )

                if result[ 'success' ]:
                    successful_count += 1
                    logger.info( f"  SUCCESS: {result[ 'phyloname' ]}" )
                    makeblastdb_commands.append( result.get( 'command', '' ) )
                else:
                    failed_count += 1
                    logger.error( f"  FAILED: {result[ 'phyloname' ]} - {result.get( 'error', 'Unknown error' )}" )

            except Exception as error:
                failed_count += 1
                logger.error( f"  FAILED: {job[ 'phyloname' ]} - Exception: {error}" )

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
    # COPY TO OUTPUT_TO_INPUT
    # ========================================================================

    logger.info( f"Copying BLAST databases to output_to_input: {output_to_input_blastdb}" )

    for item in blastdb_directory.iterdir():
        dest_path = output_to_input_blastdb / item.name
        if item.is_file():
            shutil.copy2( item, dest_path )

    logger.info( f"Copied {sum( 1 for _ in blastdb_directory.iterdir() )} files to output_to_input" )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Species processed: {len( phylonames_to_include )}" )
    logger.info( f"Successful builds: {successful_count}" )
    logger.info( f"Failed builds: {failed_count}" )
    logger.info( f"BLAST database directory: {blastdb_directory}" )
    logger.info( f"output_to_input: {output_to_input_blastdb}" )
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
