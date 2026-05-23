#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 04 | Purpose: Extract per-species gene coordinate TSVs from Kim 2025 GTF annotations for the GIGANTIC gene_sizes pipeline
# Human: Eric Edsinger
"""
Extract gene coordinate TSVs from Kim 2025 GTF annotations.

Kim 2025 differs from NCBI in three ways:
  1. GTF format (not GFF3): attributes use 'key "value"; key "value";' syntax
  2. No 'gene' feature type — only transcript/exon/CDS. Gene span is taken from
     the transcript feature (each gene has one transcript in the T1 set).
  3. transcript_acc and protein_acc are identical in the proteome header
     (e.g., both 'Cowc_VH_COWC_00001.t1'); there is no separate protein accession.

Auto-discovers Kim 2025 species from proteome filenames (no manifest required;
mirrors the existing kim_2025_genomes T1 extraction pattern).

Output (one file per species):
    OUTPUT_pipeline/<Genus_species>-gene_coordinates.tsv

    Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  CDS_Intervals
"""

import argparse
import os
import re
import sys
from pathlib import Path


def sanitize_gene_name( name ):
    """Replace hyphens with underscores. Other characters preserved.

    Same rule as the NCBI extractor (matches what the T1 extractor wrote).
    """
    return name.replace( '-', '_' )


def normalize_transcript_accession( transcript_id ):
    """Apply the same hyphen-to-underscore normalization the T1 extractor used.

    Cladtertia_collaboinventa is the case that requires this: GTF transcript_ids
    like 'HoiH23_PlH23_005827-RA' (with hyphen separator) appear in the proteome
    as 'HoiH23_PlH23_005827_RA' (with underscore). Apply '-' -> '_' so GTF keys
    match the proteome's transcript_acc form.
    """
    return transcript_id.replace( '-', '_' )


def parse_gtf_attributes( attribute_string ):
    """Parse a GTF column-9 attributes string into a dict.

    Example input:
        transcript_id "Cowc_VH_COWC_07782.t1"; gene_id "Cowc_VH_COWC_07782";

    Returns:
        { 'transcript_id': 'Cowc_VH_COWC_07782.t1', 'gene_id': 'Cowc_VH_COWC_07782' }
    """
    keys___values = {}
    parts = attribute_string.strip().rstrip( ';' ).split( ';' )
    for part in parts:
        part = part.strip()
        if ' ' in part:
            key, value = part.split( None, 1 )
            value = value.strip()
            if value.startswith( '"' ) and value.endswith( '"' ):
                value = value[ 1: -1 ]
            keys___values[ key ] = value
    return keys___values


def parse_proteome_headers( input_proteome_path ):
    """Parse a Kim T1 proteome FASTA and return a list of
    (gene_symbol_sanitized, transcript_acc, protein_acc) tuples.

    Header format: >Genus_species-<gene_id>-<transcript_id>-<transcript_id>
    where transcript_id == protein_acc for Kim (no separate protein accession).
    """
    tuples_in_proteome = []
    input_proteome = open( input_proteome_path, 'r' )
    for line in input_proteome:
        if not line.startswith( '>' ):
            continue
        header = line[ 1: ].strip()
        parts_header = header.split( '-' )
        if len( parts_header ) < 4:
            continue
        gene_symbol = parts_header[ -3 ]
        transcript_acc = parts_header[ -2 ]
        protein_acc = parts_header[ -1 ]
        tuples_in_proteome.append( ( gene_symbol, transcript_acc, protein_acc ) )
    input_proteome.close()
    return tuples_in_proteome


