#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 11 | Purpose: Validate inputs for parsimony ranking workflow
# Human: Eric Edsinger

"""
Script 001 -- Validate inputs.

Reads structure_manifest, verifies that each structure has a complete OCL
summary TSV in the configured upstream orthogroups_X_ocl run, and that the
required columns are present (including Origin_Phylogenetic_Block and
Origin_Phylogenetic_Path needed for gain-aware scoring). Cross-checks the
manifest's structure IDs against trees_species to make sure the IDs
correspond to real GIGANTIC structures, and confirms the trees_species
phylogenetic_blocks aggregate file exists (needed by script 002 for
Total_Blocks_Per_Structure / Inherited_Absence derivation).

Writes a per-structure validation report. Exits with code 1 on any critical
failure (fail-fast).
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml


REQUIRED_OCL_COLUMNS = [
    'Orthogroup_ID',
    'Origin_Phylogenetic_Block',
    'Origin_Phylogenetic_Path',
    'Species_Count',
    'Conservation_Events',
    'Loss_Events',
    'Continued_Absence_Events',
    'Total_Scored_Blocks',
]


def main():
    parser = argparse.ArgumentParser( description = 'Validate parsimony workflow inputs' )
    parser.add_argument( '--config', required = True, help = 'Path to START_HERE-user_config.yaml' )
    parser.add_argument( '--output_dir', required = True, help = 'Base OUTPUT_pipeline directory' )
    args = parser.parse_args()

    config_path = Path( args.config ).resolve()
    output_dir = Path( args.output_dir ).resolve()
    workflow_dir = config_path.parent

    output_1 = output_dir / '1-output'
    output_1.mkdir( parents = True, exist_ok = True )

    log_dir = workflow_dir / 'ai' / 'logs'
    log_dir.mkdir( parents = True, exist_ok = True )
    log_file = log_dir / '1_ai-log-validate_inputs.log'
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s',
        handlers = [ logging.FileHandler( log_file ), logging.StreamHandler() ],
    )
    logger = logging.getLogger( 'validate_inputs' )

    logger.info( 'Starting script 001: validate_inputs' )
    logger.info( f'Config: {config_path}' )

    with open( config_path ) as input_config:
        config = yaml.safe_load( input_config )

    ocl_orthogroups_dir = ( workflow_dir / config[ 'inputs' ][ 'ocl_orthogroups_dir' ] ).resolve()
    trees_species_dir = ( workflow_dir / config[ 'inputs' ][ 'trees_species_dir' ] ).resolve()
    structure_manifest_path = ( workflow_dir / config[ 'inputs' ][ 'structure_manifest' ] ).resolve()

    logger.info( f'ocl_orthogroups_dir = {ocl_orthogroups_dir}' )
    logger.info( f'trees_species_dir   = {trees_species_dir}' )
    logger.info( f'structure_manifest  = {structure_manifest_path}' )

    fatal_errors = []

    if not structure_manifest_path.is_file():
        fatal_errors.append( f'structure_manifest not found: {structure_manifest_path}' )
    if not ocl_orthogroups_dir.is_dir():
        fatal_errors.append( f'ocl_orthogroups_dir not found: {ocl_orthogroups_dir}' )
    if not trees_species_dir.is_dir():
        fatal_errors.append( f'trees_species_dir not found: {trees_species_dir}' )

    trees_species_blocks_file = trees_species_dir / 'Species_Phylogenetic_Blocks' / '6_ai-phylogenetic_blocks-all_105_structures.tsv'
    if not trees_species_blocks_file.is_file():
        fatal_errors.append( f'trees_species blocks aggregate file not found: {trees_species_blocks_file}' )

    if fatal_errors:
        for error in fatal_errors:
            logger.error( f'CRITICAL: {error}' )
        sys.exit( 1 )

    # Parse structure_manifest.tsv
    # structure_id
    # 001
    structure_ids = []
    with open( structure_manifest_path ) as input_manifest:
        header_seen = False
        for line in input_manifest:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue
            if not header_seen:
                if line != 'structure_id':
                    fatal_errors.append( f'structure_manifest header must be "structure_id"; got: {line!r}' )
                header_seen = True
                continue
            structure_ids.append( line )

    if not structure_ids:
        fatal_errors.append( 'structure_manifest is empty (no structure IDs after header)' )
        for error in fatal_errors:
            logger.error( f'CRITICAL: {error}' )
        sys.exit( 1 )

    logger.info( f'Structures to validate: {len( structure_ids )}' )

    # Per-structure validation
    rows = []
    columns_checked = False
    for structure_id in structure_ids:
        ocl_summary_path = ocl_orthogroups_dir / f'structure_{structure_id}' / '4_ai-orthogroups-complete_ocl_summary.tsv'

        if not ocl_summary_path.is_file():
            rows.append( ( structure_id, 'MISSING', str( ocl_summary_path ), 'OCL summary file not found' ) )
            continue

        if not columns_checked:
            with open( ocl_summary_path ) as input_summary:
                header_line = input_summary.readline().strip()
                parts_header_line = header_line.split( '\t' )
                header_ids = [ part.split( ' ' )[ 0 ] for part in parts_header_line ]
                missing_columns = [ column for column in REQUIRED_OCL_COLUMNS if column not in header_ids ]
            if missing_columns:
                logger.error( f'CRITICAL: required columns missing in {ocl_summary_path}: {missing_columns}' )
                logger.error( f'  found header columns: {header_ids}' )
                sys.exit( 1 )
            columns_checked = True
            logger.info( f'Required columns verified against: {ocl_summary_path}' )

        with open( ocl_summary_path ) as input_summary:
            row_count = sum( 1 for _ in input_summary ) - 1
        rows.append( ( structure_id, 'OK', str( ocl_summary_path ), f'{row_count} orthogroup rows' ) )

    # Cross-check structure IDs against trees_species manifest (warn only) and derive total_blocks_per_structure
    trees_species_structure_ids = set()
    structures_to_total_blocks = {}
    with open( trees_species_blocks_file ) as input_trees_species:
        input_trees_species.readline()  # header
        for line in input_trees_species:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ 0 ]
            # blocks file rows store structure_id like "structure_NNN" -- normalize to NNN
            if structure_id.startswith( 'structure_' ):
                structure_id = structure_id[ len( 'structure_' ): ]
            trees_species_structure_ids.add( structure_id )
            structures_to_total_blocks[ structure_id ] = structures_to_total_blocks.get( structure_id, 0 ) + 1
    unknown_ids = [ s for s in structure_ids if s not in trees_species_structure_ids ]
    if unknown_ids:
        logger.warning( f'Structure IDs not in trees_species manifest: {unknown_ids[ :10 ]} (showing first 10 of {len( unknown_ids )})' )

    # Confirm Total_Blocks_Per_Structure is constant across the manifest's structures
    block_counts = { structures_to_total_blocks.get( s, -1 ) for s in structure_ids if s in trees_species_structure_ids }
    if -1 in block_counts:
        block_counts.discard( -1 )
    logger.info( f'Total_Blocks_Per_Structure observed across requested structures: {sorted( block_counts )}' )

    output_report = output_1 / '1_ai-input_validation_report.tsv'
    with open( output_report, 'w' ) as output:
        output.write( 'Structure_ID (three digit identifier from manifest)' )
        output.write( '\tValidation_Status (OK or MISSING)' )
        output.write( '\tOCL_Summary_Path (absolute path to upstream OCL summary TSV)' )
        output.write( '\tTotal_Blocks_From_Trees_Species (number of phylogenetic blocks in this structure as derived from trees_species)' )
        output.write( '\tNotes (row count or error description)\n' )
        for structure_id, status, path, notes in rows:
            blocks = structures_to_total_blocks.get( structure_id, 0 )
            line = structure_id + '\t' + status + '\t' + path + '\t' + str( blocks ) + '\t' + notes + '\n'
            output.write( line )
    logger.info( f'Wrote validation report: {output_report}' )

    missing_rows = [ row for row in rows if row[ 1 ] == 'MISSING' ]
    if missing_rows:
        logger.error( f'CRITICAL: {len( missing_rows )} structure(s) missing OCL summary files' )
        for structure_id, _, path, _ in missing_rows[ :5 ]:
            logger.error( f'  structure_{structure_id}: {path}' )
        if len( missing_rows ) > 5:
            logger.error( f'  ... ({len( missing_rows ) - 5} more)' )
        sys.exit( 1 )

    logger.info( f'Validation passed: {len( rows )} structures OK' )


if __name__ == '__main__':
    main()
