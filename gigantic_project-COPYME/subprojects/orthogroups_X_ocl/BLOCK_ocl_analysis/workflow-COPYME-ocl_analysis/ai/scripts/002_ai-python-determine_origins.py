# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Determine phylogenetic origins of orthogroups using MRCA algorithm
# Human: Eric Edsinger

"""
OCL Pipeline Script 002: Determine Orthogroup Origins

Determines the phylogenetic origin (MRCA) of each orthogroup.

Algorithm:
1. For each orthogroup, collect all species present
2. SINGLE-SPECIES ORTHOGROUPS (~86%):
   - Origin = the species itself
   - Shared clades = full phylogenetic path for that species (root to species)
3. MULTI-SPECIES ORTHOGROUPS (~14%):
   - Get phylogenetic path (root to leaf) for each species
   - Find intersection of all paths (shared ancestral clades)
   - Identify MRCA: deepest clade in shared set where divergence occurs
   - MRCA = the divergence point where the orthogroup originated

Inputs (from Script 001 outputs in 1-output/):
- Phylogenetic blocks (tree structure)
- Parent-child relationships
- Phylogenetic paths (root-to-tip for each species)
- Clade ID-to-name mappings
- Orthogroups with GIGANTIC identifiers

Optional (config-driven):
- Proteome FASTA files (for sequence embedding when include_fasta_in_output is true)

Outputs (to 2-output/):
- Per-orthogroup origins with phylogenetic block and path annotations
- Origins summary (orthogroup counts per clade)
- Orthogroups grouped by origin clade

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
        description = 'OCL Pipeline Script 002: Determine orthogroup origins using MRCA algorithm',
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
INCLUDE_FASTA = config.get( 'include_fasta_in_output', False )

# Resolve paths relative to config file directory
config_directory = config_path.parent
output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]

# Input directories (from Script 001 outputs)
input_directory = output_base_directory / TARGET_STRUCTURE / '1-output'

# Input files from Script 001
input_phylogenetic_blocks_file = input_directory / f'1_ai-phylogenetic_blocks-{TARGET_STRUCTURE}.tsv'
input_parent_child_file = input_directory / f'1_ai-parent_child_table-{TARGET_STRUCTURE}.tsv'
input_phylogenetic_paths_file = input_directory / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
input_clade_mappings_file = input_directory / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'
input_orthogroups_file = input_directory / '1_ai-orthogroups-gigantic_identifiers.tsv'
input_id_mapping_file = input_directory / '1_ai-id_mapping-short_to_gigantic.tsv'

# Upstream trees_species data (phylogenetic blocks with full 10-column format)
input_trees_species_directory = config_directory / config[ 'inputs' ][ 'trees_species_dir' ]
input_trees_phylogenetic_blocks_all = input_trees_species_directory / 'Species_Phylogenetic_Blocks'
input_trees_phylogenetic_paths_all = input_trees_species_directory / 'Species_Phylogenetic_Paths'

# Proteomes directory (for optional FASTA embedding)
input_proteomes_directory = config_directory / config[ 'inputs' ][ 'proteomes_dir' ]

# Output directory
output_directory = output_base_directory / TARGET_STRUCTURE / '2-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_origins_file = output_directory / '2_ai-orthogroup_origins.tsv'
output_summary_file = output_directory / '2_ai-origins_summary-orthogroups_per_clade.tsv'
output_by_origin_directory = output_directory / '2_ai-orthogroups_by_origin'
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

            # Build parent-to-children mapping
            if parent_name not in parents___children:
                parents___children[ parent_name ] = []
            parents___children[ parent_name ].append( child_name )

            # Build child-to-parent mapping (skip self-loops)
            if parent_name != child_name:
                children___parents[ child_name ] = parent_name

    logger.info( f"Loaded {len( parents___children )} parent-child relationships" )

    if len( parents___children ) == 0:
        logger.error( f"CRITICAL ERROR: No parent-child relationships loaded!" )
        sys.exit( 1 )

    return parents___children, children___parents


def load_clade_mappings():
    """
    Load clade ID to name mappings from Script 001 output.

    Returns:
        dict: { clade_id: clade_name }
    """
    logger.info( f"Loading clade mappings from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mappings file not found!" )
        logger.error( f"Expected location: {input_clade_mappings_file}" )
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

            clade_id = parts[ 0 ]
            clade_name = parts[ 1 ]

            clade_ids___clade_names[ clade_id ] = clade_name

    logger.info( f"Loaded {len( clade_ids___clade_names )} clade mappings" )
    return clade_ids___clade_names


# ============================================================================
# SECTION 2: LOAD PHYLOGENETIC PATHS
# ============================================================================

def load_phylogenetic_paths():
    """
    Load phylogenetic paths (root to leaf) for each species from Script 001 output.

    Returns:
        dict: { species_clade_id: [ clade_name_1, clade_name_2, ..., species_name ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_file}" )

    if not input_phylogenetic_paths_file.exists():
        logger.error( f"CRITICAL ERROR: Phylogenetic paths file not found!" )
        logger.error( f"Expected location: {input_phylogenetic_paths_file}" )
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

            # Parse path elements and extract clade names
            if '>' in path_string:
                path_elements = path_string.split( '>' )
            else:
                path_elements = path_string.split( ',' )

            path_names = []
            for element in path_elements:
                element = element.strip()
                # Split "C068_Basal" -> extract "Basal"
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
# SECTION 3: LOAD ORTHOGROUPS
# ============================================================================

def load_orthogroups():
    """
    Load orthogroups with GIGANTIC identifiers from Script 001 output.

    Returns:
        dict: { orthogroup_id: { 'gigantic_ids': [ ... ], 'sequence_count': int } }
    """
    logger.info( f"Loading orthogroups from: {input_orthogroups_file}" )

    if not input_orthogroups_file.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found!" )
        logger.error( f"Expected location: {input_orthogroups_file}" )
        sys.exit( 1 )

    orthogroup_ids___orthogroup_data = {}

    with open( input_orthogroups_file, 'r' ) as input_file:
        # Orthogroup_ID (orthogroup identifier from clustering tool)	Sequence_Count (...)	GIGANTIC_IDs (comma delimited ...)	Unmapped_Short_IDs (...)
        # OG000000	1234	g_000-t_000-...,g_001-t_001-...
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            if len( parts ) < 3:
                continue

            orthogroup_id = parts[ 0 ]
            sequence_count = int( parts[ 1 ] )
            gigantic_ids_string = parts[ 2 ]

            # Parse comma-delimited GIGANTIC IDs
            gigantic_ids = [ gid.strip() for gid in gigantic_ids_string.split( ',' ) if gid.strip() ]

            orthogroup_ids___orthogroup_data[ orthogroup_id ] = {
                'gigantic_ids': gigantic_ids,
                'sequence_count': sequence_count
            }

    logger.info( f"Loaded {len( orthogroup_ids___orthogroup_data )} orthogroups" )

    if len( orthogroup_ids___orthogroup_data ) == 0:
        logger.error( f"CRITICAL ERROR: No orthogroups loaded!" )
        sys.exit( 1 )

    return orthogroup_ids___orthogroup_data


def load_id_mapping_reverse():
    """
    Load reverse ID mapping from GIGANTIC identifiers to short IDs.

    Returns:
        dict: { gigantic_id: short_id }
    """
    logger.info( f"Loading ID mapping (reverse) from: {input_id_mapping_file}" )

    if not input_id_mapping_file.exists():
        logger.error( f"CRITICAL ERROR: ID mapping file not found!" )
        logger.error( f"Expected location: {input_id_mapping_file}" )
        sys.exit( 1 )

    gigantic_ids___short_ids = {}

    with open( input_id_mapping_file, 'r' ) as input_file:
        # Short_ID (short identifier from orthogroup tool output)	GIGANTIC_ID (GIGANTIC identifier ...)
        # Abeoforma_whisleri-1	g_000-t_000-p_g1.t1-n_...
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            if len( parts ) < 2:
                continue

            short_id = parts[ 0 ]
            gigantic_id = parts[ 1 ]

            gigantic_ids___short_ids[ gigantic_id ] = short_id

    logger.info( f"Loaded {len( gigantic_ids___short_ids )} ID mappings (reverse)" )

    if len( gigantic_ids___short_ids ) == 0:
        logger.error( f"CRITICAL ERROR: No ID mappings loaded!" )
        sys.exit( 1 )

    return gigantic_ids___short_ids


def load_sequences_from_proteomes( short_ids___gigantic_ids ):
    """
    Load sequences directly from proteome FASTA files.
    Only called when include_fasta_in_output is true.

    Args:
        short_ids___gigantic_ids: Dictionary mapping short IDs to GIGANTIC IDs

    Returns:
        dict: { gigantic_id: sequence }
    """
    logger.info( f"Loading sequences from proteome FASTAs: {input_proteomes_directory}" )

    if not input_proteomes_directory.exists():
        logger.error( f"CRITICAL ERROR: Proteomes directory not found!" )
        logger.error( f"Expected location: {input_proteomes_directory}" )
        sys.exit( 1 )

    fasta_files = list( input_proteomes_directory.glob( '*.aa' ) )

    if len( fasta_files ) == 0:
        logger.error( f"CRITICAL ERROR: No FASTA files found in {input_proteomes_directory}!" )
        sys.exit( 1 )

    logger.info( f"Found {len( fasta_files )} proteome FASTA files" )

    # Build reverse mapping for filtering
    gigantic_ids_set = set( short_ids___gigantic_ids.values() )

    gigantic_ids___sequences = {}
    total_matched = 0

    for fasta_file in fasta_files:
        current_id = None
        current_sequence = []

        with open( fasta_file, 'r' ) as input_fasta:
            for line in input_fasta:
                line = line.strip()

                if line.startswith( '>' ):
                    # Save previous sequence
                    if current_id and current_sequence:
                        gigantic_ids___sequences[ current_id ] = ''.join( current_sequence )
                        total_matched += 1
                        current_sequence = []

                    # Parse new header
                    header = line[ 1: ]
                    gigantic_id = header.split()[ 0 ]

                    if gigantic_id in gigantic_ids_set:
                        current_id = gigantic_id
                    else:
                        current_id = None

                elif current_id:
                    current_sequence.append( line )

            # Save last sequence in file
            if current_id and current_sequence:
                gigantic_ids___sequences[ current_id ] = ''.join( current_sequence )
                total_matched += 1

    logger.info( f"Loaded {total_matched} sequences from FASTA files" )
    return gigantic_ids___sequences


def load_phylogenetic_blocks_for_structure():
    """
    Load phylogenetic blocks with block names for the current structure from trees_species.

    Returns:
        dict: { clade_name: phylogenetic_block_id_name }
    """
    logger.info( f"Loading phylogenetic blocks from trees_species: {input_trees_phylogenetic_blocks_all}" )

    block_files = list( input_trees_phylogenetic_blocks_all.glob( '*phylogenetic_blocks*.tsv' ) )

    if not block_files:
        logger.warning( f"No phylogenetic blocks files found in: {input_trees_phylogenetic_blocks_all}" )
        return {}

    block_file = block_files[ 0 ]
    logger.info( f"Using file: {block_file.name}" )

    clade_names___phylogenetic_blocks = {}

    with open( block_file, 'r' ) as input_file:
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        # Find column indices dynamically
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
            logger.warning( "Could not find required columns in phylogenetic blocks file" )
            return {}

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]
            if structure_id != TARGET_STRUCTURE:
                continue

            clade_name = parts[ clade_name_column ]
            block_id_name = parts[ block_id_name_column ] if block_id_name_column is not None and block_id_name_column < len( parts ) else 'NA'

            clade_names___phylogenetic_blocks[ clade_name ] = block_id_name

    logger.info( f"Loaded {len( clade_names___phylogenetic_blocks )} phylogenetic blocks for {TARGET_STRUCTURE}" )
    return clade_names___phylogenetic_blocks


