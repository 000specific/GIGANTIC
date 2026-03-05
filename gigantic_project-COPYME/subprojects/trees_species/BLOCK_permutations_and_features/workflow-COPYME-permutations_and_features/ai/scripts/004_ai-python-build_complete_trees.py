#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Build complete species trees by grafting clade subtrees onto topology skeletons
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 004: Build Complete Species Trees

Purpose:
    Build complete species trees by grafting the full unresolved clade subtrees
    onto the annotated topology skeletons produced by Script 003.

    Each annotated topology skeleton from Script 003 contains only the unresolved
    clade names as leaves (e.g., Ctenophora, Porifera, Placozoa, Cnidaria, Bilateria)
    with clade IDs on internal nodes (e.g., C069_Clade_069). This script replaces
    each unresolved clade leaf with its full subtree from the original species tree,
    then grafts the result into the fixed structure (everything outside the variable
    root) to produce a complete annotated species tree for each topology structure.

    Strategy:
    1. Parse the original annotated species tree (with CXXX_Name:1.0 labels)
    2. Identify the variable root node (common ancestor of all unresolved clades)
    3. Extract each unresolved clade's full subtree (preserving internal clade IDs)
    4. Extract the fixed structure (everything outside the variable root) with a
       placeholder stub for the variable root node
    5. For each annotated topology skeleton from Script 003:
       a. Parse the skeleton (already has clade IDs for intermediate nodes)
       b. Find each unresolved clade leaf and replace it with the full subtree
       c. For structure_001: extract the variable root subtree from the full
          annotated skeleton (since structure_001 IS the original tree)
       d. For structures 002+: the skeleton IS the variable root subtree after
          grafting the unresolved clade subtrees
       e. Replace the variable root stub in fixed structure with the topology-
          specific subtree
       f. Generate the complete annotated Newick tree
    6. Build a registry of all clade IDs and which structures they appear in
    7. Generate phylogenetic paths for all species in all structures

    When 0 unresolved clades are specified (single tree mode), the original tree
    is output directly with no grafting.

Inputs:
    --workflow-dir: Workflow root directory
    Reads: OUTPUT_pipeline/1-output/ (metadata with variable_root_label)
           OUTPUT_pipeline/3-output/newick_trees/ (annotated topology skeletons)
           INPUT_user/species_tree.newick (original annotated species tree)
           START_HERE-user_config.yaml

Outputs:
    OUTPUT_pipeline/4-output/4_ai-clade_registry.tsv
    OUTPUT_pipeline/4-output/4_ai-phylogenetic_paths-all_structures.tsv
    OUTPUT_pipeline/4-output/newick_trees/4_ai-structure_XXX_complete_tree.newick
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import argparse
import sys
import re
import yaml
import copy


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 004: Build complete species trees by grafting clade subtrees onto topology skeletons' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    return parser.parse_args()


# ============================================================================
# NewickNode Class
# ============================================================================

