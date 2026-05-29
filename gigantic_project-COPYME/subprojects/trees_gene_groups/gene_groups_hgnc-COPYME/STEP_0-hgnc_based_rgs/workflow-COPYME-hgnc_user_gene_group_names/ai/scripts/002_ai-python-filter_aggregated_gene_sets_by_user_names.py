#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 29 | Purpose: Build aggregated gene symbol sets for the HGNC gene groups the user names (by HGNC name or HGNC id) with optional locus-type filters
# AI: Claude Code | Opus 4.7 | 2026 May 29 (parity-finishing pass)
# Human: Eric Edsinger

"""
Build aggregated gene symbol sets for ONLY the HGNC gene groups the user names.

This script is the MODE 3 (workflow-COPYME-hgnc_user_gene_group_names) variant of
MODE 1's (workflow-COPYME-hgnc_database) script 002. It reuses the same loaders
and aggregation logic verbatim (functions copied in below) and adds:

    1. A user-input loader for ../../INPUT_user/user_gene_group_names.tsv
       that parses entries of the form
            <group_input_identifier>\t<identifier_type>\t<group_display_name>\t<notes>
       where identifier_type is one of 'name', 'id', or 'auto'.

    2. A resolver that maps each user entry to an HGNC family_id, with:
        - case-insensitive, whitespace-collapsed exact match against
          family.csv's `name` column (for identifier_type=='name')
        - 'gg<N>' -> int(N) lookup against family.csv's `id` column
          (for identifier_type=='id')
        - a regex /^gg\\d+$/ decides for identifier_type=='auto'
        - on miss: substring + difflib 'did you mean' suggestions written
          to 2_ai-unresolved_groups.tsv, then sys.exit(1)

    3. A locus-type filter that is configurable via two CLI flags:
            --include-pseudogenes         (default: False)
            --include-non-protein-coding  (default: False)
       The default allowlist matches the MODE 1 database workflow EXACTLY
       ('gene with protein product' + 'complex locus constituent').

    4. Filtering the aggregated dict to only the user's resolved family_ids
       before writing the output TSVs.

Outputs (filenames are stable; downstream script 003 is reused verbatim from
the MODE 1 database workflow and reads `2_ai-aggregated_gene_sets.tsv`):

    2_ai-aggregated_gene_sets.tsv     - same column layout as MODE 1 but
                                        filtered to user's groups only
    2_ai-gene_group_metadata.tsv      - same shape as MODE 1, filtered
    2_ai-resolved_user_groups.tsv     - per-user-entry resolution trail
    2_ai-unresolved_groups.tsv        - ONLY written if any group failed
                                        resolution; carries 'did you mean'
                                        suggestions before sys.exit(1)
    2_ai-hgnc_group_catalog.tsv       - reference catalog of ALL HGNC
                                        groups so the user can grep for
                                        the right name on future runs
    2_ai-filter_policy.tsv            - single-row record of the locus-
                                        type allowlist actually used

Usage:
    python3 002_ai-python-filter_aggregated_gene_sets_by_user_names.py \\
        --input-directory <path-to-1-output> \\
        --input-user-gene-groups <path-to-user_gene_group_names.tsv> \\
        --output-directory <path> \\
        [--include-pseudogenes] \\
        [--include-non-protein-coding] \\
        [--log-file <path>]
"""

import argparse
import csv
import difflib
import logging
import re
import sys
from datetime import datetime
from pathlib import Path


# ============================================================================
# Locus-type policy
# ============================================================================
# Default allowlist matches workflow-COPYME-hgnc_database/ai/scripts/002 EXACTLY.
# CLI flags below expand the allowlist; the default behavior is identical to
# MODE 1 so users get the same RGS counts when they pass the same group.
# ============================================================================

DEFAULT_PROTEIN_CODING_LOCUS_TYPES = {
    'gene with protein product',
    'complex locus constituent',
}

PSEUDOGENE_LOCUS_TYPES = {
    'pseudogene',
}

NON_PROTEIN_CODING_LOCUS_TYPES = {
    'RNA, long non-coding',
    'RNA, micro',
    'RNA, transfer',
    'RNA, ribosomal',
    'RNA, small nuclear',
    'RNA, small nucleolar',
    'RNA, small cytoplasmic',
    'RNA, Y',
    'RNA, vault',
    'RNA, misc',
    'immunoglobulin gene',
    'immunoglobulin pseudogene',
    'T cell receptor gene',
    'T cell receptor pseudogene',
    'endogenous retrovirus',
    'readthrough',
}


# ============================================================================
# Logging
# ============================================================================

def setup_logging( log_file_path ):
    """Configure logging to both file and console."""

    logger = logging.getLogger( 'filter_gene_sets' )
    logger.setLevel( logging.INFO )

    # Clear any handlers from prior invocations (safe for NextFlow process re-runs)
    logger.handlers.clear()

    file_handler = logging.FileHandler( log_file_path )
    file_handler.setLevel( logging.INFO )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


