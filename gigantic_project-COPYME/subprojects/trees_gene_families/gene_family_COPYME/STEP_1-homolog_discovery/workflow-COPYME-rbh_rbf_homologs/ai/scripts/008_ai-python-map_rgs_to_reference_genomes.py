#!/usr/bin/env python3
# GIGANTIC BLOCK 2 - Script 008 (rewritten 2026-05-23): Map RGS to reference genomes
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Identify RGS-genome cognates via accession + BLAST thresholds + Hungarian assignment with strict fail-fast on any unresolved RGS
# Human: Eric Edsinger

"""
Map RGS Sequences to Reference Genome Identifiers (5-improvement implementation).

This script identifies the unique genome protein cognate of each RGS sequence
via a layered pipeline. See `PLAN-rgs_identification_improvements.md` (two
directories up) for full design rationale.

Pipeline:
    Improvement 1: Exact NCBI accession match (primary)
                   - Extract NP_/XP_ accession from RGS header
                   - Lookup in pre-built genome accession index
                   - Confident, zero-ambiguity mapping for NCBI-sourced RGS

    Improvement 2: BLAST fallback with strict thresholds
                   - For RGS without NCBI accessions (UniProt, JGI, curated)
                   - Identity >= 95% AND query_coverage >= 95% AND subject_coverage >= 95%
                   - T1 length invariant: RGS must NOT be longer than genome T1
                     (T1 proteomes contain the longest isoform per gene)

    Improvement 3: Conflict / paralog detection
                   - If multiple RGS claim the same genome protein top hit:
                     resolve via Improvement 4 or fail-fast
                   - Approximates BBH via "is the top hit uniquely claimed?"

    Improvement 4: Hungarian optimal assignment
                   - When conflicts exist, run scipy.optimize.linear_sum_assignment
                     to find the globally-optimal RGS<->genome bipartite matching
                   - Falls back to a greedy-with-uniqueness method if scipy is
                     unavailable; the conda environment SHOULD include scipy+numpy
                     so this code path is taken (see ai/conda_environment.yml).

    Improvement 5: Strict orphan detection (fail-fast)
                   - Any RGS not cleanly resolved by 1-4 terminates the pipeline
                   - No --include-orphan-rgs escape, no silent skipping
                   - Each unresolved RGS reported with the specific reason

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

MIN_IDENTITY_PERCENT = 95.0
MIN_COVERAGE_PERCENT = 95.0

# NCBI protein accessions: 2 letters, underscore, digits, optional version suffix.
# Examples: NP_006133, NP_006133.1, NP_006133_1, XP_011509253.1
NCBI_ACCESSION_REGEX = re.compile( r'^([A-Z]{2}_[0-9]+)(?:[._][0-9]+)?$' )

# BLAST tabular outfmt 6 columns (12-column default)
BLAST_COLS = (
    'qseqid', 'sseqid', 'pident', 'length', 'mismatch', 'gapopen',
    'qstart', 'qend', 'sstart', 'send', 'evalue', 'bitscore',
)

# scipy is optional; if missing, Hungarian falls back to greedy + fail-fast on conflicts
try:
    from scipy.optimize import linear_sum_assignment   # type: ignore
    import numpy as np                                  # type: ignore
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


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
    """RGS header format: rgs_<group>-<organism>-<gene>-<source>-<protein_id>
    Returns the normalized NCBI accession if the protein_id field is NCBI-formatted, else None.
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


def parse_rgs_species_short_name( rgs_header: str ) -> Optional[str]:
    """Extract the organism short name (parts[1]) from the RGS header.
    Format expectation: rgs_<group>-<species>-<gene>-<source>-<id> (>= 5 fields, first starts with 'rgs_').
    """
    parts_rgs_header = rgs_header.split( '-' )
    if len( parts_rgs_header ) < 5:
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
    - accession_to_header: normalized NCBI accession -> full genome header
    - header_to_length:    full genome header        -> protein length (aa)
    """
    def __init__( self ):
        self.accession_to_header: Dict[ str, str ] = {}
        self.header_to_length: Dict[ str, int ] = {}


def build_genome_index( genome_fasta: Path, logger: logging.Logger ) -> GenomeIndex:
    """Build a GenomeIndex from a source-species proteome FASTA.
    Builds BOTH the NCBI-accession lookup and a full header-to-length map.
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
        f'{len( index.accession_to_header )} with NCBI accessions'
    )
    return index


