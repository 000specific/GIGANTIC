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
    by script 007. Phylogenetic block atomic identifiers (Rule 6 form)
    come from the blocks file produced by script 006.

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
config_path = workflow_dir / 'START_HERE-user_config.yaml'
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

# Build comprehensive lookup from integrated data (Rule 6 atomic keys):
# (structure_id, clade_id_name) -> { clade_type, phylogenetic_path }
structure_clade_pairs___clade_data = {}
# Track all clade_id_names per structure
structure_ids___clade_id_names = {}
# Track species clade_id_names per structure
structure_ids___species_clade_id_names = {}

# Read header to find column indices
with open( input_integrated_data_path, 'r' ) as input_file:
    header_line = input_file.readline().strip()
    header_columns = header_line.split( '\t' )

    column_names___indices = {}
    for column_index, column_header in enumerate( header_columns ):
        column_name = column_header.split( '(' )[ 0 ].strip()
        column_names___indices[ column_name ] = column_index

    structure_id_column_index = column_names___indices.get( 'Structure_ID' )
    clade_id_name_column_index = column_names___indices.get( 'Clade_ID_Name' )
    clade_type_column_index = column_names___indices.get( 'Clade_Type' )
    phylogenetic_path_column_index = column_names___indices.get( 'Phylogenetic_Path' )

    required = {
        'Structure_ID': structure_id_column_index,
        'Clade_ID_Name': clade_id_name_column_index,
        'Clade_Type': clade_type_column_index,
        'Phylogenetic_Path': phylogenetic_path_column_index,
    }
    missing = [ name for name, idx in required.items() if idx is None ]
    if missing:
        print( f"CRITICAL ERROR: Integrated clade data file missing required columns: {missing}" )
        print( f"  Found columns: {header_columns}" )
        sys.exit( 1 )

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )
        if len( parts ) <= max( required.values() ):
            continue

        structure_id = parts[ structure_id_column_index ]
        clade_id_name = parts[ clade_id_name_column_index ]
        clade_type = parts[ clade_type_column_index ]
        phylogenetic_path = parts[ phylogenetic_path_column_index ]

        if structure_id and clade_id_name:
            structure_clade_pairs___clade_data[ ( structure_id, clade_id_name ) ] = {
                'clade_type': clade_type,
                'phylogenetic_path': phylogenetic_path
            }

            if structure_id not in structure_ids___clade_id_names:
                structure_ids___clade_id_names[ structure_id ] = []
            structure_ids___clade_id_names[ structure_id ].append( clade_id_name )

            if clade_type == 'species':
                if structure_id not in structure_ids___species_clade_id_names:
                    structure_ids___species_clade_id_names[ structure_id ] = []
                structure_ids___species_clade_id_names[ structure_id ].append( clade_id_name )

total_entries = len( structure_clade_pairs___clade_data )
total_structures = len( structure_ids___clade_id_names )
species_count_example = len( next( iter( structure_ids___species_clade_id_names.values() ) ) ) if structure_ids___species_clade_id_names else 0

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

# Build lookup keyed by atomic clade_id_name (Rule 6):
# (structure_id, child_clade_id_name) -> phylogenetic_block
structure_clade_pairs___phylogenetic_blocks = {}

# Script 006 output format (4 columns):
# Structure_ID (tree topology structure identifier)	Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)	Parent_Clade_ID_Name (atomic parent clade identifier e.g. C082_Metazoa)	Child_Clade_ID_Name (atomic child clade identifier e.g. C086_Ctenophora)
# structure_001	C000_OOL::C071_Basal	C000_OOL	C071_Basal
with open( input_phylogenetic_blocks_path, 'r' ) as input_file:
    header_line = input_file.readline().strip()
    header_columns = header_line.split( '\t' )

    column_names___indices = {}
    for column_index, column_header in enumerate( header_columns ):
        column_name = column_header.split( '(' )[ 0 ].strip()
        column_names___indices[ column_name ] = column_index

    structure_id_column_index = column_names___indices.get( 'Structure_ID' )
    phylogenetic_block_column_index = column_names___indices.get( 'Phylogenetic_Block' )
    child_clade_id_name_column_index = column_names___indices.get( 'Child_Clade_ID_Name' )

    required = {
        'Structure_ID': structure_id_column_index,
        'Phylogenetic_Block': phylogenetic_block_column_index,
        'Child_Clade_ID_Name': child_clade_id_name_column_index,
    }
    missing = [ name for name, idx in required.items() if idx is None ]
    if missing:
        print( f"CRITICAL ERROR: Phylogenetic blocks file missing required columns: {missing}" )
        print( f"  Found columns: {header_columns}" )
        sys.exit( 1 )

    for line in input_file:
        line = line.strip()
        if not line:
            continue

        parts = line.split( '\t' )
        if len( parts ) <= max( required.values() ):
            continue

        structure_id = parts[ structure_id_column_index ]
        phylogenetic_block = parts[ phylogenetic_block_column_index ]
        child_clade_id_name = parts[ child_clade_id_name_column_index ]

        if structure_id and child_clade_id_name:
            structure_clade_pairs___phylogenetic_blocks[ ( structure_id, child_clade_id_name ) ] = phylogenetic_block

