#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 04 | Purpose: Extract per-species gene coordinate TSVs from repository (Figshare/Zenodo/Dryad/etc.) GFF3 annotations for the GIGANTIC gene_sizes pipeline
# Human: Eric Edsinger
"""
Extract gene coordinate TSVs from repository genome GFF3 annotations.

Repository genomes come from various sources (Figshare, Zenodo, Dryad, BovaDB,
GigaDB, OIST, etc.) but their GFF3 files share a common simple structure:
  - gene feature with ID=<gene_id> (no 'gene-' prefix)
  - mRNA feature with ID=<transcript_id>;Parent=<gene_id>
  - CDS feature with Parent=<transcript_id>

Most are AUGUSTUS, BRAKER, or similar predictor outputs.

Auto-discovers species from proteome filenames in the input proteome dir.

Output (one file per species):
    OUTPUT_pipeline/<Genus_species>-gene_coordinates.tsv

    Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  CDS_Intervals
"""

import argparse
import os
import sys
from pathlib import Path


def normalize_id( name ):
    """Strip NCBI-style 'gene-' or 'rna-' prefix, then replace hyphens with underscores.

    Some repository genomes use NCBI-style ID conventions (e.g., Hypsibius_dujardini
    uses 'ID=gene-BV898_00001' and 'ID=rna-gnl|WGS:MTYJ|mrna.BV898_00001.1'). The
    proteome's gene_symbol and transcript_acc don't include these prefixes, so we
    strip them here. The hyphen-to-underscore replacement matches the convention
    the T1 extractor used in proteome FASTA headers.
    """
    if name.startswith( 'gene-' ):
        name = name[ len( 'gene-' ): ]
    elif name.startswith( 'rna-' ):
        name = name[ len( 'rna-' ): ]
    return name.replace( '-', '_' )


def parse_gff3_attributes( attribute_string ):
    """Parse a column-9 attributes string into a dict.

    Handles BOTH GFF3-style ('key=value;key=value') AND GTF-style
    ('key "value"; key "value";') because some repository genomes mix the
    two styles within a single annotation file (e.g., Amphiscolops_sp_MND2022
    has GFF3 lines for gene features but GTF-style attributes for CDS).
    """
    keys___values = {}
    parts = attribute_string.strip().rstrip( ';' ).split( ';' )
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '=' in part:
            key, value = part.split( '=', 1 )
            keys___values[ key.strip() ] = value.strip()
        elif ' ' in part:
            # GTF style: key "value"
            key, value = part.split( None, 1 )
            value = value.strip()
            if value.startswith( '"' ) and value.endswith( '"' ):
                value = value[ 1: -1 ]
            keys___values[ key.strip() ] = value
        else:
            # Bare token (Amphiscolops 'gene' feature has just 'g1' as the entire
            # column-9 attribute string). Treat as the feature's ID.
            keys___values.setdefault( 'ID', part )
    return keys___values


