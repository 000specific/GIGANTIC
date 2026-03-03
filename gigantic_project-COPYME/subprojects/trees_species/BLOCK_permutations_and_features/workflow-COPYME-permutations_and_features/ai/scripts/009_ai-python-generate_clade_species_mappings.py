#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Generate clade-to-species mappings for all structures
# Human: Eric Edsinger

"""
GIGANTIC trees_species - Script 009: Generate Clade Species Mappings

Purpose:
    For each clade in each structure, identify all descendant species.

    A species descends from a clade if the clade appears in the species'
    phylogenetic path. This script builds a comprehensive mapping table
    showing which species belong to each clade across all topology
    permutations.

    Additionally computes:
    - Descendant species count per clade
    - Descendant species list (comma-separated genus_species)
    - Descendant species paths (paths from the clade to each descendant species)
    - All descendant nodes (all nodes below this clade, not just species)

    Paths and clade types are derived from the integrated clade data produced
    by script 007. Phylogenetic block ID_Names come from the blocks file
    produced by script 006.

Inputs:
    --workflow-dir: Workflow root directory

    Reads:
    - OUTPUT_pipeline/6-output/6_ai-phylogenetic_blocks-all_*_structures.tsv
    - OUTPUT_pipeline/7-output/7_ai-integrated_clade_data-all_structures.tsv

Outputs:
    OUTPUT_pipeline/9-output/9_ai-clade_species_mappings-all_structures.tsv
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse
import sys
import re
import yaml


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser( description='Script 009: Generate clade-to-species mappings' )
    parser.add_argument( '--workflow-dir', required=True, help='Workflow root directory' )
    return parser.parse_args()


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
input_dir_6 = output_pipeline_dir / '6-output'
input_dir_7 = output_pipeline_dir / '7-output'
output_dir = output_pipeline_dir / '9-output'
output_dir.mkdir( parents=True, exist_ok=True )

output_clade_species_mappings = output_dir / '9_ai-clade_species_mappings-all_structures.tsv'

print( "=" * 80 )
print( "SCRIPT 009: Generate Clade Species Mappings" )
print( "=" * 80 )
print()
print( f"Species set: {species_set_name}" )
print()


# ============================================================================
# STEP 1: Read Integrated Clade Data (7-output)
# ============================================================================

print( "Reading integrated clade data from 7-output..." )

input_integrated_data_path = input_dir_7 / '7_ai-integrated_clade_data-all_structures.tsv'

if not input_integrated_data_path.exists():
    print( f"CRITICAL ERROR: Integrated clade data file not found: {input_integrated_data_path}" )
    print( "Run script 007 first." )
    sys.exit( 1 )

# Build comprehensive lookup from integrated data
# (structure_id, clade_id) -> { clade_name, clade_id_name, clade_type, phylogenetic_path }
structure_clade_pairs___clade_data = {}
# Track all clades per structure
structure_ids___clade_ids = {}
# Track species per structure
structure_ids___species_clade_ids = {}

# Read header to find column indices
with open( input_integrated_data_path, 'r' ) as input_file:
    header_line = input_file.readline().strip()
    header_columns = header_line.split( '\t' )

    # Map column names to indices
    column_names___indices = {}
    for column_index, column_header in enumerate( header_columns ):
        column_name = column_header.split( '(' )[ 0 ].strip()
        column_names___indices[ column_name ] = column_index

    structure_id_column_index = column_names___indices.get( 'Structure_ID', 0 )
    clade_id_column_index = column_names___indices.get( 'Clade_ID', 1 )
    clade_name_column_index = column_names___indices.get( 'Clade_Name', 2 )
    clade_id_name_column_index = column_names___indices.get( 'Clade_ID_Name', 3 )
    clade_type_column_index = column_names___indices.get( 'Clade_Type', 4 )
    phylogenetic_path_column_index = column_names___indices.get( 'Phylogenetic_Path', 11 )

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )

        structure_id = parts[ structure_id_column_index ] if len( parts ) > structure_id_column_index else ''
        clade_id = parts[ clade_id_column_index ] if len( parts ) > clade_id_column_index else ''
        clade_name = parts[ clade_name_column_index ] if len( parts ) > clade_name_column_index else ''
        clade_id_name = parts[ clade_id_name_column_index ] if len( parts ) > clade_id_name_column_index else ''
        clade_type = parts[ clade_type_column_index ] if len( parts ) > clade_type_column_index else ''
        phylogenetic_path = parts[ phylogenetic_path_column_index ] if len( parts ) > phylogenetic_path_column_index else ''

        if structure_id and clade_id:
            structure_clade_pairs___clade_data[ ( structure_id, clade_id ) ] = {
                'clade_name': clade_name,
                'clade_id_name': clade_id_name,
                'clade_type': clade_type,
                'phylogenetic_path': phylogenetic_path
            }

            # Track clades per structure
            if structure_id not in structure_ids___clade_ids:
                structure_ids___clade_ids[ structure_id ] = []
            structure_ids___clade_ids[ structure_id ].append( clade_id )

            # Track species per structure
            if clade_type == 'species':
                if structure_id not in structure_ids___species_clade_ids:
                    structure_ids___species_clade_ids[ structure_id ] = []
                structure_ids___species_clade_ids[ structure_id ].append( clade_id )

total_entries = len( structure_clade_pairs___clade_data )
total_structures = len( structure_ids___clade_ids )
species_count_example = len( next( iter( structure_ids___species_clade_ids.values() ) ) ) if structure_ids___species_clade_ids else 0

print( f"  Loaded {total_entries} clade entries across {total_structures} structures" )
print( f"  Species per structure (example): {species_count_example}" )
print()


# ============================================================================
# STEP 2: Read Phylogenetic Blocks (6-output) for Block ID_Name
# ============================================================================

print( "Reading phylogenetic blocks from 6-output..." )

# The combined blocks file has the count embedded in the name
phylogenetic_blocks_files = sorted( input_dir_6.glob( '6_ai-phylogenetic_blocks-all_*_structures.tsv' ) )

if not phylogenetic_blocks_files:
    print( f"CRITICAL ERROR: No combined phylogenetic blocks file found in {input_dir_6}" )
    print( "  Expected pattern: 6_ai-phylogenetic_blocks-all_*_structures.tsv" )
    print( "Run script 006 first." )
    sys.exit( 1 )

input_phylogenetic_blocks_path = phylogenetic_blocks_files[ 0 ]
print( f"  Using: {input_phylogenetic_blocks_path.name}" )

# Build lookup: (structure_id, clade_id) -> block_id_name
structure_clade_pairs___block_id_names = {}

# Structure_ID (tree topology structure identifier)	Clade_ID (clade identifier for the child in this block)	...	Phylogenetic_Block_ID_Name (block as Parent_ID_Name::Child_ID_Name)
# structure_001	C068	Root	C068_Root	C000	Pre_Root	C000_Pre_Root	Pre_Root::Root	C000::C068	C000_Pre_Root::C068_Root
with open( input_phylogenetic_blocks_path, 'r' ) as input_file:
    header_line = input_file.readline().strip()
    header_columns = header_line.split( '\t' )

    # Map column names to indices
    column_names___indices = {}
    for column_index, column_header in enumerate( header_columns ):
        column_name = column_header.split( '(' )[ 0 ].strip()
        column_names___indices[ column_name ] = column_index

    structure_id_column_index = column_names___indices.get( 'Structure_ID', 0 )
    clade_id_column_index = column_names___indices.get( 'Clade_ID', 1 )
    block_id_name_column_index = column_names___indices.get( 'Phylogenetic_Block_ID_Name', None )

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )

        structure_id = parts[ structure_id_column_index ] if len( parts ) > structure_id_column_index else ''
        clade_id = parts[ clade_id_column_index ] if len( parts ) > clade_id_column_index else ''
        block_id_name = parts[ block_id_name_column_index ] if block_id_name_column_index is not None and len( parts ) > block_id_name_column_index else ''

        if structure_id and clade_id:
            structure_clade_pairs___block_id_names[ ( structure_id, clade_id ) ] = block_id_name

print( f"  Loaded {len( structure_clade_pairs___block_id_names )} phylogenetic block entries" )
print()


# ============================================================================
# STEP 3: Compute Clade-Species Mappings
# ============================================================================

print( "Computing clade-to-species mappings..." )
print()

# For each clade in each structure, find all descendant species.
# A species descends from a clade if the clade's clade_id_name appears
# in the species' phylogenetic path.

mapping_rows = []
structures_processed = 0

for structure_id in sorted( structure_ids___clade_ids.keys() ):
    structures_processed += 1
    structure_number = int( re.search( r'\d+', structure_id ).group() ) if re.search( r'\d+', structure_id ) else 0

    all_clade_ids_in_structure = structure_ids___clade_ids[ structure_id ]
    species_clade_ids_in_structure = structure_ids___species_clade_ids.get( structure_id, [] )

    for clade_id in sorted( all_clade_ids_in_structure, key=lambda x: int( x[ 1: ] ) if x[ 1: ].isdigit() else 99999 ):
        clade_data = structure_clade_pairs___clade_data[ ( structure_id, clade_id ) ]
        clade_name = clade_data[ 'clade_name' ]
        clade_id_name = clade_data[ 'clade_id_name' ]

        # Find all descendant species and all descendant nodes
        descendant_species_list = []
        descendant_species_paths = []
        all_descendant_node_ids = []

        for other_clade_id in all_clade_ids_in_structure:
            if other_clade_id == clade_id:
                continue

            other_clade_data = structure_clade_pairs___clade_data[ ( structure_id, other_clade_id ) ]
            other_phylogenetic_path = other_clade_data[ 'phylogenetic_path' ]
            path_elements = other_phylogenetic_path.split( ',' )

            # Check if target clade's clade_id_name appears in this node's path
            if clade_id_name in path_elements:
                # This node is a descendant of clade_id
                all_descendant_node_ids.append( other_clade_id )

                # Check if this descendant is a species (leaf)
                if other_clade_data[ 'clade_type' ] == 'species':
                    genus_species = other_clade_data[ 'clade_name' ]
                    descendant_species_list.append( genus_species )

                    # Trim the path: from this clade to the descendant species
                    clade_position_in_path = path_elements.index( clade_id_name )
                    trimmed_path_elements = path_elements[ clade_position_in_path: ]
                    trimmed_path = '>'.join( trimmed_path_elements )
                    descendant_species_paths.append( trimmed_path )

        # Sort species and paths alphabetically by species name
        species_path_pairs = list( zip( descendant_species_list, descendant_species_paths ) )
        species_path_pairs.sort( key=lambda pair: pair[ 0 ] )

        if species_path_pairs:
            sorted_species = [ pair[ 0 ] for pair in species_path_pairs ]
            sorted_paths = [ pair[ 1 ] for pair in species_path_pairs ]
        else:
            sorted_species = []
            sorted_paths = []

        # Sort descendant node IDs numerically
        all_descendant_node_ids.sort( key=lambda x: int( x[ 1: ] ) if x[ 1: ].isdigit() else 99999 )

        # Get phylogenetic block ID_Name for this clade
        block_id_name = structure_clade_pairs___block_id_names.get( ( structure_id, clade_id ), '' )

        # Build row
        descendant_species_count = len( sorted_species )
        descendant_species_list_string = ','.join( sorted_species )
        descendant_species_paths_string = ','.join( sorted_paths )
        all_descendant_nodes_string = ','.join( all_descendant_node_ids )

        row = {
            'Structure_ID': structure_id,
            'Clade_ID': clade_id,
            'Clade_Name': clade_name,
            'Clade_ID_Name': clade_id_name,
            'Phylogenetic_Block_ID_Name': block_id_name,
            'Descendant_Species_Count': str( descendant_species_count ),
            'Descendant_Species_List': descendant_species_list_string,
            'Descendant_Species_Paths': descendant_species_paths_string,
            'All_Descendant_Nodes': all_descendant_nodes_string
        }

        mapping_rows.append( row )

    # Progress reporting
    if structure_number <= 10 or structure_number > total_structures - 5:
        species_count = len( species_clade_ids_in_structure )
        clades_count = len( all_clade_ids_in_structure )
        print( f"  {structure_id}: {clades_count} clades, {species_count} species" )
    elif structure_number == 11:
        print( f"  ... (processing structures 011-{total_structures - 5:03d}) ..." )

print()
print( f"  Total mapping rows: {len( mapping_rows )}" )
print()


# ============================================================================
# STEP 4: Write Output
# ============================================================================

print( "Writing clade-species mappings..." )

# Define column headers with self-documenting format
column_headers = [
    'Structure_ID (topology structure identifier)',
    'Clade_ID (clade identifier)',
    'Clade_Name (clade name after identifier prefix)',
    'Clade_ID_Name (full clade identifier and name)',
    'Phylogenetic_Block_ID_Name (phylogenetic block identifier and name for parent to child transition)',
    'Descendant_Species_Count (count of species that descend from this clade)',
    'Descendant_Species_List (comma delimited genus_species names of descendant species)',
    'Descendant_Species_Paths (comma delimited paths from clade to each descendant species using greater than as path separator)',
    'All_Descendant_Nodes (comma delimited clade identifiers of all descendant nodes including internal and species)'
]

column_keys = [
    'Structure_ID', 'Clade_ID', 'Clade_Name', 'Clade_ID_Name',
    'Phylogenetic_Block_ID_Name', 'Descendant_Species_Count',
    'Descendant_Species_List', 'Descendant_Species_Paths',
    'All_Descendant_Nodes'
]

with open( output_clade_species_mappings, 'w' ) as output_file:
    # Write header
    header_output = '\t'.join( column_headers ) + '\n'
    output_file.write( header_output )

    # Write data rows
    for row in mapping_rows:
        values = [ str( row.get( key, '' ) ) for key in column_keys ]
        output = '\t'.join( values ) + '\n'
        output_file.write( output )

print( f"  {output_clade_species_mappings.name}" )
print()

# Summary statistics
unique_structures = set()
unique_clades = set()
max_descendant_count = 0
for row in mapping_rows:
    unique_structures.add( row[ 'Structure_ID' ] )
    unique_clades.add( row[ 'Clade_ID' ] )
    descendant_count = int( row[ 'Descendant_Species_Count' ] )
    if descendant_count > max_descendant_count:
        max_descendant_count = descendant_count

print( "=" * 80 )
print( "SCRIPT 009 COMPLETE" )
print( "=" * 80 )
print()
print( f"Total mapping rows: {len( mapping_rows )}" )
print( f"Unique structures: {len( unique_structures )}" )
print( f"Unique clades: {len( unique_clades )}" )
print( f"Maximum descendant species count: {max_descendant_count}" )
print( f"Columns: {len( column_headers )}" )
print()
print( f"Output file:" )
print( f"  {output_clade_species_mappings.name}" )
print()
print( "Pipeline complete! All 9 scripts have been executed." )
print()
