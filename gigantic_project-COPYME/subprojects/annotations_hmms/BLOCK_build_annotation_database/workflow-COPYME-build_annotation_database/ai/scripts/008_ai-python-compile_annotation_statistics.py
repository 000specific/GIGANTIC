#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Compile comprehensive annotation statistics across all database types and all species
# Human: Eric Edsinger

"""
008_ai-python-compile_annotation_statistics.py

Compiles comprehensive annotation statistics across all 24 database types
(17 InterProScan component databases + interproscan summary + GO + deeploc +
signalp + tmbed + metapredict) and all species.

This script reads the discovery manifest from script 001 to know which tools
are available, then scans all database directories produced by parser scripts
003-007. For each database x species file, it counts total annotation rows,
unique proteins annotated, and unique annotation identifiers. It then produces
a per-species-per-database statistics table and a database completeness summary.

All 24 databases are in flat directories at the same level (database_pfam/,
database_gene3d/, ..., database_deeploc/, database_signalp/, etc.).

Input:
    --discovery-manifest: Path to 1_ai-tool_discovery_manifest.tsv from script 001
    --database-dir: Directory containing database_pfam/, database_gene3d/, ..., database_deeploc/, etc.
    --output-dir: Output directory

Output:
    8_ai-annotation_statistics.tsv
        Per-species, per-database statistics with columns:
        - Phyloname (phylogenetic name of species)
        - Database_Name (annotation database name)
        - Total_Annotations (total annotation rows for this species and database)
        - Unique_Proteins_Annotated (count of distinct proteins with annotations)
        - Unique_Identifiers (count of distinct annotation identifiers)
        - Annotations_Per_Protein (average annotations per annotated protein)

    8_ai-database_completeness.tsv
        Summary of which databases have data for which species with columns:
        - Phyloname (phylogenetic name of species)
        - Databases_With_Data_Count (number of databases that have annotations)
        - Databases_With_Data_List (comma delimited list of database names with data)
        - Total_Annotations_All_Databases (sum of all annotation rows across databases)
        - Total_Unique_Proteins (count of distinct proteins with any annotation)

    8_ai-log-compile_annotation_statistics.log

Usage:
    python3 008_ai-python-compile_annotation_statistics.py \\
        --discovery-manifest 1_ai-tool_discovery_manifest.tsv \\
        --database-dir . \\
        --output-dir .
"""

import argparse
import logging
import sys
from pathlib import Path
from collections import OrderedDict


# =============================================================================
# Database name mapping
# =============================================================================
# All 24 databases are flat directories at the same level: database_{name}/
# Maps tool names from the discovery manifest to the database names they produce.
# =============================================================================

# Map tool names from discovery manifest to the list of database names they produce
TOOL_NAMES___DATABASE_NAMES = {
    'interproscan': [
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
    ],
    'deeploc': [ 'deeploc' ],
    'signalp': [ 'signalp' ],
    'tmbed': [ 'tmbed' ],
    'metapredict': [ 'metapredict' ],
}


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '008_compile_annotation_statistics' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '8_ai-log-compile_annotation_statistics.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_discovery_manifest( manifest_path: Path, logger: logging.Logger ) -> dict:
    """
    Read the discovery manifest and return a dictionary of tool availability.
    Returns tool_names___tool_records: { 'interproscan': { ... }, 'deeploc': { ... }, ... }
    """

    logger.info( f"Reading discovery manifest: {manifest_path}" )

    if not manifest_path.exists():
        logger.error( "CRITICAL ERROR: Discovery manifest does not exist!" )
        logger.error( f"Expected path: {manifest_path}" )
        logger.error( "Run script 001 (discover_tool_outputs) first." )
        sys.exit( 1 )

    tool_names___tool_records = {}

    with open( manifest_path, 'r' ) as input_manifest:
        # Tool_Name (name of annotation tool)	Tool_Available (yes or no ...)	...
        # interproscan	yes	/path/to/output_to_input	5	*_interproscan_results.tsv
        for line in input_manifest:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Tool_Name' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 5:
                continue

            tool_name = parts[ 0 ]
            tool_record = {
                'tool_name': tool_name,
                'tool_available': parts[ 1 ],
                'output_directory': parts[ 2 ],
                'file_count': int( parts[ 3 ] ),
                'file_pattern': parts[ 4 ],
            }

            tool_names___tool_records[ tool_name ] = tool_record

    available_count = sum( 1 for record in tool_names___tool_records.values() if record[ 'tool_available' ] == 'yes' )
    logger.info( f"  Found {len( tool_names___tool_records )} tools in manifest, {available_count} available" )

    if available_count == 0:
        logger.error( "CRITICAL ERROR: No annotation tools are available!" )
        logger.error( "At least one tool must have results before compiling statistics." )
        sys.exit( 1 )

    return tool_names___tool_records


