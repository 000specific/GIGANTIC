#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 12 16:00 | Purpose: Select T1 (longest transcript per gene) from repository_genomes protein files with diverse header formats, reformat for genomesDB STEP_1 input, and generate identifier mapping files
# Human: Eric Edsinger

"""
004_ai-python-select_t1_longest_transcript.py

For each of the 31 repository_genomes species, parse the protein FASTA from
1-output/{genus_species}/protein.faa, extract gene IDs using species-appropriate
header parsing strategies, group proteins by gene, select the longest protein
per gene (T1), and write standardized T1 proteomes.

Output headers: >Genus_species-repository_genomes|transcript_id|gene_id

Strategies by species:
  - dot_t: Strip .tN suffix to get gene_id (AUGUSTUS-style)
  - dot_i: Strip .iN suffix to get gene_id (Hormiphora)
  - gene_attribute: Parse gene=X from header (EVM-style)
  - tab_Gene_attribute: Parse Gene=X from tab-separated fields (Nautilus)
  - trinity: Parse Trinity cNgNiN.orf pattern (Chondrosia)
  - fragment_range: Parse gN_start-end fragment pattern (Ministeria)
  - ncbi_gff: Map protein_id -> gene via GFF CDS entries (Hypsibius)
  - no_grouping: Each protein is its own gene (already T1)
  - already_done: Skip (Schmidtea - already processed)

Usage:
    python3 004_ai-python-select_t1_longest_transcript.py \
        --input-dir 1-output \
        --output-dir 2-output

Requires:
    - Python 3.6+
    - No external dependencies
"""

import argparse
import os
import sys
import re
import shutil
import logging
from pathlib import Path
from collections import defaultdict


# ============================================================================
# Setup logging
# ============================================================================

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s | %(levelname)s | %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger( __name__ )


# ============================================================================
# Per-species configuration
# ============================================================================

# Each species maps to:
#   strategy: how to extract gene_id from protein header
#   needs_filtering: whether multiple proteins per gene exist

SPECIES_CONFIGURATIONS = {

    # =========================================================================
    # ALREADY DONE - skip
    # =========================================================================
    'Schmidtea_mediterranea': {
        'strategy': 'already_done',
        'needs_filtering': False,
        'notes': 'Already T1-processed via gffread (23,125 T1 proteins from 58,739 genes)',
    },

    # =========================================================================
    # CATEGORY A: Already 1:1 gene:protein - header standardization only
    # =========================================================================

    # EVM gene models - gene= attribute in header
    'Chromosphaera_perkinsii': {
        'strategy': 'gene_attribute',
        'needs_filtering': False,
        'notes': '12,463 genes = 12,463 mRNA = 12,463 proteins. Header: >Nk52_evm1s1 gene=Nk52_evmTU1s1',
    },
    'Corallochytrium_limacisporum': {
        'strategy': 'gene_attribute',
        'needs_filtering': False,
        'notes': '7,535 genes = 7,535 mRNA = 7,535 proteins. Header: >Clim_evm1s1 gene=Clim_evmTU1s1',
    },
    'Ichthyophonus_hoferi': {
        'strategy': 'gene_attribute',
        'needs_filtering': False,
        'notes': '6,351 genes = 6,351 mRNA = 6,351 proteins. Header: >Ihof_evm1s1 gene=Ihof_evmTU1s1',
    },

    # EVM gene models - tab-separated Gene= attribute
    'Nautilus_pompilius': {
        'strategy': 'tab_Gene_attribute',
        'needs_filtering': False,
        'notes': '16,536 genes = 16,536 mRNA = 16,536 proteins. Tab-separated header with Gene=GWHGBECW000001',
    },

    # AUGUSTUS 1:1 gene:transcript
    'Lingula_anatina': {
        'strategy': 'dot_t',
        'needs_filtering': False,
        'notes': '34,105 genes = 34,105 transcript = 34,105 proteins. Header: >g1.t1',
    },
    'Phoronis_australis': {
        'strategy': 'dot_t',
        'needs_filtering': False,
        'notes': '20,473 genes = 20,473 mRNA = 20,473 proteins. Header: >g1.t1',
    },

    # Unique IDs - no gene grouping structure in headers
    'Pictodentalium_vernedei': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '32,166 genes = 32,166 mRNA = 32,166 proteins. Header: >Pve_chr01g00001.1',
    },
    'Pirum_gemmata': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '21,835 genes = 21,835 mRNA = 21,835 proteins. Header: >Pgem_evm1s1',
    },
    'Pigoraptor_chileana': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '14,492 unique proteins, headers: >Pchi_g1 (no transcript suffix, PASA-derived)',
    },
    'Pigoraptor_vietnamica': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '14,819 unique proteins, headers: >Pvie_g1 (no transcript suffix, PASA-derived)',
    },

    # Pre-filtered: protein count = gene count despite multi-transcript GFF
    'Urechis_unicinctus': {
        'strategy': 'dot_t',
        'needs_filtering': False,
        'notes': '49,091 proteins = 49,091 genes (but 56,760 transcripts in GFF). Pre-filtered 1:1.',
    },

    # Near-1:1 unique IDs
    'Chaetoderma_sp_LZ_2023a': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '23,675 proteins, 23,692 genes. Headers: >WZF000010. Effectively 1:1.',
    },
    'Lissachatina_fulica': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '23,726 mRNA = 23,726 proteins (no gene features in GFF). Headers: >Afu000001',
    },
    'Creolimax_fragrantissima': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '8,694 unique proteins (8,644 T1-suffixed + 50 without). Already T1 by nomenclature.',
    },

    # =========================================================================
    # CATEGORY B: No GFF, no gene grouping - each protein is its own gene
    # =========================================================================
    'Mnemiopsis_leidyi': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '16,548 proteins, no GFF. Header: >ML00011a',
    },
    'Pleurobrachia_bachei': {
        'strategy': 'no_grouping',
        'needs_filtering': False,
        'notes': '19,522 proteins, no GFF. Header: >3460379 sb|12258114| scaffold...',
    },

    # =========================================================================
    # CATEGORY C: Need T1 filtering - .tN suffix (most common)
    # =========================================================================
    'Abeoforma_whisleri': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '48,188 proteins, 32,047 unique genes (NO GFF). Headers: >g1.t1, >g1.t2. Up to 8 isoforms per gene.',
    },
    'Amphiscolops_sp_MND2022': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '61,445 proteins, 34,316 genes. Headers: >g4696.t1. Up to 57 isoforms per gene!',
    },
    'Berghia_stephanieae': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '26,595 proteins, 24,960 genes. Headers: >jg45245.t1. Up to 6 isoforms.',
    },
    'Beroe_ovata': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '18,661 proteins, 13,762 genes. Headers: >Bova1_5.0001.g1.t1. Up to 12 isoforms.',
    },
    'Convolutriloba_macropyga': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '41,247 proteins, 35,251 genes. Headers: >g8285.t1',
    },
    'Dicyema_japonicum': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '5,012 proteins, 4,743 genes. Headers: >g1.t1',
    },
    'Membranipora_membranacea': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '31,934 proteins, 25,909 genes. Headers: >g1.t1',
    },
    'Schizocardium_californicum': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '50,499 proteins, 42,362 genes. Headers: >g15768.t1',
    },
    'Styela_plicata': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '24,382 proteins, 21,900 genes. Headers: >g546.t1',
    },
    'Parvularia_atlantis': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '10,162 proteins, 9,028 genes. Headers: >Patl_g1155.t1',
    },

    # BRAKER1 gene models - .tN suffix
    'Hoilungia_hongkongensis_H13': {
        'strategy': 'dot_t',
        'needs_filtering': True,
        'notes': '12,575 proteins, 12,010 genes. Headers: >braker1_g00001.t1. Up to 4 isoforms.',
    },

    # =========================================================================
    # CATEGORY D: Need T1 filtering - .iN suffix (Hormiphora)
    # =========================================================================
    'Hormiphora_californensis': {
        'strategy': 'dot_i',
        'needs_filtering': True,
        'notes': '19,693 proteins, 14,335 unique genes. Headers: >Hcv1.av93.c1.g1.i1. Up to 41 isoforms.',
    },

    # =========================================================================
    # CATEGORY E: Need T1 filtering - NCBI GFF mapping (Hypsibius)
    # =========================================================================
    'Hypsibius_dujardini': {
        'strategy': 'ncbi_gff',
        'needs_filtering': True,
        'notes': '20,853 proteins, 20,076 genes. Headers: >OQV11387.1 hypothetical protein BV898_14264. Need GFF for protein_id -> gene mapping.',
    },

    # =========================================================================
    # CATEGORY F: Need T1 filtering - Trinity isoforms (Chondrosia)
    # =========================================================================
    'Chondrosia_reniformis': {
        'strategy': 'trinity',
        'needs_filtering': True,
        'notes': '84,032 proteins, 15,893 unique gene groups. Headers: >POR_Chon_reni|ERR10177766|13226c0g1i1.1. Up to 498 isoforms per gene!',
    },

    # =========================================================================
    # CATEGORY G: Need T1 filtering - fragment ranges (Ministeria)
    # =========================================================================
    'Ministeria_vibrans': {
        'strategy': 'fragment_range',
        'needs_filtering': True,
        'notes': '13,332 proteins, 12,112 unique genes. Headers: >Mvib_g3356_1-83. Gene fragments: select longest.',
    },
}


