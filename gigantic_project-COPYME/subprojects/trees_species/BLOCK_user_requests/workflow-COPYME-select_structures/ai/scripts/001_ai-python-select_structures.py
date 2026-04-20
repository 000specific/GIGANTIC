# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Select species tree structures matching topological queries
# Human: Eric Edsinger

"""
User Request Pipeline Script 001: Select Species Tree Structures

Queries the 105 species tree structures produced by trees_species and returns
structures that match user-specified topological features. Designed for
collaborator-driven requests like "give me the 4 trees with Ctenophora-sister
or Porifera-sister crossed with two Placozoa positionings."

The query language has two primitives, both leveraging Rule 7 phylogenetic
blocks:

  require_direct_child:
    - {parent: <bare_name>, child: <bare_name>}
    Asserts that a phylogenetic block exists where the parent clade has the
    given bare name (e.g. "Metazoa") and the child clade has the given bare
    name (e.g. "Ctenophora"). The bare name is the text after the CXXX_
    prefix of a clade_id_name.

  require_sister:
    - [<bare_name_A>, <bare_name_B>]
    Asserts that clades A and B share the same immediate parent on the
    species tree -- they are sister clades.

All conditions in a query are AND-combined: a structure matches if and only
if every require_direct_child AND every require_sister holds.

Bare-name matching is used (rather than exact clade_id_name matching) because
the same biological clade receives different clade_id_name values across
structures that differ in their descendant arrangement (per Rule 6).

Inputs:
  - Query manifest YAML (INPUT_user/query_manifest.yaml)
  - trees_species output_to_input:
      Species_Phylogenetic_Blocks/*phylogenetic_blocks-all_*_structures.tsv
      Species_Parent_Child_Relationships/*parent_child*.tsv
      Species_Tree_Structures/*topology*.newick

Outputs (to OUTPUT_pipeline/1-output/):
  - 1_ai-matching_structures.tsv   (query_name x structure_id, one row per match)
  - 1_ai-query_summary.md           (human-readable report)
  - 1_ai-selected_structures/       (copies of newick files for matched structures)
  - 1_ai-ascii_previews/            (one .txt per matched structure, simple tree ASCII)

Usage:
    python 001_ai-python-select_structures.py --config ../../START_HERE-user_config.yaml
"""

import sys
import shutil
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import yaml


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'Select species tree structures matching topological queries',
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

# Resolve paths
input_trees_species_directory = config_directory / config[ 'inputs' ][ 'trees_species_dir' ]
input_query_manifest_file = config_directory / config[ 'inputs' ][ 'query_manifest' ]

# Upstream trees_species subdirectories
input_phylogenetic_blocks_directory = input_trees_species_directory / 'Species_Phylogenetic_Blocks'
input_parent_child_directory = input_trees_species_directory / 'Species_Parent_Child_Relationships'
input_tree_structures_directory = input_trees_species_directory / 'Species_Tree_Structures'

# Output directory
if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]

output_directory = output_base_directory / '1-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_matches_file = output_directory / '1_ai-matching_structures.tsv'
output_canonical_file = output_directory / '1_ai-canonical_structures.tsv'
output_summary_file = output_directory / '1_ai-query_summary.md'
output_selected_structures_directory = output_directory / '1_ai-selected_structures'
output_canonical_structures_directory = output_directory / '1_ai-canonical_structures'
output_ascii_previews_directory = output_directory / '1_ai-ascii_previews'
output_canonical_previews_directory = output_directory / '1_ai-canonical_previews'

output_selected_structures_directory.mkdir( parents = True, exist_ok = True )
output_canonical_structures_directory.mkdir( parents = True, exist_ok = True )
output_ascii_previews_directory.mkdir( parents = True, exist_ok = True )
output_canonical_previews_directory.mkdir( parents = True, exist_ok = True )

# Log directory
log_directory = output_base_directory / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / '1_ai-log-select_structures.log'


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
# BARE NAME HELPERS
# ============================================================================

