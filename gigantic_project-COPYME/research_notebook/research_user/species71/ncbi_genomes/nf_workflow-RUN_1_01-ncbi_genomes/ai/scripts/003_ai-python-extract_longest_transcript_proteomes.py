#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 12 15:45 | Purpose: Extract T1 (longest transcript per gene) proteomes from NCBI protein files using GFF3 mappings, reformat for genomesDB STEP_1 input, and generate identifier mapping files
# Human: Eric Edsinger

"""
003_ai-python-extract_longest_transcript_proteomes.py

Filters NCBI protein FASTA files to retain only the longest protein per gene
(T1 = transcript 1 = longest isoform). Uses GFF3 annotation to build the
gene -> mRNA -> CDS -> protein_id mapping chain.

Reformats output for GIGANTIC genomesDB STEP_1 input:
  - File naming: genus_species-genome-ncbi_ACCESSION-downloaded_YYYYMMDD.{fasta,gff3,aa}
  - Proteome headers: >genus_species-gene_id-transcript_id-protein_id
    (dashes in source IDs replaced with underscores)
  - Genome FASTA and GFF3 are copied with new names (content unchanged)
  - Two mapping TSV files track all original -> updated identifier changes

NCBI GFF3 hierarchy:
    gene  (ID=gene-XXX)
      └── mRNA  (Parent=gene-XXX)
            └── CDS  (Parent=rna-XXX, protein_id=YYY)

NCBI protein.faa header format:
    >XP_002119107.1 description [Species name]
    >OAF67967.1 description [Species name]

The protein_id in CDS features matches the first word of protein.faa headers.

Output header format:
    >Genus_species-gene_id-transcript_id-protein_id
    (dashes in source IDs replaced with underscores)

Usage:
    python3 003_ai-python-extract_longest_transcript_proteomes.py \\
        --manifest INPUT_user/ncbi_genomes_manifest.tsv \\
        --genome-dir 2-output/genome \\
        --gff3-dir 2-output/gff3 \\
        --protein-dir 2-output/protein \\
        --output-dir 3-output \\
        --download-date downloaded_20260211
"""

import argparse
import sys
import shutil
import logging
from pathlib import Path
from collections import defaultdict


# ============================================================================
# Configuration
# ============================================================================

SOURCE_PREFIX = 'ncbi'

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


def read_manifest( manifest_path ):
    """
    Read the NCBI genomes manifest TSV to get genus_species -> accession mapping.

    Parameters:
        manifest_path (Path): Path to the manifest TSV file

    Returns:
        dict: genus_species -> accession mapping
    """

    genus_species_names___accessions = {}

    # genus_species	accession
    # Intoshia_linei	GCA_001642005.1
    with open( manifest_path, 'r' ) as input_manifest:
        for line in input_manifest:
            line = line.strip()

            # Skip comments and empty lines
            if line.startswith( '#' ) or len( line ) == 0:
                continue

            # Skip header line
            if line.startswith( 'genus_species' ):
                continue

            parts = line.split( '\t' )
            if len( parts ) >= 2:
                genus_species = parts[ 0 ]
                accession = parts[ 1 ]
                genus_species_names___accessions[ genus_species ] = accession

    return genus_species_names___accessions


def parse_gff3_attributes( attributes_string ):
    """
    Parse a GFF3 attributes column (column 9) into a dictionary.

    Parameters:
        attributes_string (str): Semicolon-separated key=value pairs

    Returns:
        dict: Attribute key-value pairs
    """

    attributes = {}

    for pair in attributes_string.strip().split( ';' ):
        if '=' in pair:
            key, value = pair.split( '=', 1 )
            attributes[ key ] = value

    return attributes


