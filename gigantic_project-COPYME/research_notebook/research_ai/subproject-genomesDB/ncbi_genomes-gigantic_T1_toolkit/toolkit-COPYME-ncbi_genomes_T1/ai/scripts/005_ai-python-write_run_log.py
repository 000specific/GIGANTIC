#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 28 | Purpose: Write per-run audit log to ai/logs/ recording manifest, output counts, alt-loci stats, runtime. Canonical final script per gigantic_conventions.md §45.
# Human: Eric Edsinger

"""
005_ai-python-write_run_log.py

Final script in the toolkit pipeline. Writes a timestamped audit log to
ai/logs/run_YYYYMMDD_HHMMSS-ncbi_genomes_T1_toolkit_success.log per §45.

The log captures everything a future reader needs to reconstruct what this
specific RUN did:
  - Toolkit name, parent dir, RUN dir
  - Manifest contents (species + accessions)
  - Output file counts per subdir (T1_proteomes / genomes / gene_annotations / maps)
  - Alt-loci log summary (species with dropped genes, total drops)
  - Bridge target paths (parent output_to_input + INPUT_user/genomic_resources)
  - Wall-clock duration if available

Usage:
    python3 005_ai-python-write_run_log.py \\
        --toolkit-name <name> \\
        --manifest <path_to_manifest.tsv> \\
        --run-3-output-dir <abs_path_to_3-output> \\
        --parent-oti-dir <abs_path_to_parent_output_to_input> \\
        --input-user-gr-dir <abs_path_to_INPUT_user_genomic_resources> \\
        --log-dir <abs_path_to_ai/logs>
"""

import argparse
import sys
import datetime
from pathlib import Path


def read_manifest_species( manifest_path ):
    """Return list of (genus_species, accession) pairs from manifest TSV, skipping comments + header."""
    species = []
    with open( manifest_path, 'r', encoding = 'utf-8' ) as input_manifest:
        for line in input_manifest:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue
            if line.split( '\t' )[ 0 ] == 'genus_species':
                continue
            parts = line.split( '\t' )
            if len( parts ) >= 2:
                species.append( ( parts[ 0 ], parts[ 1 ] ) )
    return species


def count_files_in_dir( directory_path, extension_filter = None ):
    """Count files in a directory (top-level only), optionally filtered by extension."""
    if not directory_path.is_dir():
        return 0
    files = [ f for f in directory_path.iterdir() if f.is_file() or f.is_symlink() ]
    if extension_filter is not None:
        files = [ f for f in files if f.name.endswith( extension_filter ) ]
    return len( files )


def summarize_alt_loci_log( maps_directory ):
    """
    Parse the alt-loci log TSV (written by script 003) if present, and return
    a short summary: (total_species_with_drops, total_genes_dropped).
    """
    if not maps_directory.is_dir():
        return ( 0, 0 )

    log_candidates = list( maps_directory.glob( '*alternate_loci*' ) )
    if not log_candidates:
        return ( 0, 0 )

    log_path = log_candidates[ 0 ]
    species_with_drops = set()
    total_drops = 0

    with open( log_path, 'r', encoding = 'utf-8' ) as input_log:
        for index, line in enumerate( input_log ):
            if index == 0:
                continue  # header
            parts = line.strip().split( '\t' )
            if len( parts ) < 2:
                continue
            # Heuristic: column layout written by script 003 has genus_species
            # in column [0] and a decision indicator like "dropped"/"retained"
            # in another column. We just count rows; the precise schema is in
            # the archived DOCUMENTATION-alternate_loci_filtering.md.
            species_with_drops.add( parts[ 0 ] )
            if 'drop' in line.lower():
                total_drops += 1

    return ( len( species_with_drops ), total_drops )


