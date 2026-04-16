# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Prepare inputs from upstream subprojects for OCL analysis
# Human: Eric Edsinger

"""
OCL Pipeline Script 001: Prepare Inputs from Upstream Subprojects

Loads and standardizes input data for Origin-Conservation-Loss analysis:
- Phylogenetic blocks from trees_species (filtered to target structure)
- Parent-child relationships from trees_species (structure-specific file)
- Phylogenetic paths from trees_species (filtered to target structure)
- Clade ID-to-name mappings (derived from phylogenetic blocks)
- ID mapping (orthogroup short IDs to GIGANTIC identifiers)
- Orthogroups (converted to GIGANTIC identifiers)

All orthogroup data is converted to GIGANTIC identifiers at the start.
Downstream scripts work exclusively with GIGANTIC identifiers.

Inputs come from three upstream subprojects via output_to_input:
- trees_species (phylogenetic features)
- orthogroups (clustering results)
- genomesDB (proteome FASTAs - used by Scripts 002/004 directly)

Usage:
    python 001_ai-python-prepare_inputs.py --structure_id 001 --config ../../START_HERE-user_config.yaml
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

import yaml


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'OCL Pipeline Script 001: Prepare inputs from upstream subprojects',
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

# Species set and orthogroup tool from config
SPECIES_SET_NAME = config[ 'species_set_name' ]
ORTHOGROUP_TOOL = config[ 'orthogroup_tool' ]

# Resolve input paths relative to config file directory
config_directory = config_path.parent

input_trees_species_directory = config_directory / config[ 'inputs' ][ 'trees_species_dir' ]
input_orthogroups_directory = config_directory / config[ 'inputs' ][ 'orthogroups_dir' ]

# Input files from trees_species
input_phylogenetic_blocks_file = input_trees_species_directory / 'Species_Phylogenetic_Blocks'
input_parent_child_directory = input_trees_species_directory / 'Species_Parent_Child_Relationships'
input_phylogenetic_paths_directory = input_trees_species_directory / 'Species_Phylogenetic_Paths'

# Input files from orthogroups
# GIGANTIC_1 convention: orthogroup files already contain full GIGANTIC identifiers.
# The separate ID_mapping-short_to_gigantic.tsv layer from GIGANTIC_0 is gone.
input_orthogroups_file = input_orthogroups_directory / 'orthogroups_gigantic_ids.tsv'

# Output directory
# Prefer --output_dir (passed by NextFlow main.nf for consistency with scripts 003-005);
# fall back to config.output.base_dir relative to config file when invoked standalone.
if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]
output_directory = output_base_directory / TARGET_STRUCTURE / '1-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_phylogenetic_blocks_file = output_directory / f'1_ai-phylogenetic_blocks-{TARGET_STRUCTURE}.tsv'
output_parent_child_file = output_directory / f'1_ai-parent_child_table-{TARGET_STRUCTURE}.tsv'
output_phylogenetic_paths_file = output_directory / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
output_clade_mappings_file = output_directory / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'
output_orthogroups_file = output_directory / '1_ai-orthogroups-gigantic_identifiers.tsv'

# Log directory
log_directory = output_base_directory / TARGET_STRUCTURE / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / f'1_ai-log-prepare_inputs-{TARGET_STRUCTURE}.log'


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
# SECTION 1: LOAD PHYLOGENETIC BLOCKS
# ============================================================================

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
        # structure_001	C000_Pre_Basal::C071_Basal	C000_Pre_Basal	C071_Basal
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


# ============================================================================
# SECTION 2: LOAD PARENT-CHILD RELATIONSHIPS
# ============================================================================

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


# ============================================================================
# SECTION 3: LOAD PHYLOGENETIC PATHS
# ============================================================================

def load_phylogenetic_paths():
    """
    Load phylogenetic paths (root-to-leaf) for the target structure from trees_species.

    Returns:
        dict: { leaf_clade_id: [ clade_id_1, clade_id_2, ..., leaf_clade_id ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_directory}" )

    # Find the combined phylogenetic paths file (contains all structures).
    # Pattern matches `4_ai-phylogenetic_paths-all_structures.tsv`.
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


# ============================================================================
# SECTION 4: CREATE CLADE MAPPINGS
# ============================================================================

def write_clade_mappings( child_clade_id_names___block_data ):
    """
    Write clade name -> clade_id_name mappings to standardized output file.

    Purpose of this file: a translation table for downstream OCL scripts that
    receive bare clade/species names (extracted from GIGANTIC protein
    identifiers) and need to resolve them to the atomic Rule 6 clade_id_name
    form. Both columns are emitted explicitly: Clade_Name is the lookup key
    (bare name as it appears in orthogroup input data), Clade_ID_Name is the
    atomic value.
    """
    logger.info( f"Writing clade mappings to: {output_clade_mappings_file}" )

    with open( output_clade_mappings_file, 'w' ) as output_file:
        output = 'Clade_Name (bare clade name lookup key as it appears in orthogroup input data)\t'
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
# SECTION 6: LOAD ORTHOGROUPS AND CONVERT TO GIGANTIC IDs
# ============================================================================

def load_orthogroups():
    """
    Load orthogroups directly from GIGANTIC_1 tab-separated orthogroup file.

    File format (GIGANTIC_1): No header. One row per orthogroup. First tab-separated
    column is the orthogroup identifier (e.g., OG000000). Remaining columns are
    full GIGANTIC protein identifiers already in canonical form — no short-ID to
    GIGANTIC-ID mapping layer is needed (that was a GIGANTIC_0 OrthoFinder vestige).

    Returns:
        dict: { orthogroup_id: { 'gigantic_ids': [ ... ] } }
    """
    logger.info( f"Loading orthogroups from: {input_orthogroups_file}" )

    if not input_orthogroups_file.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found!" )
        logger.error( f"Expected location: {input_orthogroups_file}" )
        logger.error( f"Run orthogroups pipeline first to generate orthogroup assignments." )
        sys.exit( 1 )

    orthogroup_ids___orthogroup_data = {}
    total_sequences = 0

    with open( input_orthogroups_file, 'r' ) as input_file:
        # OG000000<TAB>g_g23117-t_g23117.t3-p_g23117.t3-n_HolozoaUNOFFICIAL_...<TAB>g_g24455-...<TAB>...
        # OG000001<TAB>g_...<TAB>g_...<TAB>...

        for line in input_file:
            line = line.rstrip( '\n' )
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 2:
                continue

            orthogroup_id = parts[ 0 ].strip()

            # Skip header rows if any producing tool adds one
            if orthogroup_id.lower().startswith( 'orthogroup' ):
                continue

            gigantic_ids = [ part.strip() for part in parts[ 1: ] if part.strip() ]

            total_sequences += len( gigantic_ids )

            orthogroup_ids___orthogroup_data[ orthogroup_id ] = {
                'gigantic_ids': gigantic_ids
            }

    logger.info( f"Loaded {len( orthogroup_ids___orthogroup_data )} orthogroups" )
    logger.info( f"Total sequences: {total_sequences}" )

    if len( orthogroup_ids___orthogroup_data ) == 0:
        logger.error( f"CRITICAL ERROR: No orthogroups loaded!" )
        sys.exit( 1 )

    return orthogroup_ids___orthogroup_data


def write_orthogroups( orthogroup_ids___orthogroup_data ):
    """Write orthogroups with GIGANTIC identifiers to standardized output file."""
    logger.info( f"Writing orthogroups to: {output_orthogroups_file}" )

    with open( output_orthogroups_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Orthogroup_ID (orthogroup identifier from clustering tool)\t'
        output += 'Sequence_Count (total count of sequences in orthogroup)\t'
        output += 'GIGANTIC_IDs (comma delimited list of GIGANTIC identifiers)\n'
        output_file.write( output )

        for orthogroup_id in sorted( orthogroup_ids___orthogroup_data.keys() ):
            orthogroup_data = orthogroup_ids___orthogroup_data[ orthogroup_id ]
            gigantic_ids = orthogroup_data[ 'gigantic_ids' ]

            sequence_count = len( gigantic_ids )
            gigantic_ids_string = ','.join( gigantic_ids )

            output = f"{orthogroup_id}\t{sequence_count}\t{gigantic_ids_string}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( orthogroup_ids___orthogroup_data )} orthogroups to {output_orthogroups_file.name}" )


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 001: PREPARE INPUTS FROM UPSTREAM SUBPROJECTS" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Species set: {SPECIES_SET_NAME}" )
    logger.info( f"Orthogroup tool: {ORTHOGROUP_TOOL}" )
    logger.info( f"Config file: {config_path}" )
    logger.info( "" )

    # Step 1: Load phylogenetic blocks
    logger.info( "STEP 1: Loading phylogenetic blocks..." )
    clade_ids___block_data = load_phylogenetic_blocks()
    write_phylogenetic_blocks( clade_ids___block_data )

    # Step 2: Load parent-child relationships
    logger.info( "" )
    logger.info( "STEP 2: Loading parent-child relationships..." )
    relationships = load_parent_child_relationships()
    write_parent_child_relationships( relationships )

    # Step 3: Load phylogenetic paths
    logger.info( "" )
    logger.info( "STEP 3: Loading phylogenetic paths..." )
    leaf_clade_ids___paths = load_phylogenetic_paths()
    if leaf_clade_ids___paths:
        write_phylogenetic_paths( leaf_clade_ids___paths )
    else:
        logger.info( "No paths file found - will be generated from blocks if needed downstream" )

    # Step 4: Create clade mappings
    logger.info( "" )
    logger.info( "STEP 4: Creating clade ID to name mappings..." )
    write_clade_mappings( clade_ids___block_data )

    # Step 5: Load orthogroups (GIGANTIC IDs already inline — no short-ID mapping needed)
    logger.info( "" )
    logger.info( "STEP 5: Loading orthogroups (GIGANTIC identifiers)..." )
    orthogroup_ids___orthogroup_data = load_orthogroups()
    write_orthogroups( orthogroup_ids___orthogroup_data )

    # Complete
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
    logger.info( f"  {output_orthogroups_file.name}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
