#!/usr/bin/env python3
# GIGANTIC BLOCK 1 - Script 001: Validate and Prepare RGS Files
# AI: Claude Code | Sonnet 4.5 | 2025 November 09 10:45 | Purpose: Validate and prepare RGS files for GIGANTIC workflow
# Human: Eric Edsinger

"""
Validate and Prepare RGS Files

This script validates RGS FASTA files and prepares them for downstream STEP_2 processing:
1. Validates filename follows GIGANTIC_1 format
2. Validates headers follow: >rgs_{family}-{species}-{gene_symbol}-{source_details}-{sequence_identifier}
3. Checks for duplicate sequences
4. Extracts species short names for downstream use
5. Creates standardized rgs.aa output
6. Generates validation report

This is STEP_1 - the entry point for RGS into the gene families pipeline.
"""

import argparse
import hashlib
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


def setup_logging( log_file: Path = None ) -> logging.Logger:
    """
    Configure logging to both file and console.
    
    Args:
        log_file: Path to log file (optional)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger( __name__ )
    logger.setLevel( logging.INFO )
    
    # Console handler
    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setLevel( logging.INFO )
    console_formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_formatter )
    logger.addHandler( console_handler )
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler( log_file )
        file_handler.setLevel( logging.INFO )
        file_handler.setFormatter( console_formatter )
        logger.addHandler( file_handler )
    
    return logger


def validate_filename( filename: str, gene_family: str, logger: logging.Logger = None ) -> Tuple[bool, Dict[str, str]]:
    """
    Validate RGS filename and extract metadata.

    Expected format: rgs_{category}-{species_short_names}-{gene_family_details}.{ext}
    Where:
        category = functional category (e.g., channel, receptor, ligand, enzyme, transporter, tf, structure)
        species_short_names = reference species separated by underscores (e.g., human, human_worm_fly)
        gene_family_details = descriptive gene family name
        ext = file extension (alpha only, <10 characters)
              common: fasta, fa, aa, pep

    Args:
        filename: RGS filename
        gene_family: Expected gene family name
        logger: Logger instance

    Returns:
        Tuple of (is_valid, metadata_dict)
    """
    metadata = {}

    # Check for file extension
    if '.' not in filename:
        if logger:
            logger.error( f"No file extension found: {filename}" )
        return False, metadata

    # Split filename and extension
    name_without_ext, extension = filename.rsplit( '.', 1 )

    # Validate extension: alpha only, <10 characters
    if not extension.isalpha() or len( extension ) >= 10:
        if logger:
            logger.error( f"Invalid extension: .{extension}" )
            logger.error( "Extension must be alphabetic and less than 10 characters" )
            logger.error( "Common extensions: fasta, fa, aa, pep" )
        return False, metadata

    metadata['extension'] = extension

    # Split by dash
    parts = name_without_ext.split( '-' )

    if len( parts ) < 3:
        if logger:
            logger.error( f"Invalid filename format: {filename}" )
            logger.error( "Expected: rgs_{category}-{species}-{gene_family_details}.{ext}" )
            logger.error( "Example: rgs_channel-human_worm_fly-innexin_pannexin_channels.aa" )
        return False, metadata

    # Validate first part starts with rgs_
    rgs_part = parts[0]
    if not rgs_part.startswith( 'rgs_' ):
        if logger:
            logger.error( f"Invalid rgs format: {rgs_part}" )
            logger.error( "Expected: rgs_{category} (e.g., rgs_channel, rgs_receptor, rgs_ligand)" )
        return False, metadata

    # Extract metadata
    metadata['category'] = rgs_part[4:]  # Everything after 'rgs_'
    metadata['species'] = parts[1]
    metadata['gene_family_details'] = '-'.join( parts[2:] )

    if logger:
        logger.info( f"Filename validated: {filename}" )
        logger.info( f"  Category: {metadata['category']}" )
        logger.info( f"  Species: {metadata['species']}" )
        logger.info( f"  Gene family details: {metadata['gene_family_details']}" )

    return True, metadata


def parse_rgs_header( header: str ) -> Tuple[bool, Dict[str, str]]:
    """
    Parse RGS FASTA header and extract components.

    Expected format: >rgs_{family}-{species}-{gene_symbol}-{source_details}-{sequence_identifier}
    5 dash-separated fields.

    Args:
        header: FASTA header (without >)

    Returns:
        Tuple of (is_valid, components_dict)
    """
    components = {}

    parts = header.split( '-' )

    if len( parts ) < 5:
        return False, components

    # First part must start with rgs_
    rgs_part = parts[0]
    if not rgs_part.startswith( 'rgs_' ):
        return False, components

    components['family'] = rgs_part[4:]  # Everything after 'rgs_'
    components['species_short_name'] = parts[1]
    components['gene_symbol'] = parts[2]
    components['source_details'] = parts[3]
    components['sequence_identifier'] = '-'.join( parts[4:] )  # Rest is identifier

    return True, components


def validate_headers(
    input_file: Path,
    gene_family: str,
    logger: logging.Logger = None
) -> Tuple[bool, Dict[str, any]]:
    """
    Validate all RGS headers in FASTA file.

    Checks:
    - All headers follow >rgs_{family}-{species}-{gene_symbol}-{source}-{identifier} format (5 fields)
    - All headers have the same rgs_{family} prefix
    - No duplicate sequence IDs

    Args:
        input_file: Path to RGS FASTA file
        gene_family: Expected gene family name (not checked in headers, only filename)
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
                statistics['total_sequences'] += 1
                header = line[1:].strip()

                # Parse header
                is_valid, components = parse_rgs_header( header )

                if is_valid:
                    statistics['valid_headers'] += 1
                    statistics['species_found'].add( components['species_short_name'] )
                    statistics['families_found'].add( components['family'] )
                    sequence_ids.append( header )
                else:
                    statistics['invalid_headers'] += 1
                    all_valid = False
                    issue = f"Line {line_number}: Invalid header format: {header}"
                    statistics['header_issues'].append( issue )
                    if logger:
                        logger.error( issue )
                        logger.error( "Expected: >rgs_{family}-{species}-{gene_symbol}-{source_details}-{sequence_identifier}" )

    # Check that all headers have the same rgs_{family} prefix
    if len( statistics['families_found'] ) > 1:
        all_valid = False
        issue = f"Inconsistent family prefixes in headers: {sorted(statistics['families_found'])}"
        statistics['header_issues'].append( issue )
        if logger:
            logger.error( issue )
            logger.error( "All headers in one RGS file should have the same rgs_{family} prefix" )

    # Check for duplicates
    id_counts = Counter( sequence_ids )
    duplicates = [ seq_id for seq_id, count in id_counts.items() if count > 1 ]
    statistics['duplicate_ids'] = duplicates

    if duplicates:
        all_valid = False
        if logger:
            logger.error( f"Found {len(duplicates)} duplicate sequence IDs:" )
            for dup_id in duplicates[:5]:  # Show first 5
                logger.error( f"  - {dup_id}" )
            if len( duplicates ) > 5:
                logger.error( f"  ... and {len(duplicates) - 5} more" )

    return all_valid, statistics


