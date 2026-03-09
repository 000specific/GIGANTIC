#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 008: Map RGS to Reference Genomes
# AI: Claude Code | Sonnet 4.5 | 2025 November 09 11:30 | Purpose: Map RGS sequences to reference genome identifiers for reciprocal BLAST
# Human: Eric Edsinger

"""
Map RGS Sequences to Reference Genome Identifiers

This script prepares data for reciprocal BLAST by:
1. Reading RGS sequences with GIGANTIC_1 standardized headers
2. Reading BLAST reports from RGS vs RGS genome searches
3. Mapping RGS identifiers to reference genome identifiers
4. Creating updated RGS fasta with genome identifiers
5. Listing model organism fastas with RGS headers

RGS header format (GIGANTIC_1):
    >rgsN-species_short_name-source-identifier
    Where N = number of sequences in file

This script extracts the species_short_name and uses it to match against
genome databases for reciprocal BLAST setup.
"""

import argparse
import logging
import sys
from collections import defaultdict
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


def create_truncated_headers_map(
    headers: List[str],
    max_length: int = 50,
    truncate_to: int = 45,
    logger: logging.Logger = None
) -> Dict[str, str]:
    """
    Create mapping of original headers to truncated headers (if needed).
    
    Only truncates headers > max_length. Truncates to truncate_to chars and
    adds a counter suffix (_001, _002, etc.) to ensure uniqueness.
    
    Args:
        headers: List of original headers
        max_length: Maximum allowed header length (BLAST limit: 50)
        truncate_to: Length to truncate to before adding counter (default: 45)
        logger: Logger instance
        
    Returns:
        Dictionary mapping original_header → truncated_header
    """
    original_to_truncated = {}
    truncated_seen = {}  # Track truncated base → counter
    
    for original_header in headers:
        if len( original_header ) <= max_length:
            # No truncation needed
            original_to_truncated[ original_header ] = original_header
        else:
            # Truncate to 45 chars
            truncated_base = original_header[:truncate_to]
            
            # Check if this truncated base has been seen before
            if truncated_base not in truncated_seen:
                truncated_seen[ truncated_base ] = 0
            
            # Increment counter for this base
            truncated_seen[ truncated_base ] += 1
            counter = truncated_seen[ truncated_base ]
            
            # Create unique truncated header: base + _NNN
            truncated_header = f"{truncated_base}_{counter:03d}"
            
            # Verify we're still under the limit
            if len( truncated_header ) > max_length:
                if logger:
                    logger.error( f"Truncated header still too long: {truncated_header} ({len(truncated_header)} chars)" )
                # Emergency truncation - reduce base further
                emergency_base = original_header[:( max_length - 4 )]  # Leave room for _NNN
                truncated_header = f"{emergency_base}_{counter:03d}"
            
            original_to_truncated[ original_header ] = truncated_header
    
    if logger:
        num_truncated = sum( 1 for orig, trunc in original_to_truncated.items() if orig != trunc )
        logger.info( f"Headers requiring truncation: {num_truncated} / {len(headers)}" )
    
    return original_to_truncated


def parse_rgs_header( header: str ) -> Tuple[bool, str, str, str]:
    """
    Parse GIGANTIC_1 standardized RGS header.
    
    Expected format: >rgsN-species_short_name-source-identifier
    Where N = number of sequences in file
    
    Args:
        header: RGS FASTA header (without >)
        
    Returns:
        Tuple of (is_valid, species_short_name, source, full_header)
    """
    parts = header.split( '-' )
    
    if len( parts ) < 4:
        return False, '', '', header
    
    # First part must be rgsN (e.g., rgs36)
    rgs_part = parts[0]
    if not rgs_part.startswith( 'rgs' ) or len( rgs_part ) <= 3:
        return False, '', '', header
    
    # Validate digits after 'rgs'
    count_str = rgs_part[3:]
    if not count_str.isdigit():
        return False, '', '', header
    
    species_short_name = parts[1]
    source = parts[2]
    
    return True, species_short_name, source, header


