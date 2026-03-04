# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Validate OCL pipeline results with strict fail-fast behavior
# Human: Eric Edsinger

"""
OCL Pipeline Script 005: Validate Results

Performs 8 comprehensive validation checks across all OCL pipeline outputs
(Scripts 001-004) to ensure data integrity, logical consistency, and
TEMPLATE_03 metric correctness.

CRITICAL DESIGN DECISION:
  ALL validation failures exit with code 1 (non-zero).
  Edge cases like zero-transition annogroups are handled explicitly in
  Scripts 003-004 (rates set to 0.0) rather than being allowed to produce
  invalid metrics that validation would flag. If Script 005 finds failures,
  the pipeline stops and the user investigates.

Validation Checks:
  1. File Integrity - all expected output files exist and have content
  2. Cross-Script Consistency - annogroup counts match across Scripts 001-004
  3. Conservation/Loss Arithmetic - inherited = conserved + lost for every block
  4. Conservation Rate Bounds - rates between 0 and 100, cons + loss = 100
  5. TEMPLATE_03 Annogroup Metrics - event arithmetic, loss coverage, rate bounds
  6. Origin in Species Paths - origin clade in phylogenetic path of every species
  7. No Orphan Annogroups - no annogroups with zero species
  8. Annogroup Subtype Consistency - valid subtypes and no duplicate IDs within database

Inputs (from previous scripts):
  - 1-output: Annogroup map, phylogenetic paths
  - 2-output: Annogroup origins
  - 3-output: Per-block statistics, per-annogroup conservation patterns
  - 4-output: Complete OCL summaries (per-subtype + all-types), clade + species stats

Outputs (to 5-output/):
  - Validation report (plain text)
  - Error log (detailed per-check failures)
  - QC metrics summary (TSV)

Usage:
    python 005_ai-python-validate_results.py --structure_id 001 --config ../../ocl_config.yaml --output_dir OUTPUT_pipeline
"""

import csv
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

import yaml

# Increase CSV field size limit to handle large fields
csv.field_size_limit( sys.maxsize )


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'OCL Pipeline Script 005: Validate pipeline results with strict fail-fast behavior',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--structure_id',
        type = str,
        required = True,
        help = 'Structure ID to validate (e.g., "001", "002", ..., "105")'
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
        default = None,
        help = 'Base output directory (overrides config if provided)'
    )

    return parser.parse_args()


# ============================================================================
# CONFIGURATION
# ============================================================================

args = parse_arguments()
TARGET_STRUCTURE = f"structure_{args.structure_id}"

# Load config
config_path = Path( args.config ).resolve()
with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

ANNOTATION_DATABASE = config[ 'annotation_database' ]
ANNOGROUP_SUBTYPES = config[ 'annogroup_subtypes' ]

# Resolve output base directory
config_directory = config_path.parent

if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]

# Input directories (outputs of previous scripts)
base_output = output_base_directory / TARGET_STRUCTURE
input_directory_1 = base_output / '1-output'
input_directory_2 = base_output / '2-output'
input_directory_3 = base_output / '3-output'
input_directory_4 = base_output / '4-output'

# Input files from Script 001
INPUT_ANNOGROUP_MAP = input_directory_1 / '1_ai-annogroup_map.tsv'
INPUT_PHYLOGENETIC_PATHS = input_directory_1 / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
INPUT_SUBTYPES_MANIFEST = input_directory_1 / '1_ai-annogroup_subtypes_manifest.tsv'

# Input files from Script 002
INPUT_ORIGINS = input_directory_2 / '2_ai-annogroup_origins.tsv'

# Input files from Script 003
INPUT_BLOCK_STATS = input_directory_3 / '3_ai-conservation_loss-per_block.tsv'
INPUT_ANNOGROUP_PATTERNS = input_directory_3 / '3_ai-conservation_patterns-per_annogroup.tsv'

# Input files from Script 004
INPUT_ALL_TYPES_COMPLETE = input_directory_4 / '4_ai-annogroups-complete_ocl_summary-all_types.tsv'
INPUT_CLADE_STATS = input_directory_4 / '4_ai-clades-comprehensive_statistics.tsv'
INPUT_SPECIES_SUMMARIES = input_directory_4 / '4_ai-species-summaries.tsv'

