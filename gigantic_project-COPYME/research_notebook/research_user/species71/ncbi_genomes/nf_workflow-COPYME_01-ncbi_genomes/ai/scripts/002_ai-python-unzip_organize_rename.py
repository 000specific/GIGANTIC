#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Unzip NCBI datasets downloads and rename files to GIGANTIC convention
# Human: Eric Edsinger

"""
002_ai-python-unzip_organize_rename.py

Extracts NCBI datasets zip files and organizes the contents into a standardized
directory structure with GIGANTIC naming conventions.

NCBI datasets zip structure:
    ncbi_dataset/data/{accession}/
        {accession}_{assembly_name}_genomic.fna   (genome)
        genomic.gff                                (GFF3 annotation)
        protein.faa                                (protein sequences)

Output structure:
    2-output/
        genome/Genus_species-ncbi_genomes.fasta
        gff3/Genus_species-ncbi_genomes.gff3
        protein/Genus_species-ncbi_genomes.faa

Usage:
    python3 002_ai-python-unzip_organize_rename.py --input-dir 1-output/downloads --output-dir 2-output
"""

import argparse
import shutil
import sys
import zipfile
from pathlib import Path


def find_file_in_extracted( extracted_directory, extension_pattern ):
    """
    Find a file matching the given extension pattern within the NCBI dataset
    extracted directory structure.

    Parameters:
        extracted_directory (Path): Root of extracted zip contents
        extension_pattern (str): File extension to search for (e.g., '.fna', '.gff', '.faa')

    Returns:
        Path or None: Path to the matching file, or None if not found
    """

    # NCBI datasets structure: ncbi_dataset/data/{accession}/
    data_directory = extracted_directory / 'ncbi_dataset' / 'data'

    if not data_directory.exists():
        return None

    # Find accession subdirectory (there should be exactly one)
    accession_directories = [ directory for directory in data_directory.iterdir() if directory.is_dir() ]

    if len( accession_directories ) == 0:
        return None

    accession_directory = accession_directories[ 0 ]

    # Search for files matching the extension
    matching_files = list( accession_directory.glob( f'*{extension_pattern}' ) )

    if len( matching_files ) == 0:
        return None

    # Return the first match (there should typically be one)
    return matching_files[ 0 ]


def process_species_zip( zip_path, genus_species, output_genome_directory, output_gff3_directory, output_protein_directory ):
    """
    Extract a single species zip file and rename contents to GIGANTIC convention.

    Parameters:
        zip_path (Path): Path to the NCBI datasets zip file
        genus_species (str): Species name in Genus_species format
        output_genome_directory (Path): Output directory for genome files
        output_gff3_directory (Path): Output directory for GFF3 files
        output_protein_directory (Path): Output directory for protein files

    Returns:
        dict: Summary of processed files with keys 'genome', 'gff3', 'protein'
              Values are True/False indicating if file was found and copied
    """

    summary = { 'genome': False, 'gff3': False, 'protein': False }

    # Create temporary extraction directory
    temporary_directory = zip_path.parent / f'_temp_{genus_species}'

    try:
        # Extract zip
        with zipfile.ZipFile( zip_path, 'r' ) as zip_file:
            zip_file.extractall( temporary_directory )

        # Find and copy genome file (.fna)
        genome_file = find_file_in_extracted( temporary_directory, '.fna' )
        if genome_file is not None:
            output_genome_path = output_genome_directory / f'{genus_species}-ncbi_genomes.fasta'
            shutil.copy2( genome_file, output_genome_path )
            summary[ 'genome' ] = True
            print( f'    Genome: {output_genome_path.name}' )
        else:
            print( f'    WARNING: No genome .fna file found for {genus_species}' )

        # Find and copy GFF3 file (.gff)
        gff3_file = find_file_in_extracted( temporary_directory, '.gff' )
        if gff3_file is not None:
            output_gff3_path = output_gff3_directory / f'{genus_species}-ncbi_genomes.gff3'
            shutil.copy2( gff3_file, output_gff3_path )
            summary[ 'gff3' ] = True
            print( f'    GFF3:   {output_gff3_path.name}' )
        else:
            print( f'    WARNING: No GFF3 .gff file found for {genus_species}' )

        # Find and copy protein file (.faa)
        protein_file = find_file_in_extracted( temporary_directory, '.faa' )
        if protein_file is not None:
            output_protein_path = output_protein_directory / f'{genus_species}-ncbi_genomes.faa'
            shutil.copy2( protein_file, output_protein_path )
            summary[ 'protein' ] = True
            print( f'    Protein: {output_protein_path.name}' )
        else:
            print( f'    WARNING: No protein .faa file found for {genus_species}' )

    finally:
        # Clean up temporary directory
        if temporary_directory.exists():
            shutil.rmtree( temporary_directory )

    return summary


