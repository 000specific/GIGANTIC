#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 008 (rewritten 2026-05-23): Map RGS to reference genomes
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Identify RGS-genome cognates via accession + BLAST thresholds + Hungarian assignment with strict fail-fast on any unresolved RGS
# Human: Eric Edsinger

"""
Map RGS Sequences to Reference Genome Identifiers (strict, BLAST-free).

This script identifies the unique genome protein cognate of each RGS
sequence by dispatching on the RGS header format. The pipeline was
simplified for gene_groups_hgnc (Improvements 2-4, the BLAST fallback
chain inherited from trees_gene_families, were removed as dead code —
gene_groups_hgnc RGS are always either NCBI-accession-tagged or
HGNC-symbol-tagged, which Improvements 0 and 1 resolve exactly).

Pipeline (dispatch by RGS header format):

  4-field uniprot-sourced RGS  (workflow-COPYME-hgnc_user_gene_symbols):
    >rgs_snap_family-human-SNAP25-uniprotP60880
    → Improvement 0 (strict gene-symbol search)
    → Failure is FINAL (no fallback).

  5+-field hgnc/ncbi-sourced RGS (workflow-COPYME-hgnc_database):
    >rgs_syntaxins-human-STX10-hgnc_gg818_Syntaxins-NP_003756_1
    → Improvement 1 (exact NCBI accession match)
    → Failure is FINAL (no fallback).

    Improvement 0: Strict gene-symbol search (uniprot-sourced RGS only)
                   - Parse gene_symbol from RGS header field 3 (0-indexed 2)
                   - Find protein in proteome with `>g_<SYMBOL>-` header
                   - Exactly ONE match required; 0 or >1 = fail-fast
                   - Rationale: user-supplied gene sets must be HGNC-canonical;
                     ambiguous lookups indicate malformed input

    Improvement 1: Exact NCBI accession match (ncbi-sourced RGS only)
                   - Extract NP_/XP_ accession from RGS header (last field)
                   - Lookup in pre-built genome accession index
                   - Confident, zero-ambiguity mapping for NCBI-sourced RGS
                   - T1 length invariant check (RGS must NOT be longer than
                     the matched genome T1 isoform)

    Improvement 5: Strict orphan detection (fail-fast)
                   - Any RGS not cleanly resolved by 0 or 1 terminates the pipeline
                   - No --include-orphan-rgs escape, no silent skipping
                   - Each unresolved RGS reported with a specific reason

Output files:
    - <output-mapping>          (4-column TSV: genome_id, truncated_rgs, full_rgs, mechanism)
    - <output-rgs-fasta>        (RGS sequences for the reciprocal BLAST DB)
    - <output-fasta-list>       (list of model organism FASTA paths)
    - 8-output/8_ai-header_truncation_map.txt
    - 8-output/8_ai-rgs_identification_report.tsv  (audit report; one row per RGS)
"""

import argparse
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ============================================================================
# Constants
# ============================================================================

# NCBI protein accessions: 2 letters, underscore, digits, optional version suffix.
# Examples: NP_006133, NP_006133.1, NP_006133_1, XP_011509253.1
NCBI_ACCESSION_REGEX = re.compile( r'^([A-Z]{2}_[0-9]+)(?:[._][0-9]+)?$' )


# ============================================================================
# Logging
# ============================================================================

def setup_logging( log_file: Optional[Path] = None ) -> logging.Logger:
    logger = logging.getLogger( 'rgs_mapping' )
    logger.setLevel( logging.INFO )
    logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler( sys.stdout )
    console_handler.setFormatter( formatter )
    logger.addHandler( console_handler )

    if log_file:
        log_file.parent.mkdir( parents = True, exist_ok = True )
        file_handler = logging.FileHandler( log_file )
        file_handler.setFormatter( formatter )
        logger.addHandler( file_handler )

    return logger


# ============================================================================
# Identifier parsing helpers
# ============================================================================

def normalize_ncbi_accession( accession_string: str ) -> Optional[str]:
    """Return the base NCBI accession (without version), or None if not an NCBI accession.

    Accepts: NP_006133, NP_006133.1, NP_006133_1, XP_011509253.1
    Rejects: anything that doesn't match the canonical NCBI letters+underscore+digits pattern.
    """
    match = NCBI_ACCESSION_REGEX.match( accession_string )
    return match.group( 1 ) if match else None


