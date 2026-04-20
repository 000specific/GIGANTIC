#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 18 | Purpose: Compute innovations (any/all) and origins-at-clade tables per clade per structure
# Human: Eric Edsinger

"""
moroz_innovations_analysis -- Script 001

For each (feature_type in {orthogroups, annotations}) x (structure in
target_structures) x (clade in target_clades), compute THREE tables:

    1_ai-structure_NNN-clade_innovations_any_species_{feature_type}.tsv
    1_ai-structure_NNN-clade_innovations_all_species_{feature_type}.tsv
    1_ai-structure_NNN-clade_ocl_origins_{feature_type}.tsv

DEFINITIONS:
    innovation_any(clade):
        {feature : Species_List(feature) subset of Species(clade) AND Species_List(feature) non-empty}
        i.e. every species containing the feature is inside the target clade
        (at least one clade species has it).

    innovation_all(clade):
        {feature : Species_List(feature) == Species(clade) as a set}
        i.e. every clade species has it AND no non-clade species has it.

    origin_at_clade(clade, structure):
        {feature : Origin_Phylogenetic_Block ends at clade under structure}
        i.e. the block Parent_Clade::Target_Clade per GIGANTIC OCL output.
"""

import sys
import logging
import gzip
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write( "Missing pyyaml. Install in conda env: mamba install pyyaml\n" )
    sys.exit( 1 )


logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger( __name__ )


# ============================================================================
# Helpers
# ============================================================================

def bare_name( clade_id_name ):
    """
    Normalize a clade identifier to its bare name by stripping a leading
    "CXXX_" prefix if present. Idempotent, so both input forms collapse
    to the same key:
        "C082_Metazoa"  ->  "Metazoa"
        "Metazoa"       ->  "Metazoa"
        "C089_Ctenophora_Subclade_1"  ->  "Ctenophora_Subclade_1"

    Users can mix bare names and full CXXX_ labels freely in config --
    the same normalization is applied to every Clade_ID_Name in the
    mappings file, so both sides of the comparison are always in bare form.
    """
    prefix, _, rest = clade_id_name.partition( '_' )
    if prefix.startswith( 'C' ) and prefix[ 1: ].isdigit() and rest:
        return rest
    return clade_id_name


def open_maybe_gzip( path ):
    """Open .tsv or .tsv.gz transparently. Returns a text-mode file handle."""
    path = Path( path )
    if path.suffix == '.gz':
        return gzip.open( path, 'rt' )
    return open( path, 'r' )


def parse_header_column_indices( header_line, wanted_id_prefixes ):
    """
    GIGANTIC TSV headers use the self-documenting format
        "{Column_ID} (human-readable details)"
    Build a mapping { column_id : column_index } for each requested ID prefix.
    Missing prefixes are absent from the returned dict (caller decides whether
    that is fatal).
    """
    parts = header_line.rstrip( '\n' ).split( '\t' )
    column_ids___indices = {}
    for index, header_cell in enumerate( parts ):
        column_id = header_cell.split( ' ', 1 )[ 0 ]
        if column_id in wanted_id_prefixes:
            column_ids___indices[ column_id ] = index
    return column_ids___indices


def find_summary_file( output_to_input_base, run_label, summary_filename_pattern, structure_id ):
    """
    Resolve the per-structure OCL complete_ocl_summary file under the
    canonical inter-subproject location:
        {output_to_input_base}/{run_label}/{summary_filename_pattern-with-NNN-replaced}
    Prefers a .gz sibling if the uncompressed file is not present.
    """
    base = Path( output_to_input_base ).resolve() / run_label
    numeric = structure_id.split( '_' )[ -1 ]
    relative = summary_filename_pattern.replace( 'NNN', numeric )
    candidate = base / relative
    if candidate.exists():
        return candidate
    gz_candidate = Path( str( candidate ) + '.gz' )
    if gz_candidate.exists():
        return gz_candidate
    return None


# ============================================================================
# Config loading
# ============================================================================

def load_config( config_path ):
    with open( config_path, 'r' ) as handle:
        return yaml.safe_load( handle )


# ============================================================================
# Clade -> species resolution
# ============================================================================

