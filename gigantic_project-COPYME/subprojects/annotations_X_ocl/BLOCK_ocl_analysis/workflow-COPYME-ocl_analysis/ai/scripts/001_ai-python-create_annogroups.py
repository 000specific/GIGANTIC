# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Create annotation groups (annogroups) from annotation files and prepare inputs for OCL analysis
# Human: Eric Edsinger

"""
OCL Pipeline Script 001: Create Annotation Groups (Annogroups)

Creates annotation groups (annogroups) from per-species annotation files and
prepares all phylogenetic input data for Origin-Conservation-Loss analysis.

Annogroups are the annotation analog to orthogroups -- sets of proteins grouped
by their annotation pattern from a specific database. Each annogroup has a
simple ID (annogroup_{db}_N) with full details in a companion map.

Phase A: Load phylogenetic tree data from trees_species (Rule 6 atomic identifiers)
  - Phylogenetic blocks (parent_clade_id_name::child_clade_id_name)
  - Parent-child relationships (Rule 6 atomic 3-column format)
  - Phylogenetic paths (root-to-tip for each species)
  - Clade mappings (bare Clade_Name -> atomic Clade_ID_Name)

Phase B: Load annotations from raw InterProScan output (filter by database on the fly)

Phase C: Create annogroups for each requested subtype (single, combo, zero)
  The 3 annogroup subtypes (each a direct protein-level evaluation):
    single - proteins with exactly one annotation from this database
    combo  - proteins with identical multi-annotation architecture
    zero   - proteins with no annotations from this database (singletons)

Phase D: Write all outputs
  - Phylogenetic blocks, parent-child table, phylogenetic paths, clade mappings
  - Annogroup map (lookup table linking IDs to full details)
  - Per-subtype annogroup files
  - Annogroup subtypes manifest
  - Standardized annogroups file (species already resolved to Genus_species)

Inputs from upstream subprojects via output_to_input:
  - trees_species (phylogenetic features: blocks, parent-child, paths)
  - annotations_hmms/BLOCK_interproscan (raw InterProScan 15-column TSV per species;
    database filter applied on the fly from annotation_database config field)

Usage:
    python 001_ai-python-create_annogroups.py --structure_id 001 --config ../../START_HERE-user_config.yaml
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
        description = 'OCL Pipeline Script 001: Create annogroups from annotation files',
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

# Species set and annotation database from config
SPECIES_SET_NAME = config[ 'species_set_name' ]
ANNOTATION_DATABASE = config[ 'annotation_database' ]
ANNOGROUP_SUBTYPES = config[ 'annogroup_subtypes' ]

# Resolve input paths relative to config file directory
config_directory = config_path.parent

input_trees_species_directory = config_directory / config[ 'inputs' ][ 'trees_species_dir' ]
input_interproscan_directory = config_directory / config[ 'inputs' ][ 'interproscan_dir' ]

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

# Output files - annogroup data
output_annogroup_map_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_annogroup_map.tsv'
output_annogroups_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_annogroups-species_identifiers.tsv'
output_subtypes_manifest_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_annogroup_subtypes_manifest.tsv'

# Log directory
log_directory = output_base_directory / TARGET_STRUCTURE / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / f'1_ai-log-create_annogroups-{TARGET_STRUCTURE}.log'


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
# PHASE B: LOAD ANNOTATION FILES
# ============================================================================

def extract_species_name_from_phyloname( phyloname ):
    """
    Extract Genus_species from a GIGANTIC phyloname.

    Phyloname format: Kingdom_Phylum_Class_Order_Family_Genus_species
    Returns: Genus_species (handling multi-word species names)
    """
    parts_phyloname = phyloname.split( '_' )

    if len( parts_phyloname ) >= 7:
        genus = parts_phyloname[ 5 ]
        species = '_'.join( parts_phyloname[ 6: ] )
        return genus + '_' + species

    return phyloname


def load_annotation_files():
    """
    Load per-species annotation data from raw InterProScan output, filtering
    to the requested annotation_database on the fly.

    Reads the combined InterProScan TSV files (15-column standard format, no header)
    directly from BLOCK_interproscan output. This avoids the need for a separate
    pre-built annotation database step -- the database filter is applied at parse time.

    InterProScan 15-column format (tab-separated, no header):
      [0] Protein_ID (GIGANTIC format: g_XXX-t_XXX-p_XXX-n_Phyloname)
      [1] MD5
      [2] Sequence_Length
      [3] Analysis/Database (e.g. Pfam, Gene3D, PANTHER, SUPERFAMILY, CDD, SMART)
      [4] Accession (e.g. PF01931, G3DSA:3.90.950.10)
      [5] Description
      [6] Start
      [7] Stop
      [8] Score/E-value
      [9] Status (T/F)
      [10] Date
      [11] IPR_Accession
      [12] IPR_Description
      [13] GO_Terms
      [14] Pathways

    Returns:
        dict: { species_name: [ { 'sequence_identifier': str, 'annotation_identifier': str, ... } ] }
    """
    logger.info( f"Loading annotations from raw InterProScan output: {input_interproscan_directory}" )
    logger.info( f"Filtering to database: {ANNOTATION_DATABASE}" )

    if not input_interproscan_directory.exists():
        logger.error( f"CRITICAL ERROR: InterProScan output directory not found!" )
        logger.error( f"Expected location: {input_interproscan_directory}" )
        logger.error( f"Run BLOCK_interproscan pipeline first to generate InterProScan results." )
        sys.exit( 1 )

    # Find all InterProScan result TSV files (per-species combined output)
    interproscan_files = list( input_interproscan_directory.glob( '*_interproscan_results.tsv' ) )

    if len( interproscan_files ) == 0:
        logger.error( f"CRITICAL ERROR: No InterProScan result files found in {input_interproscan_directory}!" )
        sys.exit( 1 )

    logger.info( f"Found {len( interproscan_files )} InterProScan result files" )

    # Database name matching: InterProScan uses title case (e.g. "Pfam", "Gene3D"),
    # config may use lowercase (e.g. "pfam", "gene3d"). Match case-insensitively.
    target_database_lower = ANNOTATION_DATABASE.lower()

    species_names___annotations = {}
    total_annotations_loaded = 0
    total_rows_scanned = 0

    for interproscan_file in sorted( interproscan_files ):
        with open( interproscan_file, 'r' ) as input_file:
            # g_Patl_g10-t_Patl_g10.t1-p_Patl_g10.t1-n_Holomycota...Parvularia_atlantis	d0aff...	307	Gene3D	G3DSA:3.90.950.10	-	79	224	4.6E-17	T	14-03-2026	IPR029001	Inosine triphosphate pyrophosphatase-like	-	-
            # (no header -- raw InterProScan TSV format)
            for line in input_file:
                line = line.strip()
                if not line:
                    continue

                total_rows_scanned += 1

                parts = line.split( '\t' )

                if len( parts ) < 6:
                    continue

                database_name = parts[ 3 ]

                # Filter to requested database (case-insensitive)
                if database_name.lower() != target_database_lower:
                    continue

                sequence_identifier = parts[ 0 ]
                annotation_identifier = parts[ 4 ]
                annotation_details = parts[ 5 ] if parts[ 5 ] != '-' else ''

                # Extract species name from GIGANTIC protein ID
                # Format: g_XXX-t_XXX-p_XXX-n_Kingdom_Phylum_Class_Order_Family_Genus_species
                if '-n_' in sequence_identifier:
                    phyloname = sequence_identifier.split( '-n_' )[ 1 ]
                    species_name = extract_species_name_from_phyloname( phyloname )
                else:
                    # Fallback: try extracting from the file name (phyloname is in the filename)
                    species_name = None

                if not species_name:
                    continue

                if species_name not in species_names___annotations:
                    species_names___annotations[ species_name ] = []

                species_names___annotations[ species_name ].append( {
                    'phyloname': phyloname if '-n_' in sequence_identifier else '',
                    'sequence_identifier': sequence_identifier,
                    'annotation_identifier': annotation_identifier,
                    'annotation_details': annotation_details,
                    'species_name': species_name
                } )

                total_annotations_loaded += 1

    logger.info( f"Scanned {total_rows_scanned} total InterProScan rows across {len( interproscan_files )} files" )
    logger.info( f"Loaded {total_annotations_loaded} {ANNOTATION_DATABASE} annotations across {len( species_names___annotations )} species" )

    if len( species_names___annotations ) == 0:
        logger.error( f"CRITICAL ERROR: No annotations loaded for database '{ANNOTATION_DATABASE}'!" )
        logger.error( f"Available databases in InterProScan output: check column 4 of any result file" )
        logger.error( f"Common values: Pfam, Gene3D, PANTHER, SUPERFAMILY, CDD, SMART, PRINTS, SFLD, FunFam, NCBIfam" )
        sys.exit( 1 )

    return species_names___annotations


# ============================================================================
# PHASE C: CREATE ANNOGROUPS
# ============================================================================

def create_annogroups( species_names___annotations ):
    """
    Create annotation groups (annogroups) for each requested subtype.

    For each protein, evaluate its annotation status:
      single: protein has exactly 1 annotation from this database
      combo:  protein has a specific set of multiple annotations (grouped by identical set)
      zero:   protein has 0 annotations from this database (singleton annogroup)

    The annotation_identifier for zero-subtype proteins uses the format:
      unannotated_{database_name}-N

    Args:
        species_names___annotations: Dict mapping species names to annotation records

    Returns:
        tuple: ( annogroup_map_entries, subtypes___annogroup_data )
    """
    logger.info( f"Creating annogroups for database: {ANNOTATION_DATABASE}" )
    logger.info( f"Requested subtypes: {ANNOGROUP_SUBTYPES}" )

    # Step 1: Build per-protein annotation profiles
    logger.info( "Step 1: Building per-protein annotation profiles..." )

    # proteins___annotation_profiles: { sequence_identifier: { 'species_name': str, 'annotations': [ accession_1, ... ] } }
    proteins___annotation_profiles = {}

    # Also track all proteins per species (for finding unannotated ones)
    species_names___all_sequence_identifiers = defaultdict( set )

    for species_name, annotations in species_names___annotations.items():
        for annotation in annotations:
            sequence_identifier = annotation[ 'sequence_identifier' ]
            annotation_identifier = annotation[ 'annotation_identifier' ]

            species_names___all_sequence_identifiers[ species_name ].add( sequence_identifier )

            if sequence_identifier not in proteins___annotation_profiles:
                proteins___annotation_profiles[ sequence_identifier ] = {
                    'species_name': species_name,
                    'annotations': []
                }

            proteins___annotation_profiles[ sequence_identifier ][ 'annotations' ].append( annotation_identifier )

    total_annotated_proteins = len( proteins___annotation_profiles )
    logger.info( f"Found {total_annotated_proteins} annotated proteins across all species" )

    # Step 2: Classify proteins into subtypes
    logger.info( "Step 2: Classifying proteins by annotation count..." )

    # single_proteins: { annotation_accession: [ { 'sequence_identifier': str, 'species_name': str } ] }
    single_accessions___proteins = defaultdict( list )

    # combo_proteins: { tuple_of_sorted_accessions: [ { 'sequence_identifier': str, 'species_name': str } ] }
    combo_architectures___proteins = defaultdict( list )

    # zero_proteins: [ { 'sequence_identifier': str, 'species_name': str, 'unannotated_identifier': str } ]
    zero_proteins = []

    single_count = 0
    combo_count = 0

    for sequence_identifier, profile in proteins___annotation_profiles.items():
        species_name = profile[ 'species_name' ]
        annotations = profile[ 'annotations' ]

        annotation_count = len( annotations )

        if annotation_count == 1:
            # Single annotation
            accession = annotations[ 0 ]

            # Skip unannotated identifiers (they are zero-subtype)
            if accession.startswith( f"unannotated_{ANNOTATION_DATABASE}" ):
                zero_proteins.append( {
                    'sequence_identifier': sequence_identifier,
                    'species_name': species_name,
                    'unannotated_identifier': accession
                } )
                continue

            single_accessions___proteins[ accession ].append( {
                'sequence_identifier': sequence_identifier,
                'species_name': species_name
            } )
            single_count += 1

        elif annotation_count > 1:
            # Combo annotation (identical multi-annotation architecture)
            # Sort accessions to create canonical architecture key
            sorted_accessions = tuple( sorted( annotations ) )
            combo_architectures___proteins[ sorted_accessions ].append( {
                'sequence_identifier': sequence_identifier,
                'species_name': species_name
            } )
            combo_count += 1

    logger.info( f"Single-annotation proteins: {single_count}" )
    logger.info( f"Combo-annotation proteins: {combo_count}" )
    logger.info( f"Zero-annotation proteins (unannotated): {len( zero_proteins )}" )

    # Step 3: Assign annogroup IDs and build the map
    logger.info( "Step 3: Assigning annogroup IDs..." )

    annogroup_map_entries = []
    annogroup_counter = 1

    # Subtypes data for per-subtype output files
    subtypes___annogroup_data = {}

    # --- Process SINGLE subtype ---
    if 'single' in ANNOGROUP_SUBTYPES:
        logger.info( f"Processing 'single' subtype: {len( single_accessions___proteins )} unique accessions" )
        single_annogroups = []

        for accession in sorted( single_accessions___proteins.keys() ):
            proteins = single_accessions___proteins[ accession ]
            annogroup_id = f"annogroup_{ANNOTATION_DATABASE}_{annogroup_counter}"
            annogroup_counter += 1

            species_names = sorted( set( protein[ 'species_name' ] for protein in proteins ) )
            sequence_identifiers = sorted( protein[ 'sequence_identifier' ] for protein in proteins )

            map_entry = {
                'annogroup_id': annogroup_id,
                'annogroup_subtype': 'single',
                'annotation_database': ANNOTATION_DATABASE,
                'annotation_accessions': accession,
                'species_count': len( species_names ),
                'sequence_count': len( sequence_identifiers ),
                'species_list': ','.join( species_names ),
                'sequence_ids': ','.join( sequence_identifiers )
            }

            annogroup_map_entries.append( map_entry )
            single_annogroups.append( map_entry )

        subtypes___annogroup_data[ 'single' ] = single_annogroups
        logger.info( f"Created {len( single_annogroups )} single annogroups" )

    # --- Process COMBO subtype ---
    if 'combo' in ANNOGROUP_SUBTYPES:
        logger.info( f"Processing 'combo' subtype: {len( combo_architectures___proteins )} unique architectures" )
        combo_annogroups = []

        for architecture in sorted( combo_architectures___proteins.keys() ):
            proteins = combo_architectures___proteins[ architecture ]
            annogroup_id = f"annogroup_{ANNOTATION_DATABASE}_{annogroup_counter}"
            annogroup_counter += 1

            accessions_string = ','.join( architecture )
            species_names = sorted( set( protein[ 'species_name' ] for protein in proteins ) )
            sequence_identifiers = sorted( protein[ 'sequence_identifier' ] for protein in proteins )

            map_entry = {
                'annogroup_id': annogroup_id,
                'annogroup_subtype': 'combo',
                'annotation_database': ANNOTATION_DATABASE,
                'annotation_accessions': accessions_string,
                'species_count': len( species_names ),
                'sequence_count': len( sequence_identifiers ),
                'species_list': ','.join( species_names ),
                'sequence_ids': ','.join( sequence_identifiers )
            }

            annogroup_map_entries.append( map_entry )
            combo_annogroups.append( map_entry )

        subtypes___annogroup_data[ 'combo' ] = combo_annogroups
        logger.info( f"Created {len( combo_annogroups )} combo annogroups" )

    # --- Process ZERO subtype ---
    if 'zero' in ANNOGROUP_SUBTYPES:
        logger.info( f"Processing 'zero' subtype: {len( zero_proteins )} unannotated proteins" )
        zero_annogroups = []

        for zero_protein in sorted( zero_proteins, key = lambda x: x[ 'unannotated_identifier' ] ):
            annogroup_id = f"annogroup_{ANNOTATION_DATABASE}_{annogroup_counter}"
            annogroup_counter += 1

            map_entry = {
                'annogroup_id': annogroup_id,
                'annogroup_subtype': 'zero',
                'annotation_database': ANNOTATION_DATABASE,
                'annotation_accessions': zero_protein[ 'unannotated_identifier' ],
                'species_count': 1,
                'sequence_count': 1,
                'species_list': zero_protein[ 'species_name' ],
                'sequence_ids': zero_protein[ 'sequence_identifier' ]
            }

            annogroup_map_entries.append( map_entry )
            zero_annogroups.append( map_entry )

        subtypes___annogroup_data[ 'zero' ] = zero_annogroups
        logger.info( f"Created {len( zero_annogroups )} zero annogroups" )

    total_annogroups = len( annogroup_map_entries )
    logger.info( f"Total annogroups created: {total_annogroups}" )

    if total_annogroups == 0:
        logger.error( f"CRITICAL ERROR: No annogroups created!" )
        logger.error( f"Check annotation files in: {input_annotations_directory}" )
        sys.exit( 1 )

    return annogroup_map_entries, subtypes___annogroup_data


# ============================================================================
# PHASE D: WRITE ANNOGROUP OUTPUTS
# ============================================================================

def write_annogroup_map( annogroup_map_entries ):
    """Write the annogroup map (lookup table linking IDs to full details)."""
    logger.info( f"Writing annogroup map to: {output_annogroup_map_file}" )

    with open( output_annogroup_map_file, 'w' ) as output_file:
        output = 'Annogroup_ID (identifier format annogroup_{db}_N)\t'
        output += 'Annogroup_Subtype (single or combo or zero)\t'
        output += 'Annotation_Database (name of annotation database)\t'
        output += 'Annotation_Accessions (comma delimited annotation accessions from the database or unannotated identifier)\t'
        output += 'Species_Count (number of unique species with at least one member sequence)\t'
        output += 'Sequence_Count (total number of member sequences)\t'
        output += 'Species_List (comma delimited list of species names as Genus_species)\t'
        output += 'Sequence_IDs (comma delimited list of sequence identifiers)\n'
        output_file.write( output )

        for entry in annogroup_map_entries:
            output = f"{entry[ 'annogroup_id' ]}\t"
            output += f"{entry[ 'annogroup_subtype' ]}\t"
            output += f"{entry[ 'annotation_database' ]}\t"
            output += f"{entry[ 'annotation_accessions' ]}\t"
            output += f"{entry[ 'species_count' ]}\t"
            output += f"{entry[ 'sequence_count' ]}\t"
            output += f"{entry[ 'species_list' ]}\t"
            output += f"{entry[ 'sequence_ids' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( annogroup_map_entries )} entries to {output_annogroup_map_file.name}" )


def write_annogroups_standardized( annogroup_map_entries ):
    """
    Write standardized annogroups file for consumption by Scripts 002-005.

    This file parallels the orthogroups-gigantic_identifiers.tsv from the
    orthogroups_X_ocl pipeline, but with species already resolved to
    Genus_species format (no GIGANTIC ID parsing needed downstream).
    """
    logger.info( f"Writing standardized annogroups to: {output_annogroups_file}" )

    with open( output_annogroups_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Annogroup_ID (annogroup identifier format annogroup_{db}_N)\t'
        output += 'Annogroup_Subtype (single or combo or zero)\t'
        output += 'Species_Count (number of unique species in annogroup)\t'
        output += 'Species_List (comma delimited list of species names as Genus_species)\n'
        output_file.write( output )

        for entry in annogroup_map_entries:
            output = f"{entry[ 'annogroup_id' ]}\t"
            output += f"{entry[ 'annogroup_subtype' ]}\t"
            output += f"{entry[ 'species_count' ]}\t"
            output += f"{entry[ 'species_list' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( annogroup_map_entries )} annogroups to {output_annogroups_file.name}" )


def write_per_subtype_annogroup_files( subtypes___annogroup_data ):
    """Write per-subtype annogroup files with annogroup ID and member sequences."""
    logger.info( "Writing per-subtype annogroup files..." )

    for subtype, annogroup_entries in subtypes___annogroup_data.items():
        output_subtype_file = output_directory / f'1_ai-{TARGET_STRUCTURE}_annogroups-{subtype}.tsv'
        logger.info( f"Writing {subtype} annogroups to: {output_subtype_file}" )

        with open( output_subtype_file, 'w' ) as output_file:
            output = 'Annogroup_ID (annogroup identifier)\t'
            output += 'Species_Count (number of unique species in annogroup)\t'
            output += 'Sequence_Count (total count of sequences in annogroup)\t'
            output += 'Species_List (comma delimited list of species names as Genus_species)\t'
            output += 'Sequence_IDs (comma delimited list of sequence identifiers)\n'
            output_file.write( output )

            for entry in annogroup_entries:
                output = f"{entry[ 'annogroup_id' ]}\t"
                output += f"{entry[ 'species_count' ]}\t"
                output += f"{entry[ 'sequence_count' ]}\t"
                output += f"{entry[ 'species_list' ]}\t"
                output += f"{entry[ 'sequence_ids' ]}\n"
                output_file.write( output )

        logger.info( f"Wrote {len( annogroup_entries )} {subtype} annogroups" )


def write_subtypes_manifest( subtypes___annogroup_data ):
    """Write manifest listing which subtypes were generated."""
    logger.info( f"Writing subtypes manifest to: {output_subtypes_manifest_file}" )

    with open( output_subtypes_manifest_file, 'w' ) as output_file:
        output = 'Annogroup_Subtype (subtype name)\t'
        output += 'Annogroup_Count (number of annogroups of this subtype)\t'
        output += 'Output_File (filename of per-subtype annogroup file)\n'
        output_file.write( output )

        for subtype in sorted( subtypes___annogroup_data.keys() ):
            annogroup_count = len( subtypes___annogroup_data[ subtype ] )
            output_filename = f'1_ai-{TARGET_STRUCTURE}_annogroups-{subtype}.tsv'

            output = f"{subtype}\t{annogroup_count}\t{output_filename}\n"
            output_file.write( output )

    logger.info( f"Wrote manifest with {len( subtypes___annogroup_data )} subtypes" )


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    start_time = time.time()

    logger.info( "=" * 80 )
    logger.info( "SCRIPT 001: CREATE ANNOTATION GROUPS (ANNOGROUPS)" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Species set: {SPECIES_SET_NAME}" )
    logger.info( f"Annotation database: {ANNOTATION_DATABASE}" )
    logger.info( f"Annogroup subtypes: {ANNOGROUP_SUBTYPES}" )
    logger.info( f"Config file: {config_path}" )
    logger.info( "" )

    # ========================================================================
    # PHASE A: Load phylogenetic tree data (Rule 6 atomic identifiers)
    # ========================================================================
    logger.info( "PHASE A: Loading phylogenetic tree data (Rule 6 atomic identifiers)..." )

    # Step A1: Load phylogenetic blocks
    logger.info( "" )
    logger.info( "STEP A1: Loading phylogenetic blocks..." )
    child_clade_id_names___block_data = load_phylogenetic_blocks()
    write_phylogenetic_blocks( child_clade_id_names___block_data )

    # Step A2: Load parent-child relationships
    logger.info( "" )
    logger.info( "STEP A2: Loading parent-child relationships..." )
    relationships = load_parent_child_relationships()
    write_parent_child_relationships( relationships )

    # Step A3: Load phylogenetic paths
    logger.info( "" )
    logger.info( "STEP A3: Loading phylogenetic paths..." )
    leaf_clade_ids___paths = load_phylogenetic_paths()
    if leaf_clade_ids___paths:
        write_phylogenetic_paths( leaf_clade_ids___paths )
    else:
        logger.info( "No paths file found - will be generated from blocks if needed downstream" )

    # Step A4: Create clade mappings
    logger.info( "" )
    logger.info( "STEP A4: Creating clade name to clade_id_name mappings..." )
    write_clade_mappings( child_clade_id_names___block_data )

    # ========================================================================
    # PHASE B: Load annotation files
    # ========================================================================
    logger.info( "" )
    logger.info( "PHASE B: Loading annotation files..." )
    species_names___annotations = load_annotation_files()

    # ========================================================================
    # PHASE C: Create annogroups
    # ========================================================================
    logger.info( "" )
    logger.info( "PHASE C: Creating annogroups..." )
    annogroup_map_entries, subtypes___annogroup_data = create_annogroups( species_names___annotations )

    # ========================================================================
    # PHASE D: Write annogroup outputs
    # ========================================================================
    logger.info( "" )
    logger.info( "PHASE D: Writing annogroup outputs..." )
    write_annogroup_map( annogroup_map_entries )
    write_annogroups_standardized( annogroup_map_entries )
    write_per_subtype_annogroup_files( subtypes___annogroup_data )
    write_subtypes_manifest( subtypes___annogroup_data )

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
    for subtype in sorted( subtypes___annogroup_data.keys() ):
        logger.info( f"  1_ai-{TARGET_STRUCTURE}_annogroups-{subtype}.tsv" )
    logger.info( f"  {output_subtypes_manifest_file.name}" )
    logger.info( "" )
    logger.info( f"Total annogroups: {len( annogroup_map_entries )}" )
    for subtype, data in sorted( subtypes___annogroup_data.items() ):
        logger.info( f"  {subtype}: {len( data )}" )
    logger.info( "=" * 80 )

    # Emit run summary fragment
    duration_seconds = time.time() - start_time
    subtype_counts = { subtype: len( data ) for subtype, data in subtypes___annogroup_data.items() }
    emit_run_summary_fragment(
        script_number = 1,
        structure_id = args.structure_id,
        stats = {
            'duration_seconds': round( duration_seconds, 2 ),
            'annogroups_total': len( annogroup_map_entries ),
            'annogroups_by_subtype': subtype_counts,
            'species_with_annotations': len( species_names___annotations ),
            'annotation_database': ANNOTATION_DATABASE,
            'phylogenetic_blocks_loaded': len( child_clade_id_names___block_data ),
            'phylogenetic_paths_loaded': len( leaf_clade_ids___paths ) if leaf_clade_ids___paths else 0
        }
    )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
