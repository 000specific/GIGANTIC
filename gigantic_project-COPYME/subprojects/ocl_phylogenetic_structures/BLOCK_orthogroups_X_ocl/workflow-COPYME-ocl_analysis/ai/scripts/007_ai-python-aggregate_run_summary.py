#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 19 | Purpose: Aggregate run summary fragments into OUTPUT_pipeline/7-output/7_ai-run_summary.md
# Human: Eric Edsinger

"""
OCL Pipeline Script 007: Aggregate Run Summary (orthogroups_X_ocl)

Reads all run summary fragments written by Scripts 001-005 across all
structures and builds a single consolidated run summary under
OUTPUT_pipeline/7-output/.

Fragment location (per-structure per-script JSON):
    {workflow_dir}/ai/logs/run_summary_fragments/{NNN}_{structure_id}.json

Output:
    {workflow_dir}/OUTPUT_pipeline/7-output/7_ai-run_summary.md

This is the final step of the pipeline. It runs after validate_results and
aggregates everything into a human-readable summary showing:
- Overall run status (SUCCESS / FAILED / PARTIAL)
- Per-script aggregate stats (across all structures)
- Configuration and timing

For single-structure runs the summary shows exact counts.
For multi-structure runs the summary shows aggregate stats (total, min, max, median).

Design principle: fail-soft. This script should produce useful output even if
some structures failed upstream -- the whole point of RUN_SUMMARY.md is to
tell the user what happened, including partial failures.

Usage:
    python 007_ai-python-aggregate_run_summary.py --config ../../START_HERE-user_config.yaml
"""

import sys
import argparse
import statistics
from pathlib import Path
from datetime import datetime

import yaml

# Add scripts directory to path for utility imports
sys.path.insert( 0, str( Path( __file__ ).parent ) )
from utils_run_summary import read_all_fragments


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'OCL Pipeline Script 007: Aggregate run summary fragments into OUTPUT_pipeline/7-output/7_ai-run_summary.md',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type = str,
        required = True,
        help = 'Path to START_HERE-user_config.yaml'
    )

    parser.add_argument(
        '--workflow_dir',
        type = str,
        default = None,
        help = 'Path to workflow directory (default: inferred from config location)'
    )

    return parser.parse_args()


# ============================================================================
# AGGREGATION HELPERS
# ============================================================================

def aggregate_numeric_field( fragments, field_path ):
    """
    Aggregate a numeric field across fragments, returning stats.

    Args:
        fragments: list of fragment dicts
        field_path: list of keys to traverse (e.g., ['stats', 'orthogroups_total'])

    Returns:
        dict with total, min, max, median, mean -- or None if no values found
    """
    values = []
    for fragment in fragments:
        node = fragment
        try:
            for key in field_path:
                node = node[ key ]
            if isinstance( node, ( int, float ) ):
                values.append( node )
        except ( KeyError, TypeError ):
            continue

    if not values:
        return None

    return {
        'total': sum( values ),
        'min': min( values ),
        'max': max( values ),
        'median': statistics.median( values ),
        'mean': statistics.mean( values ),
        'count': len( values )
    }


def format_aggregate_stat( agg, label, single_structure = False ):
    """Format an aggregate stat dict as a Markdown bullet line."""
    if agg is None:
        return f"- {label}: (no data)"

    if single_structure or agg[ 'count' ] == 1:
        value = agg[ 'min' ]
        if isinstance( value, float ):
            return f"- {label}: {value:,.2f}"
        else:
            return f"- {label}: {value:,}"

    if all( isinstance( v, int ) for v in [ agg[ 'min' ], agg[ 'max' ], agg[ 'median' ] ] ):
        return ( f"- {label}: **{agg[ 'total' ]:,}** total "
                 f"({agg[ 'min' ]:,} min / {int( agg[ 'median' ] ):,} median / {agg[ 'max' ]:,} max "
                 f"across {agg[ 'count' ]} structures)" )
    else:
        return ( f"- {label}: **{agg[ 'total' ]:,.2f}** total "
                 f"({agg[ 'min' ]:,.2f} min / {agg[ 'median' ]:,.2f} median / {agg[ 'max' ]:,.2f} max "
                 f"across {agg[ 'count' ]} structures)" )


