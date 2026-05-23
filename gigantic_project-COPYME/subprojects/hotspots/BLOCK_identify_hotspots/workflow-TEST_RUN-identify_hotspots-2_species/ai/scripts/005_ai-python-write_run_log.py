#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Write workflow run log to ai/logs/
# Human: Eric Edsinger

"""
Write Workflow Run Log

This script creates a timestamped log file documenting each workflow run for
transparency and reproducibility. The log is written to:
    ai/logs/ (within this workflow directory)

This captures what the workflow did, when, with what inputs, and what it produced.

Usage:
    python3 005_ai-python-write_run_log.py \
        --workflow-name WORKFLOW_NAME \
        --subproject-name SUBPROJECT_NAME \
        --project-name PROJECT_NAME \
        --status success|failure \
        [--species-count N] \
        [--input-summary "description of inputs"] \
        [--output-summary "description of outputs"] \
        [--error-message "message"]
"""

import argparse
from datetime import datetime
from pathlib import Path


def get_workflow_log_path( script_dir: Path ) -> Path:
    """Get the workflow's ai/logs/ directory for run logs.

    Script is at: workflow-*/ai/scripts/NNN_ai-...py
    Logs go to:   workflow-*/ai/logs/
    """
    return script_dir.parent / 'logs'


def write_run_log(
    workflow_name: str,
    subproject_name: str,
    project_name: str,
    status: str,
    species_count: int = None,
    input_summary: str = None,
    output_summary: str = None,
    error_message: str = None,
) -> Path:
    """Write a timestamped run log to the workflow's ai/logs/ directory."""
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime( '%Y%m%d_%H%M%S' )
    timestamp_human = timestamp.strftime( '%Y-%m-%d %H:%M:%S' )

    script_dir = Path( __file__ ).parent
    log_dir = get_workflow_log_path( script_dir )
    log_dir.mkdir( parents = True, exist_ok = True )

    log_filename = f'run_{timestamp_str}-{subproject_name}_{status}.log'
    log_path = log_dir / log_filename

    log_lines = [
        '=' * 80,
        f'GIGANTIC Workflow Run Log - {workflow_name}',
        '=' * 80,
        '',
        '## Run Information',
        '',
        f'Timestamp:      {timestamp_human}',
        f'Project Name:   {project_name}',
        f'Subproject:     {subproject_name}',
        f'Workflow:       {workflow_name}',
        f'Status:         {status.upper()}',
        '',
    ]

    if species_count is not None:
        log_lines.extend( [
            '## Species',
            '',
            f'Species Count:  {species_count}',
            '',
        ] )

    if input_summary:
        log_lines.extend( [
            '## Input Summary',
            '',
            input_summary,
            '',
        ] )

    if output_summary:
        log_lines.extend( [
            '## Output Summary',
            '',
            output_summary,
            '',
        ] )

    if error_message:
        log_lines.extend( [
            '## Error',
            '',
            f'Error Message: {error_message}',
            '',
        ] )

    log_lines.extend( [
        '=' * 80,
        f'Log written to: {log_path}',
        '=' * 80,
    ] )

    output = '\n'.join( log_lines ) + '\n'
    with open( log_path, 'w' ) as output_log:
        output_log.write( output )

    return log_path


def main() -> None:
    parser = argparse.ArgumentParser( description = 'Write workflow run log to ai/logs/' )
    parser.add_argument( '--workflow-name', required = True )
    parser.add_argument( '--subproject-name', required = True )
    parser.add_argument( '--project-name', required = True )
    parser.add_argument( '--status', choices = [ 'success', 'failure' ], required = True )
    parser.add_argument( '--species-count', type = int, default = None )
    parser.add_argument( '--input-summary', default = None )
    parser.add_argument( '--output-summary', default = None )
    parser.add_argument( '--error-message', default = None )
    args = parser.parse_args()

    log_path = write_run_log(
        workflow_name = args.workflow_name,
        subproject_name = args.subproject_name,
        project_name = args.project_name,
        status = args.status,
        species_count = args.species_count,
        input_summary = args.input_summary,
        output_summary = args.output_summary,
        error_message = args.error_message,
    )

    print( f'Run log written to: {log_path}' )


if __name__ == '__main__':
    main()
