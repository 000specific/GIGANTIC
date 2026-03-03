#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Generate parent-child relationship tables for all tree structures
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 005: Extract Parent-Child Relationships

Purpose:
    Parse all complete species tree Newick files from script 004 and generate
    two types of parent-child relationship tables for each structure:

    1. Parent-Sibling Sets (9 columns):
       For each node in the tree, record the parent and both children.
       - Internal nodes: Parent → Child_1, Child_2
       - Leaf nodes: Self-referential (parent = child_1 = child_2)
       This format captures the full sibling context at each node.

    2. Parent-Child Relationships (4 columns):
       Simple parent → child pairs for every edge in the tree.
       - Internal nodes: One row per child
       - Leaf nodes: Self-referential (parent = self, child = self)

Inputs:
    --workflow-dir: Workflow root directory
    Reads: permutations_and_features_config.yaml (for species_set_name)
           OUTPUT_pipeline/4-output/newick_trees/ (complete tree Newick files)

Outputs:
    OUTPUT_pipeline/5-output/{species_set_name}_Parent_Sibling_Sets/
        5_ai-structure_XXX_parent_child_table.tsv (per structure)

    OUTPUT_pipeline/5-output/{species_set_name}_Parent_Child_Relationships/
        5_ai-structure_XXX_parent_child_relationships.tsv (per structure)
"""

from pathlib import Path
from typing import List, Optional, Tuple
import argparse
import sys
import yaml


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 005: Extract parent-child relationships from all tree structures' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    return parser.parse_args()


# ============================================================================
# Newick Parser
# ============================================================================

class NewickNode:
    """Represents a node in a Newick tree with clade ID, name, and branch length."""

    def __init__( self, label: str = '', branch_length: str = '1.0' ):
        self.label = label
        self.branch_length = branch_length
        self.children: List[ 'NewickNode' ] = []
        self.parent: Optional[ 'NewickNode' ] = None
        self.clade_id: str = ''
        self.clade_name: str = ''

        # Parse clade_id and clade_name from label (format: CXXX_Name)
        if label and '_' in label and label[ 0 ] == 'C' and label[ 1:4 ].isdigit():
            parts_label = label.split( '_', 1 )
            self.clade_id = parts_label[ 0 ]
            self.clade_name = parts_label[ 1 ]

    def add_child( self, child: 'NewickNode' ):
        """Add a child node."""
        self.children.append( child )
        child.parent = self

    def is_leaf( self ) -> bool:
        """Check if this is a leaf node."""
        return len( self.children ) == 0

    def get_clade_id_name( self ) -> str:
        """Get the full clade ID and name string (e.g., C001_Fonticula_alba)."""
        return self.label if self.label else ''


def parse_label_and_length( token: str ) -> Tuple[ str, str ]:
    """
    Parse label and branch length from a Newick token.

    Token format: CXXX_Name:branch_length or just CXXX_Name
    """
    if ':' in token:
        parts_token = token.split( ':', 1 )
        return ( parts_token[ 0 ].strip(), parts_token[ 1 ].strip() )
    else:
        return ( token.strip(), '1.0' )


def parse_newick( newick_string: str ) -> NewickNode:
    """
    Parse a Newick string with labeled internal nodes and branch lengths.

    Expected label format: CXXX_CladeName:branch_length
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

            i += 1
            label_and_length = ''
            while i < len( newick_string ) and newick_string[ i ] not in '(),;':
                label_and_length += newick_string[ i ]
                i += 1

            if label_and_length:
                label, branch_length = parse_label_and_length( label_and_length )
                finished_node.label = label
                finished_node.branch_length = branch_length
                # Re-parse clade_id and clade_name from the new label
                if label and '_' in label and label[ 0 ] == 'C' and label[ 1:4 ].isdigit():
                    parts_label = label.split( '_', 1 )
                    finished_node.clade_id = parts_label[ 0 ]
                    finished_node.clade_name = parts_label[ 1 ]

            i -= 1

        else:
            current_token += char

        i += 1

    return stack[ 0 ]


