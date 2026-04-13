#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Integrate outputs from scripts 001-006 into comprehensive clade data table
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 007: Integrate All Clade Data

Purpose:
    Integrate outputs from scripts 001-006 into a single comprehensive table
    containing all clade information across all structures. This master table
    provides a unified view of every clade in every topology permutation,
    including identifiers, names, types, parent relationships, phylogenetic
    blocks, paths, and multiple Newick representations.

    Since the phylogenetic paths file from script 004 only contains species
    (leaf) paths, this script reconstructs full phylogenetic paths for ALL
    clades (internal and leaf) by parsing the complete Newick trees directly.

    Newick conversion helpers produce four representations of each tree:
    - Structure only: just the branching pattern (parentheses and commas)
    - IDs only: just CXXX identifiers
    - Names only: just clade names (after CXXX_ prefix)
    - IDs and names: full CXXX_Name labels without branch lengths

Inputs:
    --workflow-dir: Workflow root directory (reads config and OUTPUT_pipeline/)

    Reads:
    - OUTPUT_pipeline/2-output/2_ai-topology_permutations.tsv
    - OUTPUT_pipeline/4-output/4_ai-clade_registry.tsv
    - OUTPUT_pipeline/4-output/newick_trees/ (complete tree Newick files)
    - OUTPUT_pipeline/6-output/6_ai-phylogenetic_blocks-all_*_structures.tsv

Outputs:
    OUTPUT_pipeline/7-output/7_ai-integrated_clade_data-all_structures.tsv
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import sys
import re
import yaml


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 007: Integrate all clade data into comprehensive table' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    return parser.parse_args()


# ============================================================================
# Newick Parser for Full Path Extraction
# ============================================================================

class TreeNode:
    """Represents a node in a parsed Newick tree."""

    def __init__( self, label: str = '', branch_length: str = '' ):
        self.label = label
        self.branch_length = branch_length
        self.children: List[ 'TreeNode' ] = []
        self.parent: Optional[ 'TreeNode' ] = None

    def add_child( self, child: 'TreeNode' ):
        """Add a child node."""
        self.children.append( child )
        child.parent = self

    def is_leaf( self ) -> bool:
        """Check if this is a leaf node (no children)."""
        return len( self.children ) == 0

    def get_clade_id( self ) -> str:
        """Extract CXXX from CXXX_Name label."""
        if self.label and '_' in self.label and self.label[ 0 ] == 'C':
            parts_label = self.label.split( '_', 1 )
            if parts_label[ 0 ][ 1: ].isdigit():
                return parts_label[ 0 ]
        return self.label

    def get_clade_name( self ) -> str:
        """Extract Name from CXXX_Name label."""
        if self.label and '_' in self.label and self.label[ 0 ] == 'C':
            parts_label = self.label.split( '_', 1 )
            if parts_label[ 0 ][ 1: ].isdigit():
                return parts_label[ 1 ]
        return self.label

    def get_path_to_root( self ) -> List[ str ]:
        """Get path from this node to root as list of labels."""
        path = []
        current = self
        while current is not None:
            if current.label:
                path.append( current.label )
            current = current.parent
        return path

    def to_newick( self ) -> str:
        """Convert subtree back to Newick string (without branch lengths)."""
        if self.is_leaf():
            return self.label
        children_newick = ','.join( [ child.to_newick() for child in self.children ] )
        return f"({children_newick}){self.label}"


