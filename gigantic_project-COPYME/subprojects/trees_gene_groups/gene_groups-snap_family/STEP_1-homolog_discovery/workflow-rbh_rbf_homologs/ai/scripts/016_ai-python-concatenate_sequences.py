#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 016: Concatenate Sequences
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Concatenate RGS and filtered CGS into final AGS
# Human: Eric Edsinger

"""
Concatenate RGS + Candidate Gene Set (CGS) sequences.

This script concatenates the Reference Gene Set (RGS) with the filtered Candidate
Gene Set (CGS) to create the final All Gene Set (AGS) file for phylogenetic analysis.

BLAST v5 databases preserve full GIGANTIC identifiers, so no identifier remapping
is needed. CGS sequences already have full headers from the database.

Input:
    - RGS FASTA file (Reference Gene Set with rgs_* headers)
    - Filtered CGS FASTA file (from script 014, with full GIGANTIC database headers)

Output:
    - AGS FASTA file combining RGS + CGS sequences

Log:
    - 016_ai-log-concatenate_sequences.log

Requirements:
    - Python 3.10+
"""

from pathlib import Path
import argparse
import logging
from datetime import datetime
import sys
import shutil


def setup_logging( log_file_path: Path ) -> logging.Logger:
    """Configure logging for the script."""
    logger = logging.getLogger( __name__ )
    logger.setLevel( logging.INFO )

    file_handler = logging.FileHandler( log_file_path )
    file_handler.setLevel( logging.INFO )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


def count_sequences_in_fasta( fasta_file: Path ) -> int:
    """
    Count number of sequences in FASTA file.

    Args:
        fasta_file: Path to FASTA file

    Returns:
        Number of sequences
    """
    count = 0

    if not fasta_file.exists():
        return 0

    with open( fasta_file, 'r' ) as input_file:
        for line in input_file:
            if line.startswith( '>' ):
                count += 1

    return count


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Concatenate RGS and filtered CGS into final AGS'
    )

    parser.add_argument(
        '--rgs-file',
        type=Path,
        required=True,
        help='Reference Gene Set (RGS) FASTA file'
    )

    parser.add_argument(
        '--cgs-file',
        type=Path,
        required=True,
        help='Filtered Candidate Gene Set (CGS) FASTA file (from script 014)'
    )

    parser.add_argument(
        '--output-file',
        type=Path,
        required=True,
        help='Output AGS FASTA file'
    )

    parser.add_argument(
        '--gene-family',
        type=str,
        required=True,
        help='Gene family name'
    )

    parser.add_argument(
        '--project-db',
        type=str,
        default='speciesN_T1-speciesN',
        help='Project database identifier'
    )

    args = parser.parse_args()

    # Setup logging
    log_file = Path( '016_ai-log-concatenate_sequences.log' )
    logger = setup_logging( log_file )

    logger.info( "=" * 80 )
    logger.info( "Concatenate RGS + Candidate Gene Set (AGS)" )
    logger.info( "=" * 80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Gene family: {args.gene_family}" )
    logger.info( f"Project DB: {args.project_db}" )
    logger.info( f"RGS file: {args.rgs_file}" )
    logger.info( f"CGS file: {args.cgs_file}" )
    logger.info( f"Output file: {args.output_file}" )

    # Validate inputs
    if not args.rgs_file.exists():
        logger.error( f"RGS file not found: {args.rgs_file}" )
        sys.exit( 1 )

    if not args.cgs_file.exists():
        logger.error( f"CGS file not found: {args.cgs_file}" )
        sys.exit( 1 )

    # Create output directory if needed
    args.output_file.parent.mkdir( parents=True, exist_ok=True )

    # Count input sequences
    rgs_count = count_sequences_in_fasta( args.rgs_file )
    cgs_count = count_sequences_in_fasta( args.cgs_file )

    logger.info( f"\nInput sequences:" )
    logger.info( f"  RGS: {rgs_count} sequences" )
    logger.info( f"  CGS: {cgs_count} sequences" )

    if rgs_count == 0:
        logger.error( "CRITICAL ERROR: RGS file contains no sequences!" )
        sys.exit( 1 )

    if cgs_count == 0:
        logger.warning( "No candidate gene sequences found (0 homologs)." )
        logger.warning( "Creating AGS with RGS sequences only." )

    # Write output: RGS + filtered CGS
    logger.info( "\nWriting concatenated AGS file..." )

    with open( args.output_file, 'w' ) as output_handle:
        # Write RGS sequences (keep original rgs_* headers)
        with open( args.rgs_file, 'r' ) as rgs_handle:
            shutil.copyfileobj( rgs_handle, output_handle )

        # Append CGS sequences (already have full GIGANTIC identifiers from BLAST v5)
        with open( args.cgs_file, 'r' ) as cgs_handle:
            shutil.copyfileobj( cgs_handle, output_handle )

    # Verify output
    total_sequences = count_sequences_in_fasta( args.output_file )
    expected_total = rgs_count + cgs_count

    if total_sequences != expected_total:
        logger.error( f"CRITICAL ERROR: Output has {total_sequences} sequences, expected {expected_total}" )
        sys.exit( 1 )

    logger.info( "\n" + "=" * 80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "=" * 80 )
    logger.info( f"\nOutput file: {args.output_file}" )
    logger.info( f"Total sequences: {total_sequences}" )
    logger.info( f"  - RGS: {rgs_count}" )
    logger.info( f"  - CGS: {cgs_count}" )
    logger.info( f"\nLog file: {log_file}" )
    logger.info( f"\nScript completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == "__main__":
    main()
