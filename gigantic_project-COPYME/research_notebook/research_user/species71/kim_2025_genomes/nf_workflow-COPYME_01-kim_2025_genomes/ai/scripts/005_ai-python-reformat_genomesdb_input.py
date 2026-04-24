#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 12 05:30 | Purpose: Reformat kim_2025 genome/GTF/proteome files for genomesDB STEP_1 input with standardized naming, dash-to-underscore ID replacement, and identifier mapping files
# Human: Eric Edsinger

"""
005_ai-python-reformat_genomesdb_input.py

Reformat Kim et al. 2025 genome, GTF, and T1 proteome files for input into
GIGANTIC genomesDB STEP_1.

Changes:
  1. File naming: genus_species-genome_kim_2025-downloaded_20260211.{fasta,gtf,aa}
  2. Proteome headers: >genus_species-source_gene_id-source_transcript_id-source_protein_id
     (dashes in source IDs replaced with underscores)
  3. GTF transcript_id values: dashes replaced with underscores (to match proteome headers)
  4. Two mapping TSV files:
     a. Genome identifier map: original -> updated scaffold/chromosome names
     b. Sequence identifier map: original -> updated gene/transcript/protein IDs

Usage:
    python3 005_ai-python-reformat_genomesdb_input.py \
        --genome-dir 2-output/genome \
        --annotation-dir 2-output/gene_annotation \
        --proteome-dir 3-output/T1_proteomes \
        --output-dir 5-output

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
# Configuration
# ============================================================================

DOWNLOAD_DATE = 'downloaded_20260211'
SOURCE_IDENTIFIER = 'kim_2025'

SPECIES_LIST = [
    'Capsaspora_owczarzaki',
    'Cladtertia_collaboinventa',
    'Ephydatia_muelleri',
    'Mnemiopsis_leidyi',
    'Salpingoeca_rosetta',
    'Sphaeroforma_arctica',
    'Trichoplax_adhaerens',
]


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


def parse_genome_fasta_identifiers( fasta_path ):
    """
    Extract all scaffold/chromosome identifiers from a genome FASTA file.

    Parameters:
        fasta_path (Path): Path to genome FASTA file

    Returns:
        list: List of scaffold/chromosome identifiers in order
    """

    identifiers = []

    # >Cowc_Chr01
    # ATCGATCG...
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            if line.startswith( '>' ):
                identifier = line[ 1: ].strip().split()[ 0 ]
                identifiers.append( identifier )

    return identifiers


def parse_gtf_gene_transcript_mapping( gtf_path ):
    """
    Parse a GTF file to extract gene_id -> [transcript_id] mapping.
    Only includes transcript features (not exon, CDS, etc.) to get unique mappings.

    Parameters:
        gtf_path (Path): Path to GTF annotation file

    Returns:
        dict: gene_id -> sorted list of transcript_ids
    """

    gene_identifiers___transcript_identifiers = defaultdict( set )

    # gene_id "Cowc_VH_COWC_07782"; transcript_id "Cowc_VH_COWC_07782.t1";
    with open( gtf_path, 'r' ) as input_gtf:
        for line in input_gtf:
            line = line.strip()
            if line.startswith( '#' ) or len( line ) == 0:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 9:
                continue

            feature_type = parts[ 2 ]
            if feature_type != 'transcript':
                continue

            attributes_string = parts[ 8 ]

            gene_id_match = re.search( r'gene_id "([^"]+)"', attributes_string )
            transcript_id_match = re.search( r'transcript_id "([^"]+)"', attributes_string )

            if gene_id_match and transcript_id_match:
                gene_identifier = gene_id_match.group( 1 )
                transcript_identifier = transcript_id_match.group( 1 )
                gene_identifiers___transcript_identifiers[ gene_identifier ].add( transcript_identifier )

    # Sort for reproducibility
    result = {}
    for gene_identifier in sorted( gene_identifiers___transcript_identifiers.keys() ):
        result[ gene_identifier ] = sorted( gene_identifiers___transcript_identifiers[ gene_identifier ] )

    return result


def parse_t1_proteome_headers( proteome_path ):
    """
    Parse existing T1 proteome headers to extract gene_id and transcript_id.

    Current format: >Genus_species_geneID_transcriptID
    This is ambiguous, so we reconstruct the mapping from GTF data instead.

    Parameters:
        proteome_path (Path): Path to T1 proteome file

    Returns:
        list: List of (full_header, sequence) tuples
    """

    entries = []
    current_header = None
    current_sequence_parts = []

    with open( proteome_path, 'r' ) as input_proteome:
        for line in input_proteome:
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


def reformat_gtf( input_gtf_path, output_gtf_path ):
    """
    Copy GTF file, replacing dashes with underscores in gene_id and transcript_id values.

    Parameters:
        input_gtf_path (Path): Path to input GTF
        output_gtf_path (Path): Path to output GTF

    Returns:
        int: Number of identifiers that were modified
    """

    modified_count = 0

    with open( input_gtf_path, 'r' ) as input_gtf, open( output_gtf_path, 'w' ) as output_gtf:
        for line in input_gtf:
            if line.startswith( '#' ) or line.strip() == '':
                output_gtf.write( line )
                continue

            # Replace dashes in gene_id values
            def replace_gene_id( match ):
                nonlocal modified_count
                original = match.group( 1 )
                updated = sanitize_identifier( original )
                if original != updated:
                    modified_count += 1
                return f'gene_id "{updated}"'

            def replace_transcript_id( match ):
                nonlocal modified_count
                original = match.group( 1 )
                updated = sanitize_identifier( original )
                if original != updated:
                    modified_count += 1
                return f'transcript_id "{updated}"'

            line = re.sub( r'gene_id "([^"]+)"', replace_gene_id, line )
            line = re.sub( r'transcript_id "([^"]+)"', replace_transcript_id, line )

            output_gtf.write( line )

    return modified_count


def process_species( genus_species, genome_path, gtf_path, proteome_path, output_directory ):
    """
    Process one species: reformat genome, GTF, and proteome files.

    Parameters:
        genus_species (str): Species name
        genome_path (Path): Path to genome FASTA
        gtf_path (Path): Path to GTF annotation
        proteome_path (Path): Path to T1 proteome
        output_directory (Path): Output directory

    Returns:
        dict with genome_identifiers, sequence_entries, and summary stats
    """

    logger.info( f'============================================' )
    logger.info( f'Processing: {genus_species}' )
    logger.info( f'============================================' )

    new_basename = f'{genus_species}-genome_{SOURCE_IDENTIFIER}-{DOWNLOAD_DATE}'

    # =========================================================================
    # Step 1: Copy genome FASTA with new name
    # =========================================================================
    output_genome_path = output_directory / f'{new_basename}.fasta'
    logger.info( f'  Step 1: Copying genome FASTA -> {output_genome_path.name}' )
    shutil.copy2( genome_path, output_genome_path )

    # Collect genome identifiers for the map
    genome_identifiers = parse_genome_fasta_identifiers( genome_path )
    logger.info( f'    Genome scaffolds/chromosomes: {len( genome_identifiers )}' )

    # =========================================================================
    # Step 2: Reformat GTF with new name and sanitized IDs
    # =========================================================================
    output_gtf_path = output_directory / f'{new_basename}.gtf'
    logger.info( f'  Step 2: Reformatting GTF -> {output_gtf_path.name}' )
    modified_count = reformat_gtf( gtf_path, output_gtf_path )
    logger.info( f'    GTF identifier modifications: {modified_count}' )

    # =========================================================================
    # Step 3: Parse GTF for gene->transcript mapping (from original GTF)
    # =========================================================================
    logger.info( f'  Step 3: Parsing GTF gene-transcript mapping...' )
    gene_identifiers___transcript_identifiers = parse_gtf_gene_transcript_mapping( gtf_path )
    total_gene_count = len( gene_identifiers___transcript_identifiers )
    logger.info( f'    Genes in GTF: {total_gene_count}' )

    # Build transcript_id -> gene_id reverse lookup
    transcript_identifiers___gene_identifiers = {}
    for gene_identifier in gene_identifiers___transcript_identifiers:
        for transcript_identifier in gene_identifiers___transcript_identifiers[ gene_identifier ]:
            transcript_identifiers___gene_identifiers[ transcript_identifier ] = gene_identifier

    # =========================================================================
    # Step 4: Reformat T1 proteome headers
    # =========================================================================
    logger.info( f'  Step 4: Reformatting T1 proteome headers...' )
    proteome_entries = parse_t1_proteome_headers( proteome_path )
    total_protein_count = len( proteome_entries )
    logger.info( f'    T1 proteins: {total_protein_count}' )

    # The current headers are: >Genus_species_geneID_transcriptID
    # We need to reconstruct gene_id and transcript_id from the GTF mapping
    # Strategy: for each protein, try to find the transcript_id in the GTF mapping

    # Build a lookup from the gffread output: transcript_id -> sequence
    # The gffread intermediate files used transcript_id as FASTA headers
    # The current T1 headers were built as f'>{genus_species}_{gene_id}_{transcript_id}'
    # We can reconstruct by finding which gene_id + transcript_id pair matches

    # Build set of all known (gene_id, transcript_id) pairs
    known_pairs = set()
    for gene_identifier in gene_identifiers___transcript_identifiers:
        for transcript_identifier in gene_identifiers___transcript_identifiers[ gene_identifier ]:
            known_pairs.add( ( gene_identifier, transcript_identifier ) )

    sequence_entries = []
    unmatched_count = 0

    for header, sequence in proteome_entries:
        # Current header: Genus_species_geneID_transcriptID
        # Strip the Genus_species_ prefix
        prefix = genus_species + '_'
        if header.startswith( prefix ):
            remainder = header[ len( prefix ): ]
        else:
            # Fallback: use full header
            remainder = header
            logger.warning( f'    Header does not start with {prefix}: {header}' )

        # Try to find the gene_id and transcript_id split point
        # The remainder is: geneID_transcriptID
        # We need to find where gene_id ends and transcript_id begins
        found = False
        original_gene_identifier = None
        original_transcript_identifier = None

        for gene_identifier, transcript_identifier in known_pairs:
            expected_remainder = f'{gene_identifier}_{transcript_identifier}'
            if remainder == expected_remainder:
                original_gene_identifier = gene_identifier
                original_transcript_identifier = transcript_identifier
                found = True
                break

        if not found:
            # Fallback: try splitting by known transcript_ids
            for transcript_identifier in transcript_identifiers___gene_identifiers:
                if remainder.endswith( '_' + transcript_identifier ):
                    original_gene_identifier = transcript_identifiers___gene_identifiers[ transcript_identifier ]
                    original_transcript_identifier = transcript_identifier
                    found = True
                    break

        if not found:
            unmatched_count += 1
            # Last resort: use remainder as both gene and transcript
            original_gene_identifier = remainder
            original_transcript_identifier = remainder
            logger.warning( f'    Could not match header to GTF: {header}' )

        # Sanitize identifiers (replace dashes with underscores)
        updated_gene_identifier = sanitize_identifier( original_gene_identifier )
        updated_transcript_identifier = sanitize_identifier( original_transcript_identifier )
        # protein_id = transcript_id (gffread derives proteins from transcripts)
        original_protein_identifier = original_transcript_identifier
        updated_protein_identifier = updated_transcript_identifier

        sequence_entries.append( {
            'original_gene_identifier': original_gene_identifier,
            'updated_gene_identifier': updated_gene_identifier,
            'original_transcript_identifier': original_transcript_identifier,
            'updated_transcript_identifier': updated_transcript_identifier,
            'original_protein_identifier': original_protein_identifier,
            'updated_protein_identifier': updated_protein_identifier,
            'sequence': sequence,
        } )

    if unmatched_count > 0:
        logger.warning( f'    Unmatched headers: {unmatched_count}' )

    # Write reformatted proteome
    output_proteome_path = output_directory / f'{new_basename}.aa'
    logger.info( f'  Step 5: Writing reformatted proteome -> {output_proteome_path.name}' )

    with open( output_proteome_path, 'w' ) as output_proteome:
        for entry in sequence_entries:
            header = (
                f'>{genus_species}'
                f'-{entry[ "updated_gene_identifier" ]}'
                f'-{entry[ "updated_transcript_identifier" ]}'
                f'-{entry[ "updated_protein_identifier" ]}'
            )
            output = header + '\n'
            output_proteome.write( output )

            sequence = entry[ 'sequence' ]
            for index in range( 0, len( sequence ), 80 ):
                output = sequence[ index:index + 80 ] + '\n'
                output_proteome.write( output )

    logger.info( f'    Proteins written: {len( sequence_entries )}' )

    # Count how many identifiers were actually changed
    changed_gene_count = sum(
        1 for entry in sequence_entries
        if entry[ 'original_gene_identifier' ] != entry[ 'updated_gene_identifier' ]
    )
    changed_transcript_count = sum(
        1 for entry in sequence_entries
        if entry[ 'original_transcript_identifier' ] != entry[ 'updated_transcript_identifier' ]
    )
    logger.info( f'    Gene IDs changed (dash->underscore): {changed_gene_count}' )
    logger.info( f'    Transcript/protein IDs changed (dash->underscore): {changed_transcript_count}' )

    return {
        'genus_species': genus_species,
        'genome_identifiers': genome_identifiers,
        'sequence_entries': sequence_entries,
        'total_proteins': total_protein_count,
        'changed_gene_count': changed_gene_count,
        'changed_transcript_count': changed_transcript_count,
        'unmatched_count': unmatched_count,
    }


def write_genome_identifier_map( all_species_results, output_path ):
    """
    Write the genome identifier mapping TSV file.

    Columns: Genus_Species (genus species name)
             original_genome_identifier (original scaffold or chromosome name from source)
             updated_genome_identifier (updated name with dashes replaced by underscores)

    Parameters:
        all_species_results (list): List of per-species result dicts
        output_path (Path): Output file path
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

    Columns: Genus_Species, original_gene_id, updated_gene_id,
             original_transcript_id, updated_transcript_id,
             original_protein_id, updated_protein_id

    Parameters:
        all_species_results (list): List of per-species result dicts
        output_path (Path): Output file path
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
        description = 'Reformat kim_2025 genome/GTF/proteome files for genomesDB STEP_1 input'
    )
    parser.add_argument( '--genome-dir', required = True,
                         help = 'Directory containing Genus_species-kim_2025.fasta genome files' )
    parser.add_argument( '--annotation-dir', required = True,
                         help = 'Directory containing Genus_species-kim_2025.gtf annotation files' )
    parser.add_argument( '--proteome-dir', required = True,
                         help = 'Directory containing Genus_species-kim_2025-T1_proteome.aa files' )
    parser.add_argument( '--output-dir', required = True,
                         help = 'Output directory for reformatted files and maps' )
    arguments = parser.parse_args()

    genome_directory = Path( arguments.genome_dir )
    annotation_directory = Path( arguments.annotation_dir )
    proteome_directory = Path( arguments.proteome_dir )
    output_directory = Path( arguments.output_dir )

    print( '============================================' )
    print( '005: Reformat for genomesDB STEP_1 input' )
    print( '============================================' )
    print( '' )

    # Validate input directories
    for directory, label in [
        ( genome_directory, 'Genome' ),
        ( annotation_directory, 'Annotation' ),
        ( proteome_directory, 'Proteome' ),
    ]:
        if not directory.exists():
            logger.error( f'CRITICAL ERROR: {label} directory not found: {directory}' )
            sys.exit( 1 )

    output_directory.mkdir( parents = True, exist_ok = True )

    logger.info( f'Genome directory:     {genome_directory}' )
    logger.info( f'Annotation directory: {annotation_directory}' )
    logger.info( f'Proteome directory:   {proteome_directory}' )
    logger.info( f'Output directory:     {output_directory}' )
    logger.info( f'Source identifier:    {SOURCE_IDENTIFIER}' )
    logger.info( f'Download date:        {DOWNLOAD_DATE}' )
    print( '' )

    # Process each species
    all_species_results = []

    for genus_species in sorted( SPECIES_LIST ):
        genome_path = genome_directory / f'{genus_species}-kim_2025.fasta'
        gtf_path = annotation_directory / f'{genus_species}-kim_2025.gtf'
        proteome_path = proteome_directory / f'{genus_species}-kim_2025-T1_proteome.aa'

        # Validate files exist
        for file_path, label in [
            ( genome_path, 'Genome FASTA' ),
            ( gtf_path, 'GTF' ),
            ( proteome_path, 'T1 proteome' ),
        ]:
            if not file_path.exists():
                logger.error( f'CRITICAL ERROR: {label} not found: {file_path}' )
                sys.exit( 1 )

        species_result = process_species(
            genus_species, genome_path, gtf_path, proteome_path, output_directory
        )
        all_species_results.append( species_result )
        print( '' )

    # =========================================================================
    # Write mapping files
    # =========================================================================
    logger.info( '============================================' )
    logger.info( 'Writing identifier mapping files' )
    logger.info( '============================================' )

    genome_map_path = output_directory / f'{SOURCE_IDENTIFIER}-map-genome_identifiers.tsv'
    genome_map_count = write_genome_identifier_map( all_species_results, genome_map_path )

    sequence_map_path = output_directory / f'{SOURCE_IDENTIFIER}-map-sequence_identifiers.tsv'
    sequence_map_count = write_sequence_identifier_map( all_species_results, sequence_map_path )

    # =========================================================================
    # Final summary
    # =========================================================================
    print( '' )
    print( '============================================' )
    print( 'Reformat complete' )
    print( '============================================' )
    print( '' )

    print( f'{"Species":<35} {"Proteins":>10} {"Gene Changes":>14} {"Tx Changes":>12} {"Unmatched":>10}' )
    print( '-' * 85 )

    for species_result in all_species_results:
        print(
            f'{species_result[ "genus_species" ]:<35} '
            f'{species_result[ "total_proteins" ]:>10} '
            f'{species_result[ "changed_gene_count" ]:>14} '
            f'{species_result[ "changed_transcript_count" ]:>12} '
            f'{species_result[ "unmatched_count" ]:>10}'
        )

    print( '-' * 85 )
    total_proteins = sum( r[ 'total_proteins' ] for r in all_species_results )
    total_gene_changes = sum( r[ 'changed_gene_count' ] for r in all_species_results )
    total_tx_changes = sum( r[ 'changed_transcript_count' ] for r in all_species_results )
    total_unmatched = sum( r[ 'unmatched_count' ] for r in all_species_results )
    print(
        f'{"TOTAL":<35} '
        f'{total_proteins:>10} '
        f'{total_gene_changes:>14} '
        f'{total_tx_changes:>12} '
        f'{total_unmatched:>10}'
    )
    print( '' )

    print( f'Output files in {output_directory}/:' )
    for genus_species in sorted( SPECIES_LIST ):
        new_basename = f'{genus_species}-genome_{SOURCE_IDENTIFIER}-{DOWNLOAD_DATE}'
        print( f'  {new_basename}.fasta' )
        print( f'  {new_basename}.gtf' )
        print( f'  {new_basename}.aa' )
    print( f'  {SOURCE_IDENTIFIER}-map-genome_identifiers.tsv ({genome_map_count} entries)' )
    print( f'  {SOURCE_IDENTIFIER}-map-sequence_identifiers.tsv ({sequence_map_count} entries)' )
    print( '' )

    if total_unmatched > 0:
        logger.error( f'WARNING: {total_unmatched} protein headers could not be matched to GTF entries' )
        sys.exit( 1 )

    print( 'Done!' )


if __name__ == '__main__':
    main()
