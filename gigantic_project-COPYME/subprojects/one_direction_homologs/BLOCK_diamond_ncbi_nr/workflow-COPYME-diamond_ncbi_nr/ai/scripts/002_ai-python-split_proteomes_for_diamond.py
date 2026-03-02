#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Split proteomes into N parts for parallel DIAMOND search
# Human: Eric Edsinger

"""
002_ai-python-split_proteomes_for_diamond.py

Splits each species proteome FASTA file into N approximately equal parts
for massively parallel DIAMOND search against NCBI nr.

Input:
    Validated proteome manifest from script 001

Output:
    splits/{species_name}_part_{NNN}.fasta (N split files per species)
    2_ai-diamond_job_manifest.tsv (manifest for DIAMOND search jobs)

Usage:
    python3 002_ai-python-split_proteomes_for_diamond.py \\
        --manifest OUTPUT_pipeline/1-output/1_ai-validated_proteome_manifest.tsv \\
        --output-dir OUTPUT_pipeline/2-output \\
        --num-parts 40
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir ):
    """Configure logging to both console and file."""

    log_file = Path( output_dir ) / "2_ai-log-split_proteomes_for_diamond.log"

    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s | %(levelname)s | %(message)s",
        handlers = [
            logging.FileHandler( log_file ),
            logging.StreamHandler( sys.stdout )
        ]
    )

    return logging.getLogger( __name__ )


def read_fasta( fasta_path ):
    """Read a FASTA file and return list of (header, sequence) tuples."""

    sequences = []
    current_header = None
    current_sequence_parts = []

    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()
            if not line:
                continue
            if line.startswith( '>' ):
                if current_header is not None:
                    sequences.append( ( current_header, ''.join( current_sequence_parts ) ) )
                current_header = line
                current_sequence_parts = []
            else:
                current_sequence_parts.append( line )

    # Don't forget the last sequence
    if current_header is not None:
        sequences.append( ( current_header, ''.join( current_sequence_parts ) ) )

    return sequences


def main():

    parser = argparse.ArgumentParser( description = "Split proteomes for parallel DIAMOND search" )
    parser.add_argument( "--manifest", required = True, help = "Path to validated proteome manifest" )
    parser.add_argument( "--output-dir", required = True, help = "Output directory" )
    parser.add_argument( "--num-parts", type = int, default = 40, help = "Number of parts per species (default: 40)" )
    arguments = parser.parse_args()

    input_manifest_path = Path( arguments.manifest )
    output_directory = Path( arguments.output_dir )
    number_of_parts = arguments.num_parts

    output_directory.mkdir( parents = True, exist_ok = True )
    splits_directory = output_directory / "splits"
    splits_directory.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_directory )
    logger.info( "=" * 72 )
    logger.info( "Script 002: Split Proteomes for DIAMOND" )
    logger.info( "=" * 72 )
    logger.info( f"Input manifest: {input_manifest_path}" )
    logger.info( f"Output directory: {output_directory}" )
    logger.info( f"Parts per species: {number_of_parts}" )

    # ========================================================================
    # Read manifest
    # ========================================================================

    if not input_manifest_path.exists():
        logger.error( f"CRITICAL ERROR: Manifest not found: {input_manifest_path}" )
        sys.exit( 1 )

    species_entries = []

    # Species_Name (genus species identifier)	Proteome_Path (absolute path)	Phyloname	Sequence_Count
    # Homo_sapiens	/path/to/proteome.aa	Metazoa_..._Homo_sapiens	20000
    with open( input_manifest_path, 'r' ) as input_manifest:
        header_skipped = False
        for line in input_manifest:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue
            if not header_skipped:
                header_skipped = True
                continue

            parts = line.split( '\t' )
            species_name = parts[ 0 ]
            proteome_path = parts[ 1 ]
            species_entries.append( ( species_name, proteome_path ) )

    logger.info( f"Species to split: {len( species_entries )}" )

    # ========================================================================
    # Split each proteome
    # ========================================================================

    job_manifest_entries = []
    job_number = 0

    for species_name, proteome_path in species_entries:

        logger.info( f"  Splitting: {species_name}" )

        sequences = read_fasta( proteome_path )
        total_sequences = len( sequences )

        if total_sequences == 0:
            logger.error( f"  CRITICAL ERROR: No sequences in {proteome_path}" )
            sys.exit( 1 )

        # Calculate sequences per part
        sequences_per_part = total_sequences // number_of_parts
        remainder = total_sequences % number_of_parts

        # Distribute sequences across parts
        # First 'remainder' parts get one extra sequence
        sequence_index = 0

        for part_number in range( 1, number_of_parts + 1 ):

            part_size = sequences_per_part + ( 1 if part_number <= remainder else 0 )

            if part_size == 0:
                # Skip empty parts (happens when total < num_parts)
                continue

            part_filename = f"{species_name}_part_{part_number:03d}.fasta"
            part_filepath = splits_directory / part_filename

            with open( part_filepath, 'w' ) as output_fasta:
                for i in range( part_size ):
                    header, sequence = sequences[ sequence_index ]
                    output = header + '\n' + sequence + '\n'
                    output_fasta.write( output )
                    sequence_index += 1

            job_number += 1
            job_manifest_entries.append( {
                'job_number': job_number,
                'species_name': species_name,
                'part_number': part_number,
                'input_fasta': str( part_filepath ),
                'sequence_count': part_size
            } )

        logger.info( f"    {total_sequences} sequences -> {min( number_of_parts, total_sequences )} parts" )

    # ========================================================================
    # Write job manifest
    # ========================================================================

    output_manifest_path = output_directory / "2_ai-diamond_job_manifest.tsv"

    with open( output_manifest_path, 'w' ) as output_manifest:

        output = "Job_Number (sequential job identifier for SLURM array)\t"
        output += "Species_Name (genus species identifier)\t"
        output += "Part_Number (part number within species)\t"
        output += "Input_FASTA (absolute path to split FASTA file)\t"
        output += "Sequence_Count (number of sequences in this split)\n"
        output_manifest.write( output )

        for entry in job_manifest_entries:
            output = str( entry[ 'job_number' ] ) + '\t'
            output += entry[ 'species_name' ] + '\t'
            output += str( entry[ 'part_number' ] ) + '\t'
            output += entry[ 'input_fasta' ] + '\t'
            output += str( entry[ 'sequence_count' ] ) + '\n'
            output_manifest.write( output )

    # ========================================================================
    # Summary
    # ========================================================================

    logger.info( "" )
    logger.info( "=" * 72 )
    logger.info( "Split Summary" )
    logger.info( "=" * 72 )
    logger.info( f"Species processed: {len( species_entries )}" )
    logger.info( f"Total DIAMOND jobs: {job_number}" )
    logger.info( f"Job manifest: {output_manifest_path}" )
    logger.info( f"Split files: {splits_directory}" )
    logger.info( "Script 002 complete." )


if __name__ == "__main__":
    main()
