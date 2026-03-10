#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Analyze Gene Ontology functional category distribution across species
# Human: Eric Edsinger

"""
012_ai-python-analyze_functional_categories.py

Analyzes Gene Ontology (GO) functional category distribution across species
using the GO annotation database files produced by the InterProScan parser
(script 003).

For each species, this script:
1. Reads GO database files from database_go/ (if available)
2. Extracts GO terms from the Annotation_Identifier column
3. Classifies GO terms by namespace using the Annotation_Details column
   which contains "namespace:term_name" format (e.g., "biological_process:protein phosphorylation")
4. Counts per-namespace distribution: Biological Process (BP),
   Molecular Function (MF), Cellular Component (CC)
5. Reports top 10 most frequent GO terms per species
6. Calculates functional diversity: unique GO terms divided by total GO annotations

The species list is derived from the annotation statistics file produced by
script 008. This ensures we analyze exactly the species in the pipeline.

Standardized 7-column database TSV format expected in GO input files:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

The Annotation_Details column for GO files contains:
    "go_term_name|go_namespace" (e.g., "protein phosphorylation|biological_process")

Input:
    --statistics: Path to 8_ai-annotation_statistics.tsv from script 008
    --database-dir: Directory containing database_* directories
    --output-dir: Output directory

Output:
    12_ai-functional_categories.tsv
    12_ai-log-analyze_functional_categories.log

Usage:
    python3 012_ai-python-analyze_functional_categories.py \\
        --statistics 8_ai-annotation_statistics.tsv \\
        --database-dir . \\
        --output-dir .
"""

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '012_analyze_functional_categories' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '12_ai-log-analyze_functional_categories.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def extract_species_from_statistics( statistics_path: Path, logger: logging.Logger ) -> list:
    """
    Read the annotation statistics file and extract the list of species phylonames.
    Returns a sorted list of phyloname strings.
    """

    logger.info( f"Reading annotation statistics: {statistics_path}" )

    if not statistics_path.exists():
        logger.error( "CRITICAL ERROR: Annotation statistics file does not exist!" )
        logger.error( f"Expected path: {statistics_path}" )
        logger.error( "Run script 008 (annotation_statistics) first." )
        sys.exit( 1 )

    phylonames = []

    with open( statistics_path, 'r' ) as input_statistics:
        # Phyloname (phylogenetic name of species)	...additional columns...
        # Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	...
        for line in input_statistics:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 1:
                continue

            phyloname = parts[ 0 ]
            phylonames.append( phyloname )

    if len( phylonames ) == 0:
        logger.error( "CRITICAL ERROR: No species found in annotation statistics file!" )
        logger.error( f"File: {statistics_path}" )
        logger.error( "The statistics file may be empty or incorrectly formatted." )
        sys.exit( 1 )

    phylonames = sorted( phylonames )
    logger.info( f"  Found {len( phylonames )} species in statistics file" )

    return phylonames