def build_gene_to_protein_mapping( gff3_path ):
    """
    Parse a GFF3 file to build mappings from gene IDs to protein IDs,
    and from protein IDs to their parent mRNA/transcript IDs.

    Follows the NCBI GFF3 hierarchy:
        gene (ID) -> mRNA (Parent=gene_ID) -> CDS (Parent=mRNA_ID, protein_id)

    Parameters:
        gff3_path (Path): Path to the GFF3 annotation file

    Returns:
        dict: gene_id -> list of protein_ids
        dict: protein_id -> transcript_id (mRNA accession without rna- prefix)
    """

    # Step 1: Build mRNA_id -> gene_id mapping
    messenger_rna_identifiers___gene_identifiers = {}

    # Step 2: Build protein_id -> mRNA_id mapping (via CDS Parent)
    protein_identifiers___messenger_rna_identifiers = {}

    # Also track CDS directly under genes (no intermediate mRNA)
    protein_identifiers___gene_identifiers_direct = {}

    # gff3 line format:
    # NW_002062354.1	RefSeq	gene	209	1006	.	-	.	ID=gene-TRIADDRAFT_63070;...
    # NW_002062354.1	RefSeq	mRNA	209	1006	.	-	.	ID=rna-XM_002119071.1;Parent=gene-TRIADDRAFT_63070;...
    # NW_002062354.1	RefSeq	CDS	209	1006	.	-	0	ID=cds-XP_002119107.1;Parent=rna-XM_002119071.1;...;protein_id=XP_002119107.1
    with open( gff3_path, 'r' ) as input_gff3:
        for line in input_gff3:
            line = line.strip()

            # Skip comments and empty lines
            if line.startswith( '#' ) or len( line ) == 0:
                continue

            parts = line.split( '\t' )

            if len( parts ) < 9:
                continue

            feature_type = parts[ 2 ]
            attributes = parse_gff3_attributes( parts[ 8 ] )

            if feature_type == 'mRNA':
                # mRNA links to parent gene
                messenger_rna_identifier = attributes.get( 'ID', '' )
                parent_gene_identifier = attributes.get( 'Parent', '' )

                if messenger_rna_identifier and parent_gene_identifier:
                    messenger_rna_identifiers___gene_identifiers[ messenger_rna_identifier ] = parent_gene_identifier

            elif feature_type == 'CDS':
                # CDS has protein_id and links to parent mRNA (or sometimes gene)
                protein_identifier = attributes.get( 'protein_id', '' )
                parent_identifier = attributes.get( 'Parent', '' )

                if protein_identifier and parent_identifier:
                    # Check if parent is an mRNA or a gene
                    if parent_identifier in messenger_rna_identifiers___gene_identifiers:
                        # Parent is mRNA -> map protein to mRNA
                        protein_identifiers___messenger_rna_identifiers[ protein_identifier ] = parent_identifier
                    elif parent_identifier.startswith( 'gene-' ):
                        # CDS directly under gene (no mRNA intermediate)
                        protein_identifiers___gene_identifiers_direct[ protein_identifier ] = parent_identifier
                    else:
                        # Parent might be an mRNA we haven't seen yet
                        # (GFF3 isn't always ordered) - store and resolve later
                        protein_identifiers___messenger_rna_identifiers[ protein_identifier ] = parent_identifier

    # Step 3: Build gene_id -> [protein_ids] mapping
    gene_identifiers___protein_identifiers = {}

    # Proteins linked through mRNA
    for protein_identifier, messenger_rna_identifier in protein_identifiers___messenger_rna_identifiers.items():
        gene_identifier = messenger_rna_identifiers___gene_identifiers.get( messenger_rna_identifier, None )

        if gene_identifier is not None:
            if gene_identifier not in gene_identifiers___protein_identifiers:
                gene_identifiers___protein_identifiers[ gene_identifier ] = []

            if protein_identifier not in gene_identifiers___protein_identifiers[ gene_identifier ]:
                gene_identifiers___protein_identifiers[ gene_identifier ].append( protein_identifier )

    # Proteins linked directly to genes
    for protein_identifier, gene_identifier in protein_identifiers___gene_identifiers_direct.items():
        if gene_identifier not in gene_identifiers___protein_identifiers:
            gene_identifiers___protein_identifiers[ gene_identifier ] = []

        if protein_identifier not in gene_identifiers___protein_identifiers[ gene_identifier ]:
            gene_identifiers___protein_identifiers[ gene_identifier ].append( protein_identifier )

    # Step 4: Build protein_id -> clean transcript_id mapping
    protein_identifiers___transcript_identifiers = {}

    for protein_identifier, messenger_rna_identifier in protein_identifiers___messenger_rna_identifiers.items():
        # Clean mRNA ID: remove "rna-" prefix if present
        clean_transcript_identifier = messenger_rna_identifier
        if clean_transcript_identifier.startswith( 'rna-' ):
            clean_transcript_identifier = clean_transcript_identifier[ 4: ]
        protein_identifiers___transcript_identifiers[ protein_identifier ] = clean_transcript_identifier

    # For proteins directly under genes (no mRNA), transcript_id = protein_id
    for protein_identifier in protein_identifiers___gene_identifiers_direct:
        protein_identifiers___transcript_identifiers[ protein_identifier ] = protein_identifier

    return gene_identifiers___protein_identifiers, protein_identifiers___transcript_identifiers


