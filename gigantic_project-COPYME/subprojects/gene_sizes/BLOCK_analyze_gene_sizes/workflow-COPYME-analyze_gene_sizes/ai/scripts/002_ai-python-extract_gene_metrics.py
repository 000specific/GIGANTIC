#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Compute gene structure metrics from user-provided CDS intervals
# Human: Eric Edsinger

"""
GIGANTIC gene_sizes - Script 002: Extract Gene Metrics

Purpose:
    Reads user-provided gene structure data (Source_Gene_ID + CDS intervals)
    for a single species and computes per-gene metrics. Links source gene IDs
    to GIGANTIC identifiers by parsing the g_ prefix from proteome FASTA headers.

Inputs:
    --gene-structure-file: Path to user-provided gene structure TSV for one species
    --proteome-file: Path to GIGANTIC proteome (.aa) for this species (for ID linkage)
    --genus-species: Species name (Genus_species format)
    --output-dir: Output directory

    User-provided TSV format:
        Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  CDS_Intervals
        ENSG00000139618  chr13  32315474  32400266  +  32316422-32316527,32319077-32319325

Outputs:
    2-output/2_ai-gene_metrics-{Genus_species}.tsv - Per-gene metrics with GIGANTIC IDs
    2-output/2_ai-log-extract_gene_metrics-{Genus_species}.log - Execution log

Metrics computed per gene:
    Gene_Length          - Genomic span (end - start + 1)
    Exonic_Length        - Sum of merged CDS intervals
    Intronic_Length      - Gene length minus exonic length
    Exon_Count           - Number of CDS intervals
    CDS_Length           - Total coding sequence length (same as exonic length)
    Protein_Size         - Estimated amino acids (CDS length / 3)
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path, genus_species: str ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( f'extract_gene_metrics_{genus_species}' )
    logger.setLevel( logging.INFO )

    log_file = output_dir / f'2_ai-log-extract_gene_metrics-{genus_species}.log'
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


def load_gigantic_gene_ids( proteome_file: Path, logger: logging.Logger ) -> dict:
    """Parse GIGANTIC proteome FASTA headers to build source_gene_id → gigantic_id mapping.

    GIGANTIC header format: >g_SOURCE_GENE_ID-t_TRANSCRIPT_ID-p_PROTEIN_ID-n_PHYLONAME
    Returns: source_gene_ids___gigantic_identifiers dictionary
    """
    source_gene_ids___gigantic_identifiers = {}

    if not proteome_file or not proteome_file.exists():
        logger.info( '  No proteome file provided - GIGANTIC ID linkage skipped' )
        return source_gene_ids___gigantic_identifiers

    # >g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
    # MPIGSKERPTFFEIFKTRCNK...
    with open( proteome_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if not line.startswith( '>' ):
                continue

            header = line[ 1: ]  # Remove >

            # Extract g_ field (source gene ID)
            parts_header = header.split( '-' )
            if len( parts_header ) < 1:
                continue

            # Find the g_ prefix field
            gene_id_field = ''
            for part in parts_header:
                if part.startswith( 'g_' ):
                    gene_id_field = part[ 2: ]  # Remove g_ prefix
                    break

            if gene_id_field:
                source_gene_ids___gigantic_identifiers[ gene_id_field ] = header

    logger.info( f'  Loaded {len( source_gene_ids___gigantic_identifiers )} GIGANTIC identifiers from proteome' )

    return source_gene_ids___gigantic_identifiers


def merge_intervals( intervals: list ) -> list:
    """Merge overlapping intervals. Input: list of (start, end) tuples.

    Returns sorted list of non-overlapping (start, end) tuples.
    """
    if not intervals:
        return []

    sorted_intervals = sorted( intervals, key = lambda interval: interval[ 0 ] )
    merged = [ sorted_intervals[ 0 ] ]

    for current_start, current_end in sorted_intervals[ 1: ]:
        previous_start, previous_end = merged[ -1 ]

        if current_start <= previous_end + 1:
            merged[ -1 ] = ( previous_start, max( previous_end, current_end ) )
        else:
            merged.append( ( current_start, current_end ) )

    return merged


def parse_cds_intervals( cds_intervals_string: str ) -> list:
    """Parse comma-separated CDS interval string into list of (start, end) tuples.

    Input format: 32316422-32316527,32319077-32319325,32325076-32325184
    """
    intervals = []
    parts_cds_intervals = cds_intervals_string.split( ',' )

    for interval_string in parts_cds_intervals:
        interval_string = interval_string.strip()
        parts_interval = interval_string.split( '-' )
        if len( parts_interval ) == 2:
            try:
                interval_start = int( parts_interval[ 0 ] )
                interval_end = int( parts_interval[ 1 ] )
                intervals.append( ( interval_start, interval_end ) )
            except ValueError:
                continue

    return intervals


def main():
    parser = argparse.ArgumentParser(
        description = 'Compute gene structure metrics from user-provided CDS intervals'
    )
    parser.add_argument( '--gene-structure-file', required = True,
                        help = 'Path to user-provided gene structure TSV' )
    parser.add_argument( '--proteome-file', required = False, default = '',
                        help = 'Path to GIGANTIC proteome for ID linkage (optional)' )
    parser.add_argument( '--genus-species', required = True,
                        help = 'Species name (Genus_species format)' )
    parser.add_argument( '--output-dir', required = True,
                        help = 'Output directory' )

    args = parser.parse_args()

    gene_structure_file = Path( args.gene_structure_file )
    proteome_file = Path( args.proteome_file ) if args.proteome_file else None
    genus_species = args.genus_species
    output_dir = Path( args.output_dir )

    output_dir.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_dir, genus_species )

    logger.info( '=' * 70 )
    logger.info( f'GIGANTIC gene_sizes - Extract Gene Metrics: {genus_species}' )
    logger.info( '=' * 70 )

    if not gene_structure_file.exists():
        logger.error( f'CRITICAL ERROR: Gene structure file not found: {gene_structure_file}' )
        sys.exit( 1 )

    logger.info( f'Species: {genus_species}' )
    logger.info( f'Gene structure file: {gene_structure_file}' )

    # Load GIGANTIC ID mapping from proteome (optional)
    logger.info( '' )
    logger.info( 'Loading GIGANTIC identifier mapping...' )
    source_gene_ids___gigantic_identifiers = load_gigantic_gene_ids( proteome_file, logger )

    # Parse gene structure data and compute metrics
    logger.info( '' )
    logger.info( 'Computing gene metrics...' )

    gene_metrics = []

    # Source_Gene_ID (source gene identifier)	Seqid (chromosome or scaffold)	Gene_Start (gene start position bp)	Gene_End (gene end position bp)	Strand (plus or minus strand)	CDS_Intervals (comma separated start-end pairs for coding sequence intervals)
    # ENSG00000139618	chr13	32315474	32400266	+	32316422-32316527,32319077-32319325,32325076-32325184
    header_found = False
    with open( gene_structure_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()

            if not line or line.startswith( '#' ):
                continue

            if not header_found:
                if line.startswith( 'Source_Gene_ID' ):
                    header_found = True
                    continue
                else:
                    header_found = True

            parts = line.split( '\t' )
            if len( parts ) < 6:
                continue

            source_gene_id = parts[ 0 ].strip()
            seqid = parts[ 1 ].strip()

            try:
                gene_start = int( parts[ 2 ] )
                gene_end = int( parts[ 3 ] )
            except ValueError:
                continue

            strand = parts[ 4 ].strip()
            cds_intervals_string = parts[ 5 ].strip()

            if not source_gene_id or not cds_intervals_string:
                continue

            if gene_start >= gene_end:
                continue

            # Parse and merge CDS intervals
            cds_intervals = parse_cds_intervals( cds_intervals_string )
            if not cds_intervals:
                continue

            merged_cds = merge_intervals( cds_intervals )

            # Compute metrics
            gene_length = gene_end - gene_start + 1

            exonic_length = 0
            for interval_start, interval_end in merged_cds:
                exonic_length += interval_end - interval_start + 1

            exon_count = len( merged_cds )
            intronic_length = max( gene_length - exonic_length, 0 )
            cds_length = exonic_length
            protein_size = cds_length // 3

            # Look up GIGANTIC identifier
            gigantic_identifier = source_gene_ids___gigantic_identifiers.get( source_gene_id, '' )

            gene_metrics.append( {
                'source_gene_id': source_gene_id,
                'gigantic_identifier': gigantic_identifier,
                'seqid': seqid,
                'start': gene_start,
                'end': gene_end,
                'strand': strand,
                'gene_length': gene_length,
                'exonic_length': exonic_length,
                'intronic_length': intronic_length,
                'exon_count': exon_count,
                'cds_length': cds_length,
                'protein_size': protein_size
            } )

    logger.info( f'  Computed metrics for {len( gene_metrics )} genes' )

    if len( gene_metrics ) == 0:
        logger.error( 'CRITICAL ERROR: No valid gene metrics computed!' )
        sys.exit( 1 )

    # Report GIGANTIC ID linkage
    linked_count = sum( 1 for gene in gene_metrics if gene[ 'gigantic_identifier' ] )
    unlinked_count = len( gene_metrics ) - linked_count
    if proteome_file:
        logger.info( f'  Linked to GIGANTIC IDs: {linked_count}' )
        if unlinked_count > 0:
            logger.info( f'  Not linked (source gene ID not in proteome): {unlinked_count}' )

    # Sort by source_gene_id
    gene_metrics.sort( key = lambda gene: gene[ 'source_gene_id' ] )

    # Write output
    output_file_path = output_dir / f'2_ai-gene_metrics-{genus_species}.tsv'
    with open( output_file_path, 'w' ) as output_file:
        output = 'Source_Gene_ID (source gene identifier matching g_ field in GIGANTIC headers)' + '\t' + \
                 'GIGANTIC_Identifier (full GIGANTIC FASTA header or empty if not linked)' + '\t' + \
                 'Seqid (chromosome or scaffold)' + '\t' + \
                 'Start (gene start position bp)' + '\t' + \
                 'End (gene end position bp)' + '\t' + \
                 'Strand (plus or minus strand)' + '\t' + \
                 'Gene_Length (genomic span in bp end minus start plus 1)' + '\t' + \
                 'Exonic_Length (sum of merged CDS intervals in bp)' + '\t' + \
                 'Intronic_Length (gene length minus exonic length in bp)' + '\t' + \
                 'Exon_Count (number of merged CDS intervals)' + '\t' + \
                 'CDS_Length (total coding sequence length in bp)' + '\t' + \
                 'Protein_Size (estimated amino acids as CDS length divided by 3)' + '\n'
        output_file.write( output )

        for gene in gene_metrics:
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
                     str( gene[ 'protein_size' ] ) + '\n'
            output_file.write( output )

    logger.info( '' )
    logger.info( f'Wrote gene metrics: {output_file_path}' )

    logger.info( '' )
    logger.info( '=' * 70 )
    logger.info( f'SUCCESS: {genus_species} - {len( gene_metrics )} genes processed' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
