#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Compute parsimony scores (5 states + origin-depth-based shallow-gain criterion)
# Human: Eric Edsinger

"""
Script 003 -- Compute parsimony scores per species tree structure.

Reads the per-structure OCL aggregate from script 002 and derives multiple
parsimony scores side-by-side.

5-state count scores (summed across orthogroups, unfiltered):
  Score_Total_Inherited_Absence    (A)
  Score_Total_Origins              (O) = Orthogroup_Count (constant)
  Score_Total_Conservation         (P)
  Score_Total_Losses               (L) -- loss-minimization PRIMARY
  Score_Total_Continued_Absence    (X)

Derived (unfiltered):
  Score_Total_Gains_Plus_Losses           = O + L
  Score_Conservation_to_Loss_Ratio        = P / max(1, L)
  Score_Mean_Losses_Per_Orthogroup        = L / max(1, OG)
  Score_Mean_Origin_Depth                 = Origin_Depth_Sum / max(1, OG)

Filtered shallow-gain (the SHALLOW-GAIN PRIMARY score, computed from the
per-structure parent-child table -- not from the OCL Origin_Phylogenetic_Path
column which has data-quality issues):
  Score_Total_Origin_Depth_Filtered       = Filtered_Origin_Depth_Sum
                                            (LARGER is better -- compatibility-like)
  Score_Mean_Origin_Depth_Filtered        = Filtered_Origin_Depth_Sum / max(1, Filtered_Orthogroup_Count)
  Score_Total_Losses_Filtered             = Filtered_Total_Loss (apples-to-apples loss-min on the same subset)
"""

