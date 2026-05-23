#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 04 | Purpose: Extract per-species gene coordinate TSVs from NCBI GFF3 annotations for the GIGANTIC gene_sizes pipeline
# Human: Eric Edsinger
"""
Extract gene coordinate TSVs from NCBI GFF3 annotations.

For each NCBI species in the manifest, parse the corrected T1 proteome to
determine which (gene_symbol, transcript_acc, protein_acc) tuples are the
canonical T1 representatives, then look up each gene's genomic coordinates and
its T1 transcript's CDS intervals in the species GFF3.

The corrected T1 proteome is the source of truth for which genes count, so
this script inherits the alternate-loci filtering already applied during T1
extraction (no need to re-implement GeneID-based deduplication here).

Gene symbol sanitization: NCBI gene names are normalized to alphanumeric +
underscore by replacing any other character with '_'. The GFF Name= attribute
is sanitized the same way to match the proteome representation.

Output (one file per species):
    OUTPUT_pipeline/<Genus_species>-gene_coordinates.tsv

    Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  CDS_Intervals

Plus a cross-species summary:
    OUTPUT_pipeline/extraction_summary.tsv
"""

import argparse
import os
import re
import sys
from pathlib import Path


def sanitize_gene_name( name ):
    """Replace hyphens with underscores. Other non-alphanumeric characters are preserved.

    Empirically matches what the T1 extractor wrote into proteome FASTA headers:
        'H3-4'                      -> 'H3_4'           (hyphen replaced)
        'gene-AAAS-2' (after strip) -> 'AAAS_2'         (hyphen replaced)
        'CELE_2L52.1'               -> 'CELE_2L52.1'    (period preserved)
        'hyfzd5/8'                  -> 'hyfzd5/8'       (slash preserved)
        'His.H4'                    -> 'His.H4'         (period preserved)
        'C/EBP'                     -> 'C/EBP'          (slash preserved)

    Note: the user's stated rule was 'all non-alphanumeric -> _', but the actual
    T1 extractor only converts hyphens. Periods, slashes, and other characters
    are preserved verbatim. We match the observed proteome contents to ensure
    100% lookup success against the corrected T1 proteome.
    """
    return name.replace( '-', '_' )


def normalize_transcript_accession( accession_or_feature_id ):
    """Strip 'rna-' prefix (if present) and convert hyphens to underscores.

    Matches what the T1 extractor wrote into proteome FASTA headers for
    transcript accessions: 'NM_003493.3-2' (alt-locus suffix) becomes
    'NM_003493.3_2'. Internal '.' is preserved (the T1 extractor sanitizes
    only hyphens for transcript/protein accessions, NOT all non-alphanumeric).
    """
    if accession_or_feature_id.startswith( 'rna-' ):
        accession_or_feature_id = accession_or_feature_id[ len( 'rna-' ): ]
    return accession_or_feature_id.replace( '-', '_' )


def parse_gff3_attributes( attribute_string ):
    """Parse a GFF3 column-9 attributes string into a dict.

    Example input:
        ID=gene-A1BG;Name=A1BG;gene=A1BG;gene_biotype=protein_coding

    Returns:
        { 'ID': 'gene-A1BG', 'Name': 'A1BG', 'gene': 'A1BG', 'gene_biotype': 'protein_coding' }
    """
    parts = attribute_string.strip().split( ';' )
    keys___values = {}
    for part in parts:
        if '=' in part:
            key, value = part.split( '=', 1 )
            keys___values[ key.strip() ] = value.strip()
    return keys___values


