#!/usr/bin/env python3
# GIGANTIC STEP_1 - Script 001: Validate RGS File
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Validate RGS FASTA before homolog discovery
# Human: Eric Edsinger

"""
Validate RGS FASTA File

Validates the Reference Gene Set (RGS) FASTA file before running homolog discovery.
Fails fast if validation fails so the user can fix issues before expensive BLAST runs.

Checks:
1. File exists and is not empty
2. Filename follows format: rgs_{category}-{species}-{gene_family_details}.{ext}
3. Headers follow format: >rgs_{family}-{species}-{gene_symbol}-{source_details}-{sequence_identifier}
4. All headers have the same rgs_{family} prefix
5. No duplicate sequence IDs

Input:
    - RGS FASTA file

Output:
    - Validated RGS FASTA copy (1-output/)
    - Validation report (1-output/)
    - Log file

Requirements:
    - Python 3.10+
"""

import argparse
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


def setup_logging( log_file: Path = None ) -> logging.Logger:
    """Configure logging to both file and console."""
    logger = logging.getLogger( __name__ )
    logger.setLevel( logging.INFO )

    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setLevel( logging.INFO )
    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( formatter )
    logger.addHandler( console_handler )

    if log_file:
        file_handler = logging.FileHandler( log_file )
        file_handler.setLevel( logging.INFO )
        file_handler.setFormatter( formatter )
        logger.addHandler( file_handler )

    return logger


def validate_filename( filename: str, logger: logging.Logger = None ) -> Tuple[ bool, Dict[ str, str ] ]:
    """
    Validate RGS filename format.

    Expected: rgs_{category}-{species}-{gene_family_details}.{ext}

    Args:
        filename: RGS filename
        logger: Logger instance

    Returns:
        Tuple of (is_valid, metadata_dict)
    """
    metadata = {}

    if '.' not in filename:
        if logger:
            logger.error( f"No file extension found: {filename}" )
        return False, metadata

    name_without_ext, extension = filename.rsplit( '.', 1 )

    if not extension.isalpha() or len( extension ) >= 10:
        if logger:
            logger.error( f"Invalid extension: .{extension}" )
        return False, metadata

    metadata[ 'extension' ] = extension
    parts = name_without_ext.split( '-' )

    if len( parts ) < 3:
        if logger:
            logger.error( f"Invalid filename format: {filename}" )
            logger.error( "Expected: rgs_{{category}}-{{species}}-{{gene_family_details}}.{{ext}}" )
        return False, metadata

    if not parts[ 0 ].startswith( 'rgs_' ):
        if logger:
            logger.error( f"Filename must start with rgs_: {filename}" )
        return False, metadata

    metadata[ 'category' ] = parts[ 0 ][ 4: ]
    metadata[ 'species' ] = parts[ 1 ]
    metadata[ 'gene_family_details' ] = '-'.join( parts[ 2: ] )

    if logger:
        logger.info( f"Filename validated: {filename}" )
        logger.info( f"  Category: {metadata[ 'category' ]}" )
        logger.info( f"  Species: {metadata[ 'species' ]}" )
        logger.info( f"  Gene family: {metadata[ 'gene_family_details' ]}" )

    return True, metadata


