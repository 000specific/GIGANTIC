#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Filter per-species self-BLAST hits by stringent e-value
# Human: Eric Edsinger

"""
GIGANTIC hotspots BLOCK_identify_hotspots - Script 002: Filter BLAST by e-value

Purpose:
    Reads a per-species self-BLAST report (outfmt 6 from BLOCK_self_blast)
    and keeps only hits at or below the configured e-value threshold (paper
    default 1e-60). Drops self-vs-self diagonal hits (query == subject).

    Mirrors the filter logic of GIGANTIC_0
    hotspots-002-python-parse-blast-reports-for-within-species-homologs.py
    but operates per-species and emits a compact filtered TSV consumed by
    script 003 (identify_hotspots).

Inputs (CLI):
    --self-blast-report   Path to <Genus_species>-self_blast.tsv
    --genus-species       Species name (Genus_species format)
    --evalue-threshold    Cutoff (default 1e-60). Hit kept if e-value <= cutoff.
    --output-dir          Output directory (typically 2-output)

Outputs (in --output-dir):
    2_ai-filtered_hits-<Genus_species>.tsv
        Per-row: Query_ID, Subject_ID, Evalue
        Self-hits and weak hits already dropped.

    2_ai-filter_summary-<Genus_species>.tsv
        Single-row summary: hits read, hits kept, hits dropped, self-hits dropped.

    2_ai-log-filter_blast_by_evalue-<Genus_species>.log

Failure mode:
    Exits 1 (fail-fast) if input is missing, e-value is unparseable, or any
    blast row is malformed (<12 outfmt 6 fields).
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path, genus_species: str ) -> logging.Logger:
    logger = logging.getLogger( f'filter_blast_{genus_species}' )
    logger.setLevel( logging.INFO )
    log_file = output_dir / f'2_ai-log-filter_blast_by_evalue-{genus_species}.log'
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


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--self-blast-report', required = True, type = Path )
    parser.add_argument( '--genus-species', required = True )
    parser.add_argument( '--evalue-threshold', default = '1e-60' )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir, args.genus_species )

    logger.info( '=' * 72 )
    logger.info( f'GIGANTIC hotspots BLOCK_identify_hotspots - Script 002: Filter BLAST ({args.genus_species})' )
    logger.info( '=' * 72 )
    logger.info( f'Self-BLAST report:  {args.self_blast_report}' )
    logger.info( f'E-value threshold:  {args.evalue_threshold}' )
    logger.info( f'Output dir:         {args.output_dir}' )

    if not args.self_blast_report.is_file():
        logger.error( f'CRITICAL ERROR: Self-BLAST report not found: {args.self_blast_report}' )
        return 1

    try:
        evalue_threshold = float( args.evalue_threshold )
    except ValueError:
        logger.error( f'CRITICAL ERROR: --evalue-threshold not a number: {args.evalue_threshold}' )
        return 1

    hits_read = 0
    hits_kept = 0
    hits_dropped_evalue = 0
    self_hits_dropped = 0

    filtered_path = args.output_dir / f'2_ai-filtered_hits-{args.genus_species}.tsv'

    output = 'Query_ID (full GIGANTIC FASTA header of query gene)\t'
    output += 'Subject_ID (full GIGANTIC FASTA header of subject gene)\t'
    output += 'Evalue (BLAST e-value reported for this query subject hit)\n'

    # qseqid\tsseqid\tpident\tlength\tmismatch\tgapopen\tqstart\tqend\tsstart\tsend\tevalue\tbitscore
    # g_g1-t_..-p_..-n_..\tg_g2-t_..-p_..-n_..\t99.5\t300\t0\t0\t1\t300\t1\t300\t1e-200\t650
    with open( args.self_blast_report, 'r' ) as input_blast:
        for line in input_blast:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if len( parts ) < 12:
                logger.error( f'CRITICAL ERROR: Malformed outfmt 6 row (<12 fields): {line[:120]}' )
                return 1
            hits_read += 1

            query_id = parts[ 0 ]
            subject_id = parts[ 1 ]
            evalue_str = parts[ 10 ]

            # Drop diagonal self-hits — they don't represent paralogy
            if query_id == subject_id:
                self_hits_dropped += 1
                continue

            try:
                evalue_value = float( evalue_str )
            except ValueError:
                logger.error( f'CRITICAL ERROR: Unparseable e-value "{evalue_str}" in row: {line[:120]}' )
                return 1

            # Match GIGANTIC_0 logic: keep if evalue == 0 OR evalue <= threshold
            if evalue_value == 0.0 or evalue_value <= evalue_threshold:
                output += query_id + '\t' + subject_id + '\t' + evalue_str + '\n'
                hits_kept += 1
            else:
                hits_dropped_evalue += 1

    with open( filtered_path, 'w' ) as output_filtered:
        output_filtered.write( output )

    logger.info( f'  Read:                {hits_read} hit lines' )
    logger.info( f'  Kept:                {hits_kept}' )
    logger.info( f'  Dropped (evalue):    {hits_dropped_evalue}' )
    logger.info( f'  Dropped (self):      {self_hits_dropped}' )
    logger.info( f'  Wrote {filtered_path.name}' )

    summary_path = args.output_dir / f'2_ai-filter_summary-{args.genus_species}.tsv'
    summary_output = 'Genus_Species (species name in Genus_species format)\t'
    summary_output += 'Hits_Read (total BLAST hit lines read from self-BLAST report)\t'
    summary_output += 'Hits_Kept (hits at or below e-value threshold and not self-vs-self)\t'
    summary_output += 'Hits_Dropped_Evalue (hits weaker than threshold)\t'
    summary_output += 'Self_Hits_Dropped (diagonal hits where query equals subject)\t'
    summary_output += 'Evalue_Threshold (cutoff applied)\n'
    summary_output += args.genus_species + '\t' + str( hits_read ) + '\t' + str( hits_kept ) + '\t' + str( hits_dropped_evalue ) + '\t' + str( self_hits_dropped ) + '\t' + args.evalue_threshold + '\n'
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( summary_output )
    logger.info( f'  Wrote {summary_path.name}' )

    logger.info( 'Filter complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
