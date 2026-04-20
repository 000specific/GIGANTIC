# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Render selected species tree structures as PDF using toytree
# Human: Eric Edsinger

"""
User Request Pipeline Script 002: Visualize Selected Structures

Renders the species tree structures produced by Script 001 (select_structures)
as PDF visualizations so users can visually assess the topologies. Uses
`toytree` (pure Python, no Qt dependency) as the rendering engine.

Produces:
  - PDF (primary -- most familiar format for outside collaborators)
  - SVG (secondary -- for those who want to edit the figure)

Two sets of renders:
  1. Canonical structures only (one PDF per query) -- primary deliverable
  2. All matching structures (one PDF per matched structure) -- for equivalence
     class inspection

Each PDF is titled with the query name and description, plus the structure_id.

SOFT-FAIL BEHAVIOR:
  If toytree or toyplot are unavailable, the script logs a warning, writes a
  placeholder text file, and exits 0. Script 001's selection outputs remain
  intact regardless -- visualization is a "nice-to-have" layer.

Inputs (from Script 001 outputs):
  - 1-output/1_ai-matching_structures.tsv
  - 1-output/1_ai-canonical_structures.tsv
  - 1-output/1_ai-selected_structures/*.newick
  - 1-output/1_ai-canonical_structures/*.newick

Outputs (to 2-output/):
  - 2_ai-canonical_visualizations/    (one PDF per query, with query context in title)
  - 2_ai-all_matched_visualizations/  (one PDF per matched structure)
  - 2_ai-visualization_summary.md     (human-readable report)
  - 2_ai-visualization-placeholder.txt (soft-fail only, if rendering broke)

Usage:
    python 002_ai-python-visualize_structures.py --config ../../START_HERE-user_config.yaml
"""

import os
import sys
import yaml
import logging
import argparse
from pathlib import Path
from datetime import datetime


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'Render selected species tree structures as PDF visualizations',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type = str,
        required = True,
        help = 'Path to START_HERE-user_config.yaml'
    )

    parser.add_argument(
        '--output_dir',
        type = str,
        default = None,
        help = 'Base output directory (default: derived from config.output.base_dir)'
    )

    return parser.parse_args()


# ============================================================================
# CONFIGURATION
# ============================================================================

args = parse_arguments()

config_path = Path( args.config )
if not config_path.exists():
    print( f"CRITICAL ERROR: Configuration file not found: {config_path}" )
    sys.exit( 1 )

with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

config_directory = config_path.parent

# Input query manifest (for titles/descriptions)
input_query_manifest_file = config_directory / config[ 'inputs' ][ 'query_manifest' ]

# Output directory
if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]

# Script 001 outputs we consume
input_01_directory = output_base_directory / '1-output'
input_matches_file = input_01_directory / '1_ai-matching_structures.tsv'
input_canonical_file = input_01_directory / '1_ai-canonical_structures.tsv'
input_selected_structures_directory = input_01_directory / '1_ai-selected_structures'
input_canonical_structures_directory = input_01_directory / '1_ai-canonical_structures'

# Script 002 outputs (where we write)
output_directory = output_base_directory / '2-output'
output_directory.mkdir( parents = True, exist_ok = True )
output_canonical_viz_directory = output_directory / '2_ai-canonical_visualizations'
output_all_matched_viz_directory = output_directory / '2_ai-all_matched_visualizations'
output_canonical_viz_directory.mkdir( parents = True, exist_ok = True )
output_all_matched_viz_directory.mkdir( parents = True, exist_ok = True )

output_summary_file = output_directory / '2_ai-visualization_summary.md'
output_placeholder_file = output_directory / '2_ai-visualization-placeholder.txt'

# Log directory
log_directory = output_base_directory / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / '2_ai-log-visualize_structures.log'


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
# SOFT-FAIL HELPERS
# ============================================================================

def write_placeholder( reason ):
    """Write a placeholder text file documenting a soft-fail."""
    placeholder_text = (
        f"GIGANTIC BLOCK_user_requests Script 002 -- visualization placeholder\n"
        f"\n"
        f"Rendering FAILED (soft-fail). Script 001's selection outputs are still valid.\n"
        f"\n"
        f"Reason: {reason}\n"
        f"\n"
        f"Diagnosis:\n"
        f"  See 2_ai-log-visualize_structures.log for details.\n"
        f"\n"
        f"Manual rendering (if env is broken):\n"
        f"  # Activate a Python env with toytree installed\n"
        f"  conda activate aiG-trees_species-user_requests   # or equivalent\n"
        f"  pip install toytree toyplot reportlab\n"
        f"\n"
        f"  # Then render manually\n"
        f"  python -c \"import toytree, toyplot.pdf; \"\n"
        f"            \"t = toytree.tree('path/to/structure.newick'); \"\n"
        f"            \"canvas, _, _ = t.draw(width=900, height=1400); \"\n"
        f"            \"toyplot.pdf.render(canvas, 'out.pdf')\"\n"
        f"\n"
        f"Alternative: use FigTree or iTOL on the newick files in\n"
        f"OUTPUT_pipeline/1-output/1_ai-selected_structures/ directly.\n"
    )
    output_placeholder_file.write_text( placeholder_text )
    logger.warning( f"Wrote placeholder: {output_placeholder_file.name}" )


