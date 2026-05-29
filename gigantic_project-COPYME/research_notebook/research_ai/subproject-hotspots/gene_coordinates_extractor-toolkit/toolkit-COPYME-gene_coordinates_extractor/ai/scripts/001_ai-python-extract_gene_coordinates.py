#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 29 | Purpose: Extract per-species gene coordinates (Source_Gene_ID, Seqid, Gene_Start, Gene_End, Strand) from GFF3 annotation files for hotspots
# Human: Eric Edsinger
"""
Extract per-species gene-coordinate TSVs from GFF3 annotation files.

The hotspots subproject (BLOCK_identify_hotspots) joins these per-species
TSVs against self-BLAST results to find clusters of paralogs sitting next
to each other on a chromosome.

Output schema (matches the existing species70 convention):
    Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand

The header row uses the same descriptive-parenthetical style as the
canonical species70 outputs:
    Source_Gene_ID (source gene identifier matching g_ field in GIGANTIC headers)
    Seqid (chromosome or scaffold)
    Gene_Start (1-based inclusive genomic start coordinate of gene)
    Gene_End (1-based inclusive genomic end coordinate of gene)
    Strand (plus or minus strand)

GFF flavor handling
-------------------
Three flavors are accepted automatically:

  1. NCBI RefSeq / GenBank
     - Feature type = "gene"
     - Column 9 = key=value pairs (e.g. "ID=gene-LOC123;gene=LOC123;...").
     - Source_Gene_ID extracted by preferring the `gene=` attribute, then
       falling back to `ID=` with the `gene-` prefix stripped, then `Name=`.

  2. AUGUSTUS (e.g. Schizocardium)
     - Feature type = "gene"
     - Column 9 is a bare token (e.g. "g1", "g2"). Used as the
       Source_Gene_ID directly.

  3. BRAKER (e.g. Mesocentrotus)
     - May lack `gene` rows altogether; only `mRNA` / `transcript` rows.
     - When no `gene` rows are present, the script falls back to grouping
       transcripts by their common ID stem (everything before the final
       `.tN` suffix) and reports each gene as one row with the min(Start)
       and max(End) across its transcripts.

CLI
---
    python3 001_ai-python-extract_gene_coordinates.py \\
        --annotations-dir <dir>   \\
        --output-dir <dir>        \\
        [--species <Genus_species> ...]   (optional whitelist)
        [--log-file <path>]

The script auto-discovers species from filenames of the form
`<phyloname>-genome.gff3` (the genomesDB STEP_4 convention). It writes one
TSV per species into --output-dir and prints a per-species count summary
to the log.

Exit code 0 on success. Exit 1 if ANY species produces zero rows
(fail-fast: a zero-row TSV would silently break hotspots).
"""

import argparse
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path


GFF_FILENAME_RE = re.compile( r"^(?P<phyloname>.+?)-genome\.gff3$" )

# Phyloname token layout: Kingdom_Phylum_Class_Order_Family_Genus_species[_subspecies]
# We need to recover the trailing Genus_species[_subspecies] portion for the
# output filename (matching the species70 convention: <Genus_species>-gene_coordinates.tsv).
# Strategy: phyloname has 5 leading rank tokens (Kingdom..Family); everything
# after is the binomial (or trinomial). For Genus + species: 2 tokens; for
# subspecies: 3 tokens. We don't know in advance how many trailing tokens
# there are, so we look up the species names from the proteomes_dir or
# annotations_dir filenames — both are produced by genomesDB STEP_2 from
# the same phylonames TSV, so they're consistent.
#
# Simpler: take all tokens AFTER the 5th (Family) underscore. That gives us
# whatever genus_species[_subspecies] form is in use.

GFF_LEADING_RANK_COUNT = 5  # Kingdom + Phylum + Class + Order + Family


# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------

def setup_logging( log_path ):
    logger = logging.getLogger( "extract_gene_coordinates" )
    logger.setLevel( logging.INFO )

    fh = logging.FileHandler( log_path, mode = "w" )
    fh.setLevel( logging.INFO )

    sh = logging.StreamHandler( sys.stdout )
    sh.setLevel( logging.INFO )

    fmt = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    fh.setFormatter( fmt )
    sh.setFormatter( fmt )

    logger.addHandler( fh )
    logger.addHandler( sh )
    return logger


# ----------------------------------------------------------------------------
# Phyloname → genus_species
# ----------------------------------------------------------------------------

def phyloname_to_genus_species( phyloname ):
    """
    Drop the 5 leading rank tokens (Kingdom..Family). Whatever remains is
    Genus_species[_subspecies].
    """

    parts = phyloname.split( "_" )
    if len( parts ) <= GFF_LEADING_RANK_COUNT:
        raise ValueError(
            f"Phyloname has too few tokens for Genus_species: {phyloname!r}"
        )
    return "_".join( parts[ GFF_LEADING_RANK_COUNT : ] )


# ----------------------------------------------------------------------------
# GFF column 9 attribute parsing
# ----------------------------------------------------------------------------