def parse_newick_tree( newick_string: str ) -> TreeNode:
    """Parse a Newick string into a TreeNode tree structure."""
    newick_string = newick_string.strip()
    if newick_string.endswith( ';' ):
        newick_string = newick_string[ :-1 ]

    stack = [ TreeNode() ]
    current_token = ''
    i = 0

    while i < len( newick_string ):
        char = newick_string[ i ]

        if char == '(':
            new_node = TreeNode()
            stack[ -1 ].add_child( new_node )
            stack.append( new_node )
            current_token = ''

        elif char == ',':
            if current_token:
                label, branch_length = _parse_label_and_length( current_token )
                child = TreeNode( label, branch_length )
                stack[ -1 ].add_child( child )
                current_token = ''

        elif char == ')':
            if current_token:
                label, branch_length = _parse_label_and_length( current_token )
                child = TreeNode( label, branch_length )
                stack[ -1 ].add_child( child )
                current_token = ''

            finished_node = stack.pop()

            i += 1
            label_and_length = ''
            while i < len( newick_string ) and newick_string[ i ] not in '(),;':
                label_and_length += newick_string[ i ]
                i += 1

            if label_and_length:
                label, branch_length = _parse_label_and_length( label_and_length )
                finished_node.label = label
                finished_node.branch_length = branch_length

            i -= 1

        else:
            current_token += char

        i += 1

    # The actual tree root is the single child of the dummy root
    if stack[ 0 ].children:
        return stack[ 0 ].children[ 0 ] if len( stack[ 0 ].children ) == 1 else stack[ 0 ]
    return stack[ 0 ]


def _parse_label_and_length( token: str ) -> Tuple[ str, str ]:
    """Parse label:branch_length from a token."""
    if ':' in token:
        parts_token = token.split( ':', 1 )
        return ( parts_token[ 0 ].strip(), parts_token[ 1 ].strip() )
    return ( token.strip(), '' )


def extract_all_clades_with_paths( tree_root: TreeNode ) -> List[ Dict ]:
    """
    Extract all clades from a tree with their phylogenetic paths.

    Returns a list of dictionaries with keys:
    - clade_id, clade_name, clade_id_name, clade_type, phylogenetic_path
    """
    results = []

    def traverse( node: TreeNode ):
        if node.label:
            clade_id = node.get_clade_id()
            clade_name = node.get_clade_name()
            clade_id_name = node.label
            clade_type = 'species' if node.is_leaf() else 'internal'

            path = node.get_path_to_root()
            path.reverse()
            phylogenetic_path = ','.join( path )

            results.append( {
                'clade_id': clade_id,
                'clade_name': clade_name,
                'clade_id_name': clade_id_name,
                'clade_type': clade_type,
                'phylogenetic_path': phylogenetic_path
            } )

        for child in node.children:
            traverse( child )

    traverse( tree_root )
    return results


# ============================================================================
# Newick Conversion Helpers
# ============================================================================

def convert_newick_to_structure_only( newick_string: str ) -> str:
    """
    Remove all labels and branch lengths, keeping just the branching structure.

    Example: ((C001_Fonticula_alba:1.0,C002_Capsaspora:1.0)C068_Basal:1.0)
    Result:  ((,))
    """
    result = []
    i = 0
    while i < len( newick_string ):
        char = newick_string[ i ]
        if char in '(,)':
            result.append( char )
            i += 1
        elif char == ';':
            i += 1
        else:
            # Skip all label and branch length characters
            while i < len( newick_string ) and newick_string[ i ] not in '(,);':
                i += 1
    return ''.join( result )


def convert_newick_to_ids_only( newick_string: str ) -> str:
    """
    Keep just CXXX identifier parts, removing names and branch lengths.

    Example: ((C001_Fonticula_alba:1.0,C002_Capsaspora:1.0)C068_Basal:1.0)
    Result:  ((C001,C002)C068)
    """
    # Remove branch lengths first
    cleaned = re.sub( r':[^,\)\(;]+', '', newick_string )
    # Remove semicolon
    cleaned = cleaned.rstrip( ';' )
    # Replace CXXX_anything with just CXXX
    cleaned = re.sub( r'(C\d{3,})_[^,\)\(;]+', r'\1', cleaned )
    return cleaned


def convert_newick_to_names_only( newick_string: str ) -> str:
    """
    Keep just the name parts (after CXXX_ prefix), removing IDs and branch lengths.

    Example: ((C001_Fonticula_alba:1.0,C002_Capsaspora:1.0)C068_Basal:1.0)
    Result:  ((Fonticula_alba,Capsaspora)Basal)
    """
    # Remove branch lengths first
    cleaned = re.sub( r':[^,\)\(;]+', '', newick_string )
    # Remove semicolon
    cleaned = cleaned.rstrip( ';' )
    # Replace CXXX_Name with just Name
    cleaned = re.sub( r'C\d{3,}_([^,\)\(;]+)', r'\1', cleaned )
    return cleaned