# ============================================================================
# SECTION 1: LOAD QUERY MANIFEST (for titles)
# ============================================================================

def load_queries():
    """Load queries for title/description lookup."""
    if not input_query_manifest_file.exists():
        return []

    with open( input_query_manifest_file, 'r' ) as input_file:
        manifest = yaml.safe_load( input_file )

    return manifest.get( 'queries', [] ) if manifest else []


def build_query_descriptions( queries ):
    """Build query_name -> description dict."""
    descriptions = {}
    for query in queries:
        descriptions[ query.get( 'name', '' ) ] = query.get( 'description', '' )
    return descriptions


# ============================================================================
# SECTION 2: LOAD SELECTION RESULTS
# ============================================================================

def load_canonical_mapping():
    """
    Load canonical structure selections from Script 001 output.

    Returns:
        dict: { query_name: { 'canonical_structure_id': str, 'description': str } }
    """
    if not input_canonical_file.exists():
        logger.warning( f"Canonical file not found: {input_canonical_file}" )
        return {}

    query_names___canonical = {}

    with open( input_canonical_file, 'r' ) as input_file:
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 2:
                continue

            query_name = parts[ 0 ]
            canonical_structure_id = parts[ 1 ]
            description = parts[ 6 ] if len( parts ) > 6 else ''

            query_names___canonical[ query_name ] = {
                'canonical_structure_id': canonical_structure_id,
                'description': description
            }

    logger.info( f"Loaded {len( query_names___canonical )} canonical picks" )
    return query_names___canonical


def load_all_matched_mapping():
    """
    Load all matched structures from Script 001 output.

    Returns:
        dict: { query_name: [ matching_structure_id, ... ] }
    """
    if not input_matches_file.exists():
        return {}

    query_names___matches = {}

    with open( input_matches_file, 'r' ) as input_file:
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 2:
                continue

            query_name = parts[ 0 ]
            structure_id = parts[ 1 ]

            if structure_id == 'NONE':
                continue

            query_names___matches.setdefault( query_name, [] ).append( structure_id )

    return query_names___matches


# ============================================================================
# SECTION 3: RENDER A SINGLE TREE
# ============================================================================

def find_newick_file( structure_id, search_directory ):
    """
    Find a newick file matching structure_id in the given directory.

    trees_species produces two newicks per structure:
      - 3_ai-..._topology_with_clade_ids.newick   (5-clade backbone only -- tiny)
      - 4_ai-..._complete_tree.newick              (all 70 species -- full tree)

    Prefer the complete_tree for visualization (users want to see species).
    Fall back to the topology newick only if complete is unavailable.

    Returns:
        Path or None
    """
    # Try the complete-tree newick first
    complete_matches = list( search_directory.glob( f'*{structure_id}*complete_tree*.newick' ) )
    if complete_matches:
        return complete_matches[ 0 ]

    # Fall back to any newick matching this structure
    any_matches = list( search_directory.glob( f'*{structure_id}*.newick' ) )
    return any_matches[ 0 ] if any_matches else None


