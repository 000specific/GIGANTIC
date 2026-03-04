# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Determine phylogenetic origins of annogroups using MRCA algorithm
# Human: Eric Edsinger

"""
OCL Pipeline Script 002: Determine Annogroup Origins

Determines the phylogenetic origin (MRCA) of each annogroup across all subtypes.

Algorithm:
1. For each annogroup, collect all species present (from annogroup map)
2. SINGLE-SPECIES ANNOGROUPS:
   - Origin = the species itself
   - Shared clades = full phylogenetic path for that species (root to species)
3. MULTI-SPECIES ANNOGROUPS:
   - Get phylogenetic path (root to leaf) for each species
   - Find intersection of all paths (shared ancestral clades)
   - Identify MRCA: deepest clade in shared set where divergence occurs

Processes all subtypes from the subtypes manifest (single, combo, zero).
Zero-subtype annogroups are always single-species (singleton), so their
origin is always the species itself.

Inputs (from Script 001 outputs in 1-output/):
- Phylogenetic blocks, parent-child relationships, phylogenetic paths
- Clade ID-to-name mappings
- Annogroup map (with species lists for each annogroup)
- Annogroup subtypes manifest

Outputs (to 2-output/):
- Per-annogroup origins with phylogenetic block and path annotations
- Origins summary (annogroup counts per clade)
- Annogroups grouped by origin clade

Usage:
    python 002_ai-python-determine_origins.py --structure_id 001 --config ../../ocl_config.yaml --output_dir OUTPUT_pipeline
"""

import csv
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import yaml

csv.field_size_limit( sys.maxsize )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'OCL Pipeline Script 002: Determine annogroup origins using MRCA algorithm',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--structure_id',
        type = str,
        required = True,
        help = 'Structure ID to process (e.g., "001", "002", ..., "105")'
    )

    parser.add_argument(
        '--config',
        type = str,
        required = True,
        help = 'Path to ocl_config.yaml'
    )

    parser.add_argument(
        '--output_dir',
        type = str,
        default = None,
        help = 'Base output directory (overrides config if provided)'
    )

    return parser.parse_args()


# ============================================================================
# CONFIGURATION
# ============================================================================

args = parse_arguments()

config_path = Path( args.config )
if not config_path.exists():
    print( f"CRITICAL ERROR: Configuration file not found: {config_path}" )
    sys.exit( 1 )

with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

TARGET_STRUCTURE = f"structure_{args.structure_id}"
SPECIES_SET_NAME = config[ 'species_set_name' ]
ANNOTATION_DATABASE = config[ 'annotation_database' ]

config_directory = config_path.parent

if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]

# Input directories (from Script 001 outputs)
input_directory = output_base_directory / TARGET_STRUCTURE / '1-output'

# Input files from Script 001
input_parent_child_file = input_directory / f'1_ai-parent_child_table-{TARGET_STRUCTURE}.tsv'
input_phylogenetic_paths_file = input_directory / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
input_clade_mappings_file = input_directory / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'
input_annogroup_map_file = input_directory / '1_ai-annogroup_map.tsv'

# Upstream trees_species data
input_trees_species_directory = config_directory / config[ 'inputs' ][ 'trees_species_dir' ]
input_trees_phylogenetic_blocks_all = input_trees_species_directory / 'Species_Phylogenetic_Blocks'
input_trees_phylogenetic_paths_all = input_trees_species_directory / 'Species_Phylogenetic_Paths'

# Output directory
output_directory = output_base_directory / TARGET_STRUCTURE / '2-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_origins_file = output_directory / '2_ai-annogroup_origins.tsv'
output_summary_file = output_directory / '2_ai-origins_summary-annogroups_per_clade.tsv'
output_by_origin_directory = output_directory / '2_ai-annogroups_by_origin'
output_by_origin_directory.mkdir( parents = True, exist_ok = True )

# Log directory
log_directory = output_base_directory / TARGET_STRUCTURE / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / f'2_ai-log-determine_origins-{TARGET_STRUCTURE}.log'


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s',
    handlers = [
        logging.FileHandler( log_file ),
        logging.StreamHandler( sys.stdout )
    ]
)
logger = logging.getLogger( __name__ )


