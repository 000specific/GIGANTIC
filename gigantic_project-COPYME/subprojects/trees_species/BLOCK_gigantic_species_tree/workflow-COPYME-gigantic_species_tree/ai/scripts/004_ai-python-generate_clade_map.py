#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Generate clade name and clade ID lookup map TSV from the fully labeled species tree
# Human: Eric Edsinger

"""
GIGANTIC trees_species - BLOCK_gigantic_species_tree - Script 004:
Generate Clade Map (clade name <-> clade ID)

Purpose:
    Read the fully labeled species tree from Script 002 output and emit a
    TSV lookup table mapping each clade name to its clade ID. Every node
    (leaf and internal) appears exactly once, in tree-traversal order.

    This is the canonical lookup table for downstream consumers that need to
    translate between clade IDs (CXXX) and clade names (Genus_species or
    clade name).

Output format:
    Three self-documenting columns, tab-separated:

    clade_name (Genus_species for leaves or clade name for internal nodes)
    clade_id (CXXX identifier)
    node_kind (leaf or internal)

Traversal order:
    Depth-first preorder. This matches the species67 Leonid tree convention
    and puts sibling clades in left-to-right order. Downstream consumers
    should not rely on the traversal order for correctness — they should
    key on clade_id or clade_name, both of which are unique.

Inputs (command-line arguments):
    --input-newick     Path to fully labeled species tree from Script 002
                       (typically 2-output/2_ai-species_tree-with_clade_ids_and_names.newick)
    --species-set-name Species set identifier for output filename (e.g., species70)
    --output-dir       Directory to write outputs

Outputs (in --output-dir):
    4_ai-{species_set_name}-clade_name_X_clade_id.tsv
    4_ai-log-generate_clade_map.log

Exit codes:
    0 — map written successfully
    1 — any failure (input parse, empty tree, invalid labels)

Usage (standalone):
    python3 004_ai-python-generate_clade_map.py \\
        --input-newick 2-output/2_ai-species_tree-with_clade_ids_and_names.newick \\
        --species-set-name species70 \\
        --output-dir 4-output
"""

import argparse
import logging
import re
import sys
from pathlib import Path


# ============================================================================
# CONSTANTS
# ============================================================================

CXXX_ID_PATTERN = re.compile( r'^(C\d+)_(.+)$' )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Generate clade name to clade ID lookup map TSV from the fully labeled species tree'
    )
    parser.add_argument(
        '--input-newick',
        required = True,
        help = 'Path to fully labeled species tree from Script 002'
    )
    parser.add_argument(
        '--species-set-name',
        required = True,
        help = 'Species set identifier for output filename (e.g., species70)'
    )
    parser.add_argument(
        '--output-dir',
        required = True,
        help = 'Directory to write outputs'
    )
    return parser.parse_args()


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging( output_dir ):
    log_file = output_dir / '4_ai-log-generate_clade_map.log'
    logger = logging.getLogger( 'generate_clade_map' )
    logger.setLevel( logging.INFO )
    file_handler = logging.FileHandler( log_file )
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )
    logger.addHandler( file_handler )
    logger.addHandler( console_handler )
    return logger


# ============================================================================
# NEWICK PARSER
# ============================================================================

def parse_newick( newick_string ):
    """Parse Newick into nested dict { 'name', 'branch_length', 'children' }."""
    cleaned = newick_string.strip().rstrip( ';' ).strip()
    if not cleaned:
        raise ValueError( "Newick string is empty after stripping" )

    cursor = [ 0 ]

    def parse_node():
        children = []
        if cursor[ 0 ] < len( cleaned ) and cleaned[ cursor[ 0 ] ] == '(':
            cursor[ 0 ] += 1
            children.append( parse_node() )
            while cursor[ 0 ] < len( cleaned ) and cleaned[ cursor[ 0 ] ] == ',':
                cursor[ 0 ] += 1
                children.append( parse_node() )
            if cursor[ 0 ] >= len( cleaned ) or cleaned[ cursor[ 0 ] ] != ')':
                raise ValueError( f"Newick parse error: expected ')' at position {cursor[0]}" )
            cursor[ 0 ] += 1

        label_start = cursor[ 0 ]
        while cursor[ 0 ] < len( cleaned ) and cleaned[ cursor[ 0 ] ] not in ',()':
            cursor[ 0 ] += 1
        label_text = cleaned[ label_start : cursor[ 0 ] ]

        if ':' in label_text:
            parts_label = label_text.split( ':', 1 )
            name_part = parts_label[ 0 ].strip()
            branch_length_part = parts_label[ 1 ].strip()
        else:
            name_part = label_text.strip()
            branch_length_part = ''

        return { 'name': name_part, 'branch_length': branch_length_part, 'children': children }

    return parse_node()


# ============================================================================
# CLADE MAP COLLECTION
# ============================================================================

