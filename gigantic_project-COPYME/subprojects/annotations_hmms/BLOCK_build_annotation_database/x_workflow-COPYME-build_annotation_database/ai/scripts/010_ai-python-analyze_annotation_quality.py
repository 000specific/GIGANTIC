#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Assess annotation quality by computing per-tool coverage rates and flagging low-annotation species
# Human: Eric Edsinger

"""
010_ai-python-analyze_annotation_quality.py

Assesses annotation quality by computing per-tool coverage rates and flagging
species with low annotation rates. This provides a quality control overview
that helps identify species with potentially incomplete or problematic
annotations.

The script reads the statistics table from script 008 and performs the following
analyses for each tool (grouping InterProScan sub-databases together as a single
"interproscan" tool):

1. Estimates per-species proteome size from the database with the highest
   number of unique proteins for that species. This is an approximation since
   the actual proteome size is not directly available at this pipeline stage.

2. Calculates per-species, per-tool annotation density (average annotations
   per annotated protein).

3. Computes the mean and standard deviation of unique protein counts across
   species for each tool.

4. Flags species where the unique protein count falls more than 1 standard
   deviation below the tool mean. These species may have incomplete annotations
   and warrant further investigation.

Input:
    --statistics: Path to 8_ai-annotation_statistics.tsv from script 008
    --output-dir: Output directory

Output:
    10_ai-annotation_quality.tsv
        Per-species, per-tool quality assessment with columns:
        - Phyloname (phylogenetic name of species)
        - Tool_Name (annotation tool name)
        - Unique_Proteins_Annotated (count of proteins with annotations from this tool)
        - Annotations_Per_Protein (average annotation count per annotated protein)
        - Coverage_Flag (normal or low_annotation based on z-score below negative 1)

    10_ai-log-analyze_annotation_quality.log

Usage:
    python3 010_ai-python-analyze_annotation_quality.py \\
        --statistics 8_ai-annotation_statistics.tsv \\
        --output-dir .
"""

import argparse
import logging
import math
import sys
from pathlib import Path
from collections import OrderedDict


# =============================================================================
# Tool grouping: InterProScan sub-databases are grouped under "interproscan"
# =============================================================================
# These database names are sub-databases of InterProScan and should be
# aggregated when computing tool-level statistics.
# =============================================================================

INTERPROSCAN_SUB_DATABASE_NAMES = {
    'pfam',
    'gene3d',
    'superfamily',
    'smart',
    'panther',
    'cdd',
    'prints',
    'prositepatterns',
    'prositeprofiles',
    'hamap',
    'sfld',
    'funfam',
    'ncbifam',
    'pirsf',
    'coils',
    'mobidblite',
    'antifam',
    'interproscan',
    'go',
}

STANDALONE_TOOL_NAMES = {
    'deeploc',
    'signalp',
    'tmbed',
    'metapredict',
}


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '010_analyze_annotation_quality' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '10_ai-log-analyze_annotation_quality.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_statistics( statistics_path: Path, logger: logging.Logger ) -> list:
    """
    Load the annotation statistics from script 008 output.

    Returns a list of dictionaries, each with:
        phyloname, database_name, total_annotations, unique_proteins_annotated,
        unique_identifiers, annotations_per_protein
    """

    logger.info( f"Loading statistics from: {statistics_path}" )

    if not statistics_path.exists():
        logger.error( "CRITICAL ERROR: Statistics file does not exist!" )
        logger.error( f"Expected path: {statistics_path}" )
        logger.error( "Run script 008 (compile_annotation_statistics) first." )
        sys.exit( 1 )

    statistics_records = []

    with open( statistics_path, 'r' ) as input_statistics:
        # Phyloname (phylogenetic name of species)	Database_Name (annotation database name)	Total_Annotations (...)	Unique_Proteins_Annotated (...)	Unique_Identifiers (...)	Annotations_Per_Protein (...)
        # Metazoa_...Homo_sapiens	pfam	125000	18500	4200	6.76
        for line in input_statistics:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 6:
                logger.warning( f"WARNING: Line has fewer than 6 columns ({len( parts )}), skipping" )
                continue

            phyloname = parts[ 0 ]
            database_name = parts[ 1 ]

            try:
                total_annotations = int( parts[ 2 ] )
            except ValueError:
                logger.warning( f"WARNING: Non-integer total_annotations '{parts[ 2 ]}' for {phyloname}/{database_name}, skipping" )
                continue

            try:
                unique_proteins_annotated = int( parts[ 3 ] )
            except ValueError:
                logger.warning( f"WARNING: Non-integer unique_proteins '{parts[ 3 ]}' for {phyloname}/{database_name}, skipping" )
                continue

            try:
                unique_identifiers = int( parts[ 4 ] )
            except ValueError:
                unique_identifiers = 0

            try:
                annotations_per_protein = float( parts[ 5 ] )
            except ValueError:
                annotations_per_protein = 0.0

            statistics_records.append( {
                'phyloname': phyloname,
                'database_name': database_name,
                'total_annotations': total_annotations,
                'unique_proteins_annotated': unique_proteins_annotated,
                'unique_identifiers': unique_identifiers,
                'annotations_per_protein': annotations_per_protein,
            } )

    logger.info( f"  Loaded {len( statistics_records )} statistics records" )

    if len( statistics_records ) == 0:
        logger.error( "CRITICAL ERROR: No statistics records loaded!" )
        logger.error( "The statistics file may be empty or in unexpected format." )
        sys.exit( 1 )

    return statistics_records