def parse_blast_report_rows( blast_report: Path ):
    """Yield dict per row of an outfmt 6 BLAST report (12 standard columns)."""
    with open( blast_report, 'r' ) as input_blast_report:
        for line in input_blast_report:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue
            parts = line.split( '\t' )
            if len( parts ) < 12:
                continue
            yield dict( zip( BLAST_COLS, parts ) )


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
    """Return the first model_species short name that appears as a substring in the file path, else None."""
    file_path_string = str( file_path )
    for species in model_species:
        if species in file_path_string:
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
# Improvement 2: BLAST fallback with strict thresholds
# ============================================================================

def gather_blast_candidates(
    decisions: Dict[ str, Dict ],
    rgs_sequences: Dict[ str, Tuple[ str, int ] ],
    blast_reports: List[ Path ],
    species_to_genome_index: Dict[ str, GenomeIndex ],
    model_species: List[ str ],
    logger: logging.Logger,
) -> Dict[ str, List[ Dict ] ]:
    """For RGS not yet mapped via NCBI accession, gather all BLAST hits that pass the
    identity/coverage thresholds. Returns dict[rgs_header] -> list of candidate dicts."""
    blast_candidates_by_rgs: Dict[ str, List[ Dict ] ] = defaultdict( list )
    t1_violations: List[ Tuple[ str, str, int, int ] ] = []
    hits_rejected_for_thresholds = 0

    for blast_report in blast_reports:
        if not blast_report.exists():
            logger.warning( f'BLAST report missing (skipping): {blast_report}' )
            continue
        report_species = identify_species_short_name_from_filename( blast_report, model_species )
        if report_species is None:
            logger.warning( f'Cannot identify species for report {blast_report.name} (skipping)' )
            continue
        genome_index = species_to_genome_index.get( report_species )
        if genome_index is None:
            logger.warning( f'No genome index for report species {report_species} (skipping)' )
            continue

        for row in parse_blast_report_rows( blast_report ):
            rgs_query  = row[ 'qseqid' ]
            genome_hit = row[ 'sseqid' ]

            decision = decisions.get( rgs_query )
            if decision is None:
                continue   # RGS in report but not in our input FASTA (orphan blast row)
            if decision[ 'status' ] == 'mapped':
                continue   # already mapped via NCBI accession
            if decision[ 'rgs_species' ] != report_species:
                continue   # cross-species blast row, not applicable here

            genome_length = genome_index.header_to_length.get( genome_hit )
            if genome_length is None:
                continue   # genome protein not in the FASTA index (shouldn't happen)

            _, rgs_length = rgs_sequences[ rgs_query ]
            pident = float( row[ 'pident' ] )
            try:
                qstart = int( row[ 'qstart' ] ); qend = int( row[ 'qend' ] )
                sstart = int( row[ 'sstart' ] ); send = int( row[ 'send' ] )
                bitscore = float( row[ 'bitscore' ] )
            except ValueError:
                continue

            query_coverage   = ( abs( qend - qstart ) + 1 ) / rgs_length * 100.0
            subject_coverage = ( abs( send - sstart ) + 1 ) / genome_length * 100.0

            if pident < MIN_IDENTITY_PERCENT \
               or query_coverage < MIN_COVERAGE_PERCENT \
               or subject_coverage < MIN_COVERAGE_PERCENT:
                hits_rejected_for_thresholds += 1
                continue

            if rgs_length > genome_length:
                t1_violations.append( ( rgs_query, genome_hit, rgs_length, genome_length ) )
                continue

            blast_candidates_by_rgs[ rgs_query ].append( {
                'genome_id':        genome_hit,
                'genome_length':    genome_length,
                'rgs_length':       rgs_length,
                'identity':         pident,
                'query_coverage':   query_coverage,
                'subject_coverage': subject_coverage,
                'bitscore':         bitscore,
            } )

    logger.info(
        f'Improvement 2 (BLAST fallback): '
        f'{len( blast_candidates_by_rgs )} RGS have >=1 candidate at >={MIN_IDENTITY_PERCENT}% identity / >={MIN_COVERAGE_PERCENT}% coverage, '
        f'{hits_rejected_for_thresholds} BLAST rows rejected by thresholds, '
        f'{len( t1_violations )} T1-length-invariant violations'
    )

    # T1 violations are recorded onto the per-RGS decision so they appear in fail-fast output
    for rgs_query, genome_hit, rgs_length, genome_length in t1_violations:
        decision = decisions[ rgs_query ]
        if decision[ 'status' ] != 'mapped' and decision[ 'reason' ] is None:
            decision[ 'reason' ]             = 'rgs_longer_than_t1'
            decision[ 'genome_id' ]          = genome_hit
            decision[ 'genome_length' ]      = genome_length
            decision[ 'rgs_longer_than_t1' ] = True

    return dict( blast_candidates_by_rgs )


