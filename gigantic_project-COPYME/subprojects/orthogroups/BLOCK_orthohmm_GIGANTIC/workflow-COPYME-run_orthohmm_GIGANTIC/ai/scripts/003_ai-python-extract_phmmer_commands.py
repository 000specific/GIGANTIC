#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 26 | Purpose: Extract OrthoHMM's phmmer commands via --stop prepare and write a pair manifest for the parallel fan-out
# Human: Eric Edsinger

"""
003_ai-python-extract_phmmer_commands.py

WHY THIS SCRIPT EXISTS
-----------------------
The whole point of BLOCK_orthohmm_GIGANTIC is to parallelize OrthoHMM's
all-vs-all phmmer step across SLURM burst jobs. To do that we need a list of
the (taxa_a, taxa_b) pairs OrthoHMM would internally compute.

Rather than hand-construct this list (and risk drifting from OrthoHMM's
internal logic across versions), we use OrthoHMM's own `--stop prepare` mode.
That mode generates the canonical phmmer command lines and exits BEFORE
running phmmer. We capture them, parse out the species pairs, and emit a
manifest TSV that drives the NextFlow fan-out channel.

This script's output IS the consistency guarantee: every phmmer invocation
the fan-out runs uses commands derived from OrthoHMM itself.

INPUTS
------
    --proteomes-dir  Directory of short-header proteomes (from script 002).
                     OrthoHMM reads .pep files from here.
    --evalue         OrthoHMM e-value threshold (just for logging; --stop
                     prepare doesn't actually use it for phmmer commands,
                     but we record it for run-log consistency).
    --output-dir     Where to write the manifest, captured stdout, and log.

OUTPUTS
-------
    {output-dir}/3_ai-phmmer_pair_manifest.tsv      One row per phmmer pair.
                                                    Columns: taxa_a, taxa_b,
                                                    output_filename.
    {output-dir}/3_ai-orthohmm_prepare_stdout.txt   Raw OrthoHMM --stop prepare
                                                    stdout (audit trail).
    {output-dir}/3_ai-log-extract_phmmer_commands.log

USAGE
-----
    python3 003_ai-python-extract_phmmer_commands.py \\
        --proteomes-dir 3-output/short_header_proteomes \\
        --evalue 0.0001 \\
        --output-dir 3-output
"""

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser( description = 'Extract OrthoHMM phmmer commands via --stop prepare' )
    parser.add_argument(
        '--proteomes-dir',
        type = str,
        required = True,
        help = 'Directory of short-header proteomes (.pep files from script 002)'
    )
    parser.add_argument(
        '--evalue',
        type = str,
        default = '0.0001',
        help = 'OrthoHMM e-value threshold (recorded in log; default: 0.0001)'
    )
    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/3-output',
        help = 'Output directory (default: OUTPUT_pipeline/3-output)'
    )
    return parser.parse_args()


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging( output_directory ):
    output_directory.mkdir( parents = True, exist_ok = True )
    log_file = output_directory / '3_ai-log-extract_phmmer_commands.log'

    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s - %(levelname)s - %(message)s',
        handlers = [
            logging.FileHandler( log_file ),
            logging.StreamHandler( sys.stdout )
        ]
    )
    return logging.getLogger( __name__ )


# ============================================================================
# RUN ORTHOHMM --stop prepare
# ============================================================================

def run_orthohmm_stop_prepare( proteomes_directory, output_directory, logger ):
    """
    Invoke `orthohmm --stop prepare` against the short-header proteomes.

    OrthoHMM in --stop prepare mode:
      1. Reads all .pep files from the fasta_directory
      2. Generates one phmmer command per (taxa_a, taxa_b) pair
      3. Prints the commands to stdout
      4. sys.exit()s before running phmmer

    The OrthoHMM CLI requires an output_directory even in prepare mode (for
    its own working files). We give it a scratch dir we don't use afterward.
    """

    # OrthoHMM creates orthohmm_working_res/ inside its output dir during
    # prepare. Use a scratch subdir so we don't pollute our publishDir.
    scratch_dir = output_directory / 'orthohmm_scratch_for_prepare'
    scratch_dir.mkdir( parents = True, exist_ok = True )

    cmd = [
        'orthohmm',
        str( proteomes_directory ),
        '--output_directory', str( scratch_dir ),
        '--stop', 'prepare',
        '--cpu', '1',  # cpu count is irrelevant for --stop prepare; we set it
                       # explicitly so OrthoHMM does not try to auto-detect on a
                       # node that may have a misleading view of available cores
    ]

    logger.info( f'Running: {" ".join( cmd )}' )

    result = subprocess.run(
        cmd,
        capture_output = True,
        text = True,
        check = False
    )

    # Write captured stdout to file for audit trail
    stdout_file = output_directory / '3_ai-orthohmm_prepare_stdout.txt'
    output = result.stdout
    with open( stdout_file, 'w' ) as f:
        f.write( output )
    logger.info( f'Wrote raw stdout to {stdout_file}' )

    if result.returncode != 0:
        logger.error( 'CRITICAL ERROR: orthohmm --stop prepare exited with non-zero code' )
        logger.error( f'Return code: {result.returncode}' )
        logger.error( f'Stderr:\n{result.stderr}' )
        sys.exit( 1 )

    return output


# ============================================================================
# PARSE PHMMER COMMANDS
# ============================================================================