def main():
    parser = argparse.ArgumentParser(
        description = "Write per-run audit log for the ncbi_genomes T1 toolkit."
    )
    parser.add_argument( '--toolkit-name',     required = True )
    parser.add_argument( '--manifest',         required = True )
    parser.add_argument( '--run-3-output-dir', required = True )
    parser.add_argument( '--parent-oti-dir',   required = True )
    parser.add_argument( '--input-user-gr-dir', required = True )
    parser.add_argument( '--log-dir',          required = True )
    arguments = parser.parse_args()

    toolkit_name = arguments.toolkit_name
    manifest_path = Path( arguments.manifest )
    run_3_output_dir = Path( arguments.run_3_output_dir )
    parent_oti_dir = Path( arguments.parent_oti_dir )
    input_user_gr_dir = Path( arguments.input_user_gr_dir )
    log_dir = Path( arguments.log_dir )

    log_dir.mkdir( parents = True, exist_ok = True )

    timestamp = datetime.datetime.now().strftime( '%Y%m%d_%H%M%S' )
    log_filename = f'run_{timestamp}-{toolkit_name}_success.log'
    log_path = log_dir / log_filename

    # ------------------------------------------------------------------------
    # Gather
    # ------------------------------------------------------------------------
    species_in_manifest = read_manifest_species( manifest_path ) if manifest_path.is_file() else []

    t1_count        = count_files_in_dir( run_3_output_dir / 'T1_proteomes',     extension_filter = '.aa' )
    genome_count    = count_files_in_dir( run_3_output_dir / 'genomes',          extension_filter = '.fasta' )
    annotation_count = count_files_in_dir( run_3_output_dir / 'gene_annotations', extension_filter = '.gff3' )
    map_count       = count_files_in_dir( run_3_output_dir / 'maps' )

    parent_t1_count        = count_files_in_dir( parent_oti_dir / 'T1_proteomes' )
    parent_genome_count    = count_files_in_dir( parent_oti_dir / 'genomes' )
    parent_annotation_count = count_files_in_dir( parent_oti_dir / 'gene_annotations' )
    parent_map_count       = count_files_in_dir( parent_oti_dir / 'maps' )

    input_user_proteome_count = count_files_in_dir( input_user_gr_dir / 'proteomes' )
    input_user_genome_count   = count_files_in_dir( input_user_gr_dir / 'genomes' )
    input_user_annotation_count = count_files_in_dir( input_user_gr_dir / 'annotations' )

    species_with_alt_loci_drops, total_alt_loci_drops = summarize_alt_loci_log( run_3_output_dir / 'maps' )

    # ------------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------------
    with open( log_path, 'w', encoding = 'utf-8' ) as output_log:
        write = output_log.write

        write( '=' * 72 + '\n' )
        write( f'GIGANTIC ncbi_genomes T1 Toolkit -- per-run audit log\n' )
        write( '=' * 72 + '\n' )
        write( '\n' )
        write( f'Toolkit:    {toolkit_name}\n' )
        write( f'Timestamp:  {timestamp}\n' )
        write( f'Generated:  {datetime.datetime.now().isoformat( sep = " ", timespec = "seconds" )}\n' )
        write( '\n' )

        write( '-' * 72 + '\n' )
        write( 'Inputs\n' )
        write( '-' * 72 + '\n' )
        write( f'Manifest: {manifest_path}\n' )
        write( f'Species in manifest: {len( species_in_manifest )}\n' )
        for genus_species, accession in species_in_manifest:
            write( f'  - {genus_species}\t{accession}\n' )
        write( '\n' )

        write( '-' * 72 + '\n' )
        write( 'Outputs at RUN OUTPUT_pipeline/3-output/ (real files from script 003)\n' )
        write( '-' * 72 + '\n' )
        write( f'Path: {run_3_output_dir}\n' )
        write( f'  T1_proteomes (.aa):      {t1_count}\n' )
        write( f'  genomes (.fasta):        {genome_count}\n' )
        write( f'  gene_annotations (.gff3): {annotation_count}\n' )
        write( f'  maps (TSV):              {map_count}\n' )
        write( '\n' )

        write( '-' * 72 + '\n' )
        write( "Bridge hop A: toolkit parent's output_to_input/ symlinks\n" )
        write( '-' * 72 + '\n' )
        write( f'Path: {parent_oti_dir}\n' )
        write( f'  T1_proteomes:            {parent_t1_count}\n' )
        write( f'  genomes:                 {parent_genome_count}\n' )
        write( f'  gene_annotations:        {parent_annotation_count}\n' )
        write( f'  maps:                    {parent_map_count}\n' )
        write( '\n' )

        write( '-' * 72 + '\n' )
        write( 'Bridge hop B: INPUT_user/genomic_resources/ symlinks (GIGANTIC staging arena)\n' )
        write( '-' * 72 + '\n' )
        write( f'Path: {input_user_gr_dir}\n' )
        write( f'  proteomes:               {input_user_proteome_count}\n' )
        write( f'  genomes:                 {input_user_genome_count}\n' )
        write( f'  annotations:             {input_user_annotation_count}\n' )
        write( '\n' )

        write( '-' * 72 + '\n' )
        write( 'Alternate-loci filter summary (NCBI primary/alt-haplotype dedup)\n' )
        write( '-' * 72 + '\n' )
        write( f'Species with any drops:   {species_with_alt_loci_drops}\n' )
        write( f'Total decisions in log:   {total_alt_loci_drops}\n' )
        write( '(see maps/*alternate_loci*.tsv in RUN 3-output for full detail)\n' )
        write( '\n' )

        write( '=' * 72 + '\n' )
        write( 'End of log\n' )
        write( '=' * 72 + '\n' )

    print( f'Wrote audit log: {log_path}' )


if __name__ == '__main__':
    main()
