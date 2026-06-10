#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Build Table 2 — the non-bilaterian-only orthogroups
# Human: Eric Edsinger

"""
Script 002 — Table 2: non-bilaterian-only orthogroups.

Reads the orthogroup species-composition classification (Script 001, 1-output)
and keeps the orthogroups classified non_bilaterian_only — orthogroups whose
member species contain NO bilaterian (every member is a non-bilaterian metazoan
or a non-metazoan outgroup).

One row per kept orthogroup. Fail-fast: exits 1 if the composition table is
missing.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U


def main():
    parser = argparse.ArgumentParser( description = "Build Table 2 — non-bilaterian-only orthogroups" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    input_composition_path = Path( args.output_dir ) / "1-output" / "1_ai-orthogroups-species_composition.tsv"
    if not input_composition_path.is_file():
        print( f"CRITICAL ERROR: composition table not found: {input_composition_path}", file = sys.stderr )
        print( "  Script 001 (classify_orthogroups) must run before this script.", file = sys.stderr )
        sys.exit( 1 )

    output_dir = Path( args.output_dir ) / "2-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_table_path = output_dir / "2_ai-nonbilaterian_orthogroups.tsv"

    header_columns = [
        "Orthogroup_ID (orthogroup identifier from the orthogroups subproject)",
        "Member_Protein_Count (number of member protein sequence identifiers in the orthogroup)",
        "Species_Count (number of unique non-bilaterian species among the member proteins)",
        "NonBilaterian_Species_Count (count of member species that are not in the Bilateria clade; equals Species_Count for a non-bilaterian-only orthogroup)",
        "Species_List (comma delimited list of member species as Genus_species; all non-bilaterian)",
    ]

    kept_count = 0
    total_count = 0
    with open( input_composition_path, 'r' ) as input_composition, \
         open( output_table_path, 'w' ) as output_table:
        output_table.write( '\t'.join( header_columns ) + '\n' )

        # Orthogroup_ID (...)\tMember_Protein_Count (...)\tSpecies_Count (...)\tBilaterian_Species_Count (...)\tNonBilaterian_Species_Count (...)\tComposition_Class (...)\tSpecies_List (...)
        # OG000123\t44\t6\t0\t6\tnon_bilaterian_only\tBeroe_ovata,Bolinopsis_microptera,...
        header_line = input_composition.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_member_count = header_ids___indices[ "Member_Protein_Count" ]
        index_species_count = header_ids___indices[ "Species_Count" ]
        index_non_bilaterian = header_ids___indices[ "NonBilaterian_Species_Count" ]
        index_class = header_ids___indices[ "Composition_Class" ]
        index_species_list = header_ids___indices[ "Species_List" ]

        for line in input_composition:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            total_count += 1
            if parts[ index_class ] != "non_bilaterian_only":
                continue

            output = '\t'.join( [
                parts[ index_og ],
                parts[ index_member_count ],
                parts[ index_species_count ],
                parts[ index_non_bilaterian ],
                parts[ index_species_list ],
            ] ) + '\n'
            output_table.write( output )
            kept_count += 1

    print( f"[002] non-bilaterian-only orthogroups: {kept_count} of {total_count} -> {output_table_path}" )


if __name__ == '__main__':
    main()