# ============================================================================
# Loaders copied verbatim (where possible) from MODE 1 database workflow's 002.
# Per project convention: each script is self-contained; do not import.
# ============================================================================

def load_family_metadata( family_csv_path, logger ):
    """
    Load gene group metadata from family.csv.

    Returns:
        dict: family_id (int) -> { 'name': str, 'abbreviation': str, 'typical_gene': str }
    """

    family_identifiers___metadata = {}

    # "id","abbreviation","name","external_note","pubmed_ids","desc_comment","desc_label","desc_source","desc_go","typical_gene"
    # "3","FSCN","Fascin family","NULL","21618240","Fascins are actin-binding...","NULL","Hashimoto et al...","NULL","FSCN1"
    with open( family_csv_path, 'r' ) as input_family:
        reader = csv.DictReader( input_family )
        for row in reader:
            family_id = int( row[ 'id' ] )
            family_identifiers___metadata[ family_id ] = {
                'name': row[ 'name' ],
                'abbreviation': row[ 'abbreviation' ] if row[ 'abbreviation' ] != 'NULL' else '',
                'typical_gene': row[ 'typical_gene' ] if row[ 'typical_gene' ] != 'NULL' else '',
            }

    logger.info( f"Loaded {len( family_identifiers___metadata )} gene groups from family.csv" )
    return family_identifiers___metadata


def load_hierarchy_closure( hierarchy_closure_csv_path, logger ):
    """
    Load the full hierarchy closure table.

    Returns:
        dict: parent_family_id (int) -> set of descendant family_ids (int)
              (only descendants with distance > 0, i.e., not self)
    """

    parent_identifiers___descendant_identifiers = {}

    # "parent_fam_id","child_fam_id","distance"
    # "2333","2333","0"
    with open( hierarchy_closure_csv_path, 'r' ) as input_hierarchy_closure:
        reader = csv.DictReader( input_hierarchy_closure )
        for row in reader:
            distance = int( row[ 'distance' ] )
            if distance == 0:
                continue

            parent_id = int( row[ 'parent_fam_id' ] )
            child_id = int( row[ 'child_fam_id' ] )

            if parent_id not in parent_identifiers___descendant_identifiers:
                parent_identifiers___descendant_identifiers[ parent_id ] = set()
            parent_identifiers___descendant_identifiers[ parent_id ].add( child_id )

    logger.info( f"Loaded hierarchy closure: {len( parent_identifiers___descendant_identifiers )} groups have descendants" )
    return parent_identifiers___descendant_identifiers


def load_direct_gene_symbols( hgnc_bulk_tsv_path, allowed_locus_types, logger ):
    """
    Load direct gene symbol assignments per family from the bulk TSV.

    Filters by `allowed_locus_types` (a set of HGNC `Locus type` strings).
    The default (matches MODE 1 database workflow) is
        { 'gene with protein product', 'complex locus constituent' }.

    Returns:
        dict: family_id (int) -> set of gene_symbols (str)
    """

    family_identifiers___gene_symbols = {}
    total_assignments = 0
    skipped_non_allowed = 0

    # HGNC ID	Approved symbol	Approved name	Status	Locus type	Previous symbols	Alias symbols	Chromosome	NCBI Gene ID	Ensembl gene ID	Vega gene ID	Group ID	Group name
    # HGNC:324	AGPAT1	1-acylglycerol-3-phosphate O-acyltransferase 1	Approved	gene with protein product		LPAAT-alpha, LPLAT1	6p21.32	10554	ENSG00000204310	OTTHUMG00000031210	46	1-acylglycerol-3-phosphate O-acyltransferases
    with open( hgnc_bulk_tsv_path, 'r' ) as input_bulk:
        reader = csv.DictReader( input_bulk, delimiter='\t' )
        for row in reader:
            locus_type = row[ 'Locus type' ]
            if locus_type not in allowed_locus_types:
                skipped_non_allowed += 1
                continue

            family_id = int( row[ 'Group ID' ] )
            gene_symbol = row[ 'Approved symbol' ]

            if family_id not in family_identifiers___gene_symbols:
                family_identifiers___gene_symbols[ family_id ] = set()
            family_identifiers___gene_symbols[ family_id ].add( gene_symbol )
            total_assignments += 1

    logger.info( f"Loaded {total_assignments} gene-to-group assignments (filtered)" )
    logger.info( f"  Skipped {skipped_non_allowed} assignments not in allowed locus types" )
    logger.info( f"  Allowed locus types: {sorted( allowed_locus_types )}" )
    logger.info( f"  Groups with at-least-one direct allowed gene: {len( family_identifiers___gene_symbols )}" )
    return family_identifiers___gene_symbols