def extract_phyloname_from_database_filename( filename: str, database_name: str ) -> str:
    """
    Extract the GIGANTIC phyloname from a standardized database filename.
    Expected format: gigantic_annotations-database_{database_name}-{phyloname}.tsv
    """

    prefix = f"gigantic_annotations-database_{database_name}-"
    suffix = '.tsv'

    if filename.startswith( prefix ) and filename.endswith( suffix ):
        phyloname = filename[ len( prefix ) : -len( suffix ) ]
    else:
        # Fallback: try to extract from filename
        phyloname = filename.replace( '.tsv', '' )

    return phyloname


def count_statistics_for_database_file( file_path: Path, logger: logging.Logger ) -> dict:
    """
    Parse a single standardized 7-column database TSV file and count statistics.

    Returns a dictionary with:
        total_annotations: int
        unique_proteins: set
        unique_identifiers: set
    """

    total_annotations = 0
    unique_proteins = set()
    unique_identifiers = set()

    with open( file_path, 'r' ) as input_database_file:
        # Phyloname (GIGANTIC phyloname for the species)	Sequence_Identifier (...)	...
        # Metazoa_Chordata_...Homo_sapiens	XP_027047018.1	27	283	pfam	PF00069	Protein kinase domain
        for line in input_database_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            total_annotations += 1

            sequence_identifier = parts[ 1 ]
            annotation_identifier = parts[ 5 ]

            unique_proteins.add( sequence_identifier )
            unique_identifiers.add( annotation_identifier )

    return {
        'total_annotations': total_annotations,
        'unique_proteins': unique_proteins,
        'unique_identifiers': unique_identifiers,
    }


