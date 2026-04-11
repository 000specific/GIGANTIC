# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Create annotation groups (annogroups) from annotation files and prepare inputs for OCL analysis
# Human: Eric Edsinger

"""
OCL Pipeline Script 001: Create Annotation Groups (Annogroups)

Creates annotation groups (annogroups) from per-species annotation files and
prepares all phylogenetic input data for Origin-Conservation-Loss analysis.

Annogroups are the annotation analog to orthogroups -- sets of proteins grouped
by their annotation pattern from a specific database. Each annogroup has a
simple ID (annogroup_{db}_N) with full details in a companion map.

Phase A: Load phylogenetic tree data (same as orthogroups_X_ocl Script 001)
Phase B: Load per-species annotation files from annotations_hmms
Phase C: Create annogroups for each requested subtype (single, combo, zero)
Phase D: Write annogroup map, per-subtype files, subtypes manifest, and tree data

The 3 annogroup subtypes (each a direct protein-level evaluation):
  single - proteins with exactly one annotation from this database
  combo  - proteins with identical multi-annotation architecture
  zero   - proteins with no annotations from this database (singletons)

Inputs from upstream subprojects:
  - trees_species: phylogenetic blocks, parent-child relationships, phylogenetic paths
  - annotations_hmms: per-species annotation files (7-column TSV)

Outputs (to 1-output/):
  - Phylogenetic blocks, parent-child table, phylogenetic paths, clade mappings
  - Annogroup map (lookup table linking IDs to full details)
  - Per-subtype annogroup files
  - Annogroup subtypes manifest

Usage:
    python 001_ai-python-create_annogroups.py --structure_id 001 --config ../../START_HERE-user_config.yaml --output_dir OUTPUT_pipeline
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import yaml


# ============================================================================
# COMMAND-LINE ARGUMENTS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description = 'OCL Pipeline Script 001: Create annotation groups (annogroups) from annotation files',
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--structure_id',
        type = str,
        required = True,
        help = 'Structure ID to process (e.g., "001", "002", ..., "105")'
    )

    parser.add_argument(
        '--config',
        type = str,
        required = True,
        help = 'Path to START_HERE-user_config.yaml'
    )

    parser.add_argument(
        '--output_dir',
        type = str,
        default = None,
        help = 'Base output directory (overrides config if provided)'
    )

    return parser.parse_args()


# ============================================================================
# CONFIGURATION
# ============================================================================

# Parse arguments
args = parse_arguments()

# Load configuration
config_path = Path( args.config )
if not config_path.exists():
    print( f"CRITICAL ERROR: Configuration file not found: {config_path}" )
    sys.exit( 1 )

with open( config_path, 'r' ) as config_file:
    config = yaml.safe_load( config_file )

# Format structure ID
TARGET_STRUCTURE = f"structure_{args.structure_id}"

# Species set and annotation database from config
SPECIES_SET_NAME = config[ 'species_set_name' ]
ANNOTATION_DATABASE = config[ 'annotation_database' ]
ANNOGROUP_SUBTYPES = config[ 'annogroup_subtypes' ]

# Resolve input paths relative to config file directory
config_directory = config_path.parent

input_trees_species_directory = config_directory / config[ 'inputs' ][ 'trees_species_dir' ]
input_annotations_directory = config_directory / config[ 'inputs' ][ 'annotations_dir' ]

# Input files from trees_species
input_phylogenetic_blocks_file = input_trees_species_directory / 'Species_Phylogenetic_Blocks'
input_parent_child_directory = input_trees_species_directory / 'Species_Parent_Child_Relationships'
input_phylogenetic_paths_directory = input_trees_species_directory / 'Species_Phylogenetic_Paths'

# Output directory
if args.output_dir:
    output_base_directory = Path( args.output_dir )
else:
    output_base_directory = config_directory / config[ 'output' ][ 'base_dir' ]

output_directory = output_base_directory / TARGET_STRUCTURE / '1-output'
output_directory.mkdir( parents = True, exist_ok = True )

# Output files - phylogenetic data
output_phylogenetic_blocks_file = output_directory / f'1_ai-phylogenetic_blocks-{TARGET_STRUCTURE}.tsv'
output_parent_child_file = output_directory / f'1_ai-parent_child_table-{TARGET_STRUCTURE}.tsv'
output_phylogenetic_paths_file = output_directory / f'1_ai-phylogenetic_paths-{TARGET_STRUCTURE}.tsv'
output_clade_mappings_file = output_directory / f'1_ai-clade_mappings-{TARGET_STRUCTURE}.tsv'

# Output files - annogroup data
output_annogroup_map_file = output_directory / '1_ai-annogroup_map.tsv'
output_subtypes_manifest_file = output_directory / '1_ai-annogroup_subtypes_manifest.tsv'

# Log directory
log_directory = output_base_directory / TARGET_STRUCTURE / 'logs'
log_directory.mkdir( parents = True, exist_ok = True )
log_file = log_directory / f'1_ai-log-create_annogroups-{TARGET_STRUCTURE}.log'


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s',
    handlers = [
        logging.FileHandler( log_file ),
        logging.StreamHandler( sys.stdout )
    ]
)
logger = logging.getLogger( __name__ )


# ============================================================================
# PHASE A: LOAD PHYLOGENETIC TREE DATA
# ============================================================================

# --- Section A1: Load Phylogenetic Blocks ---

def load_phylogenetic_blocks():
    """
    Load phylogenetic blocks for the target structure from trees_species.

    Returns:
        dict: { clade_id: { 'clade_name': str, 'parent_id': str, 'structure_id': str } }
    """
    logger.info( f"Loading phylogenetic blocks from: {input_phylogenetic_blocks_file}" )

    phylogenetic_blocks_files = list( input_phylogenetic_blocks_file.glob( '*phylogenetic_blocks*.tsv' ) )

    if not phylogenetic_blocks_files:
        logger.error( f"CRITICAL ERROR: No phylogenetic blocks files found!" )
        logger.error( f"Expected location: {input_phylogenetic_blocks_file}" )
        logger.error( f"Run trees_species pipeline first to generate phylogenetic blocks." )
        sys.exit( 1 )

    phylogenetic_blocks_path = phylogenetic_blocks_files[ 0 ]
    logger.info( f"Using file: {phylogenetic_blocks_path.name}" )

    clade_ids___block_data = {}

    with open( phylogenetic_blocks_path, 'r' ) as input_file:
        # Structure_ID (structure identifier)	Clade_ID (clade identifier)	Clade_Name (clade name)	...
        # structure_001	C068	Basal	C068_Basal	C000	Pre_Basal	C000_Pre_Basal	...
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        # Find column indices dynamically from header
        structure_id_column = None
        clade_id_column = None
        clade_name_column = None
        parent_clade_id_column = None

        for index, column_header in enumerate( header_parts ):
            column_id = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            if column_id == 'Structure_ID':
                structure_id_column = index
            elif column_id == 'Clade_ID':
                clade_id_column = index
            elif column_id == 'Clade_Name':
                clade_name_column = index
            elif column_id == 'Parent_Clade_ID':
                parent_clade_id_column = index

        if None in [ structure_id_column, clade_id_column, clade_name_column, parent_clade_id_column ]:
            logger.error( f"CRITICAL ERROR: Could not find required columns in phylogenetic blocks file!" )
            logger.error( f"Found columns: {header_parts}" )
            logger.error( f"Need: Structure_ID, Clade_ID, Clade_Name, Parent_Clade_ID" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]
            clade_id = parts[ clade_id_column ]
            clade_name = parts[ clade_name_column ]
            parent_clade_id = parts[ parent_clade_id_column ]

            if structure_id == TARGET_STRUCTURE:
                clade_ids___block_data[ clade_id ] = {
                    'clade_name': clade_name,
                    'parent_id': parent_clade_id if parent_clade_id != 'NA' and parent_clade_id != 'C000' else parent_clade_id,
                    'structure_id': structure_id
                }

    logger.info( f"Loaded {len( clade_ids___block_data )} phylogenetic blocks for {TARGET_STRUCTURE}" )

    if len( clade_ids___block_data ) == 0:
        logger.error( f"CRITICAL ERROR: No blocks loaded for {TARGET_STRUCTURE}!" )
        logger.error( f"Check that structure exists in: {phylogenetic_blocks_path}" )
        sys.exit( 1 )

    return clade_ids___block_data


def write_phylogenetic_blocks( clade_ids___block_data ):
    """Write phylogenetic blocks to standardized output file."""
    logger.info( f"Writing phylogenetic blocks to: {output_phylogenetic_blocks_file}" )

    with open( output_phylogenetic_blocks_file, 'w' ) as output_file:
        output = 'Clade_ID (clade identifier from trees_species)\t'
        output += 'Clade_Name (clade name from phylogenetic tree)\t'
        output += 'Parent_ID (parent clade identifier or NA for root)\t'
        output += 'Structure_ID (structure identifier for this phylogenetic tree)\n'
        output_file.write( output )

        for clade_id in sorted( clade_ids___block_data.keys() ):
            block_data = clade_ids___block_data[ clade_id ]
            clade_name = block_data[ 'clade_name' ]
            parent_id = block_data[ 'parent_id' ] if block_data[ 'parent_id' ] else 'NA'
            structure_id = block_data[ 'structure_id' ]

            output = f"{clade_id}\t{clade_name}\t{parent_id}\t{structure_id}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( clade_ids___block_data )} blocks to {output_phylogenetic_blocks_file.name}" )


# --- Section A2: Load Parent-Child Relationships ---

def load_parent_child_relationships():
    """
    Load parent-child relationships for the target structure from trees_species.

    Returns:
        list: [ { 'parent_id': str, 'parent_name': str, 'child_id': str, 'child_name': str } ]
    """
    logger.info( f"Loading parent-child relationships from: {input_parent_child_directory}" )

    parent_child_files = list( input_parent_child_directory.glob( f'*{TARGET_STRUCTURE}*parent_child*.tsv' ) )

    if not parent_child_files:
        parent_child_files = list( input_parent_child_directory.glob( f'*{args.structure_id}*parent_child*.tsv' ) )

    if not parent_child_files:
        logger.error( f"CRITICAL ERROR: Parent-child file not found for {TARGET_STRUCTURE}!" )
        logger.error( f"Expected in: {input_parent_child_directory}" )
        logger.error( f"Run trees_species pipeline first to generate parent-child relationships." )
        sys.exit( 1 )

    parent_child_path = parent_child_files[ 0 ]
    logger.info( f"Using file: {parent_child_path.name}" )

    relationships = []

    with open( parent_child_path, 'r' ) as input_file:
        # Parent_ID (parent clade identifier)	Parent_Name (parent clade name)	Child_ID (child clade identifier)	Child_Name (child clade name)
        # C068	Basal	C069	Holomycota
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            if len( parts ) < 4:
                logger.warning( f"Expected 4+ fields, got {len( parts )}, skipping: {line[:80]}" )
                continue

            relationships.append( {
                'parent_id': parts[ 0 ],
                'parent_name': parts[ 1 ],
                'child_id': parts[ 2 ],
                'child_name': parts[ 3 ]
            } )

    logger.info( f"Loaded {len( relationships )} parent-child relationships" )

    if len( relationships ) == 0:
        logger.error( f"CRITICAL ERROR: No parent-child relationships loaded!" )
        sys.exit( 1 )

    return relationships


def write_parent_child_relationships( relationships ):
    """Write parent-child relationships to standardized output file."""
    logger.info( f"Writing parent-child relationships to: {output_parent_child_file}" )

    with open( output_parent_child_file, 'w' ) as output_file:
        output = 'Parent_ID (parent clade identifier)\t'
        output += 'Parent_Name (parent clade name)\t'
        output += 'Child_ID (child clade identifier)\t'
        output += 'Child_Name (child clade name)\n'
        output_file.write( output )

        for relationship in relationships:
            output = f"{relationship[ 'parent_id' ]}\t{relationship[ 'parent_name' ]}\t"
            output += f"{relationship[ 'child_id' ]}\t{relationship[ 'child_name' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( relationships )} relationships to {output_parent_child_file.name}" )


# --- Section A3: Load Phylogenetic Paths ---

def load_phylogenetic_paths():
    """
    Load phylogenetic paths (root-to-leaf) for the target structure from trees_species.

    Returns:
        dict: { leaf_clade_id: [ clade_id_1, clade_id_2, ..., leaf_clade_id ] }
    """
    logger.info( f"Loading phylogenetic paths from: {input_phylogenetic_paths_directory}" )

    paths_files = list( input_phylogenetic_paths_directory.glob( '*paths*.tsv' ) )

    if not paths_files:
        logger.warning( f"No phylogenetic paths files found in: {input_phylogenetic_paths_directory}" )
        logger.info( "Paths will need to be generated from phylogenetic blocks if needed downstream" )
        return {}

    paths_path = paths_files[ 0 ]
    logger.info( f"Using file: {paths_path.name}" )

    leaf_clade_ids___paths = {}

    with open( paths_path, 'r' ) as input_file:
        # Structure_ID (structure identifier)	Species_Clade_ID_Name (species clade identifier and name)	Species_Name (species name)	Phylogenetic_Path (...)
        # structure_001	C001_Fonticula_alba	Fonticula_alba	C068_Basal>C069_Holomycota>C001_Fonticula_alba
        header = input_file.readline()
        header_parts = header.strip().split( '\t' )

        # Find column indices dynamically
        structure_id_column = None
        species_clade_id_column = None
        path_column = None

        for index, column_header in enumerate( header_parts ):
            column_id = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            if column_id == 'Structure_ID':
                structure_id_column = index
            elif column_id in [ 'Species_Clade_ID_Name', 'Species_Clade_ID', 'Leaf_Clade_ID' ]:
                species_clade_id_column = index
            elif 'Path' in column_id or 'path' in column_id:
                path_column = index

        if structure_id_column is None or species_clade_id_column is None or path_column is None:
            logger.error( f"CRITICAL ERROR: Could not find required columns in paths file!" )
            logger.error( f"Found columns: {header_parts}" )
            sys.exit( 1 )

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )

            structure_id = parts[ structure_id_column ]

            if structure_id != TARGET_STRUCTURE:
                continue

            leaf_clade_id = parts[ species_clade_id_column ]
            path_string = parts[ path_column ]

            if '>' in path_string:
                path = path_string.split( '>' )
            else:
                path = path_string.split( ',' )
            path = [ node.strip() for node in path ]

            leaf_clade_ids___paths[ leaf_clade_id ] = path

    logger.info( f"Loaded {len( leaf_clade_ids___paths )} phylogenetic paths for {TARGET_STRUCTURE}" )
    return leaf_clade_ids___paths


def write_phylogenetic_paths( leaf_clade_ids___paths ):
    """Write phylogenetic paths to standardized output file."""
    logger.info( f"Writing phylogenetic paths to: {output_phylogenetic_paths_file}" )

    with open( output_phylogenetic_paths_file, 'w' ) as output_file:
        output = 'Leaf_Clade_ID (terminal leaf clade identifier and name)\t'
        output += 'Path_Length (number of nodes in path from root to leaf)\t'
        output += 'Phylogenetic_Path (comma delimited path from root to leaf)\n'
        output_file.write( output )

        for leaf_clade_id in sorted( leaf_clade_ids___paths.keys() ):
            path = leaf_clade_ids___paths[ leaf_clade_id ]
            path_length = len( path )
            path_string = ','.join( path )

            output = f"{leaf_clade_id}\t{path_length}\t{path_string}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( leaf_clade_ids___paths )} paths to {output_phylogenetic_paths_file.name}" )


# --- Section A4: Write Clade Mappings ---

def write_clade_mappings( clade_ids___block_data ):
    """Write clade ID to name mappings to standardized output file."""
    logger.info( f"Writing clade mappings to: {output_clade_mappings_file}" )

    with open( output_clade_mappings_file, 'w' ) as output_file:
        output = 'Clade_ID (clade identifier from trees_species)\t'
        output += 'Clade_Name (clade name from phylogenetic tree)\n'
        output_file.write( output )

        for clade_id in sorted( clade_ids___block_data.keys() ):
            clade_name = clade_ids___block_data[ clade_id ][ 'clade_name' ]
            output = f"{clade_id}\t{clade_name}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( clade_ids___block_data )} clade mappings to {output_clade_mappings_file.name}" )


# ============================================================================
# PHASE B: LOAD ANNOTATION FILES
# ============================================================================

def extract_species_name_from_phyloname( phyloname ):
    """
    Extract Genus_species from a GIGANTIC phyloname.

    Phyloname format: Kingdom_Phylum_Class_Order_Family_Genus_species
    Returns: Genus_species (handling multi-word species names)
    """
    parts_phyloname = phyloname.split( '_' )

    if len( parts_phyloname ) >= 7:
        genus = parts_phyloname[ 5 ]
        species = '_'.join( parts_phyloname[ 6: ] )
        return genus + '_' + species

    return phyloname


def load_annotation_files():
    """
    Load per-species annotation files from annotations_hmms output.

    Each annotation file is a 7-column TSV:
      Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
      Database_Name, Annotation_Identifier, Annotation_Details

    Returns:
        dict: { species_name: [ { 'sequence_identifier': str, 'annotation_identifier': str, ... } ] }
    """
    logger.info( f"Loading annotation files from: {input_annotations_directory}" )

    if not input_annotations_directory.exists():
        logger.error( f"CRITICAL ERROR: Annotations directory not found!" )
        logger.error( f"Expected location: {input_annotations_directory}" )
        logger.error( f"Run annotations_hmms pipeline first to generate annotation files." )
        sys.exit( 1 )

    # Find all annotation TSV files
    annotation_files = list( input_annotations_directory.glob( '*.tsv' ) )

    if len( annotation_files ) == 0:
        logger.error( f"CRITICAL ERROR: No annotation files found in {input_annotations_directory}!" )
        sys.exit( 1 )

    logger.info( f"Found {len( annotation_files )} annotation files" )

    species_names___annotations = {}

    for annotation_file in sorted( annotation_files ):
        file_annotations = []

        with open( annotation_file, 'r' ) as input_file:
            # Phyloname (GIGANTIC phyloname)	Sequence_Identifier (sequence identifier)	Domain_Start (domain start position)	Domain_Stop (domain stop position)	Database_Name (annotation database name)	Annotation_Identifier (annotation accession or identifier)	Annotation_Details (annotation description or details)
            # Metazoa_Chordata_..._Homo_sapiens	XP_016856755.1	45	230	pfam	PF00069	Protein kinase domain
            header = input_file.readline()

            for line in input_file:
                line = line.strip()
                if not line:
                    continue

                parts = line.split( '\t' )

                if len( parts ) < 6:
                    continue

                phyloname = parts[ 0 ]
                sequence_identifier = parts[ 1 ]
                annotation_identifier = parts[ 5 ]
                annotation_details = parts[ 6 ] if len( parts ) > 6 else ''

                species_name = extract_species_name_from_phyloname( phyloname )

                file_annotations.append( {
                    'phyloname': phyloname,
                    'sequence_identifier': sequence_identifier,
                    'annotation_identifier': annotation_identifier,
                    'annotation_details': annotation_details,
                    'species_name': species_name
                } )

        if file_annotations:
            # Group by species name
            for annotation in file_annotations:
                species_name = annotation[ 'species_name' ]
                if species_name not in species_names___annotations:
                    species_names___annotations[ species_name ] = []
                species_names___annotations[ species_name ].append( annotation )

    total_annotations = sum( len( annotations ) for annotations in species_names___annotations.values() )
    logger.info( f"Loaded {total_annotations} annotations across {len( species_names___annotations )} species" )

    if len( species_names___annotations ) == 0:
        logger.error( f"CRITICAL ERROR: No annotations loaded!" )
        sys.exit( 1 )

    return species_names___annotations


# ============================================================================
# PHASE C: CREATE ANNOGROUPS
# ============================================================================

def create_annogroups( species_names___annotations ):
    """
    Create annotation groups (annogroups) for each requested subtype.

    For each protein, evaluate its annotation status:
      single: protein has exactly 1 annotation from this database
      combo:  protein has a specific set of multiple annotations (grouped by identical set)
      zero:   protein has 0 annotations from this database (singleton annogroup)

    The annotation_identifier for zero-subtype proteins uses the format:
      unannotated_{database_name}-N

    Args:
        species_names___annotations: Dict mapping species names to annotation records

    Returns:
        tuple: ( annogroup_map_entries, subtypes___annogroup_files )
    """
    logger.info( f"Creating annogroups for database: {ANNOTATION_DATABASE}" )
    logger.info( f"Requested subtypes: {ANNOGROUP_SUBTYPES}" )

    # Step 1: Build per-protein annotation profiles
    # For each protein, collect all its annotation identifiers
    logger.info( "Step 1: Building per-protein annotation profiles..." )

    # proteins___annotation_profiles: { sequence_identifier: { 'species_name': str, 'annotations': [ accession_1, ... ] } }
    proteins___annotation_profiles = {}

    # Also track all proteins per species (for finding unannotated ones)
    species_names___all_sequence_identifiers = defaultdict( set )

    for species_name, annotations in species_names___annotations.items():
        for annotation in annotations:
            sequence_identifier = annotation[ 'sequence_identifier' ]
            annotation_identifier = annotation[ 'annotation_identifier' ]

            species_names___all_sequence_identifiers[ species_name ].add( sequence_identifier )

            if sequence_identifier not in proteins___annotation_profiles:
                proteins___annotation_profiles[ sequence_identifier ] = {
                    'species_name': species_name,
                    'annotations': []
                }

            proteins___annotation_profiles[ sequence_identifier ][ 'annotations' ].append( annotation_identifier )

    total_annotated_proteins = len( proteins___annotation_profiles )
    logger.info( f"Found {total_annotated_proteins} annotated proteins across all species" )

    # Step 2: Classify proteins into subtypes
    logger.info( "Step 2: Classifying proteins by annotation count..." )

    # single_proteins: { annotation_accession: [ { 'sequence_identifier': str, 'species_name': str } ] }
    single_accessions___proteins = defaultdict( list )

    # combo_proteins: { tuple_of_sorted_accessions: [ { 'sequence_identifier': str, 'species_name': str } ] }
    combo_architectures___proteins = defaultdict( list )

    # zero_proteins: [ { 'sequence_identifier': str, 'species_name': str, 'unannotated_identifier': str } ]
    zero_proteins = []

    single_count = 0
    combo_count = 0

    for sequence_identifier, profile in proteins___annotation_profiles.items():
        species_name = profile[ 'species_name' ]
        annotations = profile[ 'annotations' ]

        annotation_count = len( annotations )

        if annotation_count == 1:
            # Single annotation
            accession = annotations[ 0 ]

            # Skip unannotated identifiers (they are zero-subtype)
            if accession.startswith( f"unannotated_{ANNOTATION_DATABASE}" ):
                zero_proteins.append( {
                    'sequence_identifier': sequence_identifier,
                    'species_name': species_name,
                    'unannotated_identifier': accession
                } )
                continue

            single_accessions___proteins[ accession ].append( {
                'sequence_identifier': sequence_identifier,
                'species_name': species_name
            } )
            single_count += 1

        elif annotation_count > 1:
            # Combo annotation (identical multi-annotation architecture)
            # Sort accessions to create canonical architecture key
            sorted_accessions = tuple( sorted( annotations ) )
            combo_architectures___proteins[ sorted_accessions ].append( {
                'sequence_identifier': sequence_identifier,
                'species_name': species_name
            } )
            combo_count += 1

    logger.info( f"Single-annotation proteins: {single_count}" )
    logger.info( f"Combo-annotation proteins: {combo_count}" )
    logger.info( f"Zero-annotation proteins (unannotated): {len( zero_proteins )}" )

    # Step 3: Assign annogroup IDs and build the map
    logger.info( "Step 3: Assigning annogroup IDs..." )

    annogroup_map_entries = []
    annogroup_counter = 1

    # Subtypes data for per-subtype output files
    subtypes___annogroup_data = {}

    # --- Process SINGLE subtype ---
    if 'single' in ANNOGROUP_SUBTYPES:
        logger.info( f"Processing 'single' subtype: {len( single_accessions___proteins )} unique accessions" )
        single_annogroups = []

        for accession in sorted( single_accessions___proteins.keys() ):
            proteins = single_accessions___proteins[ accession ]
            annogroup_id = f"annogroup_{ANNOTATION_DATABASE}_{annogroup_counter}"
            annogroup_counter += 1

            species_names = sorted( set( protein[ 'species_name' ] for protein in proteins ) )
            sequence_identifiers = sorted( protein[ 'sequence_identifier' ] for protein in proteins )

            map_entry = {
                'annogroup_id': annogroup_id,
                'annogroup_subtype': 'single',
                'annotation_database': ANNOTATION_DATABASE,
                'annotation_accessions': accession,
                'species_count': len( species_names ),
                'sequence_count': len( sequence_identifiers ),
                'species_list': ','.join( species_names ),
                'sequence_ids': ','.join( sequence_identifiers )
            }

            annogroup_map_entries.append( map_entry )
            single_annogroups.append( map_entry )

        subtypes___annogroup_data[ 'single' ] = single_annogroups
        logger.info( f"Created {len( single_annogroups )} single annogroups" )

    # --- Process COMBO subtype ---
    if 'combo' in ANNOGROUP_SUBTYPES:
        logger.info( f"Processing 'combo' subtype: {len( combo_architectures___proteins )} unique architectures" )
        combo_annogroups = []

        for architecture in sorted( combo_architectures___proteins.keys() ):
            proteins = combo_architectures___proteins[ architecture ]
            annogroup_id = f"annogroup_{ANNOTATION_DATABASE}_{annogroup_counter}"
            annogroup_counter += 1

            accessions_string = ','.join( architecture )
            species_names = sorted( set( protein[ 'species_name' ] for protein in proteins ) )
            sequence_identifiers = sorted( protein[ 'sequence_identifier' ] for protein in proteins )

            map_entry = {
                'annogroup_id': annogroup_id,
                'annogroup_subtype': 'combo',
                'annotation_database': ANNOTATION_DATABASE,
                'annotation_accessions': accessions_string,
                'species_count': len( species_names ),
                'sequence_count': len( sequence_identifiers ),
                'species_list': ','.join( species_names ),
                'sequence_ids': ','.join( sequence_identifiers )
            }

            annogroup_map_entries.append( map_entry )
            combo_annogroups.append( map_entry )

        subtypes___annogroup_data[ 'combo' ] = combo_annogroups
        logger.info( f"Created {len( combo_annogroups )} combo annogroups" )

    # --- Process ZERO subtype ---
    if 'zero' in ANNOGROUP_SUBTYPES:
        logger.info( f"Processing 'zero' subtype: {len( zero_proteins )} unannotated proteins" )
        zero_annogroups = []

        for zero_protein in sorted( zero_proteins, key = lambda x: x[ 'unannotated_identifier' ] ):
            annogroup_id = f"annogroup_{ANNOTATION_DATABASE}_{annogroup_counter}"
            annogroup_counter += 1

            map_entry = {
                'annogroup_id': annogroup_id,
                'annogroup_subtype': 'zero',
                'annotation_database': ANNOTATION_DATABASE,
                'annotation_accessions': zero_protein[ 'unannotated_identifier' ],
                'species_count': 1,
                'sequence_count': 1,
                'species_list': zero_protein[ 'species_name' ],
                'sequence_ids': zero_protein[ 'sequence_identifier' ]
            }

            annogroup_map_entries.append( map_entry )
            zero_annogroups.append( map_entry )

        subtypes___annogroup_data[ 'zero' ] = zero_annogroups
        logger.info( f"Created {len( zero_annogroups )} zero annogroups" )

    total_annogroups = len( annogroup_map_entries )
    logger.info( f"Total annogroups created: {total_annogroups}" )

    if total_annogroups == 0:
        logger.error( f"CRITICAL ERROR: No annogroups created!" )
        logger.error( f"Check annotation files in: {input_annotations_directory}" )
        sys.exit( 1 )

    return annogroup_map_entries, subtypes___annogroup_data


# ============================================================================
# PHASE D: WRITE ANNOGROUP OUTPUTS
# ============================================================================

def write_annogroup_map( annogroup_map_entries ):
    """Write the annogroup map (lookup table linking IDs to full details)."""
    logger.info( f"Writing annogroup map to: {output_annogroup_map_file}" )

    with open( output_annogroup_map_file, 'w' ) as output_file:
        output = 'Annogroup_ID (identifier format annogroup_{db}_N)\t'
        output += 'Annogroup_Subtype (single or combo or zero)\t'
        output += 'Annotation_Database (name of annotation database)\t'
        output += 'Annotation_Accessions (comma delimited annotation accessions from the database or unannotated identifier)\t'
        output += 'Species_Count (number of unique species with at least one member sequence)\t'
        output += 'Sequence_Count (total number of member sequences)\t'
        output += 'Species_List (comma delimited list of species names)\t'
        output += 'Sequence_IDs (comma delimited list of GIGANTIC sequence identifiers)\n'
        output_file.write( output )

        for entry in annogroup_map_entries:
            output = f"{entry[ 'annogroup_id' ]}\t"
            output += f"{entry[ 'annogroup_subtype' ]}\t"
            output += f"{entry[ 'annotation_database' ]}\t"
            output += f"{entry[ 'annotation_accessions' ]}\t"
            output += f"{entry[ 'species_count' ]}\t"
            output += f"{entry[ 'sequence_count' ]}\t"
            output += f"{entry[ 'species_list' ]}\t"
            output += f"{entry[ 'sequence_ids' ]}\n"
            output_file.write( output )

    logger.info( f"Wrote {len( annogroup_map_entries )} entries to {output_annogroup_map_file.name}" )


def write_per_subtype_annogroup_files( subtypes___annogroup_data ):
    """Write per-subtype annogroup files with annogroup ID and member sequences."""
    logger.info( "Writing per-subtype annogroup files..." )

    for subtype, annogroup_entries in subtypes___annogroup_data.items():
        output_subtype_file = output_directory / f'1_ai-annogroups-{subtype}.tsv'
        logger.info( f"Writing {subtype} annogroups to: {output_subtype_file}" )

        with open( output_subtype_file, 'w' ) as output_file:
            output = 'Annogroup_ID (annogroup identifier)\t'
            output += 'Sequence_Count (total count of sequences in annogroup)\t'
            output += 'Sequence_IDs (comma delimited list of sequence identifiers)\n'
            output_file.write( output )

            for entry in annogroup_entries:
                output = f"{entry[ 'annogroup_id' ]}\t{entry[ 'sequence_count' ]}\t{entry[ 'sequence_ids' ]}\n"
                output_file.write( output )

        logger.info( f"Wrote {len( annogroup_entries )} {subtype} annogroups" )


def write_subtypes_manifest( subtypes___annogroup_data ):
    """Write manifest listing which subtypes were generated."""
    logger.info( f"Writing subtypes manifest to: {output_subtypes_manifest_file}" )

    with open( output_subtypes_manifest_file, 'w' ) as output_file:
        output = 'Annogroup_Subtype (subtype name)\t'
        output += 'Annogroup_Count (number of annogroups of this subtype)\t'
        output += 'Output_File (filename of per-subtype annogroup file)\n'
        output_file.write( output )

        for subtype in sorted( subtypes___annogroup_data.keys() ):
            annogroup_count = len( subtypes___annogroup_data[ subtype ] )
            output_filename = f'1_ai-annogroups-{subtype}.tsv'

            output = f"{subtype}\t{annogroup_count}\t{output_filename}\n"
            output_file.write( output )

    logger.info( f"Wrote manifest with {len( subtypes___annogroup_data )} subtypes" )


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 001: CREATE ANNOTATION GROUPS (ANNOGROUPS)" )
    logger.info( "=" * 80 )
    logger.info( f"Started: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( f"Target structure: {TARGET_STRUCTURE}" )
    logger.info( f"Species set: {SPECIES_SET_NAME}" )
    logger.info( f"Annotation database: {ANNOTATION_DATABASE}" )
    logger.info( f"Annogroup subtypes: {ANNOGROUP_SUBTYPES}" )
    logger.info( f"Config file: {config_path}" )
    logger.info( "" )

    # ========================================================================
    # PHASE A: Load phylogenetic tree data
    # ========================================================================
    logger.info( "PHASE A: Loading phylogenetic tree data..." )

    # Step A1: Load phylogenetic blocks
    logger.info( "" )
    logger.info( "STEP A1: Loading phylogenetic blocks..." )
    clade_ids___block_data = load_phylogenetic_blocks()
    write_phylogenetic_blocks( clade_ids___block_data )

    # Step A2: Load parent-child relationships
    logger.info( "" )
    logger.info( "STEP A2: Loading parent-child relationships..." )
    relationships = load_parent_child_relationships()
    write_parent_child_relationships( relationships )

    # Step A3: Load phylogenetic paths
    logger.info( "" )
    logger.info( "STEP A3: Loading phylogenetic paths..." )
    leaf_clade_ids___paths = load_phylogenetic_paths()
    if leaf_clade_ids___paths:
        write_phylogenetic_paths( leaf_clade_ids___paths )
    else:
        logger.info( "No paths file found - will be generated from blocks if needed downstream" )

    # Step A4: Create clade mappings
    logger.info( "" )
    logger.info( "STEP A4: Creating clade ID to name mappings..." )
    write_clade_mappings( clade_ids___block_data )

    # ========================================================================
    # PHASE B: Load annotation files
    # ========================================================================
    logger.info( "" )
    logger.info( "PHASE B: Loading annotation files..." )
    species_names___annotations = load_annotation_files()

    # ========================================================================
    # PHASE C: Create annogroups
    # ========================================================================
    logger.info( "" )
    logger.info( "PHASE C: Creating annogroups..." )
    annogroup_map_entries, subtypes___annogroup_data = create_annogroups( species_names___annotations )

    # ========================================================================
    # PHASE D: Write annogroup outputs
    # ========================================================================
    logger.info( "" )
    logger.info( "PHASE D: Writing annogroup outputs..." )
    write_annogroup_map( annogroup_map_entries )
    write_per_subtype_annogroup_files( subtypes___annogroup_data )
    write_subtypes_manifest( subtypes___annogroup_data )

    # ========================================================================
    # Complete
    # ========================================================================
    logger.info( "" )
    logger.info( "=" * 80 )
    logger.info( "SCRIPT 001 COMPLETED SUCCESSFULLY" )
    logger.info( "=" * 80 )
    logger.info( f"All outputs written to: {output_directory}" )
    logger.info( f"Finished: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
    logger.info( "" )
    logger.info( "Output files:" )
    logger.info( f"  {output_phylogenetic_blocks_file.name}" )
    logger.info( f"  {output_parent_child_file.name}" )
    if leaf_clade_ids___paths:
        logger.info( f"  {output_phylogenetic_paths_file.name}" )
    logger.info( f"  {output_clade_mappings_file.name}" )
    logger.info( f"  {output_annogroup_map_file.name}" )
    for subtype in sorted( subtypes___annogroup_data.keys() ):
        logger.info( f"  1_ai-annogroups-{subtype}.tsv" )
    logger.info( f"  {output_subtypes_manifest_file.name}" )
    logger.info( "" )
    logger.info( f"Total annogroups: {len( annogroup_map_entries )}" )
    for subtype, data in sorted( subtypes___annogroup_data.items() ):
        logger.info( f"  {subtype}: {len( data )}" )
    logger.info( "=" * 80 )

    return 0


if __name__ == '__main__':
    sys.exit( main() )
