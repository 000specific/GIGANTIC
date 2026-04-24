#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Extract T1 (longest transcript per gene) proteomes from repository genome data using flexible input paths
# Human: Eric Edsinger

"""
003_ai-python-extract_longest_transcript_proteomes.py

Extracts T1 (longest transcript per gene) proteomes from repository genomes.
Handles three input scenarios per species:

  Path A: protein.faa + GFF3 annotation
    - Parse GFF3 for gene->mRNA->CDS->protein_id mapping
    - Filter protein.faa for longest protein per gene

  Path B: protein.faa + GTF annotation
    - Parse GTF for gene_id->transcript_id mapping
    - Match transcript_id to protein headers
    - Filter protein.faa for longest protein per gene

  Path C: genome.fasta + GFF3/GTF annotation (no protein file)
    - Use gffread to extract + translate protein sequences
    - Filter for longest transcript per gene

  Path D: protein.faa only (no annotation)
    - Use all proteins as-is (cannot do T1 filtering)
    - Log a warning

Input:
    2-output/genome/      - Genome FASTA files (optional per species)
    2-output/annotation/  - GFF3 or GTF annotation files (optional per species)
    2-output/protein/     - Protein FASTA files (optional per species)

Output:
    3-output/T1_proteomes/{genus_species}-repository_genomes-T1_proteome.aa

Header format:
    >Genus_species-repository_genomes|protein_or_gene_id|gene_or_transcript_id

Usage:
    python3 003_ai-python-extract_longest_transcript_proteomes.py \
        --input-dir 2-output --output-dir 3-output

Requires (for Path C):
    gffread (module load gffread)
"""

import argparse
import logging
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

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
# Shared FASTA parsing
# ============================================================================

def parse_fasta( fasta_path ):
    """
    Parse a FASTA file into a dictionary of identifier -> sequence.

    Parameters:
        fasta_path (Path): Path to the FASTA file

    Returns:
        dict: identifier -> sequence (no newlines)
        dict: identifier -> full header line (without '>')
    """

    identifiers___sequences = {}
    identifiers___headers = {}
    current_identifier = None
    current_header = None
    current_sequence_parts = []

    # >protein_identifier description text
    # MKLQRSTVFLANNDDD
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()

            if line.startswith( '>' ):
                # Save previous entry
                if current_identifier is not None:
                    identifiers___sequences[ current_identifier ] = ''.join( current_sequence_parts )
                    identifiers___headers[ current_identifier ] = current_header

                current_header = line[ 1: ]
                parts_header = current_header.split()
                current_identifier = parts_header[ 0 ]
                current_sequence_parts = []

            else:
                if len( line ) > 0:
                    current_sequence_parts.append( line )

    # Save last entry
    if current_identifier is not None:
        identifiers___sequences[ current_identifier ] = ''.join( current_sequence_parts )
        identifiers___headers[ current_identifier ] = current_header

    return identifiers___sequences, identifiers___headers


# ============================================================================
# GFF3 parsing (for Path A)
# ============================================================================

def parse_gff3_attributes( attributes_string ):
    """Parse GFF3 attributes column into a dictionary."""

    attributes = {}
    for pair in attributes_string.strip().split( ';' ):
        if '=' in pair:
            key, value = pair.split( '=', 1 )
            attributes[ key ] = value
    return attributes


