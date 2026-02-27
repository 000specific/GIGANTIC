#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 27 | Purpose: Per-species QC analysis of OrthoHMM results
# Human: Eric Edsinger

"""
005_ai-python-qc_analysis_per_species.py

Performs quality control analysis of OrthoHMM results at the species level.
Identifies sequences not assigned to orthogroups and provides per-species statistics.

Input:
    --proteome-list: Path to 1_ai-proteome_list.txt from script 001
    --header-mapping: Path to 2_ai-header_mapping.tsv from script 002
    --orthohmm-dir: Path to OrthoHMM output directory from script 003

Output:
    OUTPUT_pipeline/5-output/5_ai-orthogroups_per_species_summary.tsv
        Per-species orthogroup statistics

    OUTPUT_pipeline/5-output/5_ai-sequences_without_orthogroup.tsv
        List of sequences not assigned to any orthogroup

Usage:
    python3 005_ai-python-qc_analysis_per_species.py \\
        --proteome-list OUTPUT_pipeline/1-output/1_ai-proteome_list.txt \\
        --header-mapping OUTPUT_pipeline/2-output/2_ai-header_mapping.tsv \\
        --orthohmm-dir OUTPUT_pipeline/3-output
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '005_qc_analysis' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '5_ai-log-qc_analysis_per_species.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Per-species QC analysis of OrthoHMM results'
    )

    parser.add_argument(
        '--proteome-list',
        type = str,
        required = True,
        help = 'Path to 1_ai-proteome_list.txt from script 001'
    )

    parser.add_argument(
        '--header-mapping',
        type = str,
        required = True,
        help = 'Path to 2_ai-header_mapping.tsv from script 002'
    )

    parser.add_argument(
        '--orthohmm-dir',
        type = str,
        required = True,
        help = 'Path to OrthoHMM output directory from script 003'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/5-output',
        help = 'Output directory (default: OUTPUT_pipeline/5-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    proteome_list_path = Path( arguments.proteome_list )
    header_mapping_path = Path( arguments.header_mapping )
    orthohmm_directory = Path( arguments.orthohmm_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 005: Per-Species QC Analysis" )
    logger.info( "=" * 70 )

    # Validate inputs
    if not proteome_list_path.exists():
        logger.error( f"CRITICAL ERROR: Proteome list not found: {proteome_list_path}" )
        sys.exit( 1 )

    if not header_mapping_path.exists():
        logger.error( f"CRITICAL ERROR: Header mapping not found: {header_mapping_path}" )
        sys.exit( 1 )

    orthogroups_path = orthohmm_directory / 'orthohmm_orthogroups.txt'
    if not orthogroups_path.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found: {orthogroups_path}" )
        sys.exit( 1 )

    # Read proteome list for species information
    # Proteome_Filename (proteome file name)	Full_Path (absolute path to proteome file)	Genus_Species (extracted from phyloname)	Sequence_Count (number of protein sequences in file)
    # filename.aa	/path/to/file.aa	Homo_sapiens	20000

    species___sequence_counts = {}

    with open( proteome_list_path, 'r' ) as input_proteome_list:
        header_line = input_proteome_list.readline()

        for line in input_proteome_list:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            genus_species = parts[ 2 ]
            sequence_count = int( parts[ 3 ] )

            species___sequence_counts[ genus_species ] = sequence_count

    logger.info( f"Loaded {len( species___sequence_counts )} species from proteome list" )

    # Read header mapping for short ID to original header lookup
    # Short_ID (short header for OrthoHMM format Genus_species-N)	Original_Header (full GIGANTIC protein identifier)	Genus_Species (species name)	Original_Filename (source proteome file)
    # Homo_sapiens-1	NP_000001.1 protein description	Homo_sapiens	filename.aa

    short_ids___original_headers = {}
    all_short_ids_by_species = defaultdict( set )

    with open( header_mapping_path, 'r' ) as input_mapping:
        header_line = input_mapping.readline()

        for line in input_mapping:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            short_id = parts[ 0 ]
            original_header = parts[ 1 ]
            genus_species = parts[ 2 ]

            short_ids___original_headers[ short_id ] = original_header
            all_short_ids_by_species[ genus_species ].add( short_id )

    logger.info( f"Loaded {len( short_ids___original_headers )} header mappings" )

    # Parse orthogroups to find which sequences are assigned
    # Format: OG_ID: gene1 gene2 gene3 ...

    sequences_in_orthogroups = set()
    species___orthogroup_counts = defaultdict( int )
    species___genes_in_orthogroups = defaultdict( int )

    with open( orthogroups_path, 'r' ) as input_orthogroups:
        for line in input_orthogroups:
            line = line.strip()
            if not line:
                continue

            if ':' in line:
                parts = line.split( ':', 1 )
                genes_string = parts[ 1 ].strip()
                genes = genes_string.split()
            else:
                parts = line.split( '\t' )
                genes = parts[ 1: ]

            # Track species presence in this orthogroup
            species_in_this_orthogroup = set()

            for gene in genes:
                sequences_in_orthogroups.add( gene )

                # Extract species from gene ID
                if '-' in gene:
                    species = gene.rsplit( '-', 1 )[ 0 ]
                    species_in_this_orthogroup.add( species )
                    species___genes_in_orthogroups[ species ] += 1

            # Count orthogroups per species
            for species in species_in_this_orthogroup:
                species___orthogroup_counts[ species ] += 1

    logger.info( f"Found {len( sequences_in_orthogroups )} sequences in orthogroups" )

    # Find sequences NOT in orthogroups
    sequences_without_orthogroup = []

    for genus_species in all_short_ids_by_species:
        short_ids = all_short_ids_by_species[ genus_species ]

        for short_id in short_ids:
            if short_id not in sequences_in_orthogroups:
                original_header = short_ids___original_headers[ short_id ]
                sequences_without_orthogroup.append( {
                    'short_id': short_id,
                    'original_header': original_header,
                    'genus_species': genus_species
                } )

    logger.info( f"Found {len( sequences_without_orthogroup )} sequences without orthogroup" )

    # Write per-species summary
    summary_file = output_directory / '5_ai-orthogroups_per_species_summary.tsv'

    with open( summary_file, 'w' ) as output_summary:
        # Write header
        header = 'Genus_Species (species name)' + '\t'
        header += 'Total_Sequences (total protein sequences for species)' + '\t'
        header += 'Sequences_In_Orthogroups (sequences assigned to orthogroups)' + '\t'
        header += 'Sequences_Without_Orthogroup (sequences not in any orthogroup)' + '\t'
        header += 'Coverage_Percent (percent of sequences in orthogroups)' + '\t'
        header += 'Orthogroups_With_Species (orthogroups containing this species)' + '\n'
        output_summary.write( header )

        for genus_species in sorted( species___sequence_counts.keys() ):
            total_sequences = species___sequence_counts[ genus_species ]
            sequences_in_og = species___genes_in_orthogroups.get( genus_species, 0 )
            sequences_without_og = total_sequences - sequences_in_og
            coverage_percent = ( sequences_in_og / total_sequences * 100 ) if total_sequences > 0 else 0.0
            orthogroup_count = species___orthogroup_counts.get( genus_species, 0 )

            output = genus_species + '\t'
            output += str( total_sequences ) + '\t'
            output += str( sequences_in_og ) + '\t'
            output += str( sequences_without_og ) + '\t'
            output += f"{coverage_percent:.2f}" + '\t'
            output += str( orthogroup_count ) + '\n'
            output_summary.write( output )

    logger.info( f"Wrote per-species summary to: {summary_file}" )

    # Write sequences without orthogroup
    unassigned_file = output_directory / '5_ai-sequences_without_orthogroup.tsv'

    with open( unassigned_file, 'w' ) as output_unassigned:
        # Write header
        header = 'Short_ID (short header used in OrthoHMM)' + '\t'
        header += 'Original_Header (full GIGANTIC protein identifier)' + '\t'
        header += 'Genus_Species (species name)' + '\n'
        output_unassigned.write( header )

        for record in sorted( sequences_without_orthogroup, key = lambda x: ( x[ 'genus_species' ], x[ 'short_id' ] ) ):
            output = record[ 'short_id' ] + '\t'
            output += record[ 'original_header' ] + '\t'
            output += record[ 'genus_species' ] + '\n'
            output_unassigned.write( output )

    logger.info( f"Wrote unassigned sequences to: {unassigned_file}" )
    logger.info( "Script 005 completed successfully" )


if __name__ == '__main__':
    main()
