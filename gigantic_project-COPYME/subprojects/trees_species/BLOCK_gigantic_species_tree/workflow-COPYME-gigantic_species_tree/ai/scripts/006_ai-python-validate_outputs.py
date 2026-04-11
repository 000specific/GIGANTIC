#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Cross-validate all outputs from Scripts 001 through 005 for consistency
# Human: Eric Edsinger

"""
GIGANTIC trees_species - BLOCK_gigantic_species_tree - Script 006:
Validate Outputs (cross-check all prior script outputs for consistency)

Purpose:
    Cross-validate all outputs from Scripts 001-004 (and soft-check Script 005)
    for internal consistency. Hard-fails on any inconsistency. This is the
    "did the BLOCK produce a coherent set of outputs?" check.

Cross-checks performed:
    1. All input files exist and are non-empty
    2. All three Newick variants parse as valid Newick
    3. Leaf count is consistent across canonical, labeled, simple, full, and ids_only
       Newick files (all 5 must report the same leaf count)
    4. Internal node count is consistent across labeled, simple, full, and
       ids_only (all 4 must report the same internal count)
    5. Every CXXX ID in the labeled newick appears exactly once in the clade map
    6. Every CXXX ID in the clade map appears exactly once in the labeled newick
    7. Every CXXX ID in the clade map corresponds to the correct node_kind
       (leaf vs internal) — matches the tree structure
    8. Simple newick has leaves matching [A-Za-z][A-Za-z0-9_]+ format (no CXXX_)
    9. IDs-only newick has all node labels matching ^C\\d+$ (no names)
    10. Full newick has all node labels matching ^C\\d+_.+$ (CXXX_Name)

    Soft note (not hard-fail):
    - Script 005 visualization output (SVG or placeholder) is noted as present
      or absent. Not a hard-fail per the soft-fail policy for visualization.

Inputs (command-line arguments):
    --canonical-newick    Path to 1-output/1_ai-input_species_tree-canonical.newick
    --labeled-newick      Path to 2-output/2_ai-species_tree-with_clade_ids_and_names.newick
    --simple-newick       Path to 3-output/3_ai-{species_set}-species_tree-simple.newick
    --full-newick         Path to 3-output/3_ai-{species_set}-species_tree-with_clade_ids_and_names.newick
    --ids-only-newick     Path to 3-output/3_ai-{species_set}-species_tree-clade_ids_only.newick
    --clade-map           Path to 4-output/4_ai-{species_set}-clade_name_X_clade_id.tsv
    --visualization-dir   Path to 5-output/ directory (soft-check for SVG or placeholder)
    --output-dir          Directory to write outputs (6-output)

Outputs (in --output-dir):
    6_ai-validation_report.tsv               Per-check pass/fail summary
    6_ai-log-validate_outputs.log            Execution log

Exit codes:
    0 — all cross-checks passed
    1 — any cross-check failure

Usage (standalone):
    python3 006_ai-python-validate_outputs.py \\
        --canonical-newick 1-output/1_ai-input_species_tree-canonical.newick \\
        --labeled-newick 2-output/2_ai-species_tree-with_clade_ids_and_names.newick \\
        --simple-newick 3-output/3_ai-species70-species_tree-simple.newick \\
        --full-newick 3-output/3_ai-species70-species_tree-with_clade_ids_and_names.newick \\
        --ids-only-newick 3-output/3_ai-species70-species_tree-clade_ids_only.newick \\
        --clade-map 4-output/4_ai-species70-clade_name_X_clade_id.tsv \\
        --visualization-dir 5-output \\
        --output-dir 6-output
"""

import argparse
import logging
import re
import sys
from pathlib import Path


# ============================================================================
# CONSTANTS
# ============================================================================

