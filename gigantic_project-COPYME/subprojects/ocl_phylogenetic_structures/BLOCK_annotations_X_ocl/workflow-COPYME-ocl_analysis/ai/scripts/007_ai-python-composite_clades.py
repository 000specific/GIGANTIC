# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Composite Clades for the OCL run — classify each annogroup by four algorithms (exact, absent, core_urclade, core_early_clade) over its member species; structure-independent, computed ONCE
# Human: Eric Edsinger

"""
OCL Script 007 — Composite Clades (once per run, structure-independent).

The annogroups composite-clades analysis, brought into OCL. An annogroup's member
species and the building-block clade species sets do NOT vary across the 105
species-tree structures (Rule 6), so this is computed ONE time for the whole run
(not per structure). Each manifest row names an ALGORITHM that tests an annogroup's
member species (see the composite_clades block + manifest header):
  - exact            : members from EXACTLY the listed component groups
  - absent           : members ABSENT from ALL listed clades
  - core_urclade     : members in >=1 outgroup of the target AND >=1 ingroup (Ur core)
  - core_early_clade : members in >=2 ingroups (Early window = the ambiguous nodes)

OCL works at the species level (it imports the annogroup map, not the per-sequence
membership), so the detail tables list member SPECIES per component clade (the
annogroups subproject's own composite detail lists member sequences). The 'absent'
annogroup type is excluded (consistent with OCL).

Inputs:
  - annogroup map (annogroups output_to_input): Annogroup_ID, Annogroup_Type,
    Annotation_Definitions, Species_List
  - clade->species mapping + the composite_clades config block + the manifest

Outputs (OUTPUT_pipeline/composite_clades/):
  - 7_ai-<source>-composite_clades-per_annogroup.tsv     (one column per algorithm)
  - 7_ai-<source>-composite_clades-summary_counts.tsv    (one row per manifest composite clade)
  - composite_clades_detail_tables/7_ai-<source>-composite_clades-<cc_id>.tsv
        (rows = matching annogroups; columns = member species per relevant clade)

Fail-fast (§36): exits 1 if inputs / config / manifest are missing or invalid.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_run_summary as U


def species_in_detail_column( genus_species, kind, species_set ):
    """True if a species belongs in a detail-table column ('in' = in the clade; 'out' = outside it)."""
    return ( genus_species in species_set ) if kind == "in" else ( genus_species not in species_set )


def detail_column_header( label, kind ):
    if kind == "in":
        return f"{label} (comma delimited member species of this annogroup in {label})"
    return f"{label} (comma delimited member species of this annogroup outside the focal clade; the {label} members)"


def main():
    parser = argparse.ArgumentParser( description = "OCL Composite Clades (one source, once, structure-independent)" )
    parser.add_argument( '--source', required = True, help = 'Annotation source (e.g. pfam, go, panther)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config_path = Path( args.config )
    with open( config_path, 'r' ) as input_config:
        config = yaml.safe_load( input_config )
    config_directory = config_path.parent

    species_set = config[ 'species_set_name' ]
    source = args.source
    annogroup_types = set( config.get( 'annogroup_types', [ 'feature', 'combination', 'architecture' ] ) )

    annogroup_map_file = ( config_directory / config[ 'inputs' ][ 'annogroups_dir' ]
                           / species_set / source / f'2_ai-{source}-annogroup_map.tsv' )
    mappings_path = config_directory / config[ 'inputs' ][ 'clade_species_mappings' ]
    manifest_path = config_directory / config[ 'inputs' ][ 'composite_clades_manifest' ]
    for required in ( annogroup_map_file, mappings_path, manifest_path ):
        if not required.exists():
            print( f"CRITICAL ERROR: required input not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    composites = U.load_composite_clades( config, mappings_path )
    manifest = U.load_composite_clades_manifest( manifest_path, composites )
    manifest_exact_ids = { entry[ "cc_id" ] for entry in manifest if entry[ "algorithm" ] == "exact" }
    non_exact_entries = [ entry for entry in manifest if entry[ "algorithm" ] != "exact" ]

    # ---- Pass 1: classify every annogroup from its member species ---------------------
    # Annogroup_ID (...)	Source (...)	Annogroup_Type (...)	Defining_Features (...)	Annotation_Definitions (...)	Sequence_Count (...)	Species_Count (...)	Species_List (...)
    annogroup_order = []
    annogroups___type = {}
    annogroups___definition = {}
    annogroups___species = {}
    annogroups___matches = defaultdict( lambda: defaultdict( list ) )
    cc_id___annogroups = defaultdict( list )

    with open( annogroup_map_file, 'r' ) as input_map:
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
            if parts[ index_type ] not in annogroup_types:
                continue
            annogroup_id = parts[ index_annogroup ]
            member_species = { s for s in ( parts[ index_species_list ] if index_species_list < len( parts ) else "" ).split( ',' ) if s }

            annogroup_order.append( annogroup_id )
            annogroups___type[ annogroup_id ] = parts[ index_type ]
            annogroups___definition[ annogroup_id ] = parts[ index_definitions ] if index_definitions < len( parts ) else ""
            annogroups___species[ annogroup_id ] = member_species

            own_exact_id = U.composite_clade_id( U.exact_components_of_species( member_species, composites ) )
            if own_exact_id in manifest_exact_ids:
                annogroups___matches[ annogroup_id ][ "exact" ].append( own_exact_id )
                cc_id___annogroups[ own_exact_id ].append( annogroup_id )
            for entry in non_exact_entries:
                if U.annogroup_matches_composite_clade( entry, member_species, composites ):
                    annogroups___matches[ annogroup_id ][ entry[ "algorithm" ] ].append( entry[ "cc_id" ] )
                    cc_id___annogroups[ entry[ "cc_id" ] ].append( annogroup_id )

    if not annogroup_order:
        print( f"CRITICAL ERROR: no annogroups read from {annogroup_map_file.name}", file = sys.stderr )
        sys.exit( 1 )

    output_directory = Path( args.output_dir ) / "composite_clades"
    output_directory.mkdir( parents = True, exist_ok = True )

    # ---- Deliverable 1: per-annogroup table (one column per algorithm) ----------------
    per_annogroup_path = output_directory / f"7_ai-{source}-composite_clades-per_annogroup.tsv"
    per_annogroup_header = [
        "Annogroup_ID (canonical annogroup identifier)",
        "Annogroup_Type (feature or combination or architecture)",
        "Annotation_Definitions (semicolon delimited definition ==accession pairs)",
        "Composite_Clade-exact (the annogroup's exact composite clade cc_<components>-exact when curated, else None; one per annogroup)",
        "Composite_Clades-absent (comma delimited absent composite clades this annogroup matches i.e. members absent from all those clades, else None)",
        "Composite_Clades-core_urclade (comma delimited core_urclade composite clades matched i.e. members in an outgroup of the target and in an ingroup, else None)",
        "Composite_Clades-core_early_clade (comma delimited core_early_clade composite clades matched i.e. members in two or more early ingroup branches, else None)",
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
                [ annogroup_id, annogroups___type[ annogroup_id ], annogroups___definition[ annogroup_id ] ] + cells ) + '\n' )

    # ---- Deliverable 2: summary counts -----------------------------------------------
    summary_path = output_directory / f"7_ai-{source}-composite_clades-summary_counts.tsv"
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

    # ---- Deliverable 3: one detail table per manifest composite clade -----------------
    detail_dir = output_directory / "composite_clades_detail_tables"
    detail_dir.mkdir( parents = True, exist_ok = True )
    detail_tables_written = 0
    for entry in manifest:
        cc_id = entry[ "cc_id" ]
        detail_columns = entry[ "detail_columns" ]
        annogroups = sorted( cc_id___annogroups.get( cc_id, [] ) )
        detail_path = detail_dir / f"7_ai-{source}-composite_clades-{cc_id}.tsv"
        detail_header = [
            "Annogroup_ID (annogroup identifier; matches the composite clade)",
            "Annotation_Definitions (semicolon delimited definition ==accession pairs)",
        ] + [ detail_column_header( label, kind ) for ( label, kind, species_set ) in detail_columns ]
        with open( detail_path, 'w' ) as output_detail:
            output_detail.write( '\t'.join( detail_header ) + '\n' )
            for annogroup_id in annogroups:
                member_species = annogroups___species[ annogroup_id ]
                column_cells = []
                for ( label, kind, species_set ) in detail_columns:
                    species = [ genus_species for genus_species in member_species
                                if species_in_detail_column( genus_species, kind, species_set ) ]
                    column_cells.append( U.DELIM.join( sorted( species ) ) )
                output_detail.write( '\t'.join( [ annogroup_id, annogroups___definition[ annogroup_id ] ] + column_cells ) + '\n' )
        detail_tables_written += 1

    matched_total = len( { annogroup_id for annogroups in cc_id___annogroups.values() for annogroup_id in annogroups } )
    print( f"[007 composite_clades] {len( annogroup_order )} annogroups classified; {matched_total} in >=1 curated composite clade; "
           f"per-annogroup + summary ({len( manifest )} composite clades) + {detail_tables_written} detail tables" )


if __name__ == '__main__':
    main()