class NewickNode:
    """
    Represents a node in a Newick phylogenetic tree.

    Attributes:
        label: Node label in CXXX_Name format (e.g., C001_Bilateria)
        branch_length: Branch length as string (e.g., '1.0')
        children: List of child NewickNode objects
        parent: Parent NewickNode or None for root
    """

    def __init__( self, label: str = '', branch_length: str = '1.0' ):
        self.label = label
        self.branch_length = branch_length
        self.children: List[ 'NewickNode' ] = []
        self.parent: Optional[ 'NewickNode' ] = None

    def add_child( self, child: 'NewickNode' ):
        """Add a child node and set its parent reference."""
        self.children.append( child )
        child.parent = self

    def is_leaf( self ) -> bool:
        """Check if this node is a leaf (no children)."""
        return len( self.children ) == 0

    def find_clade( self, target_label: str ) -> Optional[ 'NewickNode' ]:
        """
        Find a node by its exact label.

        Args:
            target_label: The full label to match (e.g., 'C001_Bilateria')

        Returns:
            The matching NewickNode or None if not found.
        """
        if self.label == target_label:
            return self
        for child in self.children:
            result = child.find_clade( target_label )
            if result is not None:
                return result
        return None

    def find_by_clade_name( self, target_name: str ) -> Optional[ 'NewickNode' ]:
        """
        Find a node by its clade name (the part after CXXX_).

        Args:
            target_name: The clade name to match (e.g., 'Bilateria')

        Returns:
            The matching NewickNode or None if not found.
        """
        if self.label and '_' in self.label:
            parts_label = self.label.split( '_', 1 )
            if parts_label[ 1 ] == target_name:
                return self
        for child in self.children:
            result = child.find_by_clade_name( target_name )
            if result is not None:
                return result
        return None

    def extract_subtree( self ) -> 'NewickNode':
        """
        Create a deep copy of this node and its entire subtree.
        The copy has no parent (it becomes a new root).

        Returns:
            A new NewickNode that is a deep copy of this subtree.
        """
        new_node = NewickNode( self.label, self.branch_length )
        for child in self.children:
            child_copy = child.extract_subtree()
            new_node.add_child( child_copy )
        return new_node

    def replace_child( self, old_child: 'NewickNode', new_child: 'NewickNode' ):
        """
        Replace an existing child node with a new child node.

        Args:
            old_child: The child to replace
            new_child: The replacement child
        """
        for i in range( len( self.children ) ):
            if self.children[ i ] is old_child:
                self.children[ i ] = new_child
                new_child.parent = self
                old_child.parent = None
                return
        print( f"  WARNING: Could not find child to replace (label: {old_child.label})" )

    def get_all_leaf_labels( self ) -> List[ str ]:
        """
        Get all leaf labels in this subtree.

        Returns:
            List of label strings from all leaf nodes.
        """
        if self.is_leaf():
            return [ self.label ] if self.label else []
        labels = []
        for child in self.children:
            labels.extend( child.get_all_leaf_labels() )
        return labels

    def get_all_clade_ids( self ) -> List[ Tuple[ str, str, str ] ]:
        """
        Get all clade IDs in this subtree.

        Returns:
            List of tuples: (clade_id, clade_name, clade_id_name)
            Only includes nodes with labels in CXXX_Name format.
        """
        clades = []

        if self.label and '_' in self.label:
            parts_label = self.label.split( '_', 1 )
            clade_id = parts_label[ 0 ]
            clade_name = parts_label[ 1 ]
            clade_id_name = self.label
            # Only include if clade_id matches the CXXX pattern
            if re.match( r'^C\d+$', clade_id ):
                clades.append( ( clade_id, clade_name, clade_id_name ) )

        for child in self.children:
            clades.extend( child.get_all_clade_ids() )

        return clades

    def get_path_to_root( self ) -> List[ str ]:
        """
        Get the phylogenetic path from this node to the root.

        Returns:
            List of labels from this node up to the root.
        """
        path = []
        current = self
        while current is not None:
            if current.label:
                path.append( current.label )
            current = current.parent
        return path

    def to_newick( self ) -> str:
        """
        Convert this node and its subtree to Newick format string.

        Format: For internal nodes with children: (child1,child2,...)label:branch_length
                For leaf nodes: label:branch_length

        Returns:
            Newick format string (without trailing semicolon).
        """
        if self.is_leaf():
            if self.label and self.branch_length:
                return f"{self.label}:{self.branch_length}"
            elif self.label:
                return self.label
            else:
                return ''

        children_newicks = []
        for child in self.children:
            children_newicks.append( child.to_newick() )

        newick = f"({','.join( children_newicks )})"

        if self.label and self.branch_length:
            newick += f"{self.label}:{self.branch_length}"
        elif self.label:
            newick += self.label

        return newick


# ============================================================================
# Newick Parsing Functions
# ============================================================================

def parse_label_and_length( token: str ) -> Tuple[ str, str ]:
    """
    Parse a label and branch length from a Newick token.

    Args:
        token: String that may contain 'label:length' or just 'label'

    Returns:
        Tuple of (label, branch_length). Default branch_length is '1.0'.
    """
    if ':' in token:
        parts_token = token.split( ':', 1 )
        return ( parts_token[ 0 ], parts_token[ 1 ] )
    else:
        return ( token, '1.0' )


