#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Chunk processable proteomes into per-task query files for SLURM array fan-out
# Human: Eric Edsinger

"""
GIGANTIC hotspots BLOCK_self_blast - Script 002: Chunk Proteomes

Purpose:
    Splits each processable proteome into fixed-size query chunks (FASTA
    files containing N sequences each). Each chunk becomes one SLURM array
    task in the run_blastp_chunk fan-out.

    Also emits a chunk manifest TSV that drives the fan-out channel in
    main.nf (one row per chunk, carrying the species, query chunk path,
    BLAST DB stem, and expected output filename).

Inputs (CLI):
    --processable-manifest   Path to 1_ai-processable_species_manifest.tsv
                             from script 001
    --blast-db-dir           Directory containing pre-built blastp DBs
                             (passed through into the chunk manifest)
    --sequences-per-chunk    Sequences per chunk (default 600)
    --output-dir             Output directory (typically 2-output)

Outputs (in --output-dir):
    2_ai-chunk_manifest.tsv
        Per-row: Genus_Species, Chunk_Index, Chunk_Path, Blast_Db_Path,
                 Expected_Report_Filename
        One row per chunk; drives the fan-out channel.

    chunks/<Genus_species>/<Genus_species>_chunk_<NNNN>.aa
        FASTA chunk files (NNNN is zero-padded chunk index, 0-based).

    2_ai-chunking_summary.tsv
        Per-row: Genus_Species, Sequence_Count, Chunk_Count
        Per-species summary.

    2_ai-log-chunk_proteomes.log

Failure mode:
    Exits 1 (fail-fast) when:
      - Required CLI argument missing
      - Processable manifest is empty
      - Any proteome file is missing or unreadable
      - Any proteome contains zero sequences
      - --sequences-per-chunk is not a positive integer
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( 'chunk_proteomes' )
    logger.setLevel( logging.INFO )

    log_file = output_dir / '2_ai-log-chunk_proteomes.log'
    file_handler = logging.FileHandler( log_file, mode = 'w' )
    file_handler.setLevel( logging.INFO )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


def read_processable_manifest( manifest_path: Path, logger: logging.Logger ) -> list:
    """Read processable species manifest from script 001.

    Returns: list of ( genus_species, phyloname, proteome_path, blast_db_stem )
    """
    processable_records = []

    # Genus_Species (...)\tPhyloname (...)\tProteome_Path (...)\tBlast_Db_Stem (...)
    # Homo_sapiens\tMetazoa_Chordata_..._Homo_sapiens\t/abs/path/...aa\t..._Homo_sapiens-T1-proteome.aa
    with open( manifest_path, 'r' ) as input_manifest:
        header_seen = False
        for line in input_manifest:
            line = line.strip()
            if not line:
                continue
            if not header_seen:
                header_seen = True
                continue
            parts = line.split( '\t' )
            if len( parts ) < 4:
                logger.warning( f'  Skipping malformed manifest row: {line}' )
                continue
            genus_species = parts[ 0 ]
            phyloname = parts[ 1 ]
            proteome_path = Path( parts[ 2 ] )
            blast_db_stem = parts[ 3 ]
            processable_records.append( ( genus_species, phyloname, proteome_path, blast_db_stem ) )

    logger.info( f'  Read {len( processable_records )} processable species records' )
    return processable_records


def iterate_fasta_records( fasta_path: Path ):
    """Yield ( header, sequence ) tuples from a FASTA file.

    Streams the file (no full load) so memory stays low even for huge
    proteomes. Sequences are concatenated across wrapped lines exactly as
    they appear (preserving original case and any non-ACGT characters).
    """
    header = None
    sequence_lines = []
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.rstrip( '\n' )
            if line.startswith( '>' ):
                if header is not None:
                    yield header, ''.join( sequence_lines )
                header = line
                sequence_lines = []
            else:
                sequence_lines.append( line )
    if header is not None:
        yield header, ''.join( sequence_lines )


def chunk_one_proteome(
    genus_species: str,
    proteome_path: Path,
    sequences_per_chunk: int,
    chunks_root: Path,
    logger: logging.Logger,
) -> tuple:
    """Split one proteome into FASTA chunks.

    Returns: ( total_sequence_count, list_of_chunk_paths )
    """
    species_chunk_dir = chunks_root / genus_species
    species_chunk_dir.mkdir( parents = True, exist_ok = True )

    chunk_paths = []
    sequence_count = 0
    chunk_index = 0
    current_chunk_records = []

    def flush_chunk( index: int, records: list ) -> Path:
        chunk_path = species_chunk_dir / f'{genus_species}_chunk_{index:04d}.aa'
        output = ''
        for record_header, record_sequence in records:
            output += record_header + '\n' + record_sequence + '\n'
        with open( chunk_path, 'w' ) as output_chunk:
            output_chunk.write( output )
        return chunk_path

    for header, sequence in iterate_fasta_records( proteome_path ):
        sequence_count += 1
        current_chunk_records.append( ( header, sequence ) )
        if len( current_chunk_records ) >= sequences_per_chunk:
            chunk_paths.append( flush_chunk( chunk_index, current_chunk_records ) )
            chunk_index += 1
            current_chunk_records = []

    if current_chunk_records:
        chunk_paths.append( flush_chunk( chunk_index, current_chunk_records ) )

    return sequence_count, chunk_paths


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--processable-manifest', required = True, type = Path )
    parser.add_argument( '--blast-db-dir', required = True, type = Path )
    parser.add_argument( '--sequences-per-chunk', type = int, default = 600 )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir )

    logger.info( '=' * 72 )
    logger.info( 'GIGANTIC hotspots BLOCK_self_blast - Script 002: Chunk Proteomes' )
    logger.info( '=' * 72 )
    logger.info( f'Processable manifest:   {args.processable_manifest}' )
    logger.info( f'BLAST DB dir:           {args.blast_db_dir}' )
    logger.info( f'Sequences per chunk:    {args.sequences_per_chunk}' )
    logger.info( f'Output dir:             {args.output_dir}' )
    logger.info( '' )

    # ---- Validate args ----
    if args.sequences_per_chunk <= 0:
        logger.error( f'CRITICAL ERROR: --sequences-per-chunk must be positive (got {args.sequences_per_chunk}).' )
        return 1
    if not args.processable_manifest.is_file():
        logger.error( f'CRITICAL ERROR: Processable manifest not found: {args.processable_manifest}' )
        return 1
    if not args.blast_db_dir.is_dir():
        logger.error( f'CRITICAL ERROR: BLAST DB directory not found: {args.blast_db_dir}' )
        return 1

    processable_records = read_processable_manifest( args.processable_manifest, logger )
    if not processable_records:
        logger.error( 'CRITICAL ERROR: Processable manifest contains no species rows. Nothing to chunk.' )
        return 1

    chunks_root = args.output_dir / 'chunks'
    chunks_root.mkdir( parents = True, exist_ok = True )

    chunk_manifest_rows = []      # ( genus_species, chunk_index, chunk_path, blast_db_path, report_filename )
    chunking_summary_rows = []    # ( genus_species, sequence_count, chunk_count )

    blast_db_dir_resolved = args.blast_db_dir.resolve()
    total_chunks = 0

    logger.info( 'Chunking proteomes...' )
    for genus_species, phyloname, proteome_path, blast_db_stem in processable_records:
        if not proteome_path.is_file():
            logger.error( f'CRITICAL ERROR: Proteome file missing for {genus_species}: {proteome_path}' )
            logger.error( 'This indicates a stale processable manifest; rerun script 001.' )
            return 1

        sequence_count, chunk_paths = chunk_one_proteome(
            genus_species,
            proteome_path,
            args.sequences_per_chunk,
            chunks_root,
            logger,
        )

        if sequence_count == 0:
            logger.error( f'CRITICAL ERROR: Proteome for {genus_species} contains zero sequences: {proteome_path}' )
            logger.error( 'Empty proteomes cannot be self-BLASTed; investigate the source file.' )
            return 1

        blast_db_path = blast_db_dir_resolved / blast_db_stem
        chunking_summary_rows.append( ( genus_species, sequence_count, len( chunk_paths ) ) )

        for chunk_index, chunk_path in enumerate( chunk_paths ):
            report_filename = f'self_blast-{genus_species}_chunk_{chunk_index:04d}.tsv'
            chunk_manifest_rows.append( (
                genus_species,
                chunk_index,
                chunk_path.resolve(),
                blast_db_path,
                report_filename,
            ) )

        total_chunks += len( chunk_paths )
        logger.info( f'  {genus_species}: {sequence_count} sequences -> {len( chunk_paths )} chunks' )

    logger.info( '' )
    logger.info( f'Total chunks: {total_chunks} across {len( processable_records )} species' )
    logger.info( '' )

    # ---- Write chunk manifest (drives fan-out in main.nf) ----
    chunk_manifest_path = args.output_dir / '2_ai-chunk_manifest.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Chunk_Index (zero-based chunk index within the species)\t'
    output += 'Chunk_Path (absolute path to the FASTA chunk used as blastp query)\t'
    output += 'Blast_Db_Path (absolute path stem of the pre-built blastp database for this species)\t'
    output += 'Expected_Report_Filename (basename of the per-chunk blastp report this task should produce)\n'
    for genus_species, chunk_index, chunk_path, blast_db_path, report_filename in chunk_manifest_rows:
        output += genus_species + '\t' + str( chunk_index ) + '\t' + str( chunk_path ) + '\t' + str( blast_db_path ) + '\t' + report_filename + '\n'
    with open( chunk_manifest_path, 'w' ) as output_chunk_manifest:
        output_chunk_manifest.write( output )
    logger.info( f'  Wrote {chunk_manifest_path.name} ({len( chunk_manifest_rows )} rows)' )

    # ---- Write per-species chunking summary ----
    chunking_summary_path = args.output_dir / '2_ai-chunking_summary.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Sequence_Count (total proteins in the proteome)\t'
    output += 'Chunk_Count (number of chunks produced for this species)\n'
    for genus_species, sequence_count, chunk_count in chunking_summary_rows:
        output += genus_species + '\t' + str( sequence_count ) + '\t' + str( chunk_count ) + '\n'
    with open( chunking_summary_path, 'w' ) as output_chunking_summary:
        output_chunking_summary.write( output )
    logger.info( f'  Wrote {chunking_summary_path.name} ({len( chunking_summary_rows )} rows)' )

    logger.info( '' )
    logger.info( 'Chunking complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