def build_aggregated_gene_sets( family_identifiers___metadata, parent_identifiers___descendant_identifiers, family_identifiers___gene_symbols, logger ):
    """
    Build aggregated gene symbol sets for every gene group.

    For a group with descendants: aggregate all descendant genes + own direct genes.
    For a leaf group: just its own direct genes.

    Returns:
        dict: family_id (int) -> set of gene_symbols (str)
    """

    family_identifiers___aggregated_gene_symbols = {}

    for family_id in family_identifiers___metadata:

        # Start with direct gene members
        aggregated_symbols = set()
        direct_symbols = family_identifiers___gene_symbols.get( family_id, set() )
        aggregated_symbols.update( direct_symbols )

        # Add genes from all descendants
        descendant_ids = parent_identifiers___descendant_identifiers.get( family_id, set() )
        for descendant_id in descendant_ids:
            descendant_symbols = family_identifiers___gene_symbols.get( descendant_id, set() )
            aggregated_symbols.update( descendant_symbols )

        family_identifiers___aggregated_gene_symbols[ family_id ] = aggregated_symbols

    groups_with_genes = sum( 1 for symbols in family_identifiers___aggregated_gene_symbols.values() if len( symbols ) > 0 )
    groups_without_genes = sum( 1 for symbols in family_identifiers___aggregated_gene_symbols.values() if len( symbols ) == 0 )
    total_unique_symbols = set()
    for symbols in family_identifiers___aggregated_gene_symbols.values():
        total_unique_symbols.update( symbols )

    logger.info( f"Built aggregated gene sets for {len( family_identifiers___aggregated_gene_symbols )} groups (all HGNC groups)" )
    logger.info( f"  Groups with genes (after aggregation): {groups_with_genes}" )
    logger.info( f"  Groups still empty (after aggregation): {groups_without_genes}" )
    logger.info( f"  Total unique gene symbols across all groups: {len( total_unique_symbols )}" )

    return family_identifiers___aggregated_gene_symbols


def sanitize_family_name( family_name ):
    """
    Convert a family name to a filesystem-safe string.

    Replaces spaces and special characters with underscores, converts to lowercase.
    Verbatim from MODE 1 database workflow so MODE 3 output filenames collide
    cleanly with MODE 1.
    """

    sanitized = family_name.lower()
    sanitized = sanitized.replace( ' ', '_' )
    sanitized = sanitized.replace( ',', '' )
    sanitized = sanitized.replace( '(', '' )
    sanitized = sanitized.replace( ')', '' )
    sanitized = sanitized.replace( '/', '_' )
    sanitized = sanitized.replace( "'", '' )
    sanitized = sanitized.replace( '"', '' )
    sanitized = sanitized.replace( ':', '' )
    sanitized = sanitized.replace( '-', '_' )
    sanitized = sanitized.replace( '.', '_' )

    while '__' in sanitized:
        sanitized = sanitized.replace( '__', '_' )

    sanitized = sanitized.strip( '_' )

    return sanitized


# ============================================================================
# New (MODE 3) functions: user input loader + resolver + filter
# ============================================================================

GG_ID_REGEX = re.compile( r'^gg(\d+)$', re.IGNORECASE )


def load_user_gene_groups( input_path, logger ):
    """
    Parse the user TSV.

    Schema:
        group_input_identifier  identifier_type  group_display_name  notes

    Allows '#'-prefixed comment lines.
    First non-comment line is the header.
    Empty `group_input_identifier` rows are rejected.

    Returns: list of dict (one per user entry).
    Fails fast (sys.exit(1)) if the file is empty or malformed.
    """

    if not input_path.exists():
        logger.error( f"CRITICAL ERROR: User gene-group file not found: {input_path}" )
        logger.error( "Provide the user-supplied TSV at ../../INPUT_user/user_gene_group_names.tsv" )
        sys.exit( 1 )

    entries = []
    header_seen = False
    header_fields = None
    required_fields = [ 'group_input_identifier', 'identifier_type' ]

    with open( input_path, 'r' ) as input_user:
        for raw_line in input_user:
            line = raw_line.rstrip( '\n' )
            if not line.strip():
                continue
            if line.lstrip().startswith( '#' ):
                continue

            if not header_seen:
                header_fields = line.split( '\t' )
                header_seen = True
                # Validate header
                missing = [ f for f in required_fields if f not in header_fields ]
                if missing:
                    logger.error( f"CRITICAL ERROR: User TSV header missing required column(s): {missing}" )
                    logger.error( f"Got header: {header_fields}" )
                    logger.error( f"Required: {required_fields}; optional: 'group_display_name', 'notes'" )
                    sys.exit( 1 )
                continue

            parts = line.split( '\t' )
            row = {}
            for i, field in enumerate( header_fields ):
                row[ field ] = parts[ i ] if i < len( parts ) else ''

            group_input_identifier = row.get( 'group_input_identifier', '' ).strip()
            if not group_input_identifier:
                logger.error( f"CRITICAL ERROR: Row with empty group_input_identifier: {row}" )
                sys.exit( 1 )

            identifier_type = row.get( 'identifier_type', 'auto' ).strip().lower() or 'auto'
            if identifier_type not in ( 'name', 'id', 'auto' ):
                logger.error( f"CRITICAL ERROR: Invalid identifier_type '{identifier_type}' (expected one of: name, id, auto). Row: {row}" )
                sys.exit( 1 )

            entries.append( {
                'group_input_identifier': group_input_identifier,
                'identifier_type': identifier_type,
                'group_display_name': row.get( 'group_display_name', '' ).strip(),
                'notes': row.get( 'notes', '' ).strip(),
            } )

    if not entries:
        logger.error( f"CRITICAL ERROR: User TSV contains no data rows: {input_path}" )
        sys.exit( 1 )

    logger.info( f"Loaded {len( entries )} user gene-group entries from: {input_path}" )
    return entries


