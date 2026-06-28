#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 20 | Purpose: Shared helper — assembles nested upload_to_server/ tree from per-workflow manifests
# Human: Eric Edsinger

"""
GIGANTIC upload_to_server/ builder (drill-down edition)

Walks a subproject, finds every `upload_manifest.tsv` inside any workflow-RUN_*
directory, and materializes the manifest-described files as symlinks into
`<subproject>/upload_to_server/`.

The directory structure under `upload_to_server/` mirrors the source path:
  <subproject>/
    gene_family-<X>/STEP_<N>/workflow-RUN_<K>/OUTPUT_pipeline/<M>-output/<file>
                |            |                                 |
                v            v                                 v
  upload_to_server/
    <X>/                    <- "gene_family-" prefix stripped
      STEP_<N>/
        workflow-RUN_<K>/   <- full RUN name preserved
          <M>-output/       <- OUTPUT_pipeline/ layer collapsed out
            <file>

For subprojects without a family layer (annotations_hmms, phylonames, etc.)
the path is shorter but the same rule applies.

A sidecar `.section_metadata.tsv` is written next to each group of published
files so the server can pick up display_label / file_category / description /
order without re-parsing the manifest.

Usage:
    python3 update_upload_to_server.py --subproject-dir /path/to/subproject [OPTIONS]

Options:
    --dry-run     Report actions without writing anything
    --clean       Recursive cleanup of stale symlinks AND empty directories
    --strict      Turn warnings into errors (for CI)
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# Manifest parsing
# ============================================================================

MANIFEST_FILENAME = 'upload_manifest.tsv'
SIDECAR_FILENAME = '.section_metadata.tsv'
STATE_FILENAME = '.upload_state.tsv'

# Required and optional columns
REQUIRED_COLUMNS = [ 'source_path', 'include' ]
KNOWN_COLUMNS = [
    'source_path', 'include', 'dest_name',
    'display_label', 'file_category', 'description', 'order', 'dir_label',
]

# Reserved sidecar row whose 'description' carries a label for the directory
# ITSELF (rendered by the server as a folder subtitle), as opposed to a file.
# Not a real filename — never matches anything on disk.
DIR_LABEL_KEY = '__DIR__'


class ManifestParseError( Exception ):
    pass


class ManifestEntry:
    __slots__ = (
        'source_path', 'include',
        'dest_name', 'display_label', 'file_category',
        'description', 'order', 'dir_label',
    )

    def __init__( self, row: Dict[ str, str ] ):
        self.source_path = row.get( 'source_path', '' ).strip()
        self.include = row.get( 'include', '' ).strip().lower()
        self.dest_name = row.get( 'dest_name', '' ).strip()
        self.display_label = row.get( 'display_label', '' ).strip()
        self.file_category = row.get( 'file_category', '' ).strip()
        self.description = row.get( 'description', '' ).strip()
        # Short descriptor for the destination FOLDER the file lands in
        # (e.g. "AGS sequences"). Rendered by the server as a folder subtitle.
        self.dir_label = row.get( 'dir_label', '' ).strip()
        try:
            self.order = int( row.get( 'order', '100' ) or '100' )
        except ValueError:
            self.order = 100


def parse_manifest( manifest_path: Path, strict: bool = False ) -> List[ ManifestEntry ]:
    """Parse a manifest TSV. Returns list of ManifestEntry (include == 'yes' only)."""
    if not manifest_path.exists():
        return []

    entries = []
    header = None

    with open( manifest_path, 'r' ) as f:
        for line_number, line in enumerate( f, 1 ):
            line = line.rstrip( '\n' )
            if not line.strip() or line.lstrip().startswith( '#' ):
                continue

            parts = line.split( '\t' )

            if header is None:
                header = [ h.strip() for h in parts ]
                for required in REQUIRED_COLUMNS:
                    if required not in header:
                        raise ManifestParseError(
                            f"{manifest_path}: missing required column '{required}' "
                            f"(have {header})"
                        )
                continue

            if len( parts ) < len( header ):
                parts = parts + [ '' ] * ( len( header ) - len( parts ) )

            row = dict( zip( header, parts ) )
            entry = ManifestEntry( row )

            if entry.include == '':
                continue
            if entry.include not in ( 'yes', 'no' ):
                msg = ( f"{manifest_path}:{line_number}: invalid include value '{entry.include}' "
                        f"(must be 'yes' or 'no')" )
                if strict:
                    raise ManifestParseError( msg )
                print( f"  WARN: {msg}" )
                continue

            if entry.include == 'yes' and entry.source_path:
                entries.append( entry )

    return entries


# ============================================================================
# Destination path derivation
# ============================================================================

# Patterns to collapse / strip when mapping source paths to upload paths.
# Order matters: most-specific first.

def manifest_to_dest_prefix( manifest_dir: Path, subproject_dir: Path ) -> Path:
    """
    Given the directory containing a manifest (always a workflow-RUN_* dir),
    return the destination prefix path under upload_to_server/.

    Rules:
      gene_family-<X>     -> <X>                       (strip the 'gene_family-' prefix)
      gene_group-<X>      -> <X>                       (strip the 'gene_group-' prefix)
      STEP_<N>-<name>     -> STEP_<N>-<name>           (preserve)
      BLOCK_<name>        -> BLOCK_<name>              (preserve)
      workflow-RUN_<K>-*  -> workflow-RUN_<K>-*        (preserve)
      workflow-COPYME-*   -> skip (not a RUN)

    Any 'gene_groups-<set>/' top-level dir inside the subproject is also stripped
    (becomes the first hierarchy level without the 'gene_groups-' prefix).
    """
    rel = manifest_dir.relative_to( subproject_dir )
    out_parts = []
    for part in rel.parts:
        if part.startswith( 'gene_family-' ):
            out_parts.append( part[ len( 'gene_family-' ): ] )
        elif part.startswith( 'gene_group-' ):
            out_parts.append( part[ len( 'gene_group-' ): ] )
        elif part.startswith( 'gene_groups-' ):
            out_parts.append( part[ len( 'gene_groups-' ): ] )
        else:
            out_parts.append( part )
    return Path( *out_parts )


# ============================================================================
# Disambiguate identical link names within a section
# ============================================================================

def disambiguate_display_labels( rows_by_filename: Dict[ str, Dict[ str, str ] ] ) -> None:
    """
    When several files in one section share the same display_label, the server
    would show identical link names with no way to tell them apart. This appends
    each file's distinguishing token to its display_label in place.

    The distinguisher is the filename stem with the group's longest common prefix
    removed (the prefix is trimmed back to the last '-' so it starts at a clean
    token) — e.g. 'Annogroup tree counts — per structure' becomes
    '... — structure_017', and a composite detail label becomes
    '... — cc_Bilateria-exact'. Labels that are already unique (including manifests
    that disambiguate explicitly via {structure}/{stem} placeholders) are left
    untouched.
    """
    label___rows: Dict[ str, List[ Dict[ str, str ] ] ] = {}
    for filename, row in rows_by_filename.items():
        if filename == DIR_LABEL_KEY:
            continue
        label = row.get( 'display_label', '' )
        if not label:
            continue
        label___rows.setdefault( label, [] ).append( row )

    for label, group in label___rows.items():
        if len( group ) < 2:
            continue
        stems = [ Path( row[ 'filename' ] ).stem for row in group ]
        common_prefix = stems[ 0 ]
        for stem in stems[ 1: ]:
            limit = min( len( common_prefix ), len( stem ) )
            cut = 0
            while cut < limit and common_prefix[ cut ] == stem[ cut ]:
                cut += 1
            common_prefix = common_prefix[ :cut ]
        # Trim the common prefix back to the last '-' so the disambiguator starts
        # at a clean token (keep 'structure_001', 'cc_Bilateria-exact', etc.).
        last_dash = common_prefix.rfind( '-' )
        if last_dash >= 0:
            common_prefix = common_prefix[ :last_dash + 1 ]
        for row, stem in zip( group, stems ):
            disambiguator = stem[ len( common_prefix ): ] or stem
            row[ 'display_label' ] = f"{label} — {disambiguator}"


# ============================================================================
# Apply a single manifest
# ============================================================================

def apply_manifest( manifest_path: Path,
                    subproject_dir: Path,
                    upload_dir: Path,
                    dry_run: bool,
                    strict: bool ):
    """
    Process one manifest. Creates symlinks and sidecar metadata.

    Returns:
        ( files_linked, warnings, kept_paths )
        kept_paths is the set of absolute dest file Paths this manifest
        authoritatively produced (or would produce in dry_run). Used by
        the caller to prune stale symlinks that no longer appear in any
        manifest (e.g. when a line is flipped yes → no).
    """
    manifest_dir = manifest_path.parent  # workflow-RUN_* directory

    # Dest prefix under upload_to_server/
    dest_prefix_rel = manifest_to_dest_prefix( manifest_dir, subproject_dir )

    try:
        entries = parse_manifest( manifest_path, strict = strict )
    except ManifestParseError as e:
        print( f"  ERROR: {e}" )
        return ( 0, 1, set() )

    if not entries:
        return ( 0, 0, set() )

    print( f"  MANIFEST: {manifest_path.relative_to( subproject_dir )}" )
    print( f"    -> dest prefix: {dest_prefix_rel}" )

    files_linked = 0
    warnings = 0
    kept_paths = set()

    # Group per-destination-directory so we can write one sidecar per dir
    dir_to_metadata: Dict[ Path, List[ Dict[ str, str ] ] ] = {}
    # Per-destination-directory folder label (from manifest dir_label column)
    dir_to_label: Dict[ Path, str ] = {}

    for entry in entries:
        # source_path is relative to manifest_dir
        pattern_abs = ( manifest_dir / entry.source_path ).as_posix()
        matches = sorted( glob( pattern_abs ) )

        if not matches:
            # Missing-file warnings are the common case (method not run, file not produced yet).
            # Only report them in strict mode; otherwise just count silently.
            if strict:
                msg = f"    WARN: no files match '{entry.source_path}' (searched in {manifest_dir})"
                print( f"  STRICT FAIL: {msg}" )
                raise ManifestParseError( msg )
            warnings += 1
            continue

        # Derive the destination subdirectory from the source file's position
        # within manifest_dir (preserves OUTPUT_pipeline/N-output/ but collapses OUTPUT_pipeline)
        for src_str in matches:
            src_path = Path( src_str )
            if not src_path.is_file() and not src_path.is_symlink():
                continue

            rel_inside_manifest_dir = src_path.relative_to( manifest_dir )
            # Collapse OUTPUT_pipeline/ if present
            collapsed_parts = [ p for p in rel_inside_manifest_dir.parts if p != 'OUTPUT_pipeline' ]
            # The final filename; everything before = dest subdir relative to dest_prefix
            dest_filename = entry.dest_name if entry.dest_name else collapsed_parts[ -1 ]
            dest_subdir_parts = collapsed_parts[ :-1 ]
            dest_dir_rel = dest_prefix_rel / Path( *dest_subdir_parts ) if dest_subdir_parts else dest_prefix_rel

            full_dest_dir = upload_dir / dest_dir_rel
            full_dest_file = full_dest_dir / dest_filename

            # Track authoritative dest paths so stale links can be pruned later.
            # include=no lines don't reach this point, so kept_paths is exactly
            # the set of symlink paths this manifest asks to publish.
            kept_paths.add( full_dest_file )

            # Record the folder label. It belongs to the N-output directory
            # (e.g. "4-output"), NOT to a deeper subdir a file may sit in
            # (e.g. "4-output/species64_.../"). Walk the dest subdirs to find
            # the N-output component and attach the label there. If the file is
            # not under an N-output dir, the label is ignored (by convention
            # only N-output folders carry subtitles).
            if entry.dir_label:
                output_idx = None
                for i, part in enumerate( dest_subdir_parts ):
                    if re.fullmatch( r'\d+(?:_[a-z])?-output', part ):
                        output_idx = i
                if output_idx is not None:
                    n_output_dir = upload_dir / dest_prefix_rel / Path( *dest_subdir_parts[ : output_idx + 1 ] )
                    prev_label = dir_to_label.get( n_output_dir )
                    if prev_label is None:
                        dir_to_label[ n_output_dir ] = entry.dir_label
                    elif prev_label != entry.dir_label:
                        print( f"    WARN: conflicting dir_label for "
                               f"{n_output_dir.name}: '{prev_label}' vs "
                               f"'{entry.dir_label}' (keeping '{prev_label}')" )
                        warnings += 1

            if dry_run:
                print( f"    [DRY] would link {full_dest_file.relative_to( upload_dir )} -> {src_path}" )
            else:
                full_dest_dir.mkdir( parents = True, exist_ok = True )
                # Remove existing file/symlink at that spot
                if full_dest_file.exists() or full_dest_file.is_symlink():
                    full_dest_file.unlink()
                full_dest_file.symlink_to( src_path )
                files_linked += 1

            # Expand per-file placeholders in display_label and description.
            # Supported tokens (only relevant when one manifest entry's glob
            # matches multiple files and you want each file disambiguated):
            #   {stem}        — dest_filename minus the final extension
            #                   e.g.  3_ai-genome_summary-Homo_sapiens
            #   {descriptor}  — text after the last '-' in {stem}
            #                   e.g.  Homo_sapiens
            # Manifests without placeholders are unchanged.
            stem = Path( dest_filename ).stem
            descriptor = stem.rsplit( '-', 1 )[ -1 ] if '-' in stem else stem
            # {structure} = "structure_NNN" if present anywhere in the stem, else empty.
            structure_match = re.search( r'(structure_\d+)', stem )
            structure_token = structure_match.group( 1 ) if structure_match else ''
            placeholders = { 'stem': stem, 'descriptor': descriptor, 'structure': structure_token }
            display_label_expanded = entry.display_label
            description_expanded = entry.description
            for token, value in placeholders.items():
                display_label_expanded = display_label_expanded.replace( '{' + token + '}', value )
                description_expanded = description_expanded.replace( '{' + token + '}', value )

            # Record metadata for sidecar
            dir_to_metadata.setdefault( full_dest_dir, [] ).append( {
                'filename': dest_filename,
                'display_label': display_label_expanded,
                'file_category': entry.file_category,
                'description': description_expanded,
                'order': str( entry.order ),
            } )

    # Write sidecars (one per dest dir touched, plus any N-output dir that only
    # received a folder label because its files live in subdirectories).
    if not dry_run:
        sidecar_dirs = set( dir_to_metadata.keys() ) | set( dir_to_label.keys() )
        for target_dir in sidecar_dirs:
            rows = dir_to_metadata.get( target_dir, [] )
            sidecar_path = target_dir / SIDECAR_FILENAME
            # Merge with existing sidecar if present (preserve entries from OTHER manifests)
            existing: Dict[ str, Dict[ str, str ] ] = {}
            if sidecar_path.exists():
                try:
                    with open( sidecar_path, 'r' ) as f:
                        hdr = None
                        for ln in f:
                            ln = ln.rstrip( '\n' )
                            if not ln.strip() or ln.lstrip().startswith( '#' ):
                                continue
                            parts = ln.split( '\t' )
                            if hdr is None:
                                hdr = parts
                                continue
                            row = dict( zip( hdr, parts ) )
                            fname = row.get( 'filename', '' )
                            if fname:
                                existing[ fname ] = row
                except Exception:
                    existing = {}

            for row in rows:
                existing[ row[ 'filename' ] ] = row

            # Folder label: store as a reserved __DIR__ row so the server can
            # render it as a subtitle on the folder card. order=0 sorts it first.
            # Drop any pre-existing __DIR__ first so a stale/misplaced label from
            # an earlier run is cleared; re-add only if this dir is labeled now.
            existing.pop( DIR_LABEL_KEY, None )
            if target_dir in dir_to_label:
                existing[ DIR_LABEL_KEY ] = {
                    'filename': DIR_LABEL_KEY,
                    'display_label': '',
                    'file_category': '',
                    'description': dir_to_label[ target_dir ],
                    'order': '0',
                }

            # Disambiguate identical link names within this section (e.g. the 105
            # per-structure files, or the per-composite-clade detail tables).
            disambiguate_display_labels( existing )

            header_cols = [ 'filename', 'display_label', 'file_category', 'description', 'order' ]
            with open( sidecar_path, 'w' ) as f:
                f.write( '# GIGANTIC server section metadata — auto-generated; do not edit\n' )
                f.write( '\t'.join( header_cols ) + '\n' )
                for fname in sorted( existing.keys() ):
                    r = existing[ fname ]
                    f.write( '\t'.join( r.get( col, '' ) for col in header_cols ) + '\n' )

    return ( files_linked, warnings, kept_paths )


# ============================================================================
# Cleanup
# ============================================================================

def prune_stale_symlinks( upload_dir: Path, kept_paths: set, dry_run: bool ) -> int:
    """
    Remove symlinks under upload_dir that are NOT in `kept_paths` (the
    authoritative set just produced by every manifest this run). This handles
    the yes → no case: flipping a manifest entry off actually removes the
    previously-published symlink instead of leaving it orphaned.

    Sidecar (.section_metadata.tsv) and state files are left alone here —
    broken-symlink + empty-dir cleanup runs after and prunes their dirs when
    they become empty. The sidecars are rewritten per-run by apply_manifest.

    Returns:
        count of stale symlinks removed
    """
    removed = 0
    # Walk every file/symlink currently under upload_dir
    for root, dirnames, filenames in _walk_bottom_up( upload_dir ):
        root_path = Path( root )
        for fname in filenames:
            if fname in ( SIDECAR_FILENAME, STATE_FILENAME ):
                continue
            current = root_path / fname
            if not current.is_symlink():
                continue
            if current in kept_paths:
                continue
            # Stale — manifest no longer asks for this file to be published
            if dry_run:
                print( f"    [DRY] would remove stale symlink: {current.relative_to( upload_dir )}" )
            else:
                try:
                    current.unlink()
                    removed += 1
                except OSError:
                    pass
    return removed


def prune_sidecar_entries( upload_dir: Path, dry_run: bool ):
    """
    After stale symlinks are pruned, walk every sidecar and drop entries whose
    `filename` no longer exists in the dir. Keeps sidecars consistent with the
    files actually present, so the server doesn't list dead entries.
    """
    if dry_run:
        return
    for root, dirnames, filenames in _walk_bottom_up( upload_dir ):
        if SIDECAR_FILENAME not in filenames:
            continue
        root_path = Path( root )
        sidecar_path = root_path / SIDECAR_FILENAME
        try:
            with open( sidecar_path, 'r' ) as f:
                lines = f.readlines()
        except OSError:
            continue
        kept_lines = []
        hdr_written = False
        for ln in lines:
            stripped = ln.rstrip( '\n' )
            if not stripped.strip() or stripped.lstrip().startswith( '#' ):
                kept_lines.append( ln )
                continue
            parts = stripped.split( '\t' )
            if not hdr_written:
                kept_lines.append( ln )
                hdr_written = True
                hdr = parts
                continue
            row = dict( zip( hdr, parts ) )
            fname = row.get( 'filename', '' )
            # Keep the reserved folder-label row (it has no on-disk file) and
            # any row whose file is still present.
            if fname == DIR_LABEL_KEY or ( fname and ( root_path / fname ).exists() ):
                kept_lines.append( ln )
        try:
            with open( sidecar_path, 'w' ) as f:
                f.writelines( kept_lines )
        except OSError:
            pass


def clean_upload_dir( upload_dir: Path, dry_run: bool ) -> Tuple[ int, int ]:
    """
    Recursively remove broken symlinks and empty directories under upload_to_server/.

    Returns:
        ( broken_links_removed, empty_dirs_removed )
    """
    broken = 0
    empty_dirs = 0

    # Walk bottom-up so we can prune empty dirs after deleting stale links
    all_paths = []
    for root, dirnames, filenames in _walk_bottom_up( upload_dir ):
        for fname in filenames:
            all_paths.append( Path( root ) / fname )

    # 1. Remove broken symlinks + sidecar / state files that reference nothing
    for p in all_paths:
        if p.name == STATE_FILENAME or p.name == SIDECAR_FILENAME:
            continue  # keep for now; pruned at the end if dir becomes empty
        if p.is_symlink():
            if not p.exists():  # broken
                if dry_run:
                    print( f"    [DRY] would remove broken symlink: {p.relative_to( upload_dir )}" )
                else:
                    p.unlink()
                broken += 1

    # 2. Remove empty directories (leaves first). Consider a dir empty if it contains
    #    only sidecars / state files with no actual file symlinks alongside.
    for root, dirnames, filenames in _walk_bottom_up( upload_dir ):
        root_path = Path( root )
        if root_path == upload_dir:
            continue
        # Re-check contents
        try:
            contents = list( root_path.iterdir() )
        except OSError:
            continue
        non_sidecar = [ c for c in contents if c.name not in ( SIDECAR_FILENAME, STATE_FILENAME ) ]
        if not non_sidecar:
            if dry_run:
                print( f"    [DRY] would prune empty dir: {root_path.relative_to( upload_dir )}" )
            else:
                # Clean up sidecars/state first, then remove dir
                for c in contents:
                    try:
                        c.unlink()
                    except OSError:
                        pass
                try:
                    root_path.rmdir()
                    empty_dirs += 1
                except OSError:
                    pass

    return ( broken, empty_dirs )


def _walk_bottom_up( root: Path ):
    """Bottom-up walk — yields (dir_path, subdirs, files) like os.walk topdown=False."""
    try:
        entries = list( root.iterdir() )
    except OSError:
        return
    subdirs = [ e for e in entries if e.is_dir() and not e.is_symlink() ]
    files = [ e.name for e in entries if e.is_file() or e.is_symlink() ]
    for sub in subdirs:
        yield from _walk_bottom_up( sub )
    yield ( str( root ), [ s.name for s in subdirs ], files )


# ============================================================================
# State log
# ============================================================================

def write_state_log( upload_dir: Path, files_linked: int, warnings: int ):
    state = upload_dir / STATE_FILENAME
    with open( state, 'w' ) as f:
        f.write( f"# GIGANTIC upload_to_server state — last updated {datetime.now().isoformat()}\n" )
        f.write( f"files_linked\t{files_linked}\n" )
        f.write( f"warnings\t{warnings}\n" )


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description = 'Build upload_to_server/ tree from per-workflow manifests'
    )
    parser.add_argument(
        '--subproject-dir', type = str, required = True,
        help = 'Path to the subproject root directory'
    )
    parser.add_argument(
        '--dry-run', action = 'store_true',
        help = 'Show actions without making changes'
    )
    parser.add_argument(
        '--clean', action = 'store_true',
        help = 'Recursively remove broken symlinks and empty dirs before/after rebuild'
    )
    parser.add_argument(
        '--strict', action = 'store_true',
        help = 'Treat manifest warnings as errors'
    )
    args = parser.parse_args()

    subproject_dir = Path( args.subproject_dir ).resolve()
    if not subproject_dir.is_dir():
        print( f"ERROR: subproject dir does not exist: {subproject_dir}" )
        sys.exit( 1 )

    upload_dir = subproject_dir / 'upload_to_server'
    upload_dir.mkdir( exist_ok = True )

    print( f"Subproject: {subproject_dir.name}" )
    print( f"Upload dir: {upload_dir}" )
    print()

    # Find all manifests inside workflow-RUN_* directories
    manifests = []
    for candidate in subproject_dir.rglob( MANIFEST_FILENAME ):
        # Must live inside a workflow-RUN_* dir (direct parent)
        parent = candidate.parent
        if not parent.name.startswith( 'workflow-RUN_' ):
            continue
        manifests.append( candidate )

    # Policy (Eric, 2026-06): publish ONLY the most recent RUN of a given block or
    # step. Group the discovered manifests by the directory that holds the
    # workflow-RUN_* dirs (the BLOCK_/STEP_/instance dir) and keep only the highest
    # RUN number in each group. Superseded runs are dropped here; their previously
    # published files are then pruned by the stale-symlink cleanup pass below
    # (they are no longer in all_kept_paths). RUN numbers may be zero-padded
    # (RUN_04) or not (RUN_3) — compared as integers.
    def run_number_of_manifest( manifest_path: Path ) -> int:
        run_dir_name = manifest_path.parent.name  # workflow-RUN_<K>-<description>
        marker = 'RUN_'
        marker_index = run_dir_name.find( marker )
        if marker_index == -1:
            return -1
        digits = ''
        for character in run_dir_name[ marker_index + len( marker ): ]:
            if character.isdigit():
                digits += character
            else:
                break
        return int( digits ) if digits else -1

    blocks___manifests = {}
    for candidate in manifests:
        block_dir = candidate.parent.parent  # the BLOCK_/STEP_/instance dir
        blocks___manifests.setdefault( block_dir, [] ).append( candidate )

    newest_manifests = []
    for block_dir, block_manifests in blocks___manifests.items():
        newest_manifest = max( block_manifests, key = run_number_of_manifest )
        newest_manifests.append( newest_manifest )
        for superseded in block_manifests:
            if superseded is not newest_manifest:
                print( f"  SKIP superseded run: {superseded.parent.name} "
                       f"(newer RUN published for {block_dir.name})" )
    manifests = newest_manifests

    print( f"Found {len( manifests )} manifest(s) in workflow-RUN_* directories "
           f"(most recent RUN per block/step)" )
    print()

    total_linked = 0
    total_warnings = 0
    all_kept_paths = set()

    for m in sorted( manifests ):
        linked, warns, kept = apply_manifest(
            manifest_path = m,
            subproject_dir = subproject_dir,
            upload_dir = upload_dir,
            dry_run = args.dry_run,
            strict = args.strict,
        )
        total_linked += linked
        total_warnings += warns
        all_kept_paths.update( kept )

    print()
    if args.clean or not args.dry_run:
        # 1. Prune stale symlinks (files previously published but removed from / flipped off in the manifest)
        stale = prune_stale_symlinks( upload_dir, all_kept_paths, args.dry_run )
        # 2. Broken symlinks (source files no longer on disk) + empty dirs
        broken, empty = clean_upload_dir( upload_dir, args.dry_run )
        # 3. Sidecars: drop rows whose file is no longer present
        prune_sidecar_entries( upload_dir, args.dry_run )
        print( "Cleaning:" )
        print( f"  Stale symlinks removed:  {stale}" )
        print( f"  Broken symlinks removed: {broken}" )
        print( f"  Empty dirs pruned:       {empty}" )
        print()

    if not args.dry_run:
        write_state_log( upload_dir, total_linked, total_warnings )

    print( "=" * 70 )
    print( f"Files linked: {total_linked}" )
    print( f"Warnings:     {total_warnings}" )
    print( "=" * 70 )

    if total_warnings > 0 and args.strict:
        sys.exit( 2 )


if __name__ == '__main__':
    main()
