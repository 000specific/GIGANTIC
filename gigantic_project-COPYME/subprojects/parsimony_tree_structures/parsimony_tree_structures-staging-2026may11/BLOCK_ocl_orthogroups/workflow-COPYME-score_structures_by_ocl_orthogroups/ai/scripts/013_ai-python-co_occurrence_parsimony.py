#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Co-occurrence parsimony at the 6-OTU level -- classical synapomorphy-based scoring (count OGs whose presence set exactly matches each non-trivial monophyletic clade of the candidate tree)
# Human: Eric Edsinger

"""
Script 013 -- Co-occurrence parsimony (synapomorphy-based).

Reuses the 6-OTU partition from script 010 (Unicells + 5 metazoan clades,
all species per OTU). For each filtered orthogroup, computes its 6-bit
presence vector and counts orthogroups by exact presence subset.

For each candidate species tree structure:
  - Build the 6-OTU tree from the structure's parent-child table
  - Enumerate non-trivial monophyletic clades (size 2 to N-1; leaves and the
    full set are excluded)
  - Score = sum over non-trivial clades C of count_of_OGs_with_presence_exactly_equal_to_C
  - Higher score = more orthogroup presence patterns align with the tree's
    clades = more synapomorphy support

This is a discrete-state, classical-cladistics formulation of parsimony,
distinct in math from the per-OG MRCA-based scoring used by scripts 002-005,
010, 011. It rewards trees whose internal clades correspond to ACTUAL
observed presence patterns (exact match), not just MRCA placements.

Outputs in 13-output/:
  13_ai-presence_subset_distribution.tsv     (count of OGs per exact presence subset)
  13_ai-co_occurrence_ranking-structures.tsv (per-structure synapomorphy score + bootstrap)
  13_ai-pairwise_synapomorphy_counts.tsv     (pair-level synapomorphy table for diagnostics)
  13_ai-summary.txt                          (top-line stats)
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
    """Return list of frozensets, one per internal node (the leaves below it).
    Includes root (full set) and all internal nodes. Caller filters trivial ones."""
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


def main():
    parser = argparse.ArgumentParser( description = 'Co-occurrence parsimony at 6-OTU level' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_13 = output_dir / '13-output'
    output_13.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_dir / '13_ai-log-co_occurrence_parsimony.log' ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'co_occurrence' )

    logger.info( 'Starting script 013: co-occurrence parsimony (synapomorphy-based)' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )

    ocl_orthogroups_dir = ( workflow_dir / config[ 'inputs' ][ 'ocl_orthogroups_dir' ] ).resolve()
    trees_species_dir = ( workflow_dir / config[ 'inputs' ][ 'trees_species_dir' ] ).resolve()
    structure_manifest_path = ( workflow_dir / config[ 'inputs' ][ 'structure_manifest' ] ).resolve()
    parent_child_dir = trees_species_dir / 'Species_Parent_Child_Relationships'
    clade_species_mapping_path = trees_species_dir / 'Species_Clade_Species_Mappings' / '9_ai-clade_species_mappings-all_structures.tsv'

    cb_config = config.get( 'clade_binarization', {} ) or {}
    metazoan_leaves = cb_config.get( 'metazoan_clades', DEFAULT_METAZOAN_LEAF_CLADES )
    unicells_label = cb_config.get( 'unicells_short_name', DEFAULT_UNICELLS_LABEL )

    iterations = int( config.get( 'bootstrap', {} ).get( 'iterations', 1000 ) )
    seed = int( config.get( 'bootstrap', {} ).get( 'seed', 42 ) )

    filter_config = config.get( 'filter', {} ) or {}
    min_species_count = int( filter_config.get( 'min_species_count', 2 ) )
    max_species_count_raw = filter_config.get( 'max_species_count', None )
    max_species_count = int( max_species_count_raw ) if max_species_count_raw is not None else 10 ** 9
    logger.info( f'Filter: Species_Count in [{min_species_count}, {max_species_count}]' )

    structure_ids = []
    with open( structure_manifest_path ) as input_manifest:
        input_manifest.readline()
        for line in input_manifest:
            line = line.strip()
            if line and not line.startswith( '#' ):
                structure_ids.append( line )

    # Load 6-OTU partition (same logic as script 010)
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
        if idx_sp is None:
            logger.error( 'CRITICAL: no recognized species-list column' )
            sys.exit( 1 )
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

    metazoan_species_union = set()
    metazoan_species_sets = {}
    for clade_id in metazoan_leaves:
        if clade_id not in clades_to_species:
            logger.error( f'CRITICAL: metazoan clade {clade_id} not in clade-species mapping' )
            sys.exit( 1 )
        metazoan_species_sets[ clade_id ] = set( clades_to_species[ clade_id ] )
        metazoan_species_union |= metazoan_species_sets[ clade_id ]
    unicells_species = all_species - metazoan_species_union

    logger.info(
        f'OTU partition: {unicells_label}={len( unicells_species )}, '
        + ', '.join( f'{SHORT_LABELS.get( c, c )}={len( metazoan_species_sets[ c ] )}' for c in metazoan_leaves )
    )

    all_leaves = { unicells_label } | set( metazoan_leaves )
    n_leaves = len( all_leaves )

    # Build per-OG 6-bit presence vector by reading any single structure's OCL (orthogroup-species memberships are tree-invariant)
    logger.info( 'Building presence subset distribution from structure_001 OCL (memberships are tree-invariant)' )
    ocl_path_for_presence = ocl_orthogroups_dir / 'structure_001' / '4_ai-orthogroups-complete_ocl_summary.tsv'
    subset_to_count = defaultdict( int )
    filtered_count = 0
    with open( ocl_path_for_presence ) as input_ocl:
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
    logger.info( f'Filtered orthogroups indexed: {filtered_count}' )
    logger.info( f'Distinct presence subsets observed: {len( subset_to_count )}' )

    # Write presence subset distribution (sorted by count desc)
    output_dist = output_13 / '13_ai-presence_subset_distribution.tsv'
    with open( output_dist, 'w' ) as output:
        output.write( 'Presence_Subset (comma delimited short labels of OTUs in which this orthogroup is present)' )
        output.write( '\tSubset_Size (number of OTUs in the presence subset)' )
        output.write( '\tOrthogroup_Count (number of filtered orthogroups with exactly this presence pattern)\n' )
        ordered = sorted( subset_to_count.items(), key = lambda kv: ( -kv[ 1 ], -len( kv[ 0 ] ) ) )
        for subset, count in ordered:
            short_labels = sorted( SHORT_LABELS.get( s, s ) for s in subset )
            output.write( ','.join( short_labels ) + '\t' + str( len( subset ) ) + '\t' + str( count ) + '\n' )
    logger.info( f'Wrote subset distribution: {output_dist}' )

    # Per-structure scoring
    logger.info( 'Scoring each structure by synapomorphy support' )
    n_structures = len( structure_ids )
    structure_scores = np.zeros( n_structures, dtype = np.int64 )
    per_structure_clades = []  # list of lists of frozensets

    for structure_index, structure_id in enumerate( structure_ids ):
        parent_child_path = parent_child_dir / f'5_ai-structure_{structure_id}_parent_child_relationships.tsv'
        parents_to_children = load_parent_child( parent_child_path )
        otu_children, _ = build_otu_tree( parents_to_children, metazoan_leaves, unicells_label )
        all_subsets = collect_clade_subsets( otu_children, all_leaves )
        # Non-trivial: size in [2, n_leaves - 1]; also exclude duplicates
        non_trivial = []
        seen = set()
        for s in all_subsets:
            if 2 <= len( s ) <= n_leaves - 1 and s not in seen:
                seen.add( s )
                non_trivial.append( s )
        per_structure_clades.append( non_trivial )
        score = 0
        for clade in non_trivial:
            score += subset_to_count.get( clade, 0 )
        structure_scores[ structure_index ] = score

    # Pairwise synapomorphy table
    output_pair = output_13 / '13_ai-pairwise_synapomorphy_counts.tsv'
    with open( output_pair, 'w' ) as output:
        output.write( 'OTU_A_Short_Label (first OTU in pair)' )
        output.write( '\tOTU_B_Short_Label (second OTU in pair)' )
        output.write( '\tExact_Pair_OG_Count (orthogroups present in exactly this pair of OTUs and absent from all others)\n' )
        all_short_labels = sorted( [ unicells_label ] + [ SHORT_LABELS.get( c, c ) for c in metazoan_leaves ] )
        reverse_labels = { unicells_label: unicells_label }
        for c in metazoan_leaves:
            reverse_labels[ SHORT_LABELS.get( c, c ) ] = c
        for a, b in itertools.combinations( all_short_labels, 2 ):
            full_a = reverse_labels[ a ]
            full_b = reverse_labels[ b ]
            pair_subset = frozenset( { full_a, full_b } )
            output.write( a + '\t' + b + '\t' + str( subset_to_count.get( pair_subset, 0 ) ) + '\n' )
    logger.info( f'Wrote pairwise synapomorphy counts: {output_pair}' )

    # Bootstrap (resample over orthogroups)
    logger.info( f'Running bootstrap: iterations={iterations} seed={seed}' )
    # Build OG-indexed presence array for bootstrap: each row = a filtered OG, frozenset key
    # For memory efficiency, store as list of indices into a sorted subset list
    subset_list = sorted( subset_to_count.keys(), key = lambda s: -subset_to_count[ s ] )
    subset_to_index = { s: i for i, s in enumerate( subset_list ) }
    n_subsets = len( subset_list )
    n_filtered_total = sum( subset_to_count.values() )

    # Expand to OG-indexed array
    og_subset_index = np.zeros( n_filtered_total, dtype = np.int32 )
    pos = 0
    for s, c in subset_to_count.items():
        og_subset_index[ pos : pos + c ] = subset_to_index[ s ]
        pos += c

    # Per-structure: bitmask of which subset indices are in its non-trivial clades
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
        sampled_subset_indices = og_subset_index[ sampled ]
        # Tally counts per subset
        subset_counts_this_iter = np.bincount( sampled_subset_indices, minlength = n_subsets )
        # Score each structure
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

    # Cross-comparison with script 005 ranks
    ranking_path = output_dir / '5-output' / '5_ai-parsimony_ranking-structures.tsv'
    loss_min_ranks = {}
    depth_ranks = {}
    if ranking_path.is_file():
        with open( ranking_path ) as input_ranking:
            header_line = input_ranking.readline()
            cols = parse_header_to_index( header_line )
            for line in input_ranking:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                loss_min_ranks[ parts[ cols[ 'Structure_ID' ] ] ] = float( parts[ cols[ 'Final_Rank_Losses' ] ] )
                depth_ranks[ parts[ cols[ 'Structure_ID' ] ] ] = float( parts[ cols[ 'Final_Rank_Depth' ] ] )

    output_ranking = output_13 / '13_ai-co_occurrence_ranking-structures.tsv'
    with open( output_ranking, 'w' ) as output:
        output.write( 'Final_Rank_Co_Occurrence (rank descending by synapomorphy support score; 1 is best)' )
        output.write( '\tStructure_ID (three digit identifier)' )
        output.write( '\tCo_Occurrence_Score (sum of OG counts whose exact presence subset equals one of the structures non trivial clades)' )
        output.write( '\tBootstrap_Mean_Rank (mean rank across bootstrap iterations)' )
        output.write( '\tBootstrap_Rank_CI_Lower_95 (2.5 percentile)' )
        output.write( '\tBootstrap_Rank_CI_Upper_95 (97.5 percentile)' )
        output.write( '\tBootstrap_Pct_Times_Best (percent of iterations winning)' )
        output.write( '\tBootstrap_Iterations (total iterations)' )
        output.write( '\tFinal_Rank_Losses_From_005 (loss minimization rank from script 005)' )
        output.write( '\tFinal_Rank_Depth_From_005 (shallow gain rank from script 005)' )
        output.write( '\tNon_Trivial_Clades_In_Structure (comma delimited short label sets for the structures non trivial monophyletic clades)\n' )
        for idx in np.argsort( final_ranks, kind = 'stable' ):
            sid = structure_ids[ idx ]
            clades_short = []
            for clade in per_structure_clades[ idx ]:
                short_set = sorted( SHORT_LABELS.get( s, s ) for s in clade )
                clades_short.append( '|'.join( short_set ) )
            clades_repr = ','.join( clades_short )
            output.write(
                f'{final_ranks[ idx ]:.1f}\t{sid}\t{structure_scores[ idx ]}\t'
                f'{mean_rank[ idx ]:.4f}\t{ci_lower[ idx ]:.4f}\t{ci_upper[ idx ]:.4f}\t{pct_best[ idx ]:.4f}\t{iterations}\t'
                f'{loss_min_ranks.get( sid, float( "nan" ) ):.1f}\t{depth_ranks.get( sid, float( "nan" ) ):.1f}\t{clades_repr}\n'
            )
    logger.info( f'Wrote co-occurrence ranking: {output_ranking}' )

    output_summary = output_13 / '13_ai-summary.txt'
    with open( output_summary, 'w' ) as output:
        output.write( '# parsimony_tree_structures BLOCK_ocl_orthogroups -- co-occurrence parsimony (synapomorphy-based)\n' )
        output.write( f'# run_label: {config.get( "run_label", "UNSPECIFIED" )}\n' )
        output.write( '\n' )
        output.write( f'Filtered_Orthogroups_Total\t{filtered_count}\n' )
        output.write( f'Distinct_Presence_Subsets_Observed\t{len( subset_to_count )}\n' )
        output.write( '\n' )
        output.write( '## Top 10 by Co_Occurrence_Score\n' )
        output.write( 'Final_Rank_Co_Occurrence\tStructure_ID\tCo_Occurrence_Score\tBootstrap_Pct_Times_Best\tFinal_Rank_Losses_005\tFinal_Rank_Depth_005\n' )
        for idx in np.argsort( -structure_scores, kind = 'stable' )[ :10 ]:
            sid = structure_ids[ idx ]
            output.write(
                f'{final_ranks[ idx ]:.1f}\t{sid}\t{structure_scores[ idx ]}\t{pct_best[ idx ]:.4f}\t'
                f'{loss_min_ranks.get( sid, float( "nan" ) ):.1f}\t{depth_ranks.get( sid, float( "nan" ) ):.1f}\n'
            )
        output.write( '\n' )
        output.write( '## Top 10 most-supported presence subsets (largest OG counts)\n' )
        output.write( 'Presence_Subset\tSubset_Size\tOrthogroup_Count\n' )
        ordered = sorted( subset_to_count.items(), key = lambda kv: -kv[ 1 ] )[ :10 ]
        for subset, count in ordered:
            short_labels = sorted( SHORT_LABELS.get( s, s ) for s in subset )
            output.write( ','.join( short_labels ) + '\t' + str( len( subset ) ) + '\t' + str( count ) + '\n' )
    logger.info( f'Wrote summary: {output_summary}' )

    top_idx = int( np.argmax( structure_scores ) )
    logger.info( f'Best by co-occurrence: structure_{structure_ids[ top_idx ]} (score={structure_scores[ top_idx ]}, pct_best_bootstrap={pct_best[ top_idx ]:.2f}%)' )


if __name__ == '__main__':
    main()
