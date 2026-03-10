#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Detect species with extreme annotation rates using z-score analysis
# Human: Eric Edsinger

"""
014_ai-python-detect_annotation_outliers.py

Detects species with unusually high or low annotation counts for each annotation
database using z-score analysis. This quality control step identifies potential
issues such as:
    - Species with incomplete proteomes (low outliers)
    - Species with duplicated or fragmented proteomes (high outliers)
    - Database-specific annotation biases
    - Data quality problems in upstream annotation tools

For each annotation database, the script computes the distribution of
Total_Annotations across all species, calculates z-scores, and flags species
with |z-score| > 2 as outliers.

Input:
    --statistics: Path to 8_ai-annotation_statistics.tsv from script 008
    --output-dir: Directory for output files

Output:
    14_ai-annotation_outliers.tsv
        Tab-separated file with columns:
        - Phyloname (phylogenetic name of species)
        - Database_Name (annotation database name)
        - Total_Annotations (total annotation rows for this species and database)
        - Mean_Annotations_All_Species (mean across all species for this database)
        - Standard_Deviation_All_Species (standard deviation across all species)
        - Z_Score (z-score calculated as species count minus mean divided by stdev)
        - Outlier_Status (high_outlier or low_outlier or normal)

    14_ai-log-detect_annotation_outliers.log

Usage:
    python3 014_ai-python-detect_annotation_outliers.py \\
        --statistics 8_ai-annotation_statistics.tsv \\
        --output-dir .
"""