def load_clade_species_mappings( mappings_tsv, target_structures, target_clades_user_input ):
    """
    Parse 9_ai-clade_species_mappings-all_structures.tsv filtered to
    (target_structures) x (user-specified clade names, normalized via bare_name).

    Returns:
        ( map, unresolved_by_structure )
        map: { ( structure_id, bare_name ) : { 'clade_id_name': str, 'species_set': frozenset } }
        unresolved_by_structure: { structure_id : set( bare_names_not_found ) }
    """
    # Structure_ID  Clade_ID_Name  Phylogenetic_Block  Descendant_Species_Count  Descendant_Species_List  Descendant_Species_Paths  All_Descendant_Clade_ID_Names
    # structure_001  C082_Metazoa  C071_Basal::C082_Metazoa  70  Species_1,Species_2,...

    targets_bare = { bare_name( name ) for name in target_clades_user_input }
    target_structures_set = set( target_structures )

    wanted = { 'Structure_ID', 'Clade_ID_Name', 'Descendant_Species_List' }

    mapping = {}

    with open( mappings_tsv, 'r' ) as input_mappings:
        header_line = input_mappings.readline()
        column_ids___indices = parse_header_column_indices( header_line, wanted )

        missing = wanted - column_ids___indices.keys()
        if missing:
            logger.error( "CRITICAL ERROR: clade_species_mappings file missing expected columns." )
            logger.error( f"  File: {mappings_tsv}" )
            logger.error( f"  Missing column IDs: {sorted( missing )}" )
            logger.error( f"  Header seen: {header_line.rstrip()}" )
            sys.exit( 1 )

        index_structure = column_ids___indices[ 'Structure_ID' ]
        index_clade = column_ids___indices[ 'Clade_ID_Name' ]
        index_species = column_ids___indices[ 'Descendant_Species_List' ]

        for line in input_mappings:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ index_structure ]
            if structure_id not in target_structures_set:
                continue
            clade_id_name = parts[ index_clade ]
            clade_bare = bare_name( clade_id_name )
            if clade_bare not in targets_bare:
                continue
            species_field = parts[ index_species ] if len( parts ) > index_species else ''
            species_set = frozenset(
                species.strip() for species in species_field.split( ',' )
                if species.strip()
            )
            # Leaf species clade: Descendant_Species_List is empty because
            # a species has no descendants. Treat the clade as containing
            # itself (its bare name IS the species name).
            if not species_set:
                species_set = frozenset( [ clade_bare ] )
            mapping[ ( structure_id, clade_bare ) ] = {
                'clade_id_name': clade_id_name,
                'species_set': species_set,
            }

    unresolved_by_structure = {}
    for structure_id in target_structures:
        found_bares = { key[ 1 ] for key in mapping if key[ 0 ] == structure_id }
        unresolved = targets_bare - found_bares
        if unresolved:
            unresolved_by_structure[ structure_id ] = unresolved

    return mapping, unresolved_by_structure


def load_all_species_for_structure( mappings_tsv, structure_id ):
    """
    Return frozenset of ALL species under structure_id by taking the row
    with maximum Descendant_Species_Count (the root/basal clade).
    """
    wanted = { 'Structure_ID', 'Descendant_Species_Count', 'Descendant_Species_List' }

    best_count = -1
    best_species_set = frozenset()

    with open( mappings_tsv, 'r' ) as input_mappings:
        header_line = input_mappings.readline()
        column_ids___indices = parse_header_column_indices( header_line, wanted )

        if wanted - column_ids___indices.keys():
            logger.error( "CRITICAL ERROR: mappings file missing columns needed for root-species discovery." )
            sys.exit( 1 )

        index_structure = column_ids___indices[ 'Structure_ID' ]
        index_count = column_ids___indices[ 'Descendant_Species_Count' ]
        index_species = column_ids___indices[ 'Descendant_Species_List' ]

        for line in input_mappings:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_structure ] != structure_id:
                continue
            try:
                count = int( parts[ index_count ] )
            except ValueError:
                continue
            if count > best_count:
                best_count = count
                species_field = parts[ index_species ] if len( parts ) > index_species else ''
                best_species_set = frozenset(
                    species.strip() for species in species_field.split( ',' )
                    if species.strip()
                )

    return best_species_set


# ============================================================================
# Feature loading
# ============================================================================

