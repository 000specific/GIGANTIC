#!/usr/bin/env python3
# GIGANTIC BLOCK 3 - Script 007: Visualize Trees (Human-Friendly)
# AI: Claude Code | Sonnet 4.5 | 2025 November 06 23:32 | Purpose: Visualize phylogenetic trees optimized for human viewing and interpretation
# Human: Eric Edsinger

"""
Visualize phylogenetic trees optimized for human viewing.

This script takes FastTree and IQ-TREE Newick files and generates both SVG and PDF
visualizations of the phylogenetic trees. Optimized for human readability with smaller
symbols (10px) and minimal padding. It uses ETE3 toolkit for tree rendering.

Usage:
    python3 007_ai-python-visualize_phylogenetic_trees-human_friendly.py [options]
    
Options:
    --no-bootstraps          Hide bootstrap values (shown by default)
    --no-ultrafast-bootstraps Hide ultrafast bootstrap values (shown by default)
    --no-node-identifiers    Hide clade ID labels (shown by default)
    --no-color               Disable colored bootstrap values (colored by default)
    --branch_lengths         Show branch lengths with scale bar (default: no)
    --bootstrap_threshold    Threshold for bootstrap coloring (default: 0.8)
    --ultrafast_threshold    Threshold for ultrafast bootstrap coloring (default: 0.95)

Examples:
    # Default visualization (bootstraps, UFBoot, and clade IDs shown)
    python3 007_ai-python-visualize_phylogenetic_trees-human_friendly.py
    
    # Add branch lengths with scale bar
    python3 007_ai-python-visualize_phylogenetic_trees-human_friendly.py --branch_lengths
    
    # Custom bootstrap threshold (default is 0.8)
    python3 007_ai-python-visualize_phylogenetic_trees-human_friendly.py --bootstrap_threshold 0.9

Notes:
    - FastTree trees show bootstrap support values (shown by default)
    - IQ-TREE trees show SH-aLRT (top) and UFBoot (bottom) support values (both shown by default)
    - Clade IDs (CNNN format) shown by default as medium-light grey labels on right side of all nodes
    - Bootstrap values colored: red if below threshold (0.8), blueberry blue if above
    - Scale bar only appears when --branch_lengths is specified
    - Clade numbering: species/leaves first (top to bottom), then internal/ancestral clades
    - Leaf nodes shown as circles (○), internal nodes shown as squares (□)
    - Node symbol size: 10 pixels (optimized for human viewing)
    - Font size: 20 pixels (all text elements)
    - Text padding: 1 pixel (minimal padding for clean appearance)
    - Use clade IDs to identify rooting points for re-rooting trees

Input Files:
    - FastTree Newick file: output/5-AGS-species67_T1-species37-innexin_pannexin.fasttree
    - IQ-TREE Newick file: output/6-AGS-species67_T1-species37-innexin_pannexin.treefile

Output Files:
    - output/7-AGS-species67_T1-species37-innexin_pannexin-fasttree-human_friendly.svg
    - output/7-AGS-species67_T1-species37-innexin_pannexin-fasttree-human_friendly.pdf
    - output/7-AGS-species67_T1-species37-innexin_pannexin-iqtree-human_friendly.svg
    - output/7-AGS-species67_T1-species37-innexin_pannexin-iqtree-human_friendly.pdf

Log File:
    - 7_ai-log-visualize_trees.log

Requirements:
    - conda environment: ai_tree_visualization
    - ete3 package
"""

from pathlib import Path
from typing import Tuple, Optional
import logging
from datetime import datetime
import os
import sys
import argparse

# Set up headless rendering for HPC environment (no display)
os.environ[ 'QT_QPA_PLATFORM' ] = 'offscreen'

from ete3 import Tree, TreeStyle, NodeStyle, TextFace, faces