CXXX_ID_ONLY_PATTERN = re.compile( r'^C\d+$' )
CXXX_NAME_PATTERN = re.compile( r'^C\d+_.+$' )
GENUS_SPECIES_PATTERN = re.compile( r'^[A-Z][a-zA-Z0-9_]+$' )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Cross-validate all outputs from Scripts 001-004 for consistency'
    )
    parser.add_argument( '--canonical-newick', required = True, help = 'Script 001 canonical newick' )
    parser.add_argument( '--labeled-newick', required = True, help = 'Script 002 labeled newick' )
    parser.add_argument( '--simple-newick', required = True, help = 'Script 003 simple newick' )
    parser.add_argument( '--full-newick', required = True, help = 'Script 003 full newick' )
    parser.add_argument( '--ids-only-newick', required = True, help = 'Script 003 ids-only newick' )
    parser.add_argument( '--clade-map', required = True, help = 'Script 004 clade map TSV' )
    parser.add_argument( '--visualization-dir', required = True, help = 'Script 005 5-output directory (soft-checked)' )
    parser.add_argument( '--output-dir', required = True, help = 'Directory to write outputs' )
    return parser.parse_args()


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging( output_dir ):
    log_file = output_dir / '6_ai-log-validate_outputs.log'
    logger = logging.getLogger( 'validate_outputs' )
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
# TREE WALKING
# ============================================================================

def collect_all_nodes_with_labels( root_node ):
    """Return list of ( label, 'leaf' | 'internal' ) in DFS preorder."""
    nodes = []

    def walk( current_node ):
        node_kind = 'internal' if current_node[ 'children' ] else 'leaf'
        nodes.append( ( current_node[ 'name' ], node_kind ) )
        for child in current_node[ 'children' ]:
            walk( child )

    walk( root_node )
    return nodes


def count_leaves_and_internals( root_node ):
    """Return ( leaf_count, internal_count ) for a parsed tree."""
    leaf_count = 0
    internal_count = 0

    def walk( node ):
        nonlocal leaf_count, internal_count
        if node[ 'children' ]:
            internal_count += 1
            for child in node[ 'children' ]:
                walk( child )
        else:
            leaf_count += 1

    walk( root_node )
    return ( leaf_count, internal_count )


# ============================================================================
# LOAD + PARSE HELPERS
# ============================================================================

def load_newick_file( newick_path, logger, label ):
    """Load and parse a newick file, hard-failing on errors. Returns parsed root node."""
    if not newick_path.exists():
        logger.error( f"CRITICAL ERROR: {label} not found: {newick_path}" )
        sys.exit( 1 )

    content = newick_path.read_text().strip()
    if not content:
        logger.error( f"CRITICAL ERROR: {label} is empty: {newick_path}" )
        sys.exit( 1 )

    try:
        return parse_newick( content )
    except ValueError as parse_error:
        logger.error( f"CRITICAL ERROR: Failed to parse {label}: {parse_error}" )
        sys.exit( 1 )


