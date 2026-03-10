#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 004: Extract Gene Set Sequences
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 03:10 | Purpose: Extract gene sequences from BLAST hits
# Human: Eric Edsinger

"""
Extract gene sequences from BLAST reports.

This script parses BLAST reports to identify hits, then extracts both full-length
sequences and hit-region subsequences from the project database FASTA files.

Input:
    - output/1-output/1_ai-list-projectdb-blastdbs: List of database FASTA files
    - output/4-output/4_ai-list-reports: List of BLAST report files
    - Database FASTA files

Output:
    - output/4-output/4_ai-blastp-hits.fasta: Full-length sequences of all hits
    - output/4-output/4_ai-blastp-hit-regions.fasta: Hit-region subsequences (optional)

Log:
    - 004_ai-log-extract_gene_set_sequences.log

Requirements:
    - Python 3.10+
    - BLAST tabular output (outfmt 6)
"""

from pathlib import Path
from typing import Dict, List, Tuple, Set
import argparse
import logging
from datetime import datetime
import sys


def setup_logging( log_file_path: Path ) -> logging.Logger:
    """
    Configure logging for the script.
    
    Args:
        log_file_path: Path to log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger( __name__ )
    logger.setLevel( logging.INFO )
    
    # File handler
    file_handler = logging.FileHandler( log_file_path )
    file_handler.setLevel( logging.INFO )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )
    
    logger.addHandler( file_handler )
    logger.addHandler( console_handler )
    
    return logger


def load_fasta_sequences(
    fasta_list_file: Path,
    logger: logging.Logger = None
) -> Dict[str, str]:
    """
    Load all sequences from multiple FASTA files.
    
    Args:
        fasta_list_file: File containing list of FASTA file paths
        logger: Logger instance
        
    Returns:
        Dictionary mapping sequence identifiers to sequences
    """
    identifiers___sequences = {}
    
    if logger:
        logger.info( f"Loading FASTA files from: {fasta_list_file}" )
    
    with open( fasta_list_file, 'r' ) as input_list:
        for line in input_list:
            fasta_path = Path( line.strip() )
            
            if not fasta_path.exists():
                if logger:
                    logger.warning( f"FASTA file not found: {fasta_path}" )
                continue
            
            # Read FASTA file
            with open( fasta_path, 'r' ) as input_fasta:
                current_identifier = None
                
                for fasta_line in input_fasta:
                    if fasta_line.startswith( '>' ):
                        # Header line
                        current_identifier = fasta_line[1:].strip()
                        identifiers___sequences[ current_identifier ] = ''
                    elif current_identifier:
                        # Sequence line
                        sequence = fasta_line.strip()
                        identifiers___sequences[ current_identifier ] += sequence
    
    if logger:
        logger.info( f"Loaded {len(identifiers___sequences)} sequences" )
    
    return identifiers___sequences


def parse_blast_reports(
    report_list_file: Path,
    logger: logging.Logger = None
) -> Tuple[Set[str], Dict[str, Tuple[int, int]]]:
    """
    Parse BLAST reports to extract hit identifiers and coordinates.
    
    Args:
        report_list_file: File containing list of BLAST report file paths
        logger: Logger instance
        
    Returns:
        Tuple of (unique hit identifiers, hit coordinates dictionary)
    """
    all_hits = []
    identifiers___coordinates = {}
    
    if logger:
        logger.info( f"Parsing BLAST reports from: {report_list_file}" )
    
    with open( report_list_file, 'r' ) as input_list:
        for line in input_list:
            report_path = Path( line.strip() )
            
            if not report_path.exists():
                if logger:
                    logger.warning( f"BLAST report not found: {report_path}" )
                continue
            
            # Read BLAST report (tabular format)
            with open( report_path, 'r' ) as input_report:
                for report_line in input_report:
                    # qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore
                    parts = report_line.strip().split( '\t' )
                    
                    if len( parts ) < 10:
                        continue
                    
                    gene_identifier = parts[ 1 ]  # sseqid (subject sequence ID)
                    all_hits.append( gene_identifier )
                    
                    # Extract hit coordinates (0-based for Python)
                    coordinate_start = int( parts[ 8 ] ) - 1  # sstart
                    coordinate_end = int( parts[ 9 ] ) - 1    # send
                    
                    # Store coordinates (may get overwritten if multiple hits to same gene)
                    identifiers___coordinates[ gene_identifier ] = ( coordinate_start, coordinate_end )
    
    # Get unique hits
    unique_hits = set( all_hits )
    
    if logger:
        logger.info( f"Total hits: {len(all_hits)}" )
        logger.info( f"Unique hits: {len(unique_hits)}" )
    
    return unique_hits, identifiers___coordinates


def extract_sequences(
    unique_hits: Set[str],
    identifiers___sequences: Dict[str, str],
    identifiers___coordinates: Dict[str, Tuple[int, int]],
    output_full: Path,
    output_regions: Path = None,
    logger: logging.Logger = None
) -> Tuple[int, int]:
    """
    Extract and write full-length and hit-region sequences.
    
    Args:
        unique_hits: Set of unique hit identifiers
        identifiers___sequences: Dictionary of all sequences
        identifiers___coordinates: Dictionary of hit coordinates
        output_full: Output file for full-length sequences
        output_regions: Output file for hit regions (optional)
        logger: Logger instance
        
    Returns:
        Tuple of (full sequences written, region sequences written)
    """
    full_count = 0
    region_count = 0
    
    # Open output files
    with open( output_full, 'w' ) as output_full_handle:
        output_regions_handle = open( output_regions, 'w' ) if output_regions else None
        
        try:
            for gene_identifier in sorted( unique_hits ):
                if gene_identifier not in identifiers___sequences:
                    if logger:
                        logger.warning( f"Sequence not found for hit: {gene_identifier}" )
                    continue
                
                sequence = identifiers___sequences[ gene_identifier ]
                
                # Write full-length sequence
                output = f">{gene_identifier}\n{sequence}\n"
                output_full_handle.write( output )
                full_count += 1
                
                # Write hit-region sequence if requested
                if output_regions_handle and gene_identifier in identifiers___coordinates:
                    coordinate_start, coordinate_end = identifiers___coordinates[ gene_identifier ]
                    subsequence = sequence[ coordinate_start:coordinate_end ]
                    
                    output_sub = f">{gene_identifier}\n{subsequence}\n"
                    output_regions_handle.write( output_sub )
                    region_count += 1
        
        finally:
            if output_regions_handle:
                output_regions_handle.close()
    
    if logger:
        logger.info( f"Extracted {full_count} full-length sequences" )
        if output_regions:
            logger.info( f"Extracted {region_count} hit-region sequences" )
    
    return full_count, region_count


def main():
    """
    Main execution function.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Extract gene sequences from BLAST hits'
    )
    
    parser.add_argument(
        '--database-list',
        type=Path,
        default=Path( 'output/1-list-projectdb-blastdbs' ),
        help='File containing list of FASTA database paths'
    )
    
    parser.add_argument(
        '--report-list',
        type=Path,
        default=Path( 'output/4-list-reports' ),
        help='File containing list of BLAST report paths'
    )
    
    parser.add_argument(
        '--output-full',
        type=Path,
        default=Path( 'output/4-output/4_ai-blastp-hits.fasta' ),
        help='Output file for full-length sequences'
    )
    
    parser.add_argument(
        '--output-regions',
        type=Path,
        default=Path( 'output/4-output/4_ai-blastp-hit-regions.fasta' ),
        help='Output file for hit-region sequences (optional)'
    )
    
    parser.add_argument(
        '--no-regions',
        action='store_true',
        help='Skip extraction of hit-region sequences'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path( '004_ai-log-extract_gene_set_sequences.log' )
    logger = setup_logging( log_file )
    
    logger.info( "="*80 )
    logger.info( "Extract Gene Set Sequences from BLAST Hits" )
    logger.info( "="*80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    
    # Validate inputs
    if not args.database_list.exists():
        logger.error( f"Database list file not found: {args.database_list}" )
        sys.exit( 1 )
    
    if not args.report_list.exists():
        logger.error( f"Report list file not found: {args.report_list}" )
        sys.exit( 1 )
    
    # Create script output directory
    script_output_dir = args.output_full.parent
    script_output_dir.mkdir( parents=True, exist_ok=True )
    
    # Load sequences
    logger.info( "\nLoading sequences from FASTA files..." )
    identifiers___sequences = load_fasta_sequences( args.database_list, logger )
    
    # Parse BLAST reports
    logger.info( "\nParsing BLAST reports..." )
    unique_hits, identifiers___coordinates = parse_blast_reports( args.report_list, logger )
    
    if not unique_hits:
        logger.warning( "No hits found in BLAST reports!" )
        # Create empty output files
        args.output_full.touch()
        if not args.no_regions and args.output_regions:
            args.output_regions.touch()
        logger.info( "\nCreated empty output files" )
        sys.exit( 0 )
    
    # Extract sequences
    logger.info( "\nExtracting sequences..." )
    output_regions = None if args.no_regions else args.output_regions
    full_count, region_count = extract_sequences(
        unique_hits,
        identifiers___sequences,
        identifiers___coordinates,
        args.output_full,
        output_regions,
        logger
    )
    
    logger.info( "\n" + "="*80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "="*80 )
    logger.info( f"\nFull-length sequences: {args.output_full} ({full_count} sequences)" )
    if not args.no_regions:
        logger.info( f"Hit-region sequences: {args.output_regions} ({region_count} sequences)" )
    logger.info( f"\nLog file: {log_file}" )
    logger.info( f"\nScript completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == "__main__":
    main()