def convert_newick_to_ids_and_names( newick_string: str ) -> str:
    """
    Remove branch lengths but keep full CXXX_Name labels.

    Example: ((C001_Fonticula_alba:1.0,C002_Capsaspora:1.0)C068_Basal:1.0)
    Result:  ((C001_Fonticula_alba,C002_Capsaspora)C068_Basal)
    """
    # Remove branch lengths
    cleaned = re.sub( r':[^,\)\(;]+', '', newick_string )
    # Remove semicolon
    cleaned = cleaned.rstrip( ';' )
    return cleaned


def extract_clade_subtree_newick( full_newick: str, target_clade_id_name: str ) -> Optional[ str ]:
    """
    Extract the Newick subtree rooted at a specific clade from the full tree.

    Finds the node labeled with target_clade_id_name and extracts its complete
    subtree including all descendants.

    Returns the subtree Newick string, or None if clade not found.
    """
    working_newick = full_newick.rstrip( ';' ).strip()

    target_position = working_newick.find( target_clade_id_name )

    if target_position == -1:
        return None

    # Check if this clade is an internal node (label appears after a closing parenthesis)
    if target_position > 0 and working_newick[ target_position - 1 ] == ')':
        # Internal node: find the matching opening parenthesis
        close_paren_position = target_position - 1
        depth = 1
        search_position = close_paren_position - 1

        while search_position >= 0 and depth > 0:
            if working_newick[ search_position ] == ')':
                depth += 1
            elif working_newick[ search_position ] == '(':
                depth -= 1
            search_position -= 1

        open_paren_position = search_position + 1

        # The subtree goes from the opening paren to the end of the label
        label_end = target_position + len( target_clade_id_name )
        # Skip any branch length after the label
        while label_end < len( working_newick ) and working_newick[ label_end ] not in ',);':
            label_end += 1

        subtree = working_newick[ open_paren_position:label_end ]
        return subtree
    else:
        # Leaf node: subtree is just the label (possibly with branch length)
        label_end = target_position + len( target_clade_id_name )
        while label_end < len( working_newick ) and working_newick[ label_end ] not in ',);':
            label_end += 1
        subtree = working_newick[ target_position:label_end ]
        return subtree


# ============================================================================
# Main Script
# ============================================================================

args = parse_arguments()
workflow_dir = Path( args.workflow_dir )

# Read config
config_path = workflow_dir / 'START_HERE-user_config.yaml'
with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

species_set_name = config[ 'species_set_name' ]

# Paths
output_pipeline_dir = workflow_dir / config[ 'output' ][ 'base_dir' ]
input_dir_2 = output_pipeline_dir / '2-output'
input_dir_4 = output_pipeline_dir / '4-output'
input_dir_6 = output_pipeline_dir / '6-output'
output_dir = output_pipeline_dir / '7-output'
output_dir.mkdir( parents=True, exist_ok=True )

output_integrated_clade_data = output_dir / '7_ai-integrated_clade_data-all_structures.tsv'

print( "=" * 80 )
print( "SCRIPT 007: Integrate All Clade Data" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print()


# ============================================================================
# STEP 1: Read Topology Permutations (2-output)
# ============================================================================

print( "Reading topology permutations from 2-output..." )

input_topologies_path = input_dir_2 / '2_ai-topology_permutations.tsv'

if not input_topologies_path.exists():
    print( f"CRITICAL ERROR: Topology permutations file not found: {input_topologies_path}" )
    print( "Run script 002 first." )
    sys.exit( 1 )

structure_ids___topology_newicks = {}

# Structure_ID (topology structure identifier)	Topology_Newick (newick string with semicolon)	Newick_Structure (newick string without semicolon)
# structure_001	((((Bilateria,Cnidaria),Placozoa),Porifera),Ctenophora);	((((Bilateria,Cnidaria),Placozoa),Porifera),Ctenophora)
with open( input_topologies_path, 'r' ) as input_file:
    header = input_file.readline()

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )
        structure_id = parts[ 0 ]
        topology_newick = parts[ 1 ]

        structure_ids___topology_newicks[ structure_id ] = topology_newick

