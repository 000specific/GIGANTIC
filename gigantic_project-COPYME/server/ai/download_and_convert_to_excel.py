#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Download GIGANTIC server tables and convert them to Excel locally, deleting the downloaded TSVs
# Human: Eric Edsinger

"""
download_and_convert_to_excel — fetch TSV/CSV tables from a GIGANTIC data
server URL, convert each to Excel (.xlsx) on this machine, and delete the
downloaded TSV, keeping only the Excel files.

This is the companion to the server's built-in "EXCEL" button. Use this when
you want to grab a whole directory of tables at once from the command line (or
have Claude Code do it for you).

It is STDLIB ONLY — no pip install needed. It just needs `tsv_to_xlsx.py` in
the same directory (it is, in this repo).

Safety contract (shared with the server via tsv_to_xlsx):
  * Every cell is written as TEXT — gene names and e-values are never coerced.
  * REFUSE + REPORT: if a table cannot be stored in Excel without loss
    (cell > 32,767 chars, sheet > 1,048,576 rows / 16,384 cols, bad encoding),
    NO .xlsx is produced for it and the downloaded TSV is KEPT so nothing is
    lost. The script reports exactly which file/cell blocked it and exits 1.

Usage:
    python3 download_and_convert_to_excel.py URL [--output-dir DIR] [--recursive] [--keep-tsv]

Examples:
    # One directory of tables (the common case):
    python3 download_and_convert_to_excel.py \\
        http://localhost:9456/annogroups/BLOCK_build_annogroups/workflow-RUN_6-build_annogroups/2-output/pfam/

    # Into a chosen folder, including subdirectories:
    python3 download_and_convert_to_excel.py URL --output-dir ~/Desktop/pfam_excel --recursive

    # A single table (directory page, file page, or /download/ link all work).
"""

from pathlib import Path
import argparse
import sys
import re
import urllib.parse
import urllib.request

# Use the same converter the server uses (sits next to this file).
_THIS_DIRECTORY = Path( __file__ ).resolve().parent
if str( _THIS_DIRECTORY ) not in sys.path:
    sys.path.insert( 0, str( _THIS_DIRECTORY ) )
import tsv_to_xlsx


FILE_LINK_PATTERN = re.compile( r'href="(/download/[^"]+)"' )
CARD_LINK_PATTERN = re.compile( r'class="card"\s+href="([^"]+)"' )
TABLE_SUFFIXES = ( '.tsv', '.csv' )


def fetch( url ):
    """Return ( content_type, raw_bytes ) for a URL."""
    request = urllib.request.Request( url, headers = { 'User-Agent': 'gigantic-excel-fetch' } )
    with urllib.request.urlopen( request, timeout = 120 ) as response:
        content_type = response.headers.get_content_type()
        return content_type, response.read()


def path_segments( url, strip_download = False ):
    """Return the non-empty path segments of a URL, optionally dropping a
    leading 'download' segment."""
    path = urllib.parse.urlparse( url ).path
    segments = [ urllib.parse.unquote( p ) for p in path.split( '/' ) if p ]
    if strip_download and segments and segments[ 0 ] == 'download':
        segments = segments[ 1: ]
    return segments


def convert_one( file_url, start_segments, output_dir, keep_tsv, results, quiet ):
    """Download a single TSV/CSV and convert it. Deletes the downloaded TSV on
    success; keeps it (and records the reason) on refusal."""
    file_segments = path_segments( file_url, strip_download = True )
    filename = file_segments[ -1 ] if file_segments else 'table.tsv'

    # Mirror subdirectories below the starting directory (for --recursive).
    if start_segments and file_segments[ :len( start_segments ) ] == start_segments:
        relative_parts = file_segments[ len( start_segments ): ]
    else:
        relative_parts = [ filename ]
    sub_directory_parts = relative_parts[ :-1 ]

    target_directory = output_dir.joinpath( *sub_directory_parts ) if sub_directory_parts else output_dir
    target_directory.mkdir( parents = True, exist_ok = True )
    tsv_path = target_directory / filename
    xlsx_path = tsv_path.with_suffix( '.xlsx' )

    try:
        raw_bytes = fetch( file_url )[ 1 ]
    except Exception as download_error:
        results[ 'errors' ].append( ( filename, f'download failed: {download_error}' ) )
        return

    tsv_path.write_bytes( raw_bytes )

    ok, report = tsv_to_xlsx.convert_file( tsv_path, xlsx_path )
    if ok:
        if not keep_tsv:
            tsv_path.unlink()
        results[ 'converted' ].append( xlsx_path )
        if not quiet:
            print( f"  OK     {filename} -> {xlsx_path.name}" )
    else:
        # Keep the TSV so the data is not lost; report why.
        results[ 'refused' ].append( ( filename, report ) )
        if not quiet:
            print( f"  REFUSED {filename} (kept TSV; not converted):" )
            for problem in report:
                print( f"            - {problem}" )


