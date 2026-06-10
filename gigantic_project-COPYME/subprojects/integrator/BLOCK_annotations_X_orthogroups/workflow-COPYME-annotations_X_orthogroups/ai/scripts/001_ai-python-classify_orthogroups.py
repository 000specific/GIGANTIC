#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Classify every orthogroup by bilaterian / non-bilaterian species composition
# Human: Eric Edsinger

"""
Script 001 — Orthogroup species-composition classification.

Reads the orthogroups membership table (headerless: OG_ID then tab-delimited
member full GIGANTIC IDs) and the Bilateria clade species set from trees_species.

For each orthogroup, member species are resolved from each member's
-n_<phyloname> and classified relative to the Bilateria species set:

  - bilaterian_only     : every member species is in Bilateria
  - non_bilaterian_only : NO member species is in Bilateria (i.e. zero
                          bilaterian members; non-bilaterian metazoans AND
                          non-metazoan outgroups both count as non-bilaterian)
  - mixed               : both bilaterian and non-bilaterian members present

This classification is the shared spine for Table 2 (Script 002) and the
per-orthogroup class lookup for Table 1 (Script 003). Structure-independent:
the Bilateria species set is a named clade outside the unresolved zone and is
stable across all species-tree structures (Rule 6).

Fail-fast: exits 1 if the Bilateria clade row, the clade-mapping file, or the
orthogroups file is missing.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U


def load_bilateria_species( mappings_path: Path, reference_structure: str, clade_id_name: str ) -> set:
    """
    Read the Bilateria descendant-species set from the trees_species
    clade->species mapping file for one reference structure.

    Returns a set of Genus_species strings. Exits 1 if the requested clade row
    is not found (a clade name typo or wrong species set must fail loudly, not
    silently yield an empty bilaterian set that would mislabel every orthogroup).
    """
    bilaterian_species = set()
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
                bilaterian_species = { s for s in species_cell.split( ',' ) if s }
                found = True
                break

    if not found:
        print( f"CRITICAL ERROR: Bilateria clade '{clade_id_name}' not found in mapping file", file = sys.stderr )
        print( f"  File: {mappings_path}", file = sys.stderr )
        print( f"  Reference structure: {reference_structure}", file = sys.stderr )
        print( "  Verify bilateria_clade_id_name + bilateria_reference_structure in the config.", file = sys.stderr )
        sys.exit( 1 )
    if not bilaterian_species:
        print( f"CRITICAL ERROR: Bilateria clade '{clade_id_name}' resolved to ZERO species", file = sys.stderr )
        print( f"  File: {mappings_path}", file = sys.stderr )
        sys.exit( 1 )

    return bilaterian_species


def classify_composition( member_species: set, bilaterian_species: set ) -> tuple:
    """
    Return ( composition_class, bilaterian_count, non_bilaterian_count ) for one
    orthogroup's member-species set.
    """
    bilaterian_members = member_species & bilaterian_species
    non_bilaterian_members = member_species - bilaterian_species
    bilaterian_count = len( bilaterian_members )
    non_bilaterian_count = len( non_bilaterian_members )

    if non_bilaterian_count == 0 and bilaterian_count > 0:
        composition_class = "bilaterian_only"
    elif bilaterian_count == 0 and non_bilaterian_count > 0:
        composition_class = "non_bilaterian_only"
    else:
        composition_class = "mixed"

    return ( composition_class, bilaterian_count, non_bilaterian_count )


def main():
    parser = argparse.ArgumentParser( description = "Classify orthogroups by bilaterian/non-bilaterian species composition" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    input_orthogroups_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "orthogroups_file" ] )
    input_mappings_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "bilateria_clade_species_mappings" ] )
    bilateria_clade_id_name = config[ "inputs" ][ "bilateria_clade_id_name" ]
    bilateria_reference_structure = config[ "inputs" ][ "bilateria_reference_structure" ]

    if not input_orthogroups_path.is_file():
        print( f"CRITICAL ERROR: orthogroups file not found: {input_orthogroups_path}", file = sys.stderr )
        print( "  Verify inputs.orthogroups_file resolves to a populated output_to_input/ table.", file = sys.stderr )
        sys.exit( 1 )
    if not input_mappings_path.is_file():
        print( f"CRITICAL ERROR: Bilateria clade-species mapping not found: {input_mappings_path}", file = sys.stderr )
        print( "  Verify inputs.bilateria_clade_species_mappings (trees_species output_to_input).", file = sys.stderr )
        sys.exit( 1 )

    bilaterian_species = load_bilateria_species(
        input_mappings_path, bilateria_reference_structure, bilateria_clade_id_name
    )
    print( f"[001] Bilateria ({bilateria_clade_id_name}) = {len( bilaterian_species )} species" )

    output_dir = Path( args.output_dir ) / "1-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_composition_path = output_dir / "1_ai-orthogroups-species_composition.tsv"

    header_columns = [
        "Orthogroup_ID (orthogroup identifier from the orthogroups subproject)",
        "Member_Protein_Count (number of member protein sequence identifiers in the orthogroup)",
        "Species_Count (number of unique species among the member proteins)",
        "Bilaterian_Species_Count (count of member species that are in the Bilateria clade)",
        "NonBilaterian_Species_Count (count of member species that are not in the Bilateria clade)",
        "Composition_Class (bilaterian_only if every species is bilaterian, non_bilaterian_only if no species is bilaterian, mixed otherwise)",
        "Species_List (comma delimited list of member species as Genus_species)",
    ]

    counts___classes = { "bilaterian_only": 0, "non_bilaterian_only": 0, "mixed": 0 }
    orthogroup_count = 0
    unparsed_member_count = 0

    with open( input_orthogroups_path, 'r' ) as input_orthogroups, \
         open( output_composition_path, 'w' ) as output_composition:
        output_composition.write( '\t'.join( header_columns ) + '\n' )

        # Headerless: OG_ID\tmember_full_id\tmember_full_id...
        # OG000000\tg_g5785-t_g5785.t1-p_g5785.t1-n_Holozoa..._Abeoforma_whisleri\tg_LOC...-n_Metazoa_Cnidaria_..._Acropora_muricata\t...
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

            composition_class, bilaterian_count, non_bilaterian_count = classify_composition(
                member_species, bilaterian_species
            )
            counts___classes[ composition_class ] += 1

            output = '\t'.join( [
                orthogroup_id,
                str( len( members ) ),
                str( len( member_species ) ),
                str( bilaterian_count ),
                str( non_bilaterian_count ),
                composition_class,
                U.DELIM.join( sorted( member_species ) ),
            ] ) + '\n'
            output_composition.write( output )
            orthogroup_count += 1

    print( f"[001] classified {orthogroup_count} orthogroups -> {output_composition_path}" )
    print( f"[001]   bilaterian_only={counts___classes[ 'bilaterian_only' ]}  "
           f"non_bilaterian_only={counts___classes[ 'non_bilaterian_only' ]}  "
           f"mixed={counts___classes[ 'mixed' ]}" )
    if unparsed_member_count:
        print( f"[001]   note: {unparsed_member_count} member IDs did not parse to a phyloname (skipped from species sets)" )

    if orthogroup_count == 0:
        print( "CRITICAL ERROR: zero orthogroups classified — orthogroups file appears empty", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
