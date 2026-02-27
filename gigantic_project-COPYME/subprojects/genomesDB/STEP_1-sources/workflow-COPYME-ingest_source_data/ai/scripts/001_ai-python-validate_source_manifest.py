#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 13 16:00 | Purpose: Validate source manifest and check all listed files exist
# Human: Eric Edsinger
"""
001_ai-python-validate_source_manifest.py

STEP 1 of 3 in the source data ingestion workflow.

Reads the user's source manifest TSV and validates that every listed file
exists on disk. Produces a detailed validation report and human-readable
summary so the user can see exactly what data is available before ingestion.

Input:
    - Source manifest TSV from INPUT_user/source_manifest.tsv
      (4 columns: genus_species, genome_path, gff_path, proteome_path)

Output (to OUTPUT_pipeline/1-output/):
    - 1_ai-source_validation_report.tsv
      (one row per species per data type: genus_species, data_type, path,
       file_exists, file_size_bytes)
    - 1_ai-validation_summary.txt
      (human-readable summary of what was found)

Usage:
    python3 001_ai-python-validate_source_manifest.py \\
        --manifest INPUT_user/source_manifest.tsv \\
        --output-dir OUTPUT_pipeline/1-output \\
        --workflow-dir /path/to/workflow/root
"""

import argparse
import os
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


def validate_entries( entries: list ) -> list:
    """
    Check each file path for existence and collect file sizes.

    Returns list of validation records:
        (genus_species, data_type, path_string, file_exists, file_size_bytes)
    """
    validation_records = []

    data_types___path_keys = {
        'T1_proteome': 'proteome_path',
        'genome': 'genome_path',
        'gene_annotation': 'gff_path',
    }

    for entry in entries:
        genus_species = entry[ 'genus_species' ]

        for data_type in data_types___path_keys:
            path_key = data_types___path_keys[ data_type ]
            file_path = entry[ path_key ]

            if file_path is None:
                validation_records.append( {
                    'genus_species': genus_species,
                    'data_type': data_type,
                    'path': 'NA',
                    'file_exists': 'not_applicable',
                    'file_size_bytes': 'NA',
                } )
            elif file_path.exists():
                file_size = file_path.stat().st_size
                validation_records.append( {
                    'genus_species': genus_species,
                    'data_type': data_type,
                    'path': str( file_path ),
                    'file_exists': 'yes',
                    'file_size_bytes': str( file_size ),
                } )
            else:
                validation_records.append( {
                    'genus_species': genus_species,
                    'data_type': data_type,
                    'path': str( file_path ),
                    'file_exists': 'no',
                    'file_size_bytes': 'NA',
                } )

    return validation_records


def write_validation_report( validation_records: list, output_dir: Path ):
    """
    Write the detailed validation report TSV.
    """
    report_path = output_dir / '1_ai-source_validation_report.tsv'

    with open( report_path, 'w' ) as output_report:
        output = (
            'Genus_Species (species identifier)\t'
            'Data_Type (type of data: T1_proteome, genome, or gene_annotation)\t'
            'Path (resolved absolute path to source file)\t'
            'File_Exists (yes, no, or not_applicable if path is NA)\t'
            'File_Size_Bytes (file size in bytes or NA)\n'
        )
        output_report.write( output )

        for record in validation_records:
            output = (
                record[ 'genus_species' ] + '\t'
                + record[ 'data_type' ] + '\t'
                + record[ 'path' ] + '\t'
                + record[ 'file_exists' ] + '\t'
                + record[ 'file_size_bytes' ] + '\n'
            )
            output_report.write( output )

    print( f"Validation report: {report_path}" )
    return report_path