def normalize_group_name( name ):
    """Lowercase + collapse internal whitespace + strip."""

    if name is None:
        return ''
    normalized = ' '.join( str( name ).lower().split() ).strip()
    return normalized


def build_name_to_family_id_index( family_identifiers___metadata ):
    """
    Build a map of normalized HGNC group name -> family_id.

    If two distinct HGNC family_ids share the same normalized name (rare),
    the first-seen wins and the duplicate is silently tolerated; the
    `family_identifiers___metadata` is the source of truth.
    """

    normalized_name___family_id = {}
    for family_id, metadata in family_identifiers___metadata.items():
        normalized = normalize_group_name( metadata[ 'name' ] )
        if normalized and normalized not in normalized_name___family_id:
            normalized_name___family_id[ normalized ] = family_id
    return normalized_name___family_id


def suggest_similar_names( normalized_query, family_identifiers___metadata, k = 5 ):
    """
    Find up to k 'did you mean...' candidates for a missed name query.

    Combines substring search + difflib.get_close_matches over the universe
    of HGNC group names. Returns a list of (family_id, original_name) tuples
    ranked by closeness; substring matches are prioritized.
    """

    family_id___original_name = { fid: m[ 'name' ] for fid, m in family_identifiers___metadata.items() }
    normalized___family_id = {}
    for fid, m in family_identifiers___metadata.items():
        normalized___family_id.setdefault( normalize_group_name( m[ 'name' ] ), fid )

    suggestions = []
    seen_family_ids = set()

    # Substring search first (case-insensitive on normalized form).
    for normalized_name, family_id in normalized___family_id.items():
        if normalized_query and normalized_query in normalized_name:
            if family_id not in seen_family_ids:
                suggestions.append( ( family_id, family_id___original_name[ family_id ] ) )
                seen_family_ids.add( family_id )
                if len( suggestions ) >= k:
                    return suggestions

    # difflib top-k for the remainder.
    remaining = k - len( suggestions )
    if remaining > 0 and normalized_query:
        candidates = list( normalized___family_id.keys() )
        close = difflib.get_close_matches( normalized_query, candidates, n = remaining, cutoff = 0.6 )
        for normalized_name in close:
            family_id = normalized___family_id[ normalized_name ]
            if family_id not in seen_family_ids:
                suggestions.append( ( family_id, family_id___original_name[ family_id ] ) )
                seen_family_ids.add( family_id )

    return suggestions


def resolve_user_groups_to_family_ids( user_entries, family_identifiers___metadata, name_index, logger ):
    """
    Resolve each user entry to a family_id.

    For identifier_type:
        'id'   - strip 'gg' prefix, int(), look up in family_identifiers___metadata
        'name' - normalize, look up in name_index (case-insensitive exact)
        'auto' - if /^gg\\d+$/ match -> treat as id; else treat as name

    Returns: ( list_of_resolved_dicts, list_of_unresolved_dicts )

    Each resolved dict carries:
        user_entry fields + 'resolved_family_id' (int), 'resolved_name' (str),
        'sanitized_name' (str), 'resolution_status' (str)

    Each unresolved dict carries:
        user_entry fields + 'suggestions' (list of (family_id, name) tuples)
    """

    resolved = []
    unresolved = []

    for entry in user_entries:
        raw_identifier = entry[ 'group_input_identifier' ]
        identifier_type = entry[ 'identifier_type' ]

        effective_type = identifier_type
        if identifier_type == 'auto':
            if GG_ID_REGEX.match( raw_identifier ):
                effective_type = 'id'
            else:
                effective_type = 'name'

        resolved_family_id = None
        resolution_status = None

        if effective_type == 'id':
            match = GG_ID_REGEX.match( raw_identifier )
            if not match:
                # Looks like an id was forced but doesn't match pattern.
                logger.warning( f"identifier_type='id' but '{raw_identifier}' does not match /^gg\\d+$/ pattern" )
            else:
                try:
                    family_id_candidate = int( match.group( 1 ) )
                    if family_id_candidate in family_identifiers___metadata:
                        resolved_family_id = family_id_candidate
                        resolution_status = 'ID_MATCH'
                except ValueError:
                    pass

        elif effective_type == 'name':
            normalized = normalize_group_name( raw_identifier )
            if normalized in name_index:
                resolved_family_id = name_index[ normalized ]
                # Distinguish exact (byte-for-byte) vs case-insensitive match
                original_name = family_identifiers___metadata[ resolved_family_id ][ 'name' ]
                if raw_identifier == original_name:
                    resolution_status = 'NAME_MATCH_EXACT'
                else:
                    resolution_status = 'NAME_MATCH_CASE_INSENSITIVE'

        if resolved_family_id is not None:
            metadata = family_identifiers___metadata[ resolved_family_id ]
            resolved.append( {
                **entry,
                'resolved_family_id': resolved_family_id,
                'resolved_name': metadata[ 'name' ],
                'sanitized_name': sanitize_family_name( metadata[ 'name' ] ),
                'resolution_status': resolution_status,
            } )
        else:
            # Build suggestions for the user.
            normalized_query = normalize_group_name( raw_identifier )
            suggestions = suggest_similar_names( normalized_query, family_identifiers___metadata, k = 5 )
            unresolved.append( {
                **entry,
                'suggestions': suggestions,
            } )

    return resolved, unresolved


