#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Extract protein sequences from genome + GFF3 annotation using gffread, then filter to longest transcript per gene (T1)
# Human: Eric Edsinger

"""
002_ai-python-extract_protein_from_genome_annotation.py

For repository_genomes species that have genome.fasta + annotation.gff3 but no
protein.faa, extract protein sequences using gffread and select the longest
transcript per gene (T1).

Pipeline for each species:
  1. Validate GFF3 coordinates against genome scaffolds (filter out-of-bounds)
  2. Run gffread -y to extract protein sequences for ALL transcripts
  3. Parse GFF3 to build gene -> transcript mapping
  4. Select longest protein per gene (T1)
  5. Write T1 proteome to 2-output/{genus_species}/protein.faa
  6. Also copy back to 1-output/{genus_species}/protein.faa

GFF3 hierarchy (standard):
    gene  (ID=gene_id)
      └── mRNA or transcript  (ID=transcript_id, Parent=gene_id)
            └── CDS  (Parent=transcript_id)

gffread output: uses transcript IDs as FASTA headers

Usage:
    python3 002_ai-python-extract_protein_from_genome_annotation.py \\
        --input-dir 1-output \\
        --output-dir 2-output

Requires:
    - gffread (module load gffread or /apps/gffread/0.12.7/bin/gffread)
"""

import argparse
import os
import sys
import subprocess
import re
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
# Functions
# ============================================================================

def parse_fasta( fasta_path ):
    """Parse a FASTA file into a dictionary of identifier -> sequence."""

    identifiers___sequences = {}
    current_identifier = None
    current_sequence_parts = []

    # >g587.t1
    # MAAGSKLRLTVLCILLMQAASIPAVSFTSIPG...
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()
            if line.startswith( '>' ):
                if current_identifier is not None:
                    identifiers___sequences[ current_identifier ] = ''.join( current_sequence_parts )
                # Take first whitespace-delimited token as identifier
                current_identifier = line[ 1: ].split()[ 0 ]
                current_sequence_parts = []
            else:
                current_sequence_parts.append( line )

        if current_identifier is not None:
            identifiers___sequences[ current_identifier ] = ''.join( current_sequence_parts )

    return identifiers___sequences


def parse_gff3_gene_transcript_mapping( gff3_path ):
    """
    Parse a GFF3 file to extract gene_id -> [transcript_id] mapping.

    Handles both standard GFF3 hierarchy:
        gene (ID) -> mRNA (Parent=gene_ID) -> CDS (Parent=mRNA_ID)
    And Schmidtea-style:
        gene (ID) -> transcript (Parent=gene_ID or gene_id attribute) -> CDS (Parent=transcript_ID)

    Parameters:
        gff3_path (Path): Path to GFF3 annotation file

    Returns:
        dict: gene_id -> sorted list of transcript_ids
    """

    gene_identifiers___transcript_identifiers = defaultdict( set )
    transcript_identifiers___gene_identifiers = {}

    # gene_id	ID=g587;Name=g587.t1
    # mRNA	ID=g587.t1;Parent=g587
    # OR
    # gene	ID=h1SMcG0000001;gene_id=h1SMcG0000001
    # transcript	ID=h1SMcT0000001.1;gene_id=h1SMcG0000001
    with open( gff3_path, 'r' ) as input_gff3:
        for line in input_gff3:
            line = line.strip()
            if line.startswith( '#' ) or len( line ) == 0:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 9:
                continue

            feature_type = parts[ 2 ]
            attributes_string = parts[ 8 ]

            # Parse attributes
            attributes = {}
            for pair in attributes_string.strip().split( ';' ):
                if '=' in pair:
                    key, value = pair.split( '=', 1 )
                    attributes[ key.strip() ] = value.strip()

            # Track mRNA and transcript features -> parent gene
            if feature_type in ( 'mRNA', 'transcript' ):
                transcript_identifier = attributes.get( 'ID', '' )
                parent_gene_identifier = attributes.get( 'Parent', '' )

                # Some GFF3 files use gene_id attribute instead of Parent
                if not parent_gene_identifier:
                    parent_gene_identifier = attributes.get( 'gene_id', '' )

                if transcript_identifier and parent_gene_identifier:
                    gene_identifiers___transcript_identifiers[ parent_gene_identifier ].add( transcript_identifier )
                    transcript_identifiers___gene_identifiers[ transcript_identifier ] = parent_gene_identifier

    # Sort transcript lists for reproducibility
    for gene_identifier in gene_identifiers___transcript_identifiers:
        gene_identifiers___transcript_identifiers[ gene_identifier ] = sorted(
            gene_identifiers___transcript_identifiers[ gene_identifier ]
        )

    return dict( gene_identifiers___transcript_identifiers )