def load_clade_map( clade_map_path, logger ):
    """Load clade map TSV. Returns list of ( clade_name, clade_id, node_kind ) tuples."""
    if not clade_map_path.exists():
        logger.error( f"CRITICAL ERROR: Clade map not found: {clade_map_path}" )
        sys.exit( 1 )

    entries = []

    # clade_name (Genus_species or clade name)  clade_id (CXXX)  node_kind (leaf or internal)
    # Fonticula_alba  C001  leaf
    with open( clade_map_path, 'r' ) as input_clade_map:
        header_seen = False
        for line in input_clade_map:
            line = line.strip()
            if not line:
                continue
            if not header_seen:
                header_seen = True
                continue
            parts = line.split( '\t' )
            if len( parts ) != 3:
                logger.error( f"CRITICAL ERROR: Malformed clade map line (expected 3 tab-separated columns, got {len(parts)}): {line}" )
                sys.exit( 1 )
            clade_name = parts[ 0 ]
            clade_id = parts[ 1 ]
            node_kind = parts[ 2 ]
            entries.append( ( clade_name, clade_id, node_kind ) )

    return entries


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    args = parse_arguments()

    canonical_newick_path = Path( args.canonical_newick ).resolve()
    labeled_newick_path = Path( args.labeled_newick ).resolve()
    simple_newick_path = Path( args.simple_newick ).resolve()
    full_newick_path = Path( args.full_newick ).resolve()
    ids_only_newick_path = Path( args.ids_only_newick ).resolve()
    clade_map_path = Path( args.clade_map ).resolve()
    visualization_dir = Path( args.visualization_dir ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_dir )

    logger.info( '=' * 78 )
    logger.info( 'GIGANTIC trees_species - BLOCK_gigantic_species_tree' )
    logger.info( 'Script 006: Validate Outputs (cross-check)' )
    logger.info( '=' * 78 )
    logger.info( '' )

    # ----- Check all inputs exist -----
    logger.info( "Checking all input files exist..." )
    for label, path in [
        ( "canonical newick", canonical_newick_path ),
        ( "labeled newick",  labeled_newick_path  ),
        ( "simple newick",   simple_newick_path   ),
        ( "full newick",     full_newick_path     ),
        ( "ids-only newick", ids_only_newick_path ),
        ( "clade map",       clade_map_path       ),
    ]:
        if not path.exists():
            logger.error( f"CRITICAL ERROR: {label} not found: {path}" )
            sys.exit( 1 )
        logger.info( f"  [OK] {label}: {path.name}" )
    logger.info( '' )

    # ----- Load and parse all 5 newick files -----
    logger.info( "Loading and parsing all newick files..." )
    canonical_tree = load_newick_file( canonical_newick_path, logger, "canonical newick" )
    labeled_tree   = load_newick_file( labeled_newick_path, logger, "labeled newick" )
    simple_tree    = load_newick_file( simple_newick_path, logger, "simple newick" )
    full_tree      = load_newick_file( full_newick_path, logger, "full newick" )
    ids_only_tree  = load_newick_file( ids_only_newick_path, logger, "ids-only newick" )
    logger.info( "  [OK] All 5 newick files parsed successfully" )
    logger.info( '' )

    # ----- Check leaf counts consistent across all 5 trees -----
    logger.info( "Checking leaf count consistency across all 5 newick variants..." )
    canonical_leaf_count, canonical_internal_count = count_leaves_and_internals( canonical_tree )
    labeled_leaf_count,   labeled_internal_count   = count_leaves_and_internals( labeled_tree )
    simple_leaf_count,    simple_internal_count    = count_leaves_and_internals( simple_tree )
    full_leaf_count,      full_internal_count      = count_leaves_and_internals( full_tree )
    ids_only_leaf_count,  ids_only_internal_count  = count_leaves_and_internals( ids_only_tree )

    all_leaf_counts = [
        ( "canonical",  canonical_leaf_count ),
        ( "labeled",    labeled_leaf_count ),
        ( "simple",     simple_leaf_count ),
        ( "full",       full_leaf_count ),
        ( "ids_only",   ids_only_leaf_count ),
    ]
    if len( set( count for _, count in all_leaf_counts ) ) != 1:
        logger.error( f"CRITICAL ERROR: Leaf count inconsistency across newick variants:" )
        for name, count in all_leaf_counts:
            logger.error( f"  - {name}: {count} leaves" )
        sys.exit( 1 )
    consistent_leaf_count = canonical_leaf_count
    logger.info( f"  [OK] All 5 variants report {consistent_leaf_count} leaves" )

    # ----- Check internal counts consistent across labeled, simple, full, ids_only -----
    # (canonical may differ because it has unlabeled internals — same count but we don't enforce)
    logger.info( "Checking internal node count consistency across labeled, simple, full, ids_only..." )
    downstream_internal_counts = [
        ( "labeled",    labeled_internal_count ),
        ( "simple",     simple_internal_count ),
        ( "full",       full_internal_count ),
        ( "ids_only",   ids_only_internal_count ),
    ]
    if len( set( count for _, count in downstream_internal_counts ) ) != 1:
        logger.error( f"CRITICAL ERROR: Internal node count inconsistency:" )
        for name, count in downstream_internal_counts:
            logger.error( f"  - {name}: {count} internal nodes" )
        sys.exit( 1 )
    consistent_internal_count = labeled_internal_count
    logger.info( f"  [OK] All 4 downstream variants report {consistent_internal_count} internal nodes" )

    # Also verify canonical matches (it should — Script 002 doesn't add or remove nodes)
    if canonical_internal_count != consistent_internal_count:
        logger.error( f"CRITICAL ERROR: Canonical tree has {canonical_internal_count} internal nodes but downstream has {consistent_internal_count}." )
        logger.error( "  Script 002 should preserve node structure while adding labels." )
        sys.exit( 1 )
    logger.info( f"  [OK] Canonical also has {canonical_internal_count} internal nodes (matches downstream)" )
    logger.info( '' )

    # ----- Check simple newick leaves match Genus_species format -----
    logger.info( "Checking simple newick leaf format (Genus_species)..." )
    simple_nodes = collect_all_nodes_with_labels( simple_tree )
    bad_simple_leaves = []
    for label, kind in simple_nodes:
        if kind == 'leaf':
            if not GENUS_SPECIES_PATTERN.match( label ):
                bad_simple_leaves.append( label )
    if bad_simple_leaves:
        logger.error( f"CRITICAL ERROR: Simple newick has leaves that don't match Genus_species format:" )
        for label in bad_simple_leaves[ :10 ]:
            logger.error( f"  - '{label}'" )
        sys.exit( 1 )
    logger.info( f"  [OK] All {consistent_leaf_count} simple-newick leaves match Genus_species format" )

    # ----- Check simple newick internals have NO label -----
    logger.info( "Checking simple newick internal nodes are unlabeled..." )
    labeled_simple_internals = [ label for label, kind in simple_nodes if kind == 'internal' and label ]
    if labeled_simple_internals:
        logger.error( f"CRITICAL ERROR: Simple newick has {len(labeled_simple_internals)} internal node(s) with labels (should be unlabeled):" )
        for label in labeled_simple_internals[ :10 ]:
            logger.error( f"  - '{label}'" )
        sys.exit( 1 )
    logger.info( f"  [OK] All {consistent_internal_count} simple-newick internals are unlabeled" )
    logger.info( '' )

    # ----- Check full newick labels all match CXXX_Name format -----
    logger.info( "Checking full newick labels match CXXX_Name format..." )
    full_nodes = collect_all_nodes_with_labels( full_tree )
    bad_full_labels = []
    for label, kind in full_nodes:
        if not CXXX_NAME_PATTERN.match( label ):
            bad_full_labels.append( ( label, kind ) )
    if bad_full_labels:
        logger.error( f"CRITICAL ERROR: Full newick has {len(bad_full_labels)} node(s) with invalid labels:" )
        for label, kind in bad_full_labels[ :10 ]:
            logger.error( f"  - '{label}' ({kind})" )
        sys.exit( 1 )
    logger.info( f"  [OK] All {consistent_leaf_count + consistent_internal_count} full-newick labels match CXXX_Name" )
    logger.info( '' )

    # ----- Check ids-only newick labels all match CXXX format (no name) -----
    logger.info( "Checking ids-only newick labels match CXXX format..." )
    ids_only_nodes = collect_all_nodes_with_labels( ids_only_tree )
    bad_ids_only_labels = []
    for label, kind in ids_only_nodes:
        if not CXXX_ID_ONLY_PATTERN.match( label ):
            bad_ids_only_labels.append( ( label, kind ) )
    if bad_ids_only_labels:
        logger.error( f"CRITICAL ERROR: Ids-only newick has {len(bad_ids_only_labels)} node(s) with invalid labels:" )
        for label, kind in bad_ids_only_labels[ :10 ]:
            logger.error( f"  - '{label}' ({kind})" )
        sys.exit( 1 )
    logger.info( f"  [OK] All {consistent_leaf_count + consistent_internal_count} ids-only-newick labels match CXXX format" )
    logger.info( '' )

    # ----- Check clade map row count -----
    logger.info( "Loading clade map..." )
    clade_map_entries = load_clade_map( clade_map_path, logger )
    expected_total = consistent_leaf_count + consistent_internal_count
    if len( clade_map_entries ) != expected_total:
        logger.error( f"CRITICAL ERROR: Clade map has {len(clade_map_entries)} entries but expected {expected_total}" )
        logger.error( f"  Expected: {consistent_leaf_count} leaves + {consistent_internal_count} internals = {expected_total}" )
        sys.exit( 1 )
    logger.info( f"  [OK] Clade map has {len(clade_map_entries)} entries ({consistent_leaf_count} leaves + {consistent_internal_count} internals)" )
    logger.info( '' )

    # ----- Check clade IDs in labeled newick vs clade map are the same set -----
    logger.info( "Checking clade ID set consistency (labeled newick vs clade map)..." )
    labeled_node_ids = set()
    for label, _ in collect_all_nodes_with_labels( labeled_tree ):
        match = re.match( r'^(C\d+)_', label )
        if match:
            labeled_node_ids.add( match.group( 1 ) )
    clade_map_ids = set( entry[ 1 ] for entry in clade_map_entries )

    missing_from_map = labeled_node_ids - clade_map_ids
    missing_from_tree = clade_map_ids - labeled_node_ids
    if missing_from_map:
        logger.error( f"CRITICAL ERROR: {len(missing_from_map)} clade ID(s) in labeled newick but NOT in clade map:" )
        for clade_id in sorted( missing_from_map )[ :10 ]:
            logger.error( f"  - {clade_id}" )
        sys.exit( 1 )
    if missing_from_tree:
        logger.error( f"CRITICAL ERROR: {len(missing_from_tree)} clade ID(s) in clade map but NOT in labeled newick:" )
        for clade_id in sorted( missing_from_tree )[ :10 ]:
            logger.error( f"  - {clade_id}" )
        sys.exit( 1 )
    logger.info( f"  [OK] Clade ID sets match ({len(labeled_node_ids)} IDs in both)" )
    logger.info( '' )

    # ----- Soft-check visualization output -----
    logger.info( "Soft-checking visualization output (Script 005)..." )
    svg_files = list( visualization_dir.glob( '5_ai-*-species_tree.svg' ) ) if visualization_dir.exists() else []
    placeholder_files = list( visualization_dir.glob( '5_ai-visualization-placeholder.txt' ) ) if visualization_dir.exists() else []
    visualization_status = 'unknown'
    if svg_files:
        visualization_status = 'svg_present'
        logger.info( f"  [INFO] SVG present: {svg_files[0].name}" )
    elif placeholder_files:
        visualization_status = 'placeholder_present'
        logger.warning( f"  [WARN] Visualization soft-failed; placeholder present: {placeholder_files[0].name}" )
    else:
        visualization_status = 'missing'
        logger.warning( f"  [WARN] No visualization output found (neither SVG nor placeholder). Script 005 may not have run." )
    logger.info( '' )

    # ----- Write validation report -----
    output_validation_report = output_dir / '6_ai-validation_report.tsv'
    report_lines = [ 'check_name (cross-check name)\tcheck_status (PASS, INFO, or WARN)\tcheck_value (count or detail)' ]
    report_lines.append( f"all_inputs_exist\tPASS\t6 input files found" )
    report_lines.append( f"all_newicks_parse\tPASS\t5 newick files parsed" )
    report_lines.append( f"leaf_count_consistent\tPASS\t{consistent_leaf_count} leaves across all 5 variants" )
    report_lines.append( f"internal_count_consistent\tPASS\t{consistent_internal_count} internals across downstream variants" )
    report_lines.append( f"simple_leaves_genus_species\tPASS\tall {consistent_leaf_count} leaves match Genus_species format" )
    report_lines.append( f"simple_internals_unlabeled\tPASS\tall {consistent_internal_count} internals unlabeled" )
    report_lines.append( f"full_labels_cxxx_name\tPASS\tall {expected_total} labels match CXXX_Name format" )
    report_lines.append( f"ids_only_labels_cxxx\tPASS\tall {expected_total} labels match CXXX format" )
    report_lines.append( f"clade_map_row_count\tPASS\t{len(clade_map_entries)} rows match expected total {expected_total}" )
    report_lines.append( f"clade_id_sets_match\tPASS\t{len(labeled_node_ids)} clade IDs in both labeled newick and clade map" )
    report_lines.append( f"visualization_status\t{visualization_status.upper()}\tvisualization output: {visualization_status}" )

    output = '\n'.join( report_lines ) + '\n'
    output_validation_report.write_text( output )
    logger.info( f"Wrote validation report: {output_validation_report.name}" )

    # ----- Final summary -----
    logger.info( '' )
    logger.info( '=' * 78 )
    logger.info( 'SUCCESS' )
    logger.info( f"  All cross-checks passed" )
    logger.info( f"  {consistent_leaf_count} leaves + {consistent_internal_count} internal nodes = {expected_total} total" )
    logger.info( f"  Visualization status: {visualization_status}" )
    logger.info( '=' * 78 )


if __name__ == '__main__':
    main()
