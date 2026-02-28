#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 016: Concatenate Sequences
# AI: Claude Code | Opus 4.5 | 2026 January 09 12:00 | Purpose: Concatenate RGS (remapped) and filtered candidate gene set sequences
# Human: Eric Edsinger

"""
Concatenate RGS + Candidate Gene Set (CGS) sequences.

This script concatenates the Reference Gene Set (RGS) with the remapped Candidate
Gene Set (CGS) to create the final All Gene Set (AGS) file for phylogenetic analysis.

NEW: RGS sequences are now also remapped to full GIGANTIC identifiers using the
008 map (RGS → CGS ID) and the main mapping file (CGS ID → GIGANTIC ID).

Input:
    - input/rgs.aa: Reference Gene Set
    - output/15-output/15_ai-CGS-{project_db}-{gene_family}-remapped.aa: Remapped CGS with full GIGANTIC IDs
    - output/8-output/8_ai-map-rgs-to-genome-identifiers.txt: RGS to CGS ID mapping
    - Main mapping file: CGS short ID to full GIGANTIC ID mapping

Output:
    - output/16-output/16_ai-AGS-{project_db}-{gene_family}-homologs.aa: Combined AGS file (both RGS and CGS remapped)

Log:
    - 016_ai-log-concatenate_sequences.log

Requirements:
    - Python 3.10+
"""

from pathlib import Path
from typing import List, Dict, Tuple
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


def load_rgs_to_cgs_map( map_file: Path, logger: logging.Logger = None ) -> Dict[ str, str ]:
    """
    Load RGS to CGS identifier mapping from 008 output.

    File format (tab-separated):
        CGS_short_id    RGS_truncated_header    RGS_full_header

    Args:
        map_file: Path to 8_ai-map-rgs-to-genome-identifiers.txt
        logger: Logger instance

    Returns:
        Dictionary mapping RGS full header to CGS short ID
    """
    rgs_headers___cgs_ids = {}

    if not map_file.exists():
        if logger:
            logger.warning( f"RGS-to-CGS map file not found: {map_file}" )
        return rgs_headers___cgs_ids

    # 8_ai-map-rgs-to-genome-identifiers.txt
    # Homo_sapiens-00372	rgs48-human-hgncgg_2068_NR0B2_Nuclear_recepto_001	rgs48-human-hgncgg_2068_NR0B2_Nuclear_receptor_subfamily_0_group_B...
    with open( map_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )
            if len( parts ) >= 3:
                cgs_short_id = parts[ 0 ]
                rgs_truncated = parts[ 1 ]
                rgs_full_header = parts[ 2 ]

                # Map both truncated and full RGS headers to CGS ID
                rgs_headers___cgs_ids[ rgs_truncated ] = cgs_short_id
                rgs_headers___cgs_ids[ rgs_full_header ] = cgs_short_id

    if logger:
        logger.info( f"Loaded {len(rgs_headers___cgs_ids)} RGS → CGS mappings from 008 map" )

    return rgs_headers___cgs_ids


def load_cgs_to_gigantic_map( map_file: Path, logger: logging.Logger = None ) -> Dict[ str, str ]:
    """
    Load CGS short ID to full GIGANTIC identifier mapping.

    File format (tab-separated):
        CGS_short_id    GIGANTIC_full_id

    Args:
        map_file: Path to main mapping file
        logger: Logger instance

    Returns:
        Dictionary mapping CGS short ID to full GIGANTIC ID
    """
    cgs_ids___gigantic_ids = {}

    if not map_file.exists():
        if logger:
            logger.error( f"CGS-to-GIGANTIC map file not found: {map_file}" )
        return cgs_ids___gigantic_ids

    # 5-map-species67-headers-complete-to-first-50-characters
    # Homo_sapiens-00372	g_OR4F5-t_000-p_NP_001005484.2-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
    with open( map_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )
            if len( parts ) >= 2:
                cgs_short_id = parts[ 0 ]
                gigantic_id = parts[ 1 ]
                cgs_ids___gigantic_ids[ cgs_short_id ] = gigantic_id

    if logger:
        logger.info( f"Loaded {len(cgs_ids___gigantic_ids)} CGS → GIGANTIC mappings" )

    return cgs_ids___gigantic_ids