print( f"  Loaded {len( structure_ids___topology_newicks )} topology permutations" )
print()


# ============================================================================
# STEP 2: Read Clade Registry (4-output)
# ============================================================================

print( "Reading clade registry from 4-output..." )

input_clade_registry_path = input_dir_4 / '4_ai-clade_registry.tsv'

if not input_clade_registry_path.exists():
    print( f"CRITICAL ERROR: Clade registry file not found: {input_clade_registry_path}" )
    print( "Run script 004 first." )
    sys.exit( 1 )

# Build a lookup: clade_id -> { clade_name, clade_id_name, appears_in_structures }
clade_ids___registry_data = {}

# Clade_ID (clade identifier)	Clade_Name (clade name after identifier prefix)	Clade_ID_Name (full clade identifier and name)	Appears_In_Structures (comma delimited list of structures containing this clade)	Newick_Structure (newick subtree for this clade)
# C001	Fonticula_alba	C001_Fonticula_alba	structure_001,structure_002,...	C001_Fonticula_alba
with open( input_clade_registry_path, 'r' ) as input_file:
    header = input_file.readline()

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )
        clade_id = parts[ 0 ]
        clade_name = parts[ 1 ]
        clade_id_name = parts[ 2 ]
        appears_in_structures = parts[ 3 ] if len( parts ) > 3 else ''

        clade_ids___registry_data[ clade_id ] = {
            'clade_name': clade_name,
            'clade_id_name': clade_id_name,
            'appears_in_structures': appears_in_structures
        }

print( f"  Loaded {len( clade_ids___registry_data )} clades from registry" )
print()


# ============================================================================
# STEP 3: Read Complete Tree Newicks and Extract All Clade Paths
# ============================================================================

print( "Reading complete tree Newick files from 4-output/newick_trees/..." )
print( "  (Parsing all clades with phylogenetic paths from Newick trees directly)" )

newick_trees_dir = input_dir_4 / 'newick_trees'

if not newick_trees_dir.exists():
    print( f"CRITICAL ERROR: Newick trees directory not found: {newick_trees_dir}" )
    print( "Run script 004 first." )
    sys.exit( 1 )

structure_ids___complete_newicks = {}
# This replaces reading the paths file since 004 only has species paths
# We need ALL clades (internal + leaf) so we parse the trees directly
structure_clade_pairs___path_data = {}

# RUN_2 optimization: store parsed tree per structure + clade_id_name->node lookup.
# Avoids O(L) string-search in the inner loop (extract_clade_subtree_newick).
structure_clade_id_names___nodes = {}

newick_files = sorted( newick_trees_dir.glob( '*.newick' ) )

if not newick_files:
    print( f"CRITICAL ERROR: No .newick files found in {newick_trees_dir}" )
    sys.exit( 1 )

for newick_file in newick_files:
    filename = newick_file.stem
    structure_id_match = re.search( r'(structure_\d{3})', filename )

    if structure_id_match:
        structure_id = structure_id_match.group( 1 )

        with open( newick_file, 'r' ) as input_file:
            newick_content = input_file.read().strip()

        structure_ids___complete_newicks[ structure_id ] = newick_content

        # Parse the tree and extract all clades with paths
        tree_root = parse_newick_tree( newick_content )
        all_clades_with_paths = extract_all_clades_with_paths( tree_root )

        for clade_data in all_clades_with_paths:
            clade_id = clade_data[ 'clade_id' ]
            structure_clade_pairs___path_data[ ( structure_id, clade_id ) ] = {
                'clade_name': clade_data[ 'clade_name' ],
                'clade_id_name': clade_data[ 'clade_id_name' ],
                'clade_type': clade_data[ 'clade_type' ],
                'phylogenetic_path': clade_data[ 'phylogenetic_path' ]
            }

        # RUN_2 optimization: build (structure_id, clade_id_name) -> node lookup
        # for fast subtree extraction in the inner loop below.
        def _build_node_lookup( node ):
            if node.label:
                structure_clade_id_names___nodes[ ( structure_id, node.label ) ] = node
            for child in node.children:
                _build_node_lookup( child )
        _build_node_lookup( tree_root )

