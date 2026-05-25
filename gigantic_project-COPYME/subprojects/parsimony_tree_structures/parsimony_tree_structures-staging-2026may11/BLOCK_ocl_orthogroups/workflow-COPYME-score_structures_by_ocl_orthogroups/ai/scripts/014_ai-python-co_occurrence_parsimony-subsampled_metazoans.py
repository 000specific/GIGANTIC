#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Co-occurrence parsimony with subsampled metazoan clades (mirrors 013 but uses 4-species-per-metazoan-clade OTUs like script 011)
# Human: Eric Edsinger

"""
Script 014 -- Co-occurrence parsimony, subsampled-metazoans variant.

Same framework as script 013 (classical synapomorphy-based scoring: count
orthogroups whose exact presence subset matches each non-trivial monophyletic
clade of the candidate tree), but using the subsampled-metazoan OTU
partition from script 011:

  - Unicells: all pre-metazoan species (kept full size for anchoring)
  - Each metazoan clade: 4 species, chosen via user override
    (config.clade_binarization_subsampled.metazoan_subsample) or via the
    phyloname-max-distance / quality-tiebreak strategy (script 011 logic).

Same scoring + bootstrap framework as script 013. Output mirrors 13-output
structure with 14- prefix.
"""

import argparse
import itertools
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml


METAZOA_ROOT = 'C082_Metazoa'
DEFAULT_METAZOAN_LEAF_CLADES = [
    'C086_Ctenophora',
    'C090_Porifera',
    'C095_Placozoa',
    'C102_Cnidaria',
    'C103_Bilateria',
]
DEFAULT_UNICELLS_LABEL = 'Unicells'
OTU_VIRTUAL_ROOT = 'OTU_ROOT'
SHORT_LABELS = {
    'C086_Ctenophora': 'Cten',
    'C090_Porifera': 'Pori',
    'C095_Placozoa': 'Plac',
    'C102_Cnidaria': 'Cnid',
    'C103_Bilateria': 'Bila',
}
DEFAULT_SUBSAMPLE_COUNT = 4
DEFAULT_SUBSAMPLE_STRATEGY = 'phyloname_max_distance_quality_tiebreak'
PHYLONAME_TAXONOMIC_LEVELS = 6


def parse_header_to_index( header_line ):
    parts = header_line.rstrip( '\n' ).split( '\t' )
    return { p.split( ' ' )[ 0 ]: i for i, p in enumerate( parts ) }


def load_parent_child( parent_child_path ):
    parents_to_children = defaultdict( list )
    with open( parent_child_path ) as input_pc:
        header_line = input_pc.readline()
        columns_to_index = parse_header_to_index( header_line )
        index_parent = columns_to_index[ 'Parent_Clade_ID_Name' ]
        index_child = columns_to_index[ 'Child_Clade_ID_Name' ]
        for line in input_pc:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            parents_to_children[ parts[ index_parent ] ].append( parts[ index_child ] )
    return parents_to_children


def build_otu_tree( parents_to_children, metazoan_leaves, unicells_label ):
    otu_children = defaultdict( list )
    metazoan_leaves_set = set( metazoan_leaves )

    def add_metazoan_subtree( node ):
        if node in metazoan_leaves_set:
            return
        for child in parents_to_children.get( node, [] ):
            otu_children[ node ].append( child )
            add_metazoan_subtree( child )

    add_metazoan_subtree( METAZOA_ROOT )
    otu_children[ OTU_VIRTUAL_ROOT ] = [ unicells_label, METAZOA_ROOT ]
    all_leaves = { unicells_label } | metazoan_leaves_set
    return otu_children, all_leaves


def collect_clade_subsets( otu_children, all_leaves, root = OTU_VIRTUAL_ROOT ):
    subsets = []
    def visit( node ):
        if node in all_leaves:
            return { node }
        leaves = set()
        for child in otu_children.get( node, [] ):
            leaves |= visit( child )
        subsets.append( frozenset( leaves ) )
        return leaves
    visit( root )
    return subsets


def compute_per_structure_ranks( scores, ascending ):
    n = len( scores )
    if ascending:
        order = np.argsort( scores, kind = 'stable' )
    else:
        order = np.argsort( -scores, kind = 'stable' )
    ranks = np.empty( n, dtype = np.float32 )
    ranks[ order ] = np.arange( 1, n + 1, dtype = np.float32 )
    sorted_scores = scores[ order ]
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_scores[ j ] == sorted_scores[ i ]:
            j += 1
        if j - i > 1:
            avg = ( ranks[ order[ i ] ] + ranks[ order[ j - 1 ] ] ) / 2.0
            for k in range( i, j ):
                ranks[ order[ k ] ] = avg
        i = j
    return ranks


