#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Identify chromosomal hotspots from filtered self-BLAST hits
# Human: Eric Edsinger

"""
GIGANTIC hotspots BLOCK_identify_hotspots - Script 003: Identify Hotspots

Purpose:
    Modernized port of GIGANTIC_0 hotspots-003. For one species:
      1. Parse proteome FASTA to build full_id → Source_Gene_ID mapping
      2. Load user-provided gene-coordinate TSV; build per-chromosome ordered
         lists sorted by (start, end)
      3. For each filtered self-BLAST hit (from script 002):
          - Translate query and subject full IDs to Source_Gene_IDs
          - If both fall on the SAME chromosome AND their ordered positions
            differ by no more than window_radius (= window_size // 2):
              add an edge (query, subject) to the paralog graph
      4. Find connected components via union-find
      5. Each component with >= minimum_paralog_count genes is a hotspot
      6. Emit per-species hotspots TSV ordered by chromosome and start.

Differences from GIGANTIC_0:
    - Genes are ordered by (chromosome, start, end) — explicit sort instead
      of relying on input file order. Eliminates a class of silent bugs.
    - Cluster merging uses union-find (O(N·α(N))) instead of GIGANTIC_0's
      O(N²) double-loop scan.
    - All gene/coordinate joining is fail-fast: any unmapped ID logs a
      detailed error and (per CLAUDE.md zero-tolerance rule) the script
      exits non-zero rather than silently dropping the hit.
    - No species-specific hardcoded special-cases (e.g. the GIGANTIC_0
      Homo_sapiens lncRNA hack).

Inputs (CLI):
    --filtered-hits          Path to 2_ai-filtered_hits-<Genus_species>.tsv
    --gene-coordinates       Path to user-provided <Genus_species>-gene_coordinates.tsv
    --proteome               Path to <phyloname>-T1-proteome.aa
    --genus-species          Species name (Genus_species format)
    --window-size            Total gene-position window (default 20)
    --minimum-paralog-count  Minimum members for a hotspot (default 2)
    --output-dir             Output directory (typically 3-output)

Outputs (in --output-dir):
    3_ai-hotspots-<Genus_species>.tsv
        Per-row: Hotspot_ID, Chromosome, Hotspot_Start, Hotspot_End,
                 Paralog_Count, Member_Source_Gene_IDs (comma delimited)

    3_ai-hotspot_summary-<Genus_species>.tsv
        Single-row summary: hotspot_count, total_paralog_genes, etc.

    3_ai-log-identify_hotspots-<Genus_species>.log

Failure mode:
    Exits 1 (fail-fast) when:
      - Required input missing
      - Window size or minimum_paralog_count not positive integer
      - Gene-coordinate TSV has malformed rows
      - Any blast hit references a gene whose Source_Gene_ID is not in the
        coordinate table (either the proteome / coordinates / blast set are
        out of sync — a research-correctness failure, not a silent skip).
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path, genus_species: str ) -> logging.Logger:
    logger = logging.getLogger( f'identify_hotspots_{genus_species}' )
    logger.setLevel( logging.INFO )
    log_file = output_dir / f'3_ai-log-identify_hotspots-{genus_species}.log'
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


def parse_full_id_to_source_gene_id( full_id: str ) -> str:
    """Extract Source_Gene_ID from a GIGANTIC FASTA header value.

    Header format: g_<source_gene_id>-t_<transcript_id>-p_<protein_id>-n_<phyloname>
    The blastp seqid is the entire header (no whitespace), so we get the
    same string back. Find the g_ field, strip the prefix.

    Returns empty string if no g_ field found.
    """
    parts_full_id = full_id.split( '-' )
    for part in parts_full_id:
        if part.startswith( 'g_' ):
            return part[ 2: ]
    return ''


def build_full_id_to_source_gene_id_map( proteome_path: Path, logger: logging.Logger ) -> dict:
    """Walk proteome FASTA and build full_GIGANTIC_id -> Source_Gene_ID dict.

    The full ID is the header line minus the leading '>'. Source_Gene_ID is
    the value after 'g_' in that header.
    """
    full_ids___source_gene_ids = {}
    with open( proteome_path, 'r' ) as input_proteome:
        for line in input_proteome:
            line = line.rstrip( '\n' )
            if not line.startswith( '>' ):
                continue
            full_id = line[ 1: ]
            source_gene_id = parse_full_id_to_source_gene_id( full_id )
            if not source_gene_id:
                continue
            # GIGANTIC headers have one record per gene/transcript/protein
            # combo. Multiple proteins can share a Source_Gene_ID; we keep
            # the first mapping (any of them resolves to the same gene).
            if full_id not in full_ids___source_gene_ids:
                full_ids___source_gene_ids[ full_id ] = source_gene_id
    logger.info( f'  Indexed {len( full_ids___source_gene_ids )} GIGANTIC headers from proteome' )
    return full_ids___source_gene_ids


def load_gene_coordinates( coords_path: Path, logger: logging.Logger ) -> tuple:
    """Read user-provided gene_coordinates TSV.

    Returns:
      source_gene_ids___records = { source_gene_id: ( chromosome, start, end, strand ) }
      chromosomes___ordered_gene_ids = { chromosome: [ source_gene_id, ... ] }
        sorted by (start, end). Each gene's chromosomal index = position in this list.
    """
    REQUIRED_COLUMNS = [ 'Source_Gene_ID', 'Seqid', 'Gene_Start', 'Gene_End', 'Strand' ]
    source_gene_ids___records = {}
    chromosomes___raw_records = {}

    # Header row may carry self-documenting "(...)" suffixes; strip them.
    # Source_Gene_ID\tSeqid\tGene_Start\tGene_End\tStrand\t[...]
    # ENSG00000139618\tchr13\t32315474\t32400266\t+\t[...]
    with open( coords_path, 'r' ) as input_coords:
        header_line = input_coords.readline().rstrip( '\n' )
        header_columns = [ raw.split( ' (' )[ 0 ].strip() for raw in header_line.split( '\t' ) ]
        column_indices = {}
        for required in REQUIRED_COLUMNS:
            if required not in header_columns:
                logger.error( f'CRITICAL ERROR: Missing required column "{required}" in {coords_path.name}' )
                logger.error( f'Found columns: {header_columns}' )
                sys.exit( 1 )
            column_indices[ required ] = header_columns.index( required )

        row_count = 0
        duplicate_count = 0
        for line in input_coords:
            line = line.rstrip( '\n' )
            if not line.strip() or line.startswith( '#' ):
                continue
            parts = line.split( '\t' )
            if len( parts ) <= max( column_indices.values() ):
                logger.error( f'CRITICAL ERROR: Row has fewer fields than header in {coords_path.name}: {line[:120]}' )
                sys.exit( 1 )

            source_gene_id = parts[ column_indices[ 'Source_Gene_ID' ] ].strip()
            chromosome = parts[ column_indices[ 'Seqid' ] ].strip()
            try:
                start = int( parts[ column_indices[ 'Gene_Start' ] ].strip() )
                end = int( parts[ column_indices[ 'Gene_End' ] ].strip() )
            except ValueError:
                logger.error( f'CRITICAL ERROR: Non-integer Gene_Start/Gene_End in {coords_path.name}: {line[:120]}' )
                sys.exit( 1 )
            strand = parts[ column_indices[ 'Strand' ] ].strip()

            if source_gene_id in source_gene_ids___records:
                duplicate_count += 1
                continue   # keep first occurrence

            record = ( chromosome, start, end, strand )
            source_gene_ids___records[ source_gene_id ] = record
            chromosomes___raw_records.setdefault( chromosome, [] ).append( ( source_gene_id, start, end ) )
            row_count += 1

        logger.info( f'  Loaded {row_count} gene coordinates across {len( chromosomes___raw_records )} chromosomes' )
        if duplicate_count:
            logger.warning( f'  Skipped {duplicate_count} duplicate Source_Gene_IDs (kept first occurrence)' )

    # Sort each chromosome's records by (start, end) and produce ordered ID list
    chromosomes___ordered_gene_ids = {}
    for chromosome, records in chromosomes___raw_records.items():
        records_sorted = sorted( records, key = lambda r: ( r[ 1 ], r[ 2 ] ) )
        chromosomes___ordered_gene_ids[ chromosome ] = [ r[ 0 ] for r in records_sorted ]

    return source_gene_ids___records, chromosomes___ordered_gene_ids


class UnionFind:
    """Compressed union-find over arbitrary hashable items.

    Used to merge paralog edges into connected components in near-linear time.
    """
    def __init__( self ):
        self.parents = {}

    def find( self, item ):
        if item not in self.parents:
            self.parents[ item ] = item
            return item
        # Path compression
        root = item
        while self.parents[ root ] != root:
            root = self.parents[ root ]
        cur = item
        while self.parents[ cur ] != root:
            nxt = self.parents[ cur ]
            self.parents[ cur ] = root
            cur = nxt
        return root

    def union( self, a, b ):
        ra = self.find( a )
        rb = self.find( b )
        if ra != rb:
            self.parents[ ra ] = rb

    def components( self ):
        comps = {}
        for item in list( self.parents.keys() ):
            root = self.find( item )
            comps.setdefault( root, [] ).append( item )
        return list( comps.values() )


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--filtered-hits', required = True, type = Path )
    parser.add_argument( '--gene-coordinates', required = True, type = Path )
    parser.add_argument( '--proteome', required = True, type = Path )
    parser.add_argument( '--genus-species', required = True )
    parser.add_argument( '--window-size', type = int, default = 20 )
    parser.add_argument( '--minimum-paralog-count', type = int, default = 2 )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir, args.genus_species )

    logger.info( '=' * 72 )
    logger.info( f'GIGANTIC hotspots BLOCK_identify_hotspots - Script 003: Identify Hotspots ({args.genus_species})' )
    logger.info( '=' * 72 )
    logger.info( f'Filtered hits:            {args.filtered_hits}' )
    logger.info( f'Gene coordinates:         {args.gene_coordinates}' )
    logger.info( f'Proteome:                 {args.proteome}' )
    logger.info( f'Window size (total):      {args.window_size}' )
    logger.info( f'Minimum paralog count:    {args.minimum_paralog_count}' )
    logger.info( f'Output dir:               {args.output_dir}' )

    if args.window_size <= 0:
        logger.error( f'CRITICAL ERROR: --window-size must be positive (got {args.window_size}).' )
        return 1
    if args.minimum_paralog_count <= 1:
        logger.error( f'CRITICAL ERROR: --minimum-paralog-count must be at least 2 (got {args.minimum_paralog_count}).' )
        return 1
    for label, path in [
        ( 'Filtered hits',     args.filtered_hits ),
        ( 'Gene coordinates',  args.gene_coordinates ),
        ( 'Proteome',          args.proteome ),
    ]:
        if not path.is_file():
            logger.error( f'CRITICAL ERROR: {label} file not found: {path}' )
            return 1

    window_radius = args.window_size // 2

    # ---- Load inputs ----
    full_ids___source_gene_ids = build_full_id_to_source_gene_id_map( args.proteome, logger )
    source_gene_ids___records, chromosomes___ordered_gene_ids = load_gene_coordinates( args.gene_coordinates, logger )

    # Build per-chromosome index lookup for fast (chromosome, position) checks
    chromosomes_source_gene_ids___positions = {}
    for chromosome, ordered_ids in chromosomes___ordered_gene_ids.items():
        for index, source_gene_id in enumerate( ordered_ids ):
            chromosomes_source_gene_ids___positions[ ( chromosome, source_gene_id ) ] = index

    # ---- Stream filtered hits and build paralog graph ----
    union_find = UnionFind()
    hits_processed = 0
    hits_in_window = 0
    hits_diff_chromosome = 0
    hits_outside_window = 0
    unmapped_full_ids = []   # ( query_id, subject_id ) collected for fail-fast report

    # Query_ID\tSubject_ID\tEvalue
    # g_g1-t_..-p_..-n_..\tg_g2-t_..-p_..-n_..\t1e-200
    with open( args.filtered_hits, 'r' ) as input_filtered:
        header_seen = False
        for line in input_filtered:
            line = line.rstrip( '\n' )
            if not line:
                continue
            if not header_seen:
                header_seen = True
                continue
            parts = line.split( '\t' )
            if len( parts ) < 3:
                logger.error( f'CRITICAL ERROR: Malformed filtered-hits row (<3 fields): {line[:120]}' )
                return 1
            hits_processed += 1
            query_full_id = parts[ 0 ]
            subject_full_id = parts[ 1 ]

            query_source_gene_id = full_ids___source_gene_ids.get( query_full_id )
            subject_source_gene_id = full_ids___source_gene_ids.get( subject_full_id )

            if query_source_gene_id is None or subject_source_gene_id is None:
                unmapped_full_ids.append( ( query_full_id, subject_full_id ) )
                continue

            # If a Source_Gene_ID does not appear in the coordinate table,
            # we cannot place it on a chromosome. Per zero-tolerance rule,
            # this is a fail-fast condition (proteome / coordinates out of
            # sync with the BLAST input). We still collect them all to
            # report at the end so the user sees the full mismatch.
            query_record = source_gene_ids___records.get( query_source_gene_id )
            subject_record = source_gene_ids___records.get( subject_source_gene_id )
            if query_record is None or subject_record is None:
                unmapped_full_ids.append( ( query_full_id, subject_full_id ) )
                continue

            query_chromosome = query_record[ 0 ]
            subject_chromosome = subject_record[ 0 ]

            if query_chromosome != subject_chromosome:
                hits_diff_chromosome += 1
                continue

            # Same chromosome → check window
            query_position = chromosomes_source_gene_ids___positions[ ( query_chromosome, query_source_gene_id ) ]
            subject_position = chromosomes_source_gene_ids___positions[ ( subject_chromosome, subject_source_gene_id ) ]
            if abs( query_position - subject_position ) <= window_radius:
                union_find.union( query_source_gene_id, subject_source_gene_id )
                hits_in_window += 1
            else:
                hits_outside_window += 1

    if unmapped_full_ids:
        logger.error( '' )
        logger.error( f'CRITICAL ERROR: {len( unmapped_full_ids )} BLAST hits reference genes not found in the proteome+coordinates index.' )
        logger.error( 'This indicates the proteome FASTA, gene_coordinates TSV, and self-BLAST report are out of sync.' )
        logger.error( 'Per the GIGANTIC zero-tolerance rule, hotspot calling cannot proceed under this ambiguity.' )
        logger.error( 'First 10 unmapped hit pairs:' )
        for query_id, subject_id in unmapped_full_ids[ :10 ]:
            logger.error( f'  query: {query_id}  |  subject: {subject_id}' )
        if len( unmapped_full_ids ) > 10:
            logger.error( f'  ... and {len( unmapped_full_ids ) - 10} more' )
        logger.error( '' )
        logger.error( 'Likely fixes:' )
        logger.error( '  - Confirm the gene_coordinates TSV was built from the SAME assembly/annotation as the proteome' )
        logger.error( '  - Confirm proteome Source_Gene_IDs (g_ field) match Source_Gene_ID values in the coords TSV' )
        return 1

    logger.info( '' )
    logger.info( f'  Hits processed:            {hits_processed}' )
    logger.info( f'  Hits within window:        {hits_in_window}  -> graph edges' )
    logger.info( f'  Hits cross-chromosome:     {hits_diff_chromosome}' )
    logger.info( f'  Hits outside window:       {hits_outside_window}' )
    logger.info( '' )

    # ---- Connected components → hotspots ----
    components = union_find.components()
    hotspot_records = []   # ( chromosome, hotspot_start, hotspot_end, member_source_gene_ids_sorted )
    for component in components:
        if len( component ) < args.minimum_paralog_count:
            continue
        # All members are guaranteed same chromosome by construction (we
        # only add edges within-chromosome). Verify defensively anyway.
        chromosome_set = { source_gene_ids___records[ sgi ][ 0 ] for sgi in component }
        if len( chromosome_set ) != 1:
            logger.error( f'CRITICAL ERROR: Hotspot component spans multiple chromosomes: {chromosome_set}; members={component}' )
            return 1
        chromosome = next( iter( chromosome_set ) )
        # Sort members by (start, end) for stable output order
        sorted_members = sorted(
            component,
            key = lambda sgi: ( source_gene_ids___records[ sgi ][ 1 ], source_gene_ids___records[ sgi ][ 2 ] ),
        )
        hotspot_start = source_gene_ids___records[ sorted_members[ 0 ] ][ 1 ]
        hotspot_end = source_gene_ids___records[ sorted_members[ -1 ] ][ 2 ]
        hotspot_records.append( ( chromosome, hotspot_start, hotspot_end, sorted_members ) )

    # Sort hotspots by chromosome then start for deterministic output ordering
    hotspot_records.sort( key = lambda r: ( r[ 0 ], r[ 1 ], r[ 2 ] ) )

    logger.info( f'  Hotspots called: {len( hotspot_records )}' )

    # ---- Write hotspots TSV ----
    hotspots_path = args.output_dir / f'3_ai-hotspots-{args.genus_species}.tsv'
    output = 'Hotspot_ID (deterministic identifier hotspot_e<evalue>_w<window>_<species>_<n>)\t'
    output += 'Chromosome (Seqid from gene coordinates table)\t'
    output += 'Hotspot_Start (1-based inclusive minimum Gene_Start across hotspot members)\t'
    output += 'Hotspot_End (1-based inclusive maximum Gene_End across hotspot members)\t'
    output += 'Paralog_Count (number of genes in this hotspot connected component)\t'
    output += 'Member_Source_Gene_IDs (comma delimited Source_Gene_IDs ordered by Gene_Start)\n'

    species_token = args.genus_species
    # Hotspot_ID format mirrors the GIGANTIC_0 pattern but parameterized.
    # Window may be passed as e.g. "20" or "200"; encode the actual value.
    for index, ( chromosome, hotspot_start, hotspot_end, members ) in enumerate( hotspot_records, start = 1 ):
        hotspot_id = f'hotspot_w{args.window_size}_{species_token}_{index:05d}'
        members_field = ','.join( members )
        output += hotspot_id + '\t' + chromosome + '\t' + str( hotspot_start ) + '\t' + str( hotspot_end ) + '\t' + str( len( members ) ) + '\t' + members_field + '\n'
    with open( hotspots_path, 'w' ) as output_hotspots:
        output_hotspots.write( output )
    logger.info( f'  Wrote {hotspots_path.name}' )

    # ---- Write summary ----
    summary_path = args.output_dir / f'3_ai-hotspot_summary-{args.genus_species}.tsv'
    summary_output = 'Genus_Species (species name in Genus_species format)\t'
    summary_output += 'Window_Size (gene-position window total used in this run)\t'
    summary_output += 'Minimum_Paralog_Count (minimum members required for a hotspot)\t'
    summary_output += 'Hits_Processed (filtered self-BLAST hit lines read)\t'
    summary_output += 'Hits_Within_Window (paralog edges added to graph)\t'
    summary_output += 'Hits_Cross_Chromosome (dropped because query and subject on different chromosomes)\t'
    summary_output += 'Hits_Outside_Window (dropped because positions exceeded window radius)\t'
    summary_output += 'Hotspot_Count (number of hotspots called)\t'
    summary_output += 'Hotspot_Member_Total (sum of Paralog_Count across hotspots)\n'
    member_total = sum( len( m ) for _, _, _, m in hotspot_records )
    summary_output += args.genus_species + '\t' + str( args.window_size ) + '\t' + str( args.minimum_paralog_count ) + '\t' + str( hits_processed ) + '\t' + str( hits_in_window ) + '\t' + str( hits_diff_chromosome ) + '\t' + str( hits_outside_window ) + '\t' + str( len( hotspot_records ) ) + '\t' + str( member_total ) + '\n'
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( summary_output )
    logger.info( f'  Wrote {summary_path.name}' )

    logger.info( 'Hotspot identification complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
