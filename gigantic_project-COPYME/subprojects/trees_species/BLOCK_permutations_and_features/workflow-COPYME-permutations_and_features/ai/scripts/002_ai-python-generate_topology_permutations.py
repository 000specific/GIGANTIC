#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Generate all possible rooted tree topologies for N unresolved clades
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 002: Generate Topology Permutations

Purpose:
    Generate all possible rooted bifurcating tree topologies for N unresolved clades.

    Mathematical basis:
    - For N taxa: (2N-3)!! possible rooted binary topologies
    - N=5: 7!! = 7x5x3x1 = 105 topologies
    - N=4: 5!! = 5x3x1 = 15 topologies
    - N=3: 3!! = 3x1 = 3 topologies
    - N=2: 1!! = 1 topology
    - N=1 or N=0: No permutation (single tree mode, 1 topology)

    Algorithm:
    1. Generate ALL possible rooted topologies (includes duplicates with different orderings)
    2. Canonicalize each topology (alphabetically order all pairs)
    3. Deduplicate to get unique topological structures
    4. Place the original tree topology as structure_001

Inputs:
    --workflow-dir: Workflow root directory
    Reads: OUTPUT_pipeline/1-output/ (fixed outgroups, unresolved clades)

Outputs:
    OUTPUT_pipeline/2-output/2_ai-topology_permutations.tsv
    OUTPUT_pipeline/2-output/newick_trees/ (individual newick files per topology)
