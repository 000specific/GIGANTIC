#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 17:20 | Purpose: Fetch canonical Swiss-Prot FASTA from UniProt REST per resolved accession; emit per-group RGS FASTAs with GIGANTIC 5-field headers
# Human: Eric Edsinger

"""
Fetch UniProt FASTA sequences and emit per-group RGS FASTAs.

Reads:
    1_ai-resolved_symbols.tsv  (from script 001; one row per resolved symbol)

Writes:
    rgs_fastas/rgs_hgnc_user-human-<group>.aa   (one FASTA per group)
    2_ai-rgs_generation_manifest.tsv             (per-gene fetch record)
    2_ai-rgs_generation_summary.tsv              (per-group summary; STEP_1
                                                  orchestrator reads this to
                                                  iterate over gene groups,
                                                  using the same column layout
                                                  that workflow-hgnc_database
                                                  emits at script 003.)

Per-sequence header (GIGANTIC 5-field convention, parsed by STEP_1):
    >rgs_<group_sanitized>-human-<symbol>-uniprot-<uniprot_accession>

UniProt API:
    GET https://rest.uniprot.org/uniprotkb/<accession>.fasta
    No auth required. Polite User-Agent + small inter-request delay.
    3 retries with exponential backoff on transient errors.

Failure semantics:
    The pipeline fails fast (sys.exit 1) if any FASTA fetch fails after
    retries. We never emit a partial RGS — STEP_1 downstream assumes the RGS
    is complete.

Usage:
    python3 002_ai-python-fetch_uniprot_fastas-emit_rgs.py \\
        --input-resolved-symbols <path-to-1_ai-resolved_symbols.tsv> \\
        --output-directory 2-output \\
        --log-file 2-output/2_ai-log-fetch_uniprot_fastas-emit_rgs.log
"""

import argparse
import logging
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


UNIPROT_FASTA_URL_TEMPLATE = "https://rest.uniprot.org/uniprotkb/{accession}.fasta"
USER_AGENT = "GIGANTIC-trees_gene_groups/1.0 (https://github.com/) python-urllib"
REQUEST_TIMEOUT_SECONDS = 30
INTER_REQUEST_DELAY_SECONDS = 0.1
RETRY_DELAYS_SECONDS = [ 1.0, 2.0, 4.0 ]


def setup_logging( log_file_path ):
    """Configure logging to both file and console."""

    logger = logging.getLogger( 'fetch_uniprot_fastas_emit_rgs' )
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


def load_resolved_symbols( input_path, logger ):
    """Parse 1_ai-resolved_symbols.tsv. Returns a list of row dicts."""

    # Group_Sanitized_Name (...)	Group_Display_Name (...)	Input_Gene_Symbol (...)	Resolved_Gene_Symbol (...)	HGNC_ID (...)	UniProt_Accession_Canonical (...)	UniProt_Accessions_All (...)	Resolution_Status (...)
    # snap_family	Synaptosomal-Associated Proteins	SNAP23	SNAP23	HGNC:11131	O00161	O00161	DIRECT_MATCH
    rows = []
    header_seen = False

    with open( input_path, 'r' ) as input_resolved_symbols:
        for line in input_resolved_symbols:
            line = line.rstrip( '\n' )

            if not line.strip():
                continue
            if line.lstrip().startswith( '#' ):
                continue

            parts = line.split( '\t' )

            if not header_seen:
                if len( parts ) < 8:
                    logger.error( f"CRITICAL ERROR: header must have 8 columns; got {len( parts )}: {parts}" )
                    sys.exit( 1 )
                header_seen = True
                continue

            if len( parts ) < 8:
                logger.warning( f"Skipping malformed row (< 8 columns): {line!r}" )
                continue

            rows.append( {
                'group_sanitized_name': parts[ 0 ].strip(),
                'group_display_name': parts[ 1 ].strip(),
                'input_gene_symbol': parts[ 2 ].strip(),
                'resolved_gene_symbol': parts[ 3 ].strip(),
                'hgnc_id': parts[ 4 ].strip(),
                'uniprot_accession_canonical': parts[ 5 ].strip(),
                'uniprot_accessions_all': parts[ 6 ].strip(),
                'resolution_status': parts[ 7 ].strip(),
            } )

    if not rows:
        logger.error( "CRITICAL ERROR: No rows parsed from resolved-symbols TSV." )
        logger.error( f"Path: {input_path}" )
        sys.exit( 1 )

    return rows