def build_gene_to_protein_mapping_gff3( gff3_path ):
    """
    Parse a GFF3 file to build gene_id -> [protein_id] mapping.

    Follows hierarchy: gene -> mRNA -> CDS (protein_id attribute)
    Also handles CDS directly under gene (no mRNA intermediate).

    Parameters:
        gff3_path (Path): Path to GFF3 annotation

    Returns:
        dict: gene_id -> list of protein_ids
    """

    messenger_rna_identifiers___gene_identifiers = {}
    protein_identifiers___messenger_rna_identifiers = {}
    protein_identifiers___gene_identifiers_direct = {}

    # scaffold_1	source	gene	100	5000	.	+	.	ID=gene001;Name=...
    # scaffold_1	source	mRNA	100	5000	.	+	.	ID=mrna001;Parent=gene001;...
    # scaffold_1	source	CDS	200	400	.	+	0	ID=cds001;Parent=mrna001;protein_id=prot001
    with open( gff3_path, 'r' ) as input_gff3:
        for line in input_gff3:
            line = line.strip()

            if line.startswith( '#' ) or len( line ) == 0:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 9:
                continue

            feature_type = parts[ 2 ]
            attributes = parse_gff3_attributes( parts[ 8 ] )

            if feature_type == 'mRNA' or feature_type == 'transcript':
                messenger_rna_identifier = attributes.get( 'ID', '' )
                parent_gene_identifier = attributes.get( 'Parent', '' )

                if messenger_rna_identifier and parent_gene_identifier:
                    messenger_rna_identifiers___gene_identifiers[ messenger_rna_identifier ] = parent_gene_identifier

            elif feature_type == 'CDS':
                protein_identifier = attributes.get( 'protein_id', '' )
                parent_identifier = attributes.get( 'Parent', '' )

                if protein_identifier and parent_identifier:
                    if parent_identifier in messenger_rna_identifiers___gene_identifiers:
                        protein_identifiers___messenger_rna_identifiers[ protein_identifier ] = parent_identifier
                    elif parent_identifier.startswith( 'gene' ):
                        protein_identifiers___gene_identifiers_direct[ protein_identifier ] = parent_identifier
                    else:
                        protein_identifiers___messenger_rna_identifiers[ protein_identifier ] = parent_identifier

    # Build gene_id -> [protein_ids]
    gene_identifiers___protein_identifiers = {}

    for protein_identifier, messenger_rna_identifier in protein_identifiers___messenger_rna_identifiers.items():
        gene_identifier = messenger_rna_identifiers___gene_identifiers.get( messenger_rna_identifier, None )

        if gene_identifier is not None:
            if gene_identifier not in gene_identifiers___protein_identifiers:
                gene_identifiers___protein_identifiers[ gene_identifier ] = []
            if protein_identifier not in gene_identifiers___protein_identifiers[ gene_identifier ]:
                gene_identifiers___protein_identifiers[ gene_identifier ].append( protein_identifier )

    for protein_identifier, gene_identifier in protein_identifiers___gene_identifiers_direct.items():
        if gene_identifier not in gene_identifiers___protein_identifiers:
            gene_identifiers___protein_identifiers[ gene_identifier ] = []
        if protein_identifier not in gene_identifiers___protein_identifiers[ gene_identifier ]:
            gene_identifiers___protein_identifiers[ gene_identifier ].append( protein_identifier )

    return gene_identifiers___protein_identifiers


# ============================================================================
# GTF parsing (for Path B and Path C)
# ============================================================================

def parse_gtf_gene_transcript_mapping( gtf_path ):
    """
    Parse a GTF file to extract gene_id -> [transcript_id] mapping.

    Parameters:
        gtf_path (Path): Path to GTF annotation

    Returns:
        dict: gene_id -> sorted list of transcript_ids
    """

    gene_identifiers___transcript_identifiers = defaultdict( set )

    # chr1	source	exon	100	200	.	+	.	gene_id "gene001"; transcript_id "tx001";
    with open( gtf_path, 'r' ) as input_gtf:
        for line in input_gtf:
            line = line.strip()

            if line.startswith( '#' ):
                continue

            gene_id_match = re.search( r'gene_id "([^"]+)"', line )
            transcript_id_match = re.search( r'transcript_id "([^"]+)"', line )

            if gene_id_match and transcript_id_match:
                gene_identifier = gene_id_match.group( 1 )
                transcript_identifier = transcript_id_match.group( 1 )
                gene_identifiers___transcript_identifiers[ gene_identifier ].add( transcript_identifier )

    # Sort transcript lists for reproducibility
    for gene_identifier in gene_identifiers___transcript_identifiers:
        gene_identifiers___transcript_identifiers[ gene_identifier ] = sorted(
            gene_identifiers___transcript_identifiers[ gene_identifier ]
        )

    return gene_identifiers___transcript_identifiers


# ============================================================================
# Path A: protein.faa + GFF3 -> T1 filtering
# ============================================================================

