#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 22 | Purpose: Filter proteome FASTAs - drop records whose header line exceeds the filesystem-safe length so SignalP6's per-protein output filenames stay under 255 bytes
# Human: Eric Edsinger

"""
000_ai-python-filter_proteome_long_headers.py

For each species in the input proteome manifest, copy the proteome FASTA
into a local `filtered_proteomes/` subdirectory of the output dir, dropping
any FASTA record whose header line (including the leading '>') exceeds
--max-header-length characters. Writes a new manifest pointing at the
filtered local copies with absolute paths.

Why:
    SignalP6 writes per-protein output files of the form
        `output_<protein_id>_plot.txt`
    Linux file names are capped at 255 bytes. With '>' stripped and the
    'output_' (7 chars) and '_plot.txt' (9 chars) wrappers, any FASTA
    header line longer than ~239 chars produces a SignalP6 filename over
    the limit, triggering `OSError: [Errno 36] File name too long` and
    failing the whole pipeline.

    Some species70 proteomes contain EvidentialGene multi-locus
    concatenated identifiers from upstream genomesDB processing (e.g.,
    Sphaeroforma_arctica: 272 records with headers up to 299 chars).
    Removing those records before SignalP avoids the filename limit.

    The dropped records are documented in the log so downstream analysis
    can audit what was excluded.
"""

import argparse
import logging
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Filter proteome FASTAs - drop records with FASTA header lines longer than --max-header-length."
    )
    parser.add_argument(
        "--input-manifest",
        required = True,
        help = "Path to input proteome manifest TSV (columns: species_name, proteome_path, phyloname)",
    )
    parser.add_argument(
        "--output-dir",
        required = True,
        help = "Directory where filtered_proteomes/ subdir, filtered manifest, and log are written",
    )
    parser.add_argument(
        "--max-header-length",
        type = int,
        default = 253,
        help = "Maximum allowed FASTA header line length in characters, including '>'; records exceeding this are dropped (default: 253)",
    )
    return parser.parse_args()


def filter_one_proteome( input_proteome_path, output_proteome_path, max_header_length, phyloname, logger ):
    """Stream-copy a FASTA, dropping records whose header line exceeds max_header_length."""
    kept_records = 0
    dropped_records = 0
    dropped_headers = []

    input_fasta = open( input_proteome_path, "r" )
    output_fasta = open( output_proteome_path, "w" )

    write_current_record = False
    for line in input_fasta:
        if line.startswith( ">" ):
            # Header line - decide whether to keep this record
            header_length = len( line.rstrip( "\n" ) )
            if header_length <= max_header_length:
                write_current_record = True
                kept_records += 1
                output_fasta.write( line )
            else:
                write_current_record = False
                dropped_records += 1
                dropped_headers.append( ( header_length, line.rstrip( "\n" ) ) )
        else:
            # Sequence line - write only if we are keeping the current record
            if write_current_record:
                output_fasta.write( line )

    input_fasta.close()
    output_fasta.close()

    logger.info( f"{phyloname}: kept={kept_records} dropped={dropped_records}" )
    for ( header_length, header_line ) in dropped_headers:
        truncated = header_line if len( header_line ) <= 120 else header_line[ :120 ] + "..."
        logger.info( f"  dropped ({header_length} chars): {truncated}" )

    return kept_records, dropped_records


def main():
    args = parse_args()

    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )
    filtered_proteomes_dir = output_dir / "filtered_proteomes"
    filtered_proteomes_dir.mkdir( parents = True, exist_ok = True )

    log_path = output_dir / "0_ai-log-filter_proteome_long_headers.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [
            logging.FileHandler( log_path ),
            logging.StreamHandler( sys.stdout ),
        ],
    )
    logger = logging.getLogger( __name__ )

    logger.info( "=" * 70 )
    logger.info( "Script 000: Filter proteome long headers" )
    logger.info( "=" * 70 )
    logger.info( f"Input manifest: {args.input_manifest}" )
    logger.info( f"Output dir: {output_dir}" )
    logger.info( f"Max header length: {args.max_header_length} chars" )
    logger.info( "" )

    # species_name	proteome_path	phyloname
    # Parvularia_atlantis	/blue/.../Holomycota_..._Parvularia_atlantis-T1-proteome.aa	Holomycota_..._Parvularia_atlantis
    input_manifest = open( args.input_manifest, "r" )

    # Filtered manifest written next to the filtered FASTAs
    filtered_manifest_path = output_dir / "0_ai-filtered_proteome_manifest.tsv"
    output_manifest = open( filtered_manifest_path, "w" )

    total_kept = 0
    total_dropped = 0
    species_count = 0

    is_header_row = True
    for line in input_manifest:
        line = line.rstrip( "\n" )
        if not line or line.startswith( "#" ):
            continue
        parts = line.split( "\t" )
        if is_header_row:
            # Pass header row through unchanged so column names match downstream readers
            output = "\t".join( parts ) + "\n"
            output_manifest.write( output )
            is_header_row = False
            continue
        species_name = parts[ 0 ]
        original_proteome_path = parts[ 1 ]
        phyloname = parts[ 2 ]

        filtered_proteome_path = filtered_proteomes_dir / f"{phyloname}-T1-proteome-filtered.aa"
        kept_records, dropped_records = filter_one_proteome(
            original_proteome_path,
            filtered_proteome_path,
            args.max_header_length,
            phyloname,
            logger,
        )

        total_kept += kept_records
        total_dropped += dropped_records
        species_count += 1

        # Filtered manifest entry uses ABSOLUTE path so downstream NextFlow
        # processes (validate, run_signalp) can read the file directly.
        output = species_name + "\t" + str( filtered_proteome_path.resolve() ) + "\t" + phyloname + "\n"
        output_manifest.write( output )

    input_manifest.close()
    output_manifest.close()

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Species processed: {species_count}" )
    logger.info( f"Total records kept: {total_kept}" )
    logger.info( f"Total records dropped: {total_dropped}" )
    logger.info( f"Filtered manifest: {filtered_manifest_path}" )
    logger.info( f"Filtered proteomes dir: {filtered_proteomes_dir}" )

    if species_count == 0:
        logger.error( "CRITICAL ERROR: no species processed from input manifest" )
        logger.error( f"Check the input manifest format at: {args.input_manifest}" )
        sys.exit( 1 )


if __name__ == "__main__":
    main()