def read_fasta_index( fai_path ):
    """Read a FASTA index (.fai) file to get scaffold/chromosome lengths."""

    scaffold_names___lengths = {}

    # scaffold_name	length	offset	linebases	linewidth
    # NODE_1579_length_10372_cov_37.9085	10372	49	80	81
    with open( fai_path, 'r' ) as input_fai:
        for line in input_fai:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            scaffold_name = parts[ 0 ]
            scaffold_length = int( parts[ 1 ] )
            scaffold_names___lengths[ scaffold_name ] = scaffold_length

    return scaffold_names___lengths


def filter_gff3_by_genome_bounds( gff3_path, genome_fasta_path, filtered_gff3_path ):
    """Filter a GFF3 file to remove entries with coordinates beyond scaffold boundaries."""

    # First, create FASTA index if it doesn't exist
    fai_path = Path( str( genome_fasta_path ) + '.fai' )
    if not fai_path.exists():
        logger.info( f'  Creating FASTA index with samtools faidx...' )
        result = subprocess.run(
            [ 'samtools', 'faidx', str( genome_fasta_path ) ],
            capture_output = True, text = True
        )
        if result.returncode != 0:
            # Try with gffread as fallback (it also creates .fai)
            logger.info( f'  samtools not available, trying gffread for indexing...' )
            subprocess.run(
                [ 'gffread', '-g', str( genome_fasta_path ), '/dev/null' ],
                capture_output = True, text = True
            )

    if not fai_path.exists():
        logger.warning( f'  Could not create FASTA index, skipping bounds validation' )
        return 0, 0

    scaffold_names___lengths = read_fasta_index( fai_path )
    logger.info( f'  Genome has {len( scaffold_names___lengths )} scaffolds/chromosomes' )

    total_line_count = 0
    kept_line_count = 0
    removed_line_count = 0

    with open( gff3_path, 'r' ) as input_gff3, open( filtered_gff3_path, 'w' ) as output_gff3:
        for line in input_gff3:
            total_line_count += 1
            line_stripped = line.strip()

            if line_stripped.startswith( '#' ) or len( line_stripped ) == 0:
                output_gff3.write( line )
                kept_line_count += 1
                continue

            parts = line_stripped.split( '\t' )
            if len( parts ) < 5:
                output_gff3.write( line )
                kept_line_count += 1
                continue

            scaffold_name = parts[ 0 ]
            end_coordinate = int( parts[ 4 ] )

            scaffold_length = scaffold_names___lengths.get( scaffold_name, None )
            if scaffold_length is None:
                removed_line_count += 1
                continue

            if end_coordinate > scaffold_length:
                removed_line_count += 1
                continue

            output_gff3.write( line )
            kept_line_count += 1

    return total_line_count, removed_line_count


def run_gffread( genome_fasta_path, gff3_path, output_protein_path ):
    """Run gffread to extract protein sequences for all transcripts."""

    # First validate and filter GFF3 coordinates
    filtered_gff3_path = Path( str( gff3_path ) + '.filtered.tmp' )
    logger.info( f'  Validating GFF3 coordinates against genome...' )

    total_line_count, removed_line_count = filter_gff3_by_genome_bounds(
        gff3_path, genome_fasta_path, filtered_gff3_path
    )

    if removed_line_count > 0:
        logger.warning( f'  Removed {removed_line_count} out-of-bounds lines from GFF3' )
        gff3_to_use = filtered_gff3_path
    else:
        logger.info( f'  All GFF3 coordinates within genome bounds' )
        gff3_to_use = gff3_path

    # Run gffread
    command = [
        'gffread',
        '-y', str( output_protein_path ),
        '-g', str( genome_fasta_path ),
        str( gff3_to_use )
    ]

    logger.info( f'  Running: {" ".join( command )}' )

    result = subprocess.run( command, capture_output = True, text = True )

    # Cleanup filtered file
    if filtered_gff3_path.exists():
        filtered_gff3_path.unlink()

    if result.returncode != 0:
        logger.error( f'  gffread failed with return code {result.returncode}' )
        logger.error( f'  stderr: {result.stderr}' )
        return False

    if result.stderr:
        # Count warnings (don't show all of them)
        warning_count = result.stderr.count( '\n' )
        if warning_count > 0:
            logger.info( f'  gffread produced {warning_count} warning lines (normal for draft annotations)' )

    return True


