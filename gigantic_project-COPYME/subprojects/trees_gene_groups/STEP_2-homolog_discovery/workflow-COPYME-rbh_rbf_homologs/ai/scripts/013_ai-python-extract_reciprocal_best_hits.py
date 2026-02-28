#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 013: Extract Reciprocal Best Hits
# AI: Claude Code | Sonnet 4.5 | 2025 November 11 16:05 | Purpose: Extract reciprocal best fit (RBF) sequences
# Human: Eric Edsinger

"""
Extract Reciprocal Best Fit (RBF) sequences.

This script performs reciprocal best fit analysis by:
1. Loading RGS identifiers
2. Parsing reciprocal BLAST results (hits back to model species)
3. Filtering sequences that hit model species but are not in original RGS
4. Extracting keeper sequences from project databases

Input:
    - output/1-output/1_ai-list-projectdb-blastdbs: List of database FASTA files
    - output/12-output/12_ai-reciprocal-blast-report.txt: Reciprocal BLAST report
    - output/8-output/8_ai-map-rgs-to-genome-identifiers.txt: RGS ID mapping

Output:
    - output/13-output/13_ai-RBF-{project_db}-{gene_family}.aa: RBF sequences (FASTA)
    - output/13-output/13_ai-log-dropped-sequences-{gene_family}: Log of dropped sequences (TSV)

Log:
    - 013_ai-log-extract_reciprocal_best_hits.log

Requirements:
    - Python 3.10+
"""

from pathlib import Path
from typing import List, Dict, Set
import argparse
import logging
from datetime import datetime
import sys


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


def load_rgs_identifiers(
    mapping_file: Path,
    logger: logging.Logger = None
) -> List[str]:
    """
    Load RGS identifiers from mapping file.
    
    Format: genome_identifier<TAB>truncated_rgs_header<TAB>original_full_rgs_header
    
    Args:
        mapping_file: File with source-to-reference ID mapping
        logger: Logger instance
        
    Returns:
        List of RGS identifiers (includes genome_id, truncated, and original headers)
    """
    rgs_identifiers = []
    
    with open( mapping_file, 'r' ) as input_file:
        for line in input_file:
            parts = line.strip().split( '\t' )
            if len( parts ) >= 3:
                # Three-column format from script 008
                projectdb_identifier = parts[ 0 ]    # genome_id
                truncated_rgs_header = parts[ 1 ]    # truncated header
                original_full_rgs_header = parts[ 2 ] # original full header
                
                # Add all identifiers to check against BLAST hits
                rgs_identifiers.append( projectdb_identifier )
                rgs_identifiers.append( truncated_rgs_header )
                rgs_identifiers.append( original_full_rgs_header )
            elif len( parts ) >= 2:
                # Two-column format (backward compatibility)
                projectdb_identifier = parts[ 0 ]
                rgs_identifier = parts[ 1 ]
                rgs_identifiers.append( rgs_identifier )
                rgs_identifiers.append( projectdb_identifier )
    
    if logger:
        logger.info( f"Loaded {len(rgs_identifiers)} RGS identifiers" )
    
    return rgs_identifiers


def parse_reciprocal_blast_results(
    blast_report: Path,
    rgs_identifiers: List[str],
    rbh_species: List[str],
    output_filtered: Path,
    logger: logging.Logger = None
) -> List[str]:
    """
    Parse reciprocal BLAST results and identify keepers.
    
    Args:
        blast_report: Reciprocal BLAST report file
        rgs_identifiers: List of RGS identifiers to exclude
        rbh_species: List of RBH species names (e.g., ['human', 'fly', 'worm'])
        output_filtered: File to write filtered/dropped sequences
        logger: Logger instance
        
    Returns:
        List of keeper sequence identifiers
    """
    keepers = []
    
    with open( blast_report, 'r' ) as input_report, \
         open( output_filtered, 'w' ) as output_dropped:
        
        for line in input_report:
            parts = line.strip().split( '\t' )
            
            if len( parts ) < 2:
                continue
            
            query = parts[ 0 ]
            hit = parts[ 1 ]
            
            # Parse hit to extract species name
            hit_parts = hit.split( '-' )
            if len( hit_parts ) < 2:
                continue
            
            species_part = hit_parts[ 1 ]
            
            # Extract species name (handle Genus_species format)
            species_name = species_part.split( '_' )[ -1 ].lower() if '_' in species_part else species_part.lower()
            
            # Check if hit is to model species
            is_rbh_species = any( species in species_name for species in rbh_species )
            
            if is_rbh_species:
                # Keep if NOT in RGS (avoid circularity)
                if query not in rgs_identifiers:
                    keepers.append( query )
            else:
                # Log filtered sequence
                output_dropped.write( f"{query}\t{hit}\n" )
    
    if logger:
        logger.info( f"Identified {len(keepers)} keeper sequences" )
    
    return keepers


