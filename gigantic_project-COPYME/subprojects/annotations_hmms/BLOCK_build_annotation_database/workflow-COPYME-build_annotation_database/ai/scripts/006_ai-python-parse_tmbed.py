#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Parse tmbed 3-line predictions into standardized annotation database format
# Human: Eric Edsinger

"""
006_ai-python-parse_tmbed.py

Parses tmbed transmembrane topology prediction files (one per species) in 3-line
format into standardized GIGANTIC annotation database files.

tmbed predicts transmembrane topology using a deep learning approach. Output is
in a 3-line format where each protein has:
    Line 1: >header (FASTA-style header with protein ID)
    Line 2: amino acid sequence
    Line 3: topology string (same length as sequence)

Topology string codes:
    H or h = Transmembrane helix (alpha-helical)
    B or b = Beta-barrel transmembrane segment
    S      = Signal peptide region
    .      = Non-transmembrane / other

Each consecutive stretch of H/h, B/b, or S characters defines one region.
Multi-pass transmembrane proteins produce multiple rows (one per helix/segment).

Output standardized 7-column TSV format:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Output directory structure:
    database_tmbed/
        gigantic_annotations-database_tmbed-{phyloname}.tsv

Input:
    --discovery-manifest: Path to 1_ai-tool_discovery_manifest.tsv from script 001
    --output-dir: Directory for output files

Output:
    database_tmbed/ directory with per-species TSV files
    6_ai-log-parse_tmbed.log

Usage:
    python3 006_ai-python-parse_tmbed.py \\
        --discovery-manifest 1_ai-tool_discovery_manifest.tsv \\
        --proteomes-dir /path/to/proteomes \\
        --output-dir .

If --proteomes-dir is provided, the script also identifies proteins in each
species proteome that have NO tmbed predictions and adds unannotated entries
with identifiers like unannotated_tmbed-1, unannotated_tmbed-2, etc.
The counter is global across all species.
"""

import argparse
import logging
import sys
from pathlib import Path


# =============================================================================
# Topology character classification
# =============================================================================
# Maps topology characters to annotation types.
# Upper and lowercase of the same letter mean the same topology type.
# =============================================================================

TOPOLOGY_CHARACTERS___ANNOTATION_TYPES = {
    'H': 'TM_helix',
    'h': 'TM_helix',
    'B': 'TM_beta_barrel',
    'b': 'TM_beta_barrel',
    'S': 'signal_peptide',
}


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '006_parse_tmbed' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '6_ai-log-parse_tmbed.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_discovery_manifest( manifest_path: Path, logger: logging.Logger ) -> dict:
    """
    Read the discovery manifest and return the tmbed tool record.
    Returns a dictionary with tool information or exits if tmbed is not available.
    """

    logger.info( f"Reading discovery manifest: {manifest_path}" )

    if not manifest_path.exists():
        logger.error( "CRITICAL ERROR: Discovery manifest does not exist!" )
        logger.error( f"Expected path: {manifest_path}" )
        logger.error( "Run script 001 (discover_tool_outputs) first." )
        sys.exit( 1 )

    tmbed_record = None

    with open( manifest_path, 'r' ) as input_manifest:
        # Tool_Name (name of annotation tool)	Tool_Available (yes or no ...)	...
        # tmbed	yes	output_to_input/BLOCK_tmbed	5	*_tmbed_predictions.3line
        for line in input_manifest:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Tool_Name' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 5:
                continue

            tool_name = parts[ 0 ]

            if tool_name == 'tmbed':
                tmbed_record = {
                    'tool_name': tool_name,
                    'tool_available': parts[ 1 ],
                    'output_directory': parts[ 2 ],
                    'file_count': int( parts[ 3 ] ),
                    'file_pattern': parts[ 4 ],
                }
                break

    if tmbed_record is None:
        logger.error( "CRITICAL ERROR: No tmbed entry found in discovery manifest!" )
        logger.error( f"Manifest path: {manifest_path}" )
        logger.error( "The discovery manifest may be corrupted or incomplete." )
        sys.exit( 1 )

    if tmbed_record[ 'tool_available' ] != 'yes':
        logger.error( "CRITICAL ERROR: tmbed results are not available!" )
        logger.error( "The discovery manifest shows tmbed as unavailable." )
        logger.error( "Complete the BLOCK_tmbed workflow before running this script." )
        sys.exit( 1 )

    logger.info( f"  tmbed output directory: {tmbed_record[ 'output_directory' ]}" )
    logger.info( f"  Expected file count: {tmbed_record[ 'file_count' ]}" )

    return tmbed_record