def bare_name( clade_id_name ):
    """
    Strip the CXXX_ prefix from a clade_id_name to get the bare clade name.

    Examples:
        "C082_Metazoa"           -> "Metazoa"
        "C086_Ctenophora"        -> "Ctenophora"
        "C001_Fonticula_alba"    -> "Fonticula_alba"
        "C000_OOL"               -> "OOL"

    Assumes clade_id_names are formatted as CXXX_Name where XXX is numeric
    and Name may itself contain underscores (e.g. Fonticula_alba).
    """
    if '_' not in clade_id_name:
        return clade_id_name
    prefix, _, rest = clade_id_name.partition( '_' )
    # prefix should be 'C' followed by digits
    if prefix.startswith( 'C' ) and prefix[ 1: ].isdigit():
        return rest
    return clade_id_name


# ============================================================================
# SECTION 1: LOAD QUERY MANIFEST
# ============================================================================

def load_query_manifest():
    """
    Load and validate the query manifest YAML.

    Returns:
        list of query dicts, each with keys:
            name (str)
            description (str, optional)
            require_direct_child (list of {parent, child})
            require_sister (list of [name_A, name_B])
    """
    logger.info( f"Loading query manifest from: {input_query_manifest_file}" )

    if not input_query_manifest_file.exists():
        logger.error( f"CRITICAL ERROR: Query manifest not found: {input_query_manifest_file}" )
        sys.exit( 1 )

    with open( input_query_manifest_file, 'r' ) as input_file:
        manifest = yaml.safe_load( input_file )

    if not manifest or 'queries' not in manifest:
        logger.error( f"CRITICAL ERROR: Query manifest missing 'queries' top-level key" )
        sys.exit( 1 )

    queries = manifest[ 'queries' ]

    # Basic validation
    for index, query in enumerate( queries ):
        if 'name' not in query:
            logger.error( f"CRITICAL ERROR: query at index {index} missing 'name'" )
            sys.exit( 1 )
        # Normalize optional fields
        query.setdefault( 'description', '' )
        query.setdefault( 'require_direct_child', [] )
        query.setdefault( 'require_sister', [] )

        if not query[ 'require_direct_child' ] and not query[ 'require_sister' ]:
            logger.warning( f"Query '{query[ 'name' ]}' has no conditions -- will match all structures" )

    logger.info( f"Loaded {len( queries )} queries from manifest" )

    return queries


# ============================================================================
# SECTION 2: LOAD PHYLOGENETIC BLOCKS PER STRUCTURE
# ============================================================================

def load_blocks_per_structure():
    """
    Load phylogenetic blocks grouped by structure_id from the combined
    all-structures TSV produced by trees_species Script 006.

    Returns:
        dict: { structure_id: [ { 'parent_clade_id_name': str,
                                  'child_clade_id_name': str,
                                  'parent_bare_name': str,
                                  'child_bare_name': str }, ... ] }
    """
    logger.info( f"Loading phylogenetic blocks from: {input_phylogenetic_blocks_directory}" )

    block_files = list( input_phylogenetic_blocks_directory.glob( '*phylogenetic_blocks-all_*_structures.tsv' ) )

    if not block_files:
        logger.error( f"CRITICAL ERROR: No combined phylogenetic blocks file found!" )
        logger.error( f"Expected pattern: *phylogenetic_blocks-all_*_structures.tsv" )
        sys.exit( 1 )

    if len( block_files ) > 1:
        logger.error( f"CRITICAL ERROR: Multiple combined phylogenetic blocks files found (ambiguous):" )
        for block_file in sorted( block_files ):
            logger.error( f"  {block_file.name}" )
        sys.exit( 1 )

    block_file = block_files[ 0 ]
    logger.info( f"Using file: {block_file.name}" )

    structure_ids___blocks = defaultdict( list )

    with open( block_file, 'r' ) as input_file:
        # Structure_ID	Phylogenetic_Block	Parent_Clade_ID_Name	Child_Clade_ID_Name
        # structure_001	C069_Holozoa::C082_Metazoa	C069_Holozoa	C082_Metazoa
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        structure_id_column = column_names___indices.get( 'Structure_ID' )
        parent_clade_id_name_column = column_names___indices.get( 'Parent_Clade_ID_Name' )
        child_clade_id_name_column = column_names___indices.get( 'Child_Clade_ID_Name' )

        if None in [ structure_id_column, parent_clade_id_name_column, child_clade_id_name_column ]:
            logger.error( f"CRITICAL ERROR: Phylogenetic blocks file missing required columns: {header_parts}" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]
            parent_clade_id_name = parts[ parent_clade_id_name_column ]
            child_clade_id_name = parts[ child_clade_id_name_column ]

            structure_ids___blocks[ structure_id ].append( {
                'parent_clade_id_name': parent_clade_id_name,
                'child_clade_id_name': child_clade_id_name,
                'parent_bare_name': bare_name( parent_clade_id_name ),
                'child_bare_name': bare_name( child_clade_id_name )
            } )

    logger.info( f"Loaded blocks for {len( structure_ids___blocks )} structures" )
    return structure_ids___blocks