def parse_attributes( attr_str ):
    """
    Parse the GFF column-9 attribute string into a dict. Returns None when
    the string doesn't look like key=value pairs (e.g. plain AUGUSTUS 'g1').
    """

    if "=" not in attr_str:
        return None
    out = {}
    for piece in attr_str.split( ";" ):
        piece = piece.strip()
        if not piece or "=" not in piece:
            continue
        k, v = piece.split( "=", 1 )
        out[ k.strip() ] = v.strip()
    return out


# ----------------------------------------------------------------------------
# Source_Gene_ID extraction (per gene-row)
# ----------------------------------------------------------------------------

def derive_source_gene_id_from_gene_row( attr_str ):
    """
    Given the GFF column-9 string from a `gene` feature row, return the
    Source_Gene_ID. Tries (in order):
      1. `gene=` attribute (NCBI: this is the gene symbol / locus ID).
      2. `ID=` with optional `gene-` prefix stripped.
      3. `Name=` as a last resort.
      4. Bare token (AUGUSTUS-style: column 9 is just `g1`).

    Returns the string, or None if nothing usable was found.
    """

    attrs = parse_attributes( attr_str )

    if attrs is None:
        bare = attr_str.strip()
        return bare if bare else None

    if "gene" in attrs:
        return attrs[ "gene" ]
    if "ID" in attrs:
        raw = attrs[ "ID" ]
        if raw.startswith( "gene-" ):
            return raw[ len( "gene-" ) : ]
        return raw
    if "Name" in attrs:
        return attrs[ "Name" ]
    return None


def derive_source_gene_id_from_mrna_row( attr_str ):
    """
    Fallback for GFFs without `gene` rows (e.g. some BRAKER outputs). Pulls
    the gene-level stem from an `mRNA` / `transcript` row's `Parent=`
    attribute (preferred) or, failing that, by stripping a trailing `.tN`
    from `ID=` or the bare token.
    """

    attrs = parse_attributes( attr_str )

    if attrs is None:
        bare = attr_str.strip()
        if not bare:
            return None
        return strip_transcript_suffix( bare )

    if "Parent" in attrs:
        # Parent may itself be "gene-LOC123" or just "LOC123".
        raw = attrs[ "Parent" ]
        if raw.startswith( "gene-" ):
            return raw[ len( "gene-" ) : ]
        return raw

    if "ID" in attrs:
        return strip_transcript_suffix( attrs[ "ID" ] )

    return None


_TRANSCRIPT_SUFFIX_RE = re.compile( r"\.t\d+$" )

def strip_transcript_suffix( ident ):
    """Strip a trailing `.tN` (BRAKER transcript suffix)."""

    return _TRANSCRIPT_SUFFIX_RE.sub( "", ident )


# ----------------------------------------------------------------------------
# Per-species GFF → gene-row list
# ----------------------------------------------------------------------------

def extract_genes_from_gff( gff_path, logger ):
    """
    Returns a list of dicts:
      { 'Source_Gene_ID', 'Seqid', 'Gene_Start', 'Gene_End', 'Strand' }

    Strategy:
      Pass 1: collect every `gene` row.
      If pass 1 yielded ≥ 1 row → return those.
      Else: pass 2 over `mRNA` / `transcript` rows, grouping by stem and
      collapsing each group into one row (min start, max end, single strand).
    """

    gene_rows = []
    transcript_rows_by_stem = defaultdict( list )

    with open( gff_path ) as f:
        for line in f:
            if not line or line.startswith( "#" ):
                continue
            line = line.rstrip( "\n" )
            cols = line.split( "\t" )
            if len( cols ) < 9:
                continue

            seqid = cols[ 0 ]
            feature_type = cols[ 2 ].lower()
            start_s = cols[ 3 ]
            end_s = cols[ 4 ]
            strand = cols[ 6 ]
            attr_str = cols[ 8 ]

            try:
                start = int( start_s )
                end = int( end_s )
            except ValueError:
                continue

            if feature_type == "gene":
                source_id = derive_source_gene_id_from_gene_row( attr_str )
                if source_id is None:
                    continue
                gene_rows.append( {
                    "Source_Gene_ID": source_id,
                    "Seqid":          seqid,
                    "Gene_Start":     start,
                    "Gene_End":       end,
                    "Strand":         strand,
                } )

            elif feature_type in ( "mrna", "transcript" ):
                if gene_rows:
                    # We've already started collecting gene rows; ignore
                    # the mRNA fallback to avoid double-counting.
                    continue
                stem = derive_source_gene_id_from_mrna_row( attr_str )
                if stem is None:
                    continue
                transcript_rows_by_stem[ stem ].append( {
                    "Seqid":      seqid,
                    "Gene_Start": start,
                    "Gene_End":   end,
                    "Strand":     strand,
                } )

    if gene_rows:
        return gene_rows

    # No gene rows: collapse transcript rows by stem.
    if not transcript_rows_by_stem:
        return []

    logger.warning(
        f"  No 'gene' rows in {gff_path.name}; falling back to mRNA/transcript "
        f"rows ({sum( len(v) for v in transcript_rows_by_stem.values() )} "
        f"transcripts across {len(transcript_rows_by_stem)} gene stems)"
    )

    collapsed = []
    for stem, txs in transcript_rows_by_stem.items():
        # Use seqid + strand from the FIRST transcript; min-start, max-end.
        first = txs[ 0 ]
        collapsed.append( {
            "Source_Gene_ID": stem,
            "Seqid":          first[ "Seqid" ],
            "Gene_Start":     min( t[ "Gene_Start" ] for t in txs ),
            "Gene_End":       max( t[ "Gene_End" ] for t in txs ),
            "Strand":         first[ "Strand" ],
        } )

    return collapsed


