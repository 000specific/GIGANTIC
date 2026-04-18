# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Determine phylogenetic origins of annogroups using MRCA algorithm
# Human: Eric Edsinger

"""
OCL Pipeline Script 002: Determine Annogroup Origins

Determines the phylogenetic origin (MRCA) of each annogroup.

Algorithm:
1. For each annogroup, collect all species present (already Genus_species in
   the standardized annogroups file from Script 001 -- no GIGANTIC ID parsing)
2. SINGLE-SPECIES ANNOGROUPS:
   - Origin = the species itself (leaf clade_id_name)
   - Shared clades = full phylogenetic path for that species (root to species)
3. MULTI-SPECIES ANNOGROUPS:
   - Get phylogenetic path (root to leaf) for each species
   - Find intersection of all paths (shared ancestral clades)
   - Identify MRCA: deepest clade in shared set where divergence occurs
   - MRCA = the divergence point where the annogroup originated

Inputs (from Script 001 outputs in 1-output/):
- Parent-child relationships (Rule 6 atomic 3-column format)
- Phylogenetic paths (root-to-tip for each species)
- Clade name-to-clade_id_name mappings
- Annogroups with species already resolved to Genus_species

Outputs (to 2-output/):
- Per-annogroup origins with phylogenetic block and path annotations
- Origins summary (annogroup counts per origin transition block)
- Annogroups grouped by origin clade

Usage:
    python 002_ai-python-determine_origins.py --structure_id 001 --config ../../START_HERE-user_config.yaml
"""

import csv
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import yaml

# Increase CSV field size limit to handle large fields
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
        help = 'Path to START_HERE-user_config.yaml'
    )

    parser.add_argument(
        '--output_dir',
        type = str,
        default = None,
        help = 'Base output directory (default: derived from config.output.base_dir relative to config file)'
    )

    return parser.parse_args()


# ============================================================================
# CONFIGURATION
# ============================================================================

args = parse_arguments()

# Load configuration
config_path = Path( args.config )
if not config_path.exists():
    print( f"CRITICAL ERROR: Configuration file not found: {config_path}" )
    sys.exit( 1 )

with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

# Format structure ID
TARGET_STRUCTURE = f"structure_{args.structure_id}"
SPECIES_SET_NAME = config[ 'species_set_name' ]
ANNOTATION_DATABASE = config[ 'annotation_database' ]

# Resolve paths relative to config file directory
config_directory = config_path.parent
# Prefer --output_dir (passed by NextFlow main.nf for consistency with scripts 003-005);
# fall back to config.output.base_dir relative to config file when invoked standalone.
if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]

# Input directories (from Script 001 outputs)
input_directory = output_base_directory / TARGET_STRUCTURE / '1-output'

# Input files from Script 001
input_parent_child_file = input_directory / f'1_ai-{TARGET_STRUCTURE}_parent_child_table.tsv'
input_phylogenetic_paths_file = input_directory / f'1_ai-{TARGET_STRUCTURE}_phylogenetic_paths.tsv'
input_clade_mappings_file = input_directory / f'1_ai-{TARGET_STRUCTURE}_clade_mappings.tsv'
input_annogroups_file = input_directory / f'1_ai-{TARGET_STRUCTURE}_annogroups-species_identifiers.tsv'

# Upstream trees_species data (phylogenetic blocks with full format for block/path annotations)
input_trees_species_directory = config_directory / config[ 'inputs' ][ 'trees_species_dir' ]
input_trees_phylogenetic_blocks_all = input_trees_species_directory / 'Species_Phylogenetic_Blocks'
input_trees_phylogenetic_paths_all = input_trees_species_directory / 'Species_Phylogenetic_Paths'

