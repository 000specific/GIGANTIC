#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 31 | Purpose: Identify top self and non-self hits from DIAMOND results
# Human: Eric Edsinger

"""
005_ai-python-identify_top_hits.py

For each query protein in the combined DIAMOND results, identifies:
- Top 10 NCBI nr hits (with sequence IDs and headers)
- Top non-self hit (first hit where alignment metrics indicate different sequence)
- Top self-hit (first hit where alignment metrics indicate identical sequence)

Self-hit detection uses a STRENGTHENED PROXY based on alignment metrics:
  - pident == 100.0 (perfect percent identity)
  - mismatch == 0 (no mismatched positions)
  - gapopen == 0 (no gap openings)
  - Alignment covers >= 95% of the full query protein length

This avoids false positives from conserved domains shared between paralogs,
which might align at 100% identity over a short domain but not over the
full protein length.

The full query protein lengths are read from the proteome FASTA files.

Input:
    Combined DIAMOND results for one species (from script 004)
    13-column format: qseqid sseqid pident length mismatch gapopen
                      qstart qend sstart send evalue bitscore stitle

    Proteome FASTA file for the species (for query length lookup)

Output:
    {species}_top_hits.tsv (per-protein top hit analysis)
    {species}_statistics.tsv (species-level summary statistics)

Usage:
    python3 005_ai-python-identify_top_hits.py \\
        --input-file OUTPUT_pipeline/4-output/combined_Homo_sapiens.tsv \\
        --output-dir OUTPUT_pipeline/5-output \\
        --species-name Homo_sapiens \\
        --proteome-file /path/to/Homo_sapiens-T1-proteome.aa
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


def read_proteome_sequence_lengths( proteome_file_path, logger ):
    """Read proteome FASTA and return dictionary of sequence_id -> length.

    Handles multi-line FASTA format. Only uses the first word of the header
    as the sequence identifier (matching DIAMOND qseqid behavior).
    """

    identifiers___lengths = {}
    current_identifier = None
    current_length = 0

    with open( proteome_file_path, 'r' ) as input_proteome:
        for line in input_proteome:
            line = line.strip()
            if not line:
                continue

            if line.startswith( '>' ):
                # Save previous sequence length
                if current_identifier is not None:
                    identifiers___lengths[ current_identifier ] = current_length

                # Parse new header - use first word as identifier
                current_identifier = line[ 1: ].split()[ 0 ]
                current_length = 0
            else:
                current_length += len( line )

    # Save last sequence
    if current_identifier is not None:
        identifiers___lengths[ current_identifier ] = current_length

    logger.info( f"Read {len( identifiers___lengths )} sequence lengths from proteome" )
    return identifiers___lengths


def main():

    parser = argparse.ArgumentParser( description = "Identify top self/non-self hits from DIAMOND results" )
    parser.add_argument( "--input-file", required = True, help = "Combined DIAMOND results file" )
    parser.add_argument( "--output-dir", required = True, help = "Output directory" )
    parser.add_argument( "--species-name", required = True, help = "Species name" )
    parser.add_argument( "--proteome-file", required = True, help = "Proteome FASTA file for query length lookup" )
    arguments = parser.parse_args()

    input_file_path = Path( arguments.input_file )
    output_directory = Path( arguments.output_dir )
    species_name = arguments.species_name
    proteome_file_path = Path( arguments.proteome_file )
    output_directory.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_directory )
    logger.info( "=" * 72 )
    logger.info( f"Script 005: Identify Top Hits - {species_name}" )
    logger.info( "=" * 72 )
    logger.info( f"Input: {input_file_path}" )
    logger.info( f"Proteome: {proteome_file_path}" )

    # ========================================================================
    # Validate inputs
    # ========================================================================

    if not input_file_path.exists():
        logger.error( f"CRITICAL ERROR: Input file not found: {input_file_path}" )
        sys.exit( 1 )

    if input_file_path.stat().st_size == 0:
        logger.error( f"CRITICAL ERROR: Input file is empty: {input_file_path}" )
        sys.exit( 1 )

    if not proteome_file_path.exists():
        logger.error( f"CRITICAL ERROR: Proteome file not found: {proteome_file_path}" )
        logger.error( "The proteome file is required for query length lookup." )
        logger.error( "Check the proteome_directory setting in START_HERE-user_config.yaml." )
        sys.exit( 1 )

    # ========================================================================
    # Read proteome sequence lengths for alignment coverage check
    # ========================================================================

    identifiers___lengths = read_proteome_sequence_lengths( proteome_file_path, logger )

    # ========================================================================
    # Read DIAMOND results and group by query
    # ========================================================================
    # Dictionary: query_id -> list of hit tuples
    # Each hit tuple: (subject_id, pident, length, mismatch, gapopen,
    #                  qstart, qend, evalue, bitscore, stitle)

    queries___hits = {}

    # qseqid	sseqid	pident	length	mismatch	gapopen	qstart	qend	sstart	send	evalue	bitscore	stitle
    # g_GENE001-t_T1-p_P1-n_Metazoa_...	XP_012345.1	98.5	500	7	0	1	500	1	500	1e-200	800	hypothetical protein [Homo sapiens]
    with open( input_file_path, 'r' ) as input_diamond_results:
        for line in input_diamond_results:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            # Ensure we have all 13 columns
            if len( parts ) < 13:
                continue

            query_id = parts[ 0 ]
            subject_id = parts[ 1 ]
            pident = float( parts[ 2 ] )
            alignment_length = int( parts[ 3 ] )
            mismatch = int( parts[ 4 ] )
            gapopen = int( parts[ 5 ] )
            qstart = int( parts[ 6 ] )
            qend = int( parts[ 7 ] )
            evalue = parts[ 10 ]
            bitscore = parts[ 11 ]
            stitle = parts[ 12 ]

            if query_id not in queries___hits:
                queries___hits[ query_id ] = []

            queries___hits[ query_id ].append( (
                subject_id,
                pident,
                alignment_length,
                mismatch,
                gapopen,
                qstart,
                qend,
                evalue,
                bitscore,
                stitle
            ) )

    total_queries = len( queries___hits )
    logger.info( f"Unique query sequences: {total_queries}" )

    # ========================================================================
    # Identify top hits for each query
    # ========================================================================
    #
    # Self-hit detection: STRENGTHENED PROXY
    #
    # A hit is classified as a self-hit when ALL of these are true:
    #   1. pident == 100.0 (perfect percent identity)
    #   2. mismatch == 0 (no mismatches in alignment)
    #   3. gapopen == 0 (no gaps in alignment)
    #   4. Alignment covers >= 95% of full query protein length
    #
    # Condition 4 prevents false positives from conserved domains shared
    # between paralogs. A paralog might share a 100%-identical domain,
    # but the alignment would only cover a fraction of the full protein.
    #
    # The 95% threshold (rather than 100%) accounts for minor alignment
    # edge effects where DIAMOND may not extend to the very first or
    # last residue.
    #
    # ========================================================================

    ALIGNMENT_COVERAGE_THRESHOLD = 0.95

    # Statistics counters
    self_hits_found = 0
    non_self_hits_found = 0
    queries_with_no_non_self_hits = 0
    queries_with_no_self_hits = 0
    queries_with_no_length_lookup = 0

    # Output file paths
    output_top_hits_path = output_directory / f"{species_name}_top_hits.tsv"
    output_statistics_path = output_directory / f"{species_name}_statistics.tsv"

    with open( output_top_hits_path, 'w', newline = '', encoding = 'utf-8' ) as output_top_hits:

        writer = csv.writer( output_top_hits, delimiter = '\t', quoting = csv.QUOTE_MINIMAL )

        # Write header
        writer.writerow( [
            "Query_Sequence_ID (query protein identifier from species proteome)",
            "Top_10_Hit_IDs (comma delimited list of top 10 NCBI nr hit sequence IDs)",
            "Top_10_Hit_Headers (comma delimited list of top 10 NCBI nr hit descriptions)",
            "Top_Non_Self_Hit_ID (sequence ID of first hit classified as non-self)",
            "Top_Non_Self_Hit_Header (NCBI description of top non-self hit)",
            "Top_Non_Self_Hit_Percent_Identity (percent identity of top non-self hit)",
            "Top_Self_Hit_ID (sequence ID of first hit classified as self with 100 percent identity and full-length alignment)",
            "Top_Self_Hit_Header (NCBI description of top self hit)",
            "Self_Hit_Classification_Method (alignment proxy with pident 100 mismatch 0 gapopen 0 and alignment coverage >= 95 percent of query length)"
        ] )

        for query_id in sorted( queries___hits.keys() ):

            hits = queries___hits[ query_id ]

            # Look up full query protein length
            query_full_length = identifiers___lengths.get( query_id, None )
            if query_full_length is None:
                queries_with_no_length_lookup += 1

            # Take top 10 hits (already sorted by DIAMOND by bitscore)
            hits_top_10 = hits[ :10 ]

            # Collect top 10 IDs and headers
            top_10_ids = [ hit[ 0 ] for hit in hits_top_10 ]
            top_10_headers = [ hit[ 9 ] for hit in hits_top_10 ]

            # Find top non-self hit and top self-hit
            top_non_self_hit_id = ""
            top_non_self_hit_header = ""
            top_non_self_hit_pident = ""
            top_self_hit_id = ""
            top_self_hit_header = ""

            found_non_self = False
            found_self = False

            for subject_id, pident, alignment_length, mismatch, gapopen, qstart, qend, evalue, bitscore, stitle in hits_top_10:

                # Check self-hit conditions: perfect identity + near-full-length alignment
                is_perfect_identity = ( pident == 100.0 and mismatch == 0 and gapopen == 0 )
                is_full_length = False

                if is_perfect_identity and query_full_length is not None and query_full_length > 0:
                    # Calculate alignment coverage of query protein
                    query_aligned_length = qend - qstart + 1
                    alignment_coverage = query_aligned_length / query_full_length
                    is_full_length = ( alignment_coverage >= ALIGNMENT_COVERAGE_THRESHOLD )

                if is_perfect_identity and is_full_length:
                    # Self-hit: 100% identity over >= 95% of query length
                    if not found_self:
                        top_self_hit_id = subject_id
                        top_self_hit_header = stitle
                        found_self = True
                        self_hits_found += 1
                else:
                    # Non-self hit: either imperfect identity or partial alignment
                    if not found_non_self:
                        top_non_self_hit_id = subject_id
                        top_non_self_hit_header = stitle
                        top_non_self_hit_pident = str( pident )
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
                top_non_self_hit_pident,
                top_self_hit_id,
                top_self_hit_header,
                "alignment_proxy_pident100_mismatch0_gapopen0_coverage95"
            ] )

    # ========================================================================
    # Write statistics
    # ========================================================================

    with open( output_statistics_path, 'w' ) as output_statistics:

        output = "Species_Name (genus species identifier)\t"
        output += "Total_Queries_Processed (total number of query sequences processed)\t"
        output += "Self_Hits_Found (queries with self hit identified using alignment proxy pident 100 mismatch 0 gapopen 0 and alignment coverage >= 95 percent of query length)\t"
        output += "Non_Self_Hits_Found (queries with non-self hit identified)\t"
        output += "Queries_With_No_Non_Self_Hits (queries where all top 10 hits were self hits)\t"
        output += "Queries_With_No_Self_Hits (queries where no top 10 hit met self-hit criteria)\t"
        output += "Queries_With_No_Length_Lookup (queries where proteome sequence length was not found for coverage calculation)\n"
        output_statistics.write( output )

        output = species_name + '\t'
        output += str( total_queries ) + '\t'
        output += str( self_hits_found ) + '\t'
        output += str( non_self_hits_found ) + '\t'
        output += str( queries_with_no_non_self_hits ) + '\t'
        output += str( queries_with_no_self_hits ) + '\t'
        output += str( queries_with_no_length_lookup ) + '\n'
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
    logger.info( f"  Queries with no length lookup: {queries_with_no_length_lookup}" )
    logger.info( f"  Alignment coverage threshold: {ALIGNMENT_COVERAGE_THRESHOLD * 100}%" )
    logger.info( f"  Top hits file: {output_top_hits_path}" )
    logger.info( f"  Statistics file: {output_statistics_path}" )
    logger.info( "Script 005 complete." )


if __name__ == "__main__":
    main()
