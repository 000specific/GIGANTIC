#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 21 | Purpose: Rewrite species column headers with short labels
# Human: Eric Edsinger

"""
GIGANTIC homolog_counts - Script 006: Rewrite species column headers

Reads a count TSV (Feature_ID + Total_Count + Total_Species_Count + 70
phyloname-headed species columns) produced by scripts 002/003/004 and writes
a copy with the 70 species column headers replaced by short labels:

  Metazoans (phyloname starts with 'Metazoa_'):
    "Phylum Genus species"

  Non-metazoans:
    "<first non-digit clade> Genus species"
    Scan parts[0..4] for the first field containing no digit characters.
    Fallback: if all upper ranks contain digits, use Kingdom (parts[0])
    anyway. This preserves data honesty for unusual cases like
    Corallochytrium_limacisporum where all 5 upper ranks are KingdomNNNN-
    style placeholders.

The first 3 columns (Feature_ID, Total_Count, Total_Species_Count) keep
their original self-documenting headers. Only the 70 species columns are
rewritten. Data rows pass through unchanged.

Usage:
    python3 006_ai-python-rewrite_species_column_headers.py \\
        --input-tsv  <path-to-N_ai-counts-source.tsv> \\
        --output-tsv <path-to-output-short-headers.tsv>
"""

import argparse
import sys
from pathlib import Path


# Direct short-label overrides for species whose species70 manifest entries
# are uninformative (digit-placeholders or NOTINNCBI for all upper ranks).
# Each override picks a specific real-name clade chosen from outside the
# manifest (user-provided per discussion May 2026).
#   Corallochytrium  -> Filozoa (user-chosen; Corallochytrium is unicellular holozoan)
#   Chromosphaera    -> Ichthyosporea (Class; consistent with the other 4 Ichthyosporea entries)
#   Hoilungia        -> Placozoa (Phylum; manifest says NOTINNCBI but Hoilungia is metazoan placozoan)
# Future cleanup: once the species70 manifest is fixed upstream, these
# overrides can be removed and the standard rule will produce equivalent
# labels for the metazoan case (Hoilungia) directly, and the user can decide
# what to do for Corallochytrium and Chromosphaera at that time.
GENUS_SPECIES___OVERRIDE_SHORT_LABEL = {
    'Corallochytrium_limacisporum': 'Filozoa Corallochytrium limacisporum',
    'Chromosphaera_perkinsii':      'Ichthyosporea Chromosphaera perkinsii',
    'Hoilungia_hongkongensis_H13':  'Placozoa Hoilungia hongkongensis_H13',
}


def short_label_for_phyloname( phyloname ):
    """Derive a short 'Clade Genus species' label from a full phyloname.

    Phyloname structure: Kingdom_Phylum_Class_Order_Family_Genus_species
    (positions 0..4 are taxonomic ranks; position 5 is genus; positions 6+
    are species, potentially multi-word).
    """
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) < 7:
        raise ValueError( f'phyloname has fewer than 7 underscore-separated fields: {phyloname}' )

    genus = parts_phyloname[ 5 ]
    species = '_'.join( parts_phyloname[ 6: ] )
    genus_species = f'{genus}_{species}'

    # Direct short-label override for species whose manifest taxonomy is
    # uninformative. Skips the standard clade-from-phyloname derivation.
    if genus_species in GENUS_SPECIES___OVERRIDE_SHORT_LABEL:
        return GENUS_SPECIES___OVERRIDE_SHORT_LABEL[ genus_species ]

    if parts_phyloname[ 0 ] == 'Metazoa':
        clade = parts_phyloname[ 1 ]  # Phylum
    else:
        # First non-digit clade among parts[0..4]
        clade = None
        for candidate in parts_phyloname[ :5 ]:
            if not any( ch.isdigit() for ch in candidate ):
                clade = candidate
                break
        if clade is None:
            # Fallback: use Kingdom even if it contains digits
            clade = parts_phyloname[ 0 ]

    return f'{clade} {genus} {species}'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Rewrite species column headers with short Clade-Genus-species labels'
    )
    parser.add_argument(
        '--input-tsv',
        required = True,
        help = 'Path to count TSV produced by 002/003/004'
    )
    parser.add_argument(
        '--output-tsv',
        required = True,
        help = 'Path to output TSV with short species headers'
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    input_tsv_path = Path( args.input_tsv )
    output_tsv_path = Path( args.output_tsv )

    if not input_tsv_path.exists():
        print( f'ERROR: input TSV not found: {input_tsv_path}', file = sys.stderr )
        sys.exit( 1 )

    output_tsv_path.parent.mkdir( parents = True, exist_ok = True )

    rewrites_count = 0
    rows_written = 0
    sample_labels = []

    with open( input_tsv_path, 'r' ) as input_tsv, open( output_tsv_path, 'w' ) as output_tsv:
        # ----------------------------------------------------------------
        # Process header line (first line)
        # ----------------------------------------------------------------
        # Species column headers in the input look like:
        #   <phyloname> (<description>)
        # We extract <phyloname> by splitting on " (".

        try:
            header_line = next( input_tsv )
        except StopIteration:
            print( f'ERROR: input TSV is empty: {input_tsv_path}', file = sys.stderr )
            sys.exit( 1 )

        header_line = header_line.rstrip( '\n' )
        parts = header_line.split( '\t' )

        # Expected layout:
        #   cols 0..2  : Feature_ID, Total_Count, Total_Species_Count
        #   cols 3..72 : 70 species columns (rewritten)
        #   cols 73..  : 0 or more extra columns (pass through unchanged)
        if len( parts ) < 73:
            print( f'ERROR: header has {len(parts)} columns, expected at least 73 (3 summary + 70 species)', file = sys.stderr )
            print( f'       input: {input_tsv_path}', file = sys.stderr )
            sys.exit( 1 )

        new_parts = list( parts[ :3 ] )  # keep summary columns as-is

        for col_index in range( 3, 73 ):
            original_header = parts[ col_index ]
            if ' (' in original_header:
                phyloname = original_header.split( ' (', 1 )[ 0 ]
            else:
                phyloname = original_header

            try:
                short_label = short_label_for_phyloname( phyloname )
            except ValueError as parse_error:
                print( f'ERROR: cannot derive short label for column {col_index+1}', file = sys.stderr )
                print( f'       header: {original_header!r}', file = sys.stderr )
                print( f'       error:  {parse_error}', file = sys.stderr )
                sys.exit( 1 )

            new_parts.append( short_label )
            rewrites_count += 1
            if len( sample_labels ) < 5:
                sample_labels.append( ( phyloname, short_label ) )

        # Pass through extra columns (e.g., Human_Gene_Names_List, phylum lists)
        passthrough_count = len( parts ) - 73
        if passthrough_count > 0:
            new_parts.extend( parts[ 73: ] )

        output_tsv.write( '\t'.join( new_parts ) + '\n' )

        # ----------------------------------------------------------------
        # Pass through data rows unchanged
        # ----------------------------------------------------------------

        for line in input_tsv:
            output_tsv.write( line )
            rows_written += 1

    print( f'OK: {input_tsv_path.name}' )
    print( f'    -> {output_tsv_path}' )
    print( f'    Header columns rewritten: {rewrites_count} / 70' )
    print( f'    Extra columns passed through: {passthrough_count}' )
    print( f'    Data rows passed through: {rows_written}' )
    print( f'    First 5 rewrites (phyloname -> short label):' )
    for phyloname, short_label in sample_labels:
        print( f'      {phyloname}' )
        print( f'        -> {short_label}' )


if __name__ == '__main__':
    main()
