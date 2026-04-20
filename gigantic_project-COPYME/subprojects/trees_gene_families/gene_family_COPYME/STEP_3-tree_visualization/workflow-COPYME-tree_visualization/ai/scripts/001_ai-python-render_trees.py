# AI: Claude Code | Opus 4.7 | 2026 April 19 | Purpose: Render gene family phylogenetic trees as PDF + SVG using toytree
# Human: Eric Edsinger

"""
STEP_3 tree_visualization Script 001: Render Gene Family Trees

Reads tree newick files produced by STEP_2 for one gene family and renders
each to PDF + SVG using `toytree` (pure Python, no Qt dependency).

This is decoupled from STEP_2 deliberately: the scientific artifact is the
newick file; the PDF/SVG is presentation. A render failure never invalidates
the science.

INPUTS (auto-discovered from output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/):
  - *.fasttree       (FastTree ML)
  - *.treefile       (IQ-TREE ML with bootstrap/aLRT)
  - *.veryfasttree   (VeryFastTree)
  - *.phylobayes.nwk (PhyloBayes consensus)

OUTPUTS (to 1-output/):
  - 1_ai-visualization-<gene_family>-<method>.pdf    (primary, for sharing)
  - 1_ai-visualization-<gene_family>-<method>.svg    (secondary, for editing)
  - 1_ai-visualization_summary.md                    (human-readable report)
  - 1_ai-visualization-placeholder.txt               (soft-fail only)

SOFT-FAIL BEHAVIOR:
  If toytree/toyplot are unavailable or any render fails, the script writes
  a placeholder and exits 0. STEP_2 outputs (newicks) remain the scientific
  artifact and are unaffected.

USAGE:
    python 001_ai-python-render_trees.py --config ../../START_HERE-user_config.yaml
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser( description = 'Render gene family trees as PDF + SVG' )
    parser.add_argument( '--config', type = str, required = True, help = 'Path to START_HERE-user_config.yaml' )
    parser.add_argument( '--output_dir', type = str, default = None, help = 'Base output directory' )
    return parser.parse_args()


args = parse_arguments()

config_path = Path( args.config )
if not config_path.exists():
    print( f"CRITICAL ERROR: Configuration file not found: {config_path}" )
    sys.exit( 1 )

with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

config_directory = config_path.parent

# Required config
gene_family = config[ 'gene_family' ][ 'name' ]
output_to_input_directory = ( config_directory / config[ 'input' ][ 'output_to_input_dir' ] ).resolve()

# Visualization config with defaults
visualization_config = config.get( 'visualization', {} )
show_tip_labels_max_tips = visualization_config.get( 'show_tip_labels_max_tips', 500 )
color_tips_by_species = visualization_config.get( 'color_tips_by_species', True )
tip_label_font_size_px = visualization_config.get( 'tip_label_font_size_px', 11 )
show_branch_support = visualization_config.get( 'show_branch_support', True )
branch_support_font_size_px = visualization_config.get( 'branch_support_font_size_px', 7 )
canvas_width_px = visualization_config.get( 'canvas_width_px', 1000 )
canvas_height_per_tip_px = visualization_config.get( 'canvas_height_per_tip_px', 20 )
canvas_height_min_px = visualization_config.get( 'canvas_height_min_px', 900 )

# Output directory
if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config.get( 'output', {} ).get( 'base_dir', 'OUTPUT_pipeline' )

output_directory = output_base_directory / '1-output'
output_directory.mkdir( parents = True, exist_ok = True )

output_summary_file = output_directory / '1_ai-visualization_summary.md'
output_placeholder_file = output_directory / '1_ai-visualization-placeholder.txt'

# Log directory
log_directory = output_base_directory / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / '1_ai-log-render_trees.log'


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s',
    handlers = [
        logging.FileHandler( log_file ),
        logging.StreamHandler( sys.stdout )
    ]
)
logger = logging.getLogger( __name__ )


# ============================================================================
# SOFT-FAIL HELPER
# ============================================================================

def write_placeholder( reason ):
    placeholder_text = (
        f"GIGANTIC STEP_3 tree_visualization -- placeholder\n"
        f"\n"
        f"Tree rendering failed (soft-fail). STEP_2 tree newick files are still valid.\n"
        f"\n"
        f"Reason: {reason}\n"
        f"\n"
        f"Diagnosis:\n"
        f"  See 1_ai-log-render_trees.log for details.\n"
        f"\n"
        f"Manual rendering (if env is broken):\n"
        f"  conda activate aiG-trees_gene_families-visualization   # or equivalent\n"
        f"  pip install toytree toyplot reportlab\n"
        f"\n"
        f"  python -c \"import toytree, toyplot.pdf; \"\n"
        f"            \"t = toytree.tree('path/to/tree.newick'); \"\n"
        f"            \"canvas, _, _ = t.draw(width=1000, height=1400); \"\n"
        f"            \"toyplot.pdf.render(canvas, 'out.pdf')\"\n"
        f"\n"
        f"Alternative: use FigTree or iTOL on the newick files in\n"
        f"output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/ directly.\n"
    )
    output_placeholder_file.write_text( placeholder_text )
    logger.warning( f"Wrote placeholder: {output_placeholder_file.name}" )


# ============================================================================
# SECTION 1: DISCOVER TREE FILES
# ============================================================================

# Mapping: file suffix -> method name shown in output filenames + titles
method_suffixes = [
    ( '.fasttree',      'fasttree' ),
    ( '.treefile',      'iqtree' ),       # IQ-TREE ML tree with UFBoot/aLRT support
    ( '.veryfasttree',  'veryfasttree' ),
    ( '.phylobayes.nwk', 'phylobayes' ),
]


def discover_trees( gene_family_step2_directory ):
    """
    Discover tree newick files in the given STEP_2 directory.

    Returns:
        list of (method_name, tree_path) tuples
    """
    trees = []
    if not gene_family_step2_directory.exists():
        logger.error( f"STEP_2 directory not found: {gene_family_step2_directory}" )
        return trees

    for suffix, method_name in method_suffixes:
        matches = sorted( gene_family_step2_directory.glob( f'*{suffix}' ) )
        # .nwk needs special handling because phylobayes produces ".phylobayes.nwk"
        # and other methods may produce .nwk too, so filter to only phylobayes-containing
        if suffix == '.phylobayes.nwk':
            matches = [ m for m in matches if 'phylobayes' in m.name ]

        for tree_path in matches:
            trees.append( ( method_name, tree_path ) )

    return trees


# ============================================================================
# SECTION 2: SPECIES COLOR-CODING
# ============================================================================

# Regex patterns to extract species from tip identifiers
# Pattern 1 (RGS sequences in AGS): rgs_FAMILY-SPECIES-GENE-SOURCE-ID
# Pattern 2 (genome proteins): g_GENE-t_TRANSCRIPT-p_PROTEIN-n_Kingdom_Phylum_..._Genus_species

rgs_header_pattern = re.compile( r'^rgs_[^-]+-([^-]+)-' )
genome_taxonomy_pattern = re.compile( r'-n_([A-Z][A-Za-z_]+)$' )


def extract_species_from_label( tip_label ):
    """
    Extract a species identifier from a GIGANTIC tip label.

    Returns:
        str species identifier, or 'unknown' if no pattern matches
    """
    # RGS case: second dash-separated field is species short name
    rgs_match = rgs_header_pattern.match( tip_label )
    if rgs_match:
        return rgs_match.group( 1 )

    # Genome protein case: taxonomy at end, last two underscore fields = Genus_species
    taxonomy_match = genome_taxonomy_pattern.search( tip_label )
    if taxonomy_match:
        taxonomy_parts = taxonomy_match.group( 1 ).split( '_' )
        if len( taxonomy_parts ) >= 2:
            # Last two fields are Genus_species
            return f"{taxonomy_parts[ -2 ]}_{taxonomy_parts[ -1 ]}"

    return 'unknown'


# colorBlindness-friendly palette (LightBlue2DarkBlue cycled through distinct hues)
# Enough distinct colors for ~20 species; tips beyond cycle repeat.
species_palette = [
    '#003FFF', '#FF7F00', '#00AA00', '#FF1493', '#7FD4FF',
    '#FFD700', '#9370DB', '#DC143C', '#20B2AA', '#FF4500',
    '#4682B4', '#228B22', '#FF69B4', '#CD853F', '#1E90FF',
    '#DAA520', '#32CD32', '#BA55D3', '#FF6347', '#5F9EA0',
]


def build_tip_colors( tip_labels ):
    """
    Build a list of colors (same length as tip_labels) based on species.

    Returns:
        ( list of colors, dict of species -> color )
    """
    species_to_color = {}
    colors = []
    for label in tip_labels:
        species = extract_species_from_label( label )
        if species not in species_to_color:
            species_to_color[ species ] = species_palette[ len( species_to_color ) % len( species_palette ) ]
        colors.append( species_to_color[ species ] )
    return colors, species_to_color


# ============================================================================
# SECTION 3: RENDER A SINGLE TREE
# ============================================================================

def render_tree_to_pdf_and_svg( newick_path, method_name, pdf_output_path, svg_output_path ):
    """
    Render a newick file to PDF + SVG using toytree.

    Returns:
        tuple: ( success: bool, ntips: int, error_message: str or None )
    """
    import toytree
    import toyplot
    import toyplot.pdf
    import toyplot.svg

    try:
        tree = toytree.tree( str( newick_path ) )
    except Exception as parse_error:
        return ( False, 0, f"Failed to parse newick: {parse_error}" )

    tip_count = tree.ntips

    # Canvas sizing
    canvas_height = max( canvas_height_min_px, canvas_height_per_tip_px * tip_count + 200 )

    # Tip label visibility: hide labels for very large trees to keep figure legible
    show_tip_labels = tip_count <= show_tip_labels_max_tips

    # Tip label colors by species
    tip_colors = None
    species_legend = {}
    if show_tip_labels and color_tips_by_species:
        tip_labels = list( tree.get_tip_labels() )
        tip_colors, species_legend = build_tip_colors( tip_labels )

    # Detect whether newick contains branch support values (numeric node labels)
    has_node_support = False
    if show_branch_support:
        try:
            for node in tree.treenode.traverse():
                name = getattr( node, 'name', '' ) or ''
                if name and not node.is_leaf():
                    try:
                        float( name )
                        has_node_support = True
                        break
                    except ( TypeError, ValueError ):
                        continue
        except Exception:
            has_node_support = False

    # Build draw kwargs
    draw_kwargs = {
        'width': canvas_width_px,
        'height': canvas_height,
        'tip_labels_align': True,
    }

    if show_tip_labels:
        draw_kwargs[ 'tip_labels_style' ] = { 'font-size': f'{tip_label_font_size_px}px' }
        if tip_colors:
            draw_kwargs[ 'tip_labels_colors' ] = tip_colors
    else:
        draw_kwargs[ 'tip_labels' ] = False

    if has_node_support:
        draw_kwargs[ 'node_labels' ] = 'name'
        draw_kwargs[ 'node_labels_style' ] = { 'font-size': f'{branch_support_font_size_px}px', 'fill': '#666666' }
        draw_kwargs[ 'node_sizes' ] = 4
        draw_kwargs[ 'node_colors' ] = '#888888'

    draw_kwargs[ 'edge_style' ] = { 'stroke': '#333333', 'stroke-width': 1 }

    try:
        canvas, axes, marks = tree.draw( **draw_kwargs )

        title_text = f"{gene_family}  |  {method_name}  |  {tip_count} tips"
        if not show_tip_labels:
            title_text += "  (tip labels hidden for readability)"
        canvas.text(
            canvas_width_px / 2, 20, title_text,
            style = { 'font-size': '14px', 'text-anchor': 'middle', 'fill': '#222222', 'font-weight': 'bold' }
        )
    except Exception as draw_error:
        return ( False, tip_count, f"Failed to draw tree: {draw_error}" )

    try:
        toyplot.pdf.render( canvas, str( pdf_output_path ) )
        toyplot.svg.render( canvas, str( svg_output_path ) )
    except Exception as render_error:
        return ( False, tip_count, f"Failed to render PDF/SVG: {render_error}" )

    return ( True, tip_count, None )


# ============================================================================
# SECTION 4: RENDER BATCH
# ============================================================================

def render_all_trees( trees ):
    """
    Render every discovered tree to PDF + SVG.

    Returns:
        list of dicts describing each render attempt
    """
    results = []

    for method_name, tree_path in trees:
        pdf_path = output_directory / f'1_ai-visualization-{gene_family}-{method_name}.pdf'
        svg_path = output_directory / f'1_ai-visualization-{gene_family}-{method_name}.svg'

        logger.info( f"Rendering {method_name}: {tree_path.name}" )
        success, tip_count, error = render_tree_to_pdf_and_svg( tree_path, method_name, pdf_path, svg_path )

        if success:
            logger.info( f"  -> {pdf_path.name} ({tip_count} tips)" )
        else:
            logger.error( f"  FAILED: {error}" )

        results.append( {
            'method': method_name,
            'tree_path': tree_path,
            'pdf_path': pdf_path if success else None,
            'svg_path': svg_path if success else None,
            'tip_count': tip_count,
            'success': success,
            'error': error,
        } )

    return results


# ============================================================================
# SECTION 5: SUMMARY REPORT
# ============================================================================

def write_summary_report( trees, results ):
    logger.info( f"Writing visualization summary to: {output_summary_file}" )

    succeeded = sum( 1 for r in results if r[ 'success' ] )
    failed = sum( 1 for r in results if not r[ 'success' ] )

    lines = []
    lines.append( f"# Tree Visualization Summary" )
    lines.append( "" )
    lines.append( f"**Gene family**: {gene_family}" )
    lines.append( f"**Generated**: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    lines.append( "" )
    lines.append( f"**Results**: {succeeded} rendered, {failed} failed" )
    lines.append( "" )
    lines.append( "## Rendered Trees" )
    lines.append( "" )

    if not results:
        lines.append( "_No tree files found in STEP_2 output._" )
        lines.append( "" )
    else:
        for r in results:
            status = "✓" if r[ 'success' ] else "✗ FAILED"
            lines.append( f"- **{r[ 'method' ]}** ({r[ 'tip_count' ]} tips) — {status}" )
            if r[ 'success' ]:
                lines.append( f"  - PDF: `1-output/{r[ 'pdf_path' ].name}`" )
                lines.append( f"  - SVG: `1-output/{r[ 'svg_path' ].name}`" )
            else:
                lines.append( f"  - Source: `{r[ 'tree_path' ]}`" )
                lines.append( f"  - Error: `{r[ 'error' ]}`" )
            lines.append( "" )

    lines.append( "## Output Formats" )
    lines.append( "" )
    lines.append( "Each rendered tree is available as:" )
    lines.append( "- **PDF** — primary format for sharing, opens in any PDF reader" )
    lines.append( "- **SVG** — editable in Inkscape/Illustrator for figure preparation" )
    lines.append( "" )

    with open( output_summary_file, 'w' ) as output_file:
        output_file.write( '\n'.join( lines ) + '\n' )

    logger.info( "Wrote summary report" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info( "=" * 80 )
    logger.info( "STEP_3 tree_visualization -- Script 001: Render Trees" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Config: {config_path}" )
    logger.info( f"Gene family: {gene_family}" )
    logger.info( "" )

    # Try importing toytree (soft-fail pattern)
    try:
        import toytree
        import toyplot
        import toyplot.pdf
        import toyplot.svg
        logger.info( f"toytree version: {toytree.__version__}" )
        logger.info( f"toyplot version: {toyplot.__version__}" )
    except ImportError as import_error:
        logger.warning( f"toytree/toyplot import failed: {import_error}" )
        logger.warning( "Rendering skipped (soft-fail). STEP_2 tree newicks remain the valid scientific artifact." )
        write_placeholder( f"toytree/toyplot not available: {import_error}" )
        logger.info( "STEP_3 COMPLETED WITH SOFT-FAIL" )
        return 0

    # Discover trees
    gene_family_step2_directory = output_to_input_directory / gene_family / 'STEP_2-phylogenetic_analysis'
    logger.info( f"Looking for trees in: {gene_family_step2_directory}" )
    trees = discover_trees( gene_family_step2_directory )

    if not trees:
        logger.warning( f"No tree files found for gene family '{gene_family}' in {gene_family_step2_directory}" )
        write_placeholder( f"No tree files found in {gene_family_step2_directory}" )
        return 0

    logger.info( f"Discovered {len( trees )} tree file(s) to render:" )
    for method_name, tree_path in trees:
        logger.info( f"  - {method_name}: {tree_path.name}" )
    logger.info( "" )

    # Render
    results = render_all_trees( trees )

    # Summary
    write_summary_report( trees, results )

    succeeded = sum( 1 for r in results if r[ 'success' ] )
    failed = sum( 1 for r in results if not r[ 'success' ] )
    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( f"STEP_3 COMPLETED — {succeeded} rendered, {failed} failed" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