def apply_unique_blast_candidates(
    decisions: Dict[ str, Dict ],
    blast_candidates_by_rgs: Dict[ str, List[ Dict ] ],
    logger: logging.Logger,
) -> Dict[ str, List[ Dict ] ]:
    """Map RGS that have exactly 1 candidate AND that candidate isn't claimed by any other RGS.
    Mutates decisions in place. Returns the still-contested candidates dict for Hungarian."""
    genome_id_claimants: Dict[ str, Set[ str ] ] = defaultdict( set )
    for rgs_header, candidates in blast_candidates_by_rgs.items():
        for candidate in candidates:
            genome_id_claimants[ candidate[ 'genome_id' ] ].add( rgs_header )

    unique_mapped_count = 0
    still_contested: Dict[ str, List[ Dict ] ] = {}
    for rgs_header, candidates in blast_candidates_by_rgs.items():
        decision = decisions[ rgs_header ]
        if decision[ 'status' ] == 'mapped':
            continue
        for candidate in candidates:
            decision[ 'candidate_count' ] += 1

        if len( candidates ) == 1 and len( genome_id_claimants[ candidates[ 0 ][ 'genome_id' ] ] ) == 1:
            cand = candidates[ 0 ]
            decision[ 'status' ]           = 'mapped'
            decision[ 'mechanism' ]        = 'blast_high_confidence'
            decision[ 'genome_id' ]        = cand[ 'genome_id' ]
            decision[ 'genome_length' ]    = cand[ 'genome_length' ]
            decision[ 'identity' ]         = cand[ 'identity' ]
            decision[ 'query_coverage' ]   = cand[ 'query_coverage' ]
            decision[ 'subject_coverage' ] = cand[ 'subject_coverage' ]
            unique_mapped_count += 1
        else:
            still_contested[ rgs_header ] = candidates

    logger.info(
        f'Improvement 2 unique-resolution: mapped {unique_mapped_count} RGS '
        f'(exactly 1 candidate AND that candidate not contested by another RGS)'
    )
    logger.info(
        f'Improvements 3/4 will resolve {len( still_contested )} RGS with multiple candidates or contested ones'
    )
    return still_contested


# ============================================================================
# Improvements 3+4: Hungarian (or fallback) assignment for contested candidates
# ============================================================================