# ============================================================================
# genomesDB STEP_1 configuration
# ============================================================================

# Source genome identifier for each species, derived from repository URLs.
# Format: repository_type_record_id
SPECIES___SOURCE_IDENTIFIERS = {
    'Abeoforma_whisleri': 'figshare_21290514',
    'Amphiscolops_sp_MND2022': 'zenodo_13743914',
    'Berghia_stephanieae': 'dryad_D1BS33',
    'Beroe_ovata': 'bovadb_v1_5',
    'Chaetoderma_sp_LZ_2023a': 'figshare_24099477',
    'Chondrosia_reniformis': 'dryad_dncjsxm47',
    'Chromosphaera_perkinsii': 'figshare_5426494',
    'Convolutriloba_macropyga': 'zenodo_13743914',
    'Corallochytrium_limacisporum': 'figshare_5426470',
    'Creolimax_fragrantissima': 'dryad_dncjsxm47',
    'Dicyema_japonicum': 'oist_77',
    'Hoilungia_hongkongensis_H13': 'bitbucket_hoilungia_genome',
    'Hormiphora_californensis': 'github_hormiphora',
    'Hypsibius_dujardini': 'zenodo_13148652',
    'Ichthyophonus_hoferi': 'figshare_5426488',
    'Lingula_anatina': 'oist_47',
    'Lissachatina_fulica': 'gigadb_100647',
    'Membranipora_membranacea': 'dryad_76hdr7t3f',
    'Ministeria_vibrans': 'figshare_19895962',
    'Nautilus_pompilius': 'ngdc_GWHBECW00000000',
    'Parvularia_atlantis': 'figshare_19895962',
    'Phoronis_australis': 'oist_51',
    'Pictodentalium_vernedei': 'figshare_38684090',
    'Pigoraptor_chileana': 'figshare_19895962',
    'Pigoraptor_vietnamica': 'figshare_19895962',
    'Pirum_gemmata': 'figshare_5426506',
    'Pleurobrachia_bachei': 'moroz_lab_2024',
    'Schizocardium_californicum': 'zenodo_13148652',
    'Schmidtea_mediterranea': 'zenodo_13798866',
    'Styela_plicata': 'zenodo_13148652',
    'Urechis_unicinctus': 'dryad_brv15dvhv',
}

# Species to exclude from genomesDB output (overlap with kim_2025)
EXCLUDED_FROM_GENOMESDB = {
    'Mnemiopsis_leidyi',       # Overlap with kim_2025_genomes
}

DEFAULT_DOWNLOAD_DATE = 'downloaded_20260211'


# ============================================================================
# Gene ID extraction functions
# ============================================================================

def extract_gene_id_dot_t( header ):
    """
    Extract gene_id by stripping the last .tN suffix from the protein header.

    Examples:
        >g1.t1           -> transcript_id='g1.t1',      gene_id='g1'
        >g1.t2           -> transcript_id='g1.t2',      gene_id='g1'
        >jg45245.t1      -> transcript_id='jg45245.t1', gene_id='jg45245'
        >Bova1_5.0001.g1.t1 -> transcript_id='Bova1_5.0001.g1.t1', gene_id='Bova1_5.0001.g1'
        >Patl_g1155.t1   -> transcript_id='Patl_g1155.t1', gene_id='Patl_g1155'

    Parameters:
        header (str): Full header line without '>'

    Returns:
        tuple: (transcript_id, gene_id)
    """

    # Take first whitespace-delimited token as the identifier
    transcript_identifier = header.split()[ 0 ]

    # Strip the last .tN where N is one or more digits
    match = re.match( r'^(.+)\.[tT](\d+)$', transcript_identifier )
    if match:
        gene_identifier = match.group( 1 )
    else:
        # No .tN suffix found - transcript IS the gene
        gene_identifier = transcript_identifier

    return ( transcript_identifier, gene_identifier )