def extract_t1_from_protein_and_gff3( protein_fasta_path, gff3_path, genus_species ):
    """
    Extract T1 proteome using protein FASTA + GFF3 annotation.

    Parameters:
        protein_fasta_path (Path): Pre-computed protein FASTA
        gff3_path (Path): GFF3 annotation
        genus_species (str): Species name

    Returns:
        list: (header, sequence) tuples
        dict: Statistics
    """

    gene_identifiers___protein_identifiers = build_gene_to_protein_mapping_gff3( gff3_path )
    protein_identifiers___sequences, protein_identifiers___headers = parse_fasta( protein_fasta_path )

    t1_proteins = []
    genes_with_single_isoform = 0
    genes_with_multiple_isoforms = 0

    for gene_identifier in sorted( gene_identifiers___protein_identifiers.keys() ):
        protein_identifiers = gene_identifiers___protein_identifiers[ gene_identifier ]

        if len( protein_identifiers ) == 1:
            genes_with_single_isoform += 1
        else:
            genes_with_multiple_isoforms += 1

        # Find longest protein
        longest_protein_identifier = None
        longest_sequence_length = 0

        for protein_identifier in protein_identifiers:
            sequence = protein_identifiers___sequences.get( protein_identifier, None )
            if sequence is not None:
                if len( sequence ) > longest_sequence_length:
                    longest_sequence_length = len( sequence )
                    longest_protein_identifier = protein_identifier

        if longest_protein_identifier is not None:
            sequence = protein_identifiers___sequences[ longest_protein_identifier ]
            clean_gene_identifier = gene_identifier
            if clean_gene_identifier.startswith( 'gene-' ):
                clean_gene_identifier = clean_gene_identifier[ 5: ]

            output_header = f'{genus_species}-repository_genomes|{longest_protein_identifier}|{clean_gene_identifier}'
            t1_proteins.append( ( output_header, sequence ) )

    linked_protein_identifiers = set()
    for protein_identifiers in gene_identifiers___protein_identifiers.values():
        linked_protein_identifiers.update( protein_identifiers )

    orphan_protein_count = len( set( protein_identifiers___sequences.keys() ) - linked_protein_identifiers )

    statistics = {
        'path': 'A (protein + GFF3)',
        'total_genes': len( gene_identifiers___protein_identifiers ),
        'single_isoform_genes': genes_with_single_isoform,
        'multiple_isoform_genes': genes_with_multiple_isoforms,
        'total_proteins_in_fasta': len( protein_identifiers___sequences ),
        't1_proteins_extracted': len( t1_proteins ),
        'orphan_proteins': orphan_protein_count,
    }

    return t1_proteins, statistics


# ============================================================================
# Path B: protein.faa + GTF -> T1 filtering
# ============================================================================

def extract_t1_from_protein_and_gtf( protein_fasta_path, gtf_path, genus_species ):
    """
    Extract T1 proteome using protein FASTA + GTF annotation.

    GTF gives gene_id -> transcript_id mapping. We try to match transcript_ids
    to protein FASTA header identifiers. If direct matching fails, we try
    prefix matching.

    Parameters:
        protein_fasta_path (Path): Pre-computed protein FASTA
        gtf_path (Path): GTF annotation
        genus_species (str): Species name

    Returns:
        list: (header, sequence) tuples
        dict: Statistics
    """

    gene_identifiers___transcript_identifiers = parse_gtf_gene_transcript_mapping( gtf_path )
    protein_identifiers___sequences, protein_identifiers___headers = parse_fasta( protein_fasta_path )

    t1_proteins = []
    genes_with_matches = 0
    genes_without_matches = 0

    for gene_identifier in sorted( gene_identifiers___transcript_identifiers.keys() ):
        transcript_identifiers = gene_identifiers___transcript_identifiers[ gene_identifier ]

        # Try to match transcript IDs to protein IDs
        longest_protein_identifier = None
        longest_sequence_length = 0

        for transcript_identifier in transcript_identifiers:
            # Try exact match first
            sequence = protein_identifiers___sequences.get( transcript_identifier, None )
            protein_key = transcript_identifier

            # If no exact match, try partial matching (some protein files use different IDs)
            if sequence is None:
                for protein_identifier in protein_identifiers___sequences:
                    if transcript_identifier in protein_identifier or protein_identifier in transcript_identifier:
                        sequence = protein_identifiers___sequences[ protein_identifier ]
                        protein_key = protein_identifier
                        break

            if sequence is not None:
                if len( sequence ) > longest_sequence_length:
                    longest_sequence_length = len( sequence )
                    longest_protein_identifier = protein_key

        if longest_protein_identifier is not None:
            sequence = protein_identifiers___sequences[ longest_protein_identifier ]
            output_header = f'{genus_species}-repository_genomes|{longest_protein_identifier}|{gene_identifier}'
            t1_proteins.append( ( output_header, sequence ) )
            genes_with_matches += 1
        else:
            genes_without_matches += 1

    statistics = {
        'path': 'B (protein + GTF)',
        'total_genes': len( gene_identifiers___transcript_identifiers ),
        'genes_with_protein_match': genes_with_matches,
        'genes_without_protein_match': genes_without_matches,
        'total_proteins_in_fasta': len( protein_identifiers___sequences ),
        't1_proteins_extracted': len( t1_proteins ),
    }

    return t1_proteins, statistics


