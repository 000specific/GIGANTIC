#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 16:45 | Purpose: Download HGNC complete_set TSV (with uniprot_ids cross-refs); idempotent against subproject canonical location
# Human: Eric Edsinger

"""
Download HGNC's `hgnc_complete_set.txt` from genenames.org.

This file is the authoritative human-gene-symbol catalog and carries the
`uniprot_ids` column needed to map symbols to UniProt accessions
without an API hop. It is required by both STEP_0 workflows in
`gene_groups_hgnc-COPYME`:

  - workflow-COPYME-hgnc_database/   (for downstream RGS sequence sourcing)
  - workflow-COPYME-hgnc_user_list/  (to resolve user-supplied symbols to UniProt
                               accessions before fetching FASTAs)

Idempotency:
    The download is skipped if --canonical-source is provided and points
    to an existing valid copy at the subproject-level output_to_input
    location. In that case the canonical copy is copied into the local
    output directory (preserving the GIGANTIC convention that script
    outputs always land in OUTPUT_pipeline).

Usage:
    python3 000_ai-python-download_hgnc_complete_set.py \
        --output-directory 0-output \
        --log-file 0-output/0_ai-log-download_hgnc_complete_set.log \
        [--canonical-source <path-to-subproject-output_to_input-copy>]

Output:
    <output-directory>/hgnc_complete_set.txt
    <output-directory>/0_ai-download_manifest.tsv
"""

import argparse
import logging
import shutil
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


HGNC_COMPLETE_SET_URL = (
    "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt"
)

EXPECTED_HEADER_COLUMNS = [
    'hgnc_id',
    'symbol',
    'uniprot_ids',
]


def setup_logging( log_file_path ):
    """Configure logging to both file and console."""

    logger = logging.getLogger( 'download_hgnc_complete_set' )
    logger.setLevel( logging.INFO )

    # Clear any handlers from prior invocations (safe for NextFlow process re-runs)
    logger.handlers.clear()

    file_handler = logging.FileHandler( log_file_path )
    file_handler.setLevel( logging.INFO )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


def download_file( url, output_path, logger ):
    """Download a single file from URL to output_path. Returns True on success."""

    try:
        logger.info( f"Downloading: {url}" )
        logger.info( f"  Target: {output_path}" )

        urllib.request.urlretrieve( url, output_path )

        if not output_path.exists():
            logger.error( f"  Download claimed success but file not present: {output_path}" )
            return False

        if output_path.stat().st_size == 0:
            logger.error( f"  Downloaded file is empty: {output_path}" )
            return False

        return True

    except urllib.error.HTTPError as e:
        logger.error( f"  HTTP error {e.code}: {e.reason}" )
        return False
    except urllib.error.URLError as e:
        logger.error( f"  URL error: {e.reason}" )
        return False
    except Exception as e:
        logger.error( f"  Unexpected error: {type( e ).__name__}: {e}" )
        return False


def copy_from_canonical( canonical_path, output_path, logger ):
    """Copy from subproject canonical location to local output. Returns True on success."""

    try:
        logger.info( f"Copying from canonical: {canonical_path}" )
        logger.info( f"  Target: {output_path}" )

        shutil.copy2( canonical_path, output_path )

        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error( f"  Copy failed or produced empty file: {output_path}" )
            return False

        return True

    except Exception as e:
        logger.error( f"  Copy failed: {type( e ).__name__}: {e}" )
        return False


def validate_header( file_path, expected_columns, logger ):
    """Read the first line and confirm expected columns are present. Returns True if all found."""

    try:
        # hgnc_id<tab>symbol<tab>...<tab>uniprot_ids<tab>...
        # HGNC:5<tab>A1BG<tab>...
        with open( file_path, 'r' ) as input_complete_set:
            header_line = input_complete_set.readline().rstrip( '\n' )

        parts_header_line = header_line.split( '\t' )
        missing = [ column for column in expected_columns if column not in parts_header_line ]

        if missing:
            logger.error( f"  Header validation FAILED. Missing columns: {missing}" )
            logger.error( f"  Got {len( parts_header_line )} columns; first 5: {parts_header_line[ :5 ]}" )
            return False

        logger.info( f"  Header validation OK ({len( parts_header_line )} columns; required all present)" )
        return True

    except Exception as e:
        logger.error( f"  Header validation error: {type( e ).__name__}: {e}" )
        return False


def count_lines( file_path ):
    """Count non-empty lines in a file."""

    line_count = 0
    with open( file_path, 'r', errors='replace' ) as input_file:
        for line in input_file:
            if line.strip():
                line_count += 1
    return line_count


