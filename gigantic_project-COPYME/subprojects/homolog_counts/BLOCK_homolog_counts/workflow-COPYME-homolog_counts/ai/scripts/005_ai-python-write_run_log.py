#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 20 | Purpose: Write homolog_counts workflow run log
# Human: Eric Edsinger

"""
GIGANTIC homolog_counts - Script 005: Write workflow run log

Writes TWO copies of the run log:

  1. <output-dir>/5_ai-run_log.md
     Published to OUTPUT_pipeline/5-output/ by NextFlow (canonical pipeline output).

  2. <script_dir>/../logs/run_<timestamp>-<subproject>_<status>.log
     Archival copy under workflow-COPYME-homolog_counts/ai/logs/ — captures
     each invocation for transparency and reproducibility.

Both files have identical content. Filename in ai/logs/ matches the orthohmm
007 convention so timestamps can be sorted chronologically across runs.

Usage (invoked by main.nf):
    python3 005_ai-python-write_run_log.py \\
        --workflow-name homolog_counts \\
        --subproject-name homolog_counts \\
        --project-name "<from START_HERE-user_config.yaml>" \\
        --status success \\
        --output-dir 5-output
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


def build_log_content(
    workflow_name,
    subproject_name,
    project_name,
    status,
    timestamp_human,
    error_message,
):
    log_lines = [
        '=' * 80,
        f'GIGANTIC Workflow Run Log - {workflow_name}',
        '=' * 80,
        '',
        '## Run Information',
        '',
        f'Timestamp:    {timestamp_human}',
        f'Project Name: {project_name}',
        f'Subproject:   {subproject_name}',
        f'Workflow:     {workflow_name}',
        f'Status:       {status.upper()}',
        '',
        '## Species Set',
        '',
        'species70 (the canonical GIGANTIC species set as of May 2026).',
        '',
        '## Pipeline Outputs',
        '',
        'Per-source wide count tables (Feature_ID | Total_Count | Total_Species_Count | 70 species cols):',
        '  OUTPUT_pipeline/1-output/1_ai-species70_alphabetical_phylonames.tsv',
        '  OUTPUT_pipeline/2-output/2_ai-counts-orthogroups_orthohmm.tsv',
        '  OUTPUT_pipeline/3-output/3_ai-counts-trees_gene_groups.tsv',
        '  OUTPUT_pipeline/4-output/4_ai-counts-trees_gene_families.tsv',
        '',
        'Per-script logs (validation, header counts, phyloname substitutions):',
        '  OUTPUT_pipeline/1-output/1_ai-log-validate_species70_manifest.log',
        '  OUTPUT_pipeline/2-output/2_ai-log-count-orthogroups_orthohmm.log',
        '  OUTPUT_pipeline/3-output/3_ai-log-count-trees_gene_groups.log',
        '  OUTPUT_pipeline/4-output/4_ai-log-count-trees_gene_families.log',
        '',
        '## Downstream Symlinks',
        '',
        'Created by RUN-workflow.sh AFTER this pipeline completes, with stable',
        'filenames for downstream subprojects to consume:',
        '  ../../output_to_input/BLOCK_homolog_counts/species70_alphabetical_phylonames.tsv',
        '  ../../output_to_input/BLOCK_homolog_counts/counts-orthogroups_orthohmm.tsv',
        '  ../../output_to_input/BLOCK_homolog_counts/counts-trees_gene_groups.tsv',
        '  ../../output_to_input/BLOCK_homolog_counts/counts-trees_gene_families.tsv',
        '',
    ]

    if error_message:
        log_lines.extend( [
            '## Error',
            '',
            f'Error Message: {error_message}',
            '',
        ] )

    log_lines.extend( [
        '=' * 80,
    ] )

    return '\n'.join( log_lines ) + '\n'


def main():
    parser = argparse.ArgumentParser(
        description = 'Write homolog_counts workflow run log to OUTPUT_pipeline and ai/logs/'
    )
    parser.add_argument(
        '--workflow-name',
        required = True,
        help = 'Name of the workflow (e.g., homolog_counts)'
    )
    parser.add_argument(
        '--subproject-name',
        required = True,
        help = 'Name of the subproject (e.g., homolog_counts)'
    )
    parser.add_argument(
        '--project-name',
        required = True,
        help = 'Project name from START_HERE-user_config.yaml'
    )
    parser.add_argument(
        '--status',
        choices = [ 'success', 'failure' ],
        required = True,
        help = 'Workflow completion status'
    )
    parser.add_argument(
        '--output-dir',
        required = True,
        help = 'Directory for the OUTPUT_pipeline copy (5-output)'
    )
    parser.add_argument(
        '--error-message',
        default = None,
        help = 'Error message if status is failure (optional)'
    )

    args = parser.parse_args()

    timestamp = datetime.now()
    timestamp_str = timestamp.strftime( '%Y%m%d_%H%M%S' )
    timestamp_human = timestamp.strftime( '%Y-%m-%d %H:%M:%S' )

    output = build_log_content(
        workflow_name = args.workflow_name,
        subproject_name = args.subproject_name,
        project_name = args.project_name,
        status = args.status,
        timestamp_human = timestamp_human,
        error_message = args.error_message,
    )

    # ========================================================================
    # Write OUTPUT_pipeline copy (NextFlow publishes this from work/ task dir)
    # ========================================================================

    output_pipeline_dir = Path( args.output_dir )
    output_pipeline_dir.mkdir( parents = True, exist_ok = True )
    output_run_log_path = output_pipeline_dir / '5_ai-run_log.md'

    with open( output_run_log_path, 'w' ) as output_run_log:
        output_run_log.write( output )

    # ========================================================================
    # Write ai/logs/ archival copy
    # ========================================================================
    # This script lives at workflow-COPYME-homolog_counts/ai/scripts/
    # Logs go to                     workflow-COPYME-homolog_counts/ai/logs/

    script_dir = Path( __file__ ).resolve().parent
    output_workflow_logs_dir = script_dir.parent / 'logs'
    output_workflow_logs_dir.mkdir( parents = True, exist_ok = True )
    output_archival_log_path = output_workflow_logs_dir / f'run_{timestamp_str}-{args.subproject_name}_{args.status}.log'

    with open( output_archival_log_path, 'w' ) as output_archival_log:
        output_archival_log.write( output )

    print( 'Run log written:' )
    print( f'  Pipeline output: {output_run_log_path}' )
    print( f'  Workflow logs:   {output_archival_log_path}' )


if __name__ == '__main__':
    main()
