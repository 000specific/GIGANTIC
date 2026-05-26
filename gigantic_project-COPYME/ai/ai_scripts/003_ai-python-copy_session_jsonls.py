#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 25 | Purpose: On-demand "Save Chat!" raw-copy of every Claude Code session JSONL for this project into research_notebook/research_ai/sessions/ as lossless gzipped permanent archives
# Human: Eric Edsinger

"""
GIGANTIC "Save Chat!" — On-Demand Session Capture

Triggered when the user types "Save Chat!" to an AI assistant. The AI runs
this script to ensure every Claude Code session for THIS project is captured
as a lossless gzipped JSONL transcript in
research_notebook/research_ai/sessions/ — surviving Claude Code's default
30-day TTL on its source JSONL storage at ~/.claude/projects/.

Companion to the PreCompact hook (002_*.py) which fires automatically before
each context compaction. 003 (this script) catches:
  - Short sessions that never compact (and so never trigger the hook)
  - The latest state of long sessions that have continued past their most
    recent capture

Usage:
    python3 ai/ai_scripts/003_ai-python-copy_session_jsonls.py

The script:
  1. Locates Claude's per-project JSONL directory based on this project's path
     (~/.claude/projects/<encoded-path>/)
  2. Scans every *.jsonl session file
  3. For each session: reads session_id, model, and last-message timestamp
  4. Constructs destination filename matching the hook's format:
     YYYYMMDD_HHMMSS-claude_code-MODEL-SESSION_SHORT_ID.jsonl.gz
     (timestamp = last-message timestamp, so re-runs skip unchanged sources
     and growing sessions produce fresh snapshots)
  5. Skips if that exact filename already exists in the destination
  6. Gzip-copies new captures
  7. Appends entries to TRANSCRIPT_CAPTURE_LOG.md with trigger=save_chat
  8. Prints a clear summary

Captures are LOSSLESS (every message, every tool call, every result),
PERMANENT (never auto-deleted by GIGANTIC), and NEVER EDITED (treat as
original lab-notebook entries). See ai/ai_FYIs/gigantic_conventions.md §9.
"""

import gzip
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def find_gigantic_project_root( start_directory: Path ) -> Path:
    """
    Walk up from start_directory to find the enclosing gigantic_project-*
    directory (the canonical AI-session root). Returns its absolute path.
    """

    current = start_directory.resolve()
    while current != current.parent:
        if current.name.startswith( 'gigantic_project-' ):
            return current
        current = current.parent
    raise RuntimeError(
        f"Could not find a gigantic_project-* directory above { start_directory }. "
        f"This script must run inside a renamed gigantic_project-* directory."
    )


def get_claude_project_jsonl_directory( project_root: Path ) -> Path:
    """
    Convert a project root path to Claude Code's encoded JSONL directory.

    Claude encodes the project path by replacing '/' and '_' with '-'.
    Example: /blue/moroz/share/ai_project -> -blue-moroz-share-ai-project
    """

    project_path_string = str( project_root )
    encoded_path = project_path_string.replace( '/', '-' ).replace( '_', '-' )
    if not encoded_path.startswith( '-' ):
        encoded_path = '-' + encoded_path
    return Path.home() / '.claude' / 'projects' / encoded_path


def read_session_metadata( jsonl_path: Path ) -> dict:
    """
    Extract session_id, model, and last-message timestamp from a JSONL file
    by walking it once line-by-line. Returns a dict; missing fields are None.
    """

    session_id = None
    model = None
    last_timestamp = None

    with open( jsonl_path, 'r' ) as input_jsonl:
        for line in input_jsonl:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads( line )
            except json.JSONDecodeError:
                continue

            if 'sessionId' in entry and session_id is None:
                session_id = entry[ 'sessionId' ]

            if entry.get( 'type' ) == 'assistant':
                message = entry.get( 'message', {} )
                if 'model' in message and message[ 'model' ]:
                    model = message[ 'model' ]

            if 'timestamp' in entry and entry[ 'timestamp' ]:
                last_timestamp = entry[ 'timestamp' ]

    return {
        'session_id': session_id,
        'model': model,
        'last_timestamp': last_timestamp,
    }


def normalize_model_name( model: str ) -> str:
    """Convert e.g. 'claude-opus-4-7' to 'claude_opus_4_7' for filename use."""

    if not model:
        return 'unknown_model'
    return model.replace( '-', '_' )


def parse_iso_timestamp( timestamp_string: str ) -> datetime:
    """Parse e.g. '2026-03-07T11:55:48.123Z' to a datetime object."""

    cleaned = timestamp_string.split( '.' )[ 0 ].rstrip( 'Z' )
    return datetime.fromisoformat( cleaned )


