#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: Run BUSCO proteome completeness evaluation for all species
# Human: Eric Edsinger

"""
005_ai-python-run_busco_proteome_evaluation.py

Run BUSCO (Benchmarking Universal Single-Copy Orthologs) on all standardized proteomes
to assess proteome completeness. Users specify which BUSCO lineage databases to use
via a simple manifest file.

BUSCO evaluates how complete a proteome is by searching for conserved single-copy
orthologs expected to be present in all members of a taxonomic group.

Inputs:
    - Lineage manifest: Simple text file with one BUSCO lineage per line
      (e.g., metazoa_odb10, eukaryota_odb10)
    - Standardized proteomes from Script 001 output (OUTPUT_pipeline/1-output/gigantic_proteomes/)

Outputs:
    - Per-species BUSCO results in OUTPUT_pipeline/5-output/busco_results/
      Organized as: phyloname/lineage_name/busco_output_files
    - Summary TSV: OUTPUT_pipeline/5-output/5_ai-busco_summary.tsv
    - Processing log: OUTPUT_pipeline/5-output/5_ai-log-run_busco_proteome_evaluation.log

REQUIRES: BUSCO (install via: mamba install busco)
          conda activate ai_gigantic_genomesdb

Usage:
    conda activate ai_gigantic_genomesdb
    python3 005_ai-python-run_busco_proteome_evaluation.py \\
        --lineage-manifest INPUT_user/busco_lineages.txt \\
        --input-proteomes OUTPUT_pipeline/1-output/gigantic_proteomes \\
        --output-dir OUTPUT_pipeline/5-output
"""

import argparse
import sys
import os
import subprocess
import logging
import re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging( log_file_path: Path ) -> logging.Logger:
    """
    Configure logging to both file and console.
    """

    logger = logging.getLogger( 'run_busco_proteome_evaluation' )
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
# LINEAGE MANIFEST LOADING
# ============================================================================

def load_lineage_manifest( manifest_path: Path, logger: logging.Logger ) -> list:
    """
    Load BUSCO lineage names from a simple manifest file.

    Format: One lineage name per line (e.g., metazoa_odb10)
    Lines starting with # are comments.

    Args:
        manifest_path: Path to the lineage manifest file
        logger: Logger instance

    Returns:
        List of lineage names
    """

    logger.info( f"Loading lineage manifest from: {manifest_path}" )

    if not manifest_path.exists():
        logger.error( f"CRITICAL ERROR: Lineage manifest not found: {manifest_path}" )
        logger.error( "Create a file with one BUSCO lineage per line." )
        logger.error( "Example lineages: metazoa_odb10, eukaryota_odb10, fungi_odb10" )
        sys.exit( 1 )

    lineages = []

    with open( manifest_path, 'r' ) as input_manifest:
        for line in input_manifest:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith( '#' ):
                continue

            lineages.append( line )

    if not lineages:
        logger.error( "CRITICAL ERROR: No lineages found in manifest!" )
        logger.error( f"File: {manifest_path}" )
        logger.error( "Add at least one BUSCO lineage (e.g., metazoa_odb10)" )
        sys.exit( 1 )

    logger.info( f"Loaded {len( lineages )} lineage(s): {', '.join( lineages )}" )

    return lineages


# ============================================================================
# PHYLONAME EXTRACTION
# ============================================================================

def extract_phyloname_from_proteome_filename( filename: str ) -> str:
    """
    Extract phyloname from a standardized proteome filename.

    Filename format: phyloname-proteome.aa

    Args:
        filename: The proteome filename

    Returns:
        The phyloname string
    """

    if not filename.endswith( '-proteome.aa' ):
        raise ValueError( f"Unexpected filename format: {filename}" )

    phyloname = filename.replace( '-proteome.aa', '' )

    return phyloname


# ============================================================================
# BUSCO EXECUTION
# ============================================================================

