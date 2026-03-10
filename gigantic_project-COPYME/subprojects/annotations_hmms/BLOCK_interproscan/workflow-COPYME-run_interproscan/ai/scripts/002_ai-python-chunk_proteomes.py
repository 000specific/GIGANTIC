#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Split a proteome FASTA file into chunks for parallel InterProScan processing
# Human: Eric Edsinger

"""
002_ai-python-chunk_proteomes.py

Splits a single species proteome FASTA file into smaller chunk files for parallel
InterProScan processing. Each chunk contains a configurable number of protein
sequences (default 1000). The last chunk may contain fewer sequences if the total
is not evenly divisible.

This chunking strategy enables per-chunk parallelism across HPC nodes and prevents
memory issues that can occur when running InterProScan on very large proteomes.

Input:
    --input-fasta: Path to the proteome FASTA file (.aa)
    --output-dir: Directory where chunk files will be written
    --phyloname: GIGANTIC phyloname for the species (used in output naming)
    --chunk-size: Number of protein sequences per chunk (default: 1000)

Output:
    {phyloname}_chunk_001.fasta
    {phyloname}_chunk_002.fasta
    {phyloname}_chunk_003.fasta
    ...
    (one file per chunk, numbered sequentially with zero-padded 3-digit suffix)

Usage:
    python3 002_ai-python-chunk_proteomes.py \\
        --input-fasta /path/to/species_proteome.aa \\
        --output-dir . \\
        --phyloname Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens \\
        --chunk-size 1000
"""

import argparse
import sys
from pathlib import Path


def chunk_fasta_file( input_fasta_path: Path, output_directory: Path, phyloname: str, chunk_size: int ) -> None:
    """
    Read a FASTA file and split it into chunk files, each containing at most
    chunk_size sequences. The last chunk may contain fewer sequences.
    """

    # =========================================================================
    # Validate input file
    # =========================================================================

    if not input_fasta_path.exists():
        print( f"CRITICAL ERROR: Input FASTA file does not exist!", file = sys.stderr )
        print( f"Expected path: {input_fasta_path}", file = sys.stderr )
        sys.exit( 1 )

    if input_fasta_path.stat().st_size == 0:
        print( f"CRITICAL ERROR: Input FASTA file is empty!", file = sys.stderr )
        print( f"Path: {input_fasta_path}", file = sys.stderr )
        sys.exit( 1 )

    if chunk_size < 1:
        print( f"CRITICAL ERROR: Chunk size must be at least 1, got {chunk_size}!", file = sys.stderr )
        sys.exit( 1 )

    # =========================================================================
    # Read FASTA and split into chunks
    # =========================================================================

    print( f"Chunking proteome for: {phyloname}" )
    print( f"Input FASTA: {input_fasta_path}" )
    print( f"Chunk size: {chunk_size} sequences per chunk" )
    print( f"Output directory: {output_directory}" )

    output_directory.mkdir( parents = True, exist_ok = True )

    current_chunk_number = 0
    current_sequence_count_in_chunk = 0
    total_sequence_count = 0
    current_chunk_file = None

    with open( input_fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:

            # Detect a new sequence by the FASTA header line
            if line.startswith( '>' ):
                total_sequence_count += 1

                # Check if we need to start a new chunk
                if current_sequence_count_in_chunk >= chunk_size or current_chunk_file is None:
                    # Close the previous chunk file if one was open
                    if current_chunk_file is not None:
                        current_chunk_file.close()

                    # Start a new chunk
                    current_chunk_number += 1
                    current_sequence_count_in_chunk = 0

                    chunk_filename = f"{phyloname}_chunk_{current_chunk_number:03d}.fasta"
                    chunk_filepath = output_directory / chunk_filename
                    current_chunk_file = open( chunk_filepath, 'w' )

                current_sequence_count_in_chunk += 1

            # Write the line to the current chunk file
            # Strip asterisk characters from sequence lines - InterProScan rejects them
            # (asterisks appear as stop codon markers in some proteome files)
            if current_chunk_file is not None:
                if not line.startswith( '>' ):
                    line = line.replace( '*', 'X' )
                current_chunk_file.write( line )

    # Close the last chunk file
    if current_chunk_file is not None:
        current_chunk_file.close()

    # =========================================================================
    # Validate output
    # =========================================================================

    if total_sequence_count == 0:
        print( f"CRITICAL ERROR: No FASTA sequences found in input file!", file = sys.stderr )
        print( f"Input file: {input_fasta_path}", file = sys.stderr )
        print( f"File exists but contains no '>' header lines.", file = sys.stderr )
        sys.exit( 1 )

    if current_chunk_number == 0:
        print( f"CRITICAL ERROR: No chunk files were created!", file = sys.stderr )
        sys.exit( 1 )

    # =========================================================================
    # Summary
    # =========================================================================

    print( "" )
    print( "========================================" )
    print( "Script 002 completed successfully" )
    print( "========================================" )
    print( f"  Phyloname: {phyloname}" )
    print( f"  Total sequences: {total_sequence_count}" )
    print( f"  Chunk size: {chunk_size}" )
    print( f"  Chunks created: {current_chunk_number}" )
    print( f"  Last chunk sequences: {current_sequence_count_in_chunk}" )

    # List all chunk files created
    print( "" )
    print( "Chunk files:" )
    for chunk_index in range( 1, current_chunk_number + 1 ):
        chunk_filename = f"{phyloname}_chunk_{chunk_index:03d}.fasta"
        chunk_filepath = output_directory / chunk_filename
        if chunk_filepath.exists():
            chunk_file_size = chunk_filepath.stat().st_size
            print( f"  {chunk_filename} ({chunk_file_size} bytes)" )
        else:
            print( f"  WARNING: Expected chunk file not found: {chunk_filename}", file = sys.stderr )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Split a proteome FASTA file into chunks for parallel InterProScan processing'
    )

    parser.add_argument(
        '--input-fasta',
        type = str,
        required = True,
        help = 'Path to the proteome FASTA file (.aa)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Directory where chunk files will be written (default: current directory)'
    )

    parser.add_argument(
        '--phyloname',
        type = str,
        required = True,
        help = 'GIGANTIC phyloname for the species (used in output file naming)'
    )

    parser.add_argument(
        '--chunk-size',
        type = int,
        default = 1000,
        help = 'Number of protein sequences per chunk (default: 1000)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    input_fasta_path = Path( arguments.input_fasta )
    output_directory = Path( arguments.output_dir )

    # Run chunking
    chunk_fasta_file(
        input_fasta_path,
        output_directory,
        arguments.phyloname,
        arguments.chunk_size
    )


if __name__ == '__main__':
    main()
