#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 27 | Purpose: Extract OrthoFinder's DIAMOND/BLAST commands via -op flag and write a pair manifest for the parallel fan-out
# Human: Eric Edsinger

"""
003_ai-python-extract_orthofinder_search_commands.py

WHY THIS SCRIPT EXISTS
-----------------------
The whole point of BLOCK_orthofinder_array is to parallelize OrthoFinder's
all-vs-all DIAMOND/BLAST step across SLURM burst array tasks. To do that we
need a list of the (taxa_a, taxa_b) pairs OrthoFinder would internally compute
PLUS the prepared workdir (renamed proteomes + DIAMOND databases) that
OrthoFinder built via makeblastdb.

OrthoFinder's `-op` flag does exactly this:
  > "prepare the files in the format required by OrthoFinder and print the
  >  set of BLAST commands that need to be run. This is useful if you want
  >  to manage the BLAST searches yourself."

Internally `-op`:
  1. Renames proteomes to Species{N}.fa
  2. Runs makeblastdb / diamond makedb to build per-species databases
  3. Prints every pairwise search command to stdout
  4. Exits before running any searches

We capture the printed commands, parse them into pair tuples, and emit a
manifest TSV that drives the NextFlow fan-out channel. The OrthoFinder
workdir (with the prepared databases) is preserved in the output for the
fan-out tasks to use.

This script's output IS the consistency guarantee: every DIAMOND invocation
the fan-out runs uses commands derived from OrthoFinder itself.

INPUTS
------
    --proteomes-dir   Directory of OrthoFinder-input proteomes (from script 002).
                      OrthoFinder reads files from here and creates its workdir.
    --search-method   "diamond" (default) or "blast" — passed to OrthoFinder -S.
    --output-dir      Where to write the workdir, manifest, captured stdout, and log.

OUTPUTS
-------
    {output-dir}/orthofinder_workdir/                   OrthoFinder-prepared
                                                        workdir (Species{N}.fa,
                                                        DIAMOND DBs, etc.)
    {output-dir}/3_ai-search_pair_manifest.tsv          One row per search pair.
                                                        Columns: taxa_a, taxa_b,
                                                        output_filename, search_command.
    {output-dir}/3_ai-orthofinder_op_stdout.txt         Raw OrthoFinder -op stdout
                                                        (audit trail).
    {output-dir}/3_ai-log-extract_orthofinder_search_commands.log

USAGE
-----
    python3 003_ai-python-extract_orthofinder_search_commands.py \\
        --proteomes-dir 3-output/orthofinder_input_proteomes \\
        --search-method diamond \\
        --output-dir 3-output

EXIT CODES
----------
    0  Manifest written successfully.
    1  OrthoFinder -op failed, or zero commands parsed.
"""

