#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Rename repository genome/annotation/proteome files to GIGANTIC naming convention and create output_to_input structure with identifier maps
# Human: Eric Edsinger

"""
005_ai-python-reformat_genomesdb_input.py

Rename repository genomic resource files from intermediate workflow names to the
standardized GIGANTIC file naming convention, and create the full output_to_input
directory structure (genomes, gene_annotations, T1_proteomes, maps).

Input naming (from scripts 002 and 003):
    2-output/genome/Genus_species-repository_genomes.fasta
    2-output/annotation/Genus_species-repository_genomes.gff3 (or .gtf)
    2-output/protein/Genus_species-repository_genomes.faa
    3-output/T1_proteomes/Genus_species-repository_genomes-T1_proteome.aa

Output naming (GIGANTIC convention):
    5-output/T1_proteomes/Genus_species-genome_SOURCE_ID-downloaded_DATE.aa
    5-output/genomes/Genus_species-genome_SOURCE_ID-downloaded_DATE.fasta
    5-output/gene_annotations/Genus_species-genome_SOURCE_ID-downloaded_DATE.gff3
    5-output/maps/repository_genomes-map-genome_identifiers.tsv
    5-output/maps/repository_genomes-map-sequence_identifiers.tsv

Also creates output_to_input symlinks pointing to the 5-output files.

Requires source_identifiers_manifest.tsv in INPUT_user/ with per-species source IDs.

Usage:
    python3 005_ai-python-reformat_genomesdb_input.py \\
        --source-manifest INPUT_user/source_identifiers_manifest.tsv \\
        --genome-dir 2-output/genome \\
        --annotation-dir 2-output/annotation \\
        --proteome-dir 3-output/T1_proteomes \\
        --output-dir 5-output \\
        --output-to-input-dir output_to_input \\
        --download-date 20260211
"""

import argparse
import shutil
import sys
import logging
from pathlib import Path


# ============================================================================
# Setup logging
# ============================================================================

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s | %(levelname)s | %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger( __name__ )


# ============================================================================
# Functions
# ============================================================================

def read_source_identifiers_manifest( manifest_path ):
    """
    Read the source identifiers manifest to get genus_species -> source_identifier mapping.

    Parameters:
        manifest_path (Path): Path to source_identifiers_manifest.tsv

    Returns:
        dict: genus_species -> source_identifier
    """

    genus_species_names___source_identifiers = {}

    # genus_species	source_identifier
    # Chromosphaera_perkinsii	figshare_5426494
    with open( manifest_path, 'r' ) as input_manifest:
        for line in input_manifest:
            line = line.strip()

            if line.startswith( '#' ) or len( line ) == 0:
                continue

            parts = line.split( '\t' )

            if parts[ 0 ] == 'genus_species':
                continue

            genus_species = parts[ 0 ]
            source_identifier = parts[ 1 ]
            genus_species_names___source_identifiers[ genus_species ] = source_identifier

    return genus_species_names___source_identifiers


def parse_genome_fasta_identifiers( fasta_path ):
    """
    Extract all scaffold/chromosome identifiers from a genome FASTA file.

    Parameters:
        fasta_path (Path): Path to genome FASTA file

    Returns:
        list: List of scaffold/chromosome identifiers in order
    """

    identifiers = []

    # >scaffold_1 description
    # ATCGATCG...
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            if line.startswith( '>' ):
                identifier = line[ 1: ].strip().split()[ 0 ]
                identifiers.append( identifier )

    return identifiers


def parse_proteome_headers( proteome_path ):
    """
    Extract headers and sequences from a T1 proteome FASTA file.

    Parameters:
        proteome_path (Path): Path to T1 proteome file

    Returns:
        list: List of (header, sequence) tuples
    """

    entries = []
    current_header = None
    current_sequence_parts = []

    # >Genus_species-repository_genomes|protein_id|gene_id
    # MKLQRSTVFLANNDDD
    with open( proteome_path, 'r' ) as input_proteome:
        for line in input_proteome:
            line = line.strip()

            if line.startswith( '>' ):
                if current_header is not None:
                    entries.append( ( current_header, ''.join( current_sequence_parts ) ) )
                current_header = line[ 1: ]
                current_sequence_parts = []
            elif len( line ) > 0:
                current_sequence_parts.append( line )

        if current_header is not None:
            entries.append( ( current_header, ''.join( current_sequence_parts ) ) )

    return entries


