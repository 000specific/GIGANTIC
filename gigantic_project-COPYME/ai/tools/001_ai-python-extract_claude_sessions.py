#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Extract Claude Code session compactions to markdown
# Human: Eric Edsinger

"""
Extract Claude Code Session Compactions

This script extracts context compaction summaries from Claude Code's internal
JSONL files and writes them to human-readable markdown in the GIGANTIC
research_notebook structure.

Usage:
    python3 ai/tools/001_ai-python-extract_claude_sessions.py [--output-dir PATH]

The script:
1. Finds Claude's project directory based on current working directory
2. Reads all JSONL session files
3. Extracts compaction summaries (isCompactSummary = true)
4. Writes markdown to research_notebook/research_ai/project/sessions/
5. Appends extraction record to SESSION_EXTRACTION_LOG.md

Requirements:
- Must be run from a GIGANTIC project root directory
- Claude Code must have been used in this directory (creates ~/.claude/projects/...)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def get_claude_project_directory( working_directory: str ) -> Path:
    """
    Convert a working directory path to Claude's encoded project directory.

    Claude encodes paths by replacing '/' and '_' with '-'.
    Example: /blue/moroz/share/ai_project -> -blue-moroz-share-ai-project
    """

    # Encode the path: replace / and _ with -
    encoded_path = working_directory.replace( '/', '-' ).replace( '_', '-' )
    if not encoded_path.startswith( '-' ):
        encoded_path = '-' + encoded_path

    claude_projects_directory = Path.home() / '.claude' / 'projects' / encoded_path

    return claude_projects_directory


def find_jsonl_files( claude_project_directory: Path ) -> list:
    """
    Find all JSONL session files in Claude's project directory.
    """

    jsonl_files = []

    if claude_project_directory.exists():
        for file_path in claude_project_directory.glob( '*.jsonl' ):
            jsonl_files.append( file_path )

    return sorted( jsonl_files, key = lambda x: x.stat().st_mtime, reverse = True )


def extract_compaction_summaries( jsonl_file_path: Path ) -> list:
    """
    Extract all compaction summaries from a JSONL file.

    Returns list of dicts with: line_number, timestamp, content
    """

    summaries = []

    with open( jsonl_file_path, 'r' ) as input_file:
        for line_number, line in enumerate( input_file, 1 ):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads( line )
            except json.JSONDecodeError:
                continue

            # Check if this is a compaction summary
            if data.get( 'isCompactSummary', False ):
                content = data.get( 'message', {} ).get( 'content', '' )
                timestamp = data.get( 'timestamp', '' )

                # Only include entries that look like continuation summaries
                if 'This session is being continued' in content:
                    summary = {
                        'line_number': line_number,
                        'timestamp': timestamp,
                        'content': content
                    }
                    summaries.append( summary )

    return summaries


def format_timestamp( timestamp_string: str ) -> str:
    """
    Format ISO timestamp to human-readable format.
    """

    if not timestamp_string:
        return 'Unknown'

    try:
        # Parse ISO format
        datetime_object = datetime.fromisoformat( timestamp_string.replace( 'Z', '+00:00' ) )
        return datetime_object.strftime( '%Y-%m-%d %H:%M:%S' )
    except:
        return timestamp_string


def write_session_markdown( session_id: str, summaries: list, output_directory: Path, project_path: str ) -> Path:
    """
    Write extracted summaries to a markdown file.

    Returns the path to the created file.
    """

    # Create output filename based on current date and session
    current_date = datetime.now().strftime( '%Y%B%d' ).lower()
    output_filename = f'session_{current_date}_{session_id[:8]}.md'
    output_file_path = output_directory / output_filename

    # Build markdown content
    extraction_timestamp = datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )

    markdown_lines = []
    markdown_lines.append( f'# Claude Code Session Extraction' )
    markdown_lines.append( '' )
    markdown_lines.append( f'**Session ID**: {session_id}' )
    markdown_lines.append( f'**Project Path**: {project_path}' )
    markdown_lines.append( f'**Compaction Count**: {len( summaries )}' )
    markdown_lines.append( f'**Extracted**: {extraction_timestamp}' )
    markdown_lines.append( '' )
    markdown_lines.append( '---' )
    markdown_lines.append( '' )

    for index, summary in enumerate( summaries, 1 ):
        markdown_lines.append( f'## Compaction Summary {index}' )
        markdown_lines.append( '' )
        markdown_lines.append( f'**Timestamp**: {format_timestamp( summary[ "timestamp" ] )}' )
        markdown_lines.append( f'**JSONL Line**: {summary[ "line_number" ]}' )
        markdown_lines.append( '' )
        markdown_lines.append( '```' )
        markdown_lines.append( summary[ 'content' ] )
        markdown_lines.append( '```' )
        markdown_lines.append( '' )
        markdown_lines.append( '---' )
        markdown_lines.append( '' )

    # Write the file
    output_directory.mkdir( parents = True, exist_ok = True )

    output_content = '\n'.join( markdown_lines )
    with open( output_file_path, 'w' ) as output_file:
        output_file.write( output_content )

    return output_file_path


def append_to_extraction_log( log_file_path: Path, session_id: str, compaction_count: int, output_file_path: Path ):
    """
    Append an entry to the session extraction log.
    """

    extraction_timestamp = datetime.now().strftime( '%Y-%m-%d %H:%M' )
    relative_output_path = output_file_path.name

    # Create log file with header if it doesn't exist
    if not log_file_path.exists():
        log_file_path.parent.mkdir( parents = True, exist_ok = True )
        header = """# Session Extraction Log