def parse_newick( newick_string: str ) -> NewickNode:
    """
    Parse a Newick string with labeled internal nodes and branch lengths.

    Handles the format: ((leaf1:1.0,leaf2:1.0)internal:1.0,...)root:1.0;
    where internal nodes have labels in CXXX_Name format.

    Args:
        newick_string: Complete Newick string (may include trailing semicolon)

    Returns:
        The root NewickNode of the parsed tree.
    """
    newick_string = newick_string.strip()
    if newick_string.endswith( ';' ):
        newick_string = newick_string[ :-1 ]

    stack = [ NewickNode() ]
    i = 0
    current_token = ''

    while i < len( newick_string ):
        char = newick_string[ i ]

        if char == '(':
            new_node = NewickNode()
            stack[ -1 ].add_child( new_node )
            stack.append( new_node )
            current_token = ''

        elif char == ',':
            if current_token:
                label, branch_length = parse_label_and_length( current_token )
                child = NewickNode( label, branch_length )
                stack[ -1 ].add_child( child )
                current_token = ''

        elif char == ')':
            if current_token:
                label, branch_length = parse_label_and_length( current_token )
                child = NewickNode( label, branch_length )
                stack[ -1 ].add_child( child )
                current_token = ''

            finished_node = stack.pop()

            # Consume the label:length that follows the closing parenthesis
            i += 1
            label_and_length = ''
            while i < len( newick_string ) and newick_string[ i ] not in '(),;':
                label_and_length += newick_string[ i ]
                i += 1

            if label_and_length:
                label, branch_length = parse_label_and_length( label_and_length )
                finished_node.label = label
                finished_node.branch_length = branch_length

            i -= 1  # Back up one since the main loop will increment

        else:
            current_token += char

        i += 1

    # The stack[0] is the wrapper root - if it has exactly one child, return that child
    if len( stack[ 0 ].children ) == 1:
        actual_root = stack[ 0 ].children[ 0 ]
        actual_root.parent = None
        return actual_root

    return stack[ 0 ]


def parse_skeleton_newick( newick_string: str ) -> NewickNode:
    """
    Parse an annotated topology skeleton Newick string from Script 003.

    These skeletons have the format: (C001_Bilateria,C002_Cnidaria)C069_Clade_069;
    where leaves are the unresolved clade labels (with their CXXX_ prefix from the
    original tree) and internal nodes have new clade IDs assigned by Script 003.

    No branch lengths in skeleton format.

    Args:
        newick_string: Skeleton Newick string

    Returns:
        The root NewickNode of the parsed skeleton tree.
    """
    newick_string = newick_string.strip()
    if newick_string.endswith( ';' ):
        newick_string = newick_string[ :-1 ]

    stack = [ NewickNode() ]
    i = 0
    current_token = ''

    while i < len( newick_string ):
        char = newick_string[ i ]

        if char == '(':
            new_node = NewickNode()
            stack[ -1 ].add_child( new_node )
            stack.append( new_node )
            current_token = ''

        elif char == ',':
            if current_token:
                label = current_token.strip()
                # Skeleton leaves have labels like C001_Bilateria (no branch lengths)
                child = NewickNode( label, '1.0' )
                stack[ -1 ].add_child( child )
                current_token = ''

        elif char == ')':
            if current_token:
                label = current_token.strip()
                child = NewickNode( label, '1.0' )
                stack[ -1 ].add_child( child )
                current_token = ''

            finished_node = stack.pop()

            # Consume the internal node label that follows the closing parenthesis
            i += 1
            internal_label = ''
            while i < len( newick_string ) and newick_string[ i ] not in '(),;':
                internal_label += newick_string[ i ]
                i += 1

            if internal_label.strip():
                finished_node.label = internal_label.strip()
                finished_node.branch_length = '1.0'

            i -= 1

        else:
            current_token += char

        i += 1

    # Return the actual tree (unwrap the dummy root if needed)
    if len( stack[ 0 ].children ) == 1:
        actual_root = stack[ 0 ].children[ 0 ]
        actual_root.parent = None
        return actual_root

    return stack[ 0 ]


# ============================================================================
# Tree Manipulation Functions
# ============================================================================

