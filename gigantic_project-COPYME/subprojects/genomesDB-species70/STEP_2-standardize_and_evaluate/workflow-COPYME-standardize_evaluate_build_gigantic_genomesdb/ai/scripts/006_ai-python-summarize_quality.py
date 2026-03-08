#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 06 | Purpose: Summarize genome quality metrics into comprehensive quality summary
# Human: Eric Edsinger

"""
006_ai-python-summarize_quality.py

Combine genome assembly statistics (Script 004) and BUSCO results (Script 005)
into a comprehensive quality summary table.

Species selection is handled by STEP_4, not here.

Inputs:
    - Genome assembly statistics from Script 004 (OUTPUT_pipeline/4-output/4_ai-genome_assembly_statistics.tsv)
    - BUSCO summary from Script 005 (OUTPUT_pipeline/5-output/5_ai-busco_summary.tsv)
    - Proteome standardization manifest from Script 001 (for species without genomes)

Outputs:
    - Comprehensive quality summary: OUTPUT_pipeline/6-output/6_ai-comprehensive_quality_summary.tsv
    - Processing log: OUTPUT_pipeline/6-output/6_ai-log-summarize_quality.log

Usage:
    python3 006_ai-python-summarize_quality.py \\
        --assembly-stats OUTPUT_pipeline/4-output/4_ai-genome_assembly_statistics.tsv \\
        --busco-summary OUTPUT_pipeline/5-output/5_ai-busco_summary.tsv \\
        --proteome-manifest OUTPUT_pipeline/1-output/1_ai-standardization_manifest.tsv \\
        --output-dir OUTPUT_pipeline/6-output
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging( log_file_path: Path ) -> logging.Logger:
    """
    Configure logging to both file and console.
    """

    logger = logging.getLogger( 'summarize_quality' )
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
# DATA LOADING
# ============================================================================

def load_assembly_stats( stats_path: Path, logger: logging.Logger ) -> dict:
    """
    Load genome assembly statistics from Script 003 output.

    Args:
        stats_path: Path to 4_ai-genome_assembly_statistics.tsv
        logger: Logger instance

    Returns:
        Dictionary mapping phyloname to stats dictionary
    """

    logger.info( f"Loading assembly statistics from: {stats_path}" )

    if not stats_path.exists():
        logger.warning( f"Assembly statistics file not found: {stats_path}" )
        logger.warning( "Proceeding without assembly statistics (N50 columns will be NA)" )
        return {}

    phylonames___stats = {}

    with open( stats_path, 'r' ) as input_stats:
        # Read header to get column names
        header_line = input_stats.readline().strip()
        header_parts = header_line.split( '\t' )

        # Find column indices for key metrics
        # Column names have self-documenting format: Name (description)
        column_indices = {}
        for index, header in enumerate( header_parts ):
            # Extract the column name before the parenthesis
            column_name = header.split( ' (' )[ 0 ]
            column_indices[ column_name ] = index

        for line in input_stats:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            phyloname = parts[ 0 ]

            # Extract key metrics
            stats = {
                'genus_species': parts[ column_indices.get( 'Genus_Species', 1 ) ] if 'Genus_Species' in column_indices else 'NA',
                'scaffold_count': parts[ column_indices.get( 'Scaffold_Count', 3 ) ] if 'Scaffold_Count' in column_indices else 'NA',
                'total_scaffold_length': parts[ column_indices.get( 'Total_Scaffold_Length_Basepairs', 4 ) ] if 'Total_Scaffold_Length_Basepairs' in column_indices else 'NA',
                'scaffold_n50': parts[ column_indices.get( 'Scaffold_N50_Basepairs', 5 ) ] if 'Scaffold_N50_Basepairs' in column_indices else 'NA',
                'contig_n50': parts[ column_indices.get( 'Contig_N50_Basepairs', 13 ) ] if 'Contig_N50_Basepairs' in column_indices else 'NA',
                'gc_content': parts[ column_indices.get( 'GC_Content_Percent', -1 ) ] if 'GC_Content_Percent' in column_indices else 'NA'
            }

            phylonames___stats[ phyloname ] = stats

    logger.info( f"Loaded assembly statistics for {len( phylonames___stats )} species" )

    return phylonames___stats


def load_busco_summary( summary_path: Path, logger: logging.Logger ) -> tuple:
    """
    Load BUSCO summary from Script 004 output.

    Args:
        summary_path: Path to 5_ai-busco_summary.tsv
        logger: Logger instance

    Returns:
        Tuple of (phylonames___busco_stats, lineage_names)
    """

    logger.info( f"Loading BUSCO summary from: {summary_path}" )

    if not summary_path.exists():
        logger.warning( f"BUSCO summary file not found: {summary_path}" )
        logger.warning( "Proceeding without BUSCO statistics (BUSCO columns will be NA)" )
        return {}, []

    phylonames___busco_stats = {}
    lineage_names = []

    with open( summary_path, 'r' ) as input_summary:
        # Read header to identify lineages
        header_line = input_summary.readline().strip()
        header_parts = header_line.split( '\t' )

        # Extract lineage names from column headers
        # Format: lineage_Complete_Percent (description)
        for header in header_parts[ 1: ]:
            if '_Complete_Percent' in header:
                lineage = header.split( '_Complete_Percent' )[ 0 ]
                if lineage not in lineage_names:
                    lineage_names.append( lineage )

        logger.info( f"Found {len( lineage_names )} BUSCO lineage(s): {', '.join( lineage_names )}" )

        # Build column index map for each lineage
        lineage_column_indices = {}
        for lineage in lineage_names:
            for index, header in enumerate( header_parts ):
                if header.startswith( f'{lineage}_Complete_Percent' ):
                    lineage_column_indices[ lineage ] = index
                    break

        for line in input_summary:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            phyloname = parts[ 0 ]

            busco_stats = {}
            for lineage in lineage_names:
                col_index = lineage_column_indices.get( lineage )
                if col_index and col_index < len( parts ):
                    busco_stats[ lineage ] = parts[ col_index ]
                else:
                    busco_stats[ lineage ] = 'NA'

            phylonames___busco_stats[ phyloname ] = busco_stats

    logger.info( f"Loaded BUSCO statistics for {len( phylonames___busco_stats )} species" )

    return phylonames___busco_stats, lineage_names


def load_proteome_manifest( manifest_path: Path, logger: logging.Logger ) -> dict:
    """
    Load proteome standardization manifest from Script 001 output.
    This ensures we have all species even if they don't have genomes.

    Args:
        manifest_path: Path to 1_ai-standardization_manifest.tsv
        logger: Logger instance

    Returns:
        Dictionary mapping phyloname to species info
    """

    logger.info( f"Loading proteome manifest from: {manifest_path}" )

    if not manifest_path.exists():
        logger.error( f"CRITICAL ERROR: Proteome manifest not found: {manifest_path}" )
        logger.error( "Script 001 must be run first." )
        sys.exit( 1 )

    phylonames___species_info = {}

    with open( manifest_path, 'r' ) as input_manifest:
        # Skip header
        header_line = input_manifest.readline()

        # Genus_Species	Phyloname	Phyloname_Taxonid	Source_Filename	Output_Filename	Sequence_Count
        for line in input_manifest:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            genus_species = parts[ 0 ]
            phyloname = parts[ 1 ]
            sequence_count = parts[ 5 ] if len( parts ) > 5 else 'NA'

            phylonames___species_info[ phyloname ] = {
                'genus_species': genus_species,
                'sequence_count': sequence_count
            }

    logger.info( f"Loaded proteome info for {len( phylonames___species_info )} species" )

    return phylonames___species_info


# ============================================================================
# OUTPUT WRITING
# ============================================================================

def write_comprehensive_summary(
    summary_path: Path,
    phylonames___species_info: dict,
    phylonames___assembly_stats: dict,
    phylonames___busco_stats: dict,
    lineage_names: list,
    logger: logging.Logger
) -> None:
    """
    Write comprehensive quality summary combining all metrics.

    Args:
        summary_path: Output path for summary TSV
        phylonames___species_info: Species info from proteome manifest
        phylonames___assembly_stats: Assembly statistics
        phylonames___busco_stats: BUSCO statistics
        lineage_names: List of BUSCO lineage names
        logger: Logger instance
    """

    logger.info( f"Writing comprehensive quality summary to: {summary_path}" )

    with open( summary_path, 'w' ) as output_summary:
        # Build header
        header_parts = [
            'Phyloname (GIGANTIC phyloname for this species)',
            'Genus_Species (binomial species name)',
            'Proteome_Sequence_Count (number of protein sequences)',
            'Has_Genome (whether genome assembly is available YES or NO)',
            'Scaffold_Count (number of scaffolds in genome assembly)',
            'Total_Assembly_Size_Bp (total base pairs in assembly)',
            'Scaffold_N50_Bp (scaffold N50 in base pairs)',
            'Contig_N50_Bp (contig N50 in base pairs)',
            'GC_Content_Percent (GC percentage of assembly)'
        ]

        # Add BUSCO columns for each lineage
        for lineage in lineage_names:
            header_parts.append( f'BUSCO_{lineage}_Complete_Percent (percentage of complete BUSCOs for {lineage})' )

        output = '\t'.join( header_parts ) + '\n'
        output_summary.write( output )

        # Write data rows for all species
        for phyloname in sorted( phylonames___species_info.keys() ):
            species_info = phylonames___species_info[ phyloname ]
            assembly_stats = phylonames___assembly_stats.get( phyloname, {} )
            busco_stats = phylonames___busco_stats.get( phyloname, {} )

            has_genome = 'YES' if phyloname in phylonames___assembly_stats else 'NO'

            row_parts = [
                phyloname,
                species_info.get( 'genus_species', 'NA' ),
                species_info.get( 'sequence_count', 'NA' ),
                has_genome,
                assembly_stats.get( 'scaffold_count', 'NA' ),
                assembly_stats.get( 'total_scaffold_length', 'NA' ),
                assembly_stats.get( 'scaffold_n50', 'NA' ),
                assembly_stats.get( 'contig_n50', 'NA' ),
                assembly_stats.get( 'gc_content', 'NA' )
            ]

            # Add BUSCO values
            for lineage in lineage_names:
                row_parts.append( busco_stats.get( lineage, 'NA' ) )

            output = '\t'.join( row_parts ) + '\n'
            output_summary.write( output )

    logger.info( f"Summary written with {len( phylonames___species_info )} species" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: combine quality metrics and generate species manifest.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Summarize genome quality metrics into comprehensive quality summary.',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
    python3 006_ai-python-summarize_quality.py \\
        --assembly-stats OUTPUT_pipeline/4-output/4_ai-genome_assembly_statistics.tsv \\
        --busco-summary OUTPUT_pipeline/5-output/5_ai-busco_summary.tsv \\
        --proteome-manifest OUTPUT_pipeline/1-output/1_ai-standardization_manifest.tsv \\
        --output-dir OUTPUT_pipeline/6-output
        """
    )

    parser.add_argument(
        '--assembly-stats',
        type = str,
        required = True,
        help = 'Path to genome assembly statistics TSV from Script 003'
    )

    parser.add_argument(
        '--busco-summary',
        type = str,
        required = True,
        help = 'Path to BUSCO summary TSV from Script 004'
    )

    parser.add_argument(
        '--proteome-manifest',
        type = str,
        required = True,
        help = 'Path to proteome standardization manifest from Script 001'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/6-output',
        help = 'Output directory for quality summary (default: OUTPUT_pipeline/6-output)'
    )

    arguments = parser.parse_args()

    # ========================================================================
    # PATH SETUP
    # ========================================================================

    input_assembly_stats_path = Path( arguments.assembly_stats )
    input_busco_summary_path = Path( arguments.busco_summary )
    input_proteome_manifest_path = Path( arguments.proteome_manifest )
    output_base_directory = Path( arguments.output_dir )

    output_summary_path = output_base_directory / '6_ai-comprehensive_quality_summary.tsv'
    output_log_path = output_base_directory / '6_ai-log-summarize_quality.log'

    # Create output directory
    output_base_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC Quality Summary" )
    logger.info( "Script: 006_ai-python-summarize_quality.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Assembly stats input: {input_assembly_stats_path}" )
    logger.info( f"BUSCO summary input: {input_busco_summary_path}" )
    logger.info( f"Proteome manifest input: {input_proteome_manifest_path}" )
    logger.info( f"Quality summary output: {output_summary_path}" )
    logger.info( "" )

    # ========================================================================
    # LOAD DATA
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "LOADING DATA" )
    logger.info( "=" * 80 )
    logger.info( "" )

    # Load proteome manifest (required - this defines all species)
    phylonames___species_info = load_proteome_manifest( input_proteome_manifest_path, logger )

    # Load assembly statistics (optional - not all species have genomes)
    phylonames___assembly_stats = load_assembly_stats( input_assembly_stats_path, logger )

    # Load BUSCO summary (optional - may not have been run yet)
    phylonames___busco_stats, lineage_names = load_busco_summary( input_busco_summary_path, logger )

    logger.info( "" )

    # ========================================================================
    # DIAGNOSTIC: VERIFY KEY MATCHING
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "DIAGNOSTIC: KEY MATCHING BETWEEN DATA SOURCES" )
    logger.info( "=" * 80 )
    logger.info( "" )

    species_with_busco_match = 0
    species_without_busco_match = 0
    unmatched_busco_phylonames = []

    for phyloname in phylonames___species_info.keys():
        if phyloname in phylonames___busco_stats:
            species_with_busco_match += 1
        else:
            species_without_busco_match += 1

    for busco_phyloname in phylonames___busco_stats.keys():
        if busco_phyloname not in phylonames___species_info:
            unmatched_busco_phylonames.append( busco_phyloname )

    logger.info( f"Species in proteome manifest: {len( phylonames___species_info )}" )
    logger.info( f"Species with BUSCO data match: {species_with_busco_match}" )
    logger.info( f"Species WITHOUT BUSCO data match: {species_without_busco_match}" )

    if unmatched_busco_phylonames:
        logger.warning( f"BUSCO phylonames not found in proteome manifest: {len( unmatched_busco_phylonames )}" )
        for unmatched_phyloname in sorted( unmatched_busco_phylonames )[ :5 ]:
            logger.warning( f"  Unmatched BUSCO key: '{unmatched_phyloname}'" )
        if len( unmatched_busco_phylonames ) > 5:
            logger.warning( f"  ... and {len( unmatched_busco_phylonames ) - 5} more" )

    if species_without_busco_match > 0 and len( phylonames___busco_stats ) > 0:
        logger.warning( "Some species have no BUSCO data match - check phyloname consistency between scripts 001 and 005" )

        example_species_key = list( phylonames___species_info.keys() )[ 0 ]
        example_busco_key = list( phylonames___busco_stats.keys() )[ 0 ] if phylonames___busco_stats else 'N/A'
        logger.info( f"  Example proteome manifest key: '{example_species_key}'" )
        logger.info( f"  Example BUSCO summary key:     '{example_busco_key}'" )

    logger.info( "" )

    # ========================================================================
    # WRITE OUTPUTS
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "WRITING OUTPUTS" )
    logger.info( "=" * 80 )
    logger.info( "" )

    # Write comprehensive quality summary
    write_comprehensive_summary(
        summary_path = output_summary_path,
        phylonames___species_info = phylonames___species_info,
        phylonames___assembly_stats = phylonames___assembly_stats,
        phylonames___busco_stats = phylonames___busco_stats,
        lineage_names = lineage_names,
        logger = logger
    )

    logger.info( "" )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    species_with_genomes = len( phylonames___assembly_stats )
    species_with_busco = len( phylonames___busco_stats )
    total_species = len( phylonames___species_info )

    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Total species: {total_species}" )
    logger.info( f"Species with genome assemblies: {species_with_genomes}" )
    logger.info( f"Species with BUSCO results: {species_with_busco}" )
    logger.info( f"BUSCO lineages: {len( lineage_names )} ({', '.join( lineage_names ) if lineage_names else 'none'})" )
    logger.info( "" )
    logger.info( f"Quality summary: {output_summary_path}" )
    logger.info( f"Log: {output_log_path}" )
    logger.info( "" )
    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )
    logger.info( "COMPLETE" )
    logger.info( "=" * 80 )

    print( "" )
    print( f"Done! Summarized quality for {total_species} species." )
    print( f"Quality summary: {output_summary_path}" )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()