def compile_statistics( tool_names___tool_records: dict, database_directory: Path,
                         output_directory: Path, logger: logging.Logger ) -> None:
    """
    Scan all database directories for per-species TSV files and compile statistics.
    Write the annotation statistics and database completeness output files.
    """

    # =========================================================================
    # Determine which databases to scan based on tool availability
    # =========================================================================

    databases_to_scan = []

    # All databases use the same flat pattern: database_{name}/
    for tool_name in TOOL_NAMES___DATABASE_NAMES:
        if tool_name in tool_names___tool_records and tool_names___tool_records[ tool_name ][ 'tool_available' ] == 'yes':
            database_names = TOOL_NAMES___DATABASE_NAMES[ tool_name ]
            for database_name in database_names:
                database_path = database_directory / f"database_{database_name}"
                databases_to_scan.append( {
                    'database_name': database_name,
                    'database_directory': database_path,
                    'parent_tool': tool_name,
                } )

    logger.info( f"Databases to scan: {len( databases_to_scan )}" )

    if len( databases_to_scan ) == 0:
        logger.error( "CRITICAL ERROR: No database directories found to scan!" )
        logger.error( "Parser scripts (003-007) must be run before compiling statistics." )
        sys.exit( 1 )

    for database_record in databases_to_scan:
        logger.debug( f"  {database_record[ 'database_name' ]}: {database_record[ 'database_directory' ]}" )

    # =========================================================================
    # Scan all database directories and collect statistics
    # =========================================================================

    # List of statistics records: each is a dict with phyloname, database_name, counts
    statistics_records = []

    # Track all phylonames and their annotations across all databases
    # phyloname -> set of all unique proteins across all databases
    phylonames___all_unique_proteins = {}
    # phyloname -> list of database names with data
    phylonames___databases_with_data = {}
    # phyloname -> total annotations across all databases
    phylonames___total_annotations = {}

    total_files_scanned = 0
    total_databases_with_data = 0

    for database_record in databases_to_scan:
        database_name = database_record[ 'database_name' ]
        database_path = database_record[ 'database_directory' ]

        logger.info( f"  Scanning database: {database_name}" )

        if not database_path.exists():
            logger.info( f"    Directory does not exist: {database_path}" )
            logger.info( f"    Skipping {database_name} (no parsed data available)" )
            continue

        if not database_path.is_dir():
            logger.warning( f"    WARNING: Path exists but is not a directory: {database_path}" )
            continue

        # Find all per-species TSV files in this database directory
        database_files = sorted( database_path.glob( 'gigantic_annotations-database_*.tsv' ) )

        if len( database_files ) == 0:
            logger.info( f"    No database TSV files found in {database_path}" )
            continue

        total_databases_with_data += 1
        logger.info( f"    Found {len( database_files )} species file(s)" )

        for database_file in database_files:
            total_files_scanned += 1

            phyloname = extract_phyloname_from_database_filename( database_file.name, database_name )

            # Count statistics for this file
            file_statistics = count_statistics_for_database_file( database_file, logger )

            total_annotations = file_statistics[ 'total_annotations' ]
            unique_proteins = file_statistics[ 'unique_proteins' ]
            unique_identifiers = file_statistics[ 'unique_identifiers' ]

            unique_proteins_count = len( unique_proteins )
            unique_identifiers_count = len( unique_identifiers )

            # Calculate annotations per protein
            if unique_proteins_count > 0:
                annotations_per_protein = total_annotations / unique_proteins_count
            else:
                annotations_per_protein = 0.0

            # Store statistics record
            statistics_records.append( {
                'phyloname': phyloname,
                'database_name': database_name,
                'total_annotations': total_annotations,
                'unique_proteins_annotated': unique_proteins_count,
                'unique_identifiers': unique_identifiers_count,
                'annotations_per_protein': annotations_per_protein,
            } )

            # Update per-phyloname tracking
            if phyloname not in phylonames___all_unique_proteins:
                phylonames___all_unique_proteins[ phyloname ] = set()
            phylonames___all_unique_proteins[ phyloname ].update( unique_proteins )

            if phyloname not in phylonames___databases_with_data:
                phylonames___databases_with_data[ phyloname ] = []
            if total_annotations > 0:
                phylonames___databases_with_data[ phyloname ].append( database_name )

            if phyloname not in phylonames___total_annotations:
                phylonames___total_annotations[ phyloname ] = 0
            phylonames___total_annotations[ phyloname ] += total_annotations

            logger.debug( f"      {phyloname}: {total_annotations} annotations, {unique_proteins_count} proteins, {unique_identifiers_count} identifiers" )

    # =========================================================================
    # Validate that we found data
    # =========================================================================

    if len( statistics_records ) == 0:
        logger.error( "CRITICAL ERROR: No annotation statistics were collected!" )
        logger.error( f"Scanned {len( databases_to_scan )} database directories" )
        logger.error( "Database directories may be empty or contain no standardized TSV files." )
        logger.error( "Ensure parser scripts (003-007) have been run successfully." )
        sys.exit( 1 )

    if total_files_scanned == 0:
        logger.error( "CRITICAL ERROR: No database files were scanned!" )
        logger.error( "Database directories exist but contain no per-species TSV files." )
        sys.exit( 1 )

    # =========================================================================
    # Write annotation statistics output file
    # =========================================================================

    output_statistics_path = output_directory / '8_ai-annotation_statistics.tsv'

    with open( output_statistics_path, 'w' ) as output_statistics_file:
        # Write header
        header = 'Phyloname (phylogenetic name of species)' + '\t'
        header += 'Database_Name (annotation database name)' + '\t'
        header += 'Total_Annotations (total annotation rows for this species and database)' + '\t'
        header += 'Unique_Proteins_Annotated (count of distinct proteins with annotations)' + '\t'
        header += 'Unique_Identifiers (count of distinct annotation identifiers)' + '\t'
        header += 'Annotations_Per_Protein (average annotations per annotated protein)' + '\n'
        output_statistics_file.write( header )

        # Sort records by phyloname then database name for consistent output
        sorted_records = sorted( statistics_records, key = lambda record: ( record[ 'phyloname' ], record[ 'database_name' ] ) )

        for record in sorted_records:
            output = record[ 'phyloname' ] + '\t'
            output += record[ 'database_name' ] + '\t'
            output += str( record[ 'total_annotations' ] ) + '\t'
            output += str( record[ 'unique_proteins_annotated' ] ) + '\t'
            output += str( record[ 'unique_identifiers' ] ) + '\t'
            output += f"{record[ 'annotations_per_protein' ]:.2f}" + '\n'
            output_statistics_file.write( output )

    logger.info( f"Wrote annotation statistics to: {output_statistics_path}" )

    # =========================================================================
    # Write database completeness output file
    # =========================================================================

    output_completeness_path = output_directory / '8_ai-database_completeness.tsv'

    with open( output_completeness_path, 'w' ) as output_completeness_file:
        # Write header
        header = 'Phyloname (phylogenetic name of species)' + '\t'
        header += 'Databases_With_Data_Count (number of databases that have annotations for this species)' + '\t'
        header += 'Databases_With_Data_List (comma delimited list of database names with data)' + '\t'
        header += 'Total_Annotations_All_Databases (sum of all annotation rows across databases)' + '\t'
        header += 'Total_Unique_Proteins (count of distinct proteins with any annotation)' + '\n'
        output_completeness_file.write( header )

        # Sort by phyloname for consistent output
        sorted_phylonames = sorted( phylonames___all_unique_proteins.keys() )

        for phyloname in sorted_phylonames:
            databases_with_data = phylonames___databases_with_data.get( phyloname, [] )
            databases_with_data_count = len( databases_with_data )
            databases_with_data_list = ','.join( sorted( databases_with_data ) )
            total_annotations = phylonames___total_annotations.get( phyloname, 0 )
            total_unique_proteins = len( phylonames___all_unique_proteins[ phyloname ] )

            output = phyloname + '\t'
            output += str( databases_with_data_count ) + '\t'
            output += databases_with_data_list + '\t'
            output += str( total_annotations ) + '\t'
            output += str( total_unique_proteins ) + '\n'
            output_completeness_file.write( output )

    logger.info( f"Wrote database completeness to: {output_completeness_path}" )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 008 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Databases scanned: {len( databases_to_scan )}" )
    logger.info( f"  Databases with data: {total_databases_with_data}" )
    logger.info( f"  Total files scanned: {total_files_scanned}" )
    logger.info( f"  Total statistics records: {len( statistics_records )}" )
    logger.info( f"  Unique species found: {len( sorted_phylonames )}" )
    logger.info( "" )

    # Per-database summary
    logger.info( "Per-database annotation totals:" )
    database_names___total_annotation_counts = {}
    for record in statistics_records:
        database_name = record[ 'database_name' ]
        if database_name not in database_names___total_annotation_counts:
            database_names___total_annotation_counts[ database_name ] = 0
        database_names___total_annotation_counts[ database_name ] += record[ 'total_annotations' ]

    for database_name in sorted( database_names___total_annotation_counts.keys() ):
        total_count = database_names___total_annotation_counts[ database_name ]
        logger.info( f"  {database_name:<20s} {total_count:>12,d}" )

    logger.info( "" )
    logger.info( f"  Output files:" )
    logger.info( f"    {output_statistics_path}" )
    logger.info( f"    {output_completeness_path}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Compile comprehensive annotation statistics across all database types and all species'
    )

    parser.add_argument(
        '--discovery-manifest',
        type = str,
        required = True,
        help = 'Path to 1_ai-tool_discovery_manifest.tsv from script 001'
    )

    parser.add_argument(
        '--database-dir',
        type = str,
        default = '.',
        help = 'Directory containing database_pfam/, database_gene3d/, ..., database_deeploc/, etc. (default: current directory)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Output directory for statistics files (default: current directory)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    discovery_manifest_path = Path( arguments.discovery_manifest )
    database_directory = Path( arguments.database_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 008: Compile Annotation Statistics" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Validate inputs
    # =========================================================================

    if not database_directory.exists():
        logger.error( "CRITICAL ERROR: Database directory does not exist!" )
        logger.error( f"Expected path: {database_directory}" )
        logger.error( "Ensure parser scripts (003-007) have been run to create database directories." )
        sys.exit( 1 )

    # =========================================================================
    # Load discovery manifest
    # =========================================================================

    tool_names___tool_records = load_discovery_manifest( discovery_manifest_path, logger )

    # =========================================================================
    # Compile statistics
    # =========================================================================

    compile_statistics( tool_names___tool_records, database_directory, output_directory, logger )


if __name__ == '__main__':
    main()
