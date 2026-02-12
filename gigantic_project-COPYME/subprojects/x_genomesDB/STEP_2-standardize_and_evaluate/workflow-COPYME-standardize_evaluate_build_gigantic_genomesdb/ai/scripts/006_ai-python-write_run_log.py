#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Write workflow run log to research_notebook
# Human: Eric Edsinger

"""
Write Workflow Run Log to Research Notebook

This script creates a timestamped log file documenting each workflow run for
transparency and reproducibility. The log is written to:
    research_notebook/research_ai/subproject-phylonames/logs/

This serves as an AI lab notebook - capturing what the workflow did, when,
with what inputs, and what it produced.

Usage:
    python3 005_ai-python-write_run_log.py \\
        --project-name PROJECT_NAME \\
        --species-count N \\
        --species-file PATH \\
        --output-file PATH \\
        --status success|failure \\
        [--error-message "message"]
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def get_research_notebook_path( workflow_dir: Path ) -> Path:
    """
    Calculate path to research_notebook from workflow directory.

    Workflow is at: subprojects/phylonames/workflow-.../
    Research notebook is at: research_notebook/research_ai/subproject-phylonames/logs/
    """
    # Navigate up to project root then into research_notebook
    project_root = workflow_dir.parent.parent.parent
    log_dir = project_root / "research_notebook" / "research_ai" / "subproject-phylonames" / "logs"
    return log_dir


def read_species_list( species_file: Path ) -> list:
    """Read species from file, ignoring comments and blank lines."""
    species = []
    if species_file.exists():
        with open( species_file, 'r' ) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith( '#' ):
                    species.append( line )
    return species


def read_output_mapping( output_file: Path ) -> dict:
    """Read the generated mapping file and return summary stats."""
    results = {
        'species_mapped': 0,
        'sample_mappings': []
    }

    if output_file.exists():
        with open( output_file, 'r' ) as f:
            lines = f.readlines()
            # Skip header
            data_lines = [ l for l in lines[ 1: ] if l.strip() ]
            results[ 'species_mapped' ] = len( data_lines )
            # Get first 3 as samples
            for line in data_lines[ :3 ]:
                parts = line.strip().split( '\t' )
                if len( parts ) >= 2:
                    results[ 'sample_mappings' ].append( {
                        'genus_species': parts[ 0 ],
                        'phyloname': parts[ 1 ]
                    } )

    return results


def write_run_log(
    project_name: str,
    species_count: int,
    species_file: Path,
    output_file: Path,
    status: str,
    error_message: str = None
) -> Path:
    """
    Write a timestamped run log to research_notebook.

    Returns the path to the created log file.
    """
    # Get timestamp
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime( "%Y%m%d_%H%M%S" )
    timestamp_human = timestamp.strftime( "%Y-%m-%d %H:%M:%S" )

    # Determine workflow directory (this script is in ai/scripts/)
    script_dir = Path( __file__ ).parent
    workflow_dir = script_dir.parent.parent

    # Get log directory
    log_dir = get_research_notebook_path( workflow_dir )

    # Ensure directory exists
    log_dir.mkdir( parents = True, exist_ok = True )

    # Create log filename
    log_filename = f"run_{timestamp_str}-phylonames_{status}.log"
    log_path = log_dir / log_filename

    # Read species list for details
    species_list = read_species_list( species_file )

    # Read output mapping for results
    output_results = read_output_mapping( output_file )

    # Build log content
    log_lines = [
        "=" * 80,
        "GIGANTIC Phylonames Workflow Run Log",
        "=" * 80,
        "",
        "## Run Information",
        "",
        f"Timestamp:      {timestamp_human}",
        f"Project Name:   {project_name}",
        f"Status:         {status.upper()}",
        "",
        "## Input",
        "",
        f"Species File:   {species_file}",
        f"Species Count:  {species_count}",
        "",
        "Species List:",
    ]

    for species in species_list:
        log_lines.append( f"  - {species}" )

    log_lines.extend( [
        "",
        "## Output",
        "",
        f"Output File:    {output_file}",
        f"Species Mapped: {output_results[ 'species_mapped' ]}",
        "",
    ] )

    if output_results[ 'sample_mappings' ]:
        log_lines.append( "Sample Mappings (first 3):" )
        for mapping in output_results[ 'sample_mappings' ]:
            log_lines.append( f"  {mapping[ 'genus_species' ]} → {mapping[ 'phyloname' ]}" )
        log_lines.append( "" )

    if error_message:
        log_lines.extend( [
            "## Error",
            "",
            f"Error Message: {error_message}",
            "",
        ] )

    log_lines.extend( [
        "## Workflow Details",
        "",
        "Pipeline: phylonames (workflow-COPYME-generate_phylonames)",
        "Scripts executed:",
        "  1. 001_ai-bash-download_ncbi_taxonomy.sh",
        "  2. 002_ai-python-generate_phylonames.py",
        "  3. 003_ai-python-create_species_mapping.py",
        "",
        "=" * 80,
        f"Log written to: {log_path}",
        "=" * 80,
    ] )

    # Write log
    with open( log_path, 'w' ) as f:
        f.write( '\n'.join( log_lines ) + '\n' )

    return log_path


def main():
    parser = argparse.ArgumentParser(
        description = "Write workflow run log to research_notebook"
    )
    parser.add_argument(
        '--project-name',
        required = True,
        help = "Project name from config"
    )
    parser.add_argument(
        '--species-count',
        type = int,
        required = True,
        help = "Number of species processed"
    )
    parser.add_argument(
        '--species-file',
        required = True,
        help = "Path to species list file"
    )
    parser.add_argument(
        '--output-file',
        required = True,
        help = "Path to output mapping file"
    )
    parser.add_argument(
        '--status',
        choices = [ 'success', 'failure' ],
        required = True,
        help = "Workflow completion status"
    )
    parser.add_argument(
        '--error-message',
        default = None,
        help = "Error message if status is failure"
    )

    args = parser.parse_args()

    log_path = write_run_log(
        project_name = args.project_name,
        species_count = args.species_count,
        species_file = Path( args.species_file ),
        output_file = Path( args.output_file ),
        status = args.status,
        error_message = args.error_message
    )

    print( f"Run log written to: {log_path}" )


if __name__ == '__main__':
    main()
