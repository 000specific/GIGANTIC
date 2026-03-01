#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 015: Remap CGS Identifiers to GIGANTIC
# AI: Claude Code | Sonnet 4.5 | 2025 November 11 16:07 | Purpose: Remap short CGS identifiers to full GIGANTIC phyloname identifiers
# Human: Eric Edsinger

"""
Remap CGS Identifiers to Full GIGANTIC Phylonames

This script converts short sequence identifiers (Genus_species-number) used in 
BLAST databases back to full GIGANTIC phyloname identifiers. This is necessary 
because:
1. Short identifiers are used in BLAST databases for efficiency
2. Full GIGANTIC identifiers are needed for phylogenetic analysis and visualization
3. The mapping file connects: short_id → full_gigantic_phyloname

Input:
    - output/14-output/14_ai-cgs-{project_db}-{gene_family}-filtered.aa: CGS with short IDs
    - Mapping file: Provided via --mapping-file argument (configurable via gene_families_config.yaml)

Output:
    - output/15-output/15_ai-cgs-{project_db}-{gene_family}-remapped.aa: CGS with full GIGANTIC IDs

Log:
    - 015_ai-log-remap_cgs_identifiers.log

Requirements:
    - Python 3.10+
"""

from pathlib import Path
from typing import Dict, Tuple
import argparse
import logging
from datetime import datetime
import sys


def setup_logging( log_file_path: Path ) -> logging.Logger:
    """Configure logging for the script."""
    logger = logging.getLogger( __name__ )
    logger.setLevel( logging.DEBUG )
    
    # File handler
    file_handler = logging.FileHandler( log_file_path )
    file_handler.setLevel( logging.DEBUG )
    
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