def extract_ncbi_accession_from_rgs_header( rgs_header: str ) -> Optional[str]:
    """RGS header format (5-field, hgnc/ncbi-sourced): rgs_<group>-<organism>-<gene>-<source>-<protein_id>
    Returns the normalized NCBI accession if the protein_id field is NCBI-formatted, else None.

    For 4-field uniprot-sourced headers (e.g., rgs_snap_family-human-SNAP25-uniprotP60880)
    the last field doesn't normalize to an NCBI accession, so this returns None and
    Improvement 0 (gene-symbol search) handles those instead.
    """
    parts_rgs_header = rgs_header.split( '-' )
    if not parts_rgs_header:
        return None
    return normalize_ncbi_accession( parts_rgs_header[ -1 ] )


def extract_ncbi_accession_from_genome_header( genome_header: str ) -> Optional[str]:
    """Genome header format: g_<gene>-t_<transcript>-p_<protein>-n_<phyloname>
    Returns the normalized NCBI accession from the -p_ field, else None for non-NCBI proteomes.
    """
    if '-p_' not in genome_header or '-n_' not in genome_header:
        return None
    before_n = genome_header.rsplit( '-n_', 1 )[ 0 ]
    if '-p_' not in before_n:
        return None
    protein_id = before_n.rsplit( '-p_', 1 )[ 1 ]
    return normalize_ncbi_accession( protein_id )


def extract_gene_symbol_from_genome_header( genome_header: str ) -> Optional[str]:
    """Genome header format: g_<gene_symbol>-t_<transcript>-p_<protein>-n_<phyloname>
    Returns the gene symbol from the g_ field, or None if the header doesn't conform.
    """
    if not genome_header.startswith( 'g_' ):
        return None
    if '-t_' not in genome_header:
        return None
    return genome_header.split( '-t_', 1 )[ 0 ][ 2: ]   # strip leading 'g_', take up to '-t_'


def extract_gene_symbol_from_rgs_header( rgs_header: str ) -> Optional[str]:
    """Extract gene symbol from an RGS header (parts[2]).
    Works for BOTH 4-field uniprot-sourced and 5-field ncbi/hgnc-sourced headers,
    since gene symbol always sits at index 2 in the GIGANTIC RGS header convention:

        rgs_<group>-<species>-<GENE_SYMBOL>-<source(+id)>[-<id>]
    """
    parts_rgs_header = rgs_header.split( '-' )
    if len( parts_rgs_header ) < 4:
        return None
    if not parts_rgs_header[ 0 ].startswith( 'rgs_' ):
        return None
    return parts_rgs_header[ 2 ]


def is_uniprot_sourced_rgs( rgs_header: str ) -> bool:
    """True if the RGS header uses the 4-field uniprot-source convention:
        rgs_<group>-<species>-<symbol>-uniprot<accession>
    Dispatch hook for Improvement 0 (strict gene-symbol search against the proteome).
    """
    parts_rgs_header = rgs_header.split( '-' )
    if len( parts_rgs_header ) != 4:
        return False
    if not parts_rgs_header[ 0 ].startswith( 'rgs_' ):
        return False
    return parts_rgs_header[ 3 ].lower().startswith( 'uniprot' )


def parse_rgs_species_short_name( rgs_header: str ) -> Optional[str]:
    """Extract the organism short name (parts[1]) from the RGS header.
    Accepts BOTH 4-field uniprot-sourced and 5+-field ncbi/hgnc-sourced headers.
    Returns parts[1] when header starts with 'rgs_' and has at least 4 dash-delimited fields.
    """
    parts_rgs_header = rgs_header.split( '-' )
    if len( parts_rgs_header ) < 4:
        return None
    if not parts_rgs_header[ 0 ].startswith( 'rgs_' ):
        return None
    return parts_rgs_header[ 1 ]


# ============================================================================
# FASTA / BLAST IO
# ============================================================================

def read_rgs_sequences( rgs_fasta: Path, logger: logging.Logger ) -> Dict[ str, Tuple[ str, int ] ]:
    """Return dict[full_rgs_header] -> (sequence, length)."""
    # >rgs_14_3_3_phospho_serine_phospho_threonine_binding_proteins-human-SFN-hgnc_gg1053_..._proteins-NP_006133_1
    # MERASLIQKAKLAEQAERYEDMAAFMKGAVEKGEELSCEERNLLSVAYKNVVGGQRAAWRVLSSIEQKSNEEGSEEKGPE
    rgs_headers___sequence_and_length: Dict[ str, Tuple[ str, int ] ] = {}
    current_header = None
    current_chunks: List[ str ] = []

    with open( rgs_fasta, 'r' ) as input_rgs_fasta:
        for line in input_rgs_fasta:
            line = line.strip()
            if line.startswith( '>' ):
                if current_header is not None:
                    sequence = ''.join( current_chunks )
                    rgs_headers___sequence_and_length[ current_header ] = ( sequence, len( sequence ) )
                current_header = line[ 1: ]
                current_chunks = []
            else:
                current_chunks.append( line )
        if current_header is not None:
            sequence = ''.join( current_chunks )
            rgs_headers___sequence_and_length[ current_header ] = ( sequence, len( sequence ) )

    logger.info( f'Read {len( rgs_headers___sequence_and_length )} RGS sequences from {rgs_fasta.name}' )
    return rgs_headers___sequence_and_length


