#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 014: Filter Species for Tree Building
# AI: Claude Code | Sonnet 4.5 | 2025 November 11 16:06 | Purpose: Filter sequences by species keeper list
# Human: Eric Edsinger

"""
Filter sequences by species keeper list.

This script filters CGS sequences to only include species specified in the
keeper list for tree building.

Input:
    - output/13-output/13_ai-cgs-{project_db}-{gene_family}.aa: All CGS sequences
    - input/species-keeper-list: List of species to keep

Output:
    - output/14-output/14_ai-cgs-{project_db}-{gene_family}-filtered.aa: Filtered sequences

Log:
    - 014_ai-log-filter_species_for_tree_building.log

Requirements:
    - Python 3.10+
"""

from pathlib import Path
from typing import List, Set
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


def load_species_keeper_list(
    keeper_file: Path,
    logger: logging.Logger = None
) -> Set[str]:
    """
    Load species keeper list.
    
    Args:
        keeper_file: File containing keeper species names
        logger: Logger instance
        
    Returns:
        Set of keeper species names
    """
    keeper_species = set()
    
    with open( keeper_file, 'r' ) as input_file:
        for line in input_file:
            species_name = line.strip()
            if species_name:
                keeper_species.add( species_name )
    
    if logger:
        logger.info( f"Loaded {len(keeper_species)} keeper species" )
    
    return keeper_species


def filter_sequences_by_species(
    input_fasta: Path,
    keeper_species: Set[str],
    output_fasta: Path,
    logger: logging.Logger = None
) -> int:
    """
    Filter sequences by keeper species list.
    
    Args:
        input_fasta: Input FASTA file
        keeper_species: Set of keeper species names
        output_fasta: Output FASTA file
        logger: Logger instance
        
    Returns:
        Number of sequences kept
    """
    kept_count = 0
    dropped_count = 0
    
    with open( input_fasta, 'r' ) as input_file, \
         open( output_fasta, 'w' ) as output_file:
        
        should_write = False
        
        for line in input_file:
            if line.startswith( '>' ):
                # Header line - check if species is in keeper list
                header = line[1:].strip()
                
                # Try to extract species name from header
                # Common patterns: Genus_species or similar
                is_keeper = False
                for species in keeper_species:
                    if species in header:
                        is_keeper = True
                        break
                
                should_write = is_keeper
                
                if should_write:
                    output_file.write( line )
                    kept_count += 1
                else:
                    dropped_count += 1
            elif should_write:
                # Sequence line
                output_file.write( line )
    
    if logger:
        logger.info( f"Kept {kept_count} sequences" )
        logger.info( f"Dropped {dropped_count} sequences" )
    
    return kept_count


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Filter sequences by species keeper list'
    )
    
    parser.add_argument(
        '--input-fasta',
        type=Path,
        default=Path( 'output/13-output/13_ai-cgs-all-reciprocal_best_hits.aa' ),
        help='Input FASTA file (from script 013)'
    )
    
    parser.add_argument(
        '--species-keeper-list',
        type=Path,
        default=Path( 'input/species-keeper-list' ),
        help='File with species to keep'
    )
    
    parser.add_argument(
        '--output-fasta',
        type=Path,
        default=Path( 'output/14-output/14_ai-cgs-filtered_by_species.aa' ),
        help='Output FASTA file'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path( '014_ai-log-filter_species_for_tree_building.log' )
    logger = setup_logging( log_file )
    
    logger.info( "="*80 )
    logger.info( "Filter Sequences by Species Keeper List" )
    logger.info( "="*80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    
    # Create script output directory
    script_output_dir = args.output_fasta.parent
    script_output_dir.mkdir( parents=True, exist_ok=True )
    
    # Validate inputs
    if not args.input_fasta.exists():
        logger.error( f"Input FASTA not found: {args.input_fasta}" )
        sys.exit( 1 )
    
    if not args.species_keeper_list.exists():
        logger.error( f"Species keeper list not found: {args.species_keeper_list}" )
        sys.exit( 1 )
    
    # Load keeper species
    logger.info( "\nLoading species keeper list..." )
    keeper_species = load_species_keeper_list( args.species_keeper_list, logger )
    
    if not keeper_species:
        logger.warning( "No keeper species found!" )
        args.output_fasta.touch()
        sys.exit( 0 )
    
    # Filter sequences
    logger.info( "\nFiltering sequences..." )
    kept_count = filter_sequences_by_species(
        args.input_fasta,
        keeper_species,
        args.output_fasta,
        logger
    )
    
    logger.info( "\n" + "="*80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "="*80 )
    logger.info( f"\nOutput file: {args.output_fasta} ({kept_count} sequences)" )
    logger.info( f"Log file: {log_file}" )
    logger.info( f"\nScript completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == "__main__":
    main()

