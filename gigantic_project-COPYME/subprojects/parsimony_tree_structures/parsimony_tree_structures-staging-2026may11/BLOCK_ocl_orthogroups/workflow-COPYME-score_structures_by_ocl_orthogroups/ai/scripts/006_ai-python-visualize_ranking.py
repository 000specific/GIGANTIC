#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Visualize dual parsimony ranking (loss-min and shallow-gain) with colorblind-safe figures
# Human: Eric Edsinger

"""
Script 006 -- Visualize ranking (dual criteria).

Reads the final dual ranking from 5-output and writes:
  6_ai-score_total_losses-bar_chart.png
      Bar chart of Score_Total_Losses per structure, sorted by Final_Rank_Losses.
  6_ai-shallow_gain-bar_chart.png
      Bar chart of Score_Total_Origin_Depth_Filtered, sorted by Final_Rank_Depth.
  6_ai-five_state_counts-stacked_bar.png
      Stacked bar chart of A / O / P / L / X counts per structure (loss-rank order).
  6_ai-all_scores-heatmap.png
      Heatmap of all scores per structure, normalized per column so 0 = best.
  6_ai-rank_agreement-scatter.png
      Scatter plot of Final_Rank_Losses vs Final_Rank_Depth -- the
      diagnostic plot. Points near the diagonal show consistent ranking;
      off-diagonal points reveal where one criterion disagrees with the other.

Palette: LightBlue2DarkBlue10Steps and Blue2Green14Steps (CLAUDE.md
colorblind-safe references).
"""

import argparse
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
import numpy as np
import yaml


COLORBLIND_SAFE_BLUE = '#003FFF'
COLORBLIND_SAFE_LIGHT_BLUE = '#7FD4FF'
COLORBLIND_SAFE_GREEN = '#00FF00'
COLORBLIND_SAFE_HEATMAP_GRADIENT = [
    '#E5FFFF', '#CCFAFF', '#B2F2FF', '#99E5FF', '#7FD4FF',
    '#65BFFF', '#4CA5FF', '#3288FF', '#1965FF', '#003FFF',
]
STATE_COLORS = {
    'A': '#0000FF',
    'O': '#6565FF',
    'P': '#B2B2FF',
    'L': '#65FF65',
    'X': '#B2FFB2',
}
STATE_DESCRIPTIONS = {
    'A': 'Inherited Absence (pre-origin)',
    'O': 'Origin (gain)',
    'P': 'Inherited Presence (conservation)',
    'L': 'Loss',
    'X': 'Inherited Loss (post-loss)',
}
AGREEMENT_COLORS = {
    'BOTH_AGREE': '#003FFF',
    'LOSSES_ONLY': '#65FF65',
    'DEPTH_ONLY': '#1965FF',
    'NEITHER': '#B2B2FF',
}