class GenomeIndex:
    """Per-species index of the source genome:
    - accession_to_header:        normalized NCBI accession -> full genome header
    - header_to_length:           full genome header        -> protein length (aa)
    - gene_symbol_to_headers:     gene symbol               -> list of headers
                                  (multi-valued because a proteome COULD contain
                                  multiple proteins per gene_symbol; Improvement 0
                                  enforces exactly-one for strictness)
    """
    def __init__( self ):
        self.accession_to_header: Dict[ str, str ] = {}
        self.header_to_length: Dict[ str, int ] = {}
        self.gene_symbol_to_headers: Dict[ str, List[ str ] ] = {}


def build_genome_index( genome_fasta: Path, logger: logging.Logger ) -> GenomeIndex:
    """Build a GenomeIndex from a source-species proteome FASTA.
    Builds the NCBI-accession lookup, the full header-to-length map, AND the
    gene_symbol_to_headers lookup used by Improvement 0.
    Fails fast on duplicate NCBI accessions in the genome.
    """
    # >g_SFN-t_NM_006142.5-p_NP_006133.1-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
    # MERASLIQKAKLAEQAERYEDMAAFMKGAVEKGEELSCEERNLLSVAYKNVVGGQRAAWRVLSSIEQKSNEEGSEEKGPE
    index = GenomeIndex()
    current_header: Optional[str] = None
    current_length = 0

    def _commit( header: Optional[str], length: int ):
        if header is None:
            return
        index.header_to_length[ header ] = length
        accession = extract_ncbi_accession_from_genome_header( header )
        if accession is not None:
            if accession in index.accession_to_header:
                raise PipelineFailure(
                    f'Duplicate NCBI accession in genome: {accession}\n'
                    f'  First header:  {index.accession_to_header[ accession ]}\n'
                    f'  Second header: {header}\n'
                    f'  Source FASTA:  {genome_fasta}'
                )
            index.accession_to_header[ accession ] = header
        gene_symbol = extract_gene_symbol_from_genome_header( header )
        if gene_symbol is not None:
            index.gene_symbol_to_headers.setdefault( gene_symbol, [] ).append( header )

    with open( genome_fasta, 'r' ) as input_genome_fasta:
        for line in input_genome_fasta:
            line = line.strip()
            if line.startswith( '>' ):
                _commit( current_header, current_length )
                current_header = line[ 1: ]
                current_length = 0
            else:
                current_length += len( line )
        _commit( current_header, current_length )

    logger.info(
        f'Indexed {genome_fasta.name}: '
        f'{len( index.header_to_length )} proteins total, '
        f'{len( index.accession_to_header )} with NCBI accessions, '
        f'{len( index.gene_symbol_to_headers )} distinct gene symbols'
    )
    return index


def read_file_list( list_file: Path, logger: logging.Logger ) -> List[ Path ]:
    paths: List[ Path ] = []
    with open( list_file, 'r' ) as input_list:
        for line in input_list:
            line = line.strip()
            if line:
                paths.append( Path( line ) )
    logger.info( f'Read {len( paths )} paths from {list_file.name}' )
    return paths


def identify_species_short_name_from_filename( file_path: Path, model_species: List[ str ] ) -> Optional[str]:
    """Return the first model_species short name whose Genus_species form appears as a substring
    of the file path. GIGANTIC proteome filenames embed the phyloname's genus/species, not the
    short name — so 'human' will not appear in 'Metazoa_..._Homo_sapiens-T1-proteome.aa'. Translate
    short names to Genus_species before substring matching. Mapping kept in sync with script 007.

    STRUCTURAL TODO (flagged 2026-05-24):
    This hardcoded short→Genus_species mapping should be replaced with loading
    INPUT_user/rgs_species_map.tsv at runtime. The TSV is the canonical source of
    truth. As-is, any custom species added to rgs_species_map.tsv (e.g., octopus,
    squid, ctenophore) will be silently ignored by both 007 and 008 because they
    aren't in the dict below. Proper fix: add --rgs-species-map CLI arg to both
    scripts, load the TSV, and replace this dict with the loaded mapping.
    """
    species_mappings = {
        'human':      'Homo_sapiens',
        'fly':        'Drosophila_melanogaster',
        'worm':       'Caenorhabditis_elegans',
        'mouse':      'Mus_musculus',
        'zebrafish':  'Danio_rerio',
    }
    file_path_string = str( file_path )
    for species in model_species:
        scientific_name = species_mappings.get( species.lower(), species )
        if scientific_name in file_path_string:
            return species
    return None


