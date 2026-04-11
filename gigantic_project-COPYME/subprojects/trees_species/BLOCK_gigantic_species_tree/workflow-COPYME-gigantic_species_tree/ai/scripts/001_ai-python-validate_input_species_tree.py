#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Validate and standardize user-provided species tree for gigantic_species_tree BLOCK
# Human: Eric Edsinger

"""
GIGANTIC trees_species - BLOCK_gigantic_species_tree - Script 001:
Validate Input Species Tree

Purpose:
    Parse the user-provided species tree (Newick), validate it, and emit a
    standardized canonical version for downstream scripts in this BLOCK.

Validation checks (all hard-fail):
    1. Input file exists and is non-empty
    2. Newick syntax is parseable
    3. Every leaf has a non-empty name
    4. Tree is binary (every internal node has exactly 2 children — polytomies REFUSED)
    5. NO user-provided name (after standardization) matches the reserved
       ancestral_clade_NNN pattern (this namespace is reserved for Script 002)
    6. All leaf names are unique (after standardization)
    7. All user-provided internal node names are unique (after standardization)

Standardization (always applied):
    - Invalid characters in any user-provided name are REPLACED with underscores.
      Allowed character set: [A-Za-z0-9_]. Anything else (spaces, hyphens, periods,
      special chars) becomes _. Multiple consecutive underscores collapse to one.
      Leading/trailing underscores are stripped.
    - Branch lengths are REPLACED with 1.0. GIGANTIC does not use user-provided
      branch lengths anywhere downstream; standardizing here keeps tree structures
      consistent across the framework. (This is THE EXCEPTION to the general
      "never destroy user data" rule and is documented as such.)

A name-mapping table is ALWAYS emitted (even if no changes were made), recording
every input-user name alongside its gigantic-standardized name. This serves as a
reference for the user.

Inputs (command-line arguments):
    --input-newick   Path to user-provided species tree (Newick format)
    --output-dir     Directory to write outputs

Outputs (in --output-dir):
    1_ai-input_species_tree-canonical.newick    Standardized input tree (no CXXX yet)
    1_ai-input_user_name_X_gigantic_name.tsv    Name-mapping table (always emitted)
    1_ai-validation_report.tsv                  Per-check pass/fail summary
    1_ai-log-validate_input_species_tree.log    Execution log

Exit codes:
    0 — all validation passed, outputs written
    1 — any validation failure (with detailed error in log and stderr)

Usage (standalone):
    python3 001_ai-python-validate_input_species_tree.py \\
        --input-newick INPUT_user/species_tree.newick \\
        --output-dir 1-output

Usage (NextFlow): called by main.nf process validate_input_species_tree
"""

import argparse
import logging
import re
import sys
from pathlib import Path


# ============================================================================
# CONSTANTS
# ============================================================================

# Allowed characters in standardized names: ASCII letters, digits, underscore.
# Anything else gets replaced with underscore during standardization.
INVALID_NAME_CHARACTER_PATTERN = re.compile( r'[^A-Za-z0-9_]' )

# Reserved pattern for ancestral_clade auto-naming (Script 002 will populate this).
# Script 001 must REFUSE any user-provided name that matches this pattern.
ANCESTRAL_CLADE_PATTERN = re.compile( r'^ancestral_clade_\d{3}$' )