def apply_hungarian_assignment(
    decisions: Dict[ str, Dict ],
    contested_candidates: Dict[ str, List[ Dict ] ],
    logger: logging.Logger,
) -> None:
    """Resolve remaining RGS<->genome conflicts via globally-optimal bipartite matching.
    Uses scipy.optimize.linear_sum_assignment if available, else greedy + fail-on-conflict.
    Mutates decisions in place."""
    if not contested_candidates:
        return

    rgs_list = sorted( contested_candidates.keys() )
    genome_ids = sorted( { c[ 'genome_id' ] for r in rgs_list for c in contested_candidates[ r ] } )

    if HAS_SCIPY:
        rgs_index = { r: i for i, r in enumerate( rgs_list ) }
        genome_index = { g: i for i, g in enumerate( genome_ids ) }
        infinity_cost = 1e9
        # cost matrix: shape (n_rgs, n_genome); minimize cost = maximize negative bitscore
        cost = np.full( ( len( rgs_list ), len( genome_ids ) ), infinity_cost )
        candidate_lookup: Dict[ Tuple[ int, int ], Dict ] = {}
        for r in rgs_list:
            for c in contested_candidates[ r ]:
                cost[ rgs_index[ r ], genome_index[ c[ 'genome_id' ] ] ] = -c[ 'bitscore' ]
                candidate_lookup[ ( rgs_index[ r ], genome_index[ c[ 'genome_id' ] ] ) ] = c

        # Hungarian on the rectangular cost matrix.
        # If n_rgs > n_genome, pad genome side with infinity costs (unassignable).
        n_rgs = len( rgs_list )
        n_genome = len( genome_ids )
        if n_rgs > n_genome:
            padding = np.full( ( n_rgs, n_rgs - n_genome ), infinity_cost )
            cost_padded = np.concatenate( ( cost, padding ), axis = 1 )
        else:
            cost_padded = cost

        row_ind, col_ind = linear_sum_assignment( cost_padded )

        hungarian_mapped_count = 0
        for r_idx, g_idx in zip( row_ind, col_ind ):
            if g_idx >= len( genome_ids ):
                continue   # assigned to padding (no real genome)
            if cost_padded[ r_idx, g_idx ] >= infinity_cost:
                continue   # not a real candidate edge
            cand = candidate_lookup[ ( r_idx, g_idx ) ]
            decision = decisions[ rgs_list[ r_idx ] ]
            decision[ 'status' ]           = 'mapped'
            decision[ 'mechanism' ]        = 'hungarian_optimal'
            decision[ 'genome_id' ]        = cand[ 'genome_id' ]
            decision[ 'genome_length' ]    = cand[ 'genome_length' ]
            decision[ 'identity' ]         = cand[ 'identity' ]
            decision[ 'query_coverage' ]   = cand[ 'query_coverage' ]
            decision[ 'subject_coverage' ] = cand[ 'subject_coverage' ]
            hungarian_mapped_count += 1
        logger.info( f'Improvement 4 (Hungarian via scipy): mapped {hungarian_mapped_count} contested RGS' )
        return

    # scipy not available: greedy fallback, fail-fast on any residual conflict.
    logger.warning(
        'scipy.optimize.linear_sum_assignment unavailable; '
        'using greedy fallback that fails on any residual conflict. '
        'Add scipy + numpy to the conda environment (ai/conda_environment.yml) for clean Hungarian assignment.'
    )
    sorted_candidates: List[ Tuple[ float, str, Dict ] ] = []
    for r in rgs_list:
        for c in contested_candidates[ r ]:
            sorted_candidates.append( ( c[ 'bitscore' ], r, c ) )
    sorted_candidates.sort( key = lambda t: ( -t[ 0 ], t[ 1 ] ) )   # descending bitscore, then RGS header for determinism

    rgs_claimed: Set[ str ] = set()
    genome_claimed: Set[ str ] = set()
    greedy_mapped_count = 0
    for bitscore, rgs_header, cand in sorted_candidates:
        if rgs_header in rgs_claimed:
            continue
        if cand[ 'genome_id' ] in genome_claimed:
            continue
        decision = decisions[ rgs_header ]
        decision[ 'status' ]           = 'mapped'
        decision[ 'mechanism' ]        = 'greedy_fallback'
        decision[ 'genome_id' ]        = cand[ 'genome_id' ]
        decision[ 'genome_length' ]    = cand[ 'genome_length' ]
        decision[ 'identity' ]         = cand[ 'identity' ]
        decision[ 'query_coverage' ]   = cand[ 'query_coverage' ]
        decision[ 'subject_coverage' ] = cand[ 'subject_coverage' ]
        rgs_claimed.add( rgs_header )
        genome_claimed.add( cand[ 'genome_id' ] )
        greedy_mapped_count += 1
    logger.info( f'Improvement 4 (greedy fallback): mapped {greedy_mapped_count} contested RGS' )