# ============================================================================
# Path C: genome + GFF3/GTF -> gffread -> T1 filtering
# ============================================================================

def filter_annotation_by_genome_bounds( annotation_path, genome_fasta_path, filtered_annotation_path ):
    """
    Filter an annotation file to remove entries beyond scaffold boundaries.

    Parameters:
        annotation_path (Path): GFF3 or GTF file
        genome_fasta_path (Path): Genome FASTA (for scaffold lengths)
        filtered_annotation_path (Path): Output filtered annotation

    Returns:
        tuple: (total_lines, kept_lines, removed_lines)
    """

    # Create FASTA index if needed
    fai_path = Path( str( genome_fasta_path ) + '.fai' )
    if not fai_path.exists():
        logger.info( f'  Creating FASTA index...' )
        subprocess.run(
            [ 'samtools', 'faidx', str( genome_fasta_path ) ],
            capture_output = True, text = True
        )

    # Read scaffold lengths from index
    scaffold_names___lengths = {}
    if fai_path.exists():
        # scaffold_name	length	offset	linebases	linewidth
        # chr_1	16344884	7	60	61
        with open( fai_path, 'r' ) as input_fai:
            for line in input_fai:
                line = line.strip()
                if not line:
                    continue
                parts = line.split( '\t' )
                scaffold_names___lengths[ parts[ 0 ] ] = int( parts[ 1 ] )

    total_line_count = 0
    kept_line_count = 0
    removed_line_count = 0

    with open( annotation_path, 'r' ) as input_annotation, open( filtered_annotation_path, 'w' ) as output_annotation:
        for line in input_annotation:
            total_line_count += 1
            line_stripped = line.strip()

            if line_stripped.startswith( '#' ) or len( line_stripped ) == 0:
                output_annotation.write( line )
                kept_line_count += 1
                continue

            parts = line_stripped.split( '\t' )
            if len( parts ) < 5:
                output_annotation.write( line )
                kept_line_count += 1
                continue

            scaffold_name = parts[ 0 ]
            end_coordinate = int( parts[ 4 ] )

            scaffold_length = scaffold_names___lengths.get( scaffold_name, None )
            if scaffold_length is not None and end_coordinate > scaffold_length:
                removed_line_count += 1
                continue
            elif scaffold_length is None and len( scaffold_names___lengths ) > 0:
                # Scaffold not in genome index
                removed_line_count += 1
                continue

            output_annotation.write( line )
            kept_line_count += 1

    return total_line_count, kept_line_count, removed_line_count