def phyloname_distance( tokens_a, tokens_b ):
    a = tokens_a[ :PHYLONAME_TAXONOMIC_LEVELS ]
    b = tokens_b[ :PHYLONAME_TAXONOMIC_LEVELS ]
    shared = 0
    for x, y in zip( a, b ):
        if x == y:
            shared += 1
        else:
            break
    return PHYLONAME_TAXONOMIC_LEVELS - shared


def greedy_farthest_point( species_in_clade, species_to_phyloname_tokens, species_to_quality, n ):
    species_list = list( species_in_clade )
    if len( species_list ) <= n:
        return species_list
    species_sorted_by_quality = sorted( species_list, key = lambda s: -species_to_quality.get( s, 0 ) )
    picked = [ species_sorted_by_quality[ 0 ] ]
    remaining = [ s for s in species_list if s != picked[ 0 ] ]
    while len( picked ) < n and remaining:
        best_candidate = None
        best_min_distance = -1
        best_quality = -1
        for candidate in remaining:
            tokens_c = species_to_phyloname_tokens.get( candidate, [ candidate ] )
            min_dist = min(
                phyloname_distance( tokens_c, species_to_phyloname_tokens.get( p, [ p ] ) )
                for p in picked
            )
            qual = species_to_quality.get( candidate, 0 )
            if ( min_dist > best_min_distance ) or ( min_dist == best_min_distance and qual > best_quality ):
                best_min_distance = min_dist
                best_candidate = candidate
                best_quality = qual
        picked.append( best_candidate )
        remaining.remove( best_candidate )
    return picked


def subsample_species( all_species_in_clade, requested_species, strategy, subsample_count, rng,
                        species_to_phyloname_tokens = None, species_to_quality = None ):
    sorted_pool = sorted( all_species_in_clade )
    if requested_species:
        unique = [ s for s in requested_species if s in all_species_in_clade ]
        return unique, f'user-supplied list of {len( unique )} species'
    if strategy == 'random_seeded':
        permuted = sorted_pool.copy()
        rng.shuffle( permuted )
        return permuted[ :subsample_count ], 'random_seeded'
    if strategy == 'phyloname_max_distance_quality_tiebreak' and species_to_phyloname_tokens and species_to_quality:
        picked = greedy_farthest_point( all_species_in_clade, species_to_phyloname_tokens, species_to_quality, subsample_count )
        return picked, 'phyloname_max_distance_quality_tiebreak'
    return sorted_pool[ :subsample_count ], 'first_alphabetical'