# ----------------------------------------------------------------------------
# Per-species TSV writer
# ----------------------------------------------------------------------------

OUTPUT_HEADER = [
    "Source_Gene_ID (source gene identifier matching g_ field in GIGANTIC headers)",
    "Seqid (chromosome or scaffold)",
    "Gene_Start (1-based inclusive genomic start coordinate of gene)",
    "Gene_End (1-based inclusive genomic end coordinate of gene)",
    "Strand (plus or minus strand)",
]
OUTPUT_KEYS = [ "Source_Gene_ID", "Seqid", "Gene_Start", "Gene_End", "Strand" ]


def write_per_species_tsv( rows, output_path ):
    with open( output_path, "w" ) as f:
        f.write( "\t".join( OUTPUT_HEADER ) + "\n" )
        for row in rows:
            f.write(
                "\t".join( str( row[ k ] ) for k in OUTPUT_KEYS ) + "\n"
            )


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument(
        "--annotations-dir", required = True,
        help = "Directory of <phyloname>-genome.gff3 files.",
    )
    parser.add_argument(
        "--output-dir", required = True,
        help = "Directory to write <genus_species>-gene_coordinates.tsv files.",
    )
    parser.add_argument(
        "--log-file", required = True,
        help = "Path for the workflow log.",
    )
    parser.add_argument(
        "--species", nargs = "*", default = None,
        help = "Optional whitelist of Genus_species values to process. "
               "When omitted, every *.gff3 in --annotations-dir is processed.",
    )
    args = parser.parse_args()

    annotations_dir = Path( args.annotations_dir ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    log_path = Path( args.log_file ).resolve()

    output_dir.mkdir( parents = True, exist_ok = True )
    log_path.parent.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( log_path )
    logger.info( f"annotations-dir: {annotations_dir}" )
    logger.info( f"output-dir:      {output_dir}" )

    if not annotations_dir.is_dir():
        logger.error(
            f"--annotations-dir is not a directory: {annotations_dir}"
        )
        sys.exit( 1 )

    # Discover GFF files and pair them with genus_species names.
    gff_paths = sorted( annotations_dir.glob( "*-genome.gff3" ) )
    if not gff_paths:
        logger.error(
            f"No '*-genome.gff3' files found under {annotations_dir}. "
            f"This script expects genomesDB STEP_4 file naming."
        )
        sys.exit( 1 )

    logger.info( f"Discovered {len(gff_paths)} GFF3 files" )

    whitelist = set( args.species ) if args.species else None
    n_written = 0
    n_skipped_by_whitelist = 0
    failures = []

    for gff_path in gff_paths:
        m = GFF_FILENAME_RE.match( gff_path.name )
        if not m:
            logger.warning(
                f"Skipping unrecognized filename: {gff_path.name}"
            )
            continue
        phyloname = m.group( "phyloname" )
        try:
            genus_species = phyloname_to_genus_species( phyloname )
        except ValueError as e:
            logger.error( f"  {gff_path.name}: {e}" )
            failures.append( ( gff_path.name, str( e ) ) )
            continue

        if whitelist is not None and genus_species not in whitelist:
            n_skipped_by_whitelist += 1
            continue

        logger.info( f"Processing {genus_species} ({gff_path.name})" )
        rows = extract_genes_from_gff( gff_path, logger )
        if not rows:
            logger.error(
                f"  {genus_species}: zero gene rows extracted. Hotspots "
                f"will fail on this species — INVESTIGATE the GFF."
            )
            failures.append( ( genus_species, "zero rows extracted" ) )
            continue

        out_name = f"{genus_species}-gene_coordinates.tsv"
        out_path = output_dir / out_name
        write_per_species_tsv( rows, out_path )
        logger.info( f"  {genus_species}: {len(rows)} genes -> {out_name}" )
        n_written += 1

    logger.info( "" )
    logger.info(
        f"SUMMARY: wrote {n_written} TSVs; skipped {n_skipped_by_whitelist} "
        f"(whitelist); {len(failures)} failures"
    )

    if failures:
        for sp, reason in failures:
            logger.error( f"  FAIL: {sp}: {reason}" )
        sys.exit( 1 )


if __name__ == "__main__":
    main()
