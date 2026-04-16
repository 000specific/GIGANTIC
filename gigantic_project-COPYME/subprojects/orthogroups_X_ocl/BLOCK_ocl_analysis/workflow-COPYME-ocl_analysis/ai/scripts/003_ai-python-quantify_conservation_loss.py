# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Classify phylogenetic block-states per orthogroup and aggregate per-block counts
# Human: Eric Edsinger

"""
OCL Pipeline Script 003: Classify Phylogenetic Block-States (Rule 7)

For each phylogenetic block (parent::child) and each orthogroup, classify the
(block, orthogroup) pair into one of the five Rule 7 block-states:

  -A (Inherited Absence):   parent absent, child absent, pre-origin
  -O (Origin):              parent absent, child present, event
                            (emitted by Script 002; not re-scored here)
  -P (Inherited Presence):  parent present, child present, conservation
  -L (Loss):                parent present, child absent, event
  -X (Inherited Loss):      parent absent, child absent, post-loss

Two per-clade sets are computed from the phylogenetic paths imported by
Script 001 (from trees_species):

- "Scoring-eligible at this clade": the clade is a descendant of (or equal to)
  the child endpoint of the orthogroup's origin transition block. Derived by
  a single pass over the phylogenetic paths — no sampling.
- "Actually present at this clade": at least one descendant species of the
  clade carries the orthogroup in its genome.

Terminal self-loops (parent_clade_id_name == child_clade_id_name at a tip)
are placeholder rows in the parent-child table and are excluded from block
iteration — they are not phylogenetic blocks.

Edge case: an orthogroup with origin block whose child endpoint is a tip has
no descendant blocks to score; its per-orthogroup counts are all zero.

Inputs (from previous scripts):
- 1-output: Clade mappings, parent-child relationships, phylogenetic paths,
  orthogroups with GIGANTIC identifiers
- 2-output: Orthogroup origins with phylogenetic block and path annotations

Outputs (to 3-output/):
- Per-block conservation/loss statistics
- Per-orthogroup conservation patterns with dual-metric loss tracking
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

# Increase CSV field size limit to handle large FASTA sequences
csv.field_size_limit( sys.maxsize )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'OCL Pipeline Script 003: Quantify orthogroup conservation and loss across phylogenetic blocks',
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

# FASTA embedding flag
INCLUDE_FASTA = config.get( 'include_fasta_in_output', False )

# Format structure ID
TARGET_STRUCTURE = f"structure_{args.structure_id}"

# Input directories
input_directory_001 = Path( args.output_dir ) / TARGET_STRUCTURE / '1-output'
input_directory_002 = Path( args.output_dir ) / TARGET_STRUCTURE / '2-output'

# Input files from Script 001
input_clade_mappings_file = input_directory_001 / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'
input_parent_child_file = input_directory_001 / f'1_ai-parent_child_table-{TARGET_STRUCTURE}.tsv'
input_phylogenetic_paths_file = input_directory_001 / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
input_orthogroups_file = input_directory_001 / '1_ai-orthogroups-gigantic_identifiers.tsv'

# Input files from Script 002
input_origins_file = input_directory_002 / '2_ai-orthogroup_origins.tsv'

# Output directory
output_directory = Path( args.output_dir ) / TARGET_STRUCTURE / '3-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_block_statistics_file = output_directory / '3_ai-conservation_loss-per_block.tsv'
output_orthogroup_patterns_file = output_directory / '3_ai-conservation_patterns-per_orthogroup.tsv'
output_summary_file = output_directory / '3_ai-conservation_loss-summary.tsv'

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

    Builds a reverse map from bare clade_name -> clade_id_name (CXXX_Name),
    used to convert orthogroup species names (bare Genus_species) to their
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

    Args:
        species_clade_id_names___phylogenetic_paths:
            { species_clade_id_name: [ clade_id_name, ..., species_clade_id_name ] }

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
    via Script 001. Each tip's root-to-tip path is a sequence
    [ p0, p1, ..., pn ] where p0 is the root clade and pn is the tip. Every
    clade pi in that path has, within this path, the descendants
    { p_i, p_{i+1}, ..., p_n }. Unioning across all tip paths yields complete
    descendant sets for every clade in the tree.

    No new tree walk is needed — the paths already encode the ancestor/descendant
    relationships of the species tree structure.

    Args:
        species_clade_id_names___phylogenetic_paths:
            { species_clade_id_name: [ clade_id_name, ..., species_clade_id_name ] }

    Returns:
        dict: { clade_id_name: set( clade_id_name ) } — every clade maps to the
        set containing itself and every descendant clade.
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
# SECTION 2: LOAD ORTHOGROUP DATA
# ============================================================================

def extract_species_from_gigantic_id( gigantic_id ):
    """
    Extract species name from GIGANTIC identifier.

    GIGANTIC ID format:
    g_XXX-t_XXX-p_XXX-n_Kingdom_Phylum_Class_Order_Family_Genus_species...

    Returns:
        str or None: Species name (Genus_species) or None if extraction fails
    """
    if '-n_' not in gigantic_id:
        return None

    phyloname = gigantic_id.split( '-n_' )[ 1 ]
    parts_phyloname = phyloname.split( '_' )

    # Species name = Genus_species starting at position [5]
    if len( parts_phyloname ) >= 7:
        species_name = '_'.join( parts_phyloname[ 5: ] )
        return species_name
    else:
        return None


def load_orthogroup_origins():
    """
    Load orthogroup origin data from Script 002 output.

    Per Rule 7, origin is a phylogenetic transition block identified by both
    `Origin_Phylogenetic_Block` (parent::child) and `Origin_Phylogenetic_Block_State`
    (parent::child-O). The child endpoint of the origin block — useful for
    ancestor-descendant lookups — is derived here by splitting the block
    identifier on `::`.

    Returns:
        dict: { orthogroup_id: {
            'origin_child_clade_id_name': str,
            'phylogenetic_block': str,
            'phylogenetic_block_state': str,
            'phylogenetic_path': str,
            'species_list': str,
            'sequence_ids': str,
            'sequences_fasta': str or ''
        } }
    """
    logger.info( f"Loading orthogroup origins from: {input_origins_file}" )

    if not input_origins_file.exists():
        logger.error( f"CRITICAL ERROR: Orthogroup origins file not found!" )
        logger.error( f"Expected: {input_origins_file}" )
        sys.exit( 1 )

    orthogroups___origin_data = {}

    with open( input_origins_file, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Orthogroup_ID	Origin_Phylogenetic_Block	Origin_Phylogenetic_Block_State	Origin_Phylogenetic_Path	Shared_Clade_ID_Names	Species_Count	Sequence_Count	Species_List	Sequence_IDs [	Sequences_FASTA]
        # OG0000001	C069_Holozoa::C002_Filozoa	C069_Holozoa::C002_Filozoa-O	C068_Basal,C069_Holozoa,C002_Filozoa	C068_Basal,C069_Holozoa,C002_Filozoa	42	120	Homo_sapiens,...	g_001-...
        # Per Rule 7, origin is a phylogenetic transition block (state O). It is
        # fully specified by columns 1 and 2 below — the block `parent::child`
        # and the block-state `parent::child-O`. The child clade (origin clade
        # in the naming-convention sense) is extractable from the block string
        # by splitting on `::` and taking the second half; no separate column
        # is emitted for it.
        header_row = next( csv_reader )  # Skip single-row header

        column_count = len( header_row )
        has_fasta_column = column_count >= 10

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            orthogroup_id = parts[ 0 ]
            phylogenetic_block = parts[ 1 ]
            phylogenetic_block_state = parts[ 2 ]
            phylogenetic_path = parts[ 3 ]
            species_list = parts[ 7 ]
            sequence_ids = parts[ 8 ]
            sequences_fasta = parts[ 9 ] if has_fasta_column and len( parts ) > 9 else ''

            # Derive the child clade of the origin block (the "origin clade"
            # in naming-convention shorthand) from the block identifier.
            if phylogenetic_block != 'NA' and '::' in phylogenetic_block:
                origin_child_clade_id_name = phylogenetic_block.split( '::', 1 )[ 1 ]
            else:
                origin_child_clade_id_name = 'NA'

            orthogroups___origin_data[ orthogroup_id ] = {
                'origin_child_clade_id_name': origin_child_clade_id_name,
                'phylogenetic_block': phylogenetic_block,
                'phylogenetic_block_state': phylogenetic_block_state,
                'phylogenetic_path': phylogenetic_path,
                'species_list': species_list,
                'sequence_ids': sequence_ids,
                'sequences_fasta': sequences_fasta
            }

    logger.info( f"Loaded origin data for {len( orthogroups___origin_data )} orthogroups" )
    logger.info( f"FASTA data {'detected' if has_fasta_column else 'not present'} in Script 002 output" )

    return orthogroups___origin_data


def load_orthogroup_species( clade_names___clade_id_names ):
    """
    Load species composition for each orthogroup from Script 001 output,
    converting bare Genus_species names to species_clade_id_name form via
    the clade_mappings reverse index.

    Species in orthogroups but absent from the clade_mappings for this
    structure are skipped (this can legitimately happen for orthogroups that
    include species outside the structure's species set).

    Args:
        clade_names___clade_id_names: { clade_name: clade_id_name }

    Returns:
        dict: { orthogroup_id: set( species_clade_id_name ) }
    """
    logger.info( f"Loading orthogroup species from: {input_orthogroups_file}" )

    if not input_orthogroups_file.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found!" )
        logger.error( f"Expected: {input_orthogroups_file}" )
        sys.exit( 1 )

    orthogroups___species_clade_id_names = {}
    missing_species_names = set()

    with open( input_orthogroups_file, 'r' ) as input_file:
        # Orthogroup_ID (orthogroup identifier from clustering tool)	Sequence_Count (total count of sequences in orthogroup)	GIGANTIC_IDs (comma delimited list of GIGANTIC identifiers)	Unmapped_Short_IDs (comma delimited list of short IDs that could not be mapped)
        # OG0000001	45	g_001-t_001-p_001-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens,...
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            orthogroup_id = parts[ 0 ]
            gigantic_ids_string = parts[ 2 ]

            gigantic_ids = gigantic_ids_string.split( ',' )

            species_clade_id_names_set = set()
            for gigantic_id in gigantic_ids:
                gigantic_id = gigantic_id.strip()
                if not gigantic_id:
                    continue
                species_name = extract_species_from_gigantic_id( gigantic_id )
                if not species_name:
                    continue
                species_clade_id_name = clade_names___clade_id_names.get( species_name )
                if species_clade_id_name is None:
                    missing_species_names.add( species_name )
                    continue
                species_clade_id_names_set.add( species_clade_id_name )

            orthogroups___species_clade_id_names[ orthogroup_id ] = species_clade_id_names_set

    logger.info( f"Loaded species_clade_id_names for {len( orthogroups___species_clade_id_names )} orthogroups" )
    if missing_species_names:
        logger.info( f"Skipped {len( missing_species_names )} species not in this structure's clade_mappings" )

    return orthogroups___species_clade_id_names


# ============================================================================
# SECTION 3: DETERMINE ORTHOGROUPS PRESENT IN EACH CLADE
# ============================================================================

def build_clade_orthogroups( orthogroups___origin_data, orthogroups___species_clade_id_names,
                             clade_id_names___descendant_species_clade_id_names,
                             clade_id_names___descendant_clade_id_names ):
    """
    For each clade C, compute two per-clade orthogroup sets needed for scoring
    phylogenetic blocks under Rule 7:

    1. orthogroups for which C is a descendant of (or equal to) the child
       endpoint of the origin transition block — i.e. orthogroups whose origin
       transition block sits on the root-to-C lineage or at C itself. These
       are the orthogroups eligible for P/L/X block-state scoring when C is a
       parent in a block. Blocks where C is a parent but the orthogroup fails
       this test are state-A blocks (pre-origin) and must not be scored.

    2. orthogroups actually carried by at least one descendant species of C
       (biological presence, distinct from the topological eligibility above).

    The eligibility test (1) uses pre-computed ancestor-descendant relationships
    from the parent-child graph. It replaces the earlier sampling-based
    "origin in a sample descendant species' root-to-tip path" test, which gave
    wrong (sampling-dependent) answers whenever the child endpoint of the
    origin transition block happened to be a tip — most singleton orthogroups.

    Args:
        orthogroups___origin_data: {
            orthogroup_id: { 'origin_child_clade_id_name': str, ... }
        }
        orthogroups___species_clade_id_names: {
            orthogroup_id: set( species_clade_id_name )
        }
        clade_id_names___descendant_species_clade_id_names: {
            clade_id_name: set( descendant species_clade_id_name )
        }
        clade_id_names___descendant_clade_id_names: {
            clade_id_name: set( every descendant clade_id_name, including self )
        }

    Returns:
        tuple: (
            clade_id_names___orthogroups_eligible_for_scoring_at_this_clade,
            clade_id_names___orthogroups_actually_present_at_this_clade
        )
    """
    logger.info( "=" * 80 )
    logger.info( "DETERMINING ORTHOGROUP-CLADE RELATIONSHIPS (Rule 7):" )
    logger.info( "  1. SCORING-ELIGIBLE = clade is a descendant of (or equal to)" )
    logger.info( "     the child endpoint of the orthogroup's origin transition block" )
    logger.info( "  2. ACTUALLY PRESENT = at least one descendant species of the clade" )
    logger.info( "     carries the orthogroup" )
    logger.info( "=" * 80 )

    clade_id_names___orthogroups_eligible_for_scoring_at_this_clade = defaultdict( set )
    clade_id_names___orthogroups_actually_present_at_this_clade = defaultdict( set )

    for orthogroup_id, orthogroup_species_clade_id_names in orthogroups___species_clade_id_names.items():
        origin_data = orthogroups___origin_data.get( orthogroup_id )
        if not origin_data:
            continue

        origin_child_clade_id_name = origin_data.get( 'origin_child_clade_id_name', 'NA' )
        if not origin_child_clade_id_name or origin_child_clade_id_name == 'NA':
            continue

        # All clades that sit on or below the child endpoint of the origin block.
        # The child endpoint itself is included (a clade is its own descendant
        # under this convention). These are exactly the clades for which the
        # orthogroup is eligible for P/L/X scoring.
        eligible_clade_id_names = clade_id_names___descendant_clade_id_names.get(
            origin_child_clade_id_name, set()
        )

        for clade_id_name in eligible_clade_id_names:
            clade_id_names___orthogroups_eligible_for_scoring_at_this_clade[ clade_id_name ].add( orthogroup_id )

            descendant_species_clade_id_names = clade_id_names___descendant_species_clade_id_names.get(
                clade_id_name, set()
            )
            if orthogroup_species_clade_id_names.intersection( descendant_species_clade_id_names ):
                clade_id_names___orthogroups_actually_present_at_this_clade[ clade_id_name ].add( orthogroup_id )

    logger.info(
        f"Scoring-eligible orthogroups present at: "
        f"{len( clade_id_names___orthogroups_eligible_for_scoring_at_this_clade )} clades"
    )
    logger.info(
        f"Orthogroups actually present at: "
        f"{len( clade_id_names___orthogroups_actually_present_at_this_clade )} clades"
    )
    logger.info( "=" * 80 )

    return (
        clade_id_names___orthogroups_eligible_for_scoring_at_this_clade,
        clade_id_names___orthogroups_actually_present_at_this_clade,
    )


# ============================================================================
# SECTION 4: CALCULATE CONSERVATION AND LOSS PER BLOCK
# ============================================================================

def calculate_conservation_loss(
    parents___children,
    clade_id_names___orthogroups_eligible_for_scoring_at_this_clade,
    clade_id_names___orthogroups_actually_present_at_this_clade,
):
    """
    Compute per-block statistics for each phylogenetic block (parent::child).

    For each block, counts orthogroups in three categories using the biological
    "actually present" sets (not the topological eligibility sets, which are
    needed only for per-orthogroup block-state classification):

      - inherited_count: orthogroups biologically present at the parent clade.
        An orthogroup can be biologically present at the parent only if its
        origin transition block sits on the parent's descent line (Rule 7), so
        this set is naturally scoped to Rule-7-eligible orthogroups at parent.
      - conserved_count: inherited orthogroups that are also present at child
        (equivalent to the number of orthogroups on this block in block-state P).
      - lost_count: inherited orthogroups that are absent at child
        (equivalent to the number of orthogroups on this block in block-state L).

    Args:
        parents___children: { parent_clade_id_name: [ child_clade_id_name, ... ] }
        clade_id_names___orthogroups_eligible_for_scoring_at_this_clade:
            { clade_id_name: set( orthogroup_id ) } — passed for API symmetry
            with `analyze_orthogroup_patterns`; not directly needed here because
            biological presence already implies eligibility.
        clade_id_names___orthogroups_actually_present_at_this_clade:
            { clade_id_name: set( orthogroup_id ) }

    Returns:
        list: Per-block statistics dictionaries.
    """
    logger.info( "Calculating conservation and loss per phylogenetic block (Rule 7)..." )

    block_statistics = []

    for parent_clade_id_name, children in parents___children.items():
        orthogroups_actually_present_at_parent = (
            clade_id_names___orthogroups_actually_present_at_this_clade.get(
                parent_clade_id_name, set()
            )
        )

        for child_clade_id_name in children:
            orthogroups_actually_present_at_child = (
                clade_id_names___orthogroups_actually_present_at_this_clade.get(
                    child_clade_id_name, set()
                )
            )

            inherited = orthogroups_actually_present_at_parent
            conserved = inherited.intersection( orthogroups_actually_present_at_child )
            lost = inherited - orthogroups_actually_present_at_child

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
# SECTION 5: ANALYZE CONSERVATION PATTERNS PER ORTHOGROUP
# ============================================================================

def analyze_orthogroup_patterns(
    orthogroups___origin_data,
    orthogroups___species_clade_id_names,
    parents___children,
    clade_id_names___orthogroups_eligible_for_scoring_at_this_clade,
    clade_id_names___orthogroups_actually_present_at_this_clade,
):
    """
    Per-orthogroup classification of every scored block into a Rule 7 block-state.

    For each orthogroup and each phylogenetic block `parent::child`:
      - if parent is NOT on the orthogroup's eligible-for-scoring set, the block
        is state A (pre-origin) or lies in a sibling subtree — it is skipped
        and contributes nothing.
      - otherwise classify by biological presence at parent and child:
          both present         → block-state P (Inherited Presence, conservation)
          parent present only  → block-state L (Loss event)
          both absent          → block-state X (Inherited Loss, post-loss)
        The O state (origin) is produced by Script 002, not here.

    Aggregates per orthogroup:
      - total_scored_blocks: P + L + X count (all scored blocks)
      - conservation_events:    P count
      - loss_origin_events:     L count
      - continued_absence_events: X count
      - loss_coverage_events:   L + X count

    Edge case: zero scored blocks (e.g. singleton whose origin block's child is
    a tip) yields all zero counts, since the orthogroup has no descendants
    of its origin's child endpoint to score blocks through.

    Args:
        orthogroups___origin_data: {
            orthogroup_id: { 'origin_child_clade_id_name': str, ... }
        }
        orthogroups___species_clade_id_names: {
            orthogroup_id: set( species_clade_id_name )
        }
        parents___children: { parent_clade_id_name: [ child_clade_id_name, ... ] }
        clade_id_names___orthogroups_eligible_for_scoring_at_this_clade:
            { clade_id_name: set( orthogroup_id ) }
        clade_id_names___orthogroups_actually_present_at_this_clade:
            { clade_id_name: set( orthogroup_id ) }

    Returns:
        list: Per-orthogroup block-state count dictionaries.
    """
    logger.info( "Classifying per-orthogroup block-states across all phylogenetic blocks (Rule 7)..." )

    orthogroup_patterns = []

    for orthogroup_id, origin_data in orthogroups___origin_data.items():
        origin_child_clade_id_name = origin_data.get( 'origin_child_clade_id_name', 'NA' )
        species_count = len( orthogroups___species_clade_id_names.get( orthogroup_id, set() ) )

        conservation_events = 0
        loss_origin_events = 0
        continued_absence_events = 0

        # Iterate phylogenetic blocks (parent::child) and classify each block for
        # this orthogroup under the Rule 7 block-state vocabulary:
        #   -A (Inherited Absence):   parent absent, child absent, pre-origin
        #   -O (Origin):              parent absent, child present, event
        #                             (emitted by Script 002, not scored here)
        #   -P (Inherited Presence):  parent present, child present, conservation
        #   -L (Loss):                parent present, child absent, event
        #   -X (Inherited Loss):      parent absent, child absent, post-loss
        #
        # Scoring gate: the block is only classified if the parent clade sits on
        # or below the child endpoint of this orthogroup's origin transition
        # block (direct tree-structural descendant test). Blocks whose parent
        # is NOT a descendant of the origin block's child endpoint are state A
        # or in a sibling subtree and are correctly skipped.
        for parent_clade_id_name, children in parents___children.items():
            parent_scoring_eligible = (
                clade_id_names___orthogroups_eligible_for_scoring_at_this_clade.get(
                    parent_clade_id_name, set()
                )
            )
            parent_actually_present = (
                clade_id_names___orthogroups_actually_present_at_this_clade.get(
                    parent_clade_id_name, set()
                )
            )

            if orthogroup_id not in parent_scoring_eligible:
                continue

            parent_has_orthogroup = orthogroup_id in parent_actually_present

            for child_clade_id_name in children:
                child_scoring_eligible = (
                    clade_id_names___orthogroups_eligible_for_scoring_at_this_clade.get(
                        child_clade_id_name, set()
                    )
                )
                child_actually_present = (
                    clade_id_names___orthogroups_actually_present_at_this_clade.get(
                        child_clade_id_name, set()
                    )
                )

                if orthogroup_id not in child_scoring_eligible:
                    logger.warning(
                        f"Orthogroup {orthogroup_id} eligible at parent {parent_clade_id_name} "
                        f"but not at child {child_clade_id_name} — tree structure inconsistency?"
                    )
                    continue

                child_has_orthogroup = orthogroup_id in child_actually_present

                # Classify this (block, orthogroup) into its block-state.
                if parent_has_orthogroup and child_has_orthogroup:
                    # -P: Inherited Presence (conservation)
                    conservation_events += 1
                elif parent_has_orthogroup and not child_has_orthogroup:
                    # -L: Loss event (first disappearance on this block)
                    loss_origin_events += 1
                elif not parent_has_orthogroup and not child_has_orthogroup:
                    # -X: Inherited Loss (post-loss continued absence).
                    # Parent is scoring-eligible (descendant of origin's child)
                    # but the orthogroup is not biologically present at parent
                    # → the orthogroup was lost on an earlier block in this
                    # clade's ancestry; the absence continues at this block.
                    continued_absence_events += 1
                else:
                    # parent absent AND child present with parent scoring-eligible.
                    # Would imply a second origin on the same descent line, which
                    # violates Dollo-parsimonious origin assignment.
                    logger.warning(
                        f"Unexpected case for orthogroup {orthogroup_id}: "
                        f"absent in parent {parent_clade_id_name} but present in child {child_clade_id_name}."
                    )

        # Per-orthogroup derived counts. No rates — raw counts only.
        total_scored_blocks = conservation_events + loss_origin_events + continued_absence_events

        # Store pattern with counts and annotation data from Script 002.
        # phylogenetic_block (parent::child) is the tree-structural identifier of
        # the origin transition block — the block on which this orthogroup
        # originates. phylogenetic_block_state (parent::child-O) is the same
        # block tagged with the Rule 7 block-state letter code O (Origin). Per
        # Rule 7 the "origin clade" is not a separate field; the child endpoint
        # of the origin transition block is in the block identifier.
        pattern = {
            'orthogroup_id': orthogroup_id,
            'phylogenetic_block': origin_data[ 'phylogenetic_block' ],
            'phylogenetic_block_state': origin_data[ 'phylogenetic_block_state' ],
            'phylogenetic_path': origin_data[ 'phylogenetic_path' ],
            'species_count': species_count,
            'total_scored_blocks': total_scored_blocks,
            'conservation_events': conservation_events,
            'loss_origin_events': loss_origin_events,
            'continued_absence_events': continued_absence_events,
            'species_list': origin_data[ 'species_list' ],
            'sequence_ids': origin_data[ 'sequence_ids' ],
            'sequences_fasta': origin_data[ 'sequences_fasta' ]
        }

        orthogroup_patterns.append( pattern )

    logger.info( f"Analyzed patterns for {len( orthogroup_patterns )} orthogroups" )
    logger.info( f"Total scored blocks across all orthogroups: "
               f"{sum( p[ 'total_scored_blocks' ] for p in orthogroup_patterns )}" )

    return orthogroup_patterns


# ============================================================================
# SECTION 6: WRITE OUTPUTS
# ============================================================================

def write_block_statistics( block_statistics ):
    """Write per-block counts. Counts only — no rates."""
    logger.info( f"Writing block statistics to: {output_block_statistics_file}" )

    with open( output_block_statistics_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Parent_Clade_ID_Name (parent clade of phylogenetic block as clade_id_name e.g. C069_Holozoa; terminal self-loops excluded)\t'
        output += 'Child_Clade_ID_Name (child clade of phylogenetic block as clade_id_name e.g. C002_Filozoa; terminal self-loops excluded)\t'
        output += 'Inherited_Count (count of orthogroups biologically present at parent clade via its descendant species)\t'
        output += 'Conserved_Count (count of orthogroups present at parent and also present at child — block-state P)\t'
        output += 'Lost_Count (count of orthogroups present at parent but absent at child — block-state L)\n'
        output_file.write( output )

        for statistic in block_statistics:
            output = f"{statistic[ 'parent_clade_id_name' ]}\t{statistic[ 'child_clade_id_name' ]}\t"
            output += f"{statistic[ 'inherited_count' ]}\t{statistic[ 'conserved_count' ]}\t"
            output += f"{statistic[ 'lost_count' ]}\n"

            output_file.write( output )

    logger.info( f"Wrote {len( block_statistics )} block statistics" )


def write_orthogroup_patterns( orthogroup_patterns ):
    """Write per-orthogroup block-state counts (Rule 7)."""
    logger.info( f"Writing per-orthogroup block-state counts to: {output_orthogroup_patterns_file}" )

    with open( output_orthogroup_patterns_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Build single-row GIGANTIC_1 header. Per Rule 7, origin is a transition
        # block (state O); the "origin clade" is not a separate field. Counts
        # only — no rates.
        header_columns = [
            'Orthogroup_ID (orthogroup identifier)',
            'Origin_Phylogenetic_Block (phylogenetic block containing the origin transition format Parent_Clade_ID_Name::Child_Clade_ID_Name)',
            'Origin_Phylogenetic_Block_State (phylogenetic transition block for origin in five-state vocabulary format Parent_Clade_ID_Name::Child_Clade_ID_Name-O where O marks Origin; five states are A=Inherited Absence O=Origin P=Inherited Presence L=Loss X=Inherited Loss)',
            'Origin_Phylogenetic_Path (phylogenetic path from root to the child endpoint of the origin block comma delimited as clade_id_name values)',
            'Species_Count (total unique species containing this orthogroup across all genomes)',
            'Total_Scored_Blocks (count of phylogenetic blocks classified into block-states P L or X for this orthogroup; equals P plus L plus X)',
            'Conservation_Events (count of phylogenetic blocks in block-state P where orthogroup is present at both parent and child clades)',
            'Loss_Events (count of phylogenetic blocks in block-state L where orthogroup is present at parent and absent at child)',
            'Continued_Absence_Events (count of phylogenetic blocks in block-state X where orthogroup is absent at both parent and child after an upstream loss)',
            'Species_List (comma delimited list of all species containing this orthogroup)',
            'Sequence_IDs (comma delimited list of GIGANTIC sequence identifiers in this orthogroup)'
        ]

        if INCLUDE_FASTA:
            header_columns.append(
                'Sequences_FASTA (FASTA formatted sequences for this orthogroup with actual newlines within cell)'
            )

        # Write single-row header
        csv_writer.writerow( header_columns )

        # Data (sorted by orthogroup ID)
        sorted_patterns = sorted( orthogroup_patterns, key = lambda x: x[ 'orthogroup_id' ] )

        for pattern in sorted_patterns:
            output_row = [
                pattern[ 'orthogroup_id' ],
                pattern[ 'phylogenetic_block' ],
                pattern[ 'phylogenetic_block_state' ],
                pattern[ 'phylogenetic_path' ],
                pattern[ 'species_count' ],
                pattern[ 'total_scored_blocks' ],
                pattern[ 'conservation_events' ],
                pattern[ 'loss_origin_events' ],
                pattern[ 'continued_absence_events' ],
                pattern[ 'species_list' ],
                pattern[ 'sequence_ids' ]
            ]

            if INCLUDE_FASTA:
                output_row.append( pattern[ 'sequences_fasta' ] )

            csv_writer.writerow( output_row )

    column_count = 12 if INCLUDE_FASTA else 11
    logger.info( f"Wrote {len( orthogroup_patterns )} orthogroup patterns ({column_count} columns)" )


def write_summary( block_statistics, orthogroup_patterns ):
    """Write overall summary counts. Counts only — no rates."""
    logger.info( f"Writing summary to: {output_summary_file}" )

    # Block-level totals (summed across all phylogenetic blocks in the structure).
    total_blocks = len( block_statistics )
    total_inherited = sum( statistic[ 'inherited_count' ] for statistic in block_statistics )
    total_conserved = sum( statistic[ 'conserved_count' ] for statistic in block_statistics )
    total_lost = sum( statistic[ 'lost_count' ] for statistic in block_statistics )

    # Orthogroup-level totals (summed across all orthogroups).
    total_orthogroups = len( orthogroup_patterns )
    total_conservation_events = sum( p[ 'conservation_events' ] for p in orthogroup_patterns )
    total_loss_origin_events = sum( p[ 'loss_origin_events' ] for p in orthogroup_patterns )
    total_continued_absence_events = sum( p[ 'continued_absence_events' ] for p in orthogroup_patterns )
    total_scored_blocks = sum( p[ 'total_scored_blocks' ] for p in orthogroup_patterns )

    with open( output_summary_file, 'w' ) as output_file:
        output = "Conservation and Loss Analysis Summary (Rule 7 block-state counts)\n"
        output += "=" * 80 + "\n\n"
        output += f"Structure: {TARGET_STRUCTURE}\n\n"
        output += "PHYLOGENETIC BLOCKS:\n"
        output += f"  Total blocks analyzed: {total_blocks}\n"
        output += f"  Total orthogroups present at parent (summed over blocks): {total_inherited}\n"
        output += f"  Total conserved (block-state P) (summed over blocks): {total_conserved}\n"
        output += f"  Total lost (block-state L) (summed over blocks): {total_lost}\n\n"
        output += "ORTHOGROUPS (Rule 7 per-orthogroup block-state counts):\n"
        output += f"  Total orthogroups analyzed: {total_orthogroups}\n"
        output += f"  Total scored blocks (all orthogroups): {total_scored_blocks}\n"
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
    logger.info( "SCRIPT 003: CLASSIFY PHYLOGENETIC BLOCK-STATES PER ORTHOGROUP (Rule 7)" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {Path( __file__ ).name}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"FASTA embedding: {'enabled' if INCLUDE_FASTA else 'disabled'}" )
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

    # STEP 2: Load orthogroup data
    logger.info( "STEP 2: Loading orthogroup data..." )
    orthogroups___origin_data = load_orthogroup_origins()
    orthogroups___species_clade_id_names = load_orthogroup_species( clade_names___clade_id_names )
    logger.info( "" )

    # STEP 3: Determine scoring-eligible and actually-present orthogroups per clade.
    # "Scoring-eligible" means the clade is a descendant of (or equal to) the child
    # endpoint of the orthogroup's origin transition block — a direct tree-structural
    # check under Rule 7, replacing the earlier sampling-based path test.
    logger.info( "STEP 3: Determining scoring-eligible and actually-present orthogroups per clade..." )
    clade_id_names___orthogroups_eligible_for_scoring_at_this_clade, \
        clade_id_names___orthogroups_actually_present_at_this_clade = build_clade_orthogroups(
        orthogroups___origin_data,
        orthogroups___species_clade_id_names,
        clade_id_names___descendant_species_clade_id_names,
        clade_id_names___descendant_clade_id_names
    )
    logger.info( "" )

    # STEP 4: Classify each (block, orthogroup) pair into a block-state and aggregate.
    logger.info( "STEP 4: Classifying block-states and aggregating per-block statistics..." )
    block_statistics = calculate_conservation_loss(
        parents___children,
        clade_id_names___orthogroups_eligible_for_scoring_at_this_clade,
        clade_id_names___orthogroups_actually_present_at_this_clade
    )
    logger.info( "" )

    # STEP 5: Aggregate per-orthogroup block-state counts.
    logger.info( "STEP 5: Aggregating per-orthogroup block-state counts..." )
    orthogroup_patterns = analyze_orthogroup_patterns(
        orthogroups___origin_data,
        orthogroups___species_clade_id_names,
        parents___children,
        clade_id_names___orthogroups_eligible_for_scoring_at_this_clade,
        clade_id_names___orthogroups_actually_present_at_this_clade
    )
    logger.info( "" )

    # STEP 6: Write outputs
    logger.info( "STEP 6: Writing outputs..." )
    write_block_statistics( block_statistics )
    write_orthogroup_patterns( orthogroup_patterns )
    write_summary( block_statistics, orthogroup_patterns )
    logger.info( "" )

    logger.info( "=" * 80 )
    logger.info( "SCRIPT 003 COMPLETED SUCCESSFULLY" )
    logger.info( "=" * 80 )
    logger.info( f"All outputs written to: {output_directory}" )
    logger.info( "" )
    logger.info( "Output files:" )
    logger.info( f"  {output_block_statistics_file.name}" )
    logger.info( f"  {output_orthogroup_patterns_file.name}" )
    logger.info( f"  {output_summary_file.name}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
