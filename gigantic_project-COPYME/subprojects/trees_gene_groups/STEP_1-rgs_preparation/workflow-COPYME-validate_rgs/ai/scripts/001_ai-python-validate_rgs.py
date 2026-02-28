#!/usr/bin/env python3
# GIGANTIC BLOCK 1 - Script 001: Validate and Prepare RGS Files
# AI: Claude Code | Sonnet 4.5 | 2025 November 09 10:45 | Purpose: Validate and prepare RGS files for GIGANTIC workflow
# Human: Eric Edsinger

"""
Validate and Prepare RGS Files

This script validates RGS FASTA files and prepares them for downstream Block 2 processing:
1. Validates filename follows GIGANTIC_1 format
2. Validates headers follow: >rgs-species-family-identifier
3. Checks for duplicate sequences
4. Extracts species short names for downstream use
5. Creates standardized rgs.aa output
6. Generates validation report

This is Block 1 - the entry point for RGS into the gene families pipeline.
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
    
    Expected format: rgsN-gene_family_name-source-date_YYYYmonthDD.{ext}
    Where:
        N = number of sequences (one or more digits)
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
    
    if len( parts ) < 4:
        if logger:
            logger.error( f"Invalid filename format: {filename}" )
            logger.error( "Expected: rgsN-name-source-date.{ext}" )
        return False, metadata
    
    # Validate first part is rgsN format
    rgs_part = parts[0]
    if not rgs_part.startswith( 'rgs' ) or len( rgs_part ) <= 3:
        if logger:
            logger.error( f"Invalid rgs format: {rgs_part}" )
            logger.error( "Expected: rgsN (e.g., rgs3, rgs44)" )
        return False, metadata
    
    # Check digits after 'rgs'
    count_str = rgs_part[3:]
    if not count_str.isdigit():
        if logger:
            logger.error( f"Invalid rgs format: {rgs_part}" )
            logger.error( "Expected digits after 'rgs' (e.g., rgs3, rgs44)" )
        return False, metadata
    
    # Extract metadata
    metadata['sequence_count'] = int( count_str )
    metadata['rgs_name'] = parts[1]
    metadata['source'] = parts[2]
    metadata['date'] = '-'.join( parts[3:] )  # In case date has dashes
    
    if logger:
        logger.info( f"Filename validated: {filename}" )
        logger.info( f"  Sequence count (from filename): {metadata['sequence_count']}" )
        logger.info( f"  RGS name: {metadata['rgs_name']}" )
        logger.info( f"  Source: {metadata['source']}" )
        logger.info( f"  Date: {metadata['date']}" )
    
    return True, metadata


def parse_rgs_header( header: str ) -> Tuple[bool, Dict[str, str]]:
    """
    Parse RGS FASTA header and extract components.
    
    Expected format: >rgsN-species-source-identifier
    Where N = number of sequences in file
    
    Args:
        header: FASTA header (without >)
        
    Returns:
        Tuple of (is_valid, components_dict)
    """
    components = {}
    
    parts = header.split( '-' )
    
    if len( parts ) < 4:
        return False, components
    
    # First part must be rgsN
    rgs_part = parts[0]
    if not rgs_part.startswith( 'rgs' ) or len( rgs_part ) <= 3:
        return False, components
    
    # Validate digits after 'rgs'
    count_str = rgs_part[3:]
    if not count_str.isdigit():
        return False, components
    
    components['sequence_count'] = int( count_str )
    components['species_short_name'] = parts[1]
    components['source'] = parts[2]
    components['identifier'] = '-'.join( parts[3:] )  # Rest is identifier
    
    return True, components


def validate_headers(
    input_file: Path,
    gene_family: str,
    logger: logging.Logger = None
) -> Tuple[bool, Dict[str, any]]:
    """
    Validate all RGS headers in FASTA file.
    
    Checks:
    - All headers follow rgsN-species-source-identifier format
    - All headers have the same N value
    - The N value matches the actual sequence count
    
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
        'duplicate_ids': [],
        'header_issues': [],
        'sequence_counts_in_headers': set()  # Track all N values found
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
                    statistics['sequence_counts_in_headers'].add( components['sequence_count'] )
                    sequence_ids.append( header )
                else:
                    statistics['invalid_headers'] += 1
                    all_valid = False
                    issue = f"Line {line_number}: Invalid header format: {header}"
                    statistics['header_issues'].append( issue )
                    if logger:
                        logger.error( issue )
                        logger.error( "Expected: >rgsN-species-source-identifier" )
    
    # Check that all headers have the same N value
    if len( statistics['sequence_counts_in_headers'] ) > 1:
        all_valid = False
        issue = f"Inconsistent sequence counts in headers: {sorted(statistics['sequence_counts_in_headers'])}"
        statistics['header_issues'].append( issue )
        if logger:
            logger.error( issue )
            logger.error( "All headers must have the same rgsN value" )
    
    # Check that N matches actual sequence count
    if len( statistics['sequence_counts_in_headers'] ) == 1:
        header_count = list( statistics['sequence_counts_in_headers'] )[0]
        actual_count = statistics['total_sequences']
        if header_count != actual_count:
            all_valid = False
            issue = f"Sequence count mismatch: headers say rgs{header_count}, but file has {actual_count} sequences"
            statistics['header_issues'].append( issue )
            if logger:
                logger.error( issue )
    
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
        output += f"RGS name: {filename_metadata.get('rgs_name', 'N/A')}\n"
        output += f"Source: {filename_metadata.get('source', 'N/A')}\n"
        output += f"Date: {filename_metadata.get('date', 'N/A')}\n"
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

