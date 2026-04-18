# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Validate OCL pipeline results with strict fail-fast behavior
# Human: Eric Edsinger

"""
OCL Pipeline Script 005: Validate Results

Performs 8 validation checks across all OCL pipeline outputs (Scripts 001-004)
to ensure data integrity and Rule 7 count consistency.

CRITICAL DESIGN DECISION:
  ALL validation failures exit with code 1 (non-zero).
  Edge cases like zero-scored-block annogroups are handled explicitly in
  Scripts 003-004 (counts set to 0) rather than producing invalid numbers
  that validation would flag. If Script 005 finds failures, the pipeline
  stops and the user investigates.

Validation Checks:
  1. File Integrity - all expected output files exist and have content
  2. Cross-Script Consistency - annogroup counts match across Scripts 001-004
  3. Conservation/Loss Arithmetic - inherited = conserved + lost for every block
  4. Per-Block Count Consistency - conserved + lost = inherited for every block
  5. Per-Annogroup Block-State Counts - total = P + L + X for every annogroup
  6. Origin in Species Paths - child endpoint of origin block appears in phylogenetic path
  7. No Orphan Annogroups - no annogroups with zero species
  8. Phylogenetic Path-State Integrity - Rule 7 alphabet, state machine, terminal letter

Inputs (from previous scripts):
  - 1-output: Annogroups with species identifiers, phylogenetic paths
  - 2-output: Annogroup origins
  - 3-output: Per-block statistics, per-annogroup conservation patterns
  - 4-output: Complete OCL summaries, clade statistics, species summaries, path-states

Outputs (to 5-output/):
  - Validation report (plain text)
  - Error log (detailed per-check failures)
  - QC metrics summary (TSV)

Usage:
    python 005_ai-python-validate_results.py --structure_id 001 --config ../../START_HERE-user_config.yaml
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
TARGET_STRUCTURE = f"structure_{args.structure_id}"

# Load config
config_path = Path( args.config )
with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

# Input directories (outputs of previous scripts)
base_output = Path( args.output_dir ) / TARGET_STRUCTURE
input_directory_1 = base_output / '1-output'
input_directory_2 = base_output / '2-output'
input_directory_3 = base_output / '3-output'
input_directory_4 = base_output / '4-output'

# Input files from Script 001
INPUT_ANNOGROUPS = input_directory_1 / f'1_ai-{TARGET_STRUCTURE}_annogroups-species_identifiers.tsv'
INPUT_PHYLOGENETIC_PATHS = input_directory_1 / f'1_ai-{TARGET_STRUCTURE}_phylogenetic_paths.tsv'

# Input files from Script 002
INPUT_ORIGINS = input_directory_2 / f'2_ai-{TARGET_STRUCTURE}_annogroup_origins.tsv'

# Input files from Script 003
INPUT_BLOCK_STATS = input_directory_3 / f'3_ai-{TARGET_STRUCTURE}_conservation_loss-per_block.tsv'
INPUT_ANNOGROUP_PATTERNS = input_directory_3 / f'3_ai-{TARGET_STRUCTURE}_conservation_patterns-per_annogroup.tsv'

# Input files from Script 004
INPUT_ANNOGROUP_COMPLETE = input_directory_4 / f'4_ai-{TARGET_STRUCTURE}_annogroups-complete_ocl_summary-all_types.tsv'
INPUT_CLADE_STATS = input_directory_4 / f'4_ai-{TARGET_STRUCTURE}_clades-comprehensive_statistics.tsv'
INPUT_SPECIES_SUMMARIES = input_directory_4 / f'4_ai-{TARGET_STRUCTURE}_species-summaries.tsv'
INPUT_PATH_STATES = input_directory_4 / f'4_ai-{TARGET_STRUCTURE}_path_states-per_annogroup_per_species.tsv'

# Output directory
output_directory = base_output / '5-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files
OUTPUT_VALIDATION_REPORT = output_directory / f'5_ai-{TARGET_STRUCTURE}_validation_report.txt'
OUTPUT_ERROR_LOG = output_directory / f'5_ai-{TARGET_STRUCTURE}_validation_error_log.txt'
OUTPUT_QC_METRICS = output_directory / f'5_ai-{TARGET_STRUCTURE}_qc_metrics.tsv'

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

def load_annogroups():
    """
    Load annogroups and their species from the standardized file.

    Returns:
        annogroups___species: dict mapping annogroup_id to set of species names
    """
    logger.info( f"Loading annogroups from: {INPUT_ANNOGROUPS}" )

    annogroups___species = {}

    with open( INPUT_ANNOGROUPS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Annogroup_ID	Annogroup_Subtype	Species_Count	Species_List
        # annogroup_pfam_1	single	5	Homo_sapiens,Mus_musculus,...
        header = next( csv_reader )

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            species_list_string = parts[ 3 ]

            species_set = set()
            if species_list_string.strip():
                species_names = species_list_string.split( ',' )
                for species_name in species_names:
                    species_name = species_name.strip()
                    if species_name:
                        species_set.add( species_name )

            annogroups___species[ annogroup_id ] = species_set

    logger.info( f"Loaded {len( annogroups___species )} annogroups" )
    return annogroups___species


def load_phylogenetic_paths():
    """Load phylogenetic paths from Script 001 output."""
    logger.info( f"Loading phylogenetic paths from: {INPUT_PHYLOGENETIC_PATHS}" )

    species_clade_id_names___phylogenetic_paths = {}

    with open( INPUT_PHYLOGENETIC_PATHS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Leaf_Clade_ID	Path_Length	Phylogenetic_Path
        # C001_Fonticula_alba	3	C068_Basal,C069_Holomycota,C001_Fonticula_alba
        header = next( csv_reader )

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            leaf_clade_id = parts[ 0 ]
            phylogenetic_path_string = parts[ 2 ]

            path = [ clade.strip() for clade in phylogenetic_path_string.split( ',' ) if clade.strip() ]

            species_clade_id_names___phylogenetic_paths[ leaf_clade_id ] = path

    logger.info( f"Loaded {len( species_clade_id_names___phylogenetic_paths )} phylogenetic paths" )
    return species_clade_id_names___phylogenetic_paths


def load_origins():
    """Load annogroup origins from Script 002 output."""
    logger.info( f"Loading origins from: {INPUT_ORIGINS}" )

    annogroups___origins = {}

    with open( INPUT_ORIGINS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Annogroup_ID	Annogroup_Subtype	Origin_Phylogenetic_Block	Origin_Phylogenetic_Block_State	...
        # annogroup_pfam_1	single	C069_Holozoa::C082_Metazoa	C069_Holozoa::C082_Metazoa-O	...
        header = next( csv_reader )

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            phylogenetic_block = parts[ 2 ]

            # Derive child clade of origin block
            if '::' in phylogenetic_block:
                origin_child_clade_id_name = phylogenetic_block.split( '::', 1 )[ 1 ]
            else:
                origin_child_clade_id_name = 'NA'

            annogroups___origins[ annogroup_id ] = origin_child_clade_id_name

    logger.info( f"Loaded origins for {len( annogroups___origins )} annogroups" )
    return annogroups___origins


def load_block_statistics():
    """Load per-block conservation/loss statistics from Script 003 output."""
    logger.info( f"Loading block statistics from: {INPUT_BLOCK_STATS}" )

    block_stats = []

    with open( INPUT_BLOCK_STATS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Parent_Clade_ID_Name	Child_Clade_ID_Name	Inherited_Count	Conserved_Count	Lost_Count
        header = next( csv_reader )

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            stat = {
                'parent_clade': parts[ 0 ],
                'child_clade': parts[ 1 ],
                'inherited_count': int( parts[ 2 ] ),
                'conserved_count': int( parts[ 3 ] ),
                'lost_count': int( parts[ 4 ] ),
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
        INPUT_ANNOGROUPS,
        INPUT_PHYLOGENETIC_PATHS,
        INPUT_ORIGINS,
        INPUT_BLOCK_STATS,
        INPUT_ANNOGROUP_PATTERNS,
        INPUT_ANNOGROUP_COMPLETE,
        INPUT_CLADE_STATS,
        INPUT_SPECIES_SUMMARIES,
        INPUT_PATH_STATES
    ]

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

    counts = {
        'script_001': len( annogroups___species ),
        'script_002': len( annogroups___origins )
    }

    # Load Script 004 annogroup count (single-row header: subtract 1)
    with open( INPUT_ANNOGROUP_COMPLETE, 'r' ) as input_file:
        line_count = sum( 1 for line in input_file if line.strip() )
        counts[ 'script_004' ] = line_count - 1

    expected_count = counts[ 'script_001' ]

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
# SECTION 5: VALIDATION CHECK 4 - PER-BLOCK COUNT CONSISTENCY
# ============================================================================

def validate_block_count_consistency( block_stats ):
    """Per-block count sanity: conserved + lost must equal inherited for every block."""
    logger.info( "CHECK 4: Validating per-block count consistency..." )

    errors = []
    total_blocks = len( block_stats )
    passed = 0
    failed = 0

    for stat in block_stats:
        inherited = stat[ 'inherited_count' ]
        conserved = stat[ 'conserved_count' ]
        lost = stat[ 'lost_count' ]

        if conserved + lost != inherited:
            errors.append( {
                'check': 'block_count_consistency',
                'parent': stat[ 'parent_clade' ],
                'child': stat[ 'child_clade' ],
                'error': (
                    f"conserved ({conserved}) + lost ({lost}) = {conserved + lost} "
                    f"does not equal inherited ({inherited})"
                ),
            } )
            failed += 1
        else:
            passed += 1

    logger.info( f"  Passed: {passed}/{total_blocks} blocks" )
    logger.info( f"  Failed: {failed}/{total_blocks} blocks" )

    return {
        'name': 'Per-Block Count Consistency',
        'passed': passed,
        'failed': failed,
        'total': total_blocks,
        'errors': errors
    }


# ============================================================================
# SECTION 6: VALIDATION CHECK 5 - PER-ANNOGROUP BLOCK-STATE COUNTS
# ============================================================================

def validate_per_annogroup_counts():
    """Validate total_scored_blocks == P + L + X for every annogroup."""
    logger.info( "CHECK 5: Validating per-annogroup block-state counts..." )

    errors = []
    passed = 0
    failed = 0

    with open( INPUT_ANNOGROUP_COMPLETE, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Annogroup_ID	Annogroup_Subtype	Origin_Phylogenetic_Block	Origin_Phylogenetic_Block_State	Origin_Phylogenetic_Path	Species_Count	Total_Scored_Blocks	Conservation_Events	Loss_Events	Continued_Absence_Events	Species_List
        header = next( csv_reader )

        annogroup_count = 0

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            annogroup_id = parts[ 0 ]
            total_scored_blocks = int( parts[ 6 ] )
            conservation = int( parts[ 7 ] )
            loss_origin = int( parts[ 8 ] )
            continued_absence = int( parts[ 9 ] )

            annogroup_count += 1

            if total_scored_blocks != ( conservation + loss_origin + continued_absence ):
                errors.append( {
                    'check': 'per_annogroup_count_arithmetic',
                    'annogroup_id': annogroup_id,
                    'error': (
                        f"total_scored_blocks ({total_scored_blocks}) != "
                        f"conservation ({conservation}) + loss ({loss_origin}) + "
                        f"continued_absence ({continued_absence})"
                    ),
                } )
                failed += 1
            else:
                passed += 1

    logger.info( f"  Passed: {passed}/{annogroup_count} annogroups" )
    logger.info( f"  Failed: {failed}/{annogroup_count} annogroups" )

    return {
        'name': 'Per-Annogroup Block-State Counts',
        'passed': passed,
        'failed': failed,
        'total': annogroup_count,
        'errors': errors
    }


# ============================================================================
# SECTION 7: VALIDATION CHECK 6 - ORIGIN IN SPECIES PATHS
# ============================================================================

def validate_origin_in_species_paths( annogroups___origins, annogroups___species,
                                     species_clade_id_names___phylogenetic_paths ):
    """Validate that origin_clade_id_name appears in at least one phylogenetic path."""
    logger.info( "CHECK 6: Validating origin in species paths..." )

    errors = []
    total_annogroups = len( annogroups___origins )
    passed = 0
    failed = 0

    # Collect all clade_id_names across all paths
    all_path_clade_id_names = set()
    for species_clade_id_name, path in species_clade_id_names___phylogenetic_paths.items():
        for clade_id_name in path:
            all_path_clade_id_names.add( clade_id_name )

    for annogroup_id, origin_child_clade_id_name in annogroups___origins.items():
        if origin_child_clade_id_name not in all_path_clade_id_names:
            errors.append( {
                'check': 'origin_in_path',
                'annogroup_id': annogroup_id,
                'origin_child_clade_id_name': origin_child_clade_id_name,
                'error': f"Child clade_id_name of origin block '{origin_child_clade_id_name}' not found in any phylogenetic path"
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
# SECTION 8b: VALIDATION CHECK 8 - PHYLOGENETIC PATH-STATE INTEGRITY (Rule 7)
# ============================================================================

def validate_path_states( species_clade_id_names___phylogenetic_paths ):
    """
    Validate the per (annogroup, species) phylogenetic path-state file.

    Checks per row:
    1. Every path-state letter is in the Rule 7 alphabet {A, O, P, L, X}.
    2. Path-state length equals number of blocks on the species's path (path length - 1).
    3. At most one O letter.
    4. Letter sequence respects Rule 7 state machine: A*[O[P*[LX*]?]?]?
    5. Terminal letter matches species membership (True -> P or O; False -> not P or O).
    """
    logger.info( "CHECK 8: Validating phylogenetic path-state integrity..." )

    rule_7_alphabet = { 'A', 'O', 'P', 'L', 'X' }
    errors = []
    passed = 0
    failed = 0
    total = 0

    with open( INPUT_PATH_STATES, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        header = next( csv_reader )
        column_names___indices = {}
        for index, column_header in enumerate( header ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        required_columns = [
            'Annogroup_ID', 'Species_Clade_ID_Name', 'Species_In_Annogroup',
            'Phylogenetic_Path', 'Phylogenetic_Path_State'
        ]
        for column_name in required_columns:
            if column_name not in column_names___indices:
                errors.append( {
                    'check': 'header',
                    'error': f"Missing required column: {column_name}"
                } )
                failed += 1
                return {
                    'name': 'Phylogenetic Path-State Integrity',
                    'passed': passed, 'failed': failed, 'total': failed,
                    'errors': errors
                }

        annogroup_id_index = column_names___indices[ 'Annogroup_ID' ]
        species_clade_id_name_index = column_names___indices[ 'Species_Clade_ID_Name' ]
        species_in_annogroup_index = column_names___indices[ 'Species_In_Annogroup' ]
        phylogenetic_path_index = column_names___indices[ 'Phylogenetic_Path' ]
        phylogenetic_path_state_index = column_names___indices[ 'Phylogenetic_Path_State' ]

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            total += 1

            annogroup_id = parts[ annogroup_id_index ]
            species_clade_id_name = parts[ species_clade_id_name_index ]
            species_in_annogroup_string = parts[ species_in_annogroup_index ]
            phylogenetic_path_string = parts[ phylogenetic_path_index ]
            phylogenetic_path_state = parts[ phylogenetic_path_state_index ]

            species_in_annogroup = ( species_in_annogroup_string == 'True' )

            # 1. Alphabet check
            non_alphabet_letters = [ letter for letter in phylogenetic_path_state if letter not in rule_7_alphabet ]
            if non_alphabet_letters:
                errors.append( {
                    'check': 'alphabet',
                    'annogroup_id': annogroup_id,
                    'species_clade_id_name': species_clade_id_name,
                    'error': f"Path-state contains non-Rule-7 letters: {set( non_alphabet_letters )}"
                } )
                failed += 1
                continue

            # 2. Length check vs path
            path_clades = phylogenetic_path_string.split( ',' ) if phylogenetic_path_string else []
            expected_path_state_length = max( len( path_clades ) - 1, 0 )
            if len( phylogenetic_path_state ) != expected_path_state_length:
                errors.append( {
                    'check': 'length',
                    'annogroup_id': annogroup_id,
                    'species_clade_id_name': species_clade_id_name,
                    'error': ( f"Path-state length {len( phylogenetic_path_state )} does not match number of blocks "
                               f"{expected_path_state_length} (path has {len( path_clades )} clades)" )
                } )
                failed += 1
                continue

            # 3. At most one O
            origin_letter_count = phylogenetic_path_state.count( 'O' )
            if origin_letter_count > 1:
                errors.append( {
                    'check': 'multiple_origins',
                    'annogroup_id': annogroup_id,
                    'species_clade_id_name': species_clade_id_name,
                    'error': f"Path-state contains {origin_letter_count} O letters (expected at most 1)"
                } )
                failed += 1
                continue

            # 4. State-machine walk: A*[O[P*[LX*]?]?]?
            state_machine_violation = False
            phase = 'before_origin'
            for letter in phylogenetic_path_state:
                if phase == 'before_origin':
                    if letter == 'A':
                        pass
                    elif letter == 'O':
                        phase = 'after_origin'
                    else:
                        state_machine_violation = True
                        break
                elif phase == 'after_origin':
                    if letter == 'P':
                        pass
                    elif letter == 'L':
                        phase = 'after_loss'
                    else:
                        state_machine_violation = True
                        break
                elif phase == 'after_loss':
                    if letter == 'X':
                        pass
                    else:
                        state_machine_violation = True
                        break

            if state_machine_violation:
                errors.append( {
                    'check': 'state_sequence',
                    'annogroup_id': annogroup_id,
                    'species_clade_id_name': species_clade_id_name,
                    'error': ( f"Path-state '{phylogenetic_path_state}' violates Rule 7 sequence "
                               f"A* [O [P* [L X*]?]?]?" )
                } )
                failed += 1
                continue

            # 5. Terminal letter must match species membership.
            if phylogenetic_path_state:
                terminal_letter = phylogenetic_path_state[ -1 ]
                if species_in_annogroup and terminal_letter not in ( 'P', 'O' ):
                    errors.append( {
                        'check': 'terminal_membership',
                        'annogroup_id': annogroup_id,
                        'species_clade_id_name': species_clade_id_name,
                        'error': ( f"Species_In_Annogroup=True but path-state ends with '{terminal_letter}' "
                                   f"(expected P or O)" )
                    } )
                    failed += 1
                    continue
                if ( not species_in_annogroup ) and terminal_letter in ( 'P', 'O' ):
                    errors.append( {
                        'check': 'terminal_membership',
                        'annogroup_id': annogroup_id,
                        'species_clade_id_name': species_clade_id_name,
                        'error': ( f"Species_In_Annogroup=False but path-state ends with '{terminal_letter}' "
                                   f"(species would have the annogroup)" )
                    } )
                    failed += 1
                    continue

            passed += 1

    logger.info( f"  Passed: {passed}/{total} path-state rows" )
    logger.info( f"  Failed: {failed}/{total} path-state rows" )

    return {
        'name': 'Phylogenetic Path-State Integrity',
        'passed': passed,
        'failed': failed,
        'total': total,
        'errors': errors
    }


# ============================================================================
# SECTION 9: REPORT GENERATION
# ============================================================================

def generate_validation_report( validation_results ):
    """Generate comprehensive validation report."""
    logger.info( "Generating validation report..." )

    report = []
    report.append( "=" * 80 )
    report.append( "COMPREHENSIVE VALIDATION REPORT - ANNOTATIONS OCL PIPELINE" )
    report.append( "=" * 80 )
    report.append( f"Structure: {TARGET_STRUCTURE}" )
    report.append( f"Date: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    report.append( "" )

    total_checks = len( validation_results )
    total_passed = sum( 1 for result in validation_results if result[ 'failed' ] == 0 )
    total_failed = total_checks - total_passed

    report.append( "OVERALL SUMMARY" )
    report.append( "-" * 80 )
    report.append( f"Total validation checks: {total_checks}" )
    report.append( f"Checks passed: {total_passed}" )
    report.append( f"Checks failed: {total_failed}" )
    report.append( "" )

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
    logger.info( "" )

    # STEP 1: Load data for validation
    logger.info( "STEP 1: Loading data for validation..." )
    annogroups___species = load_annogroups()
    species_clade_id_names___phylogenetic_paths = load_phylogenetic_paths()
    annogroups___origins = load_origins()
    block_stats = load_block_statistics()
    logger.info( "" )

    # STEP 2: Run all 8 validation checks
    logger.info( "STEP 2: Running validation checks..." )
    validation_results = []

    validation_results.append( validate_file_integrity() )
    validation_results.append( validate_cross_script_consistency( annogroups___origins, annogroups___species ) )
    validation_results.append( validate_conservation_loss_arithmetic( block_stats ) )
    validation_results.append( validate_block_count_consistency( block_stats ) )
    validation_results.append( validate_per_annogroup_counts() )
    validation_results.append( validate_origin_in_species_paths( annogroups___origins, annogroups___species, species_clade_id_names___phylogenetic_paths ) )
    validation_results.append( validate_no_orphans( annogroups___species ) )
    validation_results.append( validate_path_states( species_clade_id_names___phylogenetic_paths ) )

    logger.info( "" )

    # STEP 3: Generate reports
    logger.info( "STEP 3: Generating validation reports..." )
    report = generate_validation_report( validation_results )
    write_error_log( validation_results )
    write_qc_metrics( validation_results )
    logger.info( "" )

    # STEP 4: Write validation report
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

    # STEP 5: Determine exit code - STRICT FAIL-FAST
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