def extract_gene_id_dot_i( header ):
    """
    Extract gene_id by stripping the last .iN suffix (Hormiphora format).

    Examples:
        >Hcv1.av93.c1.g1.i1  -> gene_id='Hcv1.av93.c1.g1'
        >Hcv1.av93.c1.g6.i4  -> gene_id='Hcv1.av93.c1.g6'

    Parameters:
        header (str): Full header line without '>'

    Returns:
        tuple: (transcript_id, gene_id)
    """

    transcript_identifier = header.split()[ 0 ]

    match = re.match( r'^(.+)\.[iI](\d+)$', transcript_identifier )
    if match:
        gene_identifier = match.group( 1 )
    else:
        gene_identifier = transcript_identifier

    return ( transcript_identifier, gene_identifier )


def extract_gene_id_gene_attribute( header ):
    """
    Extract gene_id from 'gene=X' attribute in header (EVM format).

    Examples:
        >Nk52_evm1s1 gene=Nk52_evmTU1s1  -> transcript_id='Nk52_evm1s1', gene_id='Nk52_evmTU1s1'
        >Clim_evm1s1 gene=Clim_evmTU1s1  -> transcript_id='Clim_evm1s1', gene_id='Clim_evmTU1s1'

    Parameters:
        header (str): Full header line without '>'

    Returns:
        tuple: (transcript_id, gene_id)
    """

    transcript_identifier = header.split()[ 0 ]

    match = re.search( r'gene=(\S+)', header )
    if match:
        gene_identifier = match.group( 1 )
    else:
        # Fallback: use transcript_id as gene_id
        gene_identifier = transcript_identifier

    return ( transcript_identifier, gene_identifier )


def extract_gene_id_tab_Gene_attribute( header ):
    """
    Extract gene_id from tab-separated 'Gene=X' field (Nautilus format).

    Example:
        >GWHPBECW000001\tmRNA=GWHTBECW000001\tGene=GWHGBECW000001\t...
        -> transcript_id='GWHPBECW000001', gene_id='GWHGBECW000001'

    Parameters:
        header (str): Full header line without '>'

    Returns:
        tuple: (transcript_id, gene_id)
    """

    # Split by any whitespace (tabs or spaces)
    parts_header = header.split()
    transcript_identifier = parts_header[ 0 ]

    gene_identifier = transcript_identifier  # default
    for field in parts_header[ 1: ]:
        if field.startswith( 'Gene=' ):
            gene_identifier = field.replace( 'Gene=', '' )
            break

    return ( transcript_identifier, gene_identifier )


def extract_gene_id_trinity( header ):
    """
    Extract gene_id from Trinity-style c_g_i pattern (Chondrosia format).

    The header format after last pipe:
        {cluster}c{component}g{gene}i{isoform}.{orf}

    Gene group = everything up to the isoform (cNgN).

    Examples:
        >POR_Chon_reni|ERR10177766|13226c0g1i1.1
            -> gene_id='13226c0g1' (strips iN.orf)
        >POR_Chon_reni|ERR10177766|12082c0g1i13.2
            -> gene_id='12082c0g1'

    Parameters:
        header (str): Full header line without '>'

    Returns:
        tuple: (transcript_id, gene_id)
    """

    transcript_identifier = header.split()[ 0 ]

    # Extract the Trinity-style part after the last pipe
    parts_pipe = transcript_identifier.split( '|' )
    trinity_part = parts_pipe[ -1 ]  # e.g., '13226c0g1i1.1'

    # Extract gene group: everything before 'i' followed by digit
    match = re.match( r'^(\d+c\d+g\d+)', trinity_part )
    if match:
        gene_identifier = match.group( 1 )
    else:
        # Fallback: use full header as gene
        gene_identifier = transcript_identifier

    return ( transcript_identifier, gene_identifier )


def extract_gene_id_fragment_range( header ):
    """
    Extract gene_id from fragment range pattern (Ministeria format).

    Header: >Mvib_gNNNN_start-end
    Gene: Mvib_gNNNN (strip the _start-end coordinate range)

    Examples:
        >Mvib_g3356_1-83     -> gene_id='Mvib_g3356'
        >Mvib_g3356_84-1032  -> gene_id='Mvib_g3356'
        >Mvib_g4839_920-1940 -> gene_id='Mvib_g4839'

    Parameters:
        header (str): Full header line without '>'

    Returns:
        tuple: (transcript_id, gene_id)
    """

    transcript_identifier = header.split()[ 0 ]

    # Pattern: Mvib_gNNNN_start-end
    match = re.match( r'^(Mvib_g\d+)_\d+-\d+$', transcript_identifier )
    if match:
        gene_identifier = match.group( 1 )
    else:
        # Fallback: use full identifier
        gene_identifier = transcript_identifier

    return ( transcript_identifier, gene_identifier )


def extract_gene_id_no_grouping( header ):
    """
    No gene grouping - each protein is its own gene (already T1).

    Parameters:
        header (str): Full header line without '>'

    Returns:
        tuple: (transcript_id, gene_id) where both are the same
    """

    transcript_identifier = header.split()[ 0 ]
    gene_identifier = transcript_identifier

    return ( transcript_identifier, gene_identifier )