# ============================================================================
# Header truncation (for BLAST DB name limit; preserved from prior versions)
# ============================================================================

def create_truncated_headers_map(
    headers: List[ str ],
    max_length: int = 50,
    truncate_to: int = 45,
    logger: Optional[ logging.Logger ] = None,
) -> Dict[ str, str ]:
    """Truncate RGS headers that exceed BLAST's 50-char ID limit. Headers <=50 chars pass through."""
    original_to_truncated: Dict[ str, str ] = {}
    truncated_base_to_count: Dict[ str, int ] = {}
    for original_header in headers:
        if len( original_header ) <= max_length:
            original_to_truncated[ original_header ] = original_header
        else:
            truncated_base = original_header[ :truncate_to ]
            truncated_base_to_count[ truncated_base ] = truncated_base_to_count.get( truncated_base, 0 ) + 1
            counter = truncated_base_to_count[ truncated_base ]
            truncated_header = f'{truncated_base}_{counter:03d}'
            if len( truncated_header ) > max_length:
                emergency_base = original_header[ :( max_length - 4 ) ]
                truncated_header = f'{emergency_base}_{counter:03d}'
            original_to_truncated[ original_header ] = truncated_header

    if logger is not None:
        num_truncated = sum( 1 for o, t in original_to_truncated.items() if o != t )
        logger.info( f'Headers requiring truncation: {num_truncated} / {len( headers )}' )

    return original_to_truncated


# ============================================================================
# Decision records (one per RGS) and the failure exception
# ============================================================================

class PipelineFailure( Exception ):
    """Raised when input data is malformed in a way that prevents safe mapping.
    Caught in main() to print a clean error and exit 1."""
    pass


def new_decision_record( rgs_header: str, rgs_species: Optional[str], rgs_length: int ) -> Dict:
    return {
        'rgs_header':           rgs_header,
        'rgs_species':          rgs_species,
        'rgs_length':           rgs_length,
        'status':               'unresolved',
        'mechanism':            None,
        'genome_id':            None,
        'genome_length':        None,
        'identity':             None,
        'query_coverage':       None,
        'subject_coverage':     None,
        'rgs_longer_than_t1':   False,
        'reason':               None,
        'candidate_count':      0,
    }


# ============================================================================
# Improvement 0: Strict gene-symbol search (for 4-field uniprot-sourced RGS)
# ============================================================================
# RGS headers from workflow-COPYME-hgnc_user_gene_symbols use the 4-field shape
#   rgs_<group>-<species>-<symbol>-uniprot<accession>
# where the source+id is concatenated (e.g., uniprotP60880) — there is no
# NCBI accession in the header, so Improvement 1 cannot match.
#
# For these RGS, the gene symbol IS the primary key into the proteome. We
# look for exactly one `g_<SYMBOL>-...` protein in the per-species genome
# index. If we find 0 or >1 matches, we fail fast (NO orphan fallback for
# user-defined gene sets — the user must fix the input).

def map_via_gene_symbol(
    decisions: Dict[ str, Dict ],
    rgs_sequences: Dict[ str, Tuple[ str, int ] ],
    species_to_genome_index: Dict[ str, GenomeIndex ],
    logger: logging.Logger,
) -> int:
    """For each 4-field uniprot-sourced RGS, look up the gene_symbol in the
    matching species' proteome. Strict: exactly one match → mapped; else the
    decision is finalized with a fail-fast reason and NO subsequent improvement
    is attempted (the failure is final).

    Returns the count successfully mapped.
    """
    mapped_count = 0
    failed_uniprot_count = 0

    for rgs_header, ( _, rgs_length ) in rgs_sequences.items():
        if not is_uniprot_sourced_rgs( rgs_header ):
            continue   # not our concern; existing Improvement 1 will handle it

        decision = decisions[ rgs_header ]
        rgs_species = decision[ 'rgs_species' ]
        if rgs_species is None:
            decision[ 'reason' ] = 'rgs_header_unparseable_for_species'
            failed_uniprot_count += 1
            continue

        gene_symbol = extract_gene_symbol_from_rgs_header( rgs_header )
        if gene_symbol is None:
            decision[ 'reason' ] = 'rgs_header_unparseable_for_gene_symbol'
            failed_uniprot_count += 1
            continue

        genome_index = species_to_genome_index.get( rgs_species )
        if genome_index is None:
            decision[ 'reason' ] = f'no_genome_index_for_species_{rgs_species}'
            failed_uniprot_count += 1
            continue

        matching_headers = genome_index.gene_symbol_to_headers.get( gene_symbol, [] )
        if len( matching_headers ) == 0:
            decision[ 'reason' ] = 'no_proteome_protein_for_gene_symbol'
            failed_uniprot_count += 1
            continue
        if len( matching_headers ) > 1:
            decision[ 'reason' ] = 'multiple_proteome_proteins_for_gene_symbol'
            decision[ 'genome_id' ] = matching_headers[ 0 ]   # surface ONE for debugging
            decision[ 'candidate_count' ] = len( matching_headers )
            failed_uniprot_count += 1
            continue

        # Exactly one match — record the mapping.
        genome_header = matching_headers[ 0 ]
        genome_length = genome_index.header_to_length[ genome_header ]
        decision[ 'status' ]         = 'mapped'
        decision[ 'mechanism' ]      = 'gene_symbol'
        decision[ 'genome_id' ]      = genome_header
        decision[ 'genome_length' ]  = genome_length
        # Identity/coverage aren't from a BLAST hit; record the rgs/genome length ratio
        # for the audit report (no alignment performed at this step).
        decision[ 'identity' ]         = None
        decision[ 'query_coverage' ]   = None
        decision[ 'subject_coverage' ] = None
        if rgs_length > genome_length:
            decision[ 'rgs_longer_than_t1' ] = True
        mapped_count += 1

    if mapped_count or failed_uniprot_count:
        logger.info(
            f'Improvement 0 (gene-symbol search): mapped {mapped_count}; '
            f'unresolved-uniprot {failed_uniprot_count}'
        )
    return mapped_count