def remap_rgs_sequences(
    rgs_file: Path,
    rgs_headers___cgs_ids: Dict[ str, str ],
    cgs_ids___gigantic_ids: Dict[ str, str ],
    logger: logging.Logger = None
) -> List[ Tuple[ str, str ] ]:
    """
    Remap RGS sequence headers to full GIGANTIC identifiers.

    Args:
        rgs_file: Path to RGS FASTA file
        rgs_headers___cgs_ids: RGS header to CGS ID mapping
        cgs_ids___gigantic_ids: CGS ID to GIGANTIC ID mapping
        logger: Logger instance

    Returns:
        List of tuples (new_header, sequence)
    """
    remapped_sequences = []
    unmapped_count = 0
    mapped_count = 0

    current_header = None
    current_sequence_parts = []

    with open( rgs_file, 'r' ) as input_file:
        for line in input_file:
            line = line.rstrip( '\n' )

            if line.startswith( '>' ):
                # Save previous sequence if exists
                if current_header is not None:
                    sequence = ''.join( current_sequence_parts )
                    remapped_sequences.append( ( current_header, sequence ) )

                # Process new header
                original_header = line[ 1: ]  # Remove '>'

                # Try to find CGS ID for this RGS header
                cgs_id = None

                # Try exact match first
                if original_header in rgs_headers___cgs_ids:
                    cgs_id = rgs_headers___cgs_ids[ original_header ]
                else:
                    # Try partial match (RGS header might be truncated differently)
                    for rgs_key in rgs_headers___cgs_ids:
                        if original_header.startswith( rgs_key ) or rgs_key.startswith( original_header ):
                            cgs_id = rgs_headers___cgs_ids[ rgs_key ]
                            break

                # If found CGS ID, look up GIGANTIC ID
                if cgs_id and cgs_id in cgs_ids___gigantic_ids:
                    new_header = cgs_ids___gigantic_ids[ cgs_id ]
                    current_header = new_header
                    mapped_count += 1
                    if logger:
                        logger.info( f"  Remapped: {original_header[:50]}... → {new_header[:50]}..." )
                else:
                    # Keep original header if no mapping found
                    current_header = original_header
                    unmapped_count += 1
                    if logger:
                        logger.warning( f"  No mapping found for RGS: {original_header[:60]}..." )

                current_sequence_parts = []
            else:
                current_sequence_parts.append( line )

        # Don't forget last sequence
        if current_header is not None:
            sequence = ''.join( current_sequence_parts )
            remapped_sequences.append( ( current_header, sequence ) )

    if logger:
        logger.info( f"RGS remapping complete: {mapped_count} mapped, {unmapped_count} unmapped" )

    return remapped_sequences


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
        description='Concatenate RGS (remapped) and filtered candidate gene set'
    )

    parser.add_argument(
        '--rgs-file',
        type=Path,
        default=Path( 'input/rgs.aa' ),
        help='Reference Gene Set (RGS) FASTA file'
    )

    parser.add_argument(
        '--cgs-file',
        type=Path,
        default=Path( 'output/15-output/15_ai-CGS-remapped.aa' ),
        help='Candidate Gene Set (CGS) FASTA file with full GIGANTIC identifiers (from script 015)'
    )

    parser.add_argument(
        '--rgs-map-file',
        type=Path,
        default=Path( 'output/8-output/8_ai-map-rgs-to-genome-identifiers.txt' ),
        help='RGS to CGS ID mapping file (from script 008)'
    )

    parser.add_argument(
        '--cgs-mapping-file',
        type=Path,
        required=True,
        help='CGS short ID to full GIGANTIC ID mapping file'
    )

    parser.add_argument(
        '--output-file',
        type=Path,
        help='Output AGS file (default: output/16-output/16_ai-AGS-{project_db}-{gene_family}-homologs.aa)'
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
        default='species67_T1-species67',
        help='Project database identifier'
    )

    args = parser.parse_args()

    # Generate output filename if not provided
    if not args.output_file:
        args.output_file = Path( f"output/16-output/16_ai-AGS-{args.project_db}-{args.gene_family}-homologs.aa" )

    # Setup logging
    log_file = Path( '016_ai-log-concatenate_sequences.log' )
    logger = setup_logging( log_file )

    logger.info( "=" * 80 )
    logger.info( "Concatenate RGS (Remapped) + Candidate Gene Set" )
    logger.info( "=" * 80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Gene family: {args.gene_family}" )
    logger.info( f"Project DB: {args.project_db}" )

    # Validate inputs
    if not args.rgs_file.exists():
        logger.error( f"RGS file not found: {args.rgs_file}" )
        sys.exit( 1 )

    if not args.cgs_file.exists():
        logger.error( f"CGS file not found: {args.cgs_file}" )
        sys.exit( 1 )

    if not args.cgs_mapping_file.exists():
        logger.error( f"CGS mapping file not found: {args.cgs_mapping_file}" )
        sys.exit( 1 )

    # Create output directory if needed
    args.output_file.parent.mkdir( parents=True, exist_ok=True )

    # Load mapping files
    logger.info( "\nLoading mapping files..." )
    rgs_headers___cgs_ids = load_rgs_to_cgs_map( args.rgs_map_file, logger )
    cgs_ids___gigantic_ids = load_cgs_to_gigantic_map( args.cgs_mapping_file, logger )

    # Remap RGS sequences
    logger.info( "\nRemapping RGS sequences to GIGANTIC identifiers..." )
    remapped_rgs = remap_rgs_sequences(
        args.rgs_file,
        rgs_headers___cgs_ids,
        cgs_ids___gigantic_ids,
        logger
    )

    # Write output: remapped RGS + remapped CGS
    logger.info( "\nWriting concatenated AGS file..." )

    rgs_count = len( remapped_rgs )
    cgs_count = count_sequences_in_fasta( args.cgs_file )

    with open( args.output_file, 'w' ) as output_handle:
        # Write remapped RGS sequences
        for header, sequence in remapped_rgs:
            output = '>' + header + '\n' + sequence + '\n'
            output_handle.write( output )

        # Append CGS sequences (already remapped by script 015)
        with open( args.cgs_file, 'r' ) as cgs_handle:
            shutil.copyfileobj( cgs_handle, output_handle )

    total_sequences = rgs_count + cgs_count

    logger.info( "\n" + "=" * 80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "=" * 80 )
    logger.info( f"\nOutput file: {args.output_file}" )
    logger.info( f"Total sequences: {total_sequences}" )
    logger.info( f"  - RGS (remapped): {rgs_count}" )
    logger.info( f"  - CGS (remapped): {cgs_count}" )
    logger.info( f"\nLog file: {log_file}" )
    logger.info( f"\nScript completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == "__main__":
    main()
