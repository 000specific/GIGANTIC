#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Validate DIAMOND database integrity
# Human: Eric Edsinger

"""
Validate DIAMOND Database

Runs 'diamond dbinfo' on the built database and parses the output to verify
the database was built correctly. Writes a validation report with database
path, file size, sequence count, and timestamp.

Usage:
    python3 003_ai-python-validate_database.py --database-path PATH --output-dir DIR

Arguments:
    --database-path    Path to the .dmnd DIAMOND database file
    --output-dir       Directory to write validation_report.txt
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def parse_arguments():
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description = "Validate DIAMOND database integrity"
    )
    parser.add_argument(
        "--database-path",
        required = True,
        help = "Path to the .dmnd DIAMOND database file"
    )
    parser.add_argument(
        "--output-dir",
        required = True,
        help = "Directory to write validation_report.txt"
    )

    return parser.parse_args()


def main():
    """Main validation logic."""

    arguments = parse_arguments()

    input_database_path = Path( arguments.database_path )
    output_directory = Path( arguments.output_dir )

    print( "========================================================================" )
    print( "Validating DIAMOND database" )
    print( "========================================================================" )
    print( "" )
    print( f"Database: {input_database_path}" )
    print( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    print( "" )

    # ========================================================================
    # Validate database file exists
    # ========================================================================

    if not input_database_path.exists():
        print( f"CRITICAL ERROR: Database file not found: {input_database_path}" )
        print( "The DIAMOND makedb step must complete before validation." )
        sys.exit( 1 )

    # Get file size
    file_size_bytes = input_database_path.stat().st_size

    if file_size_bytes == 0:
        print( f"CRITICAL ERROR: Database file is empty (0 bytes): {input_database_path}" )
        print( "The DIAMOND database build likely failed." )
        sys.exit( 1 )

    # Convert to human-readable size
    file_size_gigabytes = file_size_bytes / ( 1024 ** 3 )
    file_size_human = f"{file_size_gigabytes:.2f} GB"

    # ========================================================================
    # Run diamond dbinfo
    # ========================================================================

    print( "Running: diamond dbinfo..." )

    try:
        result = subprocess.run(
            [ "diamond", "dbinfo", "-d", str( input_database_path ) ],
            capture_output = True,
            text = True,
            timeout = 300
        )
    except FileNotFoundError:
        print( "CRITICAL ERROR: 'diamond' command not found in PATH" )
        print( "Ensure the conda environment with DIAMOND is activated." )
        sys.exit( 1 )
    except subprocess.TimeoutExpired:
        print( "CRITICAL ERROR: 'diamond dbinfo' timed out after 300 seconds" )
        sys.exit( 1 )

    dbinfo_output = result.stdout + result.stderr
    print( dbinfo_output )

    # ========================================================================
    # Parse sequence count from dbinfo output
    # ========================================================================

    sequence_count = 0

    for line in dbinfo_output.split( "\n" ):
        line = line.strip()
        # DIAMOND dbinfo typically outputs lines like:
        # "Database sequences: 123456789"
        # or "Sequences: 123456789"
        if "sequences" in line.lower() or "letters" in line.lower():
            parts = line.split()
            for part in parts:
                # Find the numeric value
                cleaned_part = part.replace( ",", "" )
                if cleaned_part.isdigit() and int( cleaned_part ) > sequence_count:
                    sequence_count = int( cleaned_part )

    if sequence_count == 0:
        print( "CRITICAL ERROR: Could not determine sequence count from diamond dbinfo" )
        print( "Database may be corrupted or diamond version may have changed output format." )
        print( f"Full dbinfo output:\n{dbinfo_output}" )
        sys.exit( 1 )

    print( f"Sequence count: {sequence_count:,}" )
    print( "" )

    # ========================================================================
    # Write validation report
    # ========================================================================

    output_directory.mkdir( parents = True, exist_ok = True )
    output_report_path = output_directory / "validation_report.txt"

    timestamp = datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )

    output = "DIAMOND Database Validation Report" + "\n"
    output = output + "==================================" + "\n"
    output = output + "" + "\n"
    output = output + f"Database Path: {input_database_path}" + "\n"
    output = output + f"File Size: {file_size_human} ({file_size_bytes:,} bytes)" + "\n"
    output = output + f"Sequence Count: {sequence_count:,}" + "\n"
    output = output + f"Validation Status: PASSED" + "\n"
    output = output + f"Timestamp: {timestamp}" + "\n"
    output = output + "" + "\n"
    output = output + "DIAMOND dbinfo Output:" + "\n"
    output = output + "----------------------" + "\n"
    output = output + dbinfo_output + "\n"

    with open( output_report_path, "w" ) as output_file:
        output_file.write( output )

    print( f"Validation report written to: {output_report_path}" )
    print( "" )
    print( "========================================================================" )
    print( "Validation PASSED" )
    print( f"  Sequences: {sequence_count:,}" )
    print( f"  Size: {file_size_human}" )
    print( "========================================================================" )


if __name__ == "__main__":
    main()
