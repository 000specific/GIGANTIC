#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 26 | Purpose: Pool the parallel phmmer fan-out outputs and verify completeness/integrity before handing off to OrthoHMM
# Human: Eric Edsinger

"""
004_ai-python-pool_and_verify_phmmer_outputs.py

WHY THIS SCRIPT EXISTS
-----------------------
After ~4,830 phmmer SLURM burst jobs complete, this script is the gate that
ensures we have a COMPLETE and CORRECT set of phmmer outputs before handing
off to OrthoHMM `--start search_res`. This is the silent-artifact prevention
step.

Without this gate, OrthoHMM `--start search_res` would happily process any
files present in orthohmm_working_res/ — even with a few missing pairs or
truncated outputs — and silently produce incomplete orthogroup assignments.
That is exactly the failure mode CLAUDE.md prohibits ("Zero Tolerance for
Silent Artifacts in Research Results").

VERIFICATION CHECKS
-------------------
    1. Every pair listed in the manifest has a phmmerout.txt present.
    2. Every present phmmerout.txt is well-formed: phmmer writes a
       `# [ok]` sentinel as the last line on successful completion. A
       missing or different last line means phmmer was killed mid-run.
    3. No EXTRA phmmer files beyond the manifest (would indicate a bug).

INPUTS
------
    --phmmer-outputs-dir  Directory containing all phmmerout.txt files
                          collected from the fan-out (NextFlow stages them
                          into this dir as part of the .collect()).
    --pair-manifest       The manifest TSV from script 003 — drives the
                          expected-pair list.
    --output-dir          Where to write the pooled directory and report.

OUTPUTS
-------
    {output-dir}/orthohmm_working_res/        Pooled phmmerout.txt files,
                                              ready for OrthoHMM --start search_res.
    {output-dir}/4_ai-pool_verification_report.tsv   Per-pair status (PRESENT,
                                              MISSING, MALFORMED).
    {output-dir}/4_ai-log-pool_and_verify_phmmer.log

USAGE
-----
    python3 004_ai-python-pool_and_verify_phmmer_outputs.py \\
        --phmmer-outputs-dir phmmer_outputs \\
        --pair-manifest 3_ai-phmmer_pair_manifest.tsv \\
        --output-dir 4-output

EXIT CODES
----------
    0  All pairs present, all well-formed.
    1  Verification failed (missing or malformed pairs). Pipeline halts.
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
    parser = argparse.ArgumentParser( description = 'Pool and verify phmmer fan-out outputs' )
    parser.add_argument(
        '--phmmer-outputs-dir',
        type = str,
        required = True,
        help = 'Directory of phmmerout.txt files staged by NextFlow .collect()'
    )
    parser.add_argument(
        '--pair-manifest',
        type = str,
        required = True,
        help = 'Pair manifest TSV from script 003'
    )
    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/4-output',
        help = 'Output directory (default: OUTPUT_pipeline/4-output)'
    )
    return parser.parse_args()


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging( output_directory ):
    output_directory.mkdir( parents = True, exist_ok = True )
    log_file = output_directory / '4_ai-log-pool_and_verify_phmmer.log'

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
    Read the pair manifest from script 003. Returns a list of expected
    output filenames (one per phmmer pair).

    Manifest header from script 003:
      taxa_a (short-header .pep filename for first proteome in the pair)\\t
      taxa_b (...)\\t
      output_filename (canonical phmmer output filename A_2_B.phmmerout.txt)
    """

    expected_filenames = []

    # taxa_a (short-header .pep filename for first proteome in the pair)	taxa_b (...)	output_filename (canonical phmmer output filename A_2_B.phmmerout.txt)
    # Abeoforma_whisleri.pep	Acropora_muricata.pep	Abeoforma_whisleri.pep_2_Acropora_muricata.pep.phmmerout.txt
    with open( manifest_path, 'r' ) as input_manifest:
        next( input_manifest )  # skip header
        for line in input_manifest:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            output_filename = parts[ 2 ]
            expected_filenames.append( output_filename )

    logger.info( f'Manifest expects {len( expected_filenames )} phmmer outputs' )
    return expected_filenames


# ============================================================================
# VERIFY PHMMER OUTPUT INTEGRITY
# ============================================================================

def is_phmmer_output_complete( phmmer_output_path ):
    """
    A complete phmmer output ends with '# [ok]' as its last non-empty line.
    Truncated or killed phmmer runs lack this sentinel.
    """

    if not phmmer_output_path.is_file():
        return False

    try:
        with open( phmmer_output_path, 'r' ) as f:
            lines = f.readlines()
        if not lines:
            return False
        return lines[ -1 ].strip() == '# [ok]'
    except Exception:
        return False


# ============================================================================
# POOL AND VERIFY
# ============================================================================

