#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Identify top self and non-self hits from DIAMOND results
# Human: Eric Edsinger

"""
005_ai-python-identify_top_hits.py

For each query protein in the combined DIAMOND results, identifies:
- Top 10 NCBI nr hits (with sequence IDs and headers)
- Top non-self hit (first hit where query != subject sequence)
- Top self-hit (first hit where query == subject sequence)

Uses full sequences (full_qseq, full_sseq) to distinguish self from non-self.

Input:
    Combined DIAMOND results for one species (from script 004)
    15-column format: qseqid sseqid pident length mismatch gapopen
                      qstart qend sstart send evalue bitscore
                      stitle full_qseq full_sseq

Output:
    {species}_top_hits.tsv (per-protein top hit analysis)
    {species}_statistics.tsv (species-level summary statistics)

Usage:
    python3 005_ai-python-identify_top_hits.py \\
        --input-file OUTPUT_pipeline/4-output/combined_Homo_sapiens.tsv \\
        --output-dir OUTPUT_pipeline/5-output \\
        --species-name Homo_sapiens
"""

import argparse
import csv
import logging
import sys
from pathlib import Path


def setup_logging( output_dir ):
    """Configure logging to both console and file."""

    log_file = Path( output_dir ) / "5_ai-log-identify_top_hits.log"

    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s | %(levelname)s | %(message)s",
        handlers = [
            logging.FileHandler( log_file ),
            logging.StreamHandler( sys.stdout )
        ]
    )

    return logging.getLogger( __name__ )


