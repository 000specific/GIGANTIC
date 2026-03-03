#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Assign clade IDs to all topology permutations using original tree IDs for structure_001
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 003: Assign Clade Identifiers

Purpose:
    Assign consistent clade IDs and names to all topology permutations.

    Strategy:
    1. For structure_001: Use the original species tree with its clade IDs
    2. For structures 002+: Reuse existing clade IDs where canonical subtree
       structure matches, assign new IDs starting after the highest existing ID

    New clade IDs are assigned when a topology creates a grouping that does
    not exist in structure_001.

Inputs:
    --workflow-dir: Workflow root directory
    Reads: OUTPUT_pipeline/1-output/ (clade registry, metadata)
           OUTPUT_pipeline/2-output/ (topology permutations)
           INPUT_user/species_tree.newick (original tree with clade IDs)

Outputs:
    OUTPUT_pipeline/3-output/3_ai-clade_topology_registry.tsv
    OUTPUT_pipeline/3-output/newick_trees/ (annotated newick files per structure)
"""

from pathlib import Path
from typing import Dict, List, Optional
import argparse
import sys
import re
import yaml


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 003: Assign clade identifiers to all topologies' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    return parser.parse_args()


# ============================================================================
# Tree Node Classes
# ============================================================================

class TreeNode:
    """Represents a node in the topology tree."""

    def __init__( self, name: str = '' ):
        self.name = name
        self.children: List[ TreeNode ] = []
        self.parent: Optional[ 'TreeNode' ] = None
        self.clade_id: Optional[ str ] = None
        self.clade_name: Optional[ str ] = None

    def add_child( self, child: 'TreeNode' ):
        """Add a child node."""
        self.children.append( child )
        child.parent = self

    def is_leaf( self ) -> bool:
        return len( self.children ) == 0

    def get_canonical_structure( self, unresolved_names: List[ str ] ) -> str:
        """
        Get the canonical structure of this subtree.
        For leaves: return the clade name (unresolved clade name if applicable)
        For internal nodes: return alphabetically-ordered Newick structure
        """
        if not self.children:
            # Check if this is an unresolved clade
            for unresolved_name in unresolved_names:
                if unresolved_name in self.name:
                    return unresolved_name
            return self.name

        child_structures = []
        for child in self.children:
            child_structures.append( child.get_canonical_structure( unresolved_names ) )

        child_structures.sort()
        return f"({','.join( child_structures )})"


def parse_topology_newick( newick_string: str ) -> TreeNode:
    """Parse a simple topology Newick tree string into a TreeNode structure."""
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
                child = TreeNode( current_token.strip() )
                stack[ -1 ].add_child( child )
                current_token = ''

        elif char == ')':
            if current_token:
                child = TreeNode( current_token.strip() )
                stack[ -1 ].add_child( child )
                current_token = ''

            finished_node = stack.pop()

            i += 1
            internal_name = ''
            while i < len( newick_string ) and newick_string[ i ] not in '(),;':
                internal_name += newick_string[ i ]
                i += 1

            if internal_name.strip():
                finished_node.name = internal_name.strip()

            i -= 1

        else:
            current_token += char

        i += 1

    return stack[ 0 ]


def parse_annotated_newick( newick_string: str ) -> TreeNode:
    """Parse an annotated Newick tree (with CXXX_Name:length labels)."""
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
                label = current_token.split( ':' )[ 0 ].strip()
                child = TreeNode( label )
                if '_' in label and label[ 0 ] == 'C':
                    parts_label = label.split( '_', 1 )
                    child.clade_id = parts_label[ 0 ]
                    child.clade_name = parts_label[ 1 ]
                stack[ -1 ].add_child( child )
                current_token = ''

        elif char == ')':
            if current_token:
                label = current_token.split( ':' )[ 0 ].strip()
                child = TreeNode( label )
                if '_' in label and label[ 0 ] == 'C':
                    parts_label = label.split( '_', 1 )
                    child.clade_id = parts_label[ 0 ]
                    child.clade_name = parts_label[ 1 ]
                stack[ -1 ].add_child( child )
                current_token = ''

            finished_node = stack.pop()

            i += 1
            label_and_length = ''
            while i < len( newick_string ) and newick_string[ i ] not in '(),;':
                label_and_length += newick_string[ i ]
                i += 1

            if label_and_length.strip():
                label = label_and_length.split( ':' )[ 0 ].strip()
                finished_node.name = label
                if '_' in label and label[ 0 ] == 'C':
                    parts_label = label.split( '_', 1 )
                    finished_node.clade_id = parts_label[ 0 ]
                    finished_node.clade_name = parts_label[ 1 ]

            i -= 1

        else:
            current_token += char

        i += 1

    return stack[ 0 ]


def tree_to_newick( node: TreeNode ) -> str:
    """Convert a TreeNode structure back to Newick format with clade IDs."""
    if not node.children:
        if node.clade_id and node.clade_name:
            return f"{node.clade_id}_{node.clade_name}"
        return node.name

    children_newicks = []
    for child in node.children:
        children_newicks.append( tree_to_newick( child ) )

    newick = f"({','.join( children_newicks )})"

    if node.clade_id and node.clade_name:
        newick += f"{node.clade_id}_{node.clade_name}"

    return newick


# ============================================================================
# Main Script
# ============================================================================

args = parse_arguments()
workflow_dir = Path( args.workflow_dir )

# Read config
config_path = workflow_dir / 'permutations_and_features_config.yaml'
with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

species_set_name = config[ 'species_set_name' ]
unresolved_clade_names = config[ 'permutation' ][ 'unresolved_clades' ]
input_tree_relative = config[ 'input_files' ][ 'species_tree' ]

# Paths
output_pipeline_dir = workflow_dir / config[ 'output' ][ 'base_dir' ]
input_dir_1 = output_pipeline_dir / '1-output'
input_dir_2 = output_pipeline_dir / '2-output'
output_dir = output_pipeline_dir / '3-output'
output_dir.mkdir( parents=True, exist_ok=True )

output_registry = output_dir / '3_ai-clade_topology_registry.tsv'
output_newick_trees_dir = output_dir / 'newick_trees'
output_newick_trees_dir.mkdir( parents=True, exist_ok=True )

print( "=" * 80 )
print( "SCRIPT 003: Assign Clade Identifiers to All Topologies" )
print( "=" * 80 )
print()

# Read original species tree
input_species_tree = workflow_dir / input_tree_relative
with open( input_species_tree, 'r' ) as input_file:
    species_target_newick = input_file.read().strip()

# Extract unresolved clade IDs from original tree
clade_labels = re.findall( r'(C\d{3})_([^:\),]+)', species_target_newick )

unresolved_ids___names = {}
for clade_id, clade_name in clade_labels:
    if clade_name in unresolved_clade_names:
        unresolved_ids___names[ clade_name ] = clade_id

print( "Unresolved clade IDs:" )
for clade_name in sorted( unresolved_ids___names.keys() ):
    print( f"  {clade_name}: {unresolved_ids___names[ clade_name ]}" )
print()

# Find highest existing clade ID to determine where new IDs start
all_clade_numbers = []
for clade_id, clade_name in clade_labels:
    if clade_id.startswith( 'C' ) and clade_id[ 1: ].isdigit():
        all_clade_numbers.append( int( clade_id[ 1: ] ) )

max_existing_clade_number = max( all_clade_numbers ) if all_clade_numbers else 0
next_clade_number = max_existing_clade_number + 1

print( f"Highest existing clade ID: C{max_existing_clade_number:03d}" )
print( f"New clade IDs will start at: C{next_clade_number:03d}" )
print()

# Read topologies from script 002
print( "Reading topology permutations..." )

topologies = []

# Structure_ID (topology structure identifier)	Topology_Newick (newick string with semicolon)	Newick_Structure (newick string without semicolon)
# structure_001	((((Bilateria,Cnidaria),Placozoa),Porifera),Ctenophora);	((((Bilateria,Cnidaria),Placozoa),Porifera),Ctenophora)
input_topologies_file = input_dir_2 / '2_ai-topology_permutations.tsv'
with open( input_topologies_file, 'r' ) as input_file:
    header = input_file.readline()

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )
        structure_id = parts[ 0 ]
        topology_newick = parts[ 1 ]

        topologies.append( ( structure_id, topology_newick ) )

print( f"  Loaded {len( topologies )} topologies" )
print()

# Initialize registry and clade numbering
canonical_structures___clades = {}
clade_ids___registry_entries = {}

all_tree_roots = {}

# Process structure_001 with original species tree clade IDs
print( "Processing structure_001 with original species tree clade IDs..." )

structure_001_root = parse_annotated_newick( species_target_newick )

# Extract all clade IDs and register them
def extract_and_register_clade_info( node: TreeNode, structure_id: str ):
    """Extract clade info from annotated tree and register all clades."""
    for child in node.children:
        extract_and_register_clade_info( child, structure_id )

    if node.children and node.clade_id:
        canonical_structure = node.get_canonical_structure( unresolved_clade_names )
        canonical_structures___clades[ canonical_structure ] = ( node.clade_id, node.clade_name )

        registry_entry = {
            'clade_id': node.clade_id,
            'clade_name': node.clade_name,
            'canonical_structure': canonical_structure,
            'appears_in_structures': [ structure_id ]
        }
        clade_ids___registry_entries[ node.clade_id ] = registry_entry

extract_and_register_clade_info( structure_001_root, 'structure_001' )
all_tree_roots[ 'structure_001' ] = structure_001_root

structure_001_clade_count = len( clade_ids___registry_entries )
print( f"  structure_001: Registered {structure_001_clade_count} original clade IDs" )
print()

# Process remaining structures
if len( topologies ) > 1:
    print( f"Processing structures 002-{len( topologies ):03d}..." )
    print( f"  Will reuse existing clade IDs or assign new ones starting at C{next_clade_number:03d}" )
    print()

    def assign_clade_ids( node: TreeNode, structure_id: str ):
        """Assign clade IDs to all nodes. Reuses existing or assigns new."""
        global next_clade_number

        for child in node.children:
            assign_clade_ids( child, structure_id )

        if node.children:
            canonical_structure = node.get_canonical_structure( unresolved_clade_names )

            if canonical_structure in canonical_structures___clades:
                node.clade_id, node.clade_name = canonical_structures___clades[ canonical_structure ]

                registry_entry = clade_ids___registry_entries[ node.clade_id ]
                if structure_id not in registry_entry[ 'appears_in_structures' ]:
                    registry_entry[ 'appears_in_structures' ].append( structure_id )
            else:
                node.clade_id = f"C{next_clade_number:03d}"
                node.clade_name = f"Clade_{next_clade_number:03d}"

                canonical_structures___clades[ canonical_structure ] = ( node.clade_id, node.clade_name )

                registry_entry = {
                    'clade_id': node.clade_id,
                    'clade_name': node.clade_name,
                    'canonical_structure': canonical_structure,
                    'appears_in_structures': [ structure_id ]
                }
                clade_ids___registry_entries[ node.clade_id ] = registry_entry

                next_clade_number += 1
        else:
            # Leaf node - use unresolved clade ID
            if node.name in unresolved_ids___names:
                node.clade_id = unresolved_ids___names[ node.name ]
                node.clade_name = node.name

    for structure_id, topology_newick in topologies[ 1: ]:
        root = parse_topology_newick( topology_newick )

        clades_before = len( clade_ids___registry_entries )
        assign_clade_ids( root, structure_id )
        all_tree_roots[ structure_id ] = root

        clades_after = len( clade_ids___registry_entries )
        new_clades = clades_after - clades_before

        # Show progress for first 10 and last 5
        structure_number = int( structure_id.replace( 'structure_', '' ) )
        if structure_number <= 10 or structure_number > len( topologies ) - 5:
            print( f"  {structure_id}: {new_clades} new clades added" )
        elif structure_number == 11:
            print( f"  ... (structures 011-{len( topologies ) - 5:03d}) ..." )

print()
print( f"Total clades in registry: {len( clade_ids___registry_entries )}" )
print( f"Structure_001: {structure_001_clade_count} original clade IDs" )
if next_clade_number > max_existing_clade_number + 1:
    new_count = next_clade_number - max_existing_clade_number - 1
    print( f"Structures 002+: {new_count} new clade IDs (C{max_existing_clade_number + 1:03d}-C{next_clade_number - 1:03d})" )
else:
    print( f"Structures 002+: No new clade IDs (all reused from structure_001)" )
print()

# Write registry
print( "Writing clade topology registry..." )

with open( output_registry, 'w' ) as output_file:
    output_file.write( 'Clade_ID (clade identifier)\tClade_Name (clade name)\tCanonical_Structure (canonical newick subtree structure)\tAppears_In_Structures (comma delimited list of structures)\n' )

    for clade_id in sorted( clade_ids___registry_entries.keys(), key=lambda x: int( x[ 1: ] ) if x[ 1: ].isdigit() else 99999 ):
        clade_data = clade_ids___registry_entries[ clade_id ]
        clade_name = clade_data[ 'clade_name' ]
        canonical_structure = clade_data[ 'canonical_structure' ]
        appears_in_structures = ','.join( sorted( clade_data[ 'appears_in_structures' ] ) )

        output = f"{clade_id}\t{clade_name}\t{canonical_structure}\t{appears_in_structures}\n"
        output_file.write( output )

print( f"  {output_registry.name}" )
print()

# Write annotated Newick trees
print( "Writing annotated Newick tree files..." )

for structure_id in sorted( all_tree_roots.keys() ):
    root = all_tree_roots[ structure_id ]

    newick_string = tree_to_newick( root )

    newick_tree_file = output_newick_trees_dir / f"3_ai-{structure_id}_topology_with_clade_ids.newick"
    with open( newick_tree_file, 'w' ) as tree_file:
        tree_file.write( newick_string + ';\n' )

    structure_number = int( structure_id.replace( 'structure_', '' ) )
    if structure_number <= 10 or structure_number > len( all_tree_roots ) - 5:
        display_newick = newick_string if len( newick_string ) <= 150 else newick_string[ :147 ] + '...'
        print( f"  {structure_id}: {display_newick}" )
    elif structure_number == 11:
        print( f"  ... (structures 011-{len( all_tree_roots ) - 5:03d}) ..." )

print()
print( f"  newick_trees/ ({len( all_tree_roots )} annotated Newick tree files)" )
print()

print( "=" * 80 )
print( "SCRIPT 003 COMPLETE" )
print( "=" * 80 )
print()
print( f"Total clades in registry: {len( clade_ids___registry_entries )}" )
print( f"Total annotated tree files: {len( all_tree_roots )}" )
print()
print( "Next step: Run script 004 to build complete species trees" )
print()
