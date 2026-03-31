# AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: Download HGNC gene group database tables
# Human: Eric Edsinger

"""
Download HGNC gene group database tables from genenames.org.

Downloads the following files from Google Cloud Storage:
  - family.csv: Gene group metadata (ID, name, abbreviation, description)
  - hierarchy.csv: Direct parent-child relationships between groups
  - hierarchy_closure.csv: Full transitive hierarchy with distance values
  - gene_has_family.csv: Links HGNC gene IDs to family/group IDs

Also downloads the bulk TSV from the HGNC CGI endpoint:
  - hgnc_gene_groups_all.tsv: All gene-to-group assignments with gene symbols

Usage:
    python3 001_ai-python-download_hgnc_gene_group_data.py \
        --output-directory <path>

Output:
    <output-directory>/family.csv
    <output-directory>/hierarchy.csv
    <output-directory>/hierarchy_closure.csv
    <output-directory>/gene_has_family.csv
    <output-directory>/hgnc_gene_groups_all.tsv
    <output-directory>/download_manifest.tsv
"""

import argparse
import logging
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


def setup_logging( log_file_path ):
    """Configure logging to both file and console."""

    logger = logging.getLogger( 'download_hgnc' )
    logger.setLevel( logging.INFO )

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
    """
    Download a file from a URL to a local path.

    Parameters:
        url (str): URL to download from
        output_path (Path): Local file path to save to
        logger: Logger instance

    Returns:
        bool: True if download succeeded, False otherwise
    """

    logger.info( f"Downloading: {url}" )
    logger.info( f"  -> {output_path}" )

    try:
        urllib.request.urlretrieve( str( url ), str( output_path ) )

        file_size = output_path.stat().st_size
        logger.info( f"  Downloaded: {file_size:,} bytes" )

        # Basic validation: file should not be empty
        if file_size == 0:
            logger.error( f"  CRITICAL ERROR: Downloaded file is empty: {output_path}" )
            return False

        # Check for XML error responses (Google Cloud Storage returns XML on error)
        with open( output_path, 'r', errors='replace' ) as f:
            first_line = f.readline()
            if first_line.startswith( '<?xml' ) and 'Error' in first_line:
                logger.error( f"  CRITICAL ERROR: Server returned error response for {url}" )
                logger.error( f"  Response: {first_line[:200]}" )
                return False

        return True

    except urllib.error.URLError as error:
        logger.error( f"  CRITICAL ERROR: Failed to download {url}" )
        logger.error( f"  Error: {error}" )
        return False

    except Exception as error:
        logger.error( f"  CRITICAL ERROR: Unexpected error downloading {url}" )
        logger.error( f"  Error: {error}" )
        return False


def count_lines( file_path ):
    """Count lines in a file (excluding empty lines)."""

    count = 0
    with open( file_path, 'r' ) as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser( description='Download HGNC gene group database tables' )
    parser.add_argument( '--output-directory', required=True, help='Directory to save downloaded files' )
    parser.add_argument( '--log-file', default=None, help='Path to log file' )
    arguments = parser.parse_args()

    output_directory = Path( arguments.output_directory )
    output_directory.mkdir( parents=True, exist_ok=True )

    # Setup logging
    if arguments.log_file:
        log_file_path = Path( arguments.log_file )
    else:
        log_file_path = output_directory / '1_ai-log-download_hgnc_gene_group_data.log'
    log_file_path.parent.mkdir( parents=True, exist_ok=True )
    logger = setup_logging( log_file_path )

    logger.info( "=" * 70 )
    logger.info( "HGNC Gene Group Data Download" )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Output directory: {output_directory}" )
    logger.info( "=" * 70 )

    # Define files to download
    google_cloud_storage_base = "https://storage.googleapis.com/public-download-files/hgnc/csv/csv/genefamily_db_tables"

    files_to_download = [
        {
            'url': f"{google_cloud_storage_base}/family.csv",
            'filename': 'family.csv',
            'description': 'Gene group metadata (ID, name, abbreviation, description)',
        },
        {
            'url': f"{google_cloud_storage_base}/hierarchy.csv",
            'filename': 'hierarchy.csv',
            'description': 'Direct parent-child relationships between groups',
        },
        {
            'url': f"{google_cloud_storage_base}/hierarchy_closure.csv",
            'filename': 'hierarchy_closure.csv',
            'description': 'Full transitive hierarchy with distance values',
        },
        {
            'url': f"{google_cloud_storage_base}/gene_has_family.csv",
            'filename': 'gene_has_family.csv',
            'description': 'Links HGNC gene IDs to family/group IDs',
        },
        {
            'url': "https://www.genenames.org/cgi-bin/genegroup/download-all",
            'filename': 'hgnc_gene_groups_all.tsv',
            'description': 'Bulk download: all gene-to-group assignments with gene symbols',
        },
    ]

    # Download each file
    download_results = []
    failures = 0

    for file_info in files_to_download:
        output_path = output_directory / file_info[ 'filename' ]
        success = download_file( file_info[ 'url' ], output_path, logger )

        if success:
            line_count = count_lines( output_path )
            file_size = output_path.stat().st_size
            download_results.append( {
                'filename': file_info[ 'filename' ],
                'description': file_info[ 'description' ],
                'url': file_info[ 'url' ],
                'line_count': line_count,
                'file_size': file_size,
                'status': 'SUCCESS',
            } )
            logger.info( f"  Lines: {line_count}" )
        else:
            failures += 1
            download_results.append( {
                'filename': file_info[ 'filename' ],
                'description': file_info[ 'description' ],
                'url': file_info[ 'url' ],
                'line_count': 0,
                'file_size': 0,
                'status': 'FAILED',
            } )

    # Write download manifest
    manifest_path = output_directory / 'download_manifest.tsv'
    with open( manifest_path, 'w' ) as output_manifest:
        output = 'Filename (name of downloaded file)' + '\t'
        output += 'Description (what this file contains)' + '\t'
        output += 'URL (source download URL)' + '\t'
        output += 'Line_Count (number of non-empty lines)' + '\t'
        output += 'File_Size_Bytes (size in bytes)' + '\t'
        output += 'Status (SUCCESS or FAILED)' + '\t'
        output += 'Download_Date (date of download)' + '\n'
        output_manifest.write( output )

        download_date = datetime.now().strftime( '%Y-%m-%d' )

        for result in download_results:
            output = result[ 'filename' ] + '\t'
            output += result[ 'description' ] + '\t'
            output += result[ 'url' ] + '\t'
            output += str( result[ 'line_count' ] ) + '\t'
            output += str( result[ 'file_size' ] ) + '\t'
            output += result[ 'status' ] + '\t'
            output += download_date + '\n'
            output_manifest.write( output )

    logger.info( "" )
    logger.info( f"Download manifest written: {manifest_path}" )

    # Final summary
    logger.info( "" )
    logger.info( "=" * 70 )
    if failures > 0:
        logger.error( f"CRITICAL ERROR: {failures} download(s) failed!" )
        logger.error( "Cannot proceed with incomplete data." )
        logger.info( "=" * 70 )
        sys.exit( 1 )
    else:
        logger.info( f"All {len( files_to_download )} files downloaded successfully." )
        logger.info( f"Completed: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
        logger.info( "=" * 70 )


if __name__ == '__main__':
    main()
