#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 13 15:00 | Purpose: Standardize proteome filenames and FASTA headers with phylonames
# Human: Eric Edsinger

"""
001_ai-python-standardize_proteome_phylonames.py

Standardize proteome files by:
1. Renaming files from genus_species-genome-source-date.aa to phyloname-proteome.aa
2. Updating FASTA headers from:
       >genus_species-source_gene_id-source_transcript_id-source_protein_id
   to:
       >g_source_gene_id-t_source_transcript_id-p_source_protein_id-n_phyloname

Inputs:
    - Phylonames mapping TSV from phylonames subproject output_to_input/maps/
      (columns: genus_species, phyloname, phyloname_taxonid, source, original_ncbi_phyloname)
    - Directory of source proteome .aa files from STEP_1
      (named: genus_species-genome-source_id-download_date.aa)

Outputs:
    - Standardized proteome files in OUTPUT_pipeline/1-output/gigantic_proteomes/
      (named: phyloname-proteome.aa)
    - Transformation manifest TSV: OUTPUT_pipeline/1-output/1_ai-standardization_manifest.tsv
    - Detailed log with every header transformation: OUTPUT_pipeline/1-output/1_ai-log-standardize_proteome_phylonames.log

Usage:
    python3 001_ai-python-standardize_proteome_phylonames.py \\
        --phylonames-mapping PATH_TO_MAPPING.tsv \\
        --input-proteomes PATH_TO_PROTEOMES_DIR \\
        --output-dir OUTPUT_PIPELINE/1-output
"""

import argparse
import sys
import os
import logging
import shutil
from pathlib import Path
from datetime import datetime


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

    logger = logging.getLogger( 'standardize_proteome_phylonames' )
    logger.setLevel( logging.DEBUG )

    # File handler - captures everything including DEBUG (header transformations)
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
# PHYLONAMES MAPPING
# ============================================================================

def load_phylonames_mapping( mapping_file_path: Path, logger: logging.Logger ) -> dict:
    """
    Load the phylonames mapping TSV file into a dictionary.

    The mapping file has self-documenting headers. We need columns:
    - genus_species (column 0)
    - phyloname (column 1)
    - phyloname_taxonid (column 2)

    Args:
        mapping_file_path: Path to the phylonames mapping TSV
        logger: Logger instance

    Returns:
        Dictionary mapping genus_species to (phyloname, phyloname_taxonid) tuples
    """

    logger.info( f"Loading phylonames mapping from: {mapping_file_path}" )

    if not mapping_file_path.exists():
        logger.error( f"CRITICAL ERROR: Phylonames mapping file not found: {mapping_file_path}" )
        logger.error( "The phylonames subproject must be run before STEP_2." )
        logger.error( "Expected location: phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv" )
        sys.exit( 1 )

    genus_species___phyloname_tuples = {}

    with open( mapping_file_path, 'r' ) as input_mapping:
        # genus_species (Genus_species or Genus_species_subspecies format)	phyloname (final phyloname with UNOFFICIAL markers where applicable)	phyloname_taxonid (phyloname with NCBI taxon ID suffix)	source (NCBI for auto-generated or USER for user-provided)	original_ncbi_phyloname (original NCBI-generated phyloname before user override)
        # Abeoforma_whisleri	HolozoaUNOFFICIAL_Phylum10927_Ichthyosporea_Ichthyophonida_Family10940_Abeoforma_whisleri	HolozoaUNOFFICIAL_Phylum10927_Ichthyosporea_Ichthyophonida_Family10940_Abeoforma_whisleri___749232	USER	Kingdom10928_Phylum10927_Ichthyosporea_Ichthyophonida_Family10940_Abeoforma_whisleri
        header_line = input_mapping.readline()

        for line in input_mapping:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )
            if len( parts ) < 3:
                logger.warning( f"Skipping malformed line (fewer than 3 columns): {line}" )
                continue

            genus_species = parts[ 0 ]
            phyloname = parts[ 1 ]
            phyloname_taxonid = parts[ 2 ]

            genus_species___phyloname_tuples[ genus_species ] = ( phyloname, phyloname_taxonid )

    species_count = len( genus_species___phyloname_tuples )
    logger.info( f"Loaded phylonames for {species_count} species" )

    if species_count == 0:
        logger.error( "CRITICAL ERROR: No species found in phylonames mapping file!" )
        logger.error( f"File: {mapping_file_path}" )
        logger.error( "Check that the file is not empty and has the correct format." )
        sys.exit( 1 )

    return genus_species___phyloname_tuples


