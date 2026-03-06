#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Parse SignalP predictions into standardized annotation database format
# Human: Eric Edsinger

"""
005_ai-python-parse_signalp.py

Parses SignalP signal peptide prediction TSV files (one per species) into
standardized GIGANTIC annotation database files.

SignalP predicts the presence and location of signal peptides in protein
sequences. Proteins with signal peptides have a cleavage site position
indicating where the signal peptide is cleaved from the mature protein.
The signal peptide occupies positions 1 through the cleavage site.

SignalP TSV format (with header):
    Col 0: Protein_Identifier  - Protein accession
    Col 1: Prediction          - Prediction type (e.g., Sec/SPI, Tat/SPI, Sec/SPII)
    Col 2: Cleavage_Site_Position - Position where signal peptide is cleaved
    Col 3: SP_Probability      - Probability score for signal peptide prediction

Output standardized 7-column TSV format:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Output directory structure:
    database_signalp/
        gigantic_annotations-database_signalp-{phyloname}.tsv

Input:
    --discovery-manifest: Path to 1_ai-tool_discovery_manifest.tsv from script 001
    --output-dir: Directory for output files

Output:
    database_signalp/ directory with per-species TSV files
    5_ai-log-parse_signalp.log

Usage:
    python3 005_ai-python-parse_signalp.py \\
        --discovery-manifest 1_ai-tool_discovery_manifest.tsv \\
        --proteomes-dir /path/to/proteomes \\
        --output-dir .

If --proteomes-dir is provided, the script also identifies proteins in each
species proteome that have NO SignalP predictions and adds unannotated entries
with identifiers like unannotated_signalp-1, unannotated_signalp-2, etc.
The counter is global across all species.
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '005_parse_signalp' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '5_ai-log-parse_signalp.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_discovery_manifest( manifest_path: Path, logger: logging.Logger ) -> dict:
    """
    Read the discovery manifest and return the signalp tool record.
    Returns a dictionary with tool information or exits if signalp is not available.
    """

    logger.info( f"Reading discovery manifest: {manifest_path}" )

    if not manifest_path.exists():
        logger.error( "CRITICAL ERROR: Discovery manifest does not exist!" )
        logger.error( f"Expected path: {manifest_path}" )
        logger.error( "Run script 001 (discover_tool_outputs) first." )
        sys.exit( 1 )

    signalp_record = None

    with open( manifest_path, 'r' ) as input_manifest:
        # Tool_Name (name of annotation tool)	Tool_Available (yes or no ...)	...
        # signalp	yes	output_to_input/BLOCK_signalp	5	*_signalp_predictions.tsv
        for line in input_manifest:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Tool_Name' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 5:
                continue

            tool_name = parts[ 0 ]

            if tool_name == 'signalp':
                signalp_record = {
                    'tool_name': tool_name,
                    'tool_available': parts[ 1 ],
                    'output_directory': parts[ 2 ],
                    'file_count': int( parts[ 3 ] ),
                    'file_pattern': parts[ 4 ],
                }
                break

    if signalp_record is None:
        logger.error( "CRITICAL ERROR: No signalp entry found in discovery manifest!" )
        logger.error( f"Manifest path: {manifest_path}" )
        logger.error( "The discovery manifest may be corrupted or incomplete." )
        sys.exit( 1 )

    if signalp_record[ 'tool_available' ] != 'yes':
        logger.error( "CRITICAL ERROR: SignalP results are not available!" )
        logger.error( "The discovery manifest shows signalp as unavailable." )
        logger.error( "Complete the BLOCK_signalp workflow before running this script." )
        sys.exit( 1 )

    logger.info( f"  SignalP output directory: {signalp_record[ 'output_directory' ]}" )
    logger.info( f"  Expected file count: {signalp_record[ 'file_count' ]}" )

    return signalp_record


def extract_phyloname_from_filename( filename: str, logger: logging.Logger ) -> str:
    """
    Extract the GIGANTIC phyloname from a SignalP result filename.
    Expected format: {phyloname}_signalp_predictions.tsv
    """

    suffix = '_signalp_predictions.tsv'

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
    header += 'Domain_Start (start position of signal peptide always 1)' + '\t'
    header += 'Domain_Stop (stop position of signal peptide at cleavage site)' + '\t'
    header += 'Database_Name (name of annotation database)' + '\t'
    header += 'Annotation_Identifier (signal peptide prediction type such as Sec/SPI)' + '\t'
    header += 'Annotation_Details (signal peptide type with probability score)' + '\n'

    return header


def load_proteome_protein_identifiers( proteomes_directory: Path, logger: logging.Logger ) -> dict:
    """
    Load protein identifiers from FASTA proteome files.

    Reads all .aa files in the proteomes directory, extracting protein IDs
    from FASTA headers. Returns a dictionary mapping phylonames to sets of
    protein identifiers.

    Proteome files follow GIGANTIC cleaned naming: {phyloname}-T1-proteome.aa
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
        # Extract phyloname from filename: {phyloname}-T1-proteome.aa
        filename_without_extension = proteome_file.stem
        parts_filename = filename_without_extension.split( '-T1-proteome' )
        if len( parts_filename ) < 2:
            logger.error( f"CRITICAL ERROR: Filename does not follow GIGANTIC cleaned proteome format: {proteome_file.name}" )
            logger.error( "Expected format: phyloname-T1-proteome.aa" )
            sys.exit( 1 )
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


