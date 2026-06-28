#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: Resolve which species-tree structures to materialize (explicit list or "all") and fail-fast verify their OCL inputs exist
# Human: Eric Edsinger

"""
Script 000 — Resolve the species-tree structure set for the per-structure fan-out.

The user configures `structures` in START_HERE-user_config.yaml as either:
  - the literal string "all"  -> every structure produced by the orthogroups OCL
                                  run is materialized, OR
  - a list, e.g. [ "structure_001", "structure_003", "structure_032", ... ]

This script writes the resolved structure names (one per line) to the path given
by --output_list (NextFlow consumes it as a channel via .splitText()). For every
resolved structure it fail-fast verifies BOTH required OCL summaries exist:
  - orthogroups OCL : <orthogroups_ocl_dir>/<run_label>/<structure>/4_ai-orthogroups-complete_ocl_summary.tsv
  - annogroup OCL   : <annogroup_ocl_dir>/<run_label>/<structure>/4_ai-structure_<NNN>_annogroups-complete_ocl_summary-all_types.tsv

A missing OCL summary for a requested structure is an error (exit 1) — we never
silently materialize a structure whose evolutionary inference is absent.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_species_X_all_annotations as U


def orthogroups_ocl_summary_path( orthogroups_ocl_run_dir: Path, structure: str ) -> Path:
    return orthogroups_ocl_run_dir / structure / "4_ai-orthogroups-complete_ocl_summary.tsv"


def annogroup_ocl_summary_path( annogroup_ocl_run_dir: Path, structure: str ) -> Path:
    structure_number = structure.replace( "structure_", "" )
    return annogroup_ocl_run_dir / structure / f"4_ai-structure_{structure_number}_annogroups-complete_ocl_summary-all_types.tsv"


def main():
    parser = argparse.ArgumentParser( description = "Resolve the species-tree structure set (fail-fast)" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    parser.add_argument( '--output_list', required = True, help = "Where to write the resolved structure list (one per line)" )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    orthogroups_ocl_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "orthogroups_ocl_dir" ] )
    annogroup_ocl_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "annogroup_ocl_dir" ] )
    orthogroups_ocl_run_label = config[ "orthogroups_ocl_run_label" ]
    annogroup_ocl_run_label = config[ "annogroup_ocl_run_label" ]

    orthogroups_ocl_run_dir = orthogroups_ocl_dir / orthogroups_ocl_run_label
    annogroup_ocl_run_dir = annogroup_ocl_dir / annogroup_ocl_run_label

    if not orthogroups_ocl_run_dir.is_dir():
        print( f"CRITICAL ERROR: orthogroups OCL run directory not found: {orthogroups_ocl_run_dir}", file = sys.stderr )
        print( "  Check inputs.orthogroups_ocl_dir and orthogroups_ocl_run_label.", file = sys.stderr )
        sys.exit( 1 )

    structures_setting = config[ "structures" ]

    # Resolve the requested structures.
    if isinstance( structures_setting, str ) and structures_setting.strip().lower() == "all":
        structures = sorted(
            path.name for path in orthogroups_ocl_run_dir.iterdir()
            if path.is_dir() and path.name.startswith( "structure_" )
        )
        if not structures:
            print( f"CRITICAL ERROR: structures='all' but no structure_* dirs under {orthogroups_ocl_run_dir}", file = sys.stderr )
            sys.exit( 1 )
        print( f"[000] structures='all' -> {len( structures )} structures discovered" )
    elif isinstance( structures_setting, list ):
        structures = [ str( structure ).strip() for structure in structures_setting if str( structure ).strip() ]
        if not structures:
            print( "CRITICAL ERROR: structures list is empty", file = sys.stderr )
            sys.exit( 1 )
        print( f"[000] explicit structures list -> {structures}" )
    else:
        print( f"CRITICAL ERROR: 'structures' must be the string 'all' or a list; got: {structures_setting!r}", file = sys.stderr )
        sys.exit( 1 )

    # Fail-fast: BOTH OCL summaries must exist for every requested structure.
    missing = []
    for structure in structures:
        orthogroups_summary = orthogroups_ocl_summary_path( orthogroups_ocl_run_dir, structure )
        annogroup_summary = annogroup_ocl_summary_path( annogroup_ocl_run_dir, structure )
        if not orthogroups_summary.is_file():
            missing.append( f"orthogroups OCL summary missing for {structure}: {orthogroups_summary}" )
        if not annogroup_summary.is_file():
            missing.append( f"annogroup OCL summary missing for {structure}: {annogroup_summary}" )

    if missing:
        print( f"CRITICAL ERROR: {len( missing )} required OCL input(s) missing — refusing to materialize structures with absent evolutionary inference:", file = sys.stderr )
        for item in missing:
            print( f"  - {item}", file = sys.stderr )
        print( "  Run the ocl_phylogenetic_structures OCL workflows for these structures, or adjust the 'structures' list.", file = sys.stderr )
        sys.exit( 1 )

    output_list_path = Path( args.output_list )
    output = '\n'.join( structures ) + '\n'
    with open( output_list_path, 'w' ) as output_structures:
        output_structures.write( output )

    print( f"[000] resolved {len( structures )} structure(s) -> {output_list_path}" )


if __name__ == '__main__':
    main()
