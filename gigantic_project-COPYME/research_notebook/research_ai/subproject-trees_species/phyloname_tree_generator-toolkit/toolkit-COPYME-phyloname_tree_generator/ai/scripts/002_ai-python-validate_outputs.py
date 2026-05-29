#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 29 | Purpose: Validate the binary Newick produced by script 001
# Human: Eric Edsinger
"""
Validate the emitted species-tree Newick.

Checks:
  - Newick parses to a binary tree
  - N leaves -> exactly N-1 internal nodes
  - No duplicate leaf names
  - No internal nodes labeled with the `ancestral_clade_NNN` pattern
    (reserved by trees_species/BLOCK_gigantic_species_tree)

Exit 0 on full pass; 1 on any failure.
"""

import argparse
import logging
import re
import sys
from pathlib import Path


def setup_logging( log_path ):
    logger = logging.getLogger( "validate_outputs" )
    logger.setLevel( logging.INFO )
    fh = logging.FileHandler( log_path, mode = "w" )
    sh = logging.StreamHandler( sys.stdout )
    fmt = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    fh.setFormatter( fmt )
    sh.setFormatter( fmt )
    logger.addHandler( fh )
    logger.addHandler( sh )
    return logger


def parse_newick( s ):
    """Return a nested list-of-lists tree from a Newick string."""

    s = s.strip()
    if s.endswith( ";" ):
        s = s[ :-1 ]
    pos = [ 0 ]

    def parse_node():
        if s[ pos[ 0 ] ] == "(":
            pos[ 0 ] += 1
            children = []
            children.append( parse_node() )
            while s[ pos[ 0 ] ] == ",":
                pos[ 0 ] += 1
                children.append( parse_node() )
            assert s[ pos[ 0 ] ] == ")", f"expected ')' at pos {pos[0]}"
            pos[ 0 ] += 1
            # Optional label / branch length
            start = pos[ 0 ]
            while pos[ 0 ] < len( s ) and s[ pos[ 0 ] ] not in ",()":
                pos[ 0 ] += 1
            label = s[ start : pos[ 0 ] ].strip()
            return ( label, children )
        else:
            start = pos[ 0 ]
            while pos[ 0 ] < len( s ) and s[ pos[ 0 ] ] not in ",()":
                pos[ 0 ] += 1
            name = s[ start : pos[ 0 ] ].strip()
            return ( name, None )  # leaf

    return parse_node()


def collect_leaves( node ):
    label, children = node
    if children is None:
        return [ label ]
    out = []
    for c in children:
        out.extend( collect_leaves( c ) )
    return out


def count_internals( node ):
    label, children = node
    if children is None:
        return 0
    n = 1
    for c in children:
        n += count_internals( c )
    return n


def all_internal_labels( node ):
    label, children = node
    if children is None:
        return []
    out = [ label ]
    for c in children:
        out.extend( all_internal_labels( c ) )
    return out


def is_binary( node ):
    label, children = node
    if children is None:
        return True
    if len( children ) != 2:
        return False
    return all( is_binary( c ) for c in children )


ANCESTRAL_RE = re.compile( r"^ancestral_clade_\d{3}$" )


def main():
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument( "--newick",  required = True )
    parser.add_argument( "--log-file", required = True )
    args = parser.parse_args()

    log_path = Path( args.log_file ).resolve()
    log_path.parent.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( log_path )

    newick_path = Path( args.newick ).resolve()
    text = newick_path.read_text().strip()
    tree = parse_newick( text )

    ok = True

    leaves = collect_leaves( tree )
    if len( leaves ) != len( set( leaves ) ):
        seen = {}
        for n in leaves:
            seen[ n ] = seen.get( n, 0 ) + 1
        dups = [ k for k, v in seen.items() if v > 1 ]
        logger.error( f"Duplicate leaves: {dups}" )
        ok = False
    logger.info( f"Leaves: {len(leaves)} unique" )

    internals = count_internals( tree )
    if internals != len( leaves ) - 1:
        logger.error(
            f"Internals != N-1: got {internals}, expected {len(leaves)-1}"
        )
        ok = False
    else:
        logger.info( f"Internals: {internals} (= N-1 ✓)" )

    if not is_binary( tree ):
        logger.error( "Tree is not strictly binary" )
        ok = False
    else:
        logger.info( "Binary: ✓" )

    bad_labels = [ l for l in all_internal_labels( tree ) if ANCESTRAL_RE.match( l ) ]
    if bad_labels:
        logger.error(
            f"Internal labels collide with reserved ancestral_clade_NNN pattern "
            f"(used by trees_species/BLOCK_gigantic_species_tree): {bad_labels}"
        )
        ok = False
    else:
        logger.info( "No reserved internal labels: ✓" )

    if not ok:
        sys.exit( 1 )

    logger.info( "ALL VALIDATION CHECKS PASSED" )


if __name__ == "__main__":
    main()
