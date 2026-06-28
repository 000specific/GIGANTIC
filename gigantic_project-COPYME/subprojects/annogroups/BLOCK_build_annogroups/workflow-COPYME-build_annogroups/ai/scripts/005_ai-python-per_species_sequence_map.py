#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27 | Purpose: Per-species sequence map — pivot annogroup membership into a wide table of member sequence identifiers per species, carrying annogroup ids + annotation definitions
# Human: Eric Edsinger

"""
Script 005 — Per-species sequence map (one source).

A companion to the species-tree deconvolution (Script 004): the SAME wide
per-species layout, but each cell holds the member SEQUENCE IDENTIFIERS instead
of a count. Rows are annogroups (with their annotation definitions); columns are
species (Genus_species); each cell is the comma-delimited sequence identifiers of
that annogroup whose species is that column (empty when the annogroup has no
member sequence in that species).

This links annogroup_id + Annotation_Definitions directly to the member sequence
identifiers, organized per species — the wide form of the long
2_ai-<source>-annogroup_membership.tsv. The `absent` annogroup (sequences with no
feature, hence no annotation definition) is EXCLUDED; only the feature,
combination, and architecture annogroups appear.

Inputs (per source, already on disk):
  - 2-output/<source>/2_ai-<source>-annogroup_map.tsv          (Annogroup_ID, type, definitions)
  - 2-output/<source>/2_ai-<source>-annogroup_membership.tsv   (sequence -> species -> annogroup)

Output (5-output/<source>/):
  5_ai-<source>-annogroup_sequences_per_species.tsv
    = Annogroup_ID, Annogroup_Type, Annotation_Definitions, then one column per
      species (Genus_species) holding the member sequence identifiers.

Fail-fast (§36): exits 1 if inputs are missing or the map is empty.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_annogroups as U


def main():
    parser = argparse.ArgumentParser( description = "Per-species sequence map — annogroup x species -> member sequence identifiers" )
    parser.add_argument( '--source', required = True )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    source = args.source
    output_base = Path( args.output_dir )

    map_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_map.tsv"
    membership_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_membership.tsv"
    for required in ( map_path, membership_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required file not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    # ---- Pass 1: annogroup order + type + definitions (from the map) -----------------
    # Annogroup_ID (...)\tSource (...)\tAnnogroup_Type (...)\tDefining_Features (...)\tAnnotation_Definitions (...)\tSequence_Count (...)\tSpecies_Count (...)\tSpecies_List (...)
    annogroup_order = []
    included_annogroups = set()
    annogroups___type = {}
    annogroups___definition = {}
    annogroups___extra_cells = {}   # source-specific extra map columns (e.g. GO aspect split), carried forward
    with open( map_path, 'r' ) as input_map:
        map_header_line = input_map.readline()
        header_ids___indices = U.build_header_index( map_header_line )
        # Carry forward any source-specific columns the map builder inserted between
        # Annotation_Definitions and Sequence_Count (e.g. go's GO-aspect split columns).
        extra_headers, extra_indices = U.carry_forward_map_columns( map_header_line )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_type = parts[ index_type ] if index_type < len( parts ) else ""
            # The 'absent' annogroup (sequences with no feature) has no annotation
            # definition; it is excluded from this map (Eric, 2026-06-27).
            if annogroup_type == "absent":
                continue
            annogroup_id = parts[ index_annogroup ]
            annogroup_order.append( annogroup_id )
            included_annogroups.add( annogroup_id )
            annogroups___type[ annogroup_id ] = annogroup_type
            annogroups___definition[ annogroup_id ] = parts[ index_definitions ] if index_definitions < len( parts ) else ""
            annogroups___extra_cells[ annogroup_id ] = [ parts[ i ] if i < len( parts ) else "" for i in extra_indices ]

    # ---- Pass 2: annogroup -> species -> [sequence identifiers] (from membership) -----
    # Sequence_Identifier (...)\tGenus_Species (...)\tAnnogroup_ID (...)\tAnnogroup_Type (...)\t...
    annogroups___species___sequences = defaultdict( lambda: defaultdict( list ) )
    all_species = set()
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
            if annogroup_id not in included_annogroups:
                continue
            genus_species = parts[ index_genus_species ]
            annogroups___species___sequences[ annogroup_id ][ genus_species ].append( parts[ index_sequence ] )
            all_species.add( genus_species )

    species_columns = sorted( all_species )

    output_dir = output_base / "5-output" / source
    output_dir.mkdir( parents = True, exist_ok = True )
    output_path = output_dir / f"5_ai-{source}-annogroup_sequences_per_species.tsv"

    header = [
        "Annogroup_ID (annogroup identifier from the annogroups subproject)",
        "Annogroup_Type (feature or combination or architecture or absent)",
        "Annotation_Definitions (semicolon delimited definition ==accession pairs for this annogroup)",
    ] + extra_headers + [ f"{species} (comma delimited member sequence identifiers of this annogroup whose species is {species})"
          for species in species_columns ]

    with open( output_path, 'w' ) as output_file:
        output_file.write( '\t'.join( header ) + '\n' )
        for annogroup_id in annogroup_order:
            species___sequences = annogroups___species___sequences.get( annogroup_id, {} )
            cells = [ U.DELIM.join( sorted( species___sequences.get( species, [] ) ) ) for species in species_columns ]
            output_file.write( '\t'.join( [ annogroup_id, annogroups___type[ annogroup_id ], annogroups___definition[ annogroup_id ] ]
                                          + annogroups___extra_cells.get( annogroup_id, [] ) + cells ) + '\n' )

    print( f"[005 {source}] wrote {len( annogroup_order )} annogroups x {len( species_columns )} species "
           f"sequence map -> {output_path.name}" )

    if not annogroup_order:
        print( "CRITICAL ERROR: zero annogroups read from the map", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
