#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Three-axis dark-matter classification per species (Edsinger 2024)
# Human: Eric Edsinger

"""
GIGANTIC dark_proteome BLOCK_classify_dark_proteome - Script 003: Classify Per Species

Purpose:
    For one species, classify every gene in the proteome as DARK or
    ANNOTATED based on three independent axes (Edsinger 2024):

      axis_a — Reference BLAST    : gene has a top-non-self BLAST hit
                                    AGAINST one of the reference species
                                    (strict mode), or any non-self NR hit
                                    (broad mode).
      axis_b — Reference Orthogroup : gene is in an orthogroup that contains
                                      at least one reference-species gene.
      axis_c — HMM annotation      : gene has at least one annotation in
                                     any of the configured HMM databases
                                     (default Pfam + PANTHER).

    A gene is DARK if and only if all three axes are False.

Inputs (CLI):
    --proteome                       Path to <phyloname>-T1-proteome.aa
    --reference-blast                Path to per-species top-hits TSV
    --orthogroup-membership-index    Path to 2_ai-orthogroup_membership_index.tsv
    --hmm-database-names             Comma-separated db names (e.g. "pfam,panther")
    --hmm-annotation-paths           Comma-separated absolute paths (same order as db names)
    --reference-blast-mode           "strict_reference" | "broad_any_nr_hit"
    --reference-species              Comma-separated reference Genus_species names
    --genus-species                  Species being processed
    --output-dir                     Output directory (typically 3-output)

Outputs (in --output-dir):
    3_ai-dark_proteome-<Genus_species>.tsv
        Per-row, one row per gene:
        Full_GIGANTIC_Gene_ID, Source_Gene_ID, Has_Reference_Blast,
        In_Reference_Orthogroup, Has_HMM_Annotation, Status (DARK/ANNOTATED),
        Annotation_Sources_CSV
    3_ai-dark_proteome_summary-<Genus_species>.tsv
    3_ai-log-classify_per_species-<Genus_species>.log

Failure mode:
    Exits 1 (fail-fast) when:
      - Required CLI argument missing
      - Any required file missing
      - reference-blast-mode unrecognized
      - HMM database/path lists are different lengths
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path, genus_species: str ) -> logging.Logger:
    logger = logging.getLogger( f'classify_dark_proteome_{genus_species}' )
    logger.setLevel( logging.INFO )
    log_file = output_dir / f'3_ai-log-classify_per_species-{genus_species}.log'
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
    """Source_Gene_ID = the value after 'g_' prefix in a GIGANTIC FASTA header."""
    for part in full_id.split( '-' ):
        if part.startswith( 'g_' ):
            return part[ 2: ]
    return ''


def load_proteome_full_ids( proteome_path: Path, logger: logging.Logger ) -> list:
    """Return ordered list of full GIGANTIC IDs (one per FASTA record)."""
    full_ids = []
    with open( proteome_path, 'r' ) as input_proteome:
        for line in input_proteome:
            line = line.rstrip( '\n' )
            if line.startswith( '>' ):
                full_ids.append( line[ 1: ] )
    logger.info( f'  Loaded {len( full_ids )} GIGANTIC headers from proteome' )
    return full_ids


def load_reference_orthogroup_index( index_path: Path, logger: logging.Logger ) -> dict:
    """Read 2_ai-orthogroup_membership_index.tsv → { full_id: in_ref_og_bool }."""
    full_ids___in_reference_og = {}

    # Full_GIGANTIC_Gene_ID\tOrthogroup_ID\tIn_Reference_Orthogroup
    # g_X-t_..-p_..-n_..\tOG000123\tTrue
    with open( index_path, 'r' ) as input_index:
        header_seen = False
        for line in input_index:
            line = line.rstrip( '\n' )
            if not line:
                continue
            if not header_seen:
                header_seen = True
                continue
            parts = line.split( '\t' )
            if len( parts ) < 3:
                continue
            full_id = parts[ 0 ]
            in_ref_og = parts[ 2 ].strip().lower() == 'true'
            full_ids___in_reference_og[ full_id ] = in_ref_og
    logger.info( f'  Loaded {len( full_ids___in_reference_og )} gene -> orthogroup mappings' )
    return full_ids___in_reference_og


def load_reference_blast_axis_a(
    reference_blast_path: Path,
    mode: str,
    reference_species: list,
    logger: logging.Logger,
) -> set:
    """Return set of Full_GIGANTIC_Gene_IDs that pass axis-a.

    Strict mode (default):
      A gene passes axis-a if its Top_Non_Self_Hit_Header references one of
      the reference species. The header strings from
      one_direction_homologs/BLOCK_diamond_ncbi_nr include species names in
      square brackets (NCBI convention), e.g. "alpha-1-B glycoprotein
      [Homo sapiens]". We test each reference species name in both
      "Genus species" (space) and "Genus_species" (underscore) forms.

    Broad mode:
      A gene passes axis-a if Top_Non_Self_Hit_ID is non-empty (any NR hit
      at all qualifies). Less paper-faithful but more conservative about
      what's "really" dark.
    """
    if mode not in ( 'strict_reference', 'broad_any_nr_hit' ):
        logger.error( f'CRITICAL ERROR: unrecognized reference_blast_mode "{mode}"' )
        sys.exit( 1 )

    # Build the search-token list for strict mode (Genus species + Genus_species)
    reference_search_tokens = []
    for ref in reference_species:
        with_space = ref.replace( '_', ' ' )
        reference_search_tokens.append( with_space.lower() )
        reference_search_tokens.append( ref.lower() )

    full_ids_passing_axis_a = set()
    rows_seen = 0

    # Header (from one_direction_homologs/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits):
    # Query_Sequence_ID\tTop_10_Hit_IDs\t...\tTop_Non_Self_Hit_ID\tTop_Non_Self_Hit_Header\tTop_Non_Self_Hit_Percent_Identity\t...
    with open( reference_blast_path, 'r' ) as input_blast:
        header_line = input_blast.readline().rstrip( '\n' )
        header_columns = [ raw.split( ' (' )[ 0 ].strip() for raw in header_line.split( '\t' ) ]

        try:
            query_index = header_columns.index( 'Query_Sequence_ID' )
            top_id_index = header_columns.index( 'Top_Non_Self_Hit_ID' )
            top_header_index = header_columns.index( 'Top_Non_Self_Hit_Header' )
        except ValueError:
            logger.error( f'CRITICAL ERROR: Reference BLAST file {reference_blast_path.name} missing required columns.' )
            logger.error( f'Found columns: {header_columns}' )
            sys.exit( 1 )

        for line in input_blast:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if len( parts ) <= max( query_index, top_id_index, top_header_index ):
                continue
            rows_seen += 1
            query_id = parts[ query_index ]
            top_id = parts[ top_id_index ].strip()
            top_header = parts[ top_header_index ].strip()

            if mode == 'broad_any_nr_hit':
                if top_id and top_id != '-':
                    full_ids_passing_axis_a.add( query_id )
                continue

            # Strict mode
            header_lower = top_header.lower()
            for token in reference_search_tokens:
                if token and token in header_lower:
                    full_ids_passing_axis_a.add( query_id )
                    break

    logger.info( f'  Reference BLAST: {rows_seen} rows scanned, {len( full_ids_passing_axis_a )} genes pass axis-a (mode={mode})' )
    return full_ids_passing_axis_a


def load_hmm_axis_c( hmm_paths: list, logger: logging.Logger ) -> set:
    """Return set of Full_GIGANTIC_Gene_IDs that have at least one HMM annotation
    in any of the configured databases.

    InterProScan-parsed format (annotations_hmms/output_to_input/BLOCK_interproscan_parsed):
      Protein_Identifier\tMD5\tSequence_Length\tAnalysis_Database\tAccession\t...
    The first column is the full GIGANTIC gene ID. Presence of any data row
    for a given protein means it's annotated by that database.
    """
    annotated_full_ids = set()
    for hmm_path in hmm_paths:
        if not Path( hmm_path ).is_file():
            logger.warning( f'  HMM file not found: {hmm_path}' )
            continue
        # Protein_Identifier\tMD5\tSequence_Length\tAnalysis_Database\tAccession\t...
        # g_X-t_..-p_..-n_..\t<md5>\t495\tPANTHER\tPTHR11738\t...
        with open( hmm_path, 'r' ) as input_hmm:
            header_seen = False
            for line in input_hmm:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                if not header_seen:
                    header_seen = True
                    continue
                parts = line.split( '\t' )
                if not parts or not parts[ 0 ]:
                    continue
                annotated_full_ids.add( parts[ 0 ] )
    logger.info( f'  HMM annotation: {len( annotated_full_ids )} unique genes have at least one HMM hit (axis-c)' )
    return annotated_full_ids


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--proteome', required = True, type = Path )
    parser.add_argument( '--reference-blast', required = True, type = Path )
    parser.add_argument( '--orthogroup-membership-index', required = True, type = Path )
    parser.add_argument( '--hmm-database-names', required = True )
    parser.add_argument( '--hmm-annotation-paths', required = True )
    parser.add_argument( '--reference-blast-mode', required = True, choices = [ 'strict_reference', 'broad_any_nr_hit' ] )
    parser.add_argument( '--reference-species', required = True )
    parser.add_argument( '--genus-species', required = True )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir, args.genus_species )

    hmm_database_names = [ db.strip() for db in args.hmm_database_names.split( ',' ) if db.strip() ]
    hmm_annotation_paths = [ p.strip() for p in args.hmm_annotation_paths.split( ',' ) if p.strip() ]
    reference_species = [ rs.strip() for rs in args.reference_species.split( ',' ) if rs.strip() ]

    if len( hmm_database_names ) != len( hmm_annotation_paths ):
        logger.error( f'CRITICAL ERROR: HMM db name count ({len( hmm_database_names )}) != path count ({len( hmm_annotation_paths )})' )
        return 1

    logger.info( '=' * 72 )
    logger.info( f'GIGANTIC dark_proteome - Script 003: Classify Per Species ({args.genus_species})' )
    logger.info( '=' * 72 )
    logger.info( f'Proteome:                  {args.proteome}' )
    logger.info( f'Reference BLAST:           {args.reference_blast}' )
    logger.info( f'Orthogroup index:          {args.orthogroup_membership_index}' )
    logger.info( f'HMM databases:             {hmm_database_names}' )
    logger.info( f'Reference BLAST mode:      {args.reference_blast_mode}' )
    logger.info( f'Reference species:         {reference_species}' )
    logger.info( f'Output dir:                {args.output_dir}' )
    logger.info( '' )

    for label, path in [
        ( 'Proteome',                  args.proteome ),
        ( 'Reference BLAST',           args.reference_blast ),
        ( 'Orthogroup index',          args.orthogroup_membership_index ),
    ]:
        if not path.is_file():
            logger.error( f'CRITICAL ERROR: {label} file not found: {path}' )
            return 1

    # ---- Load inputs ----
    proteome_full_ids = load_proteome_full_ids( args.proteome, logger )
    full_ids___in_reference_og = load_reference_orthogroup_index( args.orthogroup_membership_index, logger )
    full_ids_passing_axis_a = load_reference_blast_axis_a(
        args.reference_blast,
        args.reference_blast_mode,
        reference_species,
        logger,
    )
    full_ids_passing_axis_c = load_hmm_axis_c( hmm_annotation_paths, logger )

    # ---- Classify per gene ----
    dark_count = 0
    annotated_count = 0
    axis_a_count = 0
    axis_b_count = 0
    axis_c_count = 0

    output = 'Full_GIGANTIC_Gene_ID (complete FASTA header value of gene)\t'
    output += 'Source_Gene_ID (g_ field stripped from full ID)\t'
    output += 'Has_Reference_Blast (axis_a True if gene has BLAST hit in mode-defined reference set)\t'
    output += 'In_Reference_Orthogroup (axis_b True if gene is in orthogroup containing reference species)\t'
    output += 'Has_HMM_Annotation (axis_c True if gene has at least one annotation in configured HMM databases)\t'
    output += 'Status (DARK if all three axes False else ANNOTATED)\t'
    output += 'Annotation_Sources_CSV (comma delimited axes that fired or empty for DARK)\n'

    for full_id in proteome_full_ids:
        source_gene_id = parse_full_id_to_source_gene_id( full_id )
        axis_a = full_id in full_ids_passing_axis_a
        axis_b = full_ids___in_reference_og.get( full_id, False )
        axis_c = full_id in full_ids_passing_axis_c

        if axis_a:
            axis_a_count += 1
        if axis_b:
            axis_b_count += 1
        if axis_c:
            axis_c_count += 1

        sources = []
        if axis_a:
            sources.append( 'reference_blast' )
        if axis_b:
            sources.append( 'reference_orthogroup' )
        if axis_c:
            sources.append( 'hmm_annotation' )

        if not sources:
            status = 'DARK'
            dark_count += 1
        else:
            status = 'ANNOTATED'
            annotated_count += 1

        output += full_id + '\t' + source_gene_id + '\t' + str( axis_a ) + '\t' + str( axis_b ) + '\t' + str( axis_c ) + '\t' + status + '\t' + ','.join( sources ) + '\n'

    classification_path = args.output_dir / f'3_ai-dark_proteome-{args.genus_species}.tsv'
    with open( classification_path, 'w' ) as output_classification:
        output_classification.write( output )
    logger.info( f'  Wrote {classification_path.name} ({len( proteome_full_ids )} rows)' )

    # ---- Summary ----
    summary_path = args.output_dir / f'3_ai-dark_proteome_summary-{args.genus_species}.tsv'
    summary_output = 'Genus_Species (species name in Genus_species format)\t'
    summary_output += 'Reference_Blast_Mode (strict_reference or broad_any_nr_hit applied to axis_a)\t'
    summary_output += 'Hmm_Databases_CSV (comma delimited HMM databases used for axis_c)\t'
    summary_output += 'Gene_Total (number of gene records in the proteome)\t'
    summary_output += 'Annotated_Count (genes annotated by at least one of the three axes)\t'
    summary_output += 'Dark_Count (genes failing all three axes)\t'
    summary_output += 'Dark_Percent (Dark_Count divided by Gene_Total times 100)\t'
    summary_output += 'Axis_A_Reference_Blast_Count (genes passing axis_a)\t'
    summary_output += 'Axis_B_Reference_Orthogroup_Count (genes passing axis_b)\t'
    summary_output += 'Axis_C_HMM_Annotation_Count (genes passing axis_c)\n'
    dark_pct = ( dark_count / len( proteome_full_ids ) * 100 ) if proteome_full_ids else 0.0
    summary_output += args.genus_species + '\t' + args.reference_blast_mode + '\t' + ','.join( hmm_database_names ) + '\t' + str( len( proteome_full_ids ) ) + '\t' + str( annotated_count ) + '\t' + str( dark_count ) + '\t' + f'{dark_pct:.3f}' + '\t' + str( axis_a_count ) + '\t' + str( axis_b_count ) + '\t' + str( axis_c_count ) + '\n'
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( summary_output )
    logger.info( f'  Wrote {summary_path.name}' )

    logger.info( '' )
    logger.info( f'  DARK:                  {dark_count} ({dark_pct:.2f}%)' )
    logger.info( f'  ANNOTATED:             {annotated_count}' )
    logger.info( f'  axis-a hits:           {axis_a_count}' )
    logger.info( f'  axis-b hits:           {axis_b_count}' )
    logger.info( f'  axis-c hits:           {axis_c_count}' )
    logger.info( 'Classification complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
