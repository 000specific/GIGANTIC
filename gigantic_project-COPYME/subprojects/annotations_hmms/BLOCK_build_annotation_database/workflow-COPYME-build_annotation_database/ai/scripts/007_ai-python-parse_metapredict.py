#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Parse MetaPredict IDR predictions into standardized annotation database format
# Human: Eric Edsinger

"""
007_ai-python-parse_metapredict.py

Parses MetaPredict intrinsically disordered region (IDR) prediction TSV files
(one per species) into standardized GIGANTIC annotation database files.

MetaPredict identifies intrinsically disordered regions (IDRs) in protein
sequences. Each protein may have zero or more disordered regions, reported
as boundary coordinate pairs. Proteins with multiple IDRs produce multiple
rows in the output (one per disordered region).

MetaPredict IDR TSV format (with header):
    Col 0: Protein_Identifier  - Protein accession
    Col 1: IDR_Boundaries      - Comma-separated start-end pairs (e.g., "10-45,120-180")
    Col 2: IDR_Count           - Number of disordered regions
    Col 3: Sequence_Length     - Length of the protein sequence

Output standardized 7-column TSV format:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Output directory structure:
    database_metapredict/
        gigantic_annotations-database_metapredict-{phyloname}.tsv

Input:
    --discovery-manifest: Path to 1_ai-tool_discovery_manifest.tsv from script 001
    --output-dir: Directory for output files

Output:
    database_metapredict/ directory with per-species TSV files
    7_ai-log-parse_metapredict.log

Usage:
    python3 007_ai-python-parse_metapredict.py \\
        --discovery-manifest 1_ai-tool_discovery_manifest.tsv \\
        --output-dir .
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '007_parse_metapredict' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '7_ai-log-parse_metapredict.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_discovery_manifest( manifest_path: Path, logger: logging.Logger ) -> dict:
    """
    Read the discovery manifest and return the metapredict tool record.
    Returns a dictionary with tool information or exits if metapredict is not available.
    """

    logger.info( f"Reading discovery manifest: {manifest_path}" )

    if not manifest_path.exists():
        logger.error( "CRITICAL ERROR: Discovery manifest does not exist!" )
        logger.error( f"Expected path: {manifest_path}" )
        logger.error( "Run script 001 (discover_tool_outputs) first." )
        sys.exit( 1 )

    metapredict_record = None

    with open( manifest_path, 'r' ) as input_manifest:
        # Tool_Name (name of annotation tool)	Tool_Available (yes or no ...)	...
        # metapredict	yes	/path/to/output_to_input	5	*_metapredict_idrs.tsv
        for line in input_manifest:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Tool_Name' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 5:
                continue

            tool_name = parts[ 0 ]

            if tool_name == 'metapredict':
                metapredict_record = {
                    'tool_name': tool_name,
                    'tool_available': parts[ 1 ],
                    'output_directory': parts[ 2 ],
                    'file_count': int( parts[ 3 ] ),
                    'file_pattern': parts[ 4 ],
                }
                break

    if metapredict_record is None:
        logger.error( "CRITICAL ERROR: No metapredict entry found in discovery manifest!" )
        logger.error( f"Manifest path: {manifest_path}" )
        logger.error( "The discovery manifest may be corrupted or incomplete." )
        sys.exit( 1 )

    if metapredict_record[ 'tool_available' ] != 'yes':
        logger.error( "CRITICAL ERROR: MetaPredict results are not available!" )
        logger.error( "The discovery manifest shows metapredict as unavailable." )
        logger.error( "Complete the BLOCK_metapredict workflow before running this script." )
        sys.exit( 1 )

    logger.info( f"  MetaPredict output directory: {metapredict_record[ 'output_directory' ]}" )
    logger.info( f"  Expected file count: {metapredict_record[ 'file_count' ]}" )

    return metapredict_record


def extract_phyloname_from_filename( filename: str, logger: logging.Logger ) -> str:
    """
    Extract the GIGANTIC phyloname from a MetaPredict result filename.
    Expected format: {phyloname}_metapredict_idrs.tsv
    """

    suffix = '_metapredict_idrs.tsv'

    if filename.endswith( suffix ):
        phyloname = filename[ : -len( suffix ) ]
    else:
        # Fallback: remove .tsv extension and try to use as phyloname
        phyloname = filename.replace( '.tsv', '' )
        logger.warning( f"  WARNING: Filename does not match expected pattern: {filename}" )
        logger.warning( f"  Using extracted name: {phyloname}" )

    return phyloname


def write_standardized_header() -> str:
    """Return the standardized 7-column header string for database TSV files."""

    header = 'Phyloname (GIGANTIC phyloname for the species)' + '\t'
    header += 'Sequence_Identifier (protein identifier from proteome)' + '\t'
    header += 'Domain_Start (start position of disordered region on protein sequence)' + '\t'
    header += 'Domain_Stop (stop position of disordered region on protein sequence)' + '\t'
    header += 'Database_Name (name of annotation database)' + '\t'
    header += 'Annotation_Identifier (always IDR for intrinsically disordered region)' + '\t'
    header += 'Annotation_Details (disorder region with boundary coordinates)' + '\n'

    return header


def parse_idr_boundaries( boundaries_string: str, protein_identifier: str,
                           logger: logging.Logger ) -> list:
    """
    Parse the IDR boundaries string into a list of (start, stop) tuples.

    Input format: "10-45,120-180,250-300" (comma-separated start-end pairs)
    Returns: [ ( 10, 45 ), ( 120, 180 ), ( 250, 300 ) ]
    """

    regions = []

    if not boundaries_string or boundaries_string.strip() == '':
        return regions

    boundaries_string = boundaries_string.strip()

    # Split by comma to get individual boundary pairs
    boundary_pairs = boundaries_string.split( ',' )

    for boundary_pair in boundary_pairs:
        boundary_pair = boundary_pair.strip()

        if not boundary_pair:
            continue

        # Split by dash to get start and end
        parts_boundary = boundary_pair.split( '-' )

        if len( parts_boundary ) != 2:
            logger.warning( f"    WARNING: Invalid boundary pair format '{boundary_pair}' for {protein_identifier}, skipping this region" )
            continue

        try:
            region_start = int( parts_boundary[ 0 ].strip() )
            region_stop = int( parts_boundary[ 1 ].strip() )
        except ValueError:
            logger.warning( f"    WARNING: Non-integer boundary values '{boundary_pair}' for {protein_identifier}, skipping this region" )
            continue

        if region_start <= 0 or region_stop <= 0:
            logger.warning( f"    WARNING: Invalid boundary coordinates ({region_start}-{region_stop}) for {protein_identifier}, skipping" )
            continue

        if region_start > region_stop:
            logger.warning( f"    WARNING: Start ({region_start}) > stop ({region_stop}) for {protein_identifier}, swapping" )
            region_start, region_stop = region_stop, region_start

        regions.append( ( region_start, region_stop ) )

    return regions


def parse_metapredict_files( metapredict_record: dict, output_directory: Path,
                              logger: logging.Logger ) -> None:
    """
    Parse all MetaPredict IDR TSV files found in the output_to_input directory.
    Create standardized TSV files per species.
    """

    metapredict_output_directory = Path( metapredict_record[ 'output_directory' ] )
    file_pattern = metapredict_record[ 'file_pattern' ]

    # =========================================================================
    # Find MetaPredict result files
    # =========================================================================

    result_files = sorted( metapredict_output_directory.glob( file_pattern ) )

    if len( result_files ) == 0:
        logger.error( "CRITICAL ERROR: No MetaPredict result files found!" )
        logger.error( f"Searched directory: {metapredict_output_directory}" )
        logger.error( f"File pattern: {file_pattern}" )
        sys.exit( 1 )

    logger.info( f"Found {len( result_files )} MetaPredict result file(s) to parse" )

    # =========================================================================
    # Create output directory structure
    # =========================================================================

    database_output_directory = output_directory / 'database_metapredict'
    database_output_directory.mkdir( parents = True, exist_ok = True )

    # =========================================================================
    # Global statistics tracking
    # =========================================================================

    total_proteins_read = 0
    total_idr_regions_found = 0
    total_annotations_written = 0
    total_proteins_with_idrs = 0
    total_proteins_without_idrs = 0
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
        # Parse MetaPredict IDR TSV file
        # =====================================================================

        annotation_rows = []
        species_protein_count = 0
        species_proteins_with_idrs = 0
        species_proteins_without_idrs = 0
        species_idr_region_count = 0

        with open( result_file, 'r' ) as input_metapredict_results:
            # Protein_Identifier	IDR_Boundaries	IDR_Count	Sequence_Length
            # XP_027047018.1	10-45,120-180	2	543
            header_line = None

            for line in input_metapredict_results:
                line = line.strip()

                # Skip empty lines and comment lines
                if not line or line.startswith( '#' ):
                    continue

                # Detect and skip header line
                if header_line is None:
                    # Check if this looks like a header
                    if line.startswith( 'Protein' ) or line.startswith( 'ID' ) or 'IDR_Boundaries' in line or 'Identifier' in line:
                        header_line = line
                        logger.debug( f"    Header: {header_line}" )
                        continue
                    else:
                        # No header detected, treat this line as data
                        header_line = 'no_header_detected'

                parts = line.split( '\t' )

                if len( parts ) < 3:
                    logger.warning( f"    WARNING: Line has fewer than 3 columns ({len( parts )}), skipping" )
                    logger.debug( f"    Skipped line: {line[ :200 ]}" )
                    continue

                species_protein_count += 1
                total_proteins_read += 1

                protein_identifier = parts[ 0 ].strip()
                idr_boundaries_string = parts[ 1 ].strip()
                idr_count_string = parts[ 2 ].strip()

                if not protein_identifier:
                    logger.warning( f"    WARNING: Empty protein identifier at row {species_protein_count}, skipping" )
                    continue

                # Check if this protein has any IDRs
                try:
                    idr_count = int( idr_count_string )
                except ValueError:
                    idr_count = 0

                if idr_count == 0 or not idr_boundaries_string or idr_boundaries_string in [ '', 'NA', 'None', 'none' ]:
                    species_proteins_without_idrs += 1
                    total_proteins_without_idrs += 1
                    continue

                # Parse the boundary coordinates
                idr_regions = parse_idr_boundaries( idr_boundaries_string, protein_identifier, logger )

                if len( idr_regions ) == 0:
                    species_proteins_without_idrs += 1
                    total_proteins_without_idrs += 1
                    continue

                species_proteins_with_idrs += 1
                total_proteins_with_idrs += 1

                # Create one annotation row per IDR region
                for idr_region in idr_regions:
                    region_start = idr_region[ 0 ]
                    region_stop = idr_region[ 1 ]

                    species_idr_region_count += 1
                    total_idr_regions_found += 1

                    # Build annotation details
                    annotation_details = 'IDR,start=' + str( region_start ) + ',stop=' + str( region_stop )

                    annotation_row = (
                        phyloname,
                        protein_identifier,
                        str( region_start ),
                        str( region_stop ),
                        'metapredict',
                        'IDR',
                        annotation_details,
                    )

                    annotation_rows.append( annotation_row )

        # =====================================================================
        # Write standardized output file for this species
        # =====================================================================

        if len( annotation_rows ) == 0:
            logger.info( f"    No IDR regions found for {phyloname}" )
            logger.info( f"    Proteins read: {species_protein_count}" )
            logger.info( f"    This may be expected for some species." )
            # Still create an empty file with header for consistency
            output_file_path = database_output_directory / f"gigantic_annotations-database_metapredict-{phyloname}.tsv"

            with open( output_file_path, 'w' ) as output_database_file:
                output_database_file.write( write_standardized_header() )

            continue

        output_file_path = database_output_directory / f"gigantic_annotations-database_metapredict-{phyloname}.tsv"

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
        logger.info( f"    Proteins with IDRs: {species_proteins_with_idrs}" )
        logger.info( f"    Proteins without IDRs: {species_proteins_without_idrs}" )
        logger.info( f"    IDR regions extracted: {species_idr_region_count}" )

    # =========================================================================
    # Validate outputs
    # =========================================================================

    if total_proteins_read == 0:
        logger.error( "CRITICAL ERROR: No proteins were read from any MetaPredict files!" )
        logger.error( f"Attempted to parse {len( result_files )} files" )
        logger.error( "MetaPredict result files may be empty or in unexpected format." )
        sys.exit( 1 )

    # Note: it is valid for total_annotations_written to be 0 if no proteins
    # have IDRs, though this is unusual for a full proteome
    if total_annotations_written == 0:
        logger.warning( "WARNING: No IDR annotations were written!" )
        logger.warning( f"Read {total_proteins_read} proteins from {len( result_files )} files" )
        logger.warning( "This is unusual for a full proteome - verify MetaPredict output format." )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 007 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species processed: {species_count}" )
    logger.info( f"  Total proteins read: {total_proteins_read}" )
    logger.info( f"  Proteins with IDRs: {total_proteins_with_idrs}" )
    logger.info( f"  Proteins without IDRs: {total_proteins_without_idrs}" )
    logger.info( f"  Total IDR regions extracted: {total_idr_regions_found}" )
    logger.info( f"  Total annotations written: {total_annotations_written}" )
    logger.info( f"  Output directory: {database_output_directory}" )

    # Calculate disorder rate
    if total_proteins_read > 0:
        disorder_rate = ( total_proteins_with_idrs / total_proteins_read ) * 100
        logger.info( f"  Disorder rate (proteins with at least one IDR): {disorder_rate:.1f}%" )

    # Calculate average IDRs per disordered protein
    if total_proteins_with_idrs > 0:
        average_idrs_per_protein = total_idr_regions_found / total_proteins_with_idrs
        logger.info( f"  Average IDRs per disordered protein: {average_idrs_per_protein:.1f}" )

    # Count output files
    output_files_list = list( database_output_directory.glob( '*.tsv' ) )
    logger.info( f"  Output files created: {len( output_files_list )}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Parse MetaPredict IDR predictions into standardized annotation database format'
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
    logger.info( "Script 007: Parse MetaPredict IDR Predictions" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load inputs
    # =========================================================================

    metapredict_record = load_discovery_manifest( discovery_manifest_path, logger )

    # Resolve relative output_directory from manifest against annotations_hmms root
    metapredict_record[ 'output_directory' ] = str( annotations_directory / metapredict_record[ 'output_directory' ] )

    # =========================================================================
    # Parse MetaPredict files
    # =========================================================================

    parse_metapredict_files( metapredict_record, output_directory, logger )


if __name__ == '__main__':
    main()
