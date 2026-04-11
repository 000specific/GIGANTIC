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
input_id_mapping_file = input_orthogroups_directory / 'ID_mapping-short_to_gigantic.tsv'
input_orthogroups_file = input_orthogroups_directory / 'orthogroups_gigantic_ids.tsv'

# Output directory
output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]
output_directory = output_base_directory / TARGET_STRUCTURE / '1-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_phylogenetic_blocks_file = output_directory / f'1_ai-phylogenetic_blocks-{TARGET_STRUCTURE}.tsv'
output_parent_child_file = output_directory / f'1_ai-parent_child_table-{TARGET_STRUCTURE}.tsv'
output_phylogenetic_paths_file = output_directory / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
output_clade_mappings_file = output_directory / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'
output_orthogroups_file = output_directory / '1_ai-orthogroups-gigantic_identifiers.tsv'
output_id_mapping_file = output_directory / '1_ai-id_mapping-short_to_gigantic.tsv'

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
    and filters to the target structure.

    Returns:
        dict: { clade_id: { 'clade_name': str, 'parent_id': str, 'structure_id': str } }
    """
    logger.info( f"Loading phylogenetic blocks from: {input_phylogenetic_blocks_file}" )

    # Find the combined phylogenetic blocks file
    phylogenetic_blocks_files = list( input_phylogenetic_blocks_file.glob( '*phylogenetic_blocks*.tsv' ) )

    if not phylogenetic_blocks_files:
        logger.error( f"CRITICAL ERROR: No phylogenetic blocks files found!" )
        logger.error( f"Expected location: {input_phylogenetic_blocks_file}" )
        logger.error( f"Run trees_species pipeline first to generate phylogenetic blocks." )
        sys.exit( 1 )

    # Use the combined file (contains all structures)
    phylogenetic_blocks_path = phylogenetic_blocks_files[ 0 ]
    logger.info( f"Using file: {phylogenetic_blocks_path.name}" )

    clade_ids___block_data = {}

    with open( phylogenetic_blocks_path, 'r' ) as input_file:
        # Structure_ID (structure identifier)	Clade_ID (clade identifier)	Clade_Name (clade name)	...
        # structure_001	C068	Basal	C068_Basal	C000	Pre_Basal	C000_Pre_Basal	...
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        # Find column indices dynamically from header
        structure_id_column = None
        clade_id_column = None
        clade_name_column = None
        parent_clade_id_column = None

        for index, column_header in enumerate( header_parts ):
            column_id = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            if column_id == 'Structure_ID':
                structure_id_column = index
            elif column_id == 'Clade_ID':
                clade_id_column = index
            elif column_id == 'Clade_Name':
                clade_name_column = index
            elif column_id == 'Parent_Clade_ID':
                parent_clade_id_column = index

        if None in [ structure_id_column, clade_id_column, clade_name_column, parent_clade_id_column ]:
            logger.error( f"CRITICAL ERROR: Could not find required columns in phylogenetic blocks file!" )
            logger.error( f"Found columns: {header_parts}" )
            logger.error( f"Need: Structure_ID, Clade_ID, Clade_Name, Parent_Clade_ID" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]
            clade_id = parts[ clade_id_column ]
            clade_name = parts[ clade_name_column ]
            parent_clade_id = parts[ parent_clade_id_column ]

            # Only load blocks for target structure
            if structure_id == TARGET_STRUCTURE:
                clade_ids___block_data[ clade_id ] = {
                    'clade_name': clade_name,
                    'parent_id': parent_clade_id if parent_clade_id != 'NA' and parent_clade_id != 'C000' else parent_clade_id,
                    'structure_id': structure_id
                }

    logger.info( f"Loaded {len( clade_ids___block_data )} phylogenetic blocks for {TARGET_STRUCTURE}" )

    if len( clade_ids___block_data ) == 0:
        logger.error( f"CRITICAL ERROR: No blocks loaded for {TARGET_STRUCTURE}!" )
        logger.error( f"Check that structure exists in: {phylogenetic_blocks_path}" )
        sys.exit( 1 )

    return clade_ids___block_data


def write_phylogenetic_blocks( clade_ids___block_data ):
    """Write phylogenetic blocks to standardized output file."""
    logger.info( f"Writing phylogenetic blocks to: {output_phylogenetic_blocks_file}" )

    with open( output_phylogenetic_blocks_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Clade_ID (clade identifier from trees_species)\t'
        output += 'Clade_Name (clade name from phylogenetic tree)\t'
        output += 'Parent_ID (parent clade identifier or NA for root)\t'
        output += 'Structure_ID (structure identifier for this phylogenetic tree)\n'
        output_file.write( output )

        for clade_id in sorted( clade_ids___block_data.keys() ):
            block_data = clade_ids___block_data[ clade_id ]
            clade_name = block_data[ 'clade_name' ]
            parent_id = block_data[ 'parent_id' ] if block_data[ 'parent_id' ] else 'NA'
            structure_id = block_data[ 'structure_id' ]

            output = f"{clade_id}\t{clade_name}\t{parent_id}\t{structure_id}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( clade_ids___block_data )} blocks to {output_phylogenetic_blocks_file.name}" )


# ============================================================================
# SECTION 2: LOAD PARENT-CHILD RELATIONSHIPS
# ============================================================================

def load_parent_child_relationships():
    """
    Load parent-child relationships for the target structure from trees_species.

    Looks for structure-specific parent-child file in the Parent_Child_Relationships directory.

    Returns:
        list: [ { 'parent_id': str, 'parent_name': str, 'child_id': str, 'child_name': str } ]
    """
    logger.info( f"Loading parent-child relationships from: {input_parent_child_directory}" )

    # Find structure-specific parent-child file
    parent_child_files = list( input_parent_child_directory.glob( f'*{TARGET_STRUCTURE}*parent_child*.tsv' ) )

    if not parent_child_files:
        # Try alternate naming patterns
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
        # Parent_ID (parent clade identifier)	Parent_Name (parent clade name)	Child_ID (child clade identifier)	Child_Name (child clade name)
        # C068	Basal	C069	Holomycota
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            if len( parts ) < 4:
                logger.warning( f"Expected 4+ fields, got {len( parts )}, skipping: {line[:80]}" )
                continue

            parent_id = parts[ 0 ]
            parent_name = parts[ 1 ]
            child_id = parts[ 2 ]
            child_name = parts[ 3 ]

            relationships.append( {
                'parent_id': parent_id,
                'parent_name': parent_name,
                'child_id': child_id,
                'child_name': child_name
            } )

    logger.info( f"Loaded {len( relationships )} parent-child relationships" )

    if len( relationships ) == 0:
        logger.error( f"CRITICAL ERROR: No parent-child relationships loaded!" )
        sys.exit( 1 )

    return relationships


def write_parent_child_relationships( relationships ):
    """Write parent-child relationships to standardized output file."""
    logger.info( f"Writing parent-child relationships to: {output_parent_child_file}" )

    with open( output_parent_child_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Parent_ID (parent clade identifier)\t'
        output += 'Parent_Name (parent clade name)\t'
        output += 'Child_ID (child clade identifier)\t'
        output += 'Child_Name (child clade name)\n'
        output_file.write( output )

        for relationship in relationships:
            output = f"{relationship[ 'parent_id' ]}\t{relationship[ 'parent_name' ]}\t"
            output += f"{relationship[ 'child_id' ]}\t{relationship[ 'child_name' ]}\n"
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

    # Find paths file (combined or per-structure)
    paths_files = list( input_phylogenetic_paths_directory.glob( '*paths*.tsv' ) )

    if not paths_files:
        logger.warning( f"No phylogenetic paths files found in: {input_phylogenetic_paths_directory}" )
        logger.info( "Paths will need to be generated from phylogenetic blocks if needed downstream" )
        return {}

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

def write_clade_mappings( clade_ids___block_data ):
    """Write clade ID to name mappings to standardized output file."""
    logger.info( f"Writing clade mappings to: {output_clade_mappings_file}" )

    with open( output_clade_mappings_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Clade_ID (clade identifier from trees_species)\t'
        output += 'Clade_Name (clade name from phylogenetic tree)\n'
        output_file.write( output )

        for clade_id in sorted( clade_ids___block_data.keys() ):
            clade_name = clade_ids___block_data[ clade_id ][ 'clade_name' ]
            output = f"{clade_id}\t{clade_name}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( clade_ids___block_data )} clade mappings to {output_clade_mappings_file.name}" )


# ============================================================================
# SECTION 5: LOAD ID MAPPING (SHORT TO GIGANTIC)
# ============================================================================

def load_id_mapping():
    """
    Load ID mapping from orthogroup short IDs to GIGANTIC identifiers.

    Returns:
        dict: { short_id: gigantic_id }
    """
    logger.info( f"Loading ID mapping from: {input_id_mapping_file}" )

    if not input_id_mapping_file.exists():
        logger.error( f"CRITICAL ERROR: ID mapping file not found!" )
        logger.error( f"Expected location: {input_id_mapping_file}" )
        logger.error( f"Run orthogroups pipeline first to generate ID mappings." )
        sys.exit( 1 )

    short_ids___gigantic_ids = {}

    with open( input_id_mapping_file, 'r' ) as input_file:
        # g_000-t_000-p_g1.t1-n_Holozoa_..._Abeoforma_whisleri	Abeoforma_whisleri-1
        # g_000-t_000-p_g1.t2-n_Holozoa_..._Abeoforma_whisleri	Abeoforma_whisleri-2

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            # Skip header lines
            if line.startswith( 'GIGANTIC_ID' ) or line.startswith( 'Short_ID' ) or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) != 2:
                continue

            gigantic_id = parts[ 0 ]
            short_id = parts[ 1 ]

            short_ids___gigantic_ids[ short_id ] = gigantic_id

    logger.info( f"Loaded {len( short_ids___gigantic_ids )} ID mappings" )

    if len( short_ids___gigantic_ids ) == 0:
        logger.error( f"CRITICAL ERROR: No ID mappings loaded!" )
        logger.error( f"Check file format: expected two tab-separated columns (gigantic_id, short_id)" )
        sys.exit( 1 )

    return short_ids___gigantic_ids


def write_id_mapping( short_ids___gigantic_ids ):
    """Write ID mapping to standardized output file."""
    logger.info( f"Writing ID mapping to: {output_id_mapping_file}" )

    with open( output_id_mapping_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Short_ID (short identifier from orthogroup tool output)\t'
        output += 'GIGANTIC_ID (GIGANTIC identifier with gene transcript protein and phyloname)\n'
        output_file.write( output )

        for short_id in sorted( short_ids___gigantic_ids.keys() ):
            gigantic_id = short_ids___gigantic_ids[ short_id ]
            output = f"{short_id}\t{gigantic_id}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( short_ids___gigantic_ids )} ID mappings to {output_id_mapping_file.name}" )


# ============================================================================
# SECTION 6: LOAD ORTHOGROUPS AND CONVERT TO GIGANTIC IDs
# ============================================================================

def load_orthogroups( short_ids___gigantic_ids ):
    """
    Load orthogroups and convert all sequence IDs to GIGANTIC identifiers.

    Args:
        short_ids___gigantic_ids: Dictionary mapping short IDs to GIGANTIC IDs

    Returns:
        dict: { orthogroup_id: { 'gigantic_ids': [ ... ], 'unmapped_ids': [ ... ] } }
    """
    logger.info( f"Loading orthogroups from: {input_orthogroups_file}" )

    if not input_orthogroups_file.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found!" )
        logger.error( f"Expected location: {input_orthogroups_file}" )
        logger.error( f"Run orthogroups pipeline first to generate orthogroup assignments." )
        sys.exit( 1 )

    orthogroup_ids___orthogroup_data = {}
    total_sequences = 0
    total_mapped = 0
    total_unmapped = 0

    with open( input_orthogroups_file, 'r' ) as input_file:
        # OG000000: Acropora_muricata-10028 Acropora_muricata-10056 ...
        # OG000001: Mnemiopsis_leidyi-1234 Mnemiopsis_leidyi-5678 ...

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            # Skip header lines
            if line.startswith( '#' ) or line.startswith( 'Orthogroup' ):
                continue

            if ':' not in line:
                continue

            parts_line = line.split( ':', 1 )
            orthogroup_id = parts_line[ 0 ].strip()
            sequence_ids_string = parts_line[ 1 ].strip()

            short_ids = sequence_ids_string.split()

            gigantic_ids = []
            unmapped_ids = []

            for short_id in short_ids:
                total_sequences += 1

                if short_id in short_ids___gigantic_ids:
                    gigantic_id = short_ids___gigantic_ids[ short_id ]
                    gigantic_ids.append( gigantic_id )
                    total_mapped += 1
                else:
                    unmapped_ids.append( short_id )
                    total_unmapped += 1

            orthogroup_ids___orthogroup_data[ orthogroup_id ] = {
                'gigantic_ids': gigantic_ids,
                'unmapped_ids': unmapped_ids
            }

    logger.info( f"Loaded {len( orthogroup_ids___orthogroup_data )} orthogroups" )
    logger.info( f"Total sequences: {total_sequences}" )

    if total_sequences > 0:
        logger.info( f"Successfully mapped: {total_mapped} ({100 * total_mapped / total_sequences:.1f}%)" )
        logger.info( f"Unmapped: {total_unmapped} ({100 * total_unmapped / total_sequences:.1f}%)" )

    if total_unmapped > 0:
        logger.warning( f"WARNING: {total_unmapped} sequence IDs could not be mapped to GIGANTIC identifiers" )

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
        output += 'GIGANTIC_IDs (comma delimited list of GIGANTIC identifiers)\t'
        output += 'Unmapped_Short_IDs (comma delimited list of short IDs that could not be mapped)\n'
        output_file.write( output )

        for orthogroup_id in sorted( orthogroup_ids___orthogroup_data.keys() ):
            orthogroup_data = orthogroup_ids___orthogroup_data[ orthogroup_id ]
            gigantic_ids = orthogroup_data[ 'gigantic_ids' ]
            unmapped_ids = orthogroup_data[ 'unmapped_ids' ]

            sequence_count = len( gigantic_ids ) + len( unmapped_ids )
            gigantic_ids_string = ','.join( gigantic_ids )
            unmapped_ids_string = ','.join( unmapped_ids ) if unmapped_ids else ''

            output = f"{orthogroup_id}\t{sequence_count}\t{gigantic_ids_string}\t{unmapped_ids_string}\n"
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

    # Step 5: Load ID mapping
    logger.info( "" )
    logger.info( "STEP 5: Loading ID mapping (short to GIGANTIC)..." )
    short_ids___gigantic_ids = load_id_mapping()
    write_id_mapping( short_ids___gigantic_ids )

    # Step 6: Load orthogroups and convert to GIGANTIC IDs
    logger.info( "" )
    logger.info( "STEP 6: Loading orthogroups and converting to GIGANTIC identifiers..." )
    orthogroup_ids___orthogroup_data = load_orthogroups( short_ids___gigantic_ids )
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
    logger.info( f"  {output_id_mapping_file.name}" )
    logger.info( f"  {output_orthogroups_file.name}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