def extract_gene_id_already_done( header ):
    """
    Pass-through extraction for species whose input protein.faa is already
    a T1 proteome with pipe-delimited headers of the form:

        >Genus_species-repository_genomes|transcript_id|gene_id

    The input is one protein per gene (T1 already performed upstream - e.g.
    via gffread during this pipeline's 002_extract_protein step, or delivered
    as T1 by the source repository). This extractor simply parses the
    pipe-delimited fields so the downstream reformat step can convert the
    headers to the GIGANTIC dash-delimited 4-field output format
    (Species-gene_id-transcript_id-transcript_id).

    Why this is a distinct strategy rather than a global skip:
        A previous version of this script used `continue` to skip species
        with strategy='already_done' entirely, which meant the script alone
        could not regenerate their 3-output T1 files on a fresh run - they
        had to be produced by a separate upstream step. Including them as
        a first-class strategy here makes the script self-contained: given
        the 1-output/{species}/protein.faa (which the pipeline's earlier
        steps guarantee), this script produces the full GIGANTIC-named
        output for every species in SPECIES_CONFIGURATIONS.

    Parameters:
        header (str): Full header line without '>'
            Expected format: Genus_species-repository_genomes|transcript_id|gene_id

    Returns:
        tuple: (transcript_id, gene_id)
    """

    identifier = header.split()[ 0 ]
    parts_pipe = identifier.split( '|' )

    if len( parts_pipe ) >= 3:
        transcript_identifier = parts_pipe[ 1 ]
        gene_identifier = parts_pipe[ 2 ]
    else:
        # Fallback: header doesn't match the expected pipe-delimited T1 format.
        # Treat as its own gene (same semantic as no_grouping) so the species
        # still produces output rather than silently dropping.
        transcript_identifier = identifier
        gene_identifier = identifier

    return ( transcript_identifier, gene_identifier )


def build_ncbi_protein_to_gene_mapping( gff3_path ):
    """
    Parse NCBI-format GFF3 to build protein_id -> gene_id mapping.

    Uses CDS entries which have:
        protein_id=OQV25851.1
        locus_tag=BV898_00001

    And mRNA entries which have:
        ID=rna-gnl|WGS:MTYJ|mrna.BV898_00001.1
        Parent=gene-BV898_00001

    Strategy:
        1. Parse CDS entries: protein_id -> locus_tag
        2. Use locus_tag as the gene_id (each gene has a unique locus_tag)

    Parameters:
        gff3_path (Path): Path to the GFF3 annotation file

    Returns:
        dict: protein_id -> gene_id (locus_tag)
    """

    protein_identifiers___gene_identifiers = {}

    # ID=cds-OQV25851.1;Parent=rna-gnl|WGS:MTYJ|mrna.BV898_00001.1;...;locus_tag=BV898_00001;...;protein_id=OQV25851.1
    with open( gff3_path, 'r' ) as input_gff3:
        for line in input_gff3:
            line = line.strip()
            if line.startswith( '#' ) or len( line ) == 0:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 9:
                continue

            feature_type = parts[ 2 ]
            if feature_type != 'CDS':
                continue

            attributes_string = parts[ 8 ]

            # Parse attributes
            protein_identifier = None
            locus_tag = None

            for pair in attributes_string.split( ';' ):
                if '=' in pair:
                    key, value = pair.split( '=', 1 )
                    key = key.strip()
                    value = value.strip()

                    if key == 'protein_id':
                        protein_identifier = value
                    elif key == 'locus_tag':
                        locus_tag = value

            if protein_identifier and locus_tag:
                # Multiple CDS (exons) per protein - only need one entry
                if protein_identifier not in protein_identifiers___gene_identifiers:
                    protein_identifiers___gene_identifiers[ protein_identifier ] = locus_tag

    return protein_identifiers___gene_identifiers


# ============================================================================
# Strategy dispatcher
# ============================================================================

STRATEGY_FUNCTIONS = {
    'dot_t': extract_gene_id_dot_t,
    'dot_i': extract_gene_id_dot_i,
    'gene_attribute': extract_gene_id_gene_attribute,
    'tab_Gene_attribute': extract_gene_id_tab_Gene_attribute,
    'trinity': extract_gene_id_trinity,
    'fragment_range': extract_gene_id_fragment_range,
    'no_grouping': extract_gene_id_no_grouping,
    'already_done': extract_gene_id_already_done,
}


# ============================================================================
# Core functions
# ============================================================================

def parse_fasta( fasta_path ):
    """
    Parse a FASTA file, returning list of (header, sequence) tuples.
    Header is the full line after '>' (without the '>').
    """

    entries = []
    current_header = None
    current_sequence_parts = []

    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()
            if line.startswith( '>' ):
                if current_header is not None:
                    entries.append( ( current_header, ''.join( current_sequence_parts ) ) )
                current_header = line[ 1: ]
                current_sequence_parts = []
            elif len( line ) > 0:
                current_sequence_parts.append( line )

        if current_header is not None:
            entries.append( ( current_header, ''.join( current_sequence_parts ) ) )

    return entries


def clean_protein_sequence( sequence ):
    """
    Clean protein sequence: remove stop codon markers (* and .) at the end.
    Also remove internal stop codons (*) for length calculation.
    """

    # Remove trailing stop codons
    sequence_clean = sequence.rstrip( '*' ).rstrip( '.' )

    return sequence_clean


