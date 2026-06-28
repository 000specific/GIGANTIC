#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: Parse the Gene Ontology go-basic.obo into a GO_ID -> name/namespace mapping TSV (annotation reference data)
# Human: Eric Edsinger

"""
Generate the GO_ID -> GO term name/namespace mapping (annotation reference data).

GIGANTIC annotation outputs (e.g. the raw InterProScan results consumed by the
annogroups `go` parser) carry GO IDs but NOT GO term NAMES. This script parses the
canonical Gene Ontology ontology file (go-basic.obo) into a flat lookup TSV so any
consumer can attach human-readable GO names.

Source (provenance): go-basic.obo from the Gene Ontology Consortium,
    https://purl.obolibrary.org/obo/go/go-basic.obo
Download it next to this script (see reference_go/README.md), then run:
    python3 generate_go_id_to_name.py

Each OBO [Term] stanza yields one PRIMARY row (its `id:`) plus one row per
`alt_id:` (alternate/secondary IDs mapped to the same term), so lookups succeed
whether an annotation cites the primary or a secondary GO ID. Obsolete terms are
kept (they still carry a name and can appear in older annotations) and flagged.

Output (TSV, self-documenting headers, tab-delimited):
    go_id_to_name.tsv
"""

import argparse
import sys
from pathlib import Path


def parse_obo( obo_path: Path ):
    """
    Parse go-basic.obo [Term] stanzas into rows. Returns a list of tuples:
        ( go_id, name, namespace, is_obsolete, is_primary )
    one for each primary id and each alt_id.
    """
    rows = []
    in_term = False
    primary_id = name = namespace = ""
    alt_ids = []
    is_obsolete = False

    def flush():
        # Emit the primary row + one row per alt_id (carrying the primary's name).
        if not primary_id:
            return
        rows.append( ( primary_id, name, namespace, is_obsolete, True ) )
        for alt_id in alt_ids:
            rows.append( ( alt_id, name, namespace, is_obsolete, False ) )

    with open( obo_path, 'r' ) as input_obo:
        for line in input_obo:
            line = line.rstrip( '\n' )
            if line == "[Term]":
                if in_term:
                    flush()
                in_term = True
                primary_id = name = namespace = ""
                alt_ids = []
                is_obsolete = False
                continue
            if line.startswith( "[" ) and line.endswith( "]" ):
                # a non-Term stanza (e.g. [Typedef]) ends the current term
                if in_term:
                    flush()
                in_term = False
                continue
            if not in_term:
                continue
            if line.startswith( "id: " ):
                primary_id = line[ len( "id: " ): ].strip()
            elif line.startswith( "name: " ):
                name = line[ len( "name: " ): ].strip()
            elif line.startswith( "namespace: " ):
                namespace = line[ len( "namespace: " ): ].strip()
            elif line.startswith( "alt_id: " ):
                alt_ids.append( line[ len( "alt_id: " ): ].strip() )
            elif line.startswith( "is_obsolete: " ):
                is_obsolete = line[ len( "is_obsolete: " ): ].strip().lower() == "true"
        if in_term:
            flush()

    return rows


def main():
    parser = argparse.ArgumentParser( description = "Parse go-basic.obo into a GO_ID -> name/namespace TSV" )
    parser.add_argument( '--obo', default = str( Path( __file__ ).parent / "go-basic.obo" ) )
    parser.add_argument( '--output', default = str( Path( __file__ ).parent / "go_id_to_name.tsv" ) )
    args = parser.parse_args()

    obo_path = Path( args.obo )
    if not obo_path.is_file():
        print( f"CRITICAL ERROR: go-basic.obo not found: {obo_path}", file = sys.stderr )
        print( "  Download it: curl -sL -o go-basic.obo https://purl.obolibrary.org/obo/go/go-basic.obo", file = sys.stderr )
        sys.exit( 1 )

    rows = parse_obo( obo_path )
    if not rows:
        print( f"CRITICAL ERROR: no [Term] stanzas parsed from {obo_path}", file = sys.stderr )
        sys.exit( 1 )

    header = [
        "GO_ID (Gene Ontology term identifier; includes alternate/secondary ids mapped to the same term)",
        "GO_Name (human readable Gene Ontology term name)",
        "GO_Namespace (Gene Ontology aspect: biological_process, molecular_function, or cellular_component)",
        "Is_Obsolete (True if the GO term is obsolete in this ontology release, else False)",
        "Is_Primary_ID (True if GO_ID is the primary term id, False if it is an alternate/secondary id)",
    ]

    output_path = Path( args.output )
    primary_count = 0
    with open( output_path, 'w' ) as output_file:
        output_file.write( '\t'.join( header ) + '\n' )
        for ( go_id, name, namespace, is_obsolete, is_primary ) in rows:
            if is_primary:
                primary_count += 1
            output = '\t'.join( [ go_id, name, namespace, str( is_obsolete ), str( is_primary ) ] ) + '\n'
            output_file.write( output )

    print( f"[generate_go_id_to_name] wrote {len( rows )} rows ({primary_count} primary GO terms + "
           f"{len( rows ) - primary_count} alternate ids) -> {output_path}" )


if __name__ == '__main__':
    main()
