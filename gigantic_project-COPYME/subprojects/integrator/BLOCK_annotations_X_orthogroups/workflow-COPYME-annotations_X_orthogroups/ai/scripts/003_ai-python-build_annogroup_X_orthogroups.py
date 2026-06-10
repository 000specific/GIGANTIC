#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Build Table 1 — annogroups joined to their orthogroups, kept when they touch a qualifying (non-bilaterian-metazoan) orthogroup
# Human: Eric Edsinger

"""
Script 003 — Table 1: annogroups X orthogroups.

For each pfam annogroup (subtypes from config; default single + combo), map its
member proteins to the orthogroups they belong to (shared full GIGANTIC IDs),
then KEEP the annogroup if at least one of its orthogroups is QUALIFYING — class
non_bilaterian_metazoan (zero bilaterians AND >=1 non-bilaterian metazoan).
Annogroups with no qualifying orthogroup are dropped (this includes annogroups
whose orthogroups are only bilaterian-containing and/or only non-metazoan-unicell).

For each kept annogroup ALL of its orthogroups are reported, grouped by the four
composition classes, with per-class counts and comma-delimited ID lists.

Inputs:
  - orthogroups file (headerless)        -> protein -> orthogroup map
  - 1-output composition table (Script 001) -> orthogroup -> composition class
  - annogroup membership files (single/combo) -> annogroup -> member Sequence_IDs
  - annogroup all-types OCL summary       -> annogroup -> pfam accessions/definitions

Join key verified against real data: each protein belongs to exactly one
annogroup (clean partition across single+combo) and at most one orthogroup.

Fail-fast: exits 1 if any required input is missing.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U

QUALIFYING_CLASS = "non_bilaterian_metazoan"


def load_orthogroup_classes( composition_path: Path ) -> dict:
    """orthogroup_id -> composition_class (from Script 001's 1-output table)."""
    orthogroups___classes = {}
    with open( composition_path, 'r' ) as input_composition:
        header_line = input_composition.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_class = header_ids___indices[ "Composition_Class" ]
        for line in input_composition:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroups___classes[ parts[ index_og ] ] = parts[ index_class ]
    return orthogroups___classes


def load_protein_to_orthogroup( orthogroups_path: Path ) -> dict:
    """member_full_id -> orthogroup_id (from the headerless orthogroups table)."""
    proteins___orthogroups = {}
    with open( orthogroups_path, 'r' ) as input_orthogroups:
        # Headerless: OG_ID\tmember_full_id\tmember_full_id...
        for line in input_orthogroups:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ 0 ]
            for member in parts[ 1: ]:
                if member:
                    proteins___orthogroups[ member ] = orthogroup_id
    return proteins___orthogroups


def load_annogroup_annotations( summary_path: Path ) -> dict:
    """
    annogroup_id -> ( subtype, accessions, definitions ) from the all-types OCL
    summary. Used to attach pfam context columns to Table 1.
    """
    annogroups___annotations = {}
    with open( summary_path, 'r' ) as input_summary:
        header_line = input_summary.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_subtype = header_ids___indices[ "Annogroup_Subtype" ]
        index_accessions = header_ids___indices[ "Annotation_Accessions" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        for line in input_summary:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ index_annogroup ]
            subtype = parts[ index_subtype ] if index_subtype < len( parts ) else ""
            accessions = parts[ index_accessions ] if index_accessions < len( parts ) else ""
            definitions = parts[ index_definitions ] if index_definitions < len( parts ) else ""
            annogroups___annotations[ annogroup_id ] = ( subtype, accessions, definitions )
    return annogroups___annotations


def iter_annogroup_membership( membership_path: Path ):
    """Yield ( annogroup_id, member_protein_ids list ) from a single/combo file."""
    with open( membership_path, 'r' ) as input_membership:
        # Annogroup_ID (...)\tSpecies_Count (...)\tSequence_Count (...)\tSpecies_List (...)\tSequence_IDs (...)
        # annogroup_pfam_1\t56\t20391\tAcropora_muricata,...\tg_...,g_...
        header_line = input_membership.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_sequence_ids = header_ids___indices[ "Sequence_IDs" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ index_annogroup ]
            sequence_ids_cell = parts[ index_sequence_ids ] if index_sequence_ids < len( parts ) else ""
            members = [ m for m in sequence_ids_cell.split( ',' ) if m ]
            yield ( annogroup_id, members )


