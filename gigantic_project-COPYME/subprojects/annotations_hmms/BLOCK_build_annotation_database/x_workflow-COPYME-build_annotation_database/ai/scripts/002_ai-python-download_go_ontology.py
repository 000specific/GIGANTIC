#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Download GO ontology OBO file and parse into fast-lookup TSV
# Human: Eric Edsinger

"""
002_ai-python-download_go_ontology.py

Downloads the Gene Ontology (GO) basic OBO file from the GO Consortium and
parses it into a fast-lookup TSV table. The OBO file is cached locally and
only re-downloaded when the cache expires (configurable via --cache-days).

The GO ontology provides standardized vocabulary for gene and gene product
attributes across all organisms. InterProScan assigns GO terms to proteins,
and this lookup table is used by script 003 to validate and annotate those
GO term assignments.

The OBO format is a structured text format where each GO term is a [Term]
stanza containing id, name, namespace, and optionally is_obsolete fields.

Input:
    --go-url: URL for the GO basic OBO file (default: http://purl.obolibrary.org/obo/go/go-basic.obo)
    --cache-days: Number of days before re-downloading (default: 30)
    --output-dir: Directory for output files

Output:
    2_ai-go_basic.obo
        Cached copy of the GO basic OBO file from the GO Consortium.

    2_ai-go_term_lookup.tsv
        Tab-separated lookup table with columns:
        - GO_ID (gene ontology identifier format GO:NNNNNNN)
        - GO_Name (human readable name of GO term)
        - GO_Namespace (biological_process or molecular_function or cellular_component)
        - Is_Obsolete (true or false indicating if term is obsolete)

    2_ai-log-download_go_ontology.log

Usage:
    python3 002_ai-python-download_go_ontology.py \\
        --go-url http://purl.obolibrary.org/obo/go/go-basic.obo \\
        --cache-days 30 \\
        --output-dir .
"""

import argparse
import logging
import sys
import time
import urllib.request
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '002_download_go_ontology' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '2_ai-log-download_go_ontology.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def check_cache_freshness( obo_file_path: Path, cache_days: int, logger: logging.Logger ) -> bool:
    """
    Check whether the cached OBO file exists and is recent enough.
    Returns True if cache is fresh (no download needed), False otherwise.
    """

    if not obo_file_path.exists():
        logger.info( "No cached OBO file found - download required" )
        return False

    if obo_file_path.stat().st_size == 0:
        logger.info( "Cached OBO file is empty - download required" )
        return False

    # Check file age
    file_modification_time = obo_file_path.stat().st_mtime
    current_time = time.time()
    file_age_seconds = current_time - file_modification_time
    file_age_days = file_age_seconds / ( 60 * 60 * 24 )

    if file_age_days > cache_days:
        logger.info( f"Cached OBO file is {file_age_days:.1f} days old (cache limit: {cache_days} days) - download required" )
        return False

    logger.info( f"Cached OBO file is {file_age_days:.1f} days old (cache limit: {cache_days} days) - using cache" )
    return True


def download_obo_file( go_url: str, obo_file_path: Path, logger: logging.Logger ) -> None:
    """Download the GO basic OBO file from the specified URL."""

    logger.info( f"Downloading GO ontology from: {go_url}" )

    try:
        urllib.request.urlretrieve( go_url, str( obo_file_path ) )
    except urllib.error.URLError as url_error:
        logger.error( "CRITICAL ERROR: Failed to download GO ontology OBO file!" )
        logger.error( f"URL: {go_url}" )
        logger.error( f"Error: {url_error}" )
        logger.error( "Check internet connectivity and verify the URL is correct." )
        logger.error( "Default URL: http://purl.obolibrary.org/obo/go/go-basic.obo" )
        sys.exit( 1 )
    except Exception as general_error:
        logger.error( "CRITICAL ERROR: Unexpected error downloading GO ontology!" )
        logger.error( f"URL: {go_url}" )
        logger.error( f"Error: {general_error}" )
        sys.exit( 1 )

    # Validate download
    if not obo_file_path.exists():
        logger.error( "CRITICAL ERROR: Download appeared to succeed but file does not exist!" )
        logger.error( f"Expected file: {obo_file_path}" )
        sys.exit( 1 )

    file_size = obo_file_path.stat().st_size

    if file_size == 0:
        logger.error( "CRITICAL ERROR: Downloaded OBO file is empty!" )
        logger.error( f"File: {obo_file_path}" )
        logger.error( "The download may have failed silently. Try again or check the URL." )
        sys.exit( 1 )

    file_size_megabytes = file_size / ( 1024 * 1024 )
    logger.info( f"Download complete: {file_size_megabytes:.1f} MB" )


