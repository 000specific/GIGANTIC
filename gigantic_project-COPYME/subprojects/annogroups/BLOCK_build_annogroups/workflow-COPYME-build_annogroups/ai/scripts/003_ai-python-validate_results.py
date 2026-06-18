#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 18 | Purpose: Validate one source's annogroup outputs (strict fail-fast, §36)
# Human: Eric Edsinger

"""
Script 003 — Validate annogroups for one source (strict fail-fast per §36).

Cross-checks the map + membership for internal consistency. ANY failure writes a
FAIL report and exits 1 (a silent annogroup artifact in a published product is a
research-integrity failure per AI_BEHAVIOR.md).

Checks:
  1. Every Annogroup_Type is one of {feature, combination, architecture, absent}.
  2. Per annogroup: map Sequence_Count == number of membership rows.
  3. combination partitions the annotated sequences — every sequence with >=1
     feature is in exactly ONE combination annogroup.
  4. architecture: every sequence carrying >=1 positional feature (i.e. every
     sequence with an architecture membership) is in exactly ONE architecture
     annogroup.
  5. absent ∪ annotated == universe, and absent ∩ annotated == ∅.
  6. Every membership Sequence_Identifier exists in the proteome universe.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_annogroups as U

VALID_TYPES = { "feature", "combination", "architecture", "absent" }


def main():
    parser = argparse.ArgumentParser( description = "Validate one source's annogroups (fail-fast)" )
    parser.add_argument( '--source', required = True )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    source = args.source
    output_base = Path( args.output_dir )
    map_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_map.tsv"
    membership_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_membership.tsv"
    universe_path = output_base / "1-output" / "1_ai-proteome_universe.tsv"

    for required in ( map_path, membership_path, universe_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required file not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    failures = []

    # ---- universe -----------------------------------------------------------
    universe = set()
    with open( universe_path, 'r' ) as input_universe:
        index = U.build_header_index( input_universe.readline() )[ "Sequence_Identifier" ]
        for line in input_universe:
            line = line.rstrip( '\n' )
            if line:
                universe.add( line.split( '\t' )[ index ] )

    # ---- map: annogroup -> ( type, sequence_count ) -------------------------
    annogroups___type = {}
    annogroups___declared_count = {}
    with open( map_path, 'r' ) as input_map:
        idx = U.build_header_index( input_map.readline() )
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ idx[ "Annogroup_ID" ] ]
            annogroup_type = parts[ idx[ "Annogroup_Type" ] ]
            annogroups___type[ annogroup_id ] = annogroup_type
            annogroups___declared_count[ annogroup_id ] = int( parts[ idx[ "Sequence_Count" ] ] )
            if annogroup_type not in VALID_TYPES:
                failures.append( f"Check 1: annogroup {annogroup_id} has invalid type '{annogroup_type}'" )

    # ---- membership ---------------------------------------------------------
    annogroups___observed_count = defaultdict( int )
    combination_membership_per_sequence = defaultdict( int )
    architecture_membership_per_sequence = defaultdict( int )
    annotated_from_feature = set()
    absent_members = set()
    missing_in_universe = 0

    with open( membership_path, 'r' ) as input_membership:
        idx = U.build_header_index( input_membership.readline() )
        i_seq = idx[ "Sequence_Identifier" ]
        i_ag = idx[ "Annogroup_ID" ]
        i_type = idx[ "Annogroup_Type" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence = parts[ i_seq ]
            annogroup_id = parts[ i_ag ]
            annogroup_type = parts[ i_type ]
            annogroups___observed_count[ annogroup_id ] += 1
            if sequence not in universe:
                missing_in_universe += 1
            if annogroup_type == "feature":
                annotated_from_feature.add( sequence )
            elif annogroup_type == "combination":
                combination_membership_per_sequence[ sequence ] += 1
            elif annogroup_type == "architecture":
                architecture_membership_per_sequence[ sequence ] += 1
            elif annogroup_type == "absent":
                absent_members.add( sequence )

    # Check 2: declared vs observed counts
    for annogroup_id, declared in annogroups___declared_count.items():
        observed = annogroups___observed_count.get( annogroup_id, 0 )
        if declared != observed:
            failures.append( f"Check 2: annogroup {annogroup_id} map count {declared} != membership rows {observed}" )

    # Check 3: combination partitions annotated sequences
    multi_combination = [ s for s, c in combination_membership_per_sequence.items() if c != 1 ]
    if multi_combination:
        failures.append( f"Check 3: {len( multi_combination )} sequences are in !=1 combination annogroup (e.g. {multi_combination[ :3 ]})" )
    if set( combination_membership_per_sequence ) != annotated_from_feature:
        only_comb = len( set( combination_membership_per_sequence ) - annotated_from_feature )
        only_feat = len( annotated_from_feature - set( combination_membership_per_sequence ) )
        failures.append( f"Check 3: combination set != feature-annotated set (comb-only={only_comb}, feature-only={only_feat})" )

    # Check 4: architecture is one-per-sequence for sequences that have one
    multi_architecture = [ s for s, c in architecture_membership_per_sequence.items() if c != 1 ]
    if multi_architecture:
        failures.append( f"Check 4: {len( multi_architecture )} sequences are in !=1 architecture annogroup (e.g. {multi_architecture[ :3 ]})" )

    # Check 5: absent ∪ annotated == universe, disjoint
    if absent_members & annotated_from_feature:
        failures.append( f"Check 5: {len( absent_members & annotated_from_feature )} sequences are BOTH absent and feature-annotated" )
    if absent_members | annotated_from_feature != universe:
        missing = len( universe - ( absent_members | annotated_from_feature ) )
        extra = len( ( absent_members | annotated_from_feature ) - universe )
        failures.append( f"Check 5: absent ∪ annotated != universe (universe-not-covered={missing}, outside-universe={extra})" )

    # Check 6
    if missing_in_universe:
        failures.append( f"Check 6: {missing_in_universe} membership rows reference a sequence absent from the universe" )

    # ---- report -------------------------------------------------------------
    output_dir = output_base / "3-output" / source
    output_dir.mkdir( parents = True, exist_ok = True )
    report_path = output_dir / f"3_ai-{source}-validation_report.txt"

    status = "PASS" if not failures else "FAIL"
    lines = [
        "=" * 78,
        f"GIGANTIC annogroups - VALIDATION REPORT - source: {source}",
        "=" * 78, "",
        f"Status: {status}", "",
        f"Universe sequences:        {len( universe )}",
        f"Feature-annotated:         {len( annotated_from_feature )}",
        f"Absent:                    {len( absent_members )}",
        f"Annogroups (all types):    {len( annogroups___type )}", "",
        f"Failures: {len( failures )}",
    ]
    for failure in failures[ :200 ]:
        lines.append( f"  - {failure}" )
    lines.extend( [ "", "=" * 78 ] )
    with open( report_path, 'w' ) as output_report:
        output_report.write( '\n'.join( lines ) + '\n' )

    print( f"[003 {source}] validation {status} -> {report_path}" )
    if failures:
        print( f"CRITICAL ERROR: validation FAILED ({len( failures )} issue(s)). See {report_path}", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
