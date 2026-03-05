#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Extract species tree components and generate phylogenetic paths
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 001: Extract Tree Components

Purpose:
    Parse the user-provided annotated species tree in Newick format and extract:
    1. Phylogenetic paths for all clades (root-to-node path through the tree)
    2. Fixed structure clades (clades outside the variable/unresolved region)
    3. Unresolved clade membership (which species belong to which unresolved clade)
    4. Initial clade registry (all clade IDs and names from the input tree)

    The "unresolved clades" are specified in the config file. These are the clades
    whose branching order will be permuted in subsequent scripts. Everything outside
    the common ancestor of the unresolved clades is the "fixed structure."

    When 0 unresolved clades are specified, the entire tree is fixed structure
    and no permutations will be generated (single tree mode).

Inputs:
    --workflow-dir: Workflow root directory (reads config and INPUT_user/)

Outputs:
    OUTPUT_pipeline/1-output/1_ai-tree-phylogenetic_paths.tsv
    OUTPUT_pipeline/1-output/1_ai-tree-fixed_structure_clades.tsv
    OUTPUT_pipeline/1-output/1_ai-tree-unresolved_clade_membership.tsv
    OUTPUT_pipeline/1-output/1_ai-tree-clade_registry.tsv
"""

from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import argparse
import sys
import re
import yaml


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 001: Extract tree components and generate phylogenetic paths' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    return parser.parse_args()


# ============================================================================
# Newick Parser
# ============================================================================

class NewickNode:
    """Represents a node in a Newick tree."""

    def __init__( self, label: str = '', branch_length: str = '1.0' ):
        self.label = label
        self.branch_length = branch_length
        self.children: List[ 'NewickNode' ] = []
        self.parent: Optional[ 'NewickNode' ] = None

    def add_child( self, child: 'NewickNode' ):
        """Add a child node."""
        self.children.append( child )
        child.parent = self

    def is_leaf( self ) -> bool:
        """Check if this is a leaf node."""
        return len( self.children ) == 0

    def get_path_to_root( self ) -> List[ str ]:
        """Get phylogenetic path from this node to root (list of clade_id_name)."""
        path = []
        current = self
        while current is not None:
            if current.label:
                path.append( current.label )
            current = current.parent
        return path

    def get_all_clade_ids( self ) -> List[ Tuple[ str, str, str ] ]:
        """
        Get all clade IDs in this subtree.
        Returns list of (clade_id, clade_name, clade_id_name).
        """
        clades = []

        if self.label:
            if '_' in self.label:
                parts_label = self.label.split( '_', 1 )
                clade_id = parts_label[ 0 ]
                clade_name = parts_label[ 1 ]
                clade_id_name = self.label
                clades.append( ( clade_id, clade_name, clade_id_name ) )

        for child in self.children:
            clades.extend( child.get_all_clade_ids() )

        return clades

    def get_all_leaf_labels( self ) -> List[ str ]:
        """Get all leaf labels in this subtree."""
        if self.is_leaf():
            return [ self.label ] if self.label else []
        labels = []
        for child in self.children:
            labels.extend( child.get_all_leaf_labels() )
        return labels


def parse_label_and_length( token: str ) -> Tuple[ str, str ]:
    """Parse label and branch length from token."""
    if ':' in token:
        parts_token = token.split( ':', 1 )
        return ( parts_token[ 0 ], parts_token[ 1 ] )
    else:
        return ( token, '1.0' )


def parse_newick( newick_string: str ) -> NewickNode:
    """Parse a Newick string with labeled internal nodes."""
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

            i += 1
            label_and_length = ''
            while i < len( newick_string ) and newick_string[ i ] not in '(),;':
                label_and_length += newick_string[ i ]
                i += 1

            if label_and_length:
                label, branch_length = parse_label_and_length( label_and_length )
                finished_node.label = label
                finished_node.branch_length = branch_length

            i -= 1

        else:
            current_token += char

        i += 1

    return stack[ 0 ]


def find_node_by_label( node: NewickNode, target_label: str ) -> Optional[ NewickNode ]:
    """Find a node by its label."""
    if node.label == target_label:
        return node
    for child in node.children:
        result = find_node_by_label( child, target_label )
        if result:
            return result
    return None


def find_node_by_clade_name( node: NewickNode, target_name: str ) -> Optional[ NewickNode ]:
    """Find a node whose clade name (after CXXX_) matches target_name."""
    if node.label and '_' in node.label:
        parts_label = node.label.split( '_', 1 )
        if parts_label[ 1 ] == target_name:
            return node
    for child in node.children:
        result = find_node_by_clade_name( child, target_name )
        if result:
            return result
    return None


def find_common_ancestor( node: NewickNode, target_labels: Set[ str ] ) -> Optional[ NewickNode ]:
    """
    Find the lowest common ancestor of nodes matching any of the target labels.
    Target labels are matched against the clade name portion (after CXXX_).
    """
    if not target_labels:
        return None

    # Find all target nodes
    target_nodes = []
    for target_name in target_labels:
        found_node = find_node_by_clade_name( node, target_name )
        if found_node:
            target_nodes.append( found_node )

    if not target_nodes:
        return None

    if len( target_nodes ) == 1:
        return target_nodes[ 0 ].parent if target_nodes[ 0 ].parent else target_nodes[ 0 ]

    # Find common ancestor by collecting ancestor sets
    def get_ancestors( n: NewickNode ) -> List[ NewickNode ]:
        """Get list of ancestors from node to root."""
        ancestors = []
        current = n
        while current is not None:
            ancestors.append( current )
            current = current.parent
        return ancestors

    # Get ancestors for first target
    first_ancestors = get_ancestors( target_nodes[ 0 ] )

    # Find deepest ancestor that is common to all targets
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
input_tree_relative = config[ 'input_files' ][ 'species_tree' ]
unresolved_clade_names = config[ 'permutation' ][ 'unresolved_clades' ]

# Input file
input_species_tree = workflow_dir / input_tree_relative

# Output directory
output_pipeline_dir = workflow_dir / config[ 'output' ][ 'base_dir' ]
output_dir = output_pipeline_dir / '1-output'
output_dir.mkdir( parents=True, exist_ok=True )

# Output files
output_phylogenetic_paths = output_dir / '1_ai-tree-phylogenetic_paths.tsv'
output_fixed_structure = output_dir / '1_ai-tree-fixed_structure_clades.tsv'
output_unresolved_membership = output_dir / '1_ai-tree-unresolved_clade_membership.tsv'
output_clade_registry = output_dir / '1_ai-tree-clade_registry.tsv'

print( "=" * 80 )
print( "SCRIPT 001: Extract Tree Components & Generate Phylogenetic Paths" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print( f"Input tree: {input_species_tree}" )
print( f"Unresolved clades ({len( unresolved_clade_names )}): {', '.join( unresolved_clade_names ) if unresolved_clade_names else 'NONE (single tree mode)'}" )
print()


# ============================================================================
# STEP 1: Parse Species Tree
# ============================================================================

print( "Reading and parsing annotated species tree..." )

if not input_species_tree.exists():
    print( f"CRITICAL ERROR: Input tree file not found: {input_species_tree}" )
    print( "Please provide a species tree in INPUT_user/species_tree.newick" )
    sys.exit( 1 )

with open( input_species_tree, 'r' ) as input_file:
    species_newick = input_file.read().strip()

tree_root = parse_newick( species_newick )
print( f"  Parsed successfully (tree length: {len( species_newick )} characters)" )
print()


# ============================================================================
# STEP 2: Collect All Clades and Generate Phylogenetic Paths
# ============================================================================

print( "Collecting all clades from tree..." )
all_clades = tree_root.get_all_clade_ids()
print( f"  Found {len( all_clades )} total clades" )
print()

print( "Generating phylogenetic paths for all clades..." )

phylogenetic_paths_list = []

for clade_id, clade_name, clade_id_name in all_clades:
    node = find_node_by_label( tree_root, clade_id_name )
    if node:
        path = node.get_path_to_root()
        path.reverse()
        phylogenetic_path = ','.join( path )
        phylogenetic_paths_list.append( ( clade_id, clade_name, clade_id_name, phylogenetic_path ) )

print( f"  Generated {len( phylogenetic_paths_list )} phylogenetic paths" )
print()

# Write phylogenetic paths
print( "Writing phylogenetic paths..." )

with open( output_phylogenetic_paths, 'w' ) as output_file:
    output_file.write( 'Clade_ID (clade identifier)\tClade_Name (clade name after identifier prefix)\tClade_ID_Name (full clade identifier and name)\tPhylogenetic_Path (comma delimited root to node path)\n' )

    def sort_key_numeric( entry ):
        clade_id = entry[ 0 ]
        if clade_id.startswith( 'C' ) and clade_id[ 1: ].isdigit():
            return ( 0, int( clade_id[ 1: ] ) )
        else:
            return ( 1, clade_id )

    phylogenetic_paths_list.sort( key=sort_key_numeric )

    for clade_id, clade_name, clade_id_name, phylogenetic_path in phylogenetic_paths_list:
        output = f"{clade_id}\t{clade_name}\t{clade_id_name}\t{phylogenetic_path}\n"
        output_file.write( output )

print( f"  {output_phylogenetic_paths.name}" )
print()


# ============================================================================
# STEP 3: Identify Unresolved Clades and Variable Root
# ============================================================================

print( "Identifying unresolved clades in tree..." )

# Build clade data dictionary
clade_id_names___data = {}
for clade_id, clade_name, clade_id_name, phylogenetic_path in phylogenetic_paths_list:
    clade_id_names___data[ clade_id_name ] = {
        'clade_id': clade_id,
        'clade_name': clade_name,
        'clade_id_name': clade_id_name,
        'phylogenetic_path': phylogenetic_path
    }

# Find unresolved clade nodes and their IDs
unresolved_clade_ids___names = {}
for unresolved_name in unresolved_clade_names:
    found_node = find_node_by_clade_name( tree_root, unresolved_name )
    if found_node and '_' in found_node.label:
        parts_label = found_node.label.split( '_', 1 )
        unresolved_clade_ids___names[ parts_label[ 0 ] ] = unresolved_name
        print( f"  Found: {found_node.label}" )
    else:
        print( f"  WARNING: Unresolved clade '{unresolved_name}' not found in tree!" )

print( f"  Matched {len( unresolved_clade_ids___names )} of {len( unresolved_clade_names )} unresolved clades" )
print()

# Find the variable root (common ancestor of unresolved clades)
variable_root_label = None
if unresolved_clade_names:
    variable_root_node = find_common_ancestor( tree_root, set( unresolved_clade_names ) )
    if variable_root_node and variable_root_node.label:
        variable_root_label = variable_root_node.label
        print( f"  Variable root (common ancestor of unresolved clades): {variable_root_label}" )
    else:
        print( "  WARNING: Could not identify variable root!" )
else:
    print( "  No unresolved clades specified - single tree mode (entire tree is fixed)" )
print()


# ============================================================================
# STEP 4: Separate Fixed Structure from Variable Region
# ============================================================================

print( "Separating fixed structure from variable region..." )

fixed_structure_clades = []
variable_region_clades = []

for clade_id_name, data in clade_id_names___data.items():
    phylogenetic_path = data[ 'phylogenetic_path' ]
    path_parts = phylogenetic_path.split( ',' )

    if variable_root_label:
        # Check if the variable root is in this clade's path
        has_variable_root = variable_root_label in path_parts

        if not has_variable_root:
            fixed_structure_clades.append( data )
        else:
            variable_region_clades.append( data )
    else:
        # No unresolved clades - everything is fixed
        fixed_structure_clades.append( data )

print( f"  Fixed structure clades: {len( fixed_structure_clades )}" )
print( f"  Variable region clades: {len( variable_region_clades )}" )
print()


# ============================================================================
# STEP 5: Assign Variable Clades to Unresolved Groups
# ============================================================================

print( "Assigning variable clades to unresolved groups..." )

clade_memberships = []

for data in variable_region_clades:
    clade_id = data[ 'clade_id' ]
    clade_id_name = data[ 'clade_id_name' ]
    phylogenetic_path = data[ 'phylogenetic_path' ]
    path_parts = phylogenetic_path.split( ',' )

    assigned_unresolved_clade = None

    for unresolved_id, unresolved_name in unresolved_clade_ids___names.items():
        if any( unresolved_id in part for part in path_parts ):
            assigned_unresolved_clade = ( unresolved_id, unresolved_name )
            break

    if assigned_unresolved_clade:
        clade_memberships.append( ( clade_id_name, assigned_unresolved_clade[ 0 ], assigned_unresolved_clade[ 1 ] ) )
    else:
        clade_memberships.append( ( clade_id_name, 'UNASSIGNED', 'variable_internal_node' ) )

print( f"  Assigned {len( clade_memberships )} variable clades to unresolved groups" )

# Count assignments
unresolved_clade_counts = {}
for _, unresolved_id, unresolved_name in clade_memberships:
    if unresolved_id not in unresolved_clade_counts:
        unresolved_clade_counts[ unresolved_id ] = 0
    unresolved_clade_counts[ unresolved_id ] += 1

for unresolved_id in sorted( unresolved_clade_counts.keys() ):
    count = unresolved_clade_counts[ unresolved_id ]
    if unresolved_id in unresolved_clade_ids___names:
        print( f"    {unresolved_id} ({unresolved_clade_ids___names[ unresolved_id ]}): {count} clades" )
    else:
        print( f"    {unresolved_id}: {count} clades" )
print()


# ============================================================================
# STEP 6: Write Output Files
# ============================================================================

print( "Writing output files..." )

# 1. Fixed structure clades
with open( output_fixed_structure, 'w' ) as output_file:
    output_file.write( 'Clade_ID (clade identifier)\tClade_Name (clade name)\tClade_ID_Name (full identifier)\tPhylogenetic_Path (root to node path)\n' )
    for data in sorted( fixed_structure_clades, key=lambda x: x[ 'clade_id' ] ):
        output = f"{data[ 'clade_id' ]}\t{data[ 'clade_name' ]}\t{data[ 'clade_id_name' ]}\t{data[ 'phylogenetic_path' ]}\n"
        output_file.write( output )

print( f"  {output_fixed_structure.name}" )

# 2. Unresolved clade membership
with open( output_unresolved_membership, 'w' ) as output_file:
    output_file.write( 'Clade_ID_Name (full identifier)\tUnresolved_Clade_ID (parent unresolved clade identifier)\tUnresolved_Clade_Name (parent unresolved clade name)\n' )
    for clade_id_name, unresolved_id, unresolved_name in sorted( clade_memberships ):
        output = f"{clade_id_name}\t{unresolved_id}\t{unresolved_name}\n"
        output_file.write( output )

print( f"  {output_unresolved_membership.name}" )

# 3. Clade registry (seeded with structure_001 data)
with open( output_clade_registry, 'w' ) as output_file:
    output_file.write( 'Clade_ID (clade identifier)\tClade_Name (clade name)\tClade_ID_Name (full identifier)\tPhylogenetic_Path (root to node path)\tFirst_Appears_In_Structure (structure where clade first appears)\tAppears_In_Structures (comma delimited list of structures containing this clade)\n' )

    for clade_id_name in sorted( clade_id_names___data.keys(), key=lambda x: clade_id_names___data[ x ][ 'clade_id' ] ):
        data = clade_id_names___data[ clade_id_name ]
        output = f"{data[ 'clade_id' ]}\t{data[ 'clade_name' ]}\t{data[ 'clade_id_name' ]}\t{data[ 'phylogenetic_path' ]}\tstructure_001\tstructure_001\n"
        output_file.write( output )

print( f"  {output_clade_registry.name}" )
print()

# Write metadata file for downstream scripts
metadata_path = output_dir / '1_ai-tree-metadata.tsv'
with open( metadata_path, 'w' ) as output_file:
    output_file.write( f"species_set_name\t{species_set_name}\n" )
    output_file.write( f"variable_root_label\t{variable_root_label if variable_root_label else 'NONE'}\n" )
    output_file.write( f"unresolved_clade_count\t{len( unresolved_clade_ids___names )}\n" )
    output_file.write( f"total_clade_count\t{len( all_clades )}\n" )
    output_file.write( f"fixed_structure_clade_count\t{len( fixed_structure_clades )}\n" )
    output_file.write( f"variable_region_clade_count\t{len( variable_region_clades )}\n" )
    # Write the leaf species count
    all_leaves = tree_root.get_all_leaf_labels()
    output_file.write( f"leaf_species_count\t{len( all_leaves )}\n" )
    # Write unresolved clade IDs for downstream use
    for unresolved_id, unresolved_name in sorted( unresolved_clade_ids___names.items() ):
        output_file.write( f"unresolved_clade\t{unresolved_id}\t{unresolved_name}\n" )

print( f"  {metadata_path.name}" )
print()

print( "=" * 80 )
print( "SCRIPT 001 COMPLETE" )
print( "=" * 80 )
print()
print( f"Total clades: {len( all_clades )}" )
print( f"Fixed structure clades: {len( fixed_structure_clades )}" )
print( f"Variable region clades: {len( variable_region_clades )}" )
print( f"Unresolved clades for permutation: {len( unresolved_clade_ids___names )}" )
print()
print( "Output files:" )
print( f"  1. {output_phylogenetic_paths.name}" )
print( f"  2. {output_fixed_structure.name}" )
print( f"  3. {output_unresolved_membership.name}" )
print( f"  4. {output_clade_registry.name}" )
print( f"  5. {metadata_path.name}" )
print()
print( "Next step: Run script 002 to generate topology permutations" )
print()