# ============================================================================
# SECTION 3: QUERY EVALUATION
# ============================================================================

def structure_matches_query( blocks, query ):
    """
    Check if all conditions in a query hold for a given structure's blocks.

    Args:
        blocks: list of block dicts for one structure
        query: query dict with require_direct_child and require_sister

    Returns:
        tuple: (matches: bool, unmet_conditions: list of str)
    """
    unmet = []

    # Check require_direct_child: there must exist a block with matching bare names
    for condition in query[ 'require_direct_child' ]:
        parent_name = condition[ 'parent' ]
        child_name = condition[ 'child' ]

        found = False
        for block in blocks:
            if block[ 'parent_bare_name' ] == parent_name and block[ 'child_bare_name' ] == child_name:
                found = True
                break

        if not found:
            unmet.append( f"require_direct_child(parent={parent_name}, child={child_name})" )

    # Check require_sister: both A and B share the same immediate parent
    # (both parent_bare_names match, and both parent_clade_id_names are identical -- same parent node)
    for condition in query[ 'require_sister' ]:
        if len( condition ) != 2:
            unmet.append( f"require_sister has wrong arity (expected 2 names): {condition}" )
            continue

        name_a, name_b = condition

        # Find all (parent_clade_id_name) values that have name_a as child
        parents_with_a = set()
        for block in blocks:
            if block[ 'child_bare_name' ] == name_a:
                parents_with_a.add( block[ 'parent_clade_id_name' ] )

        # Find all (parent_clade_id_name) values that have name_b as child
        parents_with_b = set()
        for block in blocks:
            if block[ 'child_bare_name' ] == name_b:
                parents_with_b.add( block[ 'parent_clade_id_name' ] )

        # Sister iff there's a shared parent clade_id_name
        shared_parents = parents_with_a & parents_with_b
        if not shared_parents:
            unmet.append( f"require_sister([{name_a}, {name_b}])" )

    return ( len( unmet ) == 0, unmet )


def evaluate_all_queries( queries, structure_ids___blocks ):
    """
    Evaluate every query against every structure.

    Returns:
        dict: { query_name: [ matching_structure_id, ... ] }
    """
    logger.info( "Evaluating queries against all structures..." )

    query_names___matches = {}

    for query in queries:
        query_name = query[ 'name' ]
        matching_structures = []

        for structure_id in sorted( structure_ids___blocks.keys() ):
            blocks = structure_ids___blocks[ structure_id ]
            matches, unmet = structure_matches_query( blocks, query )
            if matches:
                matching_structures.append( structure_id )

        query_names___matches[ query_name ] = matching_structures
        logger.info( f"  {query_name}: {len( matching_structures )} structure(s) match" )

    return query_names___matches