def parse_proteome_headers( input_proteome_path ):
    """Parse a T1 proteome FASTA and return a list of (gene_symbol_sanitized,
    transcript_acc, protein_acc) tuples in proteome order.

    Header format: >Genus_species-<gene_symbol>-<transcript_acc>-<protein_acc>
    where <gene_symbol> is already sanitized (alphanumeric + underscore).

    The genus_species component itself contains an underscore (e.g. 'Homo_sapiens'),
    no hyphen, so the four-part split on '-' is unambiguous.
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
        # Last 3 fields are gene_symbol, transcript_acc, protein_acc.
        # genus_species is everything before that — joined back with '-' just in case.
        gene_symbol = parts_header[ -3 ]
        transcript_acc = parts_header[ -2 ]
        protein_acc = parts_header[ -1 ]
        tuples_in_proteome.append( ( gene_symbol, transcript_acc, protein_acc ) )
    input_proteome.close()
    return tuples_in_proteome


def parse_ncbi_gff3( input_gff3_path ):
    """Parse an NCBI GFF3 file and return four lookup structures:

    sanitized_gene_names___gene_coordinates:
        sanitized_gene_name -> ( Seqid, Gene_Start, Gene_End, Strand, original_gene_id )

    transcript_ids___exon_intervals:
        rna_feature_id (e.g. 'NM_130786.4') -> [ (exon_start, exon_end), ... ]

    transcript_ids___cds_intervals:
        rna_feature_id -> [ (cds_start, cds_end), ... ]

    transcript_ids___parent_gene_ids:
        rna_feature_id -> gene feature ID (e.g. 'gene-A1BG')

    GIGANTIC's data quality tenet: a species is processable only when we can
    produce gene_size + transcript_size + cds_size + protein_size from a single
    annotation. That means we need gene + exon + CDS records for the T1
    transcript. Any proteome entry missing any of these is dropped (logged to
    the unmatched file).
    """
    sanitized_gene_names___gene_coordinates = {}
    transcript_ids___exon_intervals = {}
    transcript_ids___cds_intervals = {}
    transcript_ids___parent_gene_ids = {}

    input_gff3 = open( input_gff3_path, 'r' )
    for line in input_gff3:
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
        attributes = parse_gff3_attributes( parts[ 8 ] )

        if feature_type == 'gene':
            # Do NOT filter by gene_biotype here. The proteome is the source of
            # truth for which genes count, and some protein-producing genes have
            # biotypes other than 'protein_coding' (e.g., Drosophila trans-splicing
            # 'segment' biotypes for mod(mdg4)-T family). Loading all gene features
            # is safe because the lookup is proteome-driven.
            gene_id = attributes.get( 'ID', '' )
            # Use the ID (gene-X) minus the 'gene-' prefix as the gene-name source.
            # This preserves alternate-locus suffixes (gene-AAAS-2 -> AAAS-2 -> sanitized AAAS_2),
            # which is critical when the alt-locus is the kept form (the 41+ "no primary form" cases).
            # Using Name= would collapse primary and alt entries to the same base symbol.
            if gene_id.startswith( 'gene-' ):
                gene_name = gene_id[ len( 'gene-' ): ]
            else:
                gene_name = attributes.get( 'Name', '' )
            sanitized_name = sanitize_gene_name( gene_name )
            # Multiple GFF entries may share a sanitized name (e.g. an alternate
            # locus 'gene-AAAS-2' sanitizes to 'AAAS_2', distinct from primary
            # 'AAAS'). Keep the first one seen; downstream lookup uses whatever
            # the proteome wrote, and the proteome only carries one per primary.
            if sanitized_name not in sanitized_gene_names___gene_coordinates:
                sanitized_gene_names___gene_coordinates[ sanitized_name ] = (
                    seqid, feature_start, feature_end, strand, gene_id
                )

        elif feature_type == 'mRNA':
            mrna_id = attributes.get( 'ID', '' )
            parent_gene_id = attributes.get( 'Parent', '' )
            if mrna_id and parent_gene_id:
                # Normalize the mRNA key to the proteome's transcript-accession form:
                # 'rna-NM_003493.3-2' (alt-locus) becomes 'NM_003493.3_2'.
                normalized_transcript = normalize_transcript_accession( mrna_id )
                transcript_ids___parent_gene_ids[ normalized_transcript ] = parent_gene_id

        elif feature_type == 'exon':
            parent_id = attributes.get( 'Parent', '' )
            if ',' in parent_id:
                parent_id = parent_id.split( ',' )[ 0 ]
            if parent_id:
                if parent_id.startswith( 'rna-' ):
                    exon_key = normalize_transcript_accession( parent_id )
                else:
                    exon_key = parent_id  # mitochondrial-style: exon parented to gene
                transcript_ids___exon_intervals.setdefault( exon_key, [] ).append(
                    ( feature_start, feature_end )
                )

        elif feature_type == 'CDS':
            parent_id = attributes.get( 'Parent', '' )
            # A CDS may have multiple parents (rare); take the first.
            if ',' in parent_id:
                parent_id = parent_id.split( ',' )[ 0 ]
            if parent_id:
                # Two parent kinds, two keying conventions:
                # 1. Normal case: Parent=rna-<acc> -> normalize to transcript-accession form
                #    (matches proteome's transcript_acc field exactly).
                # 2. Mitochondrial / no-mRNA case: Parent=gene-<symbol> -> keep verbatim
                #    so it matches the original_gene_id stored in the gene map. Fallback
                #    lookup uses original_gene_id (with hyphen) so we must preserve it.
                if parent_id.startswith( 'rna-' ):
                    cds_key = normalize_transcript_accession( parent_id )
                else:
                    cds_key = parent_id  # e.g., 'gene-COX1' (mitochondrial)
                transcript_ids___cds_intervals.setdefault( cds_key, [] ).append(
                    ( feature_start, feature_end )
                )

    input_gff3.close()
    return (
        sanitized_gene_names___gene_coordinates,
        transcript_ids___exon_intervals,
        transcript_ids___cds_intervals,
        transcript_ids___parent_gene_ids,
    )


def derive_utrs_from_exons_and_cds( merged_exons, merged_cds, strand ):
    """Derive UTR_5prime and UTR_3prime genomic intervals from merged exons and CDS.

    UTR portions are the parts of each exon that lie outside the CDS span.
    For a gene with CDS spanning [cds_min, cds_max] genomic coordinates:
      - Genomic-low UTR portions  (exon_end < cds_min) and the low-side overhang
        of any exon overlapping cds_min belong to the LOW genomic side of CDS.
      - Genomic-high UTR portions (exon_start > cds_max) and the high-side overhang
        of any exon overlapping cds_max belong to the HIGH genomic side of CDS.
      - + strand: low-genomic side = 5' UTR;  high-genomic side = 3' UTR.
      - - strand: low-genomic side = 3' UTR;  high-genomic side = 5' UTR.

    Returns ( utr_5prime_intervals, utr_3prime_intervals ) as lists of (start, end) tuples.
    Both lists may be empty if the gene has no UTR-bearing exonic content (e.g.,
    single-exon CDS-only genes, which are biologically real and common in some
    species even within otherwise UTR-annotated genomes).
    """
    if not merged_cds or not merged_exons:
        return [], []

    cds_min = min( start for start, _ in merged_cds )
    cds_max = max( end for _, end in merged_cds )

    utr_genomic_low = []
    utr_genomic_high = []

    for exon_start, exon_end in merged_exons:
        if exon_end < cds_min:
            # Whole exon sits below CDS span.
            utr_genomic_low.append( ( exon_start, exon_end ) )
        elif exon_start > cds_max:
            # Whole exon sits above CDS span.
            utr_genomic_high.append( ( exon_start, exon_end ) )
        else:
            # Exon overlaps the CDS span; harvest the overhangs on either side.
            if exon_start < cds_min:
                utr_genomic_low.append( ( exon_start, cds_min - 1 ) )
            if exon_end > cds_max:
                utr_genomic_high.append( ( cds_max + 1, exon_end ) )

    if strand == '+':
        return utr_genomic_low, utr_genomic_high
    elif strand == '-':
        return utr_genomic_high, utr_genomic_low
    else:
        # Unknown strand — collapse all into 5' (defensive; shouldn't occur in real data).
        return utr_genomic_low + utr_genomic_high, []


def intervals_total_size( intervals ):
    """Sum the (end - start + 1) lengths of all intervals."""
    return sum( end - start + 1 for start, end in intervals )


def intervals_to_string( intervals ):
    """Format a list of (start, end) tuples as comma-delimited 'start-end' pairs."""
    return ','.join( f"{start}-{end}" for start, end in intervals )


def merge_intervals( intervals ):
    """Sort and merge overlapping or adjacent intervals.

    Input:  [ (10, 20), (15, 25), (30, 40) ]
    Output: [ (10, 25), (30, 40) ]
    """
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


def find_input_files_for_species( genus_species, input_gff3_dir, input_proteome_dir ):
    """Locate the GFF3 and T1 proteome files for one species.

    GFF3 naming (in 2-output/gff3/):  <Genus_species>-ncbi_genomes.gff3
    Proteome naming (in T1_proteomes/): <Genus_species>-genome-ncbi_<accession>-downloaded_<date>.aa
    """
    gff3_path = Path( input_gff3_dir ) / f"{genus_species}-ncbi_genomes.gff3"

    proteome_candidates = list(
        Path( input_proteome_dir ).glob( f"{genus_species}-genome-ncbi_*.aa" )
    )

    return gff3_path, proteome_candidates


def extract_gene_coordinates_for_species(
    genus_species,
    input_gff3_path,
    input_proteome_path,
    output_tsv_all_inclusive_path,
    output_tsv_gene_vs_protein_path,
    output_unmatched_path,
):
    """Process one species end-to-end. Returns a stats dict for the summary.

    Two output TSVs are produced for tier-1 species (those whose annotation includes
    UTR information); one TSV is produced for tier-2 species (CDS-only annotations).

    Tier classification per species:
      Tier 1 (gene_coordinates_all_inclusive): >=50% of genes have at least one
              base of derived UTR (exon coords extend beyond CDS coords).
              Writes BOTH the all-inclusive (15-col) AND the gene-vs-protein (9-col) TSVs.
      Tier 2 (gene_coordinates_gene_vs_protein only): otherwise.
              Writes only the 9-col TSV.

    output_unmatched_path: file to write any proteome entries that failed to
    match a GFF gene, exon, or CDS (with reason).
    """

    stats = {
        'genus_species': genus_species,
        'proteome_entries': 0,
        'rows_written': 0,
        'genes_with_utr': 0,
        'tier': '',
        'wrote_all_inclusive': 'no',
        'wrote_gene_vs_protein': 'no',
        'missing_gene_lookups': 0,
        'missing_exon_lookups': 0,
        'missing_cds_lookups': 0,
        'sanitization_anomalies': 0,
        'status': 'PROCESSED',
        'notes': '',
    }

    tuples_in_proteome = parse_proteome_headers( input_proteome_path )
    stats[ 'proteome_entries' ] = len( tuples_in_proteome )

    if not tuples_in_proteome:
        stats[ 'status' ] = 'SKIPPED_EMPTY_PROTEOME'
        stats[ 'notes' ] = f"No headers parsed from {input_proteome_path.name}"
        return stats

    (
        sanitized_gene_names___gene_coordinates,
        transcript_ids___exon_intervals,
        transcript_ids___cds_intervals,
        transcript_ids___parent_gene_ids,
    ) = parse_ncbi_gff3( input_gff3_path )

    for sanitized_name in sanitized_gene_names___gene_coordinates:
        if not re.fullmatch( r'[A-Za-z0-9_]+', sanitized_name ):
            stats[ 'sanitization_anomalies' ] += 1

    output_unmatched = open( output_unmatched_path, 'w' )
    output_unmatched.write( '\t'.join( [
        'gene_symbol_from_proteome',
        'transcript_acc_from_proteome',
        'protein_acc_from_proteome',
        'reason (missing_gene_lookup, missing_exon_lookup, or missing_cds_lookup)',
    ] ) + '\n' )

    # Pass 1: collect per-gene records into memory so tier classification can be
    # computed once per species before deciding which file(s) to write.
    gene_records = []

    for gene_symbol, transcript_acc, protein_acc in tuples_in_proteome:
        gene_coordinate_record = sanitized_gene_names___gene_coordinates.get( gene_symbol )
        if gene_coordinate_record is None:
            stats[ 'missing_gene_lookups' ] += 1
            output_unmatched.write( '\t'.join( [
                gene_symbol, transcript_acc, protein_acc, 'missing_gene_lookup'
            ] ) + '\n' )
            continue
        seqid, gene_start, gene_end, strand, original_gene_id = gene_coordinate_record

        exon_intervals = transcript_ids___exon_intervals.get( transcript_acc, [] )
        if not exon_intervals:
            exon_intervals = transcript_ids___exon_intervals.get( original_gene_id, [] )
        if not exon_intervals:
            stats[ 'missing_exon_lookups' ] += 1
            output_unmatched.write( '\t'.join( [
                gene_symbol, transcript_acc, protein_acc, 'missing_exon_lookup'
            ] ) + '\n' )
            continue

        cds_intervals = transcript_ids___cds_intervals.get( transcript_acc, [] )
        if not cds_intervals:
            cds_intervals = transcript_ids___cds_intervals.get( original_gene_id, [] )
        if not cds_intervals:
            stats[ 'missing_cds_lookups' ] += 1
            output_unmatched.write( '\t'.join( [
                gene_symbol, transcript_acc, protein_acc, 'missing_cds_lookup'
            ] ) + '\n' )
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
            'gene_symbol': gene_symbol,
            'seqid': seqid,
            'gene_start': gene_start,
            'gene_end': gene_end,
            'strand': strand,
            'gene_size': gene_size,
            'merged_exons': merged_exons,
            'transcript_size': transcript_size,
            'merged_cds': merged_cds,
            'cds_size': cds_size,
            'protein_size': protein_size,
            'utr_5prime': utr_5prime,
            'utr_5prime_size': utr_5prime_size,
            'utr_3prime': utr_3prime,
            'utr_3prime_size': utr_3prime_size,
        } )

    output_unmatched.close()
    stats[ 'rows_written' ] = len( gene_records )

    if not gene_records:
        stats[ 'status' ] = 'SKIPPED_NO_USABLE_GENES'
        stats[ 'notes' ] = "No proteome entries produced gene+exon+CDS records"
        return stats

    # Tier classification: a species is tier 1 if at least 50% of its genes have
    # any derived UTR content. Single-exon UTR-less genes within a tier-1 species
    # are still legitimately written (with empty UTR fields and size 0).
    fraction_with_utr = stats[ 'genes_with_utr' ] / len( gene_records )
    is_tier_1 = fraction_with_utr >= 0.5
    stats[ 'tier' ] = 'all_inclusive' if is_tier_1 else 'gene_vs_protein'

    # Always write the gene-vs-protein (Type 2) TSV — it's the universal format that
    # every species qualifies for once it has Gene+CDS+Protein.
    output_tsv = open( output_tsv_gene_vs_protein_path, 'w' )
    header = '\t'.join( [
        'Source_Gene_ID (sanitized gene symbol matching the g_ field of the GIGANTIC proteome header)',
        'Seqid (chromosome or scaffold accession from the GFF3)',
        'Gene_Start (1-based gene feature start position)',
        'Gene_End (1-based gene feature end position inclusive)',
        'Strand (+ or - from the GFF3 strand column)',
        'Gene_Size (genomic span in bp inclusive of all introns and UTRs and CDS computed as Gene_End minus Gene_Start plus 1)',
        'CDS_Intervals (comma delimited list of CDS interval start-end pairs after sorting and merging from the T1 transcript)',
        'CDS_Size (length of protein-coding region in bp computed as sum of merged CDS intervals)',
        'Protein_Size (estimated amino acids computed as CDS_Size divided by 3)',
    ] ) + '\n'
    output_tsv.write( header )
    for record in gene_records:
        output_tsv.write( '\t'.join( [
            record[ 'gene_symbol' ],
            record[ 'seqid' ],
            str( record[ 'gene_start' ] ),
            str( record[ 'gene_end' ] ),
            record[ 'strand' ],
            str( record[ 'gene_size' ] ),
            intervals_to_string( record[ 'merged_cds' ] ),
            str( record[ 'cds_size' ] ),
            str( record[ 'protein_size' ] ),
        ] ) + '\n' )
    output_tsv.close()
    stats[ 'wrote_gene_vs_protein' ] = 'yes'

    # Tier 1 species also get the 15-col all-inclusive TSV with derived UTR columns.
    if is_tier_1:
        output_tsv = open( output_tsv_all_inclusive_path, 'w' )
        header = '\t'.join( [
            'Source_Gene_ID (sanitized gene symbol matching the g_ field of the GIGANTIC proteome header)',
            'Seqid (chromosome or scaffold accession from the GFF3)',
            'Gene_Start (1-based gene feature start position)',
            'Gene_End (1-based gene feature end position inclusive)',
            'Strand (+ or - from the GFF3 strand column)',
            'Gene_Size (genomic span in bp inclusive of all introns and UTRs and CDS)',
            'Exon_Intervals (comma delimited list of merged exon interval start-end pairs from the T1 transcript)',
            'Transcript_Size (length of mature mRNA in bp computed as sum of merged exon intervals)',
            'CDS_Intervals (comma delimited list of merged CDS interval start-end pairs from the T1 transcript)',
            'CDS_Size (length of protein-coding region in bp computed as sum of merged CDS intervals)',
            'Protein_Size (estimated amino acids computed as CDS_Size divided by 3)',
            'UTR_5prime_Intervals (genomic intervals of 5-prime UTR portions derived as exon coords outside CDS span on the 5-prime side relative to strand)',
            'UTR_5prime_Size (sum of 5-prime UTR interval lengths in bp)',
            'UTR_3prime_Intervals (genomic intervals of 3-prime UTR portions derived as exon coords outside CDS span on the 3-prime side relative to strand)',
            'UTR_3prime_Size (sum of 3-prime UTR interval lengths in bp)',
        ] ) + '\n'
        output_tsv.write( header )
        for record in gene_records:
            output_tsv.write( '\t'.join( [
                record[ 'gene_symbol' ],
                record[ 'seqid' ],
                str( record[ 'gene_start' ] ),
                str( record[ 'gene_end' ] ),
                record[ 'strand' ],
                str( record[ 'gene_size' ] ),
                intervals_to_string( record[ 'merged_exons' ] ),
                str( record[ 'transcript_size' ] ),
                intervals_to_string( record[ 'merged_cds' ] ),
                str( record[ 'cds_size' ] ),
                str( record[ 'protein_size' ] ),
                intervals_to_string( record[ 'utr_5prime' ] ),
                str( record[ 'utr_5prime_size' ] ),
                intervals_to_string( record[ 'utr_3prime' ] ),
                str( record[ 'utr_3prime_size' ] ),
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
        ( 'tier', 'all_inclusive (full UTR annotation) or gene_vs_protein (CDS-only)' ),
        ( 'wrote_all_inclusive', 'whether tier-1 TSV was written (yes/no)' ),
        ( 'wrote_gene_vs_protein', 'whether tier-2 TSV was written (yes/no)' ),
        ( 'proteome_entries', 'number of header tuples parsed from T1 proteome' ),
        ( 'rows_written', 'number of TSV rows written for this species' ),
        ( 'genes_with_utr', 'number of genes for which UTR derivation produced any UTR sequence' ),
        ( 'missing_gene_lookups', 'count of proteome entries whose gene_symbol was not found in the GFF gene index' ),
        ( 'missing_exon_lookups', 'count of proteome entries whose transcript_acc had no exon features in the GFF' ),
        ( 'missing_cds_lookups', 'count of proteome entries whose transcript_acc had no CDS features in the GFF' ),
        ( 'sanitization_anomalies', 'count of GFF gene names that contained non-alphanumeric characters after sanitization' ),
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
    parser.add_argument( '--manifest', required = True, help = 'NCBI manifest TSV: genus_species<TAB>accession (lines starting with # are ignored)' )
    parser.add_argument( '--gff3-dir', required = True, help = 'Directory of source NCBI GFF3 files (Genus_species-ncbi_genomes.gff3)' )
    parser.add_argument( '--proteome-dir', required = True, help = 'Directory of corrected T1 proteomes' )
    parser.add_argument( '--output-dir', required = True, help = 'Output directory for per-species TSVs and summary' )
    parser.add_argument( '--symlink-dir-all-inclusive', required = True, help = 'output_to_input/gene_coordinates_all_inclusive dir for tier-1 (full UTR annotation) TSVs' )
    parser.add_argument( '--symlink-dir-gene-vs-protein', required = True, help = 'output_to_input/gene_coordinates_gene_vs_protein dir for tier-2 TSVs (Type 1 species also symlinked here as superset)' )
    parser.add_argument( '--single-species', default = '', help = 'If set, process only this species (Genus_species)' )
    arguments = parser.parse_args()

    input_manifest_path = Path( arguments.manifest )
    input_gff3_dir = Path( arguments.gff3_dir )
    input_proteome_dir = Path( arguments.proteome_dir )
    output_dir = Path( arguments.output_dir )
    output_dir.mkdir( parents = True, exist_ok = True )
    symlink_dir_all_inclusive = Path( arguments.symlink_dir_all_inclusive )
    symlink_dir_all_inclusive.mkdir( parents = True, exist_ok = True )
    symlink_dir_gene_vs_protein = Path( arguments.symlink_dir_gene_vs_protein )
    symlink_dir_gene_vs_protein.mkdir( parents = True, exist_ok = True )

    # Validate inputs.
    if not input_manifest_path.is_file():
        print( f"ERROR: manifest not found: {input_manifest_path}", file = sys.stderr )
        sys.exit( 1 )
    if not input_gff3_dir.is_dir():
        print( f"ERROR: GFF3 dir not found: {input_gff3_dir}", file = sys.stderr )
        sys.exit( 1 )
    if not input_proteome_dir.is_dir():
        print( f"ERROR: proteome dir not found: {input_proteome_dir}", file = sys.stderr )
        sys.exit( 1 )

    # Read manifest. Skip comment lines (#) and the column-header line if present.
    # # NCBI Genomes Manifest for GIGANTIC databases-AI species69
    # genus_species	accession
    # Homo_sapiens	GCF_000001405.40
    species_to_process = []
    input_manifest = open( input_manifest_path, 'r' )
    for line in input_manifest:
        line = line.strip()
        if not line or line.startswith( '#' ):
            continue
        parts = line.split( '\t' )
        genus_species = parts[ 0 ]
        # Skip the column-header line — first column literally 'genus_species'.
        if genus_species == 'genus_species':
            continue
        if arguments.single_species and genus_species != arguments.single_species:
            continue
        species_to_process.append( genus_species )
    input_manifest.close()

    print( f"Manifest: {len( species_to_process )} NCBI species to process" )

    summary_records = []

    for genus_species in species_to_process:
        print( "" )
        print( f"=== {genus_species} ===" )

        gff3_path, proteome_candidates = find_input_files_for_species(
            genus_species, input_gff3_dir, input_proteome_dir
        )

        if not gff3_path.is_file():
            record = {
                'genus_species': genus_species,
                'status': 'SKIPPED_NO_GFF3',
                'notes': f"missing {gff3_path.name}",
            }
            summary_records.append( record )
            print( f"  SKIPPED_NO_GFF3: {gff3_path.name}" )
            continue

        if not proteome_candidates:
            record = {
                'genus_species': genus_species,
                'status': 'SKIPPED_NO_PROTEOME',
                'notes': f"no proteome matched {genus_species}-genome-ncbi_*.aa",
            }
            summary_records.append( record )
            print( f"  SKIPPED_NO_PROTEOME" )
            continue

        if len( proteome_candidates ) > 1:
            print( f"  WARN: multiple proteomes matched, using first: {proteome_candidates[ 0 ].name}" )

        proteome_path = proteome_candidates[ 0 ]
        output_tsv_all_inclusive_path = output_dir / f"{genus_species}-gene_coordinates_all_inclusive.tsv"
        output_tsv_gene_vs_protein_path = output_dir / f"{genus_species}-gene_coordinates_gene_vs_protein.tsv"
        output_unmatched_path = output_dir / f"{genus_species}-unmatched_proteome_entries.tsv"

        print( f"  GFF3:     {gff3_path.name}" )
        print( f"  Proteome: {proteome_path.name}" )

        stats = extract_gene_coordinates_for_species(
            genus_species, gff3_path, proteome_path,
            output_tsv_all_inclusive_path, output_tsv_gene_vs_protein_path,
            output_unmatched_path,
        )
        summary_records.append( stats )

        # Symlink based on tier classification. Tier 1 species write to BOTH dirs
        # (Type 2 is a superset). Tier 2 species write to gene_vs_protein only.
        if stats[ 'wrote_gene_vs_protein' ] == 'yes':
            symlink_path = symlink_dir_gene_vs_protein / output_tsv_gene_vs_protein_path.name
            make_relative_symlink( output_tsv_gene_vs_protein_path, symlink_path )
        if stats[ 'wrote_all_inclusive' ] == 'yes':
            symlink_path = symlink_dir_all_inclusive / output_tsv_all_inclusive_path.name
            make_relative_symlink( output_tsv_all_inclusive_path, symlink_path )

        print( f"  rows_written:            {stats[ 'rows_written' ]:>8d}" )
        print( f"  genes_with_utr:          {stats[ 'genes_with_utr' ]:>8d}" )
        print( f"  tier:                    {stats[ 'tier' ]}" )
        print( f"  proteome_entries:        {stats[ 'proteome_entries' ]:>8d}" )
        print( f"  missing_gene_lookups:    {stats[ 'missing_gene_lookups' ]:>8d}" )
        print( f"  missing_exon_lookups:    {stats[ 'missing_exon_lookups' ]:>8d}" )
        print( f"  missing_cds_lookups:     {stats[ 'missing_cds_lookups' ]:>8d}" )
        print( f"  sanitization_anomalies:  {stats[ 'sanitization_anomalies' ]:>8d}" )

    # Write summary.
    output_summary_path = output_dir / 'extraction_summary.tsv'
    write_summary( summary_records, output_summary_path )

    print( "" )
    print( "========================================================================" )
    print( f"Summary: {output_summary_path}" )
    print( f"Per-species TSVs in {output_dir}/" )
    print( f"  Tier 1 (all_inclusive)  symlinked into {symlink_dir_all_inclusive}/" )
    print( f"  Tier 2 (gene_vs_protein) symlinked into {symlink_dir_gene_vs_protein}/" )
    print( "========================================================================" )

    # Fail-fast check: if no species produced any rows, that's a configuration problem.
    total_rows = sum( record.get( 'rows_written', 0 ) for record in summary_records )
    if total_rows == 0:
        print( "ERROR: no rows written for any species. Check input paths.", file = sys.stderr )
        sys.exit( 1 )

    # Strict end-of-pipeline check: every T1 proteome identifier must have a TSV row.
    # Any miss means a symbol-difference between T1 extraction and gene_coordinates extraction
    # of the GFF, which would silently skew downstream gene_sizes results. Fail loudly.
    species_with_unmatched = []
    total_unmatched = 0
    for record in summary_records:
        unmatched_count = ( record.get( 'missing_gene_lookups', 0 )
                            + record.get( 'missing_exon_lookups', 0 )
                            + record.get( 'missing_cds_lookups', 0 ) )
        if unmatched_count > 0:
            species_with_unmatched.append( ( record[ 'genus_species' ], unmatched_count ) )
            total_unmatched += unmatched_count

    if species_with_unmatched:
        print( "", file = sys.stderr )
        print( "========================================================================", file = sys.stderr )
        print( f"NOTE: {len( species_with_unmatched )} species had unmatched T1 entries and were", file = sys.stderr )
        print( "      EXCLUDED from output_to_input (highest-quality-only tenet).", file = sys.stderr )
        print( f"      Total unmatched proteome entries: {total_unmatched}", file = sys.stderr )
        for genus_species, count in species_with_unmatched:
            print( f"      {genus_species}: {count} unmatched", file = sys.stderr )
        print( "      Local TSVs retained in OUTPUT_pipeline/ for audit.", file = sys.stderr )
        print( "========================================================================", file = sys.stderr )

    n_tier_1 = sum( 1 for r in summary_records if r.get( 'wrote_all_inclusive' ) == 'yes' )
    n_tier_2 = sum( 1 for r in summary_records if r.get( 'wrote_gene_vs_protein' ) == 'yes' )
    print( f"Tier 1 (all_inclusive):  {n_tier_1} species" )
    print( f"Tier 2 (gene_vs_protein): {n_tier_2} species (Type 1 species are also here as superset)" )


if __name__ == '__main__':
    main()