import argparse
import logging
import statistics
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '014_detect_annotation_outliers' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '14_ai-log-detect_annotation_outliers.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_statistics( statistics_path: Path, logger: logging.Logger ) -> list:
    """
    Read the annotation statistics table from script 008.
    Returns a list of dictionaries, one per row, with keys matching column names.
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
            unique_proteins_annotated = int( parts[ 3 ] )
            unique_identifiers = int( parts[ 4 ] )
            annotations_per_protein = float( parts[ 5 ] )

            statistics_records.append( {
                'phyloname': phyloname,
                'database_name': database_name,
                'total_annotations': total_annotations,
                'unique_proteins_annotated': unique_proteins_annotated,
                'unique_identifiers': unique_identifiers,
                'annotations_per_protein': annotations_per_protein,
            } )

    if len( statistics_records ) == 0:
        logger.error( "CRITICAL ERROR: No data rows found in statistics file!" )
        logger.error( f"File path: {statistics_path}" )
        logger.error( "The statistics file may be empty or have an unexpected format." )
        sys.exit( 1 )

    logger.info( f"  Loaded {len( statistics_records )} statistics records" )

    return statistics_records


def detect_outliers( statistics_records: list, output_directory: Path, logger: logging.Logger ) -> None:
    """
    Compute z-scores for each species x database combination and flag outliers.
    An outlier is defined as a species with |z-score| > 2 for a given database.
    """

    # =========================================================================
    # Group records by database
    # =========================================================================

    database_names___records = {}

    for record in statistics_records:
        database_name = record[ 'database_name' ]

        if database_name not in database_names___records:
            database_names___records[ database_name ] = []

        database_names___records[ database_name ].append( record )

    logger.info( f"Found {len( database_names___records )} databases in statistics data" )

    for database_name in sorted( database_names___records.keys() ):
        species_count = len( database_names___records[ database_name ] )
        logger.info( f"  {database_name}: {species_count} species" )

    # =========================================================================
    # Compute z-scores per database
    # =========================================================================

    outlier_records = []
    total_high_outlier_count = 0
    total_low_outlier_count = 0
    total_normal_count = 0

    for database_name in sorted( database_names___records.keys() ):
        records_for_database = database_names___records[ database_name ]

        # Extract total_annotations values for all species in this database
        annotation_counts = [ record[ 'total_annotations' ] for record in records_for_database ]

        # Compute mean and standard deviation
        mean_value = statistics.mean( annotation_counts )

        # Handle edge case: fewer than 2 species means stdev is undefined
        if len( annotation_counts ) < 2:
            standard_deviation_value = 0.0
            logger.warning( f"  WARNING: Database {database_name} has fewer than 2 species" )
            logger.warning( "  Cannot compute meaningful standard deviation, marking all as normal" )
        else:
            standard_deviation_value = statistics.stdev( annotation_counts )

        logger.info( f"  Database: {database_name}" )
        logger.info( f"    Mean: {mean_value:.2f}" )
        logger.info( f"    Standard deviation: {standard_deviation_value:.2f}" )

        database_high_outlier_count = 0
        database_low_outlier_count = 0

        for record in records_for_database:
            phyloname = record[ 'phyloname' ]
            total_annotations = record[ 'total_annotations' ]

            # Compute z-score
            if standard_deviation_value == 0.0:
                # All species have the same count, or only one species
                z_score = 0.0
            else:
                z_score = ( total_annotations - mean_value ) / standard_deviation_value

            # Determine outlier status
            if z_score > 2.0:
                outlier_status = 'high_outlier'
                database_high_outlier_count += 1
                total_high_outlier_count += 1
            elif z_score < -2.0:
                outlier_status = 'low_outlier'
                database_low_outlier_count += 1
                total_low_outlier_count += 1
            else:
                outlier_status = 'normal'
                total_normal_count += 1

            outlier_records.append( {
                'phyloname': phyloname,
                'database_name': database_name,
                'total_annotations': total_annotations,
                'mean_annotations_all_species': mean_value,
                'standard_deviation_all_species': standard_deviation_value,
                'z_score': z_score,
                'outlier_status': outlier_status,
            } )

        if database_high_outlier_count > 0:
            logger.info( f"    High outliers: {database_high_outlier_count}" )
        if database_low_outlier_count > 0:
            logger.info( f"    Low outliers: {database_low_outlier_count}" )

    # =========================================================================
    # Validate that we produced results
    # =========================================================================

    if len( outlier_records ) == 0:
        logger.error( "CRITICAL ERROR: No outlier analysis records were generated!" )
        logger.error( "This indicates a logic error in the z-score computation." )
        sys.exit( 1 )

    # =========================================================================
    # Write outlier results
    # =========================================================================

    output_file = output_directory / '14_ai-annotation_outliers.tsv'

    with open( output_file, 'w' ) as output_outliers:
        # Write header
        header = 'Phyloname (phylogenetic name of species)' + '\t'
        header += 'Database_Name (annotation database name)' + '\t'
        header += 'Total_Annotations (total annotation rows for this species and database)' + '\t'
        header += 'Mean_Annotations_All_Species (mean of total annotations across all species for this database)' + '\t'
        header += 'Standard_Deviation_All_Species (standard deviation of total annotations across all species for this database)' + '\t'
        header += 'Z_Score (z-score calculated as species count minus mean divided by standard deviation)' + '\t'
        header += 'Outlier_Status (high_outlier if z-score above 2 or low_outlier if z-score below negative 2 or normal)' + '\n'
        output_outliers.write( header )

        # Write data rows
        for outlier_record in outlier_records:
            output = outlier_record[ 'phyloname' ] + '\t'
            output += outlier_record[ 'database_name' ] + '\t'
            output += str( outlier_record[ 'total_annotations' ] ) + '\t'
            output += f"{outlier_record[ 'mean_annotations_all_species' ]:.2f}" + '\t'
            output += f"{outlier_record[ 'standard_deviation_all_species' ]:.2f}" + '\t'
            output += f"{outlier_record[ 'z_score' ]:.4f}" + '\t'
            output += outlier_record[ 'outlier_status' ] + '\n'
            output_outliers.write( output )

    logger.info( f"Wrote outlier analysis to: {output_file}" )

    # =========================================================================
    # Log outlier details
    # =========================================================================

    outlier_only_records = [ record for record in outlier_records if record[ 'outlier_status' ] != 'normal' ]

    if len( outlier_only_records ) > 0:
        logger.info( "" )
        logger.info( "Outlier species details:" )
        logger.info( "-" * 70 )

        for outlier_record in sorted( outlier_only_records, key = lambda record: ( record[ 'database_name' ], record[ 'outlier_status' ], record[ 'phyloname' ] ) ):
            logger.info(
                f"  {outlier_record[ 'outlier_status' ]:<15s} "
                f"{outlier_record[ 'database_name' ]:<20s} "
                f"z={outlier_record[ 'z_score' ]:>8.4f}  "
                f"{outlier_record[ 'phyloname' ]}"
            )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 014 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Total records analyzed: {len( outlier_records )}" )
    logger.info( f"  Databases analyzed: {len( database_names___records )}" )
    logger.info( f"  High outliers (z > 2): {total_high_outlier_count}" )
    logger.info( f"  Low outliers (z < -2): {total_low_outlier_count}" )
    logger.info( f"  Normal: {total_normal_count}" )
    logger.info( f"  Output file: {output_file}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Detect species with extreme annotation rates using z-score analysis'
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
        help = 'Output directory for outlier analysis and log (default: current directory)'
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
    logger.info( "Script 014: Detect Annotation Outliers" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load input data
    # =========================================================================

    statistics_records = load_statistics( statistics_path, logger )

    # =========================================================================
    # Detect outliers
    # =========================================================================

    detect_outliers( statistics_records, output_directory, logger )


if __name__ == '__main__':
    main()
