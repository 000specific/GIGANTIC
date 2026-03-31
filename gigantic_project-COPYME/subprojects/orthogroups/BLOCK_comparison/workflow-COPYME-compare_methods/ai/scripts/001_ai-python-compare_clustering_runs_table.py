#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 30 18:00 | Purpose: Compare orthogroup clustering runs - summary table with all metrics
# Human: Eric Edsinger

"""
001_ai-python-compare_clustering_runs_table.py

Generates a side-by-side comparison table of key clustering metrics across
multiple orthogroup clustering runs. Supports both OrthoHMM and OrthoFinder
output formats, auto-detected from the manifest's clustering_method column.

Supported clustering methods:
  - orthohmm:    Reads 4-output/4_ai-gene_count_gigantic_ids.tsv
  - orthofinder: Reads Orthogroups/Orthogroups.GeneCount.tsv +
                       Orthogroups/Orthogroups_UnassignedGenes.tsv

Computes 7 sections of metrics:
  1. Basic Clustering Metrics (totals, singletons)
  2. Single-Copy Orthogroups (1 species, 2+ species, all species, relaxed thresholds)
  3. Species Completeness (how many species per orthogroup)
  4. Size Distribution and Size Classes
  5. Per-Species Copy Number Profiles (mean across species)
  6. Taxonomic Breadth (phyla per orthogroup)
  7. Pairwise Run Overlap (gene co-clustering stability)

Input:
    --manifest: Path to clustering_manifest.tsv in INPUT_user/
        TSV with columns: run_label, output_pipeline_path, clustering_method

Output (written to --output-dir, default: current directory):
    1_ai-compare_clustering_runs.tsv
    1_ai-per_species_copy_number_profiles.tsv
    1_ai-pairwise_run_overlap.tsv
    1_ai-log-compare_clustering_runs_table.log

Usage:
    python3 ai/scripts/001_ai-python-compare_clustering_runs_table.py \\
        --manifest INPUT_user/clustering_manifest.tsv \\
        --output-dir OUTPUT_pipeline/1-output
"""

import argparse
import logging
import random
import statistics
import sys
from pathlib import Path


# =============================================================================
# Manifest parsing
# =============================================================================

def parse_manifest( manifest_path: Path ) -> tuple:
    """
    Parse a GIGANTIC clustering manifest TSV file.

    Returns:
        ( run_labels, run_directories, clustering_methods ) tuple of three lists.
    """

    if not manifest_path.exists():
        print( f"ERROR: Manifest file not found: {manifest_path}" )
        sys.exit( 1 )

    run_labels = []
    run_directories = []
    clustering_methods = []

    with open( manifest_path, 'r' ) as input_file:

        # run_label	output_pipeline_path	clustering_method
        # RUN_1	../../BLOCK_orthohmm/workflow-RUN_1-run_orthohmm/OUTPUT_pipeline	orthohmm
        header_found = False

        for line in input_file:
            line = line.strip()

            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )

            if not header_found:
                if parts[ 0 ] == 'run_label':
                    header_found = True
                    continue
                else:
                    print( f"ERROR: Expected header row with 'run_label' as first column." )
                    sys.exit( 1 )

            if len( parts ) < 3:
                print( f"ERROR: Manifest row needs 3 columns (run_label, output_pipeline_path, clustering_method)." )
                print( f"  Got: {line}" )
                sys.exit( 1 )

            run_label = parts[ 0 ]
            output_pipeline_path = Path( parts[ 1 ] )
            clustering_method = parts[ 2 ].strip().lower()

            if not output_pipeline_path.is_absolute():
                output_pipeline_path = ( manifest_path.parent / output_pipeline_path ).resolve()

            run_labels.append( run_label )
            run_directories.append( output_pipeline_path )
            clustering_methods.append( clustering_method )

    if not header_found:
        print( f"ERROR: No header row found in manifest." )
        sys.exit( 1 )

    if len( run_labels ) < 2:
        print( f"ERROR: Manifest must contain at least 2 clustering runs for comparison." )
        sys.exit( 1 )

    if len( set( run_labels ) ) != len( run_labels ):
        print( f"ERROR: Duplicate run_label values in manifest." )
        sys.exit( 1 )

    return run_labels, run_directories, clustering_methods


# =============================================================================
# Logging
# =============================================================================

def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '001_compare_clustering_runs' )
    logger.setLevel( logging.DEBUG )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    log_file = output_directory / '1_ai-log-compare_clustering_runs_table.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


# =============================================================================
# File locators
# =============================================================================

