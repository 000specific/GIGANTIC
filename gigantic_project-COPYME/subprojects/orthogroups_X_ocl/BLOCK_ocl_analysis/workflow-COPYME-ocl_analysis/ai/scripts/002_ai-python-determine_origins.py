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
INCLUDE_FASTA = config.get( 'include_fasta_in_output', False )

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
input_phylogenetic_blocks_file = input_directory / f'1_ai-phylogenetic_blocks-{TARGET_STRUCTURE}.tsv'
input_parent_child_file = input_directory / f'1_ai-parent_child_table-{TARGET_STRUCTURE}.tsv'
input_phylogenetic_paths_file = input_directory / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
input_clade_mappings_file = input_directory / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'
input_orthogroups_file = input_directory / '1_ai-orthogroups-gigantic_identifiers.tsv'
# GIGANTIC_1 convention: no separate short→gigantic mapping file (it was a
# GIGANTIC_0 OrthoFinder vestige). Orthogroup files already contain gigantic IDs.

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
    Load clade ID to name mappings from Script 001 output, and return a
    canonical-identifier view per Rule 6 of AI_GUIDE-project.md.

    Returns:
        dict: { clade_name: clade_id_name }   — e.g., "Fonticula_alba" -> "C001_Fonticula_alba"
              Used to look up a species's leaf `clade_id_name` from its bare
              species name (which is what gets extracted from GIGANTIC protein
              identifiers in the orthogroups input).
    """
    logger.info( f"Loading clade mappings from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mappings file not found!" )
        logger.error( f"Expected location: {input_clade_mappings_file}" )
        sys.exit( 1 )

    clade_names___clade_id_names = {}

    with open( input_clade_mappings_file, 'r' ) as input_file:
        # Clade_Name (bare clade name lookup key as it appears in orthogroup input data)	Clade_ID_Name (atomic clade identifier e.g. C001_Fonticula_alba)
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
    the atomic `clade_id_name` form (e.g., "C082_Metazoa"). No splitting into
    bare `clade_id` or bare `clade_name` for internal lookups.

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
            # `clade_id_name` form (e.g., "C001_Fonticula_alba"). Store as-is.
            leaf_clade_id_name = parts[ 0 ].strip()
            path_string = parts[ 2 ]

            # Parse path elements. Each element is already in `clade_id_name`
            # form (e.g., "C068_Basal"). Store them as-is — no splitting.
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


def load_sequences_from_proteomes( gigantic_ids_set ):
    """
    Load sequences directly from proteome FASTA files.
    Only called when include_fasta_in_output is true.

    Args:
        gigantic_ids_set: Set of GIGANTIC identifiers to load sequences for.

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

    # Explicitly match the combined blocks file (e.g., 6_ai-phylogenetic_blocks-all_105_structures.tsv).
    # Path.glob() does not guarantee ordering (especially on Lustre), so we must match the
    # combined file by pattern rather than rely on [0] to pick it among per-structure files.
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

    # Per Rule 6 of AI_GUIDE-project.md, this dict is keyed by the atomic
    # `child_clade_id_name` form (e.g., "C082_Metazoa"). Value is the atomic
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
        dict: { clade_name: phylogenetic_path_string }
    """
    logger.info( f"Loading phylogenetic paths from trees_species: {input_trees_phylogenetic_paths_all}" )

    # Explicitly match the combined paths file (e.g., 4_ai-phylogenetic_paths-all_structures.tsv).
    # Path.glob() does not guarantee ordering (especially on Lustre), so we must match by
    # pattern rather than rely on [0].
    path_files = list( input_trees_phylogenetic_paths_all.glob( '*phylogenetic_paths-all_structures.tsv' ) )

    if not path_files:
        logger.warning( f"No combined phylogenetic paths file found in: {input_trees_phylogenetic_paths_all}" )
        return {}

    path_file = path_files[ 0 ]
    logger.info( f"Using file: {path_file.name}" )

    # Per Rule 6 of AI_GUIDE-project.md, this dict is keyed by the atomic
    # `clade_id_name` form (e.g., "C001_Fonticula_alba"), using the upstream
    # `Species_Clade_ID_Name` column directly (no combining required).
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

def determine_origin( orthogroup_species, species_clade_id_names___phylogenetic_paths, parents___children, clade_names___clade_id_names ):
    """
    Determine the phylogenetic origin of an orthogroup using MRCA algorithm.

    Per Rule 6 of AI_GUIDE-project.md, all clade identifiers throughout this
    function are in canonical `clade_id_name` form (e.g., "C082_Metazoa"). No
    splitting into `clade_id` and `clade_name` for internal lookups.

    Algorithm:
    1. Get phylogenetic path for each species in the orthogroup
    2. Find intersection of all paths (shared ancestral clades, as clade_id_names)
    3. Identify MRCA: iterate root-to-leaf through shared clades,
       find deepest clade where divergence occurs

    Args:
        orthogroup_species: List of bare species names (e.g., "Fonticula_alba"),
            as extracted from GIGANTIC protein identifiers in the orthogroups input.
        species_clade_id_names___phylogenetic_paths: Dict mapping each species's
            leaf `clade_id_name` (e.g., "C001_Fonticula_alba") to its full path
            as a list of `clade_id_name` strings (root → leaf).
        parents___children: Dict mapping parent `clade_id_name` to list of child
            `clade_id_name` values.
        clade_names___clade_id_names: Dict mapping bare clade_name (e.g.,
            "Fonticula_alba") to that clade's `clade_id_name` (e.g.,
            "C001_Fonticula_alba"). Used to translate species names (from
            orthogroup members) into leaf clade_id_names for path lookup.

    Returns:
        tuple: ( origin_clade_id_name, shared_clade_id_names_set )
    """
    # Get phylogenetic paths for all species in orthogroup
    orthogroup_phylogenetic_paths = []
    first_species_ordered_path = None

    for species_name in orthogroup_species:
        # Translate species name -> leaf clade_id_name
        if species_name not in clade_names___clade_id_names:
            continue
        species_clade_id_name = clade_names___clade_id_names[ species_name ]

        if species_clade_id_name not in species_clade_id_names___phylogenetic_paths:
            continue

        phylogenetic_path = species_clade_id_names___phylogenetic_paths[ species_clade_id_name ]

        if first_species_ordered_path is None:
            first_species_ordered_path = phylogenetic_path

        orthogroup_phylogenetic_paths.append( set( phylogenetic_path ) )

    if len( orthogroup_phylogenetic_paths ) == 0:
        return None, set()

    # Find intersection of all phylogenetic paths (shared ancestral clade_id_names)
    shared_clade_id_names_set = orthogroup_phylogenetic_paths[ 0 ].intersection( *orthogroup_phylogenetic_paths )

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
# SECTION 6: PROCESS ALL ORTHOGROUPS
# ============================================================================

def process_orthogroups( orthogroup_ids___orthogroup_data, species_clade_id_names___phylogenetic_paths, parents___children, clade_names___clade_id_names ):
    """
    Process all orthogroups to determine their phylogenetic origins.

    Per Rule 6 of AI_GUIDE-project.md, all clade identifiers (including origins)
    are in canonical `clade_id_name` form (e.g., "C082_Metazoa").

    Single-species orthogroups (Option A from design discussion, 2026-04-14):
    origin is set to that species's LEAF `clade_id_name` (e.g.,
    "C048_Schmidtea_mediterranea"), not the bare species name — for consistency
    with the rest of the pipeline.

    Returns:
        tuple: ( orthogroup_origins, origins___orthogroups ) — both keyed / valued
        in clade_id_name form.
    """
    logger.info( f"Processing {len( orthogroup_ids___orthogroup_data )} orthogroups to determine origins..." )

    orthogroup_origins = {}
    origins___orthogroup_ids = defaultdict( list )

    processed_count = 0
    origin_found_count = 0
    origin_not_found_count = 0
    single_species_count = 0
    multi_species_count = 0

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

        # SINGLE-SPECIES ORTHOGROUPS: origin = species's LEAF `clade_id_name`
        if len( orthogroup_species ) == 1:
            single_species_count += 1
            species_name = orthogroup_species[ 0 ]

            # Option A (see design discussion 2026-04-14): origin is the
            # leaf clade_id_name for this species, consistent with Rule 6.
            species_clade_id_name = clade_names___clade_id_names.get( species_name )
            if species_clade_id_name is None:
                # Species missing from clade mappings — skip this orthogroup,
                # logging will show it as origin_not_found.
                origin_not_found_count += 1
                continue

            origin = species_clade_id_name

            # Shared clades = full phylogenetic path for this species (all
            # clade_id_names from root → leaf).
            if species_clade_id_name in species_clade_id_names___phylogenetic_paths:
                shared_clades = set( species_clade_id_names___phylogenetic_paths[ species_clade_id_name ] )
            else:
                shared_clades = { species_clade_id_name }

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
            species_clade_id_names___phylogenetic_paths,
            parents___children,
            clade_names___clade_id_names
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

def write_orthogroup_origins( orthogroup_origins, gigantic_ids___sequences, clade_id_names___phylogenetic_blocks, clade_id_names___phylogenetic_paths ):
    """Write per-orthogroup origin assignments.

    Per Rule 6 of AI_GUIDE-project.md, the `Origin_Clade` column contains
    the canonical `clade_id_name` form (e.g., "C082_Metazoa"). Shared_Clades
    is a comma-delimited list of `clade_id_name` values.
    """
    logger.info( f"Writing orthogroup origins to: {output_origins_file}" )

    with open( output_origins_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Build header columns (configurable FASTA).
        # Per Rule 7, origin is a phylogenetic transition block (state O), not a
        # clade. It is fully specified by the block identifier parent::child and
        # the block-state identifier parent::child-O. A separate "origin clade"
        # column is redundant and implies origin-as-a-clade, so it is omitted.
        header_columns = [
            'Orthogroup_ID (orthogroup identifier)',
            'Origin_Phylogenetic_Block (phylogenetic block containing the origin transition format Parent_Clade_ID_Name::Child_Clade_ID_Name)',
            'Origin_Phylogenetic_Block_State (phylogenetic transition block for origin in five-state vocabulary format Parent_Clade_ID_Name::Child_Clade_ID_Name-O where the -O suffix marks Origin; five states are A=Inherited Absence O=Origin P=Inherited Presence L=Loss X=Inherited Loss)',
            'Origin_Phylogenetic_Path (phylogenetic path from root to the child endpoint of the origin block comma delimited as clade_id_name values)',
            'Shared_Clade_ID_Names (comma delimited list of shared ancestral clade_id_name values)',
            'Species_Count (total unique species in orthogroup)',
            'Sequence_Count (total number of sequences in orthogroup)',
            'Species_List (comma delimited list of species in orthogroup)',
            'Sequence_IDs (comma delimited list of GIGANTIC sequence identifiers in orthogroup)'
        ]

        if INCLUDE_FASTA:
            header_columns.append(
                'Sequences_FASTA (FASTA formatted sequences for this orthogroup with actual newlines within cell)'
            )

        # Single-row header
        csv_writer.writerow( header_columns )

        for orthogroup_id in sorted( orthogroup_origins.keys() ):
            data = orthogroup_origins[ orthogroup_id ]

            origin = data[ 'origin' ]  # clade_id_name
            shared_clades_string = ','.join( sorted( data[ 'shared_clades' ] ) )
            species_count = data[ 'species_count' ]
            sequence_count = data[ 'sequence_count' ]

            # Look up phylogenetic block and path for origin clade (both keyed by clade_id_name).
            # The phylogenetic block is the tree-structural edge whose child endpoint is the
            # origin clade; in the GIGANTIC block vs block-state vocabulary, the block itself
            # is feature-agnostic. The origin block-state extends the block identifier with the
            # state letter `-O` (Origin) from the five-state vocabulary {A, O, P, L, X}:
            #   A = Inherited Absence, O = Origin, P = Inherited Presence,
            #   L = Loss,              X = Inherited Loss.
            phylogenetic_block = clade_id_names___phylogenetic_blocks.get( origin, 'NA' )
            phylogenetic_block_state = f"{phylogenetic_block}-O" if phylogenetic_block != 'NA' else 'NA'
            phylogenetic_path = clade_id_names___phylogenetic_paths.get( origin, 'NA' )

            species_list = ','.join( sorted( data[ 'species' ] ) )
            gigantic_ids = data[ 'gigantic_ids' ]

            # GIGANTIC_1: Sequence IDs are already gigantic — no short-ID mapping needed.
            sequence_ids_string = ','.join( sorted( gigantic_ids ) )

            output_row = [
                orthogroup_id,
                phylogenetic_block,
                phylogenetic_block_state,
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


def write_origins_summary( origins___orthogroup_ids, clade_id_names___phylogenetic_blocks ):
    """Write summary of orthogroup counts per phylogenetic origin transition block.

    Per Rule 7, origins are phylogenetic transition blocks (state O), not clades.
    Grouping is therefore on the block-state identifier `parent::child-O`.
    """
    logger.info( f"Writing origins summary to: {output_summary_file}" )

    total_orthogroups = sum( len( orthogroup_list ) for orthogroup_list in origins___orthogroup_ids.values() )

    with open( output_summary_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Origin_Phylogenetic_Block_State (phylogenetic transition block for origin format Parent_Clade_ID_Name::Child_Clade_ID_Name-O e.g. C069_Holozoa::C082_Metazoa-O)\t'
        output += 'Orthogroup_Count (count of orthogroups whose origin is this transition block)\t'
        output += 'Percentage (percentage of all orthogroups originating on this transition block)\n'
        output_file.write( output )

        # Sort by count descending.
        sorted_origins = sorted( origins___orthogroup_ids.items(), key = lambda x: len( x[ 1 ] ), reverse = True )

        for origin_child_clade_id_name, orthogroup_list in sorted_origins:
            phylogenetic_block = clade_id_names___phylogenetic_blocks.get( origin_child_clade_id_name, 'NA' )
            phylogenetic_block_state = f"{phylogenetic_block}-O" if phylogenetic_block != 'NA' else 'NA'

            count = len( orthogroup_list )
            percentage = 100.0 * count / total_orthogroups if total_orthogroups > 0 else 0.0

            output = f"{phylogenetic_block_state}\t{count}\t{percentage:.2f}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( origins___orthogroup_ids )} origin transition blocks to {output_summary_file.name}" )


def write_orthogroups_by_origin( origins___orthogroup_ids, clade_id_names___phylogenetic_blocks ):
    """Write separate files for orthogroups grouped by origin transition block.

    Per Rule 7, files are named by the block-state identifier `parent::child-O`.
    File names use the block-state string with `::` replaced by `__` so the
    identifier is filesystem-safe while remaining unambiguously recoverable.
    """
    logger.info( f"Writing orthogroups by origin to: {output_by_origin_directory}" )

    for origin_child_clade_id_name, orthogroup_list in origins___orthogroup_ids.items():
        phylogenetic_block = clade_id_names___phylogenetic_blocks.get( origin_child_clade_id_name, 'NA' )
        if phylogenetic_block == 'NA':
            phylogenetic_block_state = f"NA-{origin_child_clade_id_name}-O"
        else:
            phylogenetic_block_state = f"{phylogenetic_block}-O"

        # Filesystem-safe form: replace `::` with `__` to keep the identifier
        # readable and reversible when reading the file name back.
        safe_file_stem = phylogenetic_block_state.replace( '::', '__' ).replace( ' ', '_' ).replace( '/', '_' )
        output_file_path = output_by_origin_directory / f"{safe_file_stem}_orthogroups.txt"

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
    # Per Rule 6 of AI_GUIDE-project.md, all dicts are keyed by clade_id_name.
    logger.info( "STEP 1: Loading phylogenetic tree structure..." )
    parents___children, children___parents = load_parent_child_relationships()
    clade_names___clade_id_names = load_clade_mappings()

    # Step 2: Load phylogenetic paths
    logger.info( "" )
    logger.info( "STEP 2: Loading phylogenetic paths..." )
    species_clade_id_names___phylogenetic_paths = load_phylogenetic_paths()

    # Step 3: Load orthogroups
    logger.info( "" )
    logger.info( "STEP 3: Loading orthogroups..." )
    orthogroup_ids___orthogroup_data = load_orthogroups()

    # Step 4: Optionally load sequences from proteome FASTAs
    # (GIGANTIC_1 convention: orthogroup files contain gigantic IDs directly, so
    # we derive the target ID set from the loaded orthogroup data — no separate
    # short→gigantic mapping layer.)
    gigantic_ids___sequences = {}
    if INCLUDE_FASTA:
        logger.info( "" )
        logger.info( "STEP 4: Loading sequences from proteome FASTAs..." )
        gigantic_ids_set = set()
        for og_data in orthogroup_ids___orthogroup_data.values():
            gigantic_ids_set.update( og_data.get( 'gigantic_ids', [] ) )
        gigantic_ids___sequences = load_sequences_from_proteomes( gigantic_ids_set )
    else:
        logger.info( "" )
        logger.info( "STEP 4: Skipping sequence loading (include_fasta_in_output = false)" )

    # Step 5: Load phylogenetic blocks and paths from trees_species
    logger.info( "" )
    logger.info( "STEP 5: Loading phylogenetic blocks and paths from trees_species..." )
    clade_id_names___phylogenetic_blocks = load_phylogenetic_blocks_for_structure()
    clade_id_names___phylogenetic_paths = load_phylogenetic_paths_for_structure()

    # Step 6: Determine origins for all orthogroups
    logger.info( "" )
    logger.info( "STEP 6: Determining phylogenetic origins..." )
    orthogroup_origins, origins___orthogroup_ids = process_orthogroups(
        orthogroup_ids___orthogroup_data,
        species_clade_id_names___phylogenetic_paths,
        parents___children,
        clade_names___clade_id_names
    )

    # Step 7: Write outputs
    logger.info( "" )
    logger.info( "STEP 7: Writing outputs..." )
    write_orthogroup_origins( orthogroup_origins, gigantic_ids___sequences, clade_id_names___phylogenetic_blocks, clade_id_names___phylogenetic_paths )
    write_origins_summary( origins___orthogroup_ids, clade_id_names___phylogenetic_blocks )
    write_orthogroups_by_origin( origins___orthogroup_ids, clade_id_names___phylogenetic_blocks )

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
