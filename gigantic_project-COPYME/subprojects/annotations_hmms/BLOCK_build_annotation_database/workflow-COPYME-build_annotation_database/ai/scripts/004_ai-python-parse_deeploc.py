#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Parse DeepLoc CSV predictions into standardized annotation database format
# Human: Eric Edsinger

"""
004_ai-python-parse_deeploc.py

Parses DeepLoc subcellular localization prediction CSV files (one per species)
into standardized GIGANTIC annotation database files.

DeepLoc predicts the subcellular localization of proteins. Each protein receives
a single localization prediction (e.g., Cytoplasm, Nucleus, Mitochondrion) with
an associated probability score. Because this is a whole-protein prediction,
domain coordinates are set to NA.

DeepLoc CSV format (with header):
    Col 0: Protein_ID       - Protein accession
    Col 1: Localizations    - Predicted localization (e.g., Cytoplasm)
    Col 2: Signals          - Signal type if any
    Col 3+: Per-class probability scores (columns vary by DeepLoc version)

Output standardized 7-column TSV format:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Output directory structure:
    database_deeploc/
        gigantic_annotations-database_deeploc-{phyloname}.tsv

Input:
    --discovery-manifest: Path to 1_ai-tool_discovery_manifest.tsv from script 001
    --output-dir: Directory for output files

Output:
    database_deeploc/ directory with per-species TSV files
    4_ai-log-parse_deeploc.log

Usage:
    python3 004_ai-python-parse_deeploc.py \\
        --discovery-manifest 1_ai-tool_discovery_manifest.tsv \\
        --output-dir .
"""

import argparse
import csv
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '004_parse_deeploc' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '4_ai-log-parse_deeploc.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_discovery_manifest( manifest_path: Path, logger: logging.Logger ) -> dict:
    """
    Read the discovery manifest and return the deeploc tool record.
    Returns a dictionary with tool information or exits if deeploc is not available.
    """

    logger.info( f"Reading discovery manifest: {manifest_path}" )

    if not manifest_path.exists():
        logger.error( "CRITICAL ERROR: Discovery manifest does not exist!" )
        logger.error( f"Expected path: {manifest_path}" )
        logger.error( "Run script 001 (discover_tool_outputs) first." )
        sys.exit( 1 )

    deeploc_record = None

    with open( manifest_path, 'r' ) as input_manifest:
        # Tool_Name (name of annotation tool)	Tool_Available (yes or no ...)	...
        # deeploc	yes	output_to_input/BLOCK_deeploc	5	*_deeploc_predictions.csv
        for line in input_manifest:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Tool_Name' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 5:
                continue

            tool_name = parts[ 0 ]

            if tool_name == 'deeploc':
                deeploc_record = {
                    'tool_name': tool_name,
                    'tool_available': parts[ 1 ],
                    'output_directory': parts[ 2 ],
                    'file_count': int( parts[ 3 ] ),
                    'file_pattern': parts[ 4 ],
                }
                break

    if deeploc_record is None:
        logger.error( "CRITICAL ERROR: No deeploc entry found in discovery manifest!" )
        logger.error( f"Manifest path: {manifest_path}" )
        logger.error( "The discovery manifest may be corrupted or incomplete." )
        sys.exit( 1 )

    if deeploc_record[ 'tool_available' ] != 'yes':
        logger.error( "CRITICAL ERROR: DeepLoc results are not available!" )
        logger.error( "The discovery manifest shows deeploc as unavailable." )
        logger.error( "Complete the BLOCK_deeploc workflow before running this script." )
        sys.exit( 1 )

    logger.info( f"  DeepLoc output directory: {deeploc_record[ 'output_directory' ]}" )
    logger.info( f"  Expected file count: {deeploc_record[ 'file_count' ]}" )

    return deeploc_record


def extract_phyloname_from_filename( filename: str, logger: logging.Logger ) -> str:
    """
    Extract the GIGANTIC phyloname from a DeepLoc result filename.
    Expected format: {phyloname}_deeploc_predictions.csv
    """

    suffix = '_deeploc_predictions.csv'

    if filename.endswith( suffix ):
        phyloname = filename[ : -len( suffix ) ]
    else:
        # Fallback: remove .csv extension and try to use as phyloname
        phyloname = filename.replace( '.csv', '' )
        logger.warning( f"  WARNING: Filename does not match expected pattern: {filename}" )
        logger.warning( f"  Using extracted name: {phyloname}" )

    return phyloname