# ============================================================================
# SECTION 1: LOAD PHYLOGENETIC TREE STRUCTURE
# ============================================================================

def load_parent_child_relationships():
    """Load parent-child relationships from Script 001 output."""
    logger.info( f"Loading parent-child relationships from: {input_parent_child_file}" )

    if not input_parent_child_file.exists():
        logger.error( f"CRITICAL ERROR: Parent-child file not found: {input_parent_child_file}" )
        sys.exit( 1 )

    parents___children = {}
    children___parents = {}

    with open( input_parent_child_file, 'r' ) as input_file:
        # Parent_ID (parent clade identifier)	Parent_Name (parent clade name)	Child_ID (child clade identifier)	Child_Name (child clade name)
        # C068	Basal	C069	Holomycota
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 4:
                continue

            parent_name = parts[ 1 ]
            child_name = parts[ 3 ]

            if parent_name not in parents___children:
                parents___children[ parent_name ] = []
            parents___children[ parent_name ].append( child_name )

            if parent_name != child_name:
                children___parents[ child_name ] = parent_name

    logger.info( f"Loaded {len( parents___children )} parent-child relationships" )

    if len( parents___children ) == 0:
        logger.error( f"CRITICAL ERROR: No parent-child relationships loaded!" )
        sys.exit( 1 )

    return parents___children, children___parents


def load_clade_mappings():
    """Load clade ID to name mappings from Script 001 output."""
    logger.info( f"Loading clade mappings from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mappings file not found: {input_clade_mappings_file}" )
        sys.exit( 1 )

    clade_ids___clade_names = {}

    with open( input_clade_mappings_file, 'r' ) as input_file:
        # Clade_ID (clade identifier from trees_species)	Clade_Name (clade name from phylogenetic tree)
        # C068	Basal
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 2:
                continue

            clade_ids___clade_names[ parts[ 0 ] ] = parts[ 1 ]

    logger.info( f"Loaded {len( clade_ids___clade_names )} clade mappings" )
    return clade_ids___clade_names


# ============================================================================
# SECTION 2: LOAD PHYLOGENETIC PATHS
# ============================================================================

def load_phylogenetic_paths():
    """Load phylogenetic paths from Script 001 output."""
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_file}" )

    if not input_phylogenetic_paths_file.exists():
        logger.error( f"CRITICAL ERROR: Phylogenetic paths file not found: {input_phylogenetic_paths_file}" )
        sys.exit( 1 )

    species_ids___phylogenetic_paths = {}

    with open( input_phylogenetic_paths_file, 'r' ) as input_file:
        # Leaf_Clade_ID (terminal leaf clade identifier and name)	Path_Length (...)	Phylogenetic_Path (...)
        # C001_Fonticula_alba	3	C068_Basal,C069_Holomycota,C001_Fonticula_alba
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 3:
                continue

            leaf_clade_id = parts[ 0 ]
            path_string = parts[ 2 ]

            if '>' in path_string:
                path_elements = path_string.split( '>' )
            else:
                path_elements = path_string.split( ',' )

            path_names = []
            for element in path_elements:
                element = element.strip()
                parts_element = element.split( '_', 1 )
                if len( parts_element ) >= 2:
                    clade_name = parts_element[ 1 ]
                    path_names.append( clade_name )

            species_ids___phylogenetic_paths[ leaf_clade_id ] = path_names

    logger.info( f"Loaded {len( species_ids___phylogenetic_paths )} phylogenetic paths" )

    if len( species_ids___phylogenetic_paths ) == 0:
        logger.error( f"CRITICAL ERROR: No phylogenetic paths loaded!" )
        sys.exit( 1 )

    return species_ids___phylogenetic_paths


# ============================================================================
# SECTION 3: LOAD ANNOGROUP MAP
# ============================================================================

