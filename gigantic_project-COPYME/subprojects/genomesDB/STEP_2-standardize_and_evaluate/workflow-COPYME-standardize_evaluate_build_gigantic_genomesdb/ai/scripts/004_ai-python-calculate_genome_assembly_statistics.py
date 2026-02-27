#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 13 20:00 | Purpose: Calculate genome assembly statistics using gfastats for all genome FASTAs
# Human: Eric Edsinger

"""
004_ai-python-calculate_genome_assembly_statistics.py

Calculate comprehensive assembly statistics for all genome FASTA files using gfastats,
the standard tool for genome assembly quality metrics.

For each genome, gfastats reports scaffold-level AND contig-level statistics:
    - Scaffold stats: treats each FASTA record as a scaffold
    - Contig stats: splits scaffolds at gap runs of N's
    - GC content: excludes N bases (matches NCBI convention)
    - Gap analysis: number and total length of gaps

This script wraps gfastats, adding GIGANTIC phyloname identifiers and combining
all per-genome results into a single summary TSV.

REQUIRES: gfastats (install via: mamba install gfastats)
          conda activate ai_gigantic_genomesdb

Inputs:
    - Directory of genome FASTA files (phyloname-named, from output_to_input/gigantic_genomes/)
      Filenames follow: phyloname-genome.fasta
    - Phylonames mapping TSV from phylonames subproject output_to_input/maps/
      Used for reverse lookup: phyloname -> genus_species

Outputs:
    - Assembly statistics TSV: OUTPUT_pipeline/4-output/4_ai-genome_assembly_statistics.tsv
    - Processing log: OUTPUT_pipeline/4-output/4_ai-log-calculate_genome_assembly_statistics.log

Usage:
    conda activate ai_gigantic_genomesdb
    python3 004_ai-python-calculate_genome_assembly_statistics.py \\
        --input-genomes PATH_TO_GIGANTIC_GENOMES_DIR \\
        --phylonames-mapping PATH_TO_MAPPING.tsv \\
        --output-dir OUTPUT_PIPELINE/4-output
"""

import argparse
import sys
import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


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

    logger = logging.getLogger( 'calculate_genome_assembly_statistics' )
    logger.setLevel( logging.DEBUG )

    # File handler - captures everything including DEBUG
    file_handler = logging.FileHandler( log_file_path, mode = 'w' )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s | %(levelname)-8s | %(message)s', datefmt = '%Y-%m-%d %H:%M:%S' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    # Console handler - INFO and above
    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(levelname)-8s | %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    return logger


# ============================================================================
# PHYLONAMES MAPPING (REVERSE LOOKUP)
# ============================================================================

def load_phylonames_mapping_reverse( mapping_file_path: Path, logger: logging.Logger ) -> dict:
    """
    Load the phylonames mapping TSV and build a reverse lookup: phyloname -> genus_species.

    The mapping file has self-documenting headers. We need columns:
    - genus_species (column 0)
    - phyloname (column 1)

    Args:
        mapping_file_path: Path to the phylonames mapping TSV
        logger: Logger instance

    Returns:
        Dictionary mapping phyloname to genus_species
    """

    logger.info( f"Loading phylonames mapping from: {mapping_file_path}" )

    if not mapping_file_path.exists():
        logger.error( f"CRITICAL ERROR: Phylonames mapping file not found: {mapping_file_path}" )
        logger.error( "The phylonames subproject must be run before STEP_2." )
        logger.error( "Expected location: phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv" )
        sys.exit( 1 )

    phylonames___genus_species = {}

    with open( mapping_file_path, 'r' ) as input_mapping:
        # genus_species (Genus_species or Genus_species_subspecies format)	phyloname (final phyloname with UNOFFICIAL markers where applicable)	phyloname_taxonid (phyloname with NCBI taxon ID suffix)	source (NCBI for auto-generated or USER for user-provided)	original_ncbi_phyloname (original NCBI-generated phyloname before user override)
        # Abeoforma_whisleri	HolozoaUNOFFICIAL_Phylum10927_Ichthyosporea_Ichthyophonida_Family10940_Abeoforma_whisleri	HolozoaUNOFFICIAL_Phylum10927_Ichthyosporea_Ichthyophonida_Family10940_Abeoforma_whisleri___749232	USER	Kingdom10928_Phylum10927_Ichthyosporea_Ichthyophonida_Family10940_Abeoforma_whisleri
        header_line = input_mapping.readline()

        for line in input_mapping:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )
            if len( parts ) < 2:
                logger.warning( f"Skipping malformed line (fewer than 2 columns): {line}" )
                continue

            genus_species = parts[ 0 ]
            phyloname = parts[ 1 ]

            phylonames___genus_species[ phyloname ] = genus_species

    species_count = len( phylonames___genus_species )
    logger.info( f"Loaded reverse phylonames mapping for {species_count} species" )

    if species_count == 0:
        logger.error( "CRITICAL ERROR: No species found in phylonames mapping file!" )
        logger.error( f"File: {mapping_file_path}" )
        logger.error( "Check that the file is not empty and has the correct format." )
        sys.exit( 1 )

    return phylonames___genus_species


