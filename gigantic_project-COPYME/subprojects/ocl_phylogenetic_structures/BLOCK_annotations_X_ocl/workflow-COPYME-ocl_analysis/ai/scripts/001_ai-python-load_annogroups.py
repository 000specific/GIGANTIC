# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Create annotation groups (annogroups) from annotation files and prepare inputs for OCL analysis
# AI: Claude Code | Opus 4.8 | 2026 June 05 | Purpose: Capture per-accession descriptions and emit Annotation_Definitions (def ==acc) alongside Annotation_Accessions on annogroup outputs
# AI: Claude Code | Opus 4.8 | 2026 June 18 | Purpose: Import-only refactor — load annogroups (feature/combination/architecture/absent) from the annogroups subproject instead of computing them; map onto each structure
# Human: Eric Edsinger

"""
OCL Pipeline Script 001: Load Annogroups + Prepare Phylogenetic Inputs

Annogroups are NOT computed here. They are produced ONCE, structure-independent,
by the annogroups subproject (the four canonical types: feature, combination,
architecture, absent) and imported via output_to_input. This OCL BLOCK only
MAPS those annogroups onto each species-tree structure (Scripts 002-005 do the
origin / conservation / loss inference, which IS the structure-specific step).

Per structure this script:

Phase A: Load + write phylogenetic tree data from trees_species (Rule 6 atomic)
  - Phylogenetic blocks (parent_clade_id_name::child_clade_id_name)
  - Parent-child relationships (Rule 6 atomic 3-column format)
  - Phylogenetic paths (root-to-tip for each species)
  - Clade mappings (bare Clade_Name -> atomic Clade_ID_Name)

Phase B: Load annogroups for the configured source from the annogroups subproject
  - Reads <annogroups_dir>/<species_set>/<source>/2_ai-<source>-annogroup_map.tsv
    (Annogroup_ID, Annogroup_Type, Defining_Features, Annotation_Definitions,
     Species_Count, Species_List). The species list per annogroup is
     structure-independent; the same set is mapped onto every structure.

Phase C: Write OCL-standardized annogroup inputs for Scripts 002-005
  - 1_ai-<structure>_annogroups-species_identifiers.tsv (column order fixed:
    Annogroup_ID, Annogroup_Type, Species_Count, Species_List,
    Annotation_Accessions, Annotation_Definitions)
  - 1_ai-<structure>_annogroup_map.tsv (Annogroup_ID -> accessions/definitions,
    consumed by Scripts 002/003/004 via load_annogroup_annotation_lookup)

Inputs from upstream subprojects via output_to_input:
  - trees_species (phylogenetic features: blocks, parent-child, paths)
  - annogroups (BLOCK_build_annogroups per-source annogroup map)

Usage:
    python 001_ai-python-load_annogroups.py --structure_id 001 --config ../../START_HERE-user_config.yaml
"""

import sys
import logging
import argparse
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import yaml

