#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 13 18:00 | Purpose: Standardize genome and gene annotation filenames with phylonames via symlinks
# Human: Eric Edsinger

"""
003_ai-python-standardize_genome_and_annotation_phylonames.py

Standardize genome and gene annotation files by creating phyloname-based symlinks:
    - Genomes:          Genus_species-genome-source-date.fasta  ->  phyloname-genome.fasta
    - Gene annotations: Genus_species-genome-source-date.gff3   ->  phyloname-genome.gff3
                        Genus_species-genome-source-date.gtf    ->  phyloname-genome.gtf

Unlike script 001 (proteomes), the file contents are NOT modified -- only the
filenames are standardized. Symlinks are created pointing to the original files
in STEP_1 output_to_input.

Inputs:
    - Phylonames mapping TSV from phylonames subproject output_to_input/maps/
      (columns: genus_species, phyloname, phyloname_taxonid, source, original_ncbi_phyloname)
    - Directory of source genome .fasta files from STEP_1
      (named: Genus_species-genome-source_id-download_date.fasta)
    - Directory of source gene annotation .gff3/.gtf files from STEP_1
      (named: Genus_species-genome-source_id-download_date.gff3 or .gtf)

Outputs:
    - Symlinked genome files in OUTPUT_pipeline/3-output/gigantic_genomes/
      (named: phyloname-genome.fasta)
    - Symlinked gene annotation files in OUTPUT_pipeline/3-output/gigantic_gene_annotations/
      (named: phyloname-genome.gff3 or phyloname-genome.gtf)
    - Transformation manifest TSV: OUTPUT_pipeline/3-output/3_ai-standardization_manifest.tsv
    - Detailed log: OUTPUT_pipeline/3-output/3_ai-log-standardize_genome_and_annotation_phylonames.log

Usage:
    python3 003_ai-python-standardize_genome_and_annotation_phylonames.py \\
        --phylonames-mapping PATH_TO_MAPPING.tsv \\
        --input-genomes PATH_TO_GENOMES_DIR \\
        --input-gene-annotations PATH_TO_GENE_ANNOTATIONS_DIR \\
        --output-dir OUTPUT_PIPELINE/3-output
"""

import argparse
import sys
import os
import logging
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

    logger = logging.getLogger( 'standardize_genome_annotation_phylonames' )
    logger.setLevel( logging.DEBUG )

    # File handler - captures everything including DEBUG
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
    Extract genus_species from a genome or annotation filename.

    Filenames follow the pattern:
        Genus_species-genome-source_id-download_date.extension

    The genus_species is everything before the first '-genome-' segment.

    Args:
        filename: The genome or annotation filename (not full path)
        logger: Logger instance

    Returns:
        The genus_species string

    Raises:
        SystemExit if filename cannot be parsed
    """

    if '-genome-' not in filename:
        logger.error( f"CRITICAL ERROR: Cannot parse genus_species from filename: {filename}" )
        logger.error( "Expected pattern: Genus_species-genome-source_id-download_date.extension" )
        logger.error( "The filename must contain '-genome-' as a separator." )
        sys.exit( 1 )

    genus_species = filename.split( '-genome-' )[ 0 ]

    return genus_species


# ============================================================================
# PHYLONAME LOOKUP
# ============================================================================

def lookup_phyloname(
    genus_species_from_filename: str,
    genus_species___phyloname_tuples: dict,
    logger: logging.Logger
) -> tuple:
    """
    Look up phyloname for a genus_species, with fallback for strain/isolate suffixes.

    Strategy:
        1. Try exact match first
        2. If no exact match, check if any mapping genus_species is a prefix of the
           filename genus_species (handles strain/isolate suffixes)
        3. Log clearly when a prefix match is used

    Args:
        genus_species_from_filename: genus_species extracted from the filename
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
# SYMLINK CREATION
# ============================================================================

def create_phyloname_symlink(
    source_file_path: Path,
    output_file_path: Path,
    logger: logging.Logger
) -> None:
    """
    Create a symlink from the phyloname-based output path to the original source file.

    If a symlink already exists at the output path, it is removed and recreated.

    Args:
        source_file_path: Absolute path to the original file in STEP_1
        output_file_path: Path where the phyloname-named symlink will be created
        logger: Logger instance
    """

    # Remove existing symlink if present
    if output_file_path.exists() or output_file_path.is_symlink():
        output_file_path.unlink()
        logger.debug( f"  Removed existing symlink: {output_file_path.name}" )

    os.symlink( source_file_path, output_file_path )
    logger.debug( f"  Created symlink: {output_file_path.name} -> {source_file_path}" )