def load_phylogenetic_paths_for_structure():
    """
    Load phylogenetic paths for the current structure from trees_species upstream data.

    Returns:
        dict: { clade_name: phylogenetic_path_string }
    """
    logger.info( f"Loading phylogenetic paths from trees_species: {input_trees_phylogenetic_paths_all}" )

    path_files = list( input_trees_phylogenetic_paths_all.glob( '*paths*.tsv' ) )
    if not path_files:
        path_files = list( input_trees_phylogenetic_paths_all.glob( '*evolutionary_paths*.tsv' ) )

    if not path_files:
        logger.warning( f"No phylogenetic paths files found in: {input_trees_phylogenetic_paths_all}" )
        return {}

    path_file = path_files[ 0 ]
    logger.info( f"Using file: {path_file.name}" )

    clade_names___phylogenetic_paths = {}

    with open( path_file, 'r' ) as input_file:
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        # Find column indices dynamically
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
            logger.warning( "Could not find required columns in phylogenetic paths file" )
            return {}

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]
            if structure_id != TARGET_STRUCTURE:
                continue

            species_name = parts[ species_name_column ]
            phylogenetic_path = parts[ path_column ]

            clade_names___phylogenetic_paths[ species_name ] = phylogenetic_path

    logger.info( f"Loaded {len( clade_names___phylogenetic_paths )} phylogenetic paths for {TARGET_STRUCTURE}" )
    return clade_names___phylogenetic_paths