def load_annogroup_map():
    """
    Load annogroup map from Script 001 output.

    Returns:
        dict: { annogroup_id: { 'subtype': str, 'species_list': [ ... ], 'sequence_ids': [ ... ], ... } }
    """
    logger.info( f"Loading annogroup map from: {input_annogroup_map_file}" )

    if not input_annogroup_map_file.exists():
        logger.error( f"CRITICAL ERROR: Annogroup map not found: {input_annogroup_map_file}" )
        sys.exit( 1 )

    annogroup_ids___annogroup_data = {}

    with open( input_annogroup_map_file, 'r' ) as input_file:
        # Annogroup_ID (identifier format annogroup_{db}_N)	Annogroup_Subtype (single or combo or zero)	Annotation_Database (...)	Annotation_Accessions (...)	Species_Count (...)	Sequence_Count (...)	Species_List (...)	Sequence_IDs (...)
        # annogroup_pfam_1	single	pfam	PF00069	42	120	Homo_sapiens,Mus_musculus,...	XP_016856755.1,...
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 8:
                continue

            annogroup_id = parts[ 0 ]
            annogroup_subtype = parts[ 1 ]
            annotation_accessions = parts[ 3 ]
            species_count = int( parts[ 4 ] )
            sequence_count = int( parts[ 5 ] )
            species_list_string = parts[ 6 ]
            sequence_ids_string = parts[ 7 ]

            species_list = [ species.strip() for species in species_list_string.split( ',' ) if species.strip() ]
            sequence_ids = [ seq_id.strip() for seq_id in sequence_ids_string.split( ',' ) if seq_id.strip() ]

            annogroup_ids___annogroup_data[ annogroup_id ] = {
                'subtype': annogroup_subtype,
                'annotation_accessions': annotation_accessions,
                'species': species_list,
                'species_count': species_count,
                'sequence_count': sequence_count,
                'sequence_ids': sequence_ids
            }

    logger.info( f"Loaded {len( annogroup_ids___annogroup_data )} annogroups from map" )

    if len( annogroup_ids___annogroup_data ) == 0:
        logger.error( f"CRITICAL ERROR: No annogroups loaded from map!" )
        sys.exit( 1 )

    return annogroup_ids___annogroup_data


# ============================================================================
# SECTION 4: LOAD UPSTREAM TREES DATA
# ============================================================================

def load_phylogenetic_blocks_for_structure():
    """Load phylogenetic blocks with block names for the current structure."""
    logger.info( f"Loading phylogenetic blocks from trees_species: {input_trees_phylogenetic_blocks_all}" )

    block_files = list( input_trees_phylogenetic_blocks_all.glob( '*phylogenetic_blocks*.tsv' ) )
    if not block_files:
        logger.warning( f"No phylogenetic blocks files found in: {input_trees_phylogenetic_blocks_all}" )
        return {}

    block_file = block_files[ 0 ]
    clade_names___phylogenetic_blocks = {}

    with open( block_file, 'r' ) as input_file:
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        structure_id_column = None
        clade_name_column = None
        block_id_name_column = None

        for index, column_header in enumerate( header_parts ):
            column_id = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            if column_id == 'Structure_ID':
                structure_id_column = index
            elif column_id == 'Clade_Name':
                clade_name_column = index
            elif column_id == 'Phylogenetic_Block_ID_Name':
                block_id_name_column = index

        if structure_id_column is None or clade_name_column is None:
            return {}

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if parts[ structure_id_column ] != TARGET_STRUCTURE:
                continue

            clade_name = parts[ clade_name_column ]
            block_id_name = parts[ block_id_name_column ] if block_id_name_column is not None and block_id_name_column < len( parts ) else 'NA'
            clade_names___phylogenetic_blocks[ clade_name ] = block_id_name

    logger.info( f"Loaded {len( clade_names___phylogenetic_blocks )} phylogenetic blocks for {TARGET_STRUCTURE}" )
    return clade_names___phylogenetic_blocks


def load_phylogenetic_paths_for_structure():
    """Load phylogenetic paths for the current structure from trees_species."""
    logger.info( f"Loading phylogenetic paths from trees_species: {input_trees_phylogenetic_paths_all}" )

    path_files = list( input_trees_phylogenetic_paths_all.glob( '*paths*.tsv' ) )
    if not path_files:
        path_files = list( input_trees_phylogenetic_paths_all.glob( '*evolutionary_paths*.tsv' ) )
    if not path_files:
        return {}

    path_file = path_files[ 0 ]
    clade_names___phylogenetic_paths = {}

    with open( path_file, 'r' ) as input_file:
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        structure_id_column = None
        species_name_column = None
        path_column = None

        for index, column_header in enumerate( header_parts ):
            column_id = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            if column_id == 'Structure_ID':
                structure_id_column = index
            elif column_id in [ 'Species_Name', 'Clade_Name' ]:
                species_name_column = index
            elif 'Path' in column_id:
                path_column = index

        if structure_id_column is None or species_name_column is None or path_column is None:
            return {}

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if parts[ structure_id_column ] != TARGET_STRUCTURE:
                continue

            species_name = parts[ species_name_column ]
            phylogenetic_path = parts[ path_column ]
            clade_names___phylogenetic_paths[ species_name ] = phylogenetic_path

    logger.info( f"Loaded {len( clade_names___phylogenetic_paths )} phylogenetic paths for {TARGET_STRUCTURE}" )
    return clade_names___phylogenetic_paths


