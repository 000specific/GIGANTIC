# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Generate comprehensive OCL analysis with TEMPLATE_03 dual-metric tracking
# Human: Eric Edsinger

"""
OCL Pipeline Script 004: Comprehensive OCL Analysis (TEMPLATE_03)

Integrates results from Scripts 001-003 into comprehensive summary tables.

Outputs:
- Per-orthogroup complete OCL summary (TEMPLATE_03 metrics + annotations)
- Per-clade comprehensive statistics (origins, presence, conservation rates)
- Per-species summaries (total, conserved, species-specific orthogroups)
- Cross-validation report (Script 003 vs Script 004 consistency)

All data needed for output comes from Scripts 001-003 outputs in OUTPUT_pipeline.
No access to centralized trees_species data is needed (Script 003 already carries
phylogenetic block and path annotations from Script 002).

Usage:
    python 004_ai-python-comprehensive_ocl_analysis.py --structure_id 001 --config ../../ocl_config.yaml
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
        help = 'Path to ocl_config.yaml configuration file'
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
input_clade_mappings_file = input_directory_001 / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'
input_phylogenetic_paths_file = input_directory_001 / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
input_orthogroups_file = input_directory_001 / '1_ai-orthogroups-gigantic_identifiers.tsv'

# Input files from Script 002
input_origins_file = input_directory_002 / '2_ai-orthogroup_origins.tsv'
input_origins_summary_file = input_directory_002 / '2_ai-origins_summary-orthogroups_per_clade.tsv'

# Input files from Script 003
input_block_statistics_file = input_directory_003 / '3_ai-conservation_loss-per_block.tsv'
input_orthogroup_patterns_file = input_directory_003 / '3_ai-conservation_patterns-per_orthogroup.tsv'

# Output directory
output_directory = Path( args.output_dir ) / TARGET_STRUCTURE / '4-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
output_orthogroup_complete_file = output_directory / '4_ai-orthogroups-complete_ocl_summary.tsv'
output_clade_statistics_file = output_directory / '4_ai-clades-comprehensive_statistics.tsv'
output_species_summaries_file = output_directory / '4_ai-species-summaries.tsv'
output_validation_report_file = output_directory / '4_ai-validation_report.txt'

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

    Returns:
        dict: { orthogroup_id: { 'origin_clade': str, 'species_count': int } }
    """
    logger.info( f"Loading orthogroup origins from: {input_origins_file}" )

    if not input_origins_file.exists():
        logger.error( f"CRITICAL ERROR: Origins file not found!" )
        logger.error( f"Expected: {input_origins_file}" )
        sys.exit( 1 )

    orthogroups___origins = {}

    with open( input_origins_file, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Orthogroup_ID (orthogroup identifier)	Origin_Clade (...)	Origin_Clade_Phylogenetic_Block (...)	Origin_Clade_Phylogenetic_Path (...)	Shared_Clades (...)	Species_Count (...)	Sequence_Count (...)	Species_List (...)	Sequence_IDs (...) [	Sequences_FASTA (...)]
        # OG0000001	Filozoa	C069_Holozoa::C002_Filozoa	...	42	120	Homo_sapiens,...
        header_row = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            orthogroup_id = parts[ 0 ]
            origin_clade = parts[ 1 ]
            species_count = int( parts[ 5 ] )

            orthogroups___origins[ orthogroup_id ] = {
                'origin_clade': origin_clade,
                'species_count': species_count
            }

    logger.info( f"Loaded origins for {len( orthogroups___origins )} orthogroups" )

    return orthogroups___origins


def load_orthogroup_patterns():
    """
    Load conservation/loss patterns from Script 003 (TEMPLATE_03 format).

    Returns:
        dict: { orthogroup_id: { all TEMPLATE_03 metrics + annotations } }
    """
    logger.info( f"Loading orthogroup patterns from: {input_orthogroup_patterns_file}" )

    if not input_orthogroup_patterns_file.exists():
        logger.error( f"CRITICAL ERROR: Patterns file not found!" )
        logger.error( f"Expected: {input_orthogroup_patterns_file}" )
        sys.exit( 1 )

    orthogroups___patterns = {}

    with open( input_orthogroup_patterns_file, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Single-row header from Script 003 (16 or 17 columns depending on FASTA)
        header_row = next( csv_reader )
        column_count = len( header_row )
        has_fasta_column = column_count >= 17

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            orthogroup_id = parts[ 0 ]
            origin_clade = parts[ 1 ]
            phylogenetic_block = parts[ 2 ]
            phylogenetic_path = parts[ 3 ]
            species_count = int( parts[ 4 ] )
            total_inherited_transitions = int( parts[ 5 ] )
            conservation_events = int( parts[ 6 ] )
            loss_origin_events = int( parts[ 7 ] )
            continued_absence_events = int( parts[ 8 ] )
            loss_coverage_events = int( parts[ 9 ] )
            conservation_rate_percent = float( parts[ 10 ] )
            loss_origin_rate_percent = float( parts[ 11 ] )
            percent_tree_conserved = float( parts[ 12 ] )
            percent_tree_loss = float( parts[ 13 ] )
            species_list = parts[ 14 ]
            sequence_ids = parts[ 15 ]
            sequences_fasta = parts[ 16 ] if has_fasta_column and len( parts ) > 16 else ''

            orthogroups___patterns[ orthogroup_id ] = {
                'origin_clade': origin_clade,
                'phylogenetic_block': phylogenetic_block,
                'phylogenetic_path': phylogenetic_path,
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
                'species_list': species_list,
                'sequence_ids': sequence_ids,
                'sequences_fasta': sequences_fasta
            }

    logger.info( f"Loaded TEMPLATE_03 patterns for {len( orthogroups___patterns )} orthogroups" )

    return orthogroups___patterns


def load_orthogroup_species():
    """
    Load species composition for each orthogroup from Script 001 output.

    Returns:
        dict: { orthogroup_id: set( species_names ) }
    """
    logger.info( f"Loading orthogroup species from: {input_orthogroups_file}" )

    if not input_orthogroups_file.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found!" )
        logger.error( f"Expected: {input_orthogroups_file}" )
        sys.exit( 1 )

    orthogroups___species = {}

    with open( input_orthogroups_file, 'r' ) as input_file:
        # Orthogroup_ID (orthogroup identifier from clustering tool)	Sequence_Count (...)	GIGANTIC_IDs (comma delimited...)	Unmapped_Short_IDs (...)
        # OG0000001	45	g_001-t_001-p_001-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens,...
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            orthogroup_id = parts[ 0 ]
            gigantic_ids_string = parts[ 2 ]

            # Parse comma-delimited GIGANTIC IDs
            gigantic_ids = gigantic_ids_string.split( ',' )

            species_set = set()
            for gigantic_id in gigantic_ids:
                gigantic_id = gigantic_id.strip()
                if not gigantic_id:
                    continue
                species_name = extract_species_from_gigantic_id( gigantic_id )
                if species_name:
                    species_set.add( species_name )

            orthogroups___species[ orthogroup_id ] = species_set

    logger.info( f"Loaded species for {len( orthogroups___species )} orthogroups" )

    return orthogroups___species


def load_origins_summary():
    """
    Load origins summary (orthogroups per clade) from Script 002 output.

    Returns:
        dict: { clade_name: orthogroup_count }
    """
    logger.info( f"Loading origins summary from: {input_origins_summary_file}" )

    if not input_origins_summary_file.exists():
        logger.error( f"CRITICAL ERROR: Origins summary not found!" )
        logger.error( f"Expected: {input_origins_summary_file}" )
        sys.exit( 1 )

    clades___origin_counts = {}

    with open( input_origins_summary_file, 'r' ) as input_file:
        # Origin_Clade (phylogenetic clade where orthogroup originated)	Orthogroup_Count (count of orthogroups originating at this clade)	Percentage (percentage of total orthogroups)
        # Basal	4532	2.14
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            clade_name = parts[ 0 ]
            orthogroup_count = int( parts[ 1 ] )

            clades___origin_counts[ clade_name ] = orthogroup_count

    logger.info( f"Loaded origin counts for {len( clades___origin_counts )} clades" )

    return clades___origin_counts


def load_block_statistics():
    """
    Load per-block conservation/loss statistics from Script 003 output.

    Returns:
        list: [ { 'parent_clade': str, 'child_clade': str, ... } ]
    """
    logger.info( f"Loading block statistics from: {input_block_statistics_file}" )

    if not input_block_statistics_file.exists():
        logger.error( f"CRITICAL ERROR: Block statistics not found!" )
        logger.error( f"Expected: {input_block_statistics_file}" )
        sys.exit( 1 )

    block_statistics = []

    with open( input_block_statistics_file, 'r' ) as input_file:
        # Parent_Clade (parent clade...)	Child_Clade (child clade...)	Inherited_Count (...)	Conserved_Count (...)	Lost_Count (...)	Conservation_Rate (...)	Loss_Rate (...)
        # Opisthokonta	Holozoa	45231	43892	1339	97.04	2.96
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            statistic = {
                'parent_clade': parts[ 0 ],
                'child_clade': parts[ 1 ],
                'inherited_count': int( parts[ 2 ] ),
                'conserved_count': int( parts[ 3 ] ),
                'lost_count': int( parts[ 4 ] ),
                'conservation_rate': float( parts[ 5 ] ),
                'loss_rate': float( parts[ 6 ] )
            }

            block_statistics.append( statistic )

    logger.info( f"Loaded statistics for {len( block_statistics )} blocks" )

    return block_statistics


def load_phylogenetic_paths():
    """
    Load phylogenetic paths (root-to-tip) for each species from Script 001 output.

    Returns:
        dict: { species_name: [ clade_name_1, ..., species_name ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_file}" )

    if not input_phylogenetic_paths_file.exists():
        logger.error( f"CRITICAL ERROR: Phylogenetic paths not found!" )
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

            # Parse path (comma-separated clade IDs with names)
            path_entries = path_string.split( ',' )
            path = []
            for clade_id_name in path_entries:
                if '_' in clade_id_name:
                    clade_name = '_'.join( clade_id_name.split( '_' )[ 1: ] )
                    path.append( clade_name )

            if path:
                species_name = path[ -1 ]
                species_names___phylogenetic_paths[ species_name ] = path

    logger.info( f"Loaded {len( species_names___phylogenetic_paths )} phylogenetic paths" )

    return species_names___phylogenetic_paths


def load_all_clade_names():
    """
    Load all clade names from Script 001 clade mappings.

    Returns:
        list: [ clade_name_1, clade_name_2, ... ]
    """
    logger.info( f"Loading clade names from: {input_clade_mappings_file}" )

    if not input_clade_mappings_file.exists():
        logger.error( f"CRITICAL ERROR: Clade mapping not found!" )
        logger.error( f"Expected: {input_clade_mappings_file}" )
        sys.exit( 1 )

    clade_names = []

    with open( input_clade_mappings_file, 'r' ) as input_file:
        # Clade_ID (clade identifier from trees_species)	Clade_Name (clade name from phylogenetic tree)
        # C001	Fonticula_alba
        header_line = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            clade_name = parts[ 1 ]
            clade_names.append( clade_name )

    logger.info( f"Loaded {len( clade_names )} clade names" )

    return clade_names


# ============================================================================
# SECTION 2: GENERATE PER-ORTHOGROUP COMPLETE SUMMARIES
# ============================================================================

def generate_orthogroup_summaries( orthogroups___origins, orthogroups___patterns ):
    """
    Generate complete per-orthogroup summaries with TEMPLATE_03 dual-metric tracking.

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

        # Extract TEMPLATE_03 metrics from Script 003
        total_inherited_transitions = pattern_info.get( 'total_inherited_transitions', 0 )
        conservation_events = pattern_info.get( 'conservation_events', 0 )
        loss_origin_events = pattern_info.get( 'loss_origin_events', 0 )
        continued_absence_events = pattern_info.get( 'continued_absence_events', 0 )
        loss_coverage_events = pattern_info.get( 'loss_coverage_events', 0 )
        conservation_rate_percent = pattern_info.get( 'conservation_rate_percent', 0.0 )
        loss_origin_rate_percent = pattern_info.get( 'loss_origin_rate_percent', 0.0 )
        percent_tree_conserved = pattern_info.get( 'percent_tree_conserved', 0.0 )
        percent_tree_loss = pattern_info.get( 'percent_tree_loss', 0.0 )

        # Carry forward annotation data from Script 003
        phylogenetic_block = pattern_info.get( 'phylogenetic_block', 'NA' )
        phylogenetic_path = pattern_info.get( 'phylogenetic_path', 'NA' )
        species_list = pattern_info.get( 'species_list', '' )
        sequence_ids = pattern_info.get( 'sequence_ids', '' )
        sequences_fasta = pattern_info.get( 'sequences_fasta', '' )

        summary = {
            'orthogroup_id': orthogroup_id,
            'origin_clade': origin_info[ 'origin_clade' ],
            'phylogenetic_block': phylogenetic_block,
            'phylogenetic_path': phylogenetic_path,
            'species_count': origin_info[ 'species_count' ],
            'total_inherited_transitions': total_inherited_transitions,
            'conservation_events': conservation_events,
            'loss_origin_events': loss_origin_events,
            'continued_absence_events': continued_absence_events,
            'loss_coverage_events': loss_coverage_events,
            'conservation_rate_percent': conservation_rate_percent,
            'loss_origin_rate_percent': loss_origin_rate_percent,
            'percent_tree_conserved': percent_tree_conserved,
            'percent_tree_loss': percent_tree_loss,
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

def generate_clade_statistics( clade_names, clades___origin_counts, orthogroups___species,
                               species_names___phylogenetic_paths, block_statistics ):
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

    # Build clade-to-descendants mapping
    clades___descendant_species = defaultdict( set )
    for species_name, path in species_names___phylogenetic_paths.items():
        for clade_name in path:
            clades___descendant_species[ clade_name ].add( species_name )

    # Build clade-to-orthogroups mapping (orthogroups present in clade)
    clades___orthogroups = defaultdict( set )
    for orthogroup_id, species_set in orthogroups___species.items():
        for clade_name in clade_names:
            descendant_species = clades___descendant_species.get( clade_name, set() )
            if species_set.intersection( descendant_species ):
                clades___orthogroups[ clade_name ].add( orthogroup_id )

    # Aggregate conservation/loss statistics per clade (as parent)
    clades___conservation_statistics = {}
    for statistic in block_statistics:
        parent_clade = statistic[ 'parent_clade' ]

        if parent_clade not in clades___conservation_statistics:
            clades___conservation_statistics[ parent_clade ] = {
                'as_parent_inherited': 0,
                'as_parent_conserved': 0,
                'as_parent_lost': 0
            }

        clades___conservation_statistics[ parent_clade ][ 'as_parent_inherited' ] += statistic[ 'inherited_count' ]
        clades___conservation_statistics[ parent_clade ][ 'as_parent_conserved' ] += statistic[ 'conserved_count' ]
        clades___conservation_statistics[ parent_clade ][ 'as_parent_lost' ] += statistic[ 'lost_count' ]

    # Generate statistics for each clade
    clade_statistics = []

    for clade_name in sorted( clade_names ):
        origins_count = clades___origin_counts.get( clade_name, 0 )
        orthogroups_present = len( clades___orthogroups.get( clade_name, set() ) )
        descendant_species_count = len( clades___descendant_species.get( clade_name, set() ) )

        conservation_data = clades___conservation_statistics.get( clade_name, {} )
        inherited_as_parent = conservation_data.get( 'as_parent_inherited', 0 )
        conserved_as_parent = conservation_data.get( 'as_parent_conserved', 0 )
        lost_as_parent = conservation_data.get( 'as_parent_lost', 0 )

        # Handle zero inherited explicitly
        if inherited_as_parent > 0:
            conservation_rate = ( conserved_as_parent / inherited_as_parent ) * 100
            loss_rate = ( lost_as_parent / inherited_as_parent ) * 100
        else:
            conservation_rate = 0.0
            loss_rate = 0.0

        statistic = {
            'clade_name': clade_name,
            'origins_count': origins_count,
            'orthogroups_present': orthogroups_present,
            'descendant_species_count': descendant_species_count,
            'inherited_as_parent': inherited_as_parent,
            'conserved_as_parent': conserved_as_parent,
            'lost_as_parent': lost_as_parent,
            'conservation_rate': conservation_rate,
            'loss_rate': loss_rate
        }

        clade_statistics.append( statistic )

    logger.info( f"Generated statistics for {len( clade_statistics )} clades" )

    return clade_statistics


# ============================================================================
# SECTION 4: GENERATE PER-SPECIES SUMMARIES
# ============================================================================

def generate_species_summaries( species_names___phylogenetic_paths, orthogroups___species,
                               clades___origin_counts ):
    """
    Generate per-species summaries.

    Includes:
    - Total orthogroups present in species
    - Orthogroups conserved from ancestors
    - Species-specific orthogroups (originated at this species)

    Returns:
        list: Per-species summary dictionaries
    """
    logger.info( "Generating per-species summaries..." )

    species_summaries = []

    for species_name in sorted( species_names___phylogenetic_paths.keys() ):
        # Find orthogroups present in this species
        orthogroups_in_species = set()
        for orthogroup_id, species_set in orthogroups___species.items():
            if species_name in species_set:
                orthogroups_in_species.add( orthogroup_id )

        total_orthogroups = len( orthogroups_in_species )

        # Species-specific orthogroups (originated at this species)
        species_specific = clades___origin_counts.get( species_name, 0 )

        # Conserved from ancestors = total - species-specific
        conserved_from_ancestors = total_orthogroups - species_specific

        summary = {
            'species_name': species_name,
            'total_orthogroups': total_orthogroups,
            'conserved_from_ancestors': conserved_from_ancestors,
            'species_specific': species_specific
        }

        species_summaries.append( summary )

    logger.info( f"Generated summaries for {len( species_summaries )} species" )

    return species_summaries


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
    4. Conservation rate sanity
    5. Script 004 TEMPLATE_03 metrics match Script 003 exactly

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

    # Check 4: Conservation rate sanity
    validation_report.append( "CHECK 4: Conservation Rate Sanity Checks" )
    clade_conservation_rates = [ statistic[ 'conservation_rate' ] for statistic in clade_statistics if statistic[ 'conservation_rate' ] > 0 ]

    if clade_conservation_rates:
        average_conservation = sum( clade_conservation_rates ) / len( clade_conservation_rates )
        validation_report.append( f"  Average conservation rate (clades with data): {average_conservation:.2f}%" )
        validation_report.append( "  PASS: Conservation rates within expected range" )
    else:
        validation_report.append( "  WARNING: No conservation rate data available" )

    validation_report.append( "" )

    # Check 5: Script 004 matches Script 003 (critical cross-script validation)
    validation_report.append( "CHECK 5: Script 004 Matches Script 003 (TEMPLATE_03)" )
    validation_report.append( "  Verifying orthogroup summaries match conservation patterns exactly..." )

    mismatches = []
    for summary in orthogroup_summaries:
        orthogroup_id = summary[ 'orthogroup_id' ]

        # Get TEMPLATE_03 values from Script 004 (this script)
        total_inherited_004 = summary[ 'total_inherited_transitions' ]
        conservation_004 = summary[ 'conservation_events' ]
        loss_origin_004 = summary[ 'loss_origin_events' ]
        continued_absence_004 = summary[ 'continued_absence_events' ]
        loss_coverage_004 = summary[ 'loss_coverage_events' ]

        # Get TEMPLATE_03 values from Script 003
        pattern_003 = orthogroups___patterns.get( orthogroup_id, {} )
        total_inherited_003 = pattern_003.get( 'total_inherited_transitions', -1 )
        conservation_003 = pattern_003.get( 'conservation_events', -1 )
        loss_origin_003 = pattern_003.get( 'loss_origin_events', -1 )
        continued_absence_003 = pattern_003.get( 'continued_absence_events', -1 )
        loss_coverage_003 = pattern_003.get( 'loss_coverage_events', -1 )

        if ( total_inherited_004 != total_inherited_003 or
             conservation_004 != conservation_003 or
             loss_origin_004 != loss_origin_003 or
             continued_absence_004 != continued_absence_003 or
             loss_coverage_004 != loss_coverage_003 ):
            mismatches.append( {
                'orthogroup_id': orthogroup_id,
                'total_inherited_004': total_inherited_004,
                'total_inherited_003': total_inherited_003,
                'conservation_004': conservation_004,
                'conservation_003': conservation_003,
                'loss_origin_004': loss_origin_004,
                'loss_origin_003': loss_origin_003,
                'continued_absence_004': continued_absence_004,
                'continued_absence_003': continued_absence_003,
                'loss_coverage_004': loss_coverage_004,
                'loss_coverage_003': loss_coverage_003
            } )

    if not mismatches:
        validation_report.append( f"  PASS: All {len( orthogroup_summaries )} orthogroups match between Script 003 and Script 004" )
    else:
        validation_report.append( f"  FAIL: Found {len( mismatches )} mismatches!" )
        validation_report.append( "" )
        validation_report.append( "  First 10 mismatches (TEMPLATE_03 metrics):" )
        for mismatch in mismatches[ :10 ]:
            validation_report.append( f"    {mismatch[ 'orthogroup_id' ]}:" )
            validation_report.append( f"      Total Inherited: Script004={mismatch[ 'total_inherited_004' ]} vs Script003={mismatch[ 'total_inherited_003' ]}" )
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
    """Write complete per-orthogroup summaries with TEMPLATE_03 dual-metric tracking."""
    logger.info( f"Writing orthogroup summaries to: {output_orthogroup_complete_file}" )

    with open( output_orthogroup_complete_file, 'w', newline = '', encoding = 'utf-8' ) as output_file:
        csv_writer = csv.writer( output_file, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Build single-row GIGANTIC_1 header
        header_columns = [
            'Orthogroup_ID (orthogroup identifier)',
            'Origin_Clade (phylogenetic clade where orthogroup originated)',
            'Origin_Clade_Phylogenetic_Block (phylogenetic block for origin clade format Parent_Clade::Child_Clade)',
            'Origin_Clade_Phylogenetic_Path (phylogenetic path for origin clade comma delimited from root to origin clade)',
            'Species_Count (total unique species in orthogroup)',
            'Total_Phylogenetically_Inherited_Transitions (count of all parent to child clade transitions descended from origin clade where orthogroup was phylogenetically inherited)',
            'Conservation_Events_Actually_Present_In_Both_Parent_And_Child (count of transitions where orthogroup actually present in descendant species of both parent and child clades)',
            'Loss_At_Origin_Events_Present_In_Parent_Absent_In_Child (count of transitions where orthogroup present in parent species but absent in child species representing phylogenetic origin of gene loss)',
            'Continued_Absence_Events_Absent_In_Both_Parent_And_Child (count of transitions where orthogroup absent in both parent and child species meaning loss occurred earlier and absence continues)',
            'Loss_Coverage_Events_All_Transitions_Where_Absent_In_Child (count of all transitions where orthogroup absent in child species calculated as loss at origin plus continued absence)',
            'Conservation_Rate_Percent (percentage of inherited transitions showing conservation calculated as conservation events divided by total inherited transitions times 100)',
            'Loss_At_Origin_Rate_Percent (percentage of inherited transitions where gene loss first occurs calculated as loss at origin events divided by total inherited transitions times 100)',
            'Percent_Phylogenetic_Tree_With_Orthogroup_Actually_Present (percentage of phylogenetic tree where orthogroup is present calculated as conservation events divided by total inherited transitions times 100)',
            'Percent_Phylogenetic_Tree_Lacking_Orthogroup (percentage of phylogenetic tree where orthogroup is absent calculated as loss coverage events divided by total inherited transitions times 100)',
            'Species_List (comma delimited list of all species containing this orthogroup)',
            'Sequence_IDs (comma delimited list of short sequence identifiers in this orthogroup)'
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
                summary[ 'origin_clade' ],
                summary[ 'phylogenetic_block' ],
                summary[ 'phylogenetic_path' ],
                summary[ 'species_count' ],
                summary[ 'total_inherited_transitions' ],
                summary[ 'conservation_events' ],
                summary[ 'loss_origin_events' ],
                summary[ 'continued_absence_events' ],
                summary[ 'loss_coverage_events' ],
                f"{summary[ 'conservation_rate_percent' ]:.2f}",
                f"{summary[ 'loss_origin_rate_percent' ]:.2f}",
                f"{summary[ 'percent_tree_conserved' ]:.2f}",
                f"{summary[ 'percent_tree_loss' ]:.2f}",
                summary[ 'species_list' ],
                summary[ 'sequence_ids' ]
            ]

            if INCLUDE_FASTA:
                output_row.append( summary[ 'sequences_fasta' ] )

            csv_writer.writerow( output_row )

    column_count = 17 if INCLUDE_FASTA else 16
    logger.info( f"Wrote {len( orthogroup_summaries )} orthogroup summaries ({column_count} columns)" )


def write_clade_statistics( clade_statistics ):
    """Write comprehensive per-clade statistics."""
    logger.info( f"Writing clade statistics to: {output_clade_statistics_file}" )

    with open( output_clade_statistics_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Clade_Name (phylogenetic clade name)\t'
        output += 'Origins_Count (number of orthogroups that originated in this clade)\t'
        output += 'Orthogroups_Present (total number of orthogroups present in this clade)\t'
        output += 'Descendant_Species_Count (number of species descended from this clade)\t'
        output += 'Inherited_As_Parent (number of orthogroups this clade passed to child clades)\t'
        output += 'Conserved_As_Parent (number of orthogroups conserved in child clades when this clade was parent)\t'
        output += 'Lost_As_Parent (number of orthogroups lost in child clades when this clade was parent)\t'
        output += 'Conservation_Rate (percentage of orthogroups conserved when this clade was parent calculated as conserved divided by inherited times 100)\t'
        output += 'Loss_Rate (percentage of orthogroups lost when this clade was parent calculated as lost divided by inherited times 100)\n'
        output_file.write( output )

        for statistic in clade_statistics:
            output = f"{statistic[ 'clade_name' ]}\t{statistic[ 'origins_count' ]}\t"
            output += f"{statistic[ 'orthogroups_present' ]}\t{statistic[ 'descendant_species_count' ]}\t"
            output += f"{statistic[ 'inherited_as_parent' ]}\t{statistic[ 'conserved_as_parent' ]}\t"
            output += f"{statistic[ 'lost_as_parent' ]}\t{statistic[ 'conservation_rate' ]:.2f}\t"
            output += f"{statistic[ 'loss_rate' ]:.2f}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( clade_statistics )} clade statistics" )


def write_species_summaries( species_summaries ):
    """Write per-species summaries."""
    logger.info( f"Writing species summaries to: {output_species_summaries_file}" )

    with open( output_species_summaries_file, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Species_Name (species name in Genus_species format)\t'
        output += 'Total_Orthogroups (total number of orthogroups containing this species)\t'
        output += 'Conserved_From_Ancestors (orthogroups inherited from ancestral clades)\t'
        output += 'Species_Specific (orthogroups that originated at this species)\n'
        output_file.write( output )

        for summary in species_summaries:
            output = f"{summary[ 'species_name' ]}\t{summary[ 'total_orthogroups' ]}\t"
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
    logger.info( "SCRIPT 004: COMPREHENSIVE OCL ANALYSIS (TEMPLATE_03)" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {Path( __file__ ).name}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"FASTA embedding: {'enabled' if INCLUDE_FASTA else 'disabled'}" )
    logger.info( "" )

    # STEP 1: Load all input data
    logger.info( "STEP 1: Loading all input data..." )
    orthogroups___origins = load_orthogroup_origins()
    orthogroups___patterns = load_orthogroup_patterns()
    orthogroups___species = load_orthogroup_species()
    clades___origin_counts = load_origins_summary()
    block_statistics = load_block_statistics()
    species_names___phylogenetic_paths = load_phylogenetic_paths()
    clade_names = load_all_clade_names()
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
        clade_names,
        clades___origin_counts,
        orthogroups___species,
        species_names___phylogenetic_paths,
        block_statistics
    )
    logger.info( "" )

    # STEP 4: Generate per-species summaries
    logger.info( "STEP 4: Generating per-species summaries..." )
    species_summaries = generate_species_summaries(
        species_names___phylogenetic_paths,
        orthogroups___species,
        clades___origin_counts
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
    logger.info( f"  {output_validation_report_file.name}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