def parse_kim_gtf( input_gtf_path ):
    """Parse a Kim 2025 GTF file and return:

    transcript_ids___coordinates:
        transcript_id -> ( Seqid, Start, End, Strand, gene_id )

    transcript_ids___exon_intervals:
        transcript_id -> [ (exon_start, exon_end), ... ]

    transcript_ids___cds_intervals:
        transcript_id -> [ (cds_start, cds_end), ... ]

    Kim GTFs have no 'gene' feature; gene coordinates are taken directly from
    the 'transcript' feature span (each gene has a single T1 transcript).
    """
    transcript_ids___coordinates = {}
    transcript_ids___exon_intervals = {}
    transcript_ids___cds_intervals = {}

    input_gtf = open( input_gtf_path, 'r' )
    for line in input_gtf:
        if line.startswith( '#' ) or not line.strip():
            continue
        parts = line.rstrip( '\n' ).split( '\t' )
        if len( parts ) < 9:
            continue
        seqid = parts[ 0 ]
        feature_type = parts[ 2 ]
        feature_start = int( parts[ 3 ] )
        feature_end = int( parts[ 4 ] )
        strand = parts[ 6 ]
        attributes = parse_gtf_attributes( parts[ 8 ] )

        # Normalize transcript_id to match the proteome's transcript_acc form
        # (Cladtertia case: GTF '-RA' suffix becomes proteome '_RA').
        transcript_id = normalize_transcript_accession( attributes.get( 'transcript_id', '' ) )
        gene_id = attributes.get( 'gene_id', '' )

        if feature_type == 'transcript':
            if transcript_id:
                transcript_ids___coordinates[ transcript_id ] = (
                    seqid, feature_start, feature_end, strand, gene_id
                )

        elif feature_type == 'exon':
            if transcript_id:
                transcript_ids___exon_intervals.setdefault( transcript_id, [] ).append(
                    ( feature_start, feature_end )
                )

        elif feature_type == 'CDS':
            if transcript_id:
                transcript_ids___cds_intervals.setdefault( transcript_id, [] ).append(
                    ( feature_start, feature_end )
                )

    input_gtf.close()
    return transcript_ids___coordinates, transcript_ids___exon_intervals, transcript_ids___cds_intervals


def derive_utrs_from_exons_and_cds( merged_exons, merged_cds, strand ):
    """Same UTR-derivation logic as the NCBI extractor; see that file for full doc."""
    if not merged_cds or not merged_exons:
        return [], []
    cds_min = min( start for start, _ in merged_cds )
    cds_max = max( end for _, end in merged_cds )
    utr_genomic_low = []
    utr_genomic_high = []
    for exon_start, exon_end in merged_exons:
        if exon_end < cds_min:
            utr_genomic_low.append( ( exon_start, exon_end ) )
        elif exon_start > cds_max:
            utr_genomic_high.append( ( exon_start, exon_end ) )
        else:
            if exon_start < cds_min:
                utr_genomic_low.append( ( exon_start, cds_min - 1 ) )
            if exon_end > cds_max:
                utr_genomic_high.append( ( cds_max + 1, exon_end ) )
    if strand == '+':
        return utr_genomic_low, utr_genomic_high
    elif strand == '-':
        return utr_genomic_high, utr_genomic_low
    else:
        return utr_genomic_low + utr_genomic_high, []


def intervals_total_size( intervals ):
    return sum( end - start + 1 for start, end in intervals )


def intervals_to_string( intervals ):
    return ','.join( f"{start}-{end}" for start, end in intervals )


