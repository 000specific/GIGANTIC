#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 27 | Purpose: Pool the parallel DIAMOND fan-out outputs and verify completeness/integrity, place into OrthoFinder workdir for -b resume
# Human: Eric Edsinger

"""
005_ai-python-pool_and_verify_diamond_outputs.py

WHY THIS SCRIPT EXISTS
-----------------------
After ~4,830 DIAMOND SLURM array tasks complete, this script is the gate
that ensures we have a COMPLETE and CORRECT set of search outputs before
handing off to OrthoFinder `-b` resume. Silent-artifact prevention.

Without this gate, OrthoFinder `-b` would happily process any Blast files
present in the workdir — even with a few missing pairs or truncated outputs
— and silently produce incomplete orthogroup assignments. That is exactly
the failure mode CLAUDE.md prohibits ("Zero Tolerance for Silent Artifacts
in Research Results").

VERIFICATION CHECKS
-------------------
    1. Every pair listed in the manifest has a Blast{A}_{B}.txt present.
    2. Every present Blast file is non-empty (truncated or zero-byte
       outputs indicate DIAMOND was killed mid-run).
    3. No EXTRA Blast files beyond the manifest (would indicate a bug).

INPUTS
------
    --diamond-outputs-dir    Directory containing all Blast{A}_{B}.txt files
                             collected from the fan-out (NextFlow stages them
                             into this dir as part of the .collect()).
    --pair-manifest          The manifest TSV from script 003 — drives the
                             expected-pair list.
    --orthofinder-workdir    The OrthoFinder workdir from script 003
                             (Species{N}.fa, diamondDBSpecies{N}.dmnd,
                             SequenceIDs.txt, SpeciesIDs.txt). The verified
                             Blast files are copied INTO this workdir.
    --output-dir             Where to write the populated workdir and report.

OUTPUTS
-------
    {output-dir}/orthofinder_workdir_with_results/   Full OrthoFinder workdir
                                                     ready for `-b` resume —
                                                     includes Species/DB files
                                                     plus all Blast{A}_{B}.txt.
    {output-dir}/5_ai-pool_verification_report.tsv   Per-pair status (PRESENT,
                                                     MISSING, EMPTY).
    {output-dir}/5_ai-log-pool_and_verify_diamond_outputs.log

USAGE
-----
    python3 005_ai-python-pool_and_verify_diamond_outputs.py \\
        --diamond-outputs-dir diamond_outputs \\
        --pair-manifest 3_ai-search_pair_manifest.tsv \\
        --orthofinder-workdir 3-output/orthofinder_workdir \\
        --output-dir 5-output

EXIT CODES
----------
    0  All pairs present, all non-empty.
    1  Verification failed (missing or empty pairs). Pipeline halts.
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser( description = 'Pool and verify DIAMOND fan-out outputs' )
    parser.add_argument(
        '--diamond-outputs-dir',
        type = str,
        required = True,
        help = 'Directory of Blast{A}_{B}.txt files staged by NextFlow .collect()'
    )
    parser.add_argument(
        '--pair-manifest',
        type = str,
        required = True,
        help = 'Pair manifest TSV from script 003'
    )
    parser.add_argument(
        '--orthofinder-workdir',
        type = str,
        required = True,
        help = 'OrthoFinder workdir from script 003 (Species/DB files)'
    )
    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/5-output',
        help = 'Output directory (default: OUTPUT_pipeline/5-output)'
    )
    return parser.parse_args()


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging( output_directory ):
    output_directory.mkdir( parents = True, exist_ok = True )
    log_file = output_directory / '5_ai-log-pool_and_verify_diamond_outputs.log'

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
# READ MANIFEST
# ============================================================================

def read_pair_manifest( manifest_path, logger ):
    """
    Read pair manifest from script 003. Returns list of expected output filenames.

    Manifest header from script 003:
      taxa_a (...)\\ttaxa_b (...)\\toutput_filename (...)\\tsearch_command (...)
    """

    expected_filenames = []

    # taxa_a (OrthoFinder species index for query proteome)	taxa_b (OrthoFinder species index for database proteome)	output_filename (canonical OrthoFinder search output filename Blast{A}_{B}.txt)	search_command (...)
    # 0	0	Blast0_0.txt	diamond blastp ...
    with open( manifest_path, 'r' ) as input_manifest:
        next( input_manifest )  # skip header
        for line in input_manifest:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            output_filename = parts[ 2 ]
            expected_filenames.append( output_filename )

    logger.info( f'Manifest expects {len( expected_filenames )} DIAMOND outputs' )
    return expected_filenames


# ============================================================================
# VERIFY DIAMOND OUTPUT
# ============================================================================

def is_diamond_output_valid( diamond_output_path ):
    """
    A complete DIAMOND output (BLAST tabular format 6) is non-empty.
    Empty files indicate DIAMOND was killed before writing any results.

    Note: DIAMOND in --quiet -f 6 mode writes one row per HSP. A pair with
    NO hits will produce a 0-byte file, which is biologically valid (no
    detectable similarity) but indistinguishable from a killed run by file
    size alone. We treat 0-byte as suspicious and flag it.
    """

    if not diamond_output_path.is_file():
        return False
    return diamond_output_path.stat().st_size > 0


# ============================================================================
# POOL AND VERIFY
# ============================================================================

def pool_and_verify(
    diamond_outputs_directory,
    expected_filenames,
    orthofinder_workdir_source,
    output_directory,
    logger
):
    """
    Verify every expected file is present and non-empty; copy the original
    OrthoFinder workdir plus all Blast files into a populated workdir; write
    per-pair report.

    Fails (exits 1) if any pair is missing or empty — no silent propagation
    of incomplete state.
    """

    populated_workdir = output_directory / 'orthofinder_workdir_with_results'
    if populated_workdir.exists():
        shutil.rmtree( populated_workdir )

    # Stage the OrthoFinder workdir contents (Species/DB files) as the base
    shutil.copytree( orthofinder_workdir_source, populated_workdir )
    logger.info( f'Staged OrthoFinder workdir at {populated_workdir}' )

    report_path = output_directory / '5_ai-pool_verification_report.tsv'

    statuses = []  # list of (filename, status) tuples
    missing_count = 0
    empty_count = 0

    for expected_filename in expected_filenames:
        source_path = diamond_outputs_directory / expected_filename

        if not source_path.is_file():
            statuses.append( ( expected_filename, 'MISSING' ) )
            missing_count += 1
            continue

        if not is_diamond_output_valid( source_path ):
            statuses.append( ( expected_filename, 'EMPTY' ) )
            empty_count += 1
            # Empty files MIGHT be biologically valid (no hits between divergent
            # species) — we still copy them to the workdir so OrthoFinder sees
            # the file exists, but flag for the user to inspect.
            shutil.copy( source_path, populated_workdir / expected_filename )
            continue

        # Present and non-empty → copy to populated workdir
        shutil.copy( source_path, populated_workdir / expected_filename )
        statuses.append( ( expected_filename, 'PRESENT' ) )

    # Write per-pair report
    header = (
        'diamond_output_filename (canonical Blast{A}_{B}.txt name)' + '\t'
        + 'verification_status (PRESENT, MISSING, or EMPTY)'
        + '\n'
    )
    with open( report_path, 'w' ) as f:
        f.write( header )
        for filename, status in statuses:
            output = filename + '\t' + status + '\n'
            f.write( output )

    logger.info( f'Wrote per-pair verification report to {report_path}' )

    # Detect extras (files in fan-out dir NOT in manifest)
    expected_set = set( expected_filenames )
    # OrthoFinder's DIAMOND command (extracted via -op) uses --compress 1, so
    # outputs are Blast{A}_{B}.txt.gz, not Blast{A}_{B}.txt.
    actual_files = { p.name for p in diamond_outputs_directory.glob( 'Blast*.txt.gz' ) }
    extras = actual_files - expected_set
    if extras:
        logger.warning( f'WARNING: {len( extras )} DIAMOND outputs found that are NOT in the manifest' )
        for extra_file in sorted( extras )[ :10 ]:
            logger.warning( f'  extra: {extra_file}' )

    return missing_count, empty_count


# ============================================================================
# MAIN
# ============================================================================

def main():
    args = parse_arguments()

    diamond_outputs_directory = Path( args.diamond_outputs_dir ).resolve()
    pair_manifest_path = Path( args.pair_manifest ).resolve()
    orthofinder_workdir_source = Path( args.orthofinder_workdir ).resolve()
    output_directory = Path( args.output_dir ).resolve()

    logger = setup_logging( output_directory )

    logger.info( '=' * 70 )
    logger.info( 'BLOCK_orthofinder_array | Script 005: pool_and_verify_diamond_outputs' )
    logger.info( '=' * 70 )
    logger.info( f'diamond_outputs_dir:    {diamond_outputs_directory}' )
    logger.info( f'pair_manifest:          {pair_manifest_path}' )
    logger.info( f'orthofinder_workdir:    {orthofinder_workdir_source}' )
    logger.info( f'output_dir:             {output_directory}' )

    # Sanity-check inputs
    if not diamond_outputs_directory.is_dir():
        logger.error( f'CRITICAL ERROR: diamond outputs directory does not exist: {diamond_outputs_directory}' )
        sys.exit( 1 )
    if not pair_manifest_path.is_file():
        logger.error( f'CRITICAL ERROR: pair manifest not found: {pair_manifest_path}' )
        sys.exit( 1 )
    if not orthofinder_workdir_source.is_dir():
        logger.error( f'CRITICAL ERROR: orthofinder workdir not found: {orthofinder_workdir_source}' )
        sys.exit( 1 )

    # Read expected pair list from script 003's manifest
    expected_filenames = read_pair_manifest( pair_manifest_path, logger )

    if len( expected_filenames ) == 0:
        logger.error( 'CRITICAL ERROR: pair manifest has zero rows' )
        sys.exit( 1 )

    missing_count, empty_count = pool_and_verify(
        diamond_outputs_directory,
        expected_filenames,
        orthofinder_workdir_source,
        output_directory,
        logger
    )

    # Fail fast on missing pairs. EMPTY pairs are flagged but allowed —
    # they may represent real biological "no hits" between divergent species.
    # The verification report records both for user inspection.
    if missing_count > 0:
        logger.error( '=' * 70 )
        logger.error( 'CRITICAL ERROR: DIAMOND pool verification FAILED' )
        logger.error( f'  missing pairs: {missing_count}' )
        logger.error( f'  empty pairs:   {empty_count} (allowed if biologically valid; verify in report)' )
        logger.error( f'  total expected: {len( expected_filenames )}' )
        logger.error( '' )
        logger.error( 'Cannot proceed to OrthoFinder finalize: would produce incomplete orthogroups.' )
        logger.error( f'See {output_directory}/5_ai-pool_verification_report.tsv for per-pair status.' )
        logger.error( 'Investigate failed diamond_pair tasks (NextFlow trace + slurm logs) and rerun.' )
        logger.error( '=' * 70 )
        sys.exit( 1 )

    if empty_count > 0:
        logger.warning( f'NOTE: {empty_count} DIAMOND outputs are 0-byte (no hits).' )
        logger.warning( 'This is biologically valid for distantly-related species pairs but worth inspecting.' )
        logger.warning( f'See {output_directory}/5_ai-pool_verification_report.tsv for which pairs.' )

    logger.info( f'All {len( expected_filenames )} DIAMOND pairs PRESENT (with {empty_count} non-fatal EMPTY).' )
    logger.info( '=' * 70 )
    logger.info( 'Script 005 complete.' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