# ============================================================================
# Improvement 5: Fail-fast on any unresolved RGS
# ============================================================================

REASON_HUMAN_HINTS = {
    'rgs_header_unparseable_for_species':       'RGS header does not match expected 5-field format (rgs_<group>-<species>-<gene>-<source>-<id>); cannot identify source species.',
    'no_genome_index_for_species_*':            'RGS species marker was not found among the model_fastas-list FASTAs; check rgs_species_map.tsv and --rbh-species.',
    'rgs_longer_than_t1':                       'RGS protein is LONGER than the genome T1 isoform. T1 proteomes contain the longest isoform per gene. Either the RGS is a longer-isoform sequence from outside T1 or the T1 build is wrong.',
    'no_blast_hit_passes_thresholds':           f'No BLAST hit reaches >={MIN_IDENTITY_PERCENT}% identity AND >={MIN_COVERAGE_PERCENT}% query coverage AND >={MIN_COVERAGE_PERCENT}% subject coverage.',
    'no_blast_hit_passes_thresholds_after_hungarian': 'After optimal bipartite assignment, no candidate edge remained for this RGS.',
    'accession_not_in_genome_and_no_blast_hit': 'RGS NCBI accession is not in the source genome AND BLAST fallback found no hit meeting thresholds.',
}


def finalize_unresolved_reasons( decisions: Dict[ str, Dict ] ) -> None:
    """Fill in 'reason' for any decision that is still unresolved without one set."""
    for decision in decisions.values():
        if decision[ 'status' ] == 'mapped':
            continue
        if decision[ 'reason' ] is not None:
            continue
        if decision[ 'candidate_count' ] == 0:
            decision[ 'reason' ] = 'no_blast_hit_passes_thresholds'
        else:
            decision[ 'reason' ] = 'no_blast_hit_passes_thresholds_after_hungarian'


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
        description = 'Map RGS sequences to reference genome identifiers via 5-improvement pipeline'
    )
    parser.add_argument( '--blast-reports-list', type = Path, required = True,
                         help = 'File listing RGS-vs-genome BLAST report paths' )
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
    logger.info( 'Script 008 (rewritten 2026-05-23): Map RGS to Reference Genome Identifiers' )
    logger.info( '  Improvements: NCBI-accession-match, BLAST-thresholds, T1-length-invariant,' )
    logger.info( '                Hungarian-assignment, strict-fail-fast' )
    logger.info( '=' * 80 )
    logger.info( f'Started:           {datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )}' )
    logger.info( f'RGS FASTA:         {args.rgs_fasta}' )
    logger.info( f'BLAST reports:     {args.blast_reports_list}' )
    logger.info( f'Model FASTAs list: {args.model_fastas_list}' )
    logger.info( f'RBH species:       {", ".join( model_species_list )}' )
    logger.info( f'Identity threshold: >= {MIN_IDENTITY_PERCENT}%' )
    logger.info( f'Coverage threshold: >= {MIN_COVERAGE_PERCENT}% (both query and subject)' )
    logger.info( f'scipy available:   {HAS_SCIPY}' )
    logger.info( '' )

    try:
        # Read inputs
        rgs_sequences  = read_rgs_sequences( args.rgs_fasta, logger )
        if not rgs_sequences:
            raise PipelineFailure( f'No RGS sequences in {args.rgs_fasta}.' )
        blast_reports  = read_file_list( args.blast_reports_list, logger )
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
        map_via_ncbi_accession( decisions, rgs_sequences, species_to_genome_index, logger )
        blast_candidates_by_rgs = gather_blast_candidates(
            decisions, rgs_sequences, blast_reports, species_to_genome_index, model_species_list, logger,
        )
        still_contested = apply_unique_blast_candidates( decisions, blast_candidates_by_rgs, logger )
        apply_hungarian_assignment( decisions, still_contested, logger )
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