def extract_phyloname_from_filename( filename: str, logger: logging.Logger ) -> str:
    """
    Extract the GIGANTIC phyloname from a tmbed result filename.
    Expected format: {phyloname}_tmbed_predictions.3line
    """

    suffix = '_tmbed_predictions.3line'

    if filename.endswith( suffix ):
        phyloname = filename[ : -len( suffix ) ]
    else:
        # Fallback: remove .3line extension and try to use as phyloname
        phyloname = filename.replace( '.3line', '' )
        logger.warning( f"  WARNING: Filename does not match expected pattern: {filename}" )
        logger.warning( f"  Using extracted name: {phyloname}" )

    return phyloname


def write_standardized_header() -> str:
    """Return the standardized 7-column header string for database TSV files."""

    header = 'Phyloname (GIGANTIC phyloname for the species)' + '\t'
    header += 'Sequence_Identifier (protein identifier from proteome)' + '\t'
    header += 'Domain_Start (start position of transmembrane region on protein sequence 1-indexed)' + '\t'
    header += 'Domain_Stop (stop position of transmembrane region on protein sequence 1-indexed)' + '\t'
    header += 'Database_Name (name of annotation database)' + '\t'
    header += 'Annotation_Identifier (topology type TM_helix or TM_beta_barrel or signal_peptide)' + '\t'
    header += 'Annotation_Details (topology type with start-stop coordinates)' + '\n'

    return header


def load_proteome_protein_identifiers( proteomes_directory: Path, logger: logging.Logger ) -> dict:
    """
    Load protein identifiers from FASTA proteome files.

    Reads all .aa files in the proteomes directory, extracting protein IDs
    from FASTA headers. Returns a dictionary mapping phylonames to sets of
    protein identifiers.

    Proteome files follow GIGANTIC naming: {phyloname}___taxid-assembly-date-type.aa
    FASTA headers: >protein_id description...

    Returns:
        phylonames___protein_identifiers: dict mapping phyloname -> set of protein IDs
    """

    logger.info( f"Loading proteome protein identifiers from: {proteomes_directory}" )

    if not proteomes_directory.exists():
        logger.error( "CRITICAL ERROR: Proteomes directory does not exist!" )
        logger.error( f"Expected path: {proteomes_directory}" )
        logger.error( "Verify proteomes_dir path in the configuration file." )
        logger.error( "Expected: genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/" )
        sys.exit( 1 )

    proteome_files = sorted( proteomes_directory.glob( '*.aa' ) )

    if len( proteome_files ) == 0:
        logger.error( "CRITICAL ERROR: No proteome files (*.aa) found!" )
        logger.error( f"Directory: {proteomes_directory}" )
        logger.error( "The proteomes directory should contain .aa FASTA files." )
        sys.exit( 1 )

    phylonames___protein_identifiers = {}

    for proteome_file in proteome_files:
        # Extract phyloname from filename: {phyloname}___taxid-assembly.aa
        filename_without_extension = proteome_file.stem
        parts_filename = filename_without_extension.split( '___' )
        phyloname = parts_filename[ 0 ]

        # Read FASTA headers to get protein IDs
        protein_identifiers = set()

        with open( proteome_file, 'r' ) as input_proteome:
            # >XP_027047018.1 description text
            # MSTLKQVFYILCLFSGHWAEQPADMQ...
            for line in input_proteome:
                if line.startswith( '>' ):
                    # Protein ID is the first word after >
                    header = line[ 1: ].strip()
                    protein_identifier = header.split()[ 0 ] if header else ''
                    if protein_identifier:
                        protein_identifiers.add( protein_identifier )

        phylonames___protein_identifiers[ phyloname ] = protein_identifiers
        logger.debug( f"  {phyloname}: {len( protein_identifiers )} proteins" )

    logger.info( f"  Loaded proteomes for {len( phylonames___protein_identifiers )} species" )

    total_proteins = sum( len( identifiers ) for identifiers in phylonames___protein_identifiers.values() )
    logger.info( f"  Total protein identifiers: {total_proteins:,d}" )

    return phylonames___protein_identifiers


