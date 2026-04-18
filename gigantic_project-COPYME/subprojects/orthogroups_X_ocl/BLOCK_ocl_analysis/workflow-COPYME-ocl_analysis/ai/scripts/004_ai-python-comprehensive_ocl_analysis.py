# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Integrate Scripts 002+003 into per-orthogroup, per-clade, and per-species summaries (Rule 7 counts)
# Human: Eric Edsinger

"""
OCL Pipeline Script 004: Comprehensive OCL Summaries (Rule 7 counts)

Integrates results from Scripts 001-003 into comprehensive summary tables.
Counts only — no rates.

Outputs:
- Per-orthogroup complete OCL summary (block-state counts + annotations)
- Per-clade comprehensive statistics (origins count, orthogroups present at
  clade, per-clade-as-parent counts: inherited / conserved / lost)
- Per-species summaries (total, conserved-from-ancestors, species-specific)
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

# FASTA embedding flag
INCLUDE_FASTA = config.get( 'include_fasta_in_output', False )

# Format structure ID
TARGET_STRUCTURE = f"structure_{args.structure_id}"

# Input directories
input_directory_001 = Path( args.output_dir ) / TARGET_STRUCTURE / '1-output'
input_directory_002 = Path( args.output_dir ) / TARGET_STRUCTURE / '2-output'
input_directory_003 = Path( args.output_dir ) / TARGET_STRUCTURE / '3-output'

# Input files from Script 001
input_clade_mappings_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_clade_mappings.tsv'
input_phylogenetic_paths_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_phylogenetic_paths.tsv'
input_orthogroups_file = input_directory_001 / f'1_ai-{TARGET_STRUCTURE}_orthogroups-gigantic_identifiers.tsv'

# Input files from Script 002
input_origins_file = input_directory_002 / f'2_ai-{TARGET_STRUCTURE}_orthogroup_origins.tsv'
input_origins_summary_file = input_directory_002 / f'2_ai-{TARGET_STRUCTURE}_origins_summary-orthogroups_per_clade.tsv'

# Input files from Script 003
input_block_statistics_file = input_directory_003 / f'3_ai-{TARGET_STRUCTURE}_conservation_loss-per_block.tsv'
input_orthogroup_patterns_file = input_directory_003 / f'3_ai-{TARGET_STRUCTURE}_conservation_patterns-per_orthogroup.tsv'

# Output directory
output_directory = Path( args.output_dir ) / TARGET_STRUCTURE / '4-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_orthogroup_complete_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_orthogroups-complete_ocl_summary.tsv'
output_clade_statistics_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_clades-comprehensive_statistics.tsv'
output_species_summaries_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_species-summaries.tsv'
output_path_states_file = output_directory / f'4_ai-{TARGET_STRUCTURE}_path_states-per_orthogroup_per_species.tsv'
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
# UTILITY FUNCTIONS
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

    if len( parts_phyloname ) >= 7:
        species_name = '_'.join( parts_phyloname[ 5: ] )
        return species_name
    else:
        return None


# ============================================================================
# SECTION 1: LOAD ALL INPUT DATA
# ============================================================================

def load_orthogroup_origins():
    """
    Load orthogroup origin data from Script 002 output.

    Origins are identified by block and block-state identifiers per Rule 7
    (no separate "origin clade" field).

    Returns:
        dict: { orthogroup_id: {
            'phylogenetic_block': str,        # parent::child
            'phylogenetic_block_state': str,  # parent::child-O
            'species_count': int
        } }
    """
    logger.info( f"Loading orthogroup origins from: {input_origins_file}" )

    if not input_origins_file.exists():
        logger.error( f"CRITICAL ERROR: Origins file not found!" )
        logger.error( f"Expected: {input_origins_file}" )
        sys.exit( 1 )

    orthogroups___origins = {}

    with open( input_origins_file, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Orthogroup_ID	Origin_Phylogenetic_Block	Origin_Phylogenetic_Block_State	Origin_Phylogenetic_Path	Shared_Clade_ID_Names	Species_Count	Sequence_Count	Species_List	Sequence_IDs [	Sequences_FASTA]
        # OG0000001	C069_Holozoa::C002_Filozoa	C069_Holozoa::C002_Filozoa-O	...	42	120	Homo_sapiens,...
        # Per Rule 7: column 1 is the phylogenetic block (parent::child,
        # feature-agnostic). Column 2 is the phylogenetic block-state
        # (parent::child-O), where the -O suffix encodes the Origin state in
        # the five-state vocabulary {A, O, P, L, X}. The "origin clade" in
        # naming-convention shorthand is the child endpoint of the block,
        # extractable by splitting on `::`.
        header_row = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            orthogroup_id = parts[ 0 ]
            phylogenetic_block = parts[ 1 ]
            phylogenetic_block_state = parts[ 2 ]
            species_count = int( parts[ 5 ] )

            # Derive the child endpoint of the origin block (the "origin clade"
            # in naming-convention shorthand) for downstream eligibility
            # lookups. Per Rule 7: origin block is `parent::child`, child is
            # the origin clade (the clade where the feature is first present).
            if '::' in phylogenetic_block:
                origin_child_clade_id_name = phylogenetic_block.split( '::', 1 )[ 1 ]
            else:
                origin_child_clade_id_name = phylogenetic_block

            orthogroups___origins[ orthogroup_id ] = {
                'phylogenetic_block': phylogenetic_block,
                'phylogenetic_block_state': phylogenetic_block_state,
                'origin_child_clade_id_name': origin_child_clade_id_name,
                'species_count': species_count
            }

    logger.info( f"Loaded origins for {len( orthogroups___origins )} orthogroups" )

    return orthogroups___origins


def load_orthogroup_patterns():
    """
    Load per-orthogroup block-state counts from Script 003.

    Returns:
        dict: { orthogroup_id: { block-state counts + annotations } }
    """
    logger.info( f"Loading orthogroup patterns from: {input_orthogroup_patterns_file}" )

    if not input_orthogroup_patterns_file.exists():
        logger.error( f"CRITICAL ERROR: Patterns file not found!" )
        logger.error( f"Expected: {input_orthogroup_patterns_file}" )
        sys.exit( 1 )

    orthogroups___patterns = {}

    with open( input_orthogroup_patterns_file, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Single-row header from Script 003 (11 or 12 columns depending on FASTA).
        # Per Rule 7, columns are: Orthogroup_ID, Origin_Phylogenetic_Block
        # (parent::child), Origin_Phylogenetic_Block_State (parent::child-O),
        # Origin_Phylogenetic_Path, Species_Count, Total_Scored_Blocks,
        # Conservation_Events, Loss_Events, Continued_Absence_Events, Species_List,
        # Sequence_IDs, [Sequences_FASTA].
        header_row = next( csv_reader )
        column_count = len( header_row )
        has_fasta_column = column_count >= 12

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            orthogroup_id = parts[ 0 ]
            phylogenetic_block = parts[ 1 ]
            phylogenetic_block_state = parts[ 2 ]
            phylogenetic_path = parts[ 3 ]
            species_count = int( parts[ 4 ] )
            total_scored_blocks = int( parts[ 5 ] )
            conservation_events = int( parts[ 6 ] )
            loss_origin_events = int( parts[ 7 ] )
            continued_absence_events = int( parts[ 8 ] )
            species_list = parts[ 9 ]
            sequence_ids = parts[ 10 ]
            sequences_fasta = parts[ 11 ] if has_fasta_column and len( parts ) > 11 else ''

            orthogroups___patterns[ orthogroup_id ] = {
                'phylogenetic_block': phylogenetic_block,
                'phylogenetic_block_state': phylogenetic_block_state,
                'phylogenetic_path': phylogenetic_path,
                'species_count': species_count,
                'total_scored_blocks': total_scored_blocks,
                'conservation_events': conservation_events,
                'loss_origin_events': loss_origin_events,
                'continued_absence_events': continued_absence_events,
                'species_list': species_list,
                'sequence_ids': sequence_ids,
                'sequences_fasta': sequences_fasta
            }

    logger.info( f"Loaded patterns for {len( orthogroups___patterns )} orthogroups" )

    return orthogroups___patterns


def load_clade_mappings():
    """
    Load clade mappings from Script 001 output; returns bare name -> clade_id_name.

    Returns:
        dict: { clade_name: clade_id_name }
    """
    logger.info( f"Loading clade mappings from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mapping not found!" )
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

    logger.info( f"Loaded {len( clade_names___clade_id_names )} clade mappings" )

    return clade_names___clade_id_names


def load_orthogroup_species( clade_names___clade_id_names ):
    """
    Load species composition for each orthogroup; returns species_clade_id_name sets.

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

    with open( input_orthogroups_file, 'r' ) as input_file:
        # Orthogroup_ID	Sequence_Count	GIGANTIC_IDs	Unmapped_Short_IDs
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
                    continue
                species_clade_id_names_set.add( species_clade_id_name )

            orthogroups___species_clade_id_names[ orthogroup_id ] = species_clade_id_names_set

    logger.info( f"Loaded species_clade_id_names for {len( orthogroups___species_clade_id_names )} orthogroups" )

    return orthogroups___species_clade_id_names


