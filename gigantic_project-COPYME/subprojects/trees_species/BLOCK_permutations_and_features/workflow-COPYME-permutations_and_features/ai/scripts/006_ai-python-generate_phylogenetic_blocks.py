#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 16 | Purpose: Aggregate phylogenetic blocks across all structures with C000_OOL root parent edge
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 006: Generate Phylogenetic Blocks

Purpose:
    Aggregate per-structure phylogenetic blocks produced by Script 005 into a
    combined across-structures table, and emit a per-structure phylogenetic
    blocks file that additionally carries the Structure_ID column.

    Per Rule 7 a phylogenetic block is a parent::child edge in a species tree.
    Each binary internal node contributes one block per child. The species-
    tree root has no parent in the user-provided tree, but biologically every
    real clade descends from OOL (Origin Of Life). C000_OOL is therefore
    included as the conceptual parent of the root, giving the root clade an
    incoming block like every other clade:
        C000_OOL::<root_clade_id_name>     (e.g. C000_OOL::C071_Basal)

    Tip self-loops are NOT present in Script 005 output and are not
    reintroduced here.

Inputs:
    --workflow-dir: Workflow root directory
    Reads: START_HERE-user_config.yaml (for species_set_name)
           OUTPUT_pipeline/5-output/{species_set_name}_Parent_Child_Relationships/
               5_ai-structure_XXX_parent_child_relationships.tsv
           (3 columns: Phylogenetic_Block, Parent_Clade_ID_Name, Child_Clade_ID_Name)

Outputs:
    OUTPUT_pipeline/6-output/6_ai-structure_XXX_phylogenetic_blocks.tsv
        (per structure; includes C000_OOL::root block)
    OUTPUT_pipeline/6-output/6_ai-phylogenetic_blocks-all_{N}_structures.tsv
        (combined across all structures)

    Column structure (Rule 6 atomic identifiers + Rule 7 block framing):
        Structure_ID             tree topology structure identifier
        Phylogenetic_Block       atomic block identifier
                                 Parent_Clade_ID_Name::Child_Clade_ID_Name
        Parent_Clade_ID_Name     atomic parent clade identifier
        Child_Clade_ID_Name      atomic child clade identifier
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
input_parent_child_dir = output_pipeline_dir / '5-output' / f"{species_set_name}_Parent_Child_Relationships"
output_dir = output_pipeline_dir / '6-output'
output_dir.mkdir( parents=True, exist_ok=True )