# ============================================================================
# SECTION 4: CANONICAL REPRESENTATIVE SELECTION
# ============================================================================

def load_manifest_settings( queries_manifest_path ):
    """
    Load top-level 'settings' from the query manifest (separate from per-query
    fields).

    Returns:
        dict: settings block, or empty dict if absent
    """
    with open( queries_manifest_path, 'r' ) as input_file:
        manifest = yaml.safe_load( input_file )

    return manifest.get( 'settings', {} ) if manifest else {}


def pick_canonical_representatives( query_names___matches, queries, structure_ids___blocks, settings ):
    """
    For each query with multiple matching structures, pick a single canonical
    representative that is closest to the reference structure.

    "Closest" is measured by the number of shared phylogenetic blocks:
    the structure that shares the MOST blocks with the reference is picked.
    This naturally preserves the reference tree's arrangement in regions the
    user did not constrain.

    Ties are broken by lowest structure_id (for determinism).

    Args:
        query_names___matches: dict of query_name -> list of matching structure_ids
        queries: list of query dicts (for per-query overrides)
        structure_ids___blocks: per-structure block lists
        settings: top-level settings dict from manifest

    Returns:
        dict: { query_name: {
            'canonical_structure_id': str (or None if no match),
            'n_equivalent': int,
            'equivalent_structures': [str, ...],
            'shared_block_count': int,
            'reference_structure': str (or None if canonical disabled)
        } }
    """
    # Read global settings
    canonical_config = settings.get( 'canonical_representative', {} )
    global_enabled = canonical_config.get( 'enabled', False )
    global_reference = canonical_config.get( 'reference_structure', 'structure_001' )

    canonical_results = {}

    for query in queries:
        query_name = query[ 'name' ]
        matches = query_names___matches.get( query_name, [] )

        # Per-query override (opt-in/out)
        per_query_canonical = query.get( 'canonical_representative', None )
        if per_query_canonical is not None:
            enabled = per_query_canonical.get( 'enabled', global_enabled )
            reference = per_query_canonical.get( 'reference_structure', global_reference )
        else:
            enabled = global_enabled
            reference = global_reference

        if not enabled:
            canonical_results[ query_name ] = {
                'canonical_structure_id': matches[ 0 ] if matches else None,
                'n_equivalent': len( matches ),
                'equivalent_structures': matches,
                'shared_block_count': 0,
                'reference_structure': None
            }
            continue

        if not matches:
            canonical_results[ query_name ] = {
                'canonical_structure_id': None,
                'n_equivalent': 0,
                'equivalent_structures': [],
                'shared_block_count': 0,
                'reference_structure': reference
            }
            continue

        # Build reference block set as tuples of (parent_bare_name, child_bare_name)
        # so comparisons are invariant to differing clade_id numbers between structures
        # (Rule 6: the same biological block has the same bare names, different clade IDs).
        if reference not in structure_ids___blocks:
            logger.warning( f"Reference structure '{reference}' not found in data; skipping canonical pick for query '{query_name}'" )
            canonical_results[ query_name ] = {
                'canonical_structure_id': matches[ 0 ] if matches else None,
                'n_equivalent': len( matches ),
                'equivalent_structures': matches,
                'shared_block_count': 0,
                'reference_structure': reference
            }
            continue

        reference_block_set = set(
            ( block[ 'parent_bare_name' ], block[ 'child_bare_name' ] )
            for block in structure_ids___blocks[ reference ]
        )

        best_match = None
        best_shared = -1
        for candidate_id in matches:
            candidate_block_set = set(
                ( block[ 'parent_bare_name' ], block[ 'child_bare_name' ] )
                for block in structure_ids___blocks[ candidate_id ]
            )
            shared = len( reference_block_set & candidate_block_set )

            if shared > best_shared:
                best_shared = shared
                best_match = candidate_id
            elif shared == best_shared:
                # Tie-break by lowest structure_id for determinism
                if candidate_id < best_match:
                    best_match = candidate_id

        canonical_results[ query_name ] = {
            'canonical_structure_id': best_match,
            'n_equivalent': len( matches ),
            'equivalent_structures': matches,
            'shared_block_count': best_shared,
            'reference_structure': reference
        }

    return canonical_results