def find_orthohmm_files( run_directory: Path ) -> dict:
    """Locate OrthoHMM gene_count and orthogroups files."""

    gene_count_path = run_directory / '4-output' / '4_ai-gene_count_gigantic_ids.tsv'
    orthogroups_path = run_directory / '4-output' / '4_ai-orthogroups_gigantic_ids.tsv'

    # Fallback to 3-output
    if not gene_count_path.exists():
        for candidate in ( run_directory / '3-output' ).glob( '*gene_count*' ):
            gene_count_path = candidate
            break
    if not orthogroups_path.exists():
        for candidate in ( run_directory / '3-output' ).glob( '*orthogroups*' ):
            orthogroups_path = candidate
            break

    return { 'gene_count': gene_count_path, 'orthogroups': orthogroups_path }


def find_orthofinder_files( run_directory: Path ) -> dict:
    """
    Locate OrthoFinder files. run_directory should point to the
    OrthoFinder Results_* directory (containing Orthogroups/, etc.).
    """

    gene_count_path = run_directory / 'Orthogroups' / 'Orthogroups.GeneCount.tsv'
    orthogroups_path = run_directory / 'Orthogroups' / 'Orthogroups.tsv'
    unassigned_path = run_directory / 'Orthogroups' / 'Orthogroups_UnassignedGenes.tsv'

    return {
        'gene_count': gene_count_path,
        'orthogroups': orthogroups_path,
        'unassigned': unassigned_path,
    }


# =============================================================================
# Species -> phylum mapping
# =============================================================================

def extract_phylum_from_gene_identifier( gene_identifier: str ) -> tuple:
    """
    Extract (genus_species, phylum) from a GIGANTIC gene identifier.

    Gene ID format: g_GENE-t_TRANSCRIPT-p_PROTEIN-n_Kingdom_Phylum_Class_Order_Family_Genus_species
    Returns (genus_species, phylum) or (None, None) if can't parse.
    """

    if '-n_' not in gene_identifier:
        return None, None

    phyloname = gene_identifier.split( '-n_' )[ 1 ]
    parts_phyloname = phyloname.split( '_' )

    if len( parts_phyloname ) >= 7:
        phylum = parts_phyloname[ 1 ]
        genus_species = parts_phyloname[ 5 ] + '_' + '_'.join( parts_phyloname[ 6: ] )
        return genus_species, phylum

    return None, None


def build_species_phylum_map_from_orthogroups( orthogroups_path: Path, delimiter: str, gene_column_start: int, logger: logging.Logger ) -> dict:
    """
    Build species_name -> phylum mapping from an orthogroups file.

    Works for both OrthoHMM (tab-delimited, genes in columns 1+) and
    OrthoFinder (tab-delimited, comma-separated genes in species columns).
    """

    species_names___phyla = {}

    with open( orthogroups_path, 'r' ) as input_file:
        for line in input_file:
            parts = line.strip().split( '\t' )

            for column_index in range( gene_column_start, len( parts ) ):
                cell = parts[ column_index ]
                if not cell:
                    continue

                # OrthoFinder uses comma-separated genes; OrthoHMM uses one gene per column
                gene_identifiers = [ gene.strip() for gene in cell.split( ',' ) ] if ',' in cell else [ cell ]

                for gene_identifier in gene_identifiers:
                    genus_species, phylum = extract_phylum_from_gene_identifier( gene_identifier )
                    if genus_species and genus_species not in species_names___phyla:
                        species_names___phyla[ genus_species ] = phylum

            if len( species_names___phyla ) >= 70:
                break

    logger.info( f"  Mapped {len( species_names___phyla )} species to phyla" )
    return species_names___phyla


# =============================================================================
# Gene -> orthogroup mapping (for pairwise overlap)
# =============================================================================

def build_gene_map_orthohmm( orthogroups_path: Path, logger: logging.Logger ) -> dict:
    """Build gene_id -> orthogroup_id from OrthoHMM orthogroups file."""

    gene_identifiers___orthogroup_identifiers = {}

    with open( orthogroups_path, 'r' ) as input_file:
        for line in input_file:
            parts = line.strip().split( '\t' )
            orthogroup_identifier = parts[ 0 ]
            for gene_identifier in parts[ 1: ]:
                if gene_identifier:
                    gene_identifiers___orthogroup_identifiers[ gene_identifier ] = orthogroup_identifier

    logger.info( f"  Mapped {len( gene_identifiers___orthogroup_identifiers ):,} genes to orthogroups" )
    return gene_identifiers___orthogroup_identifiers


def build_gene_map_orthofinder( orthogroups_path: Path, unassigned_path: Path, logger: logging.Logger ) -> dict:
    """Build gene_id -> orthogroup_id from OrthoFinder files."""

    gene_identifiers___orthogroup_identifiers = {}

    for file_path in [ orthogroups_path, unassigned_path ]:
        if not file_path.exists():
            continue

        with open( file_path, 'r' ) as input_file:
            header = input_file.readline()  # skip header

            for line in input_file:
                parts = line.strip().split( '\t' )
                orthogroup_identifier = parts[ 0 ]

                for column_index in range( 1, len( parts ) ):
                    cell = parts[ column_index ]
                    if not cell:
                        continue
                    gene_identifiers = [ gene.strip() for gene in cell.split( ', ' ) ]
                    for gene_identifier in gene_identifiers:
                        if gene_identifier:
                            gene_identifiers___orthogroup_identifiers[ gene_identifier ] = orthogroup_identifier

    logger.info( f"  Mapped {len( gene_identifiers___orthogroup_identifiers ):,} genes to orthogroups" )
    return gene_identifiers___orthogroup_identifiers