def write_standardized_header() -> str:
    """Return the standardized 7-column header string for database TSV files."""

    header = 'Phyloname (GIGANTIC phyloname for the species)' + '\t'
    header += 'Sequence_Identifier (protein identifier from proteome)' + '\t'
    header += 'Domain_Start (start position of annotation on protein sequence or NA for whole-protein predictions)' + '\t'
    header += 'Domain_Stop (stop position of annotation on protein sequence or NA for whole-protein predictions)' + '\t'
    header += 'Database_Name (name of annotation database)' + '\t'
    header += 'Annotation_Identifier (predicted subcellular localization)' + '\t'
    header += 'Annotation_Details (localization prediction with probability score)' + '\n'

    return header


def parse_deeploc_files( deeploc_record: dict, output_directory: Path,
                          logger: logging.Logger ) -> None:
    """
    Parse all DeepLoc CSV prediction files found in the tool output directory.
    Create standardized TSV files per species.
    """

    deeploc_output_directory = Path( deeploc_record[ 'output_directory' ] )
    file_pattern = deeploc_record[ 'file_pattern' ]

    # =========================================================================
    # Find DeepLoc result files
    # =========================================================================

    result_files = sorted( deeploc_output_directory.glob( file_pattern ) )

    if len( result_files ) == 0:
        logger.error( "CRITICAL ERROR: No DeepLoc result files found!" )
        logger.error( f"Searched directory: {deeploc_output_directory}" )
        logger.error( f"File pattern: {file_pattern}" )
        sys.exit( 1 )

    logger.info( f"Found {len( result_files )} DeepLoc result file(s) to parse" )

    # =========================================================================
    # Create output directory structure
    # =========================================================================

    database_output_directory = output_directory / 'database_deeploc'
    database_output_directory.mkdir( parents = True, exist_ok = True )

    # =========================================================================
    # Global statistics tracking
    # =========================================================================

    total_proteins_read = 0
    total_annotations_written = 0
    species_count = 0

    # =========================================================================
    # Process each species result file
    # =========================================================================

    for result_file in result_files:
        species_count += 1
        phyloname = extract_phyloname_from_filename( result_file.name, logger )

        logger.info( f"  Processing species {species_count}/{len( result_files )}: {phyloname}" )
        logger.debug( f"    File: {result_file}" )

        # =====================================================================
        # Parse DeepLoc CSV file
        # =====================================================================

        annotation_rows = []
        species_protein_count = 0

        with open( result_file, 'r' ) as input_deeploc_csv:
            csv_reader = csv.reader( input_deeploc_csv )

            # Read header to identify column positions
            header_row = next( csv_reader, None )

            if header_row is None:
                logger.warning( f"    WARNING: File is empty, skipping: {result_file.name}" )
                continue

            # Identify key column indices from header
            # DeepLoc CSV headers vary by version but typically include:
            # Protein_ID (or similar), Localizations, Signals, and probability columns
            header_names___column_indices = {}
            for column_index, column_name in enumerate( header_row ):
                column_name_stripped = column_name.strip()
                header_names___column_indices[ column_name_stripped ] = column_index

            logger.debug( f"    CSV columns: {list( header_names___column_indices.keys() )}" )

            # Identify protein ID column (first column)
            protein_id_column_index = 0

            # Identify localization column
            localization_column_index = None
            for candidate_name in [ 'Localizations', 'Localization', 'localizations', 'localization' ]:
                if candidate_name in header_names___column_indices:
                    localization_column_index = header_names___column_indices[ candidate_name ]
                    break

            if localization_column_index is None:
                # Fallback: assume second column is localization
                localization_column_index = 1
                logger.warning( f"    WARNING: Could not identify localization column by name" )
                logger.warning( f"    Using column index 1 as localization" )

            # Identify signal column if present
            signal_column_index = None
            for candidate_name in [ 'Signals', 'Signal', 'signals', 'signal' ]:
                if candidate_name in header_names___column_indices:
                    signal_column_index = header_names___column_indices[ candidate_name ]
                    break

            # Collect probability column names and indices for annotation details
            probability_column_names = []
            probability_column_indices = []
            for column_name, column_index in header_names___column_indices.items():
                # Skip known non-probability columns
                if column_index in [ protein_id_column_index, localization_column_index ]:
                    continue
                if signal_column_index is not None and column_index == signal_column_index:
                    continue
                # Remaining columns are assumed to be probability scores
                probability_column_names.append( column_name )
                probability_column_indices.append( column_index )

            # Parse data rows
            for row in csv_reader:
                if len( row ) == 0:
                    continue

                species_protein_count += 1
                total_proteins_read += 1

                protein_id = row[ protein_id_column_index ].strip()
                localization = row[ localization_column_index ].strip() if len( row ) > localization_column_index else ''

                if not protein_id:
                    logger.warning( f"    WARNING: Empty protein ID at row {species_protein_count}, skipping" )
                    continue

                if not localization:
                    logger.warning( f"    WARNING: Empty localization for protein {protein_id}, skipping" )
                    continue

                # Build annotation details: localization with probability score
                # Find the probability score for the predicted localization
                annotation_details_parts = [ localization ]

                # Look for probability column matching the prediction
                for probability_index, probability_column_name in enumerate( probability_column_names ):
                    column_data_index = probability_column_indices[ probability_index ]
                    if column_data_index < len( row ):
                        probability_value = row[ column_data_index ].strip()
                        if probability_value:
                            # Check if this column name matches or contains the localization name
                            if localization.lower() in probability_column_name.lower():
                                annotation_details_parts.append( f"probability={probability_value}" )
                                break

                # If no matching probability found, include all probabilities as a summary
                if len( annotation_details_parts ) == 1:
                    # Try to find the highest probability among all columns
                    max_probability = ''
                    for probability_index, probability_column_name in enumerate( probability_column_names ):
                        column_data_index = probability_column_indices[ probability_index ]
                        if column_data_index < len( row ):
                            probability_value = row[ column_data_index ].strip()
                            if probability_value:
                                try:
                                    float_value = float( probability_value )
                                    if not max_probability or float_value > float( max_probability ):
                                        max_probability = probability_value
                                except ValueError:
                                    pass

                    if max_probability:
                        annotation_details_parts.append( f"probability={max_probability}" )

                annotation_details = ','.join( annotation_details_parts )

                annotation_row = (
                    phyloname,
                    protein_id,
                    'NA',
                    'NA',
                    'deeploc',
                    localization,
                    annotation_details,
                )

                annotation_rows.append( annotation_row )

        # =====================================================================
        # Write standardized output file for this species
        # =====================================================================

        if len( annotation_rows ) == 0:
            logger.warning( f"    WARNING: No annotations extracted for {phyloname}" )
            logger.warning( f"    Proteins read: {species_protein_count}" )
            continue

        output_file_path = database_output_directory / f"gigantic_annotations-database_deeploc-{phyloname}.tsv"

        with open( output_file_path, 'w' ) as output_database_file:
            # Write header
            output_database_file.write( write_standardized_header() )

            # Write annotation rows
            for annotation_row in annotation_rows:
                output = annotation_row[ 0 ] + '\t'
                output += annotation_row[ 1 ] + '\t'
                output += annotation_row[ 2 ] + '\t'
                output += annotation_row[ 3 ] + '\t'
                output += annotation_row[ 4 ] + '\t'
                output += annotation_row[ 5 ] + '\t'
                output += annotation_row[ 6 ] + '\n'
                output_database_file.write( output )

        annotations_written = len( annotation_rows )
        total_annotations_written += annotations_written

        logger.info( f"    Proteins parsed: {species_protein_count}" )
        logger.info( f"    Annotations written: {annotations_written}" )

    # =========================================================================
    # Validate outputs
    # =========================================================================

    if total_annotations_written == 0:
        logger.error( "CRITICAL ERROR: No annotations were written to any database files!" )
        logger.error( f"Read {total_proteins_read} proteins from {len( result_files )} files" )
        logger.error( "DeepLoc result files may be empty or in unexpected format." )
        sys.exit( 1 )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 004 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species processed: {species_count}" )
    logger.info( f"  Total proteins read: {total_proteins_read}" )
    logger.info( f"  Total annotations written: {total_annotations_written}" )
    logger.info( f"  Output directory: {database_output_directory}" )

    # Count output files
    output_files_list = list( database_output_directory.glob( '*.tsv' ) )
    logger.info( f"  Output files created: {len( output_files_list )}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Parse DeepLoc CSV predictions into standardized annotation database format'
    )

    parser.add_argument(
        '--discovery-manifest',
        type = str,
        required = True,
        help = 'Path to 1_ai-tool_discovery_manifest.tsv from script 001'
    )

    parser.add_argument(
        '--annotations-dir',
        type = str,
        required = True,
        help = 'Path to annotations_hmms root directory containing BLOCK_* directories'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Output directory for database files (default: current directory)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    discovery_manifest_path = Path( arguments.discovery_manifest )
    annotations_directory = Path( arguments.annotations_dir ).resolve()
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 004: Parse DeepLoc Predictions" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load inputs
    # =========================================================================

    deeploc_record = load_discovery_manifest( discovery_manifest_path, logger )

    # Resolve relative output_directory from manifest against annotations_hmms root
    deeploc_record[ 'output_directory' ] = str( annotations_directory / deeploc_record[ 'output_directory' ] )

    # =========================================================================
    # Parse DeepLoc files
    # =========================================================================

    parse_deeploc_files( deeploc_record, output_directory, logger )


if __name__ == '__main__':
    main()