def load_features_with_species( summary_file, feature_id_column ):
    """
    Yield per-feature dicts:
        {
            'feature_id': str,
            'species_set': frozenset[str],
            'origin_block': str,
            'origin_path': str,
            'annogroup_subtype': str | None,
        }
    """
    wanted = {
        feature_id_column,
        'Origin_Phylogenetic_Block',
        'Origin_Phylogenetic_Path',
        'Species_List',
        'Annogroup_Subtype',   # optional, annotations only
    }

    with open_maybe_gzip( summary_file ) as input_summary:
        header_line = input_summary.readline()
        column_ids___indices = parse_header_column_indices( header_line, wanted )

        required = { feature_id_column, 'Origin_Phylogenetic_Block', 'Origin_Phylogenetic_Path', 'Species_List' }
        missing = required - column_ids___indices.keys()
        if missing:
            logger.error( f"CRITICAL ERROR: summary file missing required columns: {sorted( missing )}" )
            logger.error( f"  File: {summary_file}" )
            logger.error( f"  Header seen: {header_line.rstrip()}" )
            sys.exit( 1 )

        index_feature_id = column_ids___indices[ feature_id_column ]
        index_origin_block = column_ids___indices[ 'Origin_Phylogenetic_Block' ]
        index_origin_path = column_ids___indices[ 'Origin_Phylogenetic_Path' ]
        index_species = column_ids___indices[ 'Species_List' ]
        index_subtype = column_ids___indices.get( 'Annogroup_Subtype' )

        for line in input_summary:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            species_field = parts[ index_species ] if len( parts ) > index_species else ''
            species_set = frozenset(
                species.strip() for species in species_field.split( ',' )
                if species.strip()
            )
            annogroup_subtype = None
            if index_subtype is not None and len( parts ) > index_subtype:
                annogroup_subtype = parts[ index_subtype ]
            yield {
                'feature_id': parts[ index_feature_id ],
                'species_set': species_set,
                'origin_block': parts[ index_origin_block ] if len( parts ) > index_origin_block else '',
                'origin_path': parts[ index_origin_path ] if len( parts ) > index_origin_path else '',
                'annogroup_subtype': annogroup_subtype,
            }


# ============================================================================
# Classification
# ============================================================================

def classify_innovation_any( feature_species_set, clade_species_set ):
    """True iff every species with the feature is inside the clade (and at least one)."""
    if not feature_species_set:
        return False
    return feature_species_set.issubset( clade_species_set )


def classify_innovation_all( feature_species_set, clade_species_set ):
    """True iff the feature is present in every clade species AND in no non-clade species."""
    if not clade_species_set:
        return False
    return feature_species_set == clade_species_set


def classify_origin_at_clade( feature_origin_block, clade_id_name ):
    """
    True iff the feature's Origin_Phylogenetic_Block ends at the target clade.
    Form: "Parent_Clade_ID_Name::clade_id_name"
    """
    if not feature_origin_block or '::' not in feature_origin_block:
        return False
    _, _, child = feature_origin_block.partition( '::' )
    return child == clade_id_name


# ============================================================================
# Output writers
# ============================================================================

INNOVATIONS_HEADER = (
    'Target_Clade_Bare_Name (bare name of target clade as specified by user or derived from Clade_ID_Name)\t'
    'Target_Clade_ID_Name (full clade_id_name as used in this species tree structure e.g. C082_Metazoa)\t'
    '{FEATURE_ID_COLUMN} ({FEATURE_ID_DESCRIPTION})\t'
    'Feature_Species_Count (count of species containing this feature)\t'
    'Feature_Species_List (comma delimited list of species containing this feature as Genus_species)\t'
    'Clade_Species_Count (count of species in the target clade under this structure)\t'
    'Clade_Species_List (comma delimited list of species in the target clade as Genus_species){OPT_SUBTYPE_HEADER}\n'
)

ORIGINS_HEADER = (
    'Target_Clade_Bare_Name (bare name of target clade as specified by user or derived from Clade_ID_Name)\t'
    'Target_Clade_ID_Name (full clade_id_name as used in this species tree structure e.g. C082_Metazoa)\t'
    '{FEATURE_ID_COLUMN} ({FEATURE_ID_DESCRIPTION})\t'
    'Origin_Phylogenetic_Block (phylogenetic block containing the origin transition as Parent_Clade_ID_Name::Child_Clade_ID_Name)\t'
    'Origin_Phylogenetic_Path (phylogenetic path from root to child endpoint of origin block comma delimited as clade_id_name values)\t'
    'Feature_Species_Count (count of species containing this feature)\t'
    'Feature_Species_List (comma delimited list of species containing this feature as Genus_species){OPT_SUBTYPE_HEADER}\n'
)

SUBTYPE_HEADER_CELL = '\tAnnogroup_Subtype (single or combo or zero)'

FEATURE_ID_DESCRIPTIONS = {
    'Orthogroup_ID': 'orthogroup identifier from OCL output',
    'Annogroup_ID': 'annogroup identifier from OCL output',
}