def select_t1_for_species( genus_species, protein_fasta_path, annotation_path, configuration ):
    """
    Process one species: parse proteins, group by gene, select longest per gene.

    Parameters:
        genus_species (str): Species name
        protein_fasta_path (Path): Path to protein.faa
        annotation_path (Path): Path to annotation.gff3 (may not exist)
        configuration (dict): Species configuration from SPECIES_CONFIGURATIONS

    Returns:
        dict with results, or None on failure
    """

    strategy = configuration[ 'strategy' ]

    logger.info( f'============================================' )
    logger.info( f'Processing: {genus_species}' )
    logger.info( f'  Strategy: {strategy}' )
    logger.info( f'  Needs filtering: {configuration[ "needs_filtering" ]}' )
    logger.info( f'  Notes: {configuration[ "notes" ]}' )
    logger.info( f'============================================' )

    # Step 1: Parse protein FASTA
    logger.info( f'  Step 1: Parsing protein FASTA...' )
    entries = parse_fasta( protein_fasta_path )
    total_protein_count = len( entries )
    logger.info( f'    Total proteins: {total_protein_count}' )

    if total_protein_count == 0:
        logger.error( f'  CRITICAL: No proteins found in {protein_fasta_path}!' )
        return None

    # Step 2: Get gene extraction function
    if strategy == 'ncbi_gff':
        # Special handling: need to parse GFF first
        if annotation_path is None or not annotation_path.exists():
            logger.error( f'  CRITICAL: ncbi_gff strategy requires annotation.gff3 but file not found!' )
            return None

        logger.info( f'  Step 2a: Building protein_id -> gene mapping from GFF...' )
        protein_identifiers___gene_identifiers = build_ncbi_protein_to_gene_mapping( annotation_path )
        logger.info( f'    Mapped {len( protein_identifiers___gene_identifiers )} protein_ids to genes' )

        # Create a closure that uses the mapping
        def extract_gene_id_ncbi_gff( header ):
            transcript_identifier = header.split()[ 0 ]
            gene_identifier = protein_identifiers___gene_identifiers.get( transcript_identifier, transcript_identifier )
            return ( transcript_identifier, gene_identifier )

        extraction_function = extract_gene_id_ncbi_gff
    else:
        extraction_function = STRATEGY_FUNCTIONS[ strategy ]

    # Step 3: Group proteins by gene_id
    logger.info( f'  Step 2: Extracting gene IDs and grouping proteins...' )
    gene_identifiers___protein_entries = defaultdict( list )
    unmapped_count = 0

    for header, sequence in entries:
        transcript_identifier, gene_identifier = extraction_function( header )
        sequence_clean = clean_protein_sequence( sequence )
        gene_identifiers___protein_entries[ gene_identifier ].append( {
            'transcript_identifier': transcript_identifier,
            'gene_identifier': gene_identifier,
            'sequence': sequence_clean,
            'length': len( sequence_clean ),
            'original_header': header,
        } )

    unique_gene_count = len( gene_identifiers___protein_entries )
    logger.info( f'    Unique genes: {unique_gene_count}' )

    # Count multi-isoform genes
    multi_isoform_gene_count = sum(
        1 for gene_identifier in gene_identifiers___protein_entries
        if len( gene_identifiers___protein_entries[ gene_identifier ] ) > 1
    )
    logger.info( f'    Multi-isoform genes: {multi_isoform_gene_count}' )

    if multi_isoform_gene_count > 0:
        max_isoforms = max(
            len( protein_entries )
            for protein_entries in gene_identifiers___protein_entries.values()
        )
        logger.info( f'    Maximum isoforms per gene: {max_isoforms}' )

    # Step 4: Select longest protein per gene (T1)
    logger.info( f'  Step 3: Selecting longest protein per gene (T1)...' )
    t1_entries = []

    for gene_identifier in sorted( gene_identifiers___protein_entries.keys() ):
        protein_entries = gene_identifiers___protein_entries[ gene_identifier ]

        # Find the longest protein
        longest_entry = max( protein_entries, key = lambda entry: entry[ 'length' ] )
        t1_entries.append( longest_entry )

    t1_count = len( t1_entries )
    logger.info( f'    T1 proteins selected: {t1_count}' )

    # Step 5: Calculate summary statistics
    total_sequence_length = sum( entry[ 'length' ] for entry in t1_entries )
    average_length = total_sequence_length / t1_count if t1_count > 0 else 0
    min_length = min( entry[ 'length' ] for entry in t1_entries ) if t1_count > 0 else 0
    max_length = max( entry[ 'length' ] for entry in t1_entries ) if t1_count > 0 else 0

    logger.info( f'  Summary:' )
    logger.info( f'    Input proteins:        {total_protein_count}' )
    logger.info( f'    Unique genes:          {unique_gene_count}' )
    logger.info( f'    Multi-isoform genes:   {multi_isoform_gene_count}' )
    logger.info( f'    T1 proteins:           {t1_count}' )
    logger.info( f'    Reduction:             {total_protein_count - t1_count} removed ({( total_protein_count - t1_count ) / total_protein_count * 100:.1f}%)' )
    logger.info( f'    Avg protein length:    {average_length:.0f} aa' )
    logger.info( f'    Min protein length:    {min_length} aa' )
    logger.info( f'    Max protein length:    {max_length} aa' )

    summary = {
        'genus_species': genus_species,
        'strategy': strategy,
        'total_proteins': total_protein_count,
        'unique_genes': unique_gene_count,
        'multi_isoform_genes': multi_isoform_gene_count,
        't1_count': t1_count,
        'removed_count': total_protein_count - t1_count,
        'average_length': average_length,
    }

    return ( t1_entries, summary )


def sanitize_identifier_for_header( identifier ):
    """
    Replace pipe characters in identifiers to maintain the standard 3-field
    header format: >Species-source|transcript_id|gene_id

    Pipe characters within transcript_id or gene_id would create extra fields.
    Replace them with double underscores (__) to preserve information.

    Parameters:
        identifier (str): Original identifier that may contain pipe characters

    Returns:
        str: Sanitized identifier with pipes replaced
    """

    return identifier.replace( '|', '__' )


def write_t1_proteome( t1_entries, genus_species, output_path ):
    """
    Write T1 proteome with standardized headers.

    Header format: >Genus_species-repository_genomes|transcript_id|gene_id

    Pipe characters within transcript_id or gene_id are replaced with __ to
    maintain exactly 3 pipe-delimited fields.

    Parameters:
        t1_entries (list): List of dicts with transcript_identifier, gene_identifier, sequence
        genus_species (str): Species name
        output_path (Path): Output file path
    """

    with open( output_path, 'w' ) as output_proteome:
        for entry in t1_entries:
            transcript_identifier = sanitize_identifier_for_header( entry[ 'transcript_identifier' ] )
            gene_identifier = sanitize_identifier_for_header( entry[ 'gene_identifier' ] )
            sequence = entry[ 'sequence' ]

            # Standardized header: exactly 3 pipe-delimited fields
            header = f'>{genus_species}-repository_genomes|{transcript_identifier}|{gene_identifier}'
            output = header + '\n'
            output_proteome.write( output )

            # Write sequence in 80-character lines
            for index in range( 0, len( sequence ), 80 ):
                output = sequence[ index:index + 80 ] + '\n'
                output_proteome.write( output )


# ============================================================================
# genomesDB reformat functions
# ============================================================================

def sanitize_identifier( identifier ):
    """
    Replace dashes with underscores in an identifier.

    This ensures consistent delimiter usage:
    - Dashes (-) separate major fields in file names and headers
    - Underscores (_) are used within identifiers

    Parameters:
        identifier (str): Original identifier that may contain dashes

    Returns:
        str: Sanitized identifier with dashes replaced by underscores
    """

    return identifier.replace( '-', '_' )


def parse_genome_fasta_identifiers( fasta_path ):
    """
    Extract all scaffold/chromosome identifiers from a genome FASTA file.

    Parameters:
        fasta_path (Path): Path to genome FASTA file

    Returns:
        list: List of scaffold/chromosome identifiers in order
    """

    identifiers = []

    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            if line.startswith( '>' ):
                identifier = line[ 1: ].strip().split()[ 0 ]
                identifiers.append( identifier )

    return identifiers


