#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 009: Create Modified Genomes
# AI: Claude Code | Sonnet 4.5 | 2025 November 09 18:30 | Purpose: Create modified RBH genomes with RGS sequences inserted
# Human: Eric Edsinger

"""
Create Modified RBH Genomes with RGS Sequences

This script creates modified versions of RBH species genomes where sequences that
were top hits in RGS→genome BLAST are replaced with their corresponding RGS
header and sequence. This enables identification of reciprocal best hits.

The modified genomes contain:
1. Original genome sequences (with GIGANTIC headers)
2. RGS sequences (with truncated headers suitable for BLAST databases) replacing sequences that were top BLAST hits

This replacement allows reciprocal BLAST to identify which BGS sequences hit
back to RGS sequences, forming the basis of RBH/RBF filtering to produce the CGS.

Workflow Context:
    Script 006 → RGS genome BLAST → Script 007 → Lists → Script 008 → Mapping →
    **Script 009** → Modified genomes → Script 010 → Combined database
    
Input Files:
    - input/rgs.aa - RGS sequences (from Block 1)
    - output/8-output/8_ai-map-rgs-to-genome-identifiers.txt - RGS→genome mappings
    - RBH species genome files (paths from script 007)
    
Output Files:
    - output/9-{genome_name}.aa-rgs - Modified genome for each RBH species
    - output/9-list-modified-genomes.txt - List of modified genome paths

Usage:
    python3 009_ai-python-create_modified_genomes.py \\
        --rgs-fasta input/rgs.aa \\
        --mapping-file output/8-map-rgs-to-genome-identifiers.txt \\
        --genome-list output/7-list-model-organism-fastas.txt \\
        --output-dir output \\
        --log-file output/9-log-create-modified-genomes.log
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


def setup_logging( log_file: Path = None ) -> logging.Logger:
    """
    Configure logging with timestamps and levels.
    
    Args:
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger( __name__ )
    logger.setLevel( logging.INFO )
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setFormatter( formatter )
    logger.addHandler( console_handler )
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler( log_file )
        file_handler.setFormatter( formatter )
        logger.addHandler( file_handler )
    
    return logger


