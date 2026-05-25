#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Per-orthogroup topology vote (paired loss-min + shallow-gain) -- per-OG analog to the paired bootstrap in script 004
# Human: Eric Edsinger

"""
Script 012 -- Per-orthogroup topology vote (paired: loss-min + shallow-gain).

For each filtered orthogroup, find which of the 105 candidate species tree
structures (a) minimize its Loss_Events and (b) maximize its origin depth.
Those structure(s) are the orthogroup's "preferred topology" under each
criterion.

Paired analog to the paired bootstrap in script 004 -- exposes how each
individual orthogroup partitions support across topologies under both
parsimony criteria simultaneously.

Vote tallying (one classification per criterion):
  - UNIQUE_WINNER: exactly 1 structure achieves the OG's extremum
                   -> 1.0 vote for that structure
  - TIE_K_WAY:     K > 1 structures tied at the extremum but K < N
                   -> 1/K vote for each tied structure
  - ALL_TIED:      all 105 structures tied (criterion is invariant for this
                   orthogroup) -> no vote

Outputs in 12-output/:
  12_ai-vote_distribution_summary.txt              both-criteria classification stats
  12_ai-per_orthogroup_preferred_structures.tsv    per-OG preferred set per criterion
  12_ai-vote_tally-per_structure.tsv               per-structure vote totals + ranks for both criteria
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml


def parse_header_to_index( header_line ):
    parts = header_line.rstrip( '\n' ).split( '\t' )
    return { p.split( ' ' )[ 0 ]: i for i, p in enumerate( parts ) }


def strip_state_suffix( block_value ):
    if len( block_value ) >= 2 and block_value[ -2 ] == '-' and block_value[ -1 ] in 'AOPLX':
        return block_value[ :-2 ]
    return block_value


def child_from_block( block_value ):
    parts_block = block_value.split( '::' )
    if len( parts_block ) != 2:
        return None
    return parts_block[ 1 ]


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


def build_depth_map( parents_to_children, root_clade_id_name = 'C000_OOL' ):
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


def compute_average_ranks( scores, ascending ):
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


def tally_votes( matrix, extremum, n_structures ):
    """For each row of `matrix`, find structures achieving the extremum
    ('min' or 'max'), classify, and tally votes."""
    n_rows = matrix.shape[ 0 ]
    vote_totals = np.zeros( n_structures, dtype = np.float64 )
    unique_winner_counts = np.zeros( n_structures, dtype = np.int64 )
    fractional_vote_counts = np.zeros( n_structures, dtype = np.int64 )
    n_unique = 0
    n_tied = 0
    n_all_tied = 0
    tie_size_distribution = defaultdict( int )
    per_row_categories = []
    per_row_n_tied = []
    per_row_winner_indices = []
    per_row_extremum_values = []

    for r in range( n_rows ):
        row = matrix[ r ]
        if extremum == 'min':
            ext_value = row.min()
        else:
            ext_value = row.max()
        winners_mask = row == ext_value
        n_winners = int( winners_mask.sum() )
        winner_indices = np.flatnonzero( winners_mask )

        if n_winners == n_structures:
            category = 'ALL_TIED'
            n_all_tied += 1
        elif n_winners == 1:
            category = 'UNIQUE_WINNER'
            n_unique += 1
            vote_totals[ winner_indices[ 0 ] ] += 1.0
            unique_winner_counts[ winner_indices[ 0 ] ] += 1
        else:
            category = f'TIE_{n_winners}_WAY'
            n_tied += 1
            fractional = 1.0 / n_winners
            for w_idx in winner_indices:
                vote_totals[ w_idx ] += fractional
                fractional_vote_counts[ w_idx ] += 1
        tie_size_distribution[ n_winners ] += 1
        per_row_categories.append( category )
        per_row_n_tied.append( n_winners )
        per_row_winner_indices.append( winner_indices )
        per_row_extremum_values.append( int( ext_value ) )

    return (
        vote_totals, unique_winner_counts, fractional_vote_counts,
        n_unique, n_tied, n_all_tied, tie_size_distribution,
        per_row_categories, per_row_n_tied, per_row_winner_indices, per_row_extremum_values,
    )


def main():
    parser = argparse.ArgumentParser( description = 'Per-orthogroup topology vote (paired loss-min + shallow-gain)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_12 = output_dir / '12-output'
    output_12.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_dir / '12_ai-log-per_orthogroup_topology_vote.log' ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'topology_vote' )

    logger.info( 'Starting script 012: per_orthogroup_topology_vote (paired loss-min + shallow-gain)' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )

    ocl_orthogroups_dir = ( workflow_dir / config[ 'inputs' ][ 'ocl_orthogroups_dir' ] ).resolve()
    trees_species_dir = ( workflow_dir / config[ 'inputs' ][ 'trees_species_dir' ] ).resolve()
    parent_child_dir = trees_species_dir / 'Species_Parent_Child_Relationships'
    structure_manifest_path = ( workflow_dir / config[ 'inputs' ][ 'structure_manifest' ] ).resolve()

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

    n_structures = len( structure_ids )
    logger.info( f'Loading Loss_Events + origin block + parent-child depth across {n_structures} structures' )

    canonical_orthogroup_ids = None
    species_counts_canonical = None
    losses_matrix = None
    depth_matrix = None

    for structure_index, structure_id in enumerate( structure_ids ):
        ocl_path = ocl_orthogroups_dir / f'structure_{structure_id}' / '4_ai-orthogroups-complete_ocl_summary.tsv'
        parent_child_path = parent_child_dir / f'5_ai-structure_{structure_id}_parent_child_relationships.tsv'
        clade_id_names_to_depths = build_depth_map( load_parent_child( parent_child_path ) )

        orthogroup_ids_this = []
        losses_column = []
        depths_column = []
        species_counts_this = []

        with open( ocl_path ) as input_ocl:
            header_line = input_ocl.readline()
            columns_to_index = parse_header_to_index( header_line )
            idx_og = columns_to_index[ 'Orthogroup_ID' ]
            idx_loss = columns_to_index[ 'Loss_Events' ]
            idx_block = columns_to_index[ 'Origin_Phylogenetic_Block' ]
            idx_sc = columns_to_index[ 'Species_Count' ]
            for line in input_ocl:
                parts = line.rstrip( '\n' ).split( '\t' )
                orthogroup_ids_this.append( parts[ idx_og ] )
                losses_column.append( int( parts[ idx_loss ] ) )
                species_counts_this.append( int( parts[ idx_sc ] ) )
                origin_block = strip_state_suffix( parts[ idx_block ] )
                child_clade = child_from_block( origin_block )
                depth = clade_id_names_to_depths.get( child_clade, 1 ) if child_clade else 1
                depths_column.append( depth )

        if canonical_orthogroup_ids is None:
            canonical_orthogroup_ids = orthogroup_ids_this
            species_counts_canonical = np.array( species_counts_this, dtype = np.int32 )
            losses_matrix = np.zeros( ( len( canonical_orthogroup_ids ), n_structures ), dtype = np.int32 )
            depth_matrix = np.zeros( ( len( canonical_orthogroup_ids ), n_structures ), dtype = np.int32 )
        else:
            if orthogroup_ids_this != canonical_orthogroup_ids:
                logger.error( f'CRITICAL: orthogroup ID order differs in structure_{structure_id}' )
                sys.exit( 1 )

        losses_matrix[ :, structure_index ] = losses_column
        depth_matrix[ :, structure_index ] = depths_column

    n_orthogroups = losses_matrix.shape[ 0 ]
    logger.info( f'Built losses + depth matrices: {n_orthogroups} orthogroups x {n_structures} structures' )

    filter_mask = ( species_counts_canonical >= min_species_count ) & ( species_counts_canonical <= max_species_count )
    n_filtered = int( filter_mask.sum() )
    filter_indices = np.flatnonzero( filter_mask )
    logger.info( f'Filtered orthogroups (only these vote): {n_filtered} / {n_orthogroups}' )

    losses_filtered = losses_matrix[ filter_indices ]
    depth_filtered = depth_matrix[ filter_indices ]

    logger.info( 'Tallying loss-min votes (argmin per OG)' )
    ( vote_totals_L, unique_counts_L, frac_counts_L,
      n_unique_L, n_tied_L, n_all_tied_L, tie_dist_L,
      categories_L, n_tied_per_og_L, winners_per_og_L, ext_per_og_L ) = tally_votes( losses_filtered, 'min', n_structures )

    logger.info( 'Tallying shallow-gain votes (argmax per OG)' )
    ( vote_totals_D, unique_counts_D, frac_counts_D,
      n_unique_D, n_tied_D, n_all_tied_D, tie_dist_D,
      categories_D, n_tied_per_og_D, winners_per_og_D, ext_per_og_D ) = tally_votes( depth_filtered, 'max', n_structures )

    logger.info( f'Losses    : UNIQUE_WINNER={n_unique_L}  TIE_K_WAY={n_tied_L}  ALL_TIED={n_all_tied_L}' )
    logger.info( f'Depth     : UNIQUE_WINNER={n_unique_D}  TIE_K_WAY={n_tied_D}  ALL_TIED={n_all_tied_D}' )

    ranks_vote_L = compute_average_ranks( vote_totals_L, ascending = False )
    ranks_vote_D = compute_average_ranks( vote_totals_D, ascending = False )

    ranking_path = output_dir / '5-output' / '5_ai-parsimony_ranking-structures.tsv'
    loss_min_ranks = {}
    depth_ranks = {}
    if ranking_path.is_file():
        with open( ranking_path ) as input_ranking:
            header_line = input_ranking.readline()
            columns_to_index = parse_header_to_index( header_line )
            idx_lr = columns_to_index[ 'Final_Rank_Losses' ]
            idx_dr = columns_to_index[ 'Final_Rank_Depth' ]
            idx_sid = columns_to_index[ 'Structure_ID' ]
            for line in input_ranking:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                loss_min_ranks[ parts[ idx_sid ] ] = float( parts[ idx_lr ] )
                depth_ranks[ parts[ idx_sid ] ] = float( parts[ idx_dr ] )

    output_tally = output_12 / '12_ai-vote_tally-per_structure.tsv'
    with open( output_tally, 'w' ) as output:
        output.write( 'Structure_ID (three digit identifier from manifest)' )
        output.write( '\tFinal_Rank_Losses_From_005 (loss minimization rank from script 005 for comparison)' )
        output.write( '\tFinal_Rank_Depth_From_005 (shallow gain rank from script 005 for comparison)' )
        output.write( '\tVote_Total_Losses (sum of UNIQUE_WINNER + fractional TIE votes under loss minimization; higher is better)' )
        output.write( '\tUnique_Winner_Losses_OG_Count (number of orthogroups where this is the sole min loss structure)' )
        output.write( '\tFractional_Vote_Losses_OG_Count (number of orthogroups where this structure is tied for min loss)' )
        output.write( '\tFinal_Rank_Vote_Losses (rank by Vote_Total_Losses descending; 1 is best)' )
        output.write( '\tRank_Delta_Losses_005_minus_VoteLosses (positive = better by votes than by total losses)' )
        output.write( '\tVote_Total_Depth (sum of UNIQUE_WINNER + fractional TIE votes under shallow gain; higher is better)' )
        output.write( '\tUnique_Winner_Depth_OG_Count (number of orthogroups where this is the sole max depth structure)' )
        output.write( '\tFractional_Vote_Depth_OG_Count (number of orthogroups where this structure is tied for max depth)' )
        output.write( '\tFinal_Rank_Vote_Depth (rank by Vote_Total_Depth descending; 1 is best)' )
        output.write( '\tRank_Delta_Depth_005_minus_VoteDepth (positive = better by votes than by total depth)\n' )
        for idx in np.argsort( -vote_totals_L, kind = 'stable' ):
            sid = structure_ids[ idx ]
            lr = loss_min_ranks.get( sid, float( 'nan' ) )
            dr = depth_ranks.get( sid, float( 'nan' ) )
            output.write(
                f'{sid}\t{lr:.1f}\t{dr:.1f}\t'
                f'{vote_totals_L[ idx ]:.4f}\t{unique_counts_L[ idx ]}\t{frac_counts_L[ idx ]}\t{ranks_vote_L[ idx ]:.1f}\t{( lr - ranks_vote_L[ idx ] ):.1f}\t'
                f'{vote_totals_D[ idx ]:.4f}\t{unique_counts_D[ idx ]}\t{frac_counts_D[ idx ]}\t{ranks_vote_D[ idx ]:.1f}\t{( dr - ranks_vote_D[ idx ] ):.1f}\n'
            )
    logger.info( f'Wrote vote tally: {output_tally}' )

    output_per_og = output_12 / '12_ai-per_orthogroup_preferred_structures.tsv'
    with open( output_per_og, 'w' ) as output:
        output.write( 'Orthogroup_ID (canonical orthogroup identifier)' )
        output.write( '\tSpecies_Count (orthogroup species count)' )
        output.write( '\tMin_Loss_Events (minimum Loss_Events achieved by this orthogroup across all 105 structures)' )
        output.write( '\tN_Tied_Losses (number of structures tied at min loss)' )
        output.write( '\tTied_Structure_IDs_Losses (comma delimited list of structure IDs at min loss)' )
        output.write( '\tVote_Category_Losses (UNIQUE_WINNER or TIE_K_WAY or ALL_TIED for loss minimization)' )
        output.write( '\tMax_Origin_Depth (maximum origin depth achieved by this orthogroup across all 105 structures)' )
        output.write( '\tN_Tied_Depth (number of structures tied at max depth)' )
        output.write( '\tTied_Structure_IDs_Depth (comma delimited list of structure IDs at max depth)' )
        output.write( '\tVote_Category_Depth (UNIQUE_WINNER or TIE_K_WAY or ALL_TIED for shallow gain)\n' )
        for i, og_idx in enumerate( filter_indices ):
            og_id = canonical_orthogroup_ids[ og_idx ]
            sc = int( species_counts_canonical[ og_idx ] )
            winners_L = winners_per_og_L[ i ]
            winners_D = winners_per_og_D[ i ]
            tied_ids_L = ','.join( f'structure_{structure_ids[ w ]}' for w in winners_L )
            tied_ids_D = ','.join( f'structure_{structure_ids[ w ]}' for w in winners_D )
            output.write(
                f'{og_id}\t{sc}\t'
                f'{ext_per_og_L[ i ]}\t{n_tied_per_og_L[ i ]}\t{tied_ids_L}\t{categories_L[ i ]}\t'
                f'{ext_per_og_D[ i ]}\t{n_tied_per_og_D[ i ]}\t{tied_ids_D}\t{categories_D[ i ]}\n'
            )
    logger.info( f'Wrote per-OG preferred structures: {output_per_og}' )

    output_summary = output_12 / '12_ai-vote_distribution_summary.txt'
    with open( output_summary, 'w' ) as output:
        output.write( '# parsimony_tree_structures BLOCK_ocl_orthogroups -- per-orthogroup topology vote summary (paired)\n' )
        output.write( f'# run_label: {config.get( "run_label", "UNSPECIFIED" )}\n' )
        output.write( '\n' )
        output.write( f'Filtered_Orthogroups_Total\t{n_filtered}\n' )
        output.write( '\n' )
        output.write( '## Loss-minimization vote classification\n' )
        output.write( f'UNIQUE_WINNER_count\t{n_unique_L}\n' )
        output.write( f'TIE_K_WAY_count\t{n_tied_L}\n' )
        output.write( f'ALL_TIED_count\t{n_all_tied_L}  (cast no vote)\n' )
        output.write( 'N_Tied_Structures\tOrthogroup_Count\n' )
        for n in sorted( tie_dist_L.keys() ):
            output.write( f'{n}\t{tie_dist_L[ n ]}\n' )
        output.write( '\n' )
        output.write( '## Shallow-gain vote classification\n' )
        output.write( f'UNIQUE_WINNER_count\t{n_unique_D}\n' )
        output.write( f'TIE_K_WAY_count\t{n_tied_D}\n' )
        output.write( f'ALL_TIED_count\t{n_all_tied_D}  (cast no vote)\n' )
        output.write( 'N_Tied_Structures\tOrthogroup_Count\n' )
        for n in sorted( tie_dist_D.keys() ):
            output.write( f'{n}\t{tie_dist_D[ n ]}\n' )
        output.write( '\n' )
        output.write( '## Top 10 by Vote_Total_Losses\n' )
        output.write( 'Final_Rank_Vote_Losses\tStructure_ID\tVote_Total_Losses\tUnique_Winners\tFractional_Vote_OG_Count\tFinal_Rank_Losses_005\n' )
        for idx in np.argsort( -vote_totals_L, kind = 'stable' )[ :10 ]:
            sid = structure_ids[ idx ]
            output.write(
                f'{ranks_vote_L[ idx ]:.1f}\t{sid}\t{vote_totals_L[ idx ]:.4f}\t{unique_counts_L[ idx ]}\t{frac_counts_L[ idx ]}\t{loss_min_ranks.get( sid, float( "nan" ) ):.1f}\n'
            )
        output.write( '\n' )
        output.write( '## Top 10 by Vote_Total_Depth\n' )
        output.write( 'Final_Rank_Vote_Depth\tStructure_ID\tVote_Total_Depth\tUnique_Winners\tFractional_Vote_OG_Count\tFinal_Rank_Depth_005\n' )
        for idx in np.argsort( -vote_totals_D, kind = 'stable' )[ :10 ]:
            sid = structure_ids[ idx ]
            output.write(
                f'{ranks_vote_D[ idx ]:.1f}\t{sid}\t{vote_totals_D[ idx ]:.4f}\t{unique_counts_D[ idx ]}\t{frac_counts_D[ idx ]}\t{depth_ranks.get( sid, float( "nan" ) ):.1f}\n'
            )
    logger.info( f'Wrote vote distribution summary: {output_summary}' )

    top_L = int( np.argmax( vote_totals_L ) )
    top_D = int( np.argmax( vote_totals_D ) )
    logger.info( f'Top by vote (losses): structure_{structure_ids[ top_L ]} (Vote_Total={vote_totals_L[ top_L ]:.2f}, unique={unique_counts_L[ top_L ]})' )
    logger.info( f'Top by vote (depth):  structure_{structure_ids[ top_D ]} (Vote_Total={vote_totals_D[ top_D ]:.2f}, unique={unique_counts_D[ top_D ]})' )


if __name__ == '__main__':
    main()