print( f"  Loaded {len( structure_ids___complete_newicks )} complete tree Newick files" )
print( f"  Extracted {len( structure_clade_pairs___path_data )} (structure, clade) path entries" )
print()


# RUN_2 optimization: precompute species-tree-level newick conversions ONCE per
# structure. These are constant per structure but were previously recomputed
# inside the per-(structure,clade) loop below — i.e. ~150x per structure x 105
# structures = ~15,750 redundant regex passes over 10KB strings. Doing them
# once collapses that to 105 calls per conversion.
print( "Pre-computing per-structure species tree conversions..." )
structure_ids___species_tree_conversions = {}
for structure_id, complete_newick in structure_ids___complete_newicks.items():
    structure_ids___species_tree_conversions[ structure_id ] = {
        'structure_only': convert_newick_to_structure_only( complete_newick ),
        'ids_only': convert_newick_to_ids_only( complete_newick ),
        'names_only': convert_newick_to_names_only( complete_newick ),
        'ids_and_names': convert_newick_to_ids_and_names( complete_newick ),
    }
print( f"  Pre-computed conversions for {len( structure_ids___species_tree_conversions )} structures" )
print()


# ============================================================================
# STEP 4: Read Phylogenetic Blocks (6-output)
# ============================================================================

print( "Reading phylogenetic blocks from 6-output..." )

# The combined blocks file has the count embedded in the name:
# 6_ai-phylogenetic_blocks-all_{N}_structures.tsv
# Use glob to find it dynamically
phylogenetic_blocks_files = sorted( input_dir_6.glob( '6_ai-phylogenetic_blocks-all_*_structures.tsv' ) )

if not phylogenetic_blocks_files:
    print( f"CRITICAL ERROR: No combined phylogenetic blocks file found in {input_dir_6}" )
    print( "  Expected pattern: 6_ai-phylogenetic_blocks-all_*_structures.tsv" )
    print( "Run script 006 first." )
    sys.exit( 1 )

input_phylogenetic_blocks_path = phylogenetic_blocks_files[ 0 ]
print( f"  Using: {input_phylogenetic_blocks_path.name}" )

# Build a lookup: (structure_id, clade_id) -> { block_id, block_name, block_id_name }
structure_clade_pairs___phylogenetic_blocks = {}

# Structure_ID (tree topology structure identifier)	Clade_ID (clade identifier for the child in this block)	Clade_Name (clade name for the child in this block)	Clade_ID_Name (full child clade identifier and name)	Parent_Clade_ID (clade identifier for the parent in this block)	Parent_Clade_Name (clade name for the parent in this block)	Parent_Clade_ID_Name (full parent clade identifier and name)	Phylogenetic_Block_Name (block name as Parent_Name::Child_Name)	Phylogenetic_Block_ID (block identifier as Parent_ID::Child_ID)	Phylogenetic_Block_ID_Name (block as Parent_ID_Name::Child_ID_Name)
# structure_001	C068	Root	C068_Root	C000	Pre_Root	C000_Pre_Root	Pre_Root::Root	C000::C068	C000_Pre_Root::C068_Root
with open( input_phylogenetic_blocks_path, 'r' ) as input_file:
    header_line = input_file.readline().strip()
    header_columns = header_line.split( '\t' )

    # Map column names to indices
    column_names___indices = {}
    for column_index, column_header in enumerate( header_columns ):
        # Extract the identifier part before the parenthesized description
        column_name = column_header.split( '(' )[ 0 ].strip()
        column_names___indices[ column_name ] = column_index

    # Identify the key column indices
    structure_id_column_index = column_names___indices.get( 'Structure_ID', 0 )
    clade_id_column_index = column_names___indices.get( 'Clade_ID', 1 )
    block_id_column_index = column_names___indices.get( 'Phylogenetic_Block_ID', None )
    block_name_column_index = column_names___indices.get( 'Phylogenetic_Block_Name', None )
    block_id_name_column_index = column_names___indices.get( 'Phylogenetic_Block_ID_Name', None )

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )

        structure_id = parts[ structure_id_column_index ] if structure_id_column_index is not None else ''
        clade_id = parts[ clade_id_column_index ] if clade_id_column_index is not None else ''
        block_id = parts[ block_id_column_index ] if block_id_column_index is not None and len( parts ) > block_id_column_index else ''
        block_name = parts[ block_name_column_index ] if block_name_column_index is not None and len( parts ) > block_name_column_index else ''
        block_id_name = parts[ block_id_name_column_index ] if block_id_name_column_index is not None and len( parts ) > block_id_name_column_index else ''

        if structure_id and clade_id:
            structure_clade_pairs___phylogenetic_blocks[ ( structure_id, clade_id ) ] = {
                'block_id': block_id,
                'block_name': block_name,
                'block_id_name': block_id_name
            }