def parse_proteome_headers( input_proteome_path ):
    """Parse a repository T1 proteome FASTA and return a list of
    (gene_symbol, transcript_acc, protein_acc) tuples.

    Header format: >Genus_species-<gene_id>-<transcript_id>-<protein_id>
    Most repository proteomes have transcript_id == protein_id.
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


def parse_repository_gff3( input_gff3_path ):
    """Parse a repository GFF3/GTF and return:

    feature_ids___coordinates:
        feature_id -> ( Seqid, Start, End, Strand )
        Indexed by ANY feature with an ID we can extract (gene, mRNA, transcript).
        Used for gene-coordinate lookups: try gene_symbol first, then transcript_acc
        as fallback (handles cases where there's no separate gene feature, only mRNA).

    cds_intervals_index:
        key -> [ (cds_start, cds_end), ... ]
        Key is registered under MULTIPLE values per CDS:
          - Parent= value (could be gene or mRNA)
          - transcript_id= attribute value (GFF3 or GTF style)
        Either of these may match the proteome's transcript_acc.

    All keys normalized (hyphens -> underscores) to match proteome form.

    Heterogeneity handled:
      - Beroe_ovata: CDS has Parent=gene_id AND transcript_id attribute
      - Hormiphora: gene/mRNA/CDS hierarchy, mRNA's ID matches transcript_acc
      - Amphiscolops: gene with bare ID, CDS with GTF-style attributes
      - Lissachatina: no gene feature, just mRNA + CDS (mRNA acts as gene)
    """
    feature_ids___coordinates = {}
    exon_intervals_index = {}
    cds_intervals_index = {}
    mrna_ids___parent_genes = {}  # for transitive lookups
    mrna_ids___protein_accs = {}  # mRNA ID -> proteome transcript_acc, for Nautilus-style lookups

    input_gff3 = open( input_gff3_path, 'r' )
    for line in input_gff3:
        if line.startswith( '#' ) or not line.strip():
            continue
        parts = line.rstrip( '\n' ).split( '\t' )
        if len( parts ) < 9:
            continue
        seqid = parts[ 0 ]
        feature_type = parts[ 2 ]
        # Defensive: some repository GFFs have malformed lines (e.g., a Perl
        # object dump prepended to the first record in Beroe). Skip those.
        try:
            feature_start = int( parts[ 3 ] )
            feature_end = int( parts[ 4 ] )
        except ValueError:
            continue
        strand = parts[ 6 ]
        attributes = parse_gff3_attributes( parts[ 8 ] )

        feature_id = normalize_id( attributes.get( 'ID', '' ) )
        gene_id_attr = normalize_id( attributes.get( 'gene_id', '' ) )
        transcript_id_attr = normalize_id( attributes.get( 'transcript_id', '' ) )

        # Additional attributes that some repository GFFs use as proteome-matching keys.
        accession_attr = normalize_id( attributes.get( 'Accession', '' ) )           # Nautilus_pompilius
        protein_accession_attr = normalize_id( attributes.get( 'Protein_Accession', '' ) )  # Nautilus CDS
        protein_id_attr = normalize_id( attributes.get( 'protein_id', '' ) )         # NCBI-style CDS (Hypsibius)

        if feature_type in ( 'gene', 'mRNA', 'transcript' ):
            # Index ANY feature ID we can extract from any of these feature types.
            # First-seen wins, so 'gene' features (parsed first when present) take
            # priority over mRNA features. When no gene feature exists (Lissachatina),
            # the mRNA's coordinates serve as gene coordinates.
            # Accession attribute helps Nautilus_pompilius where the proteome's
            # gene_symbol is the gene feature's Accession=GWHGBECW000001, not its ID.
            for candidate_id in ( feature_id, gene_id_attr, transcript_id_attr, accession_attr ):
                if candidate_id and candidate_id not in feature_ids___coordinates:
                    feature_ids___coordinates[ candidate_id ] = (
                        seqid, feature_start, feature_end, strand
                    )

            # Track mRNA -> parent gene so we can transitively index CDS intervals
            # by gene_id when the proteome stores only the gene_id (Ministeria,
            # Pigoraptor: proteome has 'Mvib_g1' which strips to 'g1', but CDS
            # Parent in GFF is 'g1.t1'). After parse, we'll copy CDS intervals
            # from mrna keys to gene_parent keys.
            if feature_type == 'mRNA':
                parent_attr = normalize_id( attributes.get( 'Parent', '' ) )
                if feature_id and parent_attr:
                    mrna_ids___parent_genes[ feature_id ] = parent_attr

        elif feature_type == 'exon':
            # Same multi-key indexing strategy as CDS — exon Parent= usually
            # points to mRNA but transcript_id attribute may also be present.
            parent_id = normalize_id( attributes.get( 'Parent', '' ) )
            if ',' in parent_id:
                parent_id = parent_id.split( ',' )[ 0 ]
            for candidate_key in ( parent_id, transcript_id_attr, feature_id ):
                if candidate_key:
                    exon_intervals_index.setdefault( candidate_key, [] ).append(
                        ( feature_start, feature_end )
                    )

        elif feature_type == 'CDS':
            # Index CDS intervals under EVERY available key so proteome lookup
            # can try multiple paths. The protein_id and Protein_Accession attributes
            # let us match Hypsibius_dujardini (proteome transcript_acc=OQV25851.1
            # equals CDS protein_id=OQV25851.1) and Nautilus_pompilius (CDS
            # Protein_Accession=GWHPBECW000001 matches proteome transcript_acc).
            parent_id = normalize_id( attributes.get( 'Parent', '' ) )
            if ',' in parent_id:
                parent_id = parent_id.split( ',' )[ 0 ]
            for candidate_key in ( parent_id, transcript_id_attr, feature_id,
                                   protein_id_attr, protein_accession_attr ):
                if candidate_key:
                    cds_intervals_index.setdefault( candidate_key, [] ).append(
                        ( feature_start, feature_end )
                    )
            # Track mRNA -> protein_acc so we can transitively index exons under
            # the protein accession (Nautilus has exons keyed only by mRNA ID,
            # but the proteome's transcript_acc is the protein accession from CDS).
            if parent_id and ( protein_id_attr or protein_accession_attr ):
                mrna_ids___protein_accs[ parent_id ] = (
                    protein_id_attr or protein_accession_attr
                )

    input_gff3.close()

    # Post-process 1: copy exon and CDS intervals from mRNA-id keys to their
    # parent-gene keys. Lets the proteome look up by gene_id when transcript_acc
    # isn't a distinct identifier (e.g., Ministeria has gene_id in all 3 fields).
    for mrna_id, parent_gene_id in mrna_ids___parent_genes.items():
        if mrna_id in exon_intervals_index and parent_gene_id not in exon_intervals_index:
            exon_intervals_index[ parent_gene_id ] = list( exon_intervals_index[ mrna_id ] )
        if mrna_id in cds_intervals_index and parent_gene_id not in cds_intervals_index:
            cds_intervals_index[ parent_gene_id ] = list( cds_intervals_index[ mrna_id ] )

    # Post-process 2: copy exon intervals from mRNA-id keys to their protein_acc
    # keys (Nautilus_pompilius: exons keyed by mRNA ID 'EVMG007869.1', but
    # proteome transcript_acc is the protein accession 'GWHPBECW000001' which
    # only appears on the CDS Protein_Accession attribute).
    for mrna_id, protein_acc in mrna_ids___protein_accs.items():
        if mrna_id in exon_intervals_index and protein_acc not in exon_intervals_index:
            exon_intervals_index[ protein_acc ] = list( exon_intervals_index[ mrna_id ] )

    return feature_ids___coordinates, exon_intervals_index, cds_intervals_index


def derive_utrs_from_exons_and_cds( merged_exons, merged_cds, strand ):
    """Same UTR-derivation as the NCBI extractor; see that file for full doc."""
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


def discover_repository_species( input_proteome_dir ):
    """Discover repository species by scanning proteome filenames.

    Filename pattern: <Genus_species>-genome-<source>-downloaded_<date>.aa
    """
    species_set = set()
    for proteome_path in Path( input_proteome_dir ).glob( '*-genome-*.aa' ):
        name = proteome_path.name
        # Skip Kim and NCBI proteomes that may be in the same dir
        if 'kim_2025' in name or '-ncbi_' in name:
            continue
        idx = name.find( '-genome-' )
        if idx > 0:
            species_set.add( name[ : idx ] )
    return sorted( species_set )


def find_input_files_for_species( genus_species, input_gff3_dir, input_proteome_dir ):
    """Locate the GFF3 and proteome for one repository species.

    Both filenames pattern: <Genus_species>-genome-<source>-downloaded_<date>.{gff3,aa}
    """
    gff3_candidates = list(
        Path( input_gff3_dir ).glob( f"{genus_species}-genome-*.gff3" )
    )
    proteome_candidates = list(
        Path( input_proteome_dir ).glob( f"{genus_species}-genome-*.aa" )
    )
    # Filter Kim/NCBI proteomes if accidentally present
    proteome_candidates = [ p for p in proteome_candidates
                            if 'kim_2025' not in p.name and '-ncbi_' not in p.name ]
    return gff3_candidates, proteome_candidates


def extract_gene_coordinates_for_species(
    genus_species,
    input_gff3_path,
    input_proteome_path,
    output_tsv_all_inclusive_path,
    output_tsv_gene_vs_protein_path,
    output_unmatched_path,
):
    """Two-tier extraction. Repository genomes vary widely:
      - Some have explicit gene + exon + CDS + UTR-bearing exons -> Tier 1
      - Some have gene + exon + CDS but exon == CDS (no UTR predictions) -> Tier 2 only
      - Some have gene + CDS only (no exon records) -> Tier 2 only (Group B recovery)
    Gene + CDS are the minimum for Tier 2 inclusion. If exons are absent, the per-gene
    record can still produce gene_size / cds_size / protein_size for Tier 2.
    """
    stats = {
        'genus_species': genus_species,
        'proteome_entries': 0,
        'rows_written': 0,
        'genes_with_exons': 0,
        'genes_with_utr': 0,
        'tier': '',
        'wrote_all_inclusive': 'no',
        'wrote_gene_vs_protein': 'no',
        'missing_gene_lookups': 0,
        'missing_cds_lookups': 0,
        'status': 'PROCESSED',
        'notes': '',
    }

    tuples_in_proteome = parse_proteome_headers( input_proteome_path )
    stats[ 'proteome_entries' ] = len( tuples_in_proteome )
    if not tuples_in_proteome:
        stats[ 'status' ] = 'SKIPPED_EMPTY_PROTEOME'
        return stats

    feature_ids___coordinates, exon_intervals_index, cds_intervals_index = parse_repository_gff3( input_gff3_path )

    output_unmatched = open( output_unmatched_path, 'w' )
    output_unmatched.write( '\t'.join( [
        'gene_symbol_from_proteome', 'transcript_acc_from_proteome', 'protein_acc_from_proteome', 'reason',
    ] ) + '\n' )

    def lookup_with_prefix_fallback( key, index ):
        if key in index:
            return index[ key ]
        if '_' in key:
            stripped = key.split( '_', 1 )[ 1 ]
            if stripped in index:
                return index[ stripped ]
        return None

    gene_records = []

    for gene_symbol, transcript_acc, protein_acc in tuples_in_proteome:
        gene_record = lookup_with_prefix_fallback( gene_symbol, feature_ids___coordinates )
        if gene_record is None:
            gene_record = lookup_with_prefix_fallback( transcript_acc, feature_ids___coordinates )
        if gene_record is None:
            stats[ 'missing_gene_lookups' ] += 1
            output_unmatched.write( '\t'.join( [ gene_symbol, transcript_acc, protein_acc, 'missing_gene_lookup' ] ) + '\n' )
            continue
        seqid, gene_start, gene_end, strand = gene_record

        # CDS is required (for protein_size). If absent, the gene cannot be in either tier.
        cds_intervals = lookup_with_prefix_fallback( transcript_acc, cds_intervals_index ) or []
        if not cds_intervals:
            cds_intervals = lookup_with_prefix_fallback( gene_symbol, cds_intervals_index ) or []
        if not cds_intervals:
            stats[ 'missing_cds_lookups' ] += 1
            output_unmatched.write( '\t'.join( [ gene_symbol, transcript_acc, protein_acc, 'missing_cds_lookup' ] ) + '\n' )
            continue

        # Exons are optional — needed for Tier 1 only.
        exon_intervals = lookup_with_prefix_fallback( transcript_acc, exon_intervals_index ) or []
        if not exon_intervals:
            exon_intervals = lookup_with_prefix_fallback( gene_symbol, exon_intervals_index ) or []

        merged_cds = merge_intervals( cds_intervals )
        merged_exons = merge_intervals( exon_intervals ) if exon_intervals else []

        gene_size = gene_end - gene_start + 1
        cds_size = intervals_total_size( merged_cds )
        protein_size = cds_size // 3

        if merged_exons:
            stats[ 'genes_with_exons' ] += 1
            transcript_size = intervals_total_size( merged_exons )
            utr_5prime, utr_3prime = derive_utrs_from_exons_and_cds( merged_exons, merged_cds, strand )
            utr_5prime_size = intervals_total_size( utr_5prime )
            utr_3prime_size = intervals_total_size( utr_3prime )
            if ( utr_5prime_size + utr_3prime_size ) > 0:
                stats[ 'genes_with_utr' ] += 1
        else:
            transcript_size = 0
            utr_5prime, utr_3prime = [], []
            utr_5prime_size = 0
            utr_3prime_size = 0

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
        'Source_Gene_ID', 'Seqid', 'Gene_Start', 'Gene_End', 'Strand',
        'Gene_Size', 'CDS_Intervals', 'CDS_Size', 'Protein_Size',
    ] ) + '\n' )
    for r in gene_records:
        output_tsv.write( '\t'.join( [
            r[ 'gene_symbol' ], r[ 'seqid' ], str( r[ 'gene_start' ] ), str( r[ 'gene_end' ] ), r[ 'strand' ],
            str( r[ 'gene_size' ] ), intervals_to_string( r[ 'merged_cds' ] ),
            str( r[ 'cds_size' ] ), str( r[ 'protein_size' ] ),
        ] ) + '\n' )
    output_tsv.close()
    stats[ 'wrote_gene_vs_protein' ] = 'yes'

    # Write Type 1 (all_inclusive) only if tier 1.
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
            # Some Tier 1 species may have a few genes without exons — write them with empty exon fields.
            output_tsv.write( '\t'.join( [
                r[ 'gene_symbol' ], r[ 'seqid' ], str( r[ 'gene_start' ] ), str( r[ 'gene_end' ] ), r[ 'strand' ],
                str( r[ 'gene_size' ] ), intervals_to_string( r[ 'merged_exons' ] ), str( r[ 'transcript_size' ] ),
                intervals_to_string( r[ 'merged_cds' ] ), str( r[ 'cds_size' ] ), str( r[ 'protein_size' ] ),
                intervals_to_string( r[ 'utr_5prime' ] ), str( r[ 'utr_5prime_size' ] ),
                intervals_to_string( r[ 'utr_3prime' ] ), str( r[ 'utr_3prime_size' ] ),
            ] ) + '\n' )
        stats[ 'wrote_all_inclusive' ] = 'yes'

    return stats


def write_summary( summary_records, output_summary_path ):
    output_summary = open( output_summary_path, 'w' )
    columns = [
        ( 'genus_species', 'species name in Genus_species format' ),
        ( 'status', 'PROCESSED or SKIPPED_* status' ),
        ( 'tier', 'all_inclusive (>=50% genes have UTR) or gene_vs_protein (CDS-only or no UTR)' ),
        ( 'wrote_all_inclusive', 'whether tier-1 TSV was written (yes/no)' ),
        ( 'wrote_gene_vs_protein', 'whether tier-2 TSV was written (yes/no)' ),
        ( 'proteome_entries', 'number of header tuples parsed from T1 proteome' ),
        ( 'rows_written', 'number of TSV rows written for this species' ),
        ( 'genes_with_exons', 'number of genes for which GFF had exon records' ),
        ( 'genes_with_utr', 'number of genes for which UTR derivation produced any UTR sequence' ),
        ( 'missing_gene_lookups', 'count of proteome entries whose gene_symbol was not found in GFF gene index' ),
        ( 'missing_cds_lookups', 'count of proteome entries whose transcript_acc had no CDS features' ),
        ( 'notes', 'free text notes' ),
    ]
    header = '\t'.join( f"{name} ({description})" for name, description in columns ) + '\n'
    output_summary.write( header )
    for record in summary_records:
        output = '\t'.join( str( record.get( name, '' ) ) for name, _ in columns ) + '\n'
        output_summary.write( output )
    output_summary.close()


def make_relative_symlink( source_path, link_path ):
    source_path = Path( source_path ).resolve()
    link_path = Path( link_path )
    if link_path.is_symlink() or link_path.exists():
        link_path.unlink()
    relative_target = os.path.relpath( source_path, link_path.parent )
    link_path.symlink_to( relative_target )


def main():
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument( '--gff3-dir', required = True )
    parser.add_argument( '--proteome-dir', required = True )
    parser.add_argument( '--output-dir', required = True )
    parser.add_argument( '--symlink-dir-all-inclusive', required = True, help = 'output_to_input/gene_coordinates_all_inclusive dir' )
    parser.add_argument( '--symlink-dir-gene-vs-protein', required = True, help = 'output_to_input/gene_coordinates_gene_vs_protein dir' )
    parser.add_argument( '--single-species', default = '' )
    arguments = parser.parse_args()

    input_gff3_dir = Path( arguments.gff3_dir )
    input_proteome_dir = Path( arguments.proteome_dir )
    output_dir = Path( arguments.output_dir )
    output_dir.mkdir( parents = True, exist_ok = True )
    symlink_dir_all_inclusive = Path( arguments.symlink_dir_all_inclusive )
    symlink_dir_all_inclusive.mkdir( parents = True, exist_ok = True )
    symlink_dir_gene_vs_protein = Path( arguments.symlink_dir_gene_vs_protein )
    symlink_dir_gene_vs_protein.mkdir( parents = True, exist_ok = True )

    species_to_process = discover_repository_species( input_proteome_dir )
    if arguments.single_species:
        species_to_process = [ s for s in species_to_process if s == arguments.single_species ]

    print( f"Discovered {len( species_to_process )} repository species" )

    summary_records = []

    for genus_species in species_to_process:
        print( "" )
        print( f"=== {genus_species} ===" )

        gff3_candidates, proteome_candidates = find_input_files_for_species(
            genus_species, input_gff3_dir, input_proteome_dir
        )

        if not gff3_candidates:
            record = {
                'genus_species': genus_species,
                'status': 'SKIPPED_NO_GFF3',
                'notes': f"no GFF3 matched {genus_species}-genome-*.gff3 in {input_gff3_dir}",
            }
            summary_records.append( record )
            print( f"  SKIPPED_NO_GFF3" )
            continue

        if not proteome_candidates:
            record = {
                'genus_species': genus_species,
                'status': 'SKIPPED_NO_PROTEOME',
                'notes': f"no proteome matched {genus_species}-genome-*.aa",
            }
            summary_records.append( record )
            print( f"  SKIPPED_NO_PROTEOME" )
            continue

        gff3_path = gff3_candidates[ 0 ]
        proteome_path = proteome_candidates[ 0 ]
        output_unmatched_path = output_dir / f"{genus_species}-unmatched_proteome_entries.tsv"
        output_tsv_all_inclusive_path = output_dir / f"{genus_species}-gene_coordinates_all_inclusive.tsv"
        output_tsv_gene_vs_protein_path = output_dir / f"{genus_species}-gene_coordinates_gene_vs_protein.tsv"

        print( f"  GFF3:     {gff3_path.name}" )
        print( f"  Proteome: {proteome_path.name}" )

        stats = extract_gene_coordinates_for_species(
            genus_species, gff3_path, proteome_path,
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

        print( f"  rows_written:           {stats[ 'rows_written' ]:>8d}" )
        print( f"  genes_with_exons:       {stats[ 'genes_with_exons' ]:>8d}" )
        print( f"  genes_with_utr:         {stats[ 'genes_with_utr' ]:>8d}" )
        print( f"  tier:                   {stats[ 'tier' ]}" )
        print( f"  missing_gene_lookups:   {stats[ 'missing_gene_lookups' ]:>8d}" )
        print( f"  missing_cds_lookups:    {stats[ 'missing_cds_lookups' ]:>8d}" )

    output_summary_path = output_dir / 'extraction_summary.tsv'
    write_summary( summary_records, output_summary_path )

    print( "" )
    print( "========================================================================" )
    print( f"Summary: {output_summary_path}" )
    print( f"  Tier 1 (all_inclusive)  symlinked into {symlink_dir_all_inclusive}/" )
    print( f"  Tier 2 (gene_vs_protein) symlinked into {symlink_dir_gene_vs_protein}/" )
    print( "========================================================================" )

    n_tier_1 = sum( 1 for r in summary_records if r.get( 'wrote_all_inclusive' ) == 'yes' )
    n_tier_2 = sum( 1 for r in summary_records if r.get( 'wrote_gene_vs_protein' ) == 'yes' )
    print( f"Tier 1 (all_inclusive):  {n_tier_1} species" )
    print( f"Tier 2 (gene_vs_protein): {n_tier_2} species (Type 1 species are also here as superset)" )


if __name__ == '__main__':
    main()
