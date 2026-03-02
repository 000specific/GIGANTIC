#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Validate user-provided gene size inputs and determine species processing status
# Human: Eric Edsinger

"""
GIGANTIC gene_sizes - Script 001: Validate Gene Size Inputs

Purpose:
    Validates user-provided gene structure TSV files in INPUT_user/ against
    the GIGANTIC species set. Determines which species can be processed
    (have valid gene structure data) and which must be skipped (no data
    or incomplete data). Produces a species processing status report.

    This follows GIGANTIC's established pattern: the user handles species-
    specific GFF/GTF parsing and provides standardized gene structure data.
    The pipeline ingests and processes what the user provides.

Inputs:
    --input-dir: Path to INPUT_user/ containing per-species gene structure TSVs
    --gigantic-species-list: Path to GIGANTIC species list (all species in set)
    --output-dir: Output directory

    User-provided TSV format (one file per species, named Genus_species-gene_coordinates.tsv):
        Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  CDS_Intervals
        ENSG00000139618  chr13  32315474  32400266  +  32316422-32316527,32319077-32319325

Outputs:
    1-output/1_ai-species_processing_status.tsv - All species with status and reason
    1-output/1_ai-processable_species_list.txt - Species that will be processed
    1-output/1_ai-species_count.txt - Number of processable species
    1-output/1_ai-log-validate_gene_size_inputs.log - Execution log
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger( 'validate_gene_size_inputs' )
    logger.setLevel( logging.INFO )

    log_file = output_dir / '1_ai-log-validate_gene_size_inputs.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.INFO )

    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )

    return logger


def load_gigantic_species_list( species_list_file: Path ) -> list:
    """Load the full GIGANTIC species list."""
    species_names = []

    with open( species_list_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if line and not line.startswith( '#' ):
                species_names.append( line )

    return sorted( species_names )


def validate_gene_structure_file( gene_structure_file: Path, genus_species: str, logger: logging.Logger ) -> dict:
    """Validate a user-provided gene structure TSV file.

    Returns a dictionary with:
        'status': 'PROCESSED' or 'SKIPPED_INCOMPLETE'
        'reason': Human-readable reason for status
        'gene_count': Number of valid genes found
        'file_path': Resolved path to the file
    """
    if not gene_structure_file.exists():
        return {
            'status': 'SKIPPED_NO_DATA',
            'reason': 'No gene structure file provided by user',
            'gene_count': 0,
            'file_path': ''
        }

    valid_gene_count = 0
    invalid_line_count = 0
    missing_cds_count = 0
    header_found = False

    # Source_Gene_ID (source gene identifier)	Seqid (chromosome or scaffold)	Gene_Start (gene start position bp)	Gene_End (gene end position bp)	Strand (plus or minus strand)	CDS_Intervals (comma separated start-end pairs for coding sequence intervals)
    # ENSG00000139618	chr13	32315474	32400266	+	32316422-32316527,32319077-32319325,32325076-32325184
    with open( gene_structure_file, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()

            if not line or line.startswith( '#' ):
                continue

            # Skip header line
            if not header_found:
                if line.startswith( 'Source_Gene_ID' ):
                    header_found = True
                    continue
                else:
                    # First non-comment line is not a header - treat as data
                    header_found = True

            parts = line.split( '\t' )

            if len( parts ) < 6:
                invalid_line_count += 1
                continue

            source_gene_id = parts[ 0 ].strip()
            seqid = parts[ 1 ].strip()
            cds_intervals_string = parts[ 5 ].strip()

            # Validate required fields are non-empty
            if not source_gene_id or not seqid:
                invalid_line_count += 1
                continue

            # Validate gene start and end are integers
            try:
                gene_start = int( parts[ 2 ] )
                gene_end = int( parts[ 3 ] )
            except ValueError:
                invalid_line_count += 1
                continue

            if gene_start >= gene_end:
                invalid_line_count += 1
                continue

            # Validate CDS intervals
            if not cds_intervals_string:
                missing_cds_count += 1
                continue

            # Parse CDS intervals: start-end,start-end,...
            cds_valid = True
            parts_cds_intervals = cds_intervals_string.split( ',' )
            for interval_string in parts_cds_intervals:
                interval_string = interval_string.strip()
                parts_interval = interval_string.split( '-' )
                if len( parts_interval ) != 2:
                    cds_valid = False
                    break
                try:
                    interval_start = int( parts_interval[ 0 ] )
                    interval_end = int( parts_interval[ 1 ] )
                    if interval_start >= interval_end:
                        cds_valid = False
                        break
                except ValueError:
                    cds_valid = False
                    break

            if not cds_valid:
                invalid_line_count += 1
                continue

            valid_gene_count += 1

    # Determine status
    if valid_gene_count == 0:
        if missing_cds_count > 0:
            return {
                'status': 'SKIPPED_INCOMPLETE',
                'reason': f'File has gene entries but all {missing_cds_count} lack CDS intervals',
                'gene_count': 0,
                'file_path': str( gene_structure_file.resolve() )
            }
        elif invalid_line_count > 0:
            return {
                'status': 'SKIPPED_INCOMPLETE',
                'reason': f'File has {invalid_line_count} lines but none passed validation',
                'gene_count': 0,
                'file_path': str( gene_structure_file.resolve() )
            }
        else:
            return {
                'status': 'SKIPPED_INCOMPLETE',
                'reason': 'File exists but contains no gene data',
                'gene_count': 0,
                'file_path': str( gene_structure_file.resolve() )
            }

    # Log warnings for partial data
    if invalid_line_count > 0:
        logger.warning( f'  {genus_species}: {invalid_line_count} invalid lines skipped' )
    if missing_cds_count > 0:
        logger.warning( f'  {genus_species}: {missing_cds_count} genes without CDS intervals skipped' )

    return {
        'status': 'PROCESSED',
        'reason': f'{valid_gene_count} genes validated',
        'gene_count': valid_gene_count,
        'file_path': str( gene_structure_file.resolve() )
    }


def main():
    parser = argparse.ArgumentParser(
        description = 'Validate user-provided gene size inputs'
    )
    parser.add_argument( '--input-dir', required = True,
                        help = 'Path to INPUT_user/ containing per-species TSVs' )
    parser.add_argument( '--gigantic-species-list', required = True,
                        help = 'Path to GIGANTIC species list (all species)' )
    parser.add_argument( '--output-dir', required = True,
                        help = 'Output directory' )

    args = parser.parse_args()

    input_dir = Path( args.input_dir )
    gigantic_species_list_file = Path( args.gigantic_species_list )
    output_dir = Path( args.output_dir )

    output_dir.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( output_dir )

    logger.info( '=' * 70 )
    logger.info( 'GIGANTIC gene_sizes - Validate Gene Size Inputs' )
    logger.info( '=' * 70 )

    # Validate inputs
    if not input_dir.exists():
        logger.error( f'CRITICAL ERROR: Input directory not found: {input_dir}' )
        sys.exit( 1 )

    if not gigantic_species_list_file.exists():
        logger.error( f'CRITICAL ERROR: Species list not found: {gigantic_species_list_file}' )
        logger.error( '  Ensure genomesDB STEP_4 has completed successfully.' )
        sys.exit( 1 )

    # Load GIGANTIC species list
    gigantic_species = load_gigantic_species_list( gigantic_species_list_file )
    logger.info( f'GIGANTIC species set: {len( gigantic_species )} species' )

    # Check each species for gene structure data
    logger.info( '' )
    logger.info( 'Validating gene structure files...' )

    species_statuses = []
    processable_species = []

    for genus_species in gigantic_species:
        # Look for user-provided file: Genus_species-gene_coordinates.tsv
        gene_structure_file = input_dir / f'{genus_species}-gene_coordinates.tsv'

        validation_result = validate_gene_structure_file( gene_structure_file, genus_species, logger )

        species_statuses.append( {
            'genus_species': genus_species,
            'status': validation_result[ 'status' ],
            'reason': validation_result[ 'reason' ],
            'gene_count': validation_result[ 'gene_count' ],
            'file_path': validation_result[ 'file_path' ]
        } )

        if validation_result[ 'status' ] == 'PROCESSED':
            processable_species.append( genus_species )
            logger.info( f'  PROCESSED: {genus_species} ({validation_result[ "gene_count" ]} genes)' )
        elif validation_result[ 'status' ] == 'SKIPPED_NO_DATA':
            logger.info( f'  SKIPPED_NO_DATA: {genus_species}' )
        else:
            logger.warning( f'  SKIPPED_INCOMPLETE: {genus_species} - {validation_result[ "reason" ]}' )

    # Summary counts
    processed_count = len( processable_species )
    no_data_count = sum( 1 for status in species_statuses if status[ 'status' ] == 'SKIPPED_NO_DATA' )
    incomplete_count = sum( 1 for status in species_statuses if status[ 'status' ] == 'SKIPPED_INCOMPLETE' )

    logger.info( '' )
    logger.info( f'Species processing summary:' )
    logger.info( f'  PROCESSED: {processed_count}' )
    logger.info( f'  SKIPPED_NO_DATA: {no_data_count}' )
    logger.info( f'  SKIPPED_INCOMPLETE: {incomplete_count}' )
    logger.info( f'  Total in GIGANTIC set: {len( gigantic_species )}' )

    if processed_count == 0:
        logger.error( '' )
        logger.error( 'CRITICAL ERROR: No species have valid gene structure data!' )
        logger.error( '  Provide per-species TSV files in INPUT_user/ (Genus_species-gene_coordinates.tsv)' )
        logger.error( '  See README.md for the required input format.' )
        sys.exit( 1 )

    # Write species processing status report
    status_file = output_dir / '1_ai-species_processing_status.tsv'
    with open( status_file, 'w' ) as output_file:
        output = 'Genus_Species (species name)' + '\t' + \
                 'Status (PROCESSED or SKIPPED_NO_DATA or SKIPPED_INCOMPLETE)' + '\t' + \
                 'Reason (explanation of status)' + '\t' + \
                 'Gene_Count (number of valid genes or 0 if skipped)' + '\t' + \
                 'File_Path (path to input file or empty if no file)' + '\n'
        output_file.write( output )

        for species_status in species_statuses:
            output = species_status[ 'genus_species' ] + '\t' + \
                     species_status[ 'status' ] + '\t' + \
                     species_status[ 'reason' ] + '\t' + \
                     str( species_status[ 'gene_count' ] ) + '\t' + \
                     species_status[ 'file_path' ] + '\n'
            output_file.write( output )

    logger.info( f'Wrote species processing status: {status_file}' )

    # Write processable species list
    processable_list_file = output_dir / '1_ai-processable_species_list.txt'
    with open( processable_list_file, 'w' ) as output_file:
        for genus_species in processable_species:
            output = genus_species + '\n'
            output_file.write( output )

    logger.info( f'Wrote processable species list: {processable_list_file}' )

    # Write species count
    species_count_file = output_dir / '1_ai-species_count.txt'
    with open( species_count_file, 'w' ) as output_file:
        output = str( processed_count ) + '\n'
        output_file.write( output )

    logger.info( f'Wrote species count: {species_count_file} ({processed_count})' )

    logger.info( '' )
    logger.info( '=' * 70 )
    logger.info( f'SUCCESS: {processed_count} of {len( gigantic_species )} species will be processed' )
    if no_data_count > 0:
        logger.info( f'  {no_data_count} species skipped (no gene structure data provided)' )
    if incomplete_count > 0:
        logger.info( f'  {incomplete_count} species skipped (incomplete data)' )
    logger.info( '=' * 70 )


if __name__ == '__main__':
    main()