def read_rgs_sequences( rgs_fasta: Path, logger: logging.Logger = None ) -> Dict[str, str]:
    """
    Read RGS FASTA file into dictionary.
    
    Args:
        rgs_fasta: Path to RGS FASTA file
        logger: Logger instance
        
    Returns:
        Dictionary mapping RGS headers to sequences
    """
    rgs_sequences = {}
    current_header = None
    current_sequence = []
    
    with open( rgs_fasta, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()
            
            if line.startswith( '>' ):
                # Save previous sequence
                if current_header:
                    rgs_sequences[current_header] = ''.join( current_sequence )
                
                # Start new sequence
                current_header = line[1:]  # Remove '>'
                current_sequence = []
            
            else:
                current_sequence.append( line )
        
        # Save last sequence
        if current_header:
            rgs_sequences[current_header] = ''.join( current_sequence )
    
    if logger:
        logger.info( f"Read {len( rgs_sequences )} RGS sequences" )
    
    return rgs_sequences


def read_mapping_file(
    mapping_file: Path,
    logger: logging.Logger = None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Read RGS→genome mapping file.
    
    Format: genome_identifier<TAB>truncated_rgs_header<TAB>original_full_rgs_header
    
    Three columns from script 008:
    - Column 1: genome sequence ID (e.g., Homo_sapiens-12345)
    - Column 2: truncated RGS header (for BLAST database)
    - Column 3: original full RGS header (for sequence lookup in original RGS file)
    
    Args:
        mapping_file: Path to mapping file
        logger: Logger instance
        
    Returns:
        Tuple of dictionaries:
            - genome_identifiers___truncated_rgs_headers: genome ID → truncated header
            - genome_identifiers___full_rgs_headers: genome ID → original full header
    """
    genome_identifiers___truncated_rgs_headers = {}
    genome_identifiers___full_rgs_headers = {}
    
    with open( mapping_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            parts = line.split( '\t' )
            if len( parts ) >= 3:
                # Use THREE columns from script 008
                genome_id = parts[0]                # Column 1: genome sequence ID
                truncated_rgs_header = parts[1]     # Column 2: truncated header
                original_full_rgs_header = parts[2] # Column 3: original full header
                
                genome_identifiers___truncated_rgs_headers[genome_id] = truncated_rgs_header
                genome_identifiers___full_rgs_headers[genome_id] = original_full_rgs_header
            elif len( parts ) >= 2:
                # Backward compatibility: if only 2 columns, use column 2
                genome_id = parts[0]
                rgs_header = parts[1]
                genome_identifiers___truncated_rgs_headers[genome_id] = rgs_header
                genome_identifiers___full_rgs_headers[genome_id] = rgs_header
                if logger:
                    logger.warning( f"Mapping file has only 2 columns (old format): {mapping_file}" )
    
    if logger:
        logger.info( f"Read {len( genome_identifiers___full_rgs_headers )} genome→RGS mappings" )
    
    return genome_identifiers___truncated_rgs_headers, genome_identifiers___full_rgs_headers


def read_genome_list( genome_list_file: Path, logger: logging.Logger = None ) -> List[Path]:
    """
    Read list of genome FASTA file paths.
    
    Args:
        genome_list_file: File containing genome paths
        logger: Logger instance
        
    Returns:
        List of genome file paths
    """
    genome_paths = []
    
    with open( genome_list_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if line:
                genome_paths.append( Path( line ) )
    
    if logger:
        logger.info( f"Read {len( genome_paths )} genome file paths" )
    
    return genome_paths


def create_modified_genome(
    genome_file: Path,
    genome_identifiers___truncated_rgs_headers: Dict[str, str],
    genome_identifiers___full_rgs_headers: Dict[str, str],
    rgs_sequences: Dict[str, str],
    output_dir: Path,
    logger: logging.Logger = None
) -> Path:
    """
    Create modified genome with RGS sequences replacing top hits.
    
    Args:
        genome_file: Path to original genome FASTA
        genome_identifiers___truncated_rgs_headers: Mapping of genome IDs to truncated RGS headers
        genome_identifiers___full_rgs_headers: Mapping of genome IDs to full RGS headers
        rgs_sequences: Dictionary of RGS sequences
        output_dir: Output directory for modified genome
        logger: Logger instance
        
    Returns:
        Path to modified genome file
    """
    # Create script output directory
    script_output_dir = output_dir / "9-output"
    script_output_dir.mkdir( parents=True, exist_ok=True )
    
    # Create output filename: 9_ai-{original_name}.aa-rgs
    output_filename = f"9_ai-{genome_file.name}.aa-rgs"
    output_file = script_output_dir / output_filename
    
    sequences_replaced = 0
    sequences_kept = 0
    current_genome_id = None
    replacement_sequence = None
    writing_replacement = False
    
    with open( genome_file, 'r' ) as input_fasta, open( output_file, 'w' ) as output_fasta:
        for line in input_fasta:
            if line.startswith( '>' ):
                # Get genome sequence identifier
                current_genome_id = line[1:].strip()
                
                # Check if this sequence should be replaced
                if current_genome_id in genome_identifiers___full_rgs_headers:
                    # Replace with RGS sequence
                    rgs_full_header = genome_identifiers___full_rgs_headers[current_genome_id]
                    rgs_truncated_header = genome_identifiers___truncated_rgs_headers.get(
                        current_genome_id,
                        rgs_full_header
                    )
                    replacement_sequence = rgs_sequences.get( rgs_full_header )
                    
                    if replacement_sequence:
                        # Write RGS header (use truncation map if available)
                        output = f">{rgs_truncated_header}\n"
                        output_fasta.write( output )
                        
                        # Write RGS sequence (wrapped at 80 chars)
                        for i in range( 0, len( replacement_sequence ), 80 ):
                            output = replacement_sequence[i:i+80] + '\n'
                            output_fasta.write( output )
                        
                        sequences_replaced += 1
                        writing_replacement = True
                    else:
                        # RGS sequence not found - keep original
                        output_fasta.write( line )
                        sequences_kept += 1
                        writing_replacement = False
                        if logger:
                            logger.warning( f"RGS sequence not found for: {rgs_full_header}" )
                else:
                    # Keep original sequence
                    output_fasta.write( line )
                    sequences_kept += 1
                    writing_replacement = False
            
            else:
                # Sequence line
                if not writing_replacement:
                    # Write original sequence
                    output_fasta.write( line )
                # If writing_replacement is True, skip original sequence (already wrote RGS)
    
    if logger:
        logger.info( f"  Created: {output_file.name}" )
        logger.info( f"    Replaced: {sequences_replaced} sequences" )
        logger.info( f"    Kept: {sequences_kept} sequences" )
    
    return output_file


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Create modified RBH genomes with RGS sequences inserted'
    )
    
    parser.add_argument(
        '--rgs-fasta',
        type=Path,
        required=True,
        help='Path to RGS FASTA file'
    )
    
    parser.add_argument(
        '--mapping-file',
        type=Path,
        required=True,
        help='Path to genome→RGS mapping file (from script 008)'
    )
    
    parser.add_argument(
        '--genome-list',
        type=Path,
        required=True,
        help='Path to file listing RBH genome paths (from script 007)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        required=True,
        help='Output directory for modified genomes'
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        default=None,
        help='Path to log file (optional)'
    )
    
    args = parser.parse_args()
    
    # Create log file directory if needed
    if args.log_file:
        args.log_file.parent.mkdir( parents=True, exist_ok=True )
    
    # Setup logging
    logger = setup_logging( args.log_file )
    
    logger.info( "=" * 80 )
    logger.info( "Create Modified RBH Genomes with RGS Sequences" )
    logger.info( "=" * 80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "" )
    logger.info( f"RGS FASTA: {args.rgs_fasta}" )
    logger.info( f"Mapping file: {args.mapping_file}" )
    logger.info( f"Genome list: {args.genome_list}" )
    logger.info( f"Output directory: {args.output_dir}" )
    
    # Validate inputs
    if not args.rgs_fasta.exists():
        logger.error( f"RGS FASTA not found: {args.rgs_fasta}" )
        sys.exit( 1 )
    
    if not args.mapping_file.exists():
        logger.error( f"Mapping file not found: {args.mapping_file}" )
        sys.exit( 1 )
    
    if not args.genome_list.exists():
        logger.error( f"Genome list not found: {args.genome_list}" )
        sys.exit( 1 )
    
    # Create output directory
    args.output_dir.mkdir( parents=True, exist_ok=True )
    
    # Read RGS sequences
    logger.info( "\nReading RGS sequences..." )
    rgs_sequences = read_rgs_sequences( args.rgs_fasta, logger )
    
    if not rgs_sequences:
        logger.error( "No RGS sequences found!" )
        sys.exit( 1 )
    
    # Read mapping file
    logger.info( "\nReading genome→RGS mappings..." )
    genome_identifiers___truncated_rgs_headers, genome_identifiers___full_rgs_headers = read_mapping_file(
        args.mapping_file,
        logger
    )
    
    if not genome_identifiers___full_rgs_headers:
        logger.error( "No mappings found!" )
        sys.exit( 1 )
    
    # Read genome list
    logger.info( "\nReading genome file list..." )
    genome_paths = read_genome_list( args.genome_list, logger )
    
    if not genome_paths:
        logger.error( "No genome files found!" )
        sys.exit( 1 )
    
    # Create modified genomes
    logger.info( "\nCreating modified genomes..." )
    modified_genomes = []
    
    for genome_file in genome_paths:
        if not genome_file.exists():
            logger.warning( f"Genome file not found (skipping): {genome_file}" )
            continue
        
        logger.info( f"\nProcessing: {genome_file.name}" )
        
        modified_genome = create_modified_genome(
            genome_file,
            genome_identifiers___truncated_rgs_headers,
            genome_identifiers___full_rgs_headers,
            rgs_sequences,
            args.output_dir,
            logger
        )
        
        modified_genomes.append( modified_genome )
    
    # Write list of modified genomes
    script_output_dir = args.output_dir / "9-output"
    modified_list_file = script_output_dir / "9_ai-list-modified-genomes.txt"
    with open( modified_list_file, 'w' ) as output_list:
        for modified_genome in modified_genomes:
            output = str( modified_genome ) + '\n'
            output_list.write( output )
    
    logger.info( f"\nWrote modified genome list: {modified_list_file}" )
    
    # Summary
    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "=" * 80 )
    logger.info( f"RGS sequences: {len( rgs_sequences )}" )
    logger.info( f"Genome→RGS mappings: {len( genome_identifiers___full_rgs_headers )}" )
    logger.info( f"Original genomes processed: {len( genome_paths )}" )
    logger.info( f"Modified genomes created: {len( modified_genomes )}" )
    logger.info( "" )
    logger.info( "Output files:" )
    for modified_genome in modified_genomes:
        logger.info( f"  {modified_genome}" )
    logger.info( f"  {modified_list_file}" )
    logger.info( "" )
    logger.info( f"Script completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == "__main__":
    main()