# Add scripts directory to path for utility imports
sys.path.insert( 0, str( Path( __file__ ).parent ) )
from utils_run_summary import emit_run_summary_fragment


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'OCL Pipeline Script 001: Load annogroups + prepare phylogenetic inputs',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--structure_id',
        type = str,
        required = True,
        help = 'Structure ID to process (e.g., "001", "002", ..., "105")'
    )

    parser.add_argument(
        '--source',
        type = str,
        required = True,
        help = 'Annotation source to process (e.g., "pfam", "go", "panther"). The run '
               'fans out over sources x structures; this selects the per-source annogroups.'
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

# Parse arguments
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

# Species set from config; annotation source from --source (the run fans out over
# sources x structures). ANNOTATION_DATABASE names the annogroups subproject source
# (e.g. "pfam") -- annogroups are NOT computed here.
SPECIES_SET_NAME = config[ 'species_set_name' ]
ANNOTATION_DATABASE = args.source

# Annogroup types to map onto the structures. 'absent' is excluded by design
# (it has no single evolutionary origin); default to the origin-bearing types.
ANNOGROUP_TYPES = set( config.get( 'annogroup_types', [ 'feature', 'combination', 'architecture' ] ) )

# Resolve input paths relative to config file directory
config_directory = config_path.parent

input_trees_species_directory = config_directory / config[ 'inputs' ][ 'trees_species_dir' ]

# annogroups subproject output_to_input ROOT (the BLOCK_build_annogroups dir).
# The per-source annogroup map lives at:
#   <root>/<species_set>/<source>/2_ai-<source>-annogroup_map.tsv
input_annogroups_directory = config_directory / config[ 'inputs' ][ 'annogroups_dir' ] / SPECIES_SET_NAME / ANNOTATION_DATABASE
input_annogroup_map_file = input_annogroups_directory / f'2_ai-{ANNOTATION_DATABASE}-annogroup_map.tsv'

# Input files from trees_species
input_phylogenetic_blocks_file = input_trees_species_directory / 'Species_Phylogenetic_Blocks'
input_parent_child_directory = input_trees_species_directory / 'Species_Parent_Child_Relationships'
input_phylogenetic_paths_directory = input_trees_species_directory / 'Species_Phylogenetic_Paths'

# Output directory
# Prefer --output_dir (passed by NextFlow main.nf for consistency with scripts 003-005);
# fall back to config.output.base_dir relative to config file when invoked standalone.
if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]
output_directory = output_base_directory / TARGET_STRUCTURE / '1-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files - phylogenetic data (Rule 6 atomic identifiers)
output_phylogenetic_blocks_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_phylogenetic_blocks.tsv'
output_parent_child_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_parent_child_table.tsv'
output_phylogenetic_paths_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_phylogenetic_paths.tsv'
output_clade_mappings_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_clade_mappings.tsv'

# Output files - annogroup data (imported from the annogroups subproject, then
# emitted in the OCL-standardized shape consumed by Scripts 002-005)
output_annogroup_map_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_annogroup_map.tsv'
output_annogroups_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_annogroups-species_identifiers.tsv'

# Log directory
log_directory = output_base_directory / TARGET_STRUCTURE / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / f'1_ai-log-load_annogroups-{TARGET_STRUCTURE}.log'


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
# PHASE A: LOAD PHYLOGENETIC TREE DATA (Rule 6 atomic identifiers)
# ============================================================================

# --- Section A1: Load Phylogenetic Blocks ---

