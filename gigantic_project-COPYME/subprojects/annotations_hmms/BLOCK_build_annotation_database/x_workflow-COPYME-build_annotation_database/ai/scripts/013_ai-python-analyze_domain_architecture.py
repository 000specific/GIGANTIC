#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Analyze transmembrane topology, signal peptide frequency, and domain combinations
# Human: Eric Edsinger

"""
013_ai-python-analyze_domain_architecture.py

Analyzes transmembrane topology distribution, signal peptide frequency, and
Pfam domain pair co-occurrence across species using the standardized database
files produced by the parsing scripts (003, 005, 006).

For each species, this script:
1. From tmbed database files (if available):
   - Counts TM helices per protein (rows with Annotation_Identifier == TM_helix)
   - Classifies: single-pass (1 TM helix), multi-pass (2+ TM helices)
   - Reports topology distribution per species
2. From signalp database files (if available):
   - Counts proteins with signal peptides per species
   - Calculates signal peptide frequency (percent of proteins)
3. From Pfam database files (if available):
   - Finds most common domain pairs (co-occurring Pfam domains in same protein)
   - Reports top 10 domain combinations per species

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
    13_ai-domain_architecture.tsv
    13_ai-log-analyze_domain_architecture.log

Usage:
    python3 013_ai-python-analyze_domain_architecture.py \\
        --statistics 8_ai-annotation_statistics.tsv \\
        --database-dir . \\
        --output-dir .
"""

import argparse
import logging
import sys
from collections import Counter
from collections import defaultdict
from itertools import combinations
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '013_analyze_domain_architecture' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '13_ai-log-analyze_domain_architecture.log'
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


def analyze_tmbed_for_species( tmbed_file_path: Path, phyloname: str,
                                logger: logging.Logger ) -> dict:
    """
    Read a tmbed database file for one species and analyze transmembrane topology.

    Each row in the tmbed database represents one transmembrane region. A protein
    with 7 TM helices will have 7 rows. We group by protein to count helices per
    protein, then classify as single-pass or multi-pass.

    Returns a dictionary with:
        'single_pass_count': int  (proteins with exactly 1 TM helix)
        'multi_pass_count': int   (proteins with 2+ TM helices)
        'total_transmembrane_protein_count': int
        'max_transmembrane_helices': int
    """

    # Group TM helix rows by protein identifier
    sequence_identifiers___transmembrane_helix_counts = defaultdict( int )

    with open( tmbed_file_path, 'r' ) as input_tmbed_file:
        # Phyloname (GIGANTIC phyloname for the species)	Sequence_Identifier (protein identifier from proteome)	Domain_Start ...	Domain_Stop ...	Database_Name ...	Annotation_Identifier (topology type TM_helix or TM_beta_barrel or signal_peptide)	Annotation_Details ...
        # Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	XP_027047018.1	45	67	tmbed	TM_helix	TM_helix,start=45,stop=67
        for line in input_tmbed_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            sequence_identifier = parts[ 1 ]
            annotation_identifier = parts[ 5 ]

            # Count only TM helix annotations (not signal_peptide or TM_beta_barrel)
            # for single-pass vs. multi-pass classification
            if annotation_identifier == 'TM_helix' or annotation_identifier == 'TM_beta_barrel':
                sequence_identifiers___transmembrane_helix_counts[ sequence_identifier ] += 1

    # Classify proteins
    single_pass_count = 0
    multi_pass_count = 0
    max_transmembrane_helices = 0

    for sequence_identifier in sequence_identifiers___transmembrane_helix_counts:
        helix_count = sequence_identifiers___transmembrane_helix_counts[ sequence_identifier ]

        if helix_count == 1:
            single_pass_count += 1
        elif helix_count >= 2:
            multi_pass_count += 1

        if helix_count > max_transmembrane_helices:
            max_transmembrane_helices = helix_count

    total_transmembrane_protein_count = single_pass_count + multi_pass_count

    results = {
        'single_pass_count': single_pass_count,
        'multi_pass_count': multi_pass_count,
        'total_transmembrane_protein_count': total_transmembrane_protein_count,
        'max_transmembrane_helices': max_transmembrane_helices,
    }

    logger.debug( f"    tmbed: single-pass={single_pass_count}, multi-pass={multi_pass_count}, max TM={max_transmembrane_helices}" )

    return results