def main():
    parser = argparse.ArgumentParser( description = "Build Table 1 — annogroups X orthogroups" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    input_orthogroups_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "orthogroups_file" ] )
    input_annogroups_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "annogroups_dir" ] )
    reference_structure = config[ "inputs" ][ "reference_structure" ]
    annogroup_subtypes = config[ "annogroup_subtypes" ]

    input_composition_path = Path( args.output_dir ) / "1-output" / "1_ai-orthogroups-species_composition.tsv"
    input_summary_path = input_annogroups_dir / reference_structure / f"4_ai-{reference_structure}_annogroups-complete_ocl_summary-all_types.tsv"

    if not input_composition_path.is_file():
        print( f"CRITICAL ERROR: composition table not found: {input_composition_path}", file = sys.stderr )
        print( "  Script 001 (classify_orthogroups) must run before this script.", file = sys.stderr )
        sys.exit( 1 )
    if not input_orthogroups_path.is_file():
        print( f"CRITICAL ERROR: orthogroups file not found: {input_orthogroups_path}", file = sys.stderr )
        sys.exit( 1 )
    if not input_summary_path.is_file():
        print( f"CRITICAL ERROR: annogroup all-types summary not found: {input_summary_path}", file = sys.stderr )
        print( "  Verify inputs.annogroups_dir + reference_structure expose the OCL summary.", file = sys.stderr )
        sys.exit( 1 )

    orthogroups___classes = load_orthogroup_classes( input_composition_path )
    print( f"[003] loaded {len( orthogroups___classes )} orthogroup composition classes" )
    proteins___orthogroups = load_protein_to_orthogroup( input_orthogroups_path )
    print( f"[003] loaded protein->orthogroup map: {len( proteins___orthogroups )} proteins" )
    annogroups___annotations = load_annogroup_annotations( input_summary_path )
    print( f"[003] loaded pfam annotations for {len( annogroups___annotations )} annogroups" )

    output_dir = Path( args.output_dir ) / "3-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_table_path = output_dir / "3_ai-annogroups_X_orthogroups.tsv"

    header_columns = [
        "Annogroup_ID (annogroup identifier format annogroup_pfam_N)",
        "Annogroup_Subtype (single or combo)",
        "Annotation_Accessions (comma delimited pfam accessions for this annogroup)",
        "Annotation_Definitions (semicolon delimited accession=definition pairs for this annogroup)",
        "Annogroup_Species_Count (number of unique species in the annogroup)",
        "Annogroup_Member_Protein_Count (number of member proteins in the annogroup)",
        "Members_With_Orthogroup_Count (count of member proteins that map to an orthogroup)",
        "Members_Without_Orthogroup_Count (count of member proteins that map to no orthogroup)",
        "Orthogroup_Count (number of distinct orthogroups the member proteins fall into)",
        "NonBilaterian_Metazoan_Orthogroup_Count (count of those orthogroups that are qualifying: zero bilaterians and at least one non-bilaterian metazoan)",
        "NonMetazoan_Only_Orthogroup_Count (count of those orthogroups made of only non-metazoan unicellular outgroups)",
        "Bilaterian_Only_Orthogroup_Count (count of those orthogroups made of only bilaterians)",
        "Mixed_With_Bilaterian_Orthogroup_Count (count of those orthogroups that contain bilaterians plus non-bilaterian members)",
        "NonBilaterian_Metazoan_Orthogroup_IDs (comma delimited qualifying orthogroup identifiers)",
        "NonMetazoan_Only_Orthogroup_IDs (comma delimited non-metazoan-unicell-only orthogroup identifiers)",
        "Bilaterian_Only_Orthogroup_IDs (comma delimited bilaterian-only orthogroup identifiers)",
        "Mixed_With_Bilaterian_Orthogroup_IDs (comma delimited bilaterian-plus-non-bilaterian orthogroup identifiers)",
        "All_Orthogroup_IDs (comma delimited list of every distinct orthogroup the member proteins fall into)",
    ]

    annogroup_total = 0
    annogroup_kept = 0

    with open( output_table_path, 'w' ) as output_table:
        output_table.write( '\t'.join( header_columns ) + '\n' )

        for subtype in annogroup_subtypes:
            membership_path = input_annogroups_dir / reference_structure / f"1_ai-{reference_structure}_annogroups-{subtype}.tsv"
            if not membership_path.is_file():
                print( f"CRITICAL ERROR: annogroup membership file not found: {membership_path}", file = sys.stderr )
                print( f"  subtype '{subtype}' is listed in annogroup_subtypes but its membership file is missing.", file = sys.stderr )
                sys.exit( 1 )

            for annogroup_id, members in iter_annogroup_membership( membership_path ):
                annogroup_total += 1

                members_with_orthogroup = 0
                members_without_orthogroup = 0
                orthogroup_ids = set()
                member_species = set()
                for member in members:
                    source_gene_field, phyloname, genus_species = U.parse_full_gigantic_id( member )
                    if genus_species is not None:
                        member_species.add( genus_species )
                    orthogroup_id = proteins___orthogroups.get( member )
                    if orthogroup_id is None:
                        members_without_orthogroup += 1
                        continue
                    members_with_orthogroup += 1
                    orthogroup_ids.add( orthogroup_id )

                non_bilaterian_metazoan_ogs = []
                non_metazoan_only_ogs = []
                bilaterian_only_ogs = []
                mixed_with_bilaterian_ogs = []
                for orthogroup_id in sorted( orthogroup_ids ):
                    composition_class = orthogroups___classes.get( orthogroup_id )
                    if composition_class == "non_bilaterian_metazoan":
                        non_bilaterian_metazoan_ogs.append( orthogroup_id )
                    elif composition_class == "non_metazoan_only":
                        non_metazoan_only_ogs.append( orthogroup_id )
                    elif composition_class == "bilaterian_only":
                        bilaterian_only_ogs.append( orthogroup_id )
                    elif composition_class == "mixed_with_bilaterian":
                        mixed_with_bilaterian_ogs.append( orthogroup_id )
                    # An orthogroup with no class would be a referential-integrity
                    # error; Script 004 validates that none slip through.

                # KEEP rule (user-approved): keep iff at least one orthogroup is
                # qualifying (non_bilaterian_metazoan). Drop everything else.
                if len( non_bilaterian_metazoan_ogs ) == 0:
                    continue

                subtype_from_summary, accessions, definitions = annogroups___annotations.get(
                    annogroup_id, ( subtype, "", "" )
                )

                all_ogs = sorted( orthogroup_ids )
                output = '\t'.join( [
                    annogroup_id,
                    subtype,
                    accessions,
                    definitions,
                    str( len( member_species ) ),
                    str( len( members ) ),
                    str( members_with_orthogroup ),
                    str( members_without_orthogroup ),
                    str( len( orthogroup_ids ) ),
                    str( len( non_bilaterian_metazoan_ogs ) ),
                    str( len( non_metazoan_only_ogs ) ),
                    str( len( bilaterian_only_ogs ) ),
                    str( len( mixed_with_bilaterian_ogs ) ),
                    U.DELIM.join( non_bilaterian_metazoan_ogs ),
                    U.DELIM.join( non_metazoan_only_ogs ),
                    U.DELIM.join( bilaterian_only_ogs ),
                    U.DELIM.join( mixed_with_bilaterian_ogs ),
                    U.DELIM.join( all_ogs ),
                ] ) + '\n'
                output_table.write( output )
                annogroup_kept += 1

    print( f"[003] annogroups kept (>=1 qualifying orthogroup): {annogroup_kept} of {annogroup_total} -> {output_table_path}" )

    if annogroup_total == 0:
        print( "CRITICAL ERROR: zero annogroups read — membership files appear empty", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
