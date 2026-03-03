#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Generate pre-formatted species x database matrices for heatmap visualization
# Human: Eric Edsinger

"""
015_ai-python-generate_visualization_data.py

Generates two wide-format matrices for downstream heatmap visualization:
    1. Species x database annotation count matrix
    2. Species x database z-score matrix

These matrices pivot the long-format statistics table (one row per species x
database) into wide format (one row per species, one column per database),
making them directly usable by plotting tools.

Database columns are sorted in a logical order:
    - InterProScan component databases (alphabetical)
    - interproscan (summary)
    - go (gene ontology)
    - deeploc, signalp, tmbed, metapredict (standalone tools)

Colorblind-safe palette for heatmaps (LightBlue2DarkBlue10Steps):
    #E5FFFF, #CCFAFF, #B2F2FF, #99E5FF, #7FD4FF, #65BFFF, #4CA5FF, #3288FF,
    #1965FF, #003FFF

Input:
    --statistics: Path to 8_ai-annotation_statistics.tsv from script 008
    --output-dir: Directory for output files

Output:
    15_ai-visualization_heatmap_data.tsv
        Wide-format species x database annotation count matrix.
        Missing combinations filled with 0.

    15_ai-visualization_zscore_data.tsv
        Wide-format species x database z-score matrix.
        Missing combinations filled with NA.

    15_ai-log-generate_visualization_data.log

Usage:
    python3 015_ai-python-generate_visualization_data.py \\
        --statistics 8_ai-annotation_statistics.tsv \\
        --output-dir .
"""

import argparse
import logging
import statistics
import sys
from pathlib import Path


# =============================================================================
# Database ordering for visualization
# =============================================================================
# InterProScan component databases known to GIGANTIC, in alphabetical order.
# These appear first in the column ordering, followed by special databases.
# =============================================================================

INTERPROSCAN_COMPONENT_DATABASES = [
    'antifam',
    'cdd',
    'coils',
    'funfam',
    'gene3d',
    'hamap',
    'mobidblite',
    'ncbifam',
    'panther',
    'pfam',
    'pirsf',
    'prints',
    'prositepatterns',
    'prositeprofiles',
    'sfld',
    'smart',
    'superfamily',
]

# Special databases that come after component databases
SPECIAL_DATABASES_ORDERED = [
    'interproscan',
    'go',
    'deeploc',
    'signalp',
    'tmbed',
    'metapredict',
]

# Colorblind-safe palette reference (logged for downstream use)
HEATMAP_PALETTE_LIGHT_BLUE_TO_DARK_BLUE = [
    '#E5FFFF',
    '#CCFAFF',
    '#B2F2FF',
    '#99E5FF',
    '#7FD4FF',
    '#65BFFF',
    '#4CA5FF',
    '#3288FF',
    '#1965FF',
    '#003FFF',
]


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '015_generate_visualization_data' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '15_ai-log-generate_visualization_data.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_statistics( statistics_path: Path, logger: logging.Logger ) -> list:
    """
    Read the annotation statistics table from script 008.
    Returns a list of dictionaries, one per row.
    """

    logger.info( f"Reading annotation statistics: {statistics_path}" )

    if not statistics_path.exists():
        logger.error( "CRITICAL ERROR: Statistics file does not exist!" )
        logger.error( f"Expected path: {statistics_path}" )
        logger.error( "Run script 008 (annotation_statistics) first." )
        sys.exit( 1 )

    statistics_records = []

    with open( statistics_path, 'r' ) as input_statistics:
        # Phyloname (phylogenetic name of species)	Database_Name (annotation database name)	Total_Annotations (total annotation rows for this species and database)	Unique_Proteins_Annotated (count of distinct proteins with annotations)	Unique_Identifiers (count of distinct annotation identifiers)	Annotations_Per_Protein (average annotations per annotated protein)
        # Metazoa_Ctenophora_Tentaculata_Lobata_Bolinopsidae_Bolinopsis_microptera	pfam	12345	5678	1234	2.17
        for line in input_statistics:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 6:
                logger.warning( f"WARNING: Line has fewer than 6 columns ({len( parts )}), skipping" )
                logger.debug( f"Skipped line: {line[ :200 ]}" )
                continue

            phyloname = parts[ 0 ]
            database_name = parts[ 1 ]
            total_annotations = int( parts[ 2 ] )

            statistics_records.append( {
                'phyloname': phyloname,
                'database_name': database_name,
                'total_annotations': total_annotations,
            } )

    if len( statistics_records ) == 0:
        logger.error( "CRITICAL ERROR: No data rows found in statistics file!" )
        logger.error( f"File path: {statistics_path}" )
        logger.error( "The statistics file may be empty or have an unexpected format." )
        sys.exit( 1 )

    logger.info( f"  Loaded {len( statistics_records )} statistics records" )

    return statistics_records