# ============================================================================
# SECTION 5: ASCII TREE PREVIEW
# ============================================================================

def build_tree_from_parent_child( structure_id ):
    """
    Load per-structure parent-child table and build a minimal tree dict.

    Returns:
        tuple: (root_clade_id_name, children_map: dict of parent -> list of children)
    """
    parent_child_files = list( input_parent_child_directory.glob( f'*{structure_id}*parent_child*.tsv' ) )

    if not parent_child_files:
        return ( None, {} )

    parent_child_path = parent_child_files[ 0 ]

    children_map = defaultdict( list )
    all_parents = set()
    all_children = set()

    with open( parent_child_path, 'r' ) as input_file:
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        parent_column = column_names___indices.get( 'Parent_Clade_ID_Name' )
        child_column = column_names___indices.get( 'Child_Clade_ID_Name' )

        if parent_column is None or child_column is None:
            return ( None, {} )

        for line in input_file:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            parent = parts[ parent_column ]
            child = parts[ child_column ]

            children_map[ parent ].append( child )
            all_parents.add( parent )
            all_children.add( child )

    # Root is a parent that never appears as a child (except OOL)
    roots = all_parents - all_children
    root = None
    if roots:
        # Prefer OOL if it's one of the roots
        for candidate in roots:
            if 'OOL' in candidate:
                root = candidate
                break
        if root is None:
            root = sorted( roots )[ 0 ]

    return ( root, dict( children_map ) )


def render_ascii_tree( structure_id ):
    """
    Render an ASCII preview of the species tree for a given structure.

    Returns:
        str: ASCII tree representation
    """
    root, children_map = build_tree_from_parent_child( structure_id )

    if root is None:
        return f"(could not render tree for {structure_id})"

    lines = [ f"# Structure: {structure_id}", "" ]

    def render_node( node, prefix = "", is_last = True ):
        connector = "└── " if is_last else "├── "
        lines.append( f"{prefix}{connector}{node}" )
        children = children_map.get( node, [] )
        for index, child in enumerate( sorted( children ) ):
            extension = "    " if is_last else "│   "
            render_node( child, prefix + extension, index == len( children ) - 1 )

    # Render starting from root
    lines.append( root )
    children = children_map.get( root, [] )
    for index, child in enumerate( sorted( children ) ):
        render_node( child, "", index == len( children ) - 1 )

    return '\n'.join( lines )


# ============================================================================
# SECTION 6: WRITE OUTPUTS
# ============================================================================

def write_matches_table( queries, query_names___matches ):
    """Write query_name x structure_id matches TSV."""
    logger.info( f"Writing matches table to: {output_matches_file}" )

    with open( output_matches_file, 'w' ) as output_file:
        output = 'Query_Name (query identifier from manifest)\t'
        output += 'Structure_ID (structure identifier that matches this query)\t'
        output += 'Query_Description (description from manifest)\n'
        output_file.write( output )

        for query in queries:
            query_name = query[ 'name' ]
            description = query.get( 'description', '' )
            matches = query_names___matches.get( query_name, [] )

            if not matches:
                output = f"{query_name}\tNONE\t{description}\n"
                output_file.write( output )
            else:
                for structure_id in matches:
                    output = f"{query_name}\t{structure_id}\t{description}\n"
                    output_file.write( output )

    total_rows = sum(
        max( 1, len( query_names___matches.get( q[ 'name' ], [] ) ) )
        for q in queries
    )
    logger.info( f"Wrote {total_rows} rows" )