def reformat_proteome_headers( entries, genus_species ):
    """
    Reformat proteome headers from workflow format to GIGANTIC INPUT_user format.

    Input format:  >Genus_species-repository_genomes|protein_id|gene_id
    Output format: >Genus_species-gene_id-protein_id-protein_id

    Parameters:
        entries (list): List of (header, sequence) tuples
        genus_species (str): Species name

    Returns:
        list: List of (new_header, sequence) tuples
        list: List of dicts with identifier mapping info
    """

    reformatted_entries = []
    identifier_maps = []

    for header, sequence in entries:
        # Parse: Genus_species-repository_genomes|protein_id|gene_id
        parts_header = header.split( '|' )

        if len( parts_header ) >= 3:
            protein_identifier = parts_header[ 1 ]
            gene_identifier = parts_header[ 2 ]
        elif len( parts_header ) == 2:
            protein_identifier = parts_header[ 1 ]
            gene_identifier = parts_header[ 1 ]
        else:
            protein_identifier = header
            gene_identifier = header

        # Sanitize: replace dashes with underscores in identifiers
        sanitized_gene_identifier = gene_identifier.replace( '-', '_' )
        sanitized_protein_identifier = protein_identifier.replace( '-', '_' )

        # GIGANTIC proteome header format:
        # >Genus_species-source_gene_id-source_transcript_id-source_protein_id
        new_header = f'{genus_species}-{sanitized_gene_identifier}-{sanitized_protein_identifier}-{sanitized_protein_identifier}'
        reformatted_entries.append( ( new_header, sequence ) )

        identifier_maps.append( {
            'genus_species': genus_species,
            'original_gene_identifier': gene_identifier,
            'updated_gene_identifier': sanitized_gene_identifier,
            'original_protein_identifier': protein_identifier,
            'updated_protein_identifier': sanitized_protein_identifier,
        } )

    return reformatted_entries, identifier_maps


def write_proteome_fasta( entries, output_path ):
    """
    Write proteome entries to a FASTA file.

    Parameters:
        entries (list): List of (header, sequence) tuples
        output_path (Path): Output file path
    """

    with open( output_path, 'w' ) as output_fasta:
        for header, sequence in entries:
            output = f'>{header}\n'
            output_fasta.write( output )

            for index in range( 0, len( sequence ), 80 ):
                output = sequence[ index:index + 80 ] + '\n'
                output_fasta.write( output )


def create_relative_symlink( source_path, target_path ):
    """
    Create a relative symlink from target_path pointing to source_path.

    Parameters:
        source_path (Path): The actual file
        target_path (Path): Where the symlink will be created
    """

    import os
    relative_path = os.path.relpath( source_path, target_path.parent )

    if target_path.exists() or target_path.is_symlink():
        target_path.unlink()

    target_path.symlink_to( relative_path )


# ============================================================================
# Main
# ============================================================================