def main():
    """
    Main function: unzip all NCBI datasets downloads and organize with GIGANTIC naming.
    """

    parser = argparse.ArgumentParser(
        description = 'Unzip NCBI datasets downloads and rename to GIGANTIC convention'
    )
    parser.add_argument( '--input-dir', required = True,
                         help = 'Directory containing downloaded .zip files (1-output/downloads)' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Output directory for organized files (2-output)' )
    arguments = parser.parse_args()

    input_directory = Path( arguments.input_dir )
    output_directory = Path( arguments.output_dir )

    print( '============================================' )
    print( '002: Unzip, organize, and rename' )
    print( '============================================' )
    print( '' )
    print( f'Input:  {input_directory}' )
    print( f'Output: {output_directory}' )
    print( '' )

    # Validate input directory
    if not input_directory.exists():
        print( f'ERROR: Input directory not found: {input_directory}' )
        sys.exit( 1 )

    # Find all zip files
    zip_files = sorted( input_directory.glob( '*.zip' ) )

    if len( zip_files ) == 0:
        print( f'ERROR: No .zip files found in {input_directory}' )
        sys.exit( 1 )

    print( f'Found {len( zip_files )} zip files' )
    print( '' )

    # Create output subdirectories
    output_genome_directory = output_directory / 'genome'
    output_gff3_directory = output_directory / 'gff3'
    output_protein_directory = output_directory / 'protein'

    output_genome_directory.mkdir( parents = True, exist_ok = True )
    output_gff3_directory.mkdir( parents = True, exist_ok = True )
    output_protein_directory.mkdir( parents = True, exist_ok = True )

    # Process each zip file
    total_count = len( zip_files )
    success_count = 0
    genome_count = 0
    gff3_count = 0
    protein_count = 0
    failed_species = []

    for index, zip_path in enumerate( zip_files, 1 ):
        # Extract genus_species from filename (e.g., Homo_sapiens.zip -> Homo_sapiens)
        genus_species = zip_path.stem

        print( f'--------------------------------------------' )
        print( f'[{index}/{total_count}] {genus_species}' )
        print( f'--------------------------------------------' )

        try:
            summary = process_species_zip(
                zip_path,
                genus_species,
                output_genome_directory,
                output_gff3_directory,
                output_protein_directory
            )

            if summary[ 'genome' ]:
                genome_count += 1
            if summary[ 'gff3' ]:
                gff3_count += 1
            if summary[ 'protein' ]:
                protein_count += 1

            # Consider it a success if at least the protein file was found
            if summary[ 'protein' ]:
                success_count += 1
            else:
                failed_species.append( genus_species )
                print( f'    CRITICAL: No protein file for {genus_species} - T1 extraction will fail' )

        except Exception as error:
            print( f'    ERROR: Failed to process {genus_species}: {error}' )
            failed_species.append( genus_species )

        print( '' )

    # Summary
    print( '============================================' )
    print( 'Unzip and rename complete' )
    print( '============================================' )
    print( '' )
    print( f'Species processed: {total_count}' )
    print( f'Genomes extracted: {genome_count}' )
    print( f'GFF3 files extracted: {gff3_count}' )
    print( f'Protein files extracted: {protein_count}' )
    print( '' )

    if len( failed_species ) > 0:
        print( f'FAILED species ({len( failed_species )}):' )
        for species in failed_species:
            print( f'  - {species}' )
        print( '' )
        print( 'ERROR: Some species failed to process. Check warnings above.' )
        sys.exit( 1 )

    print( 'Done!' )


if __name__ == '__main__':
    main()