def extract_t1_via_gffread( genome_fasta_path, annotation_path, annotation_format, genus_species, intermediate_directory ):
    """
    Extract T1 proteome using gffread (genome + annotation, no pre-computed protein).

    Parameters:
        genome_fasta_path (Path): Genome FASTA
        annotation_path (Path): GFF3 or GTF annotation
        annotation_format (str): 'gff3' or 'gtf'
        genus_species (str): Species name
        intermediate_directory (Path): For gffread intermediate output

    Returns:
        list: (header, sequence) tuples
        dict: Statistics
    """

    # Validate GTF/GFF3 coordinates against genome
    filtered_annotation_path = intermediate_directory / f'{genus_species}-filtered.{annotation_format}'
    logger.info( f'  Validating annotation coordinates against genome...' )

    total_line_count, kept_line_count, removed_line_count = filter_annotation_by_genome_bounds(
        annotation_path, genome_fasta_path, filtered_annotation_path
    )

    if removed_line_count > 0:
        logger.warning( f'  Removed {removed_line_count} annotation lines with out-of-bounds coordinates' )
        annotation_to_use = filtered_annotation_path
    else:
        logger.info( f'  All annotation coordinates within genome bounds' )
        annotation_to_use = annotation_path

    # Run gffread to extract protein sequences
    gffread_output_path = intermediate_directory / f'{genus_species}-all_transcripts.fa'

    command = [
        'gffread',
        '-y', str( gffread_output_path ),
        '-g', str( genome_fasta_path ),
        str( annotation_to_use )
    ]

    logger.info( f'  Running gffread: {" ".join( command )}' )
    result = subprocess.run( command, capture_output = True, text = True )

    # Clean up filtered annotation
    if filtered_annotation_path.exists() and filtered_annotation_path != annotation_path:
        filtered_annotation_path.unlink()

    if result.returncode != 0:
        logger.error( f'  gffread failed: {result.stderr}' )
        return [], { 'path': 'C (gffread)', 'error': result.stderr }

    # Parse gffread output
    transcript_identifiers___sequences, transcript_identifiers___headers = parse_fasta( gffread_output_path )
    total_transcript_count = len( transcript_identifiers___sequences )
    logger.info( f'  Total transcripts from gffread: {total_transcript_count}' )

    # Parse annotation for gene -> transcript mapping
    if annotation_format == 'gtf':
        gene_identifiers___transcript_identifiers = parse_gtf_gene_transcript_mapping( annotation_path )
    else:
        # For GFF3, build gene -> transcript mapping
        gene_identifiers___transcript_identifiers = defaultdict( list )

        with open( annotation_path, 'r' ) as input_annotation:
            for line in input_annotation:
                line = line.strip()
                if line.startswith( '#' ) or len( line ) == 0:
                    continue

                parts = line.split( '\t' )
                if len( parts ) < 9:
                    continue

                feature_type = parts[ 2 ]
                if feature_type in ( 'mRNA', 'transcript' ):
                    attributes = parse_gff3_attributes( parts[ 8 ] )
                    transcript_identifier = attributes.get( 'ID', '' )
                    parent_gene_identifier = attributes.get( 'Parent', '' )

                    if transcript_identifier and parent_gene_identifier:
                        gene_identifiers___transcript_identifiers[ parent_gene_identifier ].append( transcript_identifier )

    total_gene_count = len( gene_identifiers___transcript_identifiers )
    logger.info( f'  Total genes in annotation: {total_gene_count}' )

    # Select longest transcript per gene
    t1_proteins = []
    multi_transcript_gene_count = 0

    for gene_identifier in sorted( gene_identifiers___transcript_identifiers.keys() ):
        transcript_identifiers = gene_identifiers___transcript_identifiers[ gene_identifier ]

        if len( transcript_identifiers ) > 1:
            multi_transcript_gene_count += 1

        longest_transcript_identifier = None
        longest_sequence = ''
        longest_length = 0

        for transcript_identifier in transcript_identifiers:
            if transcript_identifier in transcript_identifiers___sequences:
                sequence = transcript_identifiers___sequences[ transcript_identifier ]
                sequence_clean = sequence.rstrip( '.' )

                if len( sequence_clean ) > longest_length:
                    longest_length = len( sequence_clean )
                    longest_sequence = sequence_clean
                    longest_transcript_identifier = transcript_identifier

        if longest_transcript_identifier is not None:
            output_header = f'{genus_species}-repository_genomes|{gene_identifier}|{longest_transcript_identifier}'
            t1_proteins.append( ( output_header, longest_sequence ) )

    statistics = {
        'path': f'C (gffread, {annotation_format})',
        'total_genes': total_gene_count,
        'total_transcripts': total_transcript_count,
        'multi_transcript_genes': multi_transcript_gene_count,
        't1_proteins_extracted': len( t1_proteins ),
    }

    return t1_proteins, statistics


# ============================================================================
# Path D: protein.faa only -> use all as-is
# ============================================================================

def extract_all_proteins( protein_fasta_path, genus_species ):
    """
    Use all proteins from FASTA when no annotation is available.
    Cannot do T1 filtering.

    Parameters:
        protein_fasta_path (Path): Protein FASTA
        genus_species (str): Species name

    Returns:
        list: (header, sequence) tuples
        dict: Statistics
    """

    protein_identifiers___sequences, protein_identifiers___headers = parse_fasta( protein_fasta_path )

    t1_proteins = []
    for protein_identifier in sorted( protein_identifiers___sequences.keys() ):
        sequence = protein_identifiers___sequences[ protein_identifier ]
        output_header = f'{genus_species}-repository_genomes|{protein_identifier}|no_gene_mapping'
        t1_proteins.append( ( output_header, sequence ) )

    statistics = {
        'path': 'D (protein only, no T1 filtering)',
        'total_proteins': len( protein_identifiers___sequences ),
        't1_proteins_extracted': len( t1_proteins ),
        'warning': 'No annotation available - using all proteins without T1 filtering',
    }

    return t1_proteins, statistics