def main():
    parser = argparse.ArgumentParser( description = 'Visualize dual parsimony ranking' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_6 = output_dir / '6-output' / 'figures'
    output_6.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    log_file = log_dir / '6_ai-log-visualize_ranking.log'
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_file ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'visualize' )

    logger.info( 'Starting script 006: visualize dual ranking' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )
    run_label = config.get( 'run_label', 'UNSPECIFIED' )

    ranking_path = output_dir / '5-output' / '5_ai-parsimony_ranking-structures.tsv'
    if not ranking_path.is_file():
        logger.error( f'CRITICAL: ranking file not found: {ranking_path}' )
        sys.exit( 1 )

    rows = []
    with open( ranking_path ) as input_ranking:
        header_line = input_ranking.readline().rstrip( '\n' )
        headers = [ h.split( ' ' )[ 0 ] for h in header_line.split( '\t' ) ]
        for line in input_ranking:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            rows.append( dict( zip( headers, parts ) ) )

    if not rows:
        logger.error( 'CRITICAL: no rows in ranking table' )
        sys.exit( 1 )

    rows_by_loss_rank = sorted( rows, key = lambda r: ( float( r[ 'Final_Rank_Losses' ] ), r[ 'Structure_ID' ] ) )
    rows_by_path_rank = sorted( rows, key = lambda r: ( float( r[ 'Final_Rank_Depth' ] ), r[ 'Structure_ID' ] ) )

    fig_width_for_rows = lambda data: max( 8.0, 0.18 * len( data ) )

    # --- Figure 1: Score_Total_Losses bar chart (sorted by loss rank) ---
    structure_labels = [ 's_' + row[ 'Structure_ID' ] for row in rows_by_loss_rank ]
    losses_values = [ float( row[ 'Score_Total_Losses' ] ) for row in rows_by_loss_rank ]
    fig, axis = plt.subplots( figsize = ( fig_width_for_rows( rows_by_loss_rank ), 5.0 ) )
    bar_colors = [ COLORBLIND_SAFE_LIGHT_BLUE for _ in rows_by_loss_rank ]
    for index, row in enumerate( rows_by_loss_rank ):
        if float( row[ 'Final_Rank_Losses' ] ) <= 1.5:
            bar_colors[ index ] = COLORBLIND_SAFE_BLUE
    axis.bar( range( len( rows_by_loss_rank ) ), losses_values, color = bar_colors, edgecolor = 'black', linewidth = 0.3 )
    axis.set_xticks( range( len( rows_by_loss_rank ) ) )
    axis.set_xticklabels( structure_labels, rotation = 90, fontsize = 6 )
    axis.set_xlabel( 'Species tree structure (sorted by Final_Rank_Losses ascending)' )
    axis.set_ylabel( 'Score_Total_Losses (sum of Loss_Events; lower is more parsimonious)' )
    axis.set_title( f'parsimony_tree_structures / BLOCK_ocl_orthogroups\nLoss minimization criterion\nrun_label: {run_label}' )
    axis.grid( axis = 'y', linestyle = ':', alpha = 0.4 )
    fig.tight_layout()
    output_bar = output_6 / '6_ai-score_total_losses-bar_chart.png'
    fig.savefig( output_bar, dpi = 150 )
    plt.close( fig )
    logger.info( f'Wrote loss-min bar chart: {output_bar}' )

    # --- Figure 2: Shallow-gain bar chart (sorted by path-length rank) ---
    structure_labels_p = [ 's_' + row[ 'Structure_ID' ] for row in rows_by_path_rank ]
    pathlen_values = [ float( row[ 'Score_Total_Origin_Depth_Filtered' ] ) for row in rows_by_path_rank ]
    fig, axis = plt.subplots( figsize = ( fig_width_for_rows( rows_by_path_rank ), 5.0 ) )
    bar_colors = [ COLORBLIND_SAFE_LIGHT_BLUE for _ in rows_by_path_rank ]
    for index, row in enumerate( rows_by_path_rank ):
        if float( row[ 'Final_Rank_Depth' ] ) <= 1.5:
            bar_colors[ index ] = COLORBLIND_SAFE_BLUE
    axis.bar( range( len( rows_by_path_rank ) ), pathlen_values, color = bar_colors, edgecolor = 'black', linewidth = 0.3 )
    axis.set_xticks( range( len( rows_by_path_rank ) ) )
    axis.set_xticklabels( structure_labels_p, rotation = 90, fontsize = 6 )
    axis.set_xlabel( 'Species tree structure (sorted by Final_Rank_Depth ascending)' )
    axis.set_ylabel( 'Score_Total_Origin_Depth_Filtered (larger is more parsimonious; shallower gains)' )
    axis.set_title( f'parsimony_tree_structures / BLOCK_ocl_orthogroups\nShallow gain criterion (compatibility-like)\nrun_label: {run_label}' )
    axis.grid( axis = 'y', linestyle = ':', alpha = 0.4 )
    fig.tight_layout()
    output_path_bar = output_6 / '6_ai-shallow_gain-bar_chart.png'
    fig.savefig( output_path_bar, dpi = 150 )
    plt.close( fig )
    logger.info( f'Wrote shallow-gain bar chart: {output_path_bar}' )

    # --- Figure 3: 5-state stacked bar (sorted by loss rank) ---
    states = [ 'A', 'O', 'P', 'L', 'X' ]
    state_columns = {
        'A': 'Score_Total_Inherited_Absence',
        'O': 'Score_Total_Origins',
        'P': 'Score_Total_Conservation',
        'L': 'Score_Total_Losses',
        'X': 'Score_Total_Continued_Absence',
    }
    state_matrix = np.zeros( ( len( states ), len( rows_by_loss_rank ) ), dtype = float )
    for column_index, row in enumerate( rows_by_loss_rank ):
        for state_index, state in enumerate( states ):
            state_matrix[ state_index, column_index ] = float( row[ state_columns[ state ] ] )
    fig, axis = plt.subplots( figsize = ( fig_width_for_rows( rows_by_loss_rank ), 6.0 ) )
    bottom = np.zeros( len( rows_by_loss_rank ), dtype = float )
    for state_index, state in enumerate( states ):
        axis.bar(
            range( len( rows_by_loss_rank ) ),
            state_matrix[ state_index ],
            bottom = bottom,
            color = STATE_COLORS[ state ],
            edgecolor = 'black',
            linewidth = 0.2,
            label = f'{state}: {STATE_DESCRIPTIONS[ state ]}',
        )
        bottom += state_matrix[ state_index ]
    axis.set_xticks( range( len( rows_by_loss_rank ) ) )
    axis.set_xticklabels( structure_labels, rotation = 90, fontsize = 6 )
    axis.set_xlabel( 'Species tree structure (sorted by Final_Rank_Losses ascending)' )
    axis.set_ylabel( 'Block-state count summed across orthogroups' )
    axis.set_title( f'parsimony_tree_structures / BLOCK_ocl_orthogroups\nFive-state OCL composition (loss-min order)\nrun_label: {run_label}' )
    axis.legend( loc = 'upper right', fontsize = 7, framealpha = 0.9 )
    fig.tight_layout()
    output_stacked = output_6 / '6_ai-five_state_counts-stacked_bar.png'
    fig.savefig( output_stacked, dpi = 150 )
    plt.close( fig )
    logger.info( f'Wrote 5-state stacked bar: {output_stacked}' )

    # --- Figure 4: heatmap of all scores ---
    score_columns = [
        'Score_Total_Inherited_Absence',
        'Score_Total_Origins',
        'Score_Total_Conservation',
        'Score_Total_Losses',
        'Score_Total_Continued_Absence',
        'Score_Total_Gains_Plus_Losses',
        'Score_Conservation_to_Loss_Ratio',
        'Score_Mean_Losses_Per_Orthogroup',
        'Score_Mean_Origin_Depth',
        'Score_Total_Origin_Depth_Filtered',
        'Score_Mean_Origin_Depth_Filtered',
        'Score_Total_Losses_Filtered',
    ]
    higher_is_better = {
        'Score_Total_Conservation',
        'Score_Conservation_to_Loss_Ratio',
        'Score_Mean_Origin_Depth',
        'Score_Total_Origin_Depth_Filtered',
        'Score_Mean_Origin_Depth_Filtered',
    }
    raw_matrix = np.zeros( ( len( rows_by_loss_rank ), len( score_columns ) ), dtype = float )
    for row_index, row in enumerate( rows_by_loss_rank ):
        for column_index, column_name in enumerate( score_columns ):
            raw_matrix[ row_index, column_index ] = float( row[ column_name ] )
    normalized_matrix = np.zeros_like( raw_matrix )
    for column_index, column_name in enumerate( score_columns ):
        column = raw_matrix[ :, column_index ]
        column_min = column.min()
        column_max = column.max()
        if column_max - column_min == 0:
            normalized_matrix[ :, column_index ] = 0.0
        else:
            normalized = ( column - column_min ) / ( column_max - column_min )
            if column_name in higher_is_better:
                normalized = 1.0 - normalized
            normalized_matrix[ :, column_index ] = normalized
    fig_height = max( 6.0, 0.15 * len( rows_by_loss_rank ) )
    fig, axis = plt.subplots( figsize = ( 11.0, fig_height ) )
    cmap = matplotlib.colors.ListedColormap( COLORBLIND_SAFE_HEATMAP_GRADIENT )
    image = axis.imshow( normalized_matrix, aspect = 'auto', cmap = cmap, vmin = 0.0, vmax = 1.0 )
    axis.set_xticks( range( len( score_columns ) ) )
    axis.set_xticklabels( score_columns, rotation = 30, ha = 'right', fontsize = 7 )
    axis.set_yticks( range( len( rows_by_loss_rank ) ) )
    axis.set_yticklabels( structure_labels, fontsize = 6 )
    axis.set_xlabel( 'Parsimony score (oriented so 0 = best after column normalization)' )
    axis.set_ylabel( 'Species tree structure (Final_Rank_Losses order)' )
    axis.set_title( f'parsimony_tree_structures / BLOCK_ocl_orthogroups\nAll scores normalized 0 best to 1 worst\nrun_label: {run_label}' )
    colorbar = fig.colorbar( image, ax = axis, fraction = 0.04 )
    colorbar.set_label( 'Normalized parsimony cost (0 = best, 1 = worst)' )
    fig.tight_layout()
    output_heatmap = output_6 / '6_ai-all_scores-heatmap.png'
    fig.savefig( output_heatmap, dpi = 150 )
    plt.close( fig )
    logger.info( f'Wrote heatmap: {output_heatmap}' )

    # --- Figure 5: agreement scatter ---
    fig, axis = plt.subplots( figsize = ( 7.0, 7.0 ) )
    for row in rows:
        x = float( row[ 'Final_Rank_Losses' ] )
        y = float( row[ 'Final_Rank_Depth' ] )
        agreement = row.get( 'Criteria_Agreement', 'NEITHER' )
        color = AGREEMENT_COLORS.get( agreement, '#888888' )
        axis.scatter( x, y, c = color, s = 25, edgecolor = 'black', linewidth = 0.3 )
        if x <= 5 or y <= 5:
            axis.annotate( row[ 'Structure_ID' ], ( x, y ), fontsize = 6, alpha = 0.7,
                xytext = ( 4, 4 ), textcoords = 'offset points' )
    n_total = len( rows )
    axis.plot( [ 0, n_total + 1 ], [ 0, n_total + 1 ], color = '#888888', linestyle = '--', linewidth = 0.5, alpha = 0.5 )
    axis.set_xlim( 0, n_total + 1 )
    axis.set_ylim( 0, n_total + 1 )
    axis.invert_yaxis()
    axis.invert_xaxis()
    axis.set_xlabel( 'Final_Rank_Losses (1 = best by loss-min, top-right is best)' )
    axis.set_ylabel( 'Final_Rank_Depth (1 = best by shallow-gain, top-right is best)' )
    axis.set_title( f'parsimony_tree_structures / BLOCK_ocl_orthogroups\nRanking agreement between loss-min and shallow-gain criteria\nrun_label: {run_label}' )
    axis.grid( linestyle = ':', alpha = 0.4 )
    legend_handles = [
        plt.Line2D( [ 0 ], [ 0 ], marker = 'o', color = 'w', markerfacecolor = AGREEMENT_COLORS[ k ],
            markersize = 8, label = k, markeredgecolor = 'black' )
        for k in [ 'BOTH_AGREE', 'LOSSES_ONLY', 'DEPTH_ONLY', 'NEITHER' ]
    ]
    axis.legend( handles = legend_handles, loc = 'lower left', fontsize = 8 )
    fig.tight_layout()
    output_scatter = output_6 / '6_ai-rank_agreement-scatter.png'
    fig.savefig( output_scatter, dpi = 150 )
    plt.close( fig )
    logger.info( f'Wrote agreement scatter: {output_scatter}' )


if __name__ == '__main__':
    main()