def parse_go_annotations_for_species( go_file_path: Path, phyloname: str,
                                       logger: logging.Logger ) -> dict:
    """
    Read a GO database file for one species and extract GO term data.

    The Annotation_Details column contains "go_term_name|go_namespace" format.
    We split on the LAST pipe character to extract the namespace, since GO
    term names can also contain pipe characters.

    Returns a dictionary with:
        'biological_process_count': int
        'molecular_function_count': int
        'cellular_component_count': int
        'total_go_annotation_count': int
        'unique_go_terms': set of unique GO term identifiers
        'go_term_counts': Counter of GO term identifiers
    """

    biological_process_count = 0
    molecular_function_count = 0
    cellular_component_count = 0
    total_go_annotation_count = 0
    unique_go_terms = set()
    go_term_identifier___counts = Counter()

    with open( go_file_path, 'r' ) as input_go_file:
        # Phyloname (GIGANTIC phyloname for the species)	Sequence_Identifier (protein identifier from proteome)	Domain_Start ...	Domain_Stop ...	Database_Name (always go ...)	Annotation_Identifier (GO term identifier format GO:NNNNNNN)	Annotation_Details (GO term name and namespace separated by vertical bar)
        # Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	XP_027047018.1	27	283	go	GO:0005524	ATP binding|molecular_function
        for line in input_go_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            go_term_identifier = parts[ 5 ]
            annotation_details = parts[ 6 ]

            total_go_annotation_count += 1
            unique_go_terms.add( go_term_identifier )
            go_term_identifier___counts[ go_term_identifier ] += 1

            # Extract namespace from Annotation_Details
            # Format: "go_term_name|go_namespace"
            # Split on last pipe to handle term names that may contain pipes
            if '|' in annotation_details:
                last_pipe_position = annotation_details.rfind( '|' )
                go_namespace = annotation_details[ last_pipe_position + 1 : ].strip()
            else:
                # If no pipe, try to use the whole string as namespace
                # (handles edge case of malformed details)
                go_namespace = annotation_details.strip()

            # Classify by namespace
            if go_namespace == 'biological_process':
                biological_process_count += 1
            elif go_namespace == 'molecular_function':
                molecular_function_count += 1
            elif go_namespace == 'cellular_component':
                cellular_component_count += 1
            else:
                # Unknown namespace (could be "unknown" for unresolved GO terms)
                logger.debug( f"    Unknown GO namespace for {go_term_identifier}: {go_namespace}" )

    results = {
        'biological_process_count': biological_process_count,
        'molecular_function_count': molecular_function_count,
        'cellular_component_count': cellular_component_count,
        'total_go_annotation_count': total_go_annotation_count,
        'unique_go_terms': unique_go_terms,
        'go_term_identifier___counts': go_term_identifier___counts,
    }

    return results


