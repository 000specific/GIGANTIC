#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Copy user-provided species data from user_research/ to pipeline 1-output/ directories
# Human: Eric Edsinger

"""
003_ai-python-copy_user_research_species.py

Copies user-provided genome data from the user_research/ directory into the
pipeline's 1-output/{genus_species}/ directories with standardized filenames.

The user_research/ directory contains files in GIGANTIC naming convention:
    phyloname___taxid-source-download_date-data_type.ext

This script maps those files to the pipeline-standard filenames:
    genome.fasta, annotation.gff3, protein.faa

Species handled:
    1. Beroe_ovata: GFF + protein + CDS (no genome in user_research)
    2. Pleurobrachia_bachei: protein only (no genome or GFF)
    3. Urechis_unicinctus: GFF + protein + CDS (genome already from NCBI in 1-output)
    4. Membranipora_membranacea: GFF + protein + CDS (genome already from NCBI in 1-output)

Usage:
    python3 003_ai-python-copy_user_research_species.py \\
        --user-research-dir ../../user_research \\
        --output-dir 1-output
"""

import argparse
import shutil
import sys
import logging
from pathlib import Path
from datetime import datetime


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
# Species configuration
# ============================================================================

# Each species entry maps source filenames (glob patterns) to destination filenames
# Format: genus_species -> { source_pattern_key: (glob_pattern, destination_filename) }

