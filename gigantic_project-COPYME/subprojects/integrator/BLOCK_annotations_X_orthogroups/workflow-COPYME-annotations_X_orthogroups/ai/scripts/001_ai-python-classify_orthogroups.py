#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Classify every orthogroup by bilaterian / non-bilaterian-metazoan / non-metazoan species composition
# Human: Eric Edsinger

"""
Script 001 — Orthogroup species-composition classification.

Reads the orthogroups membership table (headerless: OG_ID then tab-delimited
member full GIGANTIC IDs) and two clade species sets from trees_species:
Bilateria (C103) and Metazoa (C082).

Each member species is placed in one of three categories:
  - bilaterian            : species in Bilateria
  - non_bilaterian_metazoan: species in Metazoa but NOT in Bilateria
                            (ctenophores, sponges, cnidarians, placozoans)
  - non_metazoan          : species NOT in Metazoa (unicellular outgroups)

Each orthogroup is classified by its member-species composition (B = bilaterian
count, M = non-bilaterian-metazoan count, U = non-metazoan count):
  - bilaterian_only        : B>0, M==0, U==0
  - mixed_with_bilaterian  : B>0 and (M>0 or U>0)
  - non_bilaterian_metazoan: B==0, M>0           <-- the QUALIFYING class
  - non_metazoan_only      : B==0, M==0, U>0      (unicell-only; does NOT qualify)

A QUALIFYING orthogroup (class non_bilaterian_metazoan) has zero bilaterians and
at least one non-bilaterian metazoan; non-metazoan members may ride along.

This classification is the shared spine for Table 2 (Script 002) and the
per-orthogroup class lookup for Table 1 (Script 003). Structure-independent:
both clade species sets are named clades outside the unresolved zone and are
stable across all species-tree structures (Rule 6).

Fail-fast: exits 1 if a requested clade row, the clade-mapping file, or the
orthogroups file is missing.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U


def load_clade_species( mappings_path: Path, reference_structure: str, clade_id_name: str ) -> set:
    """
    Read a clade's descendant-species set from the trees_species clade->species
    mapping file for one reference structure. Returns a set of Genus_species.

    Exits 1 if the requested clade row is not found or resolves to zero species
    (a clade typo or wrong species set must fail loudly, not silently yield an
    empty set that would mislabel every orthogroup).
    """
    clade_species = set()
    found = False
    with open( mappings_path, 'r' ) as input_mappings:
        # Structure_ID (...)\tClade_ID_Name (...)\tPhylogenetic_Block (...)\tDescendant_Species_Count (...)\tDescendant_Species_List (...)
        # structure_001\tC103_Bilateria\t...\t35\tAdineta_vaga,Amphiscolops_sp_MND2022,...
        header_line = input_mappings.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_structure = header_ids___indices[ "Structure_ID" ]
        index_clade = header_ids___indices[ "Clade_ID_Name" ]
        index_species_list = header_ids___indices[ "Descendant_Species_List" ]
        for line in input_mappings:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_structure ] == reference_structure and parts[ index_clade ] == clade_id_name:
                species_cell = parts[ index_species_list ] if index_species_list < len( parts ) else ""
                clade_species = { s for s in species_cell.split( ',' ) if s }
                found = True
                break

    if not found:
        print( f"CRITICAL ERROR: clade '{clade_id_name}' not found in mapping file", file = sys.stderr )
        print( f"  File: {mappings_path}", file = sys.stderr )
        print( f"  Reference structure: {reference_structure}", file = sys.stderr )
        print( "  Verify the clade_id_name + clade_reference_structure in the config.", file = sys.stderr )
        sys.exit( 1 )
    if not clade_species:
        print( f"CRITICAL ERROR: clade '{clade_id_name}' resolved to ZERO species", file = sys.stderr )
        print( f"  File: {mappings_path}", file = sys.stderr )
        sys.exit( 1 )

    return clade_species


def classify_composition( member_species: set, bilaterian_species: set, metazoan_species: set ) -> tuple:
    """
    Return ( composition_class, bilaterian_count, non_bilaterian_metazoan_count,
    non_metazoan_count ) for one orthogroup's member-species set.
    """
    bilaterian_members = member_species & bilaterian_species
    # non-bilaterian metazoan = in Metazoa but not in Bilateria
    non_bilaterian_metazoan_members = ( member_species & metazoan_species ) - bilaterian_species
    # non-metazoan = not in Metazoa
    non_metazoan_members = member_species - metazoan_species

    bilaterian_count = len( bilaterian_members )
    non_bilaterian_metazoan_count = len( non_bilaterian_metazoan_members )
    non_metazoan_count = len( non_metazoan_members )

    if bilaterian_count > 0:
        if non_bilaterian_metazoan_count == 0 and non_metazoan_count == 0:
            composition_class = "bilaterian_only"
        else:
            composition_class = "mixed_with_bilaterian"
    else:
        if non_bilaterian_metazoan_count > 0:
            composition_class = "non_bilaterian_metazoan"
        else:
            composition_class = "non_metazoan_only"

    return ( composition_class, bilaterian_count, non_bilaterian_metazoan_count, non_metazoan_count )


def main():
    parser = argparse.ArgumentParser( description = "Classify orthogroups by bilaterian / non-bilaterian-metazoan / non-metazoan composition" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    input_orthogroups_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "orthogroups_file" ] )
    input_mappings_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "clade_species_mappings" ] )
    bilateria_clade_id_name = config[ "inputs" ][ "bilateria_clade_id_name" ]
    metazoa_clade_id_name = config[ "inputs" ][ "metazoa_clade_id_name" ]
    clade_reference_structure = config[ "inputs" ][ "clade_reference_structure" ]

    if not input_orthogroups_path.is_file():
        print( f"CRITICAL ERROR: orthogroups file not found: {input_orthogroups_path}", file = sys.stderr )
        print( "  Verify inputs.orthogroups_file resolves to a populated output_to_input/ table.", file = sys.stderr )
        sys.exit( 1 )
    if not input_mappings_path.is_file():
        print( f"CRITICAL ERROR: clade-species mapping not found: {input_mappings_path}", file = sys.stderr )
        print( "  Verify inputs.clade_species_mappings (trees_species output_to_input).", file = sys.stderr )
        sys.exit( 1 )

    bilaterian_species = load_clade_species( input_mappings_path, clade_reference_structure, bilateria_clade_id_name )
    metazoan_species = load_clade_species( input_mappings_path, clade_reference_structure, metazoa_clade_id_name )
    non_bilaterian_metazoan_species = metazoan_species - bilaterian_species
    print( f"[001] Bilateria ({bilateria_clade_id_name}) = {len( bilaterian_species )} species" )
    print( f"[001] Metazoa ({metazoa_clade_id_name}) = {len( metazoan_species )} species "
           f"-> {len( non_bilaterian_metazoan_species )} non-bilaterian metazoans" )

    # Sanity: Bilateria must be a subset of Metazoa, else the clade IDs are wrong.
    if not bilaterian_species.issubset( metazoan_species ):
        stray = sorted( bilaterian_species - metazoan_species )[ :5 ]
        print( "CRITICAL ERROR: Bilateria is not a subset of Metazoa — clade IDs look wrong", file = sys.stderr )
        print( f"  Example bilaterian species not in Metazoa: {stray}", file = sys.stderr )
        sys.exit( 1 )

    output_dir = Path( args.output_dir ) / "1-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_composition_path = output_dir / "1_ai-orthogroups-species_composition.tsv"

    header_columns = [
        "Orthogroup_ID (orthogroup identifier from the orthogroups subproject)",
        "Member_Protein_Count (number of member protein sequence identifiers in the orthogroup)",
        "Species_Count (number of unique species among the member proteins)",
        "Bilaterian_Species_Count (count of member species in the Bilateria clade)",
        "NonBilaterian_Metazoan_Species_Count (count of member species in Metazoa but not in Bilateria)",
        "NonMetazoan_Species_Count (count of member species not in Metazoa; unicellular outgroups)",
        "Composition_Class (one of bilaterian_only, mixed_with_bilaterian, non_bilaterian_metazoan, non_metazoan_only)",
        "Qualifies_NonBilaterian_Metazoan (yes when Composition_Class is non_bilaterian_metazoan: zero bilaterians and at least one non-bilaterian metazoan)",
        "Species_List (comma delimited list of member species as Genus_species)",
    ]

    counts___classes = {
        "bilaterian_only": 0,
        "mixed_with_bilaterian": 0,
        "non_bilaterian_metazoan": 0,
        "non_metazoan_only": 0,
    }
    orthogroup_count = 0
    unparsed_member_count = 0

    with open( input_orthogroups_path, 'r' ) as input_orthogroups, \
         open( output_composition_path, 'w' ) as output_composition:
        output_composition.write( '\t'.join( header_columns ) + '\n' )

        # Headerless: OG_ID\tmember_full_id\tmember_full_id...
        # OG000000\tg_g5785-...-n_Holozoa..._Abeoforma_whisleri\tg_LOC...-n_Metazoa_Cnidaria_..._Acropora_muricata\t...
        for line in input_orthogroups:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ 0 ]
            members = [ m for m in parts[ 1: ] if m ]

            member_species = set()
            for member in members:
                source_gene_field, phyloname, genus_species = U.parse_full_gigantic_id( member )
                if genus_species is None:
                    unparsed_member_count += 1
                    continue
                member_species.add( genus_species )

            composition_class, bilaterian_count, non_bilaterian_metazoan_count, non_metazoan_count = classify_composition(
                member_species, bilaterian_species, metazoan_species
            )
            counts___classes[ composition_class ] += 1
            qualifies = "yes" if composition_class == "non_bilaterian_metazoan" else "no"

            output = '\t'.join( [
                orthogroup_id,
                str( len( members ) ),
                str( len( member_species ) ),
                str( bilaterian_count ),
                str( non_bilaterian_metazoan_count ),
                str( non_metazoan_count ),
                composition_class,
                qualifies,
                U.DELIM.join( sorted( member_species ) ),
            ] ) + '\n'
            output_composition.write( output )
            orthogroup_count += 1

    print( f"[001] classified {orthogroup_count} orthogroups -> {output_composition_path}" )
    print( f"[001]   bilaterian_only={counts___classes[ 'bilaterian_only' ]}  "
           f"mixed_with_bilaterian={counts___classes[ 'mixed_with_bilaterian' ]}  "
           f"non_bilaterian_metazoan={counts___classes[ 'non_bilaterian_metazoan' ]} (QUALIFYING)  "
           f"non_metazoan_only={counts___classes[ 'non_metazoan_only' ]}" )
    if unparsed_member_count:
        print( f"[001]   note: {unparsed_member_count} member IDs did not parse to a phyloname (skipped from species sets)" )

    if orthogroup_count == 0:
        print( "CRITICAL ERROR: zero orthogroups classified — orthogroups file appears empty", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
