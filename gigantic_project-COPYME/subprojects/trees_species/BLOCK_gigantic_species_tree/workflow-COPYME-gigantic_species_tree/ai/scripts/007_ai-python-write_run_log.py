#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Write workflow run log to ai/logs/
# Human: Eric Edsinger

"""
GIGANTIC trees_species - BLOCK_gigantic_species_tree - Script 007:
Write Workflow Run Log

This script creates a timestamped log file documenting each workflow run for
transparency and reproducibility. The log is written to the workflow's
ai/logs/ directory alongside the NextFlow execution logs.

This captures what the workflow did, when, with what inputs, and what it
produced. It is the final step in the pipeline and should run after all
upstream scripts have completed (successfully or with soft-failures).

Usage (standalone or via NextFlow):
    python3 007_ai-python-write_run_log.py \\
        --workflow-name WORKFLOW_NAME \\
        --subproject-name SUBPROJECT_NAME \\
        --species-set-name SPECIES_SET_NAME \\
        --status success|failure \\
        [--leaf-count N] \\
        [--internal-count N] \\
        [--ancestral-clade-count N] \\
        [--input-summary "description"] \\
        [--output-summary "description"] \\
        [--error-message "message"]

Note: "project name" metadata is NOT included in the run log header. The
project identity is already clear from the directory path
(gigantic_project-<name>/subprojects/.../workflow-RUN_*/ai/logs/run_*.log).
Having a per-workflow project.name config was a GIGANTIC anti-pattern inherited
from copy-paste convention; see AI_GUIDE-project.md for the project-wide rule.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


def get_workflow_log_path( script_dir: Path ) -> Path:
    """
    Get the workflow's ai/logs/ directory for run logs.

    Script is at: workflow-*/ai/scripts/NNN_ai-...py
    Logs go to:   workflow-*/ai/logs/
    """
    log_dir = script_dir.parent / "logs"
    return log_dir


def write_run_log(
    workflow_name: str,
    subproject_name: str,
    species_set_name: str,
    status: str,
    leaf_count: int = None,
    internal_count: int = None,
    ancestral_clade_count: int = None,
    input_summary: str = None,
    output_summary: str = None,
    error_message: str = None
) -> Path:
    """
    Write a timestamped run log to the workflow's ai/logs/ directory.
    Returns the path to the created log file.
    """
    # Get timestamp
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime( "%Y%m%d_%H%M%S" )
    timestamp_human = timestamp.strftime( "%Y-%m-%d %H:%M:%S" )

    # Determine log directory (this script is in ai/scripts/, logs go to ai/logs/)
    script_dir = Path( __file__ ).parent.resolve()
    log_dir = get_workflow_log_path( script_dir )

    # Ensure directory exists
    log_dir.mkdir( parents = True, exist_ok = True )

    # Create log filename
    log_filename = f"run_{timestamp_str}-{subproject_name}_{status}.log"
    log_path = log_dir / log_filename

    # Build log content
    log_lines = [
        "=" * 80,
        f"GIGANTIC Workflow Run Log - {workflow_name}",
        "=" * 80,
        "",
        "## Run Information",
        "",
        f"Timestamp:         {timestamp_human}",
        f"Subproject:        {subproject_name}",
        f"Workflow:          {workflow_name}",
        f"Species Set:       {species_set_name}",
        f"Status:            {status.upper()}",
        "",
    ]

    if leaf_count is not None or internal_count is not None or ancestral_clade_count is not None:
        log_lines.append( "## Species Tree Structure" )
        log_lines.append( "" )
        if leaf_count is not None:
            log_lines.append( f"Leaves (species):              {leaf_count}" )
        if internal_count is not None:
            log_lines.append( f"Internal nodes (clades):       {internal_count}" )
        if ancestral_clade_count is not None:
            log_lines.append( f"Auto-named ancestral clades:   {ancestral_clade_count}" )
        log_lines.append( "" )

    if input_summary:
        log_lines.extend( [
            "## Input Summary",
            "",
            f"{input_summary}",
            "",
        ] )

    if output_summary:
        log_lines.extend( [
            "## Output Summary",
            "",
            f"{output_summary}",
            "",
        ] )

    if error_message:
        log_lines.extend( [
            "## Error",
            "",
            f"Error Message: {error_message}",
            "",
        ] )

    log_lines.extend( [
        "=" * 80,
        f"Log written to: {log_path}",
        "=" * 80,
    ] )

    # Write log
    with open( log_path, 'w' ) as output_log_file:
        output = '\n'.join( log_lines ) + '\n'
        output_log_file.write( output )

    return log_path


def main():
    parser = argparse.ArgumentParser(
        description = "Write workflow run log to ai/logs/ for GIGANTIC trees_species BLOCK_gigantic_species_tree"
    )
    parser.add_argument(
        '--workflow-name',
        required = True,
        help = "Name of the workflow"
    )
    parser.add_argument(
        '--subproject-name',
        required = True,
        help = "Name of the subproject"
    )
    parser.add_argument(
        '--species-set-name',
        required = True,
        help = "Species set identifier (e.g., species70)"
    )
    parser.add_argument(
        '--status',
        choices = [ 'success', 'failure' ],
        required = True,
        help = "Workflow completion status"
    )
    parser.add_argument(
        '--leaf-count',
        type = int,
        default = None,
        help = "Number of leaves (species) in the species tree"
    )
    parser.add_argument(
        '--internal-count',
        type = int,
        default = None,
        help = "Number of internal nodes (clades) in the species tree"
    )
    parser.add_argument(
        '--ancestral-clade-count',
        type = int,
        default = None,
        help = "Number of internal nodes auto-named as ancestral_clade_NNN"
    )
    parser.add_argument(
        '--input-summary',
        default = None,
        help = "Summary of workflow inputs"
    )
    parser.add_argument(
        '--output-summary',
        default = None,
        help = "Summary of workflow outputs"
    )
    parser.add_argument(
        '--error-message',
        default = None,
        help = "Error message if status is failure"
    )

    args = parser.parse_args()

    log_path = write_run_log(
        workflow_name = args.workflow_name,
        subproject_name = args.subproject_name,
        species_set_name = args.species_set_name,
        status = args.status,
        leaf_count = args.leaf_count,
        internal_count = args.internal_count,
        ancestral_clade_count = args.ancestral_clade_count,
        input_summary = args.input_summary,
        output_summary = args.output_summary,
        error_message = args.error_message
    )

    print( f"Run log written to: {log_path}" )


if __name__ == '__main__':
    main()