def read_rgs_sequences( rgs_fasta: Path, logger: logging.Logger = None ) -> Dict[str, Tuple[str, str, str]]:
    """
    Read RGS sequences and parse headers.
    
    Args:
        rgs_fasta: Path to RGS FASTA file
        logger: Logger instance
        
    Returns:
        Dictionary mapping full_header -> (species_short_name, source, sequence)
    """
    rgs_sequences = {}
    current_header = None
    current_sequence_parts = []
    
    with open( rgs_fasta, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()
            
            if line.startswith( '>' ):
                # Save previous sequence
                if current_header:
                    sequence = ''.join( current_sequence_parts )
                    is_valid, species, source, full_header = parse_rgs_header( current_header )
                    
                    if is_valid:
                        rgs_sequences[full_header] = (species, source, sequence)
                    else:
                        if logger:
                            logger.warning( f"Invalid RGS header format: {current_header}" )
                
                # Start new sequence
                current_header = line[1:].strip()
                current_sequence_parts = []
            else:
                current_sequence_parts.append( line )
        
        # Save last sequence
        if current_header:
            sequence = ''.join( current_sequence_parts )
            is_valid, species, source, full_header = parse_rgs_header( current_header )
            
            if is_valid:
                rgs_sequences[full_header] = (species, source, sequence)
            else:
                if logger:
                    logger.warning( f"Invalid RGS header format: {current_header}" )
    
    if logger:
        logger.info( f"Read {len(rgs_sequences)} sequences" )
    
    return rgs_sequences


def read_file_list( list_file: Path, logger: logging.Logger = None ) -> List[Path]:
    """
    Read a list of file paths from a text file.
    
    Args:
        list_file: Path to file containing list of paths
        logger: Logger instance
        
    Returns:
        List of Path objects
    """
    paths = []
    
    with open( list_file, 'r' ) as input_list:
        for line in input_list:
            line = line.strip()
            if line:
                paths.append( Path( line ) )
    
    if logger:
        logger.info( f"Read {len(paths)} file paths" )
    
    return paths


def create_rgs_genome_mapping(
    blast_reports: List[Path],
    rgs_sequences: Dict[str, Tuple[str, str, str]],
    model_species: List[str],
    logger: logging.Logger = None
) -> Dict[str, str]:
    """
    Create mapping from genome sequence IDs to RGS headers based on BLAST top hits.
    
    This reads BLAST reports (RGS vs RGS genomes) and creates a mapping:
    genome_sequence_id → rgs_header
    
    Only keeps one RGS per genome sequence (first encountered).
    
    Args:
        blast_reports: List of BLAST report files (RGS vs RGS genomes)
        rgs_sequences: Dictionary of RGS sequences with parsed headers
        model_species: List of model species names to filter by
        logger: Logger instance
        
    Returns:
        Dictionary mapping genome_sequence_id -> rgs_header
    """
    genome_to_rgs = {}  # Changed: genome_id → rgs_header (not rgs → genome!)
    rgs_seen = set()  # Track which RGS sequences already have a mapping
    genome_ids_seen = set()  # Track which genome sequences already have a mapping
    
    for blast_report in blast_reports:
        if not blast_report.exists():
            if logger:
                logger.warning( f"BLAST report not found: {blast_report}" )
            continue
        
        # Determine which model species this report is for
        report_model_species = None
        for species in model_species:
            if species in str( blast_report ):
                report_model_species = species
                break
        
        if not report_model_species:
            if logger:
                logger.warning( f"Could not identify model species for: {blast_report}" )
            continue
        
        # Parse BLAST report (outfmt 6)
        with open( blast_report, 'r' ) as input_file:
            for line in input_file:
                line = line.strip()
                if not line or line.startswith( '#' ):
                    continue
                
                parts = line.split( '\t' )
                if len( parts ) < 2:
                    continue
                
                rgs_query = parts[0]  # RGS sequence ID (query)
                genome_hit = parts[1]  # Genome sequence ID (subject/hit)
                
                # Extract species from RGS header (second field: rgsN-species-source-id)
                rgs_parts = rgs_query.split( '-' )
                if len( rgs_parts ) >= 2:
                    rgs_species = rgs_parts[1]
                    
                    # Check if this RGS matches the report's model species
                    if rgs_species == report_model_species:
                        # Only add if we haven't seen this RGS or genome ID yet
                        if rgs_query not in rgs_seen and genome_hit not in genome_ids_seen:
                            genome_to_rgs[genome_hit] = rgs_query
                            rgs_seen.add( rgs_query )
                            genome_ids_seen.add( genome_hit )
    
    if logger:
        logger.info( f"\nTotal genome→RGS mappings: {len(genome_to_rgs)}" )
        
        # Count by model species
        species_counts = defaultdict( int )
        for genome_id in genome_to_rgs.keys():
            for species in model_species:
                if species in genome_id.lower() or species in genome_id:
                    species_counts[species] += 1
                    break
        
        logger.info( "\nMappings per model species:" )
        for species in sorted( species_counts.keys() ):
            logger.info( f"  {species}: {species_counts[species]} mappings" )
    
    return genome_to_rgs


def write_rgs_with_genome_ids(
    rgs_sequences: Dict[str, Tuple[str, str, str]],
    rgs_to_genome: Dict[str, str],
    output_fasta: Path,
    header_truncation_map: Dict[str, str],
    logger: logging.Logger = None
):
    """
    Write RGS fasta with genome identifier information.
    
    The headers already contain species info in standardized format.
    This just writes them out for reciprocal BLAST.
    
    Args:
        rgs_sequences: Dictionary of RGS sequences
        rgs_to_genome: Mapping of RGS to genomes
        output_fasta: Path to output FASTA file
        header_truncation_map: Dictionary mapping original to truncated headers
        logger: Logger instance
    """
    with open( output_fasta, 'w' ) as output_file:
        for rgs_header in sorted( rgs_sequences.keys() ):
            species_short_name, source, sequence = rgs_sequences[rgs_header]
            
            # Apply truncation map
            truncated_header = header_truncation_map.get( rgs_header, rgs_header )
            output = f">{truncated_header}\n"
            output_file.write( output )
            
            # Write sequence (wrap at 80 characters)
            for i in range( 0, len( sequence ), 80 ):
                output = sequence[i:i+80] + '\n'
                output_file.write( output )
    
    if logger:
        logger.info( f"Wrote RGS sequences to: {output_fasta}" )


def create_model_organism_list(
    model_fastas: List[Path],
    output_list: Path,
    logger: logging.Logger = None
):
    """
    Create list of model organism fasta files with RGS headers.
    
    Args:
        model_fastas: List of model organism fasta files
        output_list: Path to output list file
        logger: Logger instance
    """
    with open( output_list, 'w' ) as output_file:
        for fasta_path in model_fastas:
            output = str( fasta_path ) + '\n'
            output_file.write( output )
    
    if logger:
        logger.info( f"Wrote model organism list to: {output_list}" )
        logger.info( f"  Model organisms: {len(model_fastas)}" )


def write_header_truncation_map(
    original_to_truncated: Dict[str, str],
    output_file: Path,
    logger: logging.Logger = None
):
    """
    Write header truncation mapping file for reference.
    
    Format: original_header\ttruncated_header
    
    Args:
        original_to_truncated: Dictionary mapping original to truncated headers
        output_file: Path to output mapping file
        logger: Logger instance
    """
    with open( output_file, 'w' ) as output_map:
        # Write header row
        output_map.write( "original_header\ttruncated_header\n" )
        
        # Only write entries where truncation occurred
        for original, truncated in sorted( original_to_truncated.items() ):
            if original != truncated:
                output = f"{original}\t{truncated}\n"
                output_map.write( output )
    
    if logger:
        num_truncated = sum( 1 for orig, trunc in original_to_truncated.items() if orig != trunc )
        logger.info( f"Wrote header truncation map to: {output_file}" )
        logger.info( f"  Truncated headers: {num_truncated}" )


def write_mapping_file(
    genome_to_rgs: Dict[str, str],
    output_file: Path,
    header_truncation_map: Dict[str, str],
    logger: logging.Logger = None
):
    """
    Write genome to RGS mapping file.
    
    Format: genome_sequence_id\ttruncated_rgs_header\toriginal_full_rgs_header
    
    Three columns allow script 009 to:
    - Use truncated header for BLAST database compatibility
    - Use original full header to look up sequences in original RGS file
    
    Args:
        genome_to_rgs: Dictionary mapping genome sequence IDs to RGS headers (original)
        output_file: Path to output mapping file
        header_truncation_map: Dictionary mapping original to truncated headers
        logger: Logger instance
    """
    with open( output_file, 'w' ) as output_map:
        # Write mappings (no header row - matches GIGANTIC_0 format)
        for genome_id in sorted( genome_to_rgs.keys() ):
            original_rgs_header = genome_to_rgs[genome_id]
            # Apply truncation map
            truncated_header = header_truncation_map.get( original_rgs_header, original_rgs_header )
            # Write three columns: genome_id, truncated_header, original_full_header
            output = f"{genome_id}\t{truncated_header}\t{original_rgs_header}\n"
            output_map.write( output )
    
    if logger:
        logger.info( f"Wrote genome→RGS mapping to: {output_file}" )
        logger.info( f"  Format: genome_id TAB truncated_rgs_header TAB original_full_rgs_header" )


def main():
    """
    Main execution function.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Map RGS sequences to reference genome identifiers for reciprocal BLAST'
    )
    
    parser.add_argument(
        '--blast-reports-list',
        type=Path,
        required=True,
        help='Path to file listing RGS genome BLAST report paths'
    )
    
    parser.add_argument(
        '--model-fastas-list',
        type=Path,
        required=True,
        help='Path to file listing model organism FASTA paths'
    )
    
    parser.add_argument(
        '--rgs-fasta',
        type=Path,
        required=True,
        help='Path to RGS FASTA file'
    )
    
    parser.add_argument(
        '--output-mapping',
        type=Path,
        required=True,
        help='Path to output RGS→genome mapping file'
    )
    
    parser.add_argument(
        '--output-rgs-fasta',
        type=Path,
        required=True,
        help='Path to output RGS FASTA with genome identifiers'
    )
    
    parser.add_argument(
        '--output-fasta-list',
        type=Path,
        required=True,
        help='Path to output list of model organism fastas'
    )
    
    parser.add_argument(
        '--rbh-species',
        type=str,
        required=True,
        help='Space-separated list of RBH species names (e.g., "human fly worm")'
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        default=None,
        help='Path to log file (optional)'
    )
    
    args = parser.parse_args()
    
    # Parse RBH species
    model_species_list = args.rbh_species.split()
    
    # Setup logging
    logger = setup_logging( args.log_file )
    
    logger.info( "=" * 80 )
    logger.info( "Map RGS Sequences to Reference Genome Identifiers" )
    logger.info( "=" * 80 )
    logger.info( f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" )
    logger.info( "" )
    logger.info( f"RGS FASTA: {args.rgs_fasta}" )
    logger.info( f"BLAST reports list: {args.blast_reports_list}" )
    logger.info( f"Model fastas list: {args.model_fastas_list}" )
    logger.info( f"RBH species: {', '.join(model_species_list)}" )
    
    # Create script output directory
    script_output_dir = args.output_mapping.parent
    script_output_dir.mkdir( parents=True, exist_ok=True )
    
    # Read RGS sequences
    logger.info( "\nReading RGS sequences..." )
    rgs_sequences = read_rgs_sequences( args.rgs_fasta, logger )
    
    if not rgs_sequences:
        logger.error( "No valid RGS sequences found!" )
        sys.exit( 1 )
    
    # Read file lists
    logger.info( "\nReading file lists..." )
    blast_reports = read_file_list( args.blast_reports_list, logger )
    model_fastas = read_file_list( args.model_fastas_list, logger )
    
    # Create RGS→genome mappings from BLAST reports
    logger.info( "\nCreating RGS→genome mappings from BLAST reports..." )
    rgs_to_genome = create_rgs_genome_mapping(
        blast_reports,
        rgs_sequences,
        model_species_list,
        logger
    )
    
    if not rgs_to_genome:
        logger.error( "No RGS→genome mappings created!" )
        logger.error( "Cannot proceed without mappings." )
        sys.exit( 1 )
    
    # Create header truncation map
    logger.info( "\nCreating header truncation map..." )
    all_rgs_headers = list( rgs_sequences.keys() )
    header_truncation_map = create_truncated_headers_map( all_rgs_headers, logger=logger )
    
    # Write outputs
    logger.info( "\nWriting output files..." )
    
    write_mapping_file( rgs_to_genome, args.output_mapping, header_truncation_map, logger )
    write_rgs_with_genome_ids( rgs_sequences, rgs_to_genome, args.output_rgs_fasta, header_truncation_map, logger )
    create_model_organism_list( model_fastas, args.output_fasta_list, logger )
    
    # Write header truncation mapping (for reference)
    truncation_map_file = Path( 'output/8-output/8_ai-header_truncation_map.txt' )
    write_header_truncation_map( header_truncation_map, truncation_map_file, logger )
    
    # Summary
    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "=" * 80 )
    logger.info( f"RGS sequences processed: {len(rgs_sequences)}" )
    logger.info( f"RGS→genome mappings: {len(rgs_to_genome)}" )
    logger.info( f"Model organism fastas: {len(model_fastas)}" )
    logger.info( "" )
    logger.info( "Output files:" )
    logger.info( f"  Mapping: {args.output_mapping}" )
    logger.info( f"  RGS FASTA: {args.output_rgs_fasta}" )
    logger.info( f"  Model list: {args.output_fasta_list}" )
    logger.info( f"  Header truncation map: {truncation_map_file}" )
    logger.info( "" )
    logger.info( f"Script completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" )


if __name__ == "__main__":
    main()