def extract_keeper_sequences(
    keepers: List[str],
    database_list_file: Path,
    output_fasta: Path,
    logger: logging.Logger = None
) -> int:
    """
    Extract keeper sequences from database FASTA files.
    
    Args:
        keepers: List of sequence identifiers to keep
        database_list_file: File containing list of database FASTA paths
        output_fasta: Output FASTA file
        logger: Logger instance
        
    Returns:
        Number of sequences extracted
    """
    keeper_set = set( keepers )
    extracted_count = 0
    
    with open( database_list_file, 'r' ) as input_list, \
         open( output_fasta, 'w' ) as output_file:
        
        for line in input_list:
            fasta_path = Path( line.strip() )
            
            if not fasta_path.exists():
                if logger:
                    logger.warning( f"FASTA file not found: {fasta_path}" )
                continue
            
            # Read FASTA and extract keepers
            with open( fasta_path, 'r' ) as input_fasta:
                should_write = False
                
                for fasta_line in input_fasta:
                    if fasta_line.startswith( '>' ):
                        # Header line
                        identifier = fasta_line[1:].strip()
                        should_write = identifier in keeper_set
                        
                        if should_write:
                            output_file.write( fasta_line )
                            extracted_count += 1
                    elif should_write:
                        # Sequence line
                        output_file.write( fasta_line )
    
    if logger:
        logger.info( f"Extracted {extracted_count} sequences" )
    
    return extracted_count


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Extract reciprocal best fit (RBF) sequences'
    )
    
    parser.add_argument(
        '--database-list',
        type=Path,
        default=Path( 'output/1-list-projectdb-blastdbs' ),
        help='File containing list of database FASTA paths'
    )
    
    parser.add_argument(
        '--blast-report',
        type=Path,
        default=Path( 'output/12-output/12_ai-reciprocal-blast-report.txt' ),
        help='Reciprocal BLAST report file (from script 012)'
    )
    
    parser.add_argument(
        '--rgs-mapping',
        type=Path,
        default=Path( 'output/8-output/8_ai-map-rgs-to-genome-identifiers.txt' ),
        help='RGS identifier mapping file (from script 008)'
    )
    
    parser.add_argument(
        '--output-fasta',
        type=Path,
        default=Path( 'output/13-output/13_ai-all-reciprocal_best_fit-sequences.aa' ),
        help='Output FASTA with RBF sequences'
    )
    
    parser.add_argument(
        '--output-filtered',
        type=Path,
        default=Path( 'output/13-output/13_ai-dropped-sequences' ),
        help='Log of filtered/dropped sequences'
    )
    
    parser.add_argument(
        '--rbh-species',
        type=str,
        required=True,
        help='Space-separated list of RBH species names (e.g., "human fly worm")'
    )
    
    args = parser.parse_args()
    
    # Parse RBH species (split space-separated string)
    rbh_species_list = args.rbh_species.split()
    
    # Setup logging
    log_file = Path( '013_ai-log-extract_reciprocal_best_hits.log' )
    logger = setup_logging( log_file )
    
    logger.info( "="*80 )
    logger.info( "Extract Reciprocal Best Fit (RBF) Sequences" )
    logger.info( "="*80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"RBH species: {', '.join(rbh_species_list)}" )
    
    # Create script output directory
    script_output_dir = args.output_fasta.parent
    script_output_dir.mkdir( parents=True, exist_ok=True )
    
    # Validate inputs
    if not args.rgs_mapping.exists():
        logger.error( f"RGS mapping file not found: {args.rgs_mapping}" )
        sys.exit( 1 )
    
    if not args.blast_report.exists():
        logger.error( f"BLAST report not found: {args.blast_report}" )
        sys.exit( 1 )
    
    if not args.database_list.exists():
        logger.error( f"Database list not found: {args.database_list}" )
        sys.exit( 1 )
    
    # Load RGS identifiers
    logger.info( "\nLoading RGS identifiers..." )
    rgs_identifiers = load_rgs_identifiers( args.rgs_mapping, logger )
    
    # Parse reciprocal BLAST results
    logger.info( "\nParsing reciprocal BLAST results..." )
    keepers = parse_reciprocal_blast_results(
        args.blast_report,
        rgs_identifiers,
        rbh_species_list,
        args.output_filtered,
        logger
    )
    
    if not keepers:
        logger.warning( "No keeper sequences identified!" )
        args.output_fasta.touch()
        logger.info( "Created empty output file" )
        sys.exit( 0 )
    
    # Extract keeper sequences
    logger.info( "\nExtracting keeper sequences..." )
    extracted_count = extract_keeper_sequences(
        keepers,
        args.database_list,
        args.output_fasta,
        logger
    )
    
    logger.info( "\n" + "="*80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "="*80 )
    logger.info( f"\nRBF sequences: {args.output_fasta} ({extracted_count} sequences)" )
    logger.info( f"Filtered log: {args.output_filtered}" )
    logger.info( f"Log file: {log_file}" )
    logger.info( f"\nScript completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == "__main__":
    main()

