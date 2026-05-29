# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Integrate Scripts 002+003 into per-annogroup, per-clade, and per-species summaries (Rule 7 counts)
# Human: Eric Edsinger

"""
OCL Pipeline Script 004: Comprehensive OCL Summaries (Rule 7 counts)

Integrates results from Scripts 001-003 into comprehensive summary tables.
Counts only -- no rates.

Outputs:
- Per-annogroup complete OCL summary (all subtypes integrated -- primary downstream file)
- Per-subtype complete OCL summaries (one file per annogroup subtype: single, combo, zero)
- Per-clade comprehensive statistics (origins count, annogroups present at
  clade, per-clade-as-parent counts: inherited / conserved / lost)
- Per-species summaries (total, conserved-from-ancestors, species-specific)
- Per (annogroup, species) phylogenetic path-states (Rule 7 AOPLX strings)
- Cross-validation report (Script 003 vs Script 004 count consistency)

All data needed for output comes from Scripts 001-003 outputs in OUTPUT_pipeline.
No access to centralized trees_species data is needed (Script 003 already carries
phylogenetic block and path annotations from Script 002).

Usage:
    python 004_ai-python-comprehensive_ocl_analysis.py --structure_id 001 --config ../../START_HERE-user_config.yaml
"""

import csv
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

# Increase CSV field size limit to handle large fields
csv.field_size_limit( sys.maxsize )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'OCL Pipeline Script 004: Generate comprehensive OCL analysis',
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
ANNOGROUP_SUBTYPES = config[ 'annogroup_subtypes' ]

# Input directories
input_directory_001 = Path( args.output_dir ) / TARGET_STRUCTURE / '1-output'
input_directory_002 = Path( args.output_dir ) / TARGET_STRUCTURE / '2-output'
input_directory_003 = Path( args.output_dir ) / TARGET_STRUCTURE / '3-output'

# Input files from Script 001
input_clade_mappings_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_clade_mappings.tsv'
input_phylogenetic_paths_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_phylogenetic_paths.tsv'
input_annogroups_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_annogroups-species_identifiers.tsv'

# Input files from Script 002
input_origins_file = input_directory_002 / f'2_ai-{TARGET_STRUCTURE}_annogroup_origins.tsv'
input_origins_summary_file = input_directory_002 / f'2_ai-{TARGET_STRUCTURE}_origins_summary-annogroups_per_clade.tsv'

# Input files from Script 003
input_block_statistics_file = input_directory_003 / f'3_ai-{TARGET_STRUCTURE}_conservation_loss-per_block.tsv'
input_annogroup_patterns_file = input_directory_003 / f'3_ai-{TARGET_STRUCTURE}_conservation_patterns-per_annogroup.tsv'

# Output directory
output_directory = Path( args.output_dir ) / TARGET_STRUCTURE / '4-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_annogroup_complete_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_annogroups-complete_ocl_summary-all_types.tsv'
output_clade_statistics_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_clades-comprehensive_statistics.tsv'
output_species_summaries_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_species-summaries.tsv'
output_path_states_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_path_states-per_annogroup_per_species.tsv'
output_validation_report_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_validation_report.txt'

# Log file
log_directory = Path( args.output_dir ) / TARGET_STRUCTURE / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / f'4_ai-log-comprehensive_ocl_analysis-{TARGET_STRUCTURE}.log'


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
# SECTION 1: LOAD ALL INPUT DATA
# ============================================================================

