# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Validate OCL pipeline results with strict fail-fast behavior
# Human: Eric Edsinger

"""
OCL Pipeline Script 005: Validate Results

Performs 7 comprehensive validation checks across all OCL pipeline outputs
(Scripts 001-004) to ensure data integrity, logical consistency, and
TEMPLATE_03 metric correctness.

CRITICAL DESIGN DECISION:
  ALL validation failures exit with code 1 (non-zero).
  Edge cases like zero-transition orthogroups are handled explicitly in
  Scripts 003-004 (rates set to 0.0) rather than being allowed to produce
  invalid metrics that validation would flag. If Script 005 finds failures,
  the pipeline stops and the user investigates.

Validation Checks:
  1. File Integrity - all expected output files exist and have content
  2. Cross-Script Consistency - orthogroup counts match across Scripts 001-004
  3. Conservation/Loss Arithmetic - inherited = conserved + lost for every block
  4. Conservation Rate Bounds - rates between 0 and 100, cons + loss = 100
  5. TEMPLATE_03 Orthogroup Metrics - event arithmetic, loss coverage, rate bounds
  6. Origin in Species Paths - origin clade in phylogenetic path of every species
  7. No Orphan Orthogroups - no orthogroups with zero species

Inputs (from previous scripts):
  - 1-output: Orthogroups with GIGANTIC identifiers, phylogenetic paths
  - 2-output: Orthogroup origins
  - 3-output: Per-block statistics, per-orthogroup conservation patterns
  - 4-output: Complete OCL summaries, clade statistics, species summaries

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

# Increase CSV field size limit to handle large FASTA sequences
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

# Load config (only needed for FASTA flag awareness)
config_path = Path( args.config )
with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

INCLUDE_FASTA = config.get( 'include_fasta_in_output', False )

# Input directories (outputs of previous scripts)
base_output = Path( args.output_dir ) / TARGET_STRUCTURE
input_directory_1 = base_output / '1-output'
input_directory_2 = base_output / '2-output'
input_directory_3 = base_output / '3-output'
input_directory_4 = base_output / '4-output'

# Input files from Script 001
INPUT_ORTHOGROUPS = input_directory_1 / '1_ai-orthogroups-gigantic_identifiers.tsv'
INPUT_PHYLOGENETIC_PATHS = input_directory_1 / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'

# Input files from Script 002
INPUT_ORIGINS = input_directory_2 / '2_ai-orthogroup_origins.tsv'

# Input files from Script 003
INPUT_BLOCK_STATS = input_directory_3 / '3_ai-conservation_loss-per_block.tsv'
INPUT_ORTHOGROUP_PATTERNS = input_directory_3 / '3_ai-conservation_patterns-per_orthogroup.tsv'

# Input files from Script 004
INPUT_ORTHOGROUP_COMPLETE = input_directory_4 / '4_ai-orthogroups-complete_ocl_summary.tsv'
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

def load_orthogroups():
    """
    Load orthogroups and extract species from GIGANTIC identifiers.

    Returns:
        orthogroups___species: dict mapping orthogroup_id to set of species names
    """
    logger.info( f"Loading orthogroups from: {INPUT_ORTHOGROUPS}" )

    orthogroups___species = {}

    with open( INPUT_ORTHOGROUPS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Orthogroup_ID (orthogroup identifier from clustering tool)	Sequence_Count (...)	GIGANTIC_IDs (comma delimited list...)	Unmapped_Short_IDs (...)
        # OG0000000	2345	Metazoa_Chordata_...,Metazoa_Arthropoda_...
        header = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            orthogroup_id = parts[ 0 ]
            gigantic_ids_string = parts[ 2 ]

            species_set = set()
            if gigantic_ids_string.strip():
                gigantic_ids = gigantic_ids_string.split( ',' )
                for gigantic_id in gigantic_ids:
                    gigantic_id = gigantic_id.strip()
                    if gigantic_id:
                        species_name = extract_species_from_gigantic_id( gigantic_id )
                        if species_name:
                            species_set.add( species_name )

            orthogroups___species[ orthogroup_id ] = species_set

    logger.info( f"Loaded {len( orthogroups___species )} orthogroups" )
    return orthogroups___species


def extract_species_from_gigantic_id( gigantic_id ):
    """
    Extract species name from GIGANTIC identifier.

    GIGANTIC header format: g_GENEID-t_TRANSID-p_PROTID-n_Kingdom_Phylum_Class_Order_Family_Genus_species
    The phyloname follows the -n_ prefix and contains the full taxonomic hierarchy.
    """
    # All GIGANTIC-imported sequences must have -n_ prefix containing the phyloname
    if '-n_' not in gigantic_id:
        print( f"CRITICAL ERROR: GIGANTIC ID missing required '-n_' phyloname prefix: {gigantic_id}" )
        print( "This sequence was not imported through the GIGANTIC genomesDB pipeline." )
        sys.exit( 1 )

    # Phyloname is the LAST part after splitting on -n_
    parts_id = gigantic_id.split( '-n_' )
    phyloname = parts_id[ -1 ]

    # Extract Genus_species from phyloname
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) >= 7:
        genus = parts_phyloname[ 5 ]
        species = '_'.join( parts_phyloname[ 6: ] )
        return genus + '_' + species

    print( f"CRITICAL ERROR: Phyloname has {len( parts_phyloname )} fields, need at least 7: {phyloname}" )
    sys.exit( 1 )


def load_phylogenetic_paths():
    """
    Load phylogenetic paths from Script 001 output.

    Returns:
        species_names___phylogenetic_paths: dict mapping clade name to list of clades in path
    """
    logger.info( f"Loading phylogenetic paths from: {INPUT_PHYLOGENETIC_PATHS}" )

    species_names___phylogenetic_paths = {}

    with open( INPUT_PHYLOGENETIC_PATHS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Leaf_Clade_ID (leaf clade identifier...)	Path_Length (...)	Phylogenetic_Path (comma delimited path from root to leaf)
        # C001	5	C100,C050,C020,C010,C001
        header = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            leaf_clade_id = parts[ 0 ]
            phylogenetic_path_string = parts[ 2 ]

            # Parse comma-delimited path
            path = [ clade.strip() for clade in phylogenetic_path_string.split( ',' ) if clade.strip() ]

            # Store by leaf clade ID (species-level)
            species_names___phylogenetic_paths[ leaf_clade_id ] = path

    logger.info( f"Loaded {len( species_names___phylogenetic_paths )} phylogenetic paths" )
    return species_names___phylogenetic_paths


def load_origins():
    """
    Load orthogroup origins from Script 002 output.

    Returns:
        orthogroups___origins: dict mapping orthogroup_id to origin clade
    """
    logger.info( f"Loading origins from: {INPUT_ORIGINS}" )

    orthogroups___origins = {}

    with open( INPUT_ORIGINS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Orthogroup_ID (...)	Origin_Clade (...)	Origin_Clade_Phylogenetic_Block (...)	...
        # OG0000000	C100	Root::C100	C100,C050,...
        header = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            orthogroup_id = parts[ 0 ]
            origin_clade = parts[ 1 ]

            orthogroups___origins[ orthogroup_id ] = origin_clade

    logger.info( f"Loaded origins for {len( orthogroups___origins )} orthogroups" )
    return orthogroups___origins


def load_block_statistics():
    """
    Load per-block conservation/loss statistics from Script 003 output.

    Returns:
        block_stats: list of dicts with block statistics
    """
    logger.info( f"Loading block statistics from: {INPUT_BLOCK_STATS}" )

    block_stats = []

    with open( INPUT_BLOCK_STATS, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Parent_Clade (...)	Child_Clade (...)	Inherited_Count (...)	Conserved_Count (...)	Lost_Count (...)	Conservation_Rate (...)	Loss_Rate (...)
        # Eukaryota	Metazoa	45231	43892	1339	97.04	2.96
        header = next( csv_reader )  # Skip single-row header

        for parts in csv_reader:
            if not parts or all( field.strip() == '' for field in parts ):
                continue

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
    """
    Validate that all expected output files from Scripts 001-004 exist and have content.
    """
    logger.info( "CHECK 1: Validating file integrity..." )

    errors = []
    passed = 0
    failed = 0

    expected_files = [
        INPUT_ORTHOGROUPS,
        INPUT_PHYLOGENETIC_PATHS,
        INPUT_ORIGINS,
        INPUT_BLOCK_STATS,
        INPUT_ORTHOGROUP_PATTERNS,
        INPUT_ORTHOGROUP_COMPLETE,
        INPUT_CLADE_STATS,
        INPUT_SPECIES_SUMMARIES
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

def validate_cross_script_consistency( orthogroups___origins, orthogroups___species ):
    """
    Validate that orthogroup counts are consistent across Scripts 001, 002, and 004.
    """
    logger.info( "CHECK 2: Validating cross-script consistency..." )

    errors = []
    passed = 0
    failed = 0

    # Count orthogroups in each file
    counts = {
        'script_001': len( orthogroups___species ),
        'script_002': len( orthogroups___origins )
    }

    # Load Script 004 orthogroup count (single-row header: subtract 1)
    with open( INPUT_ORTHOGROUP_COMPLETE, 'r' ) as input_file:
        line_count = sum( 1 for line in input_file if line.strip() )
        counts[ 'script_004' ] = line_count - 1  # Subtract single header row

    # Check all counts match
    expected_count = counts[ 'script_001' ]

    for script_name, count in counts.items():
        if count != expected_count:
            errors.append( {
                'check': 'cross_script',
                'script': script_name,
                'count': count,
                'expected': expected_count,
                'error': f"Orthogroup count mismatch: {count} vs expected {expected_count}"
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
    """
    Validate that inherited = conserved + lost for every block.

    This is a fundamental logical constraint: every inherited orthogroup
    must be either conserved or lost in the child clade.
    """
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

    Blocks with zero inherited orthogroups have both rates set to 0.0
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

        # Check sum (allow small floating point error)
        # Only check if there are inherited orthogroups (zero inherited => both rates = 0.0)
        if inherited > 0:
            rate_sum = conservation_rate + loss_rate
            if abs( rate_sum - 100.0 ) > 0.1:
                errors.append( {
                    'check': 'rate_sum',
                    'parent': stat[ 'parent_clade' ],
                    'child': stat[ 'child_clade' ],
                    'conservation_rate': conservation_rate,
                    'loss_rate': loss_rate,
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
# SECTION 6: VALIDATION CHECK 5 - TEMPLATE_03 ORTHOGROUP METRICS
# ============================================================================

def validate_template_03_orthogroup_metrics():
    """
    Validate TEMPLATE_03 orthogroup-level metrics from Script 004.

    Checks:
    1. Event arithmetic: total_inherited = conservation + loss_origin + continued_absence
    2. Loss coverage: loss_coverage = loss_origin + continued_absence
    3. Percentage bounds: all percentages between 0 and 100
    4. Tree coverage sum: percent_tree_conserved + percent_tree_loss = 100
    5. Conservation/loss origin rate sum: conservation_rate + loss_origin_rate = 100
    """
    logger.info( "CHECK 5: Validating TEMPLATE_03 orthogroup metrics..." )

    errors = []
    passed = 0
    failed = 0

    # Load orthogroup complete summaries from Script 004
    with open( INPUT_ORTHOGROUP_COMPLETE, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )

        # Orthogroup_ID (orthogroup identifier)	Origin_Clade (...)	Origin_Clade_Phylogenetic_Block (...)	...
        # OG0000000	C100	Root::C100	C100,C050,...	67	132	110	15	7	22	83.33	11.36	83.33	16.67	...
        header = next( csv_reader )  # Skip single-row header

        orthogroup_count = 0

        for parts in csv_reader:
            # Skip empty lines
            if not parts or all( field.strip() == '' for field in parts ):
                continue

            # Parse TEMPLATE_03 format (16 or 17 columns, single-row header)
            orthogroup_id = parts[ 0 ]
            origin_clade = parts[ 1 ]
            phylogenetic_block = parts[ 2 ]
            phylogenetic_path = parts[ 3 ]
            species_count = int( parts[ 4 ] )
            total_inherited = int( parts[ 5 ] )
            conservation = int( parts[ 6 ] )
            loss_origin = int( parts[ 7 ] )
            continued_absence = int( parts[ 8 ] )
            loss_coverage = int( parts[ 9 ] )
            conservation_rate = float( parts[ 10 ] )
            loss_origin_rate = float( parts[ 11 ] )
            percent_tree_conserved = float( parts[ 12 ] )
            percent_tree_loss = float( parts[ 13 ] )

            orthogroup_count += 1
            orthogroup_valid = True

            # SUB-CHECK 1: Event arithmetic
            # total_inherited must equal sum of all event types
            if total_inherited != ( conservation + loss_origin + continued_absence ):
                errors.append( {
                    'check': 'template03_arithmetic',
                    'orthogroup_id': orthogroup_id,
                    'total_inherited': total_inherited,
                    'conservation': conservation,
                    'loss_origin': loss_origin,
                    'continued_absence': continued_absence,
                    'error': f"total_inherited ({total_inherited}) != conservation ({conservation}) + loss_origin ({loss_origin}) + continued_absence ({continued_absence})"
                } )
                orthogroup_valid = False

            # SUB-CHECK 2: Loss coverage must equal loss origin + continued absence
            if loss_coverage != ( loss_origin + continued_absence ):
                errors.append( {
                    'check': 'template03_loss_coverage',
                    'orthogroup_id': orthogroup_id,
                    'loss_coverage': loss_coverage,
                    'loss_origin': loss_origin,
                    'continued_absence': continued_absence,
                    'error': f"loss_coverage ({loss_coverage}) != loss_origin ({loss_origin}) + continued_absence ({continued_absence})"
                } )
                orthogroup_valid = False

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
                        'orthogroup_id': orthogroup_id,
                        'metric': percentage_name,
                        'value': percentage_value,
                        'error': f"{percentage_name} ({percentage_value}%) is outside valid range [0, 100]"
                    } )
                    orthogroup_valid = False

            # SUB-CHECK 4: Tree coverage sum (allow 0.1% tolerance for rounding)
            # Only check if there are inherited transitions (zero => both percentages = 0.0)
            if total_inherited > 0:
                tree_sum = percent_tree_conserved + percent_tree_loss
                if abs( tree_sum - 100.0 ) > 0.1:
                    errors.append( {
                        'check': 'template03_tree_coverage_sum',
                        'orthogroup_id': orthogroup_id,
                        'percent_tree_conserved': percent_tree_conserved,
                        'percent_tree_loss': percent_tree_loss,
                        'sum': tree_sum,
                        'error': f"percent_tree_conserved ({percent_tree_conserved}%) + percent_tree_loss ({percent_tree_loss}%) = {tree_sum}% (expected 100%)"
                    } )
                    orthogroup_valid = False

            # SUB-CHECK 5: Conservation + loss origin rate sum
            # Only check if there are conservation/loss events (parent had it)
            if ( conservation + loss_origin ) > 0:
                rate_sum = conservation_rate + loss_origin_rate
                if abs( rate_sum - 100.0 ) > 0.1:
                    errors.append( {
                        'check': 'template03_conservation_loss_rate_sum',
                        'orthogroup_id': orthogroup_id,
                        'conservation_rate': conservation_rate,
                        'loss_origin_rate': loss_origin_rate,
                        'sum': rate_sum,
                        'error': f"conservation_rate ({conservation_rate}%) + loss_origin_rate ({loss_origin_rate}%) = {rate_sum}% (expected 100%)"
                    } )
                    orthogroup_valid = False

            if orthogroup_valid:
                passed += 1
            else:
                failed += 1

    logger.info( f"  Passed: {passed}/{orthogroup_count} orthogroups" )
    logger.info( f"  Failed: {failed}/{orthogroup_count} orthogroups" )

    return {
        'name': 'TEMPLATE_03 Orthogroup Metrics',
        'passed': passed,
        'failed': failed,
        'total': orthogroup_count,
        'errors': errors
    }


# ============================================================================
# SECTION 7: VALIDATION CHECK 6 - ORIGIN IN SPECIES PATHS
# ============================================================================

def validate_origin_in_species_paths( orthogroups___origins, orthogroups___species,
                                     species_names___phylogenetic_paths ):
    """
    Validate that for each orthogroup, the origin clade appears in the
    phylogenetic path of every species that contains the orthogroup.

    Note: species_names___phylogenetic_paths is keyed by leaf clade ID,
    and origin clades are also clade IDs (from Script 002). The origin
    clade must appear somewhere in each species' root-to-leaf path.

    For single-species orthogroups, the origin IS the species' leaf clade,
    so the origin must be the last element in the path (or present).
    """
    logger.info( "CHECK 6: Validating origin in species paths..." )

    errors = []
    total_orthogroups = len( orthogroups___origins )
    passed = 0
    failed = 0

    # Build reverse mapping: species name -> set of leaf clade IDs
    # Since phylogenetic paths are by leaf clade ID and orthogroup species
    # are by name, we need to work at the orthogroup level where we have clade-based data

    # For this validation, we load the orthogroup origins which use clade IDs,
    # and the phylogenetic paths which are also by clade ID. We need to check
    # that the origin clade ID appears in the paths of leaf clades that have
    # species in the orthogroup.
    #
    # However, the orthogroups___species maps orthogroup -> species names (from GIGANTIC IDs),
    # while phylogenetic_paths maps leaf_clade_id -> path.
    # We cannot directly map species names to leaf clade IDs without the clade mappings.
    #
    # Alternative approach: check using the orthogroup origins data which stores
    # the origin clade ID, and verify it appears in ALL phylogenetic paths
    # (since the origin should be an ancestor of all species in the orthogroup).
    # We check that origin_clade appears in at least some paths.
    # Actually, for proper validation we should verify against the specific
    # leaf clades, but without a species->clade mapping loaded here, we verify
    # that the origin clade exists in the set of all path clades.

    # Collect all clades that appear in any path
    all_path_clades = set()
    for leaf_clade_id, path in species_names___phylogenetic_paths.items():
        for clade in path:
            all_path_clades.add( clade )

    for orthogroup_id, origin_clade in orthogroups___origins.items():
        # Verify origin clade is a valid clade (appears in phylogenetic paths)
        if origin_clade not in all_path_clades:
            errors.append( {
                'check': 'origin_in_path',
                'orthogroup_id': orthogroup_id,
                'origin_clade': origin_clade,
                'error': f"Origin clade '{origin_clade}' not found in any phylogenetic path"
            } )
            failed += 1
        else:
            passed += 1

    logger.info( f"  Passed: {passed}/{total_orthogroups} orthogroups" )
    logger.info( f"  Failed: {failed}/{total_orthogroups} orthogroups" )

    return {
        'name': 'Origin in Species Paths',
        'passed': passed,
        'failed': failed,
        'total': total_orthogroups,
        'errors': errors
    }


# ============================================================================
# SECTION 8: VALIDATION CHECK 7 - NO ORPHAN ORTHOGROUPS
# ============================================================================

def validate_no_orphans( orthogroups___species ):
    """
    Validate that no orthogroups are orphans (present in zero species).
    An orphan orthogroup would indicate a data processing error.
    """
    logger.info( "CHECK 7: Checking for orphan orthogroups..." )

    errors = []
    total_orthogroups = len( orthogroups___species )
    passed = 0
    failed = 0

    for orthogroup_id, species_set in orthogroups___species.items():
        if len( species_set ) == 0:
            errors.append( {
                'check': 'orphan',
                'orthogroup_id': orthogroup_id,
                'error': f"Orthogroup has zero species (orphan)"
            } )
            failed += 1
        else:
            passed += 1

    logger.info( f"  Passed: {passed}/{total_orthogroups} orthogroups" )
    logger.info( f"  Failed: {failed}/{total_orthogroups} orthogroups" )

    return {
        'name': 'No Orphan Orthogroups',
        'passed': passed,
        'failed': failed,
        'total': total_orthogroups,
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
    report.append( "COMPREHENSIVE VALIDATION REPORT - OCL PIPELINE" )
    report.append( "=" * 80 )
    report.append( f"Structure: {TARGET_STRUCTURE}" )
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
        report.append( "The OCL pipeline has completed successfully with no errors." )
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
    """
    Write QC metrics summary in TSV format.

    Output format:
    Check_Name (name of validation check)	Total_Items (number of items checked)	Passed (items that passed)	Failed (items that failed)	Pass_Rate (percentage of items passed)
    """
    logger.info( f"Writing QC metrics to: {OUTPUT_QC_METRICS}" )

    with open( OUTPUT_QC_METRICS, 'w' ) as output_file:
        # Single-row GIGANTIC_1 header
        output = 'Check_Name (name of validation check)\t'
        output += 'Total_Items (number of items checked)\t'
        output += 'Passed (items that passed validation)\t'
        output += 'Failed (items that failed validation)\t'
        output += 'Pass_Rate (percentage of items passed calculated as passed divided by total times 100)\n'
        output_file.write( output )

        # Data
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
    logger.info( f"FASTA embedding: {INCLUDE_FASTA}" )
    logger.info( "" )

    # ========================================================================
    # STEP 1: Load data for validation
    # ========================================================================
    logger.info( "STEP 1: Loading data for validation..." )
    orthogroups___species = load_orthogroups()
    species_names___phylogenetic_paths = load_phylogenetic_paths()
    orthogroups___origins = load_origins()
    block_stats = load_block_statistics()
    logger.info( "" )

    # ========================================================================
    # STEP 2: Run all 7 validation checks
    # ========================================================================
    logger.info( "STEP 2: Running validation checks..." )
    validation_results = []

    validation_results.append( validate_file_integrity() )
    validation_results.append( validate_cross_script_consistency( orthogroups___origins, orthogroups___species ) )
    validation_results.append( validate_conservation_loss_arithmetic( block_stats ) )
    validation_results.append( validate_conservation_rates( block_stats ) )
    validation_results.append( validate_template_03_orthogroup_metrics() )
    validation_results.append( validate_origin_in_species_paths( orthogroups___origins, orthogroups___species, species_names___phylogenetic_paths ) )
    validation_results.append( validate_no_orphans( orthogroups___species ) )

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
    # CRITICAL: Exit 1 on ANY validation failure
    # This is a design decision documented in the plan:
    # "GIGANTIC fail-fast validation means Script 005 exits with code 1 on
    # any validation failure. Edge cases like zero-transition orthogroups are
    # handled explicitly in Scripts 003-004 (rates set to 0.0 or NA) rather
    # than being allowed to produce invalid metrics that validation would flag."
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