# ============================================================================
# GENUS_SPECIES EXTRACTION
# ============================================================================

def extract_genus_species_from_filename( filename: str, logger: logging.Logger ) -> str:
    """
    Extract genus_species from a proteome filename.

    Filenames follow the pattern:
        genus_species-genome-source_id-download_date.aa

    The genus_species is everything before the first '-genome-' segment.

    Args:
        filename: The proteome filename (not full path)
        logger: Logger instance

    Returns:
        The genus_species string

    Raises:
        SystemExit if filename cannot be parsed
    """

    if '-genome-' not in filename:
        logger.error( f"CRITICAL ERROR: Cannot parse genus_species from filename: {filename}" )
        logger.error( "Expected pattern: genus_species-genome-source_id-download_date.aa" )
        logger.error( "The filename must contain '-genome-' as a separator." )
        sys.exit( 1 )

    genus_species = filename.split( '-genome-' )[ 0 ]

    return genus_species


# ============================================================================
# PHYLONAME LOOKUP WITH FUZZY MATCHING
# ============================================================================

def lookup_phyloname(
    genus_species_from_filename: str,
    genus_species___phyloname_tuples: dict,
    logger: logging.Logger
) -> tuple:
    """
    Look up phyloname for a genus_species, with fallback for strain/isolate suffixes.

    Genome assemblies sometimes include strain or isolate identifiers in the species
    name (e.g., 'Hoilungia_hongkongensis_H13' vs 'Hoilungia_hongkongensis' in the
    phylonames mapping). This function handles such mismatches transparently.

    Strategy:
        1. Try exact match first
        2. If no exact match, check if any mapping genus_species is a prefix of the
           filename genus_species (handles strain/isolate suffixes)
        3. Log clearly when a prefix match is used

    Args:
        genus_species_from_filename: genus_species extracted from the proteome filename
        genus_species___phyloname_tuples: Dictionary of genus_species -> (phyloname, phyloname_taxonid)
        logger: Logger instance

    Returns:
        Tuple of (phyloname, phyloname_taxonid, matched_genus_species)
        where matched_genus_species is the key actually used from the mapping

    Raises:
        SystemExit if no match is found
    """

    # Strategy 1: Exact match
    if genus_species_from_filename in genus_species___phyloname_tuples:
        phyloname, phyloname_taxonid = genus_species___phyloname_tuples[ genus_species_from_filename ]
        return ( phyloname, phyloname_taxonid, genus_species_from_filename )

    # Strategy 2: Prefix match (mapping genus_species is a prefix of filename genus_species)
    # This handles cases like filename='Hoilungia_hongkongensis_H13' matching mapping='Hoilungia_hongkongensis'
    prefix_matches = []

    for mapping_genus_species in genus_species___phyloname_tuples:
        if genus_species_from_filename.startswith( mapping_genus_species + '_' ):
            prefix_matches.append( mapping_genus_species )

    if len( prefix_matches ) == 1:
        matched_genus_species = prefix_matches[ 0 ]
        phyloname, phyloname_taxonid = genus_species___phyloname_tuples[ matched_genus_species ]

        strain_suffix = genus_species_from_filename[ len( matched_genus_species ): ]
        logger.warning( f"PREFIX MATCH: '{genus_species_from_filename}' matched to '{matched_genus_species}'" )
        logger.warning( f"  Strain/isolate suffix '{strain_suffix}' was not in phylonames mapping" )
        logger.warning( f"  Using phyloname: {phyloname}" )

        return ( phyloname, phyloname_taxonid, matched_genus_species )

    if len( prefix_matches ) > 1:
        logger.error( f"CRITICAL ERROR: Multiple prefix matches for '{genus_species_from_filename}':" )
        for match in prefix_matches:
            logger.error( f"  - {match}" )
        logger.error( "Cannot determine which phyloname to use. Fix the phylonames mapping." )
        sys.exit( 1 )

    # No match found
    logger.error( f"CRITICAL ERROR: genus_species '{genus_species_from_filename}' not found in phylonames mapping!" )
    logger.error( "No exact match or prefix match was found." )
    logger.error( "Check that the phylonames mapping includes this species." )
    logger.error( "Check that the species name matches exactly (including subspecies/strain)." )
    sys.exit( 1 )


