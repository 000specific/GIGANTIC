#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Clade-binarized parsimony with subsampled metazoan clades (4 species each), Unicells outgroup kept large for anchoring
# Human: Eric Edsinger

"""
Script 011 -- Clade-binarized parsimony with leveled metazoan sampling.

Same framework as script 010 (6-OTU partition: Unicells + 5 metazoan clades,
binarized presence per OTU, scored at clade level on the OTU tree), but with
each metazoan clade subsampled to N species (default 4) to equalize sampling
across clades.

Why level only the metazoan clades:
  - Across the 105 structures, the topology variation is entirely within the
    metazoan unresolved zone. Even sampling per metazoan clade removes the
    clade-size bias (e.g., 35 Bilateria species vs 4 Placozoa species) at
    the detection-probability level.
  - Unicells is kept LARGE because ancient lineages have undergone the most
    divergence (loss + sequence drift); a small outgroup would systematically
    miss orthogroups that should anchor at the root.

Species selection per metazoan clade:
  - Config-driven (see `clade_binarization_subsampled.metazoan_subsample`).
  - Default selection strategy: 'first_alphabetical' picks the first N species
    alphabetically per clade. User should override with specific species for
    breadth and quality.

Outputs in 11-output/:
  11_ai-otu_partition.tsv                          (debug: subsampled species per OTU)
  11_ai-clade_binarized_aggregate-per_structure.tsv
  11_ai-clade_binarized_ranking-structures.tsv
"""

import argparse
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
DEFAULT_SUBSAMPLE_COUNT = 4
DEFAULT_SUBSAMPLE_STRATEGY = 'phyloname_max_distance_quality_tiebreak'
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

    depth_map = { OTU_VIRTUAL_ROOT: 0 }
    queue = [ OTU_VIRTUAL_ROOT ]
    while queue:
        next_queue = []
        for parent in queue:
            for child in otu_children.get( parent, [] ):
                if child not in depth_map:
                    depth_map[ child ] = depth_map[ parent ] + 1
                    next_queue.append( child )
        queue = next_queue

    all_leaves = { unicells_label } | metazoan_leaves_set
    return otu_children, depth_map, all_leaves


def compute_mrca_and_losses( presence_vector, otu_children, all_leaves ):
    cache = {}

    def has_presence( node ):
        if node in cache:
            return cache[ node ]
        if node in all_leaves:
            result = presence_vector.get( node, 0 ) == 1
        else:
            children = otu_children.get( node, [] )
            result = any( has_presence( c ) for c in children )
        cache[ node ] = result
        return result

    if not has_presence( OTU_VIRTUAL_ROOT ):
        return None, 0

    current = OTU_VIRTUAL_ROOT
    while True:
        children = otu_children.get( current, [] )
        if not children:
            break
        present_children = [ c for c in children if has_presence( c ) ]
        if len( present_children ) == 1:
            current = present_children[ 0 ]
        else:
            break
    mrca = current

    losses = 0
    def walk_for_losses( node ):
        nonlocal losses
        for child in otu_children.get( node, [] ):
            if has_presence( child ):
                walk_for_losses( child )
            else:
                losses += 1
    walk_for_losses( mrca )

    return mrca, losses


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


PHYLONAME_TAXONOMIC_LEVELS = 6  # Kingdom_Phylum_Class_Order_Family_Genus (positions 0-5); 6+ is species name


