#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Write timestamped run log for NCBI nr BLAST database pipeline
# Human: Eric Edsinger

"""
004_ai-python-write_run_log.py

Reads the validation report from step 003 and writes a timestamped run log
for provenance and reproducibility.

Usage:
    python3 004_ai-python-write_run_log.py \
        --validation-report VALIDATION_REPORT \
        --output-file OUTPUT_FILE

Arguments:
    --validation-report    Path to the validation report from step 003
    --output-file          Path for the run log output
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


def main():
    # ========================================================================
    # Parse command-line arguments
    # ========================================================================

    parser = argparse.ArgumentParser(
        description = "Write timestamped run log for NCBI nr BLAST database pipeline"
    )
    parser.add_argument(
        "--validation-report",
        required = True,
        help = "Path to the validation report from step 003"
    )
    parser.add_argument(
        "--output-file",
        required = True,
        help = "Path for the run log output"
    )
    arguments = parser.parse_args()

    input_validation_report_path = Path( arguments.validation_report )
    output_run_log_path = arguments.output_file

    # ========================================================================
    # Read validation report
    # ========================================================================

    if not input_validation_report_path.exists():
        print( "CRITICAL ERROR: Validation report not found!" )
        print( f"  Expected: {input_validation_report_path}" )
        print( "  The validation step (003) must complete before writing the run log." )
        sys.exit( 1 )

    # validation_report.txt
    # ========================================================================
    # NCBI nr BLAST Protein Database Validation Report
    # ========================================================================
    with open( input_validation_report_path, "r" ) as input_validation_report:
        validation_content = input_validation_report.read()

    # ========================================================================
    # Determine validation status
    # ========================================================================

    if "OVERALL: PASSED" in validation_content:
        validation_status = "PASSED"
    elif "OVERALL: FAILED" in validation_content:
        validation_status = "FAILED"
    else:
        validation_status = "UNKNOWN"

    # ========================================================================
    # Write run log
    # ========================================================================

    timestamp = datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )

    with open( output_run_log_path, "w" ) as output_run_log:
        output = "========================================================================\n"
        output_run_log.write( output )
        output = "NCBI nr BLAST Protein Database Pipeline - Run Log\n"
        output_run_log.write( output )
        output = "========================================================================\n"
        output_run_log.write( output )
        output = "\n"
        output_run_log.write( output )
        output = f"Timestamp: {timestamp}\n"
        output_run_log.write( output )
        output = f"Pipeline: NCBI nr BLAST Protein Database (download + makeblastdb)\n"
        output_run_log.write( output )
        output = f"Validation status: {validation_status}\n"
        output_run_log.write( output )
        output = "\n"
        output_run_log.write( output )
        output = "--- Pipeline Steps ---\n"
        output_run_log.write( output )
        output = "  Step 1: Download NCBI nr FASTA (nr.gz) from NCBI FTP\n"
        output_run_log.write( output )
        output = "  Step 2: Decompress and build BLAST protein database (makeblastdb)\n"
        output_run_log.write( output )
        output = "  Step 3: Validate database (blastdbcmd -info)\n"
        output_run_log.write( output )
        output = "  Step 4: Write run log (this file)\n"
        output_run_log.write( output )
        output = "\n"
        output_run_log.write( output )
        output = "--- Validation Report ---\n"
        output_run_log.write( output )
        output = validation_content + "\n"
        output_run_log.write( output )
        output = "========================================================================\n"
        output_run_log.write( output )
        output = f"Log generated: {timestamp}\n"
        output_run_log.write( output )
        output = "========================================================================\n"
        output_run_log.write( output )

    print( f"Run log written to: {output_run_log_path}" )
    print( f"  Validation status: {validation_status}" )
    print( f"  Timestamp: {timestamp}" )


if __name__ == "__main__":
    main()