def main():
    parser = argparse.ArgumentParser( description = 'Co-occurrence parsimony with subsampled metazoans (014)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_14 = output_dir / '14-output'
    output_14.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_dir / '14_ai-log-co_occurrence_parsimony-subsampled.log' ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'co_occurrence_subsampled' )

    logger.info( 'Starting script 014: co-occurrence parsimony (subsampled metazoans)' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )

    ocl_orthogroups_dir = ( workflow_dir / config[ 'inputs' ][ 'ocl_orthogroups_dir' ] ).resolve()
    trees_species_dir = ( workflow_dir / config[ 'inputs' ][ 'trees_species_dir' ] ).resolve()
    structure_manifest_path = ( workflow_dir / config[ 'inputs' ][ 'structure_manifest' ] ).resolve()
    parent_child_dir = trees_species_dir / 'Species_Parent_Child_Relationships'
    clade_species_mapping_path = trees_species_dir / 'Species_Clade_Species_Mappings' / '9_ai-clade_species_mappings-all_structures.tsv'

    cb_sub_config = config.get( 'clade_binarization_subsampled', {} ) or {}
    metazoan_leaves = cb_sub_config.get( 'metazoan_clades', DEFAULT_METAZOAN_LEAF_CLADES )
    unicells_label = cb_sub_config.get( 'unicells_short_name', DEFAULT_UNICELLS_LABEL )
    subsample_count = int( cb_sub_config.get( 'subsample_count', DEFAULT_SUBSAMPLE_COUNT ) )
    subsample_strategy = cb_sub_config.get( 'subsample_strategy', DEFAULT_SUBSAMPLE_STRATEGY )
    subsample_seed = int( cb_sub_config.get( 'subsample_seed', 42 ) )
    user_subsample = cb_sub_config.get( 'metazoan_subsample', {} ) or {}
    phylonames_map_path = cb_sub_config.get(
        'phylonames_map_path',
        str( trees_species_dir.parent.parent.parent / 'phylonames' / 'output_to_input' / 'STEP_2-apply_user_phylonames' / 'maps' / 'species70_map-genus_species_X_phylonames.tsv' )
    )

    iterations = int( config.get( 'bootstrap', {} ).get( 'iterations', 1000 ) )
    seed = int( config.get( 'bootstrap', {} ).get( 'seed', 42 ) )

    filter_config = config.get( 'filter', {} ) or {}
    min_species_count = int( filter_config.get( 'min_species_count', 2 ) )
    max_species_count_raw = filter_config.get( 'max_species_count', None )
    max_species_count = int( max_species_count_raw ) if max_species_count_raw is not None else 10 ** 9
    logger.info( f'Filter: Species_Count in [{min_species_count}, {max_species_count}]' )
    logger.info( f'Subsample count per metazoan clade: {subsample_count}  strategy: {subsample_strategy}' )

    structure_ids = []
    with open( structure_manifest_path ) as input_manifest:
        input_manifest.readline()
        for line in input_manifest:
            line = line.strip()
            if line and not line.startswith( '#' ):
                structure_ids.append( line )

    # Load clade-species mapping
    clades_to_species = {}
    all_species = set()
    use_structure = 'structure_001'
    with open( clade_species_mapping_path ) as input_csm:
        header_line = input_csm.readline()
        columns_to_index = parse_header_to_index( header_line )
        idx_s = columns_to_index[ 'Structure_ID' ]
        idx_c = columns_to_index[ 'Clade_ID_Name' ]
        idx_sp = None
        for candidate in [ 'Descendant_Species_List', 'Species_List', 'Species_Names', 'Genus_Species_List' ]:
            if candidate in columns_to_index:
                idx_sp = columns_to_index[ candidate ]
                break
        for line in input_csm:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ idx_s ] != use_structure:
                continue
            clade_id = parts[ idx_c ]
            species_list = [ s.strip() for s in parts[ idx_sp ].split( ',' ) if s.strip() ]
            clades_to_species[ clade_id ] = species_list
            for s in species_list:
                all_species.add( s )

    # Load phylonames + compute quality (orthogroup count) per species
    species_to_phyloname_tokens = {}
    if Path( phylonames_map_path ).is_file():
        with open( phylonames_map_path ) as input_phy:
            header_line = input_phy.readline()
            columns_to_index = parse_header_to_index( header_line )
            idx_gs = columns_to_index.get( 'genus_species', 0 )
            idx_phy = columns_to_index.get( 'phyloname', 1 )
            for line in input_phy:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                species_to_phyloname_tokens[ parts[ idx_gs ] ] = parts[ idx_phy ].split( '_' )

    species_to_quality = defaultdict( int )
    structure_001_ocl_path = ocl_orthogroups_dir / 'structure_001' / '4_ai-orthogroups-complete_ocl_summary.tsv'
    if structure_001_ocl_path.is_file():
        with open( structure_001_ocl_path ) as input_ocl:
            header_line = input_ocl.readline()
            columns_to_index = parse_header_to_index( header_line )
            idx_sp_list = columns_to_index[ 'Species_List' ]
            idx_sc = columns_to_index[ 'Species_Count' ]
            for line in input_ocl:
                parts = line.rstrip( '\n' ).split( '\t' )
                sc = int( parts[ idx_sc ] )
                if sc < min_species_count or sc > max_species_count:
                    continue
                for species_name in parts[ idx_sp_list ].split( ',' ):
                    species_name = species_name.strip()
                    if species_name:
                        species_to_quality[ species_name ] += 1

    # Subsample metazoan clades
    rng_sub = np.random.default_rng( subsample_seed )
    metazoan_species_union_full = set()
    metazoan_species_sets = {}
    selection_notes = {}
    for clade_id in metazoan_leaves:
        full_pool = set( clades_to_species[ clade_id ] )
        metazoan_species_union_full |= full_pool
        requested = user_subsample.get( clade_id, [] )
        selected, note = subsample_species(
            full_pool, requested, subsample_strategy, subsample_count, rng_sub,
            species_to_phyloname_tokens = species_to_phyloname_tokens,
            species_to_quality = species_to_quality,
        )
        metazoan_species_sets[ clade_id ] = set( selected )
        selection_notes[ clade_id ] = note
        qsum = ', '.join( f'{s}(q={species_to_quality.get( s, 0 )})' for s in selected )
        logger.info( f'  {SHORT_LABELS.get( clade_id, clade_id )} ({clade_id}): pool={len( full_pool )} -> kept {len( selected )}: {qsum}' )

    unicells_species = all_species - metazoan_species_union_full
    logger.info( f'  {unicells_label}: {len( unicells_species )} species (kept full size for anchoring)' )

    partition_path = output_14 / '14_ai-otu_partition.tsv'
    with open( partition_path, 'w' ) as output:
        output.write( 'OTU_Short_Name\tClade_ID_Name\tSelection_Note\tSpecies_Count\tSpecies_List\n' )
        output.write( f'{unicells_label}\tvirtual_unicells_aggregate\tkept full size for anchoring\t{len( unicells_species )}\t{",".join( sorted( unicells_species ) )}\n' )
        for clade_id in metazoan_leaves:
            sp = sorted( metazoan_species_sets[ clade_id ] )
            output.write( f'{SHORT_LABELS.get( clade_id, clade_id )}\t{clade_id}\t{selection_notes[ clade_id ]}\t{len( sp )}\t{",".join( sp )}\n' )

    all_leaves = { unicells_label } | set( metazoan_leaves )
    n_leaves = len( all_leaves )

    # Build presence subset distribution using SUBSAMPLED metazoan species
    logger.info( 'Building presence subset distribution (subsampled metazoans)' )
    subset_to_count = defaultdict( int )
    filtered_count = 0
    with open( structure_001_ocl_path ) as input_ocl:
        header_line = input_ocl.readline()
        columns_to_index = parse_header_to_index( header_line )
        idx_sp_list = columns_to_index[ 'Species_List' ]
        idx_sc = columns_to_index[ 'Species_Count' ]
        for line in input_ocl:
            parts = line.rstrip( '\n' ).split( '\t' )
            sc = int( parts[ idx_sc ] )
            if not ( min_species_count <= sc <= max_species_count ):
                continue
            species_set = set( s.strip() for s in parts[ idx_sp_list ].split( ',' ) if s.strip() )
            presence = set()
            if species_set & unicells_species:
                presence.add( unicells_label )
            for clade_id in metazoan_leaves:
                if species_set & metazoan_species_sets[ clade_id ]:
                    presence.add( clade_id )
            subset_to_count[ frozenset( presence ) ] += 1
            filtered_count += 1
    logger.info( f'Filtered orthogroups: {filtered_count}  Distinct presence subsets: {len( subset_to_count )}' )

    output_dist = output_14 / '14_ai-presence_subset_distribution.tsv'
    with open( output_dist, 'w' ) as output:
        output.write( 'Presence_Subset\tSubset_Size\tOrthogroup_Count\n' )
        for subset, count in sorted( subset_to_count.items(), key = lambda kv: ( -kv[ 1 ], -len( kv[ 0 ] ) ) ):
            short_labels = sorted( SHORT_LABELS.get( s, s ) for s in subset )
            output.write( ','.join( short_labels ) + '\t' + str( len( subset ) ) + '\t' + str( count ) + '\n' )

    # Per-structure scoring
    n_structures = len( structure_ids )
    structure_scores = np.zeros( n_structures, dtype = np.int64 )
    per_structure_clades = []

    for structure_index, structure_id in enumerate( structure_ids ):
        parent_child_path = parent_child_dir / f'5_ai-structure_{structure_id}_parent_child_relationships.tsv'
        parents_to_children = load_parent_child( parent_child_path )
        otu_children, _ = build_otu_tree( parents_to_children, metazoan_leaves, unicells_label )
        all_subsets = collect_clade_subsets( otu_children, all_leaves )
        non_trivial = []
        seen = set()
        for s in all_subsets:
            if 2 <= len( s ) <= n_leaves - 1 and s not in seen:
                seen.add( s )
                non_trivial.append( s )
        per_structure_clades.append( non_trivial )
        structure_scores[ structure_index ] = sum( subset_to_count.get( clade, 0 ) for clade in non_trivial )

    # Pairwise synapomorphy table
    output_pair = output_14 / '14_ai-pairwise_synapomorphy_counts.tsv'
    with open( output_pair, 'w' ) as output:
        output.write( 'OTU_A_Short_Label\tOTU_B_Short_Label\tExact_Pair_OG_Count\n' )
        all_short_labels = sorted( [ unicells_label ] + [ SHORT_LABELS.get( c, c ) for c in metazoan_leaves ] )
        reverse_labels = { unicells_label: unicells_label }
        for c in metazoan_leaves:
            reverse_labels[ SHORT_LABELS.get( c, c ) ] = c
        for a, b in itertools.combinations( all_short_labels, 2 ):
            pair_subset = frozenset( { reverse_labels[ a ], reverse_labels[ b ] } )
            output.write( a + '\t' + b + '\t' + str( subset_to_count.get( pair_subset, 0 ) ) + '\n' )

    # Bootstrap
    logger.info( f'Running bootstrap: iterations={iterations} seed={seed}' )
    subset_list = sorted( subset_to_count.keys(), key = lambda s: -subset_to_count[ s ] )
    subset_to_index = { s: i for i, s in enumerate( subset_list ) }
    n_subsets = len( subset_list )
    n_filtered_total = sum( subset_to_count.values() )

    og_subset_index = np.zeros( n_filtered_total, dtype = np.int32 )
    pos = 0
    for s, c in subset_to_count.items():
        og_subset_index[ pos : pos + c ] = subset_to_index[ s ]
        pos += c

    structure_subset_masks = np.zeros( ( n_structures, n_subsets ), dtype = np.uint8 )
    for structure_index, non_trivial in enumerate( per_structure_clades ):
        for s in non_trivial:
            if s in subset_to_index:
                structure_subset_masks[ structure_index, subset_to_index[ s ] ] = 1

    rng = np.random.default_rng( seed )
    rank_records = np.zeros( ( iterations, n_structures ), dtype = np.float32 )
    best_counts = np.zeros( n_structures, dtype = np.int64 )

    for iteration in range( iterations ):
        sampled = rng.integers( 0, n_filtered_total, n_filtered_total )
        subset_counts_this_iter = np.bincount( og_subset_index[ sampled ], minlength = n_subsets )
        scores_iter = structure_subset_masks @ subset_counts_this_iter
        rank_records[ iteration ] = compute_per_structure_ranks( scores_iter.astype( np.float64 ), ascending = False )
        max_score = scores_iter.max()
        for s_idx in range( n_structures ):
            if scores_iter[ s_idx ] == max_score:
                best_counts[ s_idx ] += 1

    mean_rank = rank_records.mean( axis = 0 )
    ci_lower = np.percentile( rank_records, 2.5, axis = 0 )
    ci_upper = np.percentile( rank_records, 97.5, axis = 0 )
    pct_best = 100.0 * best_counts / iterations
    final_ranks = compute_per_structure_ranks( structure_scores.astype( np.float64 ), ascending = False )

    # Compare with 005 ranks + 013 ranks
    ranking_005_path = output_dir / '5-output' / '5_ai-parsimony_ranking-structures.tsv'
    loss_min_ranks = {}
    depth_ranks = {}
    if ranking_005_path.is_file():
        with open( ranking_005_path ) as input_ranking:
            header_line = input_ranking.readline()
            cols = parse_header_to_index( header_line )
            for line in input_ranking:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                loss_min_ranks[ parts[ cols[ 'Structure_ID' ] ] ] = float( parts[ cols[ 'Final_Rank_Losses' ] ] )
                depth_ranks[ parts[ cols[ 'Structure_ID' ] ] ] = float( parts[ cols[ 'Final_Rank_Depth' ] ] )

    ranking_013_path = output_dir / '13-output' / '13_ai-co_occurrence_ranking-structures.tsv'
    cooccur_unsubsampled_ranks = {}
    if ranking_013_path.is_file():
        with open( ranking_013_path ) as input_013:
            header_line = input_013.readline()
            cols = parse_header_to_index( header_line )
            for line in input_013:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                cooccur_unsubsampled_ranks[ parts[ cols[ 'Structure_ID' ] ] ] = float( parts[ cols[ 'Final_Rank_Co_Occurrence' ] ] )

    output_ranking = output_14 / '14_ai-co_occurrence_ranking-structures.tsv'
    with open( output_ranking, 'w' ) as output:
        output.write( 'Final_Rank_Co_Occurrence_Subsampled\tStructure_ID\tCo_Occurrence_Score_Subsampled\t' )
        output.write( 'Bootstrap_Mean_Rank\tBootstrap_Rank_CI_Lower_95\tBootstrap_Rank_CI_Upper_95\tBootstrap_Pct_Times_Best\tBootstrap_Iterations\t' )
        output.write( 'Final_Rank_Co_Occurrence_From_013_All_Species\tFinal_Rank_Losses_From_005\tFinal_Rank_Depth_From_005\t' )
        output.write( 'Non_Trivial_Clades\n' )
        for idx in np.argsort( final_ranks, kind = 'stable' ):
            sid = structure_ids[ idx ]
            clades_short = [ '|'.join( sorted( SHORT_LABELS.get( s, s ) for s in clade ) ) for clade in per_structure_clades[ idx ] ]
            output.write(
                f'{final_ranks[ idx ]:.1f}\t{sid}\t{structure_scores[ idx ]}\t'
                f'{mean_rank[ idx ]:.4f}\t{ci_lower[ idx ]:.4f}\t{ci_upper[ idx ]:.4f}\t{pct_best[ idx ]:.4f}\t{iterations}\t'
                f'{cooccur_unsubsampled_ranks.get( sid, float( "nan" ) ):.1f}\t'
                f'{loss_min_ranks.get( sid, float( "nan" ) ):.1f}\t{depth_ranks.get( sid, float( "nan" ) ):.1f}\t'
                f'{",".join( clades_short )}\n'
            )

    output_summary = output_14 / '14_ai-summary.txt'
    with open( output_summary, 'w' ) as output:
        output.write( '# parsimony_tree_structures BLOCK_ocl_orthogroups -- co-occurrence parsimony (SUBSAMPLED metazoans)\n' )
        output.write( f'# run_label: {config.get( "run_label", "UNSPECIFIED" )}\n' )
        output.write( '\n' )
        output.write( '## OTU selection per metazoan clade\n' )
        for clade_id in metazoan_leaves:
            output.write( f'{SHORT_LABELS.get( clade_id, clade_id )}\t{",".join( sorted( metazoan_species_sets[ clade_id ] ) )}\n' )
        output.write( f'Unicells\tall {len( unicells_species )} pre-metazoan species\n' )
        output.write( '\n' )
        output.write( f'Filtered_Orthogroups_Total\t{filtered_count}\n' )
        output.write( f'Distinct_Presence_Subsets_Observed\t{len( subset_to_count )}\n' )
        output.write( '\n' )
        output.write( '## Top 10 by Co_Occurrence_Score_Subsampled\n' )
        output.write( 'Final_Rank_Co_Occurrence_Subsampled\tStructure_ID\tCo_Occurrence_Score_Subsampled\tBootstrap_Pct_Times_Best\tFinal_Rank_Co_Occurrence_From_013\tFinal_Rank_Losses_005\tFinal_Rank_Depth_005\n' )
        for idx in np.argsort( -structure_scores, kind = 'stable' )[ :10 ]:
            sid = structure_ids[ idx ]
            output.write(
                f'{final_ranks[ idx ]:.1f}\t{sid}\t{structure_scores[ idx ]}\t{pct_best[ idx ]:.4f}\t'
                f'{cooccur_unsubsampled_ranks.get( sid, float( "nan" ) ):.1f}\t'
                f'{loss_min_ranks.get( sid, float( "nan" ) ):.1f}\t{depth_ranks.get( sid, float( "nan" ) ):.1f}\n'
            )
        output.write( '\n' )
        output.write( '## Top 10 most-supported presence subsets (subsampled)\n' )
        output.write( 'Presence_Subset\tSubset_Size\tOrthogroup_Count\n' )
        for subset, count in sorted( subset_to_count.items(), key = lambda kv: -kv[ 1 ] )[ :10 ]:
            short_labels = sorted( SHORT_LABELS.get( s, s ) for s in subset )
            output.write( ','.join( short_labels ) + '\t' + str( len( subset ) ) + '\t' + str( count ) + '\n' )

    top_idx = int( np.argmax( structure_scores ) )
    logger.info( f'Best by co-occurrence (subsampled): structure_{structure_ids[ top_idx ]} (score={structure_scores[ top_idx ]}, pct_best={pct_best[ top_idx ]:.2f}%)' )


if __name__ == '__main__':
    main()