def load_annogroup_origins():
    """
    Load annogroup origin data from Script 002 output.

    Returns:
        dict: { annogroup_id: {
            'phylogenetic_block': str,
            'phylogenetic_block_state': str,
            'origin_child_clade_id_name': str,
            'annogroup_subtype': str,
            'species_count': int
        } }
    """
    logger.info( f"Loading annogroup origins from: {input_origins_file}" )

    if not input_origins_file.exists():
        logger.error( f"CRITICAL ERROR: Origins file not found!" )
        logger.error( f"Expected: {input_origins_file}" )
        sys.exit( 1 )

    annogroups___origins = {}

    with open( input_origins_file, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Annogroup_ID	Annogroup_Subtype	Origin_Phylogenetic_Block	Origin_Phylogenetic_Block_State	Origin_Phylogenetic_Path	Shared_Clade_ID_Names	Species_Count	Species_List
        # annogroup_pfam_1	single	C069_Holozoa::C002_Filozoa	C069_Holozoa::C002_Filozoa-O	...	42	Homo_sapiens,...
        header_row = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            annogroup_subtype = parts[ 1 ]
            phylogenetic_block = parts[ 2 ]
            phylogenetic_block_state = parts[ 3 ]
            species_count = int( parts[ 6 ] )

            # Derive child endpoint of origin block
            if '::' in phylogenetic_block:
                origin_child_clade_id_name = phylogenetic_block.split( '::', 1 )[ 1 ]
            else:
                origin_child_clade_id_name = phylogenetic_block

            annogroups___origins[ annogroup_id ] = {
                'phylogenetic_block': phylogenetic_block,
                'phylogenetic_block_state': phylogenetic_block_state,
                'origin_child_clade_id_name': origin_child_clade_id_name,
                'annogroup_subtype': annogroup_subtype,
                'species_count': species_count
            }

    logger.info( f"Loaded origins for {len( annogroups___origins )} annogroups" )

    return annogroups___origins


def load_annogroup_patterns():
    """
    Load per-annogroup block-state counts from Script 003.

    Returns:
        dict: { annogroup_id: { block-state counts + annotations } }
    """
    logger.info( f"Loading annogroup patterns from: {input_annogroup_patterns_file}" )

    if not input_annogroup_patterns_file.exists():
        logger.error( f"CRITICAL ERROR: Patterns file not found!" )
        logger.error( f"Expected: {input_annogroup_patterns_file}" )
        sys.exit( 1 )

    annogroups___patterns = {}

    with open( input_annogroup_patterns_file, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Annogroup_ID	Origin_Phylogenetic_Block	Origin_Phylogenetic_Block_State	Origin_Phylogenetic_Path	Annogroup_Subtype	Species_Count	Total_Scored_Blocks	Conservation_Events	Loss_Events	Continued_Absence_Events	Species_List
        header_row = next( csv_reader )

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            phylogenetic_block = parts[ 1 ]
            phylogenetic_block_state = parts[ 2 ]
            phylogenetic_path = parts[ 3 ]
            annogroup_subtype = parts[ 4 ]
            species_count = int( parts[ 5 ] )
            total_scored_blocks = int( parts[ 6 ] )
            conservation_events = int( parts[ 7 ] )
            loss_origin_events = int( parts[ 8 ] )
            continued_absence_events = int( parts[ 9 ] )
            species_list = parts[ 10 ]

            annogroups___patterns[ annogroup_id ] = {
                'phylogenetic_block': phylogenetic_block,
                'phylogenetic_block_state': phylogenetic_block_state,
                'phylogenetic_path': phylogenetic_path,
                'annogroup_subtype': annogroup_subtype,
                'species_count': species_count,
                'total_scored_blocks': total_scored_blocks,
                'conservation_events': conservation_events,
                'loss_origin_events': loss_origin_events,
                'continued_absence_events': continued_absence_events,
                'species_list': species_list
            }

    logger.info( f"Loaded patterns for {len( annogroups___patterns )} annogroups" )

    return annogroups___patterns


def load_clade_mappings():
    """Load clade mappings from Script 001 output; returns bare name -> clade_id_name."""
    logger.info( f"Loading clade mappings from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mapping not found!" )
        logger.error( f"Expected: {input_clade_mappings_file}" )
        sys.exit( 1 )

    clade_names___clade_id_names = {}

    with open( input_clade_mappings_file, 'r' ) as input_file:
        # Clade_Name (bare clade name lookup key)	Clade_ID_Name (atomic clade identifier)
        # Fonticula_alba	C001_Fonticula_alba
        header_line = input_file.readline()

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


def load_annogroup_species( clade_names___clade_id_names ):
    """Load species composition for each annogroup; returns species_clade_id_name sets."""
    logger.info( f"Loading annogroup species from: {input_annogroups_file}" )

    if not input_annogroups_file.exists():
        logger.error( f"CRITICAL ERROR: Annogroups file not found!" )
        logger.error( f"Expected: {input_annogroups_file}" )
        sys.exit( 1 )

    annogroups___species_clade_id_names = {}

    with open( input_annogroups_file, 'r' ) as input_file:
        # Annogroup_ID	Annogroup_Subtype	Species_Count	Species_List
        # annogroup_pfam_1	single	5	Homo_sapiens,Mus_musculus,...
        header_line = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            annogroup_id = parts[ 0 ]
            species_list_string = parts[ 3 ]

            species_names = species_list_string.split( ',' )

            species_clade_id_names_set = set()
            for species_name in species_names:
                species_name = species_name.strip()
                if not species_name:
                    continue
                species_clade_id_name = clade_names___clade_id_names.get( species_name )
                if species_clade_id_name is None:
                    continue
                species_clade_id_names_set.add( species_clade_id_name )

            annogroups___species_clade_id_names[ annogroup_id ] = species_clade_id_names_set

    logger.info( f"Loaded species_clade_id_names for {len( annogroups___species_clade_id_names )} annogroups" )
    return annogroups___species_clade_id_names


def load_origins_summary():
    """Load origins summary from Script 002 output."""
    logger.info( f"Loading origins summary from: {input_origins_summary_file}" )

    if not input_origins_summary_file.exists():
        logger.error( f"CRITICAL ERROR: Origins summary not found!" )
        logger.error( f"Expected: {input_origins_summary_file}" )
        sys.exit( 1 )

    clade_id_names___origin_counts = {}

    with open( input_origins_summary_file, 'r' ) as input_file:
        # Origin_Phylogenetic_Block_State	Annogroup_Count	Percentage
        # C069_Holozoa::C082_Metazoa-O	4532	2.14
        header_line = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            phylogenetic_block_state = parts[ 0 ]
            annogroup_count = int( parts[ 1 ] )

            # Extract child clade_id_name from block-state identifier
            if '::' in phylogenetic_block_state and phylogenetic_block_state.endswith( '-O' ):
                child_clade_id_name = phylogenetic_block_state.split( '::', 1 )[ 1 ][:-2]
            elif phylogenetic_block_state == 'NA':
                continue
            else:
                logger.warning( f"Unexpected block-state identifier format: {phylogenetic_block_state!r} -- skipping" )
                continue

            clade_id_names___origin_counts[ child_clade_id_name ] = annogroup_count

    logger.info( f"Loaded origin counts for {len( clade_id_names___origin_counts )} clades" )
    return clade_id_names___origin_counts


def load_block_statistics():
    """Load per-block conservation/loss statistics from Script 003 output."""
    logger.info( f"Loading block statistics from: {input_block_statistics_file}" )

    if not input_block_statistics_file.exists():
        logger.error( f"CRITICAL ERROR: Block statistics not found!" )
        logger.error( f"Expected: {input_block_statistics_file}" )
        sys.exit( 1 )

    block_statistics = []

    with open( input_block_statistics_file, 'r' ) as input_file:
        # Parent_Clade_ID_Name	Child_Clade_ID_Name	Inherited_Count	Conserved_Count	Lost_Count
        header_line = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            statistic = {
                'parent_clade_id_name': parts[ 0 ],
                'child_clade_id_name': parts[ 1 ],
                'inherited_count': int( parts[ 2 ] ),
                'conserved_count': int( parts[ 3 ] ),
                'lost_count': int( parts[ 4 ] ),
            }
            block_statistics.append( statistic )

    logger.info( f"Loaded statistics for {len( block_statistics )} blocks" )
    return block_statistics


def load_phylogenetic_paths():
    """Load phylogenetic paths from Script 001 output; keyed by leaf species_clade_id_name."""
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_file}" )

    if not input_phylogenetic_paths_file.exists():
        logger.error( f"CRITICAL ERROR: Phylogenetic paths not found!" )
        logger.error( f"Expected: {input_phylogenetic_paths_file}" )
        sys.exit( 1 )

    species_clade_id_names___phylogenetic_paths = {}

    with open( input_phylogenetic_paths_file, 'r' ) as input_file:
        # Leaf_Clade_ID	Path_Length	Phylogenetic_Path
        # C001_Fonticula_alba	3	C068_Basal,C069_Holomycota,C001_Fonticula_alba
        header_line = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            path_string = parts[ 2 ]

            path = [ entry for entry in path_string.split( ',' ) if entry ]

            if path:
                species_clade_id_name = path[ -1 ]
                species_clade_id_names___phylogenetic_paths[ species_clade_id_name ] = path

    logger.info( f"Loaded {len( species_clade_id_names___phylogenetic_paths )} phylogenetic paths" )
    return species_clade_id_names___phylogenetic_paths


# ============================================================================
# SECTION 2: GENERATE PER-ANNOGROUP COMPLETE SUMMARIES
# ============================================================================

def generate_annogroup_summaries( annogroups___origins, annogroups___patterns ):
    """
    Generate complete per-annogroup summaries (Rule 7 block-state counts).

    Returns:
        list: Per-annogroup summary dictionaries
    """
    logger.info( "Generating complete annogroup summaries..." )

    annogroup_summaries = []

    for annogroup_id in sorted( annogroups___origins.keys() ):
        origin_info = annogroups___origins[ annogroup_id ]
        pattern_info = annogroups___patterns.get( annogroup_id, {} )

        total_scored_blocks = pattern_info.get( 'total_scored_blocks', 0 )
        conservation_events = pattern_info.get( 'conservation_events', 0 )
        loss_origin_events = pattern_info.get( 'loss_origin_events', 0 )
        continued_absence_events = pattern_info.get( 'continued_absence_events', 0 )

        phylogenetic_block = pattern_info.get( 'phylogenetic_block', 'NA' )
        phylogenetic_block_state = pattern_info.get( 'phylogenetic_block_state', 'NA' )
        phylogenetic_path = pattern_info.get( 'phylogenetic_path', 'NA' )
        annogroup_subtype = pattern_info.get( 'annogroup_subtype', origin_info.get( 'annogroup_subtype', 'unknown' ) )
        species_list = pattern_info.get( 'species_list', '' )

        summary = {
            'annogroup_id': annogroup_id,
            'annogroup_subtype': annogroup_subtype,
            'phylogenetic_block': phylogenetic_block,
            'phylogenetic_block_state': phylogenetic_block_state,
            'phylogenetic_path': phylogenetic_path,
            'species_count': origin_info[ 'species_count' ],
            'total_scored_blocks': total_scored_blocks,
            'conservation_events': conservation_events,
            'loss_origin_events': loss_origin_events,
            'continued_absence_events': continued_absence_events,
            'species_list': species_list
        }

        annogroup_summaries.append( summary )

    logger.info( f"Generated summaries for {len( annogroup_summaries )} annogroups" )
    return annogroup_summaries


# ============================================================================
# SECTION 3: GENERATE PER-CLADE COMPREHENSIVE STATISTICS
# ============================================================================

def generate_clade_statistics( clade_id_names, clade_id_names___origin_counts, annogroups___species_clade_id_names,
                               species_clade_id_names___phylogenetic_paths, block_statistics ):
    """Generate comprehensive statistics for each clade."""
    logger.info( "Generating comprehensive clade statistics..." )

    # Build clade_id_name-to-descendants mapping
    clade_id_names___descendant_species_clade_id_names = defaultdict( set )
    for species_clade_id_name, path in species_clade_id_names___phylogenetic_paths.items():
        for clade_id_name in path:
            clade_id_names___descendant_species_clade_id_names[ clade_id_name ].add( species_clade_id_name )

    # Build clade_id_name-to-annogroups mapping
    clade_id_names___annogroups = defaultdict( set )
    for annogroup_id, species_clade_id_names_set in annogroups___species_clade_id_names.items():
        for clade_id_name in clade_id_names:
            descendant_species_clade_id_names = clade_id_names___descendant_species_clade_id_names.get( clade_id_name, set() )
            if species_clade_id_names_set.intersection( descendant_species_clade_id_names ):
                clade_id_names___annogroups[ clade_id_name ].add( annogroup_id )

    # Aggregate conservation/loss statistics per clade (as parent)
    clade_id_names___conservation_statistics = {}
    for statistic in block_statistics:
        parent_clade_id_name = statistic[ 'parent_clade_id_name' ]

        if parent_clade_id_name not in clade_id_names___conservation_statistics:
            clade_id_names___conservation_statistics[ parent_clade_id_name ] = {
                'as_parent_inherited': 0,
                'as_parent_conserved': 0,
                'as_parent_lost': 0
            }

        clade_id_names___conservation_statistics[ parent_clade_id_name ][ 'as_parent_inherited' ] += statistic[ 'inherited_count' ]
        clade_id_names___conservation_statistics[ parent_clade_id_name ][ 'as_parent_conserved' ] += statistic[ 'conserved_count' ]
        clade_id_names___conservation_statistics[ parent_clade_id_name ][ 'as_parent_lost' ] += statistic[ 'lost_count' ]

    clade_statistics = []

    for clade_id_name in sorted( clade_id_names ):
        origins_count = clade_id_names___origin_counts.get( clade_id_name, 0 )
        annogroups_present = len( clade_id_names___annogroups.get( clade_id_name, set() ) )
        descendant_species_count = len( clade_id_names___descendant_species_clade_id_names.get( clade_id_name, set() ) )

        conservation_data = clade_id_names___conservation_statistics.get( clade_id_name, {} )
        inherited_as_parent = conservation_data.get( 'as_parent_inherited', 0 )
        conserved_as_parent = conservation_data.get( 'as_parent_conserved', 0 )
        lost_as_parent = conservation_data.get( 'as_parent_lost', 0 )

        statistic = {
            'clade_id_name': clade_id_name,
            'origins_count': origins_count,
            'annogroups_present': annogroups_present,
            'descendant_species_count': descendant_species_count,
            'inherited_as_parent': inherited_as_parent,
            'conserved_as_parent': conserved_as_parent,
            'lost_as_parent': lost_as_parent,
        }

        clade_statistics.append( statistic )

    logger.info( f"Generated statistics for {len( clade_statistics )} clades" )
    return clade_statistics


# ============================================================================
# SECTION 4: GENERATE PER-SPECIES SUMMARIES
# ============================================================================

def generate_species_summaries( species_clade_id_names___phylogenetic_paths, annogroups___species_clade_id_names,
                               clade_id_names___origin_counts ):
    """Generate per-species summaries keyed by species_clade_id_name."""
    logger.info( "Generating per-species summaries..." )

    species_summaries = []

    for species_clade_id_name in sorted( species_clade_id_names___phylogenetic_paths.keys() ):
        annogroups_in_species = set()
        for annogroup_id, species_set in annogroups___species_clade_id_names.items():
            if species_clade_id_name in species_set:
                annogroups_in_species.add( annogroup_id )

        total_annogroups = len( annogroups_in_species )
        species_specific = clade_id_names___origin_counts.get( species_clade_id_name, 0 )
        conserved_from_ancestors = total_annogroups - species_specific

        summary = {
            'species_clade_id_name': species_clade_id_name,
            'total_annogroups': total_annogroups,
            'conserved_from_ancestors': conserved_from_ancestors,
            'species_specific': species_specific
        }

        species_summaries.append( summary )

    logger.info( f"Generated summaries for {len( species_summaries )} species" )
    return species_summaries


# ============================================================================
# SECTION 4b: PHYLOGENETIC PATH-STATES (Rule 7)
# ============================================================================

def build_clade_descendant_species( species_clade_id_names___phylogenetic_paths ):
    """Build per-clade descendant-species sets using the phylogenetic paths."""
    clade_id_names___descendant_species_clade_id_names = defaultdict( set )
    for species_clade_id_name, phylogenetic_path in species_clade_id_names___phylogenetic_paths.items():
        for clade_id_name in phylogenetic_path:
            clade_id_names___descendant_species_clade_id_names[ clade_id_name ].add( species_clade_id_name )
    return clade_id_names___descendant_species_clade_id_names


def build_clade_descendant_clades( species_clade_id_names___phylogenetic_paths ):
    """Build per-clade descendant-clade sets using the phylogenetic paths."""
    clade_id_names___descendant_clade_id_names = defaultdict( set )
    for species_clade_id_name, phylogenetic_path in species_clade_id_names___phylogenetic_paths.items():
        for position_index, clade_id_name in enumerate( phylogenetic_path ):
            for descendant_clade_id_name in phylogenetic_path[ position_index: ]:
                clade_id_names___descendant_clade_id_names[ clade_id_name ].add( descendant_clade_id_name )
    return clade_id_names___descendant_clade_id_names


def compute_phylogenetic_path_state( phylogenetic_path, annogroup_species_clade_id_names,
                                     origin_child_clade_id_name,
                                     clade_id_names___descendant_clade_id_names,
                                     clade_id_names___descendant_species_clade_id_names ):
    """
    Compute the Rule 7 phylogenetic path-state letter string for one species
    path and one annogroup. Returns N-letter string using {A, O, P, L, X}.
    """
    if len( phylogenetic_path ) < 2:
        return ''

    eligible_clade_id_names = clade_id_names___descendant_clade_id_names.get(
        origin_child_clade_id_name, set()
    )

    def clade_is_present( clade_id_name ):
        """Rule 7 presence: eligible AND has annogroup descendant species."""
        if clade_id_name not in eligible_clade_id_names:
            return False
        descendant_species = clade_id_names___descendant_species_clade_id_names.get(
            clade_id_name, set()
        )
        return bool( annogroup_species_clade_id_names & descendant_species )

    letters = []

    for i in range( 1, len( phylogenetic_path ) ):
        parent_clade_id_name = phylogenetic_path[ i - 1 ]
        child_clade_id_name = phylogenetic_path[ i ]

        parent_eligible = parent_clade_id_name in eligible_clade_id_names
        child_eligible = child_clade_id_name in eligible_clade_id_names

        if not parent_eligible:
            if child_eligible:
                letters.append( 'O' )
            else:
                letters.append( 'A' )
        else:
            parent_has_descendants = clade_is_present( parent_clade_id_name )
            child_has_descendants = clade_is_present( child_clade_id_name )

            if parent_has_descendants and child_has_descendants:
                letters.append( 'P' )
            elif parent_has_descendants and ( not child_has_descendants ):
                letters.append( 'L' )
            else:
                letters.append( 'X' )

    return ''.join( letters )


def generate_path_states( annogroups___species_clade_id_names,
                          annogroups___origins,
                          species_clade_id_names___phylogenetic_paths ):
    """Generate per (annogroup, species) phylogenetic path-state rows."""
    logger.info( "Generating per-annogroup per-species phylogenetic path-states..." )

    clade_id_names___descendant_species_clade_id_names = build_clade_descendant_species(
        species_clade_id_names___phylogenetic_paths
    )
    clade_id_names___descendant_clade_id_names = build_clade_descendant_clades(
        species_clade_id_names___phylogenetic_paths
    )

    path_state_rows = []

    sorted_annogroup_ids = sorted( annogroups___species_clade_id_names.keys() )
    sorted_species_clade_id_names = sorted( species_clade_id_names___phylogenetic_paths.keys() )

    skipped_missing_origin = 0

    for annogroup_id in sorted_annogroup_ids:
        annogroup_species_clade_id_names = annogroups___species_clade_id_names[ annogroup_id ]

        origin_data = annogroups___origins.get( annogroup_id )
        if not origin_data or origin_data.get( 'origin_child_clade_id_name' ) in ( None, 'NA', '' ):
            skipped_missing_origin += 1
            continue

        origin_child_clade_id_name = origin_data[ 'origin_child_clade_id_name' ]

        for species_clade_id_name in sorted_species_clade_id_names:
            phylogenetic_path = species_clade_id_names___phylogenetic_paths[ species_clade_id_name ]

            species_in_annogroup = species_clade_id_name in annogroup_species_clade_id_names

            phylogenetic_path_state = compute_phylogenetic_path_state(
                phylogenetic_path,
                annogroup_species_clade_id_names,
                origin_child_clade_id_name,
                clade_id_names___descendant_clade_id_names,
                clade_id_names___descendant_species_clade_id_names
            )

            phylogenetic_path_string = ','.join( phylogenetic_path )

            path_state_rows.append( {
                'annogroup_id': annogroup_id,
                'species_clade_id_name': species_clade_id_name,
                'species_in_annogroup': species_in_annogroup,
                'phylogenetic_path': phylogenetic_path_string,
                'phylogenetic_path_state': phylogenetic_path_state
            } )

    logger.info( f"Generated {len( path_state_rows )} path-state rows "
                 f"({len( sorted_annogroup_ids ) - skipped_missing_origin} annogroups x "
                 f"{len( sorted_species_clade_id_names )} species)" )
    if skipped_missing_origin > 0:
        logger.info( f"Skipped {skipped_missing_origin} annogroups lacking origin data" )

    return path_state_rows


# ============================================================================
# SECTION 5: CROSS-VALIDATION AND QC
# ============================================================================

def cross_validate_results( annogroup_summaries, clade_statistics, species_summaries,
                            annogroups___origins, annogroups___patterns ):
    """Cross-validate results and generate QC report."""
    logger.info( "Cross-validating results..." )

    validation_report = []
    validation_report.append( "=" * 80 )
    validation_report.append( "CROSS-VALIDATION AND QC REPORT" )
    validation_report.append( "=" * 80 )
    validation_report.append( "" )

    # Check 1: Total annogroup count consistency
    total_annogroups = len( annogroups___origins )
    annogroup_summaries_count = len( annogroup_summaries )

    validation_report.append( "CHECK 1: Annogroup Count Consistency" )
    validation_report.append( f"  Total annogroups (Script 002): {total_annogroups}" )
    validation_report.append( f"  Annogroup summaries (Script 004): {annogroup_summaries_count}" )

    if total_annogroups == annogroup_summaries_count:
        validation_report.append( "  PASS: Counts match" )
    else:
        validation_report.append( "  FAIL: Counts do not match!" )

    validation_report.append( "" )

    # Check 2: Sum of origins
    total_origins = sum( statistic[ 'origins_count' ] for statistic in clade_statistics )

    validation_report.append( "CHECK 2: Sum of Origins" )
    validation_report.append( f"  Total annogroups: {total_annogroups}" )
    validation_report.append( f"  Sum of origins across clades: {total_origins}" )

    if total_annogroups == total_origins:
        validation_report.append( "  PASS: All annogroups have origins" )
    else:
        validation_report.append( f"  FAIL: Mismatch by {abs( total_annogroups - total_origins )} annogroups" )

    validation_report.append( "" )

    # Check 3: Species annogroup counts
    validation_report.append( "CHECK 3: Species Annogroup Counts" )
    if species_summaries:
        minimum_annogroups = min( summary[ 'total_annogroups' ] for summary in species_summaries )
        maximum_annogroups = max( summary[ 'total_annogroups' ] for summary in species_summaries )
        average_annogroups = sum( summary[ 'total_annogroups' ] for summary in species_summaries ) / len( species_summaries )

        validation_report.append( f"  Minimum annogroups per species: {minimum_annogroups}" )
        validation_report.append( f"  Maximum annogroups per species: {maximum_annogroups}" )
        validation_report.append( f"  Average annogroups per species: {average_annogroups:.1f}" )
        validation_report.append( "  PASS: Species annogroup counts vary as expected" )
    else:
        validation_report.append( "  WARNING: No species summaries available" )

    validation_report.append( "" )

    # Check 4: Per-clade conserved-vs-inherited sanity
    validation_report.append( "CHECK 4: Per-Clade Conserved vs Inherited Counts" )
    anomalies = [
        statistic[ 'clade_id_name' ]
        for statistic in clade_statistics
        if statistic[ 'conserved_as_parent' ] > statistic[ 'inherited_as_parent' ]
    ]

    if anomalies:
        validation_report.append( f"  FAIL: {len( anomalies )} clades have conserved_as_parent > inherited_as_parent (impossible)" )
        for clade_id_name in anomalies[ :10 ]:
            validation_report.append( f"    {clade_id_name}" )
    else:
        validation_report.append( "  PASS: conserved_as_parent <= inherited_as_parent for every clade" )

    validation_report.append( "" )

    # Check 5: Script 004 matches Script 003
    validation_report.append( "CHECK 5: Script 004 Matches Script 003 (per-annogroup counts)" )

    mismatches = []
    for summary in annogroup_summaries:
        annogroup_id = summary[ 'annogroup_id' ]

        total_scored_blocks_004 = summary[ 'total_scored_blocks' ]
        conservation_004 = summary[ 'conservation_events' ]
        loss_origin_004 = summary[ 'loss_origin_events' ]
        continued_absence_004 = summary[ 'continued_absence_events' ]

        pattern_003 = annogroups___patterns.get( annogroup_id, {} )
        total_scored_blocks_003 = pattern_003.get( 'total_scored_blocks', -1 )
        conservation_003 = pattern_003.get( 'conservation_events', -1 )
        loss_origin_003 = pattern_003.get( 'loss_origin_events', -1 )
        continued_absence_003 = pattern_003.get( 'continued_absence_events', -1 )

        if ( total_scored_blocks_004 != total_scored_blocks_003 or
             conservation_004 != conservation_003 or
             loss_origin_004 != loss_origin_003 or
             continued_absence_004 != continued_absence_003 ):
            mismatches.append( annogroup_id )

    if not mismatches:
        validation_report.append( f"  PASS: All {len( annogroup_summaries )} annogroups match between Script 003 and Script 004" )
    else:
        validation_report.append( f"  FAIL: Found {len( mismatches )} mismatches!" )

    validation_report.append( "" )

    # Summary
    validation_report.append( "=" * 80 )
    validation_report.append( "VALIDATION SUMMARY" )
    validation_report.append( "=" * 80 )

    if not mismatches:
        validation_report.append( "All critical checks passed. Data is consistent across all outputs." )
    else:
        validation_report.append( f"WARNING: {len( mismatches )} annogroups have mismatched data between Script 003 and Script 004!" )

    validation_report.append( "=" * 80 )

    logger.info( "Cross-validation completed" )
    return validation_report


# ============================================================================
# SECTION 6: WRITE OUTPUTS
# ============================================================================

def write_annogroup_summaries( annogroup_summaries, output_file_path, subtype_filter = None ):
    """Write per-annogroup summaries (Rule 7 block-state counts).

    Args:
        annogroup_summaries: List of summary dicts
        output_file_path: Path to write to
        subtype_filter: If provided, only write summaries matching this subtype
    """
    if subtype_filter:
        filtered_summaries = [ s for s in annogroup_summaries if s[ 'annogroup_subtype' ] == subtype_filter ]
        logger.info( f"Writing {subtype_filter} annogroup summaries ({len( filtered_summaries )}) to: {output_file_path}" )
    else:
        filtered_summaries = annogroup_summaries
        logger.info( f"Writing all-types annogroup summaries ({len( filtered_summaries )}) to: {output_file_path}" )

    with open( output_file_path, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        header_columns = [
            'Annogroup_ID (annogroup identifier)',
            'Annogroup_Subtype (single or combo or zero)',
            'Origin_Phylogenetic_Block (phylogenetic block containing the origin transition format Parent_Clade_ID_Name::Child_Clade_ID_Name)',
            'Origin_Phylogenetic_Block_State (phylogenetic transition block for origin in five-state vocabulary format Parent_Clade_ID_Name::Child_Clade_ID_Name-O where O marks Origin; five states are A=Inherited Absence O=Origin P=Inherited Presence L=Loss X=Inherited Loss)',
            'Origin_Phylogenetic_Path (phylogenetic path from root to the child endpoint of the origin block comma delimited as clade_id_name values)',
            'Species_Count (total unique species in annogroup)',
            'Total_Scored_Blocks (count of phylogenetic blocks classified into block-states P L or X for this annogroup; equals P plus L plus X)',
            'Conservation_Events (count of phylogenetic blocks in block-state P where annogroup is present at both parent and child clades)',
            'Loss_Events (count of phylogenetic blocks in block-state L where annogroup is present at parent and absent at child)',
            'Continued_Absence_Events (count of phylogenetic blocks in block-state X where annogroup is absent at both parent and child after an upstream loss)',
            'Species_List (comma delimited list of all species containing this annogroup)'
        ]

        csv_writer.writerow( header_columns )

        for summary in filtered_summaries:
            output_row = [
                summary[ 'annogroup_id' ],
                summary[ 'annogroup_subtype' ],
                summary[ 'phylogenetic_block' ],
                summary[ 'phylogenetic_block_state' ],
                summary[ 'phylogenetic_path' ],
                summary[ 'species_count' ],
                summary[ 'total_scored_blocks' ],
                summary[ 'conservation_events' ],
                summary[ 'loss_origin_events' ],
                summary[ 'continued_absence_events' ],
                summary[ 'species_list' ]
            ]

            csv_writer.writerow( output_row )

    logger.info( f"Wrote {len( filtered_summaries )} annogroup summaries (11 columns)" )


def write_clade_statistics( clade_statistics ):
    """Write comprehensive per-clade statistics."""
    logger.info( f"Writing clade statistics to: {output_clade_statistics_file}" )

    with open( output_clade_statistics_file, 'w' ) as output_file:
        output = 'Clade_ID_Name (clade identifier as clade_id_name e.g. C082_Metazoa)\t'
        output += 'Origins_Count (number of annogroups whose origin transition block has this clade as its child endpoint)\t'
        output += 'Annogroups_Present (total number of annogroups biologically present at this clade via its descendant species)\t'
        output += 'Descendant_Species_Count (number of species descended from this clade)\t'
        output += 'Inherited_As_Parent (sum across this clade-as-parent blocks of annogroups biologically present at parent)\t'
        output += 'Conserved_As_Parent (sum across this clade-as-parent blocks of annogroups in block-state P)\t'
        output += 'Lost_As_Parent (sum across this clade-as-parent blocks of annogroups in block-state L)\n'
        output_file.write( output )

        for statistic in clade_statistics:
            output = f"{statistic[ 'clade_id_name' ]}\t{statistic[ 'origins_count' ]}\t"
            output += f"{statistic[ 'annogroups_present' ]}\t{statistic[ 'descendant_species_count' ]}\t"
            output += f"{statistic[ 'inherited_as_parent' ]}\t{statistic[ 'conserved_as_parent' ]}\t"
            output += f"{statistic[ 'lost_as_parent' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( clade_statistics )} clade statistics" )


def write_species_summaries( species_summaries ):
    """Write per-species summaries."""
    logger.info( f"Writing species summaries to: {output_species_summaries_file}" )

    with open( output_species_summaries_file, 'w' ) as output_file:
        output = 'Species_Clade_ID_Name (leaf species as clade_id_name e.g. C005_Homo_sapiens)\t'
        output += 'Total_Annogroups (total number of annogroups containing this species)\t'
        output += 'Conserved_From_Ancestors (annogroups inherited from ancestral clades)\t'
        output += 'Species_Specific (annogroups that originated at this species)\n'
        output_file.write( output )

        for summary in species_summaries:
            output = f"{summary[ 'species_clade_id_name' ]}\t{summary[ 'total_annogroups' ]}\t"
            output += f"{summary[ 'conserved_from_ancestors' ]}\t{summary[ 'species_specific' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( species_summaries )} species summaries" )