def parse_signalp_files( signalp_record: dict, proteomes_directory: Path,
                          output_directory: Path, logger: logging.Logger ) -> None:
    """
    Parse all SignalP TSV prediction files found in the tool output directory.
    Create standardized TSV files per species. If proteomes_directory is provided,
    also adds unannotated protein entries with identifiers like unannotated_signalp-N.
    """

    signalp_output_directory = Path( signalp_record[ 'output_directory' ] )
    file_pattern = signalp_record[ 'file_pattern' ]

    # =========================================================================
    # Find SignalP result files
    # =========================================================================

    result_files = sorted( signalp_output_directory.glob( file_pattern ) )

    if len( result_files ) == 0:
        logger.error( "CRITICAL ERROR: No SignalP result files found!" )
        logger.error( f"Searched directory: {signalp_output_directory}" )
        logger.error( f"File pattern: {file_pattern}" )
        sys.exit( 1 )

    logger.info( f"Found {len( result_files )} SignalP result file(s) to parse" )

    # =========================================================================
    # Create output directory structure
    # =========================================================================

    database_output_directory = output_directory / 'database_signalp'
    database_output_directory.mkdir( parents = True, exist_ok = True )

    # =========================================================================
    # Global statistics tracking
    # =========================================================================

    total_proteins_read = 0
    total_signal_peptides_found = 0
    total_annotations_written = 0
    total_proteins_without_signal_peptide = 0
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
        # Parse SignalP TSV file
        # =====================================================================

        annotation_rows = []
        species_protein_count = 0
        species_signal_peptide_count = 0
        species_no_signal_peptide_count = 0

        with open( result_file, 'r' ) as input_signalp_results:
            # Protein_Identifier	Prediction	Cleavage_Site_Position	SP_Probability
            # XP_027047018.1	Sec/SPI	22	0.9876
            header_line = None

            for line in input_signalp_results:
                line = line.strip()

                # Skip empty lines and comment lines
                if not line or line.startswith( '#' ):
                    continue

                # Detect and skip header line
                if header_line is None and ( line.startswith( 'Protein' ) or line.startswith( 'ID' ) ):
                    header_line = line
                    logger.debug( f"    Header: {header_line}" )
                    continue

                # If first non-empty, non-comment line does not look like a header,
                # treat it as data (headerless file)
                if header_line is None:
                    # Check if first field looks like a protein ID (not a header keyword)
                    parts_check = line.split( '\t' )
                    if parts_check[ 0 ] in [ 'Protein_Identifier', 'protein_id', 'ID' ]:
                        header_line = line
                        logger.debug( f"    Header: {header_line}" )
                        continue
                    else:
                        header_line = 'no_header_detected'

                parts = line.split( '\t' )

                if len( parts ) < 4:
                    logger.warning( f"    WARNING: Line has fewer than 4 columns ({len( parts )}), skipping" )
                    logger.debug( f"    Skipped line: {line[ :200 ]}" )
                    continue

                species_protein_count += 1
                total_proteins_read += 1

                protein_identifier = parts[ 0 ].strip()
                prediction_type = parts[ 1 ].strip()
                cleavage_site_position = parts[ 2 ].strip()
                signal_peptide_probability = parts[ 3 ].strip()

                if not protein_identifier:
                    logger.warning( f"    WARNING: Empty protein identifier at row {species_protein_count}, skipping" )
                    continue

                # Check if this protein has a signal peptide
                # Proteins without signal peptides typically have prediction "OTHER" or "No SP"
                # or an empty/zero cleavage site
                prediction_type_lower = prediction_type.lower()
                if prediction_type_lower in [ 'other', 'no sp', 'no_sp', '' ]:
                    species_no_signal_peptide_count += 1
                    total_proteins_without_signal_peptide += 1
                    continue

                # Validate cleavage site position
                try:
                    cleavage_site_integer = int( cleavage_site_position )
                    if cleavage_site_integer <= 0:
                        logger.warning( f"    WARNING: Invalid cleavage site position ({cleavage_site_position}) for {protein_identifier}, skipping" )
                        species_no_signal_peptide_count += 1
                        total_proteins_without_signal_peptide += 1
                        continue
                except ValueError:
                    logger.warning( f"    WARNING: Non-integer cleavage site position ({cleavage_site_position}) for {protein_identifier}, skipping" )
                    species_no_signal_peptide_count += 1
                    total_proteins_without_signal_peptide += 1
                    continue

                species_signal_peptide_count += 1
                total_signal_peptides_found += 1

                # Build annotation details
                annotation_details = prediction_type + ',probability=' + signal_peptide_probability

                # Signal peptides always start at position 1 and end at cleavage site
                annotation_row = (
                    phyloname,
                    protein_identifier,
                    '1',
                    cleavage_site_position,
                    'signalp',
                    prediction_type,
                    annotation_details,
                )

                annotation_rows.append( annotation_row )

        # =====================================================================
        # Add unannotated protein entries (if proteomes were loaded)
        # =====================================================================

        if phylonames___protein_identifiers is not None and phyloname in phylonames___protein_identifiers:
            all_protein_identifiers = phylonames___protein_identifiers[ phyloname ]

            # Get protein IDs that have SignalP annotations
            annotated_protein_identifiers = set()
            for annotation_row in annotation_rows:
                annotated_protein_identifiers.add( annotation_row[ 1 ] )

            # Compute unannotated proteins
            unannotated_protein_identifiers = all_protein_identifiers - annotated_protein_identifiers

            if len( unannotated_protein_identifiers ) > 0:
                for protein_identifier in sorted( unannotated_protein_identifiers ):
                    unannotated_counter += 1
                    unannotated_identifier = f"unannotated_signalp-{unannotated_counter}"

                    unannotated_row = (
                        phyloname,
                        protein_identifier,
                        '0',
                        '0',
                        'signalp',
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
            logger.warning( f"    WARNING: No signal peptides found for {phyloname}" )
            logger.warning( f"    Proteins read: {species_protein_count}" )
            logger.warning( f"    This is unusual - verify SignalP output file format." )
            continue

        output_file_path = database_output_directory / f"gigantic_annotations-database_signalp-{phyloname}.tsv"

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
        logger.info( f"    Signal peptides found: {species_signal_peptide_count}" )
        logger.info( f"    Proteins without signal peptide: {species_no_signal_peptide_count}" )

    # =========================================================================
    # Validate outputs
    # =========================================================================

    if total_annotations_written == 0:
        logger.error( "CRITICAL ERROR: No annotations were written to any database files!" )
        logger.error( f"Read {total_proteins_read} proteins from {len( result_files )} files" )
        logger.error( "SignalP result files may be empty or in unexpected format." )
        sys.exit( 1 )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 005 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species processed: {species_count}" )
    logger.info( f"  Total proteins read: {total_proteins_read}" )
    logger.info( f"  Total signal peptides found: {total_signal_peptides_found}" )
    logger.info( f"  Total proteins without signal peptide: {total_proteins_without_signal_peptide}" )
    logger.info( f"  Total annotations written: {total_annotations_written}" )
    logger.info( f"  Unannotated protein entries added: {total_unannotated_entries_written:,d}" )
    logger.info( f"  Output directory: {database_output_directory}" )

    # Calculate signal peptide rate
    if total_proteins_read > 0:
        signal_peptide_rate = ( total_signal_peptides_found / total_proteins_read ) * 100
        logger.info( f"  Signal peptide rate: {signal_peptide_rate:.1f}%" )

    # Count output files
    output_files_list = list( database_output_directory.glob( '*.tsv' ) )
    logger.info( f"  Output files created: {len( output_files_list )}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Parse SignalP predictions into standardized annotation database format'
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
    logger.info( "Script 005: Parse SignalP Predictions" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load inputs
    # =========================================================================

    signalp_record = load_discovery_manifest( discovery_manifest_path, logger )

    # Resolve relative output_directory from manifest against annotations_hmms root
    signalp_record[ 'output_directory' ] = str( annotations_directory / signalp_record[ 'output_directory' ] )

    # =========================================================================
    # Parse SignalP files
    # =========================================================================

    parse_signalp_files( signalp_record, proteomes_directory, output_directory, logger )


if __name__ == '__main__':
    main()