def find_common_ancestor( node: NewickNode, target_names: Set[ str ] ) -> Optional[ NewickNode ]:
    """
    Find the lowest common ancestor of nodes matching any of the target clade names.

    Target names are matched against the clade name portion (after CXXX_).

    Args:
        node: Root of the tree to search
        target_names: Set of clade names to find (e.g., {'Bilateria', 'Cnidaria'})

    Returns:
        The NewickNode that is the lowest common ancestor, or None.
    """
    if not target_names:
        return None

    # Find all target nodes
    target_nodes = []
    for target_name in target_names:
        found_node = node.find_by_clade_name( target_name )
        if found_node:
            target_nodes.append( found_node )

    if not target_nodes:
        return None

    if len( target_nodes ) == 1:
        return target_nodes[ 0 ].parent if target_nodes[ 0 ].parent else target_nodes[ 0 ]

    # Get ancestor chains for all target nodes
    def get_ancestors( n: NewickNode ) -> List[ NewickNode ]:
        """Get list of ancestors from node to root."""
        ancestors = []
        current = n
        while current is not None:
            ancestors.append( current )
            current = current.parent
        return ancestors

    # Find deepest common ancestor
    first_ancestors = get_ancestors( target_nodes[ 0 ] )

    for ancestor in first_ancestors:
        is_common = True
        for other_node in target_nodes[ 1: ]:
            other_ancestors = get_ancestors( other_node )
            if ancestor not in other_ancestors:
                is_common = False
                break
        if is_common:
            return ancestor

    return None


def extract_fixed_structure_with_stub( root: NewickNode, variable_root_label: str ) -> NewickNode:
    """
    Create a deep copy of the tree with the variable root subtree replaced
    by a single stub node (a leaf with the variable root label).

    Args:
        root: Root of the full species tree
        variable_root_label: Label of the variable root node (e.g., 'C068_Basal')

    Returns:
        A new NewickNode tree where the variable root subtree has been
        replaced with a leaf stub node.
    """
    if root.label == variable_root_label:
        # The entire tree is the variable region - return a stub
        return NewickNode( variable_root_label, root.branch_length )

    new_node = NewickNode( root.label, root.branch_length )
    for child in root.children:
        if child.label == variable_root_label:
            # Replace this child's subtree with a stub leaf
            stub = NewickNode( variable_root_label, child.branch_length )
            new_node.add_child( stub )
        else:
            child_copy = extract_fixed_structure_with_stub( child, variable_root_label )
            new_node.add_child( child_copy )

    return new_node


def graft_subtrees_onto_skeleton( skeleton_root: NewickNode, unresolved_clade_subtrees: Dict[ str, NewickNode ] ) -> NewickNode:
    """
    Replace each unresolved clade leaf in the skeleton with its full subtree.

    Args:
        skeleton_root: Root of the topology skeleton from Script 003
        unresolved_clade_subtrees: Dictionary mapping clade_id_name (e.g., 'C001_Bilateria')
                                    to the full NewickNode subtree for that clade

    Returns:
        The modified skeleton with unresolved clade leaves replaced by full subtrees.
    """
    # Process leaves: if a leaf matches an unresolved clade, replace it
    if skeleton_root.is_leaf():
        if skeleton_root.label in unresolved_clade_subtrees:
            # Replace this leaf with a copy of the full subtree
            subtree_copy = unresolved_clade_subtrees[ skeleton_root.label ].extract_subtree()
            # Preserve the branch length from the skeleton
            subtree_copy.branch_length = skeleton_root.branch_length
            return subtree_copy
        else:
            # Not an unresolved clade leaf - return as-is (copy)
            return NewickNode( skeleton_root.label, skeleton_root.branch_length )

    # For internal nodes, recursively process children
    new_node = NewickNode( skeleton_root.label, skeleton_root.branch_length )
    for child in skeleton_root.children:
        grafted_child = graft_subtrees_onto_skeleton( child, unresolved_clade_subtrees )
        new_node.add_child( grafted_child )

    return new_node


def build_complete_tree( fixed_structure: NewickNode, variable_root_label: str, variable_root_subtree: NewickNode ) -> NewickNode:
    """
    Build a complete tree by inserting the variable root subtree into the
    fixed structure (replacing the stub node).

    Args:
        fixed_structure: Tree with a stub leaf at the variable root position
        variable_root_label: Label of the variable root node
        variable_root_subtree: The fully grafted variable root subtree

    Returns:
        A new complete tree with the variable root subtree inserted.
    """
    if fixed_structure.is_leaf() and fixed_structure.label == variable_root_label:
        # This is the stub - replace with the full variable root subtree
        complete_subtree = variable_root_subtree.extract_subtree()
        complete_subtree.branch_length = fixed_structure.branch_length
        return complete_subtree

    new_node = NewickNode( fixed_structure.label, fixed_structure.branch_length )
    for child in fixed_structure.children:
        if child.is_leaf() and child.label == variable_root_label:
            # Replace stub with variable root subtree
            complete_subtree = variable_root_subtree.extract_subtree()
            complete_subtree.branch_length = child.branch_length
            new_node.add_child( complete_subtree )
        else:
            child_copy = build_complete_tree( child, variable_root_label, variable_root_subtree )
            new_node.add_child( child_copy )

    return new_node


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
unresolved_clade_names = config[ 'permutation' ][ 'unresolved_clades' ]
input_tree_relative = config[ 'input_files' ][ 'species_tree' ]