# ============================================================================
# Improvement 1: NCBI accession match
# ============================================================================

def map_via_ncbi_accession(
    decisions: Dict[ str, Dict ],
    rgs_sequences: Dict[ str, Tuple[ str, int ] ],
    species_to_genome_index: Dict[ str, GenomeIndex ],
    logger: logging.Logger,
) -> int:
    """Try NCBI accession lookup for every RGS. Mutates decisions in place. Returns count mapped."""
    mapped_count = 0
    for rgs_header, ( _, rgs_length ) in rgs_sequences.items():
        decision = decisions[ rgs_header ]
        rgs_species = decision[ 'rgs_species' ]
        if rgs_species is None:
            decision[ 'reason' ] = 'rgs_header_unparseable_for_species'
            continue
        accession = extract_ncbi_accession_from_rgs_header( rgs_header )
        if accession is None:
            continue   # not an NCBI-sourced RGS; will be handled by BLAST fallback
        genome_index = species_to_genome_index.get( rgs_species )
        if genome_index is None:
            decision[ 'reason' ] = f'no_genome_index_for_species_{rgs_species}'
            continue
        genome_header = genome_index.accession_to_header.get( accession )
        if genome_header is None:
            # Accession in RGS header isn't in the source genome; will retry via BLAST
            continue
        genome_length = genome_index.header_to_length[ genome_header ]
        if rgs_length > genome_length:
            decision[ 'status' ]             = 'unresolved'
            decision[ 'reason' ]             = 'rgs_longer_than_t1'
            decision[ 'genome_id' ]          = genome_header
            decision[ 'genome_length' ]      = genome_length
            decision[ 'rgs_longer_than_t1' ] = True
            continue
        decision[ 'status' ]         = 'mapped'
        decision[ 'mechanism' ]      = 'ncbi_accession'
        decision[ 'genome_id' ]      = genome_header
        decision[ 'genome_length' ]  = genome_length
        decision[ 'identity' ]       = 100.0
        decision[ 'query_coverage' ] = 100.0
        decision[ 'subject_coverage' ] = ( rgs_length / genome_length ) * 100.0
        mapped_count += 1
    logger.info( f'Improvement 1 (NCBI accession): mapped {mapped_count} RGS' )
    return mapped_count



# ============================================================================
# Improvement 5: Fail-fast on any unresolved RGS
# ============================================================================

REASON_HUMAN_HINTS = {
    'rgs_header_unparseable_for_species':       'RGS header does not match expected GIGANTIC formats (4-field uniprot-sourced or 5-field hgnc/ncbi-sourced); cannot identify source species.',
    'rgs_header_unparseable_for_gene_symbol':   'RGS header (4-field uniprot-sourced) parses but gene_symbol (field 3, 0-indexed 2) cannot be extracted; the header is malformed.',
    'no_genome_index_for_species_*':            'RGS species marker was not found among the model_fastas-list FASTAs; check rgs_species_map.tsv and --rbh-species.',
    'no_proteome_protein_for_gene_symbol':      'Improvement 0 strict gene-symbol search found ZERO proteins with `g_<SYMBOL>-` in the source proteome. Verify the symbol is HGNC-canonical (try aliases / previous symbols) and that the proteome is the right species build.',
    'multiple_proteome_proteins_for_gene_symbol': 'Improvement 0 strict gene-symbol search found MORE THAN ONE protein with `g_<SYMBOL>-` in the source proteome. T1 proteomes should have exactly one protein per gene_symbol; investigate the proteome build.',
    'rgs_longer_than_t1':                       'RGS protein is LONGER than the genome T1 isoform. T1 proteomes contain the longest isoform per gene. Either the RGS is a longer-isoform sequence from outside T1 or the T1 build is wrong.',
    'accession_not_in_genome':                  'RGS NCBI accession is not present in the source genome. Either the proteome build does not include this accession (rebuild from a newer NCBI release) or the RGS was generated from a different proteome version.',
}