def filter_aggregated_sets_by_family_ids( family_identifiers___aggregated_gene_symbols, resolved_family_ids ):
    """Return the aggregated dict filtered to only resolved_family_ids."""

    return {
        family_id: symbols
        for family_id, symbols in family_identifiers___aggregated_gene_symbols.items()
        if family_id in resolved_family_ids
    }


# ============================================================================
# Output writers
# ============================================================================

def write_aggregated_gene_sets_tsv( output_path, resolved_family_ids, family_identifiers___metadata, family_identifiers___gene_symbols, family_identifiers___aggregated_gene_symbols, logger ):
    """
    Write 2_ai-aggregated_gene_sets.tsv with the SAME column layout as MODE 1
    so script 003 can be reused verbatim. Filtered to the user's groups.
    """

    # Gene_Group_ID  Gene_Group_Name  Sanitized_Name  Direct_Gene_Count  Aggregated_Gene_Count  Gene_Symbols
    with open( output_path, 'w' ) as output_aggregated:
        output = 'Gene_Group_ID (HGNC family ID with gg prefix)' + '\t'
        output += 'Gene_Group_Name (HGNC family name)' + '\t'
        output += 'Sanitized_Name (filesystem safe lowercase name)' + '\t'
        output += 'Direct_Gene_Count (genes directly assigned to this group)' + '\t'
        output += 'Aggregated_Gene_Count (total genes including all descendant groups)' + '\t'
        output += 'Gene_Symbols (comma delimited list of approved gene symbols)' + '\n'
        output_aggregated.write( output )

        for family_id in sorted( resolved_family_ids ):
            metadata = family_identifiers___metadata[ family_id ]
            aggregated_symbols = family_identifiers___aggregated_gene_symbols.get( family_id, set() )
            direct_symbols = family_identifiers___gene_symbols.get( family_id, set() )
            sanitized_name = sanitize_family_name( metadata[ 'name' ] )

            if len( aggregated_symbols ) == 0:
                # Per MODE 1 convention: groups with zero aggregated genes are
                # excluded from the aggregated TSV (script 003 would skip them
                # anyway because no proteome matches are possible).
                logger.warning( f"User-requested group gg{family_id} '{metadata[ 'name' ]}' has zero aggregated gene symbols under the current locus-type filter; omitting from aggregated TSV." )
                continue

            sorted_symbols = sorted( aggregated_symbols )

            output = f"gg{family_id}" + '\t'
            output += metadata[ 'name' ] + '\t'
            output += sanitized_name + '\t'
            output += str( len( direct_symbols ) ) + '\t'
            output += str( len( aggregated_symbols ) ) + '\t'
            output += ','.join( sorted_symbols ) + '\n'
            output_aggregated.write( output )

    logger.info( f"Wrote filtered aggregated gene sets: {output_path}" )


