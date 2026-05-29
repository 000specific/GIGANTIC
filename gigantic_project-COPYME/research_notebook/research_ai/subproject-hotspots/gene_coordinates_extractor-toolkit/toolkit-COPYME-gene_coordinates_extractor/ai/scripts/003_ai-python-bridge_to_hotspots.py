#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 29 | Purpose: Symlink validated gene-coordinates TSVs into the hotspots subproject's expected input location
# Human: Eric Edsinger
"""
Bridge the per-species gene-coordinates TSVs into the hotspots subproject's
expected input location.

The hotspots BLOCK_identify_hotspots workflow expects per-species TSVs at:
    research_notebook/research_user/subproject-hotspots/gene_coordinates/<Genus_species>-gene_coordinates.tsv

This script symlinks each validated TSV from the run's OUTPUT_pipeline/1-output/
into that location. Symlinks are absolute, refreshed on every run (existing
links to stale paths are removed first).

CLI
---
    python3 003_ai-python-bridge_to_hotspots.py \\
        --input-dir <toolkit run 1-output dir> \\
        --target-dir <research_notebook/research_user/subproject-hotspots/gene_coordinates> \\
        --log-file <path>
"""

import argparse
import logging
import os
import sys
from pathlib import Path


def setup_logging( log_path ):
    logger = logging.getLogger( "bridge_to_hotspots" )
    logger.setLevel( logging.INFO )
    fh = logging.FileHandler( log_path, mode = "w" )
    sh = logging.StreamHandler( sys.stdout )
    fmt = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    fh.setFormatter( fmt )
    sh.setFormatter( fmt )
    logger.addHandler( fh )
    logger.addHandler( sh )
    return logger


def main():
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument( "--input-dir",  required = True )
    parser.add_argument( "--target-dir", required = True )
    parser.add_argument( "--log-file",   required = True )
    args = parser.parse_args()

    input_dir = Path( args.input_dir ).resolve()
    target_dir = Path( args.target_dir ).resolve()
    log_path = Path( args.log_file ).resolve()

    target_dir.mkdir( parents = True, exist_ok = True )
    log_path.parent.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( log_path )
    logger.info( f"input-dir:  {input_dir}" )
    logger.info( f"target-dir: {target_dir}" )

    tsvs = sorted( input_dir.glob( "*-gene_coordinates.tsv" ) )
    if not tsvs:
        logger.error( f"No '*-gene_coordinates.tsv' files under {input_dir}" )
        sys.exit( 1 )

    n_made = 0
    n_replaced = 0
    for src in tsvs:
        dest = target_dir / src.name
        if dest.is_symlink() or dest.exists():
            try:
                dest.unlink()
                n_replaced += 1
            except OSError as e:
                logger.error( f"Cannot remove existing {dest}: {e}" )
                sys.exit( 1 )
        os.symlink( str( src ), str( dest ) )
        n_made += 1
        logger.info( f"  -> {dest.name}" )

    logger.info( "" )
    logger.info( f"Created {n_made} symlinks ({n_replaced} replaced existing)" )


if __name__ == "__main__":
    main()