# ============================================================================
# HEADER TRANSFORMATION
# ============================================================================

def transform_fasta_header( header_line: str, genus_species: str, phyloname: str, logger: logging.Logger ) -> str:
    """
    Transform a FASTA header from source format to GIGANTIC format.

    Source format:
        >genus_species-source_gene_id-source_transcript_id-source_protein_id

    Target format:
        >g_source_gene_id-t_source_transcript_id-p_source_protein_id-n_phyloname

    Args:
        header_line: The original FASTA header line (starting with >)
        genus_species: The genus_species string for this proteome
        phyloname: The phyloname to use (standard format, no taxon ID)
        logger: Logger instance

    Returns:
        The transformed header line
    """

    # Strip the > prefix for processing
    header_content = header_line.lstrip( '>' ).strip()

    # Remove the genus_species prefix
    expected_prefix = genus_species + '-'

    if not header_content.startswith( expected_prefix ):
        logger.warning( f"Header does not start with expected prefix '{expected_prefix}': {header_line.strip()}" )
        logger.warning( "Attempting to parse anyway by finding genus_species at start of header." )

        # Fallback: try to find and remove genus_species even without the exact dash
        if header_content.startswith( genus_species ):
            remaining = header_content[ len( genus_species ): ]
            if remaining.startswith( '-' ):
                remaining = remaining[ 1: ]
            else:
                logger.error( f"Cannot parse header: {header_line.strip()}" )
                logger.error( f"Expected genus_species '{genus_species}' followed by '-'" )
                sys.exit( 1 )
        else:
            logger.error( f"CRITICAL ERROR: Header does not match expected genus_species." )
            logger.error( f"Expected prefix: {expected_prefix}" )
            logger.error( f"Actual header: {header_line.strip()}" )
            logger.error( "Header genus_species must match the filename genus_species." )
            sys.exit( 1 )
    else:
        remaining = header_content[ len( expected_prefix ): ]

    # Split remaining into gene_id, transcript_id, protein_id
    # The format is: gene_id-transcript_id-protein_id
    # We use exactly 2 splits from the right to handle any edge cases
    # where gene_id might unexpectedly contain a dash
    parts_remaining = remaining.split( '-' )

    if len( parts_remaining ) < 3:
        logger.error( f"CRITICAL ERROR: Cannot parse gene/transcript/protein from header: {header_line.strip()}" )
        logger.error( f"After removing genus_species prefix, remaining is: {remaining}" )
        logger.error( "Expected format: gene_id-transcript_id-protein_id (3 dash-separated fields)" )
        sys.exit( 1 )

    if len( parts_remaining ) == 3:
        gene_id = parts_remaining[ 0 ]
        transcript_id = parts_remaining[ 1 ]
        protein_id = parts_remaining[ 2 ]
    else:
        # More than 3 parts - the protein_id is the last, transcript_id is second to last,
        # and gene_id is everything else joined together
        # This handles edge cases where gene IDs might contain dashes
        protein_id = parts_remaining[ -1 ]
        transcript_id = parts_remaining[ -2 ]
        gene_id = '-'.join( parts_remaining[ :-2 ] )
        logger.warning( f"Header has more than 3 fields after genus_species removal: {header_line.strip()}" )
        logger.warning( f"Interpreting as: gene_id='{gene_id}', transcript_id='{transcript_id}', protein_id='{protein_id}'" )

    # Sanitize IDs: replace problematic characters that break BUSCO and other tools
    # Forward slashes (/) are not allowed in FASTA headers by BUSCO
    # Examples: gene IDs like "C/EBP" or "hyfzd5/8" from NCBI
    if '/' in gene_id or '/' in transcript_id or '/' in protein_id:
        logger.debug( f"Sanitizing IDs containing '/': gene={gene_id}, transcript={transcript_id}, protein={protein_id}" )

    gene_id = gene_id.replace( '/', '_' )
    transcript_id = transcript_id.replace( '/', '_' )
    protein_id = protein_id.replace( '/', '_' )

    # Build the new header
    new_header = f">g_{gene_id}-t_{transcript_id}-p_{protein_id}-n_{phyloname}"

    return new_header


