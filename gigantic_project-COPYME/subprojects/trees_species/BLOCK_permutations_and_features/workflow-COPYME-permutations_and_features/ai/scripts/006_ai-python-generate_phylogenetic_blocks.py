#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Generate phylogenetic blocks for all tree structures
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 006: Generate Phylogenetic Blocks

Purpose:
    Generate phylogenetic blocks for all tree structures. A phylogenetic block
    represents a branch in the tree, identified by the Parent::Child notation
    (e.g., C068_Metazoa::C069_Bilateria).

    Each internal node in a binary tree produces exactly 2 phylogenetic blocks
    (one for each child). For the tree root (which has no parent), a synthetic
    C000_Pre_Basal parent is used, creating blocks like:
    C000_Pre_Basal::C079_All_Life

    Leaf nodes that are self-referential (parent = child_1 = child_2 in the
    parent-sibling table) are skipped as they have no descendant branches.

Inputs:
    --workflow-dir: Workflow root directory
    Reads: START_HERE-user_config.yaml (for species_set_name)
           OUTPUT_pipeline/5-output/{species_set_name}_Parent_Sibling_Sets/
               5_ai-structure_XXX_parent_child_table.tsv (9-column format)

Outputs:
    OUTPUT_pipeline/6-output/6_ai-phylogenetic_blocks-all_{N}_structures.tsv (combined)
    OUTPUT_pipeline/6-output/6_ai-structure_XXX_phylogenetic_blocks.tsv (per structure)