print( "=" * 80 )
print( "SCRIPT 006: Generate Phylogenetic Blocks" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print( f"Input directory: {input_parent_child_dir}" )
print( f"Output directory: {output_dir}" )
print()


# ============================================================================
# STEP 1: Find and Sort Input Parent-Child Files
# ============================================================================

print( "Finding per-structure parent-child relationship files from script 005..." )

if not input_parent_child_dir.exists():
    print( f"CRITICAL ERROR: Input directory not found: {input_parent_child_dir}" )
    print( "Script 005 must complete before running script 006." )
    sys.exit( 1 )

# Script 005 outputs files named: 5_ai-structure_XXX_parent_child_relationships.tsv
parent_child_files = sorted( input_parent_child_dir.glob( '5_ai-structure_*_parent_child_relationships.tsv' ) )

if not parent_child_files:
    print( f"CRITICAL ERROR: No parent-child relationship files found in: {input_parent_child_dir}" )
    print( "Expected pattern: 5_ai-structure_XXX_parent_child_relationships.tsv" )
    sys.exit( 1 )

print( f"  Found {len( parent_child_files )} parent-child relationship files" )
print()


# ============================================================================
# STEP 2: Define Output Header
# ============================================================================

# OOL (Origin Of Life) as the conceptual biological parent of the species-tree
# root clade. Every real clade descends from OOL; including C000_OOL in the
# parent_child / phylogenetic_blocks framework gives the root clade a parent
# so origin-at-root orthogroups have a well-defined origin block
# C000_OOL::<root_clade_id_name>.
ool_clade_id_name = 'C000_OOL'

output_header = (
    'Structure_ID (tree topology structure identifier)'
    + '\t' + 'Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)'
    + '\t' + 'Parent_Clade_ID_Name (atomic parent clade identifier e.g. C082_Metazoa)'
    + '\t' + 'Child_Clade_ID_Name (atomic child clade identifier e.g. C086_Ctenophora)'
    + '\n'
)


# ============================================================================
# STEP 3: Process Each Structure
# ============================================================================

print( "Processing per-structure parent-child relationships to generate phylogenetic blocks..." )
print()

all_blocks_rows = []
structure_count = 0
total_blocks_count = 0

for parent_child_file in parent_child_files:

    # Extract structure ID from filename: 5_ai-structure_XXX_parent_child_relationships.tsv
    filename = parent_child_file.stem
    structure_id = None

    if 'structure_' in filename:
        start_index = filename.index( 'structure_' )
        remainder = filename[ start_index: ]
        parts_remainder = remainder.split( '_' )
        if len( parts_remainder ) >= 2 and parts_remainder[ 1 ].isdigit():
            structure_id = f"structure_{parts_remainder[ 1 ]}"

    if not structure_id:
        print( f"  WARNING: Could not extract structure ID from: {parent_child_file.name}" )
        continue

    structure_number = int( structure_id.replace( 'structure_', '' ) )
    structure_count += 1
    structure_block_rows = []

    # Script 005 parent-child relationships format (3 columns):
    # Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)	Parent_Clade_ID_Name (atomic parent clade identifier e.g. C082_Metazoa)	Child_Clade_ID_Name (atomic child clade identifier e.g. C086_Ctenophora)
    # C082_Metazoa::C086_Ctenophora	C082_Metazoa	C086_Ctenophora

    parent_clade_id_names: Set[ str ] = set()
    child_clade_id_names: Set[ str ] = set()
    rows = []

    with open( parent_child_file, 'r' ) as input_file:
        header_line = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 3:
                continue

            phylogenetic_block = parts[ 0 ]
            parent_clade_id_name = parts[ 1 ]
            child_clade_id_name = parts[ 2 ]

            rows.append( {
                'phylogenetic_block': phylogenetic_block,
                'parent_clade_id_name': parent_clade_id_name,
                'child_clade_id_name': child_clade_id_name,
            } )

            parent_clade_id_names.add( parent_clade_id_name )
            child_clade_id_names.add( child_clade_id_name )

    # Note: C000_OOL::<root_clade_id_name> is already emitted by Script 005
    # (see extract_parent_child_relationships) and arrives through `rows` below,
    # so Script 006 does not synthesize the root block itself.

    # Emit one output row per input block row (pass-through with Structure_ID prepended)
    for row in rows:
        block_row = (
            structure_id
            + '\t' + row[ 'phylogenetic_block' ]
            + '\t' + row[ 'parent_clade_id_name' ]
            + '\t' + row[ 'child_clade_id_name' ]
        )
        structure_block_rows.append( block_row )

    # Write per-structure file
    output_structure_file = output_dir / f"6_ai-{structure_id}_phylogenetic_blocks.tsv"

    with open( output_structure_file, 'w' ) as output_file:
        output_file.write( output_header )
        for block_row in structure_block_rows:
            output = block_row + '\n'
            output_file.write( output )

    # Accumulate for combined file
    all_blocks_rows.extend( structure_block_rows )
    total_blocks_count += len( structure_block_rows )

    # Show progress for first 10 and last 5
    total_structures = len( parent_child_files )
    if structure_number <= 10 or structure_number > total_structures - 5:
        # Report the species-tree root as the child endpoint of any C000_OOL::<root> row
        ool_children = sorted( {
            row.split( '\t', 4 )[ 3 ] for row in structure_block_rows
            if row.split( '\t', 4 )[ 2 ] == ool_clade_id_name
        } )
        root_names = ', '.join( ool_children ) if ool_children else 'none found'
        print( f"  {structure_id}: {len( structure_block_rows )} blocks (root: {root_names})" )
    elif structure_number == 11:
        print( f"  ... (structures 011-{total_structures - 5:03d}) ..." )

print()


# ============================================================================
# STEP 4: Write Combined File
# ============================================================================

if structure_count == 0:
    print( "CRITICAL ERROR: No tree structures were successfully processed!" )
    print( "Check that script 005 produced properly formatted parent-child relationship files." )
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