# ============================================================================
# MANIFEST WRITING
# ============================================================================

def write_manifest(
    manifest_path: Path,
    genome_entries: list,
    annotation_entries: list,
    logger: logging.Logger
) -> None:
    """
    Write the transformation manifest TSV with genome and annotation sections.

    Args:
        manifest_path: Output path for the manifest TSV
        genome_entries: List of dictionaries with genome manifest data
        annotation_entries: List of dictionaries with annotation manifest data
        logger: Logger instance
    """

    logger.info( f"Writing transformation manifest to: {manifest_path}" )

    with open( manifest_path, 'w' ) as output_manifest:

        # Write genome section header
        output = (
            '# GENOMES - Phyloname symlinks to original genome FASTA files\n'
        )
        output_manifest.write( output )

        output = (
            'Data_Type (genome or gene_annotation)\t'
            'Genus_Species (original genus species name from source file)\t'
            'Phyloname (GIGANTIC phyloname used in standardized filename)\t'
            'Phyloname_Taxonid (GIGANTIC phyloname with NCBI taxon ID)\t'
            'Source_Filename (original filename from STEP_1)\t'
            'Output_Filename (standardized phyloname filename)\t'
            'Source_Extension (original file extension)\n'
        )
        output_manifest.write( output )

        for entry in genome_entries:
            output = (
                entry[ 'data_type' ] + '\t'
                + entry[ 'genus_species' ] + '\t'
                + entry[ 'phyloname' ] + '\t'
                + entry[ 'phyloname_taxonid' ] + '\t'
                + entry[ 'source_filename' ] + '\t'
                + entry[ 'output_filename' ] + '\t'
                + entry[ 'source_extension' ] + '\n'
            )
            output_manifest.write( output )

        # Write annotation section
        output = (
            '# GENE ANNOTATIONS - Phyloname symlinks to original GFF/GTF files\n'
        )
        output_manifest.write( output )

        for entry in annotation_entries:
            output = (
                entry[ 'data_type' ] + '\t'
                + entry[ 'genus_species' ] + '\t'
                + entry[ 'phyloname' ] + '\t'
                + entry[ 'phyloname_taxonid' ] + '\t'
                + entry[ 'source_filename' ] + '\t'
                + entry[ 'output_filename' ] + '\t'
                + entry[ 'source_extension' ] + '\n'
            )
            output_manifest.write( output )

    total_entries = len( genome_entries ) + len( annotation_entries )
    logger.info( f"Manifest written with {total_entries} entries ({len( genome_entries )} genomes, {len( annotation_entries )} annotations)" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: orchestrate genome and gene annotation filename standardization.
    """

    # ========================================================================
    # ARGUMENT PARSING
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = 'Standardize genome and gene annotation filenames with GIGANTIC phylonames via symlinks.',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
    # Basic usage with default output location
    python3 003_ai-python-standardize_genome_and_annotation_phylonames.py \\
        --phylonames-mapping ../../../phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv \\
        --input-genomes ../../STEP_1-sources/output_to_input/genomes \\
        --input-gene-annotations ../../STEP_1-sources/output_to_input/gene_annotations

    # Custom output directory
    python3 003_ai-python-standardize_genome_and_annotation_phylonames.py \\
        --phylonames-mapping /path/to/mapping.tsv \\
        --input-genomes /path/to/genomes \\
        --input-gene-annotations /path/to/gene_annotations \\
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
        '--input-genomes',
        type = str,
        required = True,
        help = 'Path to directory containing source genome .fasta files from STEP_1'
    )

    parser.add_argument(
        '--input-gene-annotations',
        type = str,
        required = True,
        help = 'Path to directory containing source gene annotation .gff3/.gtf files from STEP_1'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/3-output',
        help = 'Base output directory (default: OUTPUT_pipeline/3-output)'
    )

    arguments = parser.parse_args()

    # ========================================================================
    # PATH SETUP
    # ========================================================================

    input_phylonames_mapping_path = Path( arguments.phylonames_mapping ).resolve()
    input_genomes_directory = Path( arguments.input_genomes ).resolve()
    input_gene_annotations_directory = Path( arguments.input_gene_annotations ).resolve()
    output_base_directory = Path( arguments.output_dir )

    output_genomes_directory = output_base_directory / 'gigantic_genomes'
    output_gene_annotations_directory = output_base_directory / 'gigantic_gene_annotations'
    output_manifest_path = output_base_directory / '3_ai-standardization_manifest.tsv'
    output_log_path = output_base_directory / '3_ai-log-standardize_genome_and_annotation_phylonames.log'

    # Create output directories
    output_genomes_directory.mkdir( parents = True, exist_ok = True )
    output_gene_annotations_directory.mkdir( parents = True, exist_ok = True )
    output_base_directory.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # LOGGING SETUP
    # ========================================================================

    logger = setup_logging( output_log_path )

    logger.info( "=" * 80 )
    logger.info( "GIGANTIC Genome and Gene Annotation Standardization - Phylonames" )
    logger.info( "Script: 003_ai-python-standardize_genome_and_annotation_phylonames.py" )
    logger.info( "=" * 80 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Phylonames mapping: {input_phylonames_mapping_path}" )
    logger.info( f"Input genomes directory: {input_genomes_directory}" )
    logger.info( f"Input gene annotations directory: {input_gene_annotations_directory}" )
    logger.info( f"Output genomes directory: {output_genomes_directory}" )
    logger.info( f"Output gene annotations directory: {output_gene_annotations_directory}" )
    logger.info( f"Manifest output: {output_manifest_path}" )
    logger.info( f"Log output: {output_log_path}" )
    logger.info( "" )

    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================

    if not input_genomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Input genomes directory not found: {input_genomes_directory}" )
        logger.error( "STEP_1-sources must be run before STEP_2." )
        sys.exit( 1 )

    if not input_gene_annotations_directory.exists():
        logger.error( f"CRITICAL ERROR: Input gene annotations directory not found: {input_gene_annotations_directory}" )
        logger.error( "STEP_1-sources must be run before STEP_2." )
        sys.exit( 1 )

    genome_files = sorted( input_genomes_directory.glob( '*.fasta' ) )
    annotation_files_gff3 = sorted( input_gene_annotations_directory.glob( '*.gff3' ) )
    annotation_files_gtf = sorted( input_gene_annotations_directory.glob( '*.gtf' ) )
    annotation_files = sorted( annotation_files_gff3 + annotation_files_gtf, key = lambda path: path.name )

    if not genome_files:
        logger.error( f"CRITICAL ERROR: No .fasta files found in: {input_genomes_directory}" )
        logger.error( "Expected genome files with .fasta extension." )
        sys.exit( 1 )

    if not annotation_files:
        logger.error( f"CRITICAL ERROR: No .gff3 or .gtf files found in: {input_gene_annotations_directory}" )
        logger.error( "Expected gene annotation files with .gff3 or .gtf extension." )
        sys.exit( 1 )

    logger.info( f"Found {len( genome_files )} genome files to process" )
    logger.info( f"Found {len( annotation_files )} gene annotation files to process ({len( annotation_files_gff3 )} .gff3, {len( annotation_files_gtf )} .gtf)" )
    logger.info( "" )

    # ========================================================================
    # LOAD PHYLONAMES MAPPING
    # ========================================================================

    genus_species___phyloname_tuples = load_phylonames_mapping( input_phylonames_mapping_path, logger )
    logger.info( "" )

    # ========================================================================
    # PROCESS GENOMES
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "PROCESSING GENOMES" )
    logger.info( "=" * 80 )
    logger.info( "" )

    genome_manifest_entries = []
    genomes_processed = []

    for genome_file in genome_files:

        filename = genome_file.name

        # Extract genus_species from filename
        genus_species = extract_genus_species_from_filename( filename, logger )

        # Look up phyloname
        phyloname, phyloname_taxonid, matched_genus_species = lookup_phyloname(
            genus_species, genus_species___phyloname_tuples, logger
        )

        # Build output filename: phyloname-genome.fasta
        output_filename = phyloname + '-genome.fasta'
        output_file_path = output_genomes_directory / output_filename

        logger.info( f"Processing genome: {genus_species}" )
        logger.info( f"  Source file: {filename}" )
        logger.info( f"  Phyloname: {phyloname}" )
        logger.info( f"  Output symlink: {output_filename}" )

        # Create symlink to the resolved (absolute) source file
        source_absolute_path = genome_file.resolve()
        create_phyloname_symlink( source_absolute_path, output_file_path, logger )

        genomes_processed.append( genus_species )

        # Add manifest entry
        genome_manifest_entries.append( {
            'data_type': 'genome',
            'genus_species': genus_species,
            'phyloname': phyloname,
            'phyloname_taxonid': phyloname_taxonid,
            'source_filename': filename,
            'output_filename': output_filename,
            'source_extension': '.fasta'
        } )

    logger.info( "" )
    logger.info( f"Genomes processed: {len( genomes_processed )}" )
    logger.info( "" )

    # ========================================================================
    # PROCESS GENE ANNOTATIONS
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "PROCESSING GENE ANNOTATIONS" )
    logger.info( "=" * 80 )
    logger.info( "" )

    annotation_manifest_entries = []
    annotations_processed = []

    for annotation_file in annotation_files:

        filename = annotation_file.name

        # Determine the extension (.gff3 or .gtf)
        if filename.endswith( '.gff3' ):
            source_extension = '.gff3'
        elif filename.endswith( '.gtf' ):
            source_extension = '.gtf'
        else:
            logger.error( f"CRITICAL ERROR: Unexpected file extension for: {filename}" )
            logger.error( "Expected .gff3 or .gtf extension." )
            sys.exit( 1 )

        # Extract genus_species from filename
        genus_species = extract_genus_species_from_filename( filename, logger )

        # Look up phyloname
        phyloname, phyloname_taxonid, matched_genus_species = lookup_phyloname(
            genus_species, genus_species___phyloname_tuples, logger
        )

        # Build output filename: phyloname-genome.gff3 (or .gtf)
        output_filename = phyloname + '-genome' + source_extension
        output_file_path = output_gene_annotations_directory / output_filename

        logger.info( f"Processing annotation: {genus_species}" )
        logger.info( f"  Source file: {filename}" )
        logger.info( f"  Phyloname: {phyloname}" )
        logger.info( f"  Output symlink: {output_filename}" )
        logger.info( f"  Extension: {source_extension}" )

        # Create symlink to the resolved (absolute) source file
        source_absolute_path = annotation_file.resolve()
        create_phyloname_symlink( source_absolute_path, output_file_path, logger )

        annotations_processed.append( genus_species )

        # Add manifest entry
        annotation_manifest_entries.append( {
            'data_type': 'gene_annotation',
            'genus_species': genus_species,
            'phyloname': phyloname,
            'phyloname_taxonid': phyloname_taxonid,
            'source_filename': filename,
            'output_filename': output_filename,
            'source_extension': source_extension
        } )

    logger.info( "" )
    logger.info( f"Gene annotations processed: {len( annotations_processed )}" )
    logger.info( "" )

    # ========================================================================
    # WRITE MANIFEST
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "WRITING MANIFEST" )
    logger.info( "=" * 80 )
    logger.info( "" )

    write_manifest( output_manifest_path, genome_manifest_entries, annotation_manifest_entries, logger )
    logger.info( "" )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 80 )
    logger.info( f"Genomes processed: {len( genomes_processed )}" )
    logger.info( f"Gene annotations processed: {len( annotations_processed )}" )
    logger.info( f"  GFF3 files: {len( [ entry for entry in annotation_manifest_entries if entry[ 'source_extension' ] == '.gff3' ] )}" )
    logger.info( f"  GTF files: {len( [ entry for entry in annotation_manifest_entries if entry[ 'source_extension' ] == '.gtf' ] )}" )
    logger.info( f"Output genomes directory: {output_genomes_directory}" )
    logger.info( f"Output gene annotations directory: {output_gene_annotations_directory}" )
    logger.info( f"Manifest: {output_manifest_path}" )
    logger.info( f"Log: {output_log_path}" )
    logger.info( "" )

    # Log species in mapping that had no genome or no annotation
    species_without_genome = []
    species_without_annotation = []

    for genus_species in genus_species___phyloname_tuples:
        if genus_species not in genomes_processed:
            species_without_genome.append( genus_species )
        if genus_species not in annotations_processed:
            species_without_annotation.append( genus_species )

    if species_without_genome:
        logger.info( f"Species in phylonames mapping WITHOUT genome file ({len( species_without_genome )}):" )
        for species in sorted( species_without_genome ):
            logger.info( f"  - {species}" )
        logger.info( "" )

    if species_without_annotation:
        logger.info( f"Species in phylonames mapping WITHOUT gene annotation file ({len( species_without_annotation )}):" )
        for species in sorted( species_without_annotation ):
            logger.info( f"  - {species}" )
        logger.info( "" )

    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )
    logger.info( "COMPLETE" )
    logger.info( "=" * 80 )

    print( "" )
    print( f"Done! Processed {len( genomes_processed )} genomes and {len( annotations_processed )} gene annotations." )
    print( f"Output genomes: {output_genomes_directory}" )
    print( f"Output annotations: {output_gene_annotations_directory}" )
    print( f"Manifest: {output_manifest_path}" )
    print( f"Log: {output_log_path}" )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()