def finalize_unresolved_reasons( decisions: Dict[ str, Dict ] ) -> None:
    """Fill in 'reason' for any decision that is still unresolved without one set.

    With the BLAST fallback removed, unresolved RGS at this point are NCBI-sourced
    headers whose accession wasn't found in the genome index (Improvement 1 missed).
    """
    for decision in decisions.values():
        if decision[ 'status' ] == 'mapped':
            continue
        if decision[ 'reason' ] is not None:
            continue
        decision[ 'reason' ] = 'accession_not_in_genome'


def assert_all_resolved_or_fail_fast( decisions: Dict[ str, Dict ], logger: logging.Logger ) -> None:
    """If any RGS is unresolved, write a detailed error message and exit 1."""
    unresolved = [ d for d in decisions.values() if d[ 'status' ] != 'mapped' ]
    if not unresolved:
        logger.info( f'[OK] All {len( decisions )} RGS sequences cleanly resolved.' )
        return

    lines: List[ str ] = []
    lines.append( '' )
    lines.append( '=' * 80 )
    lines.append( f'CRITICAL ERROR: RGS identification failed for {len( unresolved )} of {len( decisions )} sequence(s).' )
    lines.append( '=' * 80 )
    lines.append( '' )
    lines.append( 'The pipeline cannot proceed because the following RGS sequences could' )
    lines.append( 'not be cleanly resolved to genome proteins. Per the strict fail-fast' )
    lines.append( 'policy, this is treated as malformed input requiring user intervention.' )
    lines.append( '' )
    lines.append( 'Unresolved RGS sequences and reasons:' )
    lines.append( '' )

    for i, decision in enumerate( sorted( unresolved, key = lambda d: d[ 'rgs_header' ] ), 1 ):
        rgs_header = decision[ 'rgs_header' ]
        reason     = decision[ 'reason' ] or 'unknown_reason'
        hint       = REASON_HUMAN_HINTS.get( reason, '' )
        if not hint and reason.startswith( 'no_genome_index_for_species_' ):
            hint = REASON_HUMAN_HINTS[ 'no_genome_index_for_species_*' ]
        lines.append( f'  {i}. {rgs_header}' )
        lines.append( f'     Reason:   {reason}' )
        if decision[ 'genome_id' ]:
            lines.append( f'     Best hit: {decision[ "genome_id" ]} '
                          f'(rgs_len={decision[ "rgs_length" ]} vs genome_len={decision[ "genome_length" ]}; '
                          f'identity={decision[ "identity" ]}, q_cov={decision[ "query_coverage" ]}, s_cov={decision[ "subject_coverage" ]})' )
        if hint:
            lines.append( f'     Hint:     {hint}' )
        lines.append( '' )

    lines.append( 'Resolution options:' )
    lines.append( '  - Remove the unresolved RGS sequence(s) from the input FASTA' )
    lines.append( '  - Provide a different RGS sequence (e.g., shorter isoform that fits T1)' )
    lines.append( '  - Use a different reference genome / species build that contains the' )
    lines.append( '    expected accession or sequence' )
    lines.append( '  - Inspect the per-RGS audit report (8_ai-rgs_identification_report.tsv)' )
    lines.append( '' )
    lines.append( 'NO orphan fallback is available. Fix the input and rerun.' )
    lines.append( '=' * 80 )

    for line in lines:
        logger.error( line )
    raise PipelineFailure( f'{len( unresolved )} RGS unresolved (see error above).' )


# ============================================================================
# Output writers
# ============================================================================

