#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 28 | Purpose: Auto-bridge toolkit output -> GIGANTIC INPUT_user/genomic_resources via two-hop relative symlinks. Sandbox -> staging arena per gigantic_conventions.md §17, §18.
# Human: Eric Edsinger

"""
004_ai-python-bridge_to_input_user.py

After script 003 produces GIGANTIC-conformant files in this run's
OUTPUT_pipeline/3-output/, this script does the staging-arena bridging that
gigantic_conventions.md §17 and §18 require for outside data to be visible
to GIGANTIC subprojects (genomesDB STEP_1, etc.).

Two-hop symlink chain:

    research_notebook/research_ai/subproject-<X>/<toolkit_name>/toolkit-RUN_*/OUTPUT_pipeline/3-output/<subdir>/<file>
                                                  ^
                                                  | (real files written by script 003)
                                                  |
    research_notebook/research_ai/subproject-<X>/<toolkit_name>/output_to_input/<subdir>/<file>
                                                  ^
                                                  | (RUN-stable symlink; this script writes)
                                                  | (parent's output_to_input/ exposes the
                                                  |  toolkit's current run to downstream
                                                  |  sandbox tooling and to INPUT_user)
                                                  |
    INPUT_user/genomic_resources/<dest_subdir>/<file>
                                                  (project-level staging arena symlink;
                                                   this script writes; GIGANTIC subprojects
                                                   read from here)

Subdir mapping (toolkit -> INPUT_user/genomic_resources/):
    T1_proteomes     ->  proteomes
    genomes          ->  genomes
    gene_annotations ->  annotations
    maps             ->  (parent only; not bridged to INPUT_user)

Symlinks are RELATIVE per §18 (`os.path.relpath`-based), so the entire project
survives `mv` / archival / copy-to-new-machine without breakage.

Idempotent: pre-existing symlinks are atomically replaced. Real files at
target paths are NEVER overwritten -- the script aborts with a clear error.

Usage:
    python3 004_ai-python-bridge_to_input_user.py \\
        --run-3-output-dir <abs_path_to_this_run's_3-output> \\
        --parent-output-to-input-dir <abs_path_to_toolkit_parent's_output_to_input> \\
        --input-user-genomic-resources-dir <abs_path_to_INPUT_user/genomic_resources>
"""

import argparse
import os
import sys
import logging
from pathlib import Path


# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s | %(levelname)s | %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger( __name__ )


# ============================================================================
# Subdir mapping: toolkit-side name -> (parent output_to_input name, INPUT_user destination name OR None)
# ============================================================================
# `None` for the INPUT_user destination means "expose at parent's output_to_input
# only; do not bridge to INPUT_user." (Used for maps, which are toolkit-side
# audit artifacts not consumed by GIGANTIC genomic-resources subprojects.)

SUBDIR_MAPPING = [
    ( 'T1_proteomes',     'T1_proteomes',     'proteomes' ),
    ( 'genomes',          'genomes',          'genomes' ),
    ( 'gene_annotations', 'gene_annotations', 'annotations' ),
    ( 'maps',             'maps',             None ),
]


# ============================================================================
# Symlink helpers
# ============================================================================

