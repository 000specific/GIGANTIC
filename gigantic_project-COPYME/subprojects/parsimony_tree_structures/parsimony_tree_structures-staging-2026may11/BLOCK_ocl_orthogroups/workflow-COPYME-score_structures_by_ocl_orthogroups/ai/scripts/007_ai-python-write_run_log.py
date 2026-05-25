#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 11 | Purpose: Write timestamped JSON run log for transparency
# Human: Eric Edsinger

"""
Script 007 -- Write run log.

Records a timestamped JSON snapshot of the run for transparency and
reproducibility. Captures:
  - configuration values (selected fields)
  - script files in ai/scripts/ with size + mtime
  - OUTPUT_pipeline file inventory with size + mtime
  - environment basics (python version, hostname)
"""

import argparse
import datetime
import json
import logging
import os
import platform
import socket
import sys
from pathlib import Path

import yaml


def file_inventory( root ):
    if not root.is_dir():
        return []
    entries = []
    for path in sorted( root.rglob( '*' ) ):
        if path.is_file():
            stat = path.stat()
            entries.append( {
                'path': str( path.relative_to( root ) ),
                'size_bytes': stat.st_size,
                'mtime_iso': datetime.datetime.fromtimestamp( stat.st_mtime ).isoformat( timespec = 'seconds' ),
            } )
    return entries


def main():
    parser = argparse.ArgumentParser( description = 'Write run log' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--workflow_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    workflow_dir = Path( args.workflow_dir ).resolve()

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )

    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_dir / '7_ai-log-write_run_log.log' ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'run_log' )

    logger.info( 'Starting script 007: write_run_log' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )

    scripts_dir = workflow_dir / 'ai' / 'scripts'
    output_dir = workflow_dir / config.get( 'output', {} ).get( 'base_dir', 'OUTPUT_pipeline' )

    run_log_data = {
        'run_metadata': {
            'timestamp_iso': datetime.datetime.now().isoformat( timespec = 'seconds' ),
            'hostname': socket.gethostname(),
            'python_version': platform.python_version(),
            'platform': platform.platform(),
            'workflow_dir': str( workflow_dir ),
            'config_path': str( config_path ),
        },
        'configuration': {
            'run_label': config.get( 'run_label' ),
            'species_set_name': config.get( 'species_set_name' ),
            'orthogroup_tool': config.get( 'orthogroup_tool' ),
            'execution_mode': config.get( 'execution_mode' ),
            'parallelism_mode': config.get( 'parallelism_mode' ),
            'bootstrap': config.get( 'bootstrap' ),
            'inputs': config.get( 'inputs' ),
        },
        'pipeline_scripts': file_inventory( scripts_dir ),
        'pipeline_outputs': file_inventory( output_dir ),
    }

    timestamp = datetime.datetime.now().strftime( '%Y%m%d_%H%M%S' )
    output_log = log_dir / f'{timestamp}-run_log.json'
    with open( output_log, 'w' ) as output:
        json.dump( run_log_data, output, indent = 2 )
    logger.info( f'Wrote run log: {output_log}' )


if __name__ == '__main__':
    main()
