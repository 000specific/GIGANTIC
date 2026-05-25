# AI: Claude Code | Opus 4.6 | 2026 March 31 15:30 | Purpose: Generate RGS FASTA files from HGNC gene groups using human proteome
# Human: Eric Edsinger

"""
Generate RGS (Reference Gene Set) FASTA files from HGNC gene group data.

For each HGNC gene group with protein-coding genes, extracts the matching
protein sequences from the GIGANTIC human T1 proteome and writes one RGS
FASTA file per gene group.

RGS filename format (matches trees_gene_families convention):
    rgs_hugo_hgnc-human-{sanitized_group_name}.aa

    Example: rgs_hugo_hgnc-human-gap_junction_proteins.aa

    Compare with trees_gene_families filenames:
    rgs_channel-human-aquaporin_channels.aa
    rgs_ligand-human-wnt_ligands.aa

    Fields (dash-separated):
        rgs_hugo_hgnc          - RGS category identifier (source: HUGO HGNC)
        human                  - species common name
        {sanitized_group_name} - HGNC gene group name (filesystem safe)

RGS header format (matches trees_gene_families convention):
    >rgs_{sanitized_group_name}-human-{GENE_SYMBOL}-hgnc_gg{FAMILY_ID}_{Gene_Group_Name}-{PROTEIN_ID}

    Example: >rgs_gap_junction_proteins-human-GJA1-hgnc_gg2_Gap_junction_proteins-NP_000156_1

    Compare with trees_gene_families headers:
    >rgs_aquaporins-human-MIP-hgnc_gg305_Aquaporin-NP_036196_1
    >rgs_wnts-human-WNT1-hgnc_gg360_Wnt_family-NP_005421.1

    Fields (dash-separated):
        rgs_{name}                      - RGS identifier using the sanitized gene group name
        species                         - species common name (always "human" for STEP_0)
        GENE_SYMBOL                     - HGNC approved gene symbol
        hgnc_gg{ID}_{Gene_Group_Name}   - HGNC gene group family ID + name for traceability
        PROTEIN_ID                      - NCBI protein accession with dots replaced by underscores

Gene symbol matching:
    HGNC gene symbols may contain hyphens (e.g., HLA-A, H1-0, KRTAP1-1) but
    the GIGANTIC proteome uses '-' as the header field delimiter, so hyphens
    within gene symbols are stored as underscores (HLA_A, H1_0, KRTAP1_1).
    Some proteome entries also have numeric suffixes for allele/copy variants
    (e.g., HLA_A_6, CYP21A2_5). This script uses a 3-tier matching strategy:
        1. Exact match with HGNC symbol as-is
        2. Exact match after replacing hyphens with underscores
        3. Prefix match for symbols with allele/copy suffixes

Usage:
    python3 003_ai-python-generate_rgs_fasta_files.py \
        --input-gene-sets <path-to-2_ai-aggregated_gene_sets.tsv> \
        --input-proteome <path-to-human-T1-proteome.aa> \
        --output-directory <path>

Output:
    <output-directory>/rgs_fastas/rgs_hugo_hgnc-human-{name}.aa  (one per group)
    <output-directory>/3_ai-rgs_generation_manifest.tsv
    <output-directory>/3_ai-rgs_generation_summary.tsv
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging( log_file_path ):
    """Configure logging to both file and console."""

    logger = logging.getLogger( 'generate_rgs' )
    logger.setLevel( logging.INFO )

    file_handler = logging.FileHandler( log_file_path )
    file_handler.setLevel( logging.INFO )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


def load_human_proteome( proteome_path, logger ):
    """
    Load the GIGANTIC human T1 proteome and build a gene symbol to sequence map.

    GIGANTIC proteome header format:
        >g_GENE_SYMBOL-t_TRANSCRIPT-p_PROTEIN-n_PHYLONAME

    Note: The GIGANTIC proteome header format uses '-' as field delimiter, so
    hyphens within gene symbols (e.g., HLA-A, H1-0) are converted to underscores
    (HLA_A, H1_0). Some entries also have numeric suffixes for allele/copy variants
    (e.g., HLA_A_6, CYP21A2_5). This function builds lookup structures to handle
    both cases when matching HGNC gene symbols.

    Parameters:
        proteome_path (Path): Path to human T1 proteome .aa file
        logger: Logger instance

    Returns:
        dict: gene_symbols___sequences - gene symbol (str) -> sequence (str)
        dict: gene_symbols___protein_identifiers - gene symbol (str) -> protein accession (str)
    """

    gene_symbols___sequences = {}
    gene_symbols___protein_identifiers = {}
    current_gene_symbol = None
    current_protein_identifier = None
    current_sequence_parts = []
    duplicate_symbols = []

    # >g_A1BG-t_NM_130786.4-p_NP_570602.2-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
    # MSMLVVFLLLWGVTWGPVTEAAIFYETQPSLWAESESLLKPLANVTLTCQAHLETPDFQLFKNGVAQEPVHLDSPAIKHQ
    with open( proteome_path, 'r' ) as input_proteome:
        for line in input_proteome:
            line = line.strip()

            if line.startswith( '>' ):
                # Save previous sequence
                if current_gene_symbol is not None:
                    sequence = ''.join( current_sequence_parts )
                    if current_gene_symbol in gene_symbols___sequences:
                        duplicate_symbols.append( current_gene_symbol )
                    else:
                        gene_symbols___sequences[ current_gene_symbol ] = sequence
                        gene_symbols___protein_identifiers[ current_gene_symbol ] = current_protein_identifier

                # Parse new header
                # Format: g_GENE_SYMBOL-t_TRANSCRIPT-p_PROTEIN_ID-n_PHYLONAME
                header = line[ 1: ]
                parts_header = header.split( '-' )
                gene_symbol_field = parts_header[ 0 ]

                if gene_symbol_field.startswith( 'g_' ):
                    current_gene_symbol = gene_symbol_field[ 2: ]
                else:
                    current_gene_symbol = gene_symbol_field
                    logger.warning( f"Header does not start with g_ prefix: {header}" )

                # Extract protein accession from p_ field
                current_protein_identifier = ''
                for field in parts_header:
                    if field.startswith( 'p_' ):
                        current_protein_identifier = field[ 2: ]
                        break

                current_sequence_parts = []

            elif line:
                current_sequence_parts.append( line )

    # Save last sequence
    if current_gene_symbol is not None:
        sequence = ''.join( current_sequence_parts )
        if current_gene_symbol not in gene_symbols___sequences:
            gene_symbols___sequences[ current_gene_symbol ] = sequence
            gene_symbols___protein_identifiers[ current_gene_symbol ] = current_protein_identifier

    logger.info( f"Loaded human proteome: {len( gene_symbols___sequences )} gene symbols" )
    if duplicate_symbols:
        logger.warning( f"  Skipped {len( duplicate_symbols )} duplicate gene symbols (kept first occurrence)" )

    return gene_symbols___sequences, gene_symbols___protein_identifiers


def find_proteome_match( hgnc_gene_symbol, gene_symbols___sequences ):
    """
    Find a matching proteome entry for an HGNC gene symbol, handling the
    hyphen-to-underscore conversion used in GIGANTIC proteome headers.

    The GIGANTIC proteome header format uses '-' as field delimiter, so hyphens
    within HGNC gene symbols (e.g., HLA-A, H1-0, KRTAP1-1) are stored as
    underscores (HLA_A, H1_0, KRTAP1_1). Additionally, some proteome entries
    have numeric suffixes for allele/copy variants (e.g., HLA_A_6, CYP21A2_5).

    Matching strategy (in order):
        1. Exact match with HGNC symbol as-is
        2. Exact match after replacing hyphens with underscores
        3. Prefix match after replacing hyphens with underscores
           (for symbols with allele/copy suffixes like HLA_A -> HLA_A_6)
           Picks the first match alphabetically.

    Parameters:
        hgnc_gene_symbol (str): Gene symbol from HGNC (may contain hyphens)
        gene_symbols___sequences (dict): Proteome gene symbol -> sequence

    Returns:
        str or None: The matching proteome gene symbol, or None if no match
    """

    # Strategy 1: Exact match with HGNC symbol as-is
    if hgnc_gene_symbol in gene_symbols___sequences:
        return hgnc_gene_symbol

    # Strategy 2: Exact match after replacing hyphens with underscores
    underscore_symbol = hgnc_gene_symbol.replace( '-', '_' )
    if underscore_symbol in gene_symbols___sequences:
        return underscore_symbol

    # Strategy 3: Prefix match for symbols with allele/copy suffixes
    # e.g., HLA_A matches HLA_A_6; KRTAP1_1 matches KRTAP1_1_2
    prefix = underscore_symbol + '_'
    prefix_matches = sorted( [
        proteome_symbol for proteome_symbol in gene_symbols___sequences
        if proteome_symbol.startswith( prefix )
    ] )

    if prefix_matches:
        return prefix_matches[ 0 ]

    return None


def load_aggregated_gene_sets( gene_sets_path, logger ):
    """
    Load aggregated gene sets from script 002 output.

    Returns:
        list of dict: Each dict has keys:
            gene_group_id, gene_group_name, sanitized_name,
            direct_gene_count, aggregated_gene_count, gene_symbols
    """

    gene_groups = []

    # Gene_Group_ID (HGNC family ID with gg prefix)	Gene_Group_Name (HGNC family name)	Sanitized_Name (filesystem safe lowercase name)	Direct_Gene_Count (genes directly assigned to this group)	Aggregated_Gene_Count (total genes including all descendant groups)	Gene_Symbols (comma delimited list of approved gene symbols)
    # gg2	Gap junction proteins	gap_junction_proteins	21	21	GJA1,GJA10,GJA3,...
    with open( gene_sets_path, 'r' ) as input_gene_sets:
        header_line = input_gene_sets.readline()

        for line in input_gene_sets:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            gene_group_id = parts[ 0 ]
            gene_group_name = parts[ 1 ]
            sanitized_name = parts[ 2 ]
            direct_gene_count = int( parts[ 3 ] )
            aggregated_gene_count = int( parts[ 4 ] )
            gene_symbols_string = parts[ 5 ]

            gene_symbols = gene_symbols_string.split( ',' )

            gene_groups.append( {
                'gene_group_id': gene_group_id,
                'gene_group_name': gene_group_name,
                'sanitized_name': sanitized_name,
                'direct_gene_count': direct_gene_count,
                'aggregated_gene_count': aggregated_gene_count,
                'gene_symbols': gene_symbols,
            } )

    logger.info( f"Loaded {len( gene_groups )} gene groups from aggregated gene sets" )
    return gene_groups


def write_rgs_fasta( gene_group, gene_symbols___sequences, gene_symbols___protein_identifiers, output_directory, logger ):
    """
    Write an RGS FASTA file for a single gene group.

    Filename format (matches trees_gene_families convention):
        rgs_hugo_hgnc-human-{sanitized_name}.aa
        Example: rgs_hugo_hgnc-human-gap_junction_proteins.aa

    Header format (matches trees_gene_families convention):
        >rgs_{sanitized_name}-human-{GENE_SYMBOL}-hgnc_gg{ID}_{Gene_Group_Name}-{PROTEIN_ID}
        Example: >rgs_gap_junction_proteins-human-GJA1-hgnc_gg2_Gap_junction_proteins-NP_000156_1

    Parameters:
        gene_group (dict): Gene group data from load_aggregated_gene_sets
        gene_symbols___sequences (dict): Proteome gene symbol -> sequence
        gene_symbols___protein_identifiers (dict): Proteome gene symbol -> protein accession
        output_directory (Path): Base output directory for rgs_fastas
        logger: Logger instance

    Returns:
        dict: Result with keys: gene_group_id, sanitized_name, output_path,
              matched_count, missing_count, missing_symbols, status
    """

    sanitized_name = gene_group[ 'sanitized_name' ]
    gene_group_id = gene_group[ 'gene_group_id' ]

    # Find matching sequences in proteome
    # Uses find_proteome_match to handle hyphen-to-underscore conversion and
    # allele/copy suffix matching in GIGANTIC proteome headers
    matched_symbols = []
    missing_symbols = []
    hgnc_symbols___proteome_symbols = {}

    for gene_symbol in gene_group[ 'gene_symbols' ]:
        proteome_symbol = find_proteome_match( gene_symbol, gene_symbols___sequences )
        if proteome_symbol is not None:
            matched_symbols.append( gene_symbol )
            hgnc_symbols___proteome_symbols[ gene_symbol ] = proteome_symbol
        else:
            missing_symbols.append( gene_symbol )

    matched_count = len( matched_symbols )

    if matched_count == 0:
        return {
            'gene_group_id': gene_group_id,
            'gene_group_name': gene_group[ 'gene_group_name' ],
            'sanitized_name': sanitized_name,
            'output_path': '',
            'matched_count': 0,
            'missing_count': len( missing_symbols ),
            'missing_symbols': ','.join( sorted( missing_symbols ) ),
            'status': 'SKIPPED_NO_MATCHES',
        }

    # Create flat rgs_fastas directory (no per-group subdirectories)
    rgs_fastas_directory = output_directory / 'rgs_fastas'
    rgs_fastas_directory.mkdir( parents=True, exist_ok=True )

    # Build filename: rgs_hugo_hgnc-human-{sanitized_name}.aa
    # Example: rgs_hugo_hgnc-human-gap_junction_proteins.aa
    rgs_filename = f"rgs_hugo_hgnc-human-{sanitized_name}.aa"
    output_path = rgs_fastas_directory / rgs_filename

    # Write FASTA
    # Header: >rgs_{name}-human-{GENE_SYMBOL}-hgnc_gg{ID}_{Gene_Group_Name}-{PROTEIN_ID}
    # Example: >rgs_gap_junction_proteins-human-GJA1-hgnc_gg2_Gap_junction_proteins-NP_000156_1
    # Matches trees_gene_families convention:
    #   >rgs_aquaporins-human-MIP-hgnc_gg305_Aquaporin-NP_036196_1

    # Sanitize gene group name for header field 4: replace spaces with underscores,
    # remove special characters (only letters, numbers, underscores allowed within fields)
    gene_group_name_sanitized_for_header = gene_group[ 'gene_group_name' ].replace( ' ', '_' )
    gene_group_name_sanitized_for_header = ''.join(
        character for character in gene_group_name_sanitized_for_header
        if character.isalnum() or character == '_'
    )

    with open( output_path, 'w' ) as output_fasta:
        for gene_symbol in sorted( matched_symbols ):
            proteome_symbol = hgnc_symbols___proteome_symbols[ gene_symbol ]
            sequence = gene_symbols___sequences[ proteome_symbol ]
            protein_identifier = gene_symbols___protein_identifiers[ proteome_symbol ]

            # Replace dots with underscores in protein identifier
            # (matches trees_gene_families convention: NP_036196_1 not NP_036196.1)
            protein_identifier_sanitized = protein_identifier.replace( '.', '_' )

            output = f">rgs_{sanitized_name}-human-{gene_symbol}-hgnc_{gene_group_id}_{gene_group_name_sanitized_for_header}-{protein_identifier_sanitized}" + '\n'
            output_fasta.write( output )

            # Write sequence in 80-character lines
            for start_position in range( 0, len( sequence ), 80 ):
                output = sequence[ start_position : start_position + 80 ] + '\n'
                output_fasta.write( output )

    return {
        'gene_group_id': gene_group_id,
        'gene_group_name': gene_group[ 'gene_group_name' ],
        'sanitized_name': sanitized_name,
        'output_path': str( output_path ),
        'matched_count': matched_count,
        'missing_count': len( missing_symbols ),
        'missing_symbols': ','.join( sorted( missing_symbols ) ),
        'status': 'SUCCESS',
    }


def main():
    parser = argparse.ArgumentParser( description='Generate RGS FASTA files from HGNC gene groups' )
    parser.add_argument( '--input-gene-sets', required=True, help='Path to 2_ai-aggregated_gene_sets.tsv from script 002' )
    parser.add_argument( '--input-proteome', required=True, help='Path to human T1 proteome .aa file (GIGANTIC format)' )
    parser.add_argument( '--output-directory', required=True, help='Directory to write RGS FASTA files and manifests' )
    parser.add_argument( '--log-file', default=None, help='Path to log file' )
    arguments = parser.parse_args()

    input_gene_sets_path = Path( arguments.input_gene_sets )
    input_proteome_path = Path( arguments.input_proteome )
    output_directory = Path( arguments.output_directory )
    output_directory.mkdir( parents=True, exist_ok=True )

    # Setup logging
    if arguments.log_file:
        log_file_path = Path( arguments.log_file )
    else:
        log_file_path = output_directory / '3_ai-log-generate_rgs_fasta_files.log'
    log_file_path.parent.mkdir( parents=True, exist_ok=True )
    logger = setup_logging( log_file_path )

    logger.info( "=" * 70 )
    logger.info( "Generate RGS FASTA Files from HGNC Gene Groups" )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Input gene sets: {input_gene_sets_path}" )
    logger.info( f"Input proteome: {input_proteome_path}" )
    logger.info( f"Output directory: {output_directory}" )
    logger.info( "=" * 70 )

    # Validate inputs
    if not input_gene_sets_path.exists():
        logger.error( f"CRITICAL ERROR: Input gene sets file not found: {input_gene_sets_path}" )
        logger.error( "Run script 002 (build aggregated gene sets) first." )
        sys.exit( 1 )

    if not input_proteome_path.exists():
        logger.error( f"CRITICAL ERROR: Input proteome file not found: {input_proteome_path}" )
        logger.error( "Provide the path to the GIGANTIC human T1 proteome .aa file." )
        sys.exit( 1 )

    # Load data
    logger.info( "" )
    logger.info( "Loading human proteome..." )
    gene_symbols___sequences, gene_symbols___protein_identifiers = load_human_proteome( input_proteome_path, logger )

    logger.info( "" )
    logger.info( "Loading aggregated gene sets..." )
    gene_groups = load_aggregated_gene_sets( input_gene_sets_path, logger )

    # ---- Generate RGS FASTA files for all gene groups ----
    # For each gene group, find matching protein sequences in the human proteome
    # and write a single flat .aa file to rgs_fastas/
    logger.info( "" )
    logger.info( f"Generating RGS FASTA files for {len( gene_groups )} gene groups..." )

    generation_results = []
    success_count = 0
    skipped_no_match_count = 0
    exact_match_count = 0
    underscore_match_count = 0
    prefix_match_count = 0

    for gene_group in gene_groups:
        result = write_rgs_fasta(
            gene_group,
            gene_symbols___sequences,
            gene_symbols___protein_identifiers,
            output_directory,
            logger
        )

        if result[ 'status' ] == 'SUCCESS':
            success_count += 1
        elif result[ 'status' ] == 'SKIPPED_NO_MATCHES':
            skipped_no_match_count += 1

        generation_results.append( result )

    # ---- Count match strategy types for logging ----
    # Re-walks all gene symbols to tally how many used each of the 3 matching
    # strategies (exact, hyphen-to-underscore, prefix). This is for transparency
    # in the log - showing how many genes needed non-trivial matching.
    for gene_group in gene_groups:
        for gene_symbol in gene_group[ 'gene_symbols' ]:
            if gene_symbol in gene_symbols___sequences:
                exact_match_count += 1
            else:
                underscore_symbol = gene_symbol.replace( '-', '_' )
                if underscore_symbol in gene_symbols___sequences:
                    underscore_match_count += 1
                else:
                    prefix = underscore_symbol + '_'
                    prefix_matches = [ s for s in gene_symbols___sequences if s.startswith( prefix ) ]
                    if prefix_matches:
                        prefix_match_count += 1

    logger.info( "" )
    logger.info( f"RGS generation results:" )
    logger.info( f"  Successfully generated: {success_count}" )
    logger.info( f"  Skipped (no proteome matches): {skipped_no_match_count}" )
    logger.info( "" )
    logger.info( f"Gene symbol match strategy breakdown (individual genes):" )
    logger.info( f"  Exact match: {exact_match_count}" )
    logger.info( f"  Hyphen-to-underscore match: {underscore_match_count}" )
    logger.info( f"  Prefix match (allele/copy suffix): {prefix_match_count}" )

    # ---- Write generation manifest (all results including SKIPPED) ----
    # The manifest records every gene group's outcome: which genes matched,
    # which were missing, and why groups were skipped. Used for auditing.
    manifest_path = output_directory / '3_ai-rgs_generation_manifest.tsv'
    with open( manifest_path, 'w' ) as output_manifest:
        output = 'Gene_Group_ID (HGNC family ID with gg prefix)' + '\t'
        output += 'Gene_Group_Name (HGNC family name)' + '\t'
        output += 'Sanitized_Name (filesystem safe lowercase name)' + '\t'
        output += 'RGS_File_Path (path to generated RGS FASTA file)' + '\t'
        output += 'Matched_Gene_Count (genes found in human proteome)' + '\t'
        output += 'Missing_Gene_Count (genes not found in human proteome)' + '\t'
        output += 'Missing_Gene_Symbols (comma delimited list of missing gene symbols)' + '\t'
        output += 'Status (SUCCESS or SKIPPED with reason)' + '\n'
        output_manifest.write( output )

        for result in generation_results:
            output = result[ 'gene_group_id' ] + '\t'
            output += result[ 'gene_group_name' ] + '\t'
            output += result[ 'sanitized_name' ] + '\t'
            output += result[ 'output_path' ] + '\t'
            output += str( result[ 'matched_count' ] ) + '\t'
            output += str( result[ 'missing_count' ] ) + '\t'
            output += result[ 'missing_symbols' ] + '\t'
            output += result[ 'status' ] + '\n'
            output_manifest.write( output )

    logger.info( f"Wrote generation manifest: {manifest_path}" )

    # ---- Write summary (successful RGS files only) ----
    # The summary contains only successfully generated groups and serves as
    # the input manifest for downstream STEP_1 (validation) and STEP_2
    # (homolog discovery) workflows.
    summary_path = output_directory / '3_ai-rgs_generation_summary.tsv'
    with open( summary_path, 'w' ) as output_summary:
        output = 'Gene_Group_ID (HGNC family ID with gg prefix)' + '\t'
        output += 'Gene_Group_Name (HGNC family name)' + '\t'
        output += 'Sanitized_Name (filesystem safe lowercase name)' + '\t'
        output += 'RGS_Filename (name of the RGS FASTA file in rgs_fastas directory)' + '\t'
        output += 'Sequence_Count (number of protein sequences in RGS file)' + '\n'
        output_summary.write( output )

        for result in generation_results:
            if result[ 'status' ] != 'SUCCESS':
                continue

            rgs_path = Path( result[ 'output_path' ] )

            output = result[ 'gene_group_id' ] + '\t'
            output += result[ 'gene_group_name' ] + '\t'
            output += result[ 'sanitized_name' ] + '\t'
            output += rgs_path.name + '\t'
            output += str( result[ 'matched_count' ] ) + '\n'
            output_summary.write( output )

    logger.info( f"Wrote generation summary: {summary_path}" )

    # ---- Size distribution statistics ----
    # Log how many gene groups fall into each size bin (1, 2-5, 6-10, etc.)
    # to give a quick overview of the RGS file landscape.
    logger.info( "" )
    logger.info( "Size distribution of generated RGS files:" )
    successful_results = [ r for r in generation_results if r[ 'status' ] == 'SUCCESS' ]

    if successful_results:
        matched_counts = [ r[ 'matched_count' ] for r in successful_results ]
        matched_counts.sort()

        logger.info( f"  Total RGS files: {len( successful_results )}" )
        logger.info( f"  Min sequences: {min( matched_counts )}" )
        logger.info( f"  Max sequences: {max( matched_counts )}" )
        logger.info( f"  Median sequences: {matched_counts[ len( matched_counts ) // 2 ]}" )
        logger.info( f"  Mean sequences: {sum( matched_counts ) / len( matched_counts ):.1f}" )

        # Size bins
        size_bins = [
            ( 1, 1, '1' ),
            ( 2, 5, '2-5' ),
            ( 6, 10, '6-10' ),
            ( 11, 20, '11-20' ),
            ( 21, 50, '21-50' ),
            ( 51, 100, '51-100' ),
            ( 101, 200, '101-200' ),
            ( 201, 500, '201-500' ),
            ( 501, 1000, '501-1000' ),
            ( 1001, float( 'inf' ), '1001+' ),
        ]

        logger.info( "" )
        logger.info( "  Size distribution:" )
        for lower_bound, upper_bound, label in size_bins:
            count = sum( 1 for c in matched_counts if lower_bound <= c <= upper_bound )
            if count > 0:
                logger.info( f"    {label} sequences: {count} groups" )

    # Final summary
    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( f"Generated {success_count} RGS FASTA files in: {output_directory / 'rgs_fastas'}" )
    logger.info( f"Completed: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 70 )


if __name__ == '__main__':
    main()