# =============================================================================
# Gene count parsers
# =============================================================================

def parse_orthohmm_gene_count( gene_count_path: Path, species_names___phyla: dict, logger: logging.Logger ) -> tuple:
    """Parse OrthoHMM gene_count file. Returns ( metrics, per_species_data )."""

    logger.info( f"  Parsing OrthoHMM: {gene_count_path}" )

    with open( gene_count_path, 'r' ) as input_file:

        # files: Bolinopsis_microptera.pep Monosiga_brevicollis_MX1.pep ...
        # OG000000: 88 0 277 90 250 ...
        header_line = input_file.readline().strip()

        if not header_line.startswith( 'files:' ):
            logger.error( f"  Unexpected header: {header_line[ :80 ]}" )
            sys.exit( 1 )

        parts_header = header_line.split()
        species_names = [ name.replace( '.pep', '' ) for name in parts_header[ 1: ] ]
        species_count = len( species_names )

        all_counts = []
        for line in input_file:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            counts = [ int( value ) for value in parts[ 1: ] ]
            all_counts.append( counts )

    return compute_metrics( species_names, all_counts, species_names___phyla, logger )


def parse_orthofinder_gene_count( gene_count_path: Path, unassigned_path: Path, species_names___phyla: dict, logger: logging.Logger ) -> tuple:
    """Parse OrthoFinder GeneCount + UnassignedGenes. Returns ( metrics, per_species_data )."""

    logger.info( f"  Parsing OrthoFinder: {gene_count_path}" )

    # Read GeneCount.tsv (tab-separated, has Total column at end)
    species_names = []
    all_counts = []

    with open( gene_count_path, 'r' ) as input_file:

        # Orthogroup	Sp1	Sp2	...	Total
        # OG0000000	777	224	4	...	7948
        header_line = input_file.readline().strip()
        parts_header = header_line.split( '\t' )

        # Species are columns 1 through N-1 (last column is "Total")
        for column_index in range( 1, len( parts_header ) ):
            if parts_header[ column_index ] == 'Total':
                break
            species_names.append( parts_header[ column_index ] )

        species_count = len( species_names )

        for line in input_file:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            counts = [ int( parts[ i ] ) for i in range( 1, species_count + 1 ) ]
            all_counts.append( counts )

    logger.info( f"  Assigned orthogroups: {len( all_counts ):,}" )

    # Read UnassignedGenes.tsv (same species columns, comma-separated gene IDs)
    if unassigned_path.exists():
        unassigned_count = 0

        with open( unassigned_path, 'r' ) as input_file:

            # Orthogroup	Sp1	Sp2	...
            # OG0048111			gene1, gene2	...
            header_line = input_file.readline()  # skip header

            for line in input_file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split( '\t' )

                counts = []
                for column_index in range( 1, species_count + 1 ):
                    if column_index < len( parts ) and parts[ column_index ]:
                        gene_count = len( [ gene for gene in parts[ column_index ].split( ', ' ) if gene.strip() ] )
                        counts.append( gene_count )
                    else:
                        counts.append( 0 )

                all_counts.append( counts )
                unassigned_count += 1

        logger.info( f"  Unassigned orthogroups: {unassigned_count:,}" )
    else:
        logger.warning( f"  Unassigned genes file not found: {unassigned_path}" )

    logger.info( f"  Total orthogroups: {len( all_counts ):,}" )

    return compute_metrics( species_names, all_counts, species_names___phyla, logger )


# =============================================================================
# Shared metrics computation
# =============================================================================

