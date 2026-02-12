#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Ingest source proteomes into GIGANTIC
# Human: Eric Edsinger
"""
GIGANTIC Source Proteome Ingestion Script

This script reads a source manifest and:
1. Validates that all source proteome files exist
2. Hard copies proteomes to OUTPUT_pipeline/1-output/proteomes/
3. Creates a manifest of ingested files

Input:
    - Source manifest TSV from INPUT_user/source_manifest.tsv

Output:
    - Hard copies in 1-output/proteomes/
    - Ingestion log in 1-output/ingestion_log.tsv
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def parse_source_manifest( manifest_path: Path ) -> list:
    """
    Parse the source manifest TSV file.

    # species_name	proteome_path
    # Homo_sapiens	/path/to/Homo_sapiens.fasta

    Returns list of (species_name, proteome_path) tuples.
    """
    entries = []

    with open( manifest_path, 'r' ) as input_manifest:
        for line in input_manifest:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 2:
                print( f"WARNING: Skipping malformed line (need 2 columns): {line}" )
                continue

            species_name = parts[ 0 ].strip()
            proteome_path = parts[ 1 ].strip()

            entries.append( ( species_name, proteome_path ) )

    return entries


def validate_sources( entries: list, workflow_dir: Path ) -> tuple:
    """
    Validate that all source proteome files exist.

    Returns (valid_entries, missing_entries)
    """
    valid_entries = []
    missing_entries = []

    for species_name, proteome_path in entries:
        # Handle relative paths (relative to workflow directory)
        if not os.path.isabs( proteome_path ):
            full_path = workflow_dir / proteome_path
        else:
            full_path = Path( proteome_path )

        # Resolve to absolute path
        full_path = full_path.resolve()

        if full_path.exists():
            valid_entries.append( ( species_name, str( full_path ) ) )
        else:
            missing_entries.append( ( species_name, proteome_path, str( full_path ) ) )

    return valid_entries, missing_entries


def ingest_proteomes( entries: list, output_dir: Path, overwrite: bool = False ) -> list:
    """
    Copy proteomes to output directory.

    Returns list of (species_name, source_path, dest_path) tuples for successfully copied files.
    """
    proteome_dir = output_dir / 'proteomes'
    proteome_dir.mkdir( parents = True, exist_ok = True )

    ingested = []

    for species_name, source_path in entries:
        source_path = Path( source_path )

        # Determine destination filename
        # Keep original extension, but standardize name format
        extension = source_path.suffix
        if not extension:
            extension = '.aa'

        dest_filename = f"{species_name}{extension}"
        dest_path = proteome_dir / dest_filename

        # Check if destination exists
        if dest_path.exists() and not overwrite:
            print( f"SKIP: {dest_filename} already exists (use overwrite to replace)" )
            ingested.append( ( species_name, str( source_path ), str( dest_path ), 'skipped' ) )
            continue

        # Copy the file
        try:
            shutil.copy2( source_path, dest_path )
            print( f"COPIED: {species_name} -> {dest_filename}" )
            ingested.append( ( species_name, str( source_path ), str( dest_path ), 'copied' ) )
        except Exception as error:
            print( f"ERROR: Failed to copy {species_name}: {error}" )
            ingested.append( ( species_name, str( source_path ), str( dest_path ), f'error: {error}' ) )

    return ingested


def write_ingestion_log( ingested: list, output_dir: Path, project_name: str ):
    """
    Write a log of all ingested files.
    """
    log_path = output_dir / 'ingestion_log.tsv'

    with open( log_path, 'w' ) as output_log:
        # Write header
        output = 'species_name (species identifier)\t'
        output += 'source_path (original file location)\t'
        output += 'dest_path (GIGANTIC location)\t'
        output += 'status (copied, skipped, or error)\n'
        output_log.write( output )

        # Write entries
        for species_name, source_path, dest_path, status in ingested:
            output = f"{species_name}\t{source_path}\t{dest_path}\t{status}\n"
            output_log.write( output )

    print( f"\nIngestion log written to: {log_path}" )


def main():
    parser = argparse.ArgumentParser(
        description = 'Ingest source proteomes into GIGANTIC'
    )
    parser.add_argument(
        '--manifest',
        type = str,
        required = True,
        help = 'Path to source manifest TSV file'
    )
    parser.add_argument(
        '--output-dir',
        type = str,
        required = True,
        help = 'Output directory for copied proteomes'
    )
    parser.add_argument(
        '--project-name',
        type = str,
        default = 'my_project',
        help = 'Project name for logging'
    )
    parser.add_argument(
        '--overwrite',
        action = 'store_true',
        help = 'Overwrite existing files'
    )
    parser.add_argument(
        '--missing-action',
        type = str,
        choices = [ 'error', 'warn', 'skip' ],
        default = 'error',
        help = 'Action when source files are missing'
    )

    args = parser.parse_args()

    manifest_path = Path( args.manifest )
    output_dir = Path( args.output_dir )

    # Determine workflow directory (for resolving relative paths)
    # The manifest is in INPUT_user/, so workflow dir is one level up
    workflow_dir = manifest_path.parent.parent

    print( "=" * 72 )
    print( "GIGANTIC Source Proteome Ingestion" )
    print( "=" * 72 )
    print( f"Project: {args.project_name}" )
    print( f"Manifest: {manifest_path}" )
    print( f"Output: {output_dir}" )
    print( f"Timestamp: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    print( "=" * 72 )
    print()

    # Parse manifest
    print( "Parsing source manifest..." )
    entries = parse_source_manifest( manifest_path )
    print( f"  Found {len( entries )} entries" )
    print()

    if not entries:
        print( "ERROR: No entries found in manifest!" )
        sys.exit( 1 )

    # Validate sources
    print( "Validating source files..." )
    valid_entries, missing_entries = validate_sources( entries, workflow_dir )
    print( f"  Valid: {len( valid_entries )}" )
    print( f"  Missing: {len( missing_entries )}" )
    print()

    # Handle missing files
    if missing_entries:
        print( "Missing source files:" )
        for species_name, original_path, resolved_path in missing_entries:
            print( f"  - {species_name}: {original_path}" )
            print( f"    (resolved to: {resolved_path})" )
        print()

        if args.missing_action == 'error':
            print( "ERROR: Some source files are missing! Aborting." )
            print( "Use --missing-action=warn to continue with available files." )
            sys.exit( 1 )
        elif args.missing_action == 'warn':
            print( "WARNING: Continuing with available files only." )
        # 'skip' action is silent

    if not valid_entries:
        print( "ERROR: No valid source files found!" )
        sys.exit( 1 )

    # Ingest proteomes
    print( "Ingesting proteomes..." )
    output_dir.mkdir( parents = True, exist_ok = True )
    ingested = ingest_proteomes( valid_entries, output_dir, args.overwrite )
    print()

    # Write ingestion log
    write_ingestion_log( ingested, output_dir, args.project_name )

    # Summary
    copied_count = sum( 1 for _, _, _, status in ingested if status == 'copied' )
    skipped_count = sum( 1 for _, _, _, status in ingested if status == 'skipped' )
    error_count = sum( 1 for _, _, _, status in ingested if status.startswith( 'error' ) )

    print()
    print( "=" * 72 )
    print( "INGESTION COMPLETE" )
    print( "=" * 72 )
    print( f"  Copied: {copied_count}" )
    print( f"  Skipped: {skipped_count}" )
    print( f"  Errors: {error_count}" )
    print( "=" * 72 )

    if error_count > 0:
        sys.exit( 1 )


if __name__ == '__main__':
    main()