def extract_topology_regions( topology_string: str ) -> list:
    """
    Extract contiguous regions of transmembrane or signal peptide characters
    from a tmbed topology string.

    Returns a list of tuples: ( annotation_type, start_position, stop_position )
    where positions are 1-indexed (matching protein sequence coordinates).
    """

    regions = []

    if not topology_string:
        return regions

    current_annotation_type = None
    region_start = None

    for position_index, topology_character in enumerate( topology_string ):

        if topology_character in TOPOLOGY_CHARACTERS___ANNOTATION_TYPES:
            annotation_type = TOPOLOGY_CHARACTERS___ANNOTATION_TYPES[ topology_character ]

            if annotation_type == current_annotation_type:
                # Continuation of current region
                pass
            else:
                # End previous region if one was active
                if current_annotation_type is not None:
                    # Convert from 0-indexed to 1-indexed: start+1 through position_index
                    regions.append( ( current_annotation_type, region_start + 1, position_index ) )

                # Start new region
                current_annotation_type = annotation_type
                region_start = position_index

        else:
            # Non-TM character (typically '.')
            if current_annotation_type is not None:
                # End the current region
                regions.append( ( current_annotation_type, region_start + 1, position_index ) )
                current_annotation_type = None
                region_start = None

    # Handle region that extends to the end of the sequence
    if current_annotation_type is not None:
        regions.append( ( current_annotation_type, region_start + 1, len( topology_string ) ) )

    return regions