def map_database_to_tool( database_name: str ) -> str:
    """
    Map a database name to its parent tool name.
    InterProScan sub-databases are grouped under 'interproscan'.
    Standalone tools map to themselves.
    """

    if database_name in INTERPROSCAN_SUB_DATABASE_NAMES:
        return 'interproscan'
    elif database_name in STANDALONE_TOOL_NAMES:
        return database_name
    else:
        # Unknown database - return as its own tool
        return database_name


def calculate_mean( values: list ) -> float:
    """Calculate the arithmetic mean of a list of numbers."""

    if len( values ) == 0:
        return 0.0

    return sum( values ) / len( values )


def calculate_standard_deviation( values: list, mean_value: float ) -> float:
    """Calculate the population standard deviation of a list of numbers."""

    if len( values ) <= 1:
        return 0.0

    squared_differences = [ ( value - mean_value ) ** 2 for value in values ]
    variance = sum( squared_differences ) / len( values )

    return math.sqrt( variance )


def analyze_annotation_quality( statistics_records: list, output_directory: Path,
                                  logger: logging.Logger ) -> None:
    """
    Analyze annotation quality by computing per-tool coverage and flagging
    species with low annotation rates. Write the quality assessment output file.
    """

    # =========================================================================
    # Group statistics by tool and species
    # =========================================================================

    # Build: tool_name -> phyloname -> { total_annotations, unique_proteins (aggregated) }
    # For interproscan, we aggregate all sub-database statistics per species

    # First, collect all unique proteins per tool per species
    # tool_name -> phyloname -> { 'total_annotations': int, 'unique_proteins_from_databases': list of ints }
    tool_names___phylonames___aggregated_statistics = {}

    for record in statistics_records:
        tool_name = map_database_to_tool( record[ 'database_name' ] )
        phyloname = record[ 'phyloname' ]

        if tool_name not in tool_names___phylonames___aggregated_statistics:
            tool_names___phylonames___aggregated_statistics[ tool_name ] = {}

        if phyloname not in tool_names___phylonames___aggregated_statistics[ tool_name ]:
            tool_names___phylonames___aggregated_statistics[ tool_name ][ phyloname ] = {
                'total_annotations': 0,
                'max_unique_proteins': 0,
                'sum_unique_proteins_per_database': 0,
                'database_count': 0,
            }

        species_tool_record = tool_names___phylonames___aggregated_statistics[ tool_name ][ phyloname ]
        species_tool_record[ 'total_annotations' ] += record[ 'total_annotations' ]
        species_tool_record[ 'database_count' ] += 1

        # Track the maximum unique proteins from any single database
        # This provides a conservative estimate of tool coverage
        if record[ 'unique_proteins_annotated' ] > species_tool_record[ 'max_unique_proteins' ]:
            species_tool_record[ 'max_unique_proteins' ] = record[ 'unique_proteins_annotated' ]

        # Also track sum for computing annotations per protein
        species_tool_record[ 'sum_unique_proteins_per_database' ] += record[ 'unique_proteins_annotated' ]

    tool_names = sorted( tool_names___phylonames___aggregated_statistics.keys() )
    logger.info( f"Tools identified: {len( tool_names )}" )
    for tool_name in tool_names:
        species_count = len( tool_names___phylonames___aggregated_statistics[ tool_name ] )
        logger.info( f"  {tool_name}: {species_count} species" )

    # =========================================================================
    # Calculate per-tool statistics across species and flag outliers
    # =========================================================================

    quality_records = []

    for tool_name in tool_names:
        phylonames___aggregated = tool_names___phylonames___aggregated_statistics[ tool_name ]

        # Collect unique protein counts across all species for this tool
        species_unique_protein_counts = []
        for phyloname in phylonames___aggregated:
            # Use max_unique_proteins as the representative count for this tool
            # For standalone tools, this is the direct unique protein count
            # For interproscan, this is the highest count from any sub-database
            unique_count = phylonames___aggregated[ phyloname ][ 'max_unique_proteins' ]
            species_unique_protein_counts.append( unique_count )

        # Calculate mean and standard deviation
        mean_unique_proteins = calculate_mean( species_unique_protein_counts )
        standard_deviation_unique_proteins = calculate_standard_deviation( species_unique_protein_counts, mean_unique_proteins )

        logger.info( "" )
        logger.info( f"Tool: {tool_name}" )
        logger.info( f"  Mean unique proteins: {mean_unique_proteins:.1f}" )
        logger.info( f"  Standard deviation: {standard_deviation_unique_proteins:.1f}" )
        logger.info( f"  Threshold (mean - 1 SD): {mean_unique_proteins - standard_deviation_unique_proteins:.1f}" )

        # Flag species below 1 standard deviation of the mean
        low_annotation_threshold = mean_unique_proteins - standard_deviation_unique_proteins
        low_annotation_count = 0

        sorted_phylonames = sorted( phylonames___aggregated.keys() )

        for phyloname in sorted_phylonames:
            aggregated_record = phylonames___aggregated[ phyloname ]
            unique_proteins = aggregated_record[ 'max_unique_proteins' ]
            total_annotations = aggregated_record[ 'total_annotations' ]

            # Calculate annotations per protein for this tool
            if unique_proteins > 0:
                annotations_per_protein = total_annotations / unique_proteins
            else:
                annotations_per_protein = 0.0

            # Determine coverage flag
            # Use z-score approach: flag if z-score < -1
            if standard_deviation_unique_proteins > 0:
                z_score = ( unique_proteins - mean_unique_proteins ) / standard_deviation_unique_proteins
            else:
                # If SD is 0, all values are the same - no outliers
                z_score = 0.0

            if z_score < -1.0:
                coverage_flag = 'low_annotation'
                low_annotation_count += 1
            else:
                coverage_flag = 'normal'

            quality_records.append( {
                'phyloname': phyloname,
                'tool_name': tool_name,
                'unique_proteins_annotated': unique_proteins,
                'annotations_per_protein': annotations_per_protein,
                'coverage_flag': coverage_flag,
            } )

            if coverage_flag == 'low_annotation':
                logger.debug( f"    FLAGGED: {phyloname} - {unique_proteins} proteins (z={z_score:.2f})" )

        logger.info( f"  Species flagged as low_annotation: {low_annotation_count} of {len( sorted_phylonames )}" )

    # =========================================================================
    # Validate results
    # =========================================================================

    if len( quality_records ) == 0:
        logger.error( "CRITICAL ERROR: No quality records were generated!" )
        logger.error( "The statistics file may contain no usable data." )
        sys.exit( 1 )

    # =========================================================================
    # Write annotation quality output file
    # =========================================================================

    output_quality_path = output_directory / '10_ai-annotation_quality.tsv'

    with open( output_quality_path, 'w' ) as output_quality_file:
        # Write header
        header = 'Phyloname (phylogenetic name of species)' + '\t'
        header += 'Tool_Name (annotation tool name)' + '\t'
        header += 'Unique_Proteins_Annotated (count of proteins with annotations from this tool)' + '\t'
        header += 'Annotations_Per_Protein (average annotation count per annotated protein)' + '\t'
        header += 'Coverage_Flag (normal or low_annotation based on z-score below negative 1)' + '\n'
        output_quality_file.write( header )

        # Sort records by phyloname then tool name
        sorted_records = sorted( quality_records, key = lambda record: ( record[ 'phyloname' ], record[ 'tool_name' ] ) )

        for record in sorted_records:
            output = record[ 'phyloname' ] + '\t'
            output += record[ 'tool_name' ] + '\t'
            output += str( record[ 'unique_proteins_annotated' ] ) + '\t'
            output += f"{record[ 'annotations_per_protein' ]:.2f}" + '\t'
            output += record[ 'coverage_flag' ] + '\n'
            output_quality_file.write( output )

    logger.info( f"Wrote annotation quality to: {output_quality_path}" )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 010 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Total quality records: {len( quality_records )}" )
    logger.info( f"  Tools analyzed: {len( tool_names )}" )

    # Count flagged species per tool
    total_flagged = 0
    for tool_name in tool_names:
        tool_records = [ record for record in quality_records if record[ 'tool_name' ] == tool_name ]
        flagged_records = [ record for record in tool_records if record[ 'coverage_flag' ] == 'low_annotation' ]
        total_flagged += len( flagged_records )
        logger.info( f"  {tool_name}: {len( flagged_records )} flagged / {len( tool_records )} total species" )

    logger.info( "" )
    logger.info( f"  Total flagged records: {total_flagged}" )
    logger.info( f"  Output file: {output_quality_path}" )

    # List all flagged species across all tools
    if total_flagged > 0:
        logger.info( "" )
        logger.info( "Species flagged as low_annotation:" )
        flagged_species = set()
        for record in quality_records:
            if record[ 'coverage_flag' ] == 'low_annotation':
                flagged_species.add( record[ 'phyloname' ] )

        for flagged_phyloname in sorted( flagged_species ):
            # Find which tools flagged this species
            flagged_tools = []
            for record in quality_records:
                if record[ 'phyloname' ] == flagged_phyloname and record[ 'coverage_flag' ] == 'low_annotation':
                    flagged_tools.append( record[ 'tool_name' ] )
            logger.info( f"  {flagged_phyloname}: flagged by {','.join( sorted( flagged_tools ) )}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Assess annotation quality by computing per-tool coverage rates and flagging low-annotation species'
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
        help = 'Output directory for quality analysis (default: current directory)'
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
    logger.info( "Script 010: Analyze Annotation Quality" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load statistics from script 008
    # =========================================================================

    statistics_records = load_statistics( statistics_path, logger )

    # =========================================================================
    # Analyze annotation quality
    # =========================================================================

    analyze_annotation_quality( statistics_records, output_directory, logger )


if __name__ == '__main__':
    main()