def determine_database_column_order( database_names_found: set, logger: logging.Logger ) -> list:
    """
    Determine the column order for databases in the wide-format matrix.

    Order:
        1. InterProScan component databases (alphabetical, only those present)
        2. Special databases in defined order (only those present)
        3. Any unexpected databases (alphabetical, appended at end)
    """

    ordered_databases = []
    all_known_databases = set( INTERPROSCAN_COMPONENT_DATABASES + SPECIAL_DATABASES_ORDERED )
    unexpected_databases = []

    # Add InterProScan component databases in alphabetical order
    for database_name in INTERPROSCAN_COMPONENT_DATABASES:
        if database_name in database_names_found:
            ordered_databases.append( database_name )

    # Add special databases in defined order
    for database_name in SPECIAL_DATABASES_ORDERED:
        if database_name in database_names_found:
            ordered_databases.append( database_name )

    # Check for any unexpected databases not in our known lists
    for database_name in sorted( database_names_found ):
        if database_name not in all_known_databases:
            unexpected_databases.append( database_name )
            ordered_databases.append( database_name )
            logger.warning( f"  WARNING: Unexpected database found: {database_name}" )
            logger.warning( "  This database is not in the predefined ordering lists." )
            logger.warning( "  It will be appended at the end of the column order." )

    logger.info( f"  Database column order ({len( ordered_databases )} databases):" )
    for index, database_name in enumerate( ordered_databases ):
        logger.info( f"    {index + 1}. {database_name}" )

    return ordered_databases