# ============================================================================
# SECTION 4: EXTRACT SPECIES FROM GIGANTIC IDs
# ============================================================================

def extract_species_from_gigantic_id( gigantic_id ):
    """
    Extract species name from GIGANTIC identifier.

    GIGANTIC ID format:
    g_XXX-t_XXX-p_XXX-n_Kingdom_Phylum_Class_Order_Family_Genus_species...

    Args:
        gigantic_id: Full GIGANTIC sequence identifier

    Returns:
        str: Species name (Genus_species) or None
    """
    if '-n_' not in gigantic_id:
        return None

    phyloname = gigantic_id.split( '-n_' )[ 1 ]
    parts_phyloname = phyloname.split( '_' )

    # Species name = Genus_species (positions [5] onwards in phyloname)
    if len( parts_phyloname ) >= 7:
        species_name = '_'.join( parts_phyloname[ 5: ] )
        return species_name
    else:
        return None


# ============================================================================
# SECTION 5: DETERMINE ORTHOGROUP ORIGINS (MRCA ALGORITHM)
# ============================================================================

def determine_origin( orthogroup_species, species_ids___phylogenetic_paths, parents___children, clade_ids___clade_names ):
    """
    Determine the phylogenetic origin of an orthogroup using MRCA algorithm.

    Algorithm:
    1. Get phylogenetic path for each species in the orthogroup
    2. Find intersection of all paths (shared ancestral clades)
    3. Identify MRCA: iterate root-to-leaf through shared clades,
       find deepest clade where divergence occurs

    Args:
        orthogroup_species: List of species names
        species_ids___phylogenetic_paths: Dict mapping species IDs to phylogenetic paths
        parents___children: Dict mapping parent names to children names
        clade_ids___clade_names: Dict mapping clade IDs to clade names

    Returns:
        tuple: ( origin_clade_name, shared_clades_set )
    """
    # Build reverse mapping: clade_name -> clade_id
    species_names___clade_ids = {}
    for clade_id, clade_name in clade_ids___clade_names.items():
        species_names___clade_ids[ clade_name ] = clade_id

    # Get phylogenetic paths for all species in orthogroup
    orthogroup_phylogenetic_paths = []
    first_species_ordered_path = None

    for species_name in orthogroup_species:
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

    # Find intersection of all phylogenetic paths (shared ancestral clades)
    shared_clades_set = orthogroup_phylogenetic_paths[ 0 ].intersection( *orthogroup_phylogenetic_paths )

    if len( shared_clades_set ) == 0:
        return None, set()

    # Find the MRCA (most recent shared ancestral clade)
    # Iterate through first species' path in phylogenetic order (root to leaf)
    origin = None

    for clade_name in first_species_ordered_path:
        if clade_name not in shared_clades_set:
            continue

        # Check if this clade has children in the tree
        if clade_name not in parents___children:
            origin = clade_name
            continue

        children = parents___children[ clade_name ]

        if len( children ) < 2:
            continue

        child_1_name = children[ 0 ]
        child_2_name = children[ 1 ]

        # Neither child is in shared clades -> this is the origin (divergence point)
        if child_1_name not in shared_clades_set and child_2_name not in shared_clades_set:
            origin = clade_name

        # Self-loop terminal node
        elif clade_name == child_1_name and clade_name == child_2_name:
            origin = clade_name

    return origin, shared_clades_set