# ============================================================================
# PROTEOME FILE PROCESSING
# ============================================================================

def process_proteome_file(
    input_file_path: Path,
    output_file_path: Path,
    genus_species: str,
    phyloname: str,
    logger: logging.Logger
) -> dict:
    """
    Process a single proteome file: transform all headers and write the new file.

    Args:
        input_file_path: Path to source proteome file
        output_file_path: Path for output standardized file
        genus_species: genus_species for this proteome
        phyloname: phyloname (standard format) for header tagging
        logger: Logger instance

    Returns:
        Dictionary with processing statistics:
        {
            'sequence_count': int,
            'header_transformations': list of (old_header, new_header) tuples
        }
    """

    sequence_count = 0
    header_transformations = []

    with open( input_file_path, 'r' ) as input_proteome, \
         open( output_file_path, 'w' ) as output_proteome:

        for line in input_proteome:
            if line.startswith( '>' ):
                # This is a FASTA header line
                old_header = line.strip()
                new_header = transform_fasta_header( old_header, genus_species, phyloname, logger )

                # Log every header transformation
                logger.debug( f"HEADER: {old_header}  -->  {new_header}" )

                header_transformations.append( ( old_header, new_header ) )

                output = new_header + '\n'
                output_proteome.write( output )

                sequence_count += 1
            else:
                # Sequence line - write as-is
                output_proteome.write( line )

    return {
        'sequence_count': sequence_count,
        'header_transformations': header_transformations
    }


# ============================================================================
# MANIFEST WRITING
# ============================================================================