def phyloname_distance( tokens_a, tokens_b ):
    """Number of taxonomic levels (Kingdom..Genus) until two phylonames diverge.

    Only the first PHYLONAME_TAXONOMIC_LEVELS positions are compared so that
    multi-token species names (e.g., 'sp_m_RMFG_2023') don't inflate distance.
    distance = PHYLONAME_TAXONOMIC_LEVELS - length of common prefix."""
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
    """Pick n species maximizing min pairwise phyloname distance; tiebreak by quality.
    Seed = highest-quality species. Iteratively add the species whose minimum distance
    to already-picked set is maximized; quality breaks ties."""
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
    """Return a list of `subsample_count` species for this clade.

    Priority:
      1. If `requested_species` is non-empty, use it verbatim (validated against
         the clade pool). If len != subsample_count, warn but use what is given.
      2. Else apply `strategy`:
         - 'first_alphabetical' (default): sort alphabetically, take first N
         - 'random_seeded': shuffle with rng, take first N
         - 'phyloname_max_distance_quality_tiebreak': greedy farthest-point on
           phyloname tokens; quality (orthogroup count) breaks distance ties.
           Requires species_to_phyloname_tokens and species_to_quality.
    """
    sorted_pool = sorted( all_species_in_clade )
    if requested_species:
        unique = [ s for s in requested_species if s in all_species_in_clade ]
        if len( unique ) != len( requested_species ):
            invalid = [ s for s in requested_species if s not in all_species_in_clade ]
            return unique, f'user list contained {len( invalid )} unknown species; kept valid: {unique}'
        return unique, f'user-supplied list of {len( unique )} species'
    if strategy == 'random_seeded':
        permuted = sorted_pool.copy()
        rng.shuffle( permuted )
        return permuted[ :subsample_count ], 'random_seeded (strategy)'
    if strategy == 'phyloname_max_distance_quality_tiebreak':
        if species_to_phyloname_tokens is None or species_to_quality is None:
            return sorted_pool[ :subsample_count ], 'phyloname strategy requested but data missing; fell back to first_alphabetical'
        picked = greedy_farthest_point( all_species_in_clade, species_to_phyloname_tokens, species_to_quality, subsample_count )
        return picked, 'phyloname_max_distance_quality_tiebreak (greedy farthest-point with quality tiebreak; quality = orthogroup count from filtered OCL set)'
    return sorted_pool[ :subsample_count ], 'first_alphabetical (default strategy)'