def parse_phmmer_commands( orthohmm_stdout, logger ):
    """
    Each command line from OrthoHMM's --stop prepare looks like:

        phmmer --mx BLOSUM62 --noali --notextw --cpu N \
            --tblout {output_dir}/orthohmm_working_res/{A}_2_{B}.phmmerout.txt \
            {fasta_dir}/{A} {fasta_dir}/{B}

    We extract:
      - taxa_a:           basename of the first fasta input (== A.pep)
      - taxa_b:           basename of the second fasta input (== B.pep)
      - output_filename:  {A}_2_{B}.phmmerout.txt (from the --tblout path)

    The exact command line is preserved in 3_ai-orthohmm_prepare_stdout.txt
    for audit; the manifest TSV captures only the per-pair fields the fan-out
    channel needs.
    """

    pairs = []

    for line in orthohmm_stdout.splitlines():
        line = line.strip()
        if not line.startswith( 'phmmer ' ):
            continue

        parts = line.split()

        # The command's last two tokens are the two fasta paths.
        # OrthoHMM constructs them as {fasta_directory}/{combo[0]} and
        # {fasta_directory}/{combo[1]}, so the basenames are the .pep filenames.
        fasta_a_path = parts[ -2 ]
        fasta_b_path = parts[ -1 ]
        taxa_a = Path( fasta_a_path ).name
        taxa_b = Path( fasta_b_path ).name

        # The --tblout argument is the second token after the --tblout flag.
        # We derive output_filename from it for the manifest.
        tblout_index = parts.index( '--tblout' )
        tblout_path = parts[ tblout_index + 1 ]
        output_filename = Path( tblout_path ).name  # e.g., A_2_B.phmmerout.txt

        pairs.append( ( taxa_a, taxa_b, output_filename ) )

    logger.info( f'Parsed {len( pairs )} phmmer commands from OrthoHMM stdout' )
    return pairs


# ============================================================================
# WRITE MANIFEST
# ============================================================================

def write_pair_manifest( pairs, output_directory, logger ):
    """
    Write the pair manifest TSV that drives the fan-out channel.

    NOTE: This is an INTERNAL pipeline file consumed by NextFlow's
    splitCsv(header: true). Headers must be SIMPLE bare identifiers (no
    parentheses, no descriptions) because NextFlow uses the literal header
    string as the dict key. Self-documenting headers (per GIGANTIC convention
    for user-facing output tables) would break NextFlow channel parsing.

    Column descriptions are logged below for human reference.
    """

    manifest_path = output_directory / '3_ai-phmmer_pair_manifest.tsv'

    # Simple, NextFlow-compatible headers
    header = 'taxa_a' + '\t' + 'taxa_b' + '\t' + 'output_filename' + '\n'

    with open( manifest_path, 'w' ) as f:
        f.write( header )
        for taxa_a, taxa_b, output_filename in pairs:
            output = taxa_a + '\t' + taxa_b + '\t' + output_filename + '\n'
            f.write( output )

    logger.info( f'Wrote pair manifest with {len( pairs )} rows to {manifest_path}' )
    logger.info( '  Column descriptions:' )
    logger.info( '    taxa_a:           short-header .pep filename for first proteome in the pair' )
    logger.info( '    taxa_b:           short-header .pep filename for second proteome in the pair' )
    logger.info( '    output_filename:  canonical phmmer output filename A_2_B.phmmerout.txt' )


# ============================================================================
# MAIN
# ============================================================================

def main():
    args = parse_arguments()

    proteomes_directory = Path( args.proteomes_dir ).resolve()
    output_directory = Path( args.output_dir ).resolve()

    logger = setup_logging( output_directory )

    logger.info( '=' * 70 )
    logger.info( 'BLOCK_orthohmm_GIGANTIC | Script 003: extract_phmmer_commands' )
    logger.info( '=' * 70 )
    logger.info( f'proteomes_dir: {proteomes_directory}' )
    logger.info( f'evalue (recorded only): {args.evalue}' )
    logger.info( f'output_dir: {output_directory}' )

    # Sanity check input
    if not proteomes_directory.is_dir():
        logger.error( f'CRITICAL ERROR: proteomes directory does not exist: {proteomes_directory}' )
        sys.exit( 1 )

    pep_files = list( proteomes_directory.glob( '*.pep' ) )
    if len( pep_files ) == 0:
        logger.error( f'CRITICAL ERROR: no .pep files found in {proteomes_directory}' )
        logger.error( 'Script 002 must have produced short-header .pep files.' )
        sys.exit( 1 )

    logger.info( f'Found {len( pep_files )} .pep files' )

    # Run OrthoHMM --stop prepare to get the canonical phmmer commands
    orthohmm_stdout = run_orthohmm_stop_prepare( proteomes_directory, output_directory, logger )

    # Parse commands into structured pair records
    pairs = parse_phmmer_commands( orthohmm_stdout, logger )

    if len( pairs ) == 0:
        logger.error( 'CRITICAL ERROR: parsed zero phmmer commands from orthohmm stdout' )
        logger.error( f'Check {output_directory}/3_ai-orthohmm_prepare_stdout.txt for diagnosis.' )
        sys.exit( 1 )

    # Sanity check pair count: OrthoHMM uses itertools.product(files, repeat=2)
    # so expected count is len(files)^2 (includes self-pairs A vs A).
    expected_pair_count = len( pep_files ) ** 2
    if len( pairs ) != expected_pair_count:
        logger.error( f'CRITICAL ERROR: pair count mismatch' )
        logger.error( f'Expected {expected_pair_count} (== {len( pep_files )}^2), got {len( pairs )}' )
        sys.exit( 1 )

    # Write the manifest
    write_pair_manifest( pairs, output_directory, logger )

    logger.info( '=' * 70 )
    logger.info( 'Script 003 complete.' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