def main():

    parser = argparse.ArgumentParser(
        description = 'Rename repository genome files to GIGANTIC convention and create output_to_input structure'
    )
    parser.add_argument( '--source-manifest', required = True,
                         help = 'Path to source_identifiers_manifest.tsv' )
    parser.add_argument( '--genome-dir', required = True,
                         help = 'Directory containing Genus_species-repository_genomes.fasta files' )
    parser.add_argument( '--annotation-dir', required = True,
                         help = 'Directory containing Genus_species-repository_genomes.gff3/gtf files' )
    parser.add_argument( '--proteome-dir', required = True,
                         help = 'Directory containing Genus_species-repository_genomes-T1_proteome.aa files' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Output directory (5-output)' )
    parser.add_argument( '--output-to-input-dir', required = True,
                         help = 'output_to_input directory for symlinks' )
    parser.add_argument( '--download-date', required = True,
                         help = 'Download date in YYYYMMDD format' )
    arguments = parser.parse_args()

    source_manifest_path = Path( arguments.source_manifest )
    input_genome_directory = Path( arguments.genome_dir )
    input_annotation_directory = Path( arguments.annotation_dir )
    input_proteome_directory = Path( arguments.proteome_dir )
    output_directory = Path( arguments.output_dir )
    output_to_input_directory = Path( arguments.output_to_input_dir )
    download_date = arguments.download_date

    print( '============================================' )
    print( '005: Reformat for genomesDB input' )
    print( '============================================' )
    print( '' )

    # Validate inputs
    if not source_manifest_path.exists():
        logger.error( f'CRITICAL ERROR: Source identifiers manifest not found: {source_manifest_path}' )
        logger.error( 'Create INPUT_user/source_identifiers_manifest.tsv with columns: genus_species<TAB>source_identifier' )
        sys.exit( 1 )

    # Read source identifiers manifest
    genus_species_names___source_identifiers = read_source_identifiers_manifest( source_manifest_path )
    logger.info( f'Species in source manifest: {len( genus_species_names___source_identifiers )}' )

    # Create output directories
    output_proteome_directory = output_directory / 'T1_proteomes'
    output_genome_out_directory = output_directory / 'genomes'
    output_annotation_out_directory = output_directory / 'gene_annotations'
    output_maps_directory = output_directory / 'maps'

    for directory in [ output_proteome_directory, output_genome_out_directory,
                       output_annotation_out_directory, output_maps_directory ]:
        directory.mkdir( parents = True, exist_ok = True )

    # Create output_to_input directories
    oti_proteome_directory = output_to_input_directory / 'T1_proteomes'
    oti_genome_directory = output_to_input_directory / 'genomes'
    oti_annotation_directory = output_to_input_directory / 'gene_annotations'
    oti_maps_directory = output_to_input_directory / 'maps'

    for directory in [ oti_proteome_directory, oti_genome_directory,
                       oti_annotation_directory, oti_maps_directory ]:
        directory.mkdir( parents = True, exist_ok = True )

    # Discover species from proteome directory (these are the species we have T1 data for)
    species_with_proteomes = set()
    if input_proteome_directory.exists():
        for proteome_file in input_proteome_directory.glob( '*-repository_genomes-T1_proteome.aa' ):
            genus_species = proteome_file.stem.replace( '-repository_genomes-T1_proteome', '' )
            species_with_proteomes.add( genus_species )

    # Process each species
    all_genome_identifiers = []
    all_sequence_identifiers = []
    total_count = len( species_with_proteomes )
    success_count = 0

    for index, genus_species in enumerate( sorted( species_with_proteomes ), 1 ):
        source_identifier = genus_species_names___source_identifiers.get( genus_species, None )

        if source_identifier is None:
            logger.error( f'[{index}/{total_count}] {genus_species}: NO source_identifier in manifest!' )
            logger.error( f'  Add this species to {source_manifest_path}' )
            sys.exit( 1 )

        new_basename = f'{genus_species}-genome_{source_identifier}-downloaded_{download_date}'

        logger.info( f'[{index}/{total_count}] {genus_species}' )
        logger.info( f'  Source: {source_identifier}' )
        logger.info( f'  New basename: {new_basename}' )

        # --- Proteome ---
        proteome_input_path = input_proteome_directory / f'{genus_species}-repository_genomes-T1_proteome.aa'
        if proteome_input_path.exists():
            entries = parse_proteome_headers( proteome_input_path )
            reformatted_entries, identifier_maps = reformat_proteome_headers( entries, genus_species )

            proteome_output_path = output_proteome_directory / f'{new_basename}.aa'
            write_proteome_fasta( reformatted_entries, proteome_output_path )

            create_relative_symlink( proteome_output_path.resolve(), oti_proteome_directory / proteome_output_path.name )
            logger.info( f'  Proteome: {proteome_output_path.name} ({len( reformatted_entries )} proteins)' )

            all_sequence_identifiers.extend( identifier_maps )

        # --- Genome ---
        genome_input_path = input_genome_directory / f'{genus_species}-repository_genomes.fasta'
        if genome_input_path.exists():
            genome_output_path = output_genome_out_directory / f'{new_basename}.fasta'
            shutil.copy2( genome_input_path, genome_output_path )
            create_relative_symlink( genome_output_path.resolve(), oti_genome_directory / genome_output_path.name )
            logger.info( f'  Genome: {genome_output_path.name}' )

            genome_identifiers = parse_genome_fasta_identifiers( genome_input_path )
            for identifier in genome_identifiers:
                all_genome_identifiers.append( {
                    'genus_species': genus_species,
                    'genome_identifier': identifier,
                } )
        else:
            logger.info( f'  Genome: not available' )

        # --- Annotation ---
        gff3_input_path = input_annotation_directory / f'{genus_species}-repository_genomes.gff3'
        gtf_input_path = input_annotation_directory / f'{genus_species}-repository_genomes.gtf'

        if gff3_input_path.exists():
            annotation_output_path = output_annotation_out_directory / f'{new_basename}.gff3'
            shutil.copy2( gff3_input_path, annotation_output_path )
            create_relative_symlink( annotation_output_path.resolve(), oti_annotation_directory / annotation_output_path.name )
            logger.info( f'  Annotation: {annotation_output_path.name}' )
        elif gtf_input_path.exists():
            annotation_output_path = output_annotation_out_directory / f'{new_basename}.gtf'
            shutil.copy2( gtf_input_path, annotation_output_path )
            create_relative_symlink( annotation_output_path.resolve(), oti_annotation_directory / annotation_output_path.name )
            logger.info( f'  Annotation: {annotation_output_path.name}' )
        else:
            logger.info( f'  Annotation: not available' )

        success_count += 1
        logger.info( '' )

    # --- Write genome identifier map ---
    genome_map_path = output_maps_directory / 'repository_genomes-map-genome_identifiers.tsv'
    with open( genome_map_path, 'w' ) as output_map:
        output = 'Genus_Species (genus species name)\tgenome_identifier (scaffold or chromosome name from genome FASTA)\n'
        output_map.write( output )

        for entry in all_genome_identifiers:
            output = f'{entry[ "genus_species" ]}\t{entry[ "genome_identifier" ]}\n'
            output_map.write( output )

    create_relative_symlink( genome_map_path.resolve(), oti_maps_directory / genome_map_path.name )
    logger.info( f'Genome identifier map: {len( all_genome_identifiers )} entries' )

    # --- Write sequence identifier map ---
    sequence_map_path = output_maps_directory / 'repository_genomes-map-sequence_identifiers.tsv'
    with open( sequence_map_path, 'w' ) as output_map:
        output = (
            'Genus_Species (genus species name)'
            '\toriginal_gene_identifier (gene ID from source annotation)'
            '\tupdated_gene_identifier (gene ID with dashes replaced by underscores)'
            '\toriginal_protein_identifier (protein ID from source)'
            '\tupdated_protein_identifier (protein ID with dashes replaced by underscores)'
            '\n'
        )
        output_map.write( output )

        for entry in all_sequence_identifiers:
            output = (
                f'{entry[ "genus_species" ]}'
                f'\t{entry[ "original_gene_identifier" ]}'
                f'\t{entry[ "updated_gene_identifier" ]}'
                f'\t{entry[ "original_protein_identifier" ]}'
                f'\t{entry[ "updated_protein_identifier" ]}'
                '\n'
            )
            output_map.write( output )

    create_relative_symlink( sequence_map_path.resolve(), oti_maps_directory / sequence_map_path.name )
    logger.info( f'Sequence identifier map: {len( all_sequence_identifiers )} entries' )

    # Summary
    print( '' )
    print( '============================================' )
    print( 'Reformat complete' )
    print( '============================================' )
    print( '' )
    print( f'Species processed: {success_count}/{total_count}' )
    print( f'Output directory: {output_directory}' )
    print( f'output_to_input: {output_to_input_directory}' )
    print( '' )
    print( 'Done!' )


if __name__ == '__main__':
    main()