def analyze_signalp_for_species( signalp_file_path: Path, phyloname: str,
                                  logger: logging.Logger ) -> dict:
    """
    Read a signalp database file for one species and count signal peptide proteins.

    Each protein with a signal peptide has one row in the signalp database file.

    Returns a dictionary with:
        'signal_peptide_protein_count': int
    """

    signal_peptide_proteins = set()

    with open( signalp_file_path, 'r' ) as input_signalp_file:
        # Phyloname (GIGANTIC phyloname for the species)	Sequence_Identifier (protein identifier from proteome)	Domain_Start ...	Domain_Stop ...	Database_Name ...	Annotation_Identifier ...	Annotation_Details ...
        # Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	XP_027047018.1	1	22	signalp	Sec/SPI	signal_peptide,cleavage_site=22,probability=0.95
        for line in input_signalp_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            sequence_identifier = parts[ 1 ]
            signal_peptide_proteins.add( sequence_identifier )

    signal_peptide_protein_count = len( signal_peptide_proteins )

    results = {
        'signal_peptide_protein_count': signal_peptide_protein_count,
    }

    logger.debug( f"    signalp: {signal_peptide_protein_count} proteins with signal peptides" )

    return results


def analyze_pfam_domain_pairs_for_species( pfam_file_path: Path, phyloname: str,
                                            logger: logging.Logger ) -> list:
    """
    Read a Pfam database file for one species and find co-occurring domain pairs.

    For each protein, collect all unique Pfam domain accessions (Annotation_Identifier).
    Then compute all pairwise combinations and count how often each pair co-occurs
    across proteins in this species.

    Returns a list of the top 10 domain pair strings, sorted by frequency.
    Each pair is formatted as "PF00069+PF00076" (sorted alphabetically).
    """

    # Group Pfam domain accessions by protein
    sequence_identifiers___domain_accessions = defaultdict( set )

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
            annotation_identifier = parts[ 5 ]

            sequence_identifiers___domain_accessions[ sequence_identifier ].add( annotation_identifier )

    # Count pairwise domain combinations across all proteins
    domain_pair___counts = Counter()

    for sequence_identifier in sequence_identifiers___domain_accessions:
        domain_accessions = sequence_identifiers___domain_accessions[ sequence_identifier ]

        # Only compute pairs for proteins with 2+ distinct domains
        if len( domain_accessions ) >= 2:
            sorted_domain_accessions = sorted( domain_accessions )

            # Generate all unique pairs (order-independent)
            for domain_pair in combinations( sorted_domain_accessions, 2 ):
                pair_string = domain_pair[ 0 ] + '+' + domain_pair[ 1 ]
                domain_pair___counts[ pair_string ] += 1

    # Get top 10 domain pairs
    top_domain_pairs_with_counts = domain_pair___counts.most_common( 10 )
    top_domain_pairs = [ pair_string for pair_string, count in top_domain_pairs_with_counts ]

    logger.debug( f"    Pfam pairs: {len( domain_pair___counts )} unique pairs, top 10 extracted" )

    return top_domain_pairs