def analyze_functional_categories( phylonames: list, database_directory: Path,
                                    output_directory: Path, logger: logging.Logger ) -> None:
    """
    For each species, analyze GO functional category distribution.
    Write results to the functional categories output TSV file.
    """

    # =========================================================================
    # Locate GO database directory
    # =========================================================================

    go_directory = database_directory / 'database_go'

    if not go_directory.exists() or not go_directory.is_dir():
        logger.error( "CRITICAL ERROR: GO database directory does not exist!" )
        logger.error( f"Expected directory: {go_directory}" )
        logger.error( "Run scripts 001-003 (InterProScan parsing) first." )
        logger.error( "InterProScan must have produced GO annotations for this directory to exist." )
        sys.exit( 1 )

    logger.info( f"  GO database directory: {go_directory}" )

    # =========================================================================
    # Prepare output file
    # =========================================================================

    output_file_path = output_directory / '12_ai-functional_categories.tsv'

    # =========================================================================
    # Write header
    # =========================================================================

    header = 'Phyloname (phylogenetic name of species)' + '\t'
    header += 'GO_Biological_Process_Count (count of biological process GO annotations)' + '\t'
    header += 'GO_Molecular_Function_Count (count of molecular function GO annotations)' + '\t'
    header += 'GO_Cellular_Component_Count (count of cellular component GO annotations)' + '\t'
    header += 'Total_GO_Annotations (total count of all GO annotations)' + '\t'
    header += 'Unique_GO_Terms (count of distinct GO term identifiers)' + '\t'
    header += 'Top_GO_Terms (comma delimited list of 10 most frequent GO identifiers)' + '\t'
    header += 'Functional_Diversity_Index (unique GO terms divided by total GO annotations)' + '\n'

    # =========================================================================
    # Process each species
    # =========================================================================

    species_processed_count = 0
    species_with_go_data_count = 0
    species_without_go_data_count = 0

    with open( output_file_path, 'w' ) as output_categories_file:
        output_categories_file.write( header )

        for phyloname in phylonames:
            species_processed_count += 1
            logger.info( f"  Processing species {species_processed_count}/{len( phylonames )}: {phyloname}" )

            # =================================================================
            # Read GO data for this species
            # =================================================================

            go_file_path = go_directory / f"gigantic_annotations-database_go-{phyloname}.tsv"

            if go_file_path.exists():
                species_with_go_data_count += 1

                go_results = parse_go_annotations_for_species(
                    go_file_path, phyloname, logger
                )

                biological_process_count = go_results[ 'biological_process_count' ]
                molecular_function_count = go_results[ 'molecular_function_count' ]
                cellular_component_count = go_results[ 'cellular_component_count' ]
                total_go_annotation_count = go_results[ 'total_go_annotation_count' ]
                unique_go_terms = go_results[ 'unique_go_terms' ]
                go_term_identifier___counts = go_results[ 'go_term_identifier___counts' ]

                unique_go_term_count = len( unique_go_terms )

                # Top 10 most frequent GO terms
                top_go_terms_with_counts = go_term_identifier___counts.most_common( 10 )
                top_go_terms = [ go_term_identifier for go_term_identifier, count in top_go_terms_with_counts ]
                top_go_terms_string = ','.join( top_go_terms ) if len( top_go_terms ) > 0 else 'NA'

                # Functional diversity index
                if total_go_annotation_count > 0:
                    functional_diversity_index = unique_go_term_count / total_go_annotation_count
                else:
                    functional_diversity_index = 0.0

            else:
                # No GO data for this species
                species_without_go_data_count += 1
                logger.warning( f"    WARNING: No GO file found for {phyloname}" )
                logger.warning( f"    Expected: {go_file_path}" )

                biological_process_count = 0
                molecular_function_count = 0
                cellular_component_count = 0
                total_go_annotation_count = 0
                unique_go_term_count = 0
                top_go_terms_string = 'NA'
                functional_diversity_index = 0.0

            # =================================================================
            # Write output row for this species
            # =================================================================

            output = phyloname + '\t'
            output += str( biological_process_count ) + '\t'
            output += str( molecular_function_count ) + '\t'
            output += str( cellular_component_count ) + '\t'
            output += str( total_go_annotation_count ) + '\t'
            output += str( unique_go_term_count ) + '\t'
            output += top_go_terms_string + '\t'
            output += f"{functional_diversity_index:.6f}" + '\n'
            output_categories_file.write( output )

            logger.debug( f"    BP: {biological_process_count}, MF: {molecular_function_count}, CC: {cellular_component_count}" )
            logger.debug( f"    Total: {total_go_annotation_count}, Unique: {unique_go_term_count}" )
            logger.debug( f"    Top terms: {top_go_terms_string}" )
            logger.debug( f"    Diversity index: {functional_diversity_index:.6f}" )

    # =========================================================================
    # Validate output
    # =========================================================================

    if species_processed_count == 0:
        logger.error( "CRITICAL ERROR: No species were processed!" )
        logger.error( "The species list from the statistics file was empty." )
        sys.exit( 1 )

    if species_with_go_data_count == 0:
        logger.error( "CRITICAL ERROR: No GO database files were found for any species!" )
        logger.error( f"Searched in: {go_directory}" )
        logger.error( "Run scripts 001-003 (InterProScan parsing) to generate GO database files." )
        sys.exit( 1 )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 012 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species processed: {species_processed_count}" )
    logger.info( f"  Species with GO data: {species_with_go_data_count}" )
    logger.info( f"  Species without GO data: {species_without_go_data_count}" )
    logger.info( f"  Output file: {output_file_path}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Analyze Gene Ontology functional category distribution across species'
    )

    parser.add_argument(
        '--statistics',
        type = str,
        required = True,
        help = 'Path to 8_ai-annotation_statistics.tsv from script 008'
    )

    parser.add_argument(
        '--database-dir',
        type = str,
        required = True,
        help = 'Directory containing database_* directories'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Output directory for results (default: current directory)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    statistics_path = Path( arguments.statistics )
    database_directory = Path( arguments.database_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 012: Analyze Functional Categories" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load species list from statistics file
    # =========================================================================

    phylonames = extract_species_from_statistics( statistics_path, logger )

    # =========================================================================
    # Analyze functional categories
    # =========================================================================

    analyze_functional_categories( phylonames, database_directory, output_directory, logger )


if __name__ == '__main__':
    main()