def parse_obo_file( obo_file_path: Path, logger: logging.Logger ) -> list:
    """
    Parse the OBO format file and extract GO term information.

    OBO format structure (relevant fields):
        [Term]
        id: GO:0000001
        name: mitochondrion inheritance
        namespace: biological_process
        is_obsolete: true    (only present if term is obsolete)

    Returns a list of dictionaries with keys: go_id, go_name, go_namespace, is_obsolete
    """

    logger.info( f"Parsing OBO file: {obo_file_path}" )

    go_terms = []

    # State tracking for parsing
    current_term = None
    inside_term_stanza = False

    with open( obo_file_path, 'r' ) as input_obo_file:
        for line in input_obo_file:
            line = line.strip()

            # Detect start of a [Term] stanza
            if line == '[Term]':
                # Save previous term if it exists
                if current_term is not None and 'go_id' in current_term:
                    go_terms.append( current_term )

                current_term = {
                    'go_id': '',
                    'go_name': '',
                    'go_namespace': '',
                    'is_obsolete': 'false',
                }
                inside_term_stanza = True
                continue

            # Detect start of a non-Term stanza (like [Typedef])
            if line.startswith( '[' ) and line.endswith( ']' ):
                # Save previous term if it exists
                if current_term is not None and 'go_id' in current_term:
                    go_terms.append( current_term )
                current_term = None
                inside_term_stanza = False
                continue

            # Only parse lines inside [Term] stanzas
            if not inside_term_stanza or current_term is None:
                continue

            # Empty line ends a stanza
            if not line:
                if current_term is not None and 'go_id' in current_term:
                    go_terms.append( current_term )
                current_term = None
                inside_term_stanza = False
                continue

            # Parse relevant fields
            if line.startswith( 'id: ' ):
                current_term[ 'go_id' ] = line[ 4: ]

            elif line.startswith( 'name: ' ):
                current_term[ 'go_name' ] = line[ 6: ]

            elif line.startswith( 'namespace: ' ):
                current_term[ 'go_namespace' ] = line[ 11: ]

            elif line.startswith( 'is_obsolete: true' ):
                current_term[ 'is_obsolete' ] = 'true'

    # Save final term if file does not end with empty line
    if current_term is not None and 'go_id' in current_term:
        go_terms.append( current_term )

    logger.info( f"Parsed {len( go_terms )} GO terms from OBO file" )

    return go_terms


