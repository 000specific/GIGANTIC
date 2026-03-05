#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 05 | Purpose: PreCompact hook to capture full session transcript before compaction
# Human: Eric Edsinger

"""
GIGANTIC PreCompact Hook - Lossless Session Transcript Capture

This script runs as a Claude Code PreCompact hook. Each time context compaction
is about to occur, it copies the COMPLETE session transcript (JSONL) to a
gzipped backup in research_notebook/research_ai/sessions/.

This provides lossless research provenance - the full conversation record
including every message, tool call, and result is preserved before compaction
compresses the context.

The hook receives JSON on stdin from Claude Code with:
    - session_id: current session identifier
    - transcript_path: full path to the session JSONL file
    - cwd: current working directory
    - trigger: "manual" or "auto"

Output filename format:
    YYYYMMDD_HHMMSS-claude_code-MODEL-SESSION_SHORT_ID.jsonl.gz

Hook configuration (in ~/.claude/settings.json or .claude/settings.json):
    {
        "hooks": {
            "PreCompact": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 \\"$CLAUDE_PROJECT_DIR\\"/ai/tools/002_ai-python-hook_precompact_capture_transcript.py"
                        }
                    ]
                }
            ]
        }
    }
"""

import gzip
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def find_gigantic_project_root( start_directory: Path ) -> Path:
    """
    Walk up from start_directory to find GIGANTIC project root.

    A GIGANTIC project root has a research_notebook/ directory.
    """

    current = start_directory.resolve()

    while current != current.parent:
        if ( current / 'research_notebook' ).is_dir():
            return current
        current = current.parent

    return None


def extract_model_name( transcript_path: Path ) -> str:
    """
    Extract the AI model name from the first assistant entry in the JSONL.

    Scans the first 50 lines for an entry with message.model field.
    Returns the model name or 'unknown_model' if not found.
    """

    try:
        with open( transcript_path, 'r' ) as input_file:
            for line_number, line in enumerate( input_file ):
                if line_number > 50:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads( line )
                    model = data.get( 'message', {} ).get( 'model', '' )
                    if model:
                        return model
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return 'unknown_model'


def capture_transcript( transcript_path: Path, output_directory: Path, session_id: str, model_name: str ) -> Path:
    """
    Copy the full transcript JSONL to a gzipped file in the output directory.

    Filename format: YYYYMMDD_HHMMSS-claude_code-MODEL-SESSION_SHORT_ID.jsonl.gz

    Returns the path to the created gzip file.
    """

    # Build filename components
    timestamp = datetime.now().strftime( '%Y%m%d_%H%M%S' )
    model_safe = model_name.replace( '-', '_' )
    session_short_id = session_id[ :8 ]

    output_filename = f'{timestamp}-claude_code-{model_safe}-{session_short_id}.jsonl.gz'
    output_path = output_directory / output_filename

    # Ensure output directory exists
    output_directory.mkdir( parents = True, exist_ok = True )

    # Copy and gzip the transcript
    with open( transcript_path, 'rb' ) as input_file:
        with gzip.open( output_path, 'wb' ) as output_file:
            shutil.copyfileobj( input_file, output_file )

    return output_path


def append_to_capture_log( log_file_path: Path, timestamp: str, session_id: str, model_name: str, trigger: str, transcript_size_bytes: int, output_filename: str ):
    """
    Append an entry to the transcript capture log.
    """

    # Create log file with header if it doesn't exist
    if not log_file_path.exists():
        log_file_path.parent.mkdir( parents = True, exist_ok = True )
        header = """# Transcript Capture Log

Automatic captures of full session transcripts by the PreCompact hook.
Each entry records a complete JSONL backup taken before context compaction.

| Date | Session ID | Model | Trigger | Transcript Size | Output File |
|------|------------|-------|---------|-----------------|-------------|
"""
        with open( log_file_path, 'w' ) as output_file:
            output_file.write( header )

    # Format size for readability
    if transcript_size_bytes > 1_000_000:
        size_display = f'{transcript_size_bytes / 1_000_000:.1f} MB'
    elif transcript_size_bytes > 1_000:
        size_display = f'{transcript_size_bytes / 1_000:.1f} KB'
    else:
        size_display = f'{transcript_size_bytes} B'

    log_entry = f'| {timestamp} | {session_id[ :8 ]}... | {model_name} | {trigger} | {size_display} | {output_filename} |\n'

    with open( log_file_path, 'a' ) as output_file:
        output_file.write( log_entry )


def main():
    """
    Main hook entry point.

    Reads JSON from stdin (provided by Claude Code), captures the transcript,
    and exits silently. Any errors are non-fatal (exit 0) to avoid blocking
    the user's session.
    """

    try:
        # Read hook input from stdin
        hook_input = json.loads( sys.stdin.read() )
    except Exception:
        # If we can't read stdin, silently exit
        sys.exit( 0 )

    session_id = hook_input.get( 'session_id', '' )
    transcript_path_string = hook_input.get( 'transcript_path', '' )
    working_directory = hook_input.get( 'cwd', '' )
    trigger = hook_input.get( 'trigger', 'unknown' )

    # Validate we have the essential fields
    if not transcript_path_string or not working_directory:
        sys.exit( 0 )

    transcript_path = Path( transcript_path_string ).expanduser()

    # Verify transcript file exists
    if not transcript_path.exists():
        sys.exit( 0 )

    # Find GIGANTIC project root
    project_root = find_gigantic_project_root( Path( working_directory ) )
    if not project_root:
        # Not a GIGANTIC project, silently exit
        sys.exit( 0 )

    # Extract model name from transcript
    model_name = extract_model_name( transcript_path )

    # Determine output location
    sessions_directory = project_root / 'research_notebook' / 'research_ai' / 'sessions'

    # Capture the transcript
    output_path = capture_transcript(
        transcript_path = transcript_path,
        output_directory = sessions_directory,
        session_id = session_id,
        model_name = model_name
    )

    # Get transcript size for logging
    transcript_size_bytes = transcript_path.stat().st_size

    # Log the capture
    log_file_path = sessions_directory / 'TRANSCRIPT_CAPTURE_LOG.md'
    capture_timestamp = datetime.now().strftime( '%Y-%m-%d %H:%M' )

    append_to_capture_log(
        log_file_path = log_file_path,
        timestamp = capture_timestamp,
        session_id = session_id,
        model_name = model_name,
        trigger = trigger,
        transcript_size_bytes = transcript_size_bytes,
        output_filename = output_path.name
    )

    # Exit cleanly (exit 0 = success, hook does not interfere with compaction)
    sys.exit( 0 )


if __name__ == '__main__':
    main()