def write_canonical_table( queries, canonical_results ):
    """Write canonical representative table (one row per query)."""
    logger.info( f"Writing canonical structures table to: {output_canonical_file}" )

    with open( output_canonical_file, 'w' ) as output_file:
        output = 'Query_Name (query identifier from manifest)\t'
        output += 'Canonical_Structure_ID (single representative chosen per query; closest to reference by shared phylogenetic block count)\t'
        output += 'Reference_Structure (structure against which closeness was measured; typically structure_001 which is the user input tree)\t'
        output += 'Shared_Block_Count (number of phylogenetic blocks shared with the reference structure higher is closer)\t'
        output += 'Total_Equivalent (count of matching structures that satisfy the query before canonical pick)\t'
        output += 'Equivalent_Structures (comma delimited list of all matching structures for this query)\t'
        output += 'Query_Description (description from manifest)\n'
        output_file.write( output )

        for query in queries:
            query_name = query[ 'name' ]
            description = query.get( 'description', '' )
            canonical = canonical_results.get( query_name, {} )

            canonical_structure_id = canonical.get( 'canonical_structure_id' ) or 'NONE'
            reference = canonical.get( 'reference_structure' ) or 'disabled'
            shared_count = canonical.get( 'shared_block_count', 0 )
            n_equivalent = canonical.get( 'n_equivalent', 0 )
            equivalent = ','.join( canonical.get( 'equivalent_structures', [] ) ) or 'NONE'

            output = f"{query_name}\t{canonical_structure_id}\t{reference}\t{shared_count}\t{n_equivalent}\t{equivalent}\t{description}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( queries )} canonical picks" )


def copy_canonical_newicks( canonical_results ):
    """Copy newicks for only the canonical representative of each query."""
    logger.info( f"Copying canonical newicks to: {output_canonical_structures_directory}" )

    canonical_structure_ids = set()
    for result in canonical_results.values():
        canonical_id = result.get( 'canonical_structure_id' )
        if canonical_id:
            canonical_structure_ids.add( canonical_id )

    copied = 0
    for structure_id in sorted( canonical_structure_ids ):
        newick_files = list( input_tree_structures_directory.glob( f'*{structure_id}*.newick' ) )
        for newick_file in newick_files:
            destination = output_canonical_structures_directory / newick_file.name
            shutil.copy2( newick_file, destination )
            copied += 1

    logger.info( f"Copied {copied} canonical newick files ({len( canonical_structure_ids )} unique structures)" )


def write_canonical_previews( canonical_results ):
    """Write ASCII tree previews for just the canonical structures."""
    logger.info( f"Writing canonical ASCII previews to: {output_canonical_previews_directory}" )

    canonical_structure_ids = set()
    for result in canonical_results.values():
        canonical_id = result.get( 'canonical_structure_id' )
        if canonical_id:
            canonical_structure_ids.add( canonical_id )

    written = 0
    for structure_id in sorted( canonical_structure_ids ):
        ascii_tree = render_ascii_tree( structure_id )
        preview_file = output_canonical_previews_directory / f'{structure_id}_ascii_tree.txt'
        with open( preview_file, 'w' ) as output_file:
            output_file.write( ascii_tree + '\n' )
        written += 1

    logger.info( f"Wrote {written} canonical ASCII preview files" )


def find_newicks_for_structure( structure_id ):
    """
    Find newick files for a given structure_id.

    trees_species produces two kinds of newicks per structure:
      - 3_ai-structure_NNN_topology_with_clade_ids.newick  (5-clade backbone only)
      - 4_ai-structure_NNN_complete_tree.newick            (all 70 species)

    Both are useful -- the complete tree is primary for visualization,
    the topology-only is smaller for topology comparison work. This helper
    returns all matching files.
    """
    return list( input_tree_structures_directory.glob( f'*{structure_id}*.newick' ) )


