#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Visualize species trees as SVG and PDF using ete3
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 008: Visualize Species Trees

Purpose:
    Generate publication-quality species tree visualizations in SVG and PDF format
    using the ete3 library. Each structure (topology permutation) gets its own
    pair of output files.

    Visualization features:
    - Leaf nodes displayed as circles with genus_species labels
    - Internal nodes displayed as squares with clade ID labels
    - Branch lengths shown when available (configurable)
    - Clade IDs at internal nodes can be hidden (configurable)
    - Colorblind-safe palette (GIGANTIC standard)

    Requires the ete3 library and a headless rendering environment (Qt offscreen).

Inputs:
    --workflow-dir: Workflow root directory
    --no-clade-ids: Flag to hide clade IDs at internal nodes
    --branch-lengths: Flag to show branch lengths on the tree

    Reads:
    - OUTPUT_pipeline/4-output/newick_trees/ (complete species tree Newick files)
    - Fallback: OUTPUT_pipeline/3-output/newick_trees/ (if 4-output not available)

Outputs:
    OUTPUT_pipeline/8-output/8_ai-structure_XXX-species_tree.svg
    OUTPUT_pipeline/8-output/8_ai-structure_XXX-species_tree.pdf
    OUTPUT_pipeline/8-output/8_ai-log-visualize_species_trees.log