# ============================================================================
# PHYLONAME EXTRACTION FROM FILENAME
# ============================================================================

def extract_phyloname_from_filename( filename: str, logger: logging.Logger ) -> str:
    """
    Extract phyloname from a GIGANTIC genome filename.

    Filenames follow the pattern:
        phyloname-genome.fasta

    The phyloname is everything before '-genome.fasta'.

    Args:
        filename: The genome filename (not full path)
        logger: Logger instance

    Returns:
        The phyloname string

    Raises:
        SystemExit if filename cannot be parsed
    """

    if not filename.endswith( '-genome.fasta' ):
        logger.error( f"CRITICAL ERROR: Cannot parse phyloname from filename: {filename}" )
        logger.error( "Expected pattern: phyloname-genome.fasta" )
        sys.exit( 1 )

    phyloname = filename[ : -len( '-genome.fasta' ) ]

    return phyloname


# ============================================================================
# GFASTATS EXECUTION AND PARSING
# ============================================================================

def run_gfastats( fasta_file_path: Path, logger: logging.Logger ) -> dict:
    """
    Run gfastats on a single genome FASTA file and parse its tabular output.

    gfastats reports both scaffold-level and contig-level statistics.
    Scaffold = each FASTA record. Contig = sequences split at gap runs of N's.

    Args:
        fasta_file_path: Path to the genome FASTA file
        logger: Logger instance

    Returns:
        Dictionary with parsed gfastats metrics

    Raises:
        SystemExit if gfastats fails or is not found
    """

    command = [
        'gfastats',
        str( fasta_file_path ),
        '--tabular',
        '--nstar-report'
    ]

    logger.debug( f"  Running: {' '.join( command )}" )

    try:
        result = subprocess.run(
            command,
            capture_output = True,
            text = True
        )
    except FileNotFoundError:
        logger.error( "CRITICAL ERROR: gfastats not found!" )
        logger.error( "Install gfastats: mamba install gfastats" )
        logger.error( "Or activate the environment: conda activate ai_gigantic_genomesdb" )
        sys.exit( 1 )

    if result.returncode != 0:
        logger.error( f"CRITICAL ERROR: gfastats failed on: {fasta_file_path}" )
        logger.error( f"Return code: {result.returncode}" )
        logger.error( f"stderr: {result.stderr}" )
        sys.exit( 1 )

    # Parse the tabular output (label\tvalue format)
    gfastats_metrics = {}

    for line in result.stdout.strip().split( '\n' ):
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )
        if len( parts ) >= 2:
            label = parts[ 0 ].strip()
            value = parts[ 1 ].strip()
            gfastats_metrics[ label ] = value

    # Extract the metrics we need
    parsed_statistics = {
        'scaffold_count': int( gfastats_metrics.get( '# scaffolds', '0' ) ),
        'total_scaffold_length': int( gfastats_metrics.get( 'Total scaffold length', '0' ) ),
        'scaffold_n50': int( gfastats_metrics.get( 'Scaffold N50', '0' ) ),
        'scaffold_l50': int( gfastats_metrics.get( 'Scaffold L50', '0' ) ),
        'scaffold_n90': int( gfastats_metrics.get( 'Scaffold N90', '0' ) ),
        'scaffold_l90': int( gfastats_metrics.get( 'Scaffold L90', '0' ) ),
        'largest_scaffold': int( gfastats_metrics.get( 'Largest scaffold', '0' ) ),
        'smallest_scaffold': int( gfastats_metrics.get( 'Smallest scaffold', '0' ) ),
        'contig_count': int( gfastats_metrics.get( '# contigs', '0' ) ),
        'total_contig_length': int( gfastats_metrics.get( 'Total contig length', '0' ) ),
        'contig_n50': int( gfastats_metrics.get( 'Contig N50', '0' ) ),
        'contig_l50': int( gfastats_metrics.get( 'Contig L50', '0' ) ),
        'contig_n90': int( gfastats_metrics.get( 'Contig N90', '0' ) ),
        'contig_l90': int( gfastats_metrics.get( 'Contig L90', '0' ) ),
        'largest_contig': int( gfastats_metrics.get( 'Largest contig', '0' ) ),
        'smallest_contig': int( gfastats_metrics.get( 'Smallest contig', '0' ) ),
        'gap_count': int( gfastats_metrics.get( '# gaps in scaffolds', '0' ) ),
        'total_gap_length': int( gfastats_metrics.get( 'Total gap length in scaffolds', '0' ) ),
        'gc_content_percent': float( gfastats_metrics.get( 'GC content %', '0' ) )
    }

    return parsed_statistics


