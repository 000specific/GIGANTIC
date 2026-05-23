#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Build set of orthogroups that contain at least one reference species gene
# Human: Eric Edsinger

"""
GIGANTIC dark_proteome BLOCK_classify_dark_proteome - Script 002: Build Reference Orthogroup Set

Purpose:
    One-time project-level pre-processing: walk the project orthogroups TSV
    and emit the set of orthogroup IDs that contain at least one gene from
    one of the configured reference species. This set drives axis (b) of the
    dark-matter classification — a gene is "annotated by orthogroups" if its
    OG belongs to this set.

    Doing this once up front means the per-species classification fan-out
    only needs a fast set membership check, not a full orthogroups walk.

Inputs (CLI):
    --orthogroups-file         Path to orthogroups_gigantic_ids.tsv
                               Format: tab-separated, first column = OG ID,
                               remaining columns = full GIGANTIC gene IDs.
                               GIGANTIC gene ID format:
                                 g_<source_id>-t_<tx>-p_<prot>-n_<phyloname>
                               (the n_ field encodes the phyloname which
                               ends in Genus_species)
    --reference-species        Comma-separated reference Genus_species names
    --output-dir               Output directory (typically 2-output)

Outputs (in --output-dir):
    2_ai-reference_orthogroups.tsv
        One row per OG containing reference species:
        Orthogroup_ID, Reference_Species_Members_CSV
    2_ai-orthogroup_membership_index.tsv
        Per-row: Full_GIGANTIC_Gene_ID, Orthogroup_ID, In_Reference_Orthogroup
        Used by script 003 as a fast lookup index.
    2_ai-reference_orthogroup_summary.tsv
        Single-row totals.
    2_ai-log-build_reference_orthogroup_set.log

Failure mode:
    Exits 1 (fail-fast) when:
      - Required inputs missing
      - Orthogroups file empty
      - Zero reference orthogroups found (axes-(b) would be vacuous)
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    logger = logging.getLogger( 'build_reference_orthogroup_set' )
    logger.setLevel( logging.INFO )
    log_file = output_dir / '2_ai-log-build_reference_orthogroup_set.log'
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


def extract_phyloname_from_full_id( full_id: str ) -> str:
    """Pull the n_<phyloname> field from a GIGANTIC gene ID.

    GIGANTIC ID format: g_<source>-t_<tx>-p_<prot>-n_<phyloname>
    where phyloname uses underscore-separated taxonomic levels but the
    field separator is dash. We split on dash and find the n_ prefix; the
    phyloname is everything after 'n_' (which itself contains underscores).
    """
    parts_full_id = full_id.split( '-' )
    for index, part in enumerate( parts_full_id ):
        if part.startswith( 'n_' ):
            # The phyloname starts with parts_full_id[index][2:] and continues
            # through any subsequent dash-joined fragments (it shouldn't, but
            # defensively rejoin in case the phyloname itself had dashes,
            # which CLAUDE.md says it shouldn't).
            phyloname_parts = [ part[ 2: ] ] + parts_full_id[ index + 1: ]
            return '-'.join( phyloname_parts )
    return ''


def extract_genus_species_from_phyloname( phyloname: str ) -> str:
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) < 7:
        return ''
    genus = parts_phyloname[ 5 ]
    species = '_'.join( parts_phyloname[ 6: ] )
    return genus + '_' + species


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--orthogroups-file', required = True, type = Path )
    parser.add_argument( '--reference-species', required = True, help = 'Comma-separated Genus_species names' )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir )

    reference_species = set( rs.strip() for rs in args.reference_species.split( ',' ) if rs.strip() )

    logger.info( '=' * 72 )
    logger.info( 'GIGANTIC dark_proteome - Script 002: Build Reference Orthogroup Set' )
    logger.info( '=' * 72 )
    logger.info( f'Orthogroups file:    {args.orthogroups_file}' )
    logger.info( f'Reference species:   {sorted( reference_species )}' )
    logger.info( f'Output dir:          {args.output_dir}' )
    logger.info( '' )

    if not args.orthogroups_file.is_file():
        logger.error( f'CRITICAL ERROR: Orthogroups file not found: {args.orthogroups_file}' )
        return 1
    if not reference_species:
        logger.error( 'CRITICAL ERROR: No reference species configured.' )
        return 1

    # ---- Walk the orthogroups TSV ----
    # Layout: tab-separated; col 0 = OG_ID; cols 1+ = full GIGANTIC gene IDs
    # OG000000\tg_g123-t_..-p_..-n_Phyl_..._Genus_species\tg_..._species2\t...
    reference_orthogroup_ids = set()
    reference_orthogroup_records = []   # ( og_id, [ ref_species_members_full_ids ] )

    # Per-gene index: full_id -> ( og_id, in_reference_orthogroup )
    full_ids___og_records = {}

    total_ogs = 0
    total_genes = 0

    logger.info( 'Walking orthogroups TSV...' )
    with open( args.orthogroups_file, 'r' ) as input_orthogroups:
        for line in input_orthogroups:
            line = line.rstrip( '\n' )
            if not line.strip():
                continue
            parts = line.split( '\t' )
            if len( parts ) < 2:
                continue
            og_id = parts[ 0 ]
            member_full_ids = parts[ 1: ]
            total_ogs += 1
            total_genes += len( member_full_ids )

            ref_members_in_this_og = []
            for full_id in member_full_ids:
                if not full_id:
                    continue
                phyloname = extract_phyloname_from_full_id( full_id )
                if not phyloname:
                    continue
                genus_species = extract_genus_species_from_phyloname( phyloname )
                if genus_species in reference_species:
                    ref_members_in_this_og.append( full_id )

            in_reference_og = len( ref_members_in_this_og ) > 0
            if in_reference_og:
                reference_orthogroup_ids.add( og_id )
                reference_orthogroup_records.append( ( og_id, ref_members_in_this_og ) )

            for full_id in member_full_ids:
                if full_id:
                    full_ids___og_records[ full_id ] = ( og_id, in_reference_og )

    logger.info( f'  Total orthogroups read:           {total_ogs}' )
    logger.info( f'  Total gene memberships:           {total_genes}' )
    logger.info( f'  Reference orthogroups (axis-b):   {len( reference_orthogroup_ids )}' )
    logger.info( f'  Genes mapped to an orthogroup:    {len( full_ids___og_records )}' )
    logger.info( '' )

    if not reference_orthogroup_ids:
        logger.error( 'CRITICAL ERROR: Zero reference orthogroups found. axis-(b) would be vacuous.' )
        logger.error( 'Likely cause: reference_species names do not match phylonames in the orthogroups TSV.' )
        return 1

    # ---- Write reference orthogroups TSV ----
    ref_og_path = args.output_dir / '2_ai-reference_orthogroups.tsv'
    output = 'Orthogroup_ID (orthogroup identifier from orthogroups file)\t'
    output += 'Reference_Species_Member_Full_GIGANTIC_IDs (comma delimited reference species member gene IDs in this orthogroup)\n'
    for og_id, ref_members in reference_orthogroup_records:
        output += og_id + '\t' + ','.join( ref_members ) + '\n'
    with open( ref_og_path, 'w' ) as output_ref_og:
        output_ref_og.write( output )
    logger.info( f'  Wrote {ref_og_path.name} ({len( reference_orthogroup_records )} rows)' )

    # ---- Write per-gene orthogroup membership index ----
    index_path = args.output_dir / '2_ai-orthogroup_membership_index.tsv'
    output = 'Full_GIGANTIC_Gene_ID (complete FASTA header value of gene)\t'
    output += 'Orthogroup_ID (orthogroup containing this gene)\t'
    output += 'In_Reference_Orthogroup (True if orthogroup contains at least one reference species gene)\n'
    for full_id, ( og_id, in_ref_og ) in full_ids___og_records.items():
        output += full_id + '\t' + og_id + '\t' + str( in_ref_og ) + '\n'
    with open( index_path, 'w' ) as output_index:
        output_index.write( output )
    logger.info( f'  Wrote {index_path.name} ({len( full_ids___og_records )} rows)' )

    # ---- Write summary ----
    summary_path = args.output_dir / '2_ai-reference_orthogroup_summary.tsv'
    output = 'Reference_Species_Configured (comma delimited reference Genus_species names)\t'
    output += 'Total_Orthogroups (orthogroups read from orthogroups file)\t'
    output += 'Total_Gene_Memberships (sum of member counts across all orthogroups)\t'
    output += 'Reference_Orthogroup_Count (orthogroups containing at least one reference species member)\t'
    output += 'Reference_Orthogroup_Percent (count divided by total orthogroups times 100)\n'
    pct = ( len( reference_orthogroup_ids ) / total_ogs * 100 ) if total_ogs > 0 else 0.0
    output += ','.join( sorted( reference_species ) ) + '\t' + str( total_ogs ) + '\t' + str( total_genes ) + '\t' + str( len( reference_orthogroup_ids ) ) + '\t' + f'{pct:.3f}' + '\n'
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( output )
    logger.info( f'  Wrote {summary_path.name}' )

    logger.info( 'Reference orthogroup set built.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
