#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Aggregate run summary fragments into RUN_SUMMARY.md
# Human: Eric Edsinger

"""
OCL Pipeline Script 007: Aggregate Run Summary

Reads all run summary fragments written by Scripts 001-005 across all
structures and builds a single RUN_SUMMARY.md at the workflow root.

Fragment location (per-structure per-script JSON):
    {workflow_dir}/ai/logs/run_summary_fragments/{NNN}_{structure_id}.json

Output:
    {workflow_dir}/RUN_SUMMARY.md

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
        description = 'OCL Pipeline Script 007: Aggregate run summary fragments into RUN_SUMMARY.md',
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
        field_path: list of keys to traverse (e.g., ['stats', 'annogroups_total'])

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
        # Single value -- show as-is
        value = agg[ 'min' ]
        if isinstance( value, float ):
            return f"- {label}: {value:,.2f}"
        else:
            return f"- {label}: {value:,}"

    # Multi-structure -- show aggregate
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
    """Get all fragments for a specific script number."""
    return [ f for f in fragments if f.get( 'script_number' ) == script_number ]


# ============================================================================
# SECTION BUILDERS
# ============================================================================

def build_script_001_section( fragments, is_single ):
    """Build the Script 001 (create annogroups) section."""
    lines = [ "## Script 001: Create Annogroups" ]

    if not fragments:
        lines.append( "- **NOT RUN** (no fragments found for this script)" )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'annogroups_total' ] ),
        'Annogroups created', is_single
    ) )

    # Per-subtype breakdown
    subtype_keys = set()
    for fragment in fragments:
        subtype_counts = fragment.get( 'stats', {} ).get( 'annogroups_by_subtype', {} )
        subtype_keys.update( subtype_counts.keys() )

    if subtype_keys:
        lines.append( "- By subtype:" )
        for subtype in sorted( subtype_keys ):
            values = [ f.get( 'stats', {} ).get( 'annogroups_by_subtype', {} ).get( subtype, 0 ) for f in fragments ]
            if all( v == values[ 0 ] for v in values ) or is_single:
                lines.append( f"    - {subtype}: {values[ 0 ]:,}" )
            else:
                lines.append( f"    - {subtype}: {sum( values ):,} total ({min( values ):,}-{max( values ):,} range)" )

    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'species_with_annotations' ] ),
        'Species with annotations', is_single
    ) )

    # Show annotation database (same across all structures)
    database = fragments[ 0 ].get( 'stats', {} ).get( 'annotation_database', 'unknown' )
    lines.append( f"- Annotation database: **{database}**" )

    return lines


def build_script_002_section( fragments, is_single ):
    """Build the Script 002 (determine origins) section."""
    lines = [ "## Script 002: Determine Origins" ]

    if not fragments:
        lines.append( "- **NOT RUN**" )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'origins_found' ] ),
        'Origins found', is_single
    ) )

    # Highlight if any origins failed
    origins_not_found = aggregate_numeric_field( fragments, [ 'stats', 'origins_not_found' ] )
    if origins_not_found and origins_not_found[ 'total' ] > 0:
        lines.append( f"- ⚠️  Origins NOT found: {origins_not_found[ 'total' ]:,}" )
    else:
        lines.append( "- Origins not found: 0 (100% success)" )

    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'single_species_annogroups' ] ),
        'Single-species annogroups', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'multi_species_annogroups' ] ),
        'Multi-species annogroups', is_single
    ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'distinct_origin_transition_blocks' ] ),
        'Distinct origin transition blocks', is_single
    ) )

    return lines


def build_script_003_section( fragments, is_single ):
    """Build the Script 003 (quantify conservation/loss) section."""
    lines = [ "## Script 003: Quantify Conservation and Loss (Rule 7 block-states)" ]

    if not fragments:
        lines.append( "- **NOT RUN**" )
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


def build_script_004_section( fragments, is_single ):
    """Build the Script 004 (comprehensive analysis) section."""
    lines = [ "## Script 004: Comprehensive OCL Summaries" ]

    if not fragments:
        lines.append( "- **NOT RUN**" )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )
    lines.append( format_aggregate_stat(
        aggregate_numeric_field( fragments, [ 'stats', 'annogroup_summaries_total' ] ),
        'Annogroup summaries (all subtypes)', is_single
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
        'Path-state rows (annogroup x species)', is_single
    ) )

    return lines


def build_script_005_section( fragments, is_single ):
    """Build the Script 005 (validation) section."""
    lines = [ "## Script 005: Validation (Rule 7 fail-fast)" ]

    if not fragments:
        lines.append( "- **NOT RUN**" )
        return lines

    lines.append( format_duration_stat( aggregate_numeric_field( fragments, [ 'stats', 'duration_seconds' ] ), is_single ) )

    # Aggregate pass/fail across structures
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

    # Per-check detail (sum across structures)
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


def determine_overall_status( fragments, expected_structures ):
    """
    Determine overall run status.

    Returns:
        tuple: (status_string, status_detail)
            status_string: "SUCCESS" / "FAILED" / "PARTIAL"
            status_detail: human-readable explanation
    """
    # Count fragments per script
    script_counts = {}
    for script_num in range( 1, 6 ):
        script_counts[ script_num ] = len( filter_fragments_by_script( fragments, script_num ) )

    # Check Script 005 validation status
    validation_fragments = filter_fragments_by_script( fragments, 5 )
    failed_validations = [ f for f in validation_fragments if f.get( 'stats', {} ).get( 'validation_status' ) != 'PASS' ]

    # Did every script run for every structure?
    all_complete = all( script_counts[ n ] == expected_structures for n in range( 1, 6 ) )

    if all_complete and not failed_validations:
        return ( "SUCCESS", f"All 5 scripts completed for {expected_structures} structure(s). All validation checks passed." )
    elif all_complete and failed_validations:
        return ( "FAILED", f"All scripts ran but {len( failed_validations )} structure(s) had validation failures." )
    else:
        missing = []
        for n in range( 1, 6 ):
            if script_counts[ n ] < expected_structures:
                missing.append( f"Script {n:03d}: {script_counts[ n ]}/{expected_structures}" )
        return ( "PARTIAL", f"Incomplete run. Missing fragments: {', '.join( missing )}" )


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function."""
    args = parse_arguments()

    # Load configuration
    config_path = Path( args.config ).resolve()
    if not config_path.exists():
        print( f"CRITICAL ERROR: Configuration file not found: {config_path}" )
        sys.exit( 1 )

    with open( config_path, 'r' ) as config_file:
        config = yaml.safe_load( config_file )

    # Determine workflow directory (parent of config file by default)
    if args.workflow_dir:
        workflow_directory = Path( args.workflow_dir ).resolve()
    else:
        workflow_directory = config_path.parent

    # Read all fragments
    fragments = read_all_fragments( workflow_directory )
    print( f"Read {len( fragments )} run summary fragments" )

    # Determine expected structures from manifest
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

    # Determine overall status
    status, status_detail = determine_overall_status( fragments, expected_structures )

    # Build the Markdown document
    run_label = config.get( 'run_label', 'unknown' )
    species_set = config.get( 'species_set_name', 'unknown' )
    annotation_database = config.get( 'annotation_database', 'unknown' )
    annogroup_subtypes = config.get( 'annogroup_subtypes', [] )
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
    lines.append( f"- Annotation database: `{annotation_database}`" )
    lines.append( f"- Annogroup subtypes: {', '.join( annogroup_subtypes )}" )
    lines.append( f"- Structures requested: **{expected_structures}** ({', '.join( structure_ids[ :10 ] )}{'...' if len( structure_ids ) > 10 else ''})" )
    lines.append( f"- Execution mode: `{execution_mode}` / parallelism: `{parallelism_mode}`" )
    lines.append( "" )

    # Script sections
    lines.append( "---" )
    lines.append( "" )
    lines.extend( build_script_001_section( filter_fragments_by_script( fragments, 1 ), is_single ) )
    lines.append( "" )
    lines.extend( build_script_002_section( filter_fragments_by_script( fragments, 2 ), is_single ) )
    lines.append( "" )
    lines.extend( build_script_003_section( filter_fragments_by_script( fragments, 3 ), is_single ) )
    lines.append( "" )
    lines.extend( build_script_004_section( filter_fragments_by_script( fragments, 4 ), is_single ) )
    lines.append( "" )
    lines.extend( build_script_005_section( filter_fragments_by_script( fragments, 5 ), is_single ) )
    lines.append( "" )

    # Primary output files
    lines.append( "---" )
    lines.append( "" )
    lines.append( "## Primary Output Files" )
    lines.append( "" )
    lines.append( "Per-structure all-subtypes summary (primary downstream file):" )
    lines.append( "```" )
    for structure_id in structure_ids[ :5 ]:
        lines.append( f"OUTPUT_pipeline/structure_{structure_id}/4-output/4_ai-structure_{structure_id}_annogroups-complete_ocl_summary-all_types.tsv" )
    if len( structure_ids ) > 5:
        lines.append( f"... plus {len( structure_ids ) - 5} more" )
    lines.append( "```" )
    lines.append( "" )
    lines.append( f"Downstream symlinks: `../../output_to_input/BLOCK_ocl_analysis/{run_label}/`" )
    lines.append( "" )

    # Write the summary
    summary_path = workflow_directory / 'RUN_SUMMARY.md'
    with open( summary_path, 'w' ) as output_file:
        output_file.write( '\n'.join( lines ) + '\n' )

    print( f"Wrote RUN_SUMMARY.md to: {summary_path}" )
    print( f"Overall status: {status}" )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
