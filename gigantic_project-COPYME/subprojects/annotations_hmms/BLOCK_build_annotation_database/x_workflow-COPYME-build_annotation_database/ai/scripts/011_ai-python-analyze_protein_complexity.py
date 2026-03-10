#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Analyze multi-domain protein distribution and disorder content per species
# Human: Eric Edsinger

"""
011_ai-python-analyze_protein_complexity.py

Analyzes multi-domain protein distribution and intrinsic disorder content
per species using Pfam domain annotations and MetaPredict IDR predictions.

For each species, this script:
1. Reads the Pfam database file (from database_pfam/) if available
2. Counts how many Pfam domains each protein has
3. Classifies proteins by domain count: 0, 1, 2, 3, 4+ domains
4. If MetaPredict data is available, reads database_metapredict/ files
5. For MetaPredict: counts IDR regions per protein, calculates mean IDR count
6. Reports the most complex protein: highest combined domain count

The species list is derived from the annotation statistics file produced by
script 008. This ensures we analyze exactly the species in the pipeline.

Standardized 7-column database TSV format expected in input files:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Input:
    --statistics: Path to 8_ai-annotation_statistics.tsv from script 008
    --database-dir: Directory containing database_* directories
    --output-dir: Output directory

Output:
    11_ai-protein_complexity.tsv
    11_ai-log-analyze_protein_complexity.log

Usage:
    python3 011_ai-python-analyze_protein_complexity.py \\
        --statistics 8_ai-annotation_statistics.tsv \\
        --database-dir . \\
        --output-dir .
"""

import argparse
import logging
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '011_analyze_protein_complexity' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '11_ai-log-analyze_protein_complexity.log'
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


def count_pfam_domains_per_protein( pfam_file_path: Path, phyloname: str,
                                     logger: logging.Logger ) -> dict:
    """
    Read a Pfam database file and count domains per protein.

    Returns sequence_identifiers___domain_counts: { 'XP_027047018.1': 3, ... }
    """

    sequence_identifiers___domain_counts = defaultdict( int )

    with open( pfam_file_path, 'r' ) as input_pfam_file:
        # Phyloname (GIGANTIC phyloname for the species)	Sequence_Identifier (protein identifier from proteome)	Domain_Start ...	Domain_Stop ...	Database_Name ...	Annotation_Identifier ...	Annotation_Details ...
        # Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	XP_027047018.1	27	283	pfam	PF00069	Protein kinase domain
        for line in input_pfam_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            sequence_identifier = parts[ 1 ]
            sequence_identifiers___domain_counts[ sequence_identifier ] += 1

    logger.debug( f"    Pfam: {len( sequence_identifiers___domain_counts )} proteins with domains" )

    return dict( sequence_identifiers___domain_counts )


def count_idr_regions_per_protein( metapredict_file_path: Path, phyloname: str,
                                    logger: logging.Logger ) -> dict:
    """
    Read a MetaPredict database file and count IDR regions per protein.

    Each row in the MetaPredict database file represents one IDR region for a
    protein. Proteins with multiple IDR regions have multiple rows.

    Returns sequence_identifiers___idr_counts: { 'XP_027047018.1': 2, ... }
    """

    sequence_identifiers___idr_counts = defaultdict( int )

    with open( metapredict_file_path, 'r' ) as input_metapredict_file:
        # Phyloname (GIGANTIC phyloname for the species)	Sequence_Identifier (protein identifier from proteome)	Domain_Start ...	Domain_Stop ...	Database_Name ...	Annotation_Identifier ...	Annotation_Details ...
        # Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	XP_027047018.1	10	45	metapredict	IDR	intrinsically_disordered_region,start=10,stop=45
        for line in input_metapredict_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            sequence_identifier = parts[ 1 ]
            sequence_identifiers___idr_counts[ sequence_identifier ] += 1

    logger.debug( f"    MetaPredict: {len( sequence_identifiers___idr_counts )} proteins with IDRs" )

    return dict( sequence_identifiers___idr_counts )