def read_protein_fasta( protein_fasta_path ):
    """
    Read a protein FASTA file and return a dictionary of protein_id -> sequence.

    NCBI protein.faa header format:
        >XP_002119107.1 description [Species name]

    The protein_id is the first whitespace-delimited word after '>'.

    Parameters:
        protein_fasta_path (Path): Path to the protein FASTA file

    Returns:
        dict: protein_id -> sequence (string, no newlines)
        dict: protein_id -> full_header (original header line without '>')
    """

    protein_identifiers___sequences = {}
    protein_identifiers___headers = {}

    current_protein_identifier = None
    current_header = None
    current_sequence_parts = []

    # >XP_002119107.1 uncharacterized protein TRIADDRAFT_51255 [Trichoplax adhaerens]
    # MDSSTDIPCNCVEILTASAETVNAHQTANHPVQRTATVLLAIANAVVIATVVTVNVHRAANQPVEKLATVQTIIAHAVLN
    with open( protein_fasta_path, 'r' ) as input_protein_fasta:
        for line in input_protein_fasta:
            line = line.strip()

            if line.startswith( '>' ):
                # Save previous protein
                if current_protein_identifier is not None:
                    protein_identifiers___sequences[ current_protein_identifier ] = ''.join( current_sequence_parts )
                    protein_identifiers___headers[ current_protein_identifier ] = current_header

                # Parse new header
                header = line[ 1: ]
                parts_header = header.split()
                current_protein_identifier = parts_header[ 0 ]
                current_header = header
                current_sequence_parts = []

            else:
                if len( line ) > 0:
                    current_sequence_parts.append( line )

    # Save last protein
    if current_protein_identifier is not None:
        protein_identifiers___sequences[ current_protein_identifier ] = ''.join( current_sequence_parts )
        protein_identifiers___headers[ current_protein_identifier ] = current_header

    return protein_identifiers___sequences, protein_identifiers___headers


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


def extract_t1_proteome( gff3_path, protein_fasta_path, genus_species ):
    """
    Extract the longest protein per gene (T1) for a single species.

    Parameters:
        gff3_path (Path): Path to the GFF3 annotation file
        protein_fasta_path (Path): Path to the NCBI protein FASTA file
        genus_species (str): Species name in Genus_species format

    Returns:
        list: List of dicts with gene/transcript/protein identifiers and sequence
        dict: Statistics about the extraction
    """

    # Build gene -> [protein_ids] mapping and protein -> transcript mapping from GFF3
    gene_identifiers___protein_identifiers, protein_identifiers___transcript_identifiers = build_gene_to_protein_mapping( gff3_path )

    # Read all proteins from FASTA
    protein_identifiers___sequences, protein_identifiers___headers = read_protein_fasta( protein_fasta_path )

    # For each gene, select the longest protein
    t1_proteins = []
    genes_with_single_isoform = 0
    genes_with_multiple_isoforms = 0
    orphan_protein_count = 0

    for gene_identifier in sorted( gene_identifiers___protein_identifiers.keys() ):
        protein_identifiers = gene_identifiers___protein_identifiers[ gene_identifier ]

        # Clean gene ID (remove "gene-" prefix for cleaner header)
        clean_gene_identifier = gene_identifier
        if clean_gene_identifier.startswith( 'gene-' ):
            clean_gene_identifier = clean_gene_identifier[ 5: ]

        if len( protein_identifiers ) == 1:
            genes_with_single_isoform += 1
        else:
            genes_with_multiple_isoforms += 1

        # Find the longest protein
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

            # Look up transcript/mRNA ID for this protein
            transcript_identifier = protein_identifiers___transcript_identifiers.get(
                longest_protein_identifier, longest_protein_identifier
            )

            t1_proteins.append( {
                'original_gene_identifier': clean_gene_identifier,
                'original_transcript_identifier': transcript_identifier,
                'original_protein_identifier': longest_protein_identifier,
                'updated_gene_identifier': sanitize_identifier( clean_gene_identifier ),
                'updated_transcript_identifier': sanitize_identifier( transcript_identifier ),
                'updated_protein_identifier': sanitize_identifier( longest_protein_identifier ),
                'sequence': sequence,
            } )

    # Count proteins in FASTA that weren't linked to any gene (orphans)
    linked_protein_identifiers = set()
    for protein_identifiers in gene_identifiers___protein_identifiers.values():
        linked_protein_identifiers.update( protein_identifiers )

    orphan_protein_count = len( set( protein_identifiers___sequences.keys() ) - linked_protein_identifiers )

    statistics = {
        'total_genes': len( gene_identifiers___protein_identifiers ),
        'single_isoform_genes': genes_with_single_isoform,
        'multiple_isoform_genes': genes_with_multiple_isoforms,
        'total_proteins_in_fasta': len( protein_identifiers___sequences ),
        't1_proteins_extracted': len( t1_proteins ),
        'orphan_proteins': orphan_protein_count,
    }

    return t1_proteins, statistics