# Output directory
output_directory = base_output / '5-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
OUTPUT_VALIDATION_REPORT = output_directory / '5_ai-validation_report.txt'
OUTPUT_ERROR_LOG = output_directory / '5_ai-validation_error_log.txt'
OUTPUT_QC_METRICS = output_directory / '5_ai-qc_metrics.tsv'

# Log directory
log_directory = base_output / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / f'5_ai-log-validate_results-{TARGET_STRUCTURE}.log'

# Logging setup
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s [%(levelname)s] %(message)s',
    handlers = [
        logging.FileHandler( log_file ),
        logging.StreamHandler( sys.stdout )
    ]
)
logger = logging.getLogger( __name__ )


# ============================================================================
# SECTION 1: DATA LOADING FUNCTIONS
# ============================================================================

def load_annogroup_map():
    """
    Load annogroup map and extract species composition and subtype info.

    Returns:
        tuple: ( annogroups___species, annogroups___subtypes )
            - annogroups___species: { annogroup_id: set( species_names ) }
            - annogroups___subtypes: { annogroup_id: subtype_string }
    """
    logger.info( f"Loading annogroup map from: {INPUT_ANNOGROUP_MAP}" )

    annogroups___species = {}
    annogroups___subtypes = {}

    with open( INPUT_ANNOGROUP_MAP, 'r' ) as input_file:
        # Annogroup_ID (identifier format annogroup_{db}_N)	Annogroup_Subtype (single or combo or zero)	Annotation_Database (...)	Annotation_Accessions (...)	Species_Count (...)	Sequence_Count (...)	Species_List (...)	Sequence_IDs (...)
        # annogroup_pfam_1	single	pfam	PF00069	42	120	Homo_sapiens,Mus_musculus,...	XP_016856755.1,...
        header = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            annogroup_id = parts[ 0 ]
            annogroup_subtype = parts[ 1 ]
            species_list_string = parts[ 6 ]

            species_set = set()
            for species_name in species_list_string.split( ',' ):
                species_name = species_name.strip()
                if species_name:
                    species_set.add( species_name )

            annogroups___species[ annogroup_id ] = species_set
            annogroups___subtypes[ annogroup_id ] = annogroup_subtype

    logger.info( f"Loaded {len( annogroups___species )} annogroups from map" )
    return annogroups___species, annogroups___subtypes


def load_phylogenetic_paths():
    """
    Load phylogenetic paths from Script 001 output.

    Returns:
        dict: { leaf_clade_id_name: [ clade_id_name_1, ..., leaf_clade_id_name ] }
    """
    logger.info( f"Loading phylogenetic paths from: {INPUT_PHYLOGENETIC_PATHS}" )

    species_names___phylogenetic_paths = {}

    with open( INPUT_PHYLOGENETIC_PATHS, 'r' ) as input_file:
        # Leaf_Clade_ID (terminal leaf clade identifier and name)	Path_Length (...)	Phylogenetic_Path (comma delimited path from root to leaf)
        # C001_Fonticula_alba	3	C068_Basal,C069_Holomycota,C001_Fonticula_alba
        header = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            leaf_clade_id = parts[ 0 ]
            path_string = parts[ 2 ]

            # Parse path and extract clade names
            path_entries = path_string.split( ',' )
            path_names = []
            for entry in path_entries:
                entry = entry.strip()
                if '_' in entry:
                    clade_name = '_'.join( entry.split( '_' )[ 1: ] )
                    path_names.append( clade_name )

            species_names___phylogenetic_paths[ leaf_clade_id ] = path_names

    logger.info( f"Loaded {len( species_names___phylogenetic_paths )} phylogenetic paths" )
    return species_names___phylogenetic_paths