def pool_and_verify( phmmer_outputs_directory, expected_filenames, output_directory, logger ):
    """
    Verify every expected file is present and well-formed; copy each into
    the pooled orthohmm_working_res/ directory; write a per-pair report.

    Fails (exits 1) if any pair is missing or malformed — no silent
    propagation of incomplete state.
    """

    pooled_directory = output_directory / 'orthohmm_working_res'
    pooled_directory.mkdir( parents = True, exist_ok = True )

    report_path = output_directory / '4_ai-pool_verification_report.tsv'

    statuses = []  # list of (filename, status) tuples
    missing_count = 0
    malformed_count = 0

    for expected_filename in expected_filenames:
        source_path = phmmer_outputs_directory / expected_filename

        if not source_path.is_file():
            statuses.append( ( expected_filename, 'MISSING' ) )
            missing_count += 1
            continue

        if not is_phmmer_output_complete( source_path ):
            statuses.append( ( expected_filename, 'MALFORMED' ) )
            malformed_count += 1
            continue

        # Present and well-formed → copy into pooled dir
        destination_path = pooled_directory / expected_filename
        shutil.copy( source_path, destination_path )
        statuses.append( ( expected_filename, 'PRESENT' ) )

    # Write the per-pair report TSV
    header = (
        'phmmer_output_filename (canonical A_2_B.phmmerout.txt name)' + '\t'
        + 'verification_status (PRESENT, MISSING, or MALFORMED)'
        + '\n'
    )
    with open( report_path, 'w' ) as f:
        f.write( header )
        for filename, status in statuses:
            output = filename + '\t' + status + '\n'
            f.write( output )

    logger.info( f'Wrote per-pair verification report to {report_path}' )

    # Detect extras (files present in fan-out dir that are NOT in manifest)
    expected_set = set( expected_filenames )
    actual_files = { p.name for p in phmmer_outputs_directory.glob( '*.phmmerout.txt' ) }
    extras = actual_files - expected_set
    if extras:
        logger.warning( f'WARNING: {len( extras )} phmmer outputs found that are NOT in the manifest' )
        for extra_file in sorted( extras )[ :10 ]:
            logger.warning( f'  extra: {extra_file}' )

    return missing_count, malformed_count


# ============================================================================
# MAIN
# ============================================================================

def main():
    args = parse_arguments()

    phmmer_outputs_directory = Path( args.phmmer_outputs_dir ).resolve()
    pair_manifest_path = Path( args.pair_manifest ).resolve()
    output_directory = Path( args.output_dir ).resolve()

    logger = setup_logging( output_directory )

    logger.info( '=' * 70 )
    logger.info( 'BLOCK_orthohmm_GIGANTIC | Script 004: pool_and_verify_phmmer_outputs' )
    logger.info( '=' * 70 )
    logger.info( f'phmmer_outputs_dir: {phmmer_outputs_directory}' )
    logger.info( f'pair_manifest: {pair_manifest_path}' )
    logger.info( f'output_dir: {output_directory}' )

    # Sanity-check inputs
    if not phmmer_outputs_directory.is_dir():
        logger.error( f'CRITICAL ERROR: phmmer outputs directory does not exist: {phmmer_outputs_directory}' )
        sys.exit( 1 )
    if not pair_manifest_path.is_file():
        logger.error( f'CRITICAL ERROR: pair manifest not found: {pair_manifest_path}' )
        sys.exit( 1 )

    # Read expected pair list from script 003's manifest
    expected_filenames = read_pair_manifest( pair_manifest_path, logger )

    if len( expected_filenames ) == 0:
        logger.error( 'CRITICAL ERROR: pair manifest has zero rows' )
        sys.exit( 1 )

    # Pool + verify
    missing_count, malformed_count = pool_and_verify(
        phmmer_outputs_directory,
        expected_filenames,
        output_directory,
        logger
    )

    # Fail fast if any pair is missing or malformed.
    # Per CLAUDE.md: completing with invalid data is worse than failing.
    if missing_count > 0 or malformed_count > 0:
        logger.error( '=' * 70 )
        logger.error( 'CRITICAL ERROR: phmmer pool verification FAILED' )
        logger.error( f'  missing pairs:    {missing_count}' )
        logger.error( f'  malformed pairs:  {malformed_count}' )
        logger.error( f'  total expected:   {len( expected_filenames )}' )
        logger.error( '' )
        logger.error( 'Cannot proceed to OrthoHMM finalize: would produce incomplete orthogroups.' )
        logger.error( f'See {output_directory}/4_ai-pool_verification_report.tsv for per-pair status.' )
        logger.error( 'Investigate failed phmmer_pair tasks (NextFlow trace + slurm logs) and rerun.' )
        logger.error( '=' * 70 )
        sys.exit( 1 )

    logger.info( f'All {len( expected_filenames )} phmmer pairs PRESENT and well-formed.' )
    logger.info( '=' * 70 )
    logger.info( 'Script 004 complete.' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