def write_manifest(
    manifest_path: Path,
    manifest_entries: list,
    logger: logging.Logger
) -> None:
    """
    Write the transformation manifest TSV.

    Args:
        manifest_path: Output path for the manifest TSV
        manifest_entries: List of dictionaries with manifest data
        logger: Logger instance
    """

    logger.info( f"Writing transformation manifest to: {manifest_path}" )

    with open( manifest_path, 'w' ) as output_manifest:
        # Write header
        output = (
            'Genus_Species (original genus species name from source proteome)\t'
            'Phyloname (GIGANTIC phyloname used in FASTA headers)\t'
            'Phyloname_Taxonid (GIGANTIC phyloname with NCBI taxon ID used in filename)\t'
            'Source_Filename (original proteome filename from STEP_1)\t'
            'Output_Filename (standardized proteome filename)\t'
            'Sequence_Count (number of protein sequences in proteome)\n'
        )
        output_manifest.write( output )

        for entry in manifest_entries:
            output = (
                entry[ 'genus_species' ] + '\t'
                + entry[ 'phyloname' ] + '\t'
                + entry[ 'phyloname_taxonid' ] + '\t'
                + entry[ 'source_filename' ] + '\t'
                + entry[ 'output_filename' ] + '\t'
                + str( entry[ 'sequence_count' ] ) + '\n'
            )
            output_manifest.write( output )

    logger.info( f"Manifest written with {len( manifest_entries )} entries" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: orchestrate proteome standardization.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Standardize proteome filenames and FASTA headers with GIGANTIC phylonames.',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
    # Basic usage with default output location
    python3 001_ai-python-standardize_proteome_phylonames.py \\
        --phylonames-mapping ../../../phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv \\
        --input-proteomes ../../STEP_1-sources/user_research/species71/output_to_input/T1_proteomes

    # Custom output directory
    python3 001_ai-python-standardize_proteome_phylonames.py \\
        --phylonames-mapping /path/to/mapping.tsv \\
        --input-proteomes /path/to/proteomes \\
        --output-dir /path/to/output
        """
    )

    parser.add_argument(
        '--phylonames-mapping',
        type = str,
        required = True,
        help = 'Path to phylonames mapping TSV (genus_species -> phyloname, phyloname_taxonid)'
    )

    parser.add_argument(
        '--input-proteomes',
        type = str,
        required = True,
        help = 'Path to directory containing source proteome .aa files from STEP_1'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/1-output',
        help = 'Base output directory (default: OUTPUT_pipeline/1-output)'
    )

    parser.add_argument(
        '--output-to-input-dir',
        type = str,
        default = '../../output_to_input',
        help = 'output_to_input directory for STEP_3 access (default: ../../output_to_input)'
    )

    arguments = parser.parse_args()

    # ========================================================================
    # PATH SETUP
    # ========================================================================

    input_phylonames_mapping_path = Path( arguments.phylonames_mapping ).resolve()
    input_proteomes_directory = Path( arguments.input_proteomes ).resolve()
    output_base_directory = Path( arguments.output_dir )
    output_to_input_directory = Path( arguments.output_to_input_dir )

    output_proteomes_directory = output_base_directory / 'gigantic_proteomes'
    output_manifest_path = output_base_directory / '1_ai-standardization_manifest.tsv'
    output_log_path = output_base_directory / '1_ai-log-standardize_proteome_phylonames.log'

    # output_to_input locations (for STEP_3 access)
    output_to_input_proteomes_directory = output_to_input_directory / 'gigantic_proteomes'

    # Create output directories
    output_proteomes_directory.mkdir( parents = True, exist_ok = True )
    output_base_directory.mkdir( parents = True, exist_ok = True )
    output_to_input_proteomes_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC Proteome Standardization - Phylonames" )
    logger.info( "Script: 001_ai-python-standardize_proteome_phylonames.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Phylonames mapping: {input_phylonames_mapping_path}" )
    logger.info( f"Input proteomes directory: {input_proteomes_directory}" )
    logger.info( f"Output proteomes directory: {output_proteomes_directory}" )
    logger.info( f"Output to input directory: {output_to_input_proteomes_directory}" )
    logger.info( f"Manifest output: {output_manifest_path}" )
    logger.info( f"Log output: {output_log_path}" )
    logger.info( "" )

    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================

    if not input_proteomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Input proteomes directory not found: {input_proteomes_directory}" )
        logger.error( "STEP_1-sources must be run before STEP_2." )
        sys.exit( 1 )

    proteome_files = sorted( input_proteomes_directory.glob( '*.aa' ) )

    if not proteome_files:
        logger.error( f"CRITICAL ERROR: No .aa files found in: {input_proteomes_directory}" )
        logger.error( "Expected proteome files with .aa extension." )
        sys.exit( 1 )

    logger.info( f"Found {len( proteome_files )} proteome files to process" )
    logger.info( "" )

    # ========================================================================
    # LOAD PHYLONAMES MAPPING
    # ========================================================================

    genus_species___phyloname_tuples = load_phylonames_mapping( input_phylonames_mapping_path, logger )
    logger.info( "" )

    # ========================================================================
    # PROCESS EACH PROTEOME
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "PROCESSING PROTEOMES" )
    logger.info( "=" * 80 )
    logger.info( "" )

    manifest_entries = []
    total_sequences = 0
    total_header_transformations = 0
    species_not_found = []
    species_processed = []

    for proteome_file in proteome_files:

        filename = proteome_file.name

        # Extract genus_species from filename
        genus_species = extract_genus_species_from_filename( filename, logger )

        # Look up phyloname
        if genus_species not in genus_species___phyloname_tuples:
            logger.error( f"CRITICAL ERROR: genus_species '{genus_species}' not found in phylonames mapping!" )
            logger.error( f"Source file: {filename}" )
            logger.error( "Check that the phylonames mapping includes this species." )
            logger.error( "Check that the species name matches exactly (including subspecies)." )
            species_not_found.append( genus_species )
            sys.exit( 1 )

        phyloname, phyloname_taxonid = genus_species___phyloname_tuples[ genus_species ]

        # Build output filename: phyloname-proteome.aa
        output_filename = phyloname + '-proteome.aa'
        output_file_path = output_proteomes_directory / output_filename

        logger.info( f"Processing: {genus_species}" )
        logger.info( f"  Source file: {filename}" )
        logger.info( f"  Phyloname: {phyloname}" )
        logger.info( f"  Output file: {output_filename}" )

        # Process the proteome file
        result = process_proteome_file(
            input_file_path = proteome_file,
            output_file_path = output_file_path,
            genus_species = genus_species,
            phyloname = phyloname,
            logger = logger
        )

        sequence_count = result[ 'sequence_count' ]
        header_transformations = result[ 'header_transformations' ]

        # Copy standardized proteome to output_to_input for STEP_3 access
        output_to_input_proteome_path = output_to_input_proteomes_directory / output_filename
        shutil.copy2( output_file_path, output_to_input_proteome_path )

        logger.info( f"  Sequences processed: {sequence_count}" )
        logger.info( f"  Header transformations logged: {len( header_transformations )}" )
        logger.info( f"  Copied to output_to_input: {output_to_input_proteome_path.name}" )
        logger.info( "" )

        total_sequences += sequence_count
        total_header_transformations += len( header_transformations )
        species_processed.append( genus_species )

        # Add manifest entry
        manifest_entries.append( {
            'genus_species': genus_species,
            'phyloname': phyloname,
            'phyloname_taxonid': phyloname_taxonid,
            'source_filename': filename,
            'output_filename': output_filename,
            'sequence_count': sequence_count
        } )

    # ========================================================================
    # WRITE MANIFEST
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "WRITING MANIFEST" )
    logger.info( "=" * 80 )
    logger.info( "" )

    write_manifest( output_manifest_path, manifest_entries, logger )
    logger.info( "" )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Species processed: {len( species_processed )}" )
    logger.info( f"Total sequences: {total_sequences}" )
    logger.info( f"Total header transformations: {total_header_transformations}" )
    logger.info( f"Output proteomes directory: {output_proteomes_directory}" )
    logger.info( f"Output to input (for STEP_3): {output_to_input_proteomes_directory}" )
    logger.info( f"Manifest: {output_manifest_path}" )
    logger.info( f"Log: {output_log_path}" )
    logger.info( "" )

    if species_not_found:
        logger.error( f"Species NOT found in phylonames mapping: {len( species_not_found )}" )
        for species in species_not_found:
            logger.error( f"  - {species}" )
        logger.info( "" )

    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )
    logger.info( "COMPLETE" )
    logger.info( "=" * 80 )

    print( "" )
    print( f"Done! Processed {len( species_processed )} species, {total_sequences} total sequences." )
    print( f"Output: {output_proteomes_directory}" )
    print( f"Manifest: {output_manifest_path}" )
    print( f"Log (with all header transformations): {output_log_path}" )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()