def format_duration_stat( agg, single_structure = False ):
    """Format duration stat line with human-readable seconds."""
    if agg is None:
        return "- Duration: (no data)"

    if single_structure or agg[ 'count' ] == 1:
        return f"- Duration: {agg[ 'min' ]:.1f}s"

    return ( f"- Duration: {int( agg[ 'median' ] )}s median "
             f"({agg[ 'min' ]:.1f}s min / {agg[ 'max' ]:.1f}s max "
             f"across {agg[ 'count' ]} structures)" )


def filter_fragments_by_script( fragments, script_number ):
    return [ f for f in fragments if f.get( 'script_number' ) == script_number ]


# Per-script "this structure completed" sentinel files. Used as the on-disk
# fallback when fragment JSONs are absent because tasks were cached on resume
# (NextFlow doesn't re-emit fragments for cached tasks). Each path is relative
# to OUTPUT_pipeline/structure_NNN/.
SCRIPT_SENTINEL_FILES = {
    1: '1-output/1_ai-structure_{nnn}_orthogroups-gigantic_identifiers.tsv',
    2: '2-output/2_ai-structure_{nnn}_orthogroup_origins.tsv',
    3: '3-output/3_ai-structure_{nnn}_conservation_loss-per_block.tsv',
    4: '4-output/4_ai-structure_{nnn}_orthogroups-complete_ocl_summary.tsv',
    5: '5-output/5_ai-structure_{nnn}_validation_report.txt',
}


def count_completed_structures_on_disk( workflow_directory, script_number, structure_ids ):
    """
    Count structures with on-disk evidence the given script completed.

    On-disk fallback for resume runs: cached tasks don't emit new fragment
    JSONs even though their outputs persist from the prior run. Without this
    fallback, Script 007 falsely reports PARTIAL when the data is actually
    complete.
    """
    sentinel_template = SCRIPT_SENTINEL_FILES.get( script_number )
    if sentinel_template is None:
        return 0
    output_base = workflow_directory / 'OUTPUT_pipeline'
    count = 0
    for structure_id in structure_ids:
        sentinel = output_base / f'structure_{structure_id}' / sentinel_template.format( nnn = structure_id )
        if sentinel.exists():
            count += 1
    return count


def detect_validation_failures_on_disk( workflow_directory, structure_ids, fragment_validation_status ):
    """
    Determine which structures failed validation by combining fragment data with
    on-disk validation reports. On resume, Script 005 fragments may be absent
    for cached structures; their validation status must be read from the
    persisted 5_ai-..._validation_report.txt files instead.
    """
    output_base = workflow_directory / 'OUTPUT_pipeline'
    failed = []
    for structure_id in structure_ids:
        if structure_id in fragment_validation_status:
            if fragment_validation_status[ structure_id ] != 'PASS':
                failed.append( structure_id )
            continue
        report_path = output_base / f'structure_{structure_id}' / '5-output' / f'5_ai-structure_{structure_id}_validation_report.txt'
        if not report_path.exists():
            failed.append( structure_id )
            continue
        report_text = report_path.read_text()
        if 'ALL VALIDATION CHECKS PASSED' not in report_text:
            failed.append( structure_id )
    return failed


# ============================================================================
# SECTION BUILDERS
# ============================================================================

def _empty_fragments_line( completion ):
    """Standard message for a script with no emitted fragments this run."""
    if completion is not None and completion[ 'fully_cached' ]:
        return f"- **CACHED FROM PRIOR RUN** ({completion[ 'on_disk_count' ]}/{completion[ 'expected' ]} structures complete on disk; no fresh stats from this run)"
    return "- **NOT RUN** (no fragments found for this script)"


def build_script_001_section( fragments, is_single, completion = None ):
    """Build the Script 001 (prepare inputs) section."""
    lines = [ "## Script 001: Prepare Inputs" ]

    if not fragments:
        lines.append( _empty_fragments_line( completion ) )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'orthogroups_total' ] ),
        'Orthogroups loaded', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'phylogenetic_blocks_loaded' ] ),
        'Phylogenetic blocks loaded', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'phylogenetic_paths_loaded' ] ),
        'Phylogenetic paths loaded', is_single
    ) )

    orthogroup_tool = fragments[ 0 ].get( 'stats', {} ).get( 'orthogroup_tool', 'unknown' )
    lines.append( f"- Orthogroup tool: **{orthogroup_tool}**" )

    return lines