def write_mapping_file(
    decisions: Dict[ str, Dict ],
    output_mapping: Path,
    header_truncation_map: Dict[ str, str ],
    logger: logging.Logger,
) -> None:
    """Format: genome_id<TAB>truncated_rgs_header<TAB>original_full_rgs_header<TAB>mechanism

    Output is sorted by genome_id for deterministic file content.
    """
    mapped_decisions = [ d for d in decisions.values() if d[ 'status' ] == 'mapped' ]
    mapped_decisions.sort( key = lambda d: d[ 'genome_id' ] )

    output_mapping.parent.mkdir( parents = True, exist_ok = True )
    with open( output_mapping, 'w' ) as output_mapping_file:
        for decision in mapped_decisions:
            genome_id  = decision[ 'genome_id' ]
            rgs_header = decision[ 'rgs_header' ]
            truncated  = header_truncation_map.get( rgs_header, rgs_header )
            mechanism  = decision[ 'mechanism' ]
            output = f'{genome_id}\t{truncated}\t{rgs_header}\t{mechanism}\n'
            output_mapping_file.write( output )

    logger.info( f'Wrote mapping to {output_mapping} ({len( mapped_decisions )} rows; 4 columns including mechanism)' )


def write_rgs_with_genome_ids(
    rgs_sequences: Dict[ str, Tuple[ str, int ] ],
    output_rgs_fasta: Path,
    header_truncation_map: Dict[ str, str ],
    logger: logging.Logger,
) -> None:
    """Write the RGS FASTA with possibly-truncated headers (for the reciprocal BLAST DB)."""
    output_rgs_fasta.parent.mkdir( parents = True, exist_ok = True )
    with open( output_rgs_fasta, 'w' ) as output_rgs_fasta_file:
        for rgs_header in sorted( rgs_sequences ):
            sequence, _ = rgs_sequences[ rgs_header ]
            truncated_header = header_truncation_map.get( rgs_header, rgs_header )
            output_rgs_fasta_file.write( f'>{truncated_header}\n' )
            for i in range( 0, len( sequence ), 80 ):
                output_rgs_fasta_file.write( sequence[ i: i + 80 ] + '\n' )
    logger.info( f'Wrote RGS sequences to {output_rgs_fasta}' )


def create_model_organism_list( model_fastas: List[ Path ], output_list: Path, logger: logging.Logger ) -> None:
    output_list.parent.mkdir( parents = True, exist_ok = True )
    with open( output_list, 'w' ) as output_list_file:
        for fasta_path in model_fastas:
            output_list_file.write( f'{fasta_path}\n' )
    logger.info( f'Wrote model organism list to {output_list} ({len( model_fastas )} entries)' )


def write_header_truncation_map(
    header_truncation_map: Dict[ str, str ],
    output_file: Path,
    logger: logging.Logger,
) -> None:
    output_file.parent.mkdir( parents = True, exist_ok = True )
    with open( output_file, 'w' ) as output_file_handle:
        output_file_handle.write( 'original_header\ttruncated_header\n' )
        for original, truncated in sorted( header_truncation_map.items() ):
            if original != truncated:
                output_file_handle.write( f'{original}\t{truncated}\n' )
    num_truncated = sum( 1 for o, t in header_truncation_map.items() if o != t )
    logger.info( f'Wrote header truncation map to {output_file} ({num_truncated} truncated)' )


def write_rgs_identification_report(
    decisions: Dict[ str, Dict ],
    output_report: Path,
    logger: logging.Logger,
) -> None:
    """Audit sidecar: one row per RGS with the full decision provenance."""
    output_report.parent.mkdir( parents = True, exist_ok = True )
    columns = [
        'rgs_header', 'rgs_species', 'rgs_length',
        'status', 'mechanism', 'genome_id', 'genome_length',
        'identity', 'query_coverage', 'subject_coverage',
        'rgs_longer_than_t1', 'candidate_count', 'reason',
    ]
    with open( output_report, 'w' ) as output_report_file:
        output_report_file.write( '\t'.join( columns ) + '\n' )
        for decision in sorted( decisions.values(), key = lambda d: d[ 'rgs_header' ] ):
            row_values = [ str( decision.get( col, '' ) if decision.get( col ) is not None else '' ) for col in columns ]
            output_report_file.write( '\t'.join( row_values ) + '\n' )
    logger.info( f'Wrote RGS identification audit report to {output_report} ({len( decisions )} rows)' )


