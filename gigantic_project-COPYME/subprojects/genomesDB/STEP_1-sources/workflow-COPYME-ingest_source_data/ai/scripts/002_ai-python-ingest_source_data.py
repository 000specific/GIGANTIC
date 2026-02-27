#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 13 16:00 | Purpose: Ingest source data by hard-copying files into GIGANTIC structure
# Human: Eric Edsinger
"""
002_ai-python-ingest_source_data.py

STEP 2 of 3 in the source data ingestion workflow.

Reads the source manifest and hard-copies all listed files into organized
subdirectories within OUTPUT_pipeline/2-output/. Files are organized by
data type (T1_proteomes, genomes, gene_annotations) and original filenames
are preserved.

Input:
    - Source manifest TSV from INPUT_user/source_manifest.tsv
      (4 columns: genus_species, genome_path, gff_path, proteome_path)

Output (to OUTPUT_pipeline/2-output/):
    - T1_proteomes/       Hard copies of all proteome .aa files
    - genomes/            Hard copies of all genome .fasta files
    - gene_annotations/   Hard copies of all .gff3 and .gtf files
    - 2_ai-ingestion_log.tsv   Per-file log of what was copied

Usage:
    python3 002_ai-python-ingest_source_data.py \\
        --manifest INPUT_user/source_manifest.tsv \\
        --output-dir OUTPUT_pipeline/2-output \\
        --workflow-dir /path/to/workflow/root
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def resolve_path( path_string: str, workflow_dir: Path ):
    """
    Resolve a path from the manifest.

    Returns absolute Path if valid, None if 'NA' or empty.
    """
    if not path_string or path_string.upper() == 'NA':
        return None

    if not os.path.isabs( path_string ):
        full_path = workflow_dir / path_string
    else:
        full_path = Path( path_string )

    return full_path.resolve()


def parse_manifest( manifest_path: Path, workflow_dir: Path ) -> list:
    """
    Parse the 4-column source manifest TSV file.

    # genus_species	genome_path	gff_path	proteome_path
    # Abeoforma_whisleri	../user_research/.../file.fasta	NA	../user_research/.../file.aa

    Returns list of dicts with keys: genus_species, genome_path, gff_path, proteome_path.
    Each path is resolved to absolute. 'NA' or empty paths become None.
    """
    entries = []
    header_found = False

    with open( manifest_path, 'r' ) as input_manifest:
        for line in input_manifest:
            line = line.strip()

            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )

            if not header_found:
                if parts[ 0 ] == 'genus_species':
                    header_found = True
                    continue
                else:
                    print( f"WARNING: Expected header row starting with 'genus_species', got: {parts[ 0 ]}" )
                    print( "  Treating as data row" )

            if len( parts ) < 4:
                print( f"WARNING: Skipping malformed line (need 4 columns, got {len( parts )}): {line}" )
                continue

            genus_species = parts[ 0 ].strip()
            genome_path = resolve_path( parts[ 1 ].strip(), workflow_dir )
            gff_path = resolve_path( parts[ 2 ].strip(), workflow_dir )
            proteome_path = resolve_path( parts[ 3 ].strip(), workflow_dir )

            entries.append( {
                'genus_species': genus_species,
                'genome_path': genome_path,
                'gff_path': gff_path,
                'proteome_path': proteome_path,
            } )

    return entries


def ingest_files( entries: list, output_dir: Path, overwrite: bool = False ) -> list:
    """
    Copy source data files to organized output directories, preserving original filenames.

    Output structure:
        output_dir/T1_proteomes/       proteome .aa files
        output_dir/genomes/            genome .fasta files
        output_dir/gene_annotations/   annotation .gff3/.gtf files

    Returns list of ingestion records for the log.
    """
    proteome_dir = output_dir / 'T1_proteomes'
    genome_dir = output_dir / 'genomes'
    gff_dir = output_dir / 'gene_annotations'

    proteome_dir.mkdir( parents = True, exist_ok = True )
    genome_dir.mkdir( parents = True, exist_ok = True )
    gff_dir.mkdir( parents = True, exist_ok = True )

    ingestion_records = []

    data_types___output_directories = {
        'proteome_path': proteome_dir,
        'genome_path': genome_dir,
        'gff_path': gff_dir,
    }

    data_types___labels = {
        'proteome_path': 'T1_proteome',
        'genome_path': 'genome',
        'gff_path': 'gene_annotation',
    }

    for entry in entries:
        genus_species = entry[ 'genus_species' ]

        for path_key in [ 'proteome_path', 'genome_path', 'gff_path' ]:
            source_path = entry[ path_key ]
            data_label = data_types___labels[ path_key ]
            destination_directory = data_types___output_directories[ path_key ]

            if source_path is None:
                ingestion_records.append( {
                    'genus_species': genus_species,
                    'data_type': data_label,
                    'source_path': 'NA',
                    'destination_path': 'NA',
                    'status': 'not_available',
                } )
                continue

            if not source_path.exists():
                ingestion_records.append( {
                    'genus_species': genus_species,
                    'data_type': data_label,
                    'source_path': str( source_path ),
                    'destination_path': 'NA',
                    'status': 'missing',
                } )
                continue

            destination_path = destination_directory / source_path.name

            if destination_path.exists() and not overwrite:
                print( f"  SKIP: {genus_species} {data_label} already exists" )
                ingestion_records.append( {
                    'genus_species': genus_species,
                    'data_type': data_label,
                    'source_path': str( source_path ),
                    'destination_path': str( destination_path ),
                    'status': 'skipped',
                } )
                continue

            try:
                shutil.copy2( source_path, destination_path )
                print( f"  COPIED: {genus_species} {data_label} -> {source_path.name}" )
                ingestion_records.append( {
                    'genus_species': genus_species,
                    'data_type': data_label,
                    'source_path': str( source_path ),
                    'destination_path': str( destination_path ),
                    'status': 'copied',
                } )
            except Exception as error:
                print( f"  ERROR: {genus_species} {data_label}: {error}" )
                ingestion_records.append( {
                    'genus_species': genus_species,
                    'data_type': data_label,
                    'source_path': str( source_path ),
                    'destination_path': str( destination_path ),
                    'status': f'error: {error}',
                } )

    return ingestion_records


def write_ingestion_log( ingestion_records: list, output_dir: Path ):
    """
    Write the ingestion log TSV documenting every file operation.
    """
    log_path = output_dir / '2_ai-ingestion_log.tsv'

    with open( log_path, 'w' ) as output_log:
        output = (
            'Genus_Species (species identifier)\t'
            'Data_Type (type of data file: T1_proteome, genome, or gene_annotation)\t'
            'Source_Path (original file location)\t'
            'Destination_Path (GIGANTIC location in OUTPUT_pipeline 2-output)\t'
            'Status (copied, skipped, not_available, missing, or error)\n'
        )
        output_log.write( output )

        for record in ingestion_records:
            output = (
                record[ 'genus_species' ] + '\t'
                + record[ 'data_type' ] + '\t'
                + record[ 'source_path' ] + '\t'
                + record[ 'destination_path' ] + '\t'
                + record[ 'status' ] + '\n'
            )
            output_log.write( output )

    print( f"Ingestion log: {log_path}" )
    return log_path


def main():
    parser = argparse.ArgumentParser(
        description = 'Ingest source data (proteomes, genomes, GFFs) by copying into GIGANTIC structure'
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
        help = 'Output directory for ingested files (OUTPUT_pipeline/2-output)'
    )
    parser.add_argument(
        '--workflow-dir',
        type = str,
        default = None,
        help = 'Workflow root directory for resolving relative paths in manifest'
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
        help = 'Action when source files are missing: error (abort), warn (continue), skip (silent)'
    )

    arguments = parser.parse_args()

    manifest_path = Path( arguments.manifest ).resolve()
    output_dir = Path( arguments.output_dir )

    if arguments.workflow_dir:
        workflow_dir = Path( arguments.workflow_dir ).resolve()
    else:
        workflow_dir = manifest_path.parent.parent

    # Create output directory
    output_dir.mkdir( parents = True, exist_ok = True )

    print( "=" * 60 )
    print( "STEP 2: Ingest Source Data" )
    print( "=" * 60 )
    print( f"Project: {arguments.project_name}" )
    print( f"Manifest: {manifest_path}" )
    print( f"Output: {output_dir}" )
    print( f"Timestamp: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    print( "=" * 60 )
    print()

    # Parse manifest
    print( "Parsing manifest..." )
    entries = parse_manifest( manifest_path, workflow_dir )
    print( f"  Found {len( entries )} species entries" )

    proteome_count = sum( 1 for entry in entries if entry[ 'proteome_path' ] is not None )
    genome_count = sum( 1 for entry in entries if entry[ 'genome_path' ] is not None )
    gff_count = sum( 1 for entry in entries if entry[ 'gff_path' ] is not None )

    print( f"  Proteomes: {proteome_count}" )
    print( f"  Genomes: {genome_count}" )
    print( f"  Gene annotations: {gff_count}" )
    print()

    if not entries:
        print( "CRITICAL ERROR: No entries found in manifest!" )
        sys.exit( 1 )

    # Ingest files
    print( "Ingesting source data..." )
    ingestion_records = ingest_files( entries, output_dir, arguments.overwrite )
    print()

    # Write log
    write_ingestion_log( ingestion_records, output_dir )

    # Summary
    copied_count = sum( 1 for record in ingestion_records if record[ 'status' ] == 'copied' )
    skipped_count = sum( 1 for record in ingestion_records if record[ 'status' ] == 'skipped' )
    not_available_count = sum( 1 for record in ingestion_records if record[ 'status' ] == 'not_available' )
    error_count = sum( 1 for record in ingestion_records if record[ 'status' ].startswith( 'error' ) )

    print()
    print( "=" * 60 )
    print( "INGESTION COMPLETE" )
    print( "=" * 60 )
    print( f"  Species: {len( entries )}" )
    print( f"  Files copied: {copied_count}" )
    print( f"  Files skipped (already exist): {skipped_count}" )
    print( f"  Files not available (NA in manifest): {not_available_count}" )
    print( f"  Errors: {error_count}" )
    print( "=" * 60 )

    if error_count > 0:
        print( "CRITICAL ERROR: Some files failed to copy!" )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