species_configurations = {

    'Beroe_ovata': {
        'genus_species': 'Beroe_ovata',
        'description': 'Ctenophore - Beroe ovata genome data from Whitney Lab (Bova1_5)',
        'files': {
            'annotation': {
                'source_pattern': '*Beroe_ovata*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Beroe_ovata*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
            'cds': {
                'source_pattern': '*Beroe_ovata*gene_models.cds',
                'destination_filename': 'cds.fna',
            },
        },
    },

    'Pleurobrachia_bachei': {
        'genus_species': 'Pleurobrachia_bachei',
        'description': 'Ctenophore - Pleurobrachia bachei protein data from Moroz Excel 2024',
        'files': {
            'protein': {
                'source_pattern': '*Pleurobrachia_bachei*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
        },
    },

    'Urechis_unicinctus': {
        'genus_species': 'Urechis_unicinctus',
        'description': 'Echiuran worm - Urechis unicinctus data from Dryad (brv15dvhv)',
        'files': {
            'annotation': {
                'source_pattern': '*Urechis_unicinctus*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Urechis_unicinctus*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
            'cds': {
                'source_pattern': '*Urechis_unicinctus*gene_models.cds',
                'destination_filename': 'cds.fna',
            },
        },
    },

    'Membranipora_membranacea': {
        'genus_species': 'Membranipora_membranacea',
        'description': 'Bryozoan - Membranipora membranacea data from Dryad (76hdr7t3f)',
        'files': {
            'annotation': {
                'source_pattern': '*Membranipora_membranacea*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Membranipora_membranacea*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
            'cds': {
                'source_pattern': '*Membranipora_membranacea*gene_models.cds',
                'destination_filename': 'cds.fna',
            },
        },
    },

    'Creolimax_fragrantissima': {
        'genus_species': 'Creolimax_fragrantissima',
        'description': 'Ichthyosporean - Creolimax fragrantissima data from Dryad (dncjsxm47)',
        'files': {
            'annotation': {
                'source_pattern': '*Creolimax_fragrantissima*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Creolimax_fragrantissima*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
        },
    },

    'Chondrosia_reniformis': {
        'genus_species': 'Chondrosia_reniformis',
        'description': 'Demosponge - Chondrosia reniformis data from Dryad (dncjsxm47)',
        'files': {
            'annotation': {
                'source_pattern': '*Chondrosia_reniformis*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Chondrosia_reniformis*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
        },
    },

    'Berghia_stephanieae': {
        'genus_species': 'Berghia_stephanieae',
        'description': 'Nudibranch - Berghia stephanieae data from Dryad (D1BS33)',
        'files': {
            'genome': {
                'source_pattern': '*Berghia_stephanieae*assembly.fasta',
                'destination_filename': 'genome.fasta',
            },
            'annotation': {
                'source_pattern': '*Berghia_stephanieae*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Berghia_stephanieae*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
        },
    },

    'Lissachatina_fulica': {
        'genus_species': 'Lissachatina_fulica',
        'description': 'Giant African snail - Lissachatina fulica data from GigaDB (100647)',
        'files': {
            'annotation': {
                'source_pattern': '*Lissachatina_fulica*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Lissachatina_fulica*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
            'cds': {
                'source_pattern': '*Lissachatina_fulica*gene_models.cds',
                'destination_filename': 'cds.fna',
            },
        },
    },

    'Amphiscolops_sp_MND2022': {
        'genus_species': 'Amphiscolops_sp_MND2022',
        'description': 'Acoel - Amphiscolops sp MND2022 data from Zenodo (13743914)',
        'files': {
            'annotation': {
                'source_pattern': '*Amphiscolops_sp_MND2022*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Amphiscolops_sp_MND2022*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
            'cds': {
                'source_pattern': '*Amphiscolops_sp_MND2022*gene_models.cds',
                'destination_filename': 'cds.fna',
            },
        },
    },

    'Convolutriloba_macropyga': {
        'genus_species': 'Convolutriloba_macropyga',
        'description': 'Acoel - Convolutriloba macropyga data from Zenodo (13743914)',
        'files': {
            'annotation': {
                'source_pattern': '*Convolutriloba_macropyga*assembly.gff',
                'destination_filename': 'annotation.gff3',
            },
            'protein': {
                'source_pattern': '*Convolutriloba_macropyga*gene_models.aa',
                'destination_filename': 'protein.faa',
            },
            'cds': {
                'source_pattern': '*Convolutriloba_macropyga*gene_models.cds',
                'destination_filename': 'cds.fna',
            },
        },
    },

}


# ============================================================================
# Functions
# ============================================================================

def count_fasta_sequences( fasta_path ):
    """Count the number of sequences in a FASTA file."""

    count = 0

    # >sequence_header
    # MAAGSKLRLTVLCILLMQAAS...
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            if line.startswith( '>' ):
                count += 1

    return count


def process_species( genus_species, species_configuration, user_research_directory, output_directory ):
    """
    Copy files for a single species from user_research to 1-output.

    Parameters:
        genus_species (str): Species name (e.g., 'Beroe_ovata')
        species_configuration (dict): Configuration with file patterns and destinations
        user_research_directory (Path): Source directory with user-provided files
        output_directory (Path): Destination 1-output directory

    Returns:
        dict: Summary statistics for this species
    """

    logger.info( f'============================================' )
    logger.info( f'Processing: {genus_species}' )
    logger.info( f'  Description: {species_configuration[ "description" ]}' )
    logger.info( f'============================================' )

    # Create species output directory
    species_output_directory = output_directory / genus_species
    species_output_directory.mkdir( parents = True, exist_ok = True )

    # Initialize download log
    log_file_path = species_output_directory / 'download_log.txt'

    # Append to existing log if present (don't overwrite previous NCBI download info)
    with open( log_file_path, 'a' ) as log_file:
        output = '\n'
        output += f'--- User Research Data Copy ---\n'
        output += f'Date: {datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )}\n'
        output += f'Source: user_research/ directory\n'
        output += f'Description: {species_configuration[ "description" ]}\n'
        output += '\n'
        log_file.write( output )

    files_copied = 0
    protein_count = 0

    for file_type, file_configuration in species_configuration[ 'files' ].items():
        source_pattern = file_configuration[ 'source_pattern' ]
        destination_filename = file_configuration[ 'destination_filename' ]

        # Find matching source file
        matching_files = sorted( user_research_directory.glob( source_pattern ) )

        if len( matching_files ) == 0:
            logger.warning( f'  {file_type}: No file matching "{source_pattern}" found in user_research/' )
            with open( log_file_path, 'a' ) as log_file:
                output = f'{file_type}: NOT FOUND (pattern: {source_pattern})\n'
                log_file.write( output )
            continue

        source_file = matching_files[ 0 ]
        destination_file = species_output_directory / destination_filename

        # Check if destination already exists and has content
        if destination_file.exists() and destination_file.stat().st_size > 0:
            logger.info( f'  {file_type}: {destination_filename} already exists ({destination_file.stat().st_size / 1024 / 1024:.1f} MB), overwriting with user_research data' )

        # Copy file
        logger.info( f'  {file_type}: Copying {source_file.name}' )
        logger.info( f'           -> {destination_file}' )
        shutil.copy2( source_file, destination_file )
        files_copied += 1

        # Get file size
        file_size_megabytes = destination_file.stat().st_size / 1024 / 1024

        # Count sequences if FASTA
        if destination_filename.endswith( '.faa' ) or destination_filename.endswith( '.fna' ) or destination_filename.endswith( '.aa' ):
            sequence_count = count_fasta_sequences( destination_file )
            logger.info( f'           {sequence_count} sequences ({file_size_megabytes:.1f} MB)' )

            if file_type == 'protein':
                protein_count = sequence_count

            with open( log_file_path, 'a' ) as log_file:
                output = f'{file_type}: copied from {source_file.name} ({sequence_count} sequences, {file_size_megabytes:.1f} MB)\n'
                log_file.write( output )
        else:
            logger.info( f'           {file_size_megabytes:.1f} MB' )
            with open( log_file_path, 'a' ) as log_file:
                output = f'{file_type}: copied from {source_file.name} ({file_size_megabytes:.1f} MB)\n'
                log_file.write( output )

    # Check if genome already exists (from NCBI or previous download)
    genome_path = species_output_directory / 'genome.fasta'
    genome_status = 'present' if ( genome_path.exists() and genome_path.stat().st_size > 0 ) else 'missing'

    if genome_status == 'present':
        genome_size_megabytes = genome_path.stat().st_size / 1024 / 1024
        logger.info( f'  genome: already present ({genome_size_megabytes:.1f} MB)' )

    summary = {
        'genus_species': genus_species,
        'files_copied': files_copied,
        'protein_count': protein_count,
        'genome_status': genome_status,
    }

    logger.info( f'  Summary: {files_copied} files copied, {protein_count} proteins, genome={genome_status}' )

    return summary


# ============================================================================
# Main
# ============================================================================

def main():

    parser = argparse.ArgumentParser(
        description = 'Copy user-provided species data from user_research/ to pipeline 1-output/'
    )
    parser.add_argument( '--user-research-dir', required = True,
                         help = 'Path to user_research/ directory with source files' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Path to 1-output/ directory for pipeline data' )
    arguments = parser.parse_args()

    user_research_directory = Path( arguments.user_research_dir )
    output_directory = Path( arguments.output_dir )

    print( '============================================' )
    print( '003: Copy user research species data' )
    print( '============================================' )
    print( '' )

    # Validate source directory
    if not user_research_directory.exists():
        logger.error( f'CRITICAL ERROR: user_research directory not found: {user_research_directory}' )
        sys.exit( 1 )

    logger.info( f'Source: {user_research_directory}' )
    logger.info( f'Destination: {output_directory}' )
    print( '' )

    # List available source files
    source_files = sorted( user_research_directory.glob( '*.aa' ) ) + \
                   sorted( user_research_directory.glob( '*.gff' ) ) + \
                   sorted( user_research_directory.glob( '*.cds' ) )

    logger.info( f'Source files found: {len( source_files )}' )
    for source_file in source_files:
        logger.info( f'  {source_file.name} ({source_file.stat().st_size / 1024 / 1024:.1f} MB)' )
    print( '' )

    # Process each species
    all_summaries = []

    for genus_species in sorted( species_configurations.keys() ):
        species_configuration = species_configurations[ genus_species ]

        summary = process_species(
            genus_species,
            species_configuration,
            user_research_directory,
            output_directory
        )

        all_summaries.append( summary )

    # Final summary
    print( '' )
    print( '============================================' )
    print( '003: Copy complete' )
    print( '============================================' )
    print( '' )
    print( f'{"Species":<35} {"Files":>7} {"Proteins":>10} {"Genome":>8}' )
    print( '-' * 65 )

    for summary in all_summaries:
        print(
            f'{summary[ "genus_species" ]:<35} '
            f'{summary[ "files_copied" ]:>7} '
            f'{summary[ "protein_count" ]:>10} '
            f'{summary[ "genome_status" ]:>8}'
        )

    print( '-' * 65 )
    print( f'Total species: {len( all_summaries )}' )
    print( '' )
    print( 'Done!' )


if __name__ == '__main__':
    main()
