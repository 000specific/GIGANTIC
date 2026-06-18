# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Shared utility for emitting run summary fragments
# AI: Claude Code | Opus 4.8 | 2026 June 05 | Purpose: Add annogroup annotation lookup so downstream scripts can append Pfam accessions + definitions
# Human: Eric Edsinger

"""
Run Summary Fragment Utility

Each pipeline script (001-005) calls emit_run_summary_fragment() at the end of
its work with a dict of key stats. The fragment is written as JSON to:

    {workflow_dir}/ai/logs/run_summary_fragments/{script_number:03d}_{structure_id}.json

Script 007 (the aggregator) reads all fragments, aggregates across structures,
and builds RUN_SUMMARY.md at the workflow root. See Script 007 for the
aggregation rules and output format.

This fragment-first design solves the concurrent-write problem when 105
structures run in parallel -- each structure writes its own file rather than
appending to a shared document.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def get_fragments_directory( workflow_directory ):
    """
    Get the fragments directory for this workflow run.

    Args:
        workflow_directory: Path to workflow directory (contains ai/, INPUT_user/, etc.)

    Returns:
        Path: {workflow_directory}/ai/logs/run_summary_fragments/
    """
    workflow_path = Path( workflow_directory )
    return workflow_path / 'ai' / 'logs' / 'run_summary_fragments'


def emit_run_summary_fragment( script_number, structure_id, stats, workflow_directory = None ):
    """
    Write a run summary fragment for this (script, structure) pair.

    Called by each pipeline script at the end of its work with a dict of
    interesting stats (counts, durations, key numbers). The aggregator
    (Script 007) reads all fragments and builds RUN_SUMMARY.md.

    Args:
        script_number: int, 1-5 for the analysis scripts
        structure_id: str, e.g. "001"
        stats: dict of stats to record. Expected keys vary by script but
               typically include 'duration_seconds' and script-specific counts.
        workflow_directory: Path to workflow directory. If None, inferred as
               two levels up from this script's __file__ location.

    Returns:
        Path to the written fragment file.
    """
    # Resolve workflow directory if not provided.
    # This script lives at: {workflow_dir}/ai/scripts/utils_run_summary.py
    # So workflow_dir is two levels up.
    if workflow_directory is None:
        workflow_directory = Path( __file__ ).parent.parent.parent

    fragments_directory = get_fragments_directory( workflow_directory )
    fragments_directory.mkdir( parents = True, exist_ok = True )

    fragment_filename = f"{script_number:03d}_{structure_id}.json"
    fragment_path = fragments_directory / fragment_filename

    # Add standard metadata
    fragment_data = {
        'script_number': script_number,
        'structure_id': structure_id,
        'timestamp': datetime.now().isoformat(),
        'stats': stats
    }

    with open( fragment_path, 'w' ) as output_file:
        json.dump( fragment_data, output_file, indent = 2 )

    return fragment_path


def read_all_fragments( workflow_directory ):
    """
    Read all run summary fragments in a workflow's fragments directory.

    Args:
        workflow_directory: Path to workflow directory

    Returns:
        list of dicts, one per fragment, sorted by (script_number, structure_id)
    """
    fragments_directory = get_fragments_directory( workflow_directory )

    if not fragments_directory.exists():
        return []

    fragments = []
    for fragment_path in sorted( fragments_directory.glob( '*.json' ) ):
        try:
            with open( fragment_path, 'r' ) as input_file:
                fragment_data = json.load( input_file )
                fragments.append( fragment_data )
        except ( json.JSONDecodeError, IOError ):
            continue

    fragments.sort( key = lambda f: ( f.get( 'script_number', 0 ), f.get( 'structure_id', '' ) ) )

    return fragments


def clear_fragments_directory( workflow_directory ):
    """
    Remove all existing fragments (called at start of a run to ensure clean state).

    Args:
        workflow_directory: Path to workflow directory
    """
    fragments_directory = get_fragments_directory( workflow_directory )

    if not fragments_directory.exists():
        return

    for fragment_path in fragments_directory.glob( '*.json' ):
        try:
            fragment_path.unlink()
        except OSError:
            pass


# ============================================================================
# Annogroup annotation lookup (Pfam accessions + definitions)
# ============================================================================
#
# Script 001 writes the authoritative annogroup map with two annotation columns:
#   Annotation_Accessions  -- comma delimited database accessions (e.g. Pfam PF00069)
#                             or the unannotated identifier for the zero subtype
#   Annotation_Definitions -- semicolon delimited "definition ==accession" pairs, where
#                             definition is the InterProScan signature description
#                             (e.g. "Protein kinase domain ==PF00069; WD40 repeat ==PF00400")
#
# Downstream scripts (002, 003, 004) carry these two columns onto every output
# that bears an Annogroup_ID by looking them up here by Annogroup_ID. They are
# always appended as the final two columns so existing positional parsers (which
# read fixed low indices) are unaffected.


def sanitize_annotation_text( text ):
    """
    Make a single annotation field safe to embed inside one TSV column.

    Tabs and newlines would break the column/row structure, so they are
    collapsed to spaces. Commas, semicolons and '=' are left intact (the
    "definition ==accession" ... format relies on them and TSV only splits on
    tabs). Returns the cleaned string.
    """
    if text is None:
        return ''
    return text.replace( '\t', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' ).strip()


def format_annotation_definitions( accessions, accessions___descriptions ):
    """
    Build the Annotation_Definitions string for one annogroup.

    Accessions are DEDUPLICATED here (first-occurrence order preserved): a
    combo architecture can repeat the same accession many times (e.g. a protein
    with 300 PF00041 hits), but its definition only needs to appear once. The
    full multiplicity is retained in the separate Annotation_Accessions column;
    Annotation_Definitions is the unique domain glossary for the annogroup.

    Args:
        accessions: list of database accessions for this annogroup (may contain
            duplicates), in the same order used for Annotation_Accessions.
        accessions___descriptions: dict mapping accession -> definition text.

    Returns:
        str: semicolon delimited 'definition ==accession' pairs over the UNIQUE
             accessions, e.g. 'Protein kinase domain ==PF00069; WD40 repeat ==PF00400'.
             Note the literal ' ==' separator (space + two equals signs); the
             definition comes first so the column reads as human text with the
             accession appended for provenance. Missing definitions render as
             '==accession' (no leading text).
    """
    seen_accessions = set()
    pairs = []
    for accession in accessions:
        if accession in seen_accessions:
            continue
        seen_accessions.add( accession )
        definition = sanitize_annotation_text( accessions___descriptions.get( accession, '' ) )
        pairs.append( f"{definition} =={accession}" if definition else f"=={accession}" )
    return '; '.join( pairs )


def load_annogroup_annotation_lookup( annogroup_map_file ):
    """
    Load Annogroup_ID -> ( Annotation_Accessions, Annotation_Definitions ) from
    the Script 001 annogroup map. Used by downstream scripts (002, 003, 004) to
    append these two columns to their annogroup-bearing outputs.

    Columns are located by their header_ID (the text before the first ' (' in a
    self-documenting header), so column order in the map does not matter.

    Args:
        annogroup_map_file: Path to 1_ai-structure_NNN_annogroup_map.tsv

    Returns:
        dict: { annogroup_id: { 'accessions': str, 'definitions': str } }
              Empty dict if the file is missing or lacks the columns (callers
              then emit empty cells, never crash).
    """
    annogroup_ids___annotation_columns = {}

    map_path = Path( annogroup_map_file )
    if not map_path.exists():
        return annogroup_ids___annotation_columns

    with open( map_path, 'r' ) as input_file:
        # Annogroup_ID (...)	Annogroup_Subtype (...)	Annotation_Database (...)	Annotation_Accessions (...)	Annotation_Definitions (...)	...
        header_line = input_file.readline().rstrip( '\n' )
        header_parts = header_line.split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        annogroup_id_index = column_names___indices.get( 'Annogroup_ID' )
        accessions_index = column_names___indices.get( 'Annotation_Accessions' )
        definitions_index = column_names___indices.get( 'Annotation_Definitions' )

        if annogroup_id_index is None:
            return annogroup_ids___annotation_columns

        for line in input_file:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if annogroup_id_index >= len( parts ):
                continue
            annogroup_id = parts[ annogroup_id_index ]
            accessions = parts[ accessions_index ] if accessions_index is not None and accessions_index < len( parts ) else ''
            definitions = parts[ definitions_index ] if definitions_index is not None and definitions_index < len( parts ) else ''
            annogroup_ids___annotation_columns[ annogroup_id ] = {
                'accessions': accessions,
                'definitions': definitions
            }

    return annogroup_ids___annotation_columns
