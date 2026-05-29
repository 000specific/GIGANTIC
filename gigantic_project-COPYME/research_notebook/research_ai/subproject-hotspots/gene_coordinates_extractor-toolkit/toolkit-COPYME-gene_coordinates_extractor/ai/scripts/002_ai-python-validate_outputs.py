#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 29 | Purpose: Validate the per-species gene-coordinates TSVs emitted by script 001
# Human: Eric Edsinger
"""
Validate the per-species gene-coordinates TSVs produced by
`001_ai-python-extract_gene_coordinates.py`.

Checks (per species TSV):
  - Header row is present and matches the canonical 5-column shape.
  - Every data row has 5 columns.
  - Gene_Start and Gene_End parse as integers and Gene_Start <= Gene_End.
  - Strand is in { '+', '-' }.
  - Source_Gene_ID is non-empty.
  - Row count > 0.

Also reports global counts:
  - Number of TSVs validated.
  - Number of TSVs that failed any check.
  - Mean / min / max rows per species.

Exit 0 on full pass, 1 on any per-row failure or empty TSV.
"""

import argparse
import logging
import statistics
import sys
from pathlib import Path


EXPECTED_HEADER_KEYS = [
    "Source_Gene_ID",
    "Seqid",
    "Gene_Start",
    "Gene_End",
    "Strand",
]


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


def header_first_words( header_cells ):
    """
    The canonical header has descriptive parentheticals after each name
    (e.g. 'Source_Gene_ID (source gene identifier matching g_ field...)').
    Return just the first space-separated token of each cell.
    """

    return [ cell.split()[ 0 ] if cell.strip() else "" for cell in header_cells ]


def validate_tsv( path, logger ):
    """
    Validate one TSV. Return (ok: bool, n_rows: int).
    """

    with open( path ) as f:
        lines = [ line.rstrip( "\n" ) for line in f ]

    if not lines:
        logger.error( f"  {path.name}: file is empty" )
        return False, 0

    header_cells = lines[ 0 ].split( "\t" )
    if header_first_words( header_cells ) != EXPECTED_HEADER_KEYS:
        logger.error(
            f"  {path.name}: header mismatch; got "
            f"{header_first_words(header_cells)!r}, expected "
            f"{EXPECTED_HEADER_KEYS!r}"
        )
        return False, 0

    ok = True
    n_rows = 0
    for line_no, line in enumerate( lines[ 1 : ], start = 2 ):
        if not line.strip():
            continue
        cells = line.split( "\t" )
        if len( cells ) != 5:
            logger.error(
                f"  {path.name} line {line_no}: expected 5 columns, got "
                f"{len(cells)}"
            )
            ok = False
            continue

        source_id, seqid, start_s, end_s, strand = cells

        if not source_id.strip():
            logger.error(
                f"  {path.name} line {line_no}: empty Source_Gene_ID"
            )
            ok = False
            continue

        try:
            start = int( start_s )
            end = int( end_s )
        except ValueError:
            logger.error(
                f"  {path.name} line {line_no}: non-integer "
                f"Gene_Start/Gene_End ({start_s!r}, {end_s!r})"
            )
            ok = False
            continue

        if start > end:
            logger.error(
                f"  {path.name} line {line_no}: Gene_Start ({start}) > "
                f"Gene_End ({end})"
            )
            ok = False
            continue

        if strand not in ( "+", "-" ):
            logger.error(
                f"  {path.name} line {line_no}: strand must be '+' or '-' "
                f"(got {strand!r})"
            )
            ok = False
            continue

        n_rows += 1

    if n_rows == 0:
        logger.error( f"  {path.name}: zero data rows" )
        return False, 0

    return ok, n_rows


def main():
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument( "--input-dir",  required = True )
    parser.add_argument( "--output-dir", required = True )
    parser.add_argument( "--log-file",   required = True )
    args = parser.parse_args()

    input_dir = Path( args.input_dir ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    log_path = Path( args.log_file ).resolve()

    output_dir.mkdir( parents = True, exist_ok = True )
    log_path.parent.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( log_path )
    logger.info( f"validate input-dir: {input_dir}" )

    tsvs = sorted( input_dir.glob( "*-gene_coordinates.tsv" ) )
    if not tsvs:
        logger.error( f"No '*-gene_coordinates.tsv' files in {input_dir}" )
        sys.exit( 1 )

    summary_path = output_dir / "2_ai-validation_summary.tsv"
    summary_rows = []
    failures = []

    for tsv in tsvs:
        ok, n_rows = validate_tsv( tsv, logger )
        summary_rows.append( ( tsv.name, "PASS" if ok else "FAIL", n_rows ) )
        if not ok:
            failures.append( tsv.name )

    with open( summary_path, "w" ) as f:
        f.write( "filename\tstatus\trow_count\n" )
        for name, status, n in summary_rows:
            f.write( f"{name}\t{status}\t{n}\n" )

    counts = [ n for _, _, n in summary_rows if n > 0 ]
    logger.info( "" )
    logger.info( f"Validated: {len(summary_rows)} TSVs" )
    if counts:
        logger.info(
            f"Row counts: min={min(counts)} max={max(counts)} "
            f"median={statistics.median(counts):.0f}"
        )
    logger.info( f"Failures:  {len(failures)}" )
    logger.info( f"Summary:   {summary_path}" )

    if failures:
        sys.exit( 1 )


if __name__ == "__main__":
    main()