# ============================================================================
# Write FASTA output
# ============================================================================

def write_proteome_fasta( t1_proteins, output_path ):
    """
    Write T1 proteins to a FASTA file.

    Parameters:
        t1_proteins (list): List of (header, sequence) tuples
        output_path (Path): Output FASTA path
    """

    with open( output_path, 'w' ) as output_fasta:
        for header, sequence in t1_proteins:
            output = f'>{header}\n'
            output_fasta.write( output )

            # Write sequence in 80-character lines
            for index in range( 0, len( sequence ), 80 ):
                output = sequence[ index:index + 80 ] + '\n'
                output_fasta.write( output )


# ============================================================================
# Main
# ============================================================================

def main():
    """
    Main function: extract T1 proteomes for all species in repository genomes,
    choosing the appropriate extraction path based on available data.
    """

    parser = argparse.ArgumentParser(
        description = 'Extract T1 proteomes from repository genome data (flexible input paths)'
    )
    parser.add_argument( '--input-dir', required = True,
                         help = 'Directory containing genome/, annotation/, protein/ subdirs (2-output)' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Output directory (3-output)' )
    arguments = parser.parse_args()

    input_directory = Path( arguments.input_dir )
    output_directory = Path( arguments.output_dir )

    input_genome_directory = input_directory / 'genome'
    input_annotation_directory = input_directory / 'annotation'
    input_protein_directory = input_directory / 'protein'

    logger.info( '============================================' )
    logger.info( '003: Extract T1 proteomes' )
    logger.info( '============================================' )
    logger.info( '' )
    logger.info( f'Input genome:     {input_genome_directory}' )
    logger.info( f'Input annotation: {input_annotation_directory}' )
    logger.info( f'Input protein:    {input_protein_directory}' )
    logger.info( f'Output:           {output_directory}' )
    logger.info( '' )

    # Create output directories
    output_t1_directory = output_directory / 'T1_proteomes'
    output_t1_directory.mkdir( parents = True, exist_ok = True )
    intermediate_directory = output_directory / 'gffread_intermediate'
    intermediate_directory.mkdir( parents = True, exist_ok = True )

    # Discover all species from available files across all three input directories
    species_names = set()

    if input_genome_directory.exists():
        for genome_file in input_genome_directory.glob( '*-repository_genomes.fasta' ):
            genus_species = genome_file.stem.replace( '-repository_genomes', '' )
            species_names.add( genus_species )

    if input_annotation_directory.exists():
        for annotation_file in list( input_annotation_directory.glob( '*-repository_genomes.gff3' ) ) + list( input_annotation_directory.glob( '*-repository_genomes.gtf' ) ):
            genus_species = annotation_file.stem.replace( '-repository_genomes', '' )
            species_names.add( genus_species )

    if input_protein_directory.exists():
        for protein_file in input_protein_directory.glob( '*-repository_genomes.faa' ):
            genus_species = protein_file.stem.replace( '-repository_genomes', '' )
            species_names.add( genus_species )

    if len( species_names ) == 0:
        logger.warning( 'No species files found in 2-output/ subdirectories.' )
        logger.warning( 'This is expected if no per-species download scripts have been run yet.' )
        sys.exit( 0 )

    species_names_sorted = sorted( species_names )
    logger.info( f'Species discovered: {len( species_names_sorted )}' )
    logger.info( '' )

    # Process each species
    total_count = len( species_names_sorted )
    success_count = 0
    failed_species = []
    all_statistics = []

    for index, genus_species in enumerate( species_names_sorted, 1 ):

        logger.info( f'--------------------------------------------' )
        logger.info( f'[{index}/{total_count}] {genus_species}' )
        logger.info( f'--------------------------------------------' )

        # Detect available files
        has_genome = ( input_genome_directory / f'{genus_species}-repository_genomes.fasta' ).exists() if input_genome_directory.exists() else False
        has_protein = ( input_protein_directory / f'{genus_species}-repository_genomes.faa' ).exists() if input_protein_directory.exists() else False

        has_gff3 = ( input_annotation_directory / f'{genus_species}-repository_genomes.gff3' ).exists() if input_annotation_directory.exists() else False
        has_gtf = ( input_annotation_directory / f'{genus_species}-repository_genomes.gtf' ).exists() if input_annotation_directory.exists() else False

        logger.info( f'  Available: genome={has_genome}, protein={has_protein}, gff3={has_gff3}, gtf={has_gtf}' )

        t1_proteins = []
        statistics = {}

        try:
            # Path A: protein + GFF3
            if has_protein and has_gff3:
                logger.info( f'  Using Path A: protein.faa + GFF3 annotation' )
                protein_path = input_protein_directory / f'{genus_species}-repository_genomes.faa'
                gff3_path = input_annotation_directory / f'{genus_species}-repository_genomes.gff3'
                t1_proteins, statistics = extract_t1_from_protein_and_gff3( protein_path, gff3_path, genus_species )

            # Path B: protein + GTF
            elif has_protein and has_gtf:
                logger.info( f'  Using Path B: protein.faa + GTF annotation' )
                protein_path = input_protein_directory / f'{genus_species}-repository_genomes.faa'
                gtf_path = input_annotation_directory / f'{genus_species}-repository_genomes.gtf'
                t1_proteins, statistics = extract_t1_from_protein_and_gtf( protein_path, gtf_path, genus_species )

            # Path C: genome + annotation (no protein) -> gffread
            elif has_genome and ( has_gff3 or has_gtf ):
                logger.info( f'  Using Path C: genome + annotation via gffread' )
                genome_path = input_genome_directory / f'{genus_species}-repository_genomes.fasta'

                if has_gff3:
                    annotation_path = input_annotation_directory / f'{genus_species}-repository_genomes.gff3'
                    annotation_format = 'gff3'
                else:
                    annotation_path = input_annotation_directory / f'{genus_species}-repository_genomes.gtf'
                    annotation_format = 'gtf'

                t1_proteins, statistics = extract_t1_via_gffread(
                    genome_path, annotation_path, annotation_format, genus_species, intermediate_directory
                )

            # Path D: protein only (no annotation)
            elif has_protein:
                logger.warning( f'  Using Path D: protein only (NO T1 filtering possible)' )
                protein_path = input_protein_directory / f'{genus_species}-repository_genomes.faa'
                t1_proteins, statistics = extract_all_proteins( protein_path, genus_species )

            # No usable data
            else:
                logger.error( f'  No usable data combination for {genus_species}' )
                logger.error( f'  Need at minimum: protein.faa OR genome.fasta + annotation' )
                failed_species.append( genus_species )
                continue

            # Report statistics
            for key, value in statistics.items():
                logger.info( f'  {key}: {value}' )

            # Write output
            if len( t1_proteins ) > 0:
                output_path = output_t1_directory / f'{genus_species}-repository_genomes-T1_proteome.aa'
                write_proteome_fasta( t1_proteins, output_path )
                logger.info( f'  Output: {output_path.name} ({len( t1_proteins )} proteins)' )
                success_count += 1
                statistics[ 'genus_species' ] = genus_species
                all_statistics.append( statistics )
            else:
                logger.error( f'  CRITICAL: No proteins extracted for {genus_species}!' )
                failed_species.append( genus_species )

        except Exception as error:
            logger.error( f'  ERROR: Failed to process {genus_species}: {error}' )
            import traceback
            traceback.print_exc()
            failed_species.append( genus_species )

        logger.info( '' )

    # Summary
    logger.info( '============================================' )
    logger.info( 'T1 extraction complete' )
    logger.info( '============================================' )
    logger.info( '' )
    logger.info( f'Species discovered: {total_count}' )
    logger.info( f'Successful:         {success_count}' )
    logger.info( f'Failed:             {len( failed_species )}' )
    logger.info( '' )

    if len( all_statistics ) > 0:
        logger.info( f'{"Species":<40} {"Path":<25} {"T1 Proteins":>12}' )
        logger.info( '-' * 80 )
        for statistics in all_statistics:
            logger.info(
                f'{statistics[ "genus_species" ]:<40} '
                f'{statistics[ "path" ]:<25} '
                f'{statistics[ "t1_proteins_extracted" ]:>12}'
            )

    if len( failed_species ) > 0:
        logger.info( '' )
        logger.info( 'Failed species:' )
        for species in failed_species:
            logger.info( f'  - {species}' )
        logger.info( '' )
        logger.error( 'ERROR: Some species failed T1 extraction.' )
        sys.exit( 1 )

    logger.info( '' )
    logger.info( 'Done!' )


if __name__ == '__main__':
    main()