def create_rgs_output( input_file: Path, output_file: Path, logger: logging.Logger = None ):
    """
    Create standardized rgs.aa output file.
    
    This is a direct copy for now, but could include:
    - Reformatting
    - Sequence cleaning
    - Additional validation
    
    Args:
        input_file: Path to input RGS FASTA
        output_file: Path to output rgs.aa file
        logger: Logger instance
    """
    with open( input_file, 'r' ) as input_fasta, open( output_file, 'w' ) as output_fasta:
        output_fasta.write( input_fasta.read() )
    
    if logger:
        logger.info( f"Created standardized output: {output_file}" )


def write_validation_report(
    output_file: Path,
    input_filename: str,
    gene_family: str,
    filename_metadata: Dict[str, str],
    statistics: Dict[str, any],
    all_valid: bool,
    logger: logging.Logger = None
):
    """
    Write validation report.
    
    Args:
        output_file: Path to validation report file
        input_filename: Input RGS filename
        gene_family: Gene family name
        filename_metadata: Metadata extracted from filename
        statistics: Header validation statistics
        all_valid: Overall validation result
        logger: Logger instance
    """
    with open( output_file, 'w' ) as output_report:
        output = "=" * 80 + "\n"
        output += "RGS VALIDATION REPORT\n"
        output += "=" * 80 + "\n"
        output += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        output += f"\n"
        
        output += "FILE INFORMATION\n"
        output += "-" * 80 + "\n"
        output += f"Input file: {input_filename}\n"
        output += f"Gene family: {gene_family}\n"
        output += f"Category: {filename_metadata.get('category', 'N/A')}\n"
        output += f"Species: {filename_metadata.get('species', 'N/A')}\n"
        output += f"Gene family details: {filename_metadata.get('gene_family_details', 'N/A')}\n"
        output += f"\n"
        
        output += "VALIDATION STATISTICS\n"
        output += "-" * 80 + "\n"
        output += f"Total sequences: {statistics['total_sequences']}\n"
        output += f"Valid headers: {statistics['valid_headers']}\n"
        output += f"Invalid headers: {statistics['invalid_headers']}\n"
        output += f"Unique species: {len(statistics['species_found'])}\n"
        output += f"Duplicate IDs: {len(statistics['duplicate_ids'])}\n"
        output += f"\n"
        
        if statistics['species_found']:
            output += "SPECIES FOUND\n"
            output += "-" * 80 + "\n"
            for species in sorted( statistics['species_found'] ):
                output += f"  - {species}\n"
            output += f"\n"
        
        if statistics['header_issues']:
            output += "HEADER ISSUES\n"
            output += "-" * 80 + "\n"
            for issue in statistics['header_issues'][:20]:  # Show first 20
                output += f"  {issue}\n"
            if len( statistics['header_issues'] ) > 20:
                output += f"  ... and {len(statistics['header_issues']) - 20} more issues\n"
            output += f"\n"
        
        if statistics['duplicate_ids']:
            output += "DUPLICATE SEQUENCE IDs\n"
            output += "-" * 80 + "\n"
            for dup_id in statistics['duplicate_ids'][:10]:  # Show first 10
                output += f"  {dup_id}\n"
            if len( statistics['duplicate_ids'] ) > 10:
                output += f"  ... and {len(statistics['duplicate_ids']) - 10} more duplicates\n"
            output += f"\n"
        
        output += "=" * 80 + "\n"
        output += f"VALIDATION RESULT: {'PASS' if all_valid else 'FAIL'}\n"
        output += "=" * 80 + "\n"
        
        output_report.write( output )
    
    if logger:
        logger.info( f"Wrote validation report: {output_file}" )