# ============================================================================
# SECTION 6: PROCESS ALL ORTHOGROUPS
# ============================================================================

def process_orthogroups( orthogroup_ids___orthogroup_data, species_ids___phylogenetic_paths, parents___children, clade_ids___clade_names ):
    """
    Process all orthogroups to determine their phylogenetic origins.

    Returns:
        tuple: ( orthogroup_origins, origins___orthogroups )
    """
    logger.info( f"Processing {len( orthogroup_ids___orthogroup_data )} orthogroups to determine origins..." )

    orthogroup_origins = {}
    origins___orthogroup_ids = defaultdict( list )

    processed_count = 0
    origin_found_count = 0
    origin_not_found_count = 0
    single_species_count = 0
    multi_species_count = 0

    # Build reverse mapping once
    species_names___clade_ids = { clade_name: clade_id for clade_id, clade_name in clade_ids___clade_names.items() }

    for orthogroup_id, orthogroup_data in orthogroup_ids___orthogroup_data.items():
        processed_count += 1

        if processed_count % 10000 == 0:
            logger.info( f"Processed {processed_count} / {len( orthogroup_ids___orthogroup_data )} orthogroups..." )

        # Extract species from GIGANTIC IDs
        gigantic_ids = orthogroup_data[ 'gigantic_ids' ]
        orthogroup_species = []

        for gigantic_id in gigantic_ids:
            species_name = extract_species_from_gigantic_id( gigantic_id )
            if species_name and species_name not in orthogroup_species:
                orthogroup_species.append( species_name )

        if len( orthogroup_species ) == 0:
            origin_not_found_count += 1
            continue

        # SINGLE-SPECIES ORTHOGROUPS: origin = the species itself
        if len( orthogroup_species ) == 1:
            single_species_count += 1
            species_name = orthogroup_species[ 0 ]
            origin = species_name

            # Shared clades = full phylogenetic path for this species
            if species_name in species_names___clade_ids:
                species_clade_id = species_names___clade_ids[ species_name ]
                if species_clade_id in species_ids___phylogenetic_paths:
                    shared_clades = set( species_ids___phylogenetic_paths[ species_clade_id ] )
                else:
                    shared_clades = { species_name }
            else:
                shared_clades = { species_name }

            orthogroup_origins[ orthogroup_id ] = {
                'origin': origin,
                'shared_clades': shared_clades,
                'species': orthogroup_species,
                'species_count': 1,
                'sequence_count': orthogroup_data[ 'sequence_count' ],
                'gigantic_ids': gigantic_ids
            }

            origins___orthogroup_ids[ origin ].append( orthogroup_id )
            origin_found_count += 1
            continue

        # MULTI-SPECIES ORTHOGROUPS: use MRCA algorithm
        multi_species_count += 1

        origin, shared_clades = determine_origin(
            orthogroup_species,
            species_ids___phylogenetic_paths,
            parents___children,
            clade_ids___clade_names
        )

        if origin is None:
            origin_not_found_count += 1
            continue

        orthogroup_origins[ orthogroup_id ] = {
            'origin': origin,
            'shared_clades': shared_clades,
            'species': orthogroup_species,
            'species_count': len( orthogroup_species ),
            'sequence_count': orthogroup_data[ 'sequence_count' ],
            'gigantic_ids': gigantic_ids
        }

        origins___orthogroup_ids[ origin ].append( orthogroup_id )
        origin_found_count += 1

    logger.info( f"Processed {processed_count} orthogroups" )
    logger.info( f"Single-species orthogroups: {single_species_count}" )
    logger.info( f"Multi-species orthogroups: {multi_species_count}" )
    logger.info( f"Origin found: {origin_found_count}" )
    logger.info( f"Origin not found: {origin_not_found_count}" )

    if origin_found_count == 0:
        logger.error( f"CRITICAL ERROR: No orthogroup origins found!" )
        sys.exit( 1 )

    return orthogroup_origins, origins___orthogroup_ids