# Output directory
output_directory = output_base_directory / TARGET_STRUCTURE / '2-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_origins_file = output_directory / f'2_ai-{TARGET_STRUCTURE}_annogroup_origins.tsv'
output_summary_file = output_directory / f'2_ai-{TARGET_STRUCTURE}_origins_summary-annogroups_per_clade.tsv'
output_by_origin_directory = output_directory / f'2_ai-{TARGET_STRUCTURE}_annogroups_by_origin'
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
    """
    Load parent-child relationships from Script 001 output.

    Returns:
        tuple: ( parents___children, children___parents )
    """
    logger.info( f"Loading parent-child relationships from: {input_parent_child_file}" )

    if not input_parent_child_file.exists():
        logger.error( f"CRITICAL ERROR: Parent-child file not found!" )
        logger.error( f"Expected location: {input_parent_child_file}" )
        logger.error( f"Run Script 001 first to generate this file." )
        sys.exit( 1 )

    parents___children = {}
    children___parents = {}

    with open( input_parent_child_file, 'r' ) as input_file:
        # Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)	Parent_Clade_ID_Name (atomic parent clade identifier)	Child_Clade_ID_Name (atomic child clade identifier)
        # C069_Holozoa::C082_Metazoa	C069_Holozoa	C082_Metazoa
        # Rule 6: Parent_Clade_ID_Name and Child_Clade_ID_Name are the atomic
        # identifiers consumed directly (no recombination from split forms).
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        parent_clade_id_name_column = column_names___indices.get( 'Parent_Clade_ID_Name' )
        child_clade_id_name_column = column_names___indices.get( 'Child_Clade_ID_Name' )

        if parent_clade_id_name_column is None or child_clade_id_name_column is None:
            logger.error( f"CRITICAL ERROR: Parent-child file missing required columns!" )
            logger.error( f"Need: Parent_Clade_ID_Name, Child_Clade_ID_Name" )
            logger.error( f"Found: {header_parts}" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) <= max( parent_clade_id_name_column, child_clade_id_name_column ):
                continue

            parent_clade_id_name = parts[ parent_clade_id_name_column ]
            child_clade_id_name = parts[ child_clade_id_name_column ]

            # Build parent-to-children mapping (atomic clade_id_name -> list of atomic clade_id_name)
            if parent_clade_id_name not in parents___children:
                parents___children[ parent_clade_id_name ] = []
            parents___children[ parent_clade_id_name ].append( child_clade_id_name )

            # Build child-to-parent mapping. Script 005 no longer emits tip
            # self-loops so no self-loop guard is needed here.
            children___parents[ child_clade_id_name ] = parent_clade_id_name

    logger.info( f"Loaded {len( parents___children )} parent-child relationships" )

    if len( parents___children ) == 0:
        logger.error( f"CRITICAL ERROR: No parent-child relationships loaded!" )
        sys.exit( 1 )

    return parents___children, children___parents


def load_clade_mappings():
    """
    Load clade name to clade_id_name mappings from Script 001 output.

    Returns:
        dict: { clade_name: clade_id_name }   -- e.g., "Fonticula_alba" -> "C001_Fonticula_alba"
              Used to look up a species's leaf clade_id_name from its bare
              species name (which is what appears in annogroup species lists).
    """
    logger.info( f"Loading clade mappings from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mappings file not found!" )
        logger.error( f"Expected location: {input_clade_mappings_file}" )
        sys.exit( 1 )

    clade_names___clade_id_names = {}

    with open( input_clade_mappings_file, 'r' ) as input_file:
        # Clade_Name (bare clade name lookup key as it appears in annogroup species lists)	Clade_ID_Name (atomic clade identifier e.g. C001_Fonticula_alba)
        # Fonticula_alba	C001_Fonticula_alba
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            if len( parts ) < 2:
                continue

            clade_name = parts[ 0 ]
            clade_id_name = parts[ 1 ]

            clade_names___clade_id_names[ clade_name ] = clade_id_name

    logger.info( f"Loaded {len( clade_names___clade_id_names )} clade mappings" )
    return clade_names___clade_id_names


