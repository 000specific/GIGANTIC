#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Verify and concatenate per-chunk blastp reports into per-species self-BLAST reports
# Human: Eric Edsinger

"""
GIGANTIC hotspots BLOCK_self_blast - Script 004: Concatenate Chunk Reports

Purpose:
    After the SLURM array fan-out completes, this script:
      (a) verifies every chunk in the chunk_manifest produced its expected
          report file (fail-fast on any missing chunk);
      (b) concatenates per-chunk reports into one per-species self-BLAST
          report;
      (c) emits a per-species summary (chunk count, total hit lines).

    The per-species reports are the deliverable consumed downstream by
    BLOCK_identify_hotspots.

Inputs (CLI):
    --chunk-manifest        Path to 2_ai-chunk_manifest.tsv from script 002
    --chunk-reports-dir     Directory containing the per-chunk blastp .tsv
                            reports (one .tsv per chunk; filenames must
                            match Expected_Report_Filename in the manifest)
    --output-dir            Output directory (typically 4-output)

Outputs (in --output-dir):
    self_blast_reports/<Genus_species>-self_blast.tsv
        Per-species concatenated blastp tabular report (outfmt 6).

    4_ai-self_blast_summary.tsv
        Per-row: Genus_Species, Chunk_Count_Expected, Chunk_Count_Found,
                 Hit_Line_Count, Status

    4_ai-log-concatenate_chunk_reports.log

Failure mode:
    Exits 1 (fail-fast) when ANY expected chunk report is missing or any
    chunk report contains malformed lines. The fan-out either produced all
    reports or the pipeline fails — no silent partial results.
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( 'concatenate_chunk_reports' )
    logger.setLevel( logging.INFO )

    log_file = output_dir / '4_ai-log-concatenate_chunk_reports.log'
    file_handler = logging.FileHandler( log_file, mode = 'w' )
    file_handler.setLevel( logging.INFO )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


def read_chunk_manifest( manifest_path: Path, logger: logging.Logger ) -> dict:
    """Read the chunk manifest from script 002.

    Returns: genus_species___chunk_records dict where each value is a list
    of ( chunk_index, expected_report_filename ) tuples ordered by chunk
    index.
    """
    genus_species___chunk_records = {}

    # Genus_Species (...)\tChunk_Index (...)\tChunk_Path (...)\tBlast_Db_Path (...)\tExpected_Report_Filename (...)
    # Homo_sapiens\t0\t/abs/path/Homo_sapiens_chunk_0000.aa\t/abs/db/...aa\tself_blast-Homo_sapiens_chunk_0000.tsv
    with open( manifest_path, 'r' ) as input_manifest:
        header_seen = False
        for line in input_manifest:
            line = line.strip()
            if not line:
                continue
            if not header_seen:
                header_seen = True
                continue
            parts = line.split( '\t' )
            if len( parts ) < 5:
                logger.warning( f'  Skipping malformed manifest row: {line}' )
                continue
            genus_species = parts[ 0 ]
            chunk_index = int( parts[ 1 ] )
            report_filename = parts[ 4 ]
            if genus_species not in genus_species___chunk_records:
                genus_species___chunk_records[ genus_species ] = []
            genus_species___chunk_records[ genus_species ].append( ( chunk_index, report_filename ) )

    # Sort each species' chunk list by index for deterministic concatenation
    for genus_species in genus_species___chunk_records:
        genus_species___chunk_records[ genus_species ].sort( key = lambda r: r[ 0 ] )

    total_chunks = sum( len( v ) for v in genus_species___chunk_records.values() )
    logger.info( f'  Manifest covers {len( genus_species___chunk_records )} species and {total_chunks} chunks' )

    return genus_species___chunk_records


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--chunk-manifest', required = True, type = Path )
    parser.add_argument( '--chunk-reports-dir', required = True, type = Path )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir )

    logger.info( '=' * 72 )
    logger.info( 'GIGANTIC hotspots BLOCK_self_blast - Script 004: Concatenate Chunk Reports' )
    logger.info( '=' * 72 )
    logger.info( f'Chunk manifest:       {args.chunk_manifest}' )
    logger.info( f'Chunk reports dir:    {args.chunk_reports_dir}' )
    logger.info( f'Output dir:           {args.output_dir}' )
    logger.info( '' )

    if not args.chunk_manifest.is_file():
        logger.error( f'CRITICAL ERROR: Chunk manifest not found: {args.chunk_manifest}' )
        return 1
    if not args.chunk_reports_dir.is_dir():
        logger.error( f'CRITICAL ERROR: Chunk reports directory not found: {args.chunk_reports_dir}' )
        return 1

    genus_species___chunk_records = read_chunk_manifest( args.chunk_manifest, logger )
    if not genus_species___chunk_records:
        logger.error( 'CRITICAL ERROR: Chunk manifest contains no species rows.' )
        return 1

    self_blast_reports_dir = args.output_dir / 'self_blast_reports'
    self_blast_reports_dir.mkdir( parents = True, exist_ok = True )

    summary_rows = []
    missing_chunks = []     # ( genus_species, chunk_index, report_filename )
    logger.info( 'Concatenating per-chunk reports per species...' )

    for genus_species in sorted( genus_species___chunk_records.keys() ):
        chunk_records = genus_species___chunk_records[ genus_species ]
        chunk_count_expected = len( chunk_records )

        per_species_report = self_blast_reports_dir / f'{genus_species}-self_blast.tsv'
        chunks_found = 0
        hit_line_count = 0

        with open( per_species_report, 'w' ) as output_per_species:
            for chunk_index, report_filename in chunk_records:
                report_path = args.chunk_reports_dir / report_filename
                if not report_path.is_file():
                    missing_chunks.append( ( genus_species, chunk_index, report_filename ) )
                    continue

                chunks_found += 1
                # Stream-copy the chunk report into the per-species report.
                # blastp outfmt 6 has no header; concatenation is trivial.
                with open( report_path, 'r' ) as input_chunk_report:
                    for line in input_chunk_report:
                        line = line.rstrip( '\n' )
                        if not line:
                            continue
                        # Sanity: outfmt 6 should be tab-separated with >=12 fields.
                        # Reject obvious malformations before they corrupt
                        # downstream parsing (CLAUDE.md zero-tolerance rule).
                        parts = line.split( '\t' )
                        if len( parts ) < 12:
                            logger.error( f'CRITICAL ERROR: Malformed blastp line in {report_path.name}: {line[ :120 ]}' )
                            logger.error( f'Expected outfmt 6 with >=12 tab-separated fields; got {len( parts )}.' )
                            return 1
                        output_per_species.write( line + '\n' )
                        hit_line_count += 1

        status = 'COMPLETE' if chunks_found == chunk_count_expected else 'MISSING_CHUNKS'
        summary_rows.append( ( genus_species, chunk_count_expected, chunks_found, hit_line_count, status ) )
        logger.info( f'  {genus_species}: {chunks_found}/{chunk_count_expected} chunks, {hit_line_count} hit lines  [{status}]' )

    if missing_chunks:
        logger.error( '' )
        logger.error( 'CRITICAL ERROR: Missing chunk reports detected.' )
        logger.error( f'  {len( missing_chunks )} chunk report file(s) missing across the fan-out.' )
        for genus_species, chunk_index, report_filename in missing_chunks[ :20 ]:
            logger.error( f'    {genus_species} chunk {chunk_index}: {report_filename}' )
        if len( missing_chunks ) > 20:
            logger.error( f'    ... and {len( missing_chunks ) - 20} more' )
        logger.error( 'Fix: Check fan-out task logs for failed blastp invocations and rerun.' )
        return 1

    # ---- Write summary ----
    summary_path = args.output_dir / '4_ai-self_blast_summary.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Chunk_Count_Expected (number of chunks defined in chunk manifest)\t'
    output += 'Chunk_Count_Found (number of chunk report files actually found)\t'
    output += 'Hit_Line_Count (total blastp hit lines in concatenated per-species report)\t'
    output += 'Status (COMPLETE if all chunks found else MISSING_CHUNKS)\n'
    for genus_species, chunk_count_expected, chunks_found, hit_line_count, status in summary_rows:
        output += genus_species + '\t' + str( chunk_count_expected ) + '\t' + str( chunks_found ) + '\t' + str( hit_line_count ) + '\t' + status + '\n'
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( output )
    logger.info( '' )
    logger.info( f'  Wrote {summary_path.name} ({len( summary_rows )} rows)' )

    logger.info( '' )
    logger.info( 'Concatenation complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