def compute_metrics( species_names: list, all_counts: list, species_names___phyla: dict, logger: logging.Logger ) -> tuple:
    """
    Compute all comparison metrics from a standardized list of per-OG count vectors.

    species_names: list of species name strings
    all_counts: list of lists, each inner list = gene counts per species for one OG
    species_names___phyla: dict mapping species name -> phylum

    Returns ( metrics_dict, per_species_data_dict ).
    """

    species_count = len( species_names )
    half_species = species_count // 2
    logger.info( f"  Species count: {species_count}" )

    # Build species index -> phylum
    species_indices___phyla = {}
    for species_index in range( species_count ):
        phylum = species_names___phyla.get( species_names[ species_index ], 'Unknown' )
        species_indices___phyla[ species_index ] = phylum

    # Counters
    orthogroup_sizes = []
    total_sequences = 0
    singleton_count = 0

    single_copy_one_species_count = 0
    single_copy_two_or_more_species_count = 0
    single_copy_all_species_count = 0
    single_copy_threshold_50_count = 0
    single_copy_threshold_75_count = 0
    single_copy_threshold_90_count = 0

    completeness_universal = 0
    completeness_near_universal = 0
    completeness_half_plus = 0
    completeness_some = 0
    completeness_few = 0

    size_class_small = 0
    size_class_medium = 0
    size_class_large = 0
    size_class_very_large = 0

    per_species_single_copy = [ 0 ] * species_count
    per_species_two_copy = [ 0 ] * species_count
    per_species_low_multi_copy = [ 0 ] * species_count
    per_species_high_multi_copy = [ 0 ] * species_count

    phyla_per_orthogroup_values = []

    for counts in all_counts:
        orthogroup_size = sum( counts )
        orthogroup_sizes.append( orthogroup_size )
        total_sequences += orthogroup_size

        if orthogroup_size == 1:
            singleton_count += 1

        species_present = 0
        single_copy_species = 0
        phyla_in_this_orthogroup = set()

        for species_index in range( species_count ):
            count = counts[ species_index ]

            if count == 0:
                pass
            elif count == 1:
                per_species_single_copy[ species_index ] += 1
                species_present += 1
                single_copy_species += 1
                phyla_in_this_orthogroup.add( species_indices___phyla[ species_index ] )
            elif count == 2:
                per_species_two_copy[ species_index ] += 1
                species_present += 1
                phyla_in_this_orthogroup.add( species_indices___phyla[ species_index ] )
            elif count <= 5:
                per_species_low_multi_copy[ species_index ] += 1
                species_present += 1
                phyla_in_this_orthogroup.add( species_indices___phyla[ species_index ] )
            else:
                per_species_high_multi_copy[ species_index ] += 1
                species_present += 1
                phyla_in_this_orthogroup.add( species_indices___phyla[ species_index ] )

        all_single_copy = ( single_copy_species == species_present )

        # Single-copy: 1 species (exactly 1 species with 1 gene)
        if all_single_copy and species_present == 1:
            single_copy_one_species_count += 1

        # Single-copy: 2+ species
        if all_single_copy and species_present >= 2:
            single_copy_two_or_more_species_count += 1

        # Single-copy: all species
        if all_single_copy and species_present == species_count:
            single_copy_all_species_count += 1

        # Single-copy: relaxed thresholds (2+ species OGs only)
        if species_present >= 2:
            fraction = single_copy_species / species_present
            if fraction >= 0.50:
                single_copy_threshold_50_count += 1
            if fraction >= 0.75:
                single_copy_threshold_75_count += 1
            if fraction >= 0.90:
                single_copy_threshold_90_count += 1
            phyla_per_orthogroup_values.append( len( phyla_in_this_orthogroup ) )

        # Species completeness
        if species_present == species_count:
            completeness_universal += 1
        elif species_present >= 50:
            completeness_near_universal += 1
        elif species_present >= half_species:
            completeness_half_plus += 1
        elif species_present >= 10:
            completeness_some += 1
        elif species_present >= 2:
            completeness_few += 1

        # Size class
        if orthogroup_size >= 2 and orthogroup_size <= 10:
            size_class_small += 1
        elif orthogroup_size >= 11 and orthogroup_size <= 100:
            size_class_medium += 1
        elif orthogroup_size >= 101 and orthogroup_size <= 1000:
            size_class_large += 1
        elif orthogroup_size > 1000:
            size_class_very_large += 1

    total_orthogroups = len( orthogroup_sizes )
    multi_gene_count = total_orthogroups - singleton_count

    if orthogroup_sizes:
        mean_size = statistics.mean( orthogroup_sizes )
        median_size = statistics.median( orthogroup_sizes )
        max_size = max( orthogroup_sizes )
    else:
        mean_size = 0
        median_size = 0
        max_size = 0

    if phyla_per_orthogroup_values:
        mean_phyla = statistics.mean( phyla_per_orthogroup_values )
        median_phyla = statistics.median( phyla_per_orthogroup_values )
        max_phyla = max( phyla_per_orthogroup_values )
        broad_taxonomic_count = sum( 1 for v in phyla_per_orthogroup_values if v >= 10 )
        narrow_taxonomic_count = sum( 1 for v in phyla_per_orthogroup_values if v == 1 )
    else:
        mean_phyla = 0
        median_phyla = 0
        max_phyla = 0
        broad_taxonomic_count = 0
        narrow_taxonomic_count = 0

    mean_single_copy_per_species = statistics.mean( per_species_single_copy )
    mean_two_copy_per_species = statistics.mean( per_species_two_copy )
    mean_low_multi_per_species = statistics.mean( per_species_low_multi_copy )
    mean_high_multi_per_species = statistics.mean( per_species_high_multi_copy )

    metrics = {
        'Species_Count': species_count,
        'Total_Orthogroups': total_orthogroups,
        'Total_Sequences': total_sequences,
        'Singleton_Orthogroups': singleton_count,
        'Singleton_Percent': f"{singleton_count / total_orthogroups * 100:.1f}" if total_orthogroups > 0 else "0.0",
        'Multi_Gene_Orthogroups': multi_gene_count,
        'Single_Copy_One_Species': single_copy_one_species_count,
        'Single_Copy_Two_Or_More_Species': single_copy_two_or_more_species_count,
        'Single_Copy_All_Species': single_copy_all_species_count,
        'Single_Copy_Relaxed_50_Percent': single_copy_threshold_50_count,
        'Single_Copy_Relaxed_75_Percent': single_copy_threshold_75_count,
        'Single_Copy_Relaxed_90_Percent': single_copy_threshold_90_count,
        'Completeness_Universal': completeness_universal,
        'Completeness_Near_Universal_50_Plus': completeness_near_universal,
        'Completeness_Half_Plus': completeness_half_plus,
        'Completeness_Some_10_To_Half': completeness_some,
        'Completeness_Few_2_To_9': completeness_few,
        'Max_Orthogroup_Size': max_size,
        'Mean_Orthogroup_Size': f"{mean_size:.2f}",
        'Median_Orthogroup_Size': median_size,
        'Size_Class_Small_2_To_10': size_class_small,
        'Size_Class_Medium_11_To_100': size_class_medium,
        'Size_Class_Large_101_To_1000': size_class_large,
        'Size_Class_Very_Large_Over_1000': size_class_very_large,
        'Mean_Single_Copy_Orthogroups_Per_Species': int( round( mean_single_copy_per_species ) ),
        'Mean_Two_Copy_Orthogroups_Per_Species': int( round( mean_two_copy_per_species ) ),
        'Mean_Low_Multi_Copy_3_To_5_Per_Species': int( round( mean_low_multi_per_species ) ),
        'Mean_High_Multi_Copy_6_Plus_Per_Species': int( round( mean_high_multi_per_species ) ),
        'Mean_Phyla_Per_Orthogroup': f"{mean_phyla:.2f}",
        'Median_Phyla_Per_Orthogroup': median_phyla,
        'Max_Phyla_Per_Orthogroup': max_phyla,
        'Broad_Taxonomic_Orthogroups_10_Plus_Phyla': broad_taxonomic_count,
        'Narrow_Taxonomic_Orthogroups_1_Phylum': narrow_taxonomic_count,
    }

    per_species_data = {
        'species_names': species_names,
        'single_copy': per_species_single_copy,
        'two_copy': per_species_two_copy,
        'low_multi_copy': per_species_low_multi_copy,
        'high_multi_copy': per_species_high_multi_copy,
    }

    logger.info( f"  Total orthogroups: {total_orthogroups:,}" )
    logger.info( f"  Total sequences: {total_sequences:,}" )
    logger.info( f"  Single-copy (1 species): {single_copy_one_species_count:,}" )
    logger.info( f"  Single-copy (2+ species): {single_copy_two_or_more_species_count:,}" )
    logger.info( f"  Single-copy (all species): {single_copy_all_species_count:,}" )

    return metrics, per_species_data