def collect_all_nodes( node: NewickNode ) -> List[ NewickNode ]:
    """Collect all nodes in the tree via depth-first traversal."""
    nodes = []
    if node.label:
        nodes.append( node )
    for child in node.children:
        nodes.extend( collect_all_nodes( child ) )
    return nodes


def sort_key_clade_id( node: NewickNode ) -> Tuple[ int, int ]:
    """Sort key for ordering nodes by clade ID numerically."""
    if node.clade_id and node.clade_id.startswith( 'C' ) and node.clade_id[ 1: ].isdigit():
        return ( 0, int( node.clade_id[ 1: ] ) )
    else:
        return ( 1, 0 )


# ============================================================================
# Relationship Extraction Functions
# ============================================================================

def extract_parent_sibling_rows( root: NewickNode ) -> List[ dict ]:
    """
    Extract parent-sibling set rows for all nodes in the tree.

    For internal nodes: parent → child_1, child_2
    For leaf nodes: self-referential (parent = child_1 = child_2)
    """
    all_nodes = collect_all_nodes( root )
    rows = []

    for node in all_nodes:
        if node.is_leaf():
            # Leaf node: self-referential row
            row = {
                'parent_id': node.clade_id,
                'parent_name': node.clade_name,
                'parent_id_name': node.get_clade_id_name(),
                'child_1_id': node.clade_id,
                'child_1_name': node.clade_name,
                'child_1_id_name': node.get_clade_id_name(),
                'child_2_id': node.clade_id,
                'child_2_name': node.clade_name,
                'child_2_id_name': node.get_clade_id_name(),
            }
            rows.append( row )
        else:
            # Internal node: parent with two children
            # Trees are bifurcating, so expect exactly 2 children
            if len( node.children ) == 2:
                child_1 = node.children[ 0 ]
                child_2 = node.children[ 1 ]

                row = {
                    'parent_id': node.clade_id,
                    'parent_name': node.clade_name,
                    'parent_id_name': node.get_clade_id_name(),
                    'child_1_id': child_1.clade_id,
                    'child_1_name': child_1.clade_name,
                    'child_1_id_name': child_1.get_clade_id_name(),
                    'child_2_id': child_2.clade_id,
                    'child_2_name': child_2.clade_name,
                    'child_2_id_name': child_2.get_clade_id_name(),
                }
                rows.append( row )
            elif len( node.children ) > 2:
                # Handle multifurcating nodes: emit one row per pair
                for child_index in range( 0, len( node.children ), 2 ):
                    child_1 = node.children[ child_index ]
                    child_2 = node.children[ child_index + 1 ] if child_index + 1 < len( node.children ) else child_1

                    row = {
                        'parent_id': node.clade_id,
                        'parent_name': node.clade_name,
                        'parent_id_name': node.get_clade_id_name(),
                        'child_1_id': child_1.clade_id,
                        'child_1_name': child_1.clade_name,
                        'child_1_id_name': child_1.get_clade_id_name(),
                        'child_2_id': child_2.clade_id,
                        'child_2_name': child_2.clade_name,
                        'child_2_id_name': child_2.get_clade_id_name(),
                    }
                    rows.append( row )

    return rows


def extract_parent_child_rows( root: NewickNode ) -> List[ dict ]:
    """
    Extract simple parent-child relationship rows for all nodes in the tree.

    For internal nodes: one row per child (parent → child)
    For leaf nodes: self-referential (parent = self, child = self)
    """
    all_nodes = collect_all_nodes( root )
    rows = []

    for node in all_nodes:
        if node.is_leaf():
            # Leaf node: self-referential row
            row = {
                'parent_id': node.clade_id,
                'parent_name': node.clade_name,
                'child_id': node.clade_id,
                'child_name': node.clade_name,
            }
            rows.append( row )
        else:
            # Internal node: one row per child
            for child in node.children:
                row = {
                    'parent_id': node.clade_id,
                    'parent_name': node.clade_name,
                    'child_id': child.clade_id,
                    'child_name': child.clade_name,
                }
                rows.append( row )

    return rows


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

# Paths
output_pipeline_dir = workflow_dir / config[ 'output' ][ 'base_dir' ]
input_newick_dir = output_pipeline_dir / '4-output' / 'newick_trees'
output_dir = output_pipeline_dir / '5-output'
output_dir.mkdir( parents=True, exist_ok=True )

