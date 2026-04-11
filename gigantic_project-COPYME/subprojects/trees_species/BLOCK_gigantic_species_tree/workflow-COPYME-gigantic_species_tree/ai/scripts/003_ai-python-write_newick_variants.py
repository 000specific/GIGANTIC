#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Emit three Newick format variants from the fully labeled species tree
# Human: Eric Edsinger

"""
GIGANTIC trees_species - BLOCK_gigantic_species_tree - Script 003:
Write Newick Variants

Purpose:
    Read the fully labeled species tree from Script 002 output and emit three
    Newick format variants, each useful for a different downstream purpose.

Three output formats:
    1. SIMPLE
       - Leaves: Genus_species only (CXXX_ prefix stripped)
       - Internal nodes: no label at all
       - Branch lengths: still present (1.0)
       - Use: plain downstream-consumable species tree; valid Newick; the
         format most external tree tools expect.

    2. FULL (with clade ids and names)
       - Leaves: CXXX_Genus_species
       - Internal nodes: CXXX_Clade_Name
       - Branch lengths: present
       - Use: human-readable + machine-readable canonical form; what most
         GIGANTIC downstream pipelines consume; mirrors the species67
         leonid-tree format.

    3. IDS_ONLY
       - Leaves: CXXX (no species name)
       - Internal nodes: CXXX (no clade name)
       - Branch lengths: present
       - Use: compact structural format; requires the clade map TSV from
         Script 004 to interpret.

Inputs (command-line arguments):
    --input-newick     Path to fully labeled species tree from Script 002
                       (typically 2-output/2_ai-species_tree-with_clade_ids_and_names.newick)
    --species-set-name Species set identifier for output filenames (e.g., species70)
    --output-dir       Directory to write outputs

Outputs (in --output-dir):
    3_ai-{species_set_name}-species_tree-simple.newick
    3_ai-{species_set_name}-species_tree-with_clade_ids_and_names.newick
    3_ai-{species_set_name}-species_tree-clade_ids_only.newick
    3_ai-log-write_newick_variants.log

Exit codes:
    0 — all three variants written successfully
    1 — any failure (input parse, output write)

Usage (standalone):
    python3 003_ai-python-write_newick_variants.py \\
        --input-newick 2-output/2_ai-species_tree-with_clade_ids_and_names.newick \\
        --species-set-name species70 \\
        --output-dir 3-output
"""

import argparse
import logging
import re
import sys
from pathlib import Path


# ============================================================================
# CONSTANTS
# ============================================================================

