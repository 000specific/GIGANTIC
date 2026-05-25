#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Aggregate all 5 OCL block-states per structure plus origin depth (computed from parent-child table, not from buggy OCL path field) plus per-block gain distribution
# Human: Eric Edsinger

"""
Script 002 -- Aggregate OCL per structure (all 5 states + reliably computed origin depths).

KEY DEPARTURE FROM EARLIER VERSION: the upstream OCL pipeline emits
Origin_Phylogenetic_Path = "NA" for many orthogroups whose origin block is
actually mid-tree (e.g., C082_Metazoa::C087_Metazoa_Subclade_1 with NA path).
That is an upstream-data-quality bug, not a deep-origin marker. Using the
NA-laden path field collapses the shallow-gain signal to a constant.

Fix here: compute origin DEPTH per orthogroup directly from the parent-child
table of each structure (read from
trees_species/output_to_input/BLOCK_permutations_and_features/Species_Parent_Child_Relationships/).
Depth = number of edges from C000_OOL to the child endpoint of the origin
block. This is fully determined by the structure's topology and never falls
back to NA.

Aggregates per structure:
  - All 5 block-state counts (A / O / P / L / X)
  - Origin_Depth_Sum (full unfiltered) -- sum across orthogroups
  - Filtered_Orthogroup_Count + Filtered_Origin_Depth_Sum (Species_Count
    in [min, max]) -- the topology-informative subset for shallow-gain ranking
  - Filtered_Total_Loss -- losses on the same filtered subset
  - Per-block gain distribution

Writes:
  2-output/2_ai-aggregate_ocl-per_structure.tsv
  2-output/2_ai-gain_distribution-per_block.tsv
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

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
    """Read a per-structure parent_child_relationships.tsv and BFS from root
    to build a clade_id_name -> depth-from-root map. Depth of root = 0."""
    parents_to_children = defaultdict( list )
    # Phylogenetic_Block	Parent_Clade_ID_Name	Child_Clade_ID_Name
    # C000_OOL::C071_Basal	C000_OOL	C071_Basal
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


def main():
    parser = argparse.ArgumentParser( description = 'Aggregate OCL events per structure (depth from parent-child table)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_2 = output_dir / '2-output'
    output_2.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    log_file = log_dir / '2_ai-log-aggregate_ocl_per_structure.log'
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_file ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'aggregate_ocl' )

    logger.info( 'Starting script 002: aggregate_ocl_per_structure (depth from parent-child table)' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )

    ocl_orthogroups_dir = ( workflow_dir / config[ 'inputs' ][ 'ocl_orthogroups_dir' ] ).resolve()
    trees_species_dir = ( workflow_dir / config[ 'inputs' ][ 'trees_species_dir' ] ).resolve()
    structure_manifest_path = ( workflow_dir / config[ 'inputs' ][ 'structure_manifest' ] ).resolve()

    filter_config = config.get( 'filter', {} ) or {}
    min_species_count = int( filter_config.get( 'min_species_count', 2 ) )
    max_species_count_raw = filter_config.get( 'max_species_count', None )
    max_species_count = int( max_species_count_raw ) if max_species_count_raw is not None else 10 ** 9
    logger.info( f'Filter: min_species_count={min_species_count}  max_species_count={max_species_count}' )

    parent_child_dir = trees_species_dir / 'Species_Parent_Child_Relationships'
    if not parent_child_dir.is_dir():
        logger.error( f'CRITICAL: parent-child dir not found: {parent_child_dir}' )
        sys.exit( 1 )

    # Total_Blocks_Per_Structure
    trees_species_blocks_file = trees_species_dir / 'Species_Phylogenetic_Blocks' / '6_ai-phylogenetic_blocks-all_105_structures.tsv'
    structures_to_total_blocks = defaultdict( int )
    with open( trees_species_blocks_file ) as input_trees_species:
        input_trees_species.readline()
        for line in input_trees_species:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ 0 ]
            if structure_id.startswith( 'structure_' ):
                structure_id = structure_id[ len( 'structure_' ): ]
            structures_to_total_blocks[ structure_id ] += 1

    logger.info( f'Loaded Total_Blocks_Per_Structure for {len( structures_to_total_blocks )} structures' )

    # Read manifest
    structure_ids = []
    with open( structure_manifest_path ) as input_manifest:
        input_manifest.readline()
        for line in input_manifest:
            line = line.strip()
            if line and not line.startswith( '#' ):
                structure_ids.append( line )

    if not structure_ids:
        logger.error( 'CRITICAL: structure_manifest is empty' )
        sys.exit( 1 )

    logger.info( f'Aggregating {len( structure_ids )} structures' )

    aggregate_rows = []
    gain_distribution_rows = []

    for structure_id in structure_ids:
        ocl_summary_path = ocl_orthogroups_dir / f'structure_{structure_id}' / '4_ai-orthogroups-complete_ocl_summary.tsv'
        parent_child_path = parent_child_dir / f'5_ai-structure_{structure_id}_parent_child_relationships.tsv'

        if not ocl_summary_path.is_file():
            logger.error( f'CRITICAL: OCL summary file not found: {ocl_summary_path}' )
            sys.exit( 1 )
        if not parent_child_path.is_file():
            logger.error( f'CRITICAL: parent-child file not found: {parent_child_path}' )
            sys.exit( 1 )

        total_blocks_per_structure = structures_to_total_blocks.get( structure_id, 0 )
        if total_blocks_per_structure == 0:
            logger.error( f'CRITICAL: Total_Blocks_Per_Structure unknown for structure_{structure_id}' )
            sys.exit( 1 )

        clade_id_names_to_depths = build_depth_map( parent_child_path )

        with open( ocl_summary_path ) as input_summary:
            header_line = input_summary.readline()
            columns_to_index = parse_header_to_index( header_line )

            index_loss = columns_to_index[ 'Loss_Events' ]
            index_conservation = columns_to_index[ 'Conservation_Events' ]
            index_continued_absence = columns_to_index[ 'Continued_Absence_Events' ]
            index_total_scored_blocks = columns_to_index[ 'Total_Scored_Blocks' ]
            index_origin_block = columns_to_index[ 'Origin_Phylogenetic_Block' ]
            index_species_count = columns_to_index[ 'Species_Count' ]

            total_loss = 0
            total_conservation = 0
            total_continued_absence = 0
            total_scored_blocks_sum = 0
            origin_depth_sum = 0
            orthogroup_count = 0
            filtered_orthogroup_count = 0
            filtered_origin_depth_sum = 0
            filtered_total_loss = 0
            origin_blocks_to_counts = defaultdict( int )
            missing_depth_count = 0

            for line in input_summary:
                parts = line.rstrip( '\n' ).split( '\t' )
                loss_value = int( parts[ index_loss ] )
                species_count = int( parts[ index_species_count ] )
                origin_block = strip_state_suffix( parts[ index_origin_block ] )
                child_clade = child_from_block( origin_block )

                if child_clade is None or child_clade not in clade_id_names_to_depths:
                    missing_depth_count += 1
                    origin_depth = 1  # fallback for unparseable / unknown -- treated as deepest non-root
                else:
                    origin_depth = clade_id_names_to_depths[ child_clade ]

                total_loss += loss_value
                total_conservation += int( parts[ index_conservation ] )
                total_continued_absence += int( parts[ index_continued_absence ] )
                total_scored_blocks_sum += int( parts[ index_total_scored_blocks ] )
                origin_depth_sum += origin_depth
                origin_blocks_to_counts[ origin_block ] += 1
                orthogroup_count += 1

                if min_species_count <= species_count <= max_species_count:
                    filtered_orthogroup_count += 1
                    filtered_origin_depth_sum += origin_depth
                    filtered_total_loss += loss_value

        if missing_depth_count > 0:
            logger.warning(
                f'structure_{structure_id}: {missing_depth_count} orthogroups had unparseable/unmapped origin blocks; depth set to 1 as fallback'
            )

        # 5-state count math (unfiltered)
        total_origins = orthogroup_count
        total_inherited_absence = orthogroup_count * ( total_blocks_per_structure - 1 ) - total_scored_blocks_sum

        expected_grand_total = orthogroup_count * total_blocks_per_structure
        actual_grand_total = total_inherited_absence + total_origins + total_conservation + total_loss + total_continued_absence
        if expected_grand_total != actual_grand_total:
            logger.error(
                f'CRITICAL: 5-state count math failed for structure_{structure_id}. '
                f'Expected sum {expected_grand_total} got {actual_grand_total}'
            )
            sys.exit( 1 )

        aggregate_rows.append( {
            'Structure_ID': structure_id,
            'Orthogroup_Count': orthogroup_count,
            'Total_Blocks_Per_Structure': total_blocks_per_structure,
            'Total_Inherited_Absence': total_inherited_absence,
            'Total_Origins': total_origins,
            'Total_Conservation': total_conservation,
            'Total_Loss': total_loss,
            'Total_Continued_Absence': total_continued_absence,
            'Total_Scored_Blocks_Sum': total_scored_blocks_sum,
            'Origin_Depth_Sum': origin_depth_sum,
            'Filtered_Orthogroup_Count': filtered_orthogroup_count,
            'Filtered_Origin_Depth_Sum': filtered_origin_depth_sum,
            'Filtered_Total_Loss': filtered_total_loss,
        } )

        for block, count in sorted( origin_blocks_to_counts.items() ):
            gain_distribution_rows.append( ( structure_id, block, count ) )

        logger.info(
            f'structure_{structure_id}: OG={orthogroup_count} (filt={filtered_orthogroup_count}) '
            f'L={total_loss} (filt_L={filtered_total_loss}) '
            f'origin_depth_sum={origin_depth_sum} (filt={filtered_origin_depth_sum}) '
            f'unique_origin_blocks={len( origin_blocks_to_counts )}'
        )

    output_aggregate = output_2 / '2_ai-aggregate_ocl-per_structure.tsv'
    with open( output_aggregate, 'w' ) as output:
        output.write( 'Structure_ID (three digit identifier from manifest)' )
        output.write( '\tOrthogroup_Count (number of orthogroups; full unfiltered set)' )
        output.write( '\tTotal_Blocks_Per_Structure (number of phylogenetic blocks in this species tree structure)' )
        output.write( '\tTotal_Inherited_Absence (A state count summed across all orthogroups; derived as Orthogroup_Count times Total_Blocks_Per_Structure minus 1 minus Total_Scored_Blocks_Sum)' )
        output.write( '\tTotal_Origins (O state count; equals Orthogroup_Count under Dollo single origin per orthogroup)' )
        output.write( '\tTotal_Conservation (P state count; sum of Conservation_Events)' )
        output.write( '\tTotal_Loss (L state count; sum of Loss_Events)' )
        output.write( '\tTotal_Continued_Absence (X state count; sum of Continued_Absence_Events)' )
        output.write( '\tTotal_Scored_Blocks_Sum (sum of Total_Scored_Blocks; equals Total_Conservation plus Total_Loss plus Total_Continued_Absence)' )
        output.write( '\tOrigin_Depth_Sum (sum across all unfiltered orthogroups of the depth of the origin block child clade from C000_OOL; computed from the per structure parent-child table not the OCL Origin_Phylogenetic_Path which has data quality issues; larger means origins sit on average closer to leaves)' )
        output.write( '\tFiltered_Orthogroup_Count (number of orthogroups with Species_Count in the configured filter window)' )
        output.write( '\tFiltered_Origin_Depth_Sum (sum across filtered orthogroups of the depth of the origin block child clade from C000_OOL; SHALLOW GAIN parsimony input; LARGER is better)' )
        output.write( '\tFiltered_Total_Loss (sum of Loss_Events across the same filtered orthogroup subset; for apples to apples comparison with the shallow gain score)\n' )
        for row in aggregate_rows:
            line = ( row[ 'Structure_ID' ]
                + '\t' + str( row[ 'Orthogroup_Count' ] )
                + '\t' + str( row[ 'Total_Blocks_Per_Structure' ] )
                + '\t' + str( row[ 'Total_Inherited_Absence' ] )
                + '\t' + str( row[ 'Total_Origins' ] )
                + '\t' + str( row[ 'Total_Conservation' ] )
                + '\t' + str( row[ 'Total_Loss' ] )
                + '\t' + str( row[ 'Total_Continued_Absence' ] )
                + '\t' + str( row[ 'Total_Scored_Blocks_Sum' ] )
                + '\t' + str( row[ 'Origin_Depth_Sum' ] )
                + '\t' + str( row[ 'Filtered_Orthogroup_Count' ] )
                + '\t' + str( row[ 'Filtered_Origin_Depth_Sum' ] )
                + '\t' + str( row[ 'Filtered_Total_Loss' ] )
                + '\n' )
            output.write( line )
    logger.info( f'Wrote aggregate table: {output_aggregate}' )

    output_gain_distribution = output_2 / '2_ai-gain_distribution-per_block.tsv'
    with open( output_gain_distribution, 'w' ) as output:
        output.write( 'Structure_ID (three digit identifier from manifest)' )
        output.write( '\tPhylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name colon colon Child_Clade_ID_Name)' )
        output.write( '\tGain_Count (number of orthogroup origins landing on this phylogenetic block under this species tree structure)\n' )
        for structure_id, block, count in gain_distribution_rows:
            line = structure_id + '\t' + block + '\t' + str( count ) + '\n'
            output.write( line )
    logger.info( f'Wrote gain distribution: {output_gain_distribution} ({len( gain_distribution_rows )} structure-block rows)' )


if __name__ == '__main__':
    main()