"""

import os
# Set Qt platform to offscreen BEFORE importing any Qt-dependent libraries
os.environ[ 'QT_QPA_PLATFORM' ] = 'offscreen'

from pathlib import Path
from typing import Dict, List, Optional
import argparse
import sys
import re
import yaml
import logging


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 008: Visualize species trees as SVG and PDF' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    parser.add_argument( '--no-clade-ids', action='store_true', default=False,
                         help='Hide clade IDs at internal nodes' )
    parser.add_argument( '--branch-lengths', action='store_true', default=False,
                         help='Show branch lengths on the tree' )
    return parser.parse_args()


def setup_logging( log_path: Path ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( 'visualize_species_trees' )
    logger.setLevel( logging.DEBUG )

    # File handler
    file_handler = logging.FileHandler( str( log_path ), mode='w' )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    return logger


def extract_genus_species_from_label( label: str ) -> str:
    """
    Extract genus_species from a clade label like CXXX_Genus_species.

    For multi-word species (e.g., C001_Fonticula_alba), extracts the portion
    after the CXXX_ prefix. For internal nodes (e.g., C068_Basal), returns
    the clade name as-is.
    """
    if '_' in label and label[ 0 ] == 'C' and label[ 1:4 ].isdigit():
        parts_label = label.split( '_', 1 )
        return parts_label[ 1 ]
    return label


def extract_clade_id_from_label( label: str ) -> str:
    """
    Extract the CXXX clade ID from a label like CXXX_Genus_species.
    """
    if '_' in label and label[ 0 ] == 'C' and label[ 1:4 ].isdigit():
        parts_label = label.split( '_', 1 )
        return parts_label[ 0 ]
    return label


def render_tree( newick_string: str, output_svg_path: Path, output_pdf_path: Path,
                 structure_id: str, show_clade_ids: bool, show_branch_lengths: bool,
                 logger: logging.Logger ) -> bool:
    """
    Render a single species tree to SVG and PDF formats using ete3.

    Args:
        newick_string: Newick format tree string
        output_svg_path: Path for SVG output
        output_pdf_path: Path for PDF output
        structure_id: Structure identifier for labeling
        show_clade_ids: Whether to show clade IDs at internal nodes
        show_branch_lengths: Whether to show branch lengths
        logger: Logger instance

    Returns:
        True if rendering succeeded, False otherwise
    """
    try:
        from ete3 import Tree, TreeStyle, NodeStyle, TextFace
    except ImportError:
        logger.error( "CRITICAL ERROR: ete3 library not available!" )
        logger.error( "Install via: conda activate ai_tree_visualization" )
        logger.error( "Or: pip install ete3" )
        return False

    try:
        # Parse the Newick tree
        # Determine format based on whether branch lengths are present
        if ':' in newick_string:
            tree = Tree( newick_string, format=1 )
        else:
            tree = Tree( newick_string, format=8 )

        # ---- Tree Style ----
        tree_style = TreeStyle()
        tree_style.show_leaf_name = False
        tree_style.show_branch_length = show_branch_lengths
        tree_style.branch_vertical_margin = 10
        tree_style.scale = 200
        tree_style.title.add_face( TextFace( f"Species Tree: {structure_id}", fsize=14, bold=True ), column=0 )

        # ---- GIGANTIC Colorblind-Safe Colors ----
        leaf_color = '#003FFF'       # Dark blue (GIGANTIC standard)
        internal_color = '#7FD4FF'   # Light blue (GIGANTIC standard)
        label_color = '#000000'      # Black text

        # ---- Style Each Node ----
        for node in tree.traverse():
            node_style = NodeStyle()
            node_style[ 'hz_line_width' ] = 2
            node_style[ 'vt_line_width' ] = 2

            if node.is_leaf():
                # Leaf node: circle, genus_species label
                node_style[ 'shape' ] = 'circle'
                node_style[ 'size' ] = 8
                node_style[ 'fgcolor' ] = leaf_color

                # Add genus_species label
                leaf_label = extract_genus_species_from_label( node.name )
                leaf_face = TextFace( f" {leaf_label}", fsize=10, fgcolor=label_color )
                node.add_face( leaf_face, column=0, position='branch-right' )

            else:
                # Internal node: square, clade ID label
                node_style[ 'shape' ] = 'square'
                node_style[ 'size' ] = 6
                node_style[ 'fgcolor' ] = internal_color

                if show_clade_ids and node.name:
                    # Show the clade ID at internal nodes
                    clade_id = extract_clade_id_from_label( node.name )
                    internal_face = TextFace( f" {clade_id}", fsize=7, fgcolor=internal_color )
                    node.add_face( internal_face, column=0, position='branch-right' )

            node.set_style( node_style )

        # ---- Render to SVG and PDF ----
        tree.render( str( output_svg_path ), tree_style=tree_style, w=1200 )
        logger.debug( f"  SVG: {output_svg_path.name}" )

        tree.render( str( output_pdf_path ), tree_style=tree_style, w=1200 )
        logger.debug( f"  PDF: {output_pdf_path.name}" )

        return True

    except Exception as rendering_error:
        logger.error( f"  ERROR rendering {structure_id}: {str( rendering_error )}" )
        return False


def main():
    """Main function for species tree visualization."""
    args = parse_arguments()
    workflow_dir = Path( args.workflow_dir )

    # Read config
    config_path = workflow_dir / 'START_HERE-user_config.yaml'
    with open( config_path, 'r' ) as config_file:
        config = yaml.safe_load( config_file )

    species_set_name = config[ 'species_set_name' ]

    # Paths
    output_pipeline_dir = workflow_dir / config[ 'output' ][ 'base_dir' ]
    output_dir = output_pipeline_dir / '8-output'
    output_dir.mkdir( parents=True, exist_ok=True )

    # Log file
    log_path = output_dir / '8_ai-log-visualize_species_trees.log'
    logger = setup_logging( log_path )

    show_clade_ids = not args.no_clade_ids
    show_branch_lengths = args.branch_lengths

    logger.info( "=" * 80 )
    logger.info( "SCRIPT 008: Visualize Species Trees" )
    logger.info( "=" * 80 )
    logger.info( "" )
    logger.info( f"Species set: {species_set_name}" )
    logger.info( f"Show clade IDs: {show_clade_ids}" )
    logger.info( f"Show branch lengths: {show_branch_lengths}" )
    logger.info( "" )

    # ========================================================================
    # STEP 1: Find Newick Tree Files
    # ========================================================================

    logger.info( "Locating Newick tree files..." )

    # Try 4-output first (complete trees), fall back to 3-output
    newick_trees_dir = output_pipeline_dir / '4-output' / 'newick_trees'

    if not newick_trees_dir.exists():
        logger.info( "  4-output/newick_trees/ not found, trying 3-output/newick_trees/..." )
        newick_trees_dir = output_pipeline_dir / '3-output' / 'newick_trees'

    if not newick_trees_dir.exists():
        logger.error( "CRITICAL ERROR: No Newick tree directory found!" )
        logger.error( "  Checked: OUTPUT_pipeline/4-output/newick_trees/" )
        logger.error( "  Checked: OUTPUT_pipeline/3-output/newick_trees/" )
        logger.error( "  Run script 004 (or 003) first." )
        sys.exit( 1 )

    newick_files = sorted( newick_trees_dir.glob( '*.newick' ) )

    if not newick_files:
        logger.error( f"CRITICAL ERROR: No .newick files found in {newick_trees_dir}" )
        sys.exit( 1 )

    logger.info( f"  Found {len( newick_files )} Newick files in {newick_trees_dir.name}/" )
    logger.info( "" )

    # ========================================================================
    # STEP 2: Render Each Tree
    # ========================================================================

    logger.info( "Rendering species tree visualizations..." )
    logger.info( "" )

    success_count = 0
    failure_count = 0

    for newick_file in newick_files:
        # Extract structure_id from filename
        filename = newick_file.stem
        structure_id_match = re.search( r'(structure_\d{3})', filename )

        if not structure_id_match:
            logger.warning( f"  Skipping {filename}: cannot extract structure_id" )
            continue

        structure_id = structure_id_match.group( 1 )

        # Read Newick content
        with open( newick_file, 'r' ) as input_file:
            newick_content = input_file.read().strip()

        if not newick_content:
            logger.warning( f"  Skipping {structure_id}: empty Newick file" )
            continue

        # Output paths
        output_svg_path = output_dir / f"8_ai-{structure_id}-species_tree.svg"
        output_pdf_path = output_dir / f"8_ai-{structure_id}-species_tree.pdf"

        # Render
        structure_number = int( structure_id.replace( 'structure_', '' ) )
        if structure_number <= 10 or structure_number > len( newick_files ) - 5:
            logger.info( f"  Rendering {structure_id}..." )
        elif structure_number == 11:
            logger.info( f"  ... (rendering structures 011-{len( newick_files ) - 5:03d}) ..." )

        rendered = render_tree(
            newick_content, output_svg_path, output_pdf_path,
            structure_id, show_clade_ids, show_branch_lengths, logger
        )

        if rendered:
            success_count += 1
        else:
            failure_count += 1

    logger.info( "" )

    # ========================================================================
    # STEP 3: Summary
    # ========================================================================

    logger.info( "=" * 80 )
    logger.info( "SCRIPT 008 COMPLETE" )
    logger.info( "=" * 80 )
    logger.info( "" )
    logger.info( f"Trees rendered successfully: {success_count}" )
    if failure_count > 0:
        logger.info( f"Trees failed to render: {failure_count}" )
    logger.info( f"Output directory: {output_dir.name}/" )
    logger.info( f"Log file: {log_path.name}" )
    logger.info( "" )
    logger.info( "Output files per structure:" )
    logger.info( "  8_ai-structure_XXX-species_tree.svg" )
    logger.info( "  8_ai-structure_XXX-species_tree.pdf" )
    logger.info( "" )
    logger.info( "Next step: Run script 009 to generate clade-species mappings" )
    logger.info( "" )

    if failure_count > 0 and success_count == 0:
        logger.error( "CRITICAL: All trees failed to render!" )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