def generate_visualization_data( statistics_records: list, output_directory: Path, logger: logging.Logger ) -> None:
    """
    Pivot statistics from long format to wide format and compute z-scores.
    Write two output matrices: annotation counts and z-scores.
    """

    # =========================================================================
    # Build species x database lookup
    # =========================================================================

    # Collect all unique phylonames and database names
    phylonames_found = set()
    database_names_found = set()

    # Dictionary: (phyloname, database_name) -> total_annotations
    species_database_keys___annotation_counts = {}

    for record in statistics_records:
        phyloname = record[ 'phyloname' ]
        database_name = record[ 'database_name' ]
        total_annotations = record[ 'total_annotations' ]

        phylonames_found.add( phyloname )
        database_names_found.add( database_name )

        key = ( phyloname, database_name )
        species_database_keys___annotation_counts[ key ] = total_annotations

    sorted_phylonames = sorted( phylonames_found )

    logger.info( f"  Species found: {len( sorted_phylonames )}" )
    logger.info( f"  Databases found: {len( database_names_found )}" )

    # =========================================================================
    # Determine database column order
    # =========================================================================

    ordered_databases = determine_database_column_order( database_names_found, logger )

    # =========================================================================
    # Compute z-scores per database
    # =========================================================================

    # First, collect annotation counts per database for z-score computation
    database_names___annotation_count_lists = {}

    for database_name in ordered_databases:
        annotation_counts_for_database = []

        for phyloname in sorted_phylonames:
            key = ( phyloname, database_name )
            count = species_database_keys___annotation_counts.get( key, 0 )
            annotation_counts_for_database.append( count )

        database_names___annotation_count_lists[ database_name ] = annotation_counts_for_database

    # Compute mean and stdev for each database
    database_names___means = {}
    database_names___standard_deviations = {}

    for database_name in ordered_databases:
        annotation_counts_for_database = database_names___annotation_count_lists[ database_name ]

        mean_value = statistics.mean( annotation_counts_for_database )
        database_names___means[ database_name ] = mean_value

        if len( annotation_counts_for_database ) < 2:
            standard_deviation_value = 0.0
        else:
            standard_deviation_value = statistics.stdev( annotation_counts_for_database )

        database_names___standard_deviations[ database_name ] = standard_deviation_value

        logger.debug( f"  {database_name}: mean={mean_value:.2f}, stdev={standard_deviation_value:.2f}" )

    # Compute z-score matrix
    # Dictionary: (phyloname, database_name) -> z_score or 'NA'
    species_database_keys___z_scores = {}

    for database_name in ordered_databases:
        mean_value = database_names___means[ database_name ]
        standard_deviation_value = database_names___standard_deviations[ database_name ]

        for phyloname in sorted_phylonames:
            key = ( phyloname, database_name )
            count = species_database_keys___annotation_counts.get( key, None )

            if count is None:
                # Species has no data for this database
                species_database_keys___z_scores[ key ] = 'NA'
            elif standard_deviation_value == 0.0:
                species_database_keys___z_scores[ key ] = 0.0
            else:
                z_score = ( count - mean_value ) / standard_deviation_value
                species_database_keys___z_scores[ key ] = z_score

    # =========================================================================
    # Write annotation count heatmap data (wide format)
    # =========================================================================

    output_heatmap_file = output_directory / '15_ai-visualization_heatmap_data.tsv'

    with open( output_heatmap_file, 'w' ) as output_heatmap:
        # Write header
        header = 'Phyloname (phylogenetic name of species)'
        for database_name in ordered_databases:
            header += '\t' + database_name + ' (annotation count for ' + database_name + ' database)'
        header += '\n'
        output_heatmap.write( header )

        # Write data rows
        for phyloname in sorted_phylonames:
            output = phyloname
            for database_name in ordered_databases:
                key = ( phyloname, database_name )
                count = species_database_keys___annotation_counts.get( key, 0 )
                output += '\t' + str( count )
            output += '\n'
            output_heatmap.write( output )

    logger.info( f"Wrote annotation count heatmap data to: {output_heatmap_file}" )

    # =========================================================================
    # Write z-score heatmap data (wide format)
    # =========================================================================

    output_zscore_file = output_directory / '15_ai-visualization_zscore_data.tsv'

    with open( output_zscore_file, 'w' ) as output_zscore:
        # Write header
        header = 'Phyloname (phylogenetic name of species)'
        for database_name in ordered_databases:
            header += '\t' + database_name + ' (z-score for ' + database_name + ' database)'
        header += '\n'
        output_zscore.write( header )

        # Write data rows
        for phyloname in sorted_phylonames:
            output = phyloname
            for database_name in ordered_databases:
                key = ( phyloname, database_name )
                z_score = species_database_keys___z_scores.get( key, 'NA' )
                if z_score == 'NA':
                    output += '\t' + 'NA'
                else:
                    output += '\t' + f"{z_score:.4f}"
            output += '\n'
            output_zscore.write( output )

    logger.info( f"Wrote z-score heatmap data to: {output_zscore_file}" )

    # =========================================================================
    # Log colorblind-safe palette reference for downstream plotting
    # =========================================================================

    logger.info( "" )
    logger.info( "Colorblind-safe heatmap palette (LightBlue2DarkBlue10Steps):" )
    logger.info( "  For downstream visualization scripts, use this palette:" )
    for index, hex_color in enumerate( HEATMAP_PALETTE_LIGHT_BLUE_TO_DARK_BLUE ):
        logger.info( f"    Step {index + 1}: {hex_color}" )
    logger.info( "  Source: colorBlindness R package" )
    logger.info( "  URL: https://cran.r-project.org/web/packages/colorBlindness/" )

    # =========================================================================
    # Count missing values in the matrix
    # =========================================================================

    missing_count = 0
    total_cells = len( sorted_phylonames ) * len( ordered_databases )

    for phyloname in sorted_phylonames:
        for database_name in ordered_databases:
            key = ( phyloname, database_name )
            if key not in species_database_keys___annotation_counts:
                missing_count += 1

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 015 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species in matrix: {len( sorted_phylonames )}" )
    logger.info( f"  Databases in matrix: {len( ordered_databases )}" )
    logger.info( f"  Total matrix cells: {total_cells}" )
    logger.info( f"  Missing values (filled with 0 or NA): {missing_count}" )
    logger.info( f"  Output (annotation counts): {output_heatmap_file}" )
    logger.info( f"  Output (z-scores): {output_zscore_file}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Generate pre-formatted species x database matrices for heatmap visualization'
    )

    parser.add_argument(
        '--statistics',
        type = str,
        required = True,
        help = 'Path to 8_ai-annotation_statistics.tsv from script 008'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Output directory for visualization data and log (default: current directory)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    statistics_path = Path( arguments.statistics )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 015: Generate Visualization Data" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load input data
    # =========================================================================

    statistics_records = load_statistics( statistics_path, logger )

    # =========================================================================
    # Generate visualization matrices
    # =========================================================================

    generate_visualization_data( statistics_records, output_directory, logger )


if __name__ == '__main__':
    main()