# ============================================================================
# SECTION 5: DETERMINE ANNOGROUP ORIGINS (MRCA ALGORITHM)
# ============================================================================

def determine_origin( annogroup_species, species_ids___phylogenetic_paths, parents___children, clade_ids___clade_names ):
    """
    Determine the phylogenetic origin of an annogroup using MRCA algorithm.

    Same algorithm as orthogroups_X_ocl.
    """
    species_names___clade_ids = {}
    for clade_id, clade_name in clade_ids___clade_names.items():
        species_names___clade_ids[ clade_name ] = clade_id

    orthogroup_phylogenetic_paths = []
    first_species_ordered_path = None

    for species_name in annogroup_species:
        if species_name not in species_names___clade_ids:
            continue

        species_clade_id = species_names___clade_ids[ species_name ]

        if species_clade_id not in species_ids___phylogenetic_paths:
            continue

        phylogenetic_path = species_ids___phylogenetic_paths[ species_clade_id ]

        if first_species_ordered_path is None:
            first_species_ordered_path = phylogenetic_path

        orthogroup_phylogenetic_paths.append( set( phylogenetic_path ) )

    if len( orthogroup_phylogenetic_paths ) == 0:
        return None, set()

    shared_clades_set = orthogroup_phylogenetic_paths[ 0 ].intersection( *orthogroup_phylogenetic_paths )

    if len( shared_clades_set ) == 0:
        return None, set()

    origin = None

    for clade_name in first_species_ordered_path:
        if clade_name not in shared_clades_set:
            continue

        if clade_name not in parents___children:
            origin = clade_name
            continue

        children = parents___children[ clade_name ]

        if len( children ) < 2:
            continue

        child_1_name = children[ 0 ]
        child_2_name = children[ 1 ]

        if child_1_name not in shared_clades_set and child_2_name not in shared_clades_set:
            origin = clade_name
        elif clade_name == child_1_name and clade_name == child_2_name:
            origin = clade_name

    return origin, shared_clades_set


# ============================================================================
# SECTION 6: PROCESS ALL ANNOGROUPS
# ============================================================================

