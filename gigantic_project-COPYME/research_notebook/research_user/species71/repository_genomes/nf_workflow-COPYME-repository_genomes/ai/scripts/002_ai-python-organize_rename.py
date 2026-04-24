#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Organize and rename downloaded repository genome files to GIGANTIC convention
# Human: Eric Edsinger

"""
002_ai-python-organize_rename.py

Takes the per-species download directories from 1-output/{genus_species}/ and
organizes them into a standardized directory structure with GIGANTIC naming.

Input structure (from per-species download scripts):
    1-output/{genus_species}/
        genome.fasta       (genome assembly)
        annotation.gff3    (GFF3 annotation) or annotation.gtf (GTF)
        protein.faa        (protein sequences, if available)
        download_log.txt   (download metadata)

Output structure:
    2-output/
        genome/{genus_species}-repository_genomes.fasta
        annotation/{genus_species}-repository_genomes.gff3  (or .gtf)
        protein/{genus_species}-repository_genomes.faa      (if available)

Usage:
    python3 002_ai-python-organize_rename.py --input-dir 1-output --output-dir 2-output
"""

import argparse
import shutil
import sys
from pathlib import Path


def process_species( species_directory, genus_species, output_genome_directory, output_annotation_directory, output_protein_directory ):
    """
    Copy and rename files from a species download directory to GIGANTIC convention.

    Parameters:
        species_directory (Path): Path to 1-output/{genus_species}/
        genus_species (str): Species name
        output_genome_directory (Path): Destination for genome files
        output_annotation_directory (Path): Destination for annotation files
        output_protein_directory (Path): Destination for protein files

    Returns:
        dict: Summary with keys 'genome', 'annotation', 'annotation_format', 'protein'
    """

    summary = { 'genome': False, 'annotation': False, 'annotation_format': None, 'protein': False }

    # Copy genome
    genome_source = species_directory / 'genome.fasta'
    if genome_source.exists():
        output_path = output_genome_directory / f'{genus_species}-repository_genomes.fasta'
        shutil.copy2( genome_source, output_path )
        summary[ 'genome' ] = True
        print( f'    Genome:     {output_path.name}' )
    else:
        print( f'    Genome:     not available' )

    # Copy annotation (prefer GFF3, fall back to GTF)
    gff3_source = species_directory / 'annotation.gff3'
    gtf_source = species_directory / 'annotation.gtf'

    if gff3_source.exists():
        output_path = output_annotation_directory / f'{genus_species}-repository_genomes.gff3'
        shutil.copy2( gff3_source, output_path )
        summary[ 'annotation' ] = True
        summary[ 'annotation_format' ] = 'gff3'
        print( f'    Annotation: {output_path.name} (GFF3)' )
    elif gtf_source.exists():
        output_path = output_annotation_directory / f'{genus_species}-repository_genomes.gtf'
        shutil.copy2( gtf_source, output_path )
        summary[ 'annotation' ] = True
        summary[ 'annotation_format' ] = 'gtf'
        print( f'    Annotation: {output_path.name} (GTF)' )
    else:
        print( f'    Annotation: not available' )

    # Copy protein
    protein_source = species_directory / 'protein.faa'
    if protein_source.exists():
        output_path = output_protein_directory / f'{genus_species}-repository_genomes.faa'
        shutil.copy2( protein_source, output_path )
        summary[ 'protein' ] = True
        print( f'    Protein:    {output_path.name}' )
    else:
        print( f'    Protein:    not available' )

    return summary


def main():
    """
    Main function: organize and rename all downloaded species files.
    """

    parser = argparse.ArgumentParser(
        description = 'Organize and rename repository genome downloads to GIGANTIC convention'
    )
    parser.add_argument( '--input-dir', required = True,
                         help = 'Directory containing per-species download directories (1-output)' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Output directory for organized files (2-output)' )
    arguments = parser.parse_args()

    input_directory = Path( arguments.input_dir )
    output_directory = Path( arguments.output_dir )

    print( '============================================' )
    print( '002: Organize and rename' )
    print( '============================================' )
    print( '' )
    print( f'Input:  {input_directory}' )
    print( f'Output: {output_directory}' )
    print( '' )

    # Validate input directory
    if not input_directory.exists():
        print( f'ERROR: Input directory not found: {input_directory}' )
        sys.exit( 1 )

    # Find species directories (any directory in 1-output with at least one data file)
    species_directories = sorted( [
        directory for directory in input_directory.iterdir()
        if directory.is_dir() and directory.name != 'TEMPLATE_SPECIES'
        and any( ( directory / name ).exists() for name in [ 'genome.fasta', 'annotation.gff3', 'annotation.gtf', 'protein.faa' ] )
    ] )

    if len( species_directories ) == 0:
        print( 'WARNING: No species directories with data files found in 1-output/' )
        print( 'This is expected if no per-species download scripts have been run yet.' )
        # Create empty output dirs so pipeline doesn't fail
        ( output_directory / 'genome' ).mkdir( parents = True, exist_ok = True )
        ( output_directory / 'annotation' ).mkdir( parents = True, exist_ok = True )
        ( output_directory / 'protein' ).mkdir( parents = True, exist_ok = True )
        sys.exit( 0 )

    print( f'Species with downloaded data: {len( species_directories )}' )
    print( '' )

    # Create output subdirectories
    output_genome_directory = output_directory / 'genome'
    output_annotation_directory = output_directory / 'annotation'
    output_protein_directory = output_directory / 'protein'

    output_genome_directory.mkdir( parents = True, exist_ok = True )
    output_annotation_directory.mkdir( parents = True, exist_ok = True )
    output_protein_directory.mkdir( parents = True, exist_ok = True )

    # Process each species
    total_count = len( species_directories )
    genome_count = 0
    annotation_count = 0
    protein_count = 0

    for index, species_directory in enumerate( species_directories, 1 ):
        genus_species = species_directory.name

        print( f'--------------------------------------------' )
        print( f'[{index}/{total_count}] {genus_species}' )
        print( f'--------------------------------------------' )

        summary = process_species(
            species_directory,
            genus_species,
            output_genome_directory,
            output_annotation_directory,
            output_protein_directory
        )

        if summary[ 'genome' ]:
            genome_count += 1
        if summary[ 'annotation' ]:
            annotation_count += 1
        if summary[ 'protein' ]:
            protein_count += 1

        print( '' )

    # Summary
    print( '============================================' )
    print( 'Organize and rename complete' )
    print( '============================================' )
    print( '' )
    print( f'Species processed: {total_count}' )
    print( f'Genomes:           {genome_count}' )
    print( f'Annotations:       {annotation_count}' )
    print( f'Proteins:          {protein_count}' )
    print( '' )
    print( 'Done!' )


if __name__ == '__main__':
    main()
