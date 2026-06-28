#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 18 | Purpose: Build the four canonical annogroup types for one source (feature/combination/architecture/absent) from its parsed features
# Human: Eric Edsinger

"""
Script 002 — Build annogroups for one source.

Loads the source's parser plugin (parsers/<source>.py), gets the normalized
per-sequence feature list, and builds the four canonical annogroup types. The
construction is identical for every source; only the parser is source-specific.

Canonical types (gigantic_conventions — annogroup_* are canonical terms):
  feature       annogroup_<S>_<accession>          sequences sharing one feature
                (multi-membership; natural-accession ID, no map)
  combination   annogroup_<S>_combination<NNNNN>   sequences sharing the same
                unordered DISTINCT set of features (alphabetical canonical key)
  architecture  annogroup_<S>_architecture<NNNNN>  sequences sharing the same
                ordered arrangement of POSITIONAL features (N→C by start,stop;
                grouped on the coord-free accession pattern; each sequence's
                coordinate-tagged architecture is recorded on its membership row)
  absent        annogroup_<S>_absent               sequences (in the proteome
                universe) with NO feature from this source

Counter IDs (combination / architecture) are assigned deterministically (sort
the canonical keys, then number) so the same input always yields the same IDs.

Outputs (OUTPUT_pipeline/2-output/<source>/):
  2_ai-<S>-annogroup_map.tsv          one row per annogroup (all types)
  2_ai-<S>-annogroup_membership.tsv   one row per (sequence, annogroup)

Fail-fast: exits 1 if the parser, universe, or features are missing/empty.
"""

import argparse
import importlib
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_annogroups as U