# Paths
output_pipeline_dir = workflow_dir / config[ 'output' ][ 'base_dir' ]
input_dir_1 = output_pipeline_dir / '1-output'
input_dir_3 = output_pipeline_dir / '3-output'
output_dir = output_pipeline_dir / '4-output'
output_dir.mkdir( parents=True, exist_ok=True )

output_newick_trees_dir = output_dir / 'newick_trees'
output_newick_trees_dir.mkdir( parents=True, exist_ok=True )

output_clade_registry_path = output_dir / '4_ai-clade_registry.tsv'
output_phylogenetic_paths_path = output_dir / '4_ai-phylogenetic_paths-all_structures.tsv'

print( "=" * 80 )
print( "SCRIPT 004: Build Complete Species Trees" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print( f"Unresolved clades ({len( unresolved_clade_names )}): {', '.join( unresolved_clade_names ) if unresolved_clade_names else 'NONE (single tree mode)'}" )
print()


# ============================================================================
# STEP 1: Read Metadata from Script 001
# ============================================================================

print( "STEP 1: Reading metadata from Script 001..." )

metadata_path = input_dir_1 / '1_ai-tree-metadata.tsv'

if not metadata_path.exists():
    print( f"CRITICAL ERROR: Metadata file not found: {metadata_path}" )
    print( "Script 001 must be run before Script 004." )
    sys.exit( 1 )

# 1_ai-tree-metadata.tsv format (key-value TSV, no header):
# species_set_name	species71
# variable_root_label	C068_Basal
metadata = {}
with open( metadata_path, 'r' ) as input_file:
    for line in input_file:
        line = line.strip()
        if not line:
            continue
        parts = line.split( '\t' )
        metadata_key = parts[ 0 ]
        metadata_value = parts[ 1 ] if len( parts ) > 1 else ''
        metadata[ metadata_key ] = metadata_value

variable_root_label = metadata.get( 'variable_root_label', 'NONE' )

if variable_root_label == 'NONE':
    variable_root_label = None

print( f"  Variable root label: {variable_root_label if variable_root_label else 'NONE (single tree mode)'}" )
print( f"  Unresolved clade count: {metadata.get( 'unresolved_clade_count', '?' )}" )
print( f"  Leaf species count: {metadata.get( 'leaf_species_count', '?' )}" )
print()


# ============================================================================
# STEP 2: Parse Original Annotated Species Tree
# ============================================================================

print( "STEP 2: Parsing original annotated species tree..." )

input_species_tree_path = workflow_dir / input_tree_relative

if not input_species_tree_path.exists():
    print( f"CRITICAL ERROR: Species tree not found: {input_species_tree_path}" )
    print( "Please provide a species tree in INPUT_user/species_tree.newick" )
    sys.exit( 1 )

with open( input_species_tree_path, 'r' ) as input_file:
    original_newick_string = input_file.read().strip()

original_tree_root = parse_newick( original_newick_string )

all_original_leaves = original_tree_root.get_all_leaf_labels()
print( f"  Parsed tree with {len( all_original_leaves )} leaf species" )
print()


# ============================================================================
# STEP 3: Handle Single Tree Mode (0 or 1 unresolved clades)
# ============================================================================

if not unresolved_clade_names or len( unresolved_clade_names ) <= 1 or variable_root_label is None:
    print( "SINGLE TREE MODE: No permutations to process." )
    print( "Outputting original tree as structure_001..." )
    print()

    # Write the single complete tree
    complete_newick = original_tree_root.to_newick()
    newick_tree_file = output_newick_trees_dir / '4_ai-structure_001_complete_tree.newick'
    with open( newick_tree_file, 'w' ) as output_file:
        output_file.write( complete_newick + ';\n' )

    print( f"  Written: {newick_tree_file.name}" )

    # Build clade registry for single structure
    all_clades = original_tree_root.get_all_clade_ids()

    with open( output_clade_registry_path, 'w' ) as output_file:
        output_file.write( 'Clade_ID (clade identifier)\tClade_Name (clade name after identifier prefix)\tClade_ID_Name (full clade identifier and name)\tAppears_In_Structures (comma delimited list of structures containing this clade)\tNewick_Structure (newick subtree for this clade)\n' )

        for clade_id, clade_name, clade_id_name in sorted( all_clades, key=lambda x: int( x[ 0 ][ 1: ] ) if x[ 0 ][ 1: ].isdigit() else 99999 ):
            clade_node = original_tree_root.find_clade( clade_id_name )
            newick_structure = clade_node.to_newick() if clade_node else ''
            output = f"{clade_id}\t{clade_name}\t{clade_id_name}\tstructure_001\t{newick_structure}\n"
            output_file.write( output )

    print( f"  Written: {output_clade_registry_path.name}" )

    # Generate phylogenetic paths for single structure
    with open( output_phylogenetic_paths_path, 'w' ) as output_file:
        output_file.write( 'Structure_ID (topology structure identifier)\tSpecies_Clade_ID_Name (species clade identifier and name)\tSpecies_Name (species name extracted from clade identifier)\tPhylogenetic_Path (comma delimited root to leaf path of clade identifiers)\n' )

        for leaf_label in sorted( all_original_leaves ):
            leaf_node = original_tree_root.find_clade( leaf_label )
            if leaf_node:
                path = leaf_node.get_path_to_root()
                path.reverse()
                phylogenetic_path = ','.join( path )

                # Extract species name from label
                species_name = ''
                if '_' in leaf_label:
                    parts_label = leaf_label.split( '_', 1 )
                    species_name = parts_label[ 1 ]

                output = f"structure_001\t{leaf_label}\t{species_name}\t{phylogenetic_path}\n"
                output_file.write( output )

    print( f"  Written: {output_phylogenetic_paths_path.name}" )
    print()

    print( "=" * 80 )
    print( "SCRIPT 004 COMPLETE (single tree mode)" )
    print( "=" * 80 )
    print()
    print( f"Total complete trees: 1" )
    print( f"Total clades in registry: {len( all_clades )}" )
    print()
    sys.exit( 0 )


# ============================================================================
# STEP 4: Extract Unresolved Clade Subtrees from Original Tree
# ============================================================================

print( "STEP 3: Extracting unresolved clade subtrees from original tree..." )

unresolved_clade_id_names___subtrees = {}

for unresolved_name in unresolved_clade_names:
    clade_node = original_tree_root.find_by_clade_name( unresolved_name )
    if clade_node:
        subtree = clade_node.extract_subtree()
        clade_id_name = clade_node.label
        unresolved_clade_id_names___subtrees[ clade_id_name ] = subtree

        leaf_count = len( subtree.get_all_leaf_labels() )
        print( f"  {clade_id_name}: {leaf_count} leaf species" )
    else:
        print( f"  WARNING: Unresolved clade '{unresolved_name}' not found in tree!" )

if len( unresolved_clade_id_names___subtrees ) != len( unresolved_clade_names ):
    print( f"CRITICAL ERROR: Could not find all unresolved clades in tree!" )
    print( f"  Expected: {len( unresolved_clade_names )}" )
    print( f"  Found: {len( unresolved_clade_id_names___subtrees )}" )
    sys.exit( 1 )

print( f"  Extracted {len( unresolved_clade_id_names___subtrees )} unresolved clade subtrees" )
print()


# ============================================================================
# STEP 5: Extract Fixed Structure with Variable Root Stub
# ============================================================================

print( "STEP 4: Extracting fixed structure with variable root stub..." )

fixed_structure_root = extract_fixed_structure_with_stub( original_tree_root, variable_root_label )

fixed_leaves = fixed_structure_root.get_all_leaf_labels()
fixed_leaf_count = len( fixed_leaves )
has_stub = variable_root_label in fixed_leaves

print( f"  Fixed structure leaves: {fixed_leaf_count}" )
print( f"  Variable root stub present: {has_stub}" )

if not has_stub:
    print( f"  WARNING: Variable root stub '{variable_root_label}' not found in fixed structure!" )
    print( "  This may indicate the variable root is the tree root itself." )

print()


# ============================================================================
# STEP 6: Read Annotated Topology Skeletons from Script 003
# ============================================================================

print( "STEP 5: Reading annotated topology skeletons from Script 003..." )

input_skeleton_trees_dir = input_dir_3 / 'newick_trees'

if not input_skeleton_trees_dir.exists():
    print( f"CRITICAL ERROR: Skeleton trees directory not found: {input_skeleton_trees_dir}" )
    print( "Script 003 must be run before Script 004." )
    sys.exit( 1 )

# Find all skeleton Newick files
skeleton_files = sorted( input_skeleton_trees_dir.glob( '3_ai-structure_*_topology_with_clade_ids.newick' ) )

if not skeleton_files:
    print( f"CRITICAL ERROR: No skeleton Newick files found in {input_skeleton_trees_dir}" )
    sys.exit( 1 )

print( f"  Found {len( skeleton_files )} annotated topology skeleton files" )
print()


# ============================================================================
# STEP 7: Build Complete Trees by Grafting
# ============================================================================

print( "STEP 6: Building complete species trees..." )
print()

# Collect all clade IDs across all structures for the registry
clade_id_names___structures = {}  # clade_id_name -> set of structure_ids
clade_id_names___newick_structures = {}  # clade_id_name -> newick string of subtree

# Collect phylogenetic paths for all species across all structures
all_phylogenetic_paths = []

complete_tree_count = 0

for skeleton_file in skeleton_files:
    # Extract structure_id from filename
    # Filename pattern: 3_ai-structure_XXX_topology_with_clade_ids.newick
    filename_stem = skeleton_file.stem
    structure_id_match = re.search( r'(structure_\d{3})', filename_stem )
    if not structure_id_match:
        print( f"  WARNING: Could not extract structure ID from filename: {skeleton_file.name}" )
        continue

    structure_id = structure_id_match.group( 1 )
    structure_number = int( structure_id.replace( 'structure_', '' ) )

    # Read the skeleton Newick
    with open( skeleton_file, 'r' ) as input_file:
        skeleton_newick_string = input_file.read().strip()

    # Parse the skeleton
    skeleton_root = parse_skeleton_newick( skeleton_newick_string )

    # Graft unresolved clade subtrees onto the skeleton
    grafted_variable_root = graft_subtrees_onto_skeleton( skeleton_root, unresolved_clade_id_names___subtrees )

    # Ensure the grafted variable root has the correct label
    grafted_variable_root.label = variable_root_label

    # Build the complete tree by inserting grafted variable root into fixed structure
    complete_tree_root = build_complete_tree( fixed_structure_root, variable_root_label, grafted_variable_root )

    # Write the complete tree to a Newick file
    complete_newick = complete_tree_root.to_newick()
    output_newick_file = output_newick_trees_dir / f"4_ai-{structure_id}_complete_tree.newick"
    with open( output_newick_file, 'w' ) as output_file:
        output_file.write( complete_newick + ';\n' )

    complete_tree_count += 1

    # Collect clade IDs for the registry
    all_clades_in_structure = complete_tree_root.get_all_clade_ids()

    for clade_id, clade_name, clade_id_name in all_clades_in_structure:
        if clade_id_name not in clade_id_names___structures:
            clade_id_names___structures[ clade_id_name ] = set()
        clade_id_names___structures[ clade_id_name ].add( structure_id )

        # Store the newick structure for this clade (use first occurrence)
        if clade_id_name not in clade_id_names___newick_structures:
            clade_node = complete_tree_root.find_clade( clade_id_name )
            if clade_node:
                clade_id_names___newick_structures[ clade_id_name ] = clade_node.to_newick()

    # Generate phylogenetic paths for all leaf species in this structure
    leaf_labels = complete_tree_root.get_all_leaf_labels()

    for leaf_label in leaf_labels:
        leaf_node = complete_tree_root.find_clade( leaf_label )
        if leaf_node:
            path = leaf_node.get_path_to_root()
            path.reverse()
            phylogenetic_path = ','.join( path )

            # Extract species name from leaf label
            species_name = ''
            if '_' in leaf_label:
                parts_label = leaf_label.split( '_', 1 )
                species_name = parts_label[ 1 ]

            all_phylogenetic_paths.append( ( structure_id, leaf_label, species_name, phylogenetic_path ) )

    # Show progress
    if structure_number <= 10 or structure_number > len( skeleton_files ) - 5:
        leaf_count = len( leaf_labels )
        clade_count = len( all_clades_in_structure )
        display_newick = complete_newick if len( complete_newick ) <= 120 else complete_newick[ :117 ] + '...'
        print( f"  {structure_id}: {leaf_count} leaves, {clade_count} clades" )
    elif structure_number == 11:
        print( f"  ... (structures 011-{len( skeleton_files ) - 5:03d}) ..." )

print()
print( f"  Built {complete_tree_count} complete species trees" )
print()


# ============================================================================
# STEP 8: Write Clade Registry
# ============================================================================

print( "STEP 7: Writing clade registry..." )

with open( output_clade_registry_path, 'w' ) as output_file:
    output_file.write( 'Clade_ID (clade identifier)\tClade_Name (clade name after identifier prefix)\tClade_ID_Name (full clade identifier and name)\tAppears_In_Structures (comma delimited list of structures containing this clade)\tNewick_Structure (newick subtree for this clade)\n' )

    # Sort by clade number
    sorted_clade_id_names = sorted(
        clade_id_names___structures.keys(),
        key=lambda x: int( x.split( '_', 1 )[ 0 ][ 1: ] ) if x.split( '_', 1 )[ 0 ][ 1: ].isdigit() else 99999
    )

    for clade_id_name in sorted_clade_id_names:
        parts_clade_id_name = clade_id_name.split( '_', 1 )
        clade_id = parts_clade_id_name[ 0 ]
        clade_name = parts_clade_id_name[ 1 ]

        structure_ids = clade_id_names___structures[ clade_id_name ]
        appears_in_structures = ','.join( sorted( structure_ids ) )

        newick_structure = clade_id_names___newick_structures.get( clade_id_name, '' )

        output = f"{clade_id}\t{clade_name}\t{clade_id_name}\t{appears_in_structures}\t{newick_structure}\n"
        output_file.write( output )

total_clades_in_registry = len( clade_id_names___structures )
print( f"  Total clades in registry: {total_clades_in_registry}" )
print( f"  Written: {output_clade_registry_path.name}" )
print()


# ============================================================================
# STEP 9: Write Phylogenetic Paths
# ============================================================================

print( "STEP 8: Writing phylogenetic paths for all structures..." )

with open( output_phylogenetic_paths_path, 'w' ) as output_file:
    output_file.write( 'Structure_ID (topology structure identifier)\tSpecies_Clade_ID_Name (species clade identifier and name)\tSpecies_Name (species name extracted from clade identifier)\tPhylogenetic_Path (comma delimited root to leaf path of clade identifiers)\n' )

    # Sort by structure_id, then by species name
    all_phylogenetic_paths.sort( key=lambda x: ( x[ 0 ], x[ 2 ] ) )

    for structure_id, species_clade_id_name, species_name, phylogenetic_path in all_phylogenetic_paths:
        output = f"{structure_id}\t{species_clade_id_name}\t{species_name}\t{phylogenetic_path}\n"
        output_file.write( output )

total_phylogenetic_paths = len( all_phylogenetic_paths )
unique_species_count = len( set( path_entry[ 2 ] for path_entry in all_phylogenetic_paths ) )
print( f"  Total phylogenetic path entries: {total_phylogenetic_paths}" )
print( f"  Unique species: {unique_species_count}" )
print( f"  Structures: {complete_tree_count}" )
print( f"  Written: {output_phylogenetic_paths_path.name}" )
print()


# ============================================================================
# Summary
# ============================================================================

print( "=" * 80 )
print( "SCRIPT 004 COMPLETE" )
print( "=" * 80 )
print()
print( f"Total complete trees built: {complete_tree_count}" )
print( f"Total clades in registry: {total_clades_in_registry}" )
print( f"Total phylogenetic path entries: {total_phylogenetic_paths}" )
print( f"Unique species across all structures: {unique_species_count}" )
print()
print( "Output files:" )
print( f"  1. newick_trees/ ({complete_tree_count} complete annotated Newick tree files)" )
print( f"  2. {output_clade_registry_path.name}" )
print( f"  3. {output_phylogenetic_paths_path.name}" )
print()
print( "Next step: Run script 005 for downstream analysis" )
print()