def select_longest_transcript_per_gene( gene_identifiers___transcript_identifiers, transcript_identifiers___sequences ):
    """For each gene, select the transcript with the longest protein sequence."""

    gene_identifiers___longest_transcript_data = {}

    for gene_identifier in gene_identifiers___transcript_identifiers:
        transcript_identifiers = gene_identifiers___transcript_identifiers[ gene_identifier ]

        longest_transcript_identifier = None
        longest_sequence = ''
        longest_length = 0

        for transcript_identifier in transcript_identifiers:
            if transcript_identifier in transcript_identifiers___sequences:
                sequence = transcript_identifiers___sequences[ transcript_identifier ]
                # Remove stop codon markers (. or *)
                sequence_clean = sequence.rstrip( '.' ).rstrip( '*' )
                sequence_length = len( sequence_clean )

                if sequence_length > longest_length:
                    longest_length = sequence_length
                    longest_sequence = sequence_clean
                    longest_transcript_identifier = transcript_identifier

        if longest_transcript_identifier is not None:
            gene_identifiers___longest_transcript_data[ gene_identifier ] = {
                'transcript_identifier': longest_transcript_identifier,
                'sequence': longest_sequence,
                'length': longest_length,
            }

    return gene_identifiers___longest_transcript_data


def write_t1_proteome( gene_identifiers___longest_transcript_data, genus_species, output_path ):
    """Write the T1 proteome FASTA file with formatted headers."""

    sorted_gene_identifiers = sorted( gene_identifiers___longest_transcript_data.keys() )

    with open( output_path, 'w' ) as output_proteome:
        for gene_identifier in sorted_gene_identifiers:
            transcript_data = gene_identifiers___longest_transcript_data[ gene_identifier ]
            transcript_identifier = transcript_data[ 'transcript_identifier' ]
            sequence = transcript_data[ 'sequence' ]

            # Header format: >Genus_species-repository_genomes|transcript_id|gene_id
            header = f'>{genus_species}-repository_genomes|{transcript_identifier}|{gene_identifier}'
            output = header + '\n'
            output_proteome.write( output )

            # Write sequence in 80-character lines
            for index in range( 0, len( sequence ), 80 ):
                output = sequence[ index:index + 80 ] + '\n'
                output_proteome.write( output )