print( f"  Loaded {len( structure_clade_pairs___phylogenetic_blocks )} phylogenetic block entries" )
print()


# ============================================================================
# STEP 5: Build Integrated Table
# ============================================================================

print( "Building integrated clade data table..." )

# Use all (structure_id, clade_id) pairs from the parsed Newick trees
all_structure_clade_pairs = set( structure_clade_pairs___path_data.keys() )

print( f"  Total (structure, clade) pairs to integrate: {len( all_structure_clade_pairs )}" )

# Sort pairs for consistent output: by structure_id then clade_id (numeric)
def sort_key_structure_clade( pair ):
    """Sort by structure number, then clade number."""
    structure_id, clade_id = pair
    structure_number = int( re.search( r'\d+', structure_id ).group() ) if re.search( r'\d+', structure_id ) else 0
    clade_number = int( clade_id[ 1: ] ) if clade_id.startswith( 'C' ) and clade_id[ 1: ].isdigit() else 99999
    return ( structure_number, clade_number )

sorted_pairs = sorted( all_structure_clade_pairs, key=sort_key_structure_clade )

# Build output rows
integrated_rows = []
clade_type_counts = { 'species': 0, 'internal': 0, 'unknown': 0 }

for structure_id, clade_id in sorted_pairs:

    # --- Basic Clade Info from Registry ---
    registry_data = clade_ids___registry_data.get( clade_id, {} )
    appears_in_structures = registry_data.get( 'appears_in_structures', '' )

    # --- Clade Info from Parsed Tree ---
    path_data = structure_clade_pairs___path_data.get( ( structure_id, clade_id ), {} )
    clade_name = path_data.get( 'clade_name', registry_data.get( 'clade_name', '' ) )
    clade_id_name = path_data.get( 'clade_id_name', registry_data.get( 'clade_id_name', f"{clade_id}_{clade_name}" if clade_name else clade_id ) )
    clade_type = path_data.get( 'clade_type', 'unknown' )
    phylogenetic_path = path_data.get( 'phylogenetic_path', '' )
    clade_type_counts[ clade_type ] = clade_type_counts.get( clade_type, 0 ) + 1

    # --- Parent Clade Info (from phylogenetic path) ---
    parent_clade_id = ''
    parent_clade_name = ''
    parent_clade_id_name = ''

    if phylogenetic_path:
        path_elements = phylogenetic_path.split( ',' )
        # The current clade is the last element; the parent is the second-to-last
        if len( path_elements ) >= 2:
            parent_clade_id_name = path_elements[ -2 ]
            if '_' in parent_clade_id_name and parent_clade_id_name[ 0 ] == 'C':
                parts_parent = parent_clade_id_name.split( '_', 1 )
                parent_clade_id = parts_parent[ 0 ]
                parent_clade_name = parts_parent[ 1 ]

    # --- Phylogenetic Block Info ---
    block_data = structure_clade_pairs___phylogenetic_blocks.get( ( structure_id, clade_id ), {} )
    phylogenetic_block_id = block_data.get( 'block_id', '' )
    phylogenetic_block_name = block_data.get( 'block_name', '' )
    phylogenetic_block_id_name = block_data.get( 'block_id_name', '' )

    # --- Clade ID or Structure Columns ---
    clade_id_or_structure = f"{clade_id}|{structure_id}"
    clade_name_or_structure = f"{clade_name}|{structure_id}" if clade_name else f"|{structure_id}"
    clade_id_name_or_structure = f"{clade_id_name}|{structure_id}" if clade_id_name else f"|{structure_id}"

    # --- Clade Newick Representations ---
    # RUN_2 optimization: O(1) node lookup + O(N) tree-walk (node.to_newick())
    # replaces the previous O(L) string-search via extract_clade_subtree_newick().
    clade_newick_ids_only = ''
    clade_newick_names_only = ''
    clade_newick_ids_and_names = ''

    clade_node = structure_clade_id_names___nodes.get( ( structure_id, clade_id_name ) )
    if clade_node is not None:
        clade_subtree = clade_node.to_newick()
        if clade_subtree:
            clade_newick_ids_only = convert_newick_to_ids_only( clade_subtree )
            clade_newick_names_only = convert_newick_to_names_only( clade_subtree )
            clade_newick_ids_and_names = convert_newick_to_ids_and_names( clade_subtree )

    # --- Species Tree Representations ---
    # RUN_2 optimization: pull from per-structure pre-computed cache instead of
    # re-running the regex conversions on every (structure, clade) row.
    species_tree_data = structure_ids___species_tree_conversions.get( structure_id, {} )
    species_tree_structure_only = species_tree_data.get( 'structure_only', '' )
    species_tree_ids_only = species_tree_data.get( 'ids_only', '' )
    species_tree_names_only = species_tree_data.get( 'names_only', '' )
    species_tree_ids_and_names = species_tree_data.get( 'ids_and_names', '' )

    # --- Topology Newick ---
    topology_newick = structure_ids___topology_newicks.get( structure_id, '' )

    # --- Build Row ---
    row = {
        'Structure_ID': structure_id,
        'Clade_ID': clade_id,
        'Clade_Name': clade_name,
        'Clade_ID_Name': clade_id_name,
        'Clade_Type': clade_type,
        'Parent_Clade_ID': parent_clade_id,
        'Parent_Clade_Name': parent_clade_name,
        'Parent_Clade_ID_Name': parent_clade_id_name,
        'Phylogenetic_Block_ID': phylogenetic_block_id,
        'Phylogenetic_Block_Name': phylogenetic_block_name,
        'Phylogenetic_Block_ID_Name': phylogenetic_block_id_name,
        'Phylogenetic_Path': phylogenetic_path,
        'Clade_ID_Or_Structure': clade_id_or_structure,
        'Clade_Name_Or_Structure': clade_name_or_structure,
        'Clade_ID_Name_Or_Structure': clade_id_name_or_structure,
        'Clade_Newick_IDs_Only': clade_newick_ids_only,
        'Clade_Newick_Names_Only': clade_newick_names_only,
        'Clade_Newick_IDs_And_Names': clade_newick_ids_and_names,
        'Species_Tree_Structure_Only': species_tree_structure_only,
        'Species_Tree_IDs_Only': species_tree_ids_only,
        'Species_Tree_Names_Only': species_tree_names_only,
        'Species_Tree_IDs_And_Names': species_tree_ids_and_names,
        'Topology_Newick': topology_newick,
        'Appears_In_Structures': appears_in_structures
    }

    integrated_rows.append( row )