def load_identifier_mapping(
    mapping_file: Path,
    logger: logging.Logger = None
) -> Dict[str, str]:
    """
    Load mapping from short identifiers to full GIGANTIC identifiers.
    
    Args:
        mapping_file: TSV file with format: short_id\tfull_gigantic_id
        logger: Logger instance
        
    Returns:
        Dictionary mapping short_ids to full_gigantic_ids
    """
    short_ids___gigantic_ids = {}
    
    if not mapping_file.exists():
        error_msg = f"Mapping file not found: {mapping_file}"
        if logger:
            logger.error( error_msg )
        raise FileNotFoundError( error_msg )
    
    if logger:
        logger.info( f"Loading identifier mapping from: {mapping_file}" )
    
    with open( mapping_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split( '\t' )
            if len( parts ) != 2:
                if logger:
                    logger.warning( f"Skipping malformed line: {line}" )
                continue
            
            short_id = parts[ 0 ]
            gigantic_id = parts[ 1 ]
            short_ids___gigantic_ids[ short_id ] = gigantic_id
    
    if logger:
        logger.info( f"Loaded {len(short_ids___gigantic_ids)} identifier mappings" )
    
    return short_ids___gigantic_ids


def remap_fasta_identifiers(
    input_fasta: Path,
    output_fasta: Path,
    short_ids___gigantic_ids: Dict[str, str],
    logger: logging.Logger = None
) -> Tuple[int, int, int]:
    """
    Remap FASTA sequence identifiers from short to full GIGANTIC format.
    
    Args:
        input_fasta: Input FASTA with short identifiers
        output_fasta: Output FASTA with GIGANTIC identifiers
        short_ids___gigantic_ids: Mapping dictionary
        logger: Logger instance
        
    Returns:
        Tuple of (sequences processed, remapped, not found in map)
    """
    sequences_processed = 0
    sequences_remapped = 0
    sequences_not_found = 0
    
    # Create output directory
    output_fasta.parent.mkdir( parents=True, exist_ok=True )
    
    with open( input_fasta, 'r' ) as input_file, \
         open( output_fasta, 'w' ) as output_file:
        
        for line in input_file:
            if line.startswith( '>' ):
                sequences_processed += 1
                short_id = line[ 1: ].strip()
                
                if short_id in short_ids___gigantic_ids:
                    # Remap to full GIGANTIC identifier
                    gigantic_id = short_ids___gigantic_ids[ short_id ]
                    output = f">{gigantic_id}\n"
                    output_file.write( output )
                    sequences_remapped += 1
                else:
                    # Keep original if not found in mapping
                    if logger:
                        logger.warning( f"Identifier not found in mapping: {short_id}" )
                    output_file.write( line )
                    sequences_not_found += 1
            else:
                # Write sequence line as-is
                output_file.write( line )
    
    return sequences_processed, sequences_remapped, sequences_not_found


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Remap CGS identifiers from short to full GIGANTIC format'
    )
    
    parser.add_argument(
        '--input-fasta',
        type=Path,
        required=True,
        help='Input CGS FASTA file with short identifiers'
    )
    
    parser.add_argument(
        '--output-fasta',
        type=Path,
        required=True,
        help='Output CGS FASTA file with full GIGANTIC identifiers'
    )
    
    parser.add_argument(
        '--mapping-file',
        type=Path,
        required=True,
        help='TSV mapping file: short_id\tgigantic_id (path relative to workspace_root or absolute path)'
    )
    
    parser.add_argument(
        '--gene-family',
        type=str,
        required=True,
        help='Gene family name (for logging)'
    )
    
    parser.add_argument(
        '--project-db',
        type=str,
        default='species67_T1-species37',
        help='Project database identifier (for logging)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path( '015_ai-log-remap_cgs_identifiers.log' )
    logger = setup_logging( log_file )
    
    logger.info( "="*80 )
    logger.info( "Remap CGS Identifiers to Full GIGANTIC Format" )
    logger.info( "="*80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Gene family: {args.gene_family}" )
    logger.info( f"Project DB: {args.project_db}" )
    
    # Validate inputs
    if not args.input_fasta.exists():
        logger.error( f"Input FASTA not found: {args.input_fasta}" )
        sys.exit( 1 )
    
    if not args.mapping_file.exists():
        logger.error( f"Mapping file not found: {args.mapping_file}" )
        logger.error( "This file connects short BLAST database identifiers to full GIGANTIC phylonames" )
        sys.exit( 1 )
    
    logger.info( f"Input FASTA: {args.input_fasta}" )
    logger.info( f"Output FASTA: {args.output_fasta}" )
    logger.info( f"Mapping file: {args.mapping_file}" )
    
    try:
        # Load identifier mapping
        short_ids___gigantic_ids = load_identifier_mapping( args.mapping_file, logger )
        
        # Remap FASTA identifiers
        logger.info( "Remapping FASTA sequence identifiers..." )
        sequences_processed, sequences_remapped, sequences_not_found = remap_fasta_identifiers(
            args.input_fasta,
            args.output_fasta,
            short_ids___gigantic_ids,
            logger
        )
        
        # Report results
        logger.info( "="*80 )
        logger.info( "Remapping Statistics:" )
        logger.info( f"  Sequences processed:     {sequences_processed:>6}" )
        logger.info( f"  Sequences remapped:      {sequences_remapped:>6}" )
        logger.info( f"  Not found in mapping:    {sequences_not_found:>6}" )
        logger.info( "="*80 )
        
        if sequences_not_found > 0:
            logger.warning( f"{sequences_not_found} sequences were not found in the mapping file" )
            logger.warning( "These identifiers will remain in their original short format" )
        
        if sequences_remapped == 0:
            logger.error( "CRITICAL ERROR: No sequences were remapped!" )
            logger.error( "This suggests a mismatch between input identifiers and mapping file" )
            sys.exit( 1 )
        
        logger.info( f"Output written to: {args.output_fasta}" )
        logger.info( f"Script completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
        logger.info( "SUCCESS: CGS identifiers remapped to full GIGANTIC format" )
        
    except Exception as e:
        logger.error( f"Script failed with error: {e}" )
        logger.exception( "Full traceback:" )
        sys.exit( 1 )


if __name__ == '__main__':
    main()