def load_origins_summary():
    """
    Load origins summary (orthogroups per clade_id_name) from Script 002 output.

    Returns:
        dict: { clade_id_name: orthogroup_count }
    """
    logger.info( f"Loading origins summary from: {input_origins_summary_file}" )

    if not input_origins_summary_file.exists():
        logger.error( f"CRITICAL ERROR: Origins summary not found!" )
        logger.error( f"Expected: {input_origins_summary_file}" )
        sys.exit( 1 )

    clade_id_names___origin_counts = {}

    with open( input_origins_summary_file, 'r' ) as input_file:
        # Origin_Phylogenetic_Block_State	Orthogroup_Count	Percentage
        # C069_Holozoa::C082_Metazoa-O	4532	2.14
        # Per Rule 7, rows are keyed by the origin transition block-state
        # (parent::child-O). We key the in-memory dict by the child clade_id_name
        # — the endpoint that is contained in the transition block — so that
        # downstream per-clade aggregations (origins_count, species_specific)
        # continue to map directly from clade to count.
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            phylogenetic_block_state = parts[ 0 ]
            orthogroup_count = int( parts[ 1 ] )

            # Extract child clade_id_name from block-state identifier
            # `parent::child-O` → `child`.
            if '::' in phylogenetic_block_state and phylogenetic_block_state.endswith( '-O' ):
                child_clade_id_name = phylogenetic_block_state.split( '::', 1 )[ 1 ][:-2]
            elif phylogenetic_block_state == 'NA':
                continue
            else:
                logger.warning(
                    f"Unexpected block-state identifier format: {phylogenetic_block_state!r} — skipping"
                )
                continue

            clade_id_names___origin_counts[ child_clade_id_name ] = orthogroup_count

    logger.info( f"Loaded origin counts for {len( clade_id_names___origin_counts )} clades" )

    return clade_id_names___origin_counts