class VisualizationConfig:
    """Configuration for tree visualization options."""
    
    def __init__(
        self,
        show_bootstraps: bool = True,
        show_ultrafast_bootstraps: bool = True,
        show_branch_lengths: bool = False,
        bootstrap_threshold: float = 0.8,
        ultrafast_threshold: float = 0.95,
        color_bootstraps: bool = False,
        show_node_identifiers: bool = True
    ):
        self.show_bootstraps = show_bootstraps
        self.show_ultrafast_bootstraps = show_ultrafast_bootstraps
        self.show_branch_lengths = show_branch_lengths
        self.bootstrap_threshold = bootstrap_threshold
        self.ultrafast_threshold = ultrafast_threshold
        self.show_node_identifiers = show_node_identifiers
        
        # Auto-enable coloring if bootstraps are shown
        if show_bootstraps or show_ultrafast_bootstraps:
            self.color_bootstraps = True
        else:
            self.color_bootstraps = color_bootstraps
        
        # Color definitions (bright red and blueberry blue)
        self.color_below_threshold = "#FF0000"  # Bright red
        self.color_above_threshold = "#5856D6"  # Blueberry blue (Apple)
        self.color_clade_id = "#A9A9A9"  # Medium-light grey (dark gray) for clade IDs
        self.color_branch_length = "#5AC8FA"  # Teal (Apple)
        
        # Node symbol settings (optimized for human viewing)
        self.branch_line_width = 2  # Base branch line width
        self.node_symbol_size = 10  # 10 pixels for human-friendly viewing
        self.leaf_symbol = "circle"  # Tips/leaves/species
        self.internal_symbol = "square"  # Internal nodes/ancestral clades
        
        # Font sizes for different text elements (all 20 for readability)
        self.font_size_leaf_names = 20  # Tip/leaf names
        self.font_size_small = 20  # Bootstraps, branch lengths, clade identifiers
        
        # Spacing for leaf names and clade identifiers (minimal for clean appearance)
        self.leaf_name_margin = 5  # pixels of space between branch end and tip name
        self.text_padding = 1  # pixels of padding on all sides for minimal spacing


def parse_arguments() -> VisualizationConfig:
    """
    Parse command-line arguments.
    
    Returns:
        VisualizationConfig object with user settings
    """
    parser = argparse.ArgumentParser(
        description='Visualize phylogenetic trees with customizable annotations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--no-bootstraps',
        action='store_true',
        help='Hide bootstrap support values (shown by default)'
    )
    
    parser.add_argument(
        '--no-ultrafast-bootstraps',
        action='store_true',
        help='Hide ultrafast bootstrap support values for IQ-TREE (shown by default)'
    )
    
    parser.add_argument(
        '--branch_lengths',
        action='store_true',
        help='Show branch lengths (default: no)'
    )
    
    parser.add_argument(
        '--bootstrap_threshold',
        type=float,
        default=0.8,
        help='Threshold for bootstrap coloring, values below are red (default: 0.8)'
    )
    
    parser.add_argument(
        '--ultrafast_threshold',
        type=float,
        default=0.95,
        help='Threshold for ultrafast bootstrap coloring, values below are red (default: 0.95)'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored bootstrap values (colored by default)'
    )
    
    parser.add_argument(
        '--no-node-identifiers',
        action='store_true',
        help='Hide clade ID labels (CNNN format) - shown by default'
    )
    
    arguments = parser.parse_args()
    
    return VisualizationConfig(
        show_bootstraps=not arguments.no_bootstraps,
        show_ultrafast_bootstraps=not arguments.no_ultrafast_bootstraps,
        show_branch_lengths=arguments.branch_lengths,
        bootstrap_threshold=arguments.bootstrap_threshold,
        ultrafast_threshold=arguments.ultrafast_threshold,
        color_bootstraps=not arguments.no_color,
        show_node_identifiers=not arguments.no_node_identifiers
    )