print( f"  Loaded {len( structure_clade_pairs___phylogenetic_blocks )} phylogenetic block entries" )
print()


# ============================================================================
# STEP 3: Compute Clade-Species Mappings
# ============================================================================

print( "Computing clade-to-species mappings..." )
print()

# For each clade in each structure, find all descendant species.
# A species descends from a clade if the clade's clade_id_name appears
# in the species' phylogenetic path.

# Sort key: extract numeric Cxxx prefix of a clade_id_name for ordering.
def clade_id_name_sort_key( clade_id_name ):
    if clade_id_name and clade_id_name.startswith( 'C' ):
        prefix = clade_id_name.split( '_', 1 )[ 0 ]
        if prefix[ 1: ].isdigit():
            return int( prefix[ 1: ] )
    return 99999

mapping_rows = []
structures_processed = 0

for structure_id in sorted( structure_ids___clade_id_names.keys() ):
    structures_processed += 1
    structure_number = int( re.search( r'\d+', structure_id ).group() ) if re.search( r'\d+', structure_id ) else 0

    all_clade_id_names_in_structure = structure_ids___clade_id_names[ structure_id ]
    species_clade_id_names_in_structure = structure_ids___species_clade_id_names.get( structure_id, [] )

    for clade_id_name in sorted( all_clade_id_names_in_structure, key=clade_id_name_sort_key ):
        clade_data = structure_clade_pairs___clade_data[ ( structure_id, clade_id_name ) ]

        # Find all descendant species and all descendant nodes (Rule 6 atomic identifiers)
        descendant_species_list = []
        descendant_species_paths = []
        all_descendant_clade_id_names = []

        for other_clade_id_name in all_clade_id_names_in_structure:
            if other_clade_id_name == clade_id_name:
                continue

            other_clade_data = structure_clade_pairs___clade_data[ ( structure_id, other_clade_id_name ) ]
            other_phylogenetic_path = other_clade_data[ 'phylogenetic_path' ]
            path_elements = other_phylogenetic_path.split( ',' )

            # Check if target clade's clade_id_name appears in this node's path
            if clade_id_name in path_elements:
                all_descendant_clade_id_names.append( other_clade_id_name )

                # Check if this descendant is a species (leaf)
                if other_clade_data[ 'clade_type' ] == 'species':
                    # Extract genus_species from the atomic clade_id_name (everything after the Cxxx_ prefix)
                    genus_species = other_clade_id_name.split( '_', 1 )[ 1 ] if '_' in other_clade_id_name else other_clade_id_name
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

        # Sort descendant clade identifiers numerically by Cxxx prefix
        all_descendant_clade_id_names.sort( key=clade_id_name_sort_key )

        # Get phylogenetic block for this clade (atomic identifier)
        phylogenetic_block = structure_clade_pairs___phylogenetic_blocks.get( ( structure_id, clade_id_name ), '' )

        # Build row (Rule 6 atomic identifiers only)
        descendant_species_count = len( sorted_species )
        descendant_species_list_string = ','.join( sorted_species )
        descendant_species_paths_string = ','.join( sorted_paths )
        all_descendant_clade_id_names_string = ','.join( all_descendant_clade_id_names )

        row = {
            'Structure_ID': structure_id,
            'Clade_ID_Name': clade_id_name,
            'Phylogenetic_Block': phylogenetic_block,
            'Descendant_Species_Count': str( descendant_species_count ),
            'Descendant_Species_List': descendant_species_list_string,
            'Descendant_Species_Paths': descendant_species_paths_string,
            'All_Descendant_Clade_ID_Names': all_descendant_clade_id_names_string
        }

        mapping_rows.append( row )

    # Progress reporting
    if structure_number <= 10 or structure_number > total_structures - 5:
        species_count = len( species_clade_id_names_in_structure )
        clades_count = len( all_clade_id_names_in_structure )
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

# Define column headers (Rule 6 atomic identifiers; split forms removed)
column_headers = [
    'Structure_ID (topology structure identifier)',
    'Clade_ID_Name (atomic clade identifier e.g. C082_Metazoa)',
    'Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)',
    'Descendant_Species_Count (count of species that descend from this clade)',
    'Descendant_Species_List (comma delimited genus_species names of descendant species)',
    'Descendant_Species_Paths (comma delimited paths from clade to each descendant species using greater than as path separator)',
    'All_Descendant_Clade_ID_Names (comma delimited atomic clade identifiers of all descendant nodes including internal and species)'
]

column_keys = [
    'Structure_ID', 'Clade_ID_Name', 'Phylogenetic_Block',
    'Descendant_Species_Count', 'Descendant_Species_List',
    'Descendant_Species_Paths', 'All_Descendant_Clade_ID_Names'
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
    unique_clades.add( row[ 'Clade_ID_Name' ] )
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