def main():

    parser = argparse.ArgumentParser( description = "Identify top self/non-self hits from DIAMOND results" )
    parser.add_argument( "--input-file", required = True, help = "Combined DIAMOND results file" )
    parser.add_argument( "--output-dir", required = True, help = "Output directory" )
    parser.add_argument( "--species-name", required = True, help = "Species name" )
    arguments = parser.parse_args()

    input_file_path = Path( arguments.input_file )
    output_directory = Path( arguments.output_dir )
    species_name = arguments.species_name
    output_directory.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_directory )
    logger.info( "=" * 72 )
    logger.info( f"Script 005: Identify Top Hits - {species_name}" )
    logger.info( "=" * 72 )
    logger.info( f"Input: {input_file_path}" )

    # ========================================================================
    # Validate input
    # ========================================================================

    if not input_file_path.exists():
        logger.error( f"CRITICAL ERROR: Input file not found: {input_file_path}" )
        sys.exit( 1 )

    if input_file_path.stat().st_size == 0:
        logger.error( f"CRITICAL ERROR: Input file is empty: {input_file_path}" )
        sys.exit( 1 )

    # ========================================================================
    # Read DIAMOND results and group by query
    # ========================================================================
    # Dictionary: query_id -> list of hit tuples
    # Each hit tuple: (subject_id, evalue, bitscore, stitle, query_sequence, subject_sequence)

    queries___hits = {}

    # qseqid	sseqid	pident	length	mismatch	gapopen	qstart	qend	sstart	send	evalue	bitscore	stitle	full_qseq	full_sseq
    # g_GENE001-t_T1-p_P1-n_Metazoa_...	XP_012345.1	98.5	500	7	0	1	500	1	500	1e-200	800	hypothetical protein [Homo sapiens]	MSTK...	MSTK...
    with open( input_file_path, 'r' ) as input_diamond_results:
        for line in input_diamond_results:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            # Ensure we have all 15 columns
            if len( parts ) < 15:
                continue

            query_id = parts[ 0 ]
            subject_id = parts[ 1 ]
            evalue = parts[ 10 ]
            bitscore = parts[ 11 ]
            stitle = parts[ 12 ]
            query_sequence = parts[ 13 ]
            subject_sequence = parts[ 14 ]

            if query_id not in queries___hits:
                queries___hits[ query_id ] = []

            queries___hits[ query_id ].append( (
                subject_id,
                evalue,
                bitscore,
                stitle,
                query_sequence,
                subject_sequence
            ) )

    total_queries = len( queries___hits )
    logger.info( f"Unique query sequences: {total_queries}" )

    # ========================================================================
    # Identify top hits for each query
    # ========================================================================

    # Statistics counters
    self_hits_found = 0
    non_self_hits_found = 0
    queries_with_no_non_self_hits = 0
    queries_with_no_self_hits = 0

    # Output file paths
    output_top_hits_path = output_directory / f"{species_name}_top_hits.tsv"
    output_statistics_path = output_directory / f"{species_name}_statistics.tsv"

    # Use CSV writer to handle potential newlines in sequences
    with open( output_top_hits_path, 'w', newline = '', encoding = 'utf-8' ) as output_top_hits:

        writer = csv.writer( output_top_hits, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Write header
        writer.writerow( [
            "Query_Sequence_ID (query protein identifier from species proteome)",
            "Top_10_Hit_IDs (comma delimited list of top 10 NCBI nr hit sequence IDs)",
            "Top_10_Hit_Headers (comma delimited list of top 10 NCBI nr hit descriptions)",
            "Top_Non_Self_Hit_ID (sequence ID of first hit with different sequence)",
            "Top_Non_Self_Hit_Header (NCBI description of top non-self hit)",
            "Top_Non_Self_Hit_Header_And_Sequence (header newline sequence for top non-self hit)",
            "Top_Self_Hit_ID (sequence ID of first hit with identical sequence)",
            "Top_Self_Hit_Header (NCBI description of top self hit)",
            "Top_Self_Hit_Header_And_Sequence (header newline sequence for top self hit)"
        ] )

        for query_id in sorted( queries___hits.keys() ):

            hits = queries___hits[ query_id ]

            # Take top 10 hits (already sorted by DIAMOND by bitscore)
            hits_top_10 = hits[ :10 ]

            # Collect top 10 IDs and headers
            top_10_ids = [ hit[ 0 ] for hit in hits_top_10 ]
            top_10_headers = [ hit[ 3 ] for hit in hits_top_10 ]

            # Find top non-self hit and top self-hit
            top_non_self_hit_id = ""
            top_non_self_hit_header = ""
            top_non_self_hit_header_and_sequence = ""
            top_self_hit_id = ""
            top_self_hit_header = ""
            top_self_hit_header_and_sequence = ""

            found_non_self = False
            found_self = False

            for subject_id, evalue, bitscore, stitle, query_sequence, subject_sequence in hits_top_10:

                if query_sequence == subject_sequence:
                    # Self-hit: query and subject sequences are identical
                    if not found_self:
                        top_self_hit_id = subject_id
                        top_self_hit_header = stitle
                        top_self_hit_header_and_sequence = f">{subject_id} {stitle}\n{subject_sequence}"
                        found_self = True
                        self_hits_found += 1
                else:
                    # Non-self hit: sequences differ
                    if not found_non_self:
                        top_non_self_hit_id = subject_id
                        top_non_self_hit_header = stitle
                        top_non_self_hit_header_and_sequence = f">{subject_id} {stitle}\n{subject_sequence}"
                        found_non_self = True
                        non_self_hits_found += 1

                # Stop early if both found
                if found_self and found_non_self:
                    break

            if not found_non_self:
                queries_with_no_non_self_hits += 1
            if not found_self:
                queries_with_no_self_hits += 1

            # Write row
            writer.writerow( [
                query_id,
                ", ".join( top_10_ids ),
                ", ".join( top_10_headers ),
                top_non_self_hit_id,
                top_non_self_hit_header,
                top_non_self_hit_header_and_sequence,
                top_self_hit_id,
                top_self_hit_header,
                top_self_hit_header_and_sequence
            ] )

    # ========================================================================
    # Write statistics
    # ========================================================================

    with open( output_statistics_path, 'w' ) as output_statistics:

        output = "Species_Name (genus species identifier)\t"
        output += "Total_Queries_Processed (total number of query sequences processed)\t"
        output += "Self_Hits_Found (total number of self hits identified across all queries)\t"
        output += "Non_Self_Hits_Found (total number of non-self hits identified across all queries)\t"
        output += "Queries_With_No_Non_Self_Hits (number of queries where all top 10 hits were self hits)\t"
        output += "Queries_With_No_Self_Hits (number of queries where no top 10 hit had identical sequence)\n"
        output_statistics.write( output )

        output = species_name + '\t'
        output += str( total_queries ) + '\t'
        output += str( self_hits_found ) + '\t'
        output += str( non_self_hits_found ) + '\t'
        output += str( queries_with_no_non_self_hits ) + '\t'
        output += str( queries_with_no_self_hits ) + '\n'
        output_statistics.write( output )

    # ========================================================================
    # Summary
    # ========================================================================

    logger.info( "" )
    logger.info( f"Results for {species_name}:" )
    logger.info( f"  Total queries: {total_queries}" )
    logger.info( f"  Self hits found: {self_hits_found}" )
    logger.info( f"  Non-self hits found: {non_self_hits_found}" )
    logger.info( f"  Queries with no non-self hits: {queries_with_no_non_self_hits}" )
    logger.info( f"  Queries with no self hits: {queries_with_no_self_hits}" )
    logger.info( f"  Top hits file: {output_top_hits_path}" )
    logger.info( f"  Statistics file: {output_statistics_path}" )
    logger.info( "Script 005 complete." )


if __name__ == "__main__":
    main()
