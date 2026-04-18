# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Classify phylogenetic block-states per annogroup and aggregate per-block counts
# Human: Eric Edsinger

"""
OCL Pipeline Script 003: Classify Phylogenetic Block-States (Rule 7)

For each phylogenetic block (parent::child) and each annogroup, classify the
(block, annogroup) pair into one of the five Rule 7 block-states:

  -A (Inherited Absence):   parent absent, child absent, pre-origin
  -O (Origin):              parent absent, child present, event
                            (emitted by Script 002; not re-scored here)
  -P (Inherited Presence):  parent present, child present, conservation
  -L (Loss):                parent present, child absent, event
  -X (Inherited Loss):      parent absent, child absent, post-loss

Two per-clade sets are computed from the phylogenetic paths imported by
Script 001 (from trees_species):

- "Scoring-eligible at this clade": the clade is a descendant of (or equal to)
  the child endpoint of the annogroup's origin transition block. Derived by
  a single pass over the phylogenetic paths -- no sampling.
- "Actually present at this clade": at least one descendant species of the
  clade carries the annogroup in its genome.

Terminal self-loops (parent_clade_id_name == child_clade_id_name at a tip)
are placeholder rows in the parent-child table and are excluded from block
iteration -- they are not phylogenetic blocks.

Edge case: an annogroup with origin block whose child endpoint is a tip has
no descendant blocks to score; its per-annogroup counts are all zero.

Inputs (from previous scripts):
- 1-output: Clade mappings, parent-child relationships, phylogenetic paths,
  annogroups with species identifiers
- 2-output: Annogroup origins with phylogenetic block and path annotations

Outputs (to 3-output/):
- Per-block conservation/loss statistics
- Per-annogroup conservation patterns with block-state counts
- Conservation/loss summary

Usage:
    python 003_ai-python-quantify_conservation_loss.py --structure_id 001 --config ../../START_HERE-user_config.yaml
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
        description = 'OCL Pipeline Script 003: Quantify annogroup conservation and loss across phylogenetic blocks',
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
        help = 'Path to START_HERE-user_config.yaml configuration file'
    )

    parser.add_argument(
        '--output_dir',
        type = str,
        default = 'OUTPUT_pipeline',
        help = 'Base output directory (default: OUTPUT_pipeline)'
    )

    return parser.parse_args()


# ============================================================================
# CONFIGURATION
# ============================================================================

args = parse_arguments()

# Load configuration
config_path = Path( args.config ).resolve()

if not config_path.exists():
    print( f"CRITICAL ERROR: Config file not found: {config_path}" )
    sys.exit( 1 )

with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

# Format structure ID
TARGET_STRUCTURE = f"structure_{args.structure_id}"

# Input directories
input_directory_001 = Path( args.output_dir ) / TARGET_STRUCTURE / '1-output'
input_directory_002 = Path( args.output_dir ) / TARGET_STRUCTURE / '2-output'

# Input files from Script 001
input_clade_mappings_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_clade_mappings.tsv'
input_parent_child_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_parent_child_table.tsv'
input_phylogenetic_paths_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_phylogenetic_paths.tsv'
input_annogroups_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_annogroups-species_identifiers.tsv'

# Input files from Script 002
input_origins_file = input_directory_002 / f'2_ai-{TARGET_STRUCTURE}_annogroup_origins.tsv'

# Output directory
output_directory = Path( args.output_dir ) / TARGET_STRUCTURE / '3-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_block_statistics_file = output_directory / f'3_ai-{TARGET_STRUCTURE}_conservation_loss-per_block.tsv'
output_annogroup_patterns_file = output_directory / f'3_ai-{TARGET_STRUCTURE}_conservation_patterns-per_annogroup.tsv'
output_summary_file = output_directory / f'3_ai-{TARGET_STRUCTURE}_conservation_loss-summary.tsv'

# Log file
log_directory = Path( args.output_dir ) / TARGET_STRUCTURE / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / f'3_ai-log-quantify_conservation_loss-{TARGET_STRUCTURE}.log'

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

def load_clade_mappings():
    """
    Load clade mappings from Script 001 output.

    Builds a map from bare clade_name -> clade_id_name (CXXX_Name),
    used to convert annogroup species names (bare Genus_species) to their
    leaf clade_id_name form for consistent clade_id_name indexing throughout.

    Returns:
        dict: { clade_name: clade_id_name }  (e.g. 'Homo_sapiens' -> 'C005_Homo_sapiens')
    """
    logger.info( f"Loading clade mappings from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mapping file not found!" )
        logger.error( f"Expected: {input_clade_mappings_file}" )
        sys.exit( 1 )

    clade_names___clade_id_names = {}

    with open( input_clade_mappings_file, 'r' ) as input_file:
        # Clade_Name (bare clade name lookup key)	Clade_ID_Name (atomic clade identifier)
        # Fonticula_alba	C001_Fonticula_alba
        header_line = input_file.readline()  # Skip single-row header

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

    logger.info( f"Loaded {len( clade_names___clade_id_names )} clade mappings (clade_name -> clade_id_name)" )

    return clade_names___clade_id_names


def load_parent_child_relationships():
    """
    Load parent-child relationships from Script 001 output (Rule 6/7 atomic
    3-column format). Each row is exactly one phylogenetic block: a parent
    clade -> child clade edge with two distinct endpoints. Script 005 no
    longer emits tip self-loops, so no self-loop filter is needed here.

    Returns:
        tuple: ( parents___children, children___parents )
            - parents___children: { parent_clade_id_name: [ child_clade_id_name, ... ] }
            - children___parents: { child_clade_id_name: parent_clade_id_name }
    """
    logger.info( f"Loading parent-child relationships from: {input_parent_child_file}" )

    if not input_parent_child_file.exists():
        logger.error( f"CRITICAL ERROR: Parent-child file not found!" )
        logger.error( f"Expected: {input_parent_child_file}" )
        sys.exit( 1 )

    parents___children = {}
    children___parents = {}

    with open( input_parent_child_file, 'r' ) as input_file:
        # Phylogenetic_Block (atomic phylogenetic block identifier as Parent_Clade_ID_Name::Child_Clade_ID_Name)	Parent_Clade_ID_Name (atomic parent clade identifier)	Child_Clade_ID_Name (atomic child clade identifier)
        # C069_Holozoa::C082_Metazoa	C069_Holozoa	C082_Metazoa
        header_line = input_file.readline()
        header_parts = header_line.strip().split( '\t' )

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

            if parent_clade_id_name not in parents___children:
                parents___children[ parent_clade_id_name ] = []
            parents___children[ parent_clade_id_name ].append( child_clade_id_name )

            children___parents[ child_clade_id_name ] = parent_clade_id_name

    logger.info( f"Loaded {len( parents___children )} parent nodes with children" )
    logger.info( f"Loaded {len( children___parents )} parent-child transitions (phylogenetic blocks)" )

    return parents___children, children___parents


def load_phylogenetic_paths():
    """
    Load phylogenetic paths (root-to-tip) from Script 001 output.

    Paths are kept in clade_id_name form throughout (no stripping). Dict
    is keyed by the leaf species_clade_id_name (e.g. 'C005_Homo_sapiens').

    Returns:
        dict: { species_clade_id_name: [ clade_id_name_root, ..., species_clade_id_name ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_file}" )

    if not input_phylogenetic_paths_file.exists():
        logger.error( f"CRITICAL ERROR: Phylogenetic paths file not found!" )
        logger.error( f"Expected: {input_phylogenetic_paths_file}" )
        sys.exit( 1 )

    species_clade_id_names___phylogenetic_paths = {}

    with open( input_phylogenetic_paths_file, 'r' ) as input_file:
        # Leaf_Clade_ID (terminal leaf clade identifier and name)	Path_Length (number of nodes in path from root to leaf)	Phylogenetic_Path (comma delimited path from root to leaf)
        # C001_Fonticula_alba	3	C068_Basal,C069_Holomycota,C001_Fonticula_alba
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            path_string = parts[ 2 ]

            # Path already in clade_id_name form - keep as-is.
            path = [ entry for entry in path_string.split( ',' ) if entry ]

            if path:
                species_clade_id_name = path[ -1 ]
                species_clade_id_names___phylogenetic_paths[ species_clade_id_name ] = path

    logger.info( f"Loaded {len( species_clade_id_names___phylogenetic_paths )} phylogenetic paths" )

    return species_clade_id_names___phylogenetic_paths


def build_clade_descendants( species_clade_id_names___phylogenetic_paths ):
    """
    Build mapping of each clade_id_name to all descendant species_clade_id_names.

    Returns:
        dict: { clade_id_name: set( descendant species_clade_id_name ) }
    """
    logger.info( "Building clade-to-descendants mapping (clade_id_name -> species_clade_id_name set)..." )

    clade_id_names___descendant_species_clade_id_names = defaultdict( set )

    for species_clade_id_name, path in species_clade_id_names___phylogenetic_paths.items():
        for clade_id_name in path:
            clade_id_names___descendant_species_clade_id_names[ clade_id_name ].add( species_clade_id_name )

    logger.info( f"Built descendants mapping for {len( clade_id_names___descendant_species_clade_id_names )} clades" )

    return clade_id_names___descendant_species_clade_id_names


def build_clade_to_all_descendant_clades_from_paths( species_clade_id_names___phylogenetic_paths ):
    """
    Build mapping of each clade_id_name to the set of all clade_id_names that
    are descendants of it on the species tree structure, including itself.

    Derived directly from the phylogenetic paths imported from trees_species
    via Script 001. No new tree walk is needed -- the paths already encode
    the ancestor/descendant relationships of the species tree structure.

    Returns:
        dict: { clade_id_name: set( clade_id_name ) }
    """
    logger.info( "Building clade-to-all-descendant-clades mapping from imported phylogenetic paths..." )

    clade_id_names___descendant_clade_id_names = defaultdict( set )

    for species_clade_id_name, path in species_clade_id_names___phylogenetic_paths.items():
        for position_index, clade_id_name in enumerate( path ):
            for descendant_clade_id_name in path[ position_index: ]:
                clade_id_names___descendant_clade_id_names[ clade_id_name ].add( descendant_clade_id_name )

    logger.info( f"Built descendant-clades mapping for {len( clade_id_names___descendant_clade_id_names )} clades" )

    return clade_id_names___descendant_clade_id_names


# ============================================================================
# SECTION 2: LOAD ANNOGROUP DATA
# ============================================================================

def load_annogroup_origins():
    """
    Load annogroup origin data from Script 002 output.

    Per Rule 7, origin is a phylogenetic transition block identified by both
    Origin_Phylogenetic_Block (parent::child) and Origin_Phylogenetic_Block_State
    (parent::child-O). The child endpoint of the origin block is derived here
    by splitting the block identifier on ::.

    Returns:
        dict: { annogroup_id: {
            'origin_child_clade_id_name': str,
            'phylogenetic_block': str,
            'phylogenetic_block_state': str,
            'phylogenetic_path': str,
            'species_list': str,
            'annogroup_subtype': str
        } }
    """
    logger.info( f"Loading annogroup origins from: {input_origins_file}" )

    if not input_origins_file.exists():
        logger.error( f"CRITICAL ERROR: Annogroup origins file not found!" )
        logger.error( f"Expected: {input_origins_file}" )
        sys.exit( 1 )

    annogroups___origin_data = {}

    with open( input_origins_file, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Annogroup_ID	Annogroup_Subtype	Origin_Phylogenetic_Block	Origin_Phylogenetic_Block_State	Origin_Phylogenetic_Path	Shared_Clade_ID_Names	Species_Count	Species_List
        # annogroup_pfam_1	single	C069_Holozoa::C002_Filozoa	C069_Holozoa::C002_Filozoa-O	C068_Basal,C069_Holozoa,C002_Filozoa	C068_Basal,C069_Holozoa,C002_Filozoa	42	Homo_sapiens,...
        header_row = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            annogroup_subtype = parts[ 1 ]
            phylogenetic_block = parts[ 2 ]
            phylogenetic_block_state = parts[ 3 ]
            phylogenetic_path = parts[ 4 ]
            species_list = parts[ 7 ]

            # Derive the child clade of the origin block
            if phylogenetic_block != 'NA' and '::' in phylogenetic_block:
                origin_child_clade_id_name = phylogenetic_block.split( '::', 1 )[ 1 ]
            else:
                origin_child_clade_id_name = 'NA'

            annogroups___origin_data[ annogroup_id ] = {
                'origin_child_clade_id_name': origin_child_clade_id_name,
                'phylogenetic_block': phylogenetic_block,
                'phylogenetic_block_state': phylogenetic_block_state,
                'phylogenetic_path': phylogenetic_path,
                'species_list': species_list,
                'annogroup_subtype': annogroup_subtype
            }

    logger.info( f"Loaded origin data for {len( annogroups___origin_data )} annogroups" )

    return annogroups___origin_data


def load_annogroup_species( clade_names___clade_id_names ):
    """
    Load species composition for each annogroup from Script 001 output,
    converting bare Genus_species names to species_clade_id_name form via
    the clade_mappings reverse index.

    Species in annogroups but absent from the clade_mappings for this
    structure are skipped.

    Args:
        clade_names___clade_id_names: { clade_name: clade_id_name }

    Returns:
        dict: { annogroup_id: set( species_clade_id_name ) }
    """
    logger.info( f"Loading annogroup species from: {input_annogroups_file}" )

    if not input_annogroups_file.exists():
        logger.error( f"CRITICAL ERROR: Annogroups file not found!" )
        logger.error( f"Expected: {input_annogroups_file}" )
        sys.exit( 1 )

    annogroups___species_clade_id_names = {}
    missing_species_names = set()

    with open( input_annogroups_file, 'r' ) as input_file:
        # Annogroup_ID (annogroup identifier format annogroup_{db}_N)	Annogroup_Subtype (single or combo or zero)	Species_Count (number of unique species in annogroup)	Species_List (comma delimited list of species names as Genus_species)
        # annogroup_pfam_1	single	5	Homo_sapiens,Mus_musculus,...
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            annogroup_id = parts[ 0 ]
            species_list_string = parts[ 3 ]

            # Species are already Genus_species -- no GIGANTIC ID parsing needed
            species_names = species_list_string.split( ',' )

            species_clade_id_names_set = set()
            for species_name in species_names:
                species_name = species_name.strip()
                if not species_name:
                    continue
                species_clade_id_name = clade_names___clade_id_names.get( species_name )
                if species_clade_id_name is None:
                    missing_species_names.add( species_name )
                    continue
                species_clade_id_names_set.add( species_clade_id_name )

            annogroups___species_clade_id_names[ annogroup_id ] = species_clade_id_names_set

    logger.info( f"Loaded species_clade_id_names for {len( annogroups___species_clade_id_names )} annogroups" )
    if missing_species_names:
        logger.info( f"Skipped {len( missing_species_names )} species not in this structure's clade_mappings" )

    return annogroups___species_clade_id_names


# ============================================================================
# SECTION 3: DETERMINE ANNOGROUPS PRESENT IN EACH CLADE
# ============================================================================

def build_clade_annogroups( annogroups___origin_data, annogroups___species_clade_id_names,
                            clade_id_names___descendant_species_clade_id_names,
                            clade_id_names___descendant_clade_id_names ):
    """
    For each clade C, compute two per-clade annogroup sets needed for scoring
    phylogenetic blocks under Rule 7:

    1. annogroups for which C is a descendant of (or equal to) the child
       endpoint of the origin transition block -- i.e. annogroups whose origin
       transition block sits on the root-to-C lineage or at C itself. These
       are the annogroups eligible for P/L/X block-state scoring when C is a
       parent in a block.

    2. annogroups actually carried by at least one descendant species of C
       (biological presence, distinct from the topological eligibility above).

    Returns:
        tuple: (
            clade_id_names___annogroups_eligible_for_scoring_at_this_clade,
            clade_id_names___annogroups_actually_present_at_this_clade
        )
    """
    logger.info( "=" * 80 )
    logger.info( "DETERMINING ANNOGROUP-CLADE RELATIONSHIPS (Rule 7):" )
    logger.info( "  1. SCORING-ELIGIBLE = clade is a descendant of (or equal to)" )
    logger.info( "     the child endpoint of the annogroup's origin transition block" )
    logger.info( "  2. ACTUALLY PRESENT = at least one descendant species of the clade" )
    logger.info( "     carries the annogroup" )
    logger.info( "=" * 80 )

    clade_id_names___annogroups_eligible_for_scoring_at_this_clade = defaultdict( set )
    clade_id_names___annogroups_actually_present_at_this_clade = defaultdict( set )

    for annogroup_id, annogroup_species_clade_id_names in annogroups___species_clade_id_names.items():
        origin_data = annogroups___origin_data.get( annogroup_id )
        if not origin_data:
            continue

        origin_child_clade_id_name = origin_data.get( 'origin_child_clade_id_name', 'NA' )
        if not origin_child_clade_id_name or origin_child_clade_id_name == 'NA':
            continue

        # All clades that sit on or below the child endpoint of the origin block.
        eligible_clade_id_names = clade_id_names___descendant_clade_id_names.get(
            origin_child_clade_id_name, set()
        )

        for clade_id_name in eligible_clade_id_names:
            clade_id_names___annogroups_eligible_for_scoring_at_this_clade[ clade_id_name ].add( annogroup_id )

            descendant_species_clade_id_names = clade_id_names___descendant_species_clade_id_names.get(
                clade_id_name, set()
            )
            if annogroup_species_clade_id_names.intersection( descendant_species_clade_id_names ):
                clade_id_names___annogroups_actually_present_at_this_clade[ clade_id_name ].add( annogroup_id )

    logger.info(
        f"Scoring-eligible annogroups present at: "
        f"{len( clade_id_names___annogroups_eligible_for_scoring_at_this_clade )} clades"
    )
    logger.info(
        f"Annogroups actually present at: "
        f"{len( clade_id_names___annogroups_actually_present_at_this_clade )} clades"
    )
    logger.info( "=" * 80 )

    return (
        clade_id_names___annogroups_eligible_for_scoring_at_this_clade,
        clade_id_names___annogroups_actually_present_at_this_clade,
    )


# ============================================================================
# SECTION 4: CALCULATE CONSERVATION AND LOSS PER BLOCK
# ============================================================================

def calculate_conservation_loss(
    parents___children,
    clade_id_names___annogroups_eligible_for_scoring_at_this_clade,
    clade_id_names___annogroups_actually_present_at_this_clade,
):
    """
    Compute per-block statistics for each phylogenetic block (parent::child).

    For each block, counts annogroups in three categories using the biological
    "actually present" sets:

      - inherited_count: annogroups biologically present at the parent clade.
      - conserved_count: inherited annogroups that are also present at child
        (block-state P).
      - lost_count: inherited annogroups that are absent at child (block-state L).

    Returns:
        list: Per-block statistics dictionaries.
    """
    logger.info( "Calculating conservation and loss per phylogenetic block (Rule 7)..." )

    block_statistics = []

    for parent_clade_id_name, children in parents___children.items():
        annogroups_actually_present_at_parent = (
            clade_id_names___annogroups_actually_present_at_this_clade.get(
                parent_clade_id_name, set()
            )
        )

        for child_clade_id_name in children:
            annogroups_actually_present_at_child = (
                clade_id_names___annogroups_actually_present_at_this_clade.get(
                    child_clade_id_name, set()
                )
            )

            inherited = annogroups_actually_present_at_parent
            conserved = inherited.intersection( annogroups_actually_present_at_child )
            lost = inherited - annogroups_actually_present_at_child

            block_statistic = {
                'parent_clade_id_name': parent_clade_id_name,
                'child_clade_id_name': child_clade_id_name,
                'inherited_count': len( inherited ),
                'conserved_count': len( conserved ),
                'lost_count': len( lost ),
            }

            block_statistics.append( block_statistic )

    logger.info( f"Calculated statistics for {len( block_statistics )} phylogenetic blocks" )

    return block_statistics


# ============================================================================
# SECTION 5: ANALYZE CONSERVATION PATTERNS PER ANNOGROUP
# ============================================================================

def analyze_annogroup_patterns(
    annogroups___origin_data,
    annogroups___species_clade_id_names,
    parents___children,
    clade_id_names___annogroups_eligible_for_scoring_at_this_clade,
    clade_id_names___annogroups_actually_present_at_this_clade,
):
    """
    Per-annogroup classification of every scored block into a Rule 7 block-state.

    For each annogroup and each phylogenetic block parent::child:
      - if parent is NOT on the annogroup's eligible-for-scoring set, skip
      - otherwise classify by biological presence at parent and child:
          both present         -> block-state P (Inherited Presence, conservation)
          parent present only  -> block-state L (Loss event)
          both absent          -> block-state X (Inherited Loss, post-loss)

    Returns:
        list: Per-annogroup block-state count dictionaries.
    """
    logger.info( "Classifying per-annogroup block-states across all phylogenetic blocks (Rule 7)..." )

    annogroup_patterns = []

    for annogroup_id, origin_data in annogroups___origin_data.items():
        origin_child_clade_id_name = origin_data.get( 'origin_child_clade_id_name', 'NA' )
        species_count = len( annogroups___species_clade_id_names.get( annogroup_id, set() ) )

        conservation_events = 0
        loss_origin_events = 0
        continued_absence_events = 0

        # Iterate phylogenetic blocks (parent::child) and classify each block for
        # this annogroup under the Rule 7 block-state vocabulary:
        #   -A (Inherited Absence):   parent absent, child absent, pre-origin
        #   -O (Origin):              parent absent, child present, event
        #                             (emitted by Script 002, not scored here)
        #   -P (Inherited Presence):  parent present, child present, conservation
        #   -L (Loss):                parent present, child absent, event
        #   -X (Inherited Loss):      parent absent, child absent, post-loss
        for parent_clade_id_name, children in parents___children.items():
            parent_scoring_eligible = (
                clade_id_names___annogroups_eligible_for_scoring_at_this_clade.get(
                    parent_clade_id_name, set()
                )
            )
            parent_actually_present = (
                clade_id_names___annogroups_actually_present_at_this_clade.get(
                    parent_clade_id_name, set()
                )
            )

            if annogroup_id not in parent_scoring_eligible:
                continue

            parent_has_annogroup = annogroup_id in parent_actually_present

            for child_clade_id_name in children:
                child_scoring_eligible = (
                    clade_id_names___annogroups_eligible_for_scoring_at_this_clade.get(
                        child_clade_id_name, set()
                    )
                )
                child_actually_present = (
                    clade_id_names___annogroups_actually_present_at_this_clade.get(
                        child_clade_id_name, set()
                    )
                )

                if annogroup_id not in child_scoring_eligible:
                    logger.warning(
                        f"Annogroup {annogroup_id} eligible at parent {parent_clade_id_name} "
                        f"but not at child {child_clade_id_name} -- tree structure inconsistency?"
                    )
                    continue

                child_has_annogroup = annogroup_id in child_actually_present

                # Classify this (block, annogroup) into its block-state.
                if parent_has_annogroup and child_has_annogroup:
                    # -P: Inherited Presence (conservation)
                    conservation_events += 1
                elif parent_has_annogroup and not child_has_annogroup:
                    # -L: Loss event (first disappearance on this block)
                    loss_origin_events += 1
                elif not parent_has_annogroup and not child_has_annogroup:
                    # -X: Inherited Loss (post-loss continued absence)
                    continued_absence_events += 1
                else:
                    # parent absent AND child present with parent scoring-eligible.
                    # Would imply a second origin on the same descent line.
                    logger.warning(
                        f"Unexpected case for annogroup {annogroup_id}: "
                        f"absent in parent {parent_clade_id_name} but present in child {child_clade_id_name}."
                    )

        # Per-annogroup derived counts. No rates -- raw counts only.
        total_scored_blocks = conservation_events + loss_origin_events + continued_absence_events

        # Store pattern with counts and annotation data from Script 002.
        pattern = {
            'annogroup_id': annogroup_id,
            'phylogenetic_block': origin_data[ 'phylogenetic_block' ],
            'phylogenetic_block_state': origin_data[ 'phylogenetic_block_state' ],
            'phylogenetic_path': origin_data[ 'phylogenetic_path' ],
            'annogroup_subtype': origin_data[ 'annogroup_subtype' ],
            'species_count': species_count,
            'total_scored_blocks': total_scored_blocks,
            'conservation_events': conservation_events,
            'loss_origin_events': loss_origin_events,
            'continued_absence_events': continued_absence_events,
            'species_list': origin_data[ 'species_list' ],
        }

        annogroup_patterns.append( pattern )

    logger.info( f"Analyzed patterns for {len( annogroup_patterns )} annogroups" )
    logger.info( f"Total scored blocks across all annogroups: "
               f"{sum( p[ 'total_scored_blocks' ] for p in annogroup_patterns )}" )

    return annogroup_patterns


# ============================================================================
# SECTION 6: WRITE OUTPUTS
# ============================================================================

def write_block_statistics( block_statistics ):
    """Write per-block counts. Counts only -- no rates."""
    logger.info( f"Writing block statistics to: {output_block_statistics_file}" )

    with open( output_block_statistics_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Parent_Clade_ID_Name (parent clade of phylogenetic block as clade_id_name e.g. C069_Holozoa; terminal self-loops excluded)\t'
        output += 'Child_Clade_ID_Name (child clade of phylogenetic block as clade_id_name e.g. C002_Filozoa; terminal self-loops excluded)\t'
        output += 'Inherited_Count (count of annogroups biologically present at parent clade via its descendant species)\t'
        output += 'Conserved_Count (count of annogroups present at parent and also present at child -- block-state P)\t'
        output += 'Lost_Count (count of annogroups present at parent but absent at child -- block-state L)\n'
        output_file.write( output )

        for statistic in block_statistics:
            output = f"{statistic[ 'parent_clade_id_name' ]}\t{statistic[ 'child_clade_id_name' ]}\t"
            output += f"{statistic[ 'inherited_count' ]}\t{statistic[ 'conserved_count' ]}\t"
            output += f"{statistic[ 'lost_count' ]}\n"

            output_file.write( output )

    logger.info( f"Wrote {len( block_statistics )} block statistics" )


def write_annogroup_patterns( annogroup_patterns ):
    """Write per-annogroup block-state counts (Rule 7)."""
    logger.info( f"Writing per-annogroup block-state counts to: {output_annogroup_patterns_file}" )

    with open( output_annogroup_patterns_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Build single-row GIGANTIC_1 header. Per Rule 7, origin is a transition
        # block (state O). Counts only -- no rates.
        header_columns = [
            'Annogroup_ID (annogroup identifier)',
            'Origin_Phylogenetic_Block (phylogenetic block containing the origin transition format Parent_Clade_ID_Name::Child_Clade_ID_Name)',
            'Origin_Phylogenetic_Block_State (phylogenetic transition block for origin in five-state vocabulary format Parent_Clade_ID_Name::Child_Clade_ID_Name-O where O marks Origin; five states are A=Inherited Absence O=Origin P=Inherited Presence L=Loss X=Inherited Loss)',
            'Origin_Phylogenetic_Path (phylogenetic path from root to the child endpoint of the origin block comma delimited as clade_id_name values)',
            'Annogroup_Subtype (single or combo or zero)',
            'Species_Count (total unique species containing this annogroup across all genomes)',
            'Total_Scored_Blocks (count of phylogenetic blocks classified into block-states P L or X for this annogroup; equals P plus L plus X)',
            'Conservation_Events (count of phylogenetic blocks in block-state P where annogroup is present at both parent and child clades)',
            'Loss_Events (count of phylogenetic blocks in block-state L where annogroup is present at parent and absent at child)',
            'Continued_Absence_Events (count of phylogenetic blocks in block-state X where annogroup is absent at both parent and child after an upstream loss)',
            'Species_List (comma delimited list of all species containing this annogroup)'
        ]

        # Write single-row header
        csv_writer.writerow( header_columns )

        # Data (sorted by annogroup ID)
        sorted_patterns = sorted( annogroup_patterns, key = lambda x: x[ 'annogroup_id' ] )

        for pattern in sorted_patterns:
            output_row = [
                pattern[ 'annogroup_id' ],
                pattern[ 'phylogenetic_block' ],
                pattern[ 'phylogenetic_block_state' ],
                pattern[ 'phylogenetic_path' ],
                pattern[ 'annogroup_subtype' ],
                pattern[ 'species_count' ],
                pattern[ 'total_scored_blocks' ],
                pattern[ 'conservation_events' ],
                pattern[ 'loss_origin_events' ],
                pattern[ 'continued_absence_events' ],
                pattern[ 'species_list' ]
            ]

            csv_writer.writerow( output_row )

    logger.info( f"Wrote {len( annogroup_patterns )} annogroup patterns (11 columns)" )


def write_summary( block_statistics, annogroup_patterns ):
    """Write overall summary counts. Counts only -- no rates."""
    logger.info( f"Writing summary to: {output_summary_file}" )

    # Block-level totals (summed across all phylogenetic blocks in the structure).
    total_blocks = len( block_statistics )
    total_inherited = sum( statistic[ 'inherited_count' ] for statistic in block_statistics )
    total_conserved = sum( statistic[ 'conserved_count' ] for statistic in block_statistics )
    total_lost = sum( statistic[ 'lost_count' ] for statistic in block_statistics )

    # Annogroup-level totals (summed across all annogroups).
    total_annogroups = len( annogroup_patterns )
    total_conservation_events = sum( p[ 'conservation_events' ] for p in annogroup_patterns )
    total_loss_origin_events = sum( p[ 'loss_origin_events' ] for p in annogroup_patterns )
    total_continued_absence_events = sum( p[ 'continued_absence_events' ] for p in annogroup_patterns )
    total_scored_blocks = sum( p[ 'total_scored_blocks' ] for p in annogroup_patterns )

    with open( output_summary_file, 'w' ) as output_file:
        output = "Conservation and Loss Analysis Summary (Rule 7 block-state counts)\n"
        output += "=" * 80 + "\n\n"
        output += f"Structure: {TARGET_STRUCTURE}\n\n"
        output += "PHYLOGENETIC BLOCKS:\n"
        output += f"  Total blocks analyzed: {total_blocks}\n"
        output += f"  Total annogroups present at parent (summed over blocks): {total_inherited}\n"
        output += f"  Total conserved (block-state P) (summed over blocks): {total_conserved}\n"
        output += f"  Total lost (block-state L) (summed over blocks): {total_lost}\n\n"
        output += "ANNOGROUPS (Rule 7 per-annogroup block-state counts):\n"
        output += f"  Total annogroups analyzed: {total_annogroups}\n"
        output += f"  Total scored blocks (all annogroups): {total_scored_blocks}\n"
        output += f"  Conservation events (block-state P): {total_conservation_events}\n"
        output += f"  Loss events (block-state L): {total_loss_origin_events}\n"
        output += f"  Continued absence events (block-state X): {total_continued_absence_events}\n"
        output_file.write( output )

    logger.info( "Wrote summary counts" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function."""
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 003: CLASSIFY PHYLOGENETIC BLOCK-STATES PER ANNOGROUP (Rule 7)" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {Path( __file__ ).name}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( "" )

    # STEP 1: Load phylogenetic tree structure (all keyed by clade_id_name)
    logger.info( "STEP 1: Loading phylogenetic tree structure..." )
    clade_names___clade_id_names = load_clade_mappings()
    parents___children, children___parents = load_parent_child_relationships()
    species_clade_id_names___phylogenetic_paths = load_phylogenetic_paths()
    clade_id_names___descendant_species_clade_id_names = build_clade_descendants( species_clade_id_names___phylogenetic_paths )
    clade_id_names___descendant_clade_id_names = build_clade_to_all_descendant_clades_from_paths(
        species_clade_id_names___phylogenetic_paths
    )
    logger.info( "" )

    # STEP 2: Load annogroup data
    logger.info( "STEP 2: Loading annogroup data..." )
    annogroups___origin_data = load_annogroup_origins()
    annogroups___species_clade_id_names = load_annogroup_species( clade_names___clade_id_names )
    logger.info( "" )

    # STEP 3: Determine scoring-eligible and actually-present annogroups per clade.
    logger.info( "STEP 3: Determining scoring-eligible and actually-present annogroups per clade..." )
    clade_id_names___annogroups_eligible_for_scoring_at_this_clade, \
        clade_id_names___annogroups_actually_present_at_this_clade = build_clade_annogroups(
        annogroups___origin_data,
        annogroups___species_clade_id_names,
        clade_id_names___descendant_species_clade_id_names,
        clade_id_names___descendant_clade_id_names
    )
    logger.info( "" )

    # STEP 4: Classify each (block, annogroup) pair into a block-state and aggregate.
    logger.info( "STEP 4: Classifying block-states and aggregating per-block statistics..." )
    block_statistics = calculate_conservation_loss(
        parents___children,
        clade_id_names___annogroups_eligible_for_scoring_at_this_clade,
        clade_id_names___annogroups_actually_present_at_this_clade
    )
    logger.info( "" )

    # STEP 5: Aggregate per-annogroup block-state counts.
    logger.info( "STEP 5: Aggregating per-annogroup block-state counts..." )
    annogroup_patterns = analyze_annogroup_patterns(
        annogroups___origin_data,
        annogroups___species_clade_id_names,
        parents___children,
        clade_id_names___annogroups_eligible_for_scoring_at_this_clade,
        clade_id_names___annogroups_actually_present_at_this_clade
    )
    logger.info( "" )

    # STEP 6: Write outputs
    logger.info( "STEP 6: Writing outputs..." )
    write_block_statistics( block_statistics )
    write_annogroup_patterns( annogroup_patterns )
    write_summary( block_statistics, annogroup_patterns )
    logger.info( "" )

    logger.info( "=" * 80 )
    logger.info( "SCRIPT 003 COMPLETED SUCCESSFULLY" )
    logger.info( "=" * 80 )
    logger.info( f"All outputs written to: {output_directory}" )
    logger.info( "" )
    logger.info( "Output files:" )
    logger.info( f"  {output_block_statistics_file.name}" )
    logger.info( f"  {output_annogroup_patterns_file.name}" )
    logger.info( f"  {output_summary_file.name}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