# ============================================================================
# RESULTS TSV WRITING
# ============================================================================

def write_results_tsv(
    output_tsv_path: Path,
    results_entries: list,
    logger: logging.Logger
) -> None:
    """
    Write the assembly statistics results to a TSV file with self-documenting headers.

    Args:
        output_tsv_path: Output path for the TSV file
        results_entries: List of dictionaries with result data
        logger: Logger instance
    """

    logger.info( f"Writing results TSV to: {output_tsv_path}" )

    with open( output_tsv_path, 'w' ) as output_tsv:
        # Write self-documenting header
        output = (
            'Phyloname (phyloname from phylonames mapping for this species)\t'
            'Genus_Species (species identifier looked up from phylonames mapping)\t'
            'Assembly_Identifier (full GIGANTIC genome filename without extension)\t'
            'Scaffold_Count (number of sequences or scaffolds in FASTA file)\t'
            'Total_Scaffold_Length_Basepairs (total base pairs including gaps)\t'
            'Scaffold_N50_Basepairs (scaffold length at 50 percent of total scaffold length)\t'
            'Scaffold_L50_Count (number of scaffolds needed to reach 50 percent of total scaffold length)\t'
            'Scaffold_N90_Basepairs (scaffold length at 90 percent of total scaffold length)\t'
            'Scaffold_L90_Count (number of scaffolds needed to reach 90 percent of total scaffold length)\t'
            'Largest_Scaffold_Basepairs (length of longest scaffold)\t'
            'Smallest_Scaffold_Basepairs (length of shortest scaffold)\t'
            'Contig_Count (number of contigs after splitting scaffolds at gap runs of N bases)\t'
            'Total_Contig_Length_Basepairs (total base pairs excluding gaps)\t'
            'Contig_N50_Basepairs (contig length at 50 percent of total contig length)\t'
            'Contig_L50_Count (number of contigs needed to reach 50 percent of total contig length)\t'
            'Contig_N90_Basepairs (contig length at 90 percent of total contig length)\t'
            'Contig_L90_Count (number of contigs needed to reach 90 percent of total contig length)\t'
            'Largest_Contig_Basepairs (length of longest contig)\t'
            'Smallest_Contig_Basepairs (length of shortest contig)\t'
            'Gap_Count (number of gap runs of N bases in scaffolds)\t'
            'Total_Gap_Length_Basepairs (total N bases representing assembly gaps)\t'
            'GC_Content_Percent (percentage of G plus C bases excluding N gap bases)\n'
        )
        output_tsv.write( output )

        for entry in results_entries:
            output = (
                entry[ 'phyloname' ] + '\t'
                + entry[ 'genus_species' ] + '\t'
                + entry[ 'assembly_identifier' ] + '\t'
                + str( entry[ 'scaffold_count' ] ) + '\t'
                + str( entry[ 'total_scaffold_length' ] ) + '\t'
                + str( entry[ 'scaffold_n50' ] ) + '\t'
                + str( entry[ 'scaffold_l50' ] ) + '\t'
                + str( entry[ 'scaffold_n90' ] ) + '\t'
                + str( entry[ 'scaffold_l90' ] ) + '\t'
                + str( entry[ 'largest_scaffold' ] ) + '\t'
                + str( entry[ 'smallest_scaffold' ] ) + '\t'
                + str( entry[ 'contig_count' ] ) + '\t'
                + str( entry[ 'total_contig_length' ] ) + '\t'
                + str( entry[ 'contig_n50' ] ) + '\t'
                + str( entry[ 'contig_l50' ] ) + '\t'
                + str( entry[ 'contig_n90' ] ) + '\t'
                + str( entry[ 'contig_l90' ] ) + '\t'
                + str( entry[ 'largest_contig' ] ) + '\t'
                + str( entry[ 'smallest_contig' ] ) + '\t'
                + str( entry[ 'gap_count' ] ) + '\t'
                + str( entry[ 'total_gap_length' ] ) + '\t'
                + str( entry[ 'gc_content_percent' ] ) + '\n'
            )
            output_tsv.write( output )

    logger.info( f"Results TSV written with {len( results_entries )} entries" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: orchestrate genome assembly statistics calculation via gfastats.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Calculate genome assembly statistics using gfastats for all genome FASTA files.',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
    # Basic usage
    python3 004_ai-python-calculate_genome_assembly_statistics.py \\
        --input-genomes ../output_to_input/gigantic_genomes \\
        --phylonames-mapping ../../../phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv

    # Custom output directory
    python3 004_ai-python-calculate_genome_assembly_statistics.py \\
        --input-genomes /path/to/genomes \\
        --phylonames-mapping /path/to/mapping.tsv \\
        --output-dir /path/to/output

Notes:
    REQUIRES gfastats to be installed and in PATH.
    Install: mamba install gfastats (from bioconda)
    Activate: conda activate ai_gigantic_genomesdb

    gfastats reports both scaffold-level and contig-level statistics:
    - Scaffold = each FASTA record as-is
    - Contig = sequences split at gap runs of N's
    - GC content excludes N bases (matches NCBI convention)
        """
    )

    parser.add_argument(
        '--input-genomes',
        type = str,
        required = True,
        help = 'Path to directory containing phyloname-named genome .fasta files'
    )

    parser.add_argument(
        '--phylonames-mapping',
        type = str,
        required = True,
        help = 'Path to phylonames mapping TSV (for reverse lookup: phyloname -> genus_species)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/4-output',
        help = 'Base output directory (default: OUTPUT_pipeline/4-output)'
    )

    parser.add_argument(
        '--threads',
        type = int,
        default = 8,
        help = 'Number of parallel gfastats processes (default: 8)'
    )

    arguments = parser.parse_args()

    # ========================================================================
    # PATH SETUP
    # ========================================================================

    input_genomes_directory = Path( arguments.input_genomes ).resolve()
    input_phylonames_mapping_path = Path( arguments.phylonames_mapping ).resolve()
    output_base_directory = Path( arguments.output_dir )

    output_tsv_path = output_base_directory / '4_ai-genome_assembly_statistics.tsv'
    output_log_path = output_base_directory / '4_ai-log-calculate_genome_assembly_statistics.log'

    # Create output directory
    output_base_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC Genome Assembly Statistics (via gfastats)" )
    logger.info( "Script: 004_ai-python-calculate_genome_assembly_statistics.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Input genomes directory: {input_genomes_directory}" )
    logger.info( f"Phylonames mapping: {input_phylonames_mapping_path}" )
    logger.info( f"Output TSV: {output_tsv_path}" )
    logger.info( f"Log output: {output_log_path}" )
    logger.info( "" )

    # ========================================================================
    # VERIFY GFASTATS IS AVAILABLE
    # ========================================================================

    try:
        version_result = subprocess.run(
            [ 'gfastats', '--version' ],
            capture_output = True,
            text = True,
            timeout = 10
        )
        gfastats_version = version_result.stdout.strip().split( '\n' )[ 0 ]
        logger.info( f"Using: {gfastats_version}" )
    except FileNotFoundError:
        logger.error( "CRITICAL ERROR: gfastats not found in PATH!" )
        logger.error( "Install gfastats: mamba install gfastats (from bioconda)" )
        logger.error( "Or activate the environment: conda activate ai_gigantic_genomesdb" )
        sys.exit( 1 )

    logger.info( "" )

    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================

    if not input_genomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Input genomes directory not found: {input_genomes_directory}" )
        logger.error( "Run script 002 (genome phyloname standardization) before this script." )
        sys.exit( 1 )

    genome_files = sorted( input_genomes_directory.glob( '*.fasta' ) )

    if not genome_files:
        logger.error( f"CRITICAL ERROR: No .fasta files found in: {input_genomes_directory}" )
        logger.error( "Expected phyloname-named genome files (e.g., phyloname-genome.fasta)." )
        sys.exit( 1 )

    logger.info( f"Found {len( genome_files )} genome files to process" )
    logger.info( "" )

    # ========================================================================
    # LOAD PHYLONAMES MAPPING (REVERSE)
    # ========================================================================

    phylonames___genus_species = load_phylonames_mapping_reverse( input_phylonames_mapping_path, logger )
    logger.info( "" )

    # ========================================================================
    # VALIDATE PHYLONAME LOOKUPS BEFORE PROCESSING
    # ========================================================================

    genome_tasks = []

    for genome_file in genome_files:
        filename = genome_file.name
        phyloname = extract_phyloname_from_filename( filename, logger )

        if phyloname not in phylonames___genus_species:
            logger.error( f"CRITICAL ERROR: phyloname '{phyloname}' not found in phylonames mapping!" )
            logger.error( f"Source file: {filename}" )
            logger.error( "Check that the phylonames mapping includes this species." )
            sys.exit( 1 )

        genus_species = phylonames___genus_species[ phyloname ]
        assembly_identifier = filename[ : -len( '.fasta' ) ]

        genome_tasks.append( {
            'genome_file': genome_file,
            'phyloname': phyloname,
            'genus_species': genus_species,
            'assembly_identifier': assembly_identifier
        } )

    # ========================================================================
    # PROCESS GENOMES IN PARALLEL
    # ========================================================================

    thread_count = arguments.threads
    logger.info( "=" * 80 )
    logger.info( f"CALCULATING ASSEMBLY STATISTICS ({thread_count} parallel threads)" )
    logger.info( "=" * 80 )
    logger.info( "" )

    results_entries = []
    completed_count = 0
    total_count = len( genome_tasks )

    def process_single_genome( task: dict ) -> dict:
        """Run gfastats on a single genome and return the combined result entry."""
        assembly_statistics = run_gfastats( task[ 'genome_file' ], logger )
        entry = {
            'phyloname': task[ 'phyloname' ],
            'genus_species': task[ 'genus_species' ],
            'assembly_identifier': task[ 'assembly_identifier' ],
            'scaffold_count': assembly_statistics[ 'scaffold_count' ],
            'total_scaffold_length': assembly_statistics[ 'total_scaffold_length' ],
            'scaffold_n50': assembly_statistics[ 'scaffold_n50' ],
            'scaffold_l50': assembly_statistics[ 'scaffold_l50' ],
            'scaffold_n90': assembly_statistics[ 'scaffold_n90' ],
            'scaffold_l90': assembly_statistics[ 'scaffold_l90' ],
            'largest_scaffold': assembly_statistics[ 'largest_scaffold' ],
            'smallest_scaffold': assembly_statistics[ 'smallest_scaffold' ],
            'contig_count': assembly_statistics[ 'contig_count' ],
            'total_contig_length': assembly_statistics[ 'total_contig_length' ],
            'contig_n50': assembly_statistics[ 'contig_n50' ],
            'contig_l50': assembly_statistics[ 'contig_l50' ],
            'contig_n90': assembly_statistics[ 'contig_n90' ],
            'contig_l90': assembly_statistics[ 'contig_l90' ],
            'largest_contig': assembly_statistics[ 'largest_contig' ],
            'smallest_contig': assembly_statistics[ 'smallest_contig' ],
            'gap_count': assembly_statistics[ 'gap_count' ],
            'total_gap_length': assembly_statistics[ 'total_gap_length' ],
            'gc_content_percent': assembly_statistics[ 'gc_content_percent' ]
        }
        return entry

    with ThreadPoolExecutor( max_workers = thread_count ) as executor:
        future_to_task = {
            executor.submit( process_single_genome, task ): task
            for task in genome_tasks
        }

        for future in as_completed( future_to_task ):
            task = future_to_task[ future ]
            completed_count += 1

            try:
                entry = future.result()
                results_entries.append( entry )

                logger.info(
                    f"[{completed_count}/{total_count}] {task[ 'genus_species' ]}: "
                    f"scaffolds={entry[ 'scaffold_count' ]}, "
                    f"scaffold_N50={entry[ 'scaffold_n50' ]:,}, "
                    f"contigs={entry[ 'contig_count' ]}, "
                    f"contig_N50={entry[ 'contig_n50' ]:,}, "
                    f"GC={entry[ 'gc_content_percent' ]}%"
                )

            except Exception as error:
                logger.error( f"CRITICAL ERROR processing {task[ 'genus_species' ]}: {error}" )
                sys.exit( 1 )

    # Sort results by phyloname for consistent output
    results_entries.sort( key = lambda entry: entry[ 'phyloname' ] )

    logger.info( "" )

    # ========================================================================
    # WRITE RESULTS TSV
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "WRITING RESULTS" )
    logger.info( "=" * 80 )
    logger.info( "" )

    write_results_tsv( output_tsv_path, results_entries, logger )
    logger.info( "" )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Genomes processed: {len( results_entries )}" )
    logger.info( f"Output TSV: {output_tsv_path}" )
    logger.info( f"Log: {output_log_path}" )
    logger.info( "" )

    # Summary statistics across all genomes
    if results_entries:
        all_scaffold_sizes = [ entry[ 'total_scaffold_length' ] for entry in results_entries ]
        all_contig_n50_values = [ entry[ 'contig_n50' ] for entry in results_entries ]
        all_scaffold_n50_values = [ entry[ 'scaffold_n50' ] for entry in results_entries ]

        logger.info( "Across all genomes:" )
        logger.info( f"  Total scaffold sizes: {min( all_scaffold_sizes ):,} - {max( all_scaffold_sizes ):,} bp" )
        logger.info( f"  Scaffold N50 range: {min( all_scaffold_n50_values ):,} - {max( all_scaffold_n50_values ):,} bp" )
        logger.info( f"  Contig N50 range: {min( all_contig_n50_values ):,} - {max( all_contig_n50_values ):,} bp" )
        logger.info( "" )

    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )
    logger.info( "COMPLETE" )
    logger.info( "=" * 80 )

    print( "" )
    print( f"Done! Processed {len( results_entries )} genomes." )
    print( f"Results TSV: {output_tsv_path}" )
    print( f"Log: {output_log_path}" )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()
