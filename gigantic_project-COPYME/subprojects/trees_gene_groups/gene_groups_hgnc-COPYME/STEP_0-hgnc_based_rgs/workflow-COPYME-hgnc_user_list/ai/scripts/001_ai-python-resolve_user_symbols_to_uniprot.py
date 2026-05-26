#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 17:00 | Purpose: Resolve user-supplied human gene symbols to UniProt accessions via HGNC complete_set (with alias/prev_symbol fallback)
# Human: Eric Edsinger

"""
Resolve user-supplied human gene symbols to UniProt accessions.

Reads:
    user_gene_set.tsv       (instance-level INPUT_user; defines groups + symbols)
    hgnc_complete_set.txt   (subproject-level reference; provides symbol → uniprot_ids)

Writes:
    1_ai-resolved_symbols.tsv  (resolved manifest with uniprot accessions per gene)

Resolution strategy (per user symbol):
    1. Direct match on HGNC `symbol` column → DIRECT_MATCH
    2. Match on `alias_symbol` column (pipe-delimited) → ALIAS_MATCH
    3. Match on `prev_symbol` column (pipe-delimited) → PREV_SYMBOL_MATCH
    4. Otherwise → FAIL FAST (the user must fix the input; the workflow refuses
       to emit a partial RGS).

Multi-UniProt handling:
    HGNC's `uniprot_ids` column is pipe-delimited when a gene has multiple
    UniProt entries. The FIRST listed entry is the canonical Swiss-Prot record
    in nearly every case; we use it for the RGS but record the full list in
    the manifest for transparency.

Usage:
    python3 001_ai-python-resolve_user_symbols_to_uniprot.py \\
        --input-user-gene-set <path-to-user_gene_set.tsv> \\
        --input-hgnc-complete-set <path-to-hgnc_complete_set.txt> \\
        --output-directory 1-output \\
        --log-file 1-output/1_ai-log-resolve_user_symbols_to_uniprot.log
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging( log_file_path ):
    """Configure logging to both file and console."""

    logger = logging.getLogger( 'resolve_user_symbols_to_uniprot' )
    logger.setLevel( logging.INFO )
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


def load_user_gene_set( input_path, logger ):
    """Parse the user gene set TSV. Returns a list of (group_sanitized, group_display, gene_symbol) tuples.

    Format:
        # comment lines allowed
        group_sanitized_name<TAB>group_display_name<TAB>gene_symbol
        snap_family<TAB>Synaptosomal-Associated Proteins<TAB>SNAP23
    """

    # group_sanitized_name	group_display_name	gene_symbol
    # snap_family	Synaptosomal-Associated Proteins	SNAP23
    entries = []
    header_seen = False

    with open( input_path, 'r' ) as input_user_gene_set:
        for line in input_user_gene_set:
            line = line.rstrip( '\n' )

            if not line.strip():
                continue
            if line.lstrip().startswith( '#' ):
                continue

            parts = line.split( '\t' )

            if not header_seen:
                if len( parts ) < 3:
                    logger.error( f"CRITICAL ERROR: header must have at least 3 tab-separated columns; got: {parts}" )
                    sys.exit( 1 )
                if parts[ 0 ].lower() != 'group_sanitized_name':
                    logger.error( f"CRITICAL ERROR: first header column must be 'group_sanitized_name'; got: {parts[ 0 ]}" )
                    sys.exit( 1 )
                header_seen = True
                continue

            if len( parts ) < 3:
                logger.warning( f"Skipping malformed row (< 3 columns): {line!r}" )
                continue

            group_sanitized = parts[ 0 ].strip()
            group_display = parts[ 1 ].strip()
            gene_symbol = parts[ 2 ].strip()

            if not group_sanitized or not gene_symbol:
                logger.warning( f"Skipping row with empty group_sanitized_name or gene_symbol: {line!r}" )
                continue

            entries.append( ( group_sanitized, group_display, gene_symbol ) )

    if not entries:
        logger.error( "CRITICAL ERROR: No gene entries parsed from user_gene_set.tsv." )
        logger.error( f"Path: {input_path}" )
        logger.error( "Check the file contains a header row + at least one data row." )
        sys.exit( 1 )

    return entries


def load_hgnc_complete_set( hgnc_path, logger ):
    """Parse hgnc_complete_set.txt into three lookup dicts.

    Returns:
        symbols___records          dict: approved symbol → record dict
        aliases___canonical_symbols dict: alias symbol → canonical approved symbol
        prev_symbols___canonical_symbols dict: prev symbol → canonical approved symbol

    Each `record` dict contains: hgnc_id, symbol, uniprot_ids (as list).
    """

    # hgnc_id<tab>symbol<tab>...alias_symbol...prev_symbol...uniprot_ids...
    # HGNC:5	A1BG	...
    symbols___records = {}
    aliases___canonical_symbols = {}
    prev_symbols___canonical_symbols = {}

    with open( hgnc_path, 'r' ) as input_hgnc_complete_set:
        header_line = input_hgnc_complete_set.readline().rstrip( '\n' )
        parts_header = header_line.split( '\t' )

        try:
            idx_hgnc_id = parts_header.index( 'hgnc_id' )
            idx_symbol = parts_header.index( 'symbol' )
            idx_alias_symbol = parts_header.index( 'alias_symbol' )
            idx_prev_symbol = parts_header.index( 'prev_symbol' )
            idx_uniprot_ids = parts_header.index( 'uniprot_ids' )
        except ValueError as e:
            logger.error( f"CRITICAL ERROR: required column missing from hgnc_complete_set.txt header: {e}" )
            logger.error( f"Header columns found: {parts_header[ :10 ]}..." )
            sys.exit( 1 )

        for line in input_hgnc_complete_set:
            line = line.rstrip( '\n' )
            parts = line.split( '\t' )

            if len( parts ) <= idx_uniprot_ids:
                continue

            hgnc_id = parts[ idx_hgnc_id ]
            symbol = parts[ idx_symbol ]
            alias_field = parts[ idx_alias_symbol ]
            prev_field = parts[ idx_prev_symbol ]
            uniprot_field = parts[ idx_uniprot_ids ]

            if not symbol:
                continue

            uniprot_accessions = [ token.strip() for token in uniprot_field.split( '|' ) if token.strip() ] if uniprot_field else []

            record = {
                'hgnc_id': hgnc_id,
                'symbol': symbol,
                'uniprot_accessions': uniprot_accessions,
            }

            symbols___records[ symbol ] = record

            if alias_field:
                for alias in alias_field.split( '|' ):
                    alias_token = alias.strip()
                    if alias_token and alias_token not in aliases___canonical_symbols:
                        aliases___canonical_symbols[ alias_token ] = symbol

            if prev_field:
                for prev in prev_field.split( '|' ):
                    prev_token = prev.strip()
                    if prev_token and prev_token not in prev_symbols___canonical_symbols:
                        prev_symbols___canonical_symbols[ prev_token ] = symbol

    logger.info( f"Loaded {len( symbols___records ):,} canonical HGNC symbols" )
    logger.info( f"Loaded {len( aliases___canonical_symbols ):,} alias mappings" )
    logger.info( f"Loaded {len( prev_symbols___canonical_symbols ):,} prev_symbol mappings" )

    return symbols___records, aliases___canonical_symbols, prev_symbols___canonical_symbols


def resolve_symbol( user_symbol, symbols___records, aliases___canonical_symbols, prev_symbols___canonical_symbols ):
    """Resolve a user-supplied symbol to a canonical HGNC record + status.

    Returns ( canonical_symbol, record, status ) or ( None, None, 'NOT_FOUND' ).
    """

    if user_symbol in symbols___records:
        return user_symbol, symbols___records[ user_symbol ], 'DIRECT_MATCH'

    if user_symbol in aliases___canonical_symbols:
        canonical = aliases___canonical_symbols[ user_symbol ]
        return canonical, symbols___records.get( canonical ), 'ALIAS_MATCH'

    if user_symbol in prev_symbols___canonical_symbols:
        canonical = prev_symbols___canonical_symbols[ user_symbol ]
        return canonical, symbols___records.get( canonical ), 'PREV_SYMBOL_MATCH'

    return None, None, 'NOT_FOUND'


def main():
    parser = argparse.ArgumentParser(
        description = "Resolve user gene symbols to UniProt accessions via HGNC complete_set."
    )
    parser.add_argument( '--input-user-gene-set', required=True )
    parser.add_argument( '--input-hgnc-complete-set', required=True )
    parser.add_argument( '--output-directory', required=True )
    parser.add_argument( '--log-file', default=None )
    arguments = parser.parse_args()

    output_directory = Path( arguments.output_directory )
    output_directory.mkdir( parents=True, exist_ok=True )

    log_file_path = (
        Path( arguments.log_file )
        if arguments.log_file
        else output_directory / '1_ai-log-resolve_user_symbols_to_uniprot.log'
    )
    log_file_path.parent.mkdir( parents=True, exist_ok=True )

    logger = setup_logging( log_file_path )

    logger.info( "=" * 70 )
    logger.info( "Resolve User Symbols to UniProt Accessions" )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"User gene set:  {arguments.input_user_gene_set}" )
    logger.info( f"HGNC reference: {arguments.input_hgnc_complete_set}" )
    logger.info( f"Output dir:     {output_directory}" )
    logger.info( "=" * 70 )

    user_entries = load_user_gene_set( Path( arguments.input_user_gene_set ), logger )
    logger.info( f"Parsed {len( user_entries )} (group, symbol) entries from user gene set" )

    symbols___records, aliases___canonical_symbols, prev_symbols___canonical_symbols = load_hgnc_complete_set(
        Path( arguments.input_hgnc_complete_set ), logger
    )

    resolution_rows = []
    unresolved = []
    no_uniprot = []
    alias_resolved = []
    prev_resolved = []

    for group_sanitized, group_display, user_symbol in user_entries:
        canonical_symbol, record, status = resolve_symbol(
            user_symbol,
            symbols___records,
            aliases___canonical_symbols,
            prev_symbols___canonical_symbols,
        )

        if status == 'NOT_FOUND':
            unresolved.append( ( group_sanitized, user_symbol ) )
            logger.error( f"  NOT_FOUND: {user_symbol} (group: {group_sanitized})" )
            continue

        if not record or not record[ 'uniprot_accessions' ]:
            no_uniprot.append( ( group_sanitized, user_symbol, canonical_symbol ) )
            logger.error( f"  NO_UNIPROT: {user_symbol} (group: {group_sanitized}) resolved to {canonical_symbol} but no uniprot_ids in HGNC" )
            continue

        if status == 'ALIAS_MATCH':
            alias_resolved.append( ( group_sanitized, user_symbol, canonical_symbol ) )
            logger.warning( f"  ALIAS_MATCH: user provided '{user_symbol}', HGNC canonical is '{canonical_symbol}' (group: {group_sanitized})" )
        elif status == 'PREV_SYMBOL_MATCH':
            prev_resolved.append( ( group_sanitized, user_symbol, canonical_symbol ) )
            logger.warning( f"  PREV_SYMBOL_MATCH: user provided '{user_symbol}', HGNC canonical is '{canonical_symbol}' (group: {group_sanitized})" )

        canonical_uniprot = record[ 'uniprot_accessions' ][ 0 ]
        all_uniprots = ','.join( record[ 'uniprot_accessions' ] )

        resolution_rows.append( {
            'group_sanitized_name': group_sanitized,
            'group_display_name': group_display,
            'input_gene_symbol': user_symbol,
            'resolved_gene_symbol': canonical_symbol,
            'hgnc_id': record[ 'hgnc_id' ],
            'uniprot_accession_canonical': canonical_uniprot,
            'uniprot_accessions_all': all_uniprots,
            'resolution_status': status,
        } )

    logger.info( "" )
    logger.info( f"Resolved: {len( resolution_rows )} / {len( user_entries )}" )
    logger.info( f"  Direct matches:       {sum( 1 for r in resolution_rows if r[ 'resolution_status' ] == 'DIRECT_MATCH' )}" )
    logger.info( f"  Alias matches:        {len( alias_resolved )}" )
    logger.info( f"  Prev_symbol matches:  {len( prev_resolved )}" )
    logger.info( f"  NOT_FOUND:            {len( unresolved )}" )
    logger.info( f"  NO_UNIPROT:           {len( no_uniprot )}" )

    if unresolved or no_uniprot:
        logger.error( "" )
        logger.error( "CRITICAL ERROR: One or more user symbols could not be resolved to a UniProt accession." )
        if unresolved:
            logger.error( f"NOT_FOUND ({len( unresolved )}):" )
            for group_sanitized, user_symbol in unresolved:
                logger.error( f"  group={group_sanitized}  symbol={user_symbol}" )
            logger.error( "  → Check the symbol spelling; consult https://www.genenames.org/ for the current HGNC-approved name." )
        if no_uniprot:
            logger.error( f"NO_UNIPROT ({len( no_uniprot )}):" )
            for group_sanitized, user_symbol, canonical in no_uniprot:
                logger.error( f"  group={group_sanitized}  input={user_symbol}  canonical={canonical}" )
            logger.error( "  → These HGNC entries have no UniProt cross-reference (often non-protein-coding loci or pseudogenes). Remove them from user_gene_set.tsv or substitute a protein-coding family member." )
        sys.exit( 1 )

    output_path = output_directory / '1_ai-resolved_symbols.tsv'

    # Self-documenting header per GIGANTIC convention.
    output = 'Group_Sanitized_Name (filesystem-safe group identifier from user input)' + '\t'
    output += 'Group_Display_Name (human-readable group description from user input)' + '\t'
    output += 'Input_Gene_Symbol (the symbol as provided by the user)' + '\t'
    output += 'Resolved_Gene_Symbol (canonical HGNC-approved symbol; same as input unless alias-resolved)' + '\t'
    output += 'HGNC_ID (HGNC database identifier; HGNC:NNNN)' + '\t'
    output += 'UniProt_Accession_Canonical (first entry in HGNC uniprot_ids list; typically the Swiss-Prot canonical record)' + '\t'
    output += 'UniProt_Accessions_All (comma delimited full list of UniProt accessions associated with this HGNC entry)' + '\t'
    output += 'Resolution_Status (DIRECT_MATCH, ALIAS_MATCH, or PREV_SYMBOL_MATCH)' + '\n'

    with open( output_path, 'w' ) as output_resolved_symbols:
        output_resolved_symbols.write( output )

        for row in resolution_rows:
            row_output = row[ 'group_sanitized_name' ] + '\t'
            row_output += row[ 'group_display_name' ] + '\t'
            row_output += row[ 'input_gene_symbol' ] + '\t'
            row_output += row[ 'resolved_gene_symbol' ] + '\t'
            row_output += row[ 'hgnc_id' ] + '\t'
            row_output += row[ 'uniprot_accession_canonical' ] + '\t'
            row_output += row[ 'uniprot_accessions_all' ] + '\t'
            row_output += row[ 'resolution_status' ] + '\n'
            output_resolved_symbols.write( row_output )

    logger.info( "" )
    logger.info( f"Resolved-symbols manifest written: {output_path}" )
    logger.info( "=" * 70 )
    logger.info( "Resolution complete." )
    logger.info( "=" * 70 )


if __name__ == '__main__':
    main()
