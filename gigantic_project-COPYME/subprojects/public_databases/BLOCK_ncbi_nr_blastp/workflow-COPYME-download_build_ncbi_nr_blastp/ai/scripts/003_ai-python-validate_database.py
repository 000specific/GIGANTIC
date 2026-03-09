#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Validate BLAST protein database using blastdbcmd
# Human: Eric Edsinger

"""
003_ai-python-validate_database.py

Validates a BLAST protein database by running blastdbcmd -info and parsing
the output to confirm the database exists and contains sequences.

Usage:
    python3 003_ai-python-validate_database.py \
        --database-path DATABASE_PATH \
        --output-file OUTPUT_FILE

Arguments:
    --database-path    Path to the BLAST database (without file extensions)
    --output-file      Path for the validation report output
"""

import argparse
import subprocess
import sys
from datetime import datetime


def main():
    # ========================================================================
    # Parse command-line arguments
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = "Validate BLAST protein database using blastdbcmd"
    )
    parser.add_argument(
        "--database-path",
        required = True,
        help = "Path to the BLAST database (without file extensions)"
    )
    parser.add_argument(
        "--output-file",
        required = True,
        help = "Path for the validation report output"
    )
    arguments = parser.parse_args()

    input_database_path = arguments.database_path
    output_validation_file = arguments.output_file

    # ========================================================================
    # Run blastdbcmd -info
    # ========================================================================

    print( "========================================================================" )
    print( "Validating BLAST Protein Database" )
    print( "========================================================================" )
    print( f"Database path: {input_database_path}" )
    print( f"Started: {datetime.now()}" )
    print( "" )

    try:
        result = subprocess.run(
            [ "blastdbcmd", "-db", input_database_path, "-info" ],
            capture_output = True,
            text = True,
            timeout = 300
        )
    except FileNotFoundError:
        print( "CRITICAL ERROR: blastdbcmd command not found!" )
        print( "Ensure BLAST+ is installed and available in PATH." )
        sys.exit( 1 )
    except subprocess.TimeoutExpired:
        print( "CRITICAL ERROR: blastdbcmd -info timed out after 300 seconds." )
        sys.exit( 1 )

    blastdbcmd_stdout = result.stdout
    blastdbcmd_stderr = result.stderr
    blastdbcmd_return_code = result.returncode

    print( "blastdbcmd -info output:" )
    print( blastdbcmd_stdout )

    if blastdbcmd_stderr:
        print( "blastdbcmd stderr:" )
        print( blastdbcmd_stderr )

    # ========================================================================
    # Parse sequence count from blastdbcmd output
    # ========================================================================

    sequence_count = 0
    total_letters = 0

    for line in blastdbcmd_stdout.split( "\n" ):
        line = line.strip()

        # blastdbcmd -info output includes lines like:
        #   X,XXX,XXX sequences; X,XXX,XXX,XXX total letters
        if "sequences" in line and "total" in line:
            parts = line.split( "sequences" )
            sequence_count_string = parts[ 0 ].strip().replace( ",", "" )
            try:
                sequence_count = int( sequence_count_string )
            except ValueError:
                pass

            if "total letters" in line or "total residues" in line:
                parts_letters = line.split( ";" )
                if len( parts_letters ) > 1:
                    letters_string = parts_letters[ 1 ].strip().split()[ 0 ].replace( ",", "" )
                    try:
                        total_letters = int( letters_string )
                    except ValueError:
                        pass

    # ========================================================================
    # Validate results
    # ========================================================================

    validation_passed = True
    validation_messages = []

    if blastdbcmd_return_code != 0:
        validation_passed = False
        validation_messages.append( f"FAIL: blastdbcmd exited with code {blastdbcmd_return_code}" )

    if sequence_count == 0:
        validation_passed = False
        validation_messages.append( "FAIL: Database contains 0 sequences" )
    else:
        validation_messages.append( f"PASS: Database contains {sequence_count:,} sequences" )

    if total_letters > 0:
        validation_messages.append( f"PASS: Database contains {total_letters:,} total residues" )

    # ========================================================================
    # Write validation report
    # ========================================================================

    with open( output_validation_file, "w" ) as output_report:
        output = "========================================================================\n"
        output_report.write( output )
        output = "NCBI nr BLAST Protein Database Validation Report\n"
        output_report.write( output )
        output = "========================================================================\n"
        output_report.write( output )
        output = f"Timestamp: {datetime.now()}\n"
        output_report.write( output )
        output = f"Database path: {input_database_path}\n"
        output_report.write( output )
        output = f"blastdbcmd return code: {blastdbcmd_return_code}\n"
        output_report.write( output )
        output = "\n"
        output_report.write( output )
        output = "--- blastdbcmd -info output ---\n"
        output_report.write( output )
        output = blastdbcmd_stdout + "\n"
        output_report.write( output )
        output = "--- Validation Results ---\n"
        output_report.write( output )

        for message in validation_messages:
            output = message + "\n"
            output_report.write( output )

        output = "\n"
        output_report.write( output )

        if validation_passed:
            output = "OVERALL: PASSED\n"
            output_report.write( output )
        else:
            output = "OVERALL: FAILED\n"
            output_report.write( output )

        output = "========================================================================\n"
        output_report.write( output )

    print( "" )
    print( "Validation report written to: " + output_validation_file )

    # ========================================================================
    # Exit with appropriate code
    # ========================================================================

    if not validation_passed:
        print( "" )
        print( "CRITICAL ERROR: Database validation FAILED!" )
        for message in validation_messages:
            if message.startswith( "FAIL" ):
                print( f"  {message}" )
        sys.exit( 1 )

    print( "" )
    print( "Database validation PASSED." )
    print( f"  Sequences: {sequence_count:,}" )
    if total_letters > 0:
        print( f"  Total residues: {total_letters:,}" )


if __name__ == "__main__":
    main()
