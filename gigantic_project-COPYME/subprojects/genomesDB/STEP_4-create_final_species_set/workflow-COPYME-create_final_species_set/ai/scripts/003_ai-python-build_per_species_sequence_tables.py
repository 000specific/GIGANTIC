#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 June 27 | Purpose: Build per-species (GIGANTIC ID, sequence) TSV tables from T1 proteome FASTAs
# Human: Eric Edsinger

"""
GIGANTIC genomesDB STEP_4 — Script 003:
Build per-species sequence tables (TSV) from T1 proteome FASTAs.

For each '<phyloname>-T1-proteome.aa' file in the input proteomes directory,
emits a companion TSV with 4 columns:
    Phyloname | Gigantic_Protein_Identifier | Sequence_Length | Protein_Sequence

Self-documenting headers, tabs between columns. Sequences are single-letter
amino acid codes with no internal whitespace, so no within-column delimiter
is needed.

Also emits:
    3_ai-summary.tsv                                 — per-species protein count
    3_ai-log-build_per_species_sequence_tables.log   — main log file

Usage:
    python3 003_ai-python-build_per_species_sequence_tables.py \\
        --proteomes-dir PATH_TO_species70_gigantic_T1_proteomes \\
        --output-dir    OUTPUT_pipeline/3-output
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Build per-species GIGANTIC sequence tables from T1 proteome FASTAs'
    )
    parser.add_argument(
        '--proteomes-dir',
        required = True,
        help = 'Directory containing <phyloname>-T1-proteome.aa files'
    )
    parser.add_argument(
        '--output-dir',
        required = True,
        help = 'Output directory (e.g., OUTPUT_pipeline/3-output)'
    )
    parser.add_argument(
        '--proteome-file-suffix',
        default = '-T1-proteome.aa',
        help = 'Suffix of input proteome FASTA filenames (default: -T1-proteome.aa)'
    )
    parser.add_argument(
        '--output-file-suffix',
        default = '-T1-proteome-sequence_table.tsv',
        help = 'Suffix for output TSV filenames (default: -T1-proteome-sequence_table.tsv)'
    )
    return parser.parse_args()


def setup_logging( output_dir: Path ) -> logging.Logger:
    output_dir.mkdir( parents = True, exist_ok = True )
    log_path = output_dir / '3_ai-log-build_per_species_sequence_tables.log'
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s - %(levelname)s - %(message)s',
        handlers = [
            logging.FileHandler( log_path, mode = 'w' ),
            logging.StreamHandler( sys.stdout ),
        ],
    )
    return logging.getLogger( __name__ )


def extract_phyloname_from_filename( fasta_filename: str, proteome_file_suffix: str ) -> str:
    """Filenames look like '<phyloname>-T1-proteome.aa'. Strip the suffix."""
    if not fasta_filename.endswith( proteome_file_suffix ):
        return ''
    return fasta_filename[ :-len( proteome_file_suffix ) ]


def parse_fasta( input_fasta_path: Path ):
    """
    Yield ( identifier, sequence ) pairs from a FASTA file.

    Concatenates multi-line sequences into a single string. The identifier
    is the first whitespace-delimited token after the '>'.
    """
    # >g_Patl_g1-t_Patl_g1.t1-p_Patl_g1.t1-n_HolomycotaUNOFFICIAL_..._Parvularia_atlantis
    # MPVVRRGQPAVVWFNVLRPVPVVCPRHVQLGHQRQWPLRLQQRLVRRDLCF
    identifier = None
    sequence_lines = []
    with open( input_fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.rstrip( '\n' )
            if not line:
                continue
            if line.startswith( '>' ):
                if identifier is not None:
                    yield identifier, ''.join( sequence_lines )
                parts_header = line[ 1: ].split()
                identifier = parts_header[ 0 ] if parts_header else ''
                sequence_lines = []
            else:
                sequence_lines.append( line.strip() )
        if identifier is not None:
            yield identifier, ''.join( sequence_lines )


def build_per_species_tsv(
    input_fasta_path: Path,
    phyloname: str,
    output_tsv_path: Path,
    logger: logging.Logger,
) -> int:
    """Write a per-species TSV. Returns the protein count."""
    header = (
        'Phyloname (GIGANTIC phyloname for the species)' + '\t' +
        'Gigantic_Protein_Identifier (FASTA header word 1)' + '\t' +
        'Sequence_Length (residue count of the protein sequence)' + '\t' +
        'Protein_Sequence (amino acid sequence, single-letter codes, no whitespace)' + '\n'
    )
    protein_count = 0
    with open( output_tsv_path, 'w' ) as output_tsv:
        output_tsv.write( header )
        for identifier, sequence in parse_fasta( input_fasta_path ):
            if not identifier:
                logger.warning(
                    f'Skipping FASTA record with empty identifier in {input_fasta_path.name}'
                )
                continue
            output = (
                phyloname + '\t' +
                identifier + '\t' +
                str( len( sequence ) ) + '\t' +
                sequence + '\n'
            )
            output_tsv.write( output )
            protein_count += 1
    return protein_count


def write_summary_tsv( phylonames___protein_counts: dict, output_summary_path: Path ):
    header = (
        'Phyloname (GIGANTIC phyloname for the species)' + '\t' +
        'Protein_Count (number of proteins in the per-species sequence table TSV)' + '\n'
    )
    with open( output_summary_path, 'w' ) as output_summary:
        output_summary.write( header )
        for phyloname in sorted( phylonames___protein_counts.keys() ):
            protein_count = phylonames___protein_counts[ phyloname ]
            output = phyloname + '\t' + str( protein_count ) + '\n'
            output_summary.write( output )


def main():
    args = parse_arguments()

    input_proteomes_dir = Path( args.proteomes_dir ).resolve()
    output_dir = Path( args.output_dir ).resolve()

    logger = setup_logging( output_dir )

    logger.info( 'GIGANTIC genomesDB STEP_4 — Script 003: build per-species sequence tables' )
    logger.info( f'Started: {datetime.now().isoformat()}' )
    logger.info( f'Proteomes dir: {input_proteomes_dir}' )
    logger.info( f'Output dir: {output_dir}' )
    logger.info( f'Proteome file suffix: {args.proteome_file_suffix}' )
    logger.info( f'Output file suffix: {args.output_file_suffix}' )

    if not input_proteomes_dir.is_dir():
        logger.error( f'CRITICAL ERROR: Proteomes directory not found: {input_proteomes_dir}' )
        logger.error(
            'Expected the STEP_4 copy_selected_files process to have populated '
            'this directory.'
        )
        logger.error( 'Verify the earlier pipeline step completed successfully.' )
        sys.exit( 1 )

    fasta_paths = sorted( input_proteomes_dir.glob( f'*{args.proteome_file_suffix}' ) )

    if not fasta_paths:
        logger.error(
            f'CRITICAL ERROR: No FASTA files matching *{args.proteome_file_suffix} '
            f'found in {input_proteomes_dir}'
        )
        logger.error( 'Check --proteome-file-suffix matches the actual filename pattern.' )
        sys.exit( 1 )

    logger.info( f'Found {len( fasta_paths )} per-species FASTA files' )

    phylonames___protein_counts = {}
    for input_fasta_path in fasta_paths:
        phyloname = extract_phyloname_from_filename(
            input_fasta_path.name, args.proteome_file_suffix
        )
        if not phyloname:
            logger.error(
                f'CRITICAL ERROR: Could not extract phyloname from filename: '
                f'{input_fasta_path.name}'
            )
            logger.error( f'Expected suffix: {args.proteome_file_suffix}' )
            sys.exit( 1 )

        output_tsv_filename = phyloname + args.output_file_suffix
        output_tsv_path = output_dir / output_tsv_filename

        protein_count = build_per_species_tsv(
            input_fasta_path, phyloname, output_tsv_path, logger
        )
        phylonames___protein_counts[ phyloname ] = protein_count
        logger.info( f'{phyloname}: {protein_count} proteins -> {output_tsv_filename}' )

    species_with_zero_proteins = [
        phyloname for phyloname, count in phylonames___protein_counts.items() if count == 0
    ]
    if species_with_zero_proteins:
        logger.error(
            f'CRITICAL ERROR: {len( species_with_zero_proteins )} species produced '
            'zero-protein TSVs:'
        )
        for phyloname in species_with_zero_proteins:
            logger.error( f'  - {phyloname}' )
        logger.error( 'Likely cause: source FASTA empty or malformed.' )
        sys.exit( 1 )

    output_summary_path = output_dir / '3_ai-summary.tsv'
    write_summary_tsv( phylonames___protein_counts, output_summary_path )
    logger.info( f'Wrote summary: {output_summary_path}' )

    total_proteins = sum( phylonames___protein_counts.values() )
    logger.info(
        f'Done. {len( phylonames___protein_counts )} species, '
        f'{total_proteins:,} total proteins.'
    )
    logger.info( f'Completed: {datetime.now().isoformat()}' )


if __name__ == '__main__':
    main()