def write_manifest( manifest_path, file_path, source, download_date ):
    """Write a self-documenting download manifest TSV."""

    line_count = count_lines( file_path )
    file_size = file_path.stat().st_size

    output = 'Filename (name of downloaded file)' + '\t'
    output += 'Source (URL downloaded from, or canonical_local_copy if reused)' + '\t'
    output += 'Line_Count (number of non-empty lines including header)' + '\t'
    output += 'File_Size_Bytes (size in bytes)' + '\t'
    output += 'Download_Date (YYYY-MM-DD when this run executed)' + '\t'
    output += 'Status (SUCCESS or FAILED)' + '\n'

    with open( manifest_path, 'w' ) as output_manifest:
        output_manifest.write( output )

        row = file_path.name + '\t'
        row += source + '\t'
        row += str( line_count ) + '\t'
        row += str( file_size ) + '\t'
        row += download_date + '\t'
        row += 'SUCCESS' + '\n'
        output_manifest.write( row )


def main():
    parser = argparse.ArgumentParser(
        description = "Download HGNC complete_set TSV (with uniprot_ids); idempotent against canonical subproject copy."
    )
    parser.add_argument(
        '--output-directory',
        required = True,
        help = "Directory where hgnc_complete_set.txt + download manifest will be written.",
    )
    parser.add_argument(
        '--log-file',
        default = None,
        help = "Path to log file. Defaults to <output-directory>/0_ai-log-download_hgnc_complete_set.log",
    )
    parser.add_argument(
        '--canonical-source',
        default = None,
        help = "Optional absolute path to canonical hgnc_complete_set.txt at subproject level. If it exists, it is copied locally instead of re-downloading from the network.",
    )
    arguments = parser.parse_args()

    output_directory = Path( arguments.output_directory )
    output_directory.mkdir( parents=True, exist_ok=True )

    log_file_path = (
        Path( arguments.log_file )
        if arguments.log_file
        else output_directory / '0_ai-log-download_hgnc_complete_set.log'
    )
    log_file_path.parent.mkdir( parents=True, exist_ok=True )

    logger = setup_logging( log_file_path )

    logger.info( "=" * 70 )
    logger.info( "HGNC complete_set Download" )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Output directory: {output_directory}" )
    logger.info( "=" * 70 )

    output_file = output_directory / 'hgnc_complete_set.txt'

    # Idempotency: prefer a canonical local copy at subproject level if present.
    source = HGNC_COMPLETE_SET_URL
    used_canonical = False

    if arguments.canonical_source:
        canonical_path = Path( arguments.canonical_source )
        if canonical_path.exists() and canonical_path.is_file() and canonical_path.stat().st_size > 0:
            logger.info( f"Canonical source exists: {canonical_path}" )
            if copy_from_canonical( canonical_path, output_file, logger ):
                source = 'canonical_local_copy'
                used_canonical = True
            else:
                logger.warning( "Canonical copy failed; falling back to network download." )
        else:
            logger.info( f"Canonical source not present (or empty): {canonical_path}" )
            logger.info( "Falling through to network download." )

    if not used_canonical:
        if not download_file( HGNC_COMPLETE_SET_URL, output_file, logger ):
            logger.error( "CRITICAL ERROR: Failed to download hgnc_complete_set.txt." )
            logger.error( f"URL: {HGNC_COMPLETE_SET_URL}" )
            logger.error( "Check network connectivity from the compute node, and that genenames.org is reachable." )
            sys.exit( 1 )

    # Validate the file has the columns we depend on.
    if not validate_header( output_file, EXPECTED_HEADER_COLUMNS, logger ):
        logger.error( "CRITICAL ERROR: Downloaded file does not contain expected columns." )
        logger.error( f"Required columns: {EXPECTED_HEADER_COLUMNS}" )
        logger.error( "The HGNC TSV layout may have changed upstream; inspect the file at:" )
        logger.error( f"  {output_file}" )
        sys.exit( 1 )

    file_size = output_file.stat().st_size
    line_count = count_lines( output_file )
    logger.info( f"File size: {file_size:,} bytes" )
    logger.info( f"Line count (non-empty): {line_count:,}" )

    # Write self-documenting manifest.
    manifest_path = output_directory / '0_ai-download_manifest.tsv'
    download_date = datetime.now().strftime( '%Y-%m-%d' )
    write_manifest( manifest_path, output_file, source, download_date )
    logger.info( f"Manifest written: {manifest_path}" )

    logger.info( "=" * 70 )
    logger.info( "HGNC complete_set Download Complete" )
    logger.info( "=" * 70 )


if __name__ == '__main__':
    main()