def fetch_uniprot_fasta( accession, logger ):
    """Fetch FASTA text from UniProt REST. Returns (header_line, sequence_string) or (None, None) on failure."""

    url = UNIPROT_FASTA_URL_TEMPLATE.format( accession=accession )

    last_error = None
    for attempt, retry_delay in enumerate( [ 0.0 ] + RETRY_DELAYS_SECONDS ):
        if retry_delay > 0:
            logger.warning( f"  Retrying {accession} after {retry_delay}s delay (attempt {attempt + 1})" )
            time.sleep( retry_delay )

        try:
            request = urllib.request.Request( url, headers={ 'User-Agent': USER_AGENT } )
            with urllib.request.urlopen( request, timeout=REQUEST_TIMEOUT_SECONDS ) as response:
                if response.status != 200:
                    last_error = f"HTTP {response.status}"
                    continue

                text = response.read().decode( 'utf-8' )

            lines = [ line for line in text.split( '\n' ) if line != '' ]
            if not lines or not lines[ 0 ].startswith( '>' ):
                last_error = f"Unexpected response (no FASTA header): first 100 chars: {text[ :100 ]!r}"
                continue

            header_line = lines[ 0 ]
            sequence_lines = lines[ 1: ]
            sequence_string = ''.join( sequence_lines ).replace( ' ', '' ).strip()

            if not sequence_string:
                last_error = "Empty sequence body"
                continue

            return header_line, sequence_string

        except urllib.error.HTTPError as e:
            last_error = f"HTTPError {e.code}: {e.reason}"
            if e.code == 404:
                # Don't retry a 404 — accession is wrong
                logger.error( f"  {accession}: 404 Not Found (UniProt has no entry for this accession)" )
                break
        except urllib.error.URLError as e:
            last_error = f"URLError: {e.reason}"
        except Exception as e:
            last_error = f"{type( e ).__name__}: {e}"

    logger.error( f"  {accession}: failed after all retries — {last_error}" )
    return None, None


def build_rgs_header( group_sanitized, gene_symbol, uniprot_accession ):
    """Build the GIGANTIC 5-field RGS header.

    Format: >rgs_<group>-human-<symbol>-uniprot-<accession>
    """

    return f">rgs_{group_sanitized}-human-{gene_symbol}-uniprot-{uniprot_accession}"