def _header_with_feature_column( template, feature_id_column, has_subtype ):
    opt_subtype = SUBTYPE_HEADER_CELL if has_subtype else ''
    return template.format(
        FEATURE_ID_COLUMN = feature_id_column,
        FEATURE_ID_DESCRIPTION = FEATURE_ID_DESCRIPTIONS.get( feature_id_column, feature_id_column ),
        OPT_SUBTYPE_HEADER = opt_subtype,
    )


def write_innovations_table( rows, output_path, feature_id_column, has_subtype ):
    output_path.parent.mkdir( parents = True, exist_ok = True )
    with open( output_path, 'w' ) as output_innovations:
        output_innovations.write( _header_with_feature_column( INNOVATIONS_HEADER, feature_id_column, has_subtype ) )
        for row in rows:
            feature_species = sorted( row[ 'feature_species_set' ] )
            clade_species = sorted( row[ 'clade_species_set' ] )
            fields = [
                row[ 'target_clade_bare_name' ],
                row[ 'target_clade_id_name' ],
                row[ 'feature_id' ],
                str( len( feature_species ) ),
                ','.join( feature_species ),
                str( len( clade_species ) ),
                ','.join( clade_species ),
            ]
            if has_subtype:
                fields.append( row.get( 'annogroup_subtype' ) or '' )
            output = '\t'.join( fields ) + '\n'
            output_innovations.write( output )


def write_origins_at_clade_table( rows, output_path, feature_id_column, has_subtype ):
    output_path.parent.mkdir( parents = True, exist_ok = True )
    with open( output_path, 'w' ) as output_origins:
        output_origins.write( _header_with_feature_column( ORIGINS_HEADER, feature_id_column, has_subtype ) )
        for row in rows:
            feature_species = sorted( row[ 'feature_species_set' ] )
            fields = [
                row[ 'target_clade_bare_name' ],
                row[ 'target_clade_id_name' ],
                row[ 'feature_id' ],
                row[ 'origin_block' ],
                row[ 'origin_path' ],
                str( len( feature_species ) ),
                ','.join( feature_species ),
            ]
            if has_subtype:
                fields.append( row.get( 'annogroup_subtype' ) or '' )
            output = '\t'.join( fields ) + '\n'
            output_origins.write( output )


# ============================================================================
# Main
# ============================================================================