# Output subdirectories
output_parent_sibling_dir = output_dir / f"{species_set_name}_Parent_Sibling_Sets"
output_parent_child_dir = output_dir / f"{species_set_name}_Parent_Child_Relationships"
output_parent_sibling_dir.mkdir( parents=True, exist_ok=True )
output_parent_child_dir.mkdir( parents=True, exist_ok=True )

print( "=" * 80 )
print( "SCRIPT 005: Extract Parent-Child Relationships" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print( f"Input directory: {input_newick_dir}" )
print( f"Output directory: {output_dir}" )
print()


# ============================================================================
# STEP 1: Find and Sort Input Newick Files
# ============================================================================

print( "Finding complete tree Newick files from script 004..." )

if not input_newick_dir.exists():
    print( f"CRITICAL ERROR: Input directory not found: {input_newick_dir}" )
    print( "Script 004 must complete before running script 005." )
    sys.exit( 1 )

newick_files = sorted( input_newick_dir.glob( '*.newick' ) )

if not newick_files:
    print( f"CRITICAL ERROR: No Newick files found in: {input_newick_dir}" )
    print( "Script 004 must produce complete tree Newick files." )
    sys.exit( 1 )

print( f"  Found {len( newick_files )} Newick tree files" )
print()


# ============================================================================
# STEP 2: Process Each Tree Structure
# ============================================================================

print( "Processing tree structures..." )
print()

total_parent_sibling_rows = 0
total_parent_child_rows = 0
structures_processed = 0

for newick_file in newick_files:
    # Extract structure ID from filename
    # Expected filename pattern: 4_ai-structure_XXX_complete_tree.newick (or similar)
    filename = newick_file.stem
    structure_id = None

    # Try to extract structure_XXX from the filename
    if 'structure_' in filename:
        # Find the structure_XXX portion
        start_index = filename.index( 'structure_' )
        remainder = filename[ start_index: ]
        # Extract structure_XXX (structure_ + 3 digits)
        parts_remainder = remainder.split( '_' )
        if len( parts_remainder ) >= 2 and parts_remainder[ 1 ].isdigit():
            structure_id = f"structure_{parts_remainder[ 1 ]}"

    if not structure_id:
        print( f"  WARNING: Could not extract structure ID from: {newick_file.name}" )
        print( f"    Skipping this file." )
        continue

    structure_number = int( structure_id.replace( 'structure_', '' ) )

    # Read and parse the Newick tree
    with open( newick_file, 'r' ) as input_file:
        newick_string = input_file.read().strip()

    if not newick_string:
        print( f"  WARNING: Empty Newick file: {newick_file.name}" )
        continue

    tree_root = parse_newick( newick_string )

    # Validate that the tree has labeled nodes
    all_nodes = collect_all_nodes( tree_root )
    if not all_nodes:
        print( f"  WARNING: No labeled nodes found in: {newick_file.name}" )
        continue

    # ----------------------------------------------------------------
    # Extract Parent-Sibling Sets (9-column format)
    # ----------------------------------------------------------------

    parent_sibling_rows = extract_parent_sibling_rows( tree_root )

    # Sort rows by parent clade ID numerically
    parent_sibling_rows.sort( key=lambda row: (
        ( 0, int( row[ 'parent_id' ][ 1: ] ) ) if row[ 'parent_id' ] and row[ 'parent_id' ].startswith( 'C' ) and row[ 'parent_id' ][ 1: ].isdigit() else ( 1, 0 )
    ) )

    output_parent_sibling_file = output_parent_sibling_dir / f"5_ai-{structure_id}_parent_child_table.tsv"

    with open( output_parent_sibling_file, 'w' ) as output_file:
        # Write header
        header = (
            'Parent_ID (clade identifier of the parent node)\t'
            'Parent_Name (clade name of the parent node)\t'
            'Parent_ID_Name (full clade identifier and name of the parent node)\t'
            'Child_1_ID (clade identifier of the first child node)\t'
            'Child_1_Name (clade name of the first child node)\t'
            'Child_1_ID_Name (full clade identifier and name of the first child node)\t'
            'Child_2_ID (clade identifier of the second child node)\t'
            'Child_2_Name (clade name of the second child node)\t'
            'Child_2_ID_Name (full clade identifier and name of the second child node)\n'
        )
        output_file.write( header )

        for row in parent_sibling_rows:
            output = (
                f"{row[ 'parent_id' ]}\t"
                f"{row[ 'parent_name' ]}\t"
                f"{row[ 'parent_id_name' ]}\t"
                f"{row[ 'child_1_id' ]}\t"
                f"{row[ 'child_1_name' ]}\t"
                f"{row[ 'child_1_id_name' ]}\t"
                f"{row[ 'child_2_id' ]}\t"
                f"{row[ 'child_2_name' ]}\t"
                f"{row[ 'child_2_id_name' ]}\n"
            )
            output_file.write( output )

    total_parent_sibling_rows += len( parent_sibling_rows )

    # ----------------------------------------------------------------
    # Extract Parent-Child Relationships (4-column format)
    # ----------------------------------------------------------------

    parent_child_rows = extract_parent_child_rows( tree_root )

    # Sort rows by parent clade ID numerically, then by child clade ID
    parent_child_rows.sort( key=lambda row: (
        ( 0, int( row[ 'parent_id' ][ 1: ] ) ) if row[ 'parent_id' ] and row[ 'parent_id' ].startswith( 'C' ) and row[ 'parent_id' ][ 1: ].isdigit() else ( 1, 0 ),
        ( 0, int( row[ 'child_id' ][ 1: ] ) ) if row[ 'child_id' ] and row[ 'child_id' ].startswith( 'C' ) and row[ 'child_id' ][ 1: ].isdigit() else ( 1, 0 )
    ) )

    output_parent_child_file = output_parent_child_dir / f"5_ai-{structure_id}_parent_child_relationships.tsv"

    with open( output_parent_child_file, 'w' ) as output_file:
        # Write header
        header = (
            'Parent_ID (clade identifier of the parent node)\t'
            'Parent_Name (clade name of the parent node)\t'
            'Child_ID (clade identifier of the child node)\t'
            'Child_Name (clade name of the child node)\n'
        )
        output_file.write( header )

        for row in parent_child_rows:
            output = (
                f"{row[ 'parent_id' ]}\t"
                f"{row[ 'parent_name' ]}\t"
                f"{row[ 'child_id' ]}\t"
                f"{row[ 'child_name' ]}\n"
            )
            output_file.write( output )

    total_parent_child_rows += len( parent_child_rows )

    structures_processed += 1

    # Show progress for first 10 and last 5
    total_structures = len( newick_files )
    if structure_number <= 10 or structure_number > total_structures - 5:
        leaf_count = sum( 1 for node in all_nodes if node.is_leaf() )
        internal_count = sum( 1 for node in all_nodes if not node.is_leaf() )
        print( f"  {structure_id}: {len( parent_sibling_rows )} parent-sibling rows, "
               f"{len( parent_child_rows )} parent-child rows "
               f"({leaf_count} leaves, {internal_count} internal)" )
    elif structure_number == 11:
        print( f"  ... (structures 011-{total_structures - 5:03d}) ..." )

print()


# ============================================================================
# STEP 3: Validate and Report
# ============================================================================

if structures_processed == 0:
    print( "CRITICAL ERROR: No tree structures were successfully processed!" )
    print( "Check that script 004 produced properly formatted Newick files." )
    sys.exit( 1 )

print( "=" * 80 )
print( "SCRIPT 005 COMPLETE" )
print( "=" * 80 )
print()
print( f"Structures processed: {structures_processed}" )
print( f"Total parent-sibling rows: {total_parent_sibling_rows}" )
print( f"Total parent-child rows: {total_parent_child_rows}" )
print()
print( f"Output directories:" )
print( f"  Parent-Sibling Sets:         {output_parent_sibling_dir.name}/" )
print( f"    ({structures_processed} files, 9-column format)" )
print( f"  Parent-Child Relationships:  {output_parent_child_dir.name}/" )
print( f"    ({structures_processed} files, 4-column format)" )
print()
print( "Next step: Run script 006 to generate phylogenetic blocks" )
print()
