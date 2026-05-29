# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Shared utility for emitting run summary fragments
# Human: Eric Edsinger

"""
Run Summary Fragment Utility

Each pipeline script (001-005) calls emit_run_summary_fragment() at the end of
its work with a dict of key stats. The fragment is written as JSON to:

    {workflow_dir}/ai/logs/run_summary_fragments/{script_number:03d}_{structure_id}.json

Script 007 (the aggregator) reads all fragments, aggregates across structures,
and builds RUN_SUMMARY.md at the workflow root. See Script 007 for the
aggregation rules and output format.

This fragment-first design solves the concurrent-write problem when 105
structures run in parallel -- each structure writes its own file rather than
appending to a shared document.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def get_fragments_directory( workflow_directory ):
    """
    Get the fragments directory for this workflow run.

    Args:
        workflow_directory: Path to workflow directory (contains ai/, INPUT_user/, etc.)

    Returns:
        Path: {workflow_directory}/ai/logs/run_summary_fragments/
    """
    workflow_path = Path( workflow_directory )
    return workflow_path / 'ai' / 'logs' / 'run_summary_fragments'


def emit_run_summary_fragment( script_number, structure_id, stats, workflow_directory = None ):
    """
    Write a run summary fragment for this (script, structure) pair.

    Called by each pipeline script at the end of its work with a dict of
    interesting stats (counts, durations, key numbers). The aggregator
    (Script 007) reads all fragments and builds RUN_SUMMARY.md.

    Args:
        script_number: int, 1-5 for the analysis scripts
        structure_id: str, e.g. "001"
        stats: dict of stats to record. Expected keys vary by script but
               typically include 'duration_seconds' and script-specific counts.
        workflow_directory: Path to workflow directory. If None, inferred as
               two levels up from this script's __file__ location.

    Returns:
        Path to the written fragment file.
    """
    # Resolve workflow directory if not provided.
    # This script lives at: {workflow_dir}/ai/scripts/utils_run_summary.py
    # So workflow_dir is two levels up.
    if workflow_directory is None:
        workflow_directory = Path( __file__ ).parent.parent.parent

    fragments_directory = get_fragments_directory( workflow_directory )
    fragments_directory.mkdir( parents = True, exist_ok = True )

    fragment_filename = f"{script_number:03d}_{structure_id}.json"
    fragment_path = fragments_directory / fragment_filename

    # Add standard metadata
    fragment_data = {
        'script_number': script_number,
        'structure_id': structure_id,
        'timestamp': datetime.now().isoformat(),
        'stats': stats
    }

    with open( fragment_path, 'w' ) as output_file:
        json.dump( fragment_data, output_file, indent = 2 )

    return fragment_path


def read_all_fragments( workflow_directory ):
    """
    Read all run summary fragments in a workflow's fragments directory.

    Args:
        workflow_directory: Path to workflow directory

    Returns:
        list of dicts, one per fragment, sorted by (script_number, structure_id)
    """
    fragments_directory = get_fragments_directory( workflow_directory )

    if not fragments_directory.exists():
        return []

    fragments = []
    for fragment_path in sorted( fragments_directory.glob( '*.json' ) ):
        try:
            with open( fragment_path, 'r' ) as input_file:
                fragment_data = json.load( input_file )
                fragments.append( fragment_data )
        except ( json.JSONDecodeError, IOError ):
            continue

    fragments.sort( key = lambda f: ( f.get( 'script_number', 0 ), f.get( 'structure_id', '' ) ) )

    return fragments


def clear_fragments_directory( workflow_directory ):
    """
    Remove all existing fragments (called at start of a run to ensure clean state).

    Args:
        workflow_directory: Path to workflow directory
    """
    fragments_directory = get_fragments_directory( workflow_directory )

    if not fragments_directory.exists():
        return

    for fragment_path in fragments_directory.glob( '*.json' ):
        try:
            fragment_path.unlink()
        except OSError:
            pass