# =============================================================================
# Pairwise overlap
# =============================================================================

def compute_pairwise_overlap( run_a_label: str, run_a_gene_map: dict,
                              run_b_label: str, run_b_gene_map: dict,
                              sample_size: int, logger: logging.Logger ) -> dict:
    """Compute gene co-clustering overlap between two runs using sampling."""

    logger.info( f"  Computing overlap: {run_a_label} vs {run_b_label}" )

    shared_genes = set( run_a_gene_map.keys() ) & set( run_b_gene_map.keys() )
    logger.info( f"    Shared genes: {len( shared_genes ):,}" )

    if len( shared_genes ) < 100:
        return {
            'shared_genes': len( shared_genes ),
            'sampled_pairs': 0,
            'same_in_a_count': 0, 'same_in_a_also_same_in_b': 0,
            'agreement_a_to_b': 'NA',
            'same_in_b_count': 0, 'same_in_b_also_same_in_a': 0,
            'agreement_b_to_a': 'NA',
        }

    shared_genes_list = list( shared_genes )
    random.seed( 42 )

    same_in_a_count = 0
    same_in_a_also_same_in_b = 0
    same_in_b_count = 0
    same_in_b_also_same_in_a = 0

    for _ in range( sample_size ):
        gene_1 = random.choice( shared_genes_list )
        gene_2 = random.choice( shared_genes_list )
        if gene_1 == gene_2:
            continue

        same_in_a = ( run_a_gene_map[ gene_1 ] == run_a_gene_map[ gene_2 ] )
        same_in_b = ( run_b_gene_map[ gene_1 ] == run_b_gene_map[ gene_2 ] )

        if same_in_a:
            same_in_a_count += 1
            if same_in_b:
                same_in_a_also_same_in_b += 1
        if same_in_b:
            same_in_b_count += 1
            if same_in_a:
                same_in_b_also_same_in_a += 1

    agreement_a_to_b = same_in_a_also_same_in_b / same_in_a_count * 100 if same_in_a_count > 0 else 0
    agreement_b_to_a = same_in_b_also_same_in_a / same_in_b_count * 100 if same_in_b_count > 0 else 0

    logger.info( f"    {run_a_label} -> {run_b_label}: {agreement_a_to_b:.1f}% agreement" )
    logger.info( f"    {run_b_label} -> {run_a_label}: {agreement_b_to_a:.1f}% agreement" )

    return {
        'shared_genes': len( shared_genes ),
        'sampled_pairs': sample_size,
        'same_in_a_count': same_in_a_count,
        'same_in_a_also_same_in_b': same_in_a_also_same_in_b,
        'agreement_a_to_b': f"{agreement_a_to_b:.1f}",
        'same_in_b_count': same_in_b_count,
        'same_in_b_also_same_in_a': same_in_b_also_same_in_a,
        'agreement_b_to_a': f"{agreement_b_to_a:.1f}",
    }