import argparse
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser( description = 'Extract OrthoFinder search commands via -op' )
    parser.add_argument(
        '--proteomes-dir',
        type = str,
        required = True,
        help = 'Directory of OrthoFinder-input proteomes (from script 002)'
    )
    parser.add_argument(
        '--search-method',
        type = str,
        default = 'diamond',
        choices = [ 'diamond', 'blast' ],
        help = 'OrthoFinder -S value (default: diamond)'
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
    log_file = output_directory / '3_ai-log-extract_orthofinder_search_commands.log'

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
# RUN ORTHOFINDER -op
# ============================================================================

def run_orthofinder_op( proteomes_directory, search_method, output_directory, logger ):
    """
    Invoke `orthofinder -op` against the input proteomes.

    OrthoFinder creates a Results_<date>/WorkingDirectory/ inside its output
    location. We point OrthoFinder at a scratch dir inside our output_dir,
    then locate and re-stage the WorkingDirectory at a stable path.

    `orthofinder -op` exits 0 even though it didn't run searches — that's
    the intended behavior of the flag.
    """

    scratch_dir = output_directory / 'orthofinder_op_scratch'
    if scratch_dir.exists():
        shutil.rmtree( scratch_dir )
    scratch_dir.mkdir( parents = True )

    cmd = [
        'orthofinder',
        '-f', str( proteomes_directory ),
        '-o', str( scratch_dir / 'orthofinder_results' ),
        '-S', search_method,
        '-op',
        '-t', '1',  # cpu count is irrelevant for -op (no searches run); set
                    # explicitly so OrthoFinder doesn't auto-detect on a node
                    # that may have a misleading view of available cores
    ]

    logger.info( f'Running: {" ".join( cmd )}' )

    result = subprocess.run(
        cmd,
        capture_output = True,
        text = True,
        check = False
    )

    # Save raw stdout for audit
    stdout_file = output_directory / '3_ai-orthofinder_op_stdout.txt'
    with open( stdout_file, 'w' ) as f:
        f.write( result.stdout )
    logger.info( f'Wrote raw stdout to {stdout_file}' )

    if result.returncode != 0:
        logger.error( 'CRITICAL ERROR: orthofinder -op exited with non-zero code' )
        logger.error( f'Return code: {result.returncode}' )
        logger.error( f'Stderr:\n{result.stderr}' )
        sys.exit( 1 )

    # Locate the WorkingDirectory inside the OrthoFinder Results_<date>
    results_dirs = list( ( scratch_dir / 'orthofinder_results' ).glob( 'Results_*' ) )
    if len( results_dirs ) == 0:
        logger.error( 'CRITICAL ERROR: OrthoFinder did not produce a Results_<date> directory' )
        sys.exit( 1 )
    if len( results_dirs ) > 1:
        logger.error( f'CRITICAL ERROR: multiple Results_ dirs found: {results_dirs}' )
        sys.exit( 1 )

    workdir_source = results_dirs[ 0 ] / 'WorkingDirectory'
    if not workdir_source.is_dir():
        logger.error( f'CRITICAL ERROR: WorkingDirectory not found inside {results_dirs[ 0 ]}' )
        sys.exit( 1 )

    # Move WorkingDirectory to a stable path inside output_directory
    workdir_destination = output_directory / 'orthofinder_workdir'
    if workdir_destination.exists():
        shutil.rmtree( workdir_destination )
    shutil.copytree( workdir_source, workdir_destination )
    logger.info( f'Staged OrthoFinder workdir at {workdir_destination}' )

    # Clean up scratch
    shutil.rmtree( scratch_dir )

    return result.stdout, workdir_destination


# ============================================================================
# PARSE SEARCH COMMANDS
# ============================================================================

def parse_search_commands( orthofinder_stdout, workdir_destination, logger ):
    """
    OrthoFinder prints DIAMOND commands roughly like:

        diamond blastp -d {workdir}/diamondDBSpecies{B} -q {workdir}/Species{A}.fa \
            -o {workdir}/Blast{A}_{B}.txt -e 0.001 --more-sensitive -p 1 -f 6 --quiet

    For BLAST mode, the structure is similar but with `blastp` instead of
    `diamond blastp` and slightly different flags.

    We parse each command to extract:
      - taxa_a:           query species index
      - taxa_b:           database species index
      - output_filename:  Blast{A}_{B}.txt (the basename of the -o argument)
      - search_command:   the full command line as printed by OrthoFinder,
                          but with workdir paths rewritten to point at our
                          stable workdir_destination

    The original workdir path (in the captured stdout) is the OrthoFinder
    scratch path which we tore down. We rewrite to point at the persistent
    workdir under output_directory so the fan-out tasks can find their inputs.
    """

    pairs = []

    # Pattern matches Blast{A}_{B}.txt where A and B are non-negative integers
    blast_filename_pattern = re.compile( r'Blast(\d+)_(\d+)\.txt' )

    # The original workdir path that OrthoFinder embedded in its commands
    # ends with /Results_<date>/WorkingDirectory. We need to find that exact
    # prefix in the printed commands and replace with our stable path.
    workdir_original_prefix = None

    for line in orthofinder_stdout.splitlines():
        line = line.strip()
        # OrthoFinder prints both diamond and blastp commands depending on -S.
        # Lines starting with the search-tool name are the ones we want.
        if not ( line.startswith( 'diamond ' ) or line.startswith( 'blastp ' ) ):
            continue

        # Detect the original workdir prefix from the first command's -o arg.
        # We use the directory portion of the -o filename.
        if workdir_original_prefix is None:
            o_match = re.search( r'-o\s+(\S+/Blast\d+_\d+\.txt)', line )
            if o_match:
                full_output_path = o_match.group( 1 )
                workdir_original_prefix = str( Path( full_output_path ).parent )
                logger.info( f'Detected OrthoFinder workdir prefix: {workdir_original_prefix}' )

        # Rewrite all workdir-prefixed paths to our stable path so DIAMOND
        # can find -d (database) and -q (query) inputs in the published workdir.
        if workdir_original_prefix:
            rewritten_command = line.replace( workdir_original_prefix, str( workdir_destination ) )
        else:
            rewritten_command = line

        # Extract Blast{A}_{B}.txt to identify the pair
        blast_match = blast_filename_pattern.search( line )
        if blast_match is None:
            continue
        taxa_a = blast_match.group( 1 )
        taxa_b = blast_match.group( 2 )
        # OrthoFinder's -op emits DIAMOND commands with `--compress 1`, which
        # makes DIAMOND append .gz to the -o argument. So even though the
        # printed command says `-o BlastA_B.txt`, the file DIAMOND actually
        # creates is `BlastA_B.txt.gz`. NextFlow's output declaration matches
        # the real filename, not the printed one.
        output_filename = f'Blast{taxa_a}_{taxa_b}.txt.gz'

        # Rewrite -o to use just the basename (Blast{A}_{B}.txt) instead of
        # the absolute workdir path. Each NextFlow task runs from its own
        # work dir; we want DIAMOND to write the output THERE so NextFlow's
        # `output: path "${output_filename}"` declaration matches. Inputs
        # (-d, -q) keep their absolute paths so DIAMOND still finds them
        # in the published workdir.
        rewritten_command = re.sub(
            r'-o\s+\S+/(Blast\d+_\d+\.txt)',
            r'-o \1',
            rewritten_command
        )

        pairs.append( ( taxa_a, taxa_b, output_filename, rewritten_command ) )

    logger.info( f'Parsed {len( pairs )} search commands from OrthoFinder stdout' )
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

    manifest_path = output_directory / '3_ai-search_pair_manifest.tsv'

    # Simple, NextFlow-compatible headers
    header = 'taxa_a' + '\t' + 'taxa_b' + '\t' + 'output_filename' + '\t' + 'search_command' + '\n'

    with open( manifest_path, 'w' ) as f:
        f.write( header )
        for taxa_a, taxa_b, output_filename, search_command in pairs:
            output = taxa_a + '\t' + taxa_b + '\t' + output_filename + '\t' + search_command + '\n'
            f.write( output )

    logger.info( f'Wrote pair manifest with {len( pairs )} rows to {manifest_path}' )
    logger.info( '  Column descriptions:' )
    logger.info( '    taxa_a:           OrthoFinder species index for query proteome' )
    logger.info( '    taxa_b:           OrthoFinder species index for database proteome' )
    logger.info( '    output_filename:  canonical OrthoFinder search output filename Blast{A}_{B}.txt' )
    logger.info( '    search_command:   full DIAMOND or BLAST command line as extracted from OrthoFinder -op,' )
    logger.info( '                      with workdir paths rewritten to the stable workdir_destination' )


# ============================================================================
# MAIN
# ============================================================================

def main():
    args = parse_arguments()

    proteomes_directory = Path( args.proteomes_dir ).resolve()
    output_directory = Path( args.output_dir ).resolve()

    logger = setup_logging( output_directory )

    logger.info( '=' * 70 )
    logger.info( 'BLOCK_orthofinder_array | Script 003: extract_orthofinder_search_commands' )
    logger.info( '=' * 70 )
    logger.info( f'proteomes_dir: {proteomes_directory}' )
    logger.info( f'search_method: {args.search_method}' )
    logger.info( f'output_dir: {output_directory}' )

    # Sanity check input
    if not proteomes_directory.is_dir():
        logger.error( f'CRITICAL ERROR: proteomes directory does not exist: {proteomes_directory}' )
        sys.exit( 1 )

    # GIGANTIC convention is .aa proteome files. OrthoFinder's default
    # extensions are .fa, .fas, .fasta, .faa, .pep — .aa is NOT recognized.
    # Rename .aa → .fa in the staged dir so OrthoFinder finds them.
    # (Staged files are NextFlow-managed copies/symlinks; renaming has no
    # effect on the canonical genomesDB source files.)
    aa_files = list( proteomes_directory.glob( '*.aa' ) )
    if aa_files:
        logger.info( f'Renaming {len( aa_files )} .aa → .fa for OrthoFinder compatibility' )
        for aa_file in aa_files:
            aa_file.rename( aa_file.with_suffix( '.fa' ) )

    fa_files = list( proteomes_directory.glob( '*.fa' ) ) + list( proteomes_directory.glob( '*.fasta' ) ) + list( proteomes_directory.glob( '*.faa' ) )
    if len( fa_files ) == 0:
        logger.error( f'CRITICAL ERROR: no proteome files found in {proteomes_directory}' )
        logger.error( 'Script 002 must produce OrthoFinder-input proteomes (.aa, .fa, .fasta, or .faa).' )
        sys.exit( 1 )

    logger.info( f'Found {len( fa_files )} input proteome files' )

    # Run OrthoFinder -op to get the canonical search commands and workdir
    orthofinder_stdout, workdir_destination = run_orthofinder_op(
        proteomes_directory,
        args.search_method,
        output_directory,
        logger
    )

    # Parse commands into structured pair records
    pairs = parse_search_commands( orthofinder_stdout, workdir_destination, logger )

    if len( pairs ) == 0:
        logger.error( 'CRITICAL ERROR: parsed zero search commands from orthofinder stdout' )
        logger.error( f'Check {output_directory}/3_ai-orthofinder_op_stdout.txt for diagnosis.' )
        sys.exit( 1 )

    # Sanity check pair count: OrthoFinder generates N x N pairs (including self-comparisons).
    expected_pair_count = len( fa_files ) ** 2
    if len( pairs ) != expected_pair_count:
        logger.warning( f'WARNING: pair count mismatch (expected {expected_pair_count} == {len( fa_files )}^2, got {len( pairs )})' )
        logger.warning( 'OrthoFinder version may use a different pair-generation pattern. Verify against orthofinder_op_stdout.txt.' )

    write_pair_manifest( pairs, output_directory, logger )

    logger.info( '=' * 70 )
    logger.info( 'Script 003 complete.' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