def gather_and_convert( page_url, page_html, start_segments, output_dir, recursive, keep_tsv, visited, results, quiet ):
    """Process every table linked on a directory page; optionally recurse into
    its subdirectories."""
    file_links = FILE_LINK_PATTERN.findall( page_html )
    for link in file_links:
        file_url = urllib.parse.urljoin( page_url, link )
        if link.lower().endswith( TABLE_SUFFIXES ):
            convert_one( file_url, start_segments, output_dir, keep_tsv, results, quiet )
        else:
            results[ 'skipped' ].append( path_segments( file_url, strip_download = True )[ -1 ] )

    if recursive:
        for card in CARD_LINK_PATTERN.findall( page_html ):
            sub_url = urllib.parse.urljoin( page_url, card )
            if not sub_url.endswith( '/' ) or sub_url in visited:
                continue
            visited.add( sub_url )
            try:
                content_type, data = fetch( sub_url )
            except Exception as sub_error:
                results[ 'errors' ].append( ( sub_url, f'fetch failed: {sub_error}' ) )
                continue
            if 'html' in content_type:
                gather_and_convert(
                    sub_url, data.decode( 'utf-8', 'replace' ), start_segments,
                    output_dir, recursive, keep_tsv, visited, results, quiet
                )


def main():
    parser = argparse.ArgumentParser(
        description = 'Download GIGANTIC server tables and convert them to Excel locally (deletes the downloaded TSVs).'
    )
    parser.add_argument( 'url', help = 'A GIGANTIC server URL: a directory page, a file page, or a /download/ link.' )
    parser.add_argument( '--output-dir', default = '.', help = 'Where to write the .xlsx files (default: current directory).' )
    parser.add_argument( '--recursive', action = 'store_true', help = 'Also convert tables in subdirectories.' )
    parser.add_argument( '--keep-tsv', action = 'store_true', help = 'Keep the downloaded TSVs instead of deleting them.' )
    parser.add_argument( '--quiet', action = 'store_true', help = 'Only print the final summary.' )
    args = parser.parse_args()

    output_dir = Path( args.output_dir ).expanduser()
    output_dir.mkdir( parents = True, exist_ok = True )

    results = { 'converted': [], 'refused': [], 'skipped': [], 'errors': [] }

    print( f"Source: {args.url}" )
    print( f"Output: {output_dir}" )
    print()

    try:
        content_type, data = fetch( args.url )
    except Exception as fetch_error:
        print( f"ERROR: could not reach {args.url}: {fetch_error}", file = sys.stderr )
        sys.exit( 1 )

    if 'html' in content_type:
        # A page (directory or single-file). Scrape its /download/ links.
        start_segments = path_segments( args.url )
        gather_and_convert(
            args.url, data.decode( 'utf-8', 'replace' ), start_segments,
            output_dir, args.recursive, args.keep_tsv, set(), results, args.quiet
        )
    else:
        # The URL pointed straight at a raw file (e.g. a /download/ link).
        filename = path_segments( args.url, strip_download = True )[ -1 ]
        tsv_path = output_dir / filename
        if filename.lower().endswith( TABLE_SUFFIXES ):
            tsv_path.write_bytes( data )
            xlsx_path = tsv_path.with_suffix( '.xlsx' )
            ok, report = tsv_to_xlsx.convert_file( tsv_path, xlsx_path )
            if ok:
                if not args.keep_tsv:
                    tsv_path.unlink()
                results[ 'converted' ].append( xlsx_path )
            else:
                results[ 'refused' ].append( ( filename, report ) )
        else:
            results[ 'skipped' ].append( filename )

    # Summary
    print()
    print( '=' * 60 )
    print( f"Converted: {len( results[ 'converted' ] )} file(s)" )
    if results[ 'skipped' ]:
        print( f"Skipped (not a table): {len( results[ 'skipped' ] )}" )
    if results[ 'refused' ]:
        print( f"REFUSED (kept TSV, not converted): {len( results[ 'refused' ] )}" )
        for filename, report in results[ 'refused' ]:
            print( f"  - {filename}" )
            for problem in report:
                print( f"      {problem}" )
    if results[ 'errors' ]:
        print( f"Errors: {len( results[ 'errors' ] )}" )
        for where, message in results[ 'errors' ]:
            print( f"  - {where}: {message}" )
    print( '=' * 60 )

    if results[ 'refused' ] or results[ 'errors' ]:
        sys.exit( 1 )


if __name__ == '__main__':
    main()
