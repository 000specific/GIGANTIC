# AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: Build aggregated gene symbol sets for each HGNC gene group
# Human: Eric Edsinger

"""
Build aggregated gene symbol sets for each HGNC gene group.

For each gene group, collects:
  - Direct gene members (from gene_has_family.csv via hgnc_gene_groups_all.tsv)
  - All descendant gene members (from hierarchy_closure.csv)

Aggregation rule: If group A contains subgroups B and C plus its own direct
genes, group A's gene set = B's genes + C's genes + A's direct genes.

Uses the bulk TSV (hgnc_gene_groups_all.tsv) to map HGNC gene IDs to
approved gene symbols (which match the GIGANTIC human proteome g_ field).

Usage:
    python3 002_ai-python-build_aggregated_gene_sets.py \
        --input-directory <path-to-downloaded-hgnc-data> \
        --output-directory <path>

Output:
    <output-directory>/2_ai-aggregated_gene_sets.tsv
    <output-directory>/2_ai-gene_group_metadata.tsv
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging( log_file_path ):
    """Configure logging to both file and console."""

    logger = logging.getLogger( 'build_gene_sets' )
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


def load_family_metadata( family_csv_path, logger ):
    """
    Load gene group metadata from family.csv.

    Returns:
        dict: family_id (int) -> { 'name': str, 'abbreviation': str, 'typical_gene': str }
    """

    family_identifiers___metadata = {}

    # "id","abbreviation","name","external_note","pubmed_ids","desc_comment","desc_label","desc_source","desc_go","typical_gene"
    # "3","FSCN","Fascin family","NULL","21618240","Fascins are actin-binding...","NULL","Hashimoto et al...","NULL","FSCN1"
    with open( family_csv_path, 'r' ) as input_family:
        reader = csv.DictReader( input_family )
        for row in reader:
            family_id = int( row[ 'id' ] )
            family_identifiers___metadata[ family_id ] = {
                'name': row[ 'name' ],
                'abbreviation': row[ 'abbreviation' ] if row[ 'abbreviation' ] != 'NULL' else '',
                'typical_gene': row[ 'typical_gene' ] if row[ 'typical_gene' ] != 'NULL' else '',
            }

    logger.info( f"Loaded {len( family_identifiers___metadata )} gene groups from family.csv" )
    return family_identifiers___metadata


def load_hierarchy_closure( hierarchy_closure_csv_path, logger ):
    """
    Load the full hierarchy closure table.

    Returns:
        dict: parent_family_id (int) -> set of descendant family_ids (int)
              (only descendants with distance > 0, i.e., not self)
    """

    parent_identifiers___descendant_identifiers = {}

    # "parent_fam_id","child_fam_id","distance"
    # "2333","2333","0"
    with open( hierarchy_closure_csv_path, 'r' ) as input_hierarchy_closure:
        reader = csv.DictReader( input_hierarchy_closure )
        for row in reader:
            distance = int( row[ 'distance' ] )
            if distance == 0:
                continue

            parent_id = int( row[ 'parent_fam_id' ] )
            child_id = int( row[ 'child_fam_id' ] )

            if parent_id not in parent_identifiers___descendant_identifiers:
                parent_identifiers___descendant_identifiers[ parent_id ] = set()
            parent_identifiers___descendant_identifiers[ parent_id ].add( child_id )

    logger.info( f"Loaded hierarchy closure: {len( parent_identifiers___descendant_identifiers )} groups have descendants" )
    return parent_identifiers___descendant_identifiers


def load_direct_gene_symbols( hgnc_bulk_tsv_path, logger ):
    """
    Load direct gene symbol assignments per family from the bulk TSV.

    The bulk TSV has one row per gene-group assignment, with gene symbols.
    Includes genes with these HGNC locus types that encode proteins:
        - 'gene with protein product' (standard protein-coding genes)
        - 'complex locus constituent' (e.g., clustered protocadherins PCDHA/B/G,
          UDP glucuronosyltransferases, paralemmins - these are protein-coding
          genes within complex genomic loci)

    Excludes non-protein-coding types: pseudogenes, RNA genes, immunoglobulin
    gene segments (V/D/J - require somatic recombination), T cell receptor gene
    segments, endogenous retroviruses, etc.

    Returns:
        dict: family_id (int) -> set of gene_symbols (str)
    """

    protein_coding_locus_types = {
        'gene with protein product',
        'complex locus constituent',
    }

    family_identifiers___gene_symbols = {}
    total_assignments = 0
    skipped_non_protein_coding = 0

    # HGNC ID	Approved symbol	Approved name	Status	Locus type	Previous symbols	Alias symbols	Chromosome	NCBI Gene ID	Ensembl gene ID	Vega gene ID	Group ID	Group name
    # HGNC:324	AGPAT1	1-acylglycerol-3-phosphate O-acyltransferase 1	Approved	gene with protein product		LPAAT-alpha, LPLAT1	6p21.32	10554	ENSG00000204310	OTTHUMG00000031210	46	1-acylglycerol-3-phosphate O-acyltransferases
    with open( hgnc_bulk_tsv_path, 'r' ) as input_bulk:
        reader = csv.DictReader( input_bulk, delimiter='\t' )
        for row in reader:
            locus_type = row[ 'Locus type' ]
            if locus_type not in protein_coding_locus_types:
                skipped_non_protein_coding += 1
                continue

            family_id = int( row[ 'Group ID' ] )
            gene_symbol = row[ 'Approved symbol' ]

            if family_id not in family_identifiers___gene_symbols:
                family_identifiers___gene_symbols[ family_id ] = set()
            family_identifiers___gene_symbols[ family_id ].add( gene_symbol )
            total_assignments += 1

    logger.info( f"Loaded {total_assignments} protein-coding gene-to-group assignments" )
    logger.info( f"  Skipped {skipped_non_protein_coding} non-protein-coding assignments" )
    logger.info( f"  Protein-coding locus types included: {sorted( protein_coding_locus_types )}" )
    logger.info( f"  Groups with protein-coding genes: {len( family_identifiers___gene_symbols )}" )
    return family_identifiers___gene_symbols


def build_aggregated_gene_sets( family_identifiers___metadata, parent_identifiers___descendant_identifiers, family_identifiers___gene_symbols, logger ):
    """
    Build aggregated gene symbol sets for every gene group.

    For a group with descendants: aggregate all descendant genes + own direct genes.
    For a leaf group: just its own direct genes.

    Returns:
        dict: family_id (int) -> set of gene_symbols (str)
    """

    family_identifiers___aggregated_gene_symbols = {}

    for family_id in family_identifiers___metadata:

        # Start with direct gene members
        aggregated_symbols = set()
        direct_symbols = family_identifiers___gene_symbols.get( family_id, set() )
        aggregated_symbols.update( direct_symbols )

        # Add genes from all descendants
        descendant_ids = parent_identifiers___descendant_identifiers.get( family_id, set() )
        for descendant_id in descendant_ids:
            descendant_symbols = family_identifiers___gene_symbols.get( descendant_id, set() )
            aggregated_symbols.update( descendant_symbols )

        family_identifiers___aggregated_gene_symbols[ family_id ] = aggregated_symbols

    # Count statistics
    groups_with_genes = sum( 1 for symbols in family_identifiers___aggregated_gene_symbols.values() if len( symbols ) > 0 )
    groups_without_genes = sum( 1 for symbols in family_identifiers___aggregated_gene_symbols.values() if len( symbols ) == 0 )
    total_unique_symbols = set()
    for symbols in family_identifiers___aggregated_gene_symbols.values():
        total_unique_symbols.update( symbols )

    logger.info( f"Built aggregated gene sets for {len( family_identifiers___aggregated_gene_symbols )} groups" )
    logger.info( f"  Groups with genes (after aggregation): {groups_with_genes}" )
    logger.info( f"  Groups still empty (after aggregation): {groups_without_genes}" )
    logger.info( f"  Total unique gene symbols across all groups: {len( total_unique_symbols )}" )

    return family_identifiers___aggregated_gene_symbols


def sanitize_family_name( family_name ):
    """
    Convert a family name to a filesystem-safe string.

    Replaces spaces and special characters with underscores, converts to lowercase.
    """

    sanitized = family_name.lower()
    sanitized = sanitized.replace( ' ', '_' )
    sanitized = sanitized.replace( ',', '' )
    sanitized = sanitized.replace( '(', '' )
    sanitized = sanitized.replace( ')', '' )
    sanitized = sanitized.replace( '/', '_' )
    sanitized = sanitized.replace( "'", '' )
    sanitized = sanitized.replace( '"', '' )
    sanitized = sanitized.replace( ':', '' )
    sanitized = sanitized.replace( '-', '_' )
    sanitized = sanitized.replace( '.', '_' )

    # Collapse multiple underscores
    while '__' in sanitized:
        sanitized = sanitized.replace( '__', '_' )

    # Remove leading/trailing underscores
    sanitized = sanitized.strip( '_' )

    return sanitized


def main():
    parser = argparse.ArgumentParser( description='Build aggregated gene symbol sets for HGNC gene groups' )
    parser.add_argument( '--input-directory', required=True, help='Directory containing downloaded HGNC data' )
    parser.add_argument( '--output-directory', required=True, help='Directory to write output files' )
    parser.add_argument( '--log-file', default=None, help='Path to log file' )
    arguments = parser.parse_args()

    input_directory = Path( arguments.input_directory )
    output_directory = Path( arguments.output_directory )
    output_directory.mkdir( parents=True, exist_ok=True )

    # Setup logging
    if arguments.log_file:
        log_file_path = Path( arguments.log_file )
    else:
        log_file_path = output_directory / '2_ai-log-build_aggregated_gene_sets.log'
    log_file_path.parent.mkdir( parents=True, exist_ok=True )
    logger = setup_logging( log_file_path )

    logger.info( "=" * 70 )
    logger.info( "Build Aggregated Gene Sets for HGNC Gene Groups" )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Input directory: {input_directory}" )
    logger.info( f"Output directory: {output_directory}" )
    logger.info( "=" * 70 )

    # Validate input files exist
    required_files = [ 'family.csv', 'hierarchy_closure.csv', 'hgnc_gene_groups_all.tsv' ]
    for filename in required_files:
        filepath = input_directory / filename
        if not filepath.exists():
            logger.error( f"CRITICAL ERROR: Required file not found: {filepath}" )
            logger.error( "Run script 001 (download HGNC data) first." )
            sys.exit( 1 )

    # Load data
    family_identifiers___metadata = load_family_metadata( input_directory / 'family.csv', logger )
    parent_identifiers___descendant_identifiers = load_hierarchy_closure( input_directory / 'hierarchy_closure.csv', logger )
    family_identifiers___gene_symbols = load_direct_gene_symbols( input_directory / 'hgnc_gene_groups_all.tsv', logger )

    # Build aggregated gene sets
    family_identifiers___aggregated_gene_symbols = build_aggregated_gene_sets(
        family_identifiers___metadata,
        parent_identifiers___descendant_identifiers,
        family_identifiers___gene_symbols,
        logger
    )

    # Write aggregated gene sets TSV
    aggregated_output_path = output_directory / '2_ai-aggregated_gene_sets.tsv'
    with open( aggregated_output_path, 'w' ) as output_aggregated:
        output = 'Gene_Group_ID (HGNC family ID with gg prefix)' + '\t'
        output += 'Gene_Group_Name (HGNC family name)' + '\t'
        output += 'Sanitized_Name (filesystem safe lowercase name)' + '\t'
        output += 'Direct_Gene_Count (genes directly assigned to this group)' + '\t'
        output += 'Aggregated_Gene_Count (total genes including all descendant groups)' + '\t'
        output += 'Gene_Symbols (comma delimited list of approved gene symbols)' + '\n'
        output_aggregated.write( output )

        for family_id in sorted( family_identifiers___metadata.keys() ):
            metadata = family_identifiers___metadata[ family_id ]
            aggregated_symbols = family_identifiers___aggregated_gene_symbols[ family_id ]
            direct_symbols = family_identifiers___gene_symbols.get( family_id, set() )
            sanitized_name = sanitize_family_name( metadata[ 'name' ] )

            if len( aggregated_symbols ) == 0:
                continue

            sorted_symbols = sorted( aggregated_symbols )

            output = f"gg{family_id}" + '\t'
            output += metadata[ 'name' ] + '\t'
            output += sanitized_name + '\t'
            output += str( len( direct_symbols ) ) + '\t'
            output += str( len( aggregated_symbols ) ) + '\t'
            output += ','.join( sorted_symbols ) + '\n'
            output_aggregated.write( output )

    logger.info( f"Wrote aggregated gene sets: {aggregated_output_path}" )

    # Write gene group metadata TSV (all groups including empty ones)
    metadata_output_path = output_directory / '2_ai-gene_group_metadata.tsv'
    with open( metadata_output_path, 'w' ) as output_metadata:
        output = 'Gene_Group_ID (HGNC family ID with gg prefix)' + '\t'
        output += 'Gene_Group_Name (HGNC family name)' + '\t'
        output += 'Sanitized_Name (filesystem safe lowercase name)' + '\t'
        output += 'Abbreviation (HGNC abbreviation if available)' + '\t'
        output += 'Typical_Gene (representative gene symbol)' + '\t'
        output += 'Direct_Gene_Count (genes directly assigned to this group)' + '\t'
        output += 'Aggregated_Gene_Count (total genes including all descendant groups)' + '\t'
        output += 'Has_Descendants (whether this group has subgroups)' + '\n'
        output_metadata.write( output )

        for family_id in sorted( family_identifiers___metadata.keys() ):
            metadata = family_identifiers___metadata[ family_id ]
            aggregated_symbols = family_identifiers___aggregated_gene_symbols[ family_id ]
            direct_symbols = family_identifiers___gene_symbols.get( family_id, set() )
            sanitized_name = sanitize_family_name( metadata[ 'name' ] )
            has_descendants = family_id in parent_identifiers___descendant_identifiers

            output = f"gg{family_id}" + '\t'
            output += metadata[ 'name' ] + '\t'
            output += sanitized_name + '\t'
            output += metadata[ 'abbreviation' ] + '\t'
            output += metadata[ 'typical_gene' ] + '\t'
            output += str( len( direct_symbols ) ) + '\t'
            output += str( len( aggregated_symbols ) ) + '\t'
            output += ( 'yes' if has_descendants else 'no' ) + '\n'
            output_metadata.write( output )

    logger.info( f"Wrote gene group metadata: {metadata_output_path}" )

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( f"Completed: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "=" * 70 )


if __name__ == '__main__':
    main()