# =============================================================================
# Metric row definitions
# =============================================================================

METRIC_ROWS = [
    ( '_SECTION_', '--- Basic Clustering Metrics ---' ),
    ( 'Species_Count', 'number of species in analysis' ),
    ( 'Total_Orthogroups', 'number of orthogroups identified' ),
    ( 'Total_Sequences', 'total protein sequences across all species' ),
    ( 'Singleton_Orthogroups', 'orthogroups containing exactly one gene' ),
    ( 'Singleton_Percent', 'percentage of orthogroups that are singletons' ),
    ( 'Multi_Gene_Orthogroups', 'orthogroups with two or more genes' ),
    ( '_SECTION_', '--- Single-Copy Orthogroups ---' ),
    ( 'Single_Copy_One_Species', 'orthogroups with exactly one species having exactly one gene' ),
    ( 'Single_Copy_Two_Or_More_Species', 'orthogroups with two or more species each having exactly one gene' ),
    ( 'Single_Copy_All_Species', 'orthogroups where every species has exactly one gene' ),
    ( 'Single_Copy_Relaxed_50_Percent', 'orthogroups where at least 50 percent of present species have one copy' ),
    ( 'Single_Copy_Relaxed_75_Percent', 'orthogroups where at least 75 percent of present species have one copy' ),
    ( 'Single_Copy_Relaxed_90_Percent', 'orthogroups where at least 90 percent of present species have one copy' ),
    ( '_SECTION_', '--- Species Completeness ---' ),
    ( 'Completeness_Universal', 'orthogroups present in all species' ),
    ( 'Completeness_Near_Universal_50_Plus', 'orthogroups present in 50 to N minus 1 species' ),
    ( 'Completeness_Half_Plus', 'orthogroups present in half to 49 species' ),
    ( 'Completeness_Some_10_To_Half', 'orthogroups present in 10 to half minus 1 species' ),
    ( 'Completeness_Few_2_To_9', 'orthogroups present in 2 to 9 species' ),
    ( '_SECTION_', '--- Size Distribution ---' ),
    ( 'Max_Orthogroup_Size', 'largest orthogroup gene count' ),
    ( 'Mean_Orthogroup_Size', 'average genes per orthogroup' ),
    ( 'Median_Orthogroup_Size', 'median genes per orthogroup' ),
    ( 'Size_Class_Small_2_To_10', 'orthogroups with 2 to 10 genes' ),
    ( 'Size_Class_Medium_11_To_100', 'orthogroups with 11 to 100 genes' ),
    ( 'Size_Class_Large_101_To_1000', 'orthogroups with 101 to 1000 genes' ),
    ( 'Size_Class_Very_Large_Over_1000', 'orthogroups with more than 1000 genes' ),
    ( '_SECTION_', '--- Per-Species Copy Number (means across species) ---' ),
    ( 'Mean_Single_Copy_Orthogroups_Per_Species', 'mean number of orthogroups where species has exactly 1 gene' ),
    ( 'Mean_Two_Copy_Orthogroups_Per_Species', 'mean number of orthogroups where species has exactly 2 genes' ),
    ( 'Mean_Low_Multi_Copy_3_To_5_Per_Species', 'mean number of orthogroups where species has 3 to 5 genes' ),
    ( 'Mean_High_Multi_Copy_6_Plus_Per_Species', 'mean number of orthogroups where species has 6 or more genes' ),
    ( '_SECTION_', '--- Taxonomic Breadth (phyla per orthogroup for multi-species OGs) ---' ),
    ( 'Mean_Phyla_Per_Orthogroup', 'mean number of phyla represented per orthogroup' ),
    ( 'Median_Phyla_Per_Orthogroup', 'median phyla per orthogroup' ),
    ( 'Max_Phyla_Per_Orthogroup', 'maximum phyla in any single orthogroup' ),
    ( 'Broad_Taxonomic_Orthogroups_10_Plus_Phyla', 'orthogroups spanning 10 or more phyla' ),
    ( 'Narrow_Taxonomic_Orthogroups_1_Phylum', 'orthogroups restricted to a single phylum' ),
]