# ============================================================================
# main
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Map RGS sequences to reference genome identifiers (strict, BLAST-free; Improvement 0 + Improvement 1)'
    )
    parser.add_argument( '--model-fastas-list', type = Path, required = True,
                         help = 'File listing model organism (source-genome) FASTA paths' )
    parser.add_argument( '--rgs-fasta', type = Path, required = True,
                         help = 'RGS FASTA file' )
    parser.add_argument( '--output-mapping', type = Path, required = True,
                         help = 'Output RGS->genome mapping (4-column TSV)' )
    parser.add_argument( '--output-rgs-fasta', type = Path, required = True,
                         help = 'Output RGS FASTA (with truncated headers for BLAST DB)' )
    parser.add_argument( '--output-fasta-list', type = Path, required = True,
                         help = 'Output list of model organism FASTAs' )
    parser.add_argument( '--output-rgs-report', type = Path, default = Path( '8-output/8_ai-rgs_identification_report.tsv' ),
                         help = 'Output audit report (one row per RGS, default 8-output/8_ai-rgs_identification_report.tsv)' )
    parser.add_argument( '--rbh-species', type = str, required = True,
                         help = 'Space-separated RBH species short names (e.g., "human fly worm")' )
    parser.add_argument( '--log-file', type = Path, default = None,
                         help = 'Optional log file path' )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    model_species_list = args.rbh_species.split()
    logger = setup_logging( args.log_file )

    logger.info( '=' * 80 )
    logger.info( 'Script 008: Map RGS to Reference Genome Identifiers (BLAST-free)' )
    logger.info( '  Pipeline: Improvement 0 (gene-symbol search for uniprot RGS)' )
    logger.info( '            Improvement 1 (exact NCBI accession match for ncbi RGS)' )
    logger.info( '            Improvement 5 (strict fail-fast on any unresolved)' )
    logger.info( '=' * 80 )
    logger.info( f'Started:           {datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )}' )
    logger.info( f'RGS FASTA:         {args.rgs_fasta}' )
    logger.info( f'Model FASTAs list: {args.model_fastas_list}' )
    logger.info( f'RBH species:       {", ".join( model_species_list )}' )
    logger.info( '' )

    try:
        # Read inputs
        rgs_sequences  = read_rgs_sequences( args.rgs_fasta, logger )
        if not rgs_sequences:
            raise PipelineFailure( f'No RGS sequences in {args.rgs_fasta}.' )
        model_fastas   = read_file_list( args.model_fastas_list, logger )

        # Build per-species genome indexes
        logger.info( 'Indexing source-genome FASTAs ...' )
        species_to_genome_index: Dict[ str, GenomeIndex ] = {}
        for fasta_path in model_fastas:
            species = identify_species_short_name_from_filename( fasta_path, model_species_list )
            if species is None:
                logger.warning( f'Cannot match a model species to FASTA {fasta_path.name} (skipping)' )
                continue
            if species in species_to_genome_index:
                logger.warning( f'Multiple genome FASTAs map to species {species}; using the first.' )
                continue
            species_to_genome_index[ species ] = build_genome_index( fasta_path, logger )

        # Initialize per-RGS decision records
        decisions: Dict[ str, Dict ] = {}
        for rgs_header, ( _, rgs_length ) in rgs_sequences.items():
            decisions[ rgs_header ] = new_decision_record(
                rgs_header  = rgs_header,
                rgs_species = parse_rgs_species_short_name( rgs_header ),
                rgs_length  = rgs_length,
            )

        # Pipeline
        # Improvement 0 — strict gene-symbol search for 4-field uniprot-sourced RGS.
        # If it fails for a uniprot RGS, the failure is FINAL.
        map_via_gene_symbol( decisions, rgs_sequences, species_to_genome_index, logger )
        # Improvement 1 — NCBI accession match for 5-field hgnc/ncbi-sourced RGS.
        # Naturally skips uniprot RGS (their last-field doesn't normalize to NCBI).
        map_via_ncbi_accession( decisions, rgs_sequences, species_to_genome_index, logger )
        # Improvement 5 — strict fail-fast on anything still unresolved.
        finalize_unresolved_reasons( decisions )
        assert_all_resolved_or_fail_fast( decisions, logger )

        # Outputs
        header_truncation_map = create_truncated_headers_map( list( rgs_sequences.keys() ), logger = logger )
        write_mapping_file( decisions, args.output_mapping, header_truncation_map, logger )
        write_rgs_with_genome_ids( rgs_sequences, args.output_rgs_fasta, header_truncation_map, logger )
        create_model_organism_list( model_fastas, args.output_fasta_list, logger )
        write_header_truncation_map(
            header_truncation_map,
            args.output_mapping.parent / '8_ai-header_truncation_map.txt',
            logger,
        )
        write_rgs_identification_report( decisions, args.output_rgs_report, logger )

        # Final summary
        mechanism_counts: Dict[ str, int ] = defaultdict( int )
        for decision in decisions.values():
            mechanism_counts[ decision.get( 'mechanism' ) or 'unresolved' ] += 1
        logger.info( '' )
        logger.info( '=' * 80 )
        logger.info( 'SCRIPT COMPLETE' )
        logger.info( '=' * 80 )
        logger.info( f'RGS sequences processed: {len( decisions )}' )
        logger.info( 'Mapping mechanism breakdown:' )
        for mechanism, count in sorted( mechanism_counts.items() ):
            logger.info( f'  {mechanism}: {count}' )
        logger.info( f'Completed: {datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )}' )

    except PipelineFailure as failure:
        logger.error( f'PipelineFailure: {failure}' )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
