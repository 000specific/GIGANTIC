#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Assign ancestral_clade_NNN names to unlabeled internals and CXXX_ clade identifiers to all nodes
# Human: Eric Edsinger

"""
GIGANTIC trees_species - BLOCK_gigantic_species_tree - Script 002:
Assign Clade Identifiers

Purpose:
    Read the canonical species tree from Script 001 output, assign
    'ancestral_clade_NNN' names to any unlabeled internal nodes, then assign
    'CXXX_' clade identifier prefixes to every node (leaves and internals).
    The result is a fully labeled species tree where every node has a
    'CXXX_Name' label.

Ancestral clade naming (for user-unlabeled internal nodes):
    - Walk the tree in breadth-first order from the root
    - For each internal node whose name is empty, assign
      'ancestral_clade_{counter:03d}' where counter starts at 1 and
      increments only for unlabeled internals (user-named internals are
      skipped and do not consume numbers)
    - Counter is 3-digit zero-padded: ancestral_clade_001, ancestral_clade_002, ...

Clade ID assignment (for every node):
    - Leaves get C001, C002, ... in depth-first preorder traversal
    - Internal nodes get C(N+1), C(N+2), ... in breadth-first order from root,
      where N is the leaf count. The root gets the first internal ID (C(N+1)).
    - Each node's final name becomes 'CXXX_{name}'.

Re-run handling:
    If the input tree already has CXXX_ prefixes (e.g., re-running on an
    output from this script), the existing prefixes are silently stripped
    before re-assignment. A log note records how many were stripped. This
    is informational only, not an error.

Validation checks (all hard-fail):
    1. Input file exists and is parseable
    2. Tree is binary (safety check, should already be guaranteed by Script 001)
    3. Every leaf has a non-empty name (after any CXXX_ stripping)
    4. After ancestral_clade fill, every internal node has a non-empty name
    5. After CXXX_ assignment, every node has a valid 'CXXX_Name' label

Inputs (command-line arguments):
    --input-newick   Path to canonical species tree from Script 001
                     (typically 1-output/1_ai-input_species_tree-canonical.newick)
    --output-dir     Directory to write outputs

Outputs (in --output-dir):
    2_ai-species_tree-with_clade_ids_and_names.newick    Fully labeled tree
    2_ai-validation_report.tsv                             Per-check summary
    2_ai-log-assign_clade_identifiers.log                  Execution log

Exit codes:
    0 — all validation passed, outputs written
    1 — any validation failure

Usage (standalone):
    python3 002_ai-python-assign_clade_identifiers.py \\
        --input-newick 1-output/1_ai-input_species_tree-canonical.newick \\
        --output-dir 2-output
"""

import argparse
import logging
import re
import sys
from collections import deque
from pathlib import Path


# ============================================================================
# CONSTANTS
# ============================================================================

