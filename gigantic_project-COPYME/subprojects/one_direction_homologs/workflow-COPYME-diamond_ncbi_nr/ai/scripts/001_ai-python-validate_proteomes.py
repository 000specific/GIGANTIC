#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Validate proteome files and input manifest
# Human: Eric Edsinger

"""
001_ai-python-validate_proteomes.py

Validates the proteome manifest and all referenced proteome FASTA files.
Ensures files exist, are non-empty, and contain valid FASTA sequences.

Input:
    Proteome manifest TSV with columns: species_name, proteome_path, phyloname

Output:
    1_ai-validated_proteome_manifest.tsv (validated copy of manifest)

Usage:
    python3 001_ai-python-validate_proteomes.py --manifest INPUT_user/proteome_manifest.tsv --output-dir OUTPUT_pipeline/1-output
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir ):
    """Configure logging to both console and file."""

    log_file = Path( output_dir ) / "1_ai-log-validate_proteomes.log"

    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s | %(levelname)s | %(message)s",
        handlers = [
            logging.FileHandler( log_file ),
            logging.StreamHandler( sys.stdout )
        ]
    )

    return logging.getLogger( __name__ )


def validate_fasta( fasta_path, logger ):
    """Check that a file contains valid FASTA format sequences."""

    sequence_count = 0
    current_sequence_length = 0

    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()
            if not line:
                continue
            if line.startswith( '>' ):
                if sequence_count > 0 and current_sequence_length == 0:
                    logger.warning( f"  Empty sequence found before header: {line[ :50 ]}" )
                sequence_count += 1
                current_sequence_length = 0
            else:
                current_sequence_length += len( line )

    return sequence_count


def main():

    parser = argparse.ArgumentParser( description = "Validate proteome files and manifest" )
    parser.add_argument( "--manifest", required = True, help = "Path to proteome manifest TSV" )
    parser.add_argument( "--output-dir", required = True, help = "Output directory for validated manifest" )
    arguments = parser.parse_args()

    input_manifest_path = Path( arguments.manifest )
    output_directory = Path( arguments.output_dir )
    output_directory.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_directory )
    logger.info( "=" * 72 )
    logger.info( "Script 001: Validate Proteomes" )
    logger.info( "=" * 72 )
    logger.info( f"Input manifest: {input_manifest_path}" )
    logger.info( f"Output directory: {output_directory}" )

    # ========================================================================
    # Validate manifest file exists
    # ========================================================================

    if not input_manifest_path.exists():
        logger.error( f"CRITICAL ERROR: Manifest file not found: {input_manifest_path}" )
        logger.error( "Please create a proteome manifest with columns: species_name, proteome_path, phyloname" )
        sys.exit( 1 )

    # ========================================================================
    # Read and validate manifest
    # ========================================================================

    validated_entries = []
    total_sequences = 0
    errors_found = 0

    # species_name	proteome_path	phyloname
    # Homo_sapiens	../../genomesDB/output_to_input/proteomes/...aa	Metazoa_Chordata_..._Homo_sapiens
    with open( input_manifest_path, 'r' ) as input_manifest:

        header_line = None

        for line in input_manifest:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith( '#' ):
                continue

            # Capture header
            if header_line is None:
                header_line = line
                parts = line.split( '\t' )
                if len( parts ) < 2:
                    logger.error( "CRITICAL ERROR: Manifest header must have at least 2 tab-separated columns" )
                    logger.error( f"Got: {line}" )
                    sys.exit( 1 )
                logger.info( f"Manifest header: {line}" )
                continue

            # Parse data rows
            parts = line.split( '\t' )
            if len( parts ) < 2:
                logger.warning( f"Skipping malformed line (too few columns): {line[ :80 ]}" )
                errors_found += 1
                continue

            species_name = parts[ 0 ]
            proteome_path = parts[ 1 ]
            phyloname = parts[ 2 ] if len( parts ) > 2 else ""

            # Resolve proteome path (may be relative to manifest location)
            proteome_file = Path( proteome_path )
            if not proteome_file.is_absolute():
                proteome_file = input_manifest_path.parent / proteome_file

            # Check file exists
            if not proteome_file.exists():
                logger.error( f"  MISSING: {species_name} - {proteome_file}" )
                errors_found += 1
                continue

            # Check file is non-empty
            file_size = proteome_file.stat().st_size
            if file_size == 0:
                logger.error( f"  EMPTY: {species_name} - {proteome_file}" )
                errors_found += 1
                continue

            # Validate FASTA format
            sequence_count = validate_fasta( proteome_file, logger )
            if sequence_count == 0:
                logger.error( f"  NO SEQUENCES: {species_name} - {proteome_file}" )
                errors_found += 1
                continue

            total_sequences += sequence_count
            logger.info( f"  VALID: {species_name} - {sequence_count} sequences ({file_size / 1024 / 1024:.1f} MB)" )

            validated_entries.append( {
                'species_name': species_name,
                'proteome_path': str( proteome_file.resolve() ),
                'phyloname': phyloname,
                'sequence_count': sequence_count
            } )

    # ========================================================================
    # Check for critical errors
    # ========================================================================

    if len( validated_entries ) == 0:
        logger.error( "CRITICAL ERROR: No valid proteomes found!" )
        logger.error( "Check that proteome paths in the manifest are correct." )
        sys.exit( 1 )

    if errors_found > 0:
        logger.warning( f"WARNING: {errors_found} entries had errors and were skipped" )

    # ========================================================================
    # Write validated manifest
    # ========================================================================

    output_manifest_path = output_directory / "1_ai-validated_proteome_manifest.tsv"

    with open( output_manifest_path, 'w' ) as output_manifest:

        output = "Species_Name (genus species identifier)\t"
        output += "Proteome_Path (absolute path to proteome FASTA file)\t"
        output += "Phyloname (full GIGANTIC phylogenetic name)\t"
        output += "Sequence_Count (number of protein sequences in proteome)\n"
        output_manifest.write( output )

        for entry in validated_entries:
            output = entry[ 'species_name' ] + '\t'
            output += entry[ 'proteome_path' ] + '\t'
            output += entry[ 'phyloname' ] + '\t'
            output += str( entry[ 'sequence_count' ] ) + '\n'
            output_manifest.write( output )

    # ========================================================================
    # Summary
    # ========================================================================

    logger.info( "" )
    logger.info( "=" * 72 )
    logger.info( "Validation Summary" )
    logger.info( "=" * 72 )
    logger.info( f"Species validated: {len( validated_entries )}" )
    logger.info( f"Total sequences: {total_sequences}" )
    logger.info( f"Errors skipped: {errors_found}" )
    logger.info( f"Validated manifest: {output_manifest_path}" )
    logger.info( "Script 001 complete." )


if __name__ == "__main__":
    main()