import argparse
import logging
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser( description = 'Compute parsimony scores (5 states + origin-depth shallow-gain)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = Path( args.config ).resolve().parent

    output_3 = output_dir / '3-output'
    output_3.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    log_file = log_dir / '3_ai-log-compute_parsimony_scores.log'
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_file ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'compute_scores' )

    logger.info( 'Starting script 003: compute_parsimony_scores (with origin-depth)' )

    aggregate_path = output_dir / '2-output' / '2_ai-aggregate_ocl-per_structure.tsv'
    if not aggregate_path.is_file():
        logger.error( f'CRITICAL: aggregate file not found: {aggregate_path}' )
        sys.exit( 1 )

    score_rows = []
    with open( aggregate_path ) as input_aggregate:
        header_line = input_aggregate.readline().rstrip( '\n' )
        parts_header_line = header_line.split( '\t' )
        columns_to_index = { part.split( ' ' )[ 0 ]: i for i, part in enumerate( parts_header_line ) }

        for line in input_aggregate:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ columns_to_index[ 'Structure_ID' ] ]
            orthogroup_count = int( parts[ columns_to_index[ 'Orthogroup_Count' ] ] )
            total_blocks_per_structure = int( parts[ columns_to_index[ 'Total_Blocks_Per_Structure' ] ] )
            total_inherited_absence = int( parts[ columns_to_index[ 'Total_Inherited_Absence' ] ] )
            total_origins = int( parts[ columns_to_index[ 'Total_Origins' ] ] )
            total_conservation = int( parts[ columns_to_index[ 'Total_Conservation' ] ] )
            total_loss = int( parts[ columns_to_index[ 'Total_Loss' ] ] )
            total_continued_absence = int( parts[ columns_to_index[ 'Total_Continued_Absence' ] ] )
            origin_depth_sum = int( parts[ columns_to_index[ 'Origin_Depth_Sum' ] ] )
            filtered_orthogroup_count = int( parts[ columns_to_index[ 'Filtered_Orthogroup_Count' ] ] )
            filtered_origin_depth_sum = int( parts[ columns_to_index[ 'Filtered_Origin_Depth_Sum' ] ] )
            filtered_total_loss = int( parts[ columns_to_index[ 'Filtered_Total_Loss' ] ] )

            score_rows.append( {
                'Structure_ID': structure_id,
                'Orthogroup_Count': orthogroup_count,
                'Total_Blocks_Per_Structure': total_blocks_per_structure,
                'Filtered_Orthogroup_Count': filtered_orthogroup_count,
                'Score_Total_Inherited_Absence': total_inherited_absence,
                'Score_Total_Origins': total_origins,
                'Score_Total_Conservation': total_conservation,
                'Score_Total_Losses': total_loss,
                'Score_Total_Continued_Absence': total_continued_absence,
                'Score_Total_Gains_Plus_Losses': total_origins + total_loss,
                'Score_Conservation_to_Loss_Ratio': total_conservation / max( 1, total_loss ),
                'Score_Mean_Losses_Per_Orthogroup': total_loss / max( 1, orthogroup_count ),
                'Score_Mean_Origin_Depth': origin_depth_sum / max( 1, orthogroup_count ),
                'Score_Total_Origin_Depth_Filtered': filtered_origin_depth_sum,
                'Score_Mean_Origin_Depth_Filtered': filtered_origin_depth_sum / max( 1, filtered_orthogroup_count ),
                'Score_Total_Losses_Filtered': filtered_total_loss,
            } )

    if not score_rows:
        logger.error( 'CRITICAL: no rows in aggregate -- aborting' )
        sys.exit( 1 )

    output_scores = output_3 / '3_ai-parsimony_scores-per_structure.tsv'
    with open( output_scores, 'w' ) as output:
        output.write( 'Structure_ID (three digit identifier from manifest)' )
        output.write( '\tOrthogroup_Count (full unfiltered orthogroup count)' )
        output.write( '\tTotal_Blocks_Per_Structure (number of phylogenetic blocks)' )
        output.write( '\tFiltered_Orthogroup_Count (orthogroups in the Species_Count filter window; topology informative subset)' )
        output.write( '\tScore_Total_Inherited_Absence (A state count summed across orthogroups)' )
        output.write( '\tScore_Total_Origins (O state count; equals Orthogroup_Count under Dollo; constant across structures)' )
        output.write( '\tScore_Total_Conservation (P state count; higher is better)' )
        output.write( '\tScore_Total_Losses (L state count; lower is better; loss minimization parsimony)' )
        output.write( '\tScore_Total_Continued_Absence (X state count; lower is better)' )
        output.write( '\tScore_Total_Gains_Plus_Losses (Score_Total_Origins plus Score_Total_Losses; classical Dollo event count; lower is better)' )
        output.write( '\tScore_Conservation_to_Loss_Ratio (P over max 1 L; higher is better)' )
        output.write( '\tScore_Mean_Losses_Per_Orthogroup (L over OG; lower is better)' )
        output.write( '\tScore_Mean_Origin_Depth (mean origin block child depth across all unfiltered orthogroups; larger means origins sit closer to leaves on average)' )
        output.write( '\tScore_Total_Origin_Depth_Filtered (sum of origin block child depths across filtered orthogroups; SHALLOW GAIN parsimony score; LARGER is better; compatibility like criterion capturing pure topology fit by avoiding the biological loss baseline; depth computed from per structure parent child table not from the OCL Origin_Phylogenetic_Path which has data quality issues)' )
        output.write( '\tScore_Mean_Origin_Depth_Filtered (Score_Total_Origin_Depth_Filtered divided by Filtered_Orthogroup_Count; larger is better)' )
        output.write( '\tScore_Total_Losses_Filtered (sum of Loss_Events across the filtered subset; lower is better)\n' )
        for row in score_rows:
            line = ( row[ 'Structure_ID' ]
                + '\t' + str( row[ 'Orthogroup_Count' ] )
                + '\t' + str( row[ 'Total_Blocks_Per_Structure' ] )
                + '\t' + str( row[ 'Filtered_Orthogroup_Count' ] )
                + '\t' + str( row[ 'Score_Total_Inherited_Absence' ] )
                + '\t' + str( row[ 'Score_Total_Origins' ] )
                + '\t' + str( row[ 'Score_Total_Conservation' ] )
                + '\t' + str( row[ 'Score_Total_Losses' ] )
                + '\t' + str( row[ 'Score_Total_Continued_Absence' ] )
                + '\t' + str( row[ 'Score_Total_Gains_Plus_Losses' ] )
                + '\t' + format( row[ 'Score_Conservation_to_Loss_Ratio' ], '.6f' )
                + '\t' + format( row[ 'Score_Mean_Losses_Per_Orthogroup' ], '.6f' )
                + '\t' + format( row[ 'Score_Mean_Origin_Depth' ], '.6f' )
                + '\t' + str( row[ 'Score_Total_Origin_Depth_Filtered' ] )
                + '\t' + format( row[ 'Score_Mean_Origin_Depth_Filtered' ], '.6f' )
                + '\t' + str( row[ 'Score_Total_Losses_Filtered' ] )
                + '\n' )
            output.write( line )
    logger.info( f'Wrote parsimony scores: {output_scores}' )
    logger.info( f'Structures scored: {len( score_rows )}' )


if __name__ == '__main__':
    main()