def write_lookup_table( go_terms: list, output_directory: Path, logger: logging.Logger ) -> None:
    """Write the parsed GO terms to a fast-lookup TSV file."""

    output_file = output_directory / '2_ai-go_term_lookup.tsv'

    # =========================================================================
    # Count terms per namespace and obsolete status
    # =========================================================================

    namespaces___counts = {}
    obsolete_count = 0

    for go_term in go_terms:
        namespace = go_term[ 'go_namespace' ]
        if namespace in namespaces___counts:
            namespaces___counts[ namespace ] += 1
        else:
            namespaces___counts[ namespace ] = 1

        if go_term[ 'is_obsolete' ] == 'true':
            obsolete_count += 1

    # =========================================================================
    # Validate parsed data
    # =========================================================================

    if len( go_terms ) == 0:
        logger.error( "CRITICAL ERROR: No GO terms were parsed from the OBO file!" )
        logger.error( "The OBO file may be corrupt or in an unexpected format." )
        logger.error( "Try deleting the cached OBO file and re-running to force a fresh download." )
        sys.exit( 1 )

    # GO ontology typically has > 40,000 terms; warn if suspiciously low
    if len( go_terms ) < 1000:
        logger.warning( f"WARNING: Only {len( go_terms )} GO terms parsed - this seems unusually low." )
        logger.warning( "The GO ontology typically contains > 40,000 terms." )
        logger.warning( "The OBO file may be truncated or corrupt." )

    # =========================================================================
    # Write lookup TSV
    # =========================================================================

    with open( output_file, 'w' ) as output_go_lookup:
        # Write header
        header = 'GO_ID (gene ontology identifier format GO:NNNNNNN)' + '\t'
        header += 'GO_Name (human readable name of GO term)' + '\t'
        header += 'GO_Namespace (biological_process or molecular_function or cellular_component)' + '\t'
        header += 'Is_Obsolete (true or false indicating if term is obsolete)' + '\n'
        output_go_lookup.write( header )

        # Write data rows
        for go_term in go_terms:
            output = go_term[ 'go_id' ] + '\t'
            output += go_term[ 'go_name' ] + '\t'
            output += go_term[ 'go_namespace' ] + '\t'
            output += go_term[ 'is_obsolete' ] + '\n'
            output_go_lookup.write( output )

    logger.info( f"Wrote GO term lookup table to: {output_file}" )

    # =========================================================================
    # Report counts per namespace
    # =========================================================================

    logger.info( "" )
    logger.info( "GO terms per namespace:" )
    for namespace in sorted( namespaces___counts.keys() ):
        count = namespaces___counts[ namespace ]
        logger.info( f"  {namespace}: {count}" )

    logger.info( f"  Obsolete terms: {obsolete_count}" )
    logger.info( f"  Total terms: {len( go_terms )}" )


def download_go_ontology( go_url: str, cache_days: int, output_directory: Path, logger: logging.Logger ) -> None:
    """
    Main workflow: check cache, download if needed, parse OBO, write lookup TSV.
    """

    obo_file_path = output_directory / '2_ai-go_basic.obo'

    # =========================================================================
    # Step 1: Check cache and download if needed
    # =========================================================================

    cache_is_fresh = check_cache_freshness( obo_file_path, cache_days, logger )

    if not cache_is_fresh:
        download_obo_file( go_url, obo_file_path, logger )
    else:
        logger.info( f"Using cached OBO file: {obo_file_path}" )

    # =========================================================================
    # Step 2: Parse OBO file
    # =========================================================================

    go_terms = parse_obo_file( obo_file_path, logger )

    # =========================================================================
    # Step 3: Write lookup table
    # =========================================================================

    write_lookup_table( go_terms, output_directory, logger )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 002 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  GO OBO file: {obo_file_path}" )
    logger.info( f"  GO lookup table: {output_directory / '2_ai-go_term_lookup.tsv'}" )
    logger.info( f"  Total GO terms: {len( go_terms )}" )
    logger.info( f"  Cache freshness: {'used cache' if cache_is_fresh else 'downloaded fresh'}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Download GO ontology OBO file and parse into fast-lookup TSV'
    )

    parser.add_argument(
        '--go-url',
        type = str,
        default = 'http://purl.obolibrary.org/obo/go/go-basic.obo',
        help = 'URL for the GO basic OBO file (default: http://purl.obolibrary.org/obo/go/go-basic.obo)'
    )

    parser.add_argument(
        '--cache-days',
        type = int,
        default = 30,
        help = 'Number of days to cache the OBO file before re-downloading (default: 30)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Output directory for OBO file and lookup TSV (default: current directory)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 002: Download GO Ontology" )
    logger.info( "=" * 70 )

    # Run download and parse
    download_go_ontology( arguments.go_url, arguments.cache_days, output_directory, logger )


if __name__ == '__main__':
    main()