def write_validation_summary( validation_records: list, entries: list, output_dir: Path, manifest_path: Path ):
    """
    Write the human-readable validation summary.
    """
    summary_path = output_dir / '1_ai-validation_summary.txt'

    species_count = len( entries )

    proteome_found = sum( 1 for record in validation_records if record[ 'data_type' ] == 'T1_proteome' and record[ 'file_exists' ] == 'yes' )
    proteome_na = sum( 1 for record in validation_records if record[ 'data_type' ] == 'T1_proteome' and record[ 'file_exists' ] == 'not_applicable' )
    proteome_missing = sum( 1 for record in validation_records if record[ 'data_type' ] == 'T1_proteome' and record[ 'file_exists' ] == 'no' )

    genome_found = sum( 1 for record in validation_records if record[ 'data_type' ] == 'genome' and record[ 'file_exists' ] == 'yes' )
    genome_na = sum( 1 for record in validation_records if record[ 'data_type' ] == 'genome' and record[ 'file_exists' ] == 'not_applicable' )
    genome_missing = sum( 1 for record in validation_records if record[ 'data_type' ] == 'genome' and record[ 'file_exists' ] == 'no' )

    gff_found = sum( 1 for record in validation_records if record[ 'data_type' ] == 'gene_annotation' and record[ 'file_exists' ] == 'yes' )
    gff_na = sum( 1 for record in validation_records if record[ 'data_type' ] == 'gene_annotation' and record[ 'file_exists' ] == 'not_applicable' )
    gff_missing = sum( 1 for record in validation_records if record[ 'data_type' ] == 'gene_annotation' and record[ 'file_exists' ] == 'no' )

    total_missing = proteome_missing + genome_missing + gff_missing

    with open( summary_path, 'w' ) as output_summary:
        output = "GIGANTIC Source Data Validation Summary\n"
        output += "=" * 60 + "\n"
        output += f"Timestamp: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}\n"
        output += f"Manifest: {manifest_path}\n"
        output += "=" * 60 + "\n\n"

        output += f"Species in manifest: {species_count}\n\n"

        output += "Data availability:\n"
        output += f"  T1 proteomes:     {proteome_found} found, {proteome_na} not listed, {proteome_missing} MISSING\n"
        output += f"  Genomes:          {genome_found} found, {genome_na} not listed, {genome_missing} MISSING\n"
        output += f"  Gene annotations: {gff_found} found, {gff_na} not listed, {gff_missing} MISSING\n\n"

        if total_missing > 0:
            output += f"WARNING: {total_missing} listed files could not be found!\n"
            output += "Missing files:\n"

            for record in validation_records:
                if record[ 'file_exists' ] == 'no':
                    output += f"  - {record[ 'genus_species' ]} ({record[ 'data_type' ]}): {record[ 'path' ]}\n"

            output += "\n"
        else:
            output += "All listed files validated successfully.\n\n"

        output += "=" * 60 + "\n"
        output += "VALIDATION " + ( "PASSED" if total_missing == 0 else "FAILED" ) + "\n"
        output += "=" * 60 + "\n"
        output_summary.write( output )

    print( f"Validation summary: {summary_path}" )
    return summary_path, total_missing


def main():
    parser = argparse.ArgumentParser(
        description = 'Validate source data manifest and check all listed files exist'
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
        help = 'Output directory for validation report (OUTPUT_pipeline/1-output)'
    )
    parser.add_argument(
        '--workflow-dir',
        type = str,
        default = None,
        help = 'Workflow root directory for resolving relative paths in manifest'
    )
    parser.add_argument(
        '--missing-action',
        type = str,
        choices = [ 'error', 'warn' ],
        default = 'error',
        help = 'Action when source files are missing: error (abort) or warn (continue)'
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
    print( "STEP 1: Validate Source Manifest" )
    print( "=" * 60 )
    print( f"Manifest: {manifest_path}" )
    print( f"Output: {output_dir}" )
    print( f"Timestamp: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    print( "=" * 60 )
    print()

    # Validate manifest exists
    if not manifest_path.exists():
        print( f"CRITICAL ERROR: Manifest file not found: {manifest_path}" )
        sys.exit( 1 )

    # Parse manifest
    print( "Parsing manifest..." )
    entries = parse_manifest( manifest_path, workflow_dir )
    print( f"  Found {len( entries )} species entries" )
    print()

    if not entries:
        print( "CRITICAL ERROR: No entries found in manifest!" )
        sys.exit( 1 )

    # Validate all files
    print( "Validating source files..." )
    validation_records = validate_entries( entries )

    # Write outputs
    write_validation_report( validation_records, output_dir )
    summary_path, total_missing = write_validation_summary( validation_records, entries, output_dir, manifest_path )

    print()

    if total_missing > 0:
        print( f"WARNING: {total_missing} listed files are missing!" )
        if arguments.missing_action == 'error':
            print( "CRITICAL ERROR: Aborting due to missing files." )
            print( "Use --missing-action warn to continue anyway." )
            sys.exit( 1 )
        else:
            print( "Continuing with warnings (--missing-action warn)" )
    else:
        print( "All listed files validated successfully." )

    print()
    print( "=" * 60 )
    print( "VALIDATION COMPLETE" )
    print( "=" * 60 )


if __name__ == '__main__':
    main()