def process_annogroups( annogroup_ids___annogroup_data, species_ids___phylogenetic_paths, parents___children, clade_ids___clade_names ):
    """Process all annogroups to determine their phylogenetic origins."""
    logger.info( f"Processing {len( annogroup_ids___annogroup_data )} annogroups to determine origins..." )

    annogroup_origins = {}
    origins___annogroup_ids = defaultdict( list )

    processed_count = 0
    origin_found_count = 0
    origin_not_found_count = 0
    single_species_count = 0
    multi_species_count = 0

    species_names___clade_ids = { clade_name: clade_id for clade_id, clade_name in clade_ids___clade_names.items() }

    for annogroup_id, annogroup_data in annogroup_ids___annogroup_data.items():
        processed_count += 1

        if processed_count % 10000 == 0:
            logger.info( f"Processed {processed_count} / {len( annogroup_ids___annogroup_data )} annogroups..." )

        annogroup_species = annogroup_data[ 'species' ]

        if len( annogroup_species ) == 0:
            origin_not_found_count += 1
            continue

        # SINGLE-SPECIES ANNOGROUPS: origin = the species itself
        if len( annogroup_species ) == 1:
            single_species_count += 1
            species_name = annogroup_species[ 0 ]
            origin = species_name

            if species_name in species_names___clade_ids:
                species_clade_id = species_names___clade_ids[ species_name ]
                if species_clade_id in species_ids___phylogenetic_paths:
                    shared_clades = set( species_ids___phylogenetic_paths[ species_clade_id ] )
                else:
                    shared_clades = { species_name }
            else:
                shared_clades = { species_name }

            annogroup_origins[ annogroup_id ] = {
                'origin': origin,
                'shared_clades': shared_clades,
                'species': annogroup_species,
                'species_count': 1,
                'sequence_count': annogroup_data[ 'sequence_count' ],
                'sequence_ids': annogroup_data[ 'sequence_ids' ],
                'subtype': annogroup_data[ 'subtype' ]
            }

            origins___annogroup_ids[ origin ].append( annogroup_id )
            origin_found_count += 1
            continue

        # MULTI-SPECIES ANNOGROUPS: use MRCA algorithm
        multi_species_count += 1

        origin, shared_clades = determine_origin(
            annogroup_species,
            species_ids___phylogenetic_paths,
            parents___children,
            clade_ids___clade_names
        )

        if origin is None:
            origin_not_found_count += 1
            continue

        annogroup_origins[ annogroup_id ] = {
            'origin': origin,
            'shared_clades': shared_clades,
            'species': annogroup_species,
            'species_count': len( annogroup_species ),
            'sequence_count': annogroup_data[ 'sequence_count' ],
            'sequence_ids': annogroup_data[ 'sequence_ids' ],
            'subtype': annogroup_data[ 'subtype' ]
        }

        origins___annogroup_ids[ origin ].append( annogroup_id )
        origin_found_count += 1

    logger.info( f"Processed {processed_count} annogroups" )
    logger.info( f"Single-species annogroups: {single_species_count}" )
    logger.info( f"Multi-species annogroups: {multi_species_count}" )
    logger.info( f"Origin found: {origin_found_count}" )
    logger.info( f"Origin not found: {origin_not_found_count}" )

    if origin_found_count == 0:
        logger.error( f"CRITICAL ERROR: No annogroup origins found!" )
        sys.exit( 1 )

    return annogroup_origins, origins___annogroup_ids


# ============================================================================
# SECTION 7: WRITE OUTPUTS
# ============================================================================

def write_annogroup_origins( annogroup_origins, clade_names___phylogenetic_blocks, clade_names___phylogenetic_paths ):
    """Write per-annogroup origin assignments."""
    logger.info( f"Writing annogroup origins to: {output_origins_file}" )

    with open( output_origins_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        header_columns = [
            'Annogroup_ID (annogroup identifier)',
            'Annogroup_Subtype (single or combo or zero)',
            'Origin_Clade (phylogenetic clade where annogroup originated)',
            'Origin_Clade_Phylogenetic_Block (phylogenetic block for origin clade format Parent_Clade::Child_Clade)',
            'Origin_Clade_Phylogenetic_Path (phylogenetic path for origin clade comma delimited from root to origin clade)',
            'Shared_Clades (comma delimited list of shared ancestral clades)',
            'Species_Count (total unique species in annogroup)',
            'Sequence_Count (total number of sequences in annogroup)',
            'Species_List (comma delimited list of species in annogroup)',
            'Sequence_IDs (comma delimited list of sequence identifiers in annogroup)'
        ]

        csv_writer.writerow( header_columns )

        for annogroup_id in sorted( annogroup_origins.keys() ):
            data = annogroup_origins[ annogroup_id ]

            origin = data[ 'origin' ]
            subtype = data[ 'subtype' ]
            shared_clades_string = ','.join( sorted( data[ 'shared_clades' ] ) )
            phylogenetic_block = clade_names___phylogenetic_blocks.get( origin, 'NA' )
            phylogenetic_path = clade_names___phylogenetic_paths.get( origin, 'NA' )
            species_list = ','.join( sorted( data[ 'species' ] ) )
            sequence_ids_string = ','.join( sorted( data[ 'sequence_ids' ] ) )

            output_row = [
                annogroup_id,
                subtype,
                origin,
                phylogenetic_block,
                phylogenetic_path,
                shared_clades_string,
                str( data[ 'species_count' ] ),
                str( data[ 'sequence_count' ] ),
                species_list,
                sequence_ids_string
            ]

            csv_writer.writerow( output_row )

    logger.info( f"Wrote {len( annogroup_origins )} annogroup origins to {output_origins_file.name}" )


def write_origins_summary( origins___annogroup_ids ):
    """Write summary of annogroup counts per phylogenetic origin."""
    logger.info( f"Writing origins summary to: {output_summary_file}" )

    total_annogroups = sum( len( annogroup_list ) for annogroup_list in origins___annogroup_ids.values() )

    with open( output_summary_file, 'w' ) as output_file:
        output = 'Origin_Clade (phylogenetic clade where annogroup originated)\t'
        output += 'Annogroup_Count (count of annogroups with this origin clade)\t'
        output += 'Percentage (percentage of all annogroups with this origin clade)\n'
        output_file.write( output )

        sorted_origins = sorted( origins___annogroup_ids.items(), key = lambda x: len( x[ 1 ] ), reverse = True )

        for origin_clade, annogroup_list in sorted_origins:
            count = len( annogroup_list )
            percentage = 100.0 * count / total_annogroups if total_annogroups > 0 else 0.0

            output = f"{origin_clade}\t{count}\t{percentage:.2f}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( origins___annogroup_ids )} origin clades to {output_summary_file.name}" )