"""

from pathlib import Path
from typing import List, Dict
import argparse
import sys
import math
import yaml


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 002: Generate topology permutations' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    return parser.parse_args()


def double_factorial( n: int ) -> int:
    """Compute double factorial n!! = n * (n-2) * (n-4) * ... * 1."""
    if n <= 0:
        return 1
    result = 1
    while n > 0:
        result *= n
        n -= 2
    return result


def generate_all_topologies_no_constraints( taxa: List[ str ] ) -> List[ str ]:
    """
    Generate ALL possible rooted topologies without canonical ordering constraints.

    Creates many duplicates with different name orderings. Duplicates are
    removed later via canonicalization.

    Args:
        taxa: List of taxon names

    Returns:
        List of Newick strings (includes duplicates with different orderings)
    """
    if len( taxa ) == 1:
        return [ taxa[ 0 ] ]

    if len( taxa ) == 2:
        return [
            f"({taxa[ 0 ]},{taxa[ 1 ]})",
            f"({taxa[ 1 ]},{taxa[ 0 ]})"
        ]

    trees = []

    for i in range( len( taxa ) ):
        for j in range( len( taxa ) ):
            if i == j:
                continue

            new_clade = f"({taxa[ i ]},{taxa[ j ]})"
            remaining = [ taxa[ k ] for k in range( len( taxa ) ) if k != i and k != j ]
            remaining.append( new_clade )

            subtrees = generate_all_topologies_no_constraints( remaining )
            trees.extend( subtrees )

    return trees


def canonicalize_newick( newick: str ) -> str:
    """
    Canonicalize a Newick string by ensuring all pairs are alphabetically ordered.

    Recursively processes the tree so that in every (X,Y) pair, X comes before Y
    alphabetically. Creates a unique canonical form for each topological structure.
    """
    if '(' not in newick:
        return newick

    if newick.startswith( '(' ) and newick.endswith( ')' ):
        inner = newick[ 1:-1 ]

        depth = 0
        comma_pos = -1
        for i, char in enumerate( inner ):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                comma_pos = i
                break

        if comma_pos == -1:
            return newick

        left = inner[ :comma_pos ]
        right = inner[ comma_pos + 1: ]

        left_canonical = canonicalize_newick( left )
        right_canonical = canonicalize_newick( right )

        if left_canonical < right_canonical:
            return f"({left_canonical},{right_canonical})"
        else:
            return f"({right_canonical},{left_canonical})"

    return newick


def extract_original_topology_from_tree( newick_string: str, unresolved_clade_names: List[ str ] ) -> str:
    """
    Extract the topology of unresolved clades from the full species tree.

    Parses the Newick tree, finds each unresolved clade node, and reconstructs
    just the topology among those clades (ignoring all other structure).

    Returns the canonical form of the original topology.
    """
    import re

    # Find clade labels matching unresolved names
    # Pattern: CXXX_CladeName
    clade_labels = re.findall( r'(C\d{3})_([^:\),]+)', newick_string )

    unresolved_ids___names = {}
    for clade_id, clade_name in clade_labels:
        if clade_name in unresolved_clade_names:
            unresolved_ids___names[ clade_id ] = clade_name

    # We need to extract the subtree topology containing just these clades
    # Strategy: Parse tree, find common ancestor, extract topology
    # For now, use a simplified approach based on the Newick structure

    # Actually, for the canonical topology comparison, we just need to know
    # the branching order. Let's extract it from the tree structure.
    # The simplest approach: parse the full tree, prune to just unresolved clades

    class SimpleNode:
        def __init__( self, label='' ):
            self.label = label
            self.children = []

        def add_child( self, child ):
            self.children.append( child )

        def is_leaf( self ):
            return len( self.children ) == 0

        def prune_to_labels( self, target_labels ):
            """Prune tree to keep only branches leading to target labels."""
            if self.is_leaf():
                if self.label in target_labels:
                    return SimpleNode( self.label )
                return None

            pruned_children = []
            for child in self.children:
                pruned = child.prune_to_labels( target_labels )
                if pruned is not None:
                    pruned_children.append( pruned )

            if not pruned_children:
                return None
            if len( pruned_children ) == 1:
                return pruned_children[ 0 ]

            new_node = SimpleNode()
            for child in pruned_children:
                new_node.add_child( child )
            return new_node

        def to_newick( self ):
            if self.is_leaf():
                return self.label
            children_newick = ','.join( [ c.to_newick() for c in self.children ] )
            return f"({children_newick})"

    # Parse the tree (simplified - just structure, using unresolved clade names as leaves)
    def parse_simple( s ):
        s = s.strip()
        if s.endswith( ';' ):
            s = s[ :-1 ]

        # Remove branch lengths
        s = re.sub( r':\d+\.?\d*', '', s )

        stack = [ SimpleNode() ]
        current_token = ''
        i = 0

        while i < len( s ):
            char = s[ i ]
            if char == '(':
                new_node = SimpleNode()
                stack[ -1 ].add_child( new_node )
                stack.append( new_node )
                current_token = ''
            elif char == ',':
                if current_token.strip():
                    child = SimpleNode( current_token.strip() )
                    stack[ -1 ].add_child( child )
                current_token = ''
            elif char == ')':
                if current_token.strip():
                    child = SimpleNode( current_token.strip() )
                    stack[ -1 ].add_child( child )
                current_token = ''
                finished = stack.pop()
                i += 1
                label = ''
                while i < len( s ) and s[ i ] not in '(),;':
                    label += s[ i ]
                    i += 1
                if label.strip():
                    finished.label = label.strip()
                i -= 1
            else:
                current_token += char
            i += 1

        return stack[ 0 ]

    # Replace clade IDs with just the clade names for matching
    # Build mapping: full_label -> clade_name (for unresolved clades)
    label_to_unresolved_name = {}
    for clade_id, clade_name in unresolved_ids___names.items():
        # The label in the tree will be CXXX_CladeName
        label_to_unresolved_name[ f"{clade_id}_{clade_name}" ] = clade_name

    tree = parse_simple( newick_string )

    # Rename unresolved clade nodes to just their names
    def rename_nodes( node ):
        if node.label in label_to_unresolved_name:
            node.label = label_to_unresolved_name[ node.label ]
        for child in node.children:
            rename_nodes( child )

    rename_nodes( tree )

    # Prune to just unresolved clade names
    pruned = tree.prune_to_labels( set( unresolved_clade_names ) )

    if pruned:
        raw_topology = pruned.to_newick()
        return canonicalize_newick( raw_topology )
    else:
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
unresolved_clade_names = config[ 'permutation' ][ 'unresolved_clades' ]
input_tree_relative = config[ 'input_files' ][ 'species_tree' ]

# Paths
output_pipeline_dir = workflow_dir / config[ 'output' ][ 'base_dir' ]
input_dir = output_pipeline_dir / '1-output'
output_dir = output_pipeline_dir / '2-output'
output_dir.mkdir( parents=True, exist_ok=True )

output_topologies = output_dir / '2_ai-topology_permutations.tsv'
output_newick_trees_dir = output_dir / 'newick_trees'
output_newick_trees_dir.mkdir( parents=True, exist_ok=True )

unresolved_count = len( unresolved_clade_names ) if unresolved_clade_names else 0

if unresolved_count >= 2:
    expected_topologies = double_factorial( 2 * unresolved_count - 3 )
else:
    expected_topologies = 1

print( "=" * 80 )
print( "SCRIPT 002: Generate Topology Permutations" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print( f"Unresolved clades ({unresolved_count}): {', '.join( unresolved_clade_names ) if unresolved_clade_names else 'NONE'}" )
print( f"Expected topologies: {expected_topologies}" )
if unresolved_count >= 2:
    print( f"  Formula: (2x{unresolved_count}-3)!! = {2 * unresolved_count - 3}!!" )
print()


# ============================================================================
# Handle Single Tree Mode (0 or 1 unresolved clades)
# ============================================================================

if unresolved_count <= 1:
    print( "Single tree mode - no permutations needed." )
    print( "Writing structure_001 (original tree topology)..." )
    print()

    # Read the original tree
    input_species_tree = workflow_dir / input_tree_relative
    with open( input_species_tree, 'r' ) as input_file:
        original_newick = input_file.read().strip()

    # Write single topology TSV
    with open( output_topologies, 'w' ) as output_file:
        output_file.write( 'Structure_ID (topology structure identifier)\tTopology_Newick (newick string with semicolon)\tNewick_Structure (newick string without semicolon)\n' )
        output = f"structure_001\t{original_newick}\t{original_newick.rstrip( ';' )}\n"
        output_file.write( output )

    # Write single newick file
    newick_tree_file = output_newick_trees_dir / 'structure_001_topology.newick'
    with open( newick_tree_file, 'w' ) as tree_file:
        tree_file.write( original_newick + '\n' )

    print( f"  structure_001: Original tree (single topology)" )
    print()
    print( "=" * 80 )
    print( "SCRIPT 002 COMPLETE" )
    print( "=" * 80 )
    print( f"Total unique topologies: 1 (single tree mode)" )
    print()
    sys.exit( 0 )


# ============================================================================
# Generate All Topologies (2+ unresolved clades)
# ============================================================================

# Sort unresolved clade names alphabetically for consistency
unresolved_clades_sorted = sorted( unresolved_clade_names )

print( f"Unresolved clades (sorted): {', '.join( unresolved_clades_sorted )}" )
print()

# Extract original topology from input tree for identification as structure_001
input_species_tree = workflow_dir / input_tree_relative
with open( input_species_tree, 'r' ) as input_file:
    original_newick = input_file.read().strip()

original_topology_canonical = extract_original_topology_from_tree( original_newick, unresolved_clade_names )

if original_topology_canonical:
    print( f"Original tree topology (canonical): {original_topology_canonical}" )
else:
    print( "WARNING: Could not extract original topology from tree" )
    print( "Using first generated topology as structure_001" )
print()

print( "Generating all topologies..." )
all_topologies_raw = generate_all_topologies_no_constraints( unresolved_clades_sorted )
print( f"  Generated {len( all_topologies_raw )} raw topologies (with duplicates)" )

print( "Canonicalizing..." )
all_topologies_canonical = [ canonicalize_newick( tree ) for tree in all_topologies_raw ]

print( "Deduplicating..." )
unique_topologies = list( set( all_topologies_canonical ) )
unique_topologies.sort()
print( f"  Result: {len( unique_topologies )} unique canonical topologies" )
print()

if len( unique_topologies ) != expected_topologies:
    print( f"  WARNING: Expected {expected_topologies} topologies, got {len( unique_topologies )}!" )
    print()

# Place original topology as structure_001
if original_topology_canonical and original_topology_canonical in unique_topologies:
    original_index = unique_topologies.index( original_topology_canonical )
    print( f"Found original topology at position {original_index + 1} of {len( unique_topologies )}" )
    unique_topologies.remove( original_topology_canonical )
    unique_topologies.insert( 0, original_topology_canonical )
    print( "Set as structure_001" )
elif original_topology_canonical:
    print( f"WARNING: Original topology not found in generated set!" )
    print( f"  Original: {original_topology_canonical}" )
    print( "  Using first generated topology as structure_001" )
else:
    print( "Using first generated topology as structure_001 (could not extract original)" )
print()


# ============================================================================
# Write Output Files
# ============================================================================

print( "Writing topologies to TSV and Newick files..." )
print()

with open( output_topologies, 'w' ) as output_file:
    output_file.write( 'Structure_ID (topology structure identifier)\tTopology_Newick (newick string with semicolon)\tNewick_Structure (newick string without semicolon)\n' )

    for i, topology_canonical in enumerate( unique_topologies, start=1 ):
        structure_id = f"structure_{i:03d}"

        topology_with_semicolon = topology_canonical + ';'
        newick_structure = topology_canonical

        output = f"{structure_id}\t{topology_with_semicolon}\t{newick_structure}\n"
        output_file.write( output )

        # Write individual Newick tree file
        newick_tree_file = output_newick_trees_dir / f"{structure_id}_topology.newick"
        with open( newick_tree_file, 'w' ) as tree_file:
            tree_file.write( topology_with_semicolon + '\n' )

        # Show first 10 and last 5
        if i <= 10 or i > len( unique_topologies ) - 5:
            if i == 1:
                print( f"  {structure_id} (original topology - canonical form):" )
                print( f"    {topology_canonical};" )
            else:
                print( f"  {structure_id}: {topology_canonical};" )
        elif i == 11:
            print( f"  ... (topologies 011-{len( unique_topologies ) - 5:03d}) ..." )

print()
print( f"  {output_topologies.name}" )
print( f"  {output_newick_trees_dir.name}/ ({len( unique_topologies )} Newick tree files)" )
print()

print( "=" * 80 )
print( "SCRIPT 002 COMPLETE" )
print( "=" * 80 )
print()
print( f"Total unique topologies: {len( unique_topologies )}" )
print()
print( "Next step: Run script 003 to assign clade identifiers to all topologies" )
print()