def load_phylogenetic_blocks():
    """
    Load phylogenetic blocks for the target structure from trees_species.

    Scans the Species_Phylogenetic_Blocks directory for the combined blocks file
    (Rule 6/7 atomic column format produced by trees_species Script 006) and
    filters to the target structure.

    Returns:
        dict: keyed by atomic Child_Clade_ID_Name (Rule 6):
            { child_clade_id_name: { 'phylogenetic_block': str,
                                     'parent_clade_id_name': str,
                                     'structure_id': str } }
    """
    logger.info( f"Loading phylogenetic blocks from: {input_phylogenetic_blocks_file}" )

    # Find the combined phylogenetic blocks file (contains all structures).
    phylogenetic_blocks_files = list( input_phylogenetic_blocks_file.glob( '*phylogenetic_blocks-all_*_structures.tsv' ) )

    if not phylogenetic_blocks_files:
        logger.error( f"CRITICAL ERROR: No combined phylogenetic blocks file found!" )
        logger.error( f"Expected pattern: *phylogenetic_blocks-all_*_structures.tsv" )
        logger.error( f"In location: {input_phylogenetic_blocks_file}" )
        logger.error( f"Run trees_species pipeline first to generate phylogenetic blocks." )
        sys.exit( 1 )

    if len( phylogenetic_blocks_files ) > 1:
        logger.error( f"CRITICAL ERROR: Multiple combined phylogenetic blocks files found (ambiguous):" )
        for blocks_file in sorted( phylogenetic_blocks_files ):
            logger.error( f"  {blocks_file.name}" )
        sys.exit( 1 )

    phylogenetic_blocks_path = phylogenetic_blocks_files[ 0 ]
    logger.info( f"Using file: {phylogenetic_blocks_path.name}" )

    child_clade_id_names___block_data = {}

    with open( phylogenetic_blocks_path, 'r' ) as input_file:
        # Structure_ID (tree topology structure identifier)	Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)	Parent_Clade_ID_Name (atomic parent clade identifier)	Child_Clade_ID_Name (atomic child clade identifier)
        # structure_001	C000_OOL::C071_Basal	C000_OOL	C071_Basal
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        structure_id_column = column_names___indices.get( 'Structure_ID' )
        phylogenetic_block_column = column_names___indices.get( 'Phylogenetic_Block' )
        parent_clade_id_name_column = column_names___indices.get( 'Parent_Clade_ID_Name' )
        child_clade_id_name_column = column_names___indices.get( 'Child_Clade_ID_Name' )

        required = {
            'Structure_ID': structure_id_column,
            'Phylogenetic_Block': phylogenetic_block_column,
            'Parent_Clade_ID_Name': parent_clade_id_name_column,
            'Child_Clade_ID_Name': child_clade_id_name_column,
        }
        missing = [ name for name, idx in required.items() if idx is None ]
        if missing:
            logger.error( f"CRITICAL ERROR: Phylogenetic blocks file missing required columns: {missing}" )
            logger.error( f"Found columns: {header_parts}" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]
            phylogenetic_block = parts[ phylogenetic_block_column ]
            parent_clade_id_name = parts[ parent_clade_id_name_column ]
            child_clade_id_name = parts[ child_clade_id_name_column ]

            # Only load blocks for target structure
            if structure_id == TARGET_STRUCTURE:
                child_clade_id_names___block_data[ child_clade_id_name ] = {
                    'phylogenetic_block': phylogenetic_block,
                    'parent_clade_id_name': parent_clade_id_name,
                    'structure_id': structure_id
                }

    logger.info( f"Loaded {len( child_clade_id_names___block_data )} phylogenetic blocks for {TARGET_STRUCTURE}" )

    if len( child_clade_id_names___block_data ) == 0:
        logger.error( f"CRITICAL ERROR: No blocks loaded for {TARGET_STRUCTURE}!" )
        logger.error( f"Check that structure exists in: {phylogenetic_blocks_path}" )
        sys.exit( 1 )

    return child_clade_id_names___block_data


def write_phylogenetic_blocks( child_clade_id_names___block_data ):
    """Write phylogenetic blocks to standardized output file (Rule 6 atomic identifiers)."""
    logger.info( f"Writing phylogenetic blocks to: {output_phylogenetic_blocks_file}" )

    with open( output_phylogenetic_blocks_file, 'w' ) as output_file:
        output = 'Structure_ID (structure identifier for this phylogenetic tree)\t'
        output += 'Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)\t'
        output += 'Parent_Clade_ID_Name (atomic parent clade identifier)\t'
        output += 'Child_Clade_ID_Name (atomic child clade identifier)\n'
        output_file.write( output )

        for child_clade_id_name in sorted( child_clade_id_names___block_data.keys() ):
            block_data = child_clade_id_names___block_data[ child_clade_id_name ]
            phylogenetic_block = block_data[ 'phylogenetic_block' ]
            parent_clade_id_name = block_data[ 'parent_clade_id_name' ]
            structure_id = block_data[ 'structure_id' ]

            output = f"{structure_id}\t{phylogenetic_block}\t{parent_clade_id_name}\t{child_clade_id_name}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( child_clade_id_names___block_data )} blocks to {output_phylogenetic_blocks_file.name}" )


# --- Section A2: Load Parent-Child Relationships ---