def write_gene_group_metadata_tsv( output_path, resolved_family_ids, family_identifiers___metadata, family_identifiers___gene_symbols, family_identifiers___aggregated_gene_symbols, parent_identifiers___descendant_identifiers, logger ):
    """Write 2_ai-gene_group_metadata.tsv (filtered to user groups)."""

    with open( output_path, 'w' ) as output_metadata:
        output = 'Gene_Group_ID (HGNC family ID with gg prefix)' + '\t'
        output += 'Gene_Group_Name (HGNC family name)' + '\t'
        output += 'Sanitized_Name (filesystem safe lowercase name)' + '\t'
        output += 'Abbreviation (HGNC abbreviation if available)' + '\t'
        output += 'Typical_Gene (representative gene symbol)' + '\t'
        output += 'Direct_Gene_Count (genes directly assigned to this group)' + '\t'
        output += 'Aggregated_Gene_Count (total genes including all descendant groups)' + '\t'
        output += 'Has_Descendants (whether this group has subgroups)' + '\n'
        output_metadata.write( output )

        for family_id in sorted( resolved_family_ids ):
            metadata = family_identifiers___metadata[ family_id ]
            aggregated_symbols = family_identifiers___aggregated_gene_symbols.get( family_id, set() )
            direct_symbols = family_identifiers___gene_symbols.get( family_id, set() )
            sanitized_name = sanitize_family_name( metadata[ 'name' ] )
            has_descendants = family_id in parent_identifiers___descendant_identifiers

            output = f"gg{family_id}" + '\t'
            output += metadata[ 'name' ] + '\t'
            output += sanitized_name + '\t'
            output += metadata[ 'abbreviation' ] + '\t'
            output += metadata[ 'typical_gene' ] + '\t'
            output += str( len( direct_symbols ) ) + '\t'
            output += str( len( aggregated_symbols ) ) + '\t'
            output += ( 'yes' if has_descendants else 'no' ) + '\n'
            output_metadata.write( output )

    logger.info( f"Wrote filtered gene group metadata: {output_path}" )


def write_resolved_user_groups_tsv( output_path, resolved_entries, logger ):
    """Write 2_ai-resolved_user_groups.tsv (per-user-entry resolution trail)."""

    with open( output_path, 'w' ) as output_resolved:
        output = 'group_input_identifier (what the user typed)' + '\t'
        output += 'identifier_type (name | id | auto)' + '\t'
        output += 'resolved_family_id (gg<N>; HGNC family id)' + '\t'
        output += 'resolved_hgnc_group_name (canonical HGNC group name)' + '\t'
        output += 'group_display_name (user-provided label; empty -> resolved name used downstream)' + '\t'
        output += 'sanitized_name (filesystem-safe lowercase name used in RGS filenames)' + '\t'
        output += 'resolution_status (ID_MATCH | NAME_MATCH_EXACT | NAME_MATCH_CASE_INSENSITIVE)' + '\t'
        output += 'notes (user-provided free text; preserved for lab-notebook)' + '\n'
        output_resolved.write( output )

        for entry in resolved_entries:
            output = entry[ 'group_input_identifier' ] + '\t'
            output += entry[ 'identifier_type' ] + '\t'
            output += f"gg{entry[ 'resolved_family_id' ]}" + '\t'
            output += entry[ 'resolved_name' ] + '\t'
            output += entry[ 'group_display_name' ] + '\t'
            output += entry[ 'sanitized_name' ] + '\t'
            output += entry[ 'resolution_status' ] + '\t'
            output += entry[ 'notes' ] + '\n'
            output_resolved.write( output )

    logger.info( f"Wrote resolved user groups: {output_path}" )


def write_unresolved_groups_tsv( output_path, unresolved_entries, logger ):
    """Write 2_ai-unresolved_groups.tsv (only when any group failed resolution)."""

    with open( output_path, 'w' ) as output_unresolved:
        output = 'group_input_identifier (what the user typed)' + '\t'
        output += 'identifier_type (name | id | auto)' + '\t'
        output += 'group_display_name (optional user label)' + '\t'
        output += 'notes (user-provided free text)' + '\t'
        output += 'suggestions (semicolon-delimited gg<N>:<name> did-you-mean candidates)' + '\n'
        output_unresolved.write( output )

        for entry in unresolved_entries:
            suggestion_strings = [ f"gg{fid}:{name}" for fid, name in entry[ 'suggestions' ] ]
            output = entry[ 'group_input_identifier' ] + '\t'
            output += entry[ 'identifier_type' ] + '\t'
            output += entry[ 'group_display_name' ] + '\t'
            output += entry[ 'notes' ] + '\t'
            output += '; '.join( suggestion_strings ) + '\n'
            output_unresolved.write( output )

    logger.error( f"Wrote unresolved groups: {output_path}" )


