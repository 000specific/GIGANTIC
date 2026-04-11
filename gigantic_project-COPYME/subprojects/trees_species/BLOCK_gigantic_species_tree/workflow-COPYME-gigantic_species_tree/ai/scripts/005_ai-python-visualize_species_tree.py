#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Visualize the fully labeled species tree as SVG using ete3 (soft-fail on tooling errors)
# Human: Eric Edsinger

"""
GIGANTIC trees_species - BLOCK_gigantic_species_tree - Script 005:
Visualize Species Tree

Purpose:
    Render the fully labeled species tree (from Script 002) as an SVG image
    using the ete3 toolkit. This provides a human-viewable representation
    of the species tree for quality checking and presentation.

SOFT-FAIL BEHAVIOR (IMPORTANT):
    This script uses a soft-fail pattern instead of the hard-fail pattern
    used by the other scripts in this BLOCK. If ete3 rendering fails (for
    any reason — import error, Qt issues in headless environments, memory
    errors, etc.), the script:
      - Logs the failure as a WARNING (not an ERROR)
      - Creates a placeholder text file documenting the failure
      - Exits with code 0 (pipeline continues)

    Rationale: Visualization is a "nice-to-have" output. No downstream
    component of GIGANTIC depends on the SVG file existing. The pipeline
    should proceed to produce its other outputs even if visualization
    tooling is broken in the current environment.

PDF NOTE:
    PDF output is NOT attempted by this script. ete3 + Qt has a known
    segfault issue when rendering PDF after SVG on headless compute nodes
    (QPaintDevice cleanup conflict). Trees_gene_families encountered this
    and resolved it by rendering SVG only and documenting that SVG -> PDF
    conversion can be done offline via:

        cairosvg input.svg -o output.pdf
        OR
        inkscape input.svg --export-type=pdf

HEADLESS ENVIRONMENT:
    This script sets QT_QPA_PLATFORM=offscreen before importing ete3 to
    support rendering in headless environments (SLURM compute nodes, CI,
    etc.). The environment variable can also be set externally by
    RUN-workflow.sh.

Inputs (command-line arguments):
    --input-newick     Path to fully labeled species tree from Script 002
                       (typically 2-output/2_ai-species_tree-with_clade_ids_and_names.newick)
    --species-set-name Species set identifier for output filename (e.g., species70)
    --output-dir       Directory to write outputs

Outputs (in --output-dir):
    5_ai-{species_set_name}-species_tree.svg    (if rendering succeeded)
    5_ai-visualization-placeholder.txt           (if rendering failed — soft-fail)
    5_ai-log-visualize_species_tree.log

Exit codes:
    0 — always (soft-fail)

Usage (standalone):
    python3 005_ai-python-visualize_species_tree.py \\
        --input-newick 2-output/2_ai-species_tree-with_clade_ids_and_names.newick \\
        --species-set-name species70 \\
        --output-dir 5-output
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Set headless Qt platform BEFORE importing ete3
# (ete3 imports PyQt which initializes Qt on import, so this must happen first)
os.environ.setdefault( 'QT_QPA_PLATFORM', 'offscreen' )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Visualize the fully labeled species tree as SVG using ete3 (soft-fail on tooling errors)'
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
    log_file = output_dir / '5_ai-log-visualize_species_tree.log'
    logger = logging.getLogger( 'visualize_species_tree' )
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
# SOFT-FAIL HELPERS
# ============================================================================

def write_placeholder_on_failure( output_dir, species_set_name, failure_reason, logger ):
    """
    Write a placeholder text file describing why visualization failed.
    This documents the failure without blocking downstream steps.
    """
    placeholder_path = output_dir / '5_ai-visualization-placeholder.txt'
    placeholder_text = (
        f"GIGANTIC trees_species BLOCK_gigantic_species_tree Script 005\n"
        f"Visualization placeholder file — rendering FAILED (soft-fail)\n"
        f"\n"
        f"Species set: {species_set_name}\n"
        f"Reason: {failure_reason}\n"
        f"\n"
        f"This file exists because Script 005 attempted to render the species tree\n"
        f"as an SVG using the ete3 toolkit but encountered an error. The failure was\n"
        f"soft-failed (exit code 0) because nothing else in GIGANTIC depends on the\n"
        f"visualization output.\n"
        f"\n"
        f"To diagnose: see 5_ai-log-visualize_species_tree.log in this directory.\n"
        f"\n"
        f"To manually render the tree with ete3:\n"
        f"  conda activate ai_gigantic_trees_species\n"
        f"  export QT_QPA_PLATFORM=offscreen\n"
        f"  python3 -c \"from ete3 import Tree; t = Tree('path/to/species_tree.newick', format=1); t.render('out.svg')\"\n"
        f"\n"
        f"Alternative: use an external tree viewer (FigTree, iTOL, dendroscope) on the Newick file.\n"
    )
    placeholder_path.write_text( placeholder_text )
    logger.warning( f"Wrote placeholder: {placeholder_path.name}" )


# ============================================================================
# ETE3 RENDERING
# ============================================================================

def render_species_tree_as_svg( input_newick_path, output_svg_path, logger ):
    """
    Load the species tree via ete3 and render it to an SVG file.
    Raises exceptions on any failure; caller handles them.
    """
    logger.info( "Importing ete3..." )
    from ete3 import Tree, TreeStyle, NodeStyle, TextFace

    logger.info( f"Loading species tree from: {input_newick_path.name}" )
    # format=1 handles internal node names (flexible labels)
    tree = Tree( str( input_newick_path ), format = 1 )

    logger.info( f"Tree loaded: {len(tree)} leaves" )

    # ----- Configure tree style -----
    tree_style = TreeStyle()
    tree_style.show_leaf_name = True
    tree_style.show_branch_length = False
    tree_style.show_branch_support = False
    tree_style.show_scale = False
    tree_style.mode = 'r'  # rectangular layout

    # ----- Configure node styles -----
    for node in tree.traverse():
        node_style = NodeStyle()
        node_style[ 'size' ] = 4
        node_style[ 'fgcolor' ] = '#3288FF'
        node_style[ 'hz_line_color' ] = '#333333'
        node_style[ 'vt_line_color' ] = '#333333'
        node_style[ 'hz_line_width' ] = 1
        node_style[ 'vt_line_width' ] = 1
        node.set_style( node_style )

        # Add internal node name as a small label (if it's an internal node with a name)
        if not node.is_leaf() and node.name:
            internal_face = TextFace( node.name, fsize = 8, fgcolor = '#A9A9A9' )
            internal_face.margin_left = 2
            internal_face.margin_right = 2
            node.add_face( internal_face, column = 1, position = 'branch-right' )

    # ----- Render SVG -----
    logger.info( f"Rendering SVG: {output_svg_path.name}" )
    tree.render( str( output_svg_path ), tree_style = tree_style )

    if not output_svg_path.exists():
        raise RuntimeError( f"ete3 render() returned without error but SVG file does not exist: {output_svg_path}" )

    svg_size_bytes = output_svg_path.stat().st_size
    if svg_size_bytes == 0:
        raise RuntimeError( f"ete3 render() produced an empty SVG file: {output_svg_path}" )

    logger.info( f"SVG rendered successfully: {svg_size_bytes:,} bytes" )


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
    logger.info( 'Script 005: Visualize Species Tree (soft-fail)' )
    logger.info( '=' * 78 )
    logger.info( f"Input newick:      {input_newick_path}" )
    logger.info( f"Species set name:  {species_set_name}" )
    logger.info( f"Output dir:        {output_dir}" )
    logger.info( f"QT_QPA_PLATFORM:   {os.environ.get('QT_QPA_PLATFORM', '(unset)')}" )
    logger.info( '' )

    # ----- Check input exists (still hard-fail on missing input) -----
    if not input_newick_path.exists():
        logger.error( f"CRITICAL ERROR: Input newick file not found: {input_newick_path}" )
        logger.error( "  Cannot proceed with visualization. This is a configuration error, not a tooling error." )
        sys.exit( 1 )

    # ----- Try ete3 rendering (soft-fail on any exception) -----
    output_svg_path = output_dir / f'5_ai-{species_set_name}-species_tree.svg'

    try:
        render_species_tree_as_svg( input_newick_path, output_svg_path, logger )
    except ImportError as import_error:
        logger.warning( f"WARNING: ete3 import failed: {import_error}" )
        logger.warning( "  The ete3 package is not available in the current environment." )
        logger.warning( "  Skipping visualization. This is a soft-fail — the pipeline will continue." )
        write_placeholder_on_failure( output_dir, species_set_name, f"ete3 import error: {import_error}", logger )
    except Exception as rendering_error:
        logger.warning( f"WARNING: ete3 rendering failed: {type(rendering_error).__name__}: {rendering_error}" )
        logger.warning( "  This may be a Qt / PyQt / headless environment issue, or a tree complexity issue." )
        logger.warning( "  Skipping visualization. This is a soft-fail — the pipeline will continue." )
        write_placeholder_on_failure( output_dir, species_set_name, f"{type(rendering_error).__name__}: {rendering_error}", logger )
    else:
        logger.info( '' )
        logger.info( '=' * 78 )
        logger.info( 'SUCCESS' )
        logger.info( f"  SVG rendered: {output_svg_path.name}" )
        logger.info( '=' * 78 )
        sys.exit( 0 )

    # If we get here, rendering failed and we soft-failed
    logger.info( '' )
    logger.info( '=' * 78 )
    logger.info( 'COMPLETED WITH SOFT-FAIL' )
    logger.info( '  Visualization was skipped due to a tooling issue (see WARNING above).' )
    logger.info( '  A placeholder file documents the failure.' )
    logger.info( '  The pipeline will continue; no downstream step depends on visualization.' )
    logger.info( '=' * 78 )
    sys.exit( 0 )


if __name__ == '__main__':
    main()