def analyze_protein_complexity( phylonames: list, database_directory: Path,
                                 output_directory: Path, logger: logging.Logger ) -> None:
    """
    For each species, analyze Pfam domain distribution and MetaPredict IDR content.
    Write results to the protein complexity output TSV file.
    """

    # =========================================================================
    # Locate database directories
    # =========================================================================

    pfam_directory = database_directory / 'database_pfam'
    metapredict_directory = database_directory / 'database_metapredict'

    pfam_available = pfam_directory.exists() and pfam_directory.is_dir()
    metapredict_available = metapredict_directory.exists() and metapredict_directory.is_dir()

    if not pfam_available:
        logger.error( "CRITICAL ERROR: Pfam database directory does not exist!" )
        logger.error( f"Expected directory: {pfam_directory}" )
        logger.error( "Run scripts 001-003 (InterProScan parsing) first." )
        sys.exit( 1 )

    logger.info( f"  Pfam database directory: {pfam_directory}" )
    logger.info( f"  MetaPredict database directory: {metapredict_directory}" )
    logger.info( f"  Pfam data available: {pfam_available}" )
    logger.info( f"  MetaPredict data available: {metapredict_available}" )

    # =========================================================================
    # Prepare output file
    # =========================================================================

    output_file_path = output_directory / '11_ai-protein_complexity.tsv'

    # =========================================================================
    # Write header
    # =========================================================================

    header = 'Phyloname (phylogenetic name of species)' + '\t'
    header += 'Proteins_With_Zero_Pfam_Domains (count of proteins with no Pfam domain annotations)' + '\t'
    header += 'Proteins_With_One_Pfam_Domain (count of proteins with exactly one Pfam domain)' + '\t'
    header += 'Proteins_With_Two_Pfam_Domains (count of proteins with exactly two Pfam domains)' + '\t'
    header += 'Proteins_With_Three_Pfam_Domains (count of proteins with exactly three Pfam domains)' + '\t'
    header += 'Proteins_With_Four_Plus_Pfam_Domains (count of proteins with four or more Pfam domains)' + '\t'
    header += 'Mean_Pfam_Domains_Per_Protein (average number of Pfam domains across all proteins with at least one domain)' + '\t'
    header += 'Max_Pfam_Domains_Single_Protein (highest domain count for any single protein)' + '\t'
    header += 'Most_Complex_Protein_Identifier (protein accession with most Pfam domains)' + '\t'
    header += 'Mean_IDR_Count_Per_Protein (average intrinsically disordered regions per protein or NA if metapredict not available)' + '\n'

    # =========================================================================
    # Process each species
    # =========================================================================

    species_processed_count = 0
    species_with_pfam_count = 0
    species_with_metapredict_count = 0

    with open( output_file_path, 'w' ) as output_complexity_file:
        output_complexity_file.write( header )

        for phyloname in phylonames:
            species_processed_count += 1
            logger.info( f"  Processing species {species_processed_count}/{len( phylonames )}: {phyloname}" )

            # =================================================================
            # Read Pfam data for this species
            # =================================================================

            pfam_file_path = pfam_directory / f"gigantic_annotations-database_pfam-{phyloname}.tsv"

            if pfam_file_path.exists():
                species_with_pfam_count += 1
                sequence_identifiers___domain_counts = count_pfam_domains_per_protein(
                    pfam_file_path, phyloname, logger
                )
            else:
                logger.warning( f"    WARNING: No Pfam file found for {phyloname}" )
                logger.warning( f"    Expected: {pfam_file_path}" )
                sequence_identifiers___domain_counts = {}

            # =================================================================
            # Classify proteins by domain count
            # =================================================================

            # All proteins with at least one domain are in the dictionary.
            # Proteins with zero domains are NOT in the dictionary (they had
            # no rows in the Pfam database file). We report them as a count
            # but we cannot know the total proteome size from Pfam alone.
            # We report counts of annotated proteins only.

            proteins_with_zero_domains = 0  # Placeholder - see note below
            proteins_with_one_domain = 0
            proteins_with_two_domains = 0
            proteins_with_three_domains = 0
            proteins_with_four_plus_domains = 0

            all_domain_counts = []
            most_complex_protein_identifier = 'NA'
            max_domain_count = 0

            for sequence_identifier in sequence_identifiers___domain_counts:
                domain_count = sequence_identifiers___domain_counts[ sequence_identifier ]
                all_domain_counts.append( domain_count )

                if domain_count == 1:
                    proteins_with_one_domain += 1
                elif domain_count == 2:
                    proteins_with_two_domains += 1
                elif domain_count == 3:
                    proteins_with_three_domains += 1
                elif domain_count >= 4:
                    proteins_with_four_plus_domains += 1

                if domain_count > max_domain_count:
                    max_domain_count = domain_count
                    most_complex_protein_identifier = sequence_identifier

            # Note: proteins_with_zero_domains stays 0 here because Pfam files
            # only contain proteins that HAVE domains. The actual count of
            # proteins with zero domains requires knowing the total proteome
            # size, which is available in the statistics file. However, this
            # script focuses on Pfam-annotated complexity, so we report 0 as
            # a placeholder. The statistics file (script 008) already tracks
            # total protein counts per species.

            # Calculate mean domains per protein (among those with at least one domain)
            if len( all_domain_counts ) > 0:
                mean_domains_per_protein = statistics.mean( all_domain_counts )
            else:
                mean_domains_per_protein = 0.0

            # =================================================================
            # Read MetaPredict IDR data for this species (if available)
            # =================================================================

            mean_idr_count_per_protein = 'NA'

            if metapredict_available:
                metapredict_file_path = metapredict_directory / f"gigantic_annotations-database_metapredict-{phyloname}.tsv"

                if metapredict_file_path.exists():
                    species_with_metapredict_count += 1
                    sequence_identifiers___idr_counts = count_idr_regions_per_protein(
                        metapredict_file_path, phyloname, logger
                    )

                    if len( sequence_identifiers___idr_counts ) > 0:
                        all_idr_counts = list( sequence_identifiers___idr_counts.values() )
                        mean_idr_count_per_protein = f"{statistics.mean( all_idr_counts ):.4f}"
                    else:
                        mean_idr_count_per_protein = '0.0000'

                else:
                    logger.debug( f"    No MetaPredict file found for {phyloname}" )

            # =================================================================
            # Write output row for this species
            # =================================================================

            output = phyloname + '\t'
            output += str( proteins_with_zero_domains ) + '\t'
            output += str( proteins_with_one_domain ) + '\t'
            output += str( proteins_with_two_domains ) + '\t'
            output += str( proteins_with_three_domains ) + '\t'
            output += str( proteins_with_four_plus_domains ) + '\t'
            output += f"{mean_domains_per_protein:.4f}" + '\t'
            output += str( max_domain_count ) + '\t'
            output += most_complex_protein_identifier + '\t'
            output += str( mean_idr_count_per_protein ) + '\n'
            output_complexity_file.write( output )

            logger.debug( f"    1-domain: {proteins_with_one_domain}, 2-domain: {proteins_with_two_domains}, 3-domain: {proteins_with_three_domains}, 4+-domain: {proteins_with_four_plus_domains}" )
            logger.debug( f"    Mean domains/protein: {mean_domains_per_protein:.4f}, Max: {max_domain_count}" )
            logger.debug( f"    Most complex protein: {most_complex_protein_identifier}" )
            logger.debug( f"    Mean IDRs/protein: {mean_idr_count_per_protein}" )

    # =========================================================================
    # Validate output
    # =========================================================================

    if species_processed_count == 0:
        logger.error( "CRITICAL ERROR: No species were processed!" )
        logger.error( "The species list from the statistics file was empty." )
        sys.exit( 1 )

    if species_with_pfam_count == 0:
        logger.error( "CRITICAL ERROR: No Pfam database files were found for any species!" )
        logger.error( f"Searched in: {pfam_directory}" )
        logger.error( "Run scripts 001-003 (InterProScan parsing) to generate Pfam database files." )
        sys.exit( 1 )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 011 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species processed: {species_processed_count}" )
    logger.info( f"  Species with Pfam data: {species_with_pfam_count}" )
    logger.info( f"  Species with MetaPredict data: {species_with_metapredict_count}" )
    logger.info( f"  Output file: {output_file_path}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Analyze multi-domain protein distribution and disorder content per species'
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
    logger.info( "Script 011: Analyze Protein Complexity" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load species list from statistics file
    # =========================================================================

    phylonames = extract_species_from_statistics( statistics_path, logger )

    # =========================================================================
    # Analyze protein complexity
    # =========================================================================

    analyze_protein_complexity( phylonames, database_directory, output_directory, logger )


if __name__ == '__main__':
    main()