# =============================================================================
# Main
# =============================================================================

def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Compare orthogroup clustering runs - summary table'
    )

    parser.add_argument( '--manifest', type = str, required = True, help = 'Path to clustering_manifest.tsv' )
    parser.add_argument( '--output-dir', type = str, default = '.', help = 'Output directory' )
    parser.add_argument( '--overlap-sample-size', type = int, default = 500000, help = 'Gene pairs for overlap analysis' )

    arguments = parser.parse_args()

    manifest_path = Path( arguments.manifest )
    output_directory = Path( arguments.output_dir )

    run_labels, run_directories, clustering_methods = parse_manifest( manifest_path )
    print( f"Loaded manifest: {manifest_path} ({len( run_labels )} runs)" )

    output_directory.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 001: Compare Clustering Runs - Summary Table" )
    logger.info( "=" * 70 )
    logger.info( f"Manifest: {manifest_path}" )
    for index in range( len( run_labels ) ):
        logger.info( f"  {run_labels[ index ]}: {clustering_methods[ index ]} @ {run_directories[ index ]}" )

    # =========================================================================
    # Build species -> phylum mapping (from first run's orthogroups file)
    # =========================================================================

    logger.info( "" )
    logger.info( "Building species -> phylum mapping..." )

    if clustering_methods[ 0 ] == 'orthofinder':
        first_files = find_orthofinder_files( run_directories[ 0 ] )
        species_names___phyla = build_species_phylum_map_from_orthogroups( first_files[ 'orthogroups' ], '\t', 1, logger )
    else:
        first_files = find_orthohmm_files( run_directories[ 0 ] )
        species_names___phyla = build_species_phylum_map_from_orthogroups( first_files[ 'orthogroups' ], '\t', 1, logger )

    # =========================================================================
    # Parse each run (dispatch by clustering method)
    # =========================================================================

    runs___metrics = {}
    runs___per_species_data = {}
    runs___gene_maps = {}

    for index in range( len( run_directories ) ):
        run_directory = run_directories[ index ]
        run_label = run_labels[ index ]
        clustering_method = clustering_methods[ index ]

        logger.info( "" )
        logger.info( f"Processing: {run_label} ({clustering_method})" )
        logger.info( f"  Directory: {run_directory}" )

        if clustering_method == 'orthofinder':
            files = find_orthofinder_files( run_directory )

            if not files[ 'gene_count' ].exists():
                logger.error( f"  CRITICAL ERROR: {files[ 'gene_count' ]} not found" )
                sys.exit( 1 )

            metrics, per_species_data = parse_orthofinder_gene_count(
                files[ 'gene_count' ],
                files.get( 'unassigned', Path( 'nonexistent' ) ),
                species_names___phyla, logger
            )

            if files[ 'orthogroups' ].exists():
                logger.info( f"  Building gene -> orthogroup map..." )
                runs___gene_maps[ run_label ] = build_gene_map_orthofinder(
                    files[ 'orthogroups' ],
                    files.get( 'unassigned', Path( 'nonexistent' ) ),
                    logger
                )

        else:  # orthohmm (default)
            files = find_orthohmm_files( run_directory )

            if not files[ 'gene_count' ].exists():
                logger.error( f"  CRITICAL ERROR: {files[ 'gene_count' ]} not found" )
                sys.exit( 1 )

            metrics, per_species_data = parse_orthohmm_gene_count(
                files[ 'gene_count' ], species_names___phyla, logger
            )

            if files[ 'orthogroups' ].exists():
                logger.info( f"  Building gene -> orthogroup map..." )
                runs___gene_maps[ run_label ] = build_gene_map_orthohmm(
                    files[ 'orthogroups' ], logger
                )

        runs___metrics[ run_label ] = metrics
        runs___per_species_data[ run_label ] = per_species_data

    # =========================================================================
    # Pairwise overlap
    # =========================================================================

    pairwise_overlaps = []

    if len( runs___gene_maps ) >= 2:
        logger.info( "" )
        logger.info( "Computing pairwise overlap..." )
        run_label_list = list( runs___gene_maps.keys() )

        for i in range( len( run_label_list ) ):
            for j in range( i + 1, len( run_label_list ) ):
                overlap = compute_pairwise_overlap(
                    run_label_list[ i ], runs___gene_maps[ run_label_list[ i ] ],
                    run_label_list[ j ], runs___gene_maps[ run_label_list[ j ] ],
                    arguments.overlap_sample_size, logger
                )
                overlap[ 'run_a' ] = run_label_list[ i ]
                overlap[ 'run_b' ] = run_label_list[ j ]
                pairwise_overlaps.append( overlap )

    # =========================================================================
    # Write main comparison table
    # =========================================================================

    output_path = output_directory / '1_ai-compare_clustering_runs.tsv'
    logger.info( f"\nWriting comparison table to: {output_path}" )

    with open( output_path, 'w' ) as output_file:

        header = 'Metric (description of clustering metric)'
        for run_label in runs___metrics:
            header += '\t' + run_label + ' (value for this run)'
        header += '\n'
        output_file.write( header )

        for metric_key, metric_description in METRIC_ROWS:
            if metric_key == '_SECTION_':
                output = metric_description
                for run_label in runs___metrics:
                    output += '\t'
                output += '\n'
            else:
                output = metric_key + ' (' + metric_description + ')'
                for run_label in runs___metrics:
                    value = runs___metrics[ run_label ].get( metric_key, 'NA' )
                    output += '\t' + str( value )
                output += '\n'
            output_file.write( output )

    # =========================================================================
    # Write per-species profiles
    # =========================================================================

    per_species_path = output_directory / '1_ai-per_species_copy_number_profiles.tsv'

    with open( per_species_path, 'w' ) as output_file:
        header = 'Species (genus species name)\tRun (run label)\t'
        header += 'Single_Copy_Orthogroups (orthogroups where species has 1 gene)\t'
        header += 'Two_Copy_Orthogroups (orthogroups where species has 2 genes)\t'
        header += 'Low_Multi_Copy_3_To_5 (orthogroups where species has 3 to 5 genes)\t'
        header += 'High_Multi_Copy_6_Plus (orthogroups where species has 6 or more genes)\n'
        output_file.write( header )

        for run_label in runs___per_species_data:
            per_species = runs___per_species_data[ run_label ]
            for species_index in range( len( per_species[ 'species_names' ] ) ):
                output = per_species[ 'species_names' ][ species_index ] + '\t'
                output += run_label + '\t'
                output += str( per_species[ 'single_copy' ][ species_index ] ) + '\t'
                output += str( per_species[ 'two_copy' ][ species_index ] ) + '\t'
                output += str( per_species[ 'low_multi_copy' ][ species_index ] ) + '\t'
                output += str( per_species[ 'high_multi_copy' ][ species_index ] ) + '\n'
                output_file.write( output )

    # =========================================================================
    # Write pairwise overlap
    # =========================================================================

    if pairwise_overlaps:
        overlap_path = output_directory / '1_ai-pairwise_run_overlap.tsv'

        with open( overlap_path, 'w' ) as output_file:
            header = 'Run_A (first run)\tRun_B (second run)\t'
            header += 'Shared_Genes (genes in both runs)\t'
            header += 'Sampled_Pairs (random gene pairs tested)\t'
            header += 'Co_Clustered_In_A (pairs in same OG in run A)\t'
            header += 'Also_In_B (of those also in same OG in run B)\t'
            header += 'Agreement_A_To_B_Percent (percent)\t'
            header += 'Co_Clustered_In_B (pairs in same OG in run B)\t'
            header += 'Also_In_A (of those also in same OG in run A)\t'
            header += 'Agreement_B_To_A_Percent (percent)\n'
            output_file.write( header )

            for overlap in pairwise_overlaps:
                output = overlap[ 'run_a' ] + '\t' + overlap[ 'run_b' ] + '\t'
                output += str( overlap[ 'shared_genes' ] ) + '\t'
                output += str( overlap[ 'sampled_pairs' ] ) + '\t'
                output += str( overlap[ 'same_in_a_count' ] ) + '\t'
                output += str( overlap[ 'same_in_a_also_same_in_b' ] ) + '\t'
                output += str( overlap[ 'agreement_a_to_b' ] ) + '\t'
                output += str( overlap[ 'same_in_b_count' ] ) + '\t'
                output += str( overlap[ 'same_in_b_also_same_in_a' ] ) + '\t'
                output += str( overlap[ 'agreement_b_to_a' ] ) + '\n'
                output_file.write( output )

    # Console summary
    print( "\nComparison table, per-species profiles, and pairwise overlap written." )
    if pairwise_overlaps:
        print( "\nPairwise Gene Co-Clustering Agreement:" )
        for overlap in pairwise_overlaps:
            print( f"  {overlap[ 'run_a' ]} -> {overlap[ 'run_b' ]}: "
                   f"{overlap[ 'agreement_a_to_b' ]}% | "
                   f"{overlap[ 'run_b' ]} -> {overlap[ 'run_a' ]}: "
                   f"{overlap[ 'agreement_b_to_a' ]}%" )

    logger.info( "Script 001 completed successfully" )


if __name__ == '__main__':
    main()