def load_parent_child_relationships():
    """
    Load parent-child relationships for the target structure from trees_species.

    Reads the structure-specific parent-child file produced by trees_species
    Script 005 (Rule 6/7 atomic 3-column format, no self-loops).

    Returns:
        list: [ { 'phylogenetic_block': str,
                  'parent_clade_id_name': str,
                  'child_clade_id_name': str } ]
    """
    logger.info( f"Loading parent-child relationships from: {input_parent_child_directory}" )

    parent_child_files = list( input_parent_child_directory.glob( f'*{TARGET_STRUCTURE}*parent_child*.tsv' ) )

    if not parent_child_files:
        parent_child_files = list( input_parent_child_directory.glob( f'*{args.structure_id}*parent_child*.tsv' ) )

    if not parent_child_files:
        logger.error( f"CRITICAL ERROR: Parent-child file not found for {TARGET_STRUCTURE}!" )
        logger.error( f"Expected in: {input_parent_child_directory}" )
        logger.error( f"Run trees_species pipeline first to generate parent-child relationships." )
        sys.exit( 1 )

    parent_child_path = parent_child_files[ 0 ]
    logger.info( f"Using file: {parent_child_path.name}" )

    relationships = []

    with open( parent_child_path, 'r' ) as input_file:
        # Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)	Parent_Clade_ID_Name (atomic parent clade identifier)	Child_Clade_ID_Name (atomic child clade identifier)
        # C069_Holozoa::C082_Metazoa	C069_Holozoa	C082_Metazoa
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        phylogenetic_block_column = column_names___indices.get( 'Phylogenetic_Block' )
        parent_clade_id_name_column = column_names___indices.get( 'Parent_Clade_ID_Name' )
        child_clade_id_name_column = column_names___indices.get( 'Child_Clade_ID_Name' )

        required = {
            'Phylogenetic_Block': phylogenetic_block_column,
            'Parent_Clade_ID_Name': parent_clade_id_name_column,
            'Child_Clade_ID_Name': child_clade_id_name_column,
        }
        missing = [ name for name, idx in required.items() if idx is None ]
        if missing:
            logger.error( f"CRITICAL ERROR: Parent-child relationships file missing required columns: {missing}" )
            logger.error( f"Found columns: {header_parts}" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) <= max( required.values() ):
                logger.warning( f"Row has fewer columns than required, skipping: {line[:80]}" )
                continue

            relationships.append( {
                'phylogenetic_block': parts[ phylogenetic_block_column ],
                'parent_clade_id_name': parts[ parent_clade_id_name_column ],
                'child_clade_id_name': parts[ child_clade_id_name_column ],
            } )

    logger.info( f"Loaded {len( relationships )} parent-child relationships" )

    if len( relationships ) == 0:
        logger.error( f"CRITICAL ERROR: No parent-child relationships loaded!" )
        sys.exit( 1 )

    return relationships


def write_parent_child_relationships( relationships ):
    """Write parent-child relationships to standardized output file (Rule 6 atomic identifiers)."""
    logger.info( f"Writing parent-child relationships to: {output_parent_child_file}" )

    with open( output_parent_child_file, 'w' ) as output_file:
        output = 'Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)\t'
        output += 'Parent_Clade_ID_Name (atomic parent clade identifier)\t'
        output += 'Child_Clade_ID_Name (atomic child clade identifier)\n'
        output_file.write( output )

        for relationship in relationships:
            output = f"{relationship[ 'phylogenetic_block' ]}\t"
            output += f"{relationship[ 'parent_clade_id_name' ]}\t"
            output += f"{relationship[ 'child_clade_id_name' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( relationships )} relationships to {output_parent_child_file.name}" )


# --- Section A3: Load Phylogenetic Paths ---

