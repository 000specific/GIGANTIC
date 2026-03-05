# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Quantify annogroup conservation and loss with TEMPLATE_03 dual-metric tracking
# Human: Eric Edsinger

"""
OCL Pipeline Script 003: Quantify Conservation and Loss (TEMPLATE_03)

TEMPLATE_03 dual-metric tracking separates "phylogenetically inherited" from
"actually present in species" to distinguish loss-at-origin from continued absence.

For each phylogenetic block (parent to child transition):
- Identifies annogroups INHERITED by clades (origin in phylogenetic path)
- Identifies annogroups PRESENT in clades (at least one descendant species has it)
- Classifies transitions into 4 event types:
  * Conservation: inherited, present in parent, present in child
  * Loss at Origin: inherited, present in parent, absent in child
  * Continued Absence: inherited, absent in parent, absent in child
  * Loss Coverage: loss at origin + continued absence

Terminal self-loops (where parent == child) are excluded as they are not
biologically meaningful transitions.

Edge cases handled explicitly:
- Zero inherited transitions: rates set to 0.0 (not division by zero)
- Annogroups not inherited by parent: skipped (not counted)

Inputs (from previous scripts):
- 1-output: Clade mappings, parent-child relationships, phylogenetic paths,
  annogroup map with species composition
- 2-output: Annogroup origins with phylogenetic block and path annotations

Outputs (to 3-output/):
- Per-block conservation/loss statistics
- Per-annogroup conservation patterns with dual-metric loss tracking
- Conservation/loss summary

Usage:
    python 003_ai-python-quantify_conservation_loss.py --structure_id 001 --config ../../START_HERE-user_config.yaml --output_dir OUTPUT_pipeline
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
        default = None,
        help = 'Base output directory (overrides config if provided)'
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
ANNOTATION_DATABASE = config[ 'annotation_database' ]

# Input directories
config_directory = config_path.parent

if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]

input_directory_001 = output_base_directory / TARGET_STRUCTURE / '1-output'
input_directory_002 = output_base_directory / TARGET_STRUCTURE / '2-output'

# Input files from Script 001
input_clade_mappings_file = input_directory_001 / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'
input_parent_child_file = input_directory_001 / f'1_ai-parent_child_table-{TARGET_STRUCTURE}.tsv'
input_phylogenetic_paths_file = input_directory_001 / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
input_annogroup_map_file = input_directory_001 / '1_ai-annogroup_map.tsv'

# Input files from Script 002
input_origins_file = input_directory_002 / '2_ai-annogroup_origins.tsv'

# Output directory
output_directory = output_base_directory / TARGET_STRUCTURE / '3-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_block_statistics_file = output_directory / '3_ai-conservation_loss-per_block.tsv'
output_annogroup_patterns_file = output_directory / '3_ai-conservation_patterns-per_annogroup.tsv'
output_summary_file = output_directory / '3_ai-conservation_loss-summary.tsv'

# Log file
log_directory = output_base_directory / TARGET_STRUCTURE / 'logs'
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

def load_clade_id_mapping():
    """
    Load clade ID to name mapping from Script 001 output.

    Returns:
        dict: { clade_id: clade_name }
    """
    logger.info( f"Loading clade ID mappings from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mapping file not found!" )
        logger.error( f"Expected: {input_clade_mappings_file}" )
        sys.exit( 1 )

    clade_ids___clade_names = {}

    with open( input_clade_mappings_file, 'r' ) as input_file:
        # Clade_ID (clade identifier from trees_species)	Clade_Name (clade name from phylogenetic tree)
        # C001	Fonticula_alba
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            clade_id = parts[ 0 ]
            clade_name = parts[ 1 ]

            clade_ids___clade_names[ clade_id ] = clade_name

    logger.info( f"Loaded {len( clade_ids___clade_names )} clade ID mappings" )

    return clade_ids___clade_names


def load_parent_child_relationships( clade_ids___clade_names ):
    """
    Load parent-child relationships from Script 001 output.

    Excludes terminal self-loops (where parent_name == child_name) as these
    are not biologically meaningful transitions for conservation/loss analysis.

    Args:
        clade_ids___clade_names: { clade_id: clade_name }

    Returns:
        tuple: ( parents___children, children___parents )
            - parents___children: { parent_name: [ child1_name, child2_name ] }
            - children___parents: { child_name: parent_name }
    """
    logger.info( f"Loading parent-child relationships from: {input_parent_child_file}" )

    if not input_parent_child_file.exists():
        logger.error( f"CRITICAL ERROR: Parent-child file not found!" )
        logger.error( f"Expected: {input_parent_child_file}" )
        sys.exit( 1 )

    parents___children = {}
    children___parents = {}
    self_loop_count = 0

    with open( input_parent_child_file, 'r' ) as input_file:
        # Parent_ID (parent clade identifier)	Parent_Name (parent clade name)	Child_ID (child clade identifier)	Child_Name (child clade name)
        # C068	Basal	C069	Holomycota
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            parent_name = parts[ 1 ]
            child_name = parts[ 3 ]

            # Skip self-loops (terminal nodes) - not biologically meaningful transitions
            if parent_name == child_name:
                self_loop_count += 1
                continue

            # Build parent-to-children mapping
            if parent_name not in parents___children:
                parents___children[ parent_name ] = []
            parents___children[ parent_name ].append( child_name )

            # Build child-to-parent mapping
            children___parents[ child_name ] = parent_name

    logger.info( f"Loaded {len( parents___children )} parent nodes with children" )
    logger.info( f"Loaded {len( children___parents )} meaningful parent-child transitions" )
    logger.info( f"Skipped {self_loop_count} terminal self-loops" )

    return parents___children, children___parents


def load_phylogenetic_paths():
    """
    Load phylogenetic paths (root-to-tip) for each species from Script 001 output.

    Returns:
        dict: { species_name: [ clade_name_1, clade_name_2, ..., species_name ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_file}" )

    if not input_phylogenetic_paths_file.exists():
        logger.error( f"CRITICAL ERROR: Phylogenetic paths file not found!" )
        logger.error( f"Expected: {input_phylogenetic_paths_file}" )
        sys.exit( 1 )

    species_names___phylogenetic_paths = {}

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

            # Parse path (comma-separated clade IDs with names, e.g. "C068_Basal,C069_Holomycota,C001_Fonticula_alba")
            path_entries = path_string.split( ',' )

            # Extract just clade names (after first underscore in "CXXX_Name" format)
            path = []
            for clade_id_name in path_entries:
                if '_' in clade_id_name:
                    clade_name = '_'.join( clade_id_name.split( '_' )[ 1: ] )
                    path.append( clade_name )

            # Species name is the last clade in the path (the leaf)
            if path:
                species_name = path[ -1 ]
                species_names___phylogenetic_paths[ species_name ] = path

    logger.info( f"Loaded {len( species_names___phylogenetic_paths )} phylogenetic paths" )

    return species_names___phylogenetic_paths


def build_clade_descendants( species_names___phylogenetic_paths ):
    """
    Build mapping of each clade to all descendant species.

    Args:
        species_names___phylogenetic_paths: { species_name: [ clade1, ..., species ] }

    Returns:
        dict: { clade_name: set( descendant_species ) }
    """
    logger.info( "Building clade-to-descendants mapping..." )

    clades___descendant_species = defaultdict( set )

    for species_name, path in species_names___phylogenetic_paths.items():
        # Add this species to all clades in its path
        for clade_name in path:
            clades___descendant_species[ clade_name ].add( species_name )

    logger.info( f"Built descendants mapping for {len( clades___descendant_species )} clades" )

    return clades___descendant_species


# ============================================================================
# SECTION 2: LOAD ANNOGROUP DATA
# ============================================================================

def load_annogroup_origins():
    """
    Load annogroup origin data from Script 002 output.

    Annotations Script 002 outputs 10 columns (including Annogroup_Subtype).

    Returns:
        dict: { annogroup_id: {
            'origin': str,
            'subtype': str,
            'phylogenetic_block': str,
            'phylogenetic_path': str,
            'species_list': str,
            'sequence_ids': str
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

        # Annogroup_ID (annogroup identifier)	Annogroup_Subtype (single or combo or zero)	Origin_Clade (...)	Origin_Clade_Phylogenetic_Block (...)	Origin_Clade_Phylogenetic_Path (...)	Shared_Clades (...)	Species_Count (...)	Sequence_Count (...)	Species_List (...)	Sequence_IDs (...)
        # annogroup_pfam_1	single	Filozoa	C069_Holozoa::C002_Filozoa	...	Basal,Holozoa,Filozoa	42	120	Homo_sapiens,Mus_musculus	seq1,seq2
        header_row = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            annogroup_subtype = parts[ 1 ]
            origin_clade = parts[ 2 ]
            phylogenetic_block = parts[ 3 ]
            phylogenetic_path = parts[ 4 ]
            # shared_clades = parts[ 5 ]    # Available but not used here
            # species_count = parts[ 6 ]    # Available but not used here
            # sequence_count = parts[ 7 ]   # Available but not used here
            species_list = parts[ 8 ]
            sequence_ids = parts[ 9 ]

            annogroups___origin_data[ annogroup_id ] = {
                'origin': origin_clade,
                'subtype': annogroup_subtype,
                'phylogenetic_block': phylogenetic_block,
                'phylogenetic_path': phylogenetic_path,
                'species_list': species_list,
                'sequence_ids': sequence_ids
            }

    logger.info( f"Loaded origin data for {len( annogroups___origin_data )} annogroups" )

    return annogroups___origin_data


def load_annogroup_species():
    """
    Load species composition for each annogroup from annogroup map (Script 001 output).

    Species names come directly from the annogroup map (already in Genus_species format).

    Returns:
        dict: { annogroup_id: set( species_names ) }
    """
    logger.info( f"Loading annogroup species from: {input_annogroup_map_file}" )

    if not input_annogroup_map_file.exists():
        logger.error( f"CRITICAL ERROR: Annogroup map file not found!" )
        logger.error( f"Expected: {input_annogroup_map_file}" )
        sys.exit( 1 )

    annogroups___species = {}

    with open( input_annogroup_map_file, 'r' ) as input_file:
        # Annogroup_ID (identifier format annogroup_{db}_N)	Annogroup_Subtype (single or combo or zero)	Annotation_Database (name of annotation database)	Annotation_Accessions (comma delimited annotation accessions from the database or unannotated identifier)	Species_Count (number of unique species with at least one member sequence)	Sequence_Count (total number of member sequences)	Species_List (comma delimited list of species names)	Sequence_IDs (comma delimited list of GIGANTIC sequence identifiers)
        # annogroup_pfam_1	single	pfam	PF00069	42	120	Homo_sapiens,Mus_musculus,...	XP_016856755.1,...
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            annogroup_id = parts[ 0 ]
            species_list_string = parts[ 6 ]

            # Parse comma-delimited species names
            species_set = set()
            for species_name in species_list_string.split( ',' ):
                species_name = species_name.strip()
                if species_name:
                    species_set.add( species_name )

            annogroups___species[ annogroup_id ] = species_set

    logger.info( f"Loaded species for {len( annogroups___species )} annogroups" )

    return annogroups___species


# ============================================================================
# SECTION 3: DETERMINE ANNOGROUPS PRESENT IN EACH CLADE
# ============================================================================

def build_clade_annogroups( annogroups___origin_data, annogroups___species,
                            clades___descendant_species, species_names___phylogenetic_paths ):
    """
    Determine PHYLOGENETICALLY INHERITED vs ACTUALLY PRESENT annogroups in each clade.

    TEMPLATE_03 CRITICAL DISTINCTION: Two Types of Annogroup-Clade Relationships

    1. PHYLOGENETICALLY INHERITED FROM ANCESTRAL ORIGIN
       Definition: Annogroup's origin clade is in the phylogenetic path to this clade
       Meaning: Annogroup COULD be present (was inherited from ancestor)
       Criterion: Origin clade appears in clade's phylogenetic path
       Requires: NO requirement for descendant species to actually have it

    2. ACTUALLY PRESENT IN DESCENDANT SPECIES (Genomic Reality)
       Definition: Annogroup is inherited AND at least one descendant species actually has it
       Meaning: Annogroup IS found in species genomes (not just theoretically possible)
       Criterion: Inherited + species intersection > 0

    Args:
        annogroups___origin_data: { annogroup_id: { 'origin': str, ... } }
        annogroups___species: { annogroup_id: set( species ) }
        clades___descendant_species: { clade_name: set( species ) }
        species_names___phylogenetic_paths: { species_name: [ clade1, ..., species ] }

    Returns:
        tuple: ( clades___phylogenetically_inherited_annogroups,
                 clades___actually_present_in_species_annogroups )
    """
    logger.info( "=" * 80 )
    logger.info( "DETERMINING ANNOGROUP-CLADE RELATIONSHIPS:" )
    logger.info( "  1. PHYLOGENETICALLY INHERITED = origin in phylogenetic path" )
    logger.info( "  2. ACTUALLY PRESENT IN SPECIES = inherited AND at least one species has it" )
    logger.info( "=" * 80 )

    # Dictionary 1: Phylogenetically inherited (theoretical inheritance from ancestor)
    clades___phylogenetically_inherited_annogroups = defaultdict( set )

    # Dictionary 2: Actually present in descendant species (genomic reality)
    clades___actually_present_in_species_annogroups = defaultdict( set )

    # Process each annogroup
    for annogroup_id, annogroup_species in annogroups___species.items():
        origin_data = annogroups___origin_data.get( annogroup_id )
        if not origin_data:
            continue
        origin_clade = origin_data[ 'origin' ]

        if not origin_clade:
            continue

        # For each clade: determine if annogroup is INHERITED and/or PRESENT
        for clade_name, descendant_species in clades___descendant_species.items():
            # Get any species in this clade to check its phylogenetic path
            if not descendant_species:
                continue

            sample_species = list( descendant_species )[ 0 ]
            clade_path = species_names___phylogenetic_paths.get( sample_species, [] )

            # CHECK 1: Is annogroup PHYLOGENETICALLY INHERITED?
            # Test: Is origin clade in this clade's phylogenetic path?
            if origin_clade not in clade_path:
                continue  # Not inherited, skip to next clade

            # Annogroup is PHYLOGENETICALLY INHERITED by this clade
            clades___phylogenetically_inherited_annogroups[ clade_name ].add( annogroup_id )

            # CHECK 2: Is annogroup ACTUALLY PRESENT IN DESCENDANT SPECIES?
            # Test: Do ANY descendant species actually have this annogroup?
            if annogroup_species.intersection( descendant_species ):
                clades___actually_present_in_species_annogroups[ clade_name ].add( annogroup_id )

    logger.info( f"Phylogenetically inherited annogroups: {len( clades___phylogenetically_inherited_annogroups )} clades" )
    logger.info( f"Actually present in species annogroups: {len( clades___actually_present_in_species_annogroups )} clades" )
    logger.info( "=" * 80 )

    return clades___phylogenetically_inherited_annogroups, clades___actually_present_in_species_annogroups


# ============================================================================
# SECTION 4: CALCULATE CONSERVATION AND LOSS PER BLOCK
# ============================================================================

def calculate_conservation_loss( parents___children, clades___inherited_annogroups,
                                clades___present_annogroups ):
    """
    Calculate conservation and loss statistics for each phylogenetic block.

    Per-block statistics track annogroups PRESENT in parent clade (at least one
    species has the annogroup). This differs from per-annogroup analysis which
    tracks ALL inherited transitions regardless of whether parent has species.

    For each parent to child transition:
    - Inherited: annogroups present in parent clade
    - Conserved: inherited annogroups still present in child clade
    - Lost: inherited annogroups absent in child clade

    Args:
        parents___children: { parent_name: [ child1, child2 ] }
        clades___inherited_annogroups: { clade_name: set( inherited annogroup_ids ) }
        clades___present_annogroups: { clade_name: set( present annogroup_ids ) }

    Returns:
        list: Per-block statistics dictionaries
    """
    logger.info( "Calculating conservation and loss per phylogenetic block..." )

    block_statistics = []

    for parent_name, children in parents___children.items():
        # Use PRESENT annogroups for per-block statistics
        parent_annogroups_present = clades___present_annogroups.get( parent_name, set() )

        for child_name in children:
            child_annogroups_present = clades___present_annogroups.get( child_name, set() )

            # Calculate conservation and loss
            inherited = parent_annogroups_present
            conserved = inherited.intersection( child_annogroups_present )
            lost = inherited - child_annogroups_present

            inherited_count = len( inherited )
            conserved_count = len( conserved )
            lost_count = len( lost )

            # Calculate rates (handle zero inherited explicitly)
            if inherited_count > 0:
                conservation_rate = ( conserved_count / inherited_count ) * 100
                loss_rate = ( lost_count / inherited_count ) * 100
            else:
                conservation_rate = 0.0
                loss_rate = 0.0

            block_statistic = {
                'parent_clade': parent_name,
                'child_clade': child_name,
                'inherited_count': inherited_count,
                'conserved_count': conserved_count,
                'lost_count': lost_count,
                'conservation_rate': conservation_rate,
                'loss_rate': loss_rate
            }

            block_statistics.append( block_statistic )

    logger.info( f"Calculated statistics for {len( block_statistics )} phylogenetic blocks" )

    return block_statistics


# ============================================================================
# SECTION 5: ANALYZE CONSERVATION PATTERNS PER ANNOGROUP
# ============================================================================

def analyze_annogroup_patterns( annogroups___origin_data, annogroups___species,
                               parents___children, clades___inherited_annogroups,
                               clades___present_annogroups ):
    """
    Analyze conservation/loss pattern across all blocks for each annogroup.

    TEMPLATE_03 dual-metric tracking:
    1. Evaluates ALL inherited transitions (not just where parent has species)
    2. Distinguishes loss at origin from continued absence
    3. Calculates tree coverage metrics

    Event Types:
    - Conservation: annogroup inherited, present in parent, present in child
    - Loss at Origin: annogroup inherited, present in parent, absent in child
    - Continued Absence: annogroup inherited, absent in parent, absent in child
    - Loss Coverage: loss at origin + continued absence

    Edge case: zero inherited transitions results in all rates = 0.0

    Args:
        annogroups___origin_data: { annogroup_id: { 'origin': str, ... } }
        annogroups___species: { annogroup_id: set( species ) }
        parents___children: { parent_name: [ child1, child2 ] }
        clades___inherited_annogroups: { clade_name: set( inherited annogroup_ids ) }
        clades___present_annogroups: { clade_name: set( present annogroup_ids ) }

    Returns:
        list: Per-annogroup conservation pattern dictionaries
    """
    logger.info( "Analyzing conservation patterns per annogroup (TEMPLATE_03 dual-metric tracking)..." )

    annogroup_patterns = []

    for annogroup_id, origin_data in annogroups___origin_data.items():
        origin_clade = origin_data[ 'origin' ]
        species_count = len( annogroups___species.get( annogroup_id, set() ) )

        # Initialize event counters (4 types of events)
        conservation_events = 0
        loss_origin_events = 0
        continued_absence_events = 0

        # Process ALL parent-child transitions where annogroup was inherited
        for parent_name, children in parents___children.items():
            parent_inherited = clades___inherited_annogroups.get( parent_name, set() )
            parent_present = clades___present_annogroups.get( parent_name, set() )

            # Skip if annogroup not inherited by parent
            if annogroup_id not in parent_inherited:
                continue

            # Determine if annogroup is present in parent
            parent_has_annogroup = annogroup_id in parent_present

            for child_name in children:
                child_inherited = clades___inherited_annogroups.get( child_name, set() )
                child_present = clades___present_annogroups.get( child_name, set() )

                # Verify child also inherited annogroup
                if annogroup_id not in child_inherited:
                    logger.warning( f"Annogroup {annogroup_id} inherited by parent {parent_name} "
                                  f"but not child {child_name} - phylogenetic path inconsistency?" )
                    continue

                # Determine if annogroup is present in child
                child_has_annogroup = annogroup_id in child_present

                # Classify transition into one of 4 event types
                if parent_has_annogroup and child_has_annogroup:
                    # CONSERVATION: Present in parent AND child
                    conservation_events += 1

                elif parent_has_annogroup and not child_has_annogroup:
                    # LOSS AT ORIGIN: Present in parent but absent in child
                    loss_origin_events += 1

                elif not parent_has_annogroup and not child_has_annogroup:
                    # CONTINUED ABSENCE: Absent in parent AND child
                    continued_absence_events += 1

                else:
                    # Absent in parent, present in child - should not occur
                    logger.warning( f"Unexpected case for annogroup {annogroup_id}: "
                                  f"absent in parent {parent_name} but present in child {child_name}. "
                                  f"This suggests annogroup re-originated or phylogenetic path error." )

        # Calculate derived metrics
        total_inherited_transitions = conservation_events + loss_origin_events + continued_absence_events
        loss_coverage_events = loss_origin_events + continued_absence_events

        # Calculate percentages (handle zero inherited transitions explicitly)
        if total_inherited_transitions > 0:
            conservation_rate_percent = ( conservation_events / total_inherited_transitions ) * 100
            loss_origin_rate_percent = ( loss_origin_events / total_inherited_transitions ) * 100
            percent_tree_conserved = conservation_rate_percent
            percent_tree_loss = ( loss_coverage_events / total_inherited_transitions ) * 100
        else:
            conservation_rate_percent = 0.0
            loss_origin_rate_percent = 0.0
            percent_tree_conserved = 0.0
            percent_tree_loss = 0.0

        # Store pattern with metrics and annotation data from Script 002
        pattern = {
            'annogroup_id': annogroup_id,
            'annogroup_subtype': origin_data[ 'subtype' ],
            'origin_clade': origin_clade,
            'phylogenetic_block': origin_data[ 'phylogenetic_block' ],
            'phylogenetic_path': origin_data[ 'phylogenetic_path' ],
            'species_count': species_count,
            'total_inherited_transitions': total_inherited_transitions,
            'conservation_events': conservation_events,
            'loss_origin_events': loss_origin_events,
            'continued_absence_events': continued_absence_events,
            'loss_coverage_events': loss_coverage_events,
            'conservation_rate_percent': conservation_rate_percent,
            'loss_origin_rate_percent': loss_origin_rate_percent,
            'percent_tree_conserved': percent_tree_conserved,
            'percent_tree_loss': percent_tree_loss,
            'species_list': origin_data[ 'species_list' ],
            'sequence_ids': origin_data[ 'sequence_ids' ]
        }

        annogroup_patterns.append( pattern )

    logger.info( f"Analyzed patterns for {len( annogroup_patterns )} annogroups" )
    logger.info( f"Total transitions evaluated across all annogroups: "
               f"{sum( p[ 'total_inherited_transitions' ] for p in annogroup_patterns )}" )

    return annogroup_patterns


# ============================================================================
# SECTION 6: WRITE OUTPUTS
# ============================================================================

def write_block_statistics( block_statistics ):
    """Write per-block conservation/loss statistics."""
    logger.info( f"Writing block statistics to: {output_block_statistics_file}" )

    with open( output_block_statistics_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Parent_Clade (parent clade in phylogenetic block transition excluding terminal self-loops)\t'
        output += 'Child_Clade (child clade in phylogenetic block transition excluding terminal self-loops)\t'
        output += 'Inherited_Count (count of annogroups present in parent clade that could be inherited by child)\t'
        output += 'Conserved_Count (count of annogroups from parent that are also present in child clade)\t'
        output += 'Lost_Count (count of annogroups from parent that are absent in child clade)\t'
        output += 'Conservation_Rate (percentage of inherited annogroups conserved in child calculated as conserved count divided by inherited count times 100)\t'
        output += 'Loss_Rate (percentage of inherited annogroups lost in child calculated as lost count divided by inherited count times 100)\n'
        output_file.write( output )

        for statistic in block_statistics:
            output = f"{statistic[ 'parent_clade' ]}\t{statistic[ 'child_clade' ]}\t"
            output += f"{statistic[ 'inherited_count' ]}\t{statistic[ 'conserved_count' ]}\t"
            output += f"{statistic[ 'lost_count' ]}\t{statistic[ 'conservation_rate' ]:.2f}\t"
            output += f"{statistic[ 'loss_rate' ]:.2f}\n"

            output_file.write( output )

    logger.info( f"Wrote {len( block_statistics )} block statistics" )


def write_annogroup_patterns( annogroup_patterns ):
    """Write per-annogroup conservation patterns with TEMPLATE_03 dual-metric tracking."""
    logger.info( f"Writing annogroup patterns (TEMPLATE_03 format) to: {output_annogroup_patterns_file}" )

    with open( output_annogroup_patterns_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Build single-row GIGANTIC_1 header
        header_columns = [
            'Annogroup_ID (annogroup identifier)',
            'Annogroup_Subtype (single or combo or zero)',
            'Origin_Clade (phylogenetic clade where annogroup originated via most recent common ancestor algorithm)',
            'Origin_Clade_Phylogenetic_Block (phylogenetic block for origin clade format Parent_Clade::Child_Clade)',
            'Origin_Clade_Phylogenetic_Path (phylogenetic path for origin clade comma delimited from root to origin clade)',
            'Species_Count (total unique species containing this annogroup across all genomes)',
            'Total_Phylogenetically_Inherited_Transitions (count of all parent to child clade transitions descended from origin clade where annogroup was phylogenetically inherited)',
            'Conservation_Events_Actually_Present_In_Both_Parent_And_Child (count of transitions where annogroup actually present in descendant species of both parent and child clades)',
            'Loss_At_Origin_Events_Present_In_Parent_Absent_In_Child (count of transitions where annogroup present in parent species but absent in child species representing phylogenetic origin of gene loss)',
            'Continued_Absence_Events_Absent_In_Both_Parent_And_Child (count of transitions where annogroup absent in both parent and child species meaning loss occurred earlier and absence continues)',
            'Loss_Coverage_Events_All_Transitions_Where_Absent_In_Child (count of all transitions where annogroup absent in child species calculated as loss at origin plus continued absence)',
            'Conservation_Rate_Percent (percentage of inherited transitions showing conservation calculated as conservation events divided by total inherited transitions times 100)',
            'Loss_At_Origin_Rate_Percent (percentage of inherited transitions where gene loss first occurs calculated as loss at origin events divided by total inherited transitions times 100)',
            'Percent_Phylogenetic_Tree_With_Annogroup_Actually_Present (percentage of phylogenetic tree where annogroup is present calculated as conservation events divided by total inherited transitions times 100)',
            'Percent_Phylogenetic_Tree_Lacking_Annogroup (percentage of phylogenetic tree where annogroup is absent calculated as loss coverage events divided by total inherited transitions times 100)',
            'Species_List (comma delimited list of all species containing this annogroup)',
            'Sequence_IDs (comma delimited list of sequence identifiers in this annogroup)'
        ]

        # Write single-row header
        csv_writer.writerow( header_columns )

        # Data (sorted by annogroup ID)
        sorted_patterns = sorted( annogroup_patterns, key = lambda x: x[ 'annogroup_id' ] )

        for pattern in sorted_patterns:
            output_row = [
                pattern[ 'annogroup_id' ],
                pattern[ 'annogroup_subtype' ],
                pattern[ 'origin_clade' ],
                pattern[ 'phylogenetic_block' ],
                pattern[ 'phylogenetic_path' ],
                pattern[ 'species_count' ],
                pattern[ 'total_inherited_transitions' ],
                pattern[ 'conservation_events' ],
                pattern[ 'loss_origin_events' ],
                pattern[ 'continued_absence_events' ],
                pattern[ 'loss_coverage_events' ],
                f"{pattern[ 'conservation_rate_percent' ]:.2f}",
                f"{pattern[ 'loss_origin_rate_percent' ]:.2f}",
                f"{pattern[ 'percent_tree_conserved' ]:.2f}",
                f"{pattern[ 'percent_tree_loss' ]:.2f}",
                pattern[ 'species_list' ],
                pattern[ 'sequence_ids' ]
            ]

            csv_writer.writerow( output_row )

    logger.info( f"Wrote {len( annogroup_patterns )} annogroup patterns (17 columns, TEMPLATE_03 format)" )


def write_summary( block_statistics, annogroup_patterns ):
    """Write overall summary statistics."""
    logger.info( f"Writing summary to: {output_summary_file}" )

    # Calculate block-level summary statistics
    total_blocks = len( block_statistics )
    total_inherited = sum( statistic[ 'inherited_count' ] for statistic in block_statistics )
    total_conserved = sum( statistic[ 'conserved_count' ] for statistic in block_statistics )
    total_lost = sum( statistic[ 'lost_count' ] for statistic in block_statistics )

    if total_inherited > 0:
        overall_conservation_rate = ( total_conserved / total_inherited ) * 100
        overall_loss_rate = ( total_lost / total_inherited ) * 100
    else:
        overall_conservation_rate = 0.0
        overall_loss_rate = 0.0

    # Calculate annogroup-level summary statistics
    total_annogroups = len( annogroup_patterns )
    total_conservation_events = sum( p[ 'conservation_events' ] for p in annogroup_patterns )
    total_loss_origin_events = sum( p[ 'loss_origin_events' ] for p in annogroup_patterns )
    total_continued_absence_events = sum( p[ 'continued_absence_events' ] for p in annogroup_patterns )
    total_loss_coverage_events = sum( p[ 'loss_coverage_events' ] for p in annogroup_patterns )
    total_inherited_transitions = sum( p[ 'total_inherited_transitions' ] for p in annogroup_patterns )

    with open( output_summary_file, 'w' ) as output_file:
        output = "Conservation and Loss Analysis Summary (TEMPLATE_03)\n"
        output += "=" * 80 + "\n\n"
        output += f"Structure: {TARGET_STRUCTURE}\n"
        output += f"Annotation Database: {ANNOTATION_DATABASE}\n\n"
        output += "PHYLOGENETIC BLOCKS:\n"
        output += f"  Total blocks analyzed: {total_blocks}\n"
        output += f"  Total inherited annogroups (all blocks): {total_inherited}\n"
        output += f"  Total conserved: {total_conserved}\n"
        output += f"  Total lost: {total_lost}\n"
        output += f"  Overall conservation rate: {overall_conservation_rate:.2f}%\n"
        output += f"  Overall loss rate: {overall_loss_rate:.2f}%\n\n"
        output += "ANNOGROUPS (TEMPLATE_03 Dual-Metric Tracking):\n"
        output += f"  Total annogroups analyzed: {total_annogroups}\n"
        output += f"  Total inherited transitions (all annogroups): {total_inherited_transitions}\n"
        output += f"  Conservation events (present in both parent and child): {total_conservation_events}\n"
        output += f"  Loss at origin events (present in parent, absent in child): {total_loss_origin_events}\n"
        output += f"  Continued absence events (absent in both parent and child): {total_continued_absence_events}\n"
        output += f"  Loss coverage events (all transitions lacking annogroup): {total_loss_coverage_events}\n"
        output_file.write( output )

    logger.info( "Wrote summary statistics" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function."""
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 003: QUANTIFY CONSERVATION AND LOSS (TEMPLATE_03)" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {Path( __file__ ).name}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Annotation database: {ANNOTATION_DATABASE}" )
    logger.info( "" )

    # STEP 1: Load phylogenetic tree structure
    logger.info( "STEP 1: Loading phylogenetic tree structure..." )
    clade_ids___clade_names = load_clade_id_mapping()
    parents___children, children___parents = load_parent_child_relationships( clade_ids___clade_names )
    species_names___phylogenetic_paths = load_phylogenetic_paths()
    clades___descendant_species = build_clade_descendants( species_names___phylogenetic_paths )
    logger.info( "" )

    # STEP 2: Load annogroup data
    logger.info( "STEP 2: Loading annogroup data..." )
    annogroups___origin_data = load_annogroup_origins()
    annogroups___species = load_annogroup_species()
    logger.info( "" )

    # STEP 3: Determine annogroups inherited and present in each clade
    logger.info( "STEP 3: Determining inherited and present annogroups for each clade..." )
    clades___inherited_annogroups, clades___present_annogroups = build_clade_annogroups(
        annogroups___origin_data,
        annogroups___species,
        clades___descendant_species,
        species_names___phylogenetic_paths
    )
    logger.info( "" )

    # STEP 4: Calculate conservation and loss per block
    logger.info( "STEP 4: Calculating conservation and loss per block..." )
    block_statistics = calculate_conservation_loss(
        parents___children,
        clades___inherited_annogroups,
        clades___present_annogroups
    )
    logger.info( "" )

    # STEP 5: Analyze conservation patterns per annogroup
    logger.info( "STEP 5: Analyzing conservation patterns per annogroup..." )
    annogroup_patterns = analyze_annogroup_patterns(
        annogroups___origin_data,
        annogroups___species,
        parents___children,
        clades___inherited_annogroups,
        clades___present_annogroups
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