"""

from pathlib import Path
from typing import List, Set
import argparse
import sys
import yaml


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 006: Generate phylogenetic blocks for all tree structures' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    return parser.parse_args()


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
input_parent_sibling_dir = output_pipeline_dir / '5-output' / f"{species_set_name}_Parent_Sibling_Sets"
output_dir = output_pipeline_dir / '6-output'
output_dir.mkdir( parents=True, exist_ok=True )

print( "=" * 80 )
print( "SCRIPT 006: Generate Phylogenetic Blocks" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print( f"Input directory: {input_parent_sibling_dir}" )
print( f"Output directory: {output_dir}" )
print()


# ============================================================================
# STEP 1: Find and Sort Input Parent-Sibling Files
# ============================================================================

print( "Finding parent-sibling table files from script 005..." )

if not input_parent_sibling_dir.exists():
    print( f"CRITICAL ERROR: Input directory not found: {input_parent_sibling_dir}" )
    print( "Script 005 must complete before running script 006." )
    sys.exit( 1 )

# Script 005 outputs files named: 5_ai-structure_XXX_parent_child_table.tsv
parent_sibling_files = sorted( input_parent_sibling_dir.glob( '5_ai-structure_*_parent_child_table.tsv' ) )

if not parent_sibling_files:
    print( f"CRITICAL ERROR: No parent-sibling table files found in: {input_parent_sibling_dir}" )
    print( "Expected pattern: 5_ai-structure_XXX_parent_child_table.tsv" )
    sys.exit( 1 )

print( f"  Found {len( parent_sibling_files )} parent-sibling table files" )
print()


# ============================================================================
# STEP 2: Define Output Header
# ============================================================================

# Pre-basal synthetic parent for root-level nodes
pre_basal_id = 'C000'
pre_basal_name = 'Pre_Basal'
pre_basal_id_name = 'C000_Pre_Basal'

output_header = (
    'Structure_ID (tree topology structure identifier)'
    + '\t' + 'Clade_ID (clade identifier for the child in this block)'
    + '\t' + 'Clade_Name (clade name for the child in this block)'
    + '\t' + 'Clade_ID_Name (full child clade identifier and name)'
    + '\t' + 'Parent_Clade_ID (clade identifier for the parent in this block)'
    + '\t' + 'Parent_Clade_Name (clade name for the parent in this block)'
    + '\t' + 'Parent_Clade_ID_Name (full parent clade identifier and name)'
    + '\t' + 'Phylogenetic_Block_Name (block name as Parent_Name::Child_Name)'
    + '\t' + 'Phylogenetic_Block_ID (block identifier as Parent_ID::Child_ID)'
    + '\t' + 'Phylogenetic_Block_ID_Name (block as Parent_ID_Name::Child_ID_Name)'
    + '\n'
)


# ============================================================================
# STEP 3: Process Each Structure
# ============================================================================

print( "Processing parent-sibling tables to generate phylogenetic blocks..." )
print()

all_blocks_rows = []
structure_count = 0
total_blocks_count = 0

for parent_sibling_file in parent_sibling_files:

    # Extract structure ID from filename: 5_ai-structure_XXX_parent_child_table.tsv
    filename = parent_sibling_file.stem
    structure_id = None

    if 'structure_' in filename:
        start_index = filename.index( 'structure_' )
        remainder = filename[ start_index: ]
        parts_remainder = remainder.split( '_' )
        if len( parts_remainder ) >= 2 and parts_remainder[ 1 ].isdigit():
            structure_id = f"structure_{parts_remainder[ 1 ]}"

    if not structure_id:
        print( f"  WARNING: Could not extract structure ID from: {parent_sibling_file.name}" )
        continue

    structure_number = int( structure_id.replace( 'structure_', '' ) )
    structure_count += 1
    structure_blocks = []

    # Script 005 parent-sibling format (9 columns):
    # Parent_ID (clade identifier of the parent node)	Parent_Name (clade name of the parent node)	Parent_ID_Name (full clade identifier and name of the parent node)	Child_1_ID (clade identifier of the first child node)	Child_1_Name (clade name of the first child node)	Child_1_ID_Name (full clade identifier and name of the first child node)	Child_2_ID (clade identifier of the second child node)	Child_2_Name (clade name of the second child node)	Child_2_ID_Name (full clade identifier and name of the second child node)
    # C068	Basal	C068_Basal	C066	Holozoa	C066_Holozoa	C067	Holomycota	C067_Holomycota

    # Track which nodes appear as parents and children to find root
    all_parent_id_names: Set[ str ] = set()
    all_child_id_names: Set[ str ] = set()

    rows = []

    with open( parent_sibling_file, 'r' ) as input_file:
        header_line = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 9:
                continue

            parent_id = parts[ 0 ]
            parent_name = parts[ 1 ]
            parent_id_name = parts[ 2 ]
            child_1_id = parts[ 3 ]
            child_1_name = parts[ 4 ]
            child_1_id_name = parts[ 5 ]
            child_2_id = parts[ 6 ]
            child_2_name = parts[ 7 ]
            child_2_id_name = parts[ 8 ]

            # Skip self-referential entries (leaf nodes: parent = child_1 = child_2)
            is_leaf = ( parent_id_name == child_1_id_name and parent_id_name == child_2_id_name )

            if is_leaf:
                continue

            rows.append( {
                'parent_id': parent_id,
                'parent_name': parent_name,
                'parent_id_name': parent_id_name,
                'child_1_id': child_1_id,
                'child_1_name': child_1_name,
                'child_1_id_name': child_1_id_name,
                'child_2_id': child_2_id,
                'child_2_name': child_2_name,
                'child_2_id_name': child_2_id_name,
            } )

            all_parent_id_names.add( parent_id_name )
            all_child_id_names.add( child_1_id_name )
            all_child_id_names.add( child_2_id_name )

    # Root detection: the node that appears as parent but never as child
    root_id_names = all_parent_id_names - all_child_id_names

    # Generate blocks from each internal node row
    for row in rows:
        parent_id = row[ 'parent_id' ]
        parent_name = row[ 'parent_name' ]
        parent_id_name = row[ 'parent_id_name' ]

        # Block 1: Parent → Child_1
        block_1_name = parent_name + '::' + row[ 'child_1_name' ]
        block_1_id = parent_id + '::' + row[ 'child_1_id' ]
        block_1_id_name = parent_id_name + '::' + row[ 'child_1_id_name' ]

        block_1_row = (
            structure_id
            + '\t' + row[ 'child_1_id' ]
            + '\t' + row[ 'child_1_name' ]
            + '\t' + row[ 'child_1_id_name' ]
            + '\t' + parent_id
            + '\t' + parent_name
            + '\t' + parent_id_name
            + '\t' + block_1_name
            + '\t' + block_1_id
            + '\t' + block_1_id_name
        )
        structure_blocks.append( block_1_row )

        # Block 2: Parent → Child_2
        block_2_name = parent_name + '::' + row[ 'child_2_name' ]
        block_2_id = parent_id + '::' + row[ 'child_2_id' ]
        block_2_id_name = parent_id_name + '::' + row[ 'child_2_id_name' ]

        block_2_row = (
            structure_id
            + '\t' + row[ 'child_2_id' ]
            + '\t' + row[ 'child_2_name' ]
            + '\t' + row[ 'child_2_id_name' ]
            + '\t' + parent_id
            + '\t' + parent_name
            + '\t' + parent_id_name
            + '\t' + block_2_name
            + '\t' + block_2_id
            + '\t' + block_2_id_name
        )
        structure_blocks.append( block_2_row )

    # Add synthetic Pre_Basal block for each root node
    for root_id_name in root_id_names:
        # Find root's ID and name from the rows
        root_id = ''
        root_name = ''
        for row in rows:
            if row[ 'parent_id_name' ] == root_id_name:
                root_id = row[ 'parent_id' ]
                root_name = row[ 'parent_name' ]
                break

        root_block_name = pre_basal_name + '::' + root_name
        root_block_id = pre_basal_id + '::' + root_id
        root_block_id_name = pre_basal_id_name + '::' + root_id_name

        root_block_row = (
            structure_id
            + '\t' + root_id
            + '\t' + root_name
            + '\t' + root_id_name
            + '\t' + pre_basal_id
            + '\t' + pre_basal_name
            + '\t' + pre_basal_id_name
            + '\t' + root_block_name
            + '\t' + root_block_id
            + '\t' + root_block_id_name
        )
        structure_blocks.insert( 0, root_block_row )

    # Write per-structure file
    output_structure_file = output_dir / f"6_ai-{structure_id}_phylogenetic_blocks.tsv"

    with open( output_structure_file, 'w' ) as output_file:
        output_file.write( output_header )
        for block_row in structure_blocks:
            output = block_row + '\n'
            output_file.write( output )

    # Accumulate for combined file
    all_blocks_rows.extend( structure_blocks )
    total_blocks_count += len( structure_blocks )

    # Show progress for first 10 and last 5
    total_structures = len( parent_sibling_files )
    if structure_number <= 10 or structure_number > total_structures - 5:
        root_names = ', '.join( root_id_names ) if root_id_names else 'none found'
        print( f"  {structure_id}: {len( structure_blocks )} blocks (root: {root_names})" )
    elif structure_number == 11:
        print( f"  ... (structures 011-{total_structures - 5:03d}) ..." )

print()


# ============================================================================
# STEP 4: Write Combined File
# ============================================================================

if structure_count == 0:
    print( "CRITICAL ERROR: No tree structures were successfully processed!" )
    print( "Check that script 005 produced properly formatted parent-sibling tables." )
    sys.exit( 1 )

output_combined_file = output_dir / f"6_ai-phylogenetic_blocks-all_{structure_count}_structures.tsv"

print( "Writing combined phylogenetic blocks file..." )

with open( output_combined_file, 'w' ) as output_file:
    output_file.write( output_header )
    for block_row in all_blocks_rows:
        output = block_row + '\n'
        output_file.write( output )

print( f"  {output_combined_file.name}" )
print()


# ============================================================================
# STEP 5: Validate Output
# ============================================================================

print( "Validating outputs..." )

output_structure_files = sorted( output_dir.glob( '6_ai-structure_*_phylogenetic_blocks.tsv' ) )

if len( output_structure_files ) != structure_count:
    print( f"CRITICAL ERROR: Expected {structure_count} per-structure files, found {len( output_structure_files )}" )
    sys.exit( 1 )

print( f"  [OK] {len( output_structure_files )} per-structure files created" )

# Validate combined file row count
combined_row_count = 0
with open( output_combined_file, 'r' ) as check_file:
    check_file.readline()  # skip header
    for line in check_file:
        if line.strip():
            combined_row_count += 1

if combined_row_count != total_blocks_count:
    print( f"CRITICAL ERROR: Combined file has {combined_row_count} rows but expected {total_blocks_count}" )
    sys.exit( 1 )

print( f"  [OK] Combined file has {combined_row_count} rows (matches expected {total_blocks_count})" )
print()


# ============================================================================
# Summary
# ============================================================================

print( "=" * 80 )
print( "SCRIPT 006 COMPLETE" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print( f"Structures processed: {structure_count}" )
print( f"Total phylogenetic blocks: {total_blocks_count}" )
if structure_count > 0:
    average_blocks = total_blocks_count / structure_count
    print( f"Average blocks per structure: {average_blocks:.1f}" )
print()
print( "Output files:" )
print( f"  Per-structure: {len( output_structure_files )} files in {output_dir.name}/" )
print( f"  Combined: {output_combined_file.name}" )
print()
print( "Next step: Run script 007 to integrate all clade data" )
print()
