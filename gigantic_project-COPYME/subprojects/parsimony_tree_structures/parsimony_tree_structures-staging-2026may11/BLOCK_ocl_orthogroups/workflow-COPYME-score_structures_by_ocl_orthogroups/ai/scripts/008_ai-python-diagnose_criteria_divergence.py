#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 12 | Purpose: Diagnose divergence between loss-minimization and shallow-gain rankings; surface per-orthogroup shifts and per-structure unresolved zone topology
# Human: Eric Edsinger

"""
Script 008 -- Diagnose criteria divergence.

Captures the post-hoc analyses needed to interpret a dual-ranking result:

  1. **Spearman + Pearson rank correlation** between Final_Rank_Losses and
     Final_Rank_Depth across all structures. Negative or weakly positive
     correlation indicates the two criteria see different signals.

  2. **Per-orthogroup origin-block shifts** between three pairs of structures
     of interest:
       (a) user input species tree (structure_001) vs best-by-losses
       (b) user input species tree (structure_001) vs best-by-depth
       (c) best-by-losses vs best-by-depth
     For each filtered orthogroup whose origin block differs between the
     two structures, emit Δ_depth and Δ_loss contributions.

  3. **Unresolved zone topology per structure** -- uniform 5-clade newick
     derived from the per-structure parent-child table for every structure
     in the manifest, treating the five basal metazoan clades (Ctenophora,
     Placozoa, Cnidaria, Bilateria, Porifera) as terminal. Lets the analyst
     see the topology that each Structure_ID represents in a comparable
     format.

Writes to 8-output/.
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import yaml


UNRESOLVED_ZONE_CLADES = {
    'C086_Ctenophora',
    'C090_Porifera',
    'C095_Placozoa',
    'C102_Cnidaria',
    'C103_Bilateria',
}
METAZOA_ROOT = 'C082_Metazoa'
SHORT_LABELS = {
    'C086_Ctenophora': 'Cten',
    'C090_Porifera': 'Pori',
    'C095_Placozoa': 'Plac',
    'C102_Cnidaria': 'Cnid',
    'C103_Bilateria': 'Bila',
}


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


def load_parent_child( parent_child_path ):
    """Return (parents_to_children, all_clades_seen)."""
    parents_to_children = defaultdict( list )
    all_clades = set()
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
            all_clades.add( parts[ index_parent ] )
            all_clades.add( parts[ index_child ] )
    return parents_to_children, all_clades


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


def render_unresolved_zone_newick( parents_to_children, metazoa_root = METAZOA_ROOT, leaf_clades = UNRESOLVED_ZONE_CLADES ):
    """Recursively render the subtree at metazoa_root, but stop at any of the
    leaf_clades (treat them as terminal leaves regardless of their actual
    children). Returns a newick string without semicolon."""
    def render( node ):
        if node in leaf_clades:
            return node
        children = parents_to_children.get( node, [] )
        if len( children ) == 0:
            return node
        return '(' + ','.join( render( c ) for c in children ) + ')' + node
    return render( metazoa_root )


def describe_unresolved_zone( parents_to_children, metazoa_root = METAZOA_ROOT, leaf_clades = UNRESOLVED_ZONE_CLADES ):
    """Identify (a) which leaf clade is sister-to-rest at the deepest split
    inside metazoa_root, and (b) the deepest pair of leaf clades.
    Returns (sister_label, deepest_pair_labels_or_None)."""
    def collect_leaves( node ):
        if node in leaf_clades:
            return [ node ]
        leaves = []
        for c in parents_to_children.get( node, () ):
            leaves.extend( collect_leaves( c ) )
        return leaves

    def deepest_pair( node ):
        # find the deepest internal node both of whose collected leaves are leaf_clades
        children = parents_to_children.get( node, () )
        if not children:
            return None
        # Recurse deepest-first
        for c in children:
            inner = deepest_pair( c )
            if inner is not None:
                return inner
        # No deeper internal pair returned -- this node is the deepest internal node above leaves
        leaves_here = []
        for c in children:
            leaves_here.extend( collect_leaves( c ) )
        if len( leaves_here ) == 2 and all( leaf in leaf_clades for leaf in leaves_here ):
            return tuple( leaves_here )
        return None

    children_of_root = parents_to_children.get( metazoa_root, () )
    sister = None
    if len( children_of_root ) == 2:
        leaves_a = collect_leaves( children_of_root[ 0 ] )
        leaves_b = collect_leaves( children_of_root[ 1 ] )
        if len( leaves_a ) == 1 and len( leaves_b ) > 1:
            sister = leaves_a[ 0 ]
        elif len( leaves_b ) == 1 and len( leaves_a ) > 1:
            sister = leaves_b[ 0 ]

    pair = deepest_pair( metazoa_root )

    sister_short = SHORT_LABELS.get( sister, sister ) if sister else 'ambiguous'
    if pair:
        pair_short = '(' + ','.join( SHORT_LABELS.get( p, p ) for p in pair ) + ')'
    else:
        pair_short = 'ambiguous'
    return sister_short, pair_short


def spearman_pearson( values_a, values_b ):
    n = len( values_a )
    mean_a = sum( values_a ) / n
    mean_b = sum( values_b ) / n
    num = sum( ( values_a[ i ] - mean_a ) * ( values_b[ i ] - mean_b ) for i in range( n ) )
    den_a = ( sum( ( values_a[ i ] - mean_a ) ** 2 for i in range( n ) ) ) ** 0.5
    den_b = ( sum( ( values_b[ i ] - mean_b ) ** 2 for i in range( n ) ) ) ** 0.5
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / ( den_a * den_b )


def main():
    parser = argparse.ArgumentParser( description = 'Diagnose criteria divergence (Spearman, per-OG shifts, unresolved zone topology)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_8 = output_dir / '8-output'
    output_8.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    log_file = log_dir / '8_ai-log-diagnose_criteria_divergence.log'
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_file ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'diagnose' )

    logger.info( 'Starting script 008: diagnose criteria divergence' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )

    ocl_orthogroups_dir = ( workflow_dir / config[ 'inputs' ][ 'ocl_orthogroups_dir' ] ).resolve()
    trees_species_dir = ( workflow_dir / config[ 'inputs' ][ 'trees_species_dir' ] ).resolve()
    structure_manifest_path = ( workflow_dir / config[ 'inputs' ][ 'structure_manifest' ] ).resolve()
    parent_child_dir = trees_species_dir / 'Species_Parent_Child_Relationships'

    filter_config = config.get( 'filter', {} ) or {}
    min_species_count = int( filter_config.get( 'min_species_count', 2 ) )
    max_species_count_raw = filter_config.get( 'max_species_count', None )
    max_species_count = int( max_species_count_raw ) if max_species_count_raw is not None else 10 ** 9

    # Read ranking + identify best structures
    ranking_path = output_dir / '5-output' / '5_ai-parsimony_ranking-structures.tsv'
    if not ranking_path.is_file():
        logger.error( f'CRITICAL: ranking file not found: {ranking_path} -- run script 005 first' )
        sys.exit( 1 )

    ranks_losses = {}
    ranks_depth = {}
    scores_losses = {}
    scores_depth = {}
    with open( ranking_path ) as input_ranking:
        header_line = input_ranking.readline()
        columns_to_index = parse_header_to_index( header_line )
        for line in input_ranking:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ columns_to_index[ 'Structure_ID' ] ]
            ranks_losses[ structure_id ] = float( parts[ columns_to_index[ 'Final_Rank_Losses' ] ] )
            ranks_depth[ structure_id ] = float( parts[ columns_to_index[ 'Final_Rank_Depth' ] ] )
            scores_losses[ structure_id ] = int( parts[ columns_to_index[ 'Score_Total_Losses' ] ] )
            scores_depth[ structure_id ] = int( parts[ columns_to_index[ 'Score_Total_Origin_Depth_Filtered' ] ] )

    all_structure_ids = sorted( ranks_losses.keys() )

    # Pick single winner per criterion (lowest rank, alphabetical tiebreak)
    best_by_losses = min( all_structure_ids, key = lambda s: ( ranks_losses[ s ], s ) )
    best_by_depth = min( all_structure_ids, key = lambda s: ( ranks_depth[ s ], s ) )
    user_input = '001' if '001' in all_structure_ids else all_structure_ids[ 0 ]

    logger.info( f'best_by_losses = structure_{best_by_losses}' )
    logger.info( f'best_by_depth  = structure_{best_by_depth}' )
    logger.info( f'user_input     = structure_{user_input}' )

    # Rank correlations
    ordered = all_structure_ids
    rank_correlation_spearman = spearman_pearson(
        [ ranks_losses[ s ] for s in ordered ],
        [ ranks_depth[ s ] for s in ordered ],
    )
    score_correlation_pearson_losses_vs_depth = spearman_pearson(
        [ float( scores_losses[ s ] ) for s in ordered ],
        [ float( scores_depth[ s ] ) for s in ordered ],
    )

    logger.info( f'Spearman rank correlation (Losses vs Depth): {rank_correlation_spearman:.4f}' )
    logger.info( f'Pearson correlation on raw scores (Losses vs Depth): {score_correlation_pearson_losses_vs_depth:.4f}' )

    # Per-OG shift computation across pairs
    def load_structure_origin_data( structure_id ):
        """Return ( orthogroup_ids, origin_blocks, species_counts, losses ) lists."""
        ocl_summary_path = ocl_orthogroups_dir / f'structure_{structure_id}' / '4_ai-orthogroups-complete_ocl_summary.tsv'
        orthogroup_ids = []
        origin_blocks = []
        species_counts = []
        losses = []
        with open( ocl_summary_path ) as input_summary:
            header_line = input_summary.readline()
            columns_to_index = parse_header_to_index( header_line )
            idx_og = columns_to_index[ 'Orthogroup_ID' ]
            idx_blk = columns_to_index[ 'Origin_Phylogenetic_Block' ]
            idx_sc = columns_to_index[ 'Species_Count' ]
            idx_l = columns_to_index[ 'Loss_Events' ]
            for line in input_summary:
                parts = line.rstrip( '\n' ).split( '\t' )
                orthogroup_ids.append( parts[ idx_og ] )
                origin_blocks.append( strip_state_suffix( parts[ idx_blk ] ) )
                species_counts.append( int( parts[ idx_sc ] ) )
                losses.append( int( parts[ idx_l ] ) )
        return orthogroup_ids, origin_blocks, species_counts, losses

    def load_structure_depth_map( structure_id ):
        parent_child_path = parent_child_dir / f'5_ai-structure_{structure_id}_parent_child_relationships.tsv'
        parents_to_children, _ = load_parent_child( parent_child_path )
        return build_depth_map( parents_to_children ), parents_to_children

    def write_pair_shifts( label, struct_a, struct_b, output_path ):
        logger.info( f'  pairwise shifts: {label}  ({struct_a} vs {struct_b})' )
        og_a, blk_a, sc_a, l_a = load_structure_origin_data( struct_a )
        og_b, blk_b, sc_b, l_b = load_structure_origin_data( struct_b )

        if og_a != og_b:
            logger.error( f'CRITICAL: orthogroup ID order differs between structures {struct_a} and {struct_b}' )
            sys.exit( 1 )

        depths_a, _ = load_structure_depth_map( struct_a )
        depths_b, _ = load_structure_depth_map( struct_b )

        rows = []
        sum_delta_depth = 0
        sum_delta_loss = 0
        for i in range( len( og_a ) ):
            sc = sc_a[ i ]
            if not ( min_species_count <= sc <= max_species_count ):
                continue
            if blk_a[ i ] == blk_b[ i ]:
                continue  # only shifters
            child_a = child_from_block( blk_a[ i ] )
            child_b = child_from_block( blk_b[ i ] )
            depth_a_value = depths_a.get( child_a, 1 ) if child_a else 1
            depth_b_value = depths_b.get( child_b, 1 ) if child_b else 1
            delta_depth = depth_b_value - depth_a_value
            delta_loss = l_b[ i ] - l_a[ i ]
            sum_delta_depth += delta_depth
            sum_delta_loss += delta_loss
            rows.append( ( og_a[ i ], sc, blk_a[ i ], blk_b[ i ], depth_a_value, depth_b_value, l_a[ i ], l_b[ i ], delta_depth, delta_loss ) )

        rows.sort( key = lambda r: -abs( r[ 8 ] ) )

        with open( output_path, 'w' ) as output:
            output.write( f'# Pairwise origin-block shifts: {label}\n' )
            output.write( f'# Structure_A_ID: structure_{struct_a}  (reference)\n' )
            output.write( f'# Structure_B_ID: structure_{struct_b}  (comparator)\n' )
            output.write( f'# Filter: Species_Count in [{min_species_count}, {max_species_count}]\n' )
            output.write( f'# Total filtered orthogroups with shifted origin block: {len( rows )}\n' )
            output.write( f'# Sum of Delta_Depth_B_minus_A across shifters: {sum_delta_depth}\n' )
            output.write( f'#   (positive means struct_B has shallower origins overall = better under shallow gain)\n' )
            output.write( f'# Sum of Delta_Loss_B_minus_A across shifters: {sum_delta_loss}\n' )
            output.write( f'#   (positive means struct_B has more losses overall = worse under loss minimization)\n' )
            output.write( 'Orthogroup_ID (OCL identifier)' )
            output.write( '\tSpecies_Count (orthogroup species count; filter window)' )
            output.write( '\tOrigin_Block_A (origin block in reference structure A)' )
            output.write( '\tOrigin_Block_B (origin block in comparator structure B)' )
            output.write( '\tDepth_A (depth of origin block child from C000_OOL in A; larger is shallower origin)' )
            output.write( '\tDepth_B (depth of origin block child from C000_OOL in B; larger is shallower origin)' )
            output.write( '\tLoss_A (Loss_Events for this orthogroup under A)' )
            output.write( '\tLoss_B (Loss_Events for this orthogroup under B)' )
            output.write( '\tDelta_Depth_B_minus_A (positive means origin shifted shallower in B)' )
            output.write( '\tDelta_Loss_B_minus_A (positive means more losses in B)\n' )
            for row in rows:
                output.write( '\t'.join( str( x ) for x in row ) + '\n' )

        return len( rows ), sum_delta_depth, sum_delta_loss

    pair_specs = [
        ( 'user_001_vs_best_by_losses', user_input, best_by_losses ),
        ( 'user_001_vs_best_by_depth',  user_input, best_by_depth ),
        ( 'best_by_losses_vs_best_by_depth', best_by_losses, best_by_depth ),
    ]
    pair_summaries = []
    for label, struct_a, struct_b in pair_specs:
        output_path = output_8 / f'8_ai-orthogroup_shifts-{label}.tsv'
        n_shifters, sum_dd, sum_dl = write_pair_shifts( label, struct_a, struct_b, output_path )
        pair_summaries.append( ( label, struct_a, struct_b, n_shifters, sum_dd, sum_dl ) )
        logger.info( f'    wrote {output_path}  ({n_shifters} shifters, sum_Delta_Depth={sum_dd}, sum_Delta_Loss={sum_dl})' )

    # Per-structure unresolved zone topology
    logger.info( 'Building per-structure unresolved zone topology summary' )

    structure_ids = []
    with open( structure_manifest_path ) as input_manifest:
        input_manifest.readline()
        for line in input_manifest:
            line = line.strip()
            if line and not line.startswith( '#' ):
                structure_ids.append( line )

    unresolved_zone_rows = []
    for structure_id in structure_ids:
        parent_child_path = parent_child_dir / f'5_ai-structure_{structure_id}_parent_child_relationships.tsv'
        if not parent_child_path.is_file():
            logger.warning( f'parent-child file missing for structure_{structure_id}; skipping unresolved zone extraction' )
            continue
        parents_to_children, all_clades = load_parent_child( parent_child_path )
        if METAZOA_ROOT not in all_clades:
            logger.warning( f'C082_Metazoa not in parent-child table for structure_{structure_id}; skipping' )
            continue
        newick_body = render_unresolved_zone_newick( parents_to_children )
        sister_short, deepest_pair_short = describe_unresolved_zone( parents_to_children )
        unresolved_zone_rows.append( ( structure_id, newick_body + ';', sister_short, deepest_pair_short ) )

    output_unresolved = output_8 / '8_ai-unresolved_zone_topology-per_structure.tsv'
    with open( output_unresolved, 'w' ) as output:
        output.write( 'Structure_ID (three digit identifier from manifest)' )
        output.write( '\tUnresolved_Zone_Newick (5 leaf newick of the basal metazoan unresolved zone derived from per structure parent child table; leaves are C086_Ctenophora C090_Porifera C095_Placozoa C102_Cnidaria C103_Bilateria)' )
        output.write( '\tSister_To_Rest_Short_Label (short label Cten Pori Plac Cnid or Bila of the leaf clade that is sister to all other unresolved zone clades at C082_Metazoa; ambiguous if not a single leaf split)' )
        output.write( '\tDeepest_Pair_Short_Label (parenthesized pair of short labels for the deepest internal pair of unresolved zone leaves; ambiguous if deeper structure intervenes)\n' )
        for row in unresolved_zone_rows:
            output.write( '\t'.join( row ) + '\n' )
    logger.info( f'Wrote unresolved zone topology summary: {output_unresolved}' )

    # Top-level divergence summary
    output_summary = output_8 / '8_ai-criteria_divergence_summary.txt'
    with open( output_summary, 'w' ) as output:
        output.write( '# parsimony_tree_structures BLOCK_ocl_orthogroups -- criteria divergence diagnostics\n' )
        output.write( f'# run_label: {config.get( "run_label", "UNSPECIFIED" )}\n' )
        output.write( '\n' )
        output.write( '## Rank correlation between loss-minimization and shallow-gain rankings\n' )
        output.write( f'Spearman_Rank_Correlation_Losses_vs_Depth\t{rank_correlation_spearman:.4f}\n' )
        output.write( f'Pearson_Score_Correlation_Losses_vs_Depth\t{score_correlation_pearson_losses_vs_depth:.4f}\n' )
        output.write( '\n' )
        output.write( '## Point-estimate best structures\n' )
        output.write( f'Best_By_Losses\tstructure_{best_by_losses}\tScore_Total_Losses={scores_losses[ best_by_losses ]}\n' )
        output.write( f'Best_By_Depth\tstructure_{best_by_depth}\tScore_Total_Origin_Depth_Filtered={scores_depth[ best_by_depth ]}\n' )
        output.write( f'User_Input_Tree\tstructure_{user_input}\tFinal_Rank_Losses={ranks_losses[ user_input ]}\tFinal_Rank_Depth={ranks_depth[ user_input ]}\n' )
        output.write( '\n' )
        output.write( '## Pairwise origin-block shifts (filtered orthogroups only)\n' )
        output.write( 'Label\tStructure_A\tStructure_B\tShifters\tSum_Delta_Depth_B_minus_A\tSum_Delta_Loss_B_minus_A\n' )
        for label, struct_a, struct_b, n_shifters, sum_dd, sum_dl in pair_summaries:
            output.write( f'{label}\tstructure_{struct_a}\tstructure_{struct_b}\t{n_shifters}\t{sum_dd}\t{sum_dl}\n' )
        output.write( '\n' )
        output.write( '## Unresolved zone topology for best structures\n' )
        for_lookup = { row[ 0 ]: row for row in unresolved_zone_rows }
        for label, struct_id in [ ( 'user', user_input ), ( 'best_by_losses', best_by_losses ), ( 'best_by_depth', best_by_depth ) ]:
            if struct_id in for_lookup:
                _, newick, sister, pair_label = for_lookup[ struct_id ]
                output.write( f'{label}\tstructure_{struct_id}\tsister_to_rest={sister}\tdeepest_pair={pair_label}\tnewick={newick}\n' )

    logger.info( f'Wrote divergence summary: {output_summary}' )


if __name__ == '__main__':
    main()