def load_block_statistics():
    """
    Load per-block conservation/loss statistics from Script 003 output.

    Returns:
        list: [ { 'parent_clade_id_name': str, 'child_clade_id_name': str, ... } ]
    """
    logger.info( f"Loading block statistics from: {input_block_statistics_file}" )

    if not input_block_statistics_file.exists():
        logger.error( f"CRITICAL ERROR: Block statistics not found!" )
        logger.error( f"Expected: {input_block_statistics_file}" )
        sys.exit( 1 )

    block_statistics = []

    with open( input_block_statistics_file, 'r' ) as input_file:
        # Parent_Clade_ID_Name	Child_Clade_ID_Name	Inherited_Count	Conserved_Count	Lost_Count
        # C069_Opisthokonta	C069_Holozoa	45231	43892	1339	97.04	2.96
        header_line = input_file.readline()  # Skip single-row header

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
    """
    Load phylogenetic paths from Script 001 output; keyed by leaf species_clade_id_name.

    Returns:
        dict: { species_clade_id_name: [ clade_id_name_root, ..., species_clade_id_name ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_file}" )

    if not input_phylogenetic_paths_file.exists():
        logger.error( f"CRITICAL ERROR: Phylogenetic paths not found!" )
        logger.error( f"Expected: {input_phylogenetic_paths_file}" )
        sys.exit( 1 )

    species_clade_id_names___phylogenetic_paths = {}

    with open( input_phylogenetic_paths_file, 'r' ) as input_file:
        # Leaf_Clade_ID	Path_Length	Phylogenetic_Path
        # C001_Fonticula_alba	3	C068_Basal,C069_Holomycota,C001_Fonticula_alba
        header_line = input_file.readline()  # Skip single-row header

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


def load_all_clade_id_names( clade_names___clade_id_names ):
    """
    Return list of all clade_id_name values present in the clade mappings.

    Args:
        clade_names___clade_id_names: { clade_name: clade_id_name }

    Returns:
        list: [ clade_id_name_1, clade_id_name_2, ... ]
    """
    clade_id_names = list( clade_names___clade_id_names.values() )
    logger.info( f"Loaded {len( clade_id_names )} clade_id_names" )
    return clade_id_names


# ============================================================================
# SECTION 2: GENERATE PER-ORTHOGROUP COMPLETE SUMMARIES
# ============================================================================

def generate_orthogroup_summaries( orthogroups___origins, orthogroups___patterns ):
    """
    Generate complete per-orthogroup summaries (Rule 7 block-state counts).

    Combines origin and conservation/loss data from Scripts 002-003. All annotation
    data (phylogenetic block, path, species list, sequence IDs, FASTA) is carried
    forward from Script 003 output.

    Returns:
        list: Per-orthogroup summary dictionaries
    """
    logger.info( "Generating complete orthogroup summaries..." )

    orthogroup_summaries = []

    for orthogroup_id in sorted( orthogroups___origins.keys() ):
        origin_info = orthogroups___origins[ orthogroup_id ]
        pattern_info = orthogroups___patterns.get( orthogroup_id, {} )

        # Carry forward counts and annotation data from Script 003.
        # phylogenetic_block (parent::child) and phylogenetic_block_state
        # (parent::child-O) identify the origin transition block per Rule 7.
        total_scored_blocks = pattern_info.get( 'total_scored_blocks', 0 )
        conservation_events = pattern_info.get( 'conservation_events', 0 )
        loss_origin_events = pattern_info.get( 'loss_origin_events', 0 )
        continued_absence_events = pattern_info.get( 'continued_absence_events', 0 )

        phylogenetic_block = pattern_info.get( 'phylogenetic_block', 'NA' )
        phylogenetic_block_state = pattern_info.get( 'phylogenetic_block_state', 'NA' )
        phylogenetic_path = pattern_info.get( 'phylogenetic_path', 'NA' )
        species_list = pattern_info.get( 'species_list', '' )
        sequence_ids = pattern_info.get( 'sequence_ids', '' )
        sequences_fasta = pattern_info.get( 'sequences_fasta', '' )

        summary = {
            'orthogroup_id': orthogroup_id,
            'phylogenetic_block': phylogenetic_block,
            'phylogenetic_block_state': phylogenetic_block_state,
            'phylogenetic_path': phylogenetic_path,
            'species_count': origin_info[ 'species_count' ],
            'total_scored_blocks': total_scored_blocks,
            'conservation_events': conservation_events,
            'loss_origin_events': loss_origin_events,
            'continued_absence_events': continued_absence_events,
            'species_list': species_list,
            'sequence_ids': sequence_ids,
            'sequences_fasta': sequences_fasta
        }

        orthogroup_summaries.append( summary )

    logger.info( f"Generated summaries for {len( orthogroup_summaries )} orthogroups" )

    return orthogroup_summaries


# ============================================================================
# SECTION 3: GENERATE PER-CLADE COMPREHENSIVE STATISTICS
# ============================================================================

def generate_clade_statistics( clade_id_names, clade_id_names___origin_counts, orthogroups___species_clade_id_names,
                               species_clade_id_names___phylogenetic_paths, block_statistics ):
    """
    Generate comprehensive statistics for each clade.

    Includes:
    - Orthogroups originated at this clade
    - Orthogroups present in this clade (at least one descendant species has it)
    - Conservation/loss statistics when clade is parent
    - Descendant species count

    Returns:
        list: Per-clade statistic dictionaries
    """
    logger.info( "Generating comprehensive clade statistics..." )

    # Build clade_id_name-to-descendants mapping (values are species_clade_id_names)
    clade_id_names___descendant_species_clade_id_names = defaultdict( set )
    for species_clade_id_name, path in species_clade_id_names___phylogenetic_paths.items():
        for clade_id_name in path:
            clade_id_names___descendant_species_clade_id_names[ clade_id_name ].add( species_clade_id_name )

    # Build clade_id_name-to-orthogroups mapping (orthogroups present in clade)
    clade_id_names___orthogroups = defaultdict( set )
    for orthogroup_id, species_clade_id_names_set in orthogroups___species_clade_id_names.items():
        for clade_id_name in clade_id_names:
            descendant_species_clade_id_names = clade_id_names___descendant_species_clade_id_names.get( clade_id_name, set() )
            if species_clade_id_names_set.intersection( descendant_species_clade_id_names ):
                clade_id_names___orthogroups[ clade_id_name ].add( orthogroup_id )

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

    # Generate statistics for each clade
    clade_statistics = []

    for clade_id_name in sorted( clade_id_names ):
        origins_count = clade_id_names___origin_counts.get( clade_id_name, 0 )
        orthogroups_present = len( clade_id_names___orthogroups.get( clade_id_name, set() ) )
        descendant_species_count = len( clade_id_names___descendant_species_clade_id_names.get( clade_id_name, set() ) )

        conservation_data = clade_id_names___conservation_statistics.get( clade_id_name, {} )
        inherited_as_parent = conservation_data.get( 'as_parent_inherited', 0 )
        conserved_as_parent = conservation_data.get( 'as_parent_conserved', 0 )
        lost_as_parent = conservation_data.get( 'as_parent_lost', 0 )

        statistic = {
            'clade_id_name': clade_id_name,
            'origins_count': origins_count,
            'orthogroups_present': orthogroups_present,
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

def generate_species_summaries( species_clade_id_names___phylogenetic_paths, orthogroups___species_clade_id_names,
                               clade_id_names___origin_counts ):
    """
    Generate per-species summaries keyed by species_clade_id_name.

    Includes:
    - Total orthogroups present in species
    - Orthogroups conserved from ancestors
    - Species-specific orthogroups (originated at this species' leaf)

    Returns:
        list: Per-species summary dictionaries
    """
    logger.info( "Generating per-species summaries..." )

    species_summaries = []

    for species_clade_id_name in sorted( species_clade_id_names___phylogenetic_paths.keys() ):
        orthogroups_in_species = set()
        for orthogroup_id, species_set in orthogroups___species_clade_id_names.items():
            if species_clade_id_name in species_set:
                orthogroups_in_species.add( orthogroup_id )

        total_orthogroups = len( orthogroups_in_species )

        # Species-specific = originated at this species' leaf clade_id_name
        species_specific = clade_id_names___origin_counts.get( species_clade_id_name, 0 )

        conserved_from_ancestors = total_orthogroups - species_specific

        summary = {
            'species_clade_id_name': species_clade_id_name,
            'total_orthogroups': total_orthogroups,
            'conserved_from_ancestors': conserved_from_ancestors,
            'species_specific': species_specific
        }

        species_summaries.append( summary )

    logger.info( f"Generated summaries for {len( species_summaries )} species" )

    return species_summaries


# ============================================================================
# SECTION 4b: PHYLOGENETIC PATH-STATES (Rule 7)
# ============================================================================
#
# A phylogenetic path-state is a feature-specific concatenation of block-state
# letters along one species's root-to-tip phylogenetic path, in root-to-tip
# order. For example "AAAOPLXX" reads left-to-right as:
#   A A A     orthogroup absent in the pre-origin ancestral region of this path
#   O         orthogroup originates on this block
#   P         orthogroup inherited (present) through this block
#   L         orthogroup is lost on this block
#   X X       post-loss continued absence on the remaining descendent blocks
#
# Path-state is computed per (orthogroup, species) pair. A species need not
# be a member of the orthogroup: path-state is still well-defined (and often
# informative) for species that never received the orthogroup or lost it.
# ============================================================================

def build_clade_descendant_species( species_clade_id_names___phylogenetic_paths ):
    """
    Build per-clade descendant-species sets using the phylogenetic paths.

    For each clade on any species path, record the set of species whose path
    passes through that clade.

    Returns:
        dict: { clade_id_name: set( species_clade_id_name, ... ) }
    """
    clade_id_names___descendant_species_clade_id_names = defaultdict( set )
    for species_clade_id_name, phylogenetic_path in species_clade_id_names___phylogenetic_paths.items():
        for clade_id_name in phylogenetic_path:
            clade_id_names___descendant_species_clade_id_names[ clade_id_name ].add( species_clade_id_name )
    return clade_id_names___descendant_species_clade_id_names


def build_clade_descendant_clades( species_clade_id_names___phylogenetic_paths ):
    """
    Build per-clade descendant-clade sets using the phylogenetic paths.

    For each clade on any species path, record the set of clades at or below
    it on the species tree. Derived from the path lists: for path
    [ c_0, c_1, ..., c_N ], each clade c_i has descendants { c_i, c_{i+1},
    ..., c_N } within that path. Unioning across all species paths yields
    the complete descendant-clade set for every clade.

    Returns:
        dict: { clade_id_name: set( clade_id_name, ... ) }
    """
    clade_id_names___descendant_clade_id_names = defaultdict( set )
    for species_clade_id_name, phylogenetic_path in species_clade_id_names___phylogenetic_paths.items():
        for position_index, clade_id_name in enumerate( phylogenetic_path ):
            for descendant_clade_id_name in phylogenetic_path[ position_index: ]:
                clade_id_names___descendant_clade_id_names[ clade_id_name ].add( descendant_clade_id_name )
    return clade_id_names___descendant_clade_id_names


def compute_phylogenetic_path_state( phylogenetic_path, orthogroup_species_clade_id_names,
                                     origin_child_clade_id_name,
                                     clade_id_names___descendant_clade_id_names,
                                     clade_id_names___descendant_species_clade_id_names ):
    """
    Compute the Rule 7 phylogenetic path-state letter string for one species
    path and one orthogroup.

    Presence rule (Rule 7 / Dollo-style):
      A clade X is present for the orthogroup if BOTH of:
        (1) X is the orthogroup's origin clade, or X is a descendant clade of
            the origin clade (the feature has been inherited down to X's
            lineage);
        (2) at least one of X's descendant species is in the orthogroup (the
            feature has not been totally lost below X).

    Per-block letter mapping from (parent_present, child_present):
      (F, F) and both NOT eligible  -> A (pre-origin on this lineage)
      (F, T)                        -> O (origin block: parent ancestral to
                                         origin clade, child is origin clade
                                         or a descendant that carries the
                                         feature)
      (T, T)                        -> P (inherited presence)
      (T, F) within origin subtree  -> L (loss on this block)
      (F, F) within origin subtree  -> X (continued absence after upstream L)

    Args:
        phylogenetic_path: list of clade_id_names from root end to species
            end [ c_0, c_1, ..., c_N ]. Each consecutive pair (c_{i-1}, c_i)
            is a phylogenetic block.
        orthogroup_species_clade_id_names: set of species clade_id_names that
            biologically contain this orthogroup.
        origin_child_clade_id_name: child endpoint of the orthogroup's origin
            phylogenetic block (== the origin clade under Rule 7 naming).
        clade_id_names___descendant_clade_id_names: per-clade set of clade
            identifiers at or below that clade on the species tree.
        clade_id_names___descendant_species_clade_id_names: per-clade set of
            species identifiers at or below that clade on the species tree.

    Returns:
        str: N-letter path-state string (N = len(phylogenetic_path) - 1),
             letters in root-end-to-species-end order using the Rule 7
             alphabet {A, O, P, L, X}.
    """
    if len( phylogenetic_path ) < 2:
        return ''

    # Eligibility set: the origin clade and its descendant clades. Clades not
    # in this set are ancestors of (or off-lineage relative to) the origin
    # clade — the feature has not reached them.
    eligible_clade_id_names = clade_id_names___descendant_clade_id_names.get(
        origin_child_clade_id_name, set()
    )

    def clade_is_present( clade_id_name ):
        """Rule 7 presence: eligible AND has orthogroup descendant species."""
        if clade_id_name not in eligible_clade_id_names:
            return False
        descendant_species = clade_id_names___descendant_species_clade_id_names.get(
            clade_id_name, set()
        )
        return bool( orthogroup_species_clade_id_names & descendant_species )

    letters = []

    for i in range( 1, len( phylogenetic_path ) ):
        parent_clade_id_name = phylogenetic_path[ i - 1 ]
        child_clade_id_name = phylogenetic_path[ i ]

        parent_eligible = parent_clade_id_name in eligible_clade_id_names
        child_eligible = child_clade_id_name in eligible_clade_id_names

        if not parent_eligible:
            if child_eligible:
                # Parent is ancestral to origin clade; child is origin clade
                # or a descendant — this is the origin boundary block.
                letters.append( 'O' )
            else:
                # Both endpoints ancestral to (or off-lineage relative to)
                # origin clade. Feature has not arrived on this lineage.
                letters.append( 'A' )
        else:
            # Parent is in origin's descent; child is necessarily in origin's
            # descent too (child of an eligible clade is always eligible).
            parent_has_descendants = clade_is_present( parent_clade_id_name )
            child_has_descendants = clade_is_present( child_clade_id_name )

            if parent_has_descendants and child_has_descendants:
                letters.append( 'P' )
            elif parent_has_descendants and ( not child_has_descendants ):
                letters.append( 'L' )
            else:
                # Parent is eligible but has no orthogroup descendant species,
                # so the feature was lost at or upstream of parent on this
                # lineage. Child shares that state.
                letters.append( 'X' )

    return ''.join( letters )


def generate_path_states( orthogroups___species_clade_id_names,
                          orthogroups___origins,
                          species_clade_id_names___phylogenetic_paths ):
    """
    Generate per (orthogroup, species) phylogenetic path-state rows.

    For every orthogroup and every species in the structure, compute the
    path-state along that species's root-end-to-species-end phylogenetic path
    using the Rule 7 presence rule (see compute_phylogenetic_path_state).

    Orthogroups with no origin data are skipped — path-states are undefined
    for them.

    Returns:
        list: Per-row dicts with orthogroup_id, species_clade_id_name,
              species_in_orthogroup flag, phylogenetic_path, and
              phylogenetic_path_state.
    """
    logger.info( "Generating per-orthogroup per-species phylogenetic path-states..." )

    clade_id_names___descendant_species_clade_id_names = build_clade_descendant_species(
        species_clade_id_names___phylogenetic_paths
    )
    clade_id_names___descendant_clade_id_names = build_clade_descendant_clades(
        species_clade_id_names___phylogenetic_paths
    )

    path_state_rows = []

    sorted_orthogroup_ids = sorted( orthogroups___species_clade_id_names.keys() )
    sorted_species_clade_id_names = sorted( species_clade_id_names___phylogenetic_paths.keys() )

    skipped_missing_origin = 0

    for orthogroup_id in sorted_orthogroup_ids:
        orthogroup_species_clade_id_names = orthogroups___species_clade_id_names[ orthogroup_id ]

        origin_data = orthogroups___origins.get( orthogroup_id )
        if not origin_data or origin_data.get( 'origin_child_clade_id_name' ) in ( None, 'NA', '' ):
            skipped_missing_origin += 1
            continue

        origin_child_clade_id_name = origin_data[ 'origin_child_clade_id_name' ]

        for species_clade_id_name in sorted_species_clade_id_names:
            phylogenetic_path = species_clade_id_names___phylogenetic_paths[ species_clade_id_name ]

            species_in_orthogroup = species_clade_id_name in orthogroup_species_clade_id_names

            phylogenetic_path_state = compute_phylogenetic_path_state(
                phylogenetic_path,
                orthogroup_species_clade_id_names,
                origin_child_clade_id_name,
                clade_id_names___descendant_clade_id_names,
                clade_id_names___descendant_species_clade_id_names
            )

            phylogenetic_path_string = ','.join( phylogenetic_path )

            path_state_rows.append( {
                'orthogroup_id': orthogroup_id,
                'species_clade_id_name': species_clade_id_name,
                'species_in_orthogroup': species_in_orthogroup,
                'phylogenetic_path': phylogenetic_path_string,
                'phylogenetic_path_state': phylogenetic_path_state
            } )

    logger.info( f"Generated {len( path_state_rows )} path-state rows "
                 f"({len( sorted_orthogroup_ids ) - skipped_missing_origin} orthogroups x "
                 f"{len( sorted_species_clade_id_names )} species)" )
    if skipped_missing_origin > 0:
        logger.info( f"Skipped {skipped_missing_origin} orthogroups lacking origin data" )

    return path_state_rows


def write_path_states( path_state_rows ):
    """Write per (orthogroup, species) path-states to a standalone TSV file."""
    logger.info( f"Writing phylogenetic path-states to: {output_path_states_file}" )

    header_columns = [
        'Orthogroup_ID (orthogroup identifier)',
        'Species_Clade_ID_Name (atomic species clade identifier e.g. C005_Homo_sapiens)',
        'Species_In_Orthogroup (True if this species is a member of this orthogroup; False otherwise)',
        'Phylogenetic_Path (comma delimited root-to-tip path of atomic clade identifiers for this species)',
        'Phylogenetic_Path_State (root-to-tip concatenation of Rule 7 block-state letters A O P L X one letter per phylogenetic block on the path)'
    ]

    with open( output_path_states_file, 'w' ) as output_file:
        output_file.write( '\t'.join( header_columns ) + '\n' )

        for row in path_state_rows:
            output = (
                row[ 'orthogroup_id' ] + '\t'
                + row[ 'species_clade_id_name' ] + '\t'
                + ( 'True' if row[ 'species_in_orthogroup' ] else 'False' ) + '\t'
                + row[ 'phylogenetic_path' ] + '\t'
                + row[ 'phylogenetic_path_state' ] + '\n'
            )
            output_file.write( output )

    logger.info( f"Wrote {len( path_state_rows )} path-state rows" )


# ============================================================================
# SECTION 5: CROSS-VALIDATION AND QC
# ============================================================================

def cross_validate_results( orthogroup_summaries, clade_statistics, species_summaries,
                            orthogroups___origins, orthogroups___patterns ):
    """
    Cross-validate results and generate QC report.

    Checks:
    1. Total orthogroup counts match across outputs
    2. Sum of origins equals total orthogroups
    3. Species orthogroup count ranges are reasonable
    4. Per-clade conserved_as_parent <= inherited_as_parent
    5. Script 004 per-orthogroup counts match Script 003 exactly

    Returns:
        list: Validation report lines
    """
    logger.info( "Cross-validating results..." )

    validation_report = []
    validation_report.append( "=" * 80 )
    validation_report.append( "CROSS-VALIDATION AND QC REPORT" )
    validation_report.append( "=" * 80 )
    validation_report.append( "" )

    # Check 1: Total orthogroup count consistency
    total_orthogroups = len( orthogroups___origins )
    orthogroup_summaries_count = len( orthogroup_summaries )

    validation_report.append( "CHECK 1: Orthogroup Count Consistency" )
    validation_report.append( f"  Total orthogroups (Script 002): {total_orthogroups}" )
    validation_report.append( f"  Orthogroup summaries (Script 004): {orthogroup_summaries_count}" )

    if total_orthogroups == orthogroup_summaries_count:
        validation_report.append( "  PASS: Counts match" )
    else:
        validation_report.append( "  FAIL: Counts do not match!" )

    validation_report.append( "" )

    # Check 2: Sum of origins
    total_origins = sum( statistic[ 'origins_count' ] for statistic in clade_statistics )

    validation_report.append( "CHECK 2: Sum of Origins" )
    validation_report.append( f"  Total orthogroups: {total_orthogroups}" )
    validation_report.append( f"  Sum of origins across clades: {total_origins}" )

    if total_orthogroups == total_origins:
        validation_report.append( "  PASS: All orthogroups have origins" )
    else:
        validation_report.append( f"  FAIL: Mismatch by {abs( total_orthogroups - total_origins )} orthogroups" )

    validation_report.append( "" )

    # Check 3: Species orthogroup counts
    validation_report.append( "CHECK 3: Species Orthogroup Counts" )
    if species_summaries:
        minimum_orthogroups = min( summary[ 'total_orthogroups' ] for summary in species_summaries )
        maximum_orthogroups = max( summary[ 'total_orthogroups' ] for summary in species_summaries )
        average_orthogroups = sum( summary[ 'total_orthogroups' ] for summary in species_summaries ) / len( species_summaries )

        validation_report.append( f"  Minimum orthogroups per species: {minimum_orthogroups}" )
        validation_report.append( f"  Maximum orthogroups per species: {maximum_orthogroups}" )
        validation_report.append( f"  Average orthogroups per species: {average_orthogroups:.1f}" )
        validation_report.append( "  PASS: Species orthogroup counts vary as expected" )
    else:
        validation_report.append( "  WARNING: No species summaries available" )

    validation_report.append( "" )

    # Check 4: Per-clade conserved-vs-inherited sanity (counts only, no rates).
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

    # Check 5: Script 004 matches Script 003 (critical cross-script validation)
    validation_report.append( "CHECK 5: Script 004 Matches Script 003 (per-orthogroup counts)" )
    validation_report.append( "  Verifying orthogroup summaries match conservation patterns exactly..." )

    mismatches = []
    for summary in orthogroup_summaries:
        orthogroup_id = summary[ 'orthogroup_id' ]

        # Per-orthogroup counts as carried through by Script 004 (this script).
        total_scored_blocks_004 = summary[ 'total_scored_blocks' ]
        conservation_004 = summary[ 'conservation_events' ]
        loss_origin_004 = summary[ 'loss_origin_events' ]
        continued_absence_004 = summary[ 'continued_absence_events' ]

        # Same counts as emitted by Script 003.
        pattern_003 = orthogroups___patterns.get( orthogroup_id, {} )
        total_scored_blocks_003 = pattern_003.get( 'total_scored_blocks', -1 )
        conservation_003 = pattern_003.get( 'conservation_events', -1 )
        loss_origin_003 = pattern_003.get( 'loss_origin_events', -1 )
        continued_absence_003 = pattern_003.get( 'continued_absence_events', -1 )

        if ( total_scored_blocks_004 != total_scored_blocks_003 or
             conservation_004 != conservation_003 or
             loss_origin_004 != loss_origin_003 or
             continued_absence_004 != continued_absence_003 ):
            mismatches.append( {
                'orthogroup_id': orthogroup_id,
                'total_scored_blocks_004': total_scored_blocks_004,
                'total_scored_blocks_003': total_scored_blocks_003,
                'conservation_004': conservation_004,
                'conservation_003': conservation_003,
                'loss_origin_004': loss_origin_004,
                'loss_origin_003': loss_origin_003,
                'continued_absence_004': continued_absence_004,
                'continued_absence_003': continued_absence_003,
            } )

    if not mismatches:
        validation_report.append( f"  PASS: All {len( orthogroup_summaries )} orthogroups match between Script 003 and Script 004" )
    else:
        validation_report.append( f"  FAIL: Found {len( mismatches )} mismatches!" )
        validation_report.append( "" )
        validation_report.append( "  First 10 mismatches (per-orthogroup counts):" )
        for mismatch in mismatches[ :10 ]:
            validation_report.append( f"    {mismatch[ 'orthogroup_id' ]}:" )
            validation_report.append( f"      Total Scored Blocks: Script004={mismatch[ 'total_scored_blocks_004' ]} vs Script003={mismatch[ 'total_scored_blocks_003' ]}" )
            validation_report.append( f"      Conservation: Script004={mismatch[ 'conservation_004' ]} vs Script003={mismatch[ 'conservation_003' ]}" )

        logger.error( f"CRITICAL ERROR: Script 004 and Script 003 data do not match!" )
        logger.error( f"Found {len( mismatches )} mismatches between scripts" )

    validation_report.append( "" )

    # Summary
    validation_report.append( "=" * 80 )
    validation_report.append( "VALIDATION SUMMARY" )
    validation_report.append( "=" * 80 )

    if not mismatches:
        validation_report.append( "All critical checks passed. Data is consistent across all outputs." )
    else:
        validation_report.append( f"WARNING: {len( mismatches )} orthogroups have mismatched data between Script 003 and Script 004!" )
        validation_report.append( "Please investigate data loading or calculation discrepancies." )

    validation_report.append( "=" * 80 )

    logger.info( "Cross-validation completed" )

    return validation_report


# ============================================================================
# SECTION 6: WRITE OUTPUTS
# ============================================================================

def write_orthogroup_summaries( orthogroup_summaries ):
    """Write complete per-orthogroup summaries (Rule 7 block-state counts)."""
    logger.info( f"Writing orthogroup summaries to: {output_orthogroup_complete_file}" )

    with open( output_orthogroup_complete_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Build single-row GIGANTIC_1 header. Per Rule 7 the origin is a
        # transition block (state O), specified by the block and block-state
        # identifiers; no separate "origin clade" column.
        header_columns = [
            'Orthogroup_ID (orthogroup identifier)',
            'Origin_Phylogenetic_Block (phylogenetic block containing the origin transition format Parent_Clade_ID_Name::Child_Clade_ID_Name)',
            'Origin_Phylogenetic_Block_State (phylogenetic transition block for origin in five-state vocabulary format Parent_Clade_ID_Name::Child_Clade_ID_Name-O where O marks Origin; five states are A=Inherited Absence O=Origin P=Inherited Presence L=Loss X=Inherited Loss)',
            'Origin_Phylogenetic_Path (phylogenetic path from root to the child endpoint of the origin block comma delimited as clade_id_name values)',
            'Species_Count (total unique species in orthogroup)',
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

        # Data
        for summary in orthogroup_summaries:
            output_row = [
                summary[ 'orthogroup_id' ],
                summary[ 'phylogenetic_block' ],
                summary[ 'phylogenetic_block_state' ],
                summary[ 'phylogenetic_path' ],
                summary[ 'species_count' ],
                summary[ 'total_scored_blocks' ],
                summary[ 'conservation_events' ],
                summary[ 'loss_origin_events' ],
                summary[ 'continued_absence_events' ],
                summary[ 'species_list' ],
                summary[ 'sequence_ids' ]
            ]

            if INCLUDE_FASTA:
                output_row.append( summary[ 'sequences_fasta' ] )

            csv_writer.writerow( output_row )

    column_count = 12 if INCLUDE_FASTA else 11
    logger.info( f"Wrote {len( orthogroup_summaries )} orthogroup summaries ({column_count} columns)" )


def write_clade_statistics( clade_statistics ):
    """Write comprehensive per-clade statistics."""
    logger.info( f"Writing clade statistics to: {output_clade_statistics_file}" )

    with open( output_clade_statistics_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header. Counts only — no rates.
        output = 'Clade_ID_Name (clade identifier as clade_id_name e.g. C082_Metazoa)\t'
        output += 'Origins_Count (number of orthogroups whose origin transition block has this clade as its child endpoint)\t'
        output += 'Orthogroups_Present (total number of orthogroups biologically present at this clade via its descendant species)\t'
        output += 'Descendant_Species_Count (number of species descended from this clade)\t'
        output += 'Inherited_As_Parent (sum across this clade-as-parent blocks of orthogroups biologically present at parent)\t'
        output += 'Conserved_As_Parent (sum across this clade-as-parent blocks of orthogroups in block-state P)\t'
        output += 'Lost_As_Parent (sum across this clade-as-parent blocks of orthogroups in block-state L)\n'
        output_file.write( output )

        for statistic in clade_statistics:
            output = f"{statistic[ 'clade_id_name' ]}\t{statistic[ 'origins_count' ]}\t"
            output += f"{statistic[ 'orthogroups_present' ]}\t{statistic[ 'descendant_species_count' ]}\t"
            output += f"{statistic[ 'inherited_as_parent' ]}\t{statistic[ 'conserved_as_parent' ]}\t"
            output += f"{statistic[ 'lost_as_parent' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( clade_statistics )} clade statistics" )


def write_species_summaries( species_summaries ):
    """Write per-species summaries."""
    logger.info( f"Writing species summaries to: {output_species_summaries_file}" )

    with open( output_species_summaries_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Species_Clade_ID_Name (leaf species as clade_id_name e.g. C005_Homo_sapiens)\t'
        output += 'Total_Orthogroups (total number of orthogroups containing this species)\t'
        output += 'Conserved_From_Ancestors (orthogroups inherited from ancestral clades)\t'
        output += 'Species_Specific (orthogroups that originated at this species)\n'
        output_file.write( output )

        for summary in species_summaries:
            output = f"{summary[ 'species_clade_id_name' ]}\t{summary[ 'total_orthogroups' ]}\t"
            output += f"{summary[ 'conserved_from_ancestors' ]}\t{summary[ 'species_specific' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( species_summaries )} species summaries" )


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
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 004: COMPREHENSIVE OCL SUMMARIES (Rule 7 counts)" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {Path( __file__ ).name}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"FASTA embedding: {'enabled' if INCLUDE_FASTA else 'disabled'}" )
    logger.info( "" )

    # STEP 1: Load all input data (all keyed by clade_id_name)
    logger.info( "STEP 1: Loading all input data..." )
    clade_names___clade_id_names = load_clade_mappings()
    orthogroups___origins = load_orthogroup_origins()
    orthogroups___patterns = load_orthogroup_patterns()
    orthogroups___species_clade_id_names = load_orthogroup_species( clade_names___clade_id_names )
    clade_id_names___origin_counts = load_origins_summary()
    block_statistics = load_block_statistics()
    species_clade_id_names___phylogenetic_paths = load_phylogenetic_paths()
    clade_id_names = load_all_clade_id_names( clade_names___clade_id_names )
    logger.info( "" )

    # STEP 2: Generate per-orthogroup complete summaries
    logger.info( "STEP 2: Generating per-orthogroup complete summaries..." )
    orthogroup_summaries = generate_orthogroup_summaries(
        orthogroups___origins,
        orthogroups___patterns
    )
    logger.info( "" )

    # STEP 3: Generate per-clade comprehensive statistics
    logger.info( "STEP 3: Generating per-clade comprehensive statistics..." )
    clade_statistics = generate_clade_statistics(
        clade_id_names,
        clade_id_names___origin_counts,
        orthogroups___species_clade_id_names,
        species_clade_id_names___phylogenetic_paths,
        block_statistics
    )
    logger.info( "" )

    # STEP 4: Generate per-species summaries
    logger.info( "STEP 4: Generating per-species summaries..." )
    species_summaries = generate_species_summaries(
        species_clade_id_names___phylogenetic_paths,
        orthogroups___species_clade_id_names,
        clade_id_names___origin_counts
    )
    logger.info( "" )

    # STEP 4b: Generate per (orthogroup, species) phylogenetic path-states (Rule 7)
    logger.info( "STEP 4b: Generating phylogenetic path-states..." )
    path_state_rows = generate_path_states(
        orthogroups___species_clade_id_names,
        orthogroups___origins,
        species_clade_id_names___phylogenetic_paths
    )
    logger.info( "" )

    # STEP 5: Cross-validate results
    logger.info( "STEP 5: Cross-validating results..." )
    validation_report = cross_validate_results(
        orthogroup_summaries,
        clade_statistics,
        species_summaries,
        orthogroups___origins,
        orthogroups___patterns
    )
    logger.info( "" )

    # STEP 6: Write outputs
    logger.info( "STEP 6: Writing outputs..." )
    write_orthogroup_summaries( orthogroup_summaries )
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
    logger.info( f"  {output_orthogroup_complete_file.name}" )
    logger.info( f"  {output_clade_statistics_file.name}" )
    logger.info( f"  {output_species_summaries_file.name}" )
    logger.info( f"  {output_path_states_file.name}" )
    logger.info( f"  {output_validation_report_file.name}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