def main():
    parser = argparse.ArgumentParser(
        description = "Fetch UniProt FASTAs for resolved symbols and emit per-group RGS FASTAs."
    )
    parser.add_argument( '--input-resolved-symbols', required=True )
    parser.add_argument( '--output-directory', required=True )
    parser.add_argument( '--log-file', default=None )
    arguments = parser.parse_args()

    output_directory = Path( arguments.output_directory )
    output_directory.mkdir( parents=True, exist_ok=True )

    rgs_fastas_directory = output_directory / 'rgs_fastas'
    rgs_fastas_directory.mkdir( parents=True, exist_ok=True )

    log_file_path = (
        Path( arguments.log_file )
        if arguments.log_file
        else output_directory / '2_ai-log-fetch_uniprot_fastas-emit_rgs.log'
    )
    log_file_path.parent.mkdir( parents=True, exist_ok=True )

    logger = setup_logging( log_file_path )

    logger.info( "=" * 70 )
    logger.info( "Fetch UniProt FASTAs and Emit Per-Group RGS" )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Input manifest: {arguments.input_resolved_symbols}" )
    logger.info( f"Output dir:     {output_directory}" )
    logger.info( "=" * 70 )

    rows = load_resolved_symbols( Path( arguments.input_resolved_symbols ), logger )
    logger.info( f"Parsed {len( rows )} resolved-symbol rows" )

    # Group by group_sanitized_name — preserve input order within each group.
    groups___rows = {}
    for row in rows:
        groups___rows.setdefault( row[ 'group_sanitized_name' ], [] ).append( row )

    logger.info( f"Distinct groups: {len( groups___rows )}" )
    for group_sanitized, group_rows in groups___rows.items():
        logger.info( f"  {group_sanitized}: {len( group_rows )} gene(s)" )

    manifest_rows = []
    fetch_failures = []

    for group_sanitized, group_rows in groups___rows.items():
        rgs_path = rgs_fastas_directory / f"rgs_hgnc_user-human-{group_sanitized}.aa"
        logger.info( "" )
        logger.info( f"Building RGS for group '{group_sanitized}' → {rgs_path}" )

        sequences_for_group = []

        for row in group_rows:
            accession = row[ 'uniprot_accession_canonical' ]
            resolved_symbol = row[ 'resolved_gene_symbol' ]

            logger.info( f"  Fetching {resolved_symbol} ({accession})..." )
            header_line, sequence_string = fetch_uniprot_fasta( accession, logger )

            if INTER_REQUEST_DELAY_SECONDS > 0:
                time.sleep( INTER_REQUEST_DELAY_SECONDS )

            if header_line is None or sequence_string is None:
                fetch_failures.append( ( group_sanitized, resolved_symbol, accession ) )
                manifest_rows.append( {
                    'group_sanitized_name': group_sanitized,
                    'group_display_name': row[ 'group_display_name' ],
                    'input_gene_symbol': row[ 'input_gene_symbol' ],
                    'resolved_gene_symbol': resolved_symbol,
                    'hgnc_id': row[ 'hgnc_id' ],
                    'uniprot_accession': accession,
                    'sequence_length': 0,
                    'rgs_fasta_header': '',
                    'status': 'FAILED_FETCH',
                } )
                continue

            rgs_header = build_rgs_header( group_sanitized, resolved_symbol, accession )
            sequence_length = len( sequence_string )

            sequences_for_group.append( ( rgs_header, sequence_string ) )
            manifest_rows.append( {
                'group_sanitized_name': group_sanitized,
                'group_display_name': row[ 'group_display_name' ],
                'input_gene_symbol': row[ 'input_gene_symbol' ],
                'resolved_gene_symbol': resolved_symbol,
                'hgnc_id': row[ 'hgnc_id' ],
                'uniprot_accession': accession,
                'sequence_length': sequence_length,
                'rgs_fasta_header': rgs_header,
                'status': 'SUCCESS',
            } )

            logger.info( f"    OK ({sequence_length} aa)" )

        # Write the per-group RGS FASTA only if all fetches succeeded.
        if not fetch_failures:
            with open( rgs_path, 'w' ) as output_rgs_fasta:
                for header_string, sequence_string in sequences_for_group:
                    output_rgs_fasta.write( header_string + '\n' )
                    # Wrap sequence to 60 chars per line (FASTA convention)
                    for offset in range( 0, len( sequence_string ), 60 ):
                        output_rgs_fasta.write( sequence_string[ offset:offset + 60 ] + '\n' )
            logger.info( f"  Wrote {len( sequences_for_group )} sequences to {rgs_path}" )

    if fetch_failures:
        logger.error( "" )
        logger.error( f"CRITICAL ERROR: {len( fetch_failures )} UniProt fetch failures." )
        for group_sanitized, resolved_symbol, accession in fetch_failures:
            logger.error( f"  group={group_sanitized}  symbol={resolved_symbol}  accession={accession}" )
        logger.error( "" )
        logger.error( "Possible causes:" )
        logger.error( "  - UniProt API temporarily unavailable (try again later)" )
        logger.error( "  - Accession was withdrawn or obsoleted (check the manifest TSV)" )
        logger.error( "  - Compute node has no network access (UniProt requires reachability)" )
        sys.exit( 1 )

    # Write the manifest TSV.
    manifest_path = output_directory / '2_ai-rgs_generation_manifest.tsv'

    output = 'Group_Sanitized_Name (filesystem-safe group identifier)' + '\t'
    output += 'Group_Display_Name (human-readable group description)' + '\t'
    output += 'Input_Gene_Symbol (the symbol as provided by the user in user_gene_set.tsv)' + '\t'
    output += 'Resolved_Gene_Symbol (canonical HGNC-approved symbol)' + '\t'
    output += 'HGNC_ID (HGNC database identifier)' + '\t'
    output += 'UniProt_Accession (UniProt accession used to fetch the sequence)' + '\t'
    output += 'Sequence_Length (number of amino acids in the fetched sequence)' + '\t'
    output += 'RGS_FASTA_Header (the 5-field GIGANTIC header written to the per-group RGS file)' + '\t'
    output += 'Status (SUCCESS or FAILED_FETCH)' + '\n'

    with open( manifest_path, 'w' ) as output_manifest:
        output_manifest.write( output )
        for row in manifest_rows:
            row_output = row[ 'group_sanitized_name' ] + '\t'
            row_output += row[ 'group_display_name' ] + '\t'
            row_output += row[ 'input_gene_symbol' ] + '\t'
            row_output += row[ 'resolved_gene_symbol' ] + '\t'
            row_output += row[ 'hgnc_id' ] + '\t'
            row_output += row[ 'uniprot_accession' ] + '\t'
            row_output += str( row[ 'sequence_length' ] ) + '\t'
            row_output += row[ 'rgs_fasta_header' ] + '\t'
            row_output += row[ 'status' ] + '\n'
            output_manifest.write( row_output )

    logger.info( "" )
    logger.info( f"Manifest written: {manifest_path}" )

    # ALSO emit a per-group summary TSV in the format STEP_1's orchestrator
    # expects (matches workflow-hgnc_database's 3_ai-rgs_generation_summary.tsv).
    # Columns: Gene_Group_ID, Gene_Group_Name, Sanitized_Name, RGS_Filename, Sequence_Count.
    summary_path = output_directory / '2_ai-rgs_generation_summary.tsv'

    summary_output = 'Gene_Group_ID (synthetic identifier for user-defined groups; format user_defined_<sanitized_name>)' + '\t'
    summary_output += 'Gene_Group_Name (group display name from user input)' + '\t'
    summary_output += 'Sanitized_Name (filesystem-safe group identifier)' + '\t'
    summary_output += 'RGS_Filename (name of the per-group RGS FASTA file in rgs_fastas/)' + '\t'
    summary_output += 'Sequence_Count (number of protein sequences in the RGS FASTA)' + '\n'

    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( summary_output )

        for group_sanitized, group_rows in groups___rows.items():
            group_display = group_rows[ 0 ][ 'group_display_name' ] if group_rows else group_sanitized
            rgs_filename = f"rgs_hgnc_user-human-{group_sanitized}.aa"
            sequence_count = sum( 1 for row in manifest_rows
                                  if row[ 'group_sanitized_name' ] == group_sanitized and row[ 'status' ] == 'SUCCESS' )

            row_output = f"user_defined_{group_sanitized}" + '\t'
            row_output += group_display + '\t'
            row_output += group_sanitized + '\t'
            row_output += rgs_filename + '\t'
            row_output += str( sequence_count ) + '\n'
            output_summary.write( row_output )

    logger.info( f"Summary written: {summary_path}" )
    logger.info( f"RGS FASTAs: {len( groups___rows )} groups × total {len( manifest_rows )} sequences" )
    logger.info( "=" * 70 )
    logger.info( "RGS generation complete." )
    logger.info( "=" * 70 )


if __name__ == '__main__':
    main()