def render_tree_to_pdf_and_svg( newick_path, title_text, pdf_output_path, svg_output_path ):
    """
    Render a newick file to PDF + SVG using toytree.

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    import toytree
    import toyplot
    import toyplot.pdf
    import toyplot.svg

    try:
        tree = toytree.tree( str( newick_path ) )
    except Exception as parse_error:
        return ( False, f"Failed to parse newick: {parse_error}" )

    tip_count = tree.ntips
    # Scale canvas height to tip count for readability: ~20px per tip with a floor
    canvas_height = max( 900, 20 * tip_count + 200 )
    canvas_width = 1000

    try:
        canvas, axes, marks = tree.draw(
            width = canvas_width,
            height = canvas_height,
            tip_labels_align = True,
            tip_labels_style = { "font-size": "11px" },
            node_labels = 'name',
            node_labels_style = { "font-size": "7px", "fill": "#7a7a7a" },
            node_sizes = 5,
            node_colors = '#3288FF',
            edge_style = { "stroke": "#333333", "stroke-width": 1 },
        )

        # Add title
        if title_text:
            canvas.text(
                canvas_width / 2,
                20,
                title_text,
                style = { "font-size": "14px", "text-anchor": "middle", "fill": "#222222", "font-weight": "bold" }
            )
    except Exception as draw_error:
        return ( False, f"Failed to draw tree: {draw_error}" )

    try:
        toyplot.pdf.render( canvas, str( pdf_output_path ) )
        toyplot.svg.render( canvas, str( svg_output_path ) )
    except Exception as render_error:
        return ( False, f"Failed to render PDF/SVG: {render_error}" )

    return ( True, None )


# ============================================================================
# SECTION 4: RENDER BATCHES
# ============================================================================

def render_canonical_batch( query_names___canonical, query_descriptions ):
    """
    Render one PDF+SVG per query for its canonical structure.
    File name includes query name for easy identification.
    """
    logger.info( "Rendering canonical visualizations (one per query)..." )

    rendered = 0
    failed = 0

    for query_name, canonical_info in query_names___canonical.items():
        structure_id = canonical_info.get( 'canonical_structure_id' )
        if not structure_id or structure_id == 'NONE':
            logger.warning( f"  {query_name}: no canonical structure to render" )
            failed += 1
            continue

        newick_path = find_newick_file( structure_id, input_canonical_structures_directory )
        if not newick_path:
            logger.warning( f"  {query_name}: newick not found for {structure_id}" )
            failed += 1
            continue

        description = canonical_info.get( 'description' ) or query_descriptions.get( query_name, '' )

        # Title shows the canonical choice + structure_id + what the query asks for
        title = f"{query_name}  |  {structure_id}"
        if description:
            title += f"  |  {description}"

        pdf_path = output_canonical_viz_directory / f'2_ai-{query_name}-{structure_id}.pdf'
        svg_path = output_canonical_viz_directory / f'2_ai-{query_name}-{structure_id}.svg'

        success, error = render_tree_to_pdf_and_svg( newick_path, title, pdf_path, svg_path )
        if success:
            logger.info( f"  {query_name}: rendered {structure_id} -> {pdf_path.name}" )
            rendered += 1
        else:
            logger.error( f"  {query_name}: render failed for {structure_id}: {error}" )
            failed += 1

    logger.info( f"Canonical rendering: {rendered} succeeded, {failed} failed" )
    return rendered, failed


def render_all_matched_batch( query_names___matches, query_descriptions, canonical_structure_ids ):
    """
    Render every matched structure (across all queries), one PDF per structure.
    Skips re-rendering structures that were already rendered in the canonical batch.
    """
    logger.info( "Rendering all matched structures (one per structure)..." )

    rendered = 0
    failed = 0
    skipped = 0

    # Build reverse mapping: structure_id -> queries that matched it (for titles)
    structure_ids___matching_queries = {}
    for query_name, structures in query_names___matches.items():
        for structure_id in structures:
            structure_ids___matching_queries.setdefault( structure_id, [] ).append( query_name )

    for structure_id in sorted( structure_ids___matching_queries.keys() ):
        matching_queries = structure_ids___matching_queries[ structure_id ]

        newick_path = find_newick_file( structure_id, input_selected_structures_directory )
        if not newick_path:
            logger.warning( f"  {structure_id}: newick not found" )
            failed += 1
            continue

        title = f"{structure_id}  |  matches: {', '.join( matching_queries )}"

        pdf_path = output_all_matched_viz_directory / f'2_ai-{structure_id}.pdf'
        svg_path = output_all_matched_viz_directory / f'2_ai-{structure_id}.svg'

        success, error = render_tree_to_pdf_and_svg( newick_path, title, pdf_path, svg_path )
        if success:
            rendered += 1
        else:
            logger.error( f"  {structure_id}: render failed: {error}" )
            failed += 1

    logger.info( f"All-matched rendering: {rendered} succeeded, {failed} failed" )
    return rendered, failed


# ============================================================================
# SECTION 5: SUMMARY REPORT
# ============================================================================

def write_summary_report( query_names___canonical, query_names___matches,
                          query_descriptions, canonical_stats, all_matched_stats ):
    """Write a human-readable markdown summary of the rendering batch."""
    logger.info( f"Writing visualization summary to: {output_summary_file}" )

    lines = []
    lines.append( "# Visualization Summary" )
    lines.append( "" )
    lines.append( f"**Generated**: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    lines.append( "" )
    lines.append( "## Canonical Visualizations (primary deliverable)" )
    lines.append( "" )
    lines.append( "One PDF per query showing the canonical representative tree." )
    lines.append( f"See `2_ai-canonical_visualizations/` ({canonical_stats[ 0 ]} rendered, {canonical_stats[ 1 ]} failed)" )
    lines.append( "" )

    for query_name, canonical_info in query_names___canonical.items():
        structure_id = canonical_info.get( 'canonical_structure_id', 'NONE' )
        description = canonical_info.get( 'description' ) or query_descriptions.get( query_name, '' )
        pdf_filename = f'2_ai-{query_name}-{structure_id}.pdf'
        lines.append( f"- **{query_name}** -> `{structure_id}`" )
        if description:
            lines.append( f"  - _{description}_" )
        lines.append( f"  - PDF: `2_ai-canonical_visualizations/{pdf_filename}`" )
        lines.append( "" )

    lines.append( "## All Matched Visualizations (reference)" )
    lines.append( "" )
    lines.append( "One PDF per structure that matches ANY query. Useful for inspecting" )
    lines.append( "equivalence classes (multiple structures matching the same query)." )
    lines.append( f"See `2_ai-all_matched_visualizations/` ({all_matched_stats[ 0 ]} rendered, {all_matched_stats[ 1 ]} failed)" )
    lines.append( "" )

    for query_name, structures in query_names___matches.items():
        if structures:
            lines.append( f"- **{query_name}** ({len( structures )} match{'' if len( structures ) == 1 else 'es'}):" )
            for structure_id in structures:
                lines.append( f"    - `2_ai-all_matched_visualizations/2_ai-{structure_id}.pdf`" )
    lines.append( "" )

    lines.append( "## Output Formats" )
    lines.append( "" )
    lines.append( "Each rendered tree is available as both:" )
    lines.append( "- **PDF** (primary -- opens in any PDF reader, familiar format)" )
    lines.append( "- **SVG** (secondary -- editable in Inkscape/Illustrator for figure prep)" )
    lines.append( "" )

    with open( output_summary_file, 'w' ) as output_file:
        output_file.write( '\n'.join( lines ) + '\n' )

    logger.info( "Wrote summary report" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function."""
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 002: VISUALIZE SELECTED STRUCTURES" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Config: {config_path}" )
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
        logger.warning( f"WARNING: toytree/toyplot import failed: {import_error}" )
        logger.warning( "Rendering skipped (soft-fail). Script 001 selection outputs remain valid." )
        write_placeholder( f"toytree/toyplot not available: {import_error}" )
        logger.info( "=" * 80 )
        logger.info( "SCRIPT 002 COMPLETED WITH SOFT-FAIL" )
        logger.info( "=" * 80 )
        return 0

    # Check inputs exist
    if not input_canonical_file.exists() and not input_matches_file.exists():
        logger.error( "CRITICAL ERROR: Script 001 outputs not found!" )
        logger.error( f"Expected: {input_canonical_file} OR {input_matches_file}" )
        logger.error( "Run Script 001 first." )
        sys.exit( 1 )

    # Step 1: Load queries (for titles)
    logger.info( "STEP 1: Loading query manifest (for titles)..." )
    queries = load_queries()
    query_descriptions = build_query_descriptions( queries )

    # Step 2: Load Script 001 outputs
    logger.info( "" )
    logger.info( "STEP 2: Loading Script 001 selection outputs..." )
    query_names___canonical = load_canonical_mapping()
    query_names___matches = load_all_matched_mapping()

    canonical_structure_ids = set()
    for info in query_names___canonical.values():
        sid = info.get( 'canonical_structure_id' )
        if sid and sid != 'NONE':
            canonical_structure_ids.add( sid )

    # Step 3: Render canonical structures (one PDF per query)
    logger.info( "" )
    logger.info( "STEP 3: Rendering canonical structures (primary deliverable)..." )
    canonical_stats = render_canonical_batch( query_names___canonical, query_descriptions )

    # Step 4: Render all matched structures (reference set)
    logger.info( "" )
    logger.info( "STEP 4: Rendering all matched structures (reference set)..." )
    all_matched_stats = render_all_matched_batch( query_names___matches, query_descriptions, canonical_structure_ids )

    # Step 5: Write summary
    logger.info( "" )
    logger.info( "STEP 5: Writing summary report..." )
    write_summary_report(
        query_names___canonical, query_names___matches,
        query_descriptions, canonical_stats, all_matched_stats
    )

    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 002 COMPLETED SUCCESSFULLY" )
    logger.info( "=" * 80 )
    logger.info( f"Outputs written to: {output_directory}" )
    logger.info( f"Canonical PDFs: {canonical_stats[ 0 ]} ({canonical_stats[ 1 ]} failed)" )
    logger.info( f"All-matched PDFs: {all_matched_stats[ 0 ]} ({all_matched_stats[ 1 ]} failed)" )
    logger.info( f"Finished: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