def load_phylogenetic_paths():
    """
    Load phylogenetic paths (root-to-leaf) for the target structure from trees_species.

    Returns:
        dict: { leaf_clade_id: [ clade_id_1, clade_id_2, ..., leaf_clade_id ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_directory}" )

    # Find the combined phylogenetic paths file (contains all structures).
    # Path.glob() does not guarantee ordering (especially on Lustre), so match
    # the combined file explicitly rather than relying on [0].
    paths_files = list( input_phylogenetic_paths_directory.glob( '*phylogenetic_paths-all_structures.tsv' ) )

    if not paths_files:
        logger.warning( f"No combined phylogenetic paths file found in: {input_phylogenetic_paths_directory}" )
        logger.info( "Paths will need to be generated from phylogenetic blocks if needed downstream" )
        return {}

    if len( paths_files ) > 1:
        logger.error( f"CRITICAL ERROR: Multiple combined phylogenetic paths files found (ambiguous):" )
        for paths_file in sorted( paths_files ):
            logger.error( f"  {paths_file.name}" )
        sys.exit( 1 )

    paths_path = paths_files[ 0 ]
    logger.info( f"Using file: {paths_path.name}" )

    leaf_clade_ids___paths = {}

    with open( paths_path, 'r' ) as input_file:
        # Structure_ID (structure identifier)	Species_Clade_ID_Name (species clade identifier and name)	Species_Name (species name)	Phylogenetic_Path (...)
        # structure_001	C001_Fonticula_alba	Fonticula_alba	C068_Basal>C069_Holomycota>C001_Fonticula_alba
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        # Find column indices dynamically
        structure_id_column = None
        species_clade_id_column = None
        path_column = None

        for index, column_header in enumerate( header_parts ):
            column_id = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            if column_id == 'Structure_ID':
                structure_id_column = index
            elif column_id in [ 'Species_Clade_ID_Name', 'Species_Clade_ID', 'Leaf_Clade_ID' ]:
                species_clade_id_column = index
            elif 'Path' in column_id or 'path' in column_id:
                path_column = index

        if structure_id_column is None or species_clade_id_column is None or path_column is None:
            logger.error( f"CRITICAL ERROR: Could not find required columns in paths file!" )
            logger.error( f"Found columns: {header_parts}" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]

            # Only load paths for target structure
            if structure_id != TARGET_STRUCTURE:
                continue

            leaf_clade_id = parts[ species_clade_id_column ]
            path_string = parts[ path_column ]

            # Handle both comma-delimited and > delimited paths
            if '>' in path_string:
                path = path_string.split( '>' )
            else:
                path = path_string.split( ',' )
            path = [ node.strip() for node in path ]

            leaf_clade_ids___paths[ leaf_clade_id ] = path

    logger.info( f"Loaded {len( leaf_clade_ids___paths )} phylogenetic paths for {TARGET_STRUCTURE}" )
    return leaf_clade_ids___paths


def write_phylogenetic_paths( leaf_clade_ids___paths ):
    """Write phylogenetic paths to standardized output file."""
    logger.info( f"Writing phylogenetic paths to: {output_phylogenetic_paths_file}" )

    with open( output_phylogenetic_paths_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Leaf_Clade_ID (terminal leaf clade identifier and name)\t'
        output += 'Path_Length (number of nodes in path from root to leaf)\t'
        output += 'Phylogenetic_Path (comma delimited path from root to leaf)\n'
        output_file.write( output )

        for leaf_clade_id in sorted( leaf_clade_ids___paths.keys() ):
            path = leaf_clade_ids___paths[ leaf_clade_id ]
            path_length = len( path )
            path_string = ','.join( path )

            output = f"{leaf_clade_id}\t{path_length}\t{path_string}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( leaf_clade_ids___paths )} paths to {output_phylogenetic_paths_file.name}" )


# --- Section A4: Write Clade Mappings ---

def write_clade_mappings( child_clade_id_names___block_data ):
    """
    Write clade name -> clade_id_name mappings to standardized output file.

    Purpose of this file: a translation table for downstream OCL scripts that
    receive bare clade/species names and need to resolve them to the atomic
    Rule 6 clade_id_name form. Both columns are emitted explicitly: Clade_Name
    is the lookup key (bare name as it appears in annogroup species lists),
    Clade_ID_Name is the atomic value.
    """
    logger.info( f"Writing clade mappings to: {output_clade_mappings_file}" )

    with open( output_clade_mappings_file, 'w' ) as output_file:
        output = 'Clade_Name (bare clade name lookup key as it appears in annogroup species lists)\t'
        output += 'Clade_ID_Name (atomic clade identifier e.g. C001_Fonticula_alba)\n'
        output_file.write( output )

        for child_clade_id_name in sorted( child_clade_id_names___block_data.keys() ):
            # child_clade_id_name is the atomic form; derive bare name as text after first underscore
            if '_' in child_clade_id_name:
                clade_name = child_clade_id_name.split( '_', 1 )[ 1 ]
            else:
                clade_name = child_clade_id_name

            output = f"{clade_name}\t{child_clade_id_name}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( child_clade_id_names___block_data )} clade mappings to {output_clade_mappings_file.name}" )


# ============================================================================
# PHASE B: LOAD ANNOGROUPS FROM THE ANNOGROUPS SUBPROJECT (import-only)
# ============================================================================

def load_annogroups_from_subproject():
    """
    Load the per-source annogroup map produced by the annogroups subproject.

    Annogroups (feature / combination / architecture / absent) are computed ONCE,
    structure-independent, by BLOCK_build_annogroups. This OCL BLOCK imports them
    and maps them onto each species-tree structure -- it does NOT recompute them.

    Reads <annogroups_dir>/<species_set>/<source>/2_ai-<source>-annogroup_map.tsv.
    Columns are located by self-documenting header_ID (order-independent):
      Annogroup_ID, Annogroup_Type, Defining_Features, Annotation_Definitions,
      Species_Count, Species_List

    Returns:
        tuple: ( annogroup_entries, types___counts )
        annogroup_entries: list of dicts, one per annogroup:
            { 'annogroup_id', 'annogroup_type', 'annotation_accessions',
              'annotation_definitions', 'species_count', 'species', 'species_list' }
        types___counts: { annogroup_type: count }
    """
    logger.info( f"Loading annogroups from annogroups subproject: {input_annogroup_map_file}" )

    if not input_annogroup_map_file.is_file():
        logger.error( f"CRITICAL ERROR: annogroup map not found!" )
        logger.error( f"Expected location: {input_annogroup_map_file}" )
        logger.error( f"Run the annogroups subproject (BLOCK_build_annogroups) for source "
                      f"'{ANNOTATION_DATABASE}' / species set '{SPECIES_SET_NAME}' first, and verify "
                      f"inputs.annogroups_dir points at its output_to_input/BLOCK_build_annogroups root." )
        sys.exit( 1 )

    annogroup_entries = []

    with open( input_annogroup_map_file, 'r' ) as input_file:
        # Annogroup_ID (...)	Source (...)	Annogroup_Type (...)	Defining_Features (...)	Annotation_Definitions (...)	Sequence_Count (...)	Species_Count (...)	Species_List (...)
        header = input_file.readline()
        header_parts = header.rstrip( '\n' ).split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        required = [ 'Annogroup_ID', 'Annogroup_Type', 'Defining_Features',
                     'Annotation_Definitions', 'Species_Count', 'Species_List' ]
        missing = [ name for name in required if name not in column_names___indices ]
        if missing:
            logger.error( f"CRITICAL ERROR: annogroup map missing required columns: {missing}" )
            logger.error( f"Found columns: {header_parts}" )
            sys.exit( 1 )

        index_id = column_names___indices[ 'Annogroup_ID' ]
        index_type = column_names___indices[ 'Annogroup_Type' ]
        index_features = column_names___indices[ 'Defining_Features' ]
        index_definitions = column_names___indices[ 'Annotation_Definitions' ]
        index_species_count = column_names___indices[ 'Species_Count' ]
        index_species_list = column_names___indices[ 'Species_List' ]

        for line in input_file:
            line = line.rstrip( '\n' )
            if not line:
                continue

            parts = line.split( '\t' )

            # Skip annogroup types not selected for OCL (notably 'absent', which
            # has no single evolutionary origin -- see config annogroup_types).
            if parts[ index_type ] not in ANNOGROUP_TYPES:
                continue

            species_list_string = parts[ index_species_list ]
            species = [ species_name.strip() for species_name in species_list_string.split( ',' ) if species_name.strip() ]

            annogroup_entries.append( {
                'annogroup_id': parts[ index_id ],
                'annogroup_type': parts[ index_type ],
                'annotation_accessions': parts[ index_features ],
                'annotation_definitions': parts[ index_definitions ],
                'species_count': int( parts[ index_species_count ] ) if parts[ index_species_count ] else len( species ),
                'species': species,
                'species_list': species_list_string,
            } )

    logger.info( f"Loaded {len( annogroup_entries )} annogroups from the annogroups subproject" )

    if len( annogroup_entries ) == 0:
        logger.error( f"CRITICAL ERROR: No annogroups loaded from {input_annogroup_map_file}!" )
        sys.exit( 1 )

    types___counts = defaultdict( int )
    for entry in annogroup_entries:
        types___counts[ entry[ 'annogroup_type' ] ] += 1
    for annogroup_type in sorted( types___counts.keys() ):
        logger.info( f"  {annogroup_type}: {types___counts[ annogroup_type ]}" )

    return annogroup_entries, dict( types___counts )


# ============================================================================
# PHASE C: WRITE OCL-STANDARDIZED ANNOGROUP INPUTS (for Scripts 002-005)
# ============================================================================

def write_annogroups_standardized( annogroup_entries ):
    """
    Write the standardized annogroups file consumed by Scripts 002-005.

    Column order is FIXED -- Scripts 002-005 read columns 0-3 positionally
    (Annogroup_ID, Annogroup_Type, Species_Count, Species_List); the two
    annotation context columns follow.
    """
    logger.info( f"Writing standardized annogroups to: {output_annogroups_file}" )

    with open( output_annogroups_file, 'w' ) as output_file:
        output = 'Annogroup_ID (canonical annogroup identifier from the annogroups subproject)\t'
        output += 'Annogroup_Type (one of feature, combination, architecture, absent)\t'
        output += 'Species_Count (number of unique species in annogroup)\t'
        output += 'Species_List (comma delimited list of species names as Genus_species)\t'
        output += 'Annotation_Accessions (comma delimited annotation accessions defining this annogroup; empty for absent)\t'
        output += 'Annotation_Definitions (semicolon delimited definition ==accession pairs; empty for absent)\n'
        output_file.write( output )

        for entry in annogroup_entries:
            output = f"{entry[ 'annogroup_id' ]}\t"
            output += f"{entry[ 'annogroup_type' ]}\t"
            output += f"{entry[ 'species_count' ]}\t"
            output += f"{entry[ 'species_list' ]}\t"
            output += f"{entry[ 'annotation_accessions' ]}\t"
            output += f"{entry[ 'annotation_definitions' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( annogroup_entries )} annogroups to {output_annogroups_file.name}" )


def write_annogroup_map( annogroup_entries ):
    """
    Write the annogroup map (Annogroup_ID -> annotation accessions/definitions).

    Consumed by Scripts 002/003/004 via load_annogroup_annotation_lookup to
    append Annotation_Accessions + Annotation_Definitions to their outputs.
    """
    logger.info( f"Writing annogroup map to: {output_annogroup_map_file}" )

    with open( output_annogroup_map_file, 'w' ) as output_file:
        output = 'Annogroup_ID (canonical annogroup identifier)\t'
        output += 'Annogroup_Type (one of feature, combination, architecture, absent)\t'
        output += 'Annotation_Database (annotation source database)\t'
        output += 'Annotation_Accessions (comma delimited annotation accessions defining this annogroup; empty for absent)\t'
        output += 'Annotation_Definitions (semicolon delimited definition ==accession pairs; empty for absent)\t'
        output += 'Species_Count (number of unique species with at least one member sequence)\n'
        output_file.write( output )

        for entry in annogroup_entries:
            output = f"{entry[ 'annogroup_id' ]}\t"
            output += f"{entry[ 'annogroup_type' ]}\t"
            output += f"{ANNOTATION_DATABASE}\t"
            output += f"{entry[ 'annotation_accessions' ]}\t"
            output += f"{entry[ 'annotation_definitions' ]}\t"
            output += f"{entry[ 'species_count' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( annogroup_entries )} entries to {output_annogroup_map_file.name}" )


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    start_time = time.time()

    logger.info( "=" * 80 )
    logger.info( "SCRIPT 001: LOAD ANNOGROUPS + PREPARE PHYLOGENETIC INPUTS" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Species set: {SPECIES_SET_NAME}" )
    logger.info( f"Annotation source: {ANNOTATION_DATABASE}" )
    logger.info( f"Config file: {config_path}" )
    logger.info( "" )

    # ========================================================================
    # PHASE A: Load phylogenetic tree data (Rule 6 atomic identifiers)
    # ========================================================================
    logger.info( "PHASE A: Loading phylogenetic tree data (Rule 6 atomic identifiers)..." )

    logger.info( "" )
    logger.info( "STEP A1: Loading phylogenetic blocks..." )
    child_clade_id_names___block_data = load_phylogenetic_blocks()
    write_phylogenetic_blocks( child_clade_id_names___block_data )

    logger.info( "" )
    logger.info( "STEP A2: Loading parent-child relationships..." )
    relationships = load_parent_child_relationships()
    write_parent_child_relationships( relationships )

    logger.info( "" )
    logger.info( "STEP A3: Loading phylogenetic paths..." )
    leaf_clade_ids___paths = load_phylogenetic_paths()
    if leaf_clade_ids___paths:
        write_phylogenetic_paths( leaf_clade_ids___paths )
    else:
        logger.info( "No paths file found - will be generated from blocks if needed downstream" )

    logger.info( "" )
    logger.info( "STEP A4: Creating clade name to clade_id_name mappings..." )
    write_clade_mappings( child_clade_id_names___block_data )

    # ========================================================================
    # PHASE B: Load annogroups from the annogroups subproject (import-only)
    # ========================================================================
    logger.info( "" )
    logger.info( "PHASE B: Loading annogroups from the annogroups subproject..." )
    annogroup_entries, types___counts = load_annogroups_from_subproject()

    # ========================================================================
    # PHASE C: Write OCL-standardized annogroup inputs for Scripts 002-005
    # ========================================================================
    logger.info( "" )
    logger.info( "PHASE C: Writing OCL-standardized annogroup inputs..." )
    write_annogroup_map( annogroup_entries )
    write_annogroups_standardized( annogroup_entries )

    # ========================================================================
    # Complete
    # ========================================================================
    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 001 COMPLETED SUCCESSFULLY" )
    logger.info( "=" * 80 )
    logger.info( f"All outputs written to: {output_directory}" )
    logger.info( f"Finished: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "" )
    logger.info( "Output files:" )
    logger.info( f"  {output_phylogenetic_blocks_file.name}" )
    logger.info( f"  {output_parent_child_file.name}" )
    if leaf_clade_ids___paths:
        logger.info( f"  {output_phylogenetic_paths_file.name}" )
    logger.info( f"  {output_clade_mappings_file.name}" )
    logger.info( f"  {output_annogroup_map_file.name}" )
    logger.info( f"  {output_annogroups_file.name}" )
    logger.info( "" )
    logger.info( f"Total annogroups: {len( annogroup_entries )}" )
    for annogroup_type, count in sorted( types___counts.items() ):
        logger.info( f"  {annogroup_type}: {count}" )
    logger.info( "=" * 80 )

    # Emit run summary fragment
    duration_seconds = time.time() - start_time
    emit_run_summary_fragment(
        script_number = 1,
        structure_id = args.structure_id,
        source = args.source,
        stats = {
            'duration_seconds': round( duration_seconds, 2 ),
            'annogroups_total': len( annogroup_entries ),
            'annogroups_by_type': types___counts,
            'annotation_database': ANNOTATION_DATABASE,
            'phylogenetic_blocks_loaded': len( child_clade_id_names___block_data ),
            'phylogenetic_paths_loaded': len( leaf_clade_ids___paths ) if leaf_clade_ids___paths else 0
        }
    )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
