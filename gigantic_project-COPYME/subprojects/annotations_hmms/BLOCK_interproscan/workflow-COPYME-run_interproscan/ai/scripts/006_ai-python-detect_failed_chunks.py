#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Detect chunks that did not produce InterProScan results and emit a failed-chunks manifest for follow-up runs
# Human: Eric Edsinger

"""
006_ai-python-detect_failed_chunks.py

Compares the set of EXPECTED chunks (FASTA files produced by chunk_proteomes,
step 2) against the set of SUCCESSFUL chunks (interproscan TSV files produced
by run_interproscan, step 3) and writes a manifest of the chunks that did NOT
produce results.

This is the gap-detection complement to errorStrategy='ignore' on the
run_interproscan process. With ignore semantics, individual chunk failures
do NOT kill the pipeline -- they just produce no output. This script
identifies those gaps so the user can drive a follow-up RUN_N targeting
just the failed chunks.

Input directories ( from publishDir of upstream processes ):
    --chunks-dir   : OUTPUT_pipeline/2-output/  contains <phyloname>_chunk_NNN.fasta
    --results-dir  : OUTPUT_pipeline/3-output/  contains <phyloname>_chunk_NNN_interproscan.tsv
    --output-dir   : where to write the failed-chunks manifest

Output ( tab-separated, with self-documenting header per GIGANTIC convention ):
    6_ai-failed_chunks.tsv
        Phyloname (GIGANTIC phylogenetic name of the species)
        Chunk_Basename (chunk file basename without .fasta extension)
        Chunk_Fasta_Path (absolute path to the expected chunk FASTA)
        Expected_Interproscan_Output (the basename run_interproscan would have produced)

    6_ai-log-detect_failed_chunks.log
        Run summary: expected/successful/failed counts.

Exit codes:
    0 always ( ignore-semantics design: gaps are reported, not raised as errors )

Usage ( standalone or as a NextFlow process ):
    python3 006_ai-python-detect_failed_chunks.py \\
        --chunks-dir  OUTPUT_pipeline/2-output \\
        --results-dir OUTPUT_pipeline/3-output \\
        --output-dir  OUTPUT_pipeline/6-output
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_log_path ):
    logger = logging.getLogger( '006_detect_failed_chunks' )
    logger.setLevel( logging.INFO )
    if logger.handlers:
        for h in list( logger.handlers ):
            logger.removeHandler( h )
    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler = logging.FileHandler( output_log_path )
    file_handler.setFormatter( formatter )
    logger.addHandler( file_handler )
    stream_handler = logging.StreamHandler( sys.stdout )
    stream_handler.setFormatter( formatter )
    logger.addHandler( stream_handler )
    return logger


def parse_arguments():
    parser = argparse.ArgumentParser( description = 'Detect chunks that did not produce InterProScan output and emit a manifest for follow-up runs.' )
    parser.add_argument( '--chunks-dir',  required = True, help = 'Directory containing expected <phyloname>_chunk_NNN.fasta files ( OUTPUT_pipeline/2-output ).' )
    parser.add_argument( '--results-dir', required = True, help = 'Directory containing successful <phyloname>_chunk_NNN_interproscan.tsv files ( OUTPUT_pipeline/3-output ).' )
    parser.add_argument( '--output-dir',  required = True, help = 'Directory to write failed_chunks.tsv and the log.' )
    return parser.parse_args()


def phyloname_from_chunk_basename( chunk_basename ):
    # chunk_basename like "Metazoa_..._chunk_017"
    # phyloname is everything before "_chunk_NNN"
    parts_chunk_basename = chunk_basename.rsplit( '_chunk_', 1 )
    if len( parts_chunk_basename ) != 2:
        return chunk_basename
    return parts_chunk_basename[ 0 ]


def main():
    args = parse_arguments()

    input_chunks_dir  = Path( args.chunks_dir ).resolve()
    input_results_dir = Path( args.results_dir ).resolve()
    output_dir        = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    output_log_path      = output_dir / '6_ai-log-detect_failed_chunks.log'
    output_manifest_path = output_dir / '6_ai-failed_chunks.tsv'

    logger = setup_logging( output_log_path )
    logger.info( '=== detect_failed_chunks starting ===' )
    logger.info( f'chunks-dir : {input_chunks_dir}' )
    logger.info( f'results-dir: {input_results_dir}' )
    logger.info( f'output-dir : {output_dir}' )

    # Collect expected chunk basenames ( from chunk_proteomes output, step 2 ):
    #   <phyloname>_chunk_NNN.fasta  ->  basename = <phyloname>_chunk_NNN
    expected_chunk_basenames___fasta_paths = {}
    for fasta_path in sorted( input_chunks_dir.glob( '*_chunk_*.fasta' ) ):
        basename = fasta_path.stem  # drops .fasta
        expected_chunk_basenames___fasta_paths[ basename ] = fasta_path

    # Collect successful chunk basenames ( from run_interproscan output, step 3 ):
    #   <phyloname>_chunk_NNN_interproscan.tsv  ->  strip "_interproscan" suffix
    successful_chunk_basenames = set()
    for tsv_path in sorted( input_results_dir.glob( '*_chunk_*_interproscan.tsv' ) ):
        tsv_stem = tsv_path.stem  # e.g., "..._chunk_017_interproscan"
        if tsv_stem.endswith( '_interproscan' ):
            chunk_basename = tsv_stem[ : -len( '_interproscan' ) ]
            successful_chunk_basenames.add( chunk_basename )

    expected_count   = len( expected_chunk_basenames___fasta_paths )
    successful_count = len( successful_chunk_basenames )

    failed_chunk_basenames = sorted(
        set( expected_chunk_basenames___fasta_paths ) - successful_chunk_basenames
    )
    failed_count = len( failed_chunk_basenames )

    logger.info( f'expected chunks   : {expected_count}' )
    logger.info( f'successful chunks : {successful_count}' )
    logger.info( f'failed chunks     : {failed_count}' )

    # Per-species failure summary
    failures_by_phyloname = {}
    for basename in failed_chunk_basenames:
        ph = phyloname_from_chunk_basename( basename )
        failures_by_phyloname.setdefault( ph, [] ).append( basename )
    for ph in sorted( failures_by_phyloname ):
        n = len( failures_by_phyloname[ ph ] )
        logger.info( f'  {n} failed for phyloname={ph}' )

    # Write self-documenting TSV manifest
    header = (
        'Phyloname (GIGANTIC phylogenetic name of the species)'
        + '\t' + 'Chunk_Basename (chunk file basename without .fasta extension)'
        + '\t' + 'Chunk_Fasta_Path (absolute path to the expected chunk FASTA)'
        + '\t' + 'Expected_Interproscan_Output (basename run_interproscan would have produced)'
        + '\n'
    )
    with open( output_manifest_path, 'w' ) as output_manifest:
        output_manifest.write( header )
        for basename in failed_chunk_basenames:
            phyloname    = phyloname_from_chunk_basename( basename )
            fasta_path   = expected_chunk_basenames___fasta_paths[ basename ]
            expected_tsv = basename + '_interproscan.tsv'
            output = (
                phyloname + '\t' + basename + '\t' + str( fasta_path ) + '\t' + expected_tsv + '\n'
            )
            output_manifest.write( output )

    logger.info( f'wrote: {output_manifest_path}' )
    logger.info( '=== detect_failed_chunks done ===' )

    # Always exit 0 ( ignore-semantics ): the workflow is allowed to complete
    # even when chunks failed. The manifest is the user-visible signal.
    sys.exit( 0 )


if __name__ == '__main__':
    main()