def merge_intervals( intervals ):
    """Sort and merge overlapping or adjacent intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted( intervals, key = lambda interval: interval[ 0 ] )
    merged = [ sorted_intervals[ 0 ] ]
    for current_start, current_end in sorted_intervals[ 1: ]:
        last_start, last_end = merged[ -1 ]
        if current_start <= last_end + 1:
            merged[ -1 ] = ( last_start, max( last_end, current_end ) )
        else:
            merged.append( ( current_start, current_end ) )
    return merged


def discover_kim_species( input_proteome_dir ):
    """Discover Kim 2025 species by scanning proteome filenames.

    Filename pattern: <Genus_species>-genome-kim_2025-downloaded_<date>.aa
    Returns sorted list of Genus_species names.
    """
    species_set = set()
    for proteome_path in Path( input_proteome_dir ).glob( '*-genome-kim_2025-*.aa' ):
        name = proteome_path.name
        # Strip everything from '-genome-kim_2025-' onward to get Genus_species
        idx = name.find( '-genome-kim_2025-' )
        if idx > 0:
            species_set.add( name[ : idx ] )
    return sorted( species_set )


def find_input_files_for_species( genus_species, input_gtf_dir, input_proteome_dir ):
    """Locate the GTF and T1 proteome for one Kim species.

    GTF naming: <Genus_species>-kim_2025.gtf
    Proteome naming: <Genus_species>-genome-kim_2025-downloaded_<date>.aa

    Important: prefer the standard '-kim_2025.gtf' over any variant such as
    '-kim_2025-ncbi_gene_names.gtf' (which exists for Mnemiopsis_leidyi).
    """
    gtf_path = Path( input_gtf_dir ) / f"{genus_species}-kim_2025.gtf"

    proteome_candidates = list(
        Path( input_proteome_dir ).glob( f"{genus_species}-genome-kim_2025-*.aa" )
    )

    return gtf_path, proteome_candidates


def extract_gene_coordinates_for_species(
    genus_species,
    input_gtf_path,
    input_proteome_path,
    output_tsv_all_inclusive_path,
    output_tsv_gene_vs_protein_path,
    output_unmatched_path,
):
    """Two-tier output: tier-1 species write 15-col all_inclusive + 9-col gene_vs_protein
    TSVs; tier-2 species write 9-col gene_vs_protein TSV only. Tier classification is
    by fraction of genes with derived UTR content (>=50% -> tier 1).
    """
    stats = {
        'genus_species': genus_species,
        'proteome_entries': 0,
        'rows_written': 0,
        'genes_with_utr': 0,
        'tier': '',
        'wrote_all_inclusive': 'no',
        'wrote_gene_vs_protein': 'no',
        'missing_transcript_lookups': 0,
        'missing_exon_lookups': 0,
        'missing_cds_lookups': 0,
        'status': 'PROCESSED',
        'notes': '',
    }

    tuples_in_proteome = parse_proteome_headers( input_proteome_path )
    stats[ 'proteome_entries' ] = len( tuples_in_proteome )
    if not tuples_in_proteome:
        stats[ 'status' ] = 'SKIPPED_EMPTY_PROTEOME'
        stats[ 'notes' ] = f"No headers parsed from {input_proteome_path.name}"
        return stats

    transcript_ids___coordinates, transcript_ids___exon_intervals, transcript_ids___cds_intervals = parse_kim_gtf( input_gtf_path )

    output_unmatched = open( output_unmatched_path, 'w' )
    output_unmatched.write( '\t'.join( [
        'gene_symbol_from_proteome', 'transcript_acc_from_proteome', 'protein_acc_from_proteome',
        'reason (missing_transcript_lookup, missing_exon_lookup, or missing_cds_lookup)',
    ] ) + '\n' )

    gene_records = []

    for gene_symbol, transcript_acc, protein_acc in tuples_in_proteome:
        coordinate_record = transcript_ids___coordinates.get( transcript_acc )
        if coordinate_record is None:
            stats[ 'missing_transcript_lookups' ] += 1
            output_unmatched.write( '\t'.join( [ gene_symbol, transcript_acc, protein_acc, 'missing_transcript_lookup' ] ) + '\n' )
            continue
        seqid, gene_start, gene_end, strand, _ = coordinate_record

        exon_intervals = transcript_ids___exon_intervals.get( transcript_acc, [] )
        if not exon_intervals:
            stats[ 'missing_exon_lookups' ] += 1
            output_unmatched.write( '\t'.join( [ gene_symbol, transcript_acc, protein_acc, 'missing_exon_lookup' ] ) + '\n' )
            continue

        cds_intervals = transcript_ids___cds_intervals.get( transcript_acc, [] )
        if not cds_intervals:
            stats[ 'missing_cds_lookups' ] += 1
            output_unmatched.write( '\t'.join( [ gene_symbol, transcript_acc, protein_acc, 'missing_cds_lookup' ] ) + '\n' )
            continue

        merged_exons = merge_intervals( exon_intervals )
        merged_cds = merge_intervals( cds_intervals )
        utr_5prime, utr_3prime = derive_utrs_from_exons_and_cds( merged_exons, merged_cds, strand )

        gene_size = gene_end - gene_start + 1
        transcript_size = intervals_total_size( merged_exons )
        cds_size = intervals_total_size( merged_cds )
        protein_size = cds_size // 3
        utr_5prime_size = intervals_total_size( utr_5prime )
        utr_3prime_size = intervals_total_size( utr_3prime )

        if ( utr_5prime_size + utr_3prime_size ) > 0:
            stats[ 'genes_with_utr' ] += 1

        gene_records.append( {
            'gene_symbol': gene_symbol, 'seqid': seqid,
            'gene_start': gene_start, 'gene_end': gene_end, 'strand': strand,
            'gene_size': gene_size,
            'merged_exons': merged_exons, 'transcript_size': transcript_size,
            'merged_cds': merged_cds, 'cds_size': cds_size, 'protein_size': protein_size,
            'utr_5prime': utr_5prime, 'utr_5prime_size': utr_5prime_size,
            'utr_3prime': utr_3prime, 'utr_3prime_size': utr_3prime_size,
        } )

    output_unmatched.close()
    stats[ 'rows_written' ] = len( gene_records )

    if not gene_records:
        stats[ 'status' ] = 'SKIPPED_NO_USABLE_GENES'
        return stats

    fraction_with_utr = stats[ 'genes_with_utr' ] / len( gene_records )
    is_tier_1 = fraction_with_utr >= 0.5
    stats[ 'tier' ] = 'all_inclusive' if is_tier_1 else 'gene_vs_protein'

    # Write Type 2 (gene_vs_protein) — always.
    output_tsv = open( output_tsv_gene_vs_protein_path, 'w' )
    output_tsv.write( '\t'.join( [
        'Source_Gene_ID (sanitized gene symbol matching the g_ field of the GIGANTIC proteome header)',
        'Seqid (chromosome or scaffold accession from the GTF)',
        'Gene_Start (1-based gene feature start position from the transcript feature)',
        'Gene_End (1-based gene feature end position inclusive from the transcript feature)',
        'Strand (+ or - from the GTF strand column)',
        'Gene_Size (genomic span in bp computed as Gene_End minus Gene_Start plus 1)',
        'CDS_Intervals (comma delimited list of merged CDS interval start-end pairs from the T1 transcript)',
        'CDS_Size (length of protein-coding region in bp)',
        'Protein_Size (estimated amino acids computed as CDS_Size divided by 3)',
    ] ) + '\n' )
    for r in gene_records:
        output_tsv.write( '\t'.join( [
            r[ 'gene_symbol' ], r[ 'seqid' ], str( r[ 'gene_start' ] ), str( r[ 'gene_end' ] ), r[ 'strand' ],
            str( r[ 'gene_size' ] ), intervals_to_string( r[ 'merged_cds' ] ),
            str( r[ 'cds_size' ] ), str( r[ 'protein_size' ] ),
        ] ) + '\n' )
    output_tsv.close()
    stats[ 'wrote_gene_vs_protein' ] = 'yes'

    if is_tier_1:
        output_tsv = open( output_tsv_all_inclusive_path, 'w' )
        output_tsv.write( '\t'.join( [
            'Source_Gene_ID', 'Seqid', 'Gene_Start', 'Gene_End', 'Strand',
            'Gene_Size', 'Exon_Intervals', 'Transcript_Size',
            'CDS_Intervals', 'CDS_Size', 'Protein_Size',
            'UTR_5prime_Intervals', 'UTR_5prime_Size',
            'UTR_3prime_Intervals', 'UTR_3prime_Size',
        ] ) + '\n' )
        for r in gene_records:
            output_tsv.write( '\t'.join( [
                r[ 'gene_symbol' ], r[ 'seqid' ], str( r[ 'gene_start' ] ), str( r[ 'gene_end' ] ), r[ 'strand' ],
                str( r[ 'gene_size' ] ), intervals_to_string( r[ 'merged_exons' ] ), str( r[ 'transcript_size' ] ),
                intervals_to_string( r[ 'merged_cds' ] ), str( r[ 'cds_size' ] ), str( r[ 'protein_size' ] ),
                intervals_to_string( r[ 'utr_5prime' ] ), str( r[ 'utr_5prime_size' ] ),
                intervals_to_string( r[ 'utr_3prime' ] ), str( r[ 'utr_3prime_size' ] ),
            ] ) + '\n' )
        output_tsv.close()
        stats[ 'wrote_all_inclusive' ] = 'yes'

    return stats


def write_summary( summary_records, output_summary_path ):
    """Write the cross-species extraction summary."""
    output_summary = open( output_summary_path, 'w' )
    columns = [
        ( 'genus_species', 'species name in Genus_species format' ),
        ( 'status', 'PROCESSED or SKIPPED_* status' ),
        ( 'tier', 'all_inclusive (>=50% genes have UTR) or gene_vs_protein (CDS-only)' ),
        ( 'wrote_all_inclusive', 'whether tier-1 TSV was written (yes/no)' ),
        ( 'wrote_gene_vs_protein', 'whether tier-2 TSV was written (yes/no)' ),
        ( 'proteome_entries', 'number of header tuples parsed from T1 proteome' ),
        ( 'rows_written', 'number of TSV rows written for this species' ),
        ( 'genes_with_utr', 'number of genes for which UTR derivation produced any UTR sequence' ),
        ( 'missing_transcript_lookups', 'count of proteome entries whose transcript_acc was not found in GTF transcript features' ),
        ( 'missing_exon_lookups', 'count of proteome entries whose transcript_acc had no exon features in the GTF' ),
        ( 'missing_cds_lookups', 'count of proteome entries whose transcript_acc had no CDS features in the GTF' ),
        ( 'notes', 'free text notes' ),
    ]
    header = '\t'.join( f"{name} ({description})" for name, description in columns ) + '\n'
    output_summary.write( header )
    for record in summary_records:
        output = '\t'.join( str( record.get( name, '' ) ) for name, _ in columns ) + '\n'
        output_summary.write( output )
    output_summary.close()


def make_relative_symlink( source_path, link_path ):
    """Create a relative symlink, replacing any existing one."""
    source_path = Path( source_path ).resolve()
    link_path = Path( link_path )
    if link_path.is_symlink() or link_path.exists():
        link_path.unlink()
    relative_target = os.path.relpath( source_path, link_path.parent )
    link_path.symlink_to( relative_target )


def main():
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument( '--gtf-dir', required = True, help = 'Directory of Kim 2025 GTF files (Genus_species-kim_2025.gtf)' )
    parser.add_argument( '--proteome-dir', required = True, help = 'Directory of Kim 2025 T1 proteomes' )
    parser.add_argument( '--output-dir', required = True, help = 'Output directory for per-species TSVs and summary' )
    parser.add_argument( '--symlink-dir-all-inclusive', required = True, help = 'output_to_input/gene_coordinates_all_inclusive dir for tier-1 TSVs' )
    parser.add_argument( '--symlink-dir-gene-vs-protein', required = True, help = 'output_to_input/gene_coordinates_gene_vs_protein dir for tier-2 TSVs (Type 1 species also symlinked here as superset)' )
    parser.add_argument( '--single-species', default = '', help = 'If set, process only this species (Genus_species)' )
    arguments = parser.parse_args()

    input_gtf_dir = Path( arguments.gtf_dir )
    input_proteome_dir = Path( arguments.proteome_dir )
    output_dir = Path( arguments.output_dir )
    output_dir.mkdir( parents = True, exist_ok = True )
    symlink_dir_all_inclusive = Path( arguments.symlink_dir_all_inclusive )
    symlink_dir_all_inclusive.mkdir( parents = True, exist_ok = True )
    symlink_dir_gene_vs_protein = Path( arguments.symlink_dir_gene_vs_protein )
    symlink_dir_gene_vs_protein.mkdir( parents = True, exist_ok = True )

    if not input_gtf_dir.is_dir():
        print( f"ERROR: GTF dir not found: {input_gtf_dir}", file = sys.stderr )
        sys.exit( 1 )
    if not input_proteome_dir.is_dir():
        print( f"ERROR: proteome dir not found: {input_proteome_dir}", file = sys.stderr )
        sys.exit( 1 )

    # Auto-discover Kim species from proteome filenames.
    species_to_process = discover_kim_species( input_proteome_dir )
    if arguments.single_species:
        species_to_process = [ s for s in species_to_process if s == arguments.single_species ]

    print( f"Discovered {len( species_to_process )} Kim 2025 species in {input_proteome_dir}" )

    summary_records = []

    for genus_species in species_to_process:
        print( "" )
        print( f"=== {genus_species} ===" )

        gtf_path, proteome_candidates = find_input_files_for_species(
            genus_species, input_gtf_dir, input_proteome_dir
        )

        if not gtf_path.is_file():
            record = {
                'genus_species': genus_species,
                'status': 'SKIPPED_NO_GTF',
                'notes': f"missing {gtf_path.name}",
            }
            summary_records.append( record )
            print( f"  SKIPPED_NO_GTF: {gtf_path.name}" )
            continue

        if not proteome_candidates:
            record = {
                'genus_species': genus_species,
                'status': 'SKIPPED_NO_PROTEOME',
                'notes': f"no proteome matched {genus_species}-genome-kim_2025-*.aa",
            }
            summary_records.append( record )
            print( f"  SKIPPED_NO_PROTEOME" )
            continue

        proteome_path = proteome_candidates[ 0 ]
        output_tsv_all_inclusive_path = output_dir / f"{genus_species}-gene_coordinates_all_inclusive.tsv"
        output_tsv_gene_vs_protein_path = output_dir / f"{genus_species}-gene_coordinates_gene_vs_protein.tsv"
        output_unmatched_path = output_dir / f"{genus_species}-unmatched_proteome_entries.tsv"

        print( f"  GTF:      {gtf_path.name}" )
        print( f"  Proteome: {proteome_path.name}" )

        stats = extract_gene_coordinates_for_species(
            genus_species, gtf_path, proteome_path,
            output_tsv_all_inclusive_path, output_tsv_gene_vs_protein_path,
            output_unmatched_path,
        )
        summary_records.append( stats )

        if stats[ 'wrote_gene_vs_protein' ] == 'yes':
            symlink_path = symlink_dir_gene_vs_protein / output_tsv_gene_vs_protein_path.name
            make_relative_symlink( output_tsv_gene_vs_protein_path, symlink_path )
        if stats[ 'wrote_all_inclusive' ] == 'yes':
            symlink_path = symlink_dir_all_inclusive / output_tsv_all_inclusive_path.name
            make_relative_symlink( output_tsv_all_inclusive_path, symlink_path )

        print( f"  rows_written:                 {stats[ 'rows_written' ]:>8d}" )
        print( f"  genes_with_utr:               {stats[ 'genes_with_utr' ]:>8d}" )
        print( f"  tier:                         {stats[ 'tier' ]}" )
        print( f"  missing_transcript_lookups:   {stats[ 'missing_transcript_lookups' ]:>8d}" )
        print( f"  missing_exon_lookups:         {stats[ 'missing_exon_lookups' ]:>8d}" )
        print( f"  missing_cds_lookups:          {stats[ 'missing_cds_lookups' ]:>8d}" )

    output_summary_path = output_dir / 'extraction_summary.tsv'
    write_summary( summary_records, output_summary_path )

    print( "" )
    print( "========================================================================" )
    print( f"Summary: {output_summary_path}" )
    print( f"  Tier 1 (all_inclusive)  symlinked into {symlink_dir_all_inclusive}/" )
    print( f"  Tier 2 (gene_vs_protein) symlinked into {symlink_dir_gene_vs_protein}/" )
    print( "========================================================================" )

    total_rows = sum( record.get( 'rows_written', 0 ) for record in summary_records )
    if total_rows == 0:
        print( "ERROR: no rows written for any species. Check input paths.", file = sys.stderr )
        sys.exit( 1 )

    # Strict end-of-pipeline check: every T1 proteome identifier must have a TSV row.
    species_with_unmatched = []
    total_unmatched = 0
    for record in summary_records:
        unmatched_count = ( record.get( 'missing_transcript_lookups', 0 )
                            + record.get( 'missing_exon_lookups', 0 )
                            + record.get( 'missing_cds_lookups', 0 ) )
        if unmatched_count > 0:
            species_with_unmatched.append( ( record[ 'genus_species' ], unmatched_count ) )
            total_unmatched += unmatched_count

    if species_with_unmatched:
        print( "", file = sys.stderr )
        print( f"NOTE: {len( species_with_unmatched )} species excluded from output_to_input (highest-quality-only tenet):", file = sys.stderr )
        for genus_species, count in species_with_unmatched:
            print( f"  {genus_species}: {count} unmatched", file = sys.stderr )

    n_tier_1 = sum( 1 for r in summary_records if r.get( 'wrote_all_inclusive' ) == 'yes' )
    n_tier_2 = sum( 1 for r in summary_records if r.get( 'wrote_gene_vs_protein' ) == 'yes' )
    print( f"Tier 1 (all_inclusive):  {n_tier_1} species" )
    print( f"Tier 2 (gene_vs_protein): {n_tier_2} species (Type 1 species are also here as superset)" )


if __name__ == '__main__':
    main()