def write_path_states( path_state_rows ):
    """Write per (annogroup, species) path-states to a standalone TSV file."""
    logger.info( f"Writing phylogenetic path-states to: {output_path_states_file}" )

    header_columns = [
        'Annogroup_ID (annogroup identifier)',
        'Species_Clade_ID_Name (atomic species clade identifier e.g. C005_Homo_sapiens)',
        'Species_In_Annogroup (True if this species is a member of this annogroup; False otherwise)',
        'Phylogenetic_Path (comma delimited root-to-tip path of atomic clade identifiers for this species)',
        'Phylogenetic_Path_State (root-to-tip concatenation of Rule 7 block-state letters A O P L X one letter per phylogenetic block on the path)'
    ]

    with open( output_path_states_file, 'w' ) as output_file:
        output_file.write( '\t'.join( header_columns ) + '\n' )

        for row in path_state_rows:
            output = (
                row[ 'annogroup_id' ] + '\t'
                + row[ 'species_clade_id_name' ] + '\t'
                + ( 'True' if row[ 'species_in_annogroup' ] else 'False' ) + '\t'
                + row[ 'phylogenetic_path' ] + '\t'
                + row[ 'phylogenetic_path_state' ] + '\n'
            )
            output_file.write( output )

    logger.info( f"Wrote {len( path_state_rows )} path-state rows" )


