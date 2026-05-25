#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Paired bootstrap on losses + per-structure origin depths (computed from parent-child table)
# Human: Eric Edsinger

"""
Script 004 -- Bootstrap ranking confidence (paired, both criteria, depth-based).

Resamples orthogroups with replacement and recomputes BOTH parsimony criteria
per resample:
  1. Score_Total_Losses on full orthogroup set (lower better)
  2. Score_Total_Origin_Depth_Filtered on the filtered subset (larger better)

For the shallow-gain bootstrap, per-orthogroup origin DEPTH is computed
freshly per structure using the parent-child table (depth = number of edges
from C000_OOL to the child of the origin block). This avoids the upstream
OCL Origin_Phylogenetic_Path data-quality issue (many entries are NA even
for mid-tree origins).

Outputs per-criterion: mean rank, 95% CI on rank, pct times best.
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml


def parse_header_to_index( header_line ):
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    return { part.split( ' ' )[ 0 ]: i for i, part in enumerate( parts_header_line ) }


def strip_state_suffix( block_value ):
    if len( block_value ) >= 2 and block_value[ -2 ] == '-' and block_value[ -1 ] in 'AOPLX':
        return block_value[ :-2 ]
    return block_value


def child_from_block( block_value ):
    parts_block = block_value.split( '::' )
    if len( parts_block ) != 2:
        return None
    return parts_block[ 1 ]


def build_depth_map( parent_child_path, root_clade_id_name = 'C000_OOL' ):
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
    clade_id_names_to_depths = { root_clade_id_name: 0 }
    queue = [ root_clade_id_name ]
    while queue:
        next_queue = []
        for parent in queue:
            for child in parents_to_children.get( parent, () ):
                if child in clade_id_names_to_depths:
                    continue
                clade_id_names_to_depths[ child ] = clade_id_names_to_depths[ parent ] + 1
                next_queue.append( child )
        queue = next_queue
    return clade_id_names_to_depths


def compute_per_structure_ranks( scores, ascending ):
    n_structures = len( scores )
    if ascending:
        order = np.argsort( scores, kind = 'stable' )
    else:
        order = np.argsort( -scores, kind = 'stable' )
    ranks = np.empty( n_structures, dtype = np.float32 )
    ranks[ order ] = np.arange( 1, n_structures + 1, dtype = np.float32 )
    sorted_scores = scores[ order ]
    i = 0
    while i < n_structures:
        j = i + 1
        while j < n_structures and sorted_scores[ j ] == sorted_scores[ i ]:
            j += 1
        if j - i > 1:
            avg = ( ranks[ order[ i ] ] + ranks[ order[ j - 1 ] ] ) / 2.0
            for k in range( i, j ):
                ranks[ order[ k ] ] = avg
        i = j
    return ranks


def main():
    parser = argparse.ArgumentParser( description = 'Paired bootstrap (losses + origin depth)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_4 = output_dir / '4-output'
    output_4.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    log_file = log_dir / '4_ai-log-bootstrap_ranking_confidence.log'
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_file ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'bootstrap' )

    logger.info( 'Starting script 004: paired bootstrap (depth-based shallow gain)' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )

    ocl_orthogroups_dir = ( workflow_dir / config[ 'inputs' ][ 'ocl_orthogroups_dir' ] ).resolve()
    trees_species_dir = ( workflow_dir / config[ 'inputs' ][ 'trees_species_dir' ] ).resolve()
    parent_child_dir = trees_species_dir / 'Species_Parent_Child_Relationships'
    structure_manifest_path = ( workflow_dir / config[ 'inputs' ][ 'structure_manifest' ] ).resolve()
    iterations = int( config[ 'bootstrap' ][ 'iterations' ] )
    seed = int( config[ 'bootstrap' ][ 'seed' ] )

    filter_config = config.get( 'filter', {} ) or {}
    min_species_count = int( filter_config.get( 'min_species_count', 2 ) )
    max_species_count_raw = filter_config.get( 'max_species_count', None )
    max_species_count = int( max_species_count_raw ) if max_species_count_raw is not None else 10 ** 9

    structure_ids = []
    with open( structure_manifest_path ) as input_manifest:
        input_manifest.readline()
        for line in input_manifest:
            line = line.strip()
            if line and not line.startswith( '#' ):
                structure_ids.append( line )

    n_structures = len( structure_ids )
    if n_structures < 2:
        logger.error( f'CRITICAL: bootstrap requires at least 2 structures; manifest has {n_structures}' )
        sys.exit( 1 )

    logger.info( f'Loading Loss_Events + origin block + Species_Count + parent-child depth for {n_structures} structures' )

    canonical_orthogroup_ids = None
    species_counts_canonical = None
    losses_matrix = None
    depths_matrix = None

    for structure_index, structure_id in enumerate( structure_ids ):
        ocl_summary_path = ocl_orthogroups_dir / f'structure_{structure_id}' / '4_ai-orthogroups-complete_ocl_summary.tsv'
        parent_child_path = parent_child_dir / f'5_ai-structure_{structure_id}_parent_child_relationships.tsv'
        clade_id_names_to_depths = build_depth_map( parent_child_path )

        orthogroup_ids_this = []
        losses_column = []
        depths_column = []
        species_counts_this = []

        with open( ocl_summary_path ) as input_summary:
            header_line = input_summary.readline()
            columns_to_index = parse_header_to_index( header_line )
            index_og = columns_to_index[ 'Orthogroup_ID' ]
            index_loss = columns_to_index[ 'Loss_Events' ]
            index_block = columns_to_index[ 'Origin_Phylogenetic_Block' ]
            index_species_count = columns_to_index[ 'Species_Count' ]
            for line in input_summary:
                parts = line.rstrip( '\n' ).split( '\t' )
                orthogroup_ids_this.append( parts[ index_og ] )
                losses_column.append( int( parts[ index_loss ] ) )
                species_counts_this.append( int( parts[ index_species_count ] ) )
                origin_block = strip_state_suffix( parts[ index_block ] )
                child_clade = child_from_block( origin_block )
                depth = clade_id_names_to_depths.get( child_clade, 1 ) if child_clade else 1
                depths_column.append( depth )

        if canonical_orthogroup_ids is None:
            canonical_orthogroup_ids = orthogroup_ids_this
            species_counts_canonical = np.array( species_counts_this, dtype = np.int32 )
            losses_matrix = np.zeros( ( len( canonical_orthogroup_ids ), n_structures ), dtype = np.int32 )
            depths_matrix = np.zeros( ( len( canonical_orthogroup_ids ), n_structures ), dtype = np.int32 )
        else:
            if orthogroup_ids_this != canonical_orthogroup_ids:
                logger.error( f'CRITICAL: orthogroup ID order differs between first structure and structure_{structure_id}' )
                sys.exit( 1 )

        losses_matrix[ :, structure_index ] = losses_column
        depths_matrix[ :, structure_index ] = depths_column

    n_orthogroups = losses_matrix.shape[ 0 ]
    logger.info( f'Built matrices: {n_orthogroups} orthogroups x {n_structures} structures' )

    filter_mask = ( species_counts_canonical >= min_species_count ) & ( species_counts_canonical <= max_species_count )
    n_filtered = int( filter_mask.sum() )
    logger.info( f'Filtered orthogroup count: {n_filtered} / {n_orthogroups}' )

    if n_filtered == 0:
        logger.error( 'CRITICAL: filter dropped all orthogroups' )
        sys.exit( 1 )

    logger.info( f'Running paired bootstrap: iterations={iterations} seed={seed}' )
    rng = np.random.default_rng( seed )

    rank_records_losses = np.zeros( ( iterations, n_structures ), dtype = np.float32 )
    rank_records_depth = np.zeros( ( iterations, n_structures ), dtype = np.float32 )
    best_counts_losses = np.zeros( n_structures, dtype = np.int64 )
    best_counts_depth = np.zeros( n_structures, dtype = np.int64 )

    filter_indices = np.flatnonzero( filter_mask )

    for iteration in range( iterations ):
        sampled_full = rng.integers( 0, n_orthogroups, n_orthogroups )
        sampled_filtered = rng.choice( filter_indices, size = n_filtered, replace = True )

        scores_losses = losses_matrix[ sampled_full ].sum( axis = 0 )
        ranks_losses = compute_per_structure_ranks( scores_losses.astype( np.float64 ), ascending = True )
        rank_records_losses[ iteration ] = ranks_losses
        min_score_losses = scores_losses.min()
        for structure_index in range( n_structures ):
            if scores_losses[ structure_index ] == min_score_losses:
                best_counts_losses[ structure_index ] += 1

        scores_depth = depths_matrix[ sampled_filtered ].sum( axis = 0 )
        ranks_depth = compute_per_structure_ranks( scores_depth.astype( np.float64 ), ascending = False )
        rank_records_depth[ iteration ] = ranks_depth
        max_score_depth = scores_depth.max()
        for structure_index in range( n_structures ):
            if scores_depth[ structure_index ] == max_score_depth:
                best_counts_depth[ structure_index ] += 1

    logger.info( 'Bootstrap complete; computing summary statistics' )

    mean_rank_losses = rank_records_losses.mean( axis = 0 )
    ci_lower_losses = np.percentile( rank_records_losses, 2.5, axis = 0 )
    ci_upper_losses = np.percentile( rank_records_losses, 97.5, axis = 0 )
    pct_best_losses = 100.0 * best_counts_losses / iterations

    mean_rank_depth = rank_records_depth.mean( axis = 0 )
    ci_lower_depth = np.percentile( rank_records_depth, 2.5, axis = 0 )
    ci_upper_depth = np.percentile( rank_records_depth, 97.5, axis = 0 )
    pct_best_depth = 100.0 * best_counts_depth / iterations

    output_bootstrap = output_4 / '4_ai-bootstrap_confidence-per_structure.tsv'
    with open( output_bootstrap, 'w' ) as output:
        output.write( 'Structure_ID (three digit identifier from manifest)' )
        output.write( '\tBootstrap_Losses_Mean_Rank (mean rank under loss minimization on full set; rank 1 is best)' )
        output.write( '\tBootstrap_Losses_Rank_CI_Lower_95 (2.5 percentile of loss rank distribution)' )
        output.write( '\tBootstrap_Losses_Rank_CI_Upper_95 (97.5 percentile of loss rank distribution)' )
        output.write( '\tBootstrap_Losses_Pct_Times_Best (percent of iterations with the lowest Score_Total_Losses)' )
        output.write( '\tBootstrap_Depth_Mean_Rank (mean rank under shallow gain on filtered orthogroups; rank 1 is best)' )
        output.write( '\tBootstrap_Depth_Rank_CI_Lower_95 (2.5 percentile of depth rank distribution)' )
        output.write( '\tBootstrap_Depth_Rank_CI_Upper_95 (97.5 percentile of depth rank distribution)' )
        output.write( '\tBootstrap_Depth_Pct_Times_Best (percent of iterations with the largest filtered Origin_Depth sum)' )
        output.write( '\tBootstrap_Iterations (total iterations performed)' )
        output.write( '\tBootstrap_Seed (random seed)\n' )
        for structure_index, structure_id in enumerate( structure_ids ):
            line = ( structure_id
                + '\t' + format( float( mean_rank_losses[ structure_index ] ), '.4f' )
                + '\t' + format( float( ci_lower_losses[ structure_index ] ), '.4f' )
                + '\t' + format( float( ci_upper_losses[ structure_index ] ), '.4f' )
                + '\t' + format( float( pct_best_losses[ structure_index ] ), '.4f' )
                + '\t' + format( float( mean_rank_depth[ structure_index ] ), '.4f' )
                + '\t' + format( float( ci_lower_depth[ structure_index ] ), '.4f' )
                + '\t' + format( float( ci_upper_depth[ structure_index ] ), '.4f' )
                + '\t' + format( float( pct_best_depth[ structure_index ] ), '.4f' )
                + '\t' + str( iterations )
                + '\t' + str( seed )
                + '\n' )
            output.write( line )
    logger.info( f'Wrote bootstrap table: {output_bootstrap}' )


if __name__ == '__main__':
    main()