# Standard branch length used by gigantic. All user-provided branch lengths
# are replaced with this value during standardization.
GIGANTIC_STANDARD_BRANCH_LENGTH = '1.0'


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'Validate and standardize user-provided species tree for gigantic_species_tree BLOCK'
    )
    parser.add_argument(
        '--input-newick',
        required = True,
        help = 'Path to user-provided species tree (Newick format)'
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
    log_file = output_dir / '1_ai-log-validate_input_species_tree.log'
    logger = logging.getLogger( 'validate_input_species_tree' )
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

        # Read label until , ) or end of string
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

    # Check we consumed the entire string (allowing for trailing whitespace)
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
# NAME STANDARDIZATION
# ============================================================================

def standardize_name( raw_name ):
    """
    Replace any character not in [A-Za-z0-9_] with underscore.
    Collapse consecutive underscores. Strip leading/trailing underscores.
    Returns ( standardized_name, was_changed_flag ).
    """
    if not raw_name:
        return ( '', False )

    # Replace invalid characters with underscores
    standardized = INVALID_NAME_CHARACTER_PATTERN.sub( '_', raw_name )
    # Collapse consecutive underscores
    standardized = re.sub( r'_+', '_', standardized )
    # Strip leading/trailing underscores
    standardized = standardized.strip( '_' )

    was_changed = ( standardized != raw_name )
    return ( standardized, was_changed )


# ============================================================================
# VALIDATION CHECKS
# ============================================================================

def check_all_leaves_have_names( root_node, logger ):
    """Hard fail if any leaf has an empty name."""
    unnamed_leaves = []
    for node, node_kind in collect_nodes_with_kind( root_node ):
        if node_kind == 'leaf' and not node[ 'name' ]:
            unnamed_leaves.append( node )

    if unnamed_leaves:
        logger.error( f"CRITICAL ERROR: {len(unnamed_leaves)} leaf node(s) have no name." )
        logger.error( "  Every species in the species tree must have a Genus_species name." )
        sys.exit( 1 )


def check_binary_tree( root_node, logger ):
    """Hard fail if any internal node has != 2 children. Polytomies REFUSED."""
    def walk( node, path ):
        if node[ 'children' ]:
            if len( node[ 'children' ] ) != 2:
                logger.error( f"CRITICAL ERROR: Non-binary internal node at {path}" )
                logger.error( f"  Node name: '{node['name']}'" )
                logger.error( f"  Number of children: {len(node['children'])}" )
                logger.error( "  GIGANTIC requires fully resolved binary species trees." )
                logger.error( "  Polytomies (multifurcations) are not allowed in this BLOCK." )
                logger.error( "  If your tree has unresolved clades, resolve them manually before running" )
                logger.error( "  this BLOCK, or pass them to BLOCK_permutations_and_features which" )
                logger.error( "  handles unresolved clades via its config." )
                sys.exit( 1 )
            for child_index, child in enumerate( node[ 'children' ] ):
                walk( child, path = f"{path}/{node['name'] or '(unnamed)'}[{child_index}]" )

    walk( root_node, path = 'root' )


def check_for_reserved_namespace_collisions( root_node, name_mapping_entries, logger ):
    """
    Hard fail if any standardized name matches the ancestral_clade_NNN reserved pattern.
    Checks AFTER standardization so that names like "ancestral clade 001" (which
    standardize to "ancestral_clade_001") are also caught.
    """
    collisions = []
    for input_user_name, standardized_name, node_kind, _ in name_mapping_entries:
        if ANCESTRAL_CLADE_PATTERN.match( standardized_name ):
            collisions.append( ( input_user_name, standardized_name, node_kind ) )

    if collisions:
        logger.error( f"CRITICAL ERROR: {len(collisions)} user-provided name(s) collide with the reserved ancestral_clade_NNN namespace:" )
        for input_user_name, standardized_name, node_kind in collisions:
            if input_user_name == standardized_name:
                logger.error( f"  - '{input_user_name}' ({node_kind})" )
            else:
                logger.error( f"  - '{input_user_name}' -> '{standardized_name}' ({node_kind}) [collision after standardization]" )
        logger.error( "" )
        logger.error( "  The pattern 'ancestral_clade_NNN' (where NNN is a 3-digit number) is RESERVED" )
        logger.error( "  by this BLOCK for auto-naming user-unlabeled internal nodes (Script 002)." )
        logger.error( "  Please rename the conflicting node(s) in your input species tree." )
        sys.exit( 1 )


def check_for_duplicate_names( name_mapping_entries, logger ):
    """
    Hard fail on duplicate leaf names or duplicate user-provided internal node names.
    Uses standardized names so collapse-collisions are caught (e.g., 'Homo sapiens'
    and 'Homo-sapiens' both standardizing to 'Homo_sapiens').
    """
    leaf_standardized_names = []
    internal_standardized_names = []
    name_origin___inputs = {}  # standardized_name -> list of input_user_names

    for input_user_name, standardized_name, node_kind, _ in name_mapping_entries:
        if node_kind == 'leaf':
            leaf_standardized_names.append( standardized_name )
        else:
            internal_standardized_names.append( standardized_name )
        name_origin___inputs.setdefault( standardized_name, [] ).append( input_user_name )

    duplicate_leaves = [ name for name in set( leaf_standardized_names ) if leaf_standardized_names.count( name ) > 1 ]
    duplicate_internals = [ name for name in set( internal_standardized_names ) if internal_standardized_names.count( name ) > 1 ]

    if duplicate_leaves:
        logger.error( f"CRITICAL ERROR: Duplicate leaf (species) names found after standardization:" )
        for standardized_name in sorted( duplicate_leaves ):
            input_origins = name_origin___inputs[ standardized_name ]
            logger.error( f"  - '{standardized_name}' (appears {leaf_standardized_names.count(standardized_name)} times)" )
            for input_user_name in input_origins:
                if input_user_name != standardized_name:
                    logger.error( f"      from input name: '{input_user_name}'" )
        logger.error( "  Each species must appear exactly once in the species tree." )
        logger.error( "  If two different input names collapsed to the same standardized name," )
        logger.error( "  rename them in your input newick to be distinguishable after standardization." )
        sys.exit( 1 )

    if duplicate_internals:
        logger.error( f"CRITICAL ERROR: Duplicate user-provided internal node (clade) names found after standardization:" )
        for standardized_name in sorted( duplicate_internals ):
            input_origins = name_origin___inputs[ standardized_name ]
            logger.error( f"  - '{standardized_name}' (appears {internal_standardized_names.count(standardized_name)} times)" )
            for input_user_name in input_origins:
                if input_user_name != standardized_name:
                    logger.error( f"      from input name: '{input_user_name}'" )
        logger.error( "  Each user-provided clade name must be unique after standardization." )
        sys.exit( 1 )


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
    logger.info( 'Script 001: Validate Input Species Tree' )
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

    # ----- Validation: leaf names exist -----
    logger.info( "Validating: every leaf has a name..." )
    check_all_leaves_have_names( root_node, logger )
    logger.info( "  [OK]" )

    # ----- Validation: binary tree -----
    logger.info( "Validating: tree is binary (no polytomies)..." )
    check_binary_tree( root_node, logger )
    logger.info( "  [OK]" )

    # ----- Standardization: replace invalid characters in names -----
    logger.info( "Standardizing: replacing invalid characters in user-provided names..." )
    name_mapping_entries = []  # list of ( input_user_name, standardized_name, node_kind, was_changed )
    nodes = collect_nodes_with_kind( root_node )
    for node, node_kind in nodes:
        if node[ 'name' ]:
            input_user_name = node[ 'name' ]
            standardized_name, was_changed = standardize_name( input_user_name )
            if not standardized_name:
                logger.error( f"CRITICAL ERROR: Name '{input_user_name}' became empty after standardization." )
                logger.error( "  Names must contain at least one ASCII letter, digit, or underscore after invalid character removal." )
                sys.exit( 1 )
            node[ 'name' ] = standardized_name
            name_mapping_entries.append( ( input_user_name, standardized_name, node_kind, was_changed ) )

    changed_count = sum( 1 for _, _, _, was_changed in name_mapping_entries if was_changed )
    logger.info( f"  [OK] {len(name_mapping_entries)} named nodes processed; {changed_count} had character replacements" )

    # ----- Standardization: replace branch lengths with 1.0 -----
    logger.info( f"Standardizing: replacing all branch lengths with {GIGANTIC_STANDARD_BRANCH_LENGTH} (gigantic convention)..." )
    branch_length_replaced_count = 0
    for node, _ in nodes:
        if node[ 'branch_length' ] != GIGANTIC_STANDARD_BRANCH_LENGTH:
            branch_length_replaced_count += 1
        node[ 'branch_length' ] = GIGANTIC_STANDARD_BRANCH_LENGTH
    logger.info( f"  [OK] {branch_length_replaced_count} branch length(s) replaced; all now {GIGANTIC_STANDARD_BRANCH_LENGTH}" )

    # ----- Validation: reserved namespace collisions (after standardization) -----
    logger.info( "Validating: no standardized name collides with ancestral_clade_NNN reserved pattern..." )
    check_for_reserved_namespace_collisions( root_node, name_mapping_entries, logger )
    logger.info( "  [OK]" )

    # ----- Validation: duplicate names (after standardization) -----
    logger.info( "Validating: no duplicate leaf names or duplicate internal node names..." )
    check_for_duplicate_names( name_mapping_entries, logger )
    logger.info( "  [OK]" )

    # ----- Write canonical newick -----
    canonical_newick_string = write_newick( root_node ) + ';'
    output_canonical_newick = output_dir / '1_ai-input_species_tree-canonical.newick'
    output = canonical_newick_string + '\n'
    output_canonical_newick.write_text( output )
    logger.info( f"Wrote canonical newick: {output_canonical_newick.name}" )

    # ----- Write name mapping table -----
    output_name_mapping = output_dir / '1_ai-input_user_name_X_gigantic_name.tsv'
    map_lines = [ 'input_user_name (name as provided in input newick)\tgigantic_standardized_name (name after invalid-character replacement)\tnode_kind (leaf or internal)\twas_changed (true if any character was replaced, false otherwise)' ]
    for input_user_name, standardized_name, node_kind, was_changed in name_mapping_entries:
        output = input_user_name + '\t' + standardized_name + '\t' + node_kind + '\t' + ( 'true' if was_changed else 'false' )
        map_lines.append( output )
    output = '\n'.join( map_lines ) + '\n'
    output_name_mapping.write_text( output )
    logger.info( f"Wrote name mapping table: {output_name_mapping.name} ({len(name_mapping_entries)} entries)" )

    # ----- Write validation report -----
    output_validation_report = output_dir / '1_ai-validation_report.tsv'
    leaf_count = sum( 1 for _, kind in nodes if kind == 'leaf' )
    internal_count = sum( 1 for _, kind in nodes if kind == 'internal' )
    user_named_internal_count = sum( 1 for node, kind in nodes if kind == 'internal' and node[ 'name' ] )
    unlabeled_internal_count = internal_count - user_named_internal_count

    report_lines = [ 'check_name (validation check name)\tcheck_status (PASS or INFO)\tcheck_value (count or other detail)' ]
    report_lines.append( f"input_file_exists\tPASS\t{input_newick_path}" )
    report_lines.append( f"newick_parseable\tPASS\t{len(input_newick_string)} characters" )
    report_lines.append( f"leaves_have_names\tPASS\tall leaves have non-empty names" )
    report_lines.append( f"binary_tree\tPASS\tall internal nodes have exactly 2 children" )
    report_lines.append( f"reserved_namespace_uncollided\tPASS\tno standardized name matches ancestral_clade_NNN" )
    report_lines.append( f"unique_leaf_names\tPASS\t{leaf_count} leaves" )
    report_lines.append( f"unique_internal_node_names\tPASS\t{user_named_internal_count} user-provided internal node names" )
    report_lines.append( f"leaf_count\tINFO\t{leaf_count}" )
    report_lines.append( f"internal_node_count\tINFO\t{internal_count}" )
    report_lines.append( f"user_named_internal_node_count\tINFO\t{user_named_internal_count}" )
    report_lines.append( f"unlabeled_internal_node_count\tINFO\t{unlabeled_internal_count}" )
    report_lines.append( f"name_character_replacements\tINFO\t{changed_count} of {len(name_mapping_entries)} named nodes had character replacements" )
    report_lines.append( f"branch_lengths_replaced\tINFO\t{branch_length_replaced_count} of {leaf_count + internal_count} nodes had branch length changed to {GIGANTIC_STANDARD_BRANCH_LENGTH}" )

    output = '\n'.join( report_lines ) + '\n'
    output_validation_report.write_text( output )
    logger.info( f"Wrote validation report: {output_validation_report.name}" )

    # ----- Final summary -----
    logger.info( '' )
    logger.info( '=' * 78 )
    logger.info( 'SUCCESS' )
    logger.info( f"  {leaf_count} leaves (species)" )
    logger.info( f"  {internal_count} internal nodes ({user_named_internal_count} user-named, {unlabeled_internal_count} unlabeled)" )
    logger.info( f"  {changed_count} of {len(name_mapping_entries)} names had character replacements" )
    logger.info( f"  {branch_length_replaced_count} branch lengths standardized to {GIGANTIC_STANDARD_BRANCH_LENGTH}" )
    logger.info( '=' * 78 )


if __name__ == '__main__':
    main()