def setup_logging( log_file_path: Path ) -> logging.Logger:
    """
    Configure logging for the script.
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler( log_file_path ),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger( __name__ )


def parse_iqtree_support_values( tree: Tree, logger: logging.Logger ) -> None:
    """
    Parse IQ-TREE dual support values (SH-aLRT/UFBoot) from node names.
    
    IQ-TREE format: node_name like "68.2/67" means SH-aLRT=68.2, UFBoot=67
    
    Args:
        tree: ETE3 Tree object
        logger: Logger instance
    """
    parsed_count = 0
    
    for node in tree.traverse():
        if not node.is_leaf() and hasattr( node, 'name' ) and node.name:
            # Try to parse dual support format: "value1/value2"
            if '/' in str( node.name ):
                try:
                    parts_node_name = node.name.split( '/' )
                    if len( parts_node_name ) == 2:
                        sh_alrt = float( parts_node_name[ 0 ] )
                        ufboot = float( parts_node_name[ 1 ] )
                        
                        # Store both values as node attributes
                        node.add_features( sh_alrt_support=sh_alrt )
                        node.add_features( ufboot_support=ufboot )
                        parsed_count += 1
                        
                except ( ValueError, TypeError, IndexError ) as error:
                    logger.warning( f"Could not parse dual support from node name: {node.name}" )
    
    if parsed_count > 0:
        logger.info( f"Parsed {parsed_count} IQ-TREE dual support values (SH-aLRT/UFBoot)" )


def load_tree_from_newick( newick_file_path: Path, logger: logging.Logger ) -> Tree:
    """
    Load a phylogenetic tree from a Newick format file.
    
    Args:
        newick_file_path: Path to the Newick file
        logger: Logger instance for status messages
        
    Returns:
        ETE3 Tree object
        
    Raises:
        FileNotFoundError: If the Newick file doesn't exist
        ValueError: If the Newick file cannot be parsed
    """
    logger.info( f"Loading tree from: {newick_file_path}" )
    
    if not newick_file_path.exists():
        error_message = f"Newick file not found: {newick_file_path}"
        logger.error( error_message )
        raise FileNotFoundError( error_message )
    
    # Try different newick formats
    # Format 0: flexible with support values
    # Format 2: internal node names instead of support values
    formats_to_try = [ 0, 2, 1 ]
    
    for newick_format in formats_to_try:
        try:
            logger.info( f"Attempting to parse with format={newick_format}" )
            tree = Tree( str( newick_file_path ), format=newick_format )
            
            # Count nodes and leaves
            leaf_count = len( tree )
            node_count = len( list( tree.traverse() ) )
            
            logger.info( f"Tree loaded successfully with format={newick_format}: {leaf_count} leaves, {node_count} total nodes" )
            return tree
            
        except Exception as error:
            logger.warning( f"Format {newick_format} failed: {error}" )
            continue
    
    # If all formats fail, try reading and cleaning the file
    logger.info( "Standard formats failed. Attempting to clean IQ-TREE support values..." )
    try:
        with open( newick_file_path, 'r' ) as input_file:
            newick_string = input_file.read().strip()
        
        # Replace IQ-TREE dual support format (e.g., "100/95" or "68.2/67") with single value
        # Keep only the first value (SH-aLRT support)
        import re
        cleaned_newick = re.sub( r'(\d+\.?\d*)/\d+\.?\d*:', r'\1:', newick_string )
        
        logger.info( "Attempting to parse cleaned tree string" )
        tree = Tree( cleaned_newick, format=0 )
        
        # Count nodes and leaves
        leaf_count = len( tree )
        node_count = len( list( tree.traverse() ) )
        
        logger.info( f"Tree loaded successfully after cleaning: {leaf_count} leaves, {node_count} total nodes" )
        return tree
        
    except Exception as error:
        error_message = f"Failed to parse Newick file after all attempts: {error}"
        logger.error( error_message )
        raise ValueError( error_message )


def configure_tree_style( config: VisualizationConfig ) -> TreeStyle:
    """
    Configure the visual style for tree rendering.
    
    Args:
        config: VisualizationConfig object with user settings
    
    Returns:
        TreeStyle object with configured settings
    """
    tree_style = TreeStyle()
    
    # Hide default leaf names and branch lengths (we'll add custom styled ones)
    tree_style.show_leaf_name = False
    tree_style.show_branch_length = False
    
    # Don't show default branch support (we'll add custom colored ones)
    tree_style.show_branch_support = False
    
    # Layout mode: rectangular
    tree_style.mode = "r"  # rectangular layout
    
    # Scale the tree appropriately
    tree_style.scale = 120  # pixels per branch length unit
    
    # Branch style
    tree_style.branch_vertical_margin = 10  # vertical space between branches
    
    # Only show scale bar if branch lengths are being displayed
    tree_style.show_scale = config.show_branch_lengths
    
    # Set font sizes for various text elements
    tree_style.branch_vertical_margin = 10
    
    # Note: Leaf names and branch lengths need to be styled in configure_node_styles()
    # by adding custom TextFace objects to each node
    
    # Force drawing of nodes (important for custom node styles to show!)
    tree_style.draw_guiding_lines = False
    tree_style.complete_branch_lines_when_necessary = True
    
    return tree_style


def get_bootstrap_color( bootstrap_value: float, threshold: float, config: VisualizationConfig ) -> str:
    """
    Determine color for bootstrap value based on threshold.
    
    Args:
        bootstrap_value: Bootstrap support value
        threshold: Threshold for coloring
        config: VisualizationConfig with color definitions
        
    Returns:
        Color code as hex string
    """
    if bootstrap_value < threshold:
        return config.color_below_threshold  # Red
    else:
        return config.color_above_threshold  # Blueberry blue


def add_bootstrap_face( node, bootstrap_value: float, threshold: float, config: VisualizationConfig ):
    """
    Add a colored text face showing bootstrap value to a node.
    
    Args:
        node: ETE3 node object
        bootstrap_value: Bootstrap support value
        threshold: Threshold for coloring
        config: VisualizationConfig object
    """
    # Determine color
    color = get_bootstrap_color( bootstrap_value, threshold, config )
    
    # Format the bootstrap value
    if bootstrap_value >= 1.0:
        # If bootstrap is already 0-100 scale
        bootstrap_text = f"{bootstrap_value:.1f}"
    else:
        # If bootstrap is 0-1 scale, convert to percentage
        bootstrap_text = f"{bootstrap_value * 100:.1f}"
    
    # Create text face with OCR-friendly padding
    text_face = TextFace( bootstrap_text, fsize=config.font_size_small, fgcolor=color, bold=True )
    text_face.margin_left = config.text_padding
    text_face.margin_right = config.text_padding
    text_face.margin_top = config.text_padding
    text_face.margin_bottom = config.text_padding
    
    # Add face to node (position 1 = above branch)
    node.add_face( text_face, column=0, position="branch-top" )


def configure_node_styles( tree: Tree, config: VisualizationConfig, logger: logging.Logger, is_iqtree: bool = False ) -> None:
    """
    Configure visual styles for nodes in the tree.
    
    Args:
        tree: ETE3 Tree object
        config: VisualizationConfig object with user settings
        logger: Logger instance for status messages
        is_iqtree: Boolean indicating if this is an IQ-TREE file (has dual support values)
    """
    logger.info( "Configuring node styles" )
    
    bootstrap_count = 0
    ufboot_count = 0
    
    # First pass: assign clade IDs to all nodes (leaves first, then internal nodes, top to bottom)
    if config.show_node_identifiers:
        clade_id_counter = 0
        
        # Collect all leaves (tips/species) - these come first
        leaves = []
        for node in tree.traverse():
            if node.is_leaf():
                leaves.append( node )
        
        # Assign clade IDs to leaves (top to bottom in tree visualization)
        for leaf in leaves:
            leaf.add_features( clade_id=clade_id_counter )
            clade_id_counter += 1
        
        # Collect all internal nodes (ancestral clades)
        internal_nodes = []
        for node in tree.traverse():
            if not node.is_leaf():
                internal_nodes.append( node )
        
        # Assign clade IDs to internal nodes
        for internal_node in internal_nodes:
            internal_node.add_features( clade_id=clade_id_counter )
            clade_id_counter += 1
        
        # Calculate number of digits needed for formatting (CNNN with leading zeros)
        total_nodes = clade_id_counter
        num_digits = len( str( total_nodes - 1 ) )  # -1 because we start from 0
        
        logger.info( f"Assigned {total_nodes} clade IDs (C000-C{total_nodes-1:0{num_digits}d}) to all nodes" )
        logger.info( f"  Leaves/species: C000-C{len(leaves)-1:0{num_digits}d}" )
        logger.info( f"  Internal/ancestral clades: C{len(leaves):0{num_digits}d}-C{total_nodes-1:0{num_digits}d}" )
        
        # Store formatting info in config for use in display
        config.clade_id_digits = num_digits
    
    for node in tree.traverse():
        node_style = NodeStyle()
        
        # Apply branch line width
        node_style.hz_line_width = config.branch_line_width
        node_style.vt_line_width = config.branch_line_width
        
        if node.is_leaf():
            # Leaf node style (tips/species) - solid, no border
            node_style["size"] = config.node_symbol_size  # 10 pixels
            node_style["shape"] = "circle"  # flat circle (not sphere - no gradient!)
            node_style["fgcolor"] = "#000000"  # black symbol color
            
            # Add custom leaf name with font size control and margin
            leaf_name_face = TextFace( node.name, fsize=config.font_size_leaf_names, fgcolor="black", bold=False )
            leaf_name_face.margin_left = config.leaf_name_margin  # Add spacing
            node.add_face( leaf_name_face, column=0, position="branch-right" )
            
            # Note: Clade identifiers are NOT shown for leaf nodes (only internal nodes)
        
        else:
            # Internal node style (ancestral clades) - solid, no border
            node_style["size"] = config.node_symbol_size  # 10 pixels
            node_style["shape"] = "square"  # square for ancestral nodes
            node_style["fgcolor"] = "#000000"  # black symbol color
            
            # Show clade identifier for internal nodes if requested
            if config.show_node_identifiers and hasattr( node, 'clade_id' ):
                num_digits = config.clade_id_digits
                clade_id_text = f"C{node.clade_id:0{num_digits}d}"
                clade_id_face = TextFace( clade_id_text, fsize=config.font_size_small, fgcolor=config.color_clade_id, bold=False )
                # Add OCR-friendly padding on all sides
                clade_id_face.margin_left = config.text_padding
                clade_id_face.margin_right = config.text_padding
                clade_id_face.margin_top = config.text_padding
                clade_id_face.margin_bottom = config.text_padding
                # Position on branch-right side to avoid conflict with support values
                node.add_face( clade_id_face, column=1, position="branch-right" )
            
            # Handle IQ-TREE dual support values (SH-aLRT and UFBoot)
            if is_iqtree:
                # Check for parsed IQ-TREE dual support values
                if hasattr( node, 'sh_alrt_support' ) and hasattr( node, 'ufboot_support' ):
                    sh_alrt_value = node.sh_alrt_support
                    ufboot_value = node.ufboot_support
                    
                    # Normalize to 0-1 scale if needed
                    if sh_alrt_value > 1.0:
                        sh_alrt_value = sh_alrt_value / 100.0
                    if ufboot_value > 1.0:
                        ufboot_value = ufboot_value / 100.0
                    
                    # Show SH-aLRT (bootstrap) if requested
                    if config.show_bootstraps and config.color_bootstraps:
                        # Determine color based on bootstrap threshold
                        sh_color = get_bootstrap_color( sh_alrt_value, config.bootstrap_threshold, config )
                        sh_text = f"{sh_alrt_value * 100:.1f}"
                        sh_face = TextFace( sh_text, fsize=config.font_size_small, fgcolor=sh_color, bold=True )
                        # Add OCR-friendly padding on all sides
                        sh_face.margin_left = config.text_padding
                        sh_face.margin_right = config.text_padding
                        sh_face.margin_top = config.text_padding
                        sh_face.margin_bottom = config.text_padding
                        node.add_face( sh_face, column=0, position="branch-top" )
                        bootstrap_count += 1
                    
                    # Show UFBoot if requested
                    if config.show_ultrafast_bootstraps and config.color_bootstraps:
                        # Determine color based on ultrafast threshold
                        uf_color = get_bootstrap_color( ufboot_value, config.ultrafast_threshold, config )
                        uf_text = f"{ufboot_value * 100:.1f}"
                        uf_face = TextFace( uf_text, fsize=config.font_size_small, fgcolor=uf_color, bold=True )
                        # Add OCR-friendly padding on all sides
                        uf_face.margin_left = config.text_padding
                        uf_face.margin_right = config.text_padding
                        uf_face.margin_top = config.text_padding
                        uf_face.margin_bottom = config.text_padding
                        node.add_face( uf_face, column=0, position="branch-bottom" )
                        ufboot_count += 1
            
            # Handle FastTree single bootstrap values
            else:
                if config.show_bootstraps and hasattr( node, 'support' ) and node.support is not None:
                    try:
                        bootstrap_value = float( node.support )
                        
                        # Normalize bootstrap to 0-1 scale if needed
                        if bootstrap_value > 1.0:
                            bootstrap_value = bootstrap_value / 100.0
                        
                        if config.color_bootstraps:
                            add_bootstrap_face( node, bootstrap_value, config.bootstrap_threshold, config )
                            bootstrap_count += 1
                        
                    except ( ValueError, TypeError ):
                        logger.warning( f"Could not parse support value: {node.support}" )
        
        # Add branch length display if requested (for all nodes except root)
        if config.show_branch_lengths and hasattr( node, 'dist' ) and node.dist is not None and node.dist > 0:
            branch_length_text = f"{node.dist:.4f}"
            branch_length_face = TextFace( branch_length_text, fsize=config.font_size_small, fgcolor=config.color_branch_length, bold=False )
            # Add OCR-friendly padding on all sides
            branch_length_face.margin_left = config.text_padding
            branch_length_face.margin_right = config.text_padding
            branch_length_face.margin_top = config.text_padding
            branch_length_face.margin_bottom = config.text_padding
            # Position branch length on the branch itself
            node.add_face( branch_length_face, column=0, position="branch-bottom" )
        
        node.set_style( node_style )
    
    if bootstrap_count > 0:
        logger.info( f"Added {bootstrap_count} colored bootstrap values to tree" )
    if ufboot_count > 0:
        logger.info( f"Added {ufboot_count} colored ultrafast bootstrap values to tree" )


def render_tree_to_files( 
    tree: Tree, 
    output_prefix: Path, 
    tree_style: TreeStyle,
    logger: logging.Logger 
) -> Tuple[Path, Path]:
    """
    Render tree to SVG and PDF files.
    
    Args:
        tree: ETE3 Tree object to render
        output_prefix: Path prefix for output files (without extension)
        tree_style: TreeStyle object with rendering configuration
        logger: Logger instance for status messages
        
    Returns:
        Tuple of (svg_path, pdf_path)
    """
    output_svg_path = output_prefix.with_suffix( '.svg' )
    output_pdf_path = output_prefix.with_suffix( '.pdf' )
    
    logger.info( f"Rendering tree to SVG: {output_svg_path}" )
    tree.render( str( output_svg_path ), tree_style=tree_style )
    
    logger.info( f"Rendering tree to PDF: {output_pdf_path}" )
    tree.render( str( output_pdf_path ), tree_style=tree_style )
    
    # Verify output files were created
    if output_svg_path.exists():
        svg_size = output_svg_path.stat().st_size
        logger.info( f"SVG created successfully: {svg_size:,} bytes" )
    else:
        logger.warning( f"SVG file not found after rendering: {output_svg_path}" )
    
    if output_pdf_path.exists():
        pdf_size = output_pdf_path.stat().st_size
        logger.info( f"PDF created successfully: {pdf_size:,} bytes" )
    else:
        logger.warning( f"PDF file not found after rendering: {output_pdf_path}" )
    
    return output_svg_path, output_pdf_path


def visualize_tree_file(
    input_newick_path: Path,
    output_prefix: Path,
    tree_type: str,
    config: VisualizationConfig,
    logger: logging.Logger
) -> Tuple[Path, Path]:
    """
    Complete workflow to visualize a single tree file.
    
    Args:
        input_newick_path: Path to input Newick file
        output_prefix: Path prefix for output files
        tree_type: Description of tree type (e.g., "FastTree", "IQ-TREE")
        config: VisualizationConfig object
        logger: Logger instance
        
    Returns:
        Tuple of (svg_path, pdf_path)
    """
    logger.info( f"\n{'='*80}" )
    logger.info( f"Processing {tree_type} tree" )
    logger.info( f"{'='*80}" )
    
    # Determine if this is an IQ-TREE file
    is_iqtree = ( tree_type.upper() == "IQ-TREE" )
    
    # Load tree
    tree = load_tree_from_newick( input_newick_path, logger )
    
    # Parse IQ-TREE dual support values if applicable
    if is_iqtree:
        parse_iqtree_support_values( tree, logger )
    
    # Configure styles
    tree_style = configure_tree_style( config )
    configure_node_styles( tree, config, logger, is_iqtree=is_iqtree )
    
    # Render to files
    svg_path, pdf_path = render_tree_to_files( tree, output_prefix, tree_style, logger )
    
    logger.info( f"{tree_type} visualization complete" )
    
    return svg_path, pdf_path


def find_most_recent_file( directory: Path, extension: str ) -> Optional[Path]:
    """
    Find the most recently modified file with the given extension.
    
    Args:
        directory: Directory to search in
        extension: File extension to search for (e.g., '.fasttree', '.treefile')
    
    Returns:
        Path to the most recent file, or None if no files found
    """
    matching_files = list( directory.glob( f"*{extension}" ) )
    
    if not matching_files:
        return None
    
    # Sort by modification time, most recent first
    matching_files.sort( key=lambda p: p.stat().st_mtime, reverse=True )
    
    return matching_files[ 0 ]


def main():
    """
    Main execution function.
    """
    # Parse command-line arguments
    config = parse_arguments()
    
    # Start time
    start_time = datetime.now()
    
    # Define paths
    # Use current working directory (where NextFlow runs the script)
    script_directory = Path.cwd()
    output_directory = script_directory / "output"
    
    # Log file
    log_file_path = Path( "7_ai-log-visualize_trees-human_friendly.log" )
    
    # Setup logging
    logger = setup_logging( log_file_path )
    
    # Auto-discover input files by extension (most recent if multiple exist)
    logger.info( "Searching for input tree files..." )
    input_fasttree_path = find_most_recent_file( output_directory, ".fasttree" )
    input_iqtree_path = find_most_recent_file( output_directory, ".treefile" )
    
    if not input_fasttree_path:
        logger.warning( f"No FastTree file (*.fasttree) found in {output_directory}" )
    else:
        logger.info( f"Found FastTree file: {input_fasttree_path.name}" )
    
    if not input_iqtree_path:
        logger.warning( f"No IQ-TREE file (*.treefile) found in {output_directory}" )
    else:
        logger.info( f"Found IQ-TREE file: {input_iqtree_path.name}" )
    
    if not input_fasttree_path and not input_iqtree_path:
        logger.error( "No tree files found! Expected *.fasttree or *.treefile in output directory." )
        sys.exit( 1 )
    
    # Generate output filenames dynamically based on input file basenames
    if input_fasttree_path:
        # Extract base name without extension (e.g., "5-AGS-species67_T1-species37-innexin_pannexin")
        fasttree_base = input_fasttree_path.stem
        # Create output prefix by replacing the leading number with "7"
        fasttree_parts = fasttree_base.split( '-', 1 )
        if len( fasttree_parts ) == 2:
            output_fasttree_prefix = output_directory / f"7-{fasttree_parts[ 1 ]}-fasttree-human_friendly"
        else:
            output_fasttree_prefix = output_directory / f"7-{fasttree_base}-fasttree-human_friendly"
    else:
        output_fasttree_prefix = None
    
    if input_iqtree_path:
        # Extract base name without extension
        iqtree_base = input_iqtree_path.stem
        # Create output prefix by replacing the leading number with "7"
        iqtree_parts = iqtree_base.split( '-', 1 )
        if len( iqtree_parts ) == 2:
            output_iqtree_prefix = output_directory / f"7-{iqtree_parts[ 1 ]}-iqtree-human_friendly"
        else:
            output_iqtree_prefix = output_directory / f"7-{iqtree_base}-iqtree-human_friendly"
    else:
        output_iqtree_prefix = None
    
    logger.info( "="*80 )
    logger.info( "Phylogenetic Tree Visualization Script" )
    logger.info( "="*80 )
    logger.info( f"Script started at: {start_time.strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Working directory: {script_directory}" )
    
    # Log configuration
    logger.info( "\nVisualization Settings:" )
    logger.info( f"  Show bootstraps: {config.show_bootstraps}" )
    logger.info( f"  Show ultrafast bootstraps: {config.show_ultrafast_bootstraps}" )
    logger.info( f"  Show branch lengths: {config.show_branch_lengths}" )
    logger.info( f"  Show node identifiers: {config.show_node_identifiers}" )
    logger.info( f"  Bootstrap threshold: {config.bootstrap_threshold}" )
    logger.info( f"  Ultrafast threshold: {config.ultrafast_threshold}" )
    logger.info( f"  Color bootstraps: {config.color_bootstraps}" )
    if config.color_bootstraps:
        logger.info( f"  Color below threshold: {config.color_below_threshold} (red)" )
        logger.info( f"  Color above threshold: {config.color_above_threshold} (blueberry blue)" )
    if config.show_node_identifiers:
        logger.info( f"  Clade ID color: {config.color_clade_id} (medium-light grey)" )
        logger.info( f"  Leaf clade IDs: shown as grey labels (right side)" )
        logger.info( f"  Internal clade IDs: shown as grey labels (right side)" )
        logger.info( f"  Leaf symbol: {config.leaf_symbol} (size: {config.node_symbol_size})" )
        logger.info( f"  Internal symbol: {config.internal_symbol} (size: {config.node_symbol_size})" )
    
    # Verify output directory exists
    if not output_directory.exists():
        error_message = f"Output directory not found: {output_directory}"
        logger.error( error_message )
        raise FileNotFoundError( error_message )
    
    try:
        # Process FastTree (if file found)
        fasttree_svg, fasttree_pdf = None, None
        if input_fasttree_path:
            logger.info( "\nProcessing FastTree visualization..." )
            fasttree_svg, fasttree_pdf = visualize_tree_file(
                input_fasttree_path,
                output_fasttree_prefix,
                "FastTree",
                config,
                logger
            )
        
        # Process IQ-TREE (if file found)
        iqtree_svg, iqtree_pdf = None, None
        if input_iqtree_path:
            logger.info( "\nProcessing IQ-TREE visualization..." )
            iqtree_svg, iqtree_pdf = visualize_tree_file(
                input_iqtree_path,
                output_iqtree_prefix,
                "IQ-TREE",
                config,
                logger
            )
        
        # Summary
        logger.info( "\n" + "="*80 )
        logger.info( "VISUALIZATION COMPLETE" )
        logger.info( "="*80 )
        logger.info( "\nOutput files created:" )
        if fasttree_svg:
            logger.info( f"  FastTree SVG: {fasttree_svg}" )
            logger.info( f"  FastTree PDF: {fasttree_pdf}" )
        if iqtree_svg:
            logger.info( f"  IQ-TREE SVG:  {iqtree_svg}" )
            logger.info( f"  IQ-TREE PDF:  {iqtree_pdf}" )
        
        # End time
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info( f"\nScript completed at: {end_time.strftime( '%Y-%m-%d %H:%M:%S' )}" )
        logger.info( f"Total duration: {duration}" )
        logger.info( f"Log file: {log_file_path}" )
        
    except Exception as error:
        logger.error( f"\nScript failed with error: {error}" )
        raise


if __name__ == "__main__":
    main()
