#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Validate the annotations_X_orthogroups integration tables (strict fail-fast, §36)
# Human: Eric Edsinger

"""
Script 004 — Validation (strict fail-fast per gigantic_conventions §36).

Cross-checks the three output tables for internal consistency. ANY failure
writes a FAIL report and exits 1 (research-integrity: a silent join artifact in
published results is unacceptable, per AI_BEHAVIOR.md).

Checks:
  1. Composition_Class is one of {bilaterian_only, non_bilaterian_only, mixed}
     for every orthogroup.
  2. Table 2 row count == count of non_bilaterian_only rows in the composition
     table, and every Table 2 orthogroup is classified non_bilaterian_only.
  3. Table 1 referential integrity: every orthogroup ID referenced in Table 1
     exists in the composition table.
  4. Table 1 internal arithmetic per row:
       - NonBilaterian + Bilaterian + Mixed counts == Orthogroup_Count
       - each per-class ID-list length == its per-class count
       - Members_With + Members_Without == Annogroup_Member_Protein_Count
  5. Table 1 keep-rule: every retained annogroup has
     NonBilaterian_Only_Orthogroup_Count >= 1.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U

VALID_CLASSES = { "bilaterian_only", "non_bilaterian_only", "mixed" }


def split_cell( cell: str ) -> list:
    return [ token for token in cell.split( U.DELIM ) if token ]


def main():
    parser = argparse.ArgumentParser( description = "Validate annotations_X_orthogroups results (fail-fast)" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    output_base = Path( args.output_dir )
    composition_path = output_base / "1-output" / "1_ai-orthogroups-species_composition.tsv"
    table2_path = output_base / "2-output" / "2_ai-nonbilaterian_orthogroups.tsv"
    table1_path = output_base / "3-output" / "3_ai-annogroups_X_orthogroups.tsv"

    failures = []

    for required in ( composition_path, table2_path, table1_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required table not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    # ---- load composition: orthogroup -> class --------------------------------
    orthogroups___classes = {}
    composition_non_bilaterian_count = 0
    with open( composition_path, 'r' ) as input_composition:
        header_ids___indices = U.build_header_index( input_composition.readline() )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_class = header_ids___indices[ "Composition_Class" ]
        for line in input_composition:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ index_og ]
            composition_class = parts[ index_class ]
            orthogroups___classes[ orthogroup_id ] = composition_class
            if composition_class not in VALID_CLASSES:
                failures.append( f"Check 1: orthogroup {orthogroup_id} has invalid Composition_Class '{composition_class}'" )
            if composition_class == "non_bilaterian_only":
                composition_non_bilaterian_count += 1

    # ---- Table 2 ------------------------------------------------------------
    table2_row_count = 0
    with open( table2_path, 'r' ) as input_table2:
        header_ids___indices = U.build_header_index( input_table2.readline() )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        for line in input_table2:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            table2_row_count += 1
            orthogroup_id = parts[ index_og ]
            if orthogroups___classes.get( orthogroup_id ) != "non_bilaterian_only":
                failures.append( f"Check 2: Table 2 orthogroup {orthogroup_id} is not classified non_bilaterian_only in composition table" )

    if table2_row_count != composition_non_bilaterian_count:
        failures.append(
            f"Check 2: Table 2 row count ({table2_row_count}) != non_bilaterian_only count in composition table ({composition_non_bilaterian_count})"
        )

    # ---- Table 1 ------------------------------------------------------------
    table1_row_count = 0
    with open( table1_path, 'r' ) as input_table1:
        header_ids___indices = U.build_header_index( input_table1.readline() )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_member_count = header_ids___indices[ "Annogroup_Member_Protein_Count" ]
        index_with = header_ids___indices[ "Members_With_Orthogroup_Count" ]
        index_without = header_ids___indices[ "Members_Without_Orthogroup_Count" ]
        index_og_count = header_ids___indices[ "Orthogroup_Count" ]
        index_non_count = header_ids___indices[ "NonBilaterian_Only_Orthogroup_Count" ]
        index_bil_count = header_ids___indices[ "Bilaterian_Only_Orthogroup_Count" ]
        index_mixed_count = header_ids___indices[ "Mixed_Orthogroup_Count" ]
        index_non_ids = header_ids___indices[ "NonBilaterian_Only_Orthogroup_IDs" ]
        index_bil_ids = header_ids___indices[ "Bilaterian_Only_Orthogroup_IDs" ]
        index_mixed_ids = header_ids___indices[ "Mixed_Orthogroup_IDs" ]
        index_all_ids = header_ids___indices[ "All_Orthogroup_IDs" ]

        for line in input_table1:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            table1_row_count += 1
            annogroup_id = parts[ index_annogroup ]

            non_count = int( parts[ index_non_count ] )
            bil_count = int( parts[ index_bil_count ] )
            mixed_count = int( parts[ index_mixed_count ] )
            og_count = int( parts[ index_og_count ] )
            member_count = int( parts[ index_member_count ] )
            with_count = int( parts[ index_with ] )
            without_count = int( parts[ index_without ] )

            non_ids = split_cell( parts[ index_non_ids ] )
            bil_ids = split_cell( parts[ index_bil_ids ] )
            mixed_ids = split_cell( parts[ index_mixed_ids ] )
            all_ids = split_cell( parts[ index_all_ids ] )

            # Check 5: keep-rule
            if non_count < 1:
                failures.append( f"Check 5: annogroup {annogroup_id} retained with NonBilaterian_Only_Orthogroup_Count {non_count} (< 1)" )

            # Check 4: arithmetic
            if non_count + bil_count + mixed_count != og_count:
                failures.append( f"Check 4: annogroup {annogroup_id} class counts {non_count}+{bil_count}+{mixed_count} != Orthogroup_Count {og_count}" )
            if with_count + without_count != member_count:
                failures.append( f"Check 4: annogroup {annogroup_id} members {with_count}+{without_count} != Member_Protein_Count {member_count}" )
            if len( non_ids ) != non_count or len( bil_ids ) != bil_count or len( mixed_ids ) != mixed_count:
                failures.append( f"Check 4: annogroup {annogroup_id} ID-list lengths do not match per-class counts" )
            if len( all_ids ) != og_count:
                failures.append( f"Check 4: annogroup {annogroup_id} All_Orthogroup_IDs length {len( all_ids )} != Orthogroup_Count {og_count}" )

            # Check 3: referential integrity
            for orthogroup_id in all_ids:
                if orthogroup_id not in orthogroups___classes:
                    failures.append( f"Check 3: annogroup {annogroup_id} references orthogroup {orthogroup_id} absent from composition table" )

    # ---- report -------------------------------------------------------------
    output_dir = output_base / "4-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_report_path = output_dir / "4_ai-validation_report.txt"

    status = "PASS" if not failures else "FAIL"
    report_lines = [
        "=" * 78,
        "GIGANTIC integrator - annotations_X_orthogroups - VALIDATION REPORT",
        "=" * 78,
        "",
        f"Status: {status}",
        "",
        f"Orthogroups classified:            {len( orthogroups___classes )}",
        f"  non_bilaterian_only:             {composition_non_bilaterian_count}",
        f"Table 2 rows (non-bilaterian-only): {table2_row_count}",
        f"Table 1 rows (kept annogroups):    {table1_row_count}",
        "",
        f"Failures: {len( failures )}",
    ]
    for failure in failures[ :200 ]:
        report_lines.append( f"  - {failure}" )
    if len( failures ) > 200:
        report_lines.append( f"  ... and {len( failures ) - 200} more" )
    report_lines.extend( [ "", "=" * 78 ] )

    with open( output_report_path, 'w' ) as output_report:
        output_report.write( '\n'.join( report_lines ) + '\n' )

    print( f"[004] validation {status} -> {output_report_path}" )

    if failures:
        print( f"CRITICAL ERROR: validation FAILED with {len( failures )} issue(s). See {output_report_path}", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