def process_species( genus_species, genome_path, annotation_path, output_directory ):
    """Full pipeline for one species: validate -> gffread -> T1 filter -> write."""

    logger.info( f'============================================' )
    logger.info( f'Processing: {genus_species}' )
    logger.info( f'  Genome: {genome_path} ({genome_path.stat().st_size / 1024 / 1024:.0f} MB)' )
    logger.info( f'  Annotation: {annotation_path} ({annotation_path.stat().st_size / 1024 / 1024:.0f} MB)' )
    logger.info( f'============================================' )

    # Create intermediate directory for gffread output
    intermediate_directory = output_directory / 'gffread_all_transcripts'
    intermediate_directory.mkdir( parents = True, exist_ok = True )

    intermediate_protein_path = intermediate_directory / f'{genus_species}-all_transcripts.fa'

    # Step 1: Run gffread to extract ALL protein sequences
    logger.info( f'  Step 1: Extracting all protein sequences with gffread...' )
    success = run_gffread( genome_path, annotation_path, intermediate_protein_path )

    if not success:
        logger.error( f'  CRITICAL: gffread failed for {genus_species}!' )
        return None

    if not intermediate_protein_path.exists() or intermediate_protein_path.stat().st_size == 0:
        logger.error( f'  CRITICAL: gffread produced no output for {genus_species}!' )
        return None

    # Step 2: Parse gffread output
    logger.info( f'  Step 2: Parsing gffread protein output...' )
    transcript_identifiers___sequences = parse_fasta( intermediate_protein_path )
    total_transcript_count = len( transcript_identifiers___sequences )
    logger.info( f'    Total transcripts from gffread: {total_transcript_count}' )

    if total_transcript_count == 0:
        logger.error( f'  CRITICAL: No protein sequences extracted by gffread!' )
        return None

    # Step 3: Parse GFF3 for gene-transcript mapping
    logger.info( f'  Step 3: Parsing GFF3 for gene-transcript mapping...' )
    gene_identifiers___transcript_identifiers = parse_gff3_gene_transcript_mapping( annotation_path )
    total_gene_count = len( gene_identifiers___transcript_identifiers )
    logger.info( f'    Total genes in GFF3: {total_gene_count}' )

    # Step 4: Select longest transcript per gene (T1)
    logger.info( f'  Step 4: Selecting longest transcript per gene (T1)...' )
    gene_identifiers___longest_transcript_data = select_longest_transcript_per_gene(
        gene_identifiers___transcript_identifiers,
        transcript_identifiers___sequences
    )
    t1_gene_count = len( gene_identifiers___longest_transcript_data )
    logger.info( f'    T1 genes with protein: {t1_gene_count}' )

    # If gene mapping found fewer than gffread output, include orphan transcripts
    # (transcripts not linked to any gene - treat each as its own gene)
    linked_transcript_identifiers = set()
    for transcript_identifiers in gene_identifiers___transcript_identifiers.values():
        linked_transcript_identifiers.update( transcript_identifiers )

    orphan_transcript_identifiers = set( transcript_identifiers___sequences.keys() ) - linked_transcript_identifiers
    orphan_count = len( orphan_transcript_identifiers )

    if orphan_count > 0:
        logger.info( f'    Orphan transcripts (not linked to gene in GFF3): {orphan_count}' )
        logger.info( f'    Including orphan transcripts as individual genes...' )

        for transcript_identifier in sorted( orphan_transcript_identifiers ):
            sequence = transcript_identifiers___sequences[ transcript_identifier ]
            sequence_clean = sequence.rstrip( '.' ).rstrip( '*' )
            # Use transcript ID as both gene and transcript identifier
            gene_identifiers___longest_transcript_data[ transcript_identifier ] = {
                'transcript_identifier': transcript_identifier,
                'sequence': sequence_clean,
                'length': len( sequence_clean ),
            }

        t1_gene_count = len( gene_identifiers___longest_transcript_data )
        logger.info( f'    Total T1 proteins (including orphans): {t1_gene_count}' )

    # Step 5: Write T1 proteome
    species_output_directory = output_directory / genus_species
    species_output_directory.mkdir( parents = True, exist_ok = True )

    output_proteome_path = species_output_directory / 'protein.faa'
    logger.info( f'  Step 5: Writing T1 proteome to {output_proteome_path}' )
    write_t1_proteome(
        gene_identifiers___longest_transcript_data,
        genus_species,
        output_proteome_path
    )

    multi_transcript_gene_count = sum(
        1 for gene_identifier in gene_identifiers___transcript_identifiers
        if len( gene_identifiers___transcript_identifiers[ gene_identifier ] ) > 1
    )

    summary = {
        'genus_species': genus_species,
        'total_genes_in_gff3': total_gene_count,
        'total_transcripts_from_gffread': total_transcript_count,
        'multi_transcript_genes': multi_transcript_gene_count,
        'orphan_transcripts': orphan_count,
        't1_proteins': t1_gene_count,
        'output_file': str( output_proteome_path ),
    }

    logger.info( f'  Summary:' )
    logger.info( f'    Genes in GFF3:          {total_gene_count}' )
    logger.info( f'    Transcripts (gffread):  {total_transcript_count}' )
    logger.info( f'    Multi-transcript genes: {multi_transcript_gene_count}' )
    logger.info( f'    Orphan transcripts:     {orphan_count}' )
    logger.info( f'    T1 proteins written:    {t1_gene_count}' )

    return summary


# ============================================================================
# Main
# ============================================================================