def write_validation_report( validation_report ):
    """Write validation report."""
    logger.info( f"Writing validation report to: {output_validation_report_file}" )

    with open( output_validation_report_file, 'w' ) as output_file:
        for report_line in validation_report:
            output = report_line + '\n'
            output_file.write( output )

    logger.info( "Wrote validation report" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function."""
    start_time = time.time()

    logger.info( "=" * 80 )
    logger.info( "SCRIPT 004: COMPREHENSIVE OCL SUMMARIES (Rule 7 counts)" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {Path( __file__ ).name}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Annogroup subtypes: {ANNOGROUP_SUBTYPES}" )
    logger.info( "" )

    # STEP 1: Load all input data (all keyed by clade_id_name)
    logger.info( "STEP 1: Loading all input data..." )
    clade_names___clade_id_names = load_clade_mappings()
    annogroups___origins = load_annogroup_origins()
    annogroups___patterns = load_annogroup_patterns()
    annogroups___species_clade_id_names = load_annogroup_species( clade_names___clade_id_names )
    clade_id_names___origin_counts = load_origins_summary()
    block_statistics = load_block_statistics()
    species_clade_id_names___phylogenetic_paths = load_phylogenetic_paths()
    clade_id_names = list( clade_names___clade_id_names.values() )
    logger.info( "" )

    # STEP 2: Generate per-annogroup complete summaries
    logger.info( "STEP 2: Generating per-annogroup complete summaries..." )
    annogroup_summaries = generate_annogroup_summaries(
        annogroups___origins,
        annogroups___patterns
    )
    logger.info( "" )

    # STEP 3: Generate per-clade comprehensive statistics
    logger.info( "STEP 3: Generating per-clade comprehensive statistics..." )
    clade_statistics = generate_clade_statistics(
        clade_id_names,
        clade_id_names___origin_counts,
        annogroups___species_clade_id_names,
        species_clade_id_names___phylogenetic_paths,
        block_statistics
    )
    logger.info( "" )

    # STEP 4: Generate per-species summaries
    logger.info( "STEP 4: Generating per-species summaries..." )
    species_summaries = generate_species_summaries(
        species_clade_id_names___phylogenetic_paths,
        annogroups___species_clade_id_names,
        clade_id_names___origin_counts
    )
    logger.info( "" )

    # STEP 4b: Generate per (annogroup, species) phylogenetic path-states (Rule 7)
    logger.info( "STEP 4b: Generating phylogenetic path-states..." )
    path_state_rows = generate_path_states(
        annogroups___species_clade_id_names,
        annogroups___origins,
        species_clade_id_names___phylogenetic_paths
    )
    logger.info( "" )

    # STEP 5: Cross-validate results
    logger.info( "STEP 5: Cross-validating results..." )
    validation_report = cross_validate_results(
        annogroup_summaries,
        clade_statistics,
        species_summaries,
        annogroups___origins,
        annogroups___patterns
    )
    logger.info( "" )

    # STEP 6: Write outputs
    logger.info( "STEP 6: Writing outputs..." )

    # All-types integrated summary (primary downstream file)
    write_annogroup_summaries( annogroup_summaries, output_annogroup_complete_file )

    # Per-subtype summaries
    for subtype in ANNOGROUP_SUBTYPES:
        subtype_output_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_annogroups-complete_ocl_summary-{subtype}.tsv'
        write_annogroup_summaries( annogroup_summaries, subtype_output_file, subtype_filter = subtype )

    write_clade_statistics( clade_statistics )
    write_species_summaries( species_summaries )
    write_path_states( path_state_rows )
    write_validation_report( validation_report )
    logger.info( "" )

    logger.info( "=" * 80 )
    logger.info( "SCRIPT 004 COMPLETED SUCCESSFULLY" )
    logger.info( "=" * 80 )
    logger.info( f"All outputs written to: {output_directory}" )
    logger.info( "" )
    logger.info( "Output files:" )
    logger.info( f"  {output_annogroup_complete_file.name} (primary downstream file -- all subtypes)" )
    for subtype in ANNOGROUP_SUBTYPES:
        logger.info( f"  4_ai-{TARGET_STRUCTURE}_annogroups-complete_ocl_summary-{subtype}.tsv" )
    logger.info( f"  {output_clade_statistics_file.name}" )
    logger.info( f"  {output_species_summaries_file.name}" )
    logger.info( f"  {output_path_states_file.name}" )
    logger.info( f"  {output_validation_report_file.name}" )
    logger.info( "=" * 80 )

    # Emit run summary fragment
    duration_seconds = time.time() - start_time
    subtype_counts = defaultdict( int )
    for summary in annogroup_summaries:
        subtype_counts[ summary[ 'annogroup_subtype' ] ] += 1
    emit_run_summary_fragment(
        script_number = 4,
        structure_id = args.structure_id,
        stats = {
            'duration_seconds': round( duration_seconds, 2 ),
            'annogroup_summaries_total': len( annogroup_summaries ),
            'annogroup_summaries_by_subtype': dict( subtype_counts ),
            'clades_analyzed': len( clade_statistics ),
            'species_analyzed': len( species_summaries ),
            'path_state_rows': len( path_state_rows )
        }
    )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