# ============================================================================
# SECTION 7: WRITE OUTPUTS
# ============================================================================

def write_orthogroup_origins( orthogroup_origins, gigantic_ids___sequences, gigantic_ids___short_ids, clade_names___phylogenetic_blocks, clade_names___phylogenetic_paths ):
    """Write per-orthogroup origin assignments."""
    logger.info( f"Writing orthogroup origins to: {output_origins_file}" )

    with open( output_origins_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Build header columns (configurable FASTA)
        header_columns = [
            'Orthogroup_ID (orthogroup identifier)',
            'Origin_Clade (phylogenetic clade where orthogroup originated)',
            'Origin_Clade_Phylogenetic_Block (phylogenetic block for origin clade format Parent_Clade::Child_Clade)',
            'Origin_Clade_Phylogenetic_Path (phylogenetic path for origin clade comma delimited from root to origin clade)',
            'Shared_Clades (comma delimited list of shared ancestral clades)',
            'Species_Count (total unique species in orthogroup)',
            'Sequence_Count (total number of sequences in orthogroup)',
            'Species_List (comma delimited list of species in orthogroup)',
            'Sequence_IDs (comma delimited list of short sequence identifiers in orthogroup)'
        ]

        if INCLUDE_FASTA:
            header_columns.append(
                'Sequences_FASTA (FASTA formatted sequences for this orthogroup with actual newlines within cell)'
            )

        # Single-row header
        csv_writer.writerow( header_columns )

        for orthogroup_id in sorted( orthogroup_origins.keys() ):
            data = orthogroup_origins[ orthogroup_id ]

            origin = data[ 'origin' ]
            shared_clades_string = ','.join( sorted( data[ 'shared_clades' ] ) )
            species_count = data[ 'species_count' ]
            sequence_count = data[ 'sequence_count' ]

            # Look up phylogenetic block and path for origin clade
            phylogenetic_block = clade_names___phylogenetic_blocks.get( origin, 'NA' )
            phylogenetic_path = clade_names___phylogenetic_paths.get( origin, 'NA' )

            species_list = ','.join( sorted( data[ 'species' ] ) )
            gigantic_ids = data[ 'gigantic_ids' ]

            # Convert GIGANTIC IDs to short IDs
            short_ids = []
            for gigantic_id in gigantic_ids:
                short_id = gigantic_ids___short_ids.get( gigantic_id, gigantic_id )
                short_ids.append( short_id )
            sequence_ids_string = ','.join( sorted( short_ids ) )

            output_row = [
                orthogroup_id,
                origin,
                phylogenetic_block,
                phylogenetic_path,
                shared_clades_string,
                str( species_count ),
                str( sequence_count ),
                species_list,
                sequence_ids_string
            ]

            if INCLUDE_FASTA:
                fasta_lines = []
                for gigantic_id in sorted( gigantic_ids ):
                    sequence = gigantic_ids___sequences.get( gigantic_id, '' )
                    if sequence:
                        fasta_lines.append( f">{gigantic_id}" )
                        fasta_lines.append( sequence )
                fasta_string = '\n'.join( fasta_lines )
                output_row.append( fasta_string )

            csv_writer.writerow( output_row )

    logger.info( f"Wrote {len( orthogroup_origins )} orthogroup origins to {output_origins_file.name}" )


def write_origins_summary( origins___orthogroup_ids ):
    """Write summary of orthogroup counts per phylogenetic origin."""
    logger.info( f"Writing origins summary to: {output_summary_file}" )

    total_orthogroups = sum( len( orthogroup_list ) for orthogroup_list in origins___orthogroup_ids.values() )

    with open( output_summary_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Origin_Clade (phylogenetic clade where orthogroup originated)\t'
        output += 'Orthogroup_Count (count of orthogroups with this origin clade)\t'
        output += 'Percentage (percentage of all orthogroups with this origin clade)\n'
        output_file.write( output )

        # Sort by count descending
        sorted_origins = sorted( origins___orthogroup_ids.items(), key = lambda x: len( x[ 1 ] ), reverse = True )

        for origin_clade, orthogroup_list in sorted_origins:
            count = len( orthogroup_list )
            percentage = 100.0 * count / total_orthogroups if total_orthogroups > 0 else 0.0

            output = f"{origin_clade}\t{count}\t{percentage:.2f}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( origins___orthogroup_ids )} origin clades to {output_summary_file.name}" )


def write_orthogroups_by_origin( origins___orthogroup_ids ):
    """Write separate files for orthogroups grouped by origin clade."""
    logger.info( f"Writing orthogroups by origin to: {output_by_origin_directory}" )

    for origin_clade, orthogroup_list in origins___orthogroup_ids.items():
        safe_clade_name = origin_clade.replace( ' ', '_' ).replace( '/', '_' )
        output_file_path = output_by_origin_directory / f"{safe_clade_name}_orthogroups.txt"

        with open( output_file_path, 'w' ) as output_file:
            for orthogroup_id in sorted( orthogroup_list ):
                output_file.write( f"{orthogroup_id}\n" )

    logger.info( f"Wrote {len( origins___orthogroup_ids )} origin-specific orthogroup files" )


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 002: DETERMINE ORTHOGROUP ORIGINS" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Species set: {SPECIES_SET_NAME}" )
    logger.info( f"FASTA embedding: {'enabled' if INCLUDE_FASTA else 'disabled'}" )
    logger.info( "" )

    # Step 1: Load phylogenetic tree structure
    logger.info( "STEP 1: Loading phylogenetic tree structure..." )
    parents___children, children___parents = load_parent_child_relationships()
    clade_ids___clade_names = load_clade_mappings()

    # Step 2: Load phylogenetic paths
    logger.info( "" )
    logger.info( "STEP 2: Loading phylogenetic paths..." )
    species_ids___phylogenetic_paths = load_phylogenetic_paths()

    # Step 3: Load orthogroups
    logger.info( "" )
    logger.info( "STEP 3: Loading orthogroups..." )
    orthogroup_ids___orthogroup_data = load_orthogroups()

    # Step 4: Load ID mapping
    logger.info( "" )
    logger.info( "STEP 4: Loading ID mapping..." )
    gigantic_ids___short_ids = load_id_mapping_reverse()
    short_ids___gigantic_ids = { short_id: gigantic_id for gigantic_id, short_id in gigantic_ids___short_ids.items() }

    # Step 5: Optionally load sequences from proteome FASTAs
    gigantic_ids___sequences = {}
    if INCLUDE_FASTA:
        logger.info( "" )
        logger.info( "STEP 5: Loading sequences from proteome FASTAs..." )
        gigantic_ids___sequences = load_sequences_from_proteomes( short_ids___gigantic_ids )
    else:
        logger.info( "" )
        logger.info( "STEP 5: Skipping sequence loading (include_fasta_in_output = false)" )

    # Step 6: Load phylogenetic blocks and paths from trees_species
    logger.info( "" )
    logger.info( "STEP 6: Loading phylogenetic blocks and paths from trees_species..." )
    clade_names___phylogenetic_blocks = load_phylogenetic_blocks_for_structure()
    clade_names___phylogenetic_paths = load_phylogenetic_paths_for_structure()

    # Step 7: Determine origins for all orthogroups
    logger.info( "" )
    logger.info( "STEP 7: Determining phylogenetic origins..." )
    orthogroup_origins, origins___orthogroup_ids = process_orthogroups(
        orthogroup_ids___orthogroup_data,
        species_ids___phylogenetic_paths,
        parents___children,
        clade_ids___clade_names
    )

    # Step 8: Write outputs
    logger.info( "" )
    logger.info( "STEP 8: Writing outputs..." )
    write_orthogroup_origins( orthogroup_origins, gigantic_ids___sequences, gigantic_ids___short_ids, clade_names___phylogenetic_blocks, clade_names___phylogenetic_paths )
    write_origins_summary( origins___orthogroup_ids )
    write_orthogroups_by_origin( origins___orthogroup_ids )

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
    logger.info( f"  {output_by_origin_directory.name}/ ({len( origins___orthogroup_ids )} files)" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