def main():
    """
    Main execution function.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Validate and prepare RGS files for GIGANTIC workflow'
    )
    
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Path to input RGS FASTA file'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Path to output rgs.aa file'
    )
    
    parser.add_argument(
        '--gene-family',
        type=str,
        required=True,
        help='Gene family name'
    )
    
    parser.add_argument(
        '--report',
        type=Path,
        required=True,
        help='Path to validation report output file'
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        default=None,
        help='Path to log file (optional)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging( args.log_file )
    
    logger.info( "=" * 80 )
    logger.info( "Validate and Prepare RGS Files" )
    logger.info( "=" * 80 )
    logger.info( f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" )
    logger.info( "" )
    logger.info( f"Input file: {args.input}" )
    logger.info( f"Output file: {args.output}" )
    logger.info( f"Gene family: {args.gene_family}" )
    logger.info( f"Validation report: {args.report}" )
    
    # Check if input file exists
    if not args.input.exists():
        logger.error( f"Input file not found: {args.input}" )
        sys.exit( 1 )
    
    # Validate filename
    logger.info( "\nValidating filename..." )
    filename_valid, filename_metadata = validate_filename( args.input.name, args.gene_family, logger )
    
    if not filename_valid:
        logger.error( "Filename validation FAILED" )
        sys.exit( 1 )
    
    # Validate headers
    logger.info( "\nValidating sequence headers..." )
    headers_valid, statistics = validate_headers( args.input, args.gene_family, logger )
    
    logger.info( f"\nValidation summary:" )
    logger.info( f"  Total sequences: {statistics['total_sequences']}" )
    logger.info( f"  Valid headers: {statistics['valid_headers']}" )
    logger.info( f"  Invalid headers: {statistics['invalid_headers']}" )
    logger.info( f"  Unique species: {len(statistics['species_found'])}" )
    logger.info( f"  Species: {', '.join(sorted(statistics['species_found']))}" )
    logger.info( f"  Duplicate IDs: {len(statistics['duplicate_ids'])}" )
    
    # Create output
    logger.info( "\nCreating standardized output..." )
    create_rgs_output( args.input, args.output, logger )
    
    # Write validation report
    logger.info( "\nWriting validation report..." )
    all_valid = filename_valid and headers_valid
    write_validation_report(
        args.report,
        args.input.name,
        args.gene_family,
        filename_metadata,
        statistics,
        all_valid,
        logger
    )
    
    # Summary
    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "=" * 80 )
    logger.info( f"Validation result: {'PASS' if all_valid else 'FAIL'}" )
    logger.info( f"Output created: {args.output}" )
    logger.info( f"Report created: {args.report}" )
    logger.info( "" )
    logger.info( f"Script completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" )
    
    # Exit with appropriate code
    sys.exit( 0 if all_valid else 1 )


if __name__ == "__main__":
    main()

