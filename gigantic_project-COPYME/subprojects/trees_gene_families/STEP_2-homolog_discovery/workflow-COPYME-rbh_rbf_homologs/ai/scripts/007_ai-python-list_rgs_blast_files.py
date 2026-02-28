#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 007: List RGS BLAST Files
# AI: Claude Code | Sonnet 4.5 | 2025 November 08 17:30 | Purpose: List RGS genome BLAST reports and model organism fastas
# Human: Eric Edsinger

"""
List RGS Genome BLAST Reports and Model Organism Database Fastas

This script identifies RGS genome BLAST reports from script 006 and creates lists
of files needed for reciprocal BLAST analysis. It focuses on key model organisms
(human, fly, worm) that will be used for reciprocal best hit analysis.

Input Files (from script 006):
    - output/6-output/6*genome*.blastp - RGS genome BLAST reports

Output Files:
    - output/7-output/7_ai-list-rgs-blast-reports.txt - List of RGS BLAST report paths
    - output/7-output/7_ai-list-model-organism-fastas.txt - Model organism database FASTA paths

Usage:
    python3 007_ai-python-list_rgs_blast_files.py \\
        --output-dir output \\
        --blast-databases-dir ../../pipelines/database/species67-T1-blastp \\
        --model-species human fly worm
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List
from datetime import datetime


def setup_logging() -> logging.Logger:
    """Configure logging with timestamps and levels."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger( __name__ )


def find_rgs_blast_reports( output_directory: Path, logger: logging.Logger ) -> List[Path]:
    """
    Find all RGS genome BLAST reports from script 006.
    
    Args:
        output_directory: Directory containing BLAST reports
        logger: Logger instance
        
    Returns:
        List of paths to RGS BLAST report files
    """
    logger.info( "Searching for RGS genome BLAST reports..." )
    
    # Find all files matching pattern: 6_ai*genome*.blastp in 6-output subdirectory
    script_6_output_dir = output_directory / "6-output"
    blast_reports = sorted( script_6_output_dir.glob( '6_ai*genome*.blastp' ) ) if script_6_output_dir.exists() else []
    
    logger.info( f"Found {len( blast_reports )} RGS genome BLAST reports" )
    
    for report in blast_reports:
        logger.info( f"  - {report.name}" )
    
    return blast_reports


def find_model_organism_fastas(
    blast_databases_directory: Path,
    model_species: List[str],
    logger: logging.Logger
) -> List[Path]:
    """
    Find database FASTA files for specified model organisms.
    
    Args:
        blast_databases_directory: Directory containing BLAST database files
        model_species: List of model organism names to search for
        logger: Logger instance
        
    Returns:
        List of paths to model organism FASTA files
    """
    logger.info( "Searching for RBH species database fastas..." )
    logger.info( f"RBH species: {', '.join( model_species )}" )
    
    model_fastas = []
    
    # Map common names to scientific names
    species_mappings = {
        'human': 'Homo_sapiens',
        'fly': 'Drosophila_melanogaster',
        'worm': 'Caenorhabditis_elegans',
        'mouse': 'Mus_musculus',
        'zebrafish': 'Danio_rerio'
    }
    
    for species in model_species:
        # Get scientific name
        scientific_name = species_mappings.get( species.lower(), species )
        
        # Find matching FASTA files
        pattern = f"*{scientific_name}*.aa"
        matching_files = list( blast_databases_directory.glob( pattern ) )
        
        if matching_files:
            # Take first match (there should only be one)
            fasta_file = matching_files[ 0 ]
            model_fastas.append( fasta_file )
            logger.info( f"  - {species}: {fasta_file.name}" )
        else:
            logger.warning( f"  - {species}: No matching FASTA found for pattern {pattern}" )
    
    return model_fastas


def write_file_list( output_file: Path, file_paths: List[Path], logger: logging.Logger ) -> None:
    """
    Write list of file paths to output file.
    
    Args:
        output_file: Output file path
        file_paths: List of file paths to write
        logger: Logger instance
    """
    with open( output_file, 'w' ) as output_list:
        for file_path in file_paths:
            output_list.write( f"{file_path}\n" )
    
    logger.info( f"Wrote {len( file_paths )} paths to {output_file}" )


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='List RGS genome BLAST reports and model organism database fastas'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='Output directory containing BLAST reports'
    )
    
    parser.add_argument(
        '--blast-databases-dir',
        type=str,
        required=True,
        help='Directory containing BLAST database FASTA files'
    )
    
    parser.add_argument(
        '--rbh-species',
        type=str,
        required=True,
        help='Space-separated list of RBH species names (e.g., "human fly worm")'
    )
    
    parser.add_argument(
        '--output-blast-reports',
        type=str,
        default='output/7-output/7_ai-list-rgs-blast-reports.txt',
        help='Output file for BLAST report paths'
    )
    
    parser.add_argument(
        '--output-model-fastas',
        type=str,
        default='output/7-output/7_ai-list-model-organism-fastas.txt',
        help='Output file for model organism FASTA paths'
    )
    
    arguments = parser.parse_args()
    logger = setup_logging()
    
    # Log script start
    logger.info( "=" * 80 )
    logger.info( "List RGS Genome BLAST Reports and Model Organism Fastas" )
    logger.info( "=" * 80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    
    # Convert paths
    output_directory = Path( arguments.output_dir )
    blast_databases_directory = Path( arguments.blast_databases_dir )
    output_blast_reports_file = Path( arguments.output_blast_reports )
    output_model_fastas_file = Path( arguments.output_model_fastas )
    
    # Create script output directory
    script_output_dir = output_blast_reports_file.parent
    script_output_dir.mkdir( parents=True, exist_ok=True )
    
    # Validate directories
    if not output_directory.exists():
        logger.error( f"Output directory not found: {output_directory}" )
        sys.exit( 1 )
    
    if not blast_databases_directory.exists():
        logger.error( f"BLAST databases directory not found: {blast_databases_directory}" )
        sys.exit( 1 )
    
    # Parse RBH species (split space-separated string)
    rbh_species_list = arguments.rbh_species.split()
    
    # Find RGS BLAST reports
    blast_reports = find_rgs_blast_reports( output_directory, logger )
    
    if not blast_reports:
        logger.error( "CRITICAL ERROR: No RGS genome BLAST reports found!" )
        logger.error( "RGS genome BLAST (script 006) must complete before this step." )
        logger.error( f"Expected BLAST reports in: {output_directory}" )
        logger.error( "Check that script 006 generated BLAST reports successfully." )
        sys.exit( 1 )  # FAIL - cannot proceed without BLAST reports
    
    # Find RBH species fastas
    model_fastas = find_model_organism_fastas(
        blast_databases_directory,
        rbh_species_list,
        logger
    )
    
    if not model_fastas:
        logger.error( "No model organism fastas found!" )
        sys.exit( 1 )
    
    # Write output files
    logger.info( "\nWriting output files..." )
    write_file_list( output_blast_reports_file, blast_reports, logger )
    write_file_list( output_model_fastas_file, model_fastas, logger )
    
    # Summary
    logger.info( "\n" + "=" * 80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "=" * 80 )
    logger.info( f"RGS BLAST reports listed: {len( blast_reports )}" )
    logger.info( f"Model organism fastas listed: {len( model_fastas )}" )
    logger.info( f"Output files:" )
    logger.info( f"  - {output_blast_reports_file}" )
    logger.info( f"  - {output_model_fastas_file}" )
    logger.info( f"\nScript completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == '__main__':
    main()