def main():

    parser = argparse.ArgumentParser(
        description = 'Extract T1 proteomes from genome + GFF3 annotation using gffread'
    )
    parser.add_argument( '--input-dir', required = True,
                         help = 'Directory containing per-species subdirectories with genome.fasta and annotation.gff3' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Output directory (will create per-species subdirectories with protein.faa)' )
    arguments = parser.parse_args()

    input_directory = Path( arguments.input_dir )
    output_directory = Path( arguments.output_dir )

    print( '============================================' )
    print( '002: Extract protein from genome + annotation' )
    print( '============================================' )
    print( '' )

    # Check gffread availability
    gffread_check = subprocess.run( [ 'which', 'gffread' ], capture_output = True, text = True )
    if gffread_check.returncode != 0:
        logger.error( 'CRITICAL ERROR: gffread not found in PATH' )
        logger.error( 'Run: module load gffread' )
        sys.exit( 1 )
    logger.info( f'Using gffread: {gffread_check.stdout.strip()}' )

    # Find species that need protein extraction:
    # genome.fasta exists AND annotation.gff3 exists AND protein.faa does NOT exist (or is empty)
    species_to_process = []

    for species_directory in sorted( input_directory.iterdir() ):
        if not species_directory.is_dir():
            continue

        genus_species = species_directory.name

        # Skip cache directories
        if genus_species.startswith( '_' ):
            continue

        genome_path = species_directory / 'genome.fasta'
        annotation_path = species_directory / 'annotation.gff3'
        protein_path = species_directory / 'protein.faa'

        if not genome_path.exists() or genome_path.stat().st_size == 0:
            continue

        if not annotation_path.exists() or annotation_path.stat().st_size == 0:
            continue

        # Only process species without protein (or with empty protein file)
        if protein_path.exists() and protein_path.stat().st_size > 0:
            logger.info( f'SKIP {genus_species}: protein.faa already exists ({protein_path.stat().st_size / 1024:.0f} KB)' )
            continue

        species_to_process.append( ( genus_species, genome_path, annotation_path ) )

    if len( species_to_process ) == 0:
        logger.info( 'No species need protein extraction (all have protein.faa already).' )
        return

    logger.info( f'Species needing protein extraction: {len( species_to_process )}' )
    for genus_species, genome_path, annotation_path in species_to_process:
        logger.info( f'  - {genus_species}' )
    print( '' )

    # Process each species
    all_summaries = []

    for genus_species, genome_path, annotation_path in species_to_process:
        summary = process_species( genus_species, genome_path, annotation_path, output_directory )

        if summary:
            all_summaries.append( summary )

            # Also copy the protein.faa back to 1-output for consistency
            source_protein = Path( summary[ 'output_file' ] )
            destination_protein = genome_path.parent / 'protein.faa'
            if source_protein.exists() and source_protein.stat().st_size > 0:
                import shutil
                shutil.copy2( source_protein, destination_protein )
                logger.info( f'  Copied protein.faa back to {destination_protein}' )
        else:
            logger.error( f'  FAILED: {genus_species}' )

    # Final summary
    print( '' )
    print( '============================================' )
    print( 'Protein extraction complete' )
    print( '============================================' )
    print( '' )

    if len( all_summaries ) > 0:
        print( f'{"Species":<35} {"Genes":>8} {"Transcripts":>13} {"Multi-T":>9} {"Orphans":>9} {"T1 Prots":>10}' )
        print( '-' * 90 )

        for summary in all_summaries:
            print(
                f'{summary[ "genus_species" ]:<35} '
                f'{summary[ "total_genes_in_gff3" ]:>8} '
                f'{summary[ "total_transcripts_from_gffread" ]:>13} '
                f'{summary[ "multi_transcript_genes" ]:>9} '
                f'{summary[ "orphan_transcripts" ]:>9} '
                f'{summary[ "t1_proteins" ]:>10}'
            )

        print( '-' * 90 )

    print( f'Species processed: {len( all_summaries )}' )
    print( '' )

    failed = [ s for s in species_to_process if s[ 0 ] not in [ x[ 'genus_species' ] for x in all_summaries ] ]
    if len( failed ) > 0:
        print( 'FAILED species:' )
        for genus_species, _, _ in failed:
            print( f'  - {genus_species}' )
        sys.exit( 1 )

    print( 'Done!' )


if __name__ == '__main__':
    main()
