#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Compute genome-wide statistics and relative ranks per species
# Human: Eric Edsinger

"""
GIGANTIC gene_sizes - Script 003: Compute Genome-Wide Statistics and Ranks

Purpose:
    For a single species, reads the per-gene metrics from Script 002 and:
    1. Computes genome-wide summary statistics (median, mean, min, max)
    2. Computes relative rank (quantile) for each gene within its genome
    3. Adds rank columns to the gene metrics table

Inputs:
    --gene-metrics: Path to per-species gene metrics TSV from Script 002
    --genus-species: Species name (Genus_species format)
    --output-dir: Output directory

Outputs:
    3-output/3_ai-ranked_gene_metrics-{Genus_species}.tsv - Gene metrics with rank columns
    3-output/3_ai-genome_summary-{Genus_species}.tsv - Genome-wide summary statistics
    3-output/3_ai-log-compute_genome_wide_statistics-{Genus_species}.log - Execution log
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path, genus_species: str ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( f'compute_genome_wide_statistics_{genus_species}' )
    logger.setLevel( logging.INFO )

    log_file = output_dir / f'3_ai-log-compute_genome_wide_statistics-{genus_species}.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.INFO )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


def compute_quantile_rank( values: list ) -> list:
    """Compute quantile rank (0.0-1.0) for each value in the list.

    Uses the average rank method for ties. Returns list of ranks in same order.
    """
    total_count = len( values )
    if total_count == 0:
        return []

    # Create (value, original_index) pairs and sort by value
    indexed_values = [ ( value, index ) for index, value in enumerate( values ) ]
    indexed_values.sort( key = lambda pair: pair[ 0 ] )

    # Assign ranks (handle ties by averaging)
    ranks = [ 0.0 ] * total_count
    position = 0

    while position < total_count:
        # Find all ties at this position
        tie_start = position
        while position < total_count and indexed_values[ position ][ 0 ] == indexed_values[ tie_start ][ 0 ]:
            position += 1

        # Average rank for tied values (1-based ranks converted to 0-1 quantile)
        average_rank = ( tie_start + position - 1 ) / 2.0
        quantile = average_rank / ( total_count - 1 ) if total_count > 1 else 0.5

        for tie_position in range( tie_start, position ):
            original_index = indexed_values[ tie_position ][ 1 ]
            ranks[ original_index ] = round( quantile, 6 )

    return ranks


def compute_summary_statistics( values: list ) -> dict:
    """Compute summary statistics for a list of numeric values."""
    if not values:
        return {
            'count': 0,
            'mean': 0,
            'median': 0,
            'minimum': 0,
            'maximum': 0,
            'percentile_25': 0,
            'percentile_75': 0
        }

    sorted_values = sorted( values )
    total_count = len( sorted_values )
    total_sum = sum( sorted_values )

    mean_value = total_sum / total_count

    # Median
    if total_count % 2 == 0:
        median_value = ( sorted_values[ total_count // 2 - 1 ] + sorted_values[ total_count // 2 ] ) / 2.0
    else:
        median_value = sorted_values[ total_count // 2 ]

    # Percentiles (using nearest rank method)
    percentile_25_index = max( 0, int( total_count * 0.25 ) - 1 )
    percentile_75_index = min( total_count - 1, int( total_count * 0.75 ) )

    return {
        'count': total_count,
        'mean': round( mean_value, 2 ),
        'median': round( median_value, 2 ),
        'minimum': sorted_values[ 0 ],
        'maximum': sorted_values[ -1 ],
        'percentile_25': sorted_values[ percentile_25_index ],
        'percentile_75': sorted_values[ percentile_75_index ]
    }


def main():
    parser = argparse.ArgumentParser(
        description = 'Compute genome-wide statistics and relative ranks'
    )
    parser.add_argument( '--gene-metrics', required = True,
                        help = 'Path to per-species gene metrics TSV' )
    parser.add_argument( '--genus-species', required = True,
                        help = 'Species name (Genus_species format)' )
    parser.add_argument( '--output-dir', required = True,
                        help = 'Output directory' )

    args = parser.parse_args()

    gene_metrics_file = Path( args.gene_metrics )
    genus_species = args.genus_species
    output_dir = Path( args.output_dir )

    output_dir.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_dir, genus_species )

    logger.info( '=' * 70 )
    logger.info( f'GIGANTIC gene_sizes - Compute Genome-Wide Statistics: {genus_species}' )
    logger.info( '=' * 70 )

    if not gene_metrics_file.exists():
        logger.error( f'CRITICAL ERROR: Gene metrics file not found: {gene_metrics_file}' )
        sys.exit( 1 )

    # Read gene metrics
    # Source_Gene_ID (source gene identifier matching g_ field in GIGANTIC headers)	GIGANTIC_Identifier (full GIGANTIC FASTA header or empty if not linked)	...
    # ENSG00000139618	g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_...	chr13	32315474	32400266	+	...
    genes = []
    header_line = ''

    with open( gene_metrics_file, 'r' ) as input_file:
        header_line = input_file.readline().strip()
        header_columns = header_line.split( '\t' )

        for line in input_file:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            if len( parts ) < 14:
                continue

            genes.append( {
                'source_gene_id': parts[ 0 ],
                'gigantic_identifier': parts[ 1 ],
                'seqid': parts[ 2 ],
                'start': int( parts[ 3 ] ),
                'end': int( parts[ 4 ] ),
                'strand': parts[ 5 ],
                'gene_length': int( parts[ 6 ] ),
                'exonic_length': int( parts[ 7 ] ),
                'intronic_length': int( parts[ 8 ] ),
                'exon_count': int( parts[ 9 ] ),
                'cds_length': int( parts[ 10 ] ),
                'protein_size': int( parts[ 11 ] ),
                'exon_sizes_ordered': parts[ 12 ],
                'intron_sizes_ordered': parts[ 13 ]
            } )

    logger.info( f'Read {len( genes )} genes from {gene_metrics_file.name}' )

    if len( genes ) == 0:
        logger.error( 'CRITICAL ERROR: No genes found in metrics file!' )
        sys.exit( 1 )

    # Extract value lists for ranking
    gene_lengths = [ gene[ 'gene_length' ] for gene in genes ]
    exonic_lengths = [ gene[ 'exonic_length' ] for gene in genes ]
    intronic_lengths = [ gene[ 'intronic_length' ] for gene in genes ]
    exon_counts = [ gene[ 'exon_count' ] for gene in genes ]
    protein_sizes = [ gene[ 'protein_size' ] for gene in genes ]

    # Compute quantile ranks
    logger.info( 'Computing quantile ranks...' )
    gene_length_ranks = compute_quantile_rank( gene_lengths )
    exonic_length_ranks = compute_quantile_rank( exonic_lengths )
    intronic_length_ranks = compute_quantile_rank( intronic_lengths )
    exon_count_ranks = compute_quantile_rank( exon_counts )
    protein_size_ranks = compute_quantile_rank( protein_sizes )

    # Write ranked gene metrics
    ranked_output_file = output_dir / f'3_ai-ranked_gene_metrics-{genus_species}.tsv'
    with open( ranked_output_file, 'w' ) as output_file:
        # Header: original columns + rank columns
        output = header_line + '\t' + \
                 'Gene_Length_Rank (quantile rank 0 to 1 within genome for gene length)' + '\t' + \
                 'Exonic_Length_Rank (quantile rank 0 to 1 within genome for exonic length)' + '\t' + \
                 'Intronic_Length_Rank (quantile rank 0 to 1 within genome for intronic length)' + '\t' + \
                 'Exon_Count_Rank (quantile rank 0 to 1 within genome for exon count)' + '\t' + \
                 'Protein_Size_Rank (quantile rank 0 to 1 within genome for protein size)' + '\n'
        output_file.write( output )

        for index, gene in enumerate( genes ):
            output = str( gene[ 'source_gene_id' ] ) + '\t' + \
                     str( gene[ 'gigantic_identifier' ] ) + '\t' + \
                     str( gene[ 'seqid' ] ) + '\t' + \
                     str( gene[ 'start' ] ) + '\t' + \
                     str( gene[ 'end' ] ) + '\t' + \
                     str( gene[ 'strand' ] ) + '\t' + \
                     str( gene[ 'gene_length' ] ) + '\t' + \
                     str( gene[ 'exonic_length' ] ) + '\t' + \
                     str( gene[ 'intronic_length' ] ) + '\t' + \
                     str( gene[ 'exon_count' ] ) + '\t' + \
                     str( gene[ 'cds_length' ] ) + '\t' + \
                     str( gene[ 'protein_size' ] ) + '\t' + \
                     str( gene[ 'exon_sizes_ordered' ] ) + '\t' + \
                     str( gene[ 'intron_sizes_ordered' ] ) + '\t' + \
                     str( gene_length_ranks[ index ] ) + '\t' + \
                     str( exonic_length_ranks[ index ] ) + '\t' + \
                     str( intronic_length_ranks[ index ] ) + '\t' + \
                     str( exon_count_ranks[ index ] ) + '\t' + \
                     str( protein_size_ranks[ index ] ) + '\n'
            output_file.write( output )

    logger.info( f'Wrote ranked gene metrics: {ranked_output_file}' )

    # Compute genome-wide summary statistics
    logger.info( 'Computing genome-wide summary statistics...' )

    metrics_to_summarize = {
        'Gene_Length': gene_lengths,
        'Exonic_Length': exonic_lengths,
        'Intronic_Length': intronic_lengths,
        'Exon_Count': exon_counts,
        'Protein_Size': protein_sizes
    }

    # Write genome summary
    summary_output_file = output_dir / f'3_ai-genome_summary-{genus_species}.tsv'
    with open( summary_output_file, 'w' ) as output_file:
        output = 'Metric (gene structure metric name)' + '\t' + \
                 'Gene_Count (number of protein-coding genes)' + '\t' + \
                 'Mean (arithmetic mean value)' + '\t' + \
                 'Median (median value)' + '\t' + \
                 'Minimum (smallest value)' + '\t' + \
                 'Maximum (largest value)' + '\t' + \
                 'Percentile_25 (25th percentile value)' + '\t' + \
                 'Percentile_75 (75th percentile value)' + '\n'
        output_file.write( output )

        for metric_name in metrics_to_summarize:
            metric_values = metrics_to_summarize[ metric_name ]
            stats = compute_summary_statistics( metric_values )

            output = metric_name + '\t' + \
                     str( stats[ 'count' ] ) + '\t' + \
                     str( stats[ 'mean' ] ) + '\t' + \
                     str( stats[ 'median' ] ) + '\t' + \
                     str( stats[ 'minimum' ] ) + '\t' + \
                     str( stats[ 'maximum' ] ) + '\t' + \
                     str( stats[ 'percentile_25' ] ) + '\t' + \
                     str( stats[ 'percentile_75' ] ) + '\n'
            output_file.write( output )

    logger.info( f'Wrote genome summary: {summary_output_file}' )

    # Log key statistics
    gene_length_stats = compute_summary_statistics( gene_lengths )
    logger.info( '' )
    logger.info( f'Genome Summary for {genus_species}:' )
    logger.info( f'  Protein-coding genes: {gene_length_stats[ "count" ]}' )
    logger.info( f'  Median gene length: {gene_length_stats[ "median" ]:,.0f} bp' )
    logger.info( f'  Mean gene length: {gene_length_stats[ "mean" ]:,.0f} bp' )
    logger.info( f'  Largest gene: {gene_length_stats[ "maximum" ]:,} bp' )

    logger.info( '' )
    logger.info( '=' * 70 )
    logger.info( f'SUCCESS: {genus_species} - ranked metrics and summary computed' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