print( f"  Built {len( integrated_rows )} integrated rows" )
print( f"  Clade types: species={clade_type_counts.get( 'species', 0 )}, internal={clade_type_counts.get( 'internal', 0 )}, unknown={clade_type_counts.get( 'unknown', 0 )}" )
print()


# ============================================================================
# STEP 6: Write Output
# ============================================================================

print( "Writing integrated clade data table..." )

# Define column order with self-documenting headers
column_headers = [
    'Structure_ID (topology structure identifier)',
    'Clade_ID (clade identifier)',
    'Clade_Name (clade name after identifier prefix)',
    'Clade_ID_Name (full clade identifier and name)',
    'Clade_Type (species for leaf nodes or internal for non-leaf nodes)',
    'Parent_Clade_ID (parent clade identifier)',
    'Parent_Clade_Name (parent clade name)',
    'Parent_Clade_ID_Name (full parent clade identifier and name)',
    'Phylogenetic_Block_ID (phylogenetic block identifier for parent to child transition)',
    'Phylogenetic_Block_Name (phylogenetic block name for parent to child transition)',
    'Phylogenetic_Block_ID_Name (full phylogenetic block identifier and name)',
    'Phylogenetic_Path (comma delimited root to node path of clade id names)',
    'Clade_ID_Or_Structure (clade identifier pipe structure identifier for unique key)',
    'Clade_Name_Or_Structure (clade name pipe structure identifier)',
    'Clade_ID_Name_Or_Structure (full clade identifier and name pipe structure identifier)',
    'Clade_Newick_IDs_Only (newick subtree of this clade with only clade identifiers)',
    'Clade_Newick_Names_Only (newick subtree of this clade with only clade names)',
    'Clade_Newick_IDs_And_Names (newick subtree of this clade with identifiers and names)',
    'Species_Tree_Structure_Only (full species tree newick with only branching structure)',
    'Species_Tree_IDs_Only (full species tree newick with only clade identifiers)',
    'Species_Tree_Names_Only (full species tree newick with only clade names)',
    'Species_Tree_IDs_And_Names (full species tree newick with identifiers and names)',
    'Topology_Newick (topology permutation newick string with semicolon)',
    'Appears_In_Structures (comma delimited list of structures containing this clade)'
]