def reformat_t1_for_genomesdb( protein_t1_path, genus_species, output_path ):
    """
    Read existing T1 proteome (pipe-delimited headers) and write with
    genomesDB dash-delimited headers, replacing dashes in source IDs.

    Current format: >Genus_species-repository_genomes|transcript_id|gene_id
    New format:     >Genus_species-gene_id-transcript_id-protein_id

    Parameters:
        protein_t1_path (Path): Input protein_T1.faa
        genus_species (str): Species name
        output_path (Path): Output .aa file

    Returns:
        list: List of entry dicts with original and updated identifiers
    """

    sequence_entries = []
    current_header = None
    current_sequence_parts = []

    with open( protein_t1_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()
            if line.startswith( '>' ):
                if current_header is not None:
                    sequence_entries.append( ( current_header, ''.join( current_sequence_parts ) ) )
                current_header = line[ 1: ]
                current_sequence_parts = []
            elif len( line ) > 0:
                current_sequence_parts.append( line )

        if current_header is not None:
            sequence_entries.append( ( current_header, ''.join( current_sequence_parts ) ) )

    # Parse and reformat
    reformatted_entries = []

    with open( output_path, 'w' ) as output_fasta:
        for header, sequence in sequence_entries:
            # Parse pipe-delimited header: Genus_species-repository_genomes|transcript_id|gene_id
            parts_header = header.split( '|' )

            if len( parts_header ) >= 3:
                original_transcript_identifier = parts_header[ 1 ]
                original_gene_identifier = parts_header[ 2 ]
            elif len( parts_header ) == 2:
                original_transcript_identifier = parts_header[ 1 ]
                original_gene_identifier = parts_header[ 1 ]
            else:
                # Fallback: use full header
                original_transcript_identifier = header.split()[ 0 ]
                original_gene_identifier = original_transcript_identifier

            # protein_id = transcript_id for repository_genomes
            original_protein_identifier = original_transcript_identifier

            # Sanitize: replace dashes with underscores
            updated_gene_identifier = sanitize_identifier( original_gene_identifier )
            updated_transcript_identifier = sanitize_identifier( original_transcript_identifier )
            updated_protein_identifier = sanitize_identifier( original_protein_identifier )

            # Write new header
            new_header = (
                f'>{genus_species}'
                f'-{updated_gene_identifier}'
                f'-{updated_transcript_identifier}'
                f'-{updated_protein_identifier}'
            )
            output = new_header + '\n'
            output_fasta.write( output )

            for index in range( 0, len( sequence ), 80 ):
                output = sequence[ index:index + 80 ] + '\n'
                output_fasta.write( output )

            reformatted_entries.append( {
                'original_gene_identifier': original_gene_identifier,
                'updated_gene_identifier': updated_gene_identifier,
                'original_transcript_identifier': original_transcript_identifier,
                'updated_transcript_identifier': updated_transcript_identifier,
                'original_protein_identifier': original_protein_identifier,
                'updated_protein_identifier': updated_protein_identifier,
            } )

    return reformatted_entries


def write_genome_identifier_map( all_species_results, output_path ):
    """
    Write the genome identifier mapping TSV file.

    Parameters:
        all_species_results (list): List of per-species result dicts
        output_path (Path): Output file path

    Returns:
        int: Total entry count
    """

    total_count = 0

    with open( output_path, 'w' ) as output_map:
        output = (
            'Genus_Species (genus species name)'
            '\t'
            'original_genome_identifier (original scaffold or chromosome name from source)'
            '\t'
            'updated_genome_identifier (updated name with dashes replaced by underscores)'
            '\n'
        )
        output_map.write( output )

        for species_result in all_species_results:
            genus_species = species_result[ 'genus_species' ]
            genome_identifiers = species_result.get( 'genome_identifiers', [] )

            for original_identifier in genome_identifiers:
                updated_identifier = sanitize_identifier( original_identifier )
                output = f'{genus_species}\t{original_identifier}\t{updated_identifier}\n'
                output_map.write( output )
                total_count += 1

    logger.info( f'  Genome identifier map: {total_count} entries written to {output_path.name}' )

    return total_count


def write_sequence_identifier_map( all_species_results, output_path ):
    """
    Write the sequence identifier mapping TSV file.

    Parameters:
        all_species_results (list): List of per-species result dicts
        output_path (Path): Output file path

    Returns:
        int: Total entry count
    """

    total_count = 0

    with open( output_path, 'w' ) as output_map:
        output = (
            'Genus_Species (genus species name)'
            '\t'
            'original_gene_id (gene identifier from source annotation)'
            '\t'
            'updated_gene_id (gene identifier with dashes replaced by underscores)'
            '\t'
            'original_transcript_id (transcript identifier from source annotation)'
            '\t'
            'updated_transcript_id (transcript identifier with dashes replaced by underscores)'
            '\t'
            'original_protein_id (protein identifier from source annotation)'
            '\t'
            'updated_protein_id (protein identifier with dashes replaced by underscores)'
            '\n'
        )
        output_map.write( output )

        for species_result in all_species_results:
            genus_species = species_result[ 'genus_species' ]
            sequence_entries = species_result[ 'sequence_entries' ]

            for entry in sequence_entries:
                output = (
                    f'{genus_species}'
                    f'\t{entry[ "original_gene_identifier" ]}'
                    f'\t{entry[ "updated_gene_identifier" ]}'
                    f'\t{entry[ "original_transcript_identifier" ]}'
                    f'\t{entry[ "updated_transcript_identifier" ]}'
                    f'\t{entry[ "original_protein_identifier" ]}'
                    f'\t{entry[ "updated_protein_identifier" ]}'
                    '\n'
                )
                output_map.write( output )
                total_count += 1

    logger.info( f'  Sequence identifier map: {total_count} entries written to {output_path.name}' )

    return total_count


# ============================================================================
# Main
# ============================================================================

def main():

    parser = argparse.ArgumentParser(
        description = 'Select T1 (longest transcript per gene) from repository_genomes protein files'
    )
    parser.add_argument( '--input-dir', required = True,
                         help = 'Directory containing per-species subdirectories with protein.faa' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Output directory (will create per-species subdirectories)' )
    parser.add_argument( '--species', nargs = '+', default = None,
                         help = 'Process only specified species (default: all)' )
    parser.add_argument( '--genomesdb-dir', default = None,
                         help = 'Output directory for genomesDB STEP_1 formatted files (default: 3-output next to output-dir)' )
    parser.add_argument( '--download-date', default = DEFAULT_DOWNLOAD_DATE,
                         help = f'Download date string for filenames (default: {DEFAULT_DOWNLOAD_DATE})' )
    arguments = parser.parse_args()

    input_directory = Path( arguments.input_dir )
    output_directory = Path( arguments.output_dir )
    download_date = arguments.download_date

    # Derive genomesdb directory
    if arguments.genomesdb_dir:
        genomesdb_directory = Path( arguments.genomesdb_dir )
    else:
        genomesdb_directory = output_directory.parent / '3-output'

    print( '============================================' )
    print( '004: Select T1 longest transcript per gene' )
    print( '============================================' )
    print( '' )

    # Determine which species to process
    species_to_process = []

    for species_directory in sorted( input_directory.iterdir() ):
        if not species_directory.is_dir():
            continue

        genus_species = species_directory.name

        # Skip cache/hidden directories
        if genus_species.startswith( '_' ) or genus_species.startswith( '.' ):
            continue

        # Check if species has a configuration
        if genus_species not in SPECIES_CONFIGURATIONS:
            logger.warning( f'SKIP {genus_species}: No configuration defined in SPECIES_CONFIGURATIONS' )
            continue

        # Check species filter
        if arguments.species and genus_species not in arguments.species:
            continue

        configuration = SPECIES_CONFIGURATIONS[ genus_species ]

        # Note: strategy='already_done' species used to be skipped here and
        # handled by a separate special-case branch below. As of 2026-04-23
        # they are treated as a first-class strategy (extract_gene_id_already_done)
        # so the script can regenerate their 3-output T1 files from the
        # 1-output/{species}/protein.faa input on a fresh run.

        # Check protein file exists
        protein_fasta_path = species_directory / 'protein.faa'
        if not protein_fasta_path.exists() or protein_fasta_path.stat().st_size == 0:
            logger.warning( f'SKIP {genus_species}: No protein.faa found' )
            continue

        # Check annotation file (needed for ncbi_gff strategy)
        annotation_path = species_directory / 'annotation.gff3'
        if not annotation_path.exists():
            annotation_path = None

        species_to_process.append( ( genus_species, protein_fasta_path, annotation_path, configuration ) )

    if len( species_to_process ) == 0:
        logger.info( 'No species to process.' )
        return

    logger.info( f'Species to process: {len( species_to_process )}' )
    for genus_species, _, _, configuration in species_to_process:
        filtering_tag = 'FILTER' if configuration[ 'needs_filtering' ] else 'STANDARDIZE'
        logger.info( f'  - {genus_species} [{filtering_tag}, {configuration[ "strategy" ]}]' )
    print( '' )

    # Process each species
    all_summaries = []
    failed_species = []

    for genus_species, protein_fasta_path, annotation_path, configuration in species_to_process:
        result = select_t1_for_species( genus_species, protein_fasta_path, annotation_path, configuration )

        if result is None:
            logger.error( f'  FAILED: {genus_species}' )
            failed_species.append( genus_species )
            continue

        t1_entries, summary = result

        # Write T1 proteome to 2-output/{genus_species}/
        species_output_directory = output_directory / genus_species
        species_output_directory.mkdir( parents = True, exist_ok = True )

        output_proteome_path = species_output_directory / 'protein_T1.faa'
        logger.info( f'  Writing T1 proteome: {output_proteome_path}' )
        write_t1_proteome( t1_entries, genus_species, output_proteome_path )

        # Verify output
        output_size = output_proteome_path.stat().st_size
        logger.info( f'  Output file size: {output_size / 1024:.0f} KB' )

        summary[ 'output_file' ] = str( output_proteome_path )
        all_summaries.append( summary )
        print( '' )

    # =========================================================================
    # Final summary table
    # =========================================================================
    # (Schmidtea_mediterranea special-case handler was removed on 2026-04-23:
    # it relied on 2-output/Schmidtea/protein.faa being populated by an
    # external step. With the already_done strategy now a first-class T1
    # selection strategy, Schmidtea flows through the normal species_to_process
    # loop and produces both 2-output/Schmidtea/protein_T1.faa and the
    # reformatted 3-output/T1_proteomes/{GIGANTIC-name}.aa without special
    # handling.)
    print( '' )
    print( '============================================' )
    print( 'T1 selection complete' )
    print( '============================================' )
    print( '' )

    if len( all_summaries ) > 0:
        print( f'{"Species":<35} {"Strategy":<15} {"Input":>8} {"Genes":>8} {"T1":>8} {"Removed":>8} {"Avg Len":>8}' )
        print( '-' * 96 )

        for summary in all_summaries:
            print(
                f'{summary[ "genus_species" ]:<35} '
                f'{summary[ "strategy" ]:<15} '
                f'{summary[ "total_proteins" ]:>8} '
                f'{summary[ "unique_genes" ]:>8} '
                f'{summary[ "t1_count" ]:>8} '
                f'{summary[ "removed_count" ]:>8} '
                f'{summary[ "average_length" ]:>8.0f}'
            )

        print( '-' * 96 )
        total_input = sum( s[ 'total_proteins' ] for s in all_summaries )
        total_t1 = sum( s[ 't1_count' ] for s in all_summaries )
        total_removed = sum( s[ 'removed_count' ] for s in all_summaries )
        print( f'{"TOTAL":<35} {"":>15} {total_input:>8} {"":>8} {total_t1:>8} {total_removed:>8}' )

    print( '' )
    print( f'Species processed: {len( all_summaries )}' )

    if len( failed_species ) > 0:
        print( '' )
        print( 'FAILED species:' )
        for genus_species in failed_species:
            print( f'  - {genus_species}' )
        sys.exit( 1 )

    # =========================================================================
    # genomesDB STEP_1 Reformat
    # =========================================================================
    print( '' )
    print( '============================================' )
    print( 'genomesDB STEP_1 Reformat' )
    print( '============================================' )
    print( '' )
    print( f'genomesDB output: {genomesdb_directory}' )
    print( f'Download date:    {download_date}' )
    print( '' )

    genomesdb_t1_directory = genomesdb_directory / 'T1_proteomes'
    genomesdb_genome_directory = genomesdb_directory / 'genomes'
    genomesdb_annotation_directory = genomesdb_directory / 'gene_annotations'
    genomesdb_maps_directory = genomesdb_directory / 'maps'

    genomesdb_t1_directory.mkdir( parents = True, exist_ok = True )
    genomesdb_genome_directory.mkdir( parents = True, exist_ok = True )
    genomesdb_annotation_directory.mkdir( parents = True, exist_ok = True )
    genomesdb_maps_directory.mkdir( parents = True, exist_ok = True )

    # Find all T1 proteomes in 2-output/
    genomesdb_results = []
    genomesdb_skipped = []

    for species_directory in sorted( output_directory.iterdir() ):
        if not species_directory.is_dir():
            continue

        genus_species = species_directory.name

        # Skip excluded species
        if genus_species in EXCLUDED_FROM_GENOMESDB:
            genomesdb_skipped.append( ( genus_species, 'excluded (overlap or removed)' ) )
            continue

        # Skip species without source identifier mapping
        if genus_species not in SPECIES___SOURCE_IDENTIFIERS:
            genomesdb_skipped.append( ( genus_species, 'no source identifier mapping' ) )
            continue

        # Check for protein_T1.faa
        protein_t1_path = species_directory / 'protein_T1.faa'
        if not protein_t1_path.exists() or protein_t1_path.stat().st_size == 0:
            genomesdb_skipped.append( ( genus_species, 'no protein_T1.faa' ) )
            continue

        source_identifier = SPECIES___SOURCE_IDENTIFIERS[ genus_species ]
        new_basename = f'{genus_species}-genome-{source_identifier}-{download_date}'

        logger.info( f'  Reformatting: {genus_species} -> {new_basename}' )

        # Step 1: Reformat T1 proteome headers
        output_proteome_path = genomesdb_t1_directory / f'{new_basename}.aa'
        sequence_entries = reformat_t1_for_genomesdb(
            protein_t1_path, genus_species, output_proteome_path
        )
        logger.info( f'    T1 proteome: {len( sequence_entries )} proteins' )

        # Count dash changes
        changed_gene_count = sum(
            1 for entry in sequence_entries
            if entry[ 'original_gene_identifier' ] != entry[ 'updated_gene_identifier' ]
        )
        changed_transcript_count = sum(
            1 for entry in sequence_entries
            if entry[ 'original_transcript_identifier' ] != entry[ 'updated_transcript_identifier' ]
        )
        if changed_gene_count > 0 or changed_transcript_count > 0:
            logger.info( f'    Dash changes: {changed_gene_count} gene, {changed_transcript_count} transcript' )

        # Step 2: Copy genome FASTA (if available)
        genome_path = input_directory / genus_species / 'genome.fasta'
        genome_identifiers = []
        if genome_path.exists() and genome_path.stat().st_size > 0:
            output_genome_path = genomesdb_genome_directory / f'{new_basename}.fasta'
            shutil.copy2( genome_path, output_genome_path )
            genome_identifiers = parse_genome_fasta_identifiers( genome_path )
            logger.info( f'    Genome: {len( genome_identifiers )} scaffolds' )
        else:
            logger.info( f'    Genome: not available' )

        # Step 3: Copy GFF3 (if available)
        annotation_path = input_directory / genus_species / 'annotation.gff3'
        if annotation_path.exists() and annotation_path.stat().st_size > 0:
            output_annotation_path = genomesdb_annotation_directory / f'{new_basename}.gff3'
            shutil.copy2( annotation_path, output_annotation_path )
            logger.info( f'    GFF3: copied' )
        else:
            logger.info( f'    GFF3: not available' )

        genomesdb_results.append( {
            'genus_species': genus_species,
            'source_identifier': source_identifier,
            'sequence_entries': sequence_entries,
            'genome_identifiers': genome_identifiers,
            'protein_count': len( sequence_entries ),
            'changed_gene_count': changed_gene_count,
            'changed_transcript_count': changed_transcript_count,
            'has_genome': len( genome_identifiers ) > 0,
            'has_annotation': annotation_path.exists() and annotation_path.stat().st_size > 0,
        } )

    # Write mapping files
    print( '' )
    logger.info( 'Writing identifier mapping files...' )

    genome_map_path = genomesdb_maps_directory / 'repository_genomes-map-genome_identifiers.tsv'
    genome_map_count = write_genome_identifier_map( genomesdb_results, genome_map_path )

    sequence_map_path = genomesdb_maps_directory / 'repository_genomes-map-sequence_identifiers.tsv'
    sequence_map_count = write_sequence_identifier_map( genomesdb_results, sequence_map_path )

    # genomesDB summary
    print( '' )
    print( '============================================' )
    print( 'genomesDB reformat complete' )
    print( '============================================' )
    print( '' )

    print( f'{"Species":<35} {"Proteins":>10} {"Gene Chg":>10} {"Tx Chg":>8} {"Genome":>8} {"GFF3":>6}' )
    print( '-' * 82 )

    for result in genomesdb_results:
        print(
            f'{result[ "genus_species" ]:<35} '
            f'{result[ "protein_count" ]:>10} '
            f'{result[ "changed_gene_count" ]:>10} '
            f'{result[ "changed_transcript_count" ]:>8} '
            f'{"yes" if result[ "has_genome" ] else "no":>8} '
            f'{"yes" if result[ "has_annotation" ] else "no":>6}'
        )

    print( '-' * 82 )
    total_proteins = sum( r[ 'protein_count' ] for r in genomesdb_results )
    total_gene_chg = sum( r[ 'changed_gene_count' ] for r in genomesdb_results )
    total_tx_chg = sum( r[ 'changed_transcript_count' ] for r in genomesdb_results )
    print(
        f'{"TOTAL (" + str( len( genomesdb_results ) ) + " species)":<35} '
        f'{total_proteins:>10} '
        f'{total_gene_chg:>10} '
        f'{total_tx_chg:>8}'
    )
    print( '' )

    if len( genomesdb_skipped ) > 0:
        print( f'Skipped from genomesDB ({len( genomesdb_skipped )}):' )
        for genus_species, reason in genomesdb_skipped:
            print( f'  - {genus_species}: {reason}' )
        print( '' )

    print( f'Genome map:   {genome_map_count} entries' )
    print( f'Sequence map: {sequence_map_count} entries' )
    print( '' )
    print( 'Done!' )


if __name__ == '__main__':
    main()
