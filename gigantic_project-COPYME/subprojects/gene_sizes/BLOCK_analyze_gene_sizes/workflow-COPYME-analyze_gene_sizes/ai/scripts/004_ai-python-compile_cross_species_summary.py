#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Compile cross-species gene size summary
# Human: Eric Edsinger

"""
GIGANTIC gene_sizes - Script 004: Compile Cross-Species Summary

Purpose:
    Combines per-species genome summaries from Script 003 into a single
    cross-species comparison table. Also collects all ranked gene metrics
    into output directories for downstream use. Includes the species
    processing status from Script 001 to document which species were
    processed and which were skipped.

Inputs:
    --genome-summaries-dir: Directory containing 3_ai-genome_summary-*.tsv files
    --ranked-metrics-dir: Directory containing 3_ai-ranked_gene_metrics-*.tsv files
    --species-status-file: Path to 1_ai-species_processing_status.tsv from Script 001
    --species-count: Number of processable species (for output naming)
    --gigantic-species-count: Total number of species in GIGANTIC set
    --output-dir: Output directory

Outputs:
    4-output/4_ai-cross_species_summary.tsv - Combined genome summaries
    4-output/4_ai-species_processing_status.tsv - Copy of processing status for downstream
    4-output/speciesN_gigantic_gene_metrics/ - Collected ranked metrics for downstream
    4-output/speciesN_gigantic_gene_sizes_summary/ - Summary table for downstream
    4-output/4_ai-log-compile_cross_species_summary.log - Execution log
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( 'compile_cross_species_summary' )
    logger.setLevel( logging.INFO )

    log_file = output_dir / '4_ai-log-compile_cross_species_summary.log'
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


def main():
    parser = argparse.ArgumentParser(
        description = 'Compile cross-species gene size summary'
    )
    parser.add_argument( '--genome-summaries-dir', required = True,
                        help = 'Directory containing genome summary TSV files' )
    parser.add_argument( '--ranked-metrics-dir', required = True,
                        help = 'Directory containing ranked gene metrics TSV files' )
    parser.add_argument( '--species-status-file', required = True,
                        help = 'Path to species processing status TSV from Script 001' )
    parser.add_argument( '--species-count', required = True, type = int,
                        help = 'Number of processable species' )
    parser.add_argument( '--gigantic-species-count', required = True, type = int,
                        help = 'Total number of species in GIGANTIC set' )
    parser.add_argument( '--output-dir', required = True,
                        help = 'Output directory' )

    args = parser.parse_args()

    genome_summaries_dir = Path( args.genome_summaries_dir )
    ranked_metrics_dir = Path( args.ranked_metrics_dir )
    species_status_file = Path( args.species_status_file )
    species_count = args.species_count
    gigantic_species_count = args.gigantic_species_count
    output_dir = Path( args.output_dir )

    output_dir.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_dir )

    logger.info( '=' * 70 )
    logger.info( 'GIGANTIC gene_sizes - Compile Cross-Species Summary' )
    logger.info( '=' * 70 )

    # Report species processing status
    logger.info( f'GIGANTIC species set: {gigantic_species_count} species' )
    logger.info( f'Species with gene structure data: {species_count}' )
    logger.info( f'Species without gene structure data: {gigantic_species_count - species_count}' )

    # Find all genome summary files
    genome_summary_files = sorted( genome_summaries_dir.glob( '3_ai-genome_summary-*.tsv' ) )
    logger.info( f'Found {len( genome_summary_files )} genome summary files' )

    if len( genome_summary_files ) == 0:
        logger.error( 'CRITICAL ERROR: No genome summary files found!' )
        logger.error( f'  Expected in: {genome_summaries_dir}' )
        sys.exit( 1 )

    # Build cross-species summary table
    logger.info( '' )
    logger.info( 'Building cross-species summary...' )

    # Collect per-species summaries
    species_summaries = []

    for summary_file in genome_summary_files:
        # Extract species name from filename: 3_ai-genome_summary-Genus_species.tsv
        filename = summary_file.stem
        genus_species = filename.replace( '3_ai-genome_summary-', '' )

        # Read summary file
        # Metric (gene structure metric name)	Gene_Count (number of protein-coding genes)	...
        # Gene_Length	20000	45000.5	30000	100	5000000	...
        metrics___values = {}
        with open( summary_file, 'r' ) as input_file:
            header_line = input_file.readline().strip()

            for line in input_file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split( '\t' )
                if len( parts ) >= 8:
                    metric_name = parts[ 0 ]
                    metrics___values[ metric_name ] = {
                        'gene_count': parts[ 1 ],
                        'mean': parts[ 2 ],
                        'median': parts[ 3 ],
                        'minimum': parts[ 4 ],
                        'maximum': parts[ 5 ],
                        'percentile_25': parts[ 6 ],
                        'percentile_75': parts[ 7 ]
                    }

        species_summaries.append( {
            'genus_species': genus_species,
            'metrics': metrics___values
        } )

    logger.info( f'Loaded summaries for {len( species_summaries )} species' )

    # Write cross-species summary (wide format: one row per species)
    cross_species_output = output_dir / '4_ai-cross_species_summary.tsv'

    # Define metrics to include
    metric_names = [ 'Gene_Length', 'Exonic_Length', 'Intronic_Length', 'Exon_Count', 'Protein_Size' ]
    stat_types = [ 'gene_count', 'median', 'mean', 'minimum', 'maximum' ]

    with open( cross_species_output, 'w' ) as output_file:
        # Build header
        header_parts = [ 'Genus_Species (species name)' ]
        for metric_name in metric_names:
            for stat_type in stat_types:
                header_label = f'{metric_name}_{stat_type.capitalize()} ({stat_type} of {metric_name.lower().replace( "_", " " )} across all genes)'
                header_parts.append( header_label )

        output = '\t'.join( header_parts ) + '\n'
        output_file.write( output )

        # Write one row per species
        for species_summary in sorted( species_summaries, key = lambda summary: summary[ 'genus_species' ] ):
            row_parts = [ species_summary[ 'genus_species' ] ]

            for metric_name in metric_names:
                metric_values = species_summary[ 'metrics' ].get( metric_name, {} )
                for stat_type in stat_types:
                    value = metric_values.get( stat_type, 'NA' )
                    row_parts.append( str( value ) )

            output = '\t'.join( row_parts ) + '\n'
            output_file.write( output )

    logger.info( f'Wrote cross-species summary: {cross_species_output}' )

    # Copy species processing status to output for downstream reference
    if species_status_file.exists():
        status_dest = output_dir / '4_ai-species_processing_status.tsv'
        shutil.copy2( species_status_file, status_dest )
        logger.info( f'Copied species processing status: {status_dest}' )
    else:
        logger.warning( f'Species processing status file not found: {species_status_file}' )

    # Create output directories for downstream use
    gene_metrics_output_dir = output_dir / f'species{species_count}_gigantic_gene_metrics'
    gene_sizes_summary_dir = output_dir / f'species{species_count}_gigantic_gene_sizes_summary'

    gene_metrics_output_dir.mkdir( parents = True, exist_ok = True )
    gene_sizes_summary_dir.mkdir( parents = True, exist_ok = True )

    # Copy ranked gene metrics to downstream directory
    ranked_metrics_files = sorted( ranked_metrics_dir.glob( '3_ai-ranked_gene_metrics-*.tsv' ) )
    metrics_copied = 0

    for ranked_file in ranked_metrics_files:
        dest_file = gene_metrics_output_dir / ranked_file.name
        shutil.copy2( ranked_file, dest_file )
        metrics_copied += 1

    logger.info( f'Copied {metrics_copied} ranked metrics files to {gene_metrics_output_dir.name}/' )

    # Copy cross-species summary to downstream directory
    shutil.copy2( cross_species_output, gene_sizes_summary_dir / cross_species_output.name )

    # Copy species processing status to downstream summary directory
    if species_status_file.exists():
        shutil.copy2( species_status_file, gene_sizes_summary_dir / '4_ai-species_processing_status.tsv' )

    # Also copy individual genome summaries to downstream directory
    summaries_copied = 0
    for summary_file in genome_summary_files:
        dest_file = gene_sizes_summary_dir / summary_file.name
        shutil.copy2( summary_file, dest_file )
        summaries_copied += 1

    logger.info( f'Copied {summaries_copied} genome summaries to {gene_sizes_summary_dir.name}/' )

    logger.info( '' )
    logger.info( '=' * 70 )
    logger.info( f'SUCCESS: Cross-species summary compiled for {len( species_summaries )} species' )
    logger.info( f'  Processed: {species_count} of {gigantic_species_count} GIGANTIC species' )
    logger.info( f'  Output: {gene_metrics_output_dir.name}/' )
    logger.info( f'  Output: {gene_sizes_summary_dir.name}/' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