def copy_matched_newicks( query_names___matches ):
    """Copy newick files for every matched structure into output."""
    logger.info( f"Copying matched newicks to: {output_selected_structures_directory}" )

    # Collect unique structure_ids across all queries
    all_matched_structure_ids = set()
    for matches in query_names___matches.values():
        all_matched_structure_ids.update( matches )

    copied = 0
    for structure_id in sorted( all_matched_structure_ids ):
        newick_files = find_newicks_for_structure( structure_id )
        if not newick_files:
            logger.warning( f"No newick file found for {structure_id}" )
            continue

        for newick_file in newick_files:
            destination = output_selected_structures_directory / newick_file.name
            shutil.copy2( newick_file, destination )
            copied += 1

    logger.info( f"Copied {copied} newick files for {len( all_matched_structure_ids )} unique matched structures" )


def write_ascii_previews( query_names___matches ):
    """Write ASCII tree previews for every matched structure."""
    logger.info( f"Writing ASCII tree previews to: {output_ascii_previews_directory}" )

    all_matched_structure_ids = set()
    for matches in query_names___matches.values():
        all_matched_structure_ids.update( matches )

    written = 0
    for structure_id in sorted( all_matched_structure_ids ):
        ascii_tree = render_ascii_tree( structure_id )
        preview_file = output_ascii_previews_directory / f'{structure_id}_ascii_tree.txt'
        with open( preview_file, 'w' ) as output_file:
            output_file.write( ascii_tree + '\n' )
        written += 1

    logger.info( f"Wrote {written} ASCII preview files" )