def write_hgnc_group_catalog_tsv( output_path, family_identifiers___metadata, family_identifiers___gene_symbols, family_identifiers___aggregated_gene_symbols, parent_identifiers___descendant_identifiers, logger ):
    """
    Write 2_ai-hgnc_group_catalog.tsv -- all HGNC groups with sanitized names,
    aggregated gene counts, and the protein-coding-purity flag, so the user
    can grep for the right name on future runs.
    """

    with open( output_path, 'w' ) as output_catalog:
        output = 'HGNC_Group_ID (gg<N>)' + '\t'
        output += 'HGNC_Group_Name (canonical HGNC group name)' + '\t'
        output += 'Sanitized_Name (filesystem-safe lowercase name)' + '\t'
        output += 'Direct_Gene_Count (allowed-locus-type genes directly assigned)' + '\t'
        output += 'Aggregated_Gene_Count (including descendants)' + '\t'
        output += 'Has_Descendants (yes|no)' + '\n'
        output_catalog.write( output )

        for family_id in sorted( family_identifiers___metadata.keys() ):
            metadata = family_identifiers___metadata[ family_id ]
            sanitized_name = sanitize_family_name( metadata[ 'name' ] )
            direct_count = len( family_identifiers___gene_symbols.get( family_id, set() ) )
            aggregated_count = len( family_identifiers___aggregated_gene_symbols.get( family_id, set() ) )
            has_descendants = family_id in parent_identifiers___descendant_identifiers

            output = f"gg{family_id}" + '\t'
            output += metadata[ 'name' ] + '\t'
            output += sanitized_name + '\t'
            output += str( direct_count ) + '\t'
            output += str( aggregated_count ) + '\t'
            output += ( 'yes' if has_descendants else 'no' ) + '\n'
            output_catalog.write( output )

    logger.info( f"Wrote HGNC group catalog: {output_path}" )