def load_universe( universe_path: Path ) -> dict:
    """sequence_identifier -> genus_species, for every sequence in the species set."""
    sequences___genus_species = {}
    with open( universe_path, 'r' ) as input_universe:
        header_ids___indices = U.build_header_index( input_universe.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_genus_species = header_ids___indices[ "Genus_Species" ]
        for line in input_universe:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequences___genus_species[ parts[ index_sequence ] ] = parts[ index_genus_species ]
    return sequences___genus_species


def main():
    parser = argparse.ArgumentParser( description = "Build the four canonical annogroup types for one source" )
    parser.add_argument( '--source', required = True )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    source = args.source
    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    # ---- load the source parser plugin + parse its features -----------------
    try:
        parser_module = importlib.import_module( f"parsers.{source}" )
    except ModuleNotFoundError:
        print( f"CRITICAL ERROR: no parser plugin parsers/{source}.py", file = sys.stderr )
        sys.exit( 1 )

    proteins___features = parser_module.parse_source_features( workflow_root, config )
    if not proteins___features:
        print( f"CRITICAL ERROR: parser for '{source}' returned no features", file = sys.stderr )
        sys.exit( 1 )
    print( f"[002 {source}] parsed features for {len( proteins___features )} sequences" )

    # Optional half of the parser contract: per-accession definitions. A source
    # that exposes parse_source_definitions lets us attach Annotation_Definitions
    # to the map (canonical 'definition ==accession' format). Sources without
    # descriptions omit it and the definitions column renders empty.
    parse_definitions = getattr( parser_module, "parse_source_definitions", None )
    accessions___definitions = parse_definitions( workflow_root, config ) if parse_definitions else {}
    print( f"[002 {source}] loaded definitions for {len( accessions___definitions )} accessions" )

    # Optional: per-category (aspect) split columns. A source that declares
    # CATEGORIES + parse_source_categories (e.g. go's three GO aspects) gets two
    # extra map columns per category (<label>_Identifiers, <label>_Definitions),
    # inserted after Annotation_Definitions. Other sources are unaffected.
    category_specs = getattr( parser_module, "CATEGORIES", None )
    parse_categories = getattr( parser_module, "parse_source_categories", None )
    accessions___categories = parse_categories( workflow_root, config ) if ( category_specs and parse_categories ) else {}
    aspect_enabled = bool( category_specs and accessions___categories )
    if aspect_enabled:
        print( f"[002 {source}] category split enabled: "
               f"{', '.join( label for ( category_key, label ) in category_specs )} "
               f"({len( accessions___categories )} accession categories)" )

    def aspect_cells( accession_list ):
        # The 2-per-category split cells for one annogroup row (empty list when the
        # source declares no categories, so the row shape is unchanged).
        return U.category_aspect_values( accession_list, accessions___definitions,
                                         accessions___categories, category_specs ) if aspect_enabled else []

    # ---- load the proteome universe (for absent + species labels) -----------
    universe_path = Path( args.output_dir ) / "1-output" / "1_ai-proteome_universe.tsv"
    if not universe_path.is_file():
        print( f"CRITICAL ERROR: proteome universe not found: {universe_path}", file = sys.stderr )
        print( "  Script 001 (resolve_sources_and_universe) must run before this script.", file = sys.stderr )
        sys.exit( 1 )
    sequences___genus_species = load_universe( universe_path )
    print( f"[002 {source}] universe: {len( sequences___genus_species )} sequences" )

    # ---- drop orphan annotations not in the proteome universe ---------------
    # An annotated sequence whose identifier is NOT in the proteome universe
    # cannot be tied to a real proteome sequence, so it cannot become a valid
    # annogroup member. The known cause (2026-06) is EvidentialGene multi-locus
    # protein identifiers (>200 chars) that were TRUNCATED upstream in the
    # InterProScan pipeline, so the annotation identifier no longer matches the
    # full proteome header (e.g. '...Sphaeroforma_arcti' vs '...arctica').
    #
    # USER DECISION (Eric Edsinger, 2026-06-18): drop these orphan annotations.
    # This is auditable, NOT silent — the dropped identifiers are written to
    # 2_ai-<source>-dropped_orphan_sequences.tsv and warned in the log. See the
    # subproject warning note: ai/ai_FYIs/WARNING-truncated_orphan_annotations.md
    #
    # Known side effect (accepted): the corresponding FULL-id proteome sequence
    # remains in the universe and, having no surviving annotation under its real
    # identifier, is counted in annogroup_<source>_absent — a tiny false-negative
    # (7 of ~1.38M for pfam, one ichthyosporean species).
    orphan_sequences = sorted( protein for protein in proteins___features if protein not in sequences___genus_species )
    if orphan_sequences:
        print( f"[002 {source}] WARNING: dropping {len( orphan_sequences )} annotated sequence(s) "
               f"whose identifier is not in the proteome universe (truncated/orphan IDs). "
               f"See dropped_orphan_sequences.tsv + WARNING-truncated_orphan_annotations.md",
               file = sys.stderr )
        for protein in orphan_sequences:
            del proteins___features[ protein ]

    # ========================================================================
    # Build the four types. Each annogroup -> set of member sequences.
    # ========================================================================
    # feature: accession -> member sequences (multi-membership)
    accessions___members = {}
    # combination: canonical distinct-set key -> member sequences
    combination_keys___members = {}
    # architecture: coord-free ordered-accession key -> member sequences
    architecture_keys___members = {}
    # per-sequence coordinate-tagged architecture string (membership detail)
    sequences___architecture_member_string = {}

    for protein, features in proteins___features.items():
        # feature
        for accession in { feature.accession for feature in features }:
            accessions___members.setdefault( accession, set() ).add( protein )

        # combination — distinct set, alphabetical canonical key
        combination_key = tuple( sorted( { feature.accession for feature in features } ) )
        combination_keys___members.setdefault( combination_key, set() ).add( protein )

        # architecture — positional features only, N→C by (start, stop)
        positional_features = sorted(
            ( feature for feature in features if feature.is_positional ),
            key = lambda feature: ( feature.start, feature.stop )
        )
        if positional_features:
            architecture_key = tuple( feature.accession for feature in positional_features )
            architecture_keys___members.setdefault( architecture_key, set() ).add( protein )
            sequences___architecture_member_string[ protein ] = U.architecture_member_string( positional_features )

    # absent: universe minus sequences with any feature from this source
    annotated_sequences = set( proteins___features.keys() )
    absent_sequences = [ seq for seq in sequences___genus_species if seq not in annotated_sequences ]

    print( f"[002 {source}] feature={len( accessions___members )}  "
           f"combination={len( combination_keys___members )}  "
           f"architecture={len( architecture_keys___members )}  "
           f"absent={len( absent_sequences )}" )

    # ---- deterministic counter IDs ------------------------------------------
    combination_keys___ids = {
        key: U.annogroup_counter_id( source, "combination", index )
        for index, key in enumerate( sorted( combination_keys___members ), start = 1 )
    }
    architecture_keys___ids = {
        key: U.annogroup_counter_id( source, "architecture", index )
        for index, key in enumerate( sorted( architecture_keys___members ), start = 1 )
    }

    # ---- write outputs ------------------------------------------------------
    output_dir = Path( args.output_dir ) / "2-output" / source
    output_dir.mkdir( parents = True, exist_ok = True )
    output_map_path = output_dir / f"2_ai-{source}-annogroup_map.tsv"
    output_membership_path = output_dir / f"2_ai-{source}-annogroup_membership.tsv"

    # audit trail for the dropped orphan annotations (always written, even if empty)
    output_dropped_path = output_dir / f"2_ai-{source}-dropped_orphan_sequences.tsv"
    with open( output_dropped_path, 'w' ) as output_dropped:
        output_dropped.write( "Dropped_Annotation_Identifier (annotated sequence identifier from the source that is NOT in the proteome universe, dropped as a truncated or orphan identifier; see WARNING-truncated_orphan_annotations.md)\n" )
        for protein in orphan_sequences:
            output_dropped.write( protein + '\n' )
    print( f"[002 {source}] wrote {len( orphan_sequences )} dropped orphan identifier(s) -> {output_dropped_path}" )

    def species_count( members ) -> int:
        return len( { sequences___genus_species.get( member, '' ) for member in members } )

    def species_list( members ) -> str:
        # sorted comma-delimited Genus_species — the structure-independent species
        # set downstream OCL maps onto each species-tree structure.
        return U.DELIM.join( sorted( { sequences___genus_species.get( member, '' ) for member in members } ) )

    map_header = (
        [
            "Annogroup_ID (canonical annogroup identifier)",
            "Source (annotation source database)",
            "Annogroup_Type (one of feature, combination, architecture, absent)",
            "Defining_Features (the feature(s) that define this annogroup: the accession for feature, the alphabetical distinct set for combination, the N to C ordered accession pattern for architecture, empty for absent; comma delimited)",
            "Annotation_Definitions (semicolon delimited definition ==accession pairs over the unique defining accessions, where definition is the source signature description e.g. Protein kinase domain ==PF00069; empty for absent or when the source carries no descriptions)",
        ]
        + ( U.category_aspect_headers( category_specs ) if aspect_enabled else [] )
        + [
            "Sequence_Count (number of member sequences)",
            "Species_Count (number of distinct Genus_species among member sequences)",
            "Species_List (comma delimited sorted Genus_species of all member sequences; the structure-independent species set downstream OCL maps onto each species tree structure)",
        ]
    )
    membership_header = [
        "Sequence_Identifier (full GIGANTIC protein identifier)",
        "Genus_Species (Genus_species of the sequence)",
        "Annogroup_ID (canonical annogroup identifier the sequence belongs to)",
        "Annogroup_Type (one of feature, combination, architecture, absent)",
        "Member_Architecture_Coordinates (for architecture rows: this sequence's coordinate-tagged ordered features accession_startN_stopM comma delimited; empty otherwise)",
    ]

    map_rows = 0
    membership_rows = 0
    with open( output_map_path, 'w' ) as output_map, \
         open( output_membership_path, 'w' ) as output_membership:
        output_map.write( '\t'.join( map_header ) + '\n' )
        output_membership.write( '\t'.join( membership_header ) + '\n' )

        # feature
        for accession in sorted( accessions___members ):
            members = accessions___members[ accession ]
            annogroup_id = U.annogroup_feature_id( source, accession )
            definitions = U.format_annotation_definitions( [ accession ], accessions___definitions )
            output_map.write( '\t'.join( [ annogroup_id, source, "feature", accession, definitions ]
                                         + aspect_cells( [ accession ] )
                                         + [ str( len( members ) ), str( species_count( members ) ), species_list( members ) ] ) + '\n' )
            map_rows += 1
            for member in sorted( members ):
                output_membership.write( '\t'.join( [ member, sequences___genus_species.get( member, '' ),
                                                      annogroup_id, "feature", "" ] ) + '\n' )
                membership_rows += 1

        # combination
        for key in sorted( combination_keys___members ):
            members = combination_keys___members[ key ]
            annogroup_id = combination_keys___ids[ key ]
            definitions = U.format_annotation_definitions( list( key ), accessions___definitions )
            output_map.write( '\t'.join( [ annogroup_id, source, "combination", U.DELIM.join( key ), definitions ]
                                         + aspect_cells( list( key ) )
                                         + [ str( len( members ) ), str( species_count( members ) ), species_list( members ) ] ) + '\n' )
            map_rows += 1
            for member in sorted( members ):
                output_membership.write( '\t'.join( [ member, sequences___genus_species.get( member, '' ),
                                                      annogroup_id, "combination", "" ] ) + '\n' )
                membership_rows += 1

        # architecture
        for key in sorted( architecture_keys___members ):
            members = architecture_keys___members[ key ]
            annogroup_id = architecture_keys___ids[ key ]
            definitions = U.format_annotation_definitions( list( key ), accessions___definitions )
            output_map.write( '\t'.join( [ annogroup_id, source, "architecture", U.DELIM.join( key ), definitions ]
                                         + aspect_cells( list( key ) )
                                         + [ str( len( members ) ), str( species_count( members ) ), species_list( members ) ] ) + '\n' )
            map_rows += 1
            for member in sorted( members ):
                output_membership.write( '\t'.join( [ member, sequences___genus_species.get( member, '' ),
                                                      annogroup_id, "architecture",
                                                      sequences___architecture_member_string.get( member, '' ) ] ) + '\n' )
                membership_rows += 1

        # absent
        absent_id = U.annogroup_absent_id( source )
        output_map.write( '\t'.join( [ absent_id, source, "absent", "", "" ]
                                     + aspect_cells( [] )
                                     + [ str( len( absent_sequences ) ), str( species_count( absent_sequences ) ),
                                         species_list( absent_sequences ) ] ) + '\n' )
        map_rows += 1
        for member in sorted( absent_sequences ):
            output_membership.write( '\t'.join( [ member, sequences___genus_species.get( member, '' ),
                                                  absent_id, "absent", "" ] ) + '\n' )
            membership_rows += 1

    print( f"[002 {source}] wrote {map_rows} annogroups -> {output_map_path}" )
    print( f"[002 {source}] wrote {membership_rows} membership rows -> {output_membership_path}" )


if __name__ == '__main__':
    main()