column_keys = [
    'Structure_ID', 'Clade_ID', 'Clade_Name', 'Clade_ID_Name', 'Clade_Type',
    'Parent_Clade_ID', 'Parent_Clade_Name', 'Parent_Clade_ID_Name',
    'Phylogenetic_Block_ID', 'Phylogenetic_Block_Name', 'Phylogenetic_Block_ID_Name',
    'Phylogenetic_Path', 'Clade_ID_Or_Structure', 'Clade_Name_Or_Structure',
    'Clade_ID_Name_Or_Structure', 'Clade_Newick_IDs_Only', 'Clade_Newick_Names_Only',
    'Clade_Newick_IDs_And_Names', 'Species_Tree_Structure_Only', 'Species_Tree_IDs_Only',
    'Species_Tree_Names_Only', 'Species_Tree_IDs_And_Names', 'Topology_Newick',
    'Appears_In_Structures'
]

with open( output_integrated_clade_data, 'w' ) as output_file:
    # Write header
    header_output = '\t'.join( column_headers ) + '\n'
    output_file.write( header_output )

    # Write data rows
    for row in integrated_rows:
        values = [ str( row.get( key, '' ) ) for key in column_keys ]
        output = '\t'.join( values ) + '\n'
        output_file.write( output )

print( f"  {output_integrated_clade_data.name}" )
print()

# Summary statistics
unique_structures = set()
unique_clades = set()
for row in integrated_rows:
    unique_structures.add( row[ 'Structure_ID' ] )
    unique_clades.add( row[ 'Clade_ID' ] )

print( "=" * 80 )
print( "SCRIPT 007 COMPLETE" )
print( "=" * 80 )
print()
print( f"Total integrated rows: {len( integrated_rows )}" )
print( f"Unique structures: {len( unique_structures )}" )
print( f"Unique clades: {len( unique_clades )}" )
print( f"Columns: {len( column_headers )}" )
print()
print( f"Output file:" )
print( f"  {output_integrated_clade_data.name}" )
print()
print( "Next step: Run script 008 to visualize species trees" )
print()
