#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 (1M context) | 2026 April 17 | Purpose: Restore full-length RGS sequences in the final AGS after domain-restricted homolog discovery
# Human: Eric Edsinger

"""
RESTORE FULL-LENGTH RGS SEQUENCES IN FINAL AGS

================================================================================
SCRIPT PURPOSE (For Non-Programmers):
================================================================================
When building gene family trees, it is often beneficial to use SHORT
domain-specific sequences (e.g., pore regions of ion channels) for the
BLAST-based homolog discovery phase. Short, domain-focused seeds reduce
false positives — for example, using full-length TRP channel sequences
pulls in thousands of unrelated ankyrin-repeat-containing proteins,
while using pore-region-only sequences finds true TRP homologs cleanly.

However, for the FINAL phylogenetic tree, full-length sequences are
more informative — they provide more alignment columns, better branch
support, and more biologically meaningful relationships.

THIS SCRIPT solves this by swapping the domain-restricted RGS sequences
in the final AGS back to their full-length versions.

HOW IT WORKS:
The user provides TWO RGS files in INPUT_user/:

  1. Full-length RGS:  rgs_category-species-family_name.aa
  2. Domain RGS:       rgs_category-species-family_name_subsequence.aa

The domain file has IDENTICAL headers to the full-length file, except
each header has '_subsequence' appended. The domain file is what STEP_1
uses for BLAST homolog discovery. This script matches each domain RGS
header in the AGS back to its full-length counterpart by stripping
the '_subsequence' suffix.

Example:
  Full-length header:  >rgs_channel-human-TRPV1-uniprot-Q8NER1
  Domain header:       >rgs_channel-human-TRPV1-uniprot-Q8NER1_subsequence

The script:
  1. Loads the full-length RGS file
  2. Reads the AGS from Script 016
  3. For each RGS entry (header starts with 'rgs_'), strips '_subsequence'
     from the header and looks up the full-length sequence
  4. Replaces the domain sequence with the full-length version
  5. Writes the restored AGS to 18-output/
  6. Copies the restored AGS to 16-output/ so STEP_2 picks it up

USER REQUIREMENTS:
  - Both files MUST be in INPUT_user/
  - Headers MUST be identical except for the '_subsequence' suffix
  - The domain filename MUST end with '_subsequence.aa'
  - Set restore_full_length_rgs: true in START_HERE-user_config.yaml

================================================================================
USAGE:
    python3 018_ai-python-restore_full_length_rgs_sequences.py \\
        --ags-fasta OUTPUT_pipeline/16-output/16_ai-ags-*.aa \\
        --full-length-rgs INPUT_user/rgs_category-species-family_name.aa \\
        --output-dir OUTPUT_pipeline/18-output
================================================================================
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging( log_file_path: Path ) -> logging.Logger:
    """Configure logging to both file and console."""
    logger = logging.getLogger( 'restore_full_length_rgs' )
    logger.setLevel( logging.DEBUG )

    file_handler = logging.FileHandler( log_file_path, mode = 'w' )
    file_handler.setLevel( logging.DEBUG )
    file_handler.setFormatter( logging.Formatter( '%(asctime)s | %(levelname)-8s | %(message)s', datefmt = '%Y-%m-%d %H:%M:%S' ) )
    logger.addHandler( file_handler )

    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setLevel( logging.INFO )
    console_handler.setFormatter( logging.Formatter( '%(levelname)-8s | %(message)s' ) )
    logger.addHandler( console_handler )

    return logger


# ============================================================================
# MAIN LOGIC
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description = 'Restore full-length RGS sequences in AGS by matching _subsequence headers to full-length counterparts.',
    )
    parser.add_argument( '--ags-fasta', type = str, required = True,
        help = 'Path to the AGS FASTA from Script 016 (16-output/16_ai-ags-*.aa)' )
    parser.add_argument( '--full-length-rgs', type = str, required = True,
        help = 'Path to the full-length RGS FASTA (INPUT_user/rgs_*-family_name.aa, WITHOUT _subsequence)' )
    parser.add_argument( '--output-dir', type = str, required = True,
        help = 'Output directory (18-output/)' )

    arguments = parser.parse_args()

    ags_path = Path( arguments.ags_fasta ).resolve()
    full_length_rgs_path = Path( arguments.full_length_rgs ).resolve()
    output_directory = Path( arguments.output_dir )
    output_directory.mkdir( parents = True, exist_ok = True )

    ags_stem = Path( arguments.ags_fasta ).stem
    output_ags_path = output_directory / f"{ags_stem}-full_length_rgs.aa"
    log_path = output_directory / '18_ai-log-restore_full_length_rgs.log'

    logger = setup_logging( log_path )
    logger.info( "=" * 70 )
    logger.info( "GIGANTIC Full-Length RGS Sequence Restoration" )
    logger.info( "=" * 70 )
    logger.info( f"Start time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"AGS input:        {ags_path}" )
    logger.info( f"Full-length RGS:  {full_length_rgs_path}" )
    logger.info( f"Output:           {output_ags_path}" )
    logger.info( "" )

    # ========================================================================
    # VALIDATE INPUTS
    # ========================================================================

    if not ags_path.exists():
        logger.error( f"CRITICAL ERROR: AGS file not found: {ags_path}" )
        sys.exit( 1 )

    if not full_length_rgs_path.exists():
        logger.error( f"CRITICAL ERROR: Full-length RGS file not found: {full_length_rgs_path}" )
        sys.exit( 1 )

    # ========================================================================
    # LOAD FULL-LENGTH RGS INTO LOOKUP
    # ========================================================================
    # Build dictionary: header (without '>') -> sequence
    # These are the full-length versions we will swap in.

    logger.info( "Loading full-length RGS sequences..." )

    full_length_headers___sequences = {}
    current_header = None
    current_sequence_lines = []

    # >rgs_channel-human-TRPV1-uniprot-Q8NER1
    # MEQRARLGQPAGGSEGPAG...
    with open( full_length_rgs_path, 'r', encoding = 'utf-8' ) as input_rgs:
        for line in input_rgs:
            line = line.rstrip( '\n' )
            if line.startswith( '>' ):
                if current_header is not None:
                    full_length_headers___sequences[ current_header ] = ''.join( current_sequence_lines )
                current_header = line[ 1: ]
                current_sequence_lines = []
            elif line:
                current_sequence_lines.append( line )
        if current_header is not None:
            full_length_headers___sequences[ current_header ] = ''.join( current_sequence_lines )

    logger.info( f"  Loaded {len( full_length_headers___sequences )} full-length sequences" )
    logger.info( "" )

    # ========================================================================
    # PROCESS AGS: REPLACE DOMAIN RGS WITH FULL-LENGTH
    # ========================================================================
    # For each sequence in the AGS:
    #   - If header starts with 'rgs_' and ends with '_subsequence':
    #     strip '_subsequence', look up full-length, replace sequence
    #   - If header starts with 'rgs_' but no '_subsequence': pass through
    #     (RGS was already full-length, no restoration needed)
    #   - If header does not start with 'rgs_': pass through (CGS)

    logger.info( "Processing AGS..." )

    rgs_subsequence_total = 0
    rgs_restored = 0
    rgs_unmatched = 0
    rgs_already_full_length = 0
    cgs_total = 0

    output_lines = []
    current_header = None
    current_sequence_lines = []

    def process_entry( header, sequence ):
        nonlocal rgs_subsequence_total, rgs_restored, rgs_unmatched
        nonlocal rgs_already_full_length, cgs_total

        if not header.startswith( 'rgs-' ):
            # CGS sequence — pass through unchanged
            output_lines.append( '>' + header )
            output_lines.append( sequence )
            cgs_total += 1
            return

        if header.endswith( '_subsequence' ):
            # Domain-restricted RGS — restore to full-length
            rgs_subsequence_total += 1

            # Strip '_subsequence' to get the matching full-length header
            full_length_header = header[ : -len( '_subsequence' ) ]

            if full_length_header in full_length_headers___sequences:
                full_length_sequence = full_length_headers___sequences[ full_length_header ]
                # Strip _subsequence from header and use full-length sequence
                output_lines.append( '>' + full_length_header )
                output_lines.append( full_length_sequence )
                rgs_restored += 1
                logger.debug(
                    f"  RESTORED: {header[ :60 ]} "
                    f"({len( sequence )}aa -> {len( full_length_sequence )}aa)"
                )
            else:
                # No match — this RGS was a search-only seed (e.g., mouse TRPC2
                # included for BLAST but not meant for the final tree).
                # REMOVE it from the AGS rather than keeping the subsequence.
                rgs_unmatched += 1
                logger.warning(
                    f"  REMOVED (search-only seed): {header[ :80 ]}"
                )
                logger.warning(
                    f"  No full-length counterpart for: {full_length_header[ :80 ]}"
                )
        else:
            # RGS without '_subsequence' — already full-length, pass through
            output_lines.append( '>' + header )
            output_lines.append( sequence )
            rgs_already_full_length += 1

    with open( ags_path, 'r', encoding = 'utf-8' ) as input_ags:
        for line in input_ags:
            line = line.rstrip( '\n' )
            if line.startswith( '>' ):
                if current_header is not None:
                    process_entry( current_header, ''.join( current_sequence_lines ) )
                current_header = line[ 1: ]
                current_sequence_lines = []
            elif line:
                current_sequence_lines.append( line )
        if current_header is not None:
            process_entry( current_header, ''.join( current_sequence_lines ) )

    # ========================================================================
    # WRITE OUTPUT
    # ========================================================================

    logger.info( "" )
    logger.info( f"Writing restored AGS to: {output_ags_path}" )
    output = '\n'.join( output_lines ) + '\n'
    with open( output_ags_path, 'w', encoding = 'utf-8' ) as output_ags:
        output_ags.write( output )

    # Also copy to 16-output/ so STEP_2 picks it up without config changes
    ags_16_output_path = ags_path
    logger.info( f"Updating 16-output AGS in place: {ags_16_output_path}" )
    shutil.copy2( output_ags_path, ags_16_output_path )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Total AGS sequences:          {rgs_subsequence_total + rgs_already_full_length + cgs_total}" )
    logger.info( f"RGS with _subsequence suffix:      {rgs_subsequence_total}" )
    logger.info( f"  Restored to full-length:    {rgs_restored}" )
    logger.info( f"  Removed (search-only seeds): {rgs_unmatched}" )
    logger.info( f"RGS already full-length:      {rgs_already_full_length}" )
    logger.info( f"CGS sequences (unchanged):    {cgs_total}" )
    logger.info( f"End time: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 70 )

    if rgs_subsequence_total == 0:
        print( "\nNo _subsequence RGS sequences found in AGS. Nothing to restore." )
        return 0

    print( f"\nDone! Restored {rgs_restored}/{rgs_subsequence_total} RGS sequences to full-length." )
    if rgs_unmatched > 0:
        print( f"Removed {rgs_unmatched} search-only seeds (no full-length counterpart)." )
    print( f"Output: {output_ags_path}" )
    print( f"16-output AGS updated in place." )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