# Pattern for existing CXXX_ prefix (to be stripped before re-assignment on re-run)
CXXX_PREFIX_PATTERN = re.compile( r'^C\d+_' )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'Assign ancestral_clade_NNN names and CXXX_ clade identifiers to a species tree'
    )
    parser.add_argument(
        '--input-newick',
        required = True,
        help = 'Path to canonical species tree from Script 001'
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
    """Set up logging to both file and console."""
    log_file = output_dir / '2_ai-log-assign_clade_identifiers.log'
    logger = logging.getLogger( 'assign_clade_identifiers' )
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
# NEWICK PARSER (no external dependencies)
# ============================================================================

def parse_newick( newick_string ):
    """
    Parse a Newick string into a nested dict structure.
    Each node: { 'name': str, 'branch_length': str, 'children': [list of nodes] }
    Leaves have empty children list.
    """
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

    root = parse_node()

    while cursor[ 0 ] < len( cleaned ) and cleaned[ cursor[ 0 ] ].isspace():
        cursor[ 0 ] += 1
    if cursor[ 0 ] < len( cleaned ):
        trailing_preview = cleaned[ cursor[ 0 ] : ][ :50 ]
        raise ValueError( f"Newick parse error: unexpected trailing characters at position {cursor[0]}: '{trailing_preview}'" )

    return root


def write_newick( node ):
    """Write a parsed node back to Newick (no trailing semicolon)."""
    if node[ 'children' ]:
        children_string = ','.join( write_newick( child ) for child in node[ 'children' ] )
        label_string = node[ 'name' ]
        if node[ 'branch_length' ]:
            label_string += ':' + node[ 'branch_length' ]
        return f"({children_string}){label_string}"
    else:
        label_string = node[ 'name' ]
        if node[ 'branch_length' ]:
            label_string += ':' + node[ 'branch_length' ]
        return label_string


# ============================================================================
# TREE WALKING
# ============================================================================

def collect_nodes_with_kind( root_node ):
    """Return list of ( node, 'leaf' | 'internal' ) tuples in DFS preorder."""
    nodes = []

    def walk( current_node ):
        node_kind = 'internal' if current_node[ 'children' ] else 'leaf'
        nodes.append( ( current_node, node_kind ) )
        for child in current_node[ 'children' ]:
            walk( child )

    walk( root_node )
    return nodes


# ============================================================================
# VALIDATION CHECKS
# ============================================================================

def validate_binary_tree( root_node, logger ):
    """
    Safety re-check that the tree is binary. Script 001 already validates
    this; this is a defensive check in case Script 002 is called directly
    on a tree that did not come from Script 001.
    """
    def walk( node, path ):
        if node[ 'children' ]:
            if len( node[ 'children' ] ) != 2:
                logger.error( f"CRITICAL ERROR: Non-binary internal node at {path}" )
                logger.error( f"  Node name: '{node['name']}'" )
                logger.error( f"  Number of children: {len(node['children'])}" )
                logger.error( "  Input to Script 002 must be binary. Re-run Script 001 first or fix the input." )
                sys.exit( 1 )
            for child_index, child in enumerate( node[ 'children' ] ):
                walk( child, path = f"{path}/{node['name'] or '(unnamed)'}[{child_index}]" )

    walk( root_node, path = 'root' )


def check_all_leaves_have_names( root_node, logger ):
    """Hard fail if any leaf has an empty name."""
    unnamed_leaves_count = 0
    for node, node_kind in collect_nodes_with_kind( root_node ):
        if node_kind == 'leaf' and not node[ 'name' ]:
            unnamed_leaves_count += 1

    if unnamed_leaves_count > 0:
        logger.error( f"CRITICAL ERROR: {unnamed_leaves_count} leaf node(s) have no name." )
        logger.error( "  Every species in the species tree must have a Genus_species name." )
        sys.exit( 1 )


def check_all_nodes_have_final_labels( root_node, logger ):
    """After all assignment passes, every node must have a non-empty name starting with CXXX_."""
    unlabeled_nodes = []
    malformed_nodes = []

    for node, node_kind in collect_nodes_with_kind( root_node ):
        if not node[ 'name' ]:
            unlabeled_nodes.append( ( node, node_kind ) )
        elif not CXXX_PREFIX_PATTERN.match( node[ 'name' ] ):
            malformed_nodes.append( ( node, node_kind ) )

    if unlabeled_nodes:
        logger.error( f"CRITICAL ERROR: {len(unlabeled_nodes)} node(s) still have no name after assignment." )
        for node, node_kind in unlabeled_nodes[ :10 ]:
            logger.error( f"  - ({node_kind}, {len(node['children'])} children)" )
        sys.exit( 1 )

    if malformed_nodes:
        logger.error( f"CRITICAL ERROR: {len(malformed_nodes)} node(s) do not have a CXXX_ prefix after assignment." )
        for node, node_kind in malformed_nodes[ :10 ]:
            logger.error( f"  - '{node['name']}' ({node_kind})" )
        sys.exit( 1 )


# ============================================================================
# STRIPPING EXISTING CXXX_ PREFIXES (for re-run case)
# ============================================================================

def strip_existing_cxxx_prefixes( root_node, logger ):
    """
    Strip any existing CXXX_ prefix from node names. This handles the re-run
    case where the input tree already has clade identifiers (e.g., an output
    from a previous run of this script). Returns the number of prefixes stripped.
    """
    stripped_count = [ 0 ]

    def walk( node ):
        original_name = node[ 'name' ]
        if original_name:
            new_name = CXXX_PREFIX_PATTERN.sub( '', original_name )
            if new_name != original_name:
                stripped_count[ 0 ] += 1
                node[ 'name' ] = new_name
        for child in node[ 'children' ]:
            walk( child )

    walk( root_node )

    if stripped_count[ 0 ] > 0:
        logger.info( f"  Stripped existing CXXX_ prefix from {stripped_count[0]} node(s) (re-run case — input appears to have been processed by this script before)" )

    return stripped_count[ 0 ]


# ============================================================================
# ANCESTRAL CLADE NAMING
# ============================================================================

def assign_ancestral_clade_names( root_node, logger ):
    """
    Walk the tree in BFS order from root, assigning 'ancestral_clade_NNN'
    names to any internal node with an empty name. The counter starts at 1
    and increments only for unlabeled internals (user-named internals are
    skipped and do not consume numbers).

    Returns ( ancestral_clade_assigned_count, user_named_internal_count ).
    """
    ancestral_counter = 0
    user_named_internal_count = 0

    queue = deque( [ root_node ] )
    while queue:
        node = queue.popleft()
        if node[ 'children' ]:  # internal node
            if not node[ 'name' ]:
                ancestral_counter += 1
                node[ 'name' ] = f"ancestral_clade_{ancestral_counter:03d}"
            else:
                user_named_internal_count += 1
            for child in node[ 'children' ]:
                queue.append( child )

    return ( ancestral_counter, user_named_internal_count )


# ============================================================================
# CLADE ID ASSIGNMENT
# ============================================================================

def assign_clade_identifiers( root_node, logger ):
    """
    Assign CXXX_ clade identifier prefixes to every node.

      - Leaves get C001, C002, ... in depth-first preorder traversal
      - Internal nodes get C(leaf_count+1), ... in BFS order from root

    Modifies node['name'] in place: prepends 'CXXX_' to the existing name.

    Returns ( leaf_count, internal_count ).
    """
    # Pass 1: assign CXXX_ to leaves in DFS preorder
    leaf_counter = [ 0 ]

    def leaf_walk( node ):
        if not node[ 'children' ]:
            leaf_counter[ 0 ] += 1
            node[ 'name' ] = f"C{leaf_counter[0]:03d}_{node['name']}"
        else:
            for child in node[ 'children' ]:
                leaf_walk( child )

    leaf_walk( root_node )
    leaf_count = leaf_counter[ 0 ]

    # Pass 2: assign CXXX_ to internal nodes in BFS order from root
    internal_counter = [ leaf_count ]
    queue = deque( [ root_node ] )
    while queue:
        node = queue.popleft()
        if node[ 'children' ]:
            internal_counter[ 0 ] += 1
            node[ 'name' ] = f"C{internal_counter[0]:03d}_{node['name']}"
            for child in node[ 'children' ]:
                queue.append( child )

    internal_count = internal_counter[ 0 ] - leaf_count

    return ( leaf_count, internal_count )


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    args = parse_arguments()

    input_newick_path = Path( args.input_newick ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_dir )

    logger.info( '=' * 78 )
    logger.info( 'GIGANTIC trees_species - BLOCK_gigantic_species_tree' )
    logger.info( 'Script 002: Assign Clade Identifiers' )
    logger.info( '=' * 78 )
    logger.info( f"Input newick: {input_newick_path}" )
    logger.info( f"Output dir:   {output_dir}" )
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

    # ----- Defensive: validate binary tree (Script 001 should have guaranteed this) -----
    logger.info( "Validating: tree is binary..." )
    validate_binary_tree( root_node, logger )
    logger.info( "  [OK]" )

    # ----- Defensive: validate all leaves have names -----
    logger.info( "Validating: every leaf has a name..." )
    check_all_leaves_have_names( root_node, logger )
    logger.info( "  [OK]" )

    # ----- Strip any existing CXXX_ prefixes (re-run case) -----
    logger.info( "Checking for existing CXXX_ prefixes (re-run handling)..." )
    stripped_prefix_count = strip_existing_cxxx_prefixes( root_node, logger )
    if stripped_prefix_count == 0:
        logger.info( "  [OK] No existing CXXX_ prefixes found (fresh input)" )

    # ----- Assign ancestral_clade_NNN names to unlabeled internals -----
    logger.info( "Assigning ancestral_clade_NNN names to unlabeled internal nodes (BFS order from root)..." )
    ancestral_clade_count, user_named_internal_count = assign_ancestral_clade_names( root_node, logger )
    if ancestral_clade_count > 0:
        logger.info( f"  [OK] Assigned ancestral_clade_001 through ancestral_clade_{ancestral_clade_count:03d} to {ancestral_clade_count} unlabeled internal node(s)" )
    else:
        logger.info( f"  [OK] No unlabeled internal nodes to fill (all {user_named_internal_count} internals were user-named)" )

    # ----- Assign CXXX_ clade identifiers to every node -----
    logger.info( "Assigning CXXX_ clade identifiers..." )
    leaf_count, internal_count = assign_clade_identifiers( root_node, logger )
    logger.info( f"  [OK] Assigned C001 through C{leaf_count:03d} to {leaf_count} leaves (DFS preorder)" )
    logger.info( f"  [OK] Assigned C{leaf_count+1:03d} through C{leaf_count+internal_count:03d} to {internal_count} internal nodes (BFS from root)" )

    # ----- Validate all nodes now have final CXXX_Name labels -----
    logger.info( "Validating: every node has a final CXXX_Name label..." )
    check_all_nodes_have_final_labels( root_node, logger )
    logger.info( "  [OK]" )

    # ----- Write fully labeled species tree -----
    labeled_newick_string = write_newick( root_node ) + ';'
    output_labeled_newick = output_dir / '2_ai-species_tree-with_clade_ids_and_names.newick'
    output = labeled_newick_string + '\n'
    output_labeled_newick.write_text( output )
    logger.info( f"Wrote fully labeled species tree: {output_labeled_newick.name}" )

    # ----- Write validation report -----
    output_validation_report = output_dir / '2_ai-validation_report.tsv'
    total_nodes = leaf_count + internal_count

    report_lines = [ 'check_name (validation check name)\tcheck_status (PASS or INFO)\tcheck_value (count or other detail)' ]
    report_lines.append( f"input_file_exists\tPASS\t{input_newick_path.name}" )
    report_lines.append( f"newick_parseable\tPASS\t{len(input_newick_string)} characters" )
    report_lines.append( f"binary_tree\tPASS\tall internal nodes have exactly 2 children" )
    report_lines.append( f"leaves_have_names\tPASS\tall leaves have non-empty names" )
    report_lines.append( f"existing_cxxx_prefixes_stripped\tINFO\t{stripped_prefix_count}" )
    report_lines.append( f"ancestral_clade_names_assigned\tINFO\t{ancestral_clade_count}" )
    report_lines.append( f"user_named_internal_nodes\tINFO\t{user_named_internal_count}" )
    report_lines.append( f"leaf_count\tINFO\t{leaf_count}" )
    report_lines.append( f"internal_node_count\tINFO\t{internal_count}" )
    report_lines.append( f"total_nodes\tINFO\t{total_nodes}" )
    report_lines.append( f"all_nodes_have_cxxx_labels\tPASS\tevery node has CXXX_Name label" )

    output = '\n'.join( report_lines ) + '\n'
    output_validation_report.write_text( output )
    logger.info( f"Wrote validation report: {output_validation_report.name}" )

    # ----- Final summary -----
    logger.info( '' )
    logger.info( '=' * 78 )
    logger.info( 'SUCCESS' )
    logger.info( f"  {leaf_count} leaves (species) → C001 through C{leaf_count:03d}" )
    logger.info( f"  {internal_count} internal nodes (clades) → C{leaf_count+1:03d} through C{leaf_count+internal_count:03d}" )
    if ancestral_clade_count > 0:
        logger.info( f"  {ancestral_clade_count} internal nodes auto-named ancestral_clade_001 through ancestral_clade_{ancestral_clade_count:03d}" )
    else:
        logger.info( f"  0 internal nodes auto-named (all internals had user-provided names)" )
    logger.info( f"  {user_named_internal_count} internal nodes kept their user-provided names" )
    logger.info( '=' * 78 )


if __name__ == '__main__':
    main()