# ============================================================================
# SECTION 2: LOAD PHYLOGENETIC PATHS
# ============================================================================

def load_phylogenetic_paths():
    """
    Load phylogenetic paths (root to leaf) for each species from Script 001 output.

    Per Rule 6 of AI_GUIDE-project.md, clade identifiers are ALWAYS handled as
    the atomic clade_id_name form (e.g., "C082_Metazoa"). No splitting into
    bare clade_id or bare clade_name for internal lookups.

    Returns:
        dict: { species_clade_id_name: [ clade_id_name_1, clade_id_name_2, ..., species_clade_id_name ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_file}" )

    if not input_phylogenetic_paths_file.exists():
        logger.error( f"CRITICAL ERROR: Phylogenetic paths file not found!" )
        logger.error( f"Expected location: {input_phylogenetic_paths_file}" )
        sys.exit( 1 )

    species_clade_id_names___phylogenetic_paths = {}

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

            # Leaf clade identifier in the TSV is already in canonical
            # clade_id_name form (e.g., "C001_Fonticula_alba"). Store as-is.
            leaf_clade_id_name = parts[ 0 ].strip()
            path_string = parts[ 2 ]

            # Parse path elements. Each element is already in clade_id_name
            # form (e.g., "C068_Basal"). Store them as-is -- no splitting.
            if '>' in path_string:
                path_elements = path_string.split( '>' )
            else:
                path_elements = path_string.split( ',' )

            path_clade_id_names = [ element.strip() for element in path_elements if element.strip() ]

            species_clade_id_names___phylogenetic_paths[ leaf_clade_id_name ] = path_clade_id_names

    logger.info( f"Loaded {len( species_clade_id_names___phylogenetic_paths )} phylogenetic paths" )

    if len( species_clade_id_names___phylogenetic_paths ) == 0:
        logger.error( f"CRITICAL ERROR: No phylogenetic paths loaded!" )
        sys.exit( 1 )

    return species_clade_id_names___phylogenetic_paths


# ============================================================================
# SECTION 3: LOAD ANNOGROUPS
# ============================================================================

def load_annogroups():
    """
    Load annogroups with species already resolved from Script 001 output.

    Unlike orthogroups_X_ocl which must parse GIGANTIC identifiers to extract
    species names, annogroups already have Species_List as comma-delimited
    Genus_species in the standardized file produced by Script 001.

    Returns:
        dict: { annogroup_id: { 'species': [ species_name, ... ],
                                'species_count': int,
                                'annogroup_subtype': str } }
    """
    logger.info( f"Loading annogroups from: {input_annogroups_file}" )

    if not input_annogroups_file.exists():
        logger.error( f"CRITICAL ERROR: Annogroups file not found!" )
        logger.error( f"Expected location: {input_annogroups_file}" )
        sys.exit( 1 )

    annogroup_ids___annogroup_data = {}

    with open( input_annogroups_file, 'r' ) as input_file:
        # Annogroup_ID (annogroup identifier format annogroup_{db}_N)	Annogroup_Subtype (single or combo or zero)	Species_Count (number of unique species in annogroup)	Species_List (comma delimited list of species names as Genus_species)
        # annogroup_pfam_1	single	5	Homo_sapiens,Mus_musculus,Drosophila_melanogaster,Caenorhabditis_elegans,Fonticula_alba
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            if len( parts ) < 4:
                continue

            annogroup_id = parts[ 0 ]
            annogroup_subtype = parts[ 1 ]
            species_count = int( parts[ 2 ] )
            species_list_string = parts[ 3 ]

            # Parse comma-delimited species names (already Genus_species)
            species = [ species_name.strip() for species_name in species_list_string.split( ',' ) if species_name.strip() ]

            annogroup_ids___annogroup_data[ annogroup_id ] = {
                'species': species,
                'species_count': species_count,
                'annogroup_subtype': annogroup_subtype
            }

    logger.info( f"Loaded {len( annogroup_ids___annogroup_data )} annogroups" )

    if len( annogroup_ids___annogroup_data ) == 0:
        logger.error( f"CRITICAL ERROR: No annogroups loaded!" )
        sys.exit( 1 )

    return annogroup_ids___annogroup_data


def load_phylogenetic_blocks_for_structure():
    """
    Load phylogenetic blocks with block identifiers for the current structure
    from trees_species upstream data.

    Returns:
        dict: { child_clade_id_name: phylogenetic_block }
    """
    logger.info( f"Loading phylogenetic blocks from trees_species: {input_trees_phylogenetic_blocks_all}" )

    # Explicitly match the combined blocks file.
    block_files = list( input_trees_phylogenetic_blocks_all.glob( '*phylogenetic_blocks-all_*_structures.tsv' ) )

    if not block_files:
        logger.warning( f"No combined phylogenetic blocks file found in: {input_trees_phylogenetic_blocks_all}" )
        logger.warning( f"Expected pattern: *phylogenetic_blocks-all_*_structures.tsv" )
        return {}

    if len( block_files ) > 1:
        logger.error( f"CRITICAL ERROR: Multiple combined phylogenetic blocks files found (ambiguous):" )
        for f in sorted( block_files ):
            logger.error( f"  {f.name}" )
        sys.exit( 1 )

    block_file = block_files[ 0 ]
    logger.info( f"Using file: {block_file.name}" )

    # Per Rule 6: dict keyed by atomic child_clade_id_name. Value is the atomic
    # Phylogenetic_Block identifier (e.g., "C069_Holozoa::C082_Metazoa").
    clade_id_names___phylogenetic_blocks = {}

    with open( block_file, 'r' ) as input_file:
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        structure_id_column = column_names___indices.get( 'Structure_ID' )
        phylogenetic_block_column = column_names___indices.get( 'Phylogenetic_Block' )
        child_clade_id_name_column = column_names___indices.get( 'Child_Clade_ID_Name' )

        if structure_id_column is None or phylogenetic_block_column is None or child_clade_id_name_column is None:
            logger.error( "CRITICAL ERROR: Phylogenetic blocks file missing required columns!" )
            logger.error( f"Need: Structure_ID, Phylogenetic_Block, Child_Clade_ID_Name" )
            logger.error( f"Found: {header_parts}" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) <= max( structure_id_column, phylogenetic_block_column, child_clade_id_name_column ):
                continue

            structure_id = parts[ structure_id_column ]
            if structure_id != TARGET_STRUCTURE:
                continue

            phylogenetic_block = parts[ phylogenetic_block_column ]
            child_clade_id_name = parts[ child_clade_id_name_column ]

            clade_id_names___phylogenetic_blocks[ child_clade_id_name ] = phylogenetic_block

    logger.info( f"Loaded {len( clade_id_names___phylogenetic_blocks )} phylogenetic blocks for {TARGET_STRUCTURE}" )
    return clade_id_names___phylogenetic_blocks


def load_phylogenetic_paths_for_structure():
    """
    Load phylogenetic paths for the current structure from trees_species upstream data.

    Returns:
        dict: { species_clade_id_name: phylogenetic_path_string }
    """
    logger.info( f"Loading phylogenetic paths from trees_species: {input_trees_phylogenetic_paths_all}" )

    path_files = list( input_trees_phylogenetic_paths_all.glob( '*phylogenetic_paths-all_structures.tsv' ) )

    if not path_files:
        logger.warning( f"No combined phylogenetic paths file found in: {input_trees_phylogenetic_paths_all}" )
        return {}

    path_file = path_files[ 0 ]
    logger.info( f"Using file: {path_file.name}" )

    clade_id_names___phylogenetic_paths = {}

    with open( path_file, 'r' ) as input_file:
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        # Find column indices dynamically
        structure_id_column = None
        species_clade_id_name_column = None
        path_column = None

        for index, column_header in enumerate( header_parts ):
            column_id = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            if column_id == 'Structure_ID':
                structure_id_column = index
            elif column_id == 'Species_Clade_ID_Name':
                species_clade_id_name_column = index
            elif 'Path' in column_id:
                path_column = index

        if structure_id_column is None or species_clade_id_name_column is None or path_column is None:
            logger.warning( "Could not find required columns (Structure_ID, Species_Clade_ID_Name, Path) in phylogenetic paths file" )
            return {}

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]
            if structure_id != TARGET_STRUCTURE:
                continue

            species_clade_id_name = parts[ species_clade_id_name_column ]
            phylogenetic_path = parts[ path_column ]

            clade_id_names___phylogenetic_paths[ species_clade_id_name ] = phylogenetic_path

    logger.info( f"Loaded {len( clade_id_names___phylogenetic_paths )} phylogenetic paths for {TARGET_STRUCTURE}" )
    return clade_id_names___phylogenetic_paths


# ============================================================================
# SECTION 4: DETERMINE ANNOGROUP ORIGINS (MRCA ALGORITHM)
# ============================================================================

def determine_origin( annogroup_species, species_clade_id_names___phylogenetic_paths, parents___children, clade_names___clade_id_names ):
    """
    Determine the phylogenetic origin of an annogroup using MRCA algorithm.

    Per Rule 6 of AI_GUIDE-project.md, all clade identifiers throughout this
    function are in canonical clade_id_name form (e.g., "C082_Metazoa"). No
    splitting into clade_id and clade_name for internal lookups.

    Algorithm:
    1. Get phylogenetic path for each species in the annogroup
    2. Find intersection of all paths (shared ancestral clades, as clade_id_names)
    3. Identify MRCA: iterate root-to-leaf through shared clades,
       find deepest clade where divergence occurs

    Args:
        annogroup_species: List of bare species names (e.g., "Fonticula_alba"),
            as they appear in the annogroup species lists.
        species_clade_id_names___phylogenetic_paths: Dict mapping each species's
            leaf clade_id_name to its full path as a list of clade_id_name strings.
        parents___children: Dict mapping parent clade_id_name to list of child
            clade_id_name values.
        clade_names___clade_id_names: Dict mapping bare clade_name to clade_id_name.

    Returns:
        tuple: ( origin_clade_id_name, shared_clade_id_names_set )
    """
    # Get phylogenetic paths for all species in annogroup
    annogroup_phylogenetic_paths = []
    first_species_ordered_path = None

    for species_name in annogroup_species:
        # Translate species name -> leaf clade_id_name
        if species_name not in clade_names___clade_id_names:
            continue
        species_clade_id_name = clade_names___clade_id_names[ species_name ]

        if species_clade_id_name not in species_clade_id_names___phylogenetic_paths:
            continue

        phylogenetic_path = species_clade_id_names___phylogenetic_paths[ species_clade_id_name ]

        if first_species_ordered_path is None:
            first_species_ordered_path = phylogenetic_path

        annogroup_phylogenetic_paths.append( set( phylogenetic_path ) )

    if len( annogroup_phylogenetic_paths ) == 0:
        return None, set()

    # Find intersection of all phylogenetic paths (shared ancestral clade_id_names)
    shared_clade_id_names_set = annogroup_phylogenetic_paths[ 0 ].intersection( *annogroup_phylogenetic_paths )

    if len( shared_clade_id_names_set ) == 0:
        return None, set()

    # Find the MRCA (most recent shared ancestral clade)
    # Iterate through first species' path in phylogenetic order (root to leaf)
    origin = None

    for clade_id_name in first_species_ordered_path:
        if clade_id_name not in shared_clade_id_names_set:
            continue

        # Check if this clade has children in the tree
        if clade_id_name not in parents___children:
            origin = clade_id_name
            continue

        children = parents___children[ clade_id_name ]

        if len( children ) < 2:
            continue

        child_1_clade_id_name = children[ 0 ]
        child_2_clade_id_name = children[ 1 ]

        # Neither child is in shared clades -> this is the origin (divergence point)
        if child_1_clade_id_name not in shared_clade_id_names_set and child_2_clade_id_name not in shared_clade_id_names_set:
            origin = clade_id_name

        # Self-loop terminal node
        elif clade_id_name == child_1_clade_id_name and clade_id_name == child_2_clade_id_name:
            origin = clade_id_name

    return origin, shared_clade_id_names_set


# ============================================================================
# SECTION 5: PROCESS ALL ANNOGROUPS
# ============================================================================

def process_annogroups( annogroup_ids___annogroup_data, species_clade_id_names___phylogenetic_paths, parents___children, clade_names___clade_id_names ):
    """
    Process all annogroups to determine their phylogenetic origins.

    Per Rule 6 of AI_GUIDE-project.md, all clade identifiers (including origins)
    are in canonical clade_id_name form (e.g., "C082_Metazoa").

    Single-species annogroups: origin is set to that species's LEAF clade_id_name
    (e.g., "C048_Schmidtea_mediterranea"), not the bare species name -- for
    consistency with the rest of the pipeline.

    Returns:
        tuple: ( annogroup_origins, origins___annogroup_ids ) -- both keyed / valued
        in clade_id_name form.
    """
    logger.info( f"Processing {len( annogroup_ids___annogroup_data )} annogroups to determine origins..." )

    annogroup_origins = {}
    origins___annogroup_ids = defaultdict( list )

    processed_count = 0
    origin_found_count = 0
    origin_not_found_count = 0
    single_species_count = 0
    multi_species_count = 0

    for annogroup_id, annogroup_data in annogroup_ids___annogroup_data.items():
        processed_count += 1

        if processed_count % 10000 == 0:
            logger.info( f"Processed {processed_count} / {len( annogroup_ids___annogroup_data )} annogroups..." )

        # Species are already resolved to Genus_species in the standardized file
        annogroup_species = annogroup_data[ 'species' ]

        if len( annogroup_species ) == 0:
            origin_not_found_count += 1
            continue

        # SINGLE-SPECIES ANNOGROUPS: origin = species's LEAF clade_id_name
        if len( annogroup_species ) == 1:
            single_species_count += 1
            species_name = annogroup_species[ 0 ]

            species_clade_id_name = clade_names___clade_id_names.get( species_name )
            if species_clade_id_name is None:
                origin_not_found_count += 1
                continue

            origin = species_clade_id_name

            # Shared clades = full phylogenetic path for this species
            if species_clade_id_name in species_clade_id_names___phylogenetic_paths:
                shared_clades = set( species_clade_id_names___phylogenetic_paths[ species_clade_id_name ] )
            else:
                shared_clades = { species_clade_id_name }

            annogroup_origins[ annogroup_id ] = {
                'origin': origin,
                'shared_clades': shared_clades,
                'species': annogroup_species,
                'species_count': 1,
                'annogroup_subtype': annogroup_data[ 'annogroup_subtype' ]
            }

            origins___annogroup_ids[ origin ].append( annogroup_id )
            origin_found_count += 1
            continue

        # MULTI-SPECIES ANNOGROUPS: use MRCA algorithm
        multi_species_count += 1

        origin, shared_clades = determine_origin(
            annogroup_species,
            species_clade_id_names___phylogenetic_paths,
            parents___children,
            clade_names___clade_id_names
        )

        if origin is None:
            origin_not_found_count += 1
            continue

        annogroup_origins[ annogroup_id ] = {
            'origin': origin,
            'shared_clades': shared_clades,
            'species': annogroup_species,
            'species_count': len( annogroup_species ),
            'annogroup_subtype': annogroup_data[ 'annogroup_subtype' ]
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
# SECTION 6: WRITE OUTPUTS
# ============================================================================

def write_annogroup_origins( annogroup_origins, clade_id_names___phylogenetic_blocks, clade_id_names___phylogenetic_paths ):
    """Write per-annogroup origin assignments.

    Per Rule 6, the origin is identified by the canonical clade_id_name form.
    Per Rule 7, the origin is a phylogenetic transition block (state O), fully
    specified by the block identifier parent::child and the block-state
    identifier parent::child-O.
    """
    logger.info( f"Writing annogroup origins to: {output_origins_file}" )

    with open( output_origins_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Per Rule 7, origin is a phylogenetic transition block (state O).
        header_columns = [
            'Annogroup_ID (annogroup identifier)',
            'Annogroup_Subtype (single or combo or zero)',
            'Origin_Phylogenetic_Block (phylogenetic block containing the origin transition format Parent_Clade_ID_Name::Child_Clade_ID_Name)',
            'Origin_Phylogenetic_Block_State (phylogenetic transition block for origin in five-state vocabulary format Parent_Clade_ID_Name::Child_Clade_ID_Name-O where the -O suffix marks Origin; five states are A=Inherited Absence O=Origin P=Inherited Presence L=Loss X=Inherited Loss)',
            'Origin_Phylogenetic_Path (phylogenetic path from root to the child endpoint of the origin block comma delimited as clade_id_name values)',
            'Shared_Clade_ID_Names (comma delimited list of shared ancestral clade_id_name values)',
            'Species_Count (total unique species in annogroup)',
            'Species_List (comma delimited list of species in annogroup)'
        ]

        # Single-row header
        csv_writer.writerow( header_columns )

        for annogroup_id in sorted( annogroup_origins.keys() ):
            data = annogroup_origins[ annogroup_id ]

            origin = data[ 'origin' ]  # clade_id_name
            shared_clades_string = ','.join( sorted( data[ 'shared_clades' ] ) )
            species_count = data[ 'species_count' ]
            annogroup_subtype = data[ 'annogroup_subtype' ]

            # Look up phylogenetic block and path for origin clade (both keyed by clade_id_name).
            phylogenetic_block = clade_id_names___phylogenetic_blocks.get( origin, 'NA' )
            phylogenetic_block_state = f"{phylogenetic_block}-O" if phylogenetic_block != 'NA' else 'NA'
            phylogenetic_path = clade_id_names___phylogenetic_paths.get( origin, 'NA' )

            species_list = ','.join( sorted( data[ 'species' ] ) )

            output_row = [
                annogroup_id,
                annogroup_subtype,
                phylogenetic_block,
                phylogenetic_block_state,
                phylogenetic_path,
                shared_clades_string,
                str( species_count ),
                species_list
            ]

            csv_writer.writerow( output_row )

    logger.info( f"Wrote {len( annogroup_origins )} annogroup origins to {output_origins_file.name}" )


def write_origins_summary( origins___annogroup_ids, clade_id_names___phylogenetic_blocks ):
    """Write summary of annogroup counts per phylogenetic origin transition block.

    Per Rule 7, origins are phylogenetic transition blocks (state O), not clades.
    Grouping is therefore on the block-state identifier parent::child-O.
    """
    logger.info( f"Writing origins summary to: {output_summary_file}" )

    total_annogroups = sum( len( annogroup_list ) for annogroup_list in origins___annogroup_ids.values() )

    with open( output_summary_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Origin_Phylogenetic_Block_State (phylogenetic transition block for origin format Parent_Clade_ID_Name::Child_Clade_ID_Name-O e.g. C069_Holozoa::C082_Metazoa-O)\t'
        output += 'Annogroup_Count (count of annogroups whose origin is this transition block)\t'
        output += 'Percentage (percentage of all annogroups originating on this transition block)\n'
        output_file.write( output )

        # Sort by count descending.
        sorted_origins = sorted( origins___annogroup_ids.items(), key = lambda x: len( x[ 1 ] ), reverse = True )

        for origin_child_clade_id_name, annogroup_list in sorted_origins:
            phylogenetic_block = clade_id_names___phylogenetic_blocks.get( origin_child_clade_id_name, 'NA' )
            phylogenetic_block_state = f"{phylogenetic_block}-O" if phylogenetic_block != 'NA' else 'NA'

            count = len( annogroup_list )
            percentage = 100.0 * count / total_annogroups if total_annogroups > 0 else 0.0

            output = f"{phylogenetic_block_state}\t{count}\t{percentage:.2f}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( origins___annogroup_ids )} origin transition blocks to {output_summary_file.name}" )


def write_annogroups_by_origin( origins___annogroup_ids, clade_id_names___phylogenetic_blocks ):
    """Write separate files for annogroups grouped by origin transition block.

    Per Rule 7, files are named by the block-state identifier parent::child-O.
    File names use the block-state string with :: replaced by __ so the
    identifier is filesystem-safe while remaining unambiguously recoverable.
    """
    logger.info( f"Writing annogroups by origin to: {output_by_origin_directory}" )

    for origin_child_clade_id_name, annogroup_list in origins___annogroup_ids.items():
        phylogenetic_block = clade_id_names___phylogenetic_blocks.get( origin_child_clade_id_name, 'NA' )
        if phylogenetic_block == 'NA':
            phylogenetic_block_state = f"NA-{origin_child_clade_id_name}-O"
        else:
            phylogenetic_block_state = f"{phylogenetic_block}-O"

        # Filesystem-safe form: replace :: with __ to keep the identifier
        # readable and reversible when reading the file name back.
        safe_file_stem = phylogenetic_block_state.replace( '::', '__' ).replace( ' ', '_' ).replace( '/', '_' )
        output_file_path = output_by_origin_directory / f"{safe_file_stem}_annogroups.txt"

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
    # Per Rule 6 of AI_GUIDE-project.md, all dicts are keyed by clade_id_name.
    logger.info( "STEP 1: Loading phylogenetic tree structure..." )
    parents___children, children___parents = load_parent_child_relationships()
    clade_names___clade_id_names = load_clade_mappings()

    # Step 2: Load phylogenetic paths
    logger.info( "" )
    logger.info( "STEP 2: Loading phylogenetic paths..." )
    species_clade_id_names___phylogenetic_paths = load_phylogenetic_paths()

    # Step 3: Load annogroups (species already resolved -- no GIGANTIC ID parsing)
    logger.info( "" )
    logger.info( "STEP 3: Loading annogroups (species already resolved to Genus_species)..." )
    annogroup_ids___annogroup_data = load_annogroups()

    # Step 4: Load phylogenetic blocks and paths from trees_species
    logger.info( "" )
    logger.info( "STEP 4: Loading phylogenetic blocks and paths from trees_species..." )
    clade_id_names___phylogenetic_blocks = load_phylogenetic_blocks_for_structure()
    clade_id_names___phylogenetic_paths = load_phylogenetic_paths_for_structure()

    # Step 5: Determine origins for all annogroups
    logger.info( "" )
    logger.info( "STEP 5: Determining phylogenetic origins..." )
    annogroup_origins, origins___annogroup_ids = process_annogroups(
        annogroup_ids___annogroup_data,
        species_clade_id_names___phylogenetic_paths,
        parents___children,
        clade_names___clade_id_names
    )

    # Step 6: Write outputs
    logger.info( "" )
    logger.info( "STEP 6: Writing outputs..." )
    write_annogroup_origins( annogroup_origins, clade_id_names___phylogenetic_blocks, clade_id_names___phylogenetic_paths )
    write_origins_summary( origins___annogroup_ids, clade_id_names___phylogenetic_blocks )
    write_annogroups_by_origin( origins___annogroup_ids, clade_id_names___phylogenetic_blocks )

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
