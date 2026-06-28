#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27 | Purpose: Composite Clades — classify each annogroup by four algorithms (exact, absent, core_urclade, core_early_clade) over species-tree clade groupings, with a per-annogroup table (one column per algorithm), curated summary counts, and per-composite-clade detail tables
# Human: Eric Edsinger

"""
Script 006 — Composite Clades (one source).

A "composite clade" is a focused question about where an annogroup's member species
fall on the species tree. The building-block GROUPS + the scope are defined in the
`composite_clades` block of START_HERE-user_config.yaml (default: the five metazoan
phyla within Metazoa). The composite clades to REPORT are curated in
INPUT_user/composite_clades_manifest.tsv, where each row picks one ALGORITHM:

  - exact            : members come from EXACTLY the listed component groups
                       (one-per-annogroup; auto-named cc_<components>-exact)
  - absent           : members are ABSENT from ALL listed clades
  - core_urclade     : members in >=1 OUTGROUP of the target AND >=1 listed ingroup
                       -> the target's Ur (last-common-ancestor) core
  - core_early_clade : members in >=2 listed ingroups, the ingroups being the
                       ambiguous (unresolved) nodes that define the target's "Early"
                       window (its early descendant branches)

`Ur` = last common ancestor of a clade; `Early` = the early descendants of a clade.
`exact` partitions the annogroups (each maps to exactly one exact composite clade);
the other three are independent membership tests, so an annogroup may match several.

Inputs (per source, already on disk):
  - 2-output/<source>/2_ai-<source>-annogroup_map.tsv          (Annogroup_ID, type,
                                                                definitions, Species_List)
  - 2-output/<source>/2_ai-<source>-annogroup_membership.tsv   (per-sequence species)
  - clade_species_mappings + the composite_clades config block + the manifest

Outputs (6-output/<source>/):
  - 6_ai-<source>-composite_clades-per_annogroup.tsv
        every annogroup + one column per algorithm (its exact composite clade, and
        the comma lists of absent / core_urclade / core_early_clade composite clades
        it matches), else None
  - 6_ai-<source>-composite_clades-summary_counts.tsv
        one row per MANIFEST composite clade: cc_id, algorithm, definition, count
  - composite_clades_detail_tables/6_ai-<source>-composite_clades-<cc_id>.tsv
        one table per manifest composite clade: rows = its annogroups; columns =
        Annogroup_ID, definition, then one column per relevant clade holding that
        annogroup's member sequence identifiers there

Fail-fast (§36): exits 1 if inputs / config / manifest are missing or invalid.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_annogroups as U


def sequence_in_detail_column( genus_species: str, kind: str, species_set: set ) -> bool:
    """True if a sequence's species belongs in a detail-table column ('in' = species
    in the column's clade; 'out' = species outside it, e.g. the outside/outgroup column)."""
    return ( genus_species in species_set ) if kind == "in" else ( genus_species not in species_set )


def detail_column_header( label: str, kind: str ) -> str:
    """Self-documenting header for one detail-table clade column."""
    if kind == "in":
        return f"{label} (comma delimited member sequence identifiers of this annogroup whose species is in {label})"
    return f"{label} (comma delimited member sequence identifiers of this annogroup whose species falls outside the focal clade; the {label} members)"