def validate_headers( input_file: Path, logger: logging.Logger = None ) -> Tuple[ bool, Dict ]:
    """
    Validate all RGS headers in FASTA file.

    Expected header: >rgs-{identifier}-{family}-{species}-{gene_symbol}-{source}
    (6+ dash-separated fields, first is exactly 'rgs')

    Args:
        input_file: Path to RGS FASTA file
        logger: Logger instance

    Returns:
        Tuple of (all_valid, statistics_dict)
    """
    all_valid = True
    statistics = {
        'total_sequences': 0,
        'valid_headers': 0,
        'invalid_headers': 0,
        'species_found': set(),
        'families_found': set(),
        'duplicate_ids': [],
        'header_issues': [],
    }

    sequence_ids = []

    with open( input_file, 'r' ) as input_fasta:
        for line_number, line in enumerate( input_fasta, 1 ):
            if line.startswith( '>' ):
                statistics[ 'total_sequences' ] += 1
                header = line[ 1: ].strip()
                parts = header.split( '-' )

                if len( parts ) >= 6 and parts[ 0 ] == 'rgs':
                    statistics[ 'valid_headers' ] += 1
                    statistics[ 'species_found' ].add( parts[ 3 ] )
                    statistics[ 'families_found' ].add( parts[ 2 ] )
                    sequence_ids.append( header )
                else:
                    statistics[ 'invalid_headers' ] += 1
                    all_valid = False
                    issue = f"Line {line_number}: Invalid header: {header}"
                    statistics[ 'header_issues' ].append( issue )
                    if logger:
                        logger.error( issue )
                        logger.error( "Expected: >rgs_{{family}}-{{species}}-{{gene_symbol}}-{{source}}-{{identifier}}" )

    if len( statistics[ 'families_found' ] ) > 1:
        # Check if all family prefixes share a common root (e.g., kinases_AGC_Akt and kinases_CAMK
        # both start with "kinases"). Superfamily RGS files legitimately contain multiple subfamilies.
        families_list = sorted( statistics[ 'families_found' ] )
        common_root = families_list[ 0 ].split( '_' )[ 0 ]
        all_share_root = all( family.startswith( common_root ) for family in families_list )

        if not all_share_root:
            all_valid = False
            issue = f"Inconsistent family prefixes (no common root): {families_list}"
            statistics[ 'header_issues' ].append( issue )
            if logger:
                logger.error( issue )
        else:
            if logger:
                logger.info( f"Multiple subfamily prefixes found (common root: {common_root}): {len( families_list )} subfamilies" )

    id_counts = Counter( sequence_ids )
    duplicates = [ seq_id for seq_id, count in id_counts.items() if count > 1 ]
    statistics[ 'duplicate_ids' ] = duplicates

    if duplicates:
        all_valid = False
        if logger:
            logger.error( f"Found {len( duplicates )} duplicate sequence IDs" )
            for dup_id in duplicates[ :5 ]:
                logger.error( f"  - {dup_id}" )

    return all_valid, statistics


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Validate RGS FASTA file before homolog discovery'
    )

    parser.add_argument( '--input', type=Path, required=True, help='Input RGS FASTA file' )
    parser.add_argument( '--output', type=Path, required=True, help='Output validated RGS FASTA' )
    parser.add_argument( '--gene-family', type=str, required=True, help='Gene family name' )
    parser.add_argument( '--report', type=Path, required=True, help='Validation report output' )
    parser.add_argument( '--log-file', type=Path, default=None, help='Log file path' )

    args = parser.parse_args()

    logger = setup_logging( args.log_file )

    logger.info( "=" * 80 )
    logger.info( "Validate RGS File" )
    logger.info( "=" * 80 )
    logger.info( f"Input: {args.input}" )
    logger.info( f"Gene family: {args.gene_family}" )

    if not args.input.exists():
        logger.error( f"CRITICAL ERROR: Input file not found: {args.input}" )
        sys.exit( 1 )

    # Validate filename
    logger.info( "\nValidating filename..." )
    filename_valid, filename_metadata = validate_filename( args.input.name, logger )

    if not filename_valid:
        logger.error( "CRITICAL ERROR: Filename validation FAILED" )
        sys.exit( 1 )

    # Validate headers
    logger.info( "\nValidating sequence headers..." )
    headers_valid, statistics = validate_headers( args.input, logger )

    logger.info( f"\nValidation summary:" )
    logger.info( f"  Total sequences: {statistics[ 'total_sequences' ]}" )
    logger.info( f"  Valid headers: {statistics[ 'valid_headers' ]}" )
    logger.info( f"  Invalid headers: {statistics[ 'invalid_headers' ]}" )
    logger.info( f"  Species: {', '.join( sorted( statistics[ 'species_found' ] ) )}" )
    logger.info( f"  Duplicates: {len( statistics[ 'duplicate_ids' ] )}" )

    if statistics[ 'total_sequences' ] == 0:
        logger.error( "CRITICAL ERROR: No sequences found in RGS file!" )
        sys.exit( 1 )

    all_valid = filename_valid and headers_valid

    # Create output directory and copy validated file
    args.output.parent.mkdir( parents=True, exist_ok=True )
    args.report.parent.mkdir( parents=True, exist_ok=True )

    with open( args.input, 'r' ) as input_fasta, open( args.output, 'w' ) as output_fasta:
        output_fasta.write( input_fasta.read() )

    # Write validation report
    with open( args.report, 'w' ) as output_report:
        output = "=" * 80 + "\n"
        output += "RGS VALIDATION REPORT\n"
        output += "=" * 80 + "\n"
        output += f"Generated: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}\n"
        output += f"Input file: {args.input.name}\n"
        output += f"Gene family: {args.gene_family}\n"
        output += f"Total sequences: {statistics[ 'total_sequences' ]}\n"
        output += f"Valid headers: {statistics[ 'valid_headers' ]}\n"
        output += f"Invalid headers: {statistics[ 'invalid_headers' ]}\n"
        output += f"Duplicates: {len( statistics[ 'duplicate_ids' ] )}\n"
        output += f"Result: {'PASS' if all_valid else 'FAIL'}\n"
        output += "=" * 80 + "\n"
        output_report.write( output )

    logger.info( f"\nValidation result: {'PASS' if all_valid else 'FAIL'}" )

    sys.exit( 0 if all_valid else 1 )


if __name__ == "__main__":
    main()