def write_proteome_fasta( t1_proteins, genus_species, output_path ):
    """
    Write T1 proteins to a FASTA file with genomesDB header format.

    Header format: >genus_species-gene_id-transcript_id-protein_id
    (dashes in source IDs replaced with underscores)

    Parameters:
        t1_proteins (list): List of entry dicts
        genus_species (str): Species name
        output_path (Path): Output file path
    """

    with open( output_path, 'w' ) as output_fasta:
        for entry in t1_proteins:
            header = (
                f'>{genus_species}'
                f'-{entry[ "updated_gene_identifier" ]}'
                f'-{entry[ "updated_transcript_identifier" ]}'
                f'-{entry[ "updated_protein_identifier" ]}'
            )
            output = header + '\n'
            output_fasta.write( output )

            # Write sequence in 80-character lines
            sequence = entry[ 'sequence' ]
            for index in range( 0, len( sequence ), 80 ):
                output = sequence[ index:index + 80 ] + '\n'
                output_fasta.write( output )


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
        # Genus_Species (genus species name)	original_genome_identifier (original scaffold or chromosome name from source)	updated_genome_identifier (updated name with dashes replaced by underscores)
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
            genome_identifiers = species_result[ 'genome_identifiers' ]

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
        # Genus_Species (genus species name)	original_gene_id (gene identifier from source annotation)	updated_gene_id (gene identifier with dashes replaced by underscores)	original_transcript_id (transcript identifier from source annotation)	updated_transcript_id (transcript identifier with dashes replaced by underscores)	original_protein_id (protein identifier from source annotation)	updated_protein_id (protein identifier with dashes replaced by underscores)
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
            t1_proteins = species_result[ 't1_proteins' ]

            for entry in t1_proteins:
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
    """
    Main function: extract T1 proteomes for all species, reformat for genomesDB,
    and generate identifier mapping files.
    """

    parser = argparse.ArgumentParser(
        description = 'Extract T1 (longest transcript per gene) proteomes from NCBI data, reformat for genomesDB STEP_1 input'
    )
    parser.add_argument( '--manifest', required = True,
                         help = 'Path to ncbi_genomes_manifest.tsv (genus_species<TAB>accession)' )
    parser.add_argument( '--genome-dir', required = True,
                         help = 'Directory containing genome FASTA files (2-output/genome)' )
    parser.add_argument( '--gff3-dir', required = True,
                         help = 'Directory containing GFF3 files (2-output/gff3)' )
    parser.add_argument( '--protein-dir', required = True,
                         help = 'Directory containing protein FASTA files (2-output/protein)' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Output directory (3-output)' )
    parser.add_argument( '--download-date', default = 'downloaded_20260211',
                         help = 'Download date string for filenames (default: downloaded_20260211)' )
    arguments = parser.parse_args()

    manifest_path = Path( arguments.manifest )
    input_genome_directory = Path( arguments.genome_dir )
    input_gff3_directory = Path( arguments.gff3_dir )
    input_protein_directory = Path( arguments.protein_dir )
    output_directory = Path( arguments.output_dir )
    download_date = arguments.download_date

    print( '============================================' )
    print( '003: Extract T1 proteomes + genomesDB reformat' )
    print( '============================================' )
    print( '' )
    print( f'Manifest:          {manifest_path}' )
    print( f'Genome directory:  {input_genome_directory}' )
    print( f'GFF3 directory:    {input_gff3_directory}' )
    print( f'Protein directory: {input_protein_directory}' )
    print( f'Output directory:  {output_directory}' )
    print( f'Download date:     {download_date}' )
    print( '' )

    # Validate input paths
    for path, label in [
        ( manifest_path, 'Manifest' ),
        ( input_genome_directory, 'Genome directory' ),
        ( input_gff3_directory, 'GFF3 directory' ),
        ( input_protein_directory, 'Protein directory' ),
    ]:
        if not path.exists():
            logger.error( f'CRITICAL ERROR: {label} not found: {path}' )
            sys.exit( 1 )

    # Read manifest
    genus_species_names___accessions = read_manifest( manifest_path )
    print( f'Species in manifest: {len( genus_species_names___accessions )}' )
    print( '' )

    if len( genus_species_names___accessions ) == 0:
        logger.error( 'CRITICAL ERROR: No species found in manifest' )
        sys.exit( 1 )

    # Create output directories
    output_t1_directory = output_directory / 'T1_proteomes'
    output_genome_directory = output_directory / 'genomes'
    output_annotation_directory = output_directory / 'gene_annotations'
    output_maps_directory = output_directory / 'maps'

    output_t1_directory.mkdir( parents = True, exist_ok = True )
    output_genome_directory.mkdir( parents = True, exist_ok = True )
    output_annotation_directory.mkdir( parents = True, exist_ok = True )
    output_maps_directory.mkdir( parents = True, exist_ok = True )

    # Process each species
    total_count = len( genus_species_names___accessions )
    success_count = 0
    failed_species = []
    all_species_results = []

    for index, genus_species in enumerate( sorted( genus_species_names___accessions.keys() ), 1 ):
        accession = genus_species_names___accessions[ genus_species ]
        source_genome_identifier = f'{SOURCE_PREFIX}_{accession}'

        # Build the new base filename
        new_basename = f'{genus_species}-genome-{source_genome_identifier}-{download_date}'

        # Find input files
        genome_file = input_genome_directory / f'{genus_species}-ncbi_genomes.fasta'
        gff3_file = input_gff3_directory / f'{genus_species}-ncbi_genomes.gff3'
        protein_file = input_protein_directory / f'{genus_species}-ncbi_genomes.faa'

        print( f'--------------------------------------------' )
        print( f'[{index}/{total_count}] {genus_species} ({accession})' )
        print( f'  New basename: {new_basename}' )
        print( f'--------------------------------------------' )

        # Validate input files
        missing_files = []
        for file_path, label in [
            ( genome_file, 'Genome FASTA' ),
            ( gff3_file, 'GFF3' ),
            ( protein_file, 'Protein FASTA' ),
        ]:
            if not file_path.exists():
                missing_files.append( ( file_path, label ) )

        if len( missing_files ) > 0:
            for file_path, label in missing_files:
                print( f'    ERROR: {label} not found: {file_path}' )
            failed_species.append( genus_species )
            print( '' )
            continue

        try:
            # ================================================================
            # Step 1: Extract T1 proteome
            # ================================================================
            t1_proteins, statistics = extract_t1_proteome( gff3_file, protein_file, genus_species )

            print( f'    Genes in GFF3:        {statistics[ "total_genes" ]}' )
            print( f'    Proteins in FASTA:    {statistics[ "total_proteins_in_fasta" ]}' )
            print( f'    Single-isoform genes: {statistics[ "single_isoform_genes" ]}' )
            print( f'    Multi-isoform genes:  {statistics[ "multiple_isoform_genes" ]}' )
            print( f'    T1 proteins:          {statistics[ "t1_proteins_extracted" ]}' )
            print( f'    Orphan proteins:      {statistics[ "orphan_proteins" ]}' )

            if statistics[ 't1_proteins_extracted' ] == 0:
                print( f'    CRITICAL: No T1 proteins extracted for {genus_species}!' )
                failed_species.append( genus_species )
                print( '' )
                continue

            # Count dash changes
            changed_gene_count = sum(
                1 for entry in t1_proteins
                if entry[ 'original_gene_identifier' ] != entry[ 'updated_gene_identifier' ]
            )
            changed_transcript_count = sum(
                1 for entry in t1_proteins
                if entry[ 'original_transcript_identifier' ] != entry[ 'updated_transcript_identifier' ]
            )
            changed_protein_count = sum(
                1 for entry in t1_proteins
                if entry[ 'original_protein_identifier' ] != entry[ 'updated_protein_identifier' ]
            )

            print( f'    Gene IDs with dashes:       {changed_gene_count}' )
            print( f'    Transcript IDs with dashes:  {changed_transcript_count}' )
            print( f'    Protein IDs with dashes:     {changed_protein_count}' )

            # ================================================================
            # Step 2: Write T1 proteome with new header format
            # ================================================================
            output_proteome_path = output_t1_directory / f'{new_basename}.aa'
            write_proteome_fasta( t1_proteins, genus_species, output_proteome_path )
            print( f'    T1 proteome: {output_proteome_path.name}' )

            # ================================================================
            # Step 3: Copy genome FASTA with new name (content unchanged)
            # ================================================================
            output_genome_path = output_genome_directory / f'{new_basename}.fasta'
            shutil.copy2( genome_file, output_genome_path )
            print( f'    Genome:      {output_genome_path.name}' )

            # ================================================================
            # Step 4: Copy GFF3 with new name (content unchanged)
            # ================================================================
            output_gff3_path = output_annotation_directory / f'{new_basename}.gff3'
            shutil.copy2( gff3_file, output_gff3_path )
            print( f'    GFF3:        {output_gff3_path.name}' )

            # ================================================================
            # Step 5: Collect genome identifiers for mapping
            # ================================================================
            genome_identifiers = parse_genome_fasta_identifiers( genome_file )
            print( f'    Scaffolds:   {len( genome_identifiers )}' )

            # Store results
            all_species_results.append( {
                'genus_species': genus_species,
                'accession': accession,
                'source_genome_identifier': source_genome_identifier,
                't1_proteins': t1_proteins,
                'genome_identifiers': genome_identifiers,
                'statistics': statistics,
                'changed_gene_count': changed_gene_count,
                'changed_transcript_count': changed_transcript_count,
                'changed_protein_count': changed_protein_count,
            } )

            success_count += 1

        except Exception as error:
            print( f'    ERROR: Failed to process {genus_species}: {error}' )
            import traceback
            traceback.print_exc()
            failed_species.append( genus_species )

        print( '' )

    # ========================================================================
    # Write mapping files
    # ========================================================================
    print( '============================================' )
    print( 'Writing identifier mapping files' )
    print( '============================================' )

    genome_map_path = output_maps_directory / 'ncbi_genomes-map-genome_identifiers.tsv'
    genome_map_count = write_genome_identifier_map( all_species_results, genome_map_path )

    sequence_map_path = output_maps_directory / 'ncbi_genomes-map-sequence_identifiers.tsv'
    sequence_map_count = write_sequence_identifier_map( all_species_results, sequence_map_path )

    # ========================================================================
    # Final summary
    # ========================================================================
    print( '' )
    print( '============================================' )
    print( 'T1 extraction + genomesDB reformat complete' )
    print( '============================================' )
    print( '' )
    print( f'Species processed: {total_count}' )
    print( f'Successful:        {success_count}' )
    print( f'Failed:            {len( failed_species )}' )
    print( '' )

    if len( failed_species ) > 0:
        print( f'Failed species:' )
        for species in failed_species:
            print( f'  - {species}' )
        print( '' )
        print( 'ERROR: Some species failed T1 extraction.' )
        sys.exit( 1 )

    print( f'{"Species":<35} {"T1 Prots":>10} {"Gene Chg":>10} {"Tx Chg":>8} {"Prot Chg":>10}' )
    print( '-' * 80 )

    for species_result in all_species_results:
        print(
            f'{species_result[ "genus_species" ]:<35} '
            f'{species_result[ "statistics" ][ "t1_proteins_extracted" ]:>10} '
            f'{species_result[ "changed_gene_count" ]:>10} '
            f'{species_result[ "changed_transcript_count" ]:>8} '
            f'{species_result[ "changed_protein_count" ]:>10}'
        )

    print( '-' * 80 )
    total_t1 = sum( r[ 'statistics' ][ 't1_proteins_extracted' ] for r in all_species_results )
    total_gene_chg = sum( r[ 'changed_gene_count' ] for r in all_species_results )
    total_tx_chg = sum( r[ 'changed_transcript_count' ] for r in all_species_results )
    total_prot_chg = sum( r[ 'changed_protein_count' ] for r in all_species_results )
    print(
        f'{"TOTAL":<35} '
        f'{total_t1:>10} '
        f'{total_gene_chg:>10} '
        f'{total_tx_chg:>8} '
        f'{total_prot_chg:>10}'
    )
    print( '' )

    print( f'Output directories:' )
    print( f'  T1 proteomes:     {output_t1_directory}/' )
    print( f'  Genomes:          {output_genome_directory}/' )
    print( f'  Gene annotations: {output_annotation_directory}/' )
    print( f'  Maps:             {output_maps_directory}/' )
    print( f'    Genome map:     {genome_map_count} entries' )
    print( f'    Sequence map:   {sequence_map_count} entries' )
    print( '' )
    print( 'Done!' )


if __name__ == '__main__':
    main()