def run_busco_single(
    proteome_path: Path,
    phyloname: str,
    lineage: str,
    output_base_dir: Path,
    cpus_per_job: int,
    logger_name: str
) -> dict:
    """
    Run BUSCO on a single proteome for a single lineage.

    Args:
        proteome_path: Path to the proteome FASTA file
        phyloname: The phyloname for this species
        lineage: BUSCO lineage database name
        output_base_dir: Base output directory for BUSCO results
        cpus_per_job: Number of CPUs to use for this BUSCO job
        logger_name: Name for subprocess logger

    Returns:
        Dictionary with BUSCO results summary
    """

    # Create output directory structure: phyloname/lineage/
    species_output_dir = output_base_dir / 'busco_results' / phyloname / lineage
    species_output_dir.mkdir( parents = True, exist_ok = True )

    # BUSCO run name (used for output subdirectory)
    run_name = f"busco_{lineage}"

    # Build BUSCO command
    # -m protein: proteome mode
    # -l lineage: BUSCO lineage database
    # -i input: input proteome file
    # -o output: output directory name
    # --out_path: parent directory for output
    # -c cpus: CPUs per job (parallelization at species level)

    busco_command = [
        'busco',
        '-m', 'protein',
        '-l', lineage,
        '-i', str( proteome_path ),
        '-o', run_name,
        '--out_path', str( species_output_dir ),
        '-c', str( cpus_per_job ),
        '--force',
        '--quiet'
    ]

    result = {
        'phyloname': phyloname,
        'lineage': lineage,
        'proteome_path': str( proteome_path ),
        'output_dir': str( species_output_dir / run_name ),
        'success': False,
        'complete_single': 0,
        'complete_duplicated': 0,
        'fragmented': 0,
        'missing': 0,
        'total': 0,
        'complete_percent': 0.0,
        'error_message': None
    }

    try:
        # Run BUSCO
        process = subprocess.run(
            busco_command,
            capture_output = True,
            text = True,
            timeout = 3600  # 1 hour timeout per species
        )

        if process.returncode != 0:
            result[ 'error_message' ] = process.stderr[:500] if process.stderr else "Unknown error"
            return result

        # Parse BUSCO short summary
        short_summary_path = species_output_dir / run_name / 'short_summary.specific.*.txt'

        # Find the actual summary file (filename includes lineage name)
        summary_files = list( ( species_output_dir / run_name ).glob( 'short_summary*.txt' ) )

        if summary_files:
            summary_path = summary_files[ 0 ]
            busco_stats = parse_busco_summary( summary_path )
            result.update( busco_stats )
            result[ 'success' ] = True
        else:
            result[ 'error_message' ] = "BUSCO summary file not found"

    except subprocess.TimeoutExpired:
        result[ 'error_message' ] = "BUSCO timed out (>1 hour)"
    except Exception as exception:
        result[ 'error_message' ] = str( exception )

    return result


def parse_busco_summary( summary_path: Path ) -> dict:
    """
    Parse BUSCO short summary file to extract statistics.

    Args:
        summary_path: Path to BUSCO short_summary.txt file

    Returns:
        Dictionary with BUSCO statistics
    """

    stats = {
        'complete_single': 0,
        'complete_duplicated': 0,
        'fragmented': 0,
        'missing': 0,
        'total': 0,
        'complete_percent': 0.0
    }

    with open( summary_path, 'r' ) as input_summary:
        content = input_summary.read()

        # Parse the summary line like:
        # C:95.2%[S:94.1%,D:1.1%],F:2.3%,M:2.5%,n:954

        # Complete and single-copy (S)
        match_single = re.search( r'(\d+)\s+Complete and single-copy BUSCOs \(S\)', content )
        if match_single:
            stats[ 'complete_single' ] = int( match_single.group( 1 ) )

        # Complete and duplicated (D)
        match_duplicated = re.search( r'(\d+)\s+Complete and duplicated BUSCOs \(D\)', content )
        if match_duplicated:
            stats[ 'complete_duplicated' ] = int( match_duplicated.group( 1 ) )

        # Fragmented (F)
        match_fragmented = re.search( r'(\d+)\s+Fragmented BUSCOs \(F\)', content )
        if match_fragmented:
            stats[ 'fragmented' ] = int( match_fragmented.group( 1 ) )

        # Missing (M)
        match_missing = re.search( r'(\d+)\s+Missing BUSCOs \(M\)', content )
        if match_missing:
            stats[ 'missing' ] = int( match_missing.group( 1 ) )

        # Total (n)
        match_total = re.search( r'(\d+)\s+Total BUSCO groups searched', content )
        if match_total:
            stats[ 'total' ] = int( match_total.group( 1 ) )

        # Calculate complete percentage
        if stats[ 'total' ] > 0:
            complete = stats[ 'complete_single' ] + stats[ 'complete_duplicated' ]
            stats[ 'complete_percent' ] = round( ( complete / stats[ 'total' ] ) * 100, 2 )

    return stats