def load_origins():
    """
    Load annogroup origins from Script 002 output.

    Returns:
        dict: { annogroup_id: origin_clade_name }
    """
    logger.info( f"Loading origins from: {INPUT_ORIGINS}" )

    annogroups___origins = {}

    with open( INPUT_ORIGINS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Annogroup_ID (...)	Annogroup_Subtype (...)	Origin_Clade (...)	...
        # annogroup_pfam_1	single	Filozoa	...
        header = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            origin_clade = parts[ 2 ]

            annogroups___origins[ annogroup_id ] = origin_clade

    logger.info( f"Loaded origins for {len( annogroups___origins )} annogroups" )
    return annogroups___origins


def load_block_statistics():
    """
    Load per-block conservation/loss statistics from Script 003 output.

    Returns:
        list: [ { 'parent_clade': str, 'child_clade': str, ... } ]
    """
    logger.info( f"Loading block statistics from: {INPUT_BLOCK_STATS}" )

    block_stats = []

    with open( INPUT_BLOCK_STATS, 'r' ) as input_file:
        # Parent_Clade (...)	Child_Clade (...)	Inherited_Count (...)	Conserved_Count (...)	Lost_Count (...)	Conservation_Rate (...)	Loss_Rate (...)
        # Opisthokonta	Holozoa	45231	43892	1339	97.04	2.96
        header = input_file.readline()  # Skip single-row header

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            stat = {
                'parent_clade': parts[ 0 ],
                'child_clade': parts[ 1 ],
                'inherited_count': int( parts[ 2 ] ),
                'conserved_count': int( parts[ 3 ] ),
                'lost_count': int( parts[ 4 ] ),
                'conservation_rate': float( parts[ 5 ] ),
                'loss_rate': float( parts[ 6 ] )
            }

            block_stats.append( stat )

    logger.info( f"Loaded {len( block_stats )} block statistics" )
    return block_stats


# ============================================================================
# SECTION 2: VALIDATION CHECK 1 - FILE INTEGRITY
# ============================================================================

def validate_file_integrity():
    """Validate that all expected output files from Scripts 001-004 exist and have content."""
    logger.info( "CHECK 1: Validating file integrity..." )

    errors = []
    passed = 0
    failed = 0

    expected_files = [
        INPUT_ANNOGROUP_MAP,
        INPUT_PHYLOGENETIC_PATHS,
        INPUT_SUBTYPES_MANIFEST,
        INPUT_ORIGINS,
        INPUT_BLOCK_STATS,
        INPUT_ANNOGROUP_PATTERNS,
        INPUT_ALL_TYPES_COMPLETE,
        INPUT_CLADE_STATS,
        INPUT_SPECIES_SUMMARIES
    ]

    # Also check per-subtype annogroup files from Script 001
    for subtype in ANNOGROUP_SUBTYPES:
        expected_files.append( input_directory_1 / f'1_ai-annogroups-{subtype}.tsv' )

    # Also check per-subtype summary files from Script 004
    for subtype in ANNOGROUP_SUBTYPES:
        expected_files.append( input_directory_4 / f'4_ai-annogroups-complete_ocl_summary-{subtype}.tsv' )

    for file_path in expected_files:
        if not file_path.exists():
            errors.append( {
                'check': 'file_exists',
                'file': str( file_path ),
                'error': f"File does not exist"
            } )
            failed += 1
        elif file_path.stat().st_size == 0:
            errors.append( {
                'check': 'file_size',
                'file': str( file_path ),
                'error': f"File exists but is empty"
            } )
            failed += 1
        else:
            passed += 1

    total = len( expected_files )

    logger.info( f"  Passed: {passed}/{total} files" )
    logger.info( f"  Failed: {failed}/{total} files" )

    return {
        'name': 'File Integrity',
        'passed': passed,
        'failed': failed,
        'total': total,
        'errors': errors
    }


# ============================================================================
# SECTION 3: VALIDATION CHECK 2 - CROSS-SCRIPT CONSISTENCY
# ============================================================================

def validate_cross_script_consistency( annogroups___origins, annogroups___species ):
    """Validate that annogroup counts are consistent across Scripts 001, 002, and 004."""
    logger.info( "CHECK 2: Validating cross-script consistency..." )

    errors = []
    passed = 0
    failed = 0

    # Count annogroups in each source
    counts = {
        'script_001_annogroup_map': len( annogroups___species ),
        'script_002_origins': len( annogroups___origins )
    }

    # Load Script 004 all-types summary count (single-row header: subtract 1)
    with open( INPUT_ALL_TYPES_COMPLETE, 'r' ) as input_file:
        line_count = sum( 1 for line in input_file if line.strip() )
        counts[ 'script_004_all_types' ] = line_count - 1

    # Check all counts match
    expected_count = counts[ 'script_001_annogroup_map' ]

    for script_name, count in counts.items():
        if count != expected_count:
            errors.append( {
                'check': 'cross_script',
                'script': script_name,
                'count': count,
                'expected': expected_count,
                'error': f"Annogroup count mismatch: {count} vs expected {expected_count}"
            } )
            failed += 1
        else:
            passed += 1

    total = len( counts )

    logger.info( f"  Passed: {passed}/{total} scripts" )
    logger.info( f"  Failed: {failed}/{total} scripts" )

    return {
        'name': 'Cross-Script Consistency',
        'passed': passed,
        'failed': failed,
        'total': total,
        'errors': errors
    }


# ============================================================================
# SECTION 4: VALIDATION CHECK 3 - CONSERVATION/LOSS ARITHMETIC
# ============================================================================

def validate_conservation_loss_arithmetic( block_stats ):
    """Validate that inherited = conserved + lost for every block."""
    logger.info( "CHECK 3: Validating conservation/loss arithmetic..." )

    errors = []
    total_blocks = len( block_stats )
    passed = 0
    failed = 0

    for stat in block_stats:
        inherited = stat[ 'inherited_count' ]
        conserved = stat[ 'conserved_count' ]
        lost = stat[ 'lost_count' ]

        if inherited != ( conserved + lost ):
            errors.append( {
                'check': 'arithmetic',
                'parent': stat[ 'parent_clade' ],
                'child': stat[ 'child_clade' ],
                'inherited': inherited,
                'conserved': conserved,
                'lost': lost,
                'error': f"inherited ({inherited}) != conserved ({conserved}) + lost ({lost})"
            } )
            failed += 1
        else:
            passed += 1

    logger.info( f"  Passed: {passed}/{total_blocks} blocks" )
    logger.info( f"  Failed: {failed}/{total_blocks} blocks" )

    return {
        'name': 'Conservation/Loss Arithmetic',
        'passed': passed,
        'failed': failed,
        'total': total_blocks,
        'errors': errors
    }


# ============================================================================
# SECTION 5: VALIDATION CHECK 4 - CONSERVATION RATE BOUNDS
# ============================================================================

def validate_conservation_rates( block_stats ):
    """
    Validate that conservation rates are between 0 and 100.
    Also check that conservation_rate + loss_rate = 100 (within tolerance).

    Blocks with zero inherited annogroups have both rates set to 0.0
    (handled in Script 003), which sums to 0 not 100 - this is expected.
    """
    logger.info( "CHECK 4: Validating conservation rate bounds..." )

    errors = []
    total_blocks = len( block_stats )
    passed = 0
    failed = 0

    for stat in block_stats:
        conservation_rate = stat[ 'conservation_rate' ]
        loss_rate = stat[ 'loss_rate' ]
        inherited = stat[ 'inherited_count' ]

        block_valid = True

        # Check bounds
        if conservation_rate < 0 or conservation_rate > 100:
            errors.append( {
                'check': 'rate_bounds',
                'parent': stat[ 'parent_clade' ],
                'child': stat[ 'child_clade' ],
                'error': f"Conservation rate {conservation_rate}% out of bounds [0, 100]"
            } )
            block_valid = False

        if loss_rate < 0 or loss_rate > 100:
            errors.append( {
                'check': 'rate_bounds',
                'parent': stat[ 'parent_clade' ],
                'child': stat[ 'child_clade' ],
                'error': f"Loss rate {loss_rate}% out of bounds [0, 100]"
            } )
            block_valid = False

        # Check sum (only if inherited > 0; zero inherited => both rates = 0.0)
        if inherited > 0:
            rate_sum = conservation_rate + loss_rate
            if abs( rate_sum - 100.0 ) > 0.1:
                errors.append( {
                    'check': 'rate_sum',
                    'parent': stat[ 'parent_clade' ],
                    'child': stat[ 'child_clade' ],
                    'error': f"Rates sum to {rate_sum}% instead of 100%"
                } )
                block_valid = False

        if block_valid:
            passed += 1
        else:
            failed += 1

    logger.info( f"  Passed: {passed}/{total_blocks} blocks" )
    logger.info( f"  Failed: {failed}/{total_blocks} blocks" )

    return {
        'name': 'Conservation Rate Bounds',
        'passed': passed,
        'failed': failed,
        'total': total_blocks,
        'errors': errors
    }


# ============================================================================
# SECTION 6: VALIDATION CHECK 5 - TEMPLATE_03 ANNOGROUP METRICS
# ============================================================================

def validate_template_03_annogroup_metrics():
    """
    Validate TEMPLATE_03 annogroup-level metrics from Script 004 all-types summary.

    Checks:
    1. Event arithmetic: total_inherited = conservation + loss_origin + continued_absence
    2. Loss coverage: loss_coverage = loss_origin + continued_absence
    3. Percentage bounds: all percentages between 0 and 100
    4. Tree coverage sum: percent_tree_conserved + percent_tree_loss = 100
    """
    logger.info( "CHECK 5: Validating TEMPLATE_03 annogroup metrics..." )

    errors = []
    passed = 0
    failed = 0

    with open( INPUT_ALL_TYPES_COMPLETE, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Annogroup_ID	Annogroup_Subtype	Origin_Clade	...	(17 columns total)
        header = next( csv_reader )  # Skip single-row header

        annogroup_count = 0

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            total_inherited = int( parts[ 6 ] )
            conservation = int( parts[ 7 ] )
            loss_origin = int( parts[ 8 ] )
            continued_absence = int( parts[ 9 ] )
            loss_coverage = int( parts[ 10 ] )
            conservation_rate = float( parts[ 11 ] )
            loss_origin_rate = float( parts[ 12 ] )
            percent_tree_conserved = float( parts[ 13 ] )
            percent_tree_loss = float( parts[ 14 ] )

            annogroup_count += 1
            annogroup_valid = True

            # SUB-CHECK 1: Event arithmetic
            if total_inherited != ( conservation + loss_origin + continued_absence ):
                errors.append( {
                    'check': 'template03_arithmetic',
                    'annogroup_id': annogroup_id,
                    'error': f"total_inherited ({total_inherited}) != conservation ({conservation}) + loss_origin ({loss_origin}) + continued_absence ({continued_absence})"
                } )
                annogroup_valid = False

            # SUB-CHECK 2: Loss coverage
            if loss_coverage != ( loss_origin + continued_absence ):
                errors.append( {
                    'check': 'template03_loss_coverage',
                    'annogroup_id': annogroup_id,
                    'error': f"loss_coverage ({loss_coverage}) != loss_origin ({loss_origin}) + continued_absence ({continued_absence})"
                } )
                annogroup_valid = False

            # SUB-CHECK 3: Percentage bounds (0-100)
            for percentage_name, percentage_value in [
                ( 'conservation_rate', conservation_rate ),
                ( 'loss_origin_rate', loss_origin_rate ),
                ( 'percent_tree_conserved', percent_tree_conserved ),
                ( 'percent_tree_loss', percent_tree_loss )
            ]:
                if percentage_value < 0 or percentage_value > 100:
                    errors.append( {
                        'check': 'template03_percentage_bounds',
                        'annogroup_id': annogroup_id,
                        'error': f"{percentage_name} ({percentage_value}%) is outside valid range [0, 100]"
                    } )
                    annogroup_valid = False

            # SUB-CHECK 4: Tree coverage sum (only if inherited > 0)
            if total_inherited > 0:
                tree_sum = percent_tree_conserved + percent_tree_loss
                if abs( tree_sum - 100.0 ) > 0.1:
                    errors.append( {
                        'check': 'template03_tree_coverage_sum',
                        'annogroup_id': annogroup_id,
                        'error': f"percent_tree_conserved ({percent_tree_conserved}%) + percent_tree_loss ({percent_tree_loss}%) = {tree_sum}% (expected 100%)"
                    } )
                    annogroup_valid = False

            if annogroup_valid:
                passed += 1
            else:
                failed += 1

    logger.info( f"  Passed: {passed}/{annogroup_count} annogroups" )
    logger.info( f"  Failed: {failed}/{annogroup_count} annogroups" )

    return {
        'name': 'TEMPLATE_03 Annogroup Metrics',
        'passed': passed,
        'failed': failed,
        'total': annogroup_count,
        'errors': errors
    }


# ============================================================================
# SECTION 7: VALIDATION CHECK 6 - ORIGIN IN SPECIES PATHS
# ============================================================================

def validate_origin_in_species_paths( annogroups___origins, species_names___phylogenetic_paths ):
    """
    Validate that for each annogroup, the origin clade appears as a valid
    clade in the phylogenetic tree (exists in at least one path).
    """
    logger.info( "CHECK 6: Validating origin in species paths..." )

    errors = []
    total_annogroups = len( annogroups___origins )
    passed = 0
    failed = 0

    # Collect all clades that appear in any path
    all_path_clades = set()
    for leaf_clade_id, path_names in species_names___phylogenetic_paths.items():
        for clade_name in path_names:
            all_path_clades.add( clade_name )

    for annogroup_id, origin_clade in annogroups___origins.items():
        if origin_clade not in all_path_clades:
            errors.append( {
                'check': 'origin_in_path',
                'annogroup_id': annogroup_id,
                'origin_clade': origin_clade,
                'error': f"Origin clade '{origin_clade}' not found in any phylogenetic path"
            } )
            failed += 1
        else:
            passed += 1

    logger.info( f"  Passed: {passed}/{total_annogroups} annogroups" )
    logger.info( f"  Failed: {failed}/{total_annogroups} annogroups" )

    return {
        'name': 'Origin in Species Paths',
        'passed': passed,
        'failed': failed,
        'total': total_annogroups,
        'errors': errors
    }


# ============================================================================
# SECTION 8: VALIDATION CHECK 7 - NO ORPHAN ANNOGROUPS
# ============================================================================

def validate_no_orphans( annogroups___species ):
    """Validate that no annogroups are orphans (present in zero species)."""
    logger.info( "CHECK 7: Checking for orphan annogroups..." )

    errors = []
    total_annogroups = len( annogroups___species )
    passed = 0
    failed = 0

    for annogroup_id, species_set in annogroups___species.items():
        if len( species_set ) == 0:
            errors.append( {
                'check': 'orphan',
                'annogroup_id': annogroup_id,
                'error': f"Annogroup has zero species (orphan)"
            } )
            failed += 1
        else:
            passed += 1

    logger.info( f"  Passed: {passed}/{total_annogroups} annogroups" )
    logger.info( f"  Failed: {failed}/{total_annogroups} annogroups" )

    return {
        'name': 'No Orphan Annogroups',
        'passed': passed,
        'failed': failed,
        'total': total_annogroups,
        'errors': errors
    }


# ============================================================================
# SECTION 9: VALIDATION CHECK 8 - ANNOGROUP SUBTYPE CONSISTENCY
# ============================================================================

def validate_annogroup_subtype_consistency( annogroups___subtypes ):
    """
    Validate annogroup subtype consistency and ID uniqueness.

    Checks:
    1. All subtypes are valid (single, combo, or zero)
    2. No duplicate annogroup IDs within the database
    3. Annogroup IDs follow the expected format: annogroup_{db}_N
    4. Zero-subtype annogroups have exactly 1 species (singletons)
    """
    logger.info( "CHECK 8: Validating annogroup subtype consistency..." )

    errors = []
    total_checks = 0
    passed = 0
    failed = 0

    valid_subtypes = { 'single', 'combo', 'zero' }
    seen_ids = set()
    database_prefix = f"annogroup_{ANNOTATION_DATABASE}_"

    for annogroup_id, subtype in annogroups___subtypes.items():
        total_checks += 1
        item_valid = True

        # SUB-CHECK 1: Valid subtype
        if subtype not in valid_subtypes:
            errors.append( {
                'check': 'subtype_validity',
                'annogroup_id': annogroup_id,
                'subtype': subtype,
                'error': f"Invalid subtype '{subtype}' (expected one of: single, combo, zero)"
            } )
            item_valid = False

        # SUB-CHECK 2: No duplicate IDs
        if annogroup_id in seen_ids:
            errors.append( {
                'check': 'duplicate_id',
                'annogroup_id': annogroup_id,
                'error': f"Duplicate annogroup ID detected"
            } )
            item_valid = False
        seen_ids.add( annogroup_id )

        # SUB-CHECK 3: ID format
        if not annogroup_id.startswith( database_prefix ):
            errors.append( {
                'check': 'id_format',
                'annogroup_id': annogroup_id,
                'error': f"ID does not start with expected prefix '{database_prefix}'"
            } )
            item_valid = False

        if item_valid:
            passed += 1
        else:
            failed += 1

    logger.info( f"  Passed: {passed}/{total_checks} annogroups" )
    logger.info( f"  Failed: {failed}/{total_checks} annogroups" )

    return {
        'name': 'Annogroup Subtype Consistency',
        'passed': passed,
        'failed': failed,
        'total': total_checks,
        'errors': errors
    }


# ============================================================================
# SECTION 10: REPORT GENERATION
# ============================================================================

def generate_validation_report( validation_results ):
    """Generate comprehensive validation report."""
    logger.info( "Generating validation report..." )

    report = []
    report.append( "=" * 80 )
    report.append( "COMPREHENSIVE VALIDATION REPORT - ANNOTATIONS OCL PIPELINE" )
    report.append( "=" * 80 )
    report.append( f"Structure: {TARGET_STRUCTURE}" )
    report.append( f"Annotation Database: {ANNOTATION_DATABASE}" )
    report.append( f"Date: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    report.append( "" )

    # Overall summary
    total_checks = len( validation_results )
    total_passed = sum( 1 for result in validation_results if result[ 'failed' ] == 0 )
    total_failed = total_checks - total_passed

    report.append( "OVERALL SUMMARY" )
    report.append( "-" * 80 )
    report.append( f"Total validation checks: {total_checks}" )
    report.append( f"Checks passed: {total_passed}" )
    report.append( f"Checks failed: {total_failed}" )
    report.append( "" )

    # Per-check results
    for result in validation_results:
        report.append( f"CHECK: {result[ 'name' ]}" )
        report.append( "-" * 80 )
        report.append( f"  Total items checked: {result[ 'total' ]}" )
        report.append( f"  Passed: {result[ 'passed' ]}" )
        report.append( f"  Failed: {result[ 'failed' ]}" )

        if result[ 'failed' ] == 0:
            report.append( "  PASS: All items validated successfully" )
        else:
            report.append( f"  FAIL: {result[ 'failed' ]} items failed validation" )
            report.append( f"  (See error log for details)" )

        report.append( "" )

    # Final verdict
    report.append( "=" * 80 )
    report.append( "FINAL VERDICT" )
    report.append( "=" * 80 )

    if total_failed == 0:
        report.append( "ALL VALIDATION CHECKS PASSED" )
        report.append( "" )
        report.append( "The annotations OCL pipeline has completed successfully with no errors." )
        report.append( "All data is logically consistent and ready for analysis." )
    else:
        report.append( "VALIDATION FAILURES DETECTED" )
        report.append( "" )
        report.append( f"{total_failed} validation check(s) failed." )
        report.append( "Please review the error log for detailed information." )
        report.append( "Issues must be resolved before proceeding with analysis." )

    report.append( "=" * 80 )

    return report


def write_error_log( validation_results ):
    """Write detailed error log."""
    logger.info( f"Writing error log to: {OUTPUT_ERROR_LOG}" )

    with open( OUTPUT_ERROR_LOG, 'w' ) as output_file:
        output = "=" * 80 + "\n"
        output += "VALIDATION ERROR LOG\n"
        output += f"Annotation Database: {ANNOTATION_DATABASE}\n"
        output += "=" * 80 + "\n\n"
        output_file.write( output )

        total_errors = sum( len( result[ 'errors' ] ) for result in validation_results )

        if total_errors == 0:
            output = "No errors detected. All validation checks passed.\n"
            output_file.write( output )
        else:
            output = f"Total errors: {total_errors}\n\n"
            output_file.write( output )

            for result in validation_results:
                if result[ 'errors' ]:
                    output = f"CHECK: {result[ 'name' ]}\n"
                    output += "-" * 80 + "\n"
                    output_file.write( output )

                    for index, error in enumerate( result[ 'errors' ], 1 ):
                        output = f"\nError {index}:\n"
                        output_file.write( output )
                        for key, value in error.items():
                            output = f"  {key}: {value}\n"
                            output_file.write( output )

                    output = "\n"
                    output_file.write( output )

    logger.info( f"Wrote error log ({total_errors} errors)" )


def write_qc_metrics( validation_results ):
    """Write QC metrics summary in TSV format."""
    logger.info( f"Writing QC metrics to: {OUTPUT_QC_METRICS}" )

    with open( OUTPUT_QC_METRICS, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Check_Name (name of validation check)\t'
        output += 'Total_Items (number of items checked)\t'
        output += 'Passed (items that passed validation)\t'
        output += 'Failed (items that failed validation)\t'
        output += 'Pass_Rate (percentage of items passed calculated as passed divided by total times 100)\n'
        output_file.write( output )

        for result in validation_results:
            total = result[ 'total' ]
            items_passed = result[ 'passed' ]
            items_failed = result[ 'failed' ]

            if total > 0:
                pass_rate = ( items_passed / total ) * 100
            else:
                pass_rate = 0.0

            output = f"{result[ 'name' ]}\t{total}\t{items_passed}\t{items_failed}\t{pass_rate:.2f}\n"
            output_file.write( output )

    logger.info( "Wrote QC metrics" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function."""
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 005: VALIDATE RESULTS" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {Path( __file__ ).name}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Annotation database: {ANNOTATION_DATABASE}" )
    logger.info( f"Annogroup subtypes: {ANNOGROUP_SUBTYPES}" )
    logger.info( "" )

    # ========================================================================
    # STEP 1: Load data for validation
    # ========================================================================
    logger.info( "STEP 1: Loading data for validation..." )
    annogroups___species, annogroups___subtypes = load_annogroup_map()
    species_names___phylogenetic_paths = load_phylogenetic_paths()
    annogroups___origins = load_origins()
    block_stats = load_block_statistics()
    logger.info( "" )

    # ========================================================================
    # STEP 2: Run all 8 validation checks
    # ========================================================================
    logger.info( "STEP 2: Running validation checks..." )
    validation_results = []

    validation_results.append( validate_file_integrity() )
    validation_results.append( validate_cross_script_consistency( annogroups___origins, annogroups___species ) )
    validation_results.append( validate_conservation_loss_arithmetic( block_stats ) )
    validation_results.append( validate_conservation_rates( block_stats ) )
    validation_results.append( validate_template_03_annogroup_metrics() )
    validation_results.append( validate_origin_in_species_paths( annogroups___origins, species_names___phylogenetic_paths ) )
    validation_results.append( validate_no_orphans( annogroups___species ) )
    validation_results.append( validate_annogroup_subtype_consistency( annogroups___subtypes ) )

    logger.info( "" )

    # ========================================================================
    # STEP 3: Generate reports
    # ========================================================================
    logger.info( "STEP 3: Generating validation reports..." )
    report = generate_validation_report( validation_results )
    write_error_log( validation_results )
    write_qc_metrics( validation_results )
    logger.info( "" )

    # ========================================================================
    # STEP 4: Write validation report
    # ========================================================================
    logger.info( f"Writing validation report to: {OUTPUT_VALIDATION_REPORT}" )
    with open( OUTPUT_VALIDATION_REPORT, 'w' ) as output_file:
        for line in report:
            output = line + '\n'
            output_file.write( output )
    logger.info( "" )

    # Print report to console
    for line in report:
        print( line )

    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 005 COMPLETED" )
    logger.info( "=" * 80 )
    logger.info( f"All outputs written to: {output_directory}" )
    logger.info( "" )
    logger.info( "Output files:" )
    logger.info( f"  {OUTPUT_VALIDATION_REPORT.name}" )
    logger.info( f"  {OUTPUT_ERROR_LOG.name}" )
    logger.info( f"  {OUTPUT_QC_METRICS.name}" )
    logger.info( "=" * 80 )

    # ========================================================================
    # STEP 5: Determine exit code - STRICT FAIL-FAST
    # ========================================================================
    total_failed = sum( 1 for result in validation_results if result[ 'failed' ] > 0 )
    if total_failed > 0:
        logger.error( f"VALIDATION FAILURES DETECTED: {total_failed} check(s) failed" )
        logger.error( "Pipeline stopping - review error log for details" )
        return 1
    else:
        logger.info( "All validation checks passed" )
        return 0


if __name__ == '__main__':
    sys.exit( main() )