def write_summary_report( queries, query_names___matches, canonical_results, total_structures ):
    """Write human-readable Markdown summary of the query results."""
    logger.info( f"Writing query summary report to: {output_summary_file}" )

    lines = []
    lines.append( "# User Request Query Summary" )
    lines.append( "" )
    lines.append( f"**Generated**: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    lines.append( "" )
    lines.append( f"- Queries evaluated: {len( queries )}" )
    lines.append( f"- Structures scanned: {total_structures}" )

    total_matches = sum( len( m ) for m in query_names___matches.values() )
    unique_matches = len( set( s for matches in query_names___matches.values() for s in matches ) )
    lines.append( f"- Total query-structure matches: {total_matches}" )
    lines.append( f"- Unique matched structures: {unique_matches}" )
    lines.append( "" )

    for query in queries:
        query_name = query[ 'name' ]
        description = query.get( 'description', '' )
        matches = query_names___matches.get( query_name, [] )

        lines.append( f"## {query_name}" )
        lines.append( "" )
        if description:
            lines.append( f"_{description}_" )
            lines.append( "" )

        # Conditions
        conditions = []
        for condition in query.get( 'require_direct_child', [] ):
            conditions.append( f"- {condition[ 'parent' ]} has {condition[ 'child' ]} as direct child" )
        for condition in query.get( 'require_sister', [] ):
            conditions.append( f"- {condition[ 0 ]} and {condition[ 1 ]} are sister clades" )

        if conditions:
            lines.append( "**Conditions:**" )
            lines.extend( conditions )
            lines.append( "" )

        # Matching structures
        if matches:
            lines.append( f"**Matching structures ({len( matches )}):** {', '.join( matches )}" )
        else:
            lines.append( "**Matching structures**: (none found)" )

        # Canonical representative (if enabled and a pick was made)
        canonical = canonical_results.get( query_name, {} )
        canonical_id = canonical.get( 'canonical_structure_id' )
        reference = canonical.get( 'reference_structure' )
        if canonical_id and reference and len( matches ) > 1:
            shared = canonical.get( 'shared_block_count', 0 )
            lines.append( f"**Canonical pick**: `{canonical_id}` (shares {shared} phylogenetic blocks with reference `{reference}`)" )
        elif canonical_id and len( matches ) == 1:
            lines.append( f"**Canonical pick**: `{canonical_id}` (only match)" )

        lines.append( "" )

    # Cross-matrix showing which structures match multiple queries
    lines.append( "---" )
    lines.append( "" )
    lines.append( "## Cross-Matrix: Structures Matching Multiple Queries" )
    lines.append( "" )

    structure_ids___matched_queries = defaultdict( list )
    for query_name, matches in query_names___matches.items():
        for structure_id in matches:
            structure_ids___matched_queries[ structure_id ].append( query_name )

    multi_match_structures = [ ( sid, qs ) for sid, qs in structure_ids___matched_queries.items() if len( qs ) > 1 ]
    if multi_match_structures:
        for structure_id, query_list in sorted( multi_match_structures ):
            lines.append( f"- **{structure_id}** matches: {', '.join( sorted( query_list ) )}" )
    else:
        lines.append( "(no structures match multiple queries)" )
    lines.append( "" )

    # Output files
    lines.append( "---" )
    lines.append( "" )
    lines.append( "## Output Files" )
    lines.append( "" )
    lines.append( "All matches (equivalence classes per query):" )
    lines.append( f"- `1_ai-matching_structures.tsv` -- every (query x structure) match in TSV form" )
    lines.append( f"- `1_ai-selected_structures/` -- newick copies of all matched structures" )
    lines.append( f"- `1_ai-ascii_previews/` -- ASCII tree previews of all matched structures" )
    lines.append( "" )
    lines.append( "Canonical representative per query (one structure each):" )
    lines.append( f"- `1_ai-canonical_structures.tsv` -- one row per query with the canonical pick" )
    lines.append( f"- `1_ai-canonical_structures/` -- newick copies of canonical picks only" )
    lines.append( f"- `1_ai-canonical_previews/` -- ASCII previews of canonical picks only" )
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
    logger.info( "SCRIPT 001: SELECT SPECIES TREE STRUCTURES" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Config file: {config_path}" )
    logger.info( "" )

    # Step 1: Load query manifest
    logger.info( "STEP 1: Loading query manifest..." )
    queries = load_query_manifest()

    # Step 2: Load phylogenetic blocks per structure
    logger.info( "" )
    logger.info( "STEP 2: Loading phylogenetic blocks..." )
    structure_ids___blocks = load_blocks_per_structure()
    total_structures = len( structure_ids___blocks )

    # Step 3: Evaluate queries
    logger.info( "" )
    logger.info( "STEP 3: Evaluating queries..." )
    query_names___matches = evaluate_all_queries( queries, structure_ids___blocks )

    # Step 4: Pick canonical representative per query (if enabled in settings)
    logger.info( "" )
    logger.info( "STEP 4: Picking canonical representatives..." )
    settings = load_manifest_settings( input_query_manifest_file )
    canonical_results = pick_canonical_representatives(
        query_names___matches, queries, structure_ids___blocks, settings
    )
    canonical_enabled = settings.get( 'canonical_representative', {} ).get( 'enabled', False )
    if canonical_enabled:
        reference = settings.get( 'canonical_representative', {} ).get( 'reference_structure', 'structure_001' )
        for query in queries:
            result = canonical_results.get( query[ 'name' ], {} )
            canonical_id = result.get( 'canonical_structure_id' ) or 'NONE'
            n_equiv = result.get( 'n_equivalent', 0 )
            shared = result.get( 'shared_block_count', 0 )
            logger.info( f"  {query[ 'name' ]}: {canonical_id} (shared={shared} blocks with {reference}, {n_equiv} equivalent)" )
    else:
        logger.info( "  canonical_representative disabled (no canonical picks made)" )

    # Step 5: Write outputs
    logger.info( "" )
    logger.info( "STEP 5: Writing outputs..." )
    write_matches_table( queries, query_names___matches )
    write_canonical_table( queries, canonical_results )
    copy_matched_newicks( query_names___matches )
    copy_canonical_newicks( canonical_results )
    write_ascii_previews( query_names___matches )
    write_canonical_previews( canonical_results )
    write_summary_report( queries, query_names___matches, canonical_results, total_structures )

    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 001 COMPLETED SUCCESSFULLY" )
    logger.info( "=" * 80 )
    logger.info( f"Outputs written to: {output_directory}" )
    logger.info( f"Finished: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