# ============================================================================
# SUMMARY TABLE WRITING
# ============================================================================

def write_summary_table( summary_path: Path, results: list, lineages: list, logger: logging.Logger ) -> None:
    """
    Write BUSCO results summary to a TSV file.

    Args:
        summary_path: Output path for summary TSV
        results: List of result dictionaries from BUSCO runs
        lineages: List of lineage names used
        logger: Logger instance
    """

    logger.info( f"Writing BUSCO summary to: {summary_path}" )

    # Organize results by phyloname
    phylonames___results = {}

    for result in results:
        phyloname = result[ 'phyloname' ]
        lineage = result[ 'lineage' ]

        if phyloname not in phylonames___results:
            phylonames___results[ phyloname ] = {}

        phylonames___results[ phyloname ][ lineage ] = result

    with open( summary_path, 'w' ) as output_summary:
        # Build header with columns for each lineage
        header_parts = [ 'Phyloname (GIGANTIC phyloname for this species)' ]

        for lineage in lineages:
            header_parts.append( f'{lineage}_Complete_Percent (percentage of complete BUSCOs for {lineage})' )
            header_parts.append( f'{lineage}_Complete_Single (count of complete single-copy BUSCOs for {lineage})' )
            header_parts.append( f'{lineage}_Complete_Duplicated (count of complete duplicated BUSCOs for {lineage})' )
            header_parts.append( f'{lineage}_Fragmented (count of fragmented BUSCOs for {lineage})' )
            header_parts.append( f'{lineage}_Missing (count of missing BUSCOs for {lineage})' )
            header_parts.append( f'{lineage}_Total (total BUSCO groups searched for {lineage})' )
            header_parts.append( f'{lineage}_Status (success or error message for {lineage})' )

        output = '\t'.join( header_parts ) + '\n'
        output_summary.write( output )

        # Write data rows
        for phyloname in sorted( phylonames___results.keys() ):
            row_parts = [ phyloname ]

            for lineage in lineages:
                if lineage in phylonames___results[ phyloname ]:
                    result = phylonames___results[ phyloname ][ lineage ]

                    if result[ 'success' ]:
                        row_parts.append( str( result[ 'complete_percent' ] ) )
                        row_parts.append( str( result[ 'complete_single' ] ) )
                        row_parts.append( str( result[ 'complete_duplicated' ] ) )
                        row_parts.append( str( result[ 'fragmented' ] ) )
                        row_parts.append( str( result[ 'missing' ] ) )
                        row_parts.append( str( result[ 'total' ] ) )
                        row_parts.append( 'SUCCESS' )
                    else:
                        row_parts.extend( [ 'NA', 'NA', 'NA', 'NA', 'NA', 'NA' ] )
                        row_parts.append( f"ERROR: {result[ 'error_message' ]}" )
                else:
                    row_parts.extend( [ 'NA', 'NA', 'NA', 'NA', 'NA', 'NA', 'NOT_RUN' ] )

            output = '\t'.join( row_parts ) + '\n'
            output_summary.write( output )

    logger.info( f"Summary written with {len( phylonames___results )} species" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: orchestrate BUSCO evaluation for all proteomes.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Run BUSCO proteome completeness evaluation for all species.',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
    python3 005_ai-python-run_busco_proteome_evaluation.py \\
        --lineage-manifest INPUT_user/busco_lineages.txt \\
        --input-proteomes OUTPUT_pipeline/1-output/gigantic_proteomes \\
        --output-dir OUTPUT_pipeline/5-output

Lineage manifest format (one lineage per line):
    metazoa_odb10
    eukaryota_odb10
        """
    )

    parser.add_argument(
        '--lineage-manifest',
        type = str,
        required = True,
        help = 'Path to lineage manifest file (one BUSCO lineage per line)'
    )

    parser.add_argument(
        '--input-proteomes',
        type = str,
        required = True,
        help = 'Path to directory containing standardized proteome .aa files'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/5-output',
        help = 'Output directory (default: OUTPUT_pipeline/5-output)'
    )

    parser.add_argument(
        '--parallel',
        type = int,
        default = 4,
        help = 'Number of parallel BUSCO jobs (default: 4)'
    )

    parser.add_argument(
        '--cpus-per-job',
        type = int,
        default = 1,
        help = 'Number of CPUs per BUSCO job (default: 1)'
    )

    arguments = parser.parse_args()

    # ========================================================================
    # PATH SETUP
    # ========================================================================

    input_lineage_manifest_path = Path( arguments.lineage_manifest ).resolve()
    input_proteomes_directory = Path( arguments.input_proteomes ).resolve()
    output_base_directory = Path( arguments.output_dir )

    output_summary_path = output_base_directory / '5_ai-busco_summary.tsv'
    output_log_path = output_base_directory / '5_ai-log-run_busco_proteome_evaluation.log'

    # Create output directory
    output_base_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC BUSCO Proteome Evaluation" )
    logger.info( "Script: 005_ai-python-run_busco_proteome_evaluation.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Lineage manifest: {input_lineage_manifest_path}" )
    logger.info( f"Input proteomes directory: {input_proteomes_directory}" )
    logger.info( f"Output directory: {output_base_directory}" )
    logger.info( f"Parallel jobs: {arguments.parallel}" )
    logger.info( f"CPUs per job: {arguments.cpus_per_job}" )
    logger.info( f"Total CPUs used: {arguments.parallel * arguments.cpus_per_job}" )
    logger.info( "" )

    # ========================================================================
    # CHECK BUSCO AVAILABILITY
    # ========================================================================

    logger.info( "Checking BUSCO availability..." )

    try:
        busco_version = subprocess.run(
            [ 'busco', '--version' ],
            capture_output = True,
            text = True
        )
        if busco_version.returncode == 0:
            logger.info( f"BUSCO version: {busco_version.stdout.strip()}" )
        else:
            logger.error( "CRITICAL ERROR: BUSCO not found or not working!" )
            logger.error( "Install BUSCO: mamba install busco" )
            logger.error( "Activate environment: conda activate ai_gigantic_genomesdb" )
            sys.exit( 1 )
    except FileNotFoundError:
        logger.error( "CRITICAL ERROR: BUSCO command not found!" )
        logger.error( "Install BUSCO: mamba install busco" )
        sys.exit( 1 )

    logger.info( "" )

    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================

    if not input_proteomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Input proteomes directory not found: {input_proteomes_directory}" )
        logger.error( "Run Script 001 first to generate standardized proteomes." )
        sys.exit( 1 )

    proteome_files = sorted( input_proteomes_directory.glob( '*.aa' ) )

    if not proteome_files:
        logger.error( f"CRITICAL ERROR: No .aa files found in: {input_proteomes_directory}" )
        sys.exit( 1 )

    logger.info( f"Found {len( proteome_files )} proteome files to process" )
    logger.info( "" )

    # ========================================================================
    # LOAD LINEAGE MANIFEST
    # ========================================================================

    lineages = load_lineage_manifest( input_lineage_manifest_path, logger )
    logger.info( "" )

    # ========================================================================
    # RUN BUSCO FOR ALL PROTEOMES AND LINEAGES
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "RUNNING BUSCO EVALUATIONS" )
    logger.info( "=" * 80 )
    logger.info( f"Total jobs: {len( proteome_files )} proteomes x {len( lineages )} lineages = {len( proteome_files ) * len( lineages )}" )
    logger.info( "" )

    all_results = []
    total_jobs = len( proteome_files ) * len( lineages )

    # Build list of all jobs to run
    jobs_to_run = []
    for proteome_file in proteome_files:
        phyloname = extract_phyloname_from_proteome_filename( proteome_file.name )
        for lineage in lineages:
            jobs_to_run.append( {
                'proteome_path': proteome_file,
                'phyloname': phyloname,
                'lineage': lineage,
                'output_base_dir': output_base_directory,
                'cpus_per_job': arguments.cpus_per_job,
                'logger_name': 'busco_subprocess'
            } )

    # Run jobs in parallel using ProcessPoolExecutor
    logger.info( f"Starting parallel execution with {arguments.parallel} workers..." )
    logger.info( "" )

    jobs_completed = 0

    with ProcessPoolExecutor( max_workers = arguments.parallel ) as executor:
        # Submit all jobs
        future_to_job = {}
        for job in jobs_to_run:
            future = executor.submit(
                run_busco_single,
                proteome_path = job[ 'proteome_path' ],
                phyloname = job[ 'phyloname' ],
                lineage = job[ 'lineage' ],
                output_base_dir = job[ 'output_base_dir' ],
                cpus_per_job = job[ 'cpus_per_job' ],
                logger_name = job[ 'logger_name' ]
            )
            future_to_job[ future ] = job

        # Collect results as they complete
        for future in as_completed( future_to_job ):
            jobs_completed += 1
            job = future_to_job[ future ]

            try:
                result = future.result()
                all_results.append( result )

                if result[ 'success' ]:
                    logger.info( f"[{jobs_completed}/{total_jobs}] {result[ 'phyloname' ]} - {result[ 'lineage' ]}: Complete {result[ 'complete_percent' ]}% ({result[ 'complete_single' ]}S + {result[ 'complete_duplicated' ]}D)" )
                else:
                    logger.warning( f"[{jobs_completed}/{total_jobs}] {result[ 'phyloname' ]} - {result[ 'lineage' ]}: FAILED - {result[ 'error_message' ]}" )

            except Exception as exception:
                logger.error( f"[{jobs_completed}/{total_jobs}] {job[ 'phyloname' ]} - {job[ 'lineage' ]}: EXCEPTION - {str( exception )}" )
                all_results.append( {
                    'phyloname': job[ 'phyloname' ],
                    'lineage': job[ 'lineage' ],
                    'proteome_path': str( job[ 'proteome_path' ] ),
                    'output_dir': '',
                    'success': False,
                    'complete_single': 0,
                    'complete_duplicated': 0,
                    'fragmented': 0,
                    'missing': 0,
                    'total': 0,
                    'complete_percent': 0.0,
                    'error_message': str( exception )
                } )

    logger.info( "" )

    # ========================================================================
    # WRITE SUMMARY TABLE
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "WRITING SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( "" )

    write_summary_table( output_summary_path, all_results, lineages, logger )
    logger.info( "" )

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================

    successful_runs = sum( 1 for r in all_results if r[ 'success' ] )
    failed_runs = sum( 1 for r in all_results if not r[ 'success' ] )

    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Total BUSCO runs: {len( all_results )}" )
    logger.info( f"Successful: {successful_runs}" )
    logger.info( f"Failed: {failed_runs}" )
    logger.info( "" )
    logger.info( f"BUSCO results directory: {output_base_directory / 'busco_results'}" )
    logger.info( f"Summary table: {output_summary_path}" )
    logger.info( f"Log: {output_log_path}" )
    logger.info( "" )
    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )
    logger.info( "COMPLETE" )
    logger.info( "=" * 80 )

    print( "" )
    print( f"Done! Ran BUSCO on {len( proteome_files )} proteomes x {len( lineages )} lineages." )
    print( f"Successful: {successful_runs}, Failed: {failed_runs}" )
    print( f"Results: {output_base_directory / 'busco_results'}" )
    print( f"Summary: {output_summary_path}" )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()
