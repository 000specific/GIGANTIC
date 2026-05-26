#!/usr/bin/env python3
# GIGANTIC trees_gene_groups STEP_1 - Script 007: List model-organism FASTAs
# AI: Claude Code | Opus 4.7 | 2026 May 26 | Purpose: List RBH species proteome FASTA paths for downstream script 008
# Human: Eric Edsinger

"""
List Model-Organism Proteome FASTAs for the RBH species set.

Simplified 2026-05-26: the prior version also catalogued RGS-vs-genome
BLAST reports (`6_ai*genome*.blastp`) for consumption by Improvement 2
in script 008. That BLAST fallback and its upstream BLAST work were
removed as dead code for gene_groups_hgnc (Improvement 0 gene-symbol
search + Improvement 1 NCBI accession match cover all valid RGS shapes).
This script now does ONE thing: emit the list of per-species proteome
FASTA paths that script 008's genome indexer will consume.

Output:
    7-output/7_ai-list-model-organism-fastas.txt
        One absolute path per line, one per RBH species.

Usage:
    python3 007_ai-python-list_rgs_blast_files.py \\
        --output-dir 7-output \\
        --blast-databases-dir <path-to-species70_gigantic_T1_blastp> \\
        --rbh-species "human" \\
        --output-model-fastas 7-output/7_ai-list-model-organism-fastas.txt
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger( __name__ )


def find_model_organism_fastas(
    blast_databases_directory: Path,
    model_species: List[ str ],
    logger: logging.Logger,
) -> List[ Path ]:
    """Find per-species proteome FASTAs in the blast-databases dir.

    Each `model_species` short name is mapped to a Genus_species via the
    hardcoded short→Genus_species dict below; the FASTA is found by glob
    against the proteome filename convention.

    STRUCTURAL TODO (flagged 2026-05-24):
    This hardcoded short→Genus_species mapping should be replaced with
    loading INPUT_user/rgs_species_map.tsv at runtime. The same dict
    lives in script 008 — fix both together with a shared --rgs-species-map
    CLI arg.
    """
    logger.info( "Searching for RBH species proteome FASTAs..." )
    logger.info( f"RBH species: {', '.join( model_species )}" )

    species_mappings = {
        'human':     'Homo_sapiens',
        'fly':       'Drosophila_melanogaster',
        'worm':      'Caenorhabditis_elegans',
        'mouse':     'Mus_musculus',
        'zebrafish': 'Danio_rerio',
    }

    model_fastas: List[ Path ] = []
    for species in model_species:
        scientific_name = species_mappings.get( species.lower(), species )
        pattern = f"*{scientific_name}*.aa"
        matching_files = list( blast_databases_directory.glob( pattern ) )

        if matching_files:
            fasta_file = matching_files[ 0 ]
            model_fastas.append( fasta_file )
            logger.info( f"  - {species}: {fasta_file.name}" )
        else:
            logger.warning( f"  - {species}: No matching FASTA found for pattern {pattern}" )

    return model_fastas


def write_file_list( output_file: Path, file_paths: List[ Path ], logger: logging.Logger ) -> None:
    with open( output_file, 'w' ) as output_list:
        for file_path in file_paths:
            output_list.write( f"{file_path}\n" )
    logger.info( f"Wrote {len( file_paths )} paths to {output_file}" )


def main():
    parser = argparse.ArgumentParser(
        description='List per-species proteome FASTA paths for script 008 (BLAST-free).'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='Working/output directory (created if missing).',
    )
    parser.add_argument(
        '--blast-databases-dir',
        type=str,
        required=True,
        help='Directory containing per-species proteome FASTA files (e.g., species70 blastp dir).',
    )
    parser.add_argument(
        '--rbh-species',
        type=str,
        required=True,
        help='Space-separated list of RBH species short names (e.g., "human" or "human fly worm").',
    )
    parser.add_argument(
        '--output-model-fastas',
        type=str,
        default='7-output/7_ai-list-model-organism-fastas.txt',
        help='Output file for the list of model-organism proteome FASTA paths.',
    )
    arguments = parser.parse_args()
    logger = setup_logging()

    logger.info( "=" * 80 )
    logger.info( "List Model-Organism Proteome FASTAs (BLAST-free)" )
    logger.info( "=" * 80 )
    logger.info( f"Script started at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )

    output_directory = Path( arguments.output_dir )
    blast_databases_directory = Path( arguments.blast_databases_dir )
    output_model_fastas_file = Path( arguments.output_model_fastas )

    script_output_dir = output_model_fastas_file.parent
    script_output_dir.mkdir( parents=True, exist_ok=True )

    if not output_directory.exists():
        logger.error( f"Output directory not found: {output_directory}" )
        sys.exit( 1 )
    if not blast_databases_directory.exists():
        logger.error( f"BLAST databases directory not found: {blast_databases_directory}" )
        sys.exit( 1 )

    rbh_species_list = arguments.rbh_species.split()

    model_fastas = find_model_organism_fastas(
        blast_databases_directory,
        rbh_species_list,
        logger,
    )

    if not model_fastas:
        logger.error( "CRITICAL ERROR: No model organism FASTAs found!" )
        logger.error( f"Searched: {blast_databases_directory}" )
        logger.error( f"For species: {', '.join( rbh_species_list )}" )
        sys.exit( 1 )

    logger.info( "" )
    write_file_list( output_model_fastas_file, model_fastas, logger )

    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT COMPLETE" )
    logger.info( "=" * 80 )
    logger.info( f"Model organism FASTAs listed: {len( model_fastas )}" )
    logger.info( f"Output file: {output_model_fastas_file}" )
    logger.info( f"Script completed at: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )


if __name__ == '__main__':
    main()