def create_relative_symlink( source_path, link_path ):
    """
    Create a relative symlink at link_path pointing to source_path.

    Atomic replace: if link_path already exists AS A SYMLINK, it is unlinked
    and recreated. If link_path is a real file or directory, raise to avoid
    silent data destruction.

    Parameters:
        source_path (Path): The thing the symlink will point at (absolute or relative).
        link_path (Path):   Where the symlink will live.

    Returns:
        str: The relative path that was written into the symlink.
    """

    if link_path.is_symlink():
        link_path.unlink()
    elif link_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite non-symlink at {link_path} "
            f"(might be real data). Resolve manually."
        )

    relative_target = os.path.relpath( source_path, link_path.parent )
    link_path.symlink_to( relative_target )

    return relative_target


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description = "Bridge toolkit output to GIGANTIC INPUT_user via two-hop relative symlinks."
    )
    # WHY two paths per subdir, not one? NextFlow's publishDir is async: when
    # process 4 starts, the work-dir-staged inputs (channel-dependent) are
    # guaranteed complete, but the published OUTPUT_pipeline/3-output/ may
    # still be mid-copy. Enumerate from the *-staged dir for the file list;
    # point symlinks at the *-published path (stable, post-completion).
    parser.add_argument( '--t1-proteomes-staged',     required = True )
    parser.add_argument( '--genomes-staged',          required = True )
    parser.add_argument( '--gene-annotations-staged', required = True )
    parser.add_argument( '--maps-staged',             required = True )
    parser.add_argument( '--published-3-output-dir',  required = True,
                         help = "OUTPUT_pipeline/3-output where symlinks should point (stable, post-publish)." )
    parser.add_argument( '--parent-output-to-input-dir', required = True,
                         help = "Toolkit parent's output_to_input directory (where stable symlinks point at this RUN)." )
    parser.add_argument( '--input-user-genomic-resources-dir', required = True,
                         help = "Project-level INPUT_user/genomic_resources directory (GIGANTIC's staging arena)." )
    arguments = parser.parse_args()

    # Map toolkit_subdir -> staged path (for enumeration only)
    staged_paths_by_subdir = {
        'T1_proteomes':     Path( arguments.t1_proteomes_staged ).resolve(),
        'genomes':          Path( arguments.genomes_staged ).resolve(),
        'gene_annotations': Path( arguments.gene_annotations_staged ).resolve(),
        'maps':             Path( arguments.maps_staged ).resolve(),
    }
    published_3_output = Path( arguments.published_3_output_dir ).resolve()
    parent_oti_dir     = Path( arguments.parent_output_to_input_dir ).resolve()
    input_user_gr_dir  = Path( arguments.input_user_genomic_resources_dir ).resolve()

    print( '============================================' )
    print( '004: Bridge to INPUT_user' )
    print( '============================================' )
    print( '' )
    print( f'Published 3-output (symlink target base):  {published_3_output}' )
    print( f'Parent output_to_input:                    {parent_oti_dir}' )
    print( f'INPUT_user/genomic_resources:              {input_user_gr_dir}' )
    print( '' )

    # ------------------------------------------------------------------------
    # Ensure target dirs exist
    # ------------------------------------------------------------------------
    if not parent_oti_dir.is_dir():
        logger.info( f'Creating parent output_to_input dir: {parent_oti_dir}' )
        parent_oti_dir.mkdir( parents = True, exist_ok = True )
    if not input_user_gr_dir.is_dir():
        logger.info( f'Creating INPUT_user/genomic_resources dir: {input_user_gr_dir}' )
        input_user_gr_dir.mkdir( parents = True, exist_ok = True )

    # ------------------------------------------------------------------------
    # Hop A: parent output_to_input/<subdir>/  ->  published 3-output/<subdir>/
    # Hop B: INPUT_user/genomic_resources/<dest>/  ->  parent output_to_input/<subdir>/
    # ------------------------------------------------------------------------
    parent_linked_count = 0
    input_user_linked_count = 0
    skipped_subdirs = []

    for toolkit_subdir, parent_subdir, input_user_subdir in SUBDIR_MAPPING:

        staged_path = staged_paths_by_subdir[ toolkit_subdir ]
        if not staged_path.is_dir():
            skipped_subdirs.append( ( toolkit_subdir, f'staged path not found: {staged_path}' ) )
            continue

        # Enumerate from the work-dir staged path (guaranteed populated by
        # channel dependency from process 3).
        files_in_subdir = sorted( staged_path.iterdir() )
        if not files_in_subdir:
            skipped_subdirs.append( ( toolkit_subdir, 'directory present but empty' ) )
            continue

        # ---- Hop A: parent output_to_input -> published 3-output (NOT the staged work dir) ----
        parent_subdir_path = parent_oti_dir / parent_subdir
        parent_subdir_path.mkdir( parents = True, exist_ok = True )

        published_source_subdir = published_3_output / toolkit_subdir

        print( f'--- {toolkit_subdir} ({len( files_in_subdir )} files) ---' )
        for staged_file in files_in_subdir:
            # Symlink target = stable published path (NOT the ephemeral work-dir staging)
            symlink_source = published_source_subdir / staged_file.name
            link_path = parent_subdir_path / staged_file.name
            relative_target = create_relative_symlink( symlink_source, link_path )
            print( f'  [parent_oti] {link_path.name} -> {relative_target}' )
            parent_linked_count += 1

        # ---- Hop B: INPUT_user/genomic_resources -> parent output_to_input ----
        if input_user_subdir is None:
            print( f'  (no INPUT_user bridge for {toolkit_subdir} -- parent-only)' )
            print( '' )
            continue

        input_user_subdir_path = input_user_gr_dir / input_user_subdir
        input_user_subdir_path.mkdir( parents = True, exist_ok = True )

        # Enumerate the parent_oti symlinks we just created; point INPUT_user at them.
        # This keeps Hop B stable across re-runs (only Hop A needs to re-point).
        for parent_link in sorted( parent_subdir_path.iterdir() ):
            link_path = input_user_subdir_path / parent_link.name
            relative_target = create_relative_symlink( parent_link, link_path )
            print( f'  [INPUT_user] {link_path.name} -> {relative_target}' )
            input_user_linked_count += 1

        print( '' )

    # ------------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------------
    print( '============================================' )
    print( 'Bridge complete' )
    print( '============================================' )
    print( '' )
    print( f'Parent output_to_input symlinks: {parent_linked_count}' )
    print( f'INPUT_user/genomic_resources symlinks: {input_user_linked_count}' )

    if skipped_subdirs:
        print( '' )
        print( 'Skipped subdirs:' )
        for subdir, reason in skipped_subdirs:
            print( f'  - {subdir}: {reason}' )

    print( '' )

    # Fail-fast per §36: if no symlinks were created at all, something's wrong.
    if parent_linked_count == 0:
        logger.error( 'CRITICAL: No symlinks created. RUN 3-output dir appears empty.' )
        sys.exit( 1 )

    print( 'Done.' )


if __name__ == '__main__':
    main()
