#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Validate the user-supplied JSON secretome filter manifest
# Human: Eric Edsinger

"""
001_ai-python-validate_filter_manifest.py

Validates the JSON manifest produced by INPUT_user/secretome_filter_manifest_builder.html
( or hand-edited ). Writes a normalized copy named <run_label>_validated_manifest.json
to the workflow output dir for downstream processes to consume.

Validation ( hard fail if any rule broken ):
  1. JSON parses.
  2. Top-level keys: `output_name` ( string ), `filters` ( list ).
  3. Each filter has: `feature` ( string ), `combine_clauses` ( all|any|at_least_k ),
                      `clauses` ( non-empty list ).
     - `at_least_k` requires a top-level `k` ( int ).
  4. Each clause has: `tool` ( string, informational ), `column` ( string ),
                      `operator` ( one of the supported set ).
     - For comparison operators ( equals / less_than / etc. ): clause has `value`.
     - For multi-value operators ( in_set / contains_any / contains_all ): clause
       has `values` ( list ).
     - For `between`: clause has `value` ( lower ) AND `value_upper`.

The validated manifest is the same JSON shape, with a top-level `validated: true`
flag, and is re-serialized in canonical form ( 2-space indent ).
"""

import argparse
import json
import logging
import sys
from pathlib import Path


SUPPORTED_OPERATORS_SINGLE_VALUE = {
    "equals", "not_equals",
    "less_than", "less_or_equal", "greater_than", "greater_or_equal",
    "contains", "not_contains",
}
SUPPORTED_OPERATORS_MULTI_VALUE = {
    "in_set", "contains_any", "contains_all",
}
SUPPORTED_OPERATORS_RANGE = {
    "between",
}
SUPPORTED_OPERATORS = ( SUPPORTED_OPERATORS_SINGLE_VALUE
                      | SUPPORTED_OPERATORS_MULTI_VALUE
                      | SUPPORTED_OPERATORS_RANGE )
SUPPORTED_COMBINERS = { "all", "any", "at_least_k" }


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Validate a secretome filter JSON manifest and emit a normalized copy."
    )
    parser.add_argument( "--manifest-path", required = True )
    parser.add_argument( "--run-label", required = True )
    parser.add_argument( "--output-dir", required = True )
    return parser.parse_args()


def fail( logger, *messages ):
    for m in messages:
        logger.error( m )
    sys.exit( 1 )


def validate_clause( clause, logger, feature_name, clause_index ):
    """Raises sys.exit on hard validation failure."""
    where = f"feature '{feature_name}' clause #{clause_index}"
    for required_key in ( "tool", "column", "operator" ):
        if required_key not in clause:
            fail( logger,
                  f"CRITICAL: {where} missing required key: {required_key}",
                  f"  clause: {json.dumps( clause )}" )
    operator = clause[ "operator" ]
    if operator not in SUPPORTED_OPERATORS:
        fail( logger,
              f"CRITICAL: {where} uses unsupported operator: {operator}",
              f"  supported: {sorted( SUPPORTED_OPERATORS )}" )
    if operator in SUPPORTED_OPERATORS_SINGLE_VALUE:
        if "value" not in clause:
            fail( logger, f"CRITICAL: {where} operator '{operator}' requires 'value'" )
    elif operator in SUPPORTED_OPERATORS_MULTI_VALUE:
        if "values" not in clause or not isinstance( clause[ "values" ], list ):
            fail( logger,
                  f"CRITICAL: {where} operator '{operator}' requires 'values' (a list)" )
    elif operator in SUPPORTED_OPERATORS_RANGE:
        if "value" not in clause or "value_upper" not in clause:
            fail( logger,
                  f"CRITICAL: {where} operator 'between' requires 'value' (lower) AND 'value_upper'" )


def validate_filter( f, logger, index ):
    where = f"filter #{index}"
    for required_key in ( "feature", "combine_clauses", "clauses" ):
        if required_key not in f:
            fail( logger,
                  f"CRITICAL: {where} missing required key: {required_key}",
                  f"  filter: {json.dumps( f )}" )
    combiner = f[ "combine_clauses" ]
    if combiner not in SUPPORTED_COMBINERS:
        fail( logger,
              f"CRITICAL: {where} unsupported combine_clauses: {combiner}",
              f"  supported: {sorted( SUPPORTED_COMBINERS )}" )
    if combiner == "at_least_k" and "k" not in f:
        fail( logger, f"CRITICAL: {where} combine_clauses=at_least_k requires top-level 'k' int" )
    clauses = f[ "clauses" ]
    if not isinstance( clauses, list ) or len( clauses ) == 0:
        fail( logger, f"CRITICAL: {where} clauses must be a non-empty list" )
    for ci, c in enumerate( clauses ):
        validate_clause( c, logger, f[ "feature" ], ci )


def main():
    args = parse_args()
    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    log_path = output_dir / f"{args.run_label}_log-validate_filter_manifest.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [ logging.FileHandler( log_path ), logging.StreamHandler( sys.stdout ) ],
    )
    logger = logging.getLogger( __name__ )

    manifest_path = Path( args.manifest_path )
    logger.info( "=" * 70 )
    logger.info( "Script 001: validate_filter_manifest" )
    logger.info( "=" * 70 )
    logger.info( f"Run label:       {args.run_label}" )
    logger.info( f"Manifest path:   {manifest_path}" )

    if not manifest_path.exists():
        fail( logger, f"CRITICAL: manifest file does not exist: {manifest_path}" )

    try:
        with open( manifest_path ) as f:
            manifest = json.load( f )
    except json.JSONDecodeError as e:
        fail( logger, f"CRITICAL: manifest is not valid JSON: {e}" )

    if not isinstance( manifest, dict ):
        fail( logger, "CRITICAL: top-level JSON must be an object/dict" )
    if "filters" not in manifest:
        fail( logger, "CRITICAL: top-level 'filters' key missing" )
    if not isinstance( manifest[ "filters" ], list ):
        fail( logger, "CRITICAL: 'filters' must be a list" )
    manifest.setdefault( "output_name", "" )

    n_filters = len( manifest[ "filters" ] )
    logger.info( f"Number of filters: {n_filters}" )
    if n_filters == 0:
        logger.warning( "Manifest has zero filters — every protein in every species would pass." )

    for i, f in enumerate( manifest[ "filters" ] ):
        validate_filter( f, logger, i )
        clauses_n = len( f[ "clauses" ] )
        logger.info( f"  filter #{i}: feature={f[ 'feature' ]!r}, combine={f[ 'combine_clauses' ]}, clauses={clauses_n}" )

    manifest[ "validated" ] = True
    manifest[ "run_label" ] = args.run_label

    out_path = output_dir / f"{args.run_label}_validated_manifest.json"
    with open( out_path, "w" ) as f:
        json.dump( manifest, f, indent = 2 )

    logger.info( "" )
    logger.info( f"OK. Validated manifest written to: {out_path}" )


if __name__ == "__main__":
    main()