def analyze_domain_architecture( phylonames: list, database_directory: Path,
                                  output_directory: Path, logger: logging.Logger ) -> None:
    """
    For each species, analyze transmembrane topology, signal peptide frequency,
    and Pfam domain pair co-occurrence.
    Write results to the domain architecture output TSV file.
    """

    # =========================================================================
    # Locate database directories
    # =========================================================================

    tmbed_directory = database_directory / 'database_tmbed'
    signalp_directory = database_directory / 'database_signalp'
    pfam_directory = database_directory / 'database_pfam'

    tmbed_available = tmbed_directory.exists() and tmbed_directory.is_dir()
    signalp_available = signalp_directory.exists() and signalp_directory.is_dir()
    pfam_available = pfam_directory.exists() and pfam_directory.is_dir()

    logger.info( f"  tmbed database directory: {tmbed_directory}" )
    logger.info( f"  signalp database directory: {signalp_directory}" )
    logger.info( f"  Pfam database directory: {pfam_directory}" )
    logger.info( f"  tmbed data available: {tmbed_available}" )
    logger.info( f"  signalp data available: {signalp_available}" )
    logger.info( f"  Pfam data available: {pfam_available}" )

    # At least one data source must be available
    if not tmbed_available and not signalp_available and not pfam_available:
        logger.error( "CRITICAL ERROR: No database directories found!" )
        logger.error( "At least one of tmbed, signalp, or Pfam database directories must exist." )
        logger.error( "Run the appropriate parsing scripts (003, 005, 006) first." )
        sys.exit( 1 )

    # =========================================================================
    # Prepare output file
    # =========================================================================

    output_file_path = output_directory / '13_ai-domain_architecture.tsv'

    # =========================================================================
    # Write header
    # =========================================================================

    header = 'Phyloname (phylogenetic name of species)' + '\t'
    header += 'Single_Pass_Transmembrane_Proteins (count of proteins with exactly one TM helix or NA)' + '\t'
    header += 'Multi_Pass_Transmembrane_Proteins (count of proteins with two or more TM helices or NA)' + '\t'
    header += 'Total_Transmembrane_Proteins (count of all proteins with any TM helix or NA)' + '\t'
    header += 'Max_TM_Helices_Single_Protein (highest TM helix count for any protein or NA)' + '\t'
    header += 'Signal_Peptide_Proteins (count of proteins with signal peptides or NA)' + '\t'
    header += 'Signal_Peptide_Frequency_Percent (signal peptide proteins divided by total transmembrane plus signal peptide proteins times 100 or NA)' + '\t'
    header += 'Top_Domain_Pairs (comma delimited list of 10 most frequent Pfam domain pair combinations or NA)' + '\n'

    # =========================================================================
    # Process each species
    # =========================================================================

    species_processed_count = 0
    species_with_tmbed_count = 0
    species_with_signalp_count = 0
    species_with_pfam_count = 0

    with open( output_file_path, 'w' ) as output_architecture_file:
        output_architecture_file.write( header )

        for phyloname in phylonames:
            species_processed_count += 1
            logger.info( f"  Processing species {species_processed_count}/{len( phylonames )}: {phyloname}" )

            # =================================================================
            # Analyze tmbed data for this species
            # =================================================================

            single_pass_transmembrane_proteins = 'NA'
            multi_pass_transmembrane_proteins = 'NA'
            total_transmembrane_proteins = 'NA'
            max_transmembrane_helices_single_protein = 'NA'

            if tmbed_available:
                tmbed_file_path = tmbed_directory / f"gigantic_annotations-database_tmbed-{phyloname}.tsv"

                if tmbed_file_path.exists():
                    species_with_tmbed_count += 1

                    tmbed_results = analyze_tmbed_for_species(
                        tmbed_file_path, phyloname, logger
                    )

                    single_pass_transmembrane_proteins = str( tmbed_results[ 'single_pass_count' ] )
                    multi_pass_transmembrane_proteins = str( tmbed_results[ 'multi_pass_count' ] )
                    total_transmembrane_proteins = str( tmbed_results[ 'total_transmembrane_protein_count' ] )
                    max_transmembrane_helices_single_protein = str( tmbed_results[ 'max_transmembrane_helices' ] )
                else:
                    logger.debug( f"    No tmbed file found for {phyloname}" )

            # =================================================================
            # Analyze signalp data for this species
            # =================================================================

            signal_peptide_proteins = 'NA'
            signal_peptide_frequency_percent = 'NA'

            if signalp_available:
                signalp_file_path = signalp_directory / f"gigantic_annotations-database_signalp-{phyloname}.tsv"

                if signalp_file_path.exists():
                    species_with_signalp_count += 1

                    signalp_results = analyze_signalp_for_species(
                        signalp_file_path, phyloname, logger
                    )

                    signal_peptide_protein_count = signalp_results[ 'signal_peptide_protein_count' ]
                    signal_peptide_proteins = str( signal_peptide_protein_count )

                    # Calculate frequency as signal peptide proteins divided by
                    # (total transmembrane + signal peptide proteins)
                    # Only possible if tmbed data is also available
                    if total_transmembrane_proteins != 'NA':
                        total_transmembrane_protein_count = int( total_transmembrane_proteins )
                        denominator = total_transmembrane_protein_count + signal_peptide_protein_count

                        if denominator > 0:
                            frequency = ( signal_peptide_protein_count / denominator ) * 100
                            signal_peptide_frequency_percent = f"{frequency:.2f}"
                        else:
                            signal_peptide_frequency_percent = '0.00'
                else:
                    logger.debug( f"    No signalp file found for {phyloname}" )

            # =================================================================
            # Analyze Pfam domain pairs for this species
            # =================================================================

            top_domain_pairs_string = 'NA'

            if pfam_available:
                pfam_file_path = pfam_directory / f"gigantic_annotations-database_pfam-{phyloname}.tsv"

                if pfam_file_path.exists():
                    species_with_pfam_count += 1

                    top_domain_pairs = analyze_pfam_domain_pairs_for_species(
                        pfam_file_path, phyloname, logger
                    )

                    if len( top_domain_pairs ) > 0:
                        top_domain_pairs_string = ','.join( top_domain_pairs )
                else:
                    logger.debug( f"    No Pfam file found for {phyloname}" )

            # =================================================================
            # Write output row for this species
            # =================================================================

            output = phyloname + '\t'
            output += single_pass_transmembrane_proteins + '\t'
            output += multi_pass_transmembrane_proteins + '\t'
            output += total_transmembrane_proteins + '\t'
            output += max_transmembrane_helices_single_protein + '\t'
            output += signal_peptide_proteins + '\t'
            output += signal_peptide_frequency_percent + '\t'
            output += top_domain_pairs_string + '\n'
            output_architecture_file.write( output )

            logger.debug( f"    TM single-pass: {single_pass_transmembrane_proteins}, multi-pass: {multi_pass_transmembrane_proteins}" )
            logger.debug( f"    Signal peptide proteins: {signal_peptide_proteins}" )
            logger.debug( f"    Top domain pairs: {top_domain_pairs_string[ :100 ]}" )

    # =========================================================================
    # Validate output
    # =========================================================================

    if species_processed_count == 0:
        logger.error( "CRITICAL ERROR: No species were processed!" )
        logger.error( "The species list from the statistics file was empty." )
        sys.exit( 1 )

    total_data_sources_found = species_with_tmbed_count + species_with_signalp_count + species_with_pfam_count

    if total_data_sources_found == 0:
        logger.error( "CRITICAL ERROR: No database files were found for any species!" )
        logger.error( "Checked tmbed, signalp, and Pfam directories." )
        logger.error( "Run the appropriate parsing scripts (003, 005, 006) first." )
        sys.exit( 1 )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 013 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species processed: {species_processed_count}" )
    logger.info( f"  Species with tmbed data: {species_with_tmbed_count}" )
    logger.info( f"  Species with signalp data: {species_with_signalp_count}" )
    logger.info( f"  Species with Pfam data: {species_with_pfam_count}" )
    logger.info( f"  Output file: {output_file_path}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Analyze transmembrane topology, signal peptide frequency, and domain combinations'
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
    logger.info( "Script 013: Analyze Domain Architecture" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load species list from statistics file
    # =========================================================================

    phylonames = extract_species_from_statistics( statistics_path, logger )

    # =========================================================================
    # Analyze domain architecture
    # =========================================================================

    analyze_domain_architecture( phylonames, database_directory, output_directory, logger )


if __name__ == '__main__':
    main()