def main():
    parser = argparse.ArgumentParser( description = 'Clade-binarized parsimony with subsampled metazoans (4 per clade)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_11 = output_dir / '11-output'
    output_11.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_dir / '11_ai-log-clade_binarized_parsimony-subsampled.log' ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'clade_binarized_subsampled' )

    logger.info( 'Starting script 011: clade-binarized parsimony with subsampled metazoans' )

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

    iterations = int( config.get( 'bootstrap', {} ).get( 'iterations', 1000 ) )
    seed = int( config.get( 'bootstrap', {} ).get( 'seed', 42 ) )

    filter_config = config.get( 'filter', {} ) or {}
    min_species_count = int( filter_config.get( 'min_species_count', 2 ) )
    max_species_count_raw = filter_config.get( 'max_species_count', None )
    max_species_count = int( max_species_count_raw ) if max_species_count_raw is not None else 10 ** 9
    logger.info( f'Filter: Species_Count in [{min_species_count}, {max_species_count}]' )
    logger.info( f'Subsample count per metazoan clade: {subsample_count}  strategy: {subsample_strategy}  seed: {subsample_seed}' )

    structure_ids = []
    with open( structure_manifest_path ) as input_manifest:
        input_manifest.readline()
        for line in input_manifest:
            line = line.strip()
            if line and not line.startswith( '#' ):
                structure_ids.append( line )

    # Load clade-species mapping (any structure suffices)
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
            logger.error( f'CRITICAL: no recognized species-list column in {clade_species_mapping_path}' )
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

    # Load phyloname tokens per species (for phyloname-max-distance strategy)
    phylonames_map_path = cb_sub_config.get(
        'phylonames_map_path',
        str( trees_species_dir.parent.parent.parent / 'phylonames' / 'output_to_input' / 'STEP_2-apply_user_phylonames' / 'maps' / 'species70_map-genus_species_X_phylonames.tsv' )
    )
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
                if len( parts ) <= max( idx_gs, idx_phy ):
                    continue
                species_to_phyloname_tokens[ parts[ idx_gs ] ] = parts[ idx_phy ].split( '_' )
        logger.info( f'Loaded phylonames for {len( species_to_phyloname_tokens )} species from {phylonames_map_path}' )
    else:
        logger.warning( f'Phyloname map not found at {phylonames_map_path}; phyloname-distance strategy will fall back to first_alphabetical' )

    # Compute per-species orthogroup count from structure_001 OCL (orthogroup-species memberships are tree-invariant)
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
        logger.info( f'Computed orthogroup-count quality scores for {len( species_to_quality )} species' )
    else:
        logger.warning( f'Cannot compute quality scores (structure_001 OCL missing); strategies needing quality will use 0 tiebreak' )

    # Subsample metazoan clades
    rng_subsample = np.random.default_rng( subsample_seed )
    metazoan_species_union_full = set()
    metazoan_species_sets = {}
    selection_notes = {}
    for clade_id in metazoan_leaves:
        if clade_id not in clades_to_species:
            logger.error( f'CRITICAL: metazoan clade {clade_id} missing from clade-species mapping' )
            sys.exit( 1 )
        full_pool = set( clades_to_species[ clade_id ] )
        metazoan_species_union_full |= full_pool
        requested = user_subsample.get( clade_id, [] )
        selected, note = subsample_species(
            full_pool, requested, subsample_strategy, subsample_count, rng_subsample,
            species_to_phyloname_tokens = species_to_phyloname_tokens,
            species_to_quality = species_to_quality,
        )
        metazoan_species_sets[ clade_id ] = set( selected )
        selection_notes[ clade_id ] = note
        quality_summary = ', '.join( f'{s}(q={species_to_quality.get( s, 0 )})' for s in selected )
        logger.info( f'  {SHORT_LABELS.get( clade_id, clade_id )} ({clade_id}): pool={len( full_pool )} -> kept {len( selected )}: {quality_summary}' )

    # Unicells = all species not in any of the FULL metazoan pools (not subsampled)
    unicells_species = all_species - metazoan_species_union_full
    logger.info( f'  {unicells_label}: {len( unicells_species )} species (kept full size for anchoring)' )

    partition_path = output_11 / '11_ai-otu_partition.tsv'
    with open( partition_path, 'w' ) as output:
        output.write( 'OTU_Short_Name (short label used in scoring)' )
        output.write( '\tClade_ID_Name (canonical GIGANTIC clade identifier or virtual aggregate name)' )
        output.write( '\tSelection_Note (how species were chosen for this OTU)' )
        output.write( '\tSpecies_Count (number of species retained in this OTU after subsampling)' )
        output.write( '\tSpecies_List (comma delimited list of species retained)\n' )
        output.write( f'{unicells_label}\tvirtual_unicells_aggregate\tkept full size for anchoring\t{len( unicells_species )}\t{",".join( sorted( unicells_species ) )}\n' )
        for clade_id in metazoan_leaves:
            sp = sorted( metazoan_species_sets[ clade_id ] )
            output.write( f'{SHORT_LABELS.get( clade_id, clade_id )}\t{clade_id}\t{selection_notes[ clade_id ]}\t{len( sp )}\t{",".join( sp )}\n' )
    logger.info( f'Wrote OTU partition: {partition_path}' )

    all_leaves = { unicells_label } | set( metazoan_leaves )

    n_structures = len( structure_ids )
    canonical_orthogroup_ids = None
    species_counts_canonical = None
    losses_matrix = None
    depth_matrix = None
    structure_aggregate_rows = []

    for structure_index, structure_id in enumerate( structure_ids ):
        parent_child_path = parent_child_dir / f'5_ai-structure_{structure_id}_parent_child_relationships.tsv'
        parents_to_children = load_parent_child( parent_child_path )
        otu_children, depth_map, _ = build_otu_tree( parents_to_children, metazoan_leaves, unicells_label )

        ocl_path = ocl_orthogroups_dir / f'structure_{structure_id}' / '4_ai-orthogroups-complete_ocl_summary.tsv'
        orthogroup_ids_this = []
        species_counts_this = []
        clade_losses_this = []
        clade_depths_this = []

        total_clade_losses = 0
        total_clade_depth = 0
        filtered_total_clade_losses = 0
        filtered_total_clade_depth = 0
        filtered_count = 0

        with open( ocl_path ) as input_ocl:
            header_line = input_ocl.readline()
            columns_to_index = parse_header_to_index( header_line )
            idx_og = columns_to_index[ 'Orthogroup_ID' ]
            idx_sp_list = columns_to_index[ 'Species_List' ]
            idx_sc = columns_to_index[ 'Species_Count' ]

            for line in input_ocl:
                parts = line.rstrip( '\n' ).split( '\t' )
                og_id = parts[ idx_og ]
                species_count = int( parts[ idx_sc ] )
                species_set = set( s.strip() for s in parts[ idx_sp_list ].split( ',' ) if s.strip() )

                presence = {}
                presence[ unicells_label ] = 1 if ( species_set & unicells_species ) else 0
                for clade_id in metazoan_leaves:
                    presence[ clade_id ] = 1 if ( species_set & metazoan_species_sets[ clade_id ] ) else 0

                mrca, losses = compute_mrca_and_losses( presence, otu_children, all_leaves )
                depth_value = depth_map.get( mrca, 0 ) if mrca else 0

                orthogroup_ids_this.append( og_id )
                species_counts_this.append( species_count )
                clade_losses_this.append( losses )
                clade_depths_this.append( depth_value )

                total_clade_losses += losses
                total_clade_depth += depth_value

                if min_species_count <= species_count <= max_species_count:
                    filtered_total_clade_losses += losses
                    filtered_total_clade_depth += depth_value
                    filtered_count += 1

        if canonical_orthogroup_ids is None:
            canonical_orthogroup_ids = orthogroup_ids_this
            species_counts_canonical = np.array( species_counts_this, dtype = np.int32 )
            n_orthogroups = len( canonical_orthogroup_ids )
            losses_matrix = np.zeros( ( n_orthogroups, n_structures ), dtype = np.int32 )
            depth_matrix = np.zeros( ( n_orthogroups, n_structures ), dtype = np.int32 )
        else:
            if orthogroup_ids_this != canonical_orthogroup_ids:
                logger.error( f'CRITICAL: orthogroup ID order differs in structure_{structure_id}' )
                sys.exit( 1 )

        losses_matrix[ :, structure_index ] = clade_losses_this
        depth_matrix[ :, structure_index ] = clade_depths_this

        structure_aggregate_rows.append( {
            'Structure_ID': structure_id,
            'Orthogroup_Count': len( orthogroup_ids_this ),
            'Filtered_Orthogroup_Count': filtered_count,
            'Total_Clade_Losses': total_clade_losses,
            'Total_Clade_Origin_Depth': total_clade_depth,
            'Filtered_Total_Clade_Losses': filtered_total_clade_losses,
            'Filtered_Total_Clade_Origin_Depth': filtered_total_clade_depth,
        } )

        if structure_index < 3 or structure_index == n_structures - 1:
            logger.info(
                f'structure_{structure_id}: clade_L={total_clade_losses} filt_L={filtered_total_clade_losses} '
                f'clade_depth={total_clade_depth} filt_depth={filtered_total_clade_depth}'
            )

    aggregate_path = output_11 / '11_ai-clade_binarized_aggregate-per_structure.tsv'
    with open( aggregate_path, 'w' ) as output:
        output.write( 'Structure_ID (three digit identifier from manifest)' )
        output.write( '\tOrthogroup_Count (full unfiltered orthogroup count)' )
        output.write( '\tFiltered_Orthogroup_Count (orthogroups with Species_Count in filter window)' )
        output.write( '\tTotal_Clade_Losses (sum of clade level loss events under Dollo across all unfiltered orthogroups; 6 OTU tree with metazoan clades subsampled)' )
        output.write( '\tTotal_Clade_Origin_Depth (sum of MRCA depth at clade level across all unfiltered orthogroups)' )
        output.write( '\tFiltered_Total_Clade_Losses (clade level losses summed over filtered orthogroups; loss minimization input)' )
        output.write( '\tFiltered_Total_Clade_Origin_Depth (clade level depth summed over filtered orthogroups; shallow gain input)\n' )
        for row in structure_aggregate_rows:
            output.write(
                f"{row[ 'Structure_ID' ]}\t{row[ 'Orthogroup_Count' ]}\t{row[ 'Filtered_Orthogroup_Count' ]}\t"
                f"{row[ 'Total_Clade_Losses' ]}\t{row[ 'Total_Clade_Origin_Depth' ]}\t"
                f"{row[ 'Filtered_Total_Clade_Losses' ]}\t{row[ 'Filtered_Total_Clade_Origin_Depth' ]}\n"
            )
    logger.info( f'Wrote aggregate: {aggregate_path}' )

    logger.info( f'Running paired bootstrap (clade-binarized subsampled): iterations={iterations} seed={seed}' )
    rng = np.random.default_rng( seed )
    filter_mask = ( species_counts_canonical >= min_species_count ) & ( species_counts_canonical <= max_species_count )
    n_filtered = int( filter_mask.sum() )
    filter_indices = np.flatnonzero( filter_mask )

    rank_records_losses = np.zeros( ( iterations, n_structures ), dtype = np.float32 )
    rank_records_depth = np.zeros( ( iterations, n_structures ), dtype = np.float32 )
    best_counts_losses = np.zeros( n_structures, dtype = np.int64 )
    best_counts_depth = np.zeros( n_structures, dtype = np.int64 )

    for iteration in range( iterations ):
        sampled = rng.choice( filter_indices, size = n_filtered, replace = True )
        scores_losses = losses_matrix[ sampled ].sum( axis = 0 )
        scores_depth = depth_matrix[ sampled ].sum( axis = 0 )
        rank_records_losses[ iteration ] = compute_per_structure_ranks( scores_losses.astype( np.float64 ), ascending = True )
        rank_records_depth[ iteration ] = compute_per_structure_ranks( scores_depth.astype( np.float64 ), ascending = False )
        min_loss = scores_losses.min()
        max_depth = scores_depth.max()
        for s_idx in range( n_structures ):
            if scores_losses[ s_idx ] == min_loss:
                best_counts_losses[ s_idx ] += 1
            if scores_depth[ s_idx ] == max_depth:
                best_counts_depth[ s_idx ] += 1

    mean_rank_losses = rank_records_losses.mean( axis = 0 )
    ci_lower_losses = np.percentile( rank_records_losses, 2.5, axis = 0 )
    ci_upper_losses = np.percentile( rank_records_losses, 97.5, axis = 0 )
    pct_best_losses = 100.0 * best_counts_losses / iterations

    mean_rank_depth = rank_records_depth.mean( axis = 0 )
    ci_lower_depth = np.percentile( rank_records_depth, 2.5, axis = 0 )
    ci_upper_depth = np.percentile( rank_records_depth, 97.5, axis = 0 )
    pct_best_depth = 100.0 * best_counts_depth / iterations

    overall_scores_losses = losses_matrix[ filter_indices ].sum( axis = 0 )
    overall_scores_depth = depth_matrix[ filter_indices ].sum( axis = 0 )
    final_ranks_losses = compute_per_structure_ranks( overall_scores_losses.astype( np.float64 ), ascending = True )
    final_ranks_depth = compute_per_structure_ranks( overall_scores_depth.astype( np.float64 ), ascending = False )

    order_for_output = sorted( range( n_structures ), key = lambda i: ( final_ranks_losses[ i ], structure_ids[ i ] ) )

    ranking_path = output_11 / '11_ai-clade_binarized_ranking-structures.tsv'
    with open( ranking_path, 'w' ) as output:
        output.write( 'Final_Rank_Clade_Losses (rank ascending by clade level Total_Losses on filtered orthogroups subsampled metazoans; 1 is best)' )
        output.write( '\tFinal_Rank_Clade_Depth (rank descending by clade level Origin_Depth on filtered orthogroups subsampled metazoans; 1 is best shallow gain)' )
        output.write( '\tStructure_ID (three digit identifier)' )
        output.write( '\tClade_Loss_Score (filtered clade level losses; lower is better)' )
        output.write( '\tClade_Depth_Score (filtered clade level origin depth; larger is better)' )
        output.write( '\tBootstrap_Clade_Losses_Mean_Rank' )
        output.write( '\tBootstrap_Clade_Losses_Rank_CI_Lower_95' )
        output.write( '\tBootstrap_Clade_Losses_Rank_CI_Upper_95' )
        output.write( '\tBootstrap_Clade_Losses_Pct_Times_Best' )
        output.write( '\tBootstrap_Clade_Depth_Mean_Rank' )
        output.write( '\tBootstrap_Clade_Depth_Rank_CI_Lower_95' )
        output.write( '\tBootstrap_Clade_Depth_Rank_CI_Upper_95' )
        output.write( '\tBootstrap_Clade_Depth_Pct_Times_Best' )
        output.write( '\tBootstrap_Iterations (total bootstrap iterations)\n' )
        for idx in order_for_output:
            output.write(
                f'{final_ranks_losses[ idx ]:.1f}\t{final_ranks_depth[ idx ]:.1f}\t{structure_ids[ idx ]}\t'
                f'{overall_scores_losses[ idx ]}\t{overall_scores_depth[ idx ]}\t'
                f'{mean_rank_losses[ idx ]:.4f}\t{ci_lower_losses[ idx ]:.4f}\t{ci_upper_losses[ idx ]:.4f}\t{pct_best_losses[ idx ]:.4f}\t'
                f'{mean_rank_depth[ idx ]:.4f}\t{ci_lower_depth[ idx ]:.4f}\t{ci_upper_depth[ idx ]:.4f}\t{pct_best_depth[ idx ]:.4f}\t'
                f'{iterations}\n'
            )
    logger.info( f'Wrote ranking: {ranking_path}' )

    best_loss_idx = int( np.argmin( overall_scores_losses ) )
    best_depth_idx = int( np.argmax( overall_scores_depth ) )
    logger.info( f'Best by clade loss-min: structure_{structure_ids[ best_loss_idx ]} (Clade_Loss_Score={overall_scores_losses[ best_loss_idx ]})' )
    logger.info( f'Best by clade shallow-gain: structure_{structure_ids[ best_depth_idx ]} (Clade_Depth_Score={overall_scores_depth[ best_depth_idx ]})' )


if __name__ == '__main__':
    main()