CXXX_PREFIX_PATTERN = re.compile( r'^C\d+_' )
CXXX_ID_PATTERN = re.compile( r'^(C\d+)' )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Emit three Newick format variants (simple, full, ids-only) from the fully labeled species tree'
    )
    parser.add_argument(
        '--input-newick',
        required = True,
        help = 'Path to fully labeled species tree from Script 002'
    )
    parser.add_argument(
        '--species-set-name',
        required = True,
        help = 'Species set identifier for output filenames (e.g., species70)'
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
    log_file = output_dir / '3_ai-log-write_newick_variants.log'
    logger = logging.getLogger( 'write_newick_variants' )
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
# NAME HELPERS
# ============================================================================

def strip_clade_id_from_name( name ):
    """Strip leading CXXX_ from a node name, leaving just the bare name."""
    return CXXX_PREFIX_PATTERN.sub( '', name )


def extract_clade_id_from_name( name ):
    """Extract just the CXXX prefix from a CXXX_Name label."""
    match = CXXX_ID_PATTERN.match( name )
    return match.group( 1 ) if match else name


# ============================================================================
# NEWICK WRITERS (three format variants)
# ============================================================================

def write_newick_full( node ):
    """
    FULL format: CXXX_Genus_species at leaves, CXXX_Clade_Name at internals.
    This is the input format (no transformation) — just re-emit as-is.
    Returns Newick string without trailing semicolon.
    """
    if node[ 'children' ]:
        children_string = ','.join( write_newick_full( child ) for child in node[ 'children' ] )
        label_string = node[ 'name' ]
        if node[ 'branch_length' ]:
            label_string += ':' + node[ 'branch_length' ]
        return f"({children_string}){label_string}"
    else:
        label_string = node[ 'name' ]
        if node[ 'branch_length' ]:
            label_string += ':' + node[ 'branch_length' ]
        return label_string


def write_newick_simple( node ):
    """
    SIMPLE format: Genus_species at leaves only (CXXX_ stripped),
    internal nodes have no label at all (empty string, only branch length).
    Returns Newick string without trailing semicolon.
    """
    if node[ 'children' ]:
        children_string = ','.join( write_newick_simple( child ) for child in node[ 'children' ] )
        label_string = ''
        if node[ 'branch_length' ]:
            label_string += ':' + node[ 'branch_length' ]
        return f"({children_string}){label_string}"
    else:
        label_string = strip_clade_id_from_name( node[ 'name' ] )
        if node[ 'branch_length' ]:
            label_string += ':' + node[ 'branch_length' ]
        return label_string


def write_newick_ids_only( node ):
    """
    IDS_ONLY format: CXXX at every node (leaves and internals), no names.
    Returns Newick string without trailing semicolon.
    """
    if node[ 'children' ]:
        children_string = ','.join( write_newick_ids_only( child ) for child in node[ 'children' ] )
        label_string = extract_clade_id_from_name( node[ 'name' ] )
        if node[ 'branch_length' ]:
            label_string += ':' + node[ 'branch_length' ]
        return f"({children_string}){label_string}"
    else:
        label_string = extract_clade_id_from_name( node[ 'name' ] )
        if node[ 'branch_length' ]:
            label_string += ':' + node[ 'branch_length' ]
        return label_string


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
    logger.info( 'Script 003: Write Newick Variants' )
    logger.info( '=' * 78 )
    logger.info( f"Input newick:       {input_newick_path}" )
    logger.info( f"Species set name:   {species_set_name}" )
    logger.info( f"Output dir:         {output_dir}" )
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

    # ----- Write SIMPLE variant -----
    output_simple = output_dir / f'3_ai-{species_set_name}-species_tree-simple.newick'
    simple_newick_string = write_newick_simple( root_node ) + ';'
    output = simple_newick_string + '\n'
    output_simple.write_text( output )
    logger.info( f"Wrote SIMPLE variant: {output_simple.name}" )

    # ----- Write FULL variant -----
    output_full = output_dir / f'3_ai-{species_set_name}-species_tree-with_clade_ids_and_names.newick'
    full_newick_string = write_newick_full( root_node ) + ';'
    output = full_newick_string + '\n'
    output_full.write_text( output )
    logger.info( f"Wrote FULL variant: {output_full.name}" )

    # ----- Write IDS_ONLY variant -----
    output_ids_only = output_dir / f'3_ai-{species_set_name}-species_tree-clade_ids_only.newick'
    ids_only_newick_string = write_newick_ids_only( root_node ) + ';'
    output = ids_only_newick_string + '\n'
    output_ids_only.write_text( output )
    logger.info( f"Wrote IDS_ONLY variant: {output_ids_only.name}" )

    # ----- Final summary -----
    logger.info( '' )
    logger.info( '=' * 78 )
    logger.info( 'SUCCESS' )
    logger.info( f"  3 Newick variants written for {species_set_name}" )
    logger.info( f"  Simple (plain tree):        {output_simple.name} ({len(simple_newick_string)} chars)" )
    logger.info( f"  Full (with clade ids+names): {output_full.name} ({len(full_newick_string)} chars)" )
    logger.info( f"  IDs only (CXXX only):       {output_ids_only.name} ({len(ids_only_newick_string)} chars)" )
    logger.info( '=' * 78 )


if __name__ == '__main__':
    main()