def build_script_002_section( fragments, is_single, completion = None ):
    """Build the Script 002 (determine origins) section."""
    lines = [ "## Script 002: Determine Origins" ]

    if not fragments:
        lines.append( _empty_fragments_line( completion ) )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'origins_found' ] ),
        'Origins found', is_single
    ) )

    origins_not_found = aggregate_numeric_field( fragments, [ 'stats', 'origins_not_found' ] )
    if origins_not_found and origins_not_found[ 'total' ] > 0:
        lines.append( f"- ⚠️  Origins NOT found: {origins_not_found[ 'total' ]:,}" )
    else:
        lines.append( "- Origins not found: 0 (100% success)" )

    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'single_species_orthogroups' ] ),
        'Single-species orthogroups', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'multi_species_orthogroups' ] ),
        'Multi-species orthogroups', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'distinct_origin_transition_blocks' ] ),
        'Distinct origin transition blocks', is_single
    ) )

    return lines


def build_script_003_section( fragments, is_single, completion = None ):
    """Build the Script 003 (quantify conservation/loss) section."""
    lines = [ "## Script 003: Quantify Conservation and Loss (Rule 7 block-states)" ]

    if not fragments:
        lines.append( _empty_fragments_line( completion ) )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'phylogenetic_blocks' ] ),
        'Phylogenetic blocks analyzed', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'total_scored_blocks' ] ),
        'Total block-states classified', is_single
    ) )
    lines.append( "- Block-state counts:" )
    lines.append( "    " + format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'conservation_events_P' ] ),
        'P (Inherited Presence / Conservation)', is_single
    ).lstrip( '-' ).lstrip() )
    lines.append( "    " + format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'loss_events_L' ] ),
        'L (Loss event)', is_single
    ).lstrip( '-' ).lstrip() )
    lines.append( "    " + format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'continued_absence_events_X' ] ),
        'X (Inherited Loss)', is_single
    ).lstrip( '-' ).lstrip() )

    return lines


def build_script_004_section( fragments, is_single, completion = None ):
    """Build the Script 004 (comprehensive analysis) section."""
    lines = [ "## Script 004: Comprehensive OCL Summaries" ]

    if not fragments:
        lines.append( _empty_fragments_line( completion ) )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'orthogroup_summaries_total' ] ),
        'Orthogroup summaries', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'clades_analyzed' ] ),
        'Clades analyzed', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'species_analyzed' ] ),
        'Species analyzed', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'path_state_rows' ] ),
        'Path-state rows (orthogroup x species)', is_single
    ) )

    return lines


def build_script_005_section( fragments, is_single, completion = None ):
    """Build the Script 005 (validation) section."""
    lines = [ "## Script 005: Validation (Rule 7 fail-fast)" ]

    if not fragments:
        lines.append( _empty_fragments_line( completion ) )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )

    total_checks = 0
    total_checks_passed = 0
    total_checks_failed = 0
    failure_structures = []
    for fragment in fragments:
        stats = fragment.get( 'stats', {} )
        total_checks += stats.get( 'total_checks', 0 )
        total_checks_passed += stats.get( 'checks_passed', 0 )
        total_checks_failed += stats.get( 'checks_failed', 0 )
        if stats.get( 'validation_status' ) != 'PASS':
            failure_structures.append( fragment.get( 'structure_id', '?' ) )

    if failure_structures:
        lines.append( f"- ⚠️  **{len( failure_structures )} structure(s) had validation failures**: {', '.join( sorted( failure_structures )[ :10 ] )}" )
    else:
        lines.append( f"- **ALL validation checks PASSED** ({total_checks_passed}/{total_checks} checks across {len( fragments )} structure(s))" )

    per_check_totals = {}
    for fragment in fragments:
        per_check = fragment.get( 'stats', {} ).get( 'per_check_results', {} )
        for check_name, check_result in per_check.items():
            if check_name not in per_check_totals:
                per_check_totals[ check_name ] = { 'total': 0, 'passed': 0, 'failed': 0 }
            per_check_totals[ check_name ][ 'total' ] += check_result.get( 'total', 0 )
            per_check_totals[ check_name ][ 'passed' ] += check_result.get( 'passed', 0 )
            per_check_totals[ check_name ][ 'failed' ] += check_result.get( 'failed', 0 )

    if per_check_totals:
        lines.append( "- Per-check results:" )
        for check_name in sorted( per_check_totals.keys() ):
            result = per_check_totals[ check_name ]
            status = "✓" if result[ 'failed' ] == 0 else f"✗ ({result[ 'failed' ]} failed)"
            lines.append( f"    - {check_name}: {result[ 'passed' ]:,}/{result[ 'total' ]:,} pass {status}" )

    return lines


