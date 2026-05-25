#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Dual ranking by loss-minimization AND shallow-gain (origin depth) criteria
# Human: Eric Edsinger

"""
Script 005 -- Dual ranking + summary.

Joins per-structure parsimony scores (script 003) with paired bootstrap
(script 004) and emits a single ranking table with BOTH criteria side-by-side:

  Final_Rank_Losses  -- rank by Score_Total_Losses ascending (loss-min PRIMARY)
  Final_Rank_Depth   -- rank by Score_Total_Origin_Depth_Filtered descending
                        (shallow-gain PRIMARY)

Identifies best structure(s) under each criterion and flags agreement.
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml


def parse_header_to_index( header_line ):
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    return { part.split( ' ' )[ 0 ]: i for i, part in enumerate( parts_header_line ) }


def average_ranks( ordered_structure_ids, key_function ):
    ranks = {}
    n = len( ordered_structure_ids )
    i = 0
    while i < n:
        j = i + 1
        ki = key_function( ordered_structure_ids[ i ] )
        while j < n and key_function( ordered_structure_ids[ j ] ) == ki:
            j += 1
        rank_value = ( ( i + 1 ) + j ) / 2.0
        for k in range( i, j ):
            ranks[ ordered_structure_ids[ k ] ] = rank_value
        i = j
    return ranks


def main():
    parser = argparse.ArgumentParser( description = 'Dual ranking (loss-min + shallow-gain depth)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_5 = output_dir / '5-output'
    output_5.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    log_file = log_dir / '5_ai-log-rank_structures_and_summarize.log'
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_file ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'rank_summarize' )

    logger.info( 'Starting script 005: dual rank + summarize (depth-based shallow gain)' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )
    tie_threshold_pct = float( config[ 'bootstrap' ][ 'tie_threshold_pct' ] )
    run_label = config.get( 'run_label', 'UNSPECIFIED' )

    scores_path = output_dir / '3-output' / '3_ai-parsimony_scores-per_structure.tsv'
    bootstrap_path = output_dir / '4-output' / '4_ai-bootstrap_confidence-per_structure.tsv'
    for path in ( scores_path, bootstrap_path ):
        if not path.is_file():
            logger.error( f'CRITICAL: required input not found: {path}' )
            sys.exit( 1 )

    structure_ids_to_scores = {}
    with open( scores_path ) as input_scores:
        header_line = input_scores.readline()
        columns_to_index = parse_header_to_index( header_line )
        for line in input_scores:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ columns_to_index[ 'Structure_ID' ] ]
            structure_ids_to_scores[ structure_id ] = {
                key: parts[ columns_to_index[ key ] ] for key in columns_to_index if key != 'Structure_ID'
            }

    structure_ids_to_bootstrap = {}
    with open( bootstrap_path ) as input_bootstrap:
        header_line = input_bootstrap.readline()
        columns_to_index = parse_header_to_index( header_line )
        for line in input_bootstrap:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ columns_to_index[ 'Structure_ID' ] ]
            structure_ids_to_bootstrap[ structure_id ] = {
                key: parts[ columns_to_index[ key ] ] for key in columns_to_index if key != 'Structure_ID'
            }

    if set( structure_ids_to_scores.keys() ) != set( structure_ids_to_bootstrap.keys() ):
        logger.error( 'CRITICAL: Structure ID sets differ between scores and bootstrap inputs' )
        sys.exit( 1 )

    all_structure_ids = list( structure_ids_to_scores.keys() )

    sorted_by_losses = sorted(
        all_structure_ids,
        key = lambda s: ( int( structure_ids_to_scores[ s ][ 'Score_Total_Losses' ] ), s ),
    )
    rank_by_losses = average_ranks(
        sorted_by_losses,
        key_function = lambda s: int( structure_ids_to_scores[ s ][ 'Score_Total_Losses' ] ),
    )

    sorted_by_depth = sorted(
        all_structure_ids,
        key = lambda s: ( -int( structure_ids_to_scores[ s ][ 'Score_Total_Origin_Depth_Filtered' ] ), s ),
    )
    rank_by_depth = average_ranks(
        sorted_by_depth,
        key_function = lambda s: -int( structure_ids_to_scores[ s ][ 'Score_Total_Origin_Depth_Filtered' ] ),
    )

    best_score_losses = int( structure_ids_to_scores[ sorted_by_losses[ 0 ] ][ 'Score_Total_Losses' ] )
    best_by_losses = [ s for s in sorted_by_losses if int( structure_ids_to_scores[ s ][ 'Score_Total_Losses' ] ) == best_score_losses ]

    best_score_depth = int( structure_ids_to_scores[ sorted_by_depth[ 0 ] ][ 'Score_Total_Origin_Depth_Filtered' ] )
    best_by_depth = [ s for s in sorted_by_depth if int( structure_ids_to_scores[ s ][ 'Score_Total_Origin_Depth_Filtered' ] ) == best_score_depth ]

    tied_with_best_losses_bootstrap = [
        s for s in sorted_by_losses
        if float( structure_ids_to_bootstrap[ s ][ 'Bootstrap_Losses_Pct_Times_Best' ] ) >= tie_threshold_pct
    ]
    tied_with_best_depth_bootstrap = [
        s for s in sorted_by_depth
        if float( structure_ids_to_bootstrap[ s ][ 'Bootstrap_Depth_Pct_Times_Best' ] ) >= tie_threshold_pct
    ]

    output_sorted_ids = sorted_by_losses

    output_ranking = output_5 / '5_ai-parsimony_ranking-structures.tsv'
    with open( output_ranking, 'w' ) as output:
        output.write( 'Final_Rank_Losses (1 indicates most parsimonious by Score_Total_Losses ascending)' )
        output.write( '\tFinal_Rank_Depth (1 indicates most parsimonious by Score_Total_Origin_Depth_Filtered descending)' )
        output.write( '\tStructure_ID (three digit identifier from manifest; structure_001 is the user provided input species tree)' )
        output.write( '\tOrthogroup_Count (full unfiltered orthogroup count)' )
        output.write( '\tFiltered_Orthogroup_Count (orthogroups in the Species_Count filter window)' )
        output.write( '\tTotal_Blocks_Per_Structure (number of phylogenetic blocks)' )
        output.write( '\tScore_Total_Inherited_Absence (A state count)' )
        output.write( '\tScore_Total_Origins (O state count)' )
        output.write( '\tScore_Total_Conservation (P state count)' )
        output.write( '\tScore_Total_Losses (L state count full set; lower is better)' )
        output.write( '\tScore_Total_Continued_Absence (X state count)' )
        output.write( '\tScore_Total_Gains_Plus_Losses (O plus L)' )
        output.write( '\tScore_Conservation_to_Loss_Ratio (P over max 1 L; higher is better)' )
        output.write( '\tScore_Mean_Losses_Per_Orthogroup (L over OG; lower is better)' )
        output.write( '\tScore_Mean_Origin_Depth (mean origin depth unfiltered)' )
        output.write( '\tScore_Total_Origin_Depth_Filtered (SHALLOW GAIN primary; sum of origin child clade depths from C000_OOL over filtered orthogroups; LARGER is better)' )
        output.write( '\tScore_Mean_Origin_Depth_Filtered (mean over filtered orthogroups; larger is better)' )
        output.write( '\tScore_Total_Losses_Filtered (loss sum over filtered subset for apples to apples comparison)' )
        output.write( '\tBootstrap_Losses_Mean_Rank (mean rank in loss minimization bootstrap)' )
        output.write( '\tBootstrap_Losses_Rank_CI_Lower_95 (2.5 percent percentile)' )
        output.write( '\tBootstrap_Losses_Rank_CI_Upper_95 (97.5 percent percentile)' )
        output.write( '\tBootstrap_Losses_Pct_Times_Best (percent of iterations winning by loss minimization)' )
        output.write( '\tBootstrap_Losses_Tied_With_Best (TRUE if Pct_Times_Best meets tie_threshold_pct)' )
        output.write( '\tBootstrap_Depth_Mean_Rank (mean rank in shallow gain bootstrap)' )
        output.write( '\tBootstrap_Depth_Rank_CI_Lower_95 (2.5 percent percentile)' )
        output.write( '\tBootstrap_Depth_Rank_CI_Upper_95 (97.5 percent percentile)' )
        output.write( '\tBootstrap_Depth_Pct_Times_Best (percent of iterations winning by shallow gain)' )
        output.write( '\tBootstrap_Depth_Tied_With_Best (TRUE if Pct_Times_Best meets tie_threshold_pct)' )
        output.write( '\tCriteria_Agreement (one of LOSSES_ONLY DEPTH_ONLY BOTH_AGREE NEITHER indicating bootstrap tie-threshold agreement)' )
        output.write( '\tBootstrap_Iterations (total iterations performed)' )
        output.write( '\tBootstrap_Seed (random seed)\n' )

        for structure_id in output_sorted_ids:
            scores = structure_ids_to_scores[ structure_id ]
            boot = structure_ids_to_bootstrap[ structure_id ]
            loss_pct = float( boot[ 'Bootstrap_Losses_Pct_Times_Best' ] )
            depth_pct = float( boot[ 'Bootstrap_Depth_Pct_Times_Best' ] )
            tied_losses = loss_pct >= tie_threshold_pct
            tied_depth = depth_pct >= tie_threshold_pct
            if tied_losses and tied_depth:
                agreement = 'BOTH_AGREE'
            elif tied_losses:
                agreement = 'LOSSES_ONLY'
            elif tied_depth:
                agreement = 'DEPTH_ONLY'
            else:
                agreement = 'NEITHER'

            line = ( format( rank_by_losses[ structure_id ], '.1f' )
                + '\t' + format( rank_by_depth[ structure_id ], '.1f' )
                + '\t' + structure_id
                + '\t' + scores[ 'Orthogroup_Count' ]
                + '\t' + scores[ 'Filtered_Orthogroup_Count' ]
                + '\t' + scores[ 'Total_Blocks_Per_Structure' ]
                + '\t' + scores[ 'Score_Total_Inherited_Absence' ]
                + '\t' + scores[ 'Score_Total_Origins' ]
                + '\t' + scores[ 'Score_Total_Conservation' ]
                + '\t' + scores[ 'Score_Total_Losses' ]
                + '\t' + scores[ 'Score_Total_Continued_Absence' ]
                + '\t' + scores[ 'Score_Total_Gains_Plus_Losses' ]
                + '\t' + scores[ 'Score_Conservation_to_Loss_Ratio' ]
                + '\t' + scores[ 'Score_Mean_Losses_Per_Orthogroup' ]
                + '\t' + scores[ 'Score_Mean_Origin_Depth' ]
                + '\t' + scores[ 'Score_Total_Origin_Depth_Filtered' ]
                + '\t' + scores[ 'Score_Mean_Origin_Depth_Filtered' ]
                + '\t' + scores[ 'Score_Total_Losses_Filtered' ]
                + '\t' + boot[ 'Bootstrap_Losses_Mean_Rank' ]
                + '\t' + boot[ 'Bootstrap_Losses_Rank_CI_Lower_95' ]
                + '\t' + boot[ 'Bootstrap_Losses_Rank_CI_Upper_95' ]
                + '\t' + boot[ 'Bootstrap_Losses_Pct_Times_Best' ]
                + '\t' + ( 'TRUE' if tied_losses else 'FALSE' )
                + '\t' + boot[ 'Bootstrap_Depth_Mean_Rank' ]
                + '\t' + boot[ 'Bootstrap_Depth_Rank_CI_Lower_95' ]
                + '\t' + boot[ 'Bootstrap_Depth_Rank_CI_Upper_95' ]
                + '\t' + boot[ 'Bootstrap_Depth_Pct_Times_Best' ]
                + '\t' + ( 'TRUE' if tied_depth else 'FALSE' )
                + '\t' + agreement
                + '\t' + boot[ 'Bootstrap_Iterations' ]
                + '\t' + boot[ 'Bootstrap_Seed' ]
                + '\n' )
            output.write( line )
    logger.info( f'Wrote final ranking: {output_ranking}' )

    output_best = output_5 / '5_ai-parsimony_best_structure.txt'
    with open( output_best, 'w' ) as output:
        output.write( '# parsimony_tree_structures BLOCK_ocl_orthogroups -- best species tree structure(s)\n' )
        output.write( f'# run_label: {run_label}\n' )
        output.write( f'# tie_threshold_pct: {tie_threshold_pct}\n' )
        output.write( '\n' )
        output.write( '# --- Loss-minimization criterion (Score_Total_Losses on full set, lower is better) ---\n' )
        output.write( f'Best_By_Losses_Score\t{best_score_losses}\n' )
        output.write( f'Best_By_Losses_Point_Estimate\t' + ','.join( f'structure_{s}' for s in best_by_losses ) + '\n' )
        output.write( f'Best_By_Losses_Bootstrap_Tied\t' + ','.join( f'structure_{s}' for s in tied_with_best_losses_bootstrap ) + '\n' )
        output.write( '\n' )
        output.write( '# --- Shallow-gain criterion (Score_Total_Origin_Depth_Filtered, larger is better) ---\n' )
        output.write( f'Best_By_Depth_Score\t{best_score_depth}\n' )
        output.write( f'Best_By_Depth_Point_Estimate\t' + ','.join( f'structure_{s}' for s in best_by_depth ) + '\n' )
        output.write( f'Best_By_Depth_Bootstrap_Tied\t' + ','.join( f'structure_{s}' for s in tied_with_best_depth_bootstrap ) + '\n' )
        output.write( '\n' )
        output.write( '# --- Agreement between criteria ---\n' )
        agreed = sorted( set( best_by_losses ) & set( best_by_depth ) )
        output.write( f'Best_Agreed_By_Both_Criteria_Point_Estimate\t' + ( ','.join( f'structure_{s}' for s in agreed ) if agreed else 'NONE' ) + '\n' )
        agreed_bootstrap = sorted( set( tied_with_best_losses_bootstrap ) & set( tied_with_best_depth_bootstrap ) )
        output.write( f'Best_Agreed_By_Both_Criteria_Bootstrap_Tied\t' + ( ','.join( f'structure_{s}' for s in agreed_bootstrap ) if agreed_bootstrap else 'NONE' ) + '\n' )
    logger.info( f'Wrote best-structure summary: {output_best}' )

    logger.info( f'Best by Score_Total_Losses: structure_{best_by_losses[ 0 ]} ({best_score_losses} losses)' )
    logger.info( f'Best by Score_Total_Origin_Depth_Filtered: structure_{best_by_depth[ 0 ]} ({best_score_depth} total filtered depth)' )
    if agreed:
        logger.info( f'  Both criteria agree on point-estimate best: {agreed}' )
    else:
        logger.info( f'  Criteria DISAGREE on point-estimate best (loss-min: {best_by_losses[ 0 ]}, depth: {best_by_depth[ 0 ]})' )


if __name__ == '__main__':
    main()
