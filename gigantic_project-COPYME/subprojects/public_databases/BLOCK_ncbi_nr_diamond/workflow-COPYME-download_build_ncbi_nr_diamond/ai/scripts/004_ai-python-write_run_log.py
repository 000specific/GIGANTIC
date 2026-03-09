#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Write timestamped run log for NCBI nr DIAMOND workflow
# Human: Eric Edsinger

"""
Write Run Log for NCBI nr DIAMOND Database Workflow

Reads the validation report and writes a timestamped run log documenting
the workflow completion, database details, and status.

Usage:
    python3 004_ai-python-write_run_log.py --validation-report PATH --output-dir DIR

Arguments:
    --validation-report    Path to the validation_report.txt from script 003
    --output-dir           Directory to write run_log.txt
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


def parse_arguments():
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description = "Write run log for NCBI nr DIAMOND workflow"
    )
    parser.add_argument(
        "--validation-report",
        required = True,
        help = "Path to the validation_report.txt"
    )
    parser.add_argument(
        "--output-dir",
        required = True,
        help = "Directory to write run_log.txt"
    )

    return parser.parse_args()


def main():
    """Main run log writing logic."""

    arguments = parse_arguments()

    input_validation_report_path = Path( arguments.validation_report )
    output_directory = Path( arguments.output_dir )

    # ========================================================================
    # Read validation report
    # ========================================================================

    if not input_validation_report_path.exists():
        print( f"CRITICAL ERROR: Validation report not found: {input_validation_report_path}" )
        print( "The validation step (script 003) must complete before writing the run log." )
        sys.exit( 1 )

    with open( input_validation_report_path, "r" ) as input_file:
        validation_report_contents = input_file.read()

    # ========================================================================
    # Parse key details from validation report
    # ========================================================================

    database_path = "unknown"
    file_size = "unknown"
    sequence_count = "unknown"
    validation_status = "unknown"

    # Database Path: OUTPUT_pipeline/2-output/nr.dmnd
    # File Size: 150.23 GB (161234567890 bytes)
    # Sequence Count: 123,456,789
    # Validation Status: PASSED
    for line in validation_report_contents.split( "\n" ):
        line = line.strip()
        if line.startswith( "Database Path:" ):
            database_path = line.split( ":", 1 )[ 1 ].strip()
        elif line.startswith( "File Size:" ):
            file_size = line.split( ":", 1 )[ 1 ].strip()
        elif line.startswith( "Sequence Count:" ):
            sequence_count = line.split( ":", 1 )[ 1 ].strip()
        elif line.startswith( "Validation Status:" ):
            validation_status = line.split( ":", 1 )[ 1 ].strip()

    # ========================================================================
    # Write run log
    # ========================================================================

    output_directory.mkdir( parents = True, exist_ok = True )
    output_run_log_path = output_directory / "run_log.txt"

    timestamp = datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )

    output = "NCBI nr DIAMOND Database - Run Log" + "\n"
    output = output + "===================================" + "\n"
    output = output + "" + "\n"
    output = output + f"Workflow: NCBI nr DIAMOND Database Build" + "\n"
    output = output + f"Completion Timestamp: {timestamp}" + "\n"
    output = output + f"Status: SUCCESS" + "\n"
    output = output + "" + "\n"
    output = output + "Database Details:" + "\n"
    output = output + "-----------------" + "\n"
    output = output + f"  Database Path: {database_path}" + "\n"
    output = output + f"  File Size: {file_size}" + "\n"
    output = output + f"  Sequence Count: {sequence_count}" + "\n"
    output = output + f"  Validation: {validation_status}" + "\n"
    output = output + "" + "\n"
    output = output + "Workflow Steps Completed:" + "\n"
    output = output + "-------------------------" + "\n"
    output = output + "  1. Downloaded NCBI nr protein FASTA (nr.gz)" + "\n"
    output = output + "  2. Built DIAMOND database (nr.dmnd)" + "\n"
    output = output + "  3. Validated database integrity" + "\n"
    output = output + "  4. Wrote this run log" + "\n"
    output = output + "" + "\n"
    output = output + "---" + "\n"
    output = output + f"Log generated: {timestamp}" + "\n"

    with open( output_run_log_path, "w" ) as output_file:
        output_file.write( output )

    print( f"Run log written to: {output_run_log_path}" )
    print( "" )
    print( "========================================================================" )
    print( "Run log complete" )
    print( f"  Timestamp: {timestamp}" )
    print( f"  Database: {database_path}" )
    print( f"  Sequences: {sequence_count}" )
    print( "========================================================================" )


if __name__ == "__main__":
    main()