def construct_output_filename( metadata: dict ) -> str:
    """
    Build YYYYMMDD_HHMMSS-claude_code-MODEL-SESSION_SHORT_ID.jsonl.gz
    matching the PreCompact hook's format.
    """

    timestamp = parse_iso_timestamp( metadata[ 'last_timestamp' ] )
    timestamp_string = timestamp.strftime( '%Y%m%d_%H%M%S' )
    model_string = normalize_model_name( metadata[ 'model' ] )
    session_short_id = metadata[ 'session_id' ][ :8 ]
    return f'{ timestamp_string }-claude_code-{ model_string }-{ session_short_id }.jsonl.gz'


def append_to_capture_log( log_path: Path, captured: list ):
    """Append a row per new capture to TRANSCRIPT_CAPTURE_LOG.md."""

    if not log_path.exists():
        with open( log_path, 'w' ) as log_file:
            output = (
                '# Transcript Capture Log\n\n'
                'Captures of full session transcripts.\n'
                'Trigger `precompact` = auto from hook (002); '
                'trigger `save_chat` = on-demand from "Save Chat!" script (003).\n\n'
                '| Date | Session ID | Model | Trigger | Source Size | Output File |\n'
                '|------|------------|-------|---------|-------------|-------------|\n'
            )
            log_file.write( output )

    with open( log_path, 'a' ) as log_file:
        for capture in captured:
            row_date = parse_iso_timestamp( capture[ 'timestamp' ] ).strftime( '%Y-%m-%d %H:%M' )
            output = (
                f"| { row_date } "
                f"| { capture[ 'session_short_id' ] }... "
                f"| { capture[ 'model' ] } "
                f"| save_chat "
                f"| { capture[ 'source_size_mb' ]:.1f } MB "
                f"| { capture[ 'filename' ] } |\n"
            )
            log_file.write( output )


def main():
    script_directory = Path( __file__ ).resolve().parent
    project_root = find_gigantic_project_root( script_directory )
    claude_jsonl_directory = get_claude_project_jsonl_directory( project_root )

    print( f"\n=== Save Chat! ===" )
    print( f"  Project root:  { project_root }" )
    print( f"  Source JSONLs: { claude_jsonl_directory }" )

    if not claude_jsonl_directory.exists():
        print( f"\n  No Claude session storage found for this project." )
        print( f"  This is expected if you have not yet used Claude Code in this directory." )
        sys.exit( 0 )

    session_jsonls = sorted( claude_jsonl_directory.glob( '*.jsonl' ) )
    if not session_jsonls:
        print( f"\n  No session JSONL files in source directory." )
        sys.exit( 0 )

    destination_directory = project_root / 'research_notebook' / 'research_ai' / 'sessions'
    destination_directory.mkdir( parents=True, exist_ok=True )
    print( f"  Destination:   { destination_directory }" )
    print( f"  Sessions found: { len( session_jsonls ) }" )

    captured = []
    skipped_count = 0
    error_count = 0

    for jsonl_path in session_jsonls:
        try:
            metadata = read_session_metadata( jsonl_path )

            if not metadata[ 'session_id' ] or not metadata[ 'last_timestamp' ]:
                print( f"  ! Skipping (no session_id / timestamp): { jsonl_path.name }" )
                error_count += 1
                continue

            output_filename = construct_output_filename( metadata )
            output_path = destination_directory / output_filename

            if output_path.exists():
                skipped_count += 1
                continue

            with open( jsonl_path, 'rb' ) as source_file:
                with gzip.open( output_path, 'wb' ) as destination_file:
                    shutil.copyfileobj( source_file, destination_file )

            source_size_mb = jsonl_path.stat().st_size / ( 1024 * 1024 )
            destination_size_mb = output_path.stat().st_size / ( 1024 * 1024 )

            captured.append( {
                'filename': output_filename,
                'session_short_id': metadata[ 'session_id' ][ :8 ],
                'model': metadata[ 'model' ] or 'unknown',
                'timestamp': metadata[ 'last_timestamp' ],
                'source_size_mb': source_size_mb,
                'destination_size_mb': destination_size_mb,
            } )
            print( f"  + { output_filename } ({ source_size_mb:.1f } MB -> { destination_size_mb:.1f } MB gzipped)" )
        except Exception as exception:
            print( f"  ! Error processing { jsonl_path.name }: { exception }" )
            error_count += 1

    if captured:
        log_path = destination_directory / 'TRANSCRIPT_CAPTURE_LOG.md'
        append_to_capture_log( log_path, captured )

    print( f"\n  Newly captured:   { len( captured ) }" )
    print( f"  Already captured: { skipped_count }" )
    if error_count:
        print( f"  Errors:           { error_count }" )
    if captured:
        total_destination_mb = sum( c[ 'destination_size_mb' ] for c in captured )
        print( f"  Total written:    { total_destination_mb:.1f } MB (gzipped)" )
    print( f"\nDone. Captures are lossless gzipped JSONL — never edit or delete." )


if __name__ == '__main__':
    main()
