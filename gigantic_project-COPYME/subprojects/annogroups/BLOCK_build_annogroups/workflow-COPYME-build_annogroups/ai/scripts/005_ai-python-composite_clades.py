#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27 | Purpose: Composite Clades (exact) — assign each annogroup its exact composite clade and report the curated manifest's composite clades with summary counts + per-composite-clade detail tables
# Human: Eric Edsinger

"""
Script 005 — Composite Clades, exact analysis (one source).

A "composite clade" is an EXACT combination of component clades (the groups defined
in the `composite_clades` block of START_HERE-user_config.yaml — e.g. Ctenophora,
Porifera, Placozoa, Cnidaria, Bilateria — plus the outside label NonMetazoa for
members outside the scope clade). An annogroup belongs to composite clade
cc_<components>-exact when its member sequences come from BOTH/ALL and ONLY those
components. Every annogroup therefore maps to exactly one composite clade.

Which composite clades are REPORTED is curated by the user manifest
(INPUT_user/composite_clades_manifest.tsv); composite clades not in the manifest
still get computed per annogroup but are shown as None.

Inputs (per source, already on disk):
  - 2-output/<source>/2_ai-<source>-annogroup_map.tsv          (Annogroup_ID, type,
                                                                definitions, Species_List)
  - 2-output/<source>/2_ai-<source>-annogroup_membership.tsv   (per-sequence species)
  - clade_species_mappings + the composite_clades config block + the manifest

Outputs (5-output/<source>/):
  - 5_ai-<source>-composite_clades_exact-per_annogroup.tsv
        every annogroup + its exact composite clade (the manifest's cc id, else None)
  - 5_ai-<source>-composite_clades_exact-summary_counts.tsv
        one row per MANIFEST composite clade + the count of annogroups in it
  - composite_clades_exact_detail_tables/5_ai-<source>-composite_clades_exact-<cc id>.tsv
        one table per manifest composite clade: rows = its annogroups; columns =
        Annogroup_ID, definition, then one column per constituent clade holding that
        annogroup's member sequence identifiers in that clade

Fail-fast (§36): exits 1 if inputs / config / manifest are missing or invalid.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_annogroups as U


def species_in_component( genus_species: str, component: str, composites: dict ) -> bool:
    """True if a species belongs to a composite-clade component (a config group, or
    the outside label = any species outside the scope clade)."""
    if component == composites[ "outside_label" ]:
        return genus_species not in composites[ "scope_species" ]
    return genus_species in composites[ "names___species" ][ component ]


def main():
    parser = argparse.ArgumentParser( description = "Composite Clades (exact) — per-annogroup composite clade + curated summary + detail tables" )
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
    manifest_cc_ids = { entry[ "cc_id" ] for entry in manifest }
    print( f"[005 {source}] composite clades — components {', '.join( composites[ 'names' ] )} + {composites[ 'outside_label' ]}; "
           f"manifest curates {len( manifest )} composite clades" )

    # ---- Pass 1: each annogroup's EXACT composite clade (from its member species) -----
    # Annogroup_ID (...)\tSource (...)\tAnnogroup_Type (...)\tDefining_Features (...)\tAnnotation_Definitions (...)\tSequence_Count (...)\tSpecies_Count (...)\tSpecies_List (...)
    annogroup_order = []
    annogroups___cc_id = {}
    annogroups___type = {}
    annogroups___definition = {}
    manifest_cc_id___annogroups = defaultdict( list )
    with open( map_path, 'r' ) as input_map:
        header_ids___indices = U.build_header_index( input_map.readline() )
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
            cc_id = U.composite_clade_id( U.exact_components_of_species( member_species, composites ) )

            annogroup_order.append( annogroup_id )
            annogroups___cc_id[ annogroup_id ] = cc_id
            annogroups___type[ annogroup_id ] = parts[ index_type ] if index_type < len( parts ) else ""
            annogroups___definition[ annogroup_id ] = parts[ index_definitions ] if index_definitions < len( parts ) else ""
            if cc_id in manifest_cc_ids:
                manifest_cc_id___annogroups[ cc_id ].append( annogroup_id )

    output_dir = output_base / "5-output" / source
    output_dir.mkdir( parents = True, exist_ok = True )

    # ---- Deliverable 1: per-annogroup table (one exact-composite-clade column) --------
    per_annogroup_path = output_dir / f"5_ai-{source}-composite_clades_exact-per_annogroup.tsv"
    per_annogroup_header = [
        "Annogroup_ID (annogroup identifier from the annogroups subproject)",
        "Annogroup_Type (feature or combination or architecture or absent)",
        "Annotation_Definitions (semicolon delimited definition ==accession pairs for this annogroup)",
        "Composite_Clade-exact (the annogroup's exact composite clade cc_<components>-exact when that composite clade is in the manifest, else None)",
    ]
    with open( per_annogroup_path, 'w' ) as output_per_annogroup:
        output_per_annogroup.write( '\t'.join( per_annogroup_header ) + '\n' )
        for annogroup_id in annogroup_order:
            cc_id = annogroups___cc_id[ annogroup_id ]
            shown = cc_id if cc_id in manifest_cc_ids else "None"
            output_per_annogroup.write( '\t'.join( [
                annogroup_id, annogroups___type[ annogroup_id ], annogroups___definition[ annogroup_id ], shown ] ) + '\n' )

    # ---- Deliverable 2: Composite Clade Annogroup Summary Counts ----------------------
    summary_path = output_dir / f"5_ai-{source}-composite_clades_exact-summary_counts.tsv"
    summary_header = [
        "Composite_Clade-exact (composite clade identifier cc_<components>-exact)",
        "Component_Clades (comma delimited constituent component clades of this composite clade, in config order)",
        "Annogroup_Count (count of annogroups whose member sequences come from exactly these components)",
    ]
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( '\t'.join( summary_header ) + '\n' )
        for entry in manifest:
            count = len( manifest_cc_id___annogroups.get( entry[ "cc_id" ], [] ) )
            output_summary.write( f"{entry[ 'cc_id' ]}\t{U.DELIM.join( entry[ 'components' ] )}\t{count}\n" )

    # ---- Pass 2: member sequence identifiers per matching annogroup (for detail) ------
    matching_annogroups = { annogroup_id for annogroups in manifest_cc_id___annogroups.values() for annogroup_id in annogroups }
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
    detail_dir = output_dir / "composite_clades_exact_detail_tables"
    detail_dir.mkdir( parents = True, exist_ok = True )
    detail_tables_written = 0
    for entry in manifest:
        cc_id = entry[ "cc_id" ]
        components = entry[ "components" ]
        annogroups = sorted( manifest_cc_id___annogroups.get( cc_id, [] ) )
        detail_path = detail_dir / f"5_ai-{source}-composite_clades_exact-{cc_id}.tsv"
        detail_header = [
            "Annogroup_ID (annogroup identifier; this annogroup's member sequences come from exactly these component clades)",
            "Annotation_Definitions (semicolon delimited definition ==accession pairs for this annogroup)",
        ] + [ f"{component} (comma delimited member sequence identifiers of this annogroup whose species belongs to {component})"
              for component in components ]
        with open( detail_path, 'w' ) as output_detail:
            output_detail.write( '\t'.join( detail_header ) + '\n' )
            for annogroup_id in annogroups:
                sequences = annogroups___sequences.get( annogroup_id, [] )
                component_cells = []
                for component in components:
                    sequence_ids = [ sequence_id for ( sequence_id, genus_species ) in sequences
                                     if species_in_component( genus_species, component, composites ) ]
                    component_cells.append( U.DELIM.join( sorted( sequence_ids ) ) )
                output_detail.write( '\t'.join( [ annogroup_id, annogroups___definition[ annogroup_id ] ] + component_cells ) + '\n' )
        detail_tables_written += 1

    print( f"[005 {source}] {len( annogroup_order )} annogroups classified; "
           f"{len( matching_annogroups )} fall in a manifest composite clade; "
           f"wrote per-annogroup + summary ({len( manifest )} composite clades) + {detail_tables_written} detail tables" )

    if not annogroup_order:
        print( "CRITICAL ERROR: zero annogroups read from the map", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