def write_annogroups_by_origin( origins___annogroup_ids ):
    """Write separate files for annogroups grouped by origin clade."""
    logger.info( f"Writing annogroups by origin to: {output_by_origin_directory}" )

    for origin_clade, annogroup_list in origins___annogroup_ids.items():
        safe_clade_name = origin_clade.replace( ' ', '_' ).replace( '/', '_' )
        output_file_path = output_by_origin_directory / f"{safe_clade_name}_annogroups.txt"

        with open( output_file_path, 'w' ) as output_file:
            for annogroup_id in sorted( annogroup_list ):
                output_file.write( f"{annogroup_id}\n" )

    logger.info( f"Wrote {len( origins___annogroup_ids )} origin-specific annogroup files" )


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 002: DETERMINE ANNOGROUP ORIGINS" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Species set: {SPECIES_SET_NAME}" )
    logger.info( f"Annotation database: {ANNOTATION_DATABASE}" )
    logger.info( "" )

    # Step 1: Load phylogenetic tree structure
    logger.info( "STEP 1: Loading phylogenetic tree structure..." )
    parents___children, children___parents = load_parent_child_relationships()
    clade_ids___clade_names = load_clade_mappings()

    # Step 2: Load phylogenetic paths
    logger.info( "" )
    logger.info( "STEP 2: Loading phylogenetic paths..." )
    species_ids___phylogenetic_paths = load_phylogenetic_paths()

    # Step 3: Load annogroup map
    logger.info( "" )
    logger.info( "STEP 3: Loading annogroup map..." )
    annogroup_ids___annogroup_data = load_annogroup_map()

    # Step 4: Load upstream trees data
    logger.info( "" )
    logger.info( "STEP 4: Loading phylogenetic blocks and paths from trees_species..." )
    clade_names___phylogenetic_blocks = load_phylogenetic_blocks_for_structure()
    clade_names___phylogenetic_paths = load_phylogenetic_paths_for_structure()

    # Step 5: Determine origins for all annogroups
    logger.info( "" )
    logger.info( "STEP 5: Determining phylogenetic origins..." )
    annogroup_origins, origins___annogroup_ids = process_annogroups(
        annogroup_ids___annogroup_data,
        species_ids___phylogenetic_paths,
        parents___children,
        clade_ids___clade_names
    )

    # Step 6: Write outputs
    logger.info( "" )
    logger.info( "STEP 6: Writing outputs..." )
    write_annogroup_origins( annogroup_origins, clade_names___phylogenetic_blocks, clade_names___phylogenetic_paths )
    write_origins_summary( origins___annogroup_ids )
    write_annogroups_by_origin( origins___annogroup_ids )

    # Complete
    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 002 COMPLETED SUCCESSFULLY" )
    logger.info( "=" * 80 )
    logger.info( f"All outputs written to: {output_directory}" )
    logger.info( f"Finished: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "" )
    logger.info( "Output files:" )
    logger.info( f"  {output_origins_file.name}" )
    logger.info( f"  {output_summary_file.name}" )
    logger.info( f"  {output_by_origin_directory.name}/ ({len( origins___annogroup_ids )} files)" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