def write_filter_policy_tsv( output_path, allowed_locus_types, include_pseudogenes, include_non_protein_coding, logger ):
    """Single-row record of the locus-type allowlist actually used this run."""

    with open( output_path, 'w' ) as output_policy:
        output = 'include_pseudogenes (CLI flag)' + '\t'
        output += 'include_non_protein_coding (CLI flag)' + '\t'
        output += 'allowed_locus_types (semicolon-delimited list)' + '\t'
        output += 'allowed_locus_type_count' + '\n'
        output_policy.write( output )

        output = str( include_pseudogenes ).lower() + '\t'
        output += str( include_non_protein_coding ).lower() + '\t'
        output += '; '.join( sorted( allowed_locus_types ) ) + '\t'
        output += str( len( allowed_locus_types ) ) + '\n'
        output_policy.write( output )

    logger.info( f"Wrote filter policy record: {output_path}" )


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Filter HGNC aggregated gene sets by user-supplied group names/IDs (with optional locus-type expansion).'
    )
    parser.add_argument( '--input-directory', required=True, help='Directory containing downloaded HGNC data (1-output from script 001)' )
    parser.add_argument( '--input-user-gene-groups', required=True, help='Path to user-supplied user_gene_group_names.tsv (instance-level)' )
    parser.add_argument( '--include-pseudogenes', action='store_true', default=False, help='Include locus type "pseudogene" in the allowlist (default: False)' )
    parser.add_argument( '--include-non-protein-coding', action='store_true', default=False, help='Include RNA / Ig / TR / readthrough / ERV locus types in the allowlist (default: False)' )
    parser.add_argument( '--output-directory', required=True, help='Directory to write output files (2-output)' )
    parser.add_argument( '--log-file', default=None, help='Path to log file' )
    arguments = parser.parse_args()

    input_directory = Path( arguments.input_directory )
    input_user_gene_groups_path = Path( arguments.input_user_gene_groups )
    output_directory = Path( arguments.output_directory )
    output_directory.mkdir( parents=True, exist_ok=True )

    if arguments.log_file:
        log_file_path = Path( arguments.log_file )
    else:
        log_file_path = output_directory / '2_ai-log-filter_aggregated_gene_sets_by_user_names.log'
    log_file_path.parent.mkdir( parents=True, exist_ok=True )
    logger = setup_logging( log_file_path )

    logger.info( "=" * 70 )
    logger.info( "Filter HGNC Aggregated Gene Sets by User-Supplied Group Names/IDs" )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Input directory (1-output): {input_directory}" )
    logger.info( f"Input user gene-groups TSV: {input_user_gene_groups_path}" )
    logger.info( f"Output directory: {output_directory}" )
    logger.info( f"--include-pseudogenes: {arguments.include_pseudogenes}" )
    logger.info( f"--include-non-protein-coding: {arguments.include_non_protein_coding}" )
    logger.info( "=" * 70 )

    # ---- Validate input files exist ----
    required_files = [ 'family.csv', 'hierarchy_closure.csv', 'hgnc_gene_groups_all.tsv' ]
    for filename in required_files:
        filepath = input_directory / filename
        if not filepath.exists():
            logger.error( f"CRITICAL ERROR: Required HGNC file not found: {filepath}" )
            logger.error( "Run script 001 (download HGNC data) first." )
            sys.exit( 1 )

    # ---- Build the locus-type allowlist from CLI flags ----
    allowed_locus_types = set( DEFAULT_PROTEIN_CODING_LOCUS_TYPES )
    if arguments.include_pseudogenes:
        allowed_locus_types |= PSEUDOGENE_LOCUS_TYPES
        logger.warning( "include_pseudogenes=True -- pseudogenes will be included in the RGS." )
    if arguments.include_non_protein_coding:
        allowed_locus_types |= NON_PROTEIN_CODING_LOCUS_TYPES
        logger.warning( "include_non_protein_coding=True -- RNA / Ig / TR / readthrough / ERV loci will be included." )

    logger.info( f"Final locus-type allowlist ({len( allowed_locus_types )} types):" )
    for locus_type in sorted( allowed_locus_types ):
        logger.info( f"  - {locus_type}" )

    # ---- Load HGNC reference data ----
    family_identifiers___metadata = load_family_metadata( input_directory / 'family.csv', logger )
    parent_identifiers___descendant_identifiers = load_hierarchy_closure( input_directory / 'hierarchy_closure.csv', logger )
    family_identifiers___gene_symbols = load_direct_gene_symbols( input_directory / 'hgnc_gene_groups_all.tsv', allowed_locus_types, logger )

    # ---- Build aggregated gene sets across ALL HGNC groups (cheap; we filter after) ----
    family_identifiers___aggregated_gene_symbols = build_aggregated_gene_sets(
        family_identifiers___metadata,
        parent_identifiers___descendant_identifiers,
        family_identifiers___gene_symbols,
        logger,
    )

    # ---- Always write the HGNC group catalog (helps users find the right name) ----
    catalog_path = output_directory / '2_ai-hgnc_group_catalog.tsv'
    write_hgnc_group_catalog_tsv(
        catalog_path,
        family_identifiers___metadata,
        family_identifiers___gene_symbols,
        family_identifiers___aggregated_gene_symbols,
        parent_identifiers___descendant_identifiers,
        logger,
    )

    # ---- Always write the filter-policy record (lab notebook trail) ----
    policy_path = output_directory / '2_ai-filter_policy.tsv'
    write_filter_policy_tsv(
        policy_path,
        allowed_locus_types,
        arguments.include_pseudogenes,
        arguments.include_non_protein_coding,
        logger,
    )

    # ---- Load and resolve user gene-group entries ----
    user_entries = load_user_gene_groups( input_user_gene_groups_path, logger )
    name_index = build_name_to_family_id_index( family_identifiers___metadata )
    resolved_entries, unresolved_entries = resolve_user_groups_to_family_ids(
        user_entries,
        family_identifiers___metadata,
        name_index,
        logger,
    )

    logger.info( "" )
    logger.info( f"Resolution results: {len( resolved_entries )} resolved, {len( unresolved_entries )} unresolved" )
    for entry in resolved_entries:
        logger.info( f"  RESOLVED  '{entry[ 'group_input_identifier' ]}' ({entry[ 'identifier_type' ]}) -> gg{entry[ 'resolved_family_id' ]} '{entry[ 'resolved_name' ]}' [{entry[ 'resolution_status' ]}]" )
    for entry in unresolved_entries:
        logger.error( f"  UNRESOLVED '{entry[ 'group_input_identifier' ]}' ({entry[ 'identifier_type' ]})" )
        for fid, name in entry[ 'suggestions' ]:
            logger.error( f"      did you mean: gg{fid} '{name}' ?" )

    # ---- Fail-fast if any user entry didn't resolve ----
    if unresolved_entries:
        unresolved_path = output_directory / '2_ai-unresolved_groups.tsv'
        write_unresolved_groups_tsv( unresolved_path, unresolved_entries, logger )
        logger.error( "" )
        logger.error( "CRITICAL ERROR: One or more user-supplied gene groups could not be resolved to an HGNC family id." )
        logger.error( f"See {unresolved_path} for the failed entries and 'did you mean' candidates." )
        logger.error( f"See {catalog_path} for the full HGNC group catalog (grep for the correct name)." )
        sys.exit( 1 )

    # ---- Write resolution trail ----
    resolved_path = output_directory / '2_ai-resolved_user_groups.tsv'
    write_resolved_user_groups_tsv( resolved_path, resolved_entries, logger )

    # ---- Filter aggregated dict to the user's groups, then write outputs ----
    resolved_family_ids = { entry[ 'resolved_family_id' ] for entry in resolved_entries }

    aggregated_output_path = output_directory / '2_ai-aggregated_gene_sets.tsv'
    write_aggregated_gene_sets_tsv(
        aggregated_output_path,
        resolved_family_ids,
        family_identifiers___metadata,
        family_identifiers___gene_symbols,
        family_identifiers___aggregated_gene_symbols,
        logger,
    )

    metadata_output_path = output_directory / '2_ai-gene_group_metadata.tsv'
    write_gene_group_metadata_tsv(
        metadata_output_path,
        resolved_family_ids,
        family_identifiers___metadata,
        family_identifiers___gene_symbols,
        family_identifiers___aggregated_gene_symbols,
        parent_identifiers___descendant_identifiers,
        logger,
    )

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( f"Completed: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"User groups resolved: {len( resolved_entries )}" )
    logger.info( f"Aggregated TSV written: {aggregated_output_path}" )
    logger.info( "=" * 70 )


if __name__ == '__main__':
    main()