This log records all Claude Code session extractions for this GIGANTIC project.
Each extraction overwrites the previous version with complete current state.

| Date | Session ID | Compactions | Output File |
|------|------------|-------------|-------------|
"""
        with open( log_file_path, 'w' ) as output_file:
            output_file.write( header )

    # Append new entry
    log_entry = f'| {extraction_timestamp} | {session_id[:8]}... | {compaction_count} | {relative_output_path} |\n'

    with open( log_file_path, 'a' ) as output_file:
        output_file.write( log_entry )


def main():
    """
    Main extraction workflow.
    """

    # Determine working directory (GIGANTIC project root)
    working_directory = os.getcwd()

    print( '=' * 70 )
    print( 'Claude Code Session Extraction' )
    print( '=' * 70 )
    print( '' )
    print( f'Working directory: {working_directory}' )

    # Find Claude's project directory
    claude_project_directory = get_claude_project_directory( working_directory )
    print( f'Claude project directory: {claude_project_directory}' )

    if not claude_project_directory.exists():
        print( '' )
        print( 'ERROR: No Claude Code session data found for this directory.' )
        print( 'This means Claude Code has not been used in this directory,' )
        print( 'or the session data has been deleted.' )
        sys.exit( 1 )

    # Find JSONL files
    jsonl_files = find_jsonl_files( claude_project_directory )
    print( f'Found {len( jsonl_files )} session file(s)' )
    print( '' )

    if not jsonl_files:
        print( 'No session files found. Nothing to extract.' )
        sys.exit( 0 )

    # Determine output directory
    output_directory = Path( working_directory ) / 'research_notebook' / 'research_ai' / 'project' / 'sessions'
    log_file_path = Path( working_directory ) / 'research_notebook' / 'research_ai' / 'project' / 'SESSION_EXTRACTION_LOG.md'

    print( f'Output directory: {output_directory}' )
    print( '' )

    # Process each session file
    total_compactions = 0
    files_created = []

    for jsonl_file in jsonl_files:
        session_id = jsonl_file.stem  # filename without extension
        print( f'Processing session: {session_id[:8]}...' )

        summaries = extract_compaction_summaries( jsonl_file )
        print( f'  Found {len( summaries )} compaction(s)' )

        if summaries:
            output_file_path = write_session_markdown(
                session_id = session_id,
                summaries = summaries,
                output_directory = output_directory,
                project_path = working_directory
            )
            print( f'  Written to: {output_file_path.name}' )

            # Log the extraction
            append_to_extraction_log(
                log_file_path = log_file_path,
                session_id = session_id,
                compaction_count = len( summaries ),
                output_file_path = output_file_path
            )

            total_compactions += len( summaries )
            files_created.append( output_file_path )

        print( '' )

    # Summary
    print( '=' * 70 )
    print( 'SUMMARY' )
    print( '=' * 70 )
    print( f'Sessions processed: {len( jsonl_files )}' )
    print( f'Total compactions extracted: {total_compactions}' )
    print( f'Files created/updated: {len( files_created )}' )
    print( f'Extraction log: {log_file_path}' )
    print( '' )

    if files_created:
        print( 'Output files:' )
        for file_path in files_created:
            print( f'  - {file_path}' )


if __name__ == '__main__':
    main()
