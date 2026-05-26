#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Apply secretome filter manifest to one species' evidence table
# Human: Eric Edsinger

"""
002_ai-python-apply_filters_per_species.py

For ONE species, read the STEP_1 evidence table ( 96-col wide TSV, one row
per protein ) and a validated JSON manifest. Emit a filtered TSV containing
only proteins that pass EVERY filter in the manifest ( top-level AND ).

Within each filter, clauses are combined per `combine_clauses`:
  - all          → every clause must hold
  - any          → at least one clause must hold
  - at_least_k   → at least k clauses must hold

Output preserves all input columns ( downstream augment scripts add more ).

Output: <phyloname>_<run_label>_filtered.tsv

Missing data handling:
  - Cells with literal "None" string are treated as MISSING.
  - Numeric comparisons against missing values FAIL ( do not match ).
  - String 'equals' against the literal string "None" DOES match a missing value.
  - String 'contains' against missing values FAILS.

The full input header is carried through to the output ( so downstream
augment scripts can rely on the same 96-col evidence-table column inventory ).
"""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Apply secretome filter manifest to one species' evidence table."
    )
    parser.add_argument( "--evidence-table", required = True )
    parser.add_argument( "--manifest", required = True )
    parser.add_argument( "--run-label", required = True )
    parser.add_argument( "--phyloname", required = True )
    parser.add_argument( "--output-dir", required = True )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Column-name mapping
# ---------------------------------------------------------------------------
# Evidence-table headers are self-documenting ( "Header_ID (description...)" ).
# Manifest clauses reference the short Header_ID. Build a map: short → full.

def header_short_to_full( header_cells ):
    short_to_full = {}
    for full in header_cells:
        short = full.split( " " )[ 0 ]
        if short in short_to_full and short_to_full[ short ] != full:
            # Header collision shouldn't happen with the STEP_1 schema; log + keep first.
            pass
        short_to_full.setdefault( short, full )
    return short_to_full


# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------

NONE_MARKER = "None"

def try_float( s ):
    if s is None or s == NONE_MARKER or s == "":
        return None
    try:
        return float( s )
    except ValueError:
        return None

def try_int( s ):
    if s is None or s == NONE_MARKER or s == "":
        return None
    try:
        return int( s )
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Clause evaluation
# ---------------------------------------------------------------------------

def eval_clause( cell, clause ):
    op = clause[ "operator" ]
    if op == "equals":
        return cell == str( clause[ "value" ] )
    if op == "not_equals":
        return cell != str( clause[ "value" ] )
    if op == "in_set":
        return cell in [ str( v ) for v in clause[ "values" ] ]
    if op == "contains":
        if cell == NONE_MARKER:
            return False
        return str( clause[ "value" ] ) in cell
    if op == "not_contains":
        if cell == NONE_MARKER:
            return True
        return str( clause[ "value" ] ) not in cell
    if op == "contains_any":
        if cell == NONE_MARKER:
            return False
        return any( str( v ) in cell for v in clause[ "values" ] )
    if op == "contains_all":
        if cell == NONE_MARKER:
            return False
        return all( str( v ) in cell for v in clause[ "values" ] )
    if op in ( "less_than", "less_or_equal", "greater_than", "greater_or_equal" ):
        cell_value = try_float( cell )
        if cell_value is None:
            return False
        threshold = float( clause[ "value" ] )
        if op == "less_than":         return cell_value <  threshold
        if op == "less_or_equal":     return cell_value <= threshold
        if op == "greater_than":      return cell_value >  threshold
        if op == "greater_or_equal":  return cell_value >= threshold
    if op == "between":
        cell_value = try_float( cell )
        if cell_value is None:
            return False
        return float( clause[ "value" ] ) <= cell_value <= float( clause[ "value_upper" ] )
    raise ValueError( f"unknown operator: {op}" )


def eval_filter( row, header_map, filter_definition ):
    combine = filter_definition[ "combine_clauses" ]
    clauses = filter_definition[ "clauses" ]
    holds = []
    for c in clauses:
        col_short = c[ "column" ]
        if col_short not in header_map:
            # Column missing from evidence table — silently treat clause as FAIL.
            holds.append( False )
            continue
        col_full = header_map[ col_short ]
        cell = row.get( col_full, NONE_MARKER )
        holds.append( eval_clause( cell, c ) )
    if combine == "all":
        return all( holds )
    if combine == "any":
        return any( holds )
    if combine == "at_least_k":
        return sum( holds ) >= filter_definition.get( "k", 1 )
    raise ValueError( f"unknown combiner: {combine}" )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    log_path = output_dir / f"{args.phyloname}_{args.run_label}_log-apply_filters.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [ logging.FileHandler( log_path ), logging.StreamHandler( sys.stdout ) ],
    )
    logger = logging.getLogger( __name__ )

    logger.info( "=" * 70 )
    logger.info( "Script 002: apply_filters_per_species" )
    logger.info( "=" * 70 )
    logger.info( f"Run label:       {args.run_label}" )
    logger.info( f"Phyloname:       {args.phyloname}" )
    logger.info( f"Evidence table:  {args.evidence_table}" )
    logger.info( f"Manifest:        {args.manifest}" )

    with open( args.manifest ) as f:
        manifest = json.load( f )
    filters = manifest[ "filters" ]
    logger.info( f"Filters to apply ( top-level AND ): {len( filters )}" )
    for i, fl in enumerate( filters ):
        logger.info( f"  filter #{i}: feature={fl[ 'feature' ]!r}  combine={fl[ 'combine_clauses' ]}  clauses={len( fl[ 'clauses' ] )}" )

    out_path = output_dir / f"{args.phyloname}_{args.run_label}_filtered.tsv"

    n_input = 0
    n_kept = 0
    per_filter_pass = [ 0 ] * len( filters )
    with open( args.evidence_table, newline = "" ) as fin, open( out_path, "w", newline = "" ) as fout:
        reader = csv.DictReader( fin, delimiter = "\t" )
        header_map = header_short_to_full( reader.fieldnames )

        # Pre-check: every column referenced by a clause must exist
        for i, fl in enumerate( filters ):
            for c in fl[ "clauses" ]:
                col_short = c[ "column" ]
                if col_short not in header_map:
                    logger.error( f"CRITICAL: column '{col_short}' referenced by filter #{i} not in evidence table" )
                    sys.exit( 1 )

        writer = csv.DictWriter( fout, fieldnames = reader.fieldnames, delimiter = "\t" )
        writer.writeheader()
        for row in reader:
            n_input += 1
            keeps = []
            for i, fl in enumerate( filters ):
                p = eval_filter( row, header_map, fl )
                keeps.append( p )
                if p:
                    per_filter_pass[ i ] += 1
            if all( keeps ):
                writer.writerow( row )
                n_kept += 1

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Input proteins:  {n_input:,}" )
    logger.info( f"Kept proteins:   {n_kept:,}  ({100 * n_kept / n_input:.2f}% of input)" if n_input else f"Kept proteins:   0" )
    logger.info( "Per-filter pass counts (independent of other filters):" )
    for i, fl in enumerate( filters ):
        n = per_filter_pass[ i ]
        pct = 100 * n / n_input if n_input else 0
        logger.info( f"  #{i}  {fl[ 'feature' ]:<35s} {n:>8,}  ({pct:.2f}%)" )
    logger.info( f"Output:          {out_path}" )


if __name__ == "__main__":
    main()