def collect_clade_map_entries( root_node, logger ):
    """
    Walk the tree in DFS preorder, collecting ( clade_id, clade_name, node_kind )
    tuples for every node. Hard-fails if any node does not have a valid
    CXXX_Name label.
    """
    entries = []  # list of ( clade_id, clade_name, node_kind )

    def walk( current_node ):
        full_label = current_node[ 'name' ]
        if not full_label:
            logger.error( f"CRITICAL ERROR: Found a node with no label." )
            logger.error( "  Every node must have a CXXX_Name label (produced by Script 002)." )
            sys.exit( 1 )

        match = CXXX_ID_PATTERN.match( full_label )
        if not match:
            logger.error( f"CRITICAL ERROR: Node label '{full_label}' does not match CXXX_Name format." )
            logger.error( "  Every node must start with CXXX_ (a C followed by digits and an underscore)." )
            sys.exit( 1 )

        clade_id = match.group( 1 )
        clade_name = match.group( 2 )
        node_kind = 'internal' if current_node[ 'children' ] else 'leaf'
        entries.append( ( clade_id, clade_name, node_kind ) )

        for child in current_node[ 'children' ]:
            walk( child )

    walk( root_node )
    return entries


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    args = parse_arguments()

    input_newick_path = Path( args.input_newick ).resolve()
    species_set_name = args.species_set_name
    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_dir )

    logger.info( '=' * 78 )
    logger.info( 'GIGANTIC trees_species - BLOCK_gigantic_species_tree' )
    logger.info( 'Script 004: Generate Clade Map' )
    logger.info( '=' * 78 )
    logger.info( f"Input newick:      {input_newick_path}" )
    logger.info( f"Species set name:  {species_set_name}" )
    logger.info( f"Output dir:        {output_dir}" )
    logger.info( '' )

    # ----- Read input -----
    if not input_newick_path.exists():
        logger.error( f"CRITICAL ERROR: Input newick file not found: {input_newick_path}" )
        sys.exit( 1 )

    input_newick_string = input_newick_path.read_text().strip()
    if not input_newick_string:
        logger.error( f"CRITICAL ERROR: Input newick file is empty: {input_newick_path}" )
        sys.exit( 1 )

    logger.info( f"Read input newick ({len(input_newick_string)} characters)" )

    # ----- Parse Newick -----
    try:
        root_node = parse_newick( input_newick_string )
    except ValueError as parse_error:
        logger.error( f"CRITICAL ERROR: Failed to parse input newick: {parse_error}" )
        sys.exit( 1 )

    logger.info( "Parsed input newick successfully" )

    # ----- Collect clade map entries -----
    logger.info( "Collecting clade map entries (DFS preorder traversal)..." )
    clade_map_entries = collect_clade_map_entries( root_node, logger )

    leaf_count = sum( 1 for _, _, kind in clade_map_entries if kind == 'leaf' )
    internal_count = sum( 1 for _, _, kind in clade_map_entries if kind == 'internal' )
    total_count = len( clade_map_entries )
    logger.info( f"  [OK] Collected {total_count} entries ({leaf_count} leaves, {internal_count} internal nodes)" )

    # ----- Check for duplicate clade IDs (should not happen, but defensive) -----
    clade_ids_seen = [ entry[ 0 ] for entry in clade_map_entries ]
    duplicate_ids = [ clade_id for clade_id in set( clade_ids_seen ) if clade_ids_seen.count( clade_id ) > 1 ]
    if duplicate_ids:
        logger.error( f"CRITICAL ERROR: Duplicate clade IDs found:" )
        for clade_id in sorted( duplicate_ids ):
            logger.error( f"  - {clade_id}" )
        logger.error( "  Each clade ID must appear exactly once. This indicates a bug in Script 002." )
        sys.exit( 1 )

    # ----- Write clade map TSV -----
    output_clade_map = output_dir / f'4_ai-{species_set_name}-clade_name_X_clade_id.tsv'
    map_lines = [ 'clade_name (Genus_species for leaves or clade name for internal nodes)\tclade_id (CXXX identifier)\tnode_kind (leaf or internal)' ]
    for clade_id, clade_name, node_kind in clade_map_entries:
        output = clade_name + '\t' + clade_id + '\t' + node_kind
        map_lines.append( output )
    output = '\n'.join( map_lines ) + '\n'
    output_clade_map.write_text( output )
    logger.info( f"Wrote clade map: {output_clade_map.name}" )

    # ----- Final summary -----
    logger.info( '' )
    logger.info( '=' * 78 )
    logger.info( 'SUCCESS' )
    logger.info( f"  {total_count} entries ({leaf_count} leaves + {internal_count} internal nodes)" )
    logger.info( f"  Clade map: {output_clade_map.name}" )
    logger.info( '=' * 78 )


if __name__ == '__main__':
    main()