def main():
    parser = argparse.ArgumentParser( description = "Composite Clades — per-annogroup classification (4 algorithms) + curated summary + detail tables" )
    parser.add_argument( '--source', required = True )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    source = args.source
    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    output_base = Path( args.output_dir )

    map_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_map.tsv"
    membership_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_membership.tsv"
    mappings_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "clade_species_mappings" ] )
    manifest_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "composite_clades_manifest" ] )
    for required in ( map_path, membership_path, mappings_path, manifest_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required file not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    composites = U.load_composite_clades( config, mappings_path )
    manifest = U.load_composite_clades_manifest( manifest_path, composites )

    # The exact algorithm is one-per-annogroup; the others are independent tests.
    manifest_exact_ids = { entry[ "cc_id" ] for entry in manifest if entry[ "algorithm" ] == "exact" }
    non_exact_entries = [ entry for entry in manifest if entry[ "algorithm" ] != "exact" ]
    algorithm_counts = defaultdict( int )
    for entry in manifest:
        algorithm_counts[ entry[ "algorithm" ] ] += 1
    print( f"[006 {source}] composite clades — building blocks {', '.join( composites[ 'names' ] )} + {composites[ 'outside_label' ]}; "
           f"manifest curates {len( manifest )} composite clades ("
           + ', '.join( f"{algorithm} {algorithm_counts[ algorithm ]}" for algorithm in U.COMPOSITE_CLADE_ALGORITHMS if algorithm_counts[ algorithm ] ) + ")" )

    # ---- Pass 1: classify every annogroup from its member species --------------------
    # Annogroup_ID (...)\tSource (...)\tAnnogroup_Type (...)\tDefining_Features (...)\tAnnotation_Definitions (...)\tSequence_Count (...)\tSpecies_Count (...)\tSpecies_List (...)
    annogroup_order = []
    annogroups___type = {}
    annogroups___definition = {}
    annogroups___extra_cells = {}   # source-specific extra map columns (e.g. GO aspect split), carried forward
    # per-annogroup matches, keyed by algorithm -> list of cc_ids (exact yields <=1)
    annogroups___matches = defaultdict( lambda: defaultdict( list ) )
    # per-composite-clade -> the annogroups that match it (for summary + detail)
    cc_id___annogroups = defaultdict( list )

    with open( map_path, 'r' ) as input_map:
        map_header_line = input_map.readline()
        header_ids___indices = U.build_header_index( map_header_line )
        # Carry forward any source-specific columns the map builder inserted between
        # Annotation_Definitions and Sequence_Count (e.g. go's GO-aspect split columns).
        extra_headers, extra_indices = U.carry_forward_map_columns( map_header_line )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        index_species_list = header_ids___indices[ "Species_List" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ index_annogroup ]
            member_species = { s for s in ( parts[ index_species_list ] if index_species_list < len( parts ) else "" ).split( ',' ) if s }

            annogroup_order.append( annogroup_id )
            annogroups___type[ annogroup_id ] = parts[ index_type ] if index_type < len( parts ) else ""
            annogroups___definition[ annogroup_id ] = parts[ index_definitions ] if index_definitions < len( parts ) else ""
            annogroups___extra_cells[ annogroup_id ] = [ parts[ i ] if i < len( parts ) else "" for i in extra_indices ]

            # exact: the annogroup's own exact composite clade (shown only if curated)
            own_exact_id = U.composite_clade_id( U.exact_components_of_species( member_species, composites ) )
            if own_exact_id in manifest_exact_ids:
                annogroups___matches[ annogroup_id ][ "exact" ].append( own_exact_id )
                cc_id___annogroups[ own_exact_id ].append( annogroup_id )

            # absent / core_urclade / core_early_clade: independent membership tests
            for entry in non_exact_entries:
                if U.annogroup_matches_composite_clade( entry, member_species, composites ):
                    annogroups___matches[ annogroup_id ][ entry[ "algorithm" ] ].append( entry[ "cc_id" ] )
                    cc_id___annogroups[ entry[ "cc_id" ] ].append( annogroup_id )

    output_dir = output_base / "6-output" / source
    output_dir.mkdir( parents = True, exist_ok = True )

    # ---- Deliverable 1: per-annogroup table (one column per algorithm) ---------------
    per_annogroup_path = output_dir / f"6_ai-{source}-composite_clades-per_annogroup.tsv"
    per_annogroup_header = [
        "Annogroup_ID (annogroup identifier from the annogroups subproject)",
        "Annogroup_Type (feature or combination or architecture or absent)",
        "Annotation_Definitions (semicolon delimited definition ==accession pairs for this annogroup)",
    ] + extra_headers + [
        "Composite_Clade-exact (the annogroup's exact composite clade cc_<components>-exact when that composite clade is curated in the manifest, else None; one per annogroup)",
        "Composite_Clades-absent (comma delimited absent composite clades this annogroup matches i.e. its members are absent from all the clades of that composite clade, else None)",
        "Composite_Clades-core_urclade (comma delimited core_urclade composite clades this annogroup matches i.e. members in an outgroup of the target and in an ingroup, else None)",
        "Composite_Clades-core_early_clade (comma delimited core_early_clade composite clades this annogroup matches i.e. members in two or more of the early ingroup branches, else None)",
    ]
    with open( per_annogroup_path, 'w' ) as output_per_annogroup:
        output_per_annogroup.write( '\t'.join( per_annogroup_header ) + '\n' )
        for annogroup_id in annogroup_order:
            matches = annogroups___matches.get( annogroup_id, {} )
            cells = []
            for algorithm in U.COMPOSITE_CLADE_ALGORITHMS:
                matched = matches.get( algorithm, [] )
                cells.append( U.DELIM.join( matched ) if matched else "None" )
            output_per_annogroup.write( '\t'.join(
                [ annogroup_id, annogroups___type[ annogroup_id ], annogroups___definition[ annogroup_id ] ]
                + annogroups___extra_cells.get( annogroup_id, [] ) + cells ) + '\n' )

    # ---- Deliverable 2: Composite Clade Annogroup Summary Counts ---------------------
    summary_path = output_dir / f"6_ai-{source}-composite_clades-summary_counts.tsv"
    summary_header = [
        "Composite_Clade (composite clade identifier cc_<name or components>-<algorithm>)",
        "Algorithm (exact, absent, core_urclade, or core_early_clade)",
        "Definition (the components for exact, the absent-from clades for absent, or the target and ingroups for the core algorithms)",
        "Annogroup_Count (count of annogroups that match this composite clade)",
    ]
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( '\t'.join( summary_header ) + '\n' )
        for entry in manifest:
            count = len( cc_id___annogroups.get( entry[ "cc_id" ], [] ) )
            output_summary.write( f"{entry[ 'cc_id' ]}\t{entry[ 'algorithm' ]}\t{entry[ 'definition' ]}\t{count}\n" )

    # ---- Pass 2: member sequence identifiers per matching annogroup (for detail) -----
    matching_annogroups = { annogroup_id for annogroups in cc_id___annogroups.values() for annogroup_id in annogroups }
    annogroups___sequences = defaultdict( list )
    if matching_annogroups:
        # Sequence_Identifier (...)\tGenus_Species (...)\tAnnogroup_ID (...)\tAnnogroup_Type (...)\t...
        with open( membership_path, 'r' ) as input_membership:
            header_ids___indices = U.build_header_index( input_membership.readline() )
            index_sequence = header_ids___indices[ "Sequence_Identifier" ]
            index_genus_species = header_ids___indices[ "Genus_Species" ]
            index_membership_annogroup = header_ids___indices[ "Annogroup_ID" ]
            for line in input_membership:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                annogroup_id = parts[ index_membership_annogroup ]
                if annogroup_id in matching_annogroups:
                    annogroups___sequences[ annogroup_id ].append( ( parts[ index_sequence ], parts[ index_genus_species ] ) )

    # ---- Deliverable 3: one detail table per MANIFEST composite clade -----------------
    detail_dir = output_dir / "composite_clades_detail_tables"
    detail_dir.mkdir( parents = True, exist_ok = True )
    detail_tables_written = 0
    for entry in manifest:
        cc_id = entry[ "cc_id" ]
        detail_columns = entry[ "detail_columns" ]   # list of ( label, kind, species_set )
        annogroups = sorted( cc_id___annogroups.get( cc_id, [] ) )
        detail_path = detail_dir / f"6_ai-{source}-composite_clades-{cc_id}.tsv"
        detail_header = [
            "Annogroup_ID (annogroup identifier; this annogroup matches the composite clade)",
            "Annotation_Definitions (semicolon delimited definition ==accession pairs for this annogroup)",
        ] + extra_headers + [ detail_column_header( label, kind ) for ( label, kind, species_set ) in detail_columns ]
        with open( detail_path, 'w' ) as output_detail:
            output_detail.write( '\t'.join( detail_header ) + '\n' )
            for annogroup_id in annogroups:
                sequences = annogroups___sequences.get( annogroup_id, [] )
                column_cells = []
                for ( label, kind, species_set ) in detail_columns:
                    sequence_ids = [ sequence_id for ( sequence_id, genus_species ) in sequences
                                     if sequence_in_detail_column( genus_species, kind, species_set ) ]
                    column_cells.append( U.DELIM.join( sorted( sequence_ids ) ) )
                output_detail.write( '\t'.join( [ annogroup_id, annogroups___definition[ annogroup_id ] ]
                                                + annogroups___extra_cells.get( annogroup_id, [] ) + column_cells ) + '\n' )
        detail_tables_written += 1

    matched_total = len( matching_annogroups )
    print( f"[006 {source}] {len( annogroup_order )} annogroups classified; "
           f"{matched_total} fall in >=1 curated composite clade; "
           f"wrote per-annogroup + summary ({len( manifest )} composite clades) + {detail_tables_written} detail tables" )

    if not annogroup_order:
        print( "CRITICAL ERROR: zero annogroups read from the map", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
