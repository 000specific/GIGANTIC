#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Per-species QC analysis of orthogroup results
# Human: Eric Edsinger

"""
006_ai-python-qc_analysis_per_species.py

Performs quality control analysis of orthogroup results at the species level.
Identifies sequences not assigned to orthogroups and provides per-species statistics.
Reads standardized output from script 004.

Input:
    --proteome-list: Path to 1_ai-proteome_list.tsv from script 001
    --orthogroups-file: Path to 4_ai-orthogroups_gigantic_ids.tsv from script 004

Output:
    OUTPUT_pipeline/6-output/6_ai-per_species_summary.tsv
        Per-species orthogroup statistics

Usage:
    python3 006_ai-python-qc_analysis_per_species.py \\
        --proteome-list OUTPUT_pipeline/1-output/1_ai-proteome_list.tsv \\
        --orthogroups-file OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '006_qc_analysis' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '6_ai-log-qc_analysis_per_species.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def extract_genus_species_from_gigantic_header( header: str ) -> str:
    """
    Extract Genus_species from a full GIGANTIC protein header.

    GIGANTIC headers contain the phyloname which includes Kingdom_Phylum_Class_Order_Family_Genus_species.
    The header format varies but the phyloname portion contains the taxonomic hierarchy.

    This function extracts the species name by parsing the phyloname component.
    """

    # GIGANTIC headers may have format like:
    # g_GENEID-t_TRANSID-p_PROTID-n_Kingdom_Phylum_Class_Order_Family_Genus_species
    # or just the phyloname portion

    # Try to find phyloname by looking for -n_ prefix
    if '-n_' in header:
        parts_header = header.split( '-n_' )
        phyloname = parts_header[ -1 ]
    else:
        # Assume the header IS the phyloname or contains it
        phyloname = header

    # Split phyloname on underscore
    parts_phyloname = phyloname.split( '_' )

    # Genus is at index 5, species is everything from index 6 onward
    if len( parts_phyloname ) >= 7:
        genus = parts_phyloname[ 5 ]
        species = '_'.join( parts_phyloname[ 6: ] )
        genus_species = genus + '_' + species
    elif len( parts_phyloname ) >= 2:
        # Fallback: use last two parts
        genus_species = '_'.join( parts_phyloname[ -2: ] )
    else:
        genus_species = phyloname

    return genus_species


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Per-species QC analysis of orthogroup results'
    )

    parser.add_argument(
        '--proteome-list',
        type = str,
        required = True,
        help = 'Path to 1_ai-proteome_list.tsv from script 001'
    )

    parser.add_argument(
        '--orthogroups-file',
        type = str,
        required = True,
        help = 'Path to 4_ai-orthogroups_gigantic_ids.tsv from script 004'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/6-output',
        help = 'Output directory (default: OUTPUT_pipeline/6-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    proteome_list_path = Path( arguments.proteome_list )
    orthogroups_path = Path( arguments.orthogroups_file )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 006: Per-Species QC Analysis" )
    logger.info( "=" * 70 )

    # Validate inputs
    if not proteome_list_path.exists():
        logger.error( f"CRITICAL ERROR: Proteome list not found: {proteome_list_path}" )
        sys.exit( 1 )

    if not orthogroups_path.exists():
        logger.error( f"CRITICAL ERROR: Orthogroups file not found: {orthogroups_path}" )
        sys.exit( 1 )

    # Read proteome list for species information
    # Proteome_Filename (proteome file name)	Full_Path (absolute path to proteome file)	Genus_Species (extracted from phyloname)	Sequence_Count (number of protein sequences in file)
    # filename.aa	/path/to/file.aa	Homo_sapiens	20000

    species___sequence_counts = {}

    with open( proteome_list_path, 'r' ) as input_proteome_list:
        header_line = input_proteome_list.readline()

        for line in input_proteome_list:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            genus_species = parts[ 2 ]
            sequence_count = int( parts[ 3 ] )

            species___sequence_counts[ genus_species ] = sequence_count

    logger.info( f"Loaded {len( species___sequence_counts )} species from proteome list" )

    # Parse standardized orthogroups file to count genes per species
    # Format: OG_ID\tgene1\tgene2\tgene3...

    species___genes_in_orthogroups = defaultdict( int )
    species___orthogroup_counts = defaultdict( int )

    # OG0000001	gene_header_1	gene_header_2	gene_header_3
    # OG0000002	gene_header_4	gene_header_5

    with open( orthogroups_path, 'r' ) as input_orthogroups:
        for line in input_orthogroups:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            genes = parts[ 1: ]

            # Track species presence in this orthogroup
            species_in_this_orthogroup = set()

            for gene in genes:
                if not gene:
                    continue

                genus_species = extract_genus_species_from_gigantic_header( gene )
                species_in_this_orthogroup.add( genus_species )
                species___genes_in_orthogroups[ genus_species ] += 1

            # Count orthogroups per species
            for genus_species in species_in_this_orthogroup:
                species___orthogroup_counts[ genus_species ] += 1

    logger.info( f"Found genes from {len( species___genes_in_orthogroups )} species in orthogroups" )

    # Write per-species summary
    summary_file = output_directory / '6_ai-per_species_summary.tsv'

    with open( summary_file, 'w' ) as output_summary:
        # Write header
        header = 'Genus_Species (species name)' + '\t'
        header += 'Total_Sequences (total protein sequences for species)' + '\t'
        header += 'Sequences_In_Orthogroups (sequences assigned to orthogroups)' + '\t'
        header += 'Sequences_Without_Orthogroup (sequences not in any orthogroup)' + '\t'
        header += 'Coverage_Percent (percent of sequences in orthogroups)' + '\t'
        header += 'Orthogroups_With_Species (orthogroups containing this species)' + '\n'
        output_summary.write( header )

        for genus_species in sorted( species___sequence_counts.keys() ):
            total_sequences = species___sequence_counts[ genus_species ]
            sequences_in_orthogroups = species___genes_in_orthogroups.get( genus_species, 0 )
            sequences_without_orthogroup = total_sequences - sequences_in_orthogroups
            coverage_percent = ( sequences_in_orthogroups / total_sequences * 100 ) if total_sequences > 0 else 0.0
            orthogroup_count = species___orthogroup_counts.get( genus_species, 0 )

            output = genus_species + '\t'
            output += str( total_sequences ) + '\t'
            output += str( sequences_in_orthogroups ) + '\t'
            output += str( sequences_without_orthogroup ) + '\t'
            output += f"{coverage_percent:.2f}" + '\t'
            output += str( orthogroup_count ) + '\n'
            output_summary.write( output )

    logger.info( f"Wrote per-species summary to: {summary_file}" )
    logger.info( "Script 006 completed successfully" )


if __name__ == '__main__':
    main()