def compute_completion_info( fragments, expected_structures, workflow_directory, structure_ids ):
    """
    For each script (1-5), return how many structures completed via fragment
    emission this run vs. on-disk artifacts (resume cache). The effective count
    is the max of the two: any structure with EITHER signal counts as done.
    """
    info = {}
    for script_num in range( 1, 6 ):
        fragment_count = len( filter_fragments_by_script( fragments, script_num ) )
        on_disk_count = count_completed_structures_on_disk( workflow_directory, script_num, structure_ids )
        info[ script_num ] = {
            'fragment_count': fragment_count,
            'on_disk_count': on_disk_count,
            'effective_count': max( fragment_count, on_disk_count ),
            'expected': expected_structures,
            'fully_cached': ( fragment_count == 0 and on_disk_count == expected_structures ),
        }
    return info


def determine_overall_status( fragments, expected_structures, workflow_directory, structure_ids, completion_info ):
    """
    Determine overall run status using both emitted fragments and on-disk
    artifacts. The on-disk fallback is critical for resume runs where cached
    tasks don't re-emit fragments but their output files persist.

    Returns:
        tuple: (status_string, status_detail)
    """
    fragment_validation_status = {}
    for fragment in filter_fragments_by_script( fragments, 5 ):
        sid = fragment.get( 'structure_id' )
        status = fragment.get( 'stats', {} ).get( 'validation_status' )
        if sid:
            fragment_validation_status[ sid ] = status

    failed_validations = detect_validation_failures_on_disk(
        workflow_directory, structure_ids, fragment_validation_status
    )

    all_complete = all(
        completion_info[ n ][ 'effective_count' ] == expected_structures for n in range( 1, 6 )
    )

    cached_scripts = [ n for n in range( 1, 6 ) if completion_info[ n ][ 'fully_cached' ] ]
    resume_indicator = ""
    if cached_scripts:
        resume_indicator = f" (Scripts {', '.join( str( n ) for n in cached_scripts )} fully cached from prior run -- no fresh stats this run)"

    if all_complete and not failed_validations:
        return ( "SUCCESS", f"All 5 scripts completed for {expected_structures} structure(s). All validation checks passed.{resume_indicator}" )
    elif all_complete and failed_validations:
        sample = ', '.join( sorted( failed_validations )[ :10 ] )
        return ( "FAILED", f"All scripts ran but {len( failed_validations )} structure(s) had validation failures: {sample}" )
    else:
        missing = []
        for n in range( 1, 6 ):
            if completion_info[ n ][ 'effective_count' ] < expected_structures:
                missing.append( f"Script {n:03d}: {completion_info[ n ][ 'effective_count' ]}/{expected_structures}" )
        return ( "PARTIAL", f"Incomplete run. Missing on-disk outputs: {', '.join( missing )}" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    args = parse_arguments()

    config_path = Path( args.config ).resolve()
    if not config_path.exists():
        print( f"CRITICAL ERROR: Configuration file not found: {config_path}" )
        sys.exit( 1 )

    with open( config_path, 'r' ) as config_file:
        config = yaml.safe_load( config_file )

    if args.workflow_dir:
        workflow_directory = Path( args.workflow_dir ).resolve()
    else:
        workflow_directory = config_path.parent

    fragments = read_all_fragments( workflow_directory )
    print( f"Read {len( fragments )} run summary fragments" )

    manifest_path = workflow_directory / config[ 'inputs' ][ 'structure_manifest' ]
    expected_structures = 0
    structure_ids = []
    if manifest_path.exists():
        with open( manifest_path, 'r' ) as manifest_file:
            header = manifest_file.readline()
            for line in manifest_file:
                line = line.strip()
                if line:
                    structure_ids.append( line.split( '\t' )[ 0 ] )
        expected_structures = len( structure_ids )

    is_single = ( expected_structures == 1 )

    completion_info = compute_completion_info( fragments, expected_structures, workflow_directory, structure_ids )
    status, status_detail = determine_overall_status(
        fragments, expected_structures, workflow_directory, structure_ids, completion_info
    )

    run_label = config.get( 'run_label', 'unknown' )
    species_set = config.get( 'species_set_name', 'unknown' )
    orthogroup_tool = config.get( 'orthogroup_tool', 'unknown' )
    include_fasta = config.get( 'include_fasta_in_output', False )
    execution_mode = config.get( 'execution_mode', 'local' )
    parallelism_mode = config.get( 'parallelism_mode', 'local' )

    status_emoji = { 'SUCCESS': '✅', 'FAILED': '❌', 'PARTIAL': '⚠️' }.get( status, '?' )

    lines = []
    lines.append( f"# Workflow Run Summary: {run_label}" )
    lines.append( "" )
    lines.append( f"**Status**: {status_emoji} **{status}** -- {status_detail}" )
    lines.append( "" )
    lines.append( f"**Generated**: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    lines.append( "" )

    # Configuration block
    lines.append( "## Configuration" )
    lines.append( "" )
    lines.append( f"- Run label: `{run_label}`" )
    lines.append( f"- Species set: `{species_set}`" )
    lines.append( f"- Orthogroup tool: `{orthogroup_tool}`" )
    lines.append( f"- Include FASTA in output: `{include_fasta}`" )
    lines.append( f"- Structures requested: **{expected_structures}** ({', '.join( structure_ids[ :10 ] )}{'...' if len( structure_ids ) > 10 else ''})" )
    lines.append( f"- Execution mode: `{execution_mode}` / parallelism: `{parallelism_mode}`" )
    lines.append( "" )

    lines.append( "---" )
    lines.append( "" )
    lines.extend( build_script_001_section( filter_fragments_by_script( fragments, 1 ), is_single, completion_info[ 1 ] ) )
    lines.append( "" )
    lines.extend( build_script_002_section( filter_fragments_by_script( fragments, 2 ), is_single, completion_info[ 2 ] ) )
    lines.append( "" )
    lines.extend( build_script_003_section( filter_fragments_by_script( fragments, 3 ), is_single, completion_info[ 3 ] ) )
    lines.append( "" )
    lines.extend( build_script_004_section( filter_fragments_by_script( fragments, 4 ), is_single, completion_info[ 4 ] ) )
    lines.append( "" )
    lines.extend( build_script_005_section( filter_fragments_by_script( fragments, 5 ), is_single, completion_info[ 5 ] ) )
    lines.append( "" )

    # Primary output files
    lines.append( "---" )
    lines.append( "" )
    lines.append( "## Primary Output Files" )
    lines.append( "" )
    lines.append( "Per-structure orthogroup complete summary (primary downstream file):" )
    lines.append( "```" )
    for structure_id in structure_ids[ :5 ]:
        lines.append( f"OUTPUT_pipeline/structure_{structure_id}/4-output/4_ai-orthogroups-complete_ocl_summary.tsv" )
    if len( structure_ids ) > 5:
        lines.append( f"... plus {len( structure_ids ) - 5} more" )
    lines.append( "```" )
    lines.append( "" )
    lines.append( f"Downstream symlinks: `../../output_to_input/BLOCK_orthogroups_X_ocl/{run_label}/`" )
    lines.append( "" )

    # Write the consolidated run summary into the workflow outputs
    # (gigantic_conventions Section 31): the final summary script lands in
    # OUTPUT_pipeline/7-output/, not at the workflow root.
    output_directory = workflow_directory / 'OUTPUT_pipeline' / '7-output'
    output_directory.mkdir( parents = True, exist_ok = True )
    summary_path = output_directory / '7_ai-run_summary.md'
    with open( summary_path, 'w' ) as output_file:
        output_file.write( '\n'.join( lines ) + '\n' )

    print( f"Wrote run summary to: {summary_path}" )
    print( f"Overall status: {status}" )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