def main():
    script_dir = Path( __file__ ).resolve().parent
    workflow_dir = script_dir.parent.parent
    config_path = workflow_dir / 'START_HERE-user_config.yaml'

    logger.info( f"Loading config: {config_path}" )
    config = load_config( config_path )

    target_clades_user_input = list( config[ 'target_clades' ] )
    target_structures = list( config[ 'target_structures' ] )
    output_base = workflow_dir / config[ 'output' ][ 'base_dir' ]

    logger.info( f"Target clades (user input): {target_clades_user_input}" )
    logger.info( f"Target clades (normalized bare): {[ bare_name( n ) for n in target_clades_user_input ]}" )
    logger.info( f"Target structures: {target_structures}" )
    logger.info( f"Output base: {output_base}" )

    # Resolve mappings path
    mappings_tsv = ( workflow_dir / config[ 'species_tree_source' ][ 'clade_species_mappings_tsv' ] ).resolve()
    if not mappings_tsv.exists():
        logger.error( f"CRITICAL ERROR: clade_species_mappings TSV not found: {mappings_tsv}" )
        sys.exit( 1 )

    logger.info( f"Loading clade-species mappings: {mappings_tsv}" )
    clade_map, unresolved_by_structure = load_clade_species_mappings(
        mappings_tsv, target_structures, target_clades_user_input
    )

    if unresolved_by_structure:
        logger.error( "CRITICAL ERROR: some target_clades could not be resolved against the species tree mappings." )
        for structure_id, unresolved in unresolved_by_structure.items():
            logger.error( f"  Structure {structure_id}: unresolved clades {sorted( unresolved )}" )
        logger.error( "Check spelling of target_clades in the config. Both bare names and CXXX_Name forms are accepted." )
        sys.exit( 1 )

    logger.info( f"Resolved {len( clade_map )} (structure, clade) entries." )

    # Iterate feature sources
    for feature_type, source_cfg in config[ 'feature_sources' ].items():
        if not source_cfg.get( 'enabled', True ):
            logger.info( f"Skipping feature_type={feature_type} (disabled)" )
            continue

        feature_id_column = source_cfg[ 'feature_id_column' ]
        logger.info( f"--- feature_type={feature_type} (id column: {feature_id_column}) ---" )

        for structure_id in target_structures:
            summary_file = find_summary_file(
                workflow_dir / source_cfg[ 'output_to_input_base' ],
                source_cfg[ 'run_label' ],
                source_cfg[ 'summary_filename_pattern' ],
                structure_id,
            )
            if summary_file is None:
                logger.error( f"CRITICAL ERROR: summary file not found for feature_type={feature_type}, structure={structure_id}." )
                logger.error( f"  Base: {workflow_dir / source_cfg[ 'output_to_input_base' ]}" )
                logger.error( f"  run_label: {source_cfg[ 'run_label' ]}" )
                logger.error( f"  pattern: {source_cfg[ 'summary_filename_pattern' ]}" )
                sys.exit( 1 )
            logger.info( f"  structure={structure_id}  summary={summary_file}" )

            features = list( load_features_with_species( summary_file, feature_id_column ) )
            logger.info( f"  loaded {len( features )} features" )

            has_subtype = any( feature[ 'annogroup_subtype' ] is not None for feature in features )

            innovations_any_rows = []
            innovations_all_rows = []
            origins_rows = []

            for clade_user_input in target_clades_user_input:
                clade_bare = bare_name( clade_user_input )
                info = clade_map[ ( structure_id, clade_bare ) ]
                clade_species_set = info[ 'species_set' ]
                clade_id_name = info[ 'clade_id_name' ]

                count_any = 0
                count_all = 0
                count_origin = 0

                for feature in features:
                    if classify_innovation_any( feature[ 'species_set' ], clade_species_set ):
                        innovations_any_rows.append( {
                            'target_clade_bare_name': clade_bare,
                            'target_clade_id_name': clade_id_name,
                            'feature_id': feature[ 'feature_id' ],
                            'feature_species_set': feature[ 'species_set' ],
                            'clade_species_set': clade_species_set,
                            'annogroup_subtype': feature[ 'annogroup_subtype' ],
                        } )
                        count_any += 1
                    if classify_innovation_all( feature[ 'species_set' ], clade_species_set ):
                        innovations_all_rows.append( {
                            'target_clade_bare_name': clade_bare,
                            'target_clade_id_name': clade_id_name,
                            'feature_id': feature[ 'feature_id' ],
                            'feature_species_set': feature[ 'species_set' ],
                            'clade_species_set': clade_species_set,
                            'annogroup_subtype': feature[ 'annogroup_subtype' ],
                        } )
                        count_all += 1
                    if classify_origin_at_clade( feature[ 'origin_block' ], clade_id_name ):
                        origins_rows.append( {
                            'target_clade_bare_name': clade_bare,
                            'target_clade_id_name': clade_id_name,
                            'feature_id': feature[ 'feature_id' ],
                            'origin_block': feature[ 'origin_block' ],
                            'origin_path': feature[ 'origin_path' ],
                            'feature_species_set': feature[ 'species_set' ],
                            'annogroup_subtype': feature[ 'annogroup_subtype' ],
                        } )
                        count_origin += 1

                logger.info(
                    f"    clade={clade_bare} ({clade_id_name}, {len( clade_species_set )} spp)"
                    f"  innovations_any={count_any}  innovations_all={count_all}  origins_at_clade={count_origin}"
                )

            # Write outputs
            output_dir = output_base / structure_id / '1-output'
            numeric = structure_id.split( '_' )[ -1 ]
            file_any = output_dir / f"1_ai-structure_{numeric}-clade_innovations_any_species_{feature_type}.tsv"
            file_all = output_dir / f"1_ai-structure_{numeric}-clade_innovations_all_species_{feature_type}.tsv"
            file_origins = output_dir / f"1_ai-structure_{numeric}-clade_ocl_origins_{feature_type}.tsv"

            write_innovations_table( innovations_any_rows, file_any, feature_id_column, has_subtype )
            write_innovations_table( innovations_all_rows, file_all, feature_id_column, has_subtype )
            write_origins_at_clade_table( origins_rows, file_origins, feature_id_column, has_subtype )

            logger.info( f"  wrote {file_any.name}  ({len( innovations_any_rows )} rows)" )
            logger.info( f"  wrote {file_all.name}  ({len( innovations_all_rows )} rows)" )
            logger.info( f"  wrote {file_origins.name}  ({len( origins_rows )} rows)" )

    logger.info( "Script 001 complete." )


if __name__ == '__main__':
    main()
