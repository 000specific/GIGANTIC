#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 20 | Purpose: Deconvolve the species trees into per-clade member-protein-count columns added to the annogroup table
# Human: Eric Edsinger

"""
Script 004 — Species tree deconvolution of the annogroup table (one source).

Takes everything from the Script 002 annogroup map and ADDS, per annogroup row,
one column per NON-REDUNDANT clade (node or tip) across ALL 105 species-tree
structures. Each added cell is the count of the annogroup's member proteins
within that clade:
  - tip (a species)    -> member proteins in that one species
  - internal node      -> sum over its descendant species
so any clade that covers all species (a tree root) equals the annogroup's
Sequence_Count.

Why one file for all 105 structures (and why this is non-redundant):
A clade_id_name identifies a fixed topologically-structured species set (GIGANTIC
Rule 6): the SAME clade has the SAME descendant species in every structure it
appears in, so an annogroup's count at that clade is IDENTICAL across structures.
The 105 structures therefore contribute a UNION of distinct clades (the stable
clades shared by all + the ambiguous-zone variants); each unique clade is one
column, computed once. The base annogroups remain structure-independent; this is
an overlay that lays every clade across the 105 trees out as columns.

Inputs (per source, already on disk):
  - 2-output/<source>/2_ai-<source>-annogroup_map.tsv          (carried forward)
  - 2-output/<source>/2_ai-<source>-annogroup_membership.tsv   (member -> species)
  - clade_species_mappings (trees_species), all structures

Output (4-output/<source>/):
  4_ai-<source>-annogroup_tree_counts-all_structures.tsv
    = the annogroup map columns + one member-protein-count column per
      non-redundant clade, ordered largest clade (root) -> tips.

Fail-fast (§36): exits 1 if inputs are missing, if any clade_id_name carries
DIFFERENT species sets across structures (Rule 6 violation), if a membership
species is not a tree tip (silent member loss), or if a full-coverage clade's
count != an annogroup's Sequence_Count.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_annogroups as U


def load_clade_data( clade_map_path: Path ):
    """
    Load clades from the trees_species clade->species map (all structures), building
    BOTH the non-redundant union (for the single combined table) AND each structure's
    own clade set + parent/child topology (for the per-structure tables). Validates
    Rule-6 consistency (same clade_id_name => same species set everywhere).

    Returns:
        clades___species          { clade_id_name: frozenset( Genus_species ) }
        clades___descendant_count { clade_id_name: int }   (0 for tips)
        clades___structure_count  { clade_id_name: int }   (# structures it appears in)
        tip_species               set of Genus_species (the leaves)
        structures___parents_children { structure: { parent_clade: [child_clade,...] } }
        structures___clades       { structure: set(clade_id_name) }
        all_structures            sorted list of structure ids
    """
    clades___species = {}
    clades___descendant_count = {}
    clades___structures = defaultdict( set )
    tip_species = set()
    structures___parents_children = defaultdict( lambda: defaultdict( list ) )
    structures___clades = defaultdict( set )
    all_structures = set()

    with open( clade_map_path, 'r' ) as input_clade_map:
        header_ids___indices = U.build_header_index( input_clade_map.readline() )
        index_structure = header_ids___indices[ "Structure_ID" ]
        index_clade = header_ids___indices[ "Clade_ID_Name" ]
        index_block = header_ids___indices[ "Phylogenetic_Block" ]
        index_descendant_count = header_ids___indices[ "Descendant_Species_Count" ]
        index_descendant_list = header_ids___indices[ "Descendant_Species_List" ]

        for line in input_clade_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ index_structure ]
            clade_id_name = parts[ index_clade ]
            descendant_count = int( parts[ index_descendant_count ] ) if parts[ index_descendant_count ] else 0
            descendant_list = parts[ index_descendant_list ] if index_descendant_list < len( parts ) else ''

            all_structures.add( structure_id )
            clades___structures[ clade_id_name ].add( structure_id )
            structures___clades[ structure_id ].add( clade_id_name )

            # per-structure tree edge (parent::child block; child = this clade)
            block = parts[ index_block ]
            if '::' in block:
                parent_clade = block.split( '::' )[ 0 ]
                structures___parents_children[ structure_id ][ parent_clade ].append( clade_id_name )

            if descendant_count > 0:
                species = frozenset( name.strip() for name in descendant_list.split( ',' ) if name.strip() )
            else:
                species_name = clade_id_name.split( '_', 1 )[ 1 ] if '_' in clade_id_name else clade_id_name
                species = frozenset( [ species_name ] )
                tip_species.add( species_name )

            if clade_id_name in clades___species:
                # Rule 6: the same clade_id_name MUST carry the same species set.
                if clades___species[ clade_id_name ] != species:
                    print( f"CRITICAL ERROR: clade {clade_id_name} has DIFFERENT species sets across "
                           f"structures (Rule 6 violation) -- counts would be ill-defined", file = sys.stderr )
                    sys.exit( 1 )
            else:
                clades___species[ clade_id_name ] = species
                clades___descendant_count[ clade_id_name ] = descendant_count

    if not clades___species:
        print( f"CRITICAL ERROR: no clades found in {clade_map_path}", file = sys.stderr )
        sys.exit( 1 )

    clades___structure_count = { clade: len( structures ) for clade, structures in clades___structures.items() }
    return ( clades___species, clades___descendant_count, clades___structure_count, tip_species,
             structures___parents_children, structures___clades, sorted( all_structures ) )


def order_structure_clades_root_to_tips( parents_children, structure_clades, clades___descendant_count ):
    """
    Depth-first pre-order (root -> tips) for ONE structure. The root is the clade
    whose parent is NOT a clade of this structure (it sits above the species tree).
    Children are visited largest-clade-first for a tree-like read.
    """
    clades___parents = {}
    for parent_clade, children in parents_children.items():
        for child_clade in children:
            clades___parents[ child_clade ] = parent_clade
    roots = [ clade for clade in structure_clades if clades___parents.get( clade ) not in structure_clades ]
    root = max( roots, key = lambda clade: clades___descendant_count.get( clade, 0 ) )

    ordered = []
    stack = [ root ]
    while stack:
        clade = stack.pop()
        ordered.append( clade )
        children = sorted(
            parents_children.get( clade, [] ),
            key = lambda child: ( -clades___descendant_count.get( child, 0 ), child )
        )
        for child in reversed( children ):
            stack.append( child )
    return ordered


def load_annogroup_species_counts( membership_path: Path ):
    """annogroup_id -> { Genus_species: member_protein_count } from the 002 membership."""
    annogroups___species_counts = defaultdict( lambda: defaultdict( int ) )
    all_membership_species = set()
    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_genus_species = header_ids___indices[ "Genus_Species" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            genus_species = parts[ index_genus_species ]
            annogroups___species_counts[ parts[ index_annogroup ] ][ genus_species ] += 1
            all_membership_species.add( genus_species )
    return annogroups___species_counts, all_membership_species


def main():
    parser = argparse.ArgumentParser( description = "Deconvolve all species-tree clades into per-clade annogroup counts" )
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
    clade_map_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "clade_species_mappings" ] )

    for required in ( map_path, membership_path, clade_map_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required file not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    # ---- clades: non-redundant union + per-structure topology --------------
    ( clades___species, clades___descendant_count, clades___structure_count, tip_species,
      structures___parents_children, structures___clades, all_structures ) = load_clade_data( clade_map_path )
    total_structures = len( all_structures )

    # UNION column order: largest clade (root) -> tips, then clade_id_name for ties
    union_ordered_clades = sorted(
        clades___species.keys(),
        key = lambda clade: ( -clades___descendant_count[ clade ], clade )
    )
    # clades whose species set covers every tip -> tree roots; their count per
    # annogroup must equal Sequence_Count (research-integrity check below).
    full_coverage_clades = [ clade for clade in union_ordered_clades if clades___species[ clade ] == frozenset( tip_species ) ]

    # PER-STRUCTURE column order: each structure's own clades, root -> tips
    structures___ordered_clades = {
        structure: order_structure_clades_root_to_tips(
            structures___parents_children[ structure ], structures___clades[ structure ], clades___descendant_count )
        for structure in all_structures
    }
    print( f"[004 {source}] union of {len( union_ordered_clades )} non-redundant clades across {total_structures} "
           f"structures ({len( tip_species )} tips); {len( full_coverage_clades )} full-coverage root clade(s)" )

    # species -> the clades whose covered species set contains it
    species___ancestor_clades = defaultdict( list )
    for clade_id_name, species in clades___species.items():
        for species_name in species:
            species___ancestor_clades[ species_name ].append( clade_id_name )

    # ---- per-annogroup per-species member-protein counts -------------------
    annogroups___species_counts, all_membership_species = load_annogroup_species_counts( membership_path )
    print( f"[004 {source}] aggregated member counts for {len( annogroups___species_counts )} annogroups" )

    species_not_in_tree = sorted( all_membership_species - tip_species )
    if species_not_in_tree:
        print( f"CRITICAL ERROR: {len( species_not_in_tree )} membership species are not tree tips "
               f"(members would be silently uncounted): {species_not_in_tree[ :5 ]}", file = sys.stderr )
        sys.exit( 1 )

    # ---- read the 002 map (carried-forward columns + Sequence_Count check) --
    with open( map_path, 'r' ) as input_map:
        map_header_line = input_map.readline().rstrip( '\n' )
        map_header_ids___indices = U.build_header_index( map_header_line )
        index_map_annogroup = map_header_ids___indices[ "Annogroup_ID" ]
        index_map_sequence_count = map_header_ids___indices[ "Sequence_Count" ]
        map_rows = [ line.rstrip( '\n' ) for line in input_map if line.strip() ]

    # ---- self-documenting clade header -------------------------------------
    def clade_header( clade ):
        present = f"present in {clades___structure_count[ clade ]} of {total_structures} structures"
        if clades___descendant_count[ clade ] == 0:
            species_name = next( iter( clades___species[ clade ] ) )
            return f"{clade} (member-protein count of this annogroup within tip {clade} = species {species_name}; {present})"
        return ( f"{clade} (member-protein count of this annogroup within clade {clade}; "
                 f"{clades___descendant_count[ clade ]} descendant species; {present})" )

    # ---- outputs: ONE combined union table + ONE file per structure --------
    output_dir = output_base / "4-output" / source
    output_dir.mkdir( parents = True, exist_ok = True )
    union_path = output_dir / f"4_ai-{source}-annogroup_tree_counts-all_structures.tsv"
    per_structure_dir = output_dir / "annogroup_tree_counts_per_structure"
    per_structure_dir.mkdir( parents = True, exist_ok = True )

    # open the per-structure files and write their headers
    structures___files = {}
    for structure in all_structures:
        per_structure_path = per_structure_dir / f"4_ai-{source}-annogroup_tree_counts-{structure}.tsv"
        output_file = open( per_structure_path, 'w' )
        output_file.write( map_header_line + '\t'
                           + '\t'.join( clade_header( clade ) for clade in structures___ordered_clades[ structure ] ) + '\n' )
        structures___files[ structure ] = output_file

    rows_written = 0
    with open( union_path, 'w' ) as union_table:
        union_table.write( map_header_line + '\t'
                           + '\t'.join( clade_header( clade ) for clade in union_ordered_clades ) + '\n' )

        for map_row in map_rows:
            parts = map_row.split( '\t' )
            annogroup_id = parts[ index_map_annogroup ]
            sequence_count = int( parts[ index_map_sequence_count ] ) if parts[ index_map_sequence_count ] else 0

            # the per-clade counts (computed ONCE; shared by the union + per-structure files)
            clades___counts = defaultdict( int )
            for species_name, count in annogroups___species_counts.get( annogroup_id, {} ).items():
                for clade_id_name in species___ancestor_clades[ species_name ]:
                    clades___counts[ clade_id_name ] += count

            # research-integrity: every full-coverage (root) clade must total Sequence_Count
            for clade in full_coverage_clades:
                if clades___counts.get( clade, 0 ) != sequence_count:
                    print( f"CRITICAL ERROR: annogroup {annogroup_id} count at full-coverage clade {clade} "
                           f"({clades___counts.get( clade, 0 )}) != Sequence_Count {sequence_count}", file = sys.stderr )
                    sys.exit( 1 )

            union_table.write( map_row + '\t'
                               + '\t'.join( str( clades___counts.get( clade, 0 ) ) for clade in union_ordered_clades ) + '\n' )
            for structure in all_structures:
                structures___files[ structure ].write(
                    map_row + '\t'
                    + '\t'.join( str( clades___counts.get( clade, 0 ) ) for clade in structures___ordered_clades[ structure ] ) + '\n' )
            rows_written += 1

    for output_file in structures___files.values():
        output_file.close()

    print( f"[004 {source}] wrote {rows_written} annogroup rows: union ({len( union_ordered_clades )} clades) -> {union_path.name}; "
           f"{total_structures} per-structure files -> {per_structure_dir.name}/" )


if __name__ == '__main__':
    main()
