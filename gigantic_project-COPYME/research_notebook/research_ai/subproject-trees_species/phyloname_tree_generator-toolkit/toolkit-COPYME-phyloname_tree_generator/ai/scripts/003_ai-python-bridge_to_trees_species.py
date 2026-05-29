#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 29 | Purpose: Symlink the generated Newick into trees_species BLOCK_gigantic_species_tree INPUT_user
# Human: Eric Edsinger
"""
Symlink the validated Newick into the trees_species
`BLOCK_gigantic_species_tree/workflow-COPYME-gigantic_species_tree/INPUT_user/`
path AS `species_tree.newick` (the canonical filename that workflow expects).

Symlink is absolute and refreshed on each run.
"""

import argparse
import logging
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument( "--newick",     required = True )
    parser.add_argument( "--target-dir", required = True )
    parser.add_argument( "--log-file",   required = True )
    args = parser.parse_args()

    newick = Path( args.newick ).resolve()
    target_dir = Path( args.target_dir ).resolve()
    log_path = Path( args.log_file ).resolve()

    target_dir.mkdir( parents = True, exist_ok = True )
    log_path.parent.mkdir( parents = True, exist_ok = True )

    logger = logging.getLogger( "bridge" )
    logger.setLevel( logging.INFO )
    fh = logging.FileHandler( log_path, mode = "w" )
    sh = logging.StreamHandler( sys.stdout )
    fmt = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    fh.setFormatter( fmt )
    sh.setFormatter( fmt )
    logger.addHandler( fh )
    logger.addHandler( sh )

    target = target_dir / "species_tree.newick"
    if target.is_symlink() or target.exists():
        target.unlink()
    os.symlink( str( newick ), str( target ) )
    logger.info( f"Symlink: {target} -> {newick}" )


if __name__ == "__main__":
    main()