def parse_tmbed_files( tmbed_record: dict, proteomes_directory: Path, output_directory: Path,
                        logger: logging.Logger ) -> None:
    """
    Parse all tmbed 3-line prediction files found in the tool output directory.
    Create standardized TSV files per species. If proteomes_directory is provided,
    also adds unannotated protein entries with identifiers like unannotated_tmbed-N.
    """

    tmbed_output_directory = Path( tmbed_record[ 'output_directory' ] )
    file_pattern = tmbed_record[ 'file_pattern' ]

    # =========================================================================
    # Find tmbed result files
    # =========================================================================

    result_files = sorted( tmbed_output_directory.glob( file_pattern ) )

    if len( result_files ) == 0:
        logger.error( "CRITICAL ERROR: No tmbed result files found!" )
        logger.error( f"Searched directory: {tmbed_output_directory}" )
        logger.error( f"File pattern: {file_pattern}" )
        sys.exit( 1 )

    logger.info( f"Found {len( result_files )} tmbed result file(s) to parse" )

    # =========================================================================
    # Create output directory structure
    # =========================================================================

    database_output_directory = output_directory / 'database_tmbed'
    database_output_directory.mkdir( parents = True, exist_ok = True )

    # =========================================================================
    # Global statistics tracking
    # =========================================================================

    total_proteins_read = 0
    total_regions_found = 0
    total_annotations_written = 0
    total_proteins_with_transmembrane = 0
    total_proteins_without_transmembrane = 0
    total_transmembrane_helices = 0
    total_beta_barrels = 0
    total_signal_peptides = 0
    species_count = 0

    # =========================================================================
    # Load proteome protein identifiers (if proteomes directory provided)
    # =========================================================================

    phylonames___protein_identifiers = None
    if proteomes_directory is not None:
        phylonames___protein_identifiers = load_proteome_protein_identifiers( proteomes_directory, logger )

    # Track unannotated counts (global across all species)
    unannotated_counter = 0
    total_unannotated_entries_written = 0

    # =========================================================================
    # Process each species result file
    # =========================================================================

    for result_file in result_files:
        species_count += 1
        phyloname = extract_phyloname_from_filename( result_file.name, logger )

        logger.info( f"  Processing species {species_count}/{len( result_files )}: {phyloname}" )
        logger.debug( f"    File: {result_file}" )

        # =====================================================================
        # Parse tmbed 3-line format file
        # =====================================================================

        annotation_rows = []
        species_protein_count = 0
        species_proteins_with_topology = 0
        species_proteins_without_topology = 0
        species_region_count = 0

        with open( result_file, 'r' ) as input_tmbed_results:
            # 3-line format: >header, sequence, topology_string
            # >XP_027047018.1
            # MAWKFLIVCLGLASF...
            # ...SSSS.....HHHHHHHHHHHHHHHHHHHhh....HHHHHHHHHHHHHHHHHH....

            line_counter = 0
            current_protein_identifier = None
            current_sequence = None

            for line in input_tmbed_results:
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                line_counter += 1

                # Line 1 of triplet: FASTA header
                if line.startswith( '>' ):
                    # Extract protein identifier from header
                    # Handle various header formats: >ID, >ID description, >sp|ID|name
                    header_content = line[ 1: ].strip()
                    parts_header = header_content.split()
                    current_protein_identifier = parts_header[ 0 ] if len( parts_header ) > 0 else header_content

                    # Reset for new protein
                    current_sequence = None
                    continue

                # If we have a header but no sequence yet, this is the sequence line
                if current_protein_identifier is not None and current_sequence is None:
                    current_sequence = line
                    continue

                # If we have both header and sequence, this is the topology line
                if current_protein_identifier is not None and current_sequence is not None:
                    topology_string = line

                    species_protein_count += 1
                    total_proteins_read += 1

                    # Validate that topology string length matches sequence length
                    if len( topology_string ) != len( current_sequence ):
                        logger.warning( f"    WARNING: Topology length ({len( topology_string )}) != sequence length ({len( current_sequence )}) for {current_protein_identifier}" )
                        logger.warning( f"    Using topology string as-is" )

                    # Extract transmembrane and signal peptide regions
                    regions = extract_topology_regions( topology_string )

                    if len( regions ) > 0:
                        species_proteins_with_topology += 1
                        total_proteins_with_transmembrane += 1
                    else:
                        species_proteins_without_topology += 1
                        total_proteins_without_transmembrane += 1

                    for region in regions:
                        annotation_type = region[ 0 ]
                        region_start = region[ 1 ]
                        region_stop = region[ 2 ]

                        species_region_count += 1
                        total_regions_found += 1

                        # Track region types
                        if annotation_type == 'TM_helix':
                            total_transmembrane_helices += 1
                        elif annotation_type == 'TM_beta_barrel':
                            total_beta_barrels += 1
                        elif annotation_type == 'signal_peptide':
                            total_signal_peptides += 1

                        # Build annotation details
                        annotation_details = annotation_type + ',start=' + str( region_start ) + ',stop=' + str( region_stop )

                        annotation_row = (
                            phyloname,
                            current_protein_identifier,
                            str( region_start ),
                            str( region_stop ),
                            'tmbed',
                            annotation_type,
                            annotation_details,
                        )

                        annotation_rows.append( annotation_row )

                    # Reset for next protein
                    current_protein_identifier = None
                    current_sequence = None

        # =====================================================================
        # Add unannotated protein entries (if proteomes were loaded)
        # =====================================================================

        if phylonames___protein_identifiers is not None and phyloname in phylonames___protein_identifiers:
            all_protein_identifiers = phylonames___protein_identifiers[ phyloname ]

            # Get protein IDs that have tmbed annotations
            annotated_protein_identifiers = set()
            for annotation_row in annotation_rows:
                annotated_protein_identifiers.add( annotation_row[ 1 ] )

            # Compute unannotated proteins
            unannotated_protein_identifiers = all_protein_identifiers - annotated_protein_identifiers

            if len( unannotated_protein_identifiers ) > 0:
                for protein_identifier in sorted( unannotated_protein_identifiers ):
                    unannotated_counter += 1
                    unannotated_identifier = f"unannotated_tmbed-{unannotated_counter}"

                    unannotated_row = (
                        phyloname,
                        protein_identifier,
                        '0',
                        '0',
                        'tmbed',
                        unannotated_identifier,
                        'no annotation',
                    )

                    annotation_rows.append( unannotated_row )

                total_unannotated_entries_written += len( unannotated_protein_identifiers )
                logger.debug( f"    Unannotated entries added: {len( unannotated_protein_identifiers )}" )

        elif phylonames___protein_identifiers is not None and phyloname not in phylonames___protein_identifiers:
            logger.warning( f"    WARNING: No proteome found for phyloname: {phyloname}" )
            logger.warning( "    Unannotated entries will NOT be added for this species." )

        # =====================================================================
        # Write standardized output file for this species
        # =====================================================================

        if len( annotation_rows ) == 0:
            logger.info( f"    No transmembrane or signal peptide regions found for {phyloname}" )
            logger.info( f"    Proteins read: {species_protein_count}" )
            logger.info( f"    This may be expected for some species." )
            # Still create an empty file with header for consistency
            output_file_path = database_output_directory / f"gigantic_annotations-database_tmbed-{phyloname}.tsv"

            with open( output_file_path, 'w' ) as output_database_file:
                output_database_file.write( write_standardized_header() )

            continue

        output_file_path = database_output_directory / f"gigantic_annotations-database_tmbed-{phyloname}.tsv"

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
        logger.info( f"    Proteins with topology: {species_proteins_with_topology}" )
        logger.info( f"    Proteins without topology: {species_proteins_without_topology}" )
        logger.info( f"    Total regions extracted: {species_region_count}" )

    # =========================================================================
    # Validate outputs
    # =========================================================================

    if total_proteins_read == 0:
        logger.error( "CRITICAL ERROR: No proteins were read from any tmbed files!" )
        logger.error( f"Attempted to parse {len( result_files )} files" )
        logger.error( "tmbed result files may be empty or in unexpected format." )
        sys.exit( 1 )

    # Note: it is valid for total_annotations_written to be 0 if no proteins
    # have transmembrane regions, but this is unusual for a full proteome
    if total_annotations_written == 0:
        logger.warning( "WARNING: No transmembrane or signal peptide annotations were written!" )
        logger.warning( f"Read {total_proteins_read} proteins from {len( result_files )} files" )
        logger.warning( "This is unusual for a full proteome - verify tmbed output format." )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 006 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species processed: {species_count}" )
    logger.info( f"  Total proteins read: {total_proteins_read}" )
    logger.info( f"  Proteins with transmembrane/signal regions: {total_proteins_with_transmembrane}" )
    logger.info( f"  Proteins without transmembrane/signal regions: {total_proteins_without_transmembrane}" )
    logger.info( f"  Total regions extracted: {total_regions_found}" )
    logger.info( f"    TM helices (alpha): {total_transmembrane_helices}" )
    logger.info( f"    TM beta barrels: {total_beta_barrels}" )
    logger.info( f"    Signal peptides: {total_signal_peptides}" )
    logger.info( f"  Total annotations written: {total_annotations_written}" )
    logger.info( f"  Unannotated protein entries added: {total_unannotated_entries_written:,d}" )
    logger.info( f"  Output directory: {database_output_directory}" )

    # Calculate transmembrane rate
    if total_proteins_read > 0:
        transmembrane_rate = ( total_proteins_with_transmembrane / total_proteins_read ) * 100
        logger.info( f"  Transmembrane protein rate: {transmembrane_rate:.1f}%" )

    # Count output files
    output_files_list = list( database_output_directory.glob( '*.tsv' ) )
    logger.info( f"  Output files created: {len( output_files_list )}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Parse tmbed 3-line predictions into standardized annotation database format'
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

    parser.add_argument(
        '--proteomes-dir',
        type = str,
        required = False,
        default = None,
        help = 'Path to proteomes directory containing .aa FASTA files (optional - if provided, unannotated protein entries are added)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    discovery_manifest_path = Path( arguments.discovery_manifest )
    annotations_directory = Path( arguments.annotations_dir ).resolve()
    output_directory = Path( arguments.output_dir )
    proteomes_directory = Path( arguments.proteomes_dir ).resolve() if arguments.proteomes_dir else None

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 006: Parse tmbed Predictions" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load inputs
    # =========================================================================

    tmbed_record = load_discovery_manifest( discovery_manifest_path, logger )

    # Resolve relative output_directory from manifest against annotations_hmms root
    tmbed_record[ 'output_directory' ] = str( annotations_directory / tmbed_record[ 'output_directory' ] )

    # =========================================================================
    # Parse tmbed files
    # =========================================================================

    parse_tmbed_files( tmbed_record, proteomes_directory, output_directory, logger )


if __name__ == '__main__':
    main()
