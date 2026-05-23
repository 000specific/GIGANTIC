#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Validate hotspot identification inputs and emit per-species processability manifest
# Human: Eric Edsinger

"""
GIGANTIC hotspots BLOCK_identify_hotspots - Script 001: Validate Inputs

Purpose:
    Pairs every species in the species list with its three required inputs:
      - Self-BLAST report from BLOCK_self_blast
      - User-provided gene-coordinate TSV (from research_notebook/research_user)
      - GIGANTIC proteome FASTA (for ID linkage)

    Validates that each gene-coordinate TSV has the required columns and is
    parseable. Species missing any input or with a malformed gene-coordinate
    TSV are reported in the excluded-species TSV with a reason.

Inputs (CLI):
    --self-blast-reports-dir   Directory of <Genus_species>-self_blast.tsv
                               files (from BLOCK_self_blast)
    --gene-coordinates-dir     Directory of <Genus_species>-gene_coordinates.tsv
                               files (user-provided)
    --proteomes-dir            Directory of <phyloname>-T1-proteome.aa files
    --gigantic-species-list    Path to gigantic_species_list.txt
    --output-dir               Output directory (typically 1-output)

Outputs (in --output-dir):
    1_ai-processable_species_manifest.tsv
        Per-row: Genus_Species, Self_Blast_Report_Path, Gene_Coordinates_Path,
                 Proteome_Path

    1_ai-excluded_species.tsv
        Per-row: Genus_Species, Reason_Excluded

    1_ai-species_processing_status.tsv
        Per-row: Genus_Species, Status

    1_ai-log-validate_inputs.log

Failure mode:
    Exits 1 (fail-fast) when:
      - Required CLI argument missing
      - Species list empty/unreadable
      - Any input directory missing
      - Zero species processable
"""

import argparse
import logging
import sys
from pathlib import Path


REQUIRED_GENE_COORDINATE_COLUMNS = [
    'Source_Gene_ID',
    'Seqid',
    'Gene_Start',
    'Gene_End',
    'Strand',
]


def setup_logging( output_dir: Path ) -> logging.Logger:
    logger = logging.getLogger( 'validate_inputs' )
    logger.setLevel( logging.INFO )

    log_file = output_dir / '1_ai-log-validate_inputs.log'
    file_handler = logging.FileHandler( log_file, mode = 'w' )
    file_handler.setLevel( logging.INFO )
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )

    formatter = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( formatter )
    console_handler.setFormatter( formatter )

    logger.addHandler( file_handler )
    logger.addHandler( console_handler )
    return logger


def extract_genus_species_from_phyloname( phyloname: str ) -> str:
    """Genus_species from a GIGANTIC phyloname (per CLAUDE.md convention)."""
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) < 7:
        return ''
    genus = parts_phyloname[ 5 ]
    species = '_'.join( parts_phyloname[ 6: ] )
    return genus + '_' + species


def index_proteomes( proteomes_dir: Path, logger: logging.Logger ) -> dict:
    """Build genus_species -> proteome_path map from <phyloname>-T1-proteome.aa files."""
    genus_species___proteome_paths = {}
    for proteome_file in sorted( proteomes_dir.glob( '*-T1-proteome.aa' ) ):
        stem = proteome_file.name.replace( '-T1-proteome.aa', '' )
        genus_species = extract_genus_species_from_phyloname( stem )
        if not genus_species:
            continue
        if genus_species in genus_species___proteome_paths:
            logger.warning( f'    Duplicate Genus_species in proteomes: {genus_species}' )
            continue
        genus_species___proteome_paths[ genus_species ] = proteome_file
    logger.info( f'  Indexed {len( genus_species___proteome_paths )} proteomes' )
    return genus_species___proteome_paths


def read_species_list( species_list_path: Path, logger: logging.Logger ) -> list:
    """Read the GIGANTIC species list (one Genus_species per line, # comments allowed)."""
    species_names = []
    seen = set()

    # Homo_sapiens
    # Mus_musculus
    with open( species_list_path, 'r' ) as input_species_list:
        for line in input_species_list:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue
            if line in seen:
                continue
            seen.add( line )
            species_names.append( line )

    logger.info( f'  Read {len( species_names )} unique species names' )
    return species_names


def validate_gene_coordinates_file( coords_path: Path ) -> tuple:
    """Verify the TSV has the required columns and at least one data row.

    Returns: ( ok, error_message_or_empty )
    """
    if not coords_path.is_file():
        return False, f'Gene coordinates file not found: {coords_path.name}'

    # Source_Gene_ID\tSeqid\tGene_Start\tGene_End\tStrand\t[...]
    # ENSG00000139618\tchr13\t32315474\t32400266\t+\t[...]
    with open( coords_path, 'r' ) as input_coords:
        header_line = input_coords.readline()
        if not header_line:
            return False, 'Gene coordinates file is empty'
        header_line = header_line.rstrip( '\n' )
        # Header values may include the self-documenting "(...)" suffix.
        # Strip it before checking required columns.
        header_columns = []
        for raw in header_line.split( '\t' ):
            base = raw.split( ' (' )[ 0 ].strip()
            header_columns.append( base )
        for required in REQUIRED_GENE_COORDINATE_COLUMNS:
            if required not in header_columns:
                return False, f'Missing required column "{required}" in gene coordinates header'

        # Verify at least one data row exists
        for data_line in input_coords:
            data_line = data_line.strip()
            if data_line and not data_line.startswith( '#' ):
                return True, ''
        return False, 'Gene coordinates file has header but no data rows'


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--self-blast-reports-dir', required = True, type = Path )
    parser.add_argument( '--gene-coordinates-dir', required = True, type = Path )
    parser.add_argument( '--proteomes-dir', required = True, type = Path )
    parser.add_argument( '--gigantic-species-list', required = True, type = Path )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir )

    logger.info( '=' * 72 )
    logger.info( 'GIGANTIC hotspots BLOCK_identify_hotspots - Script 001: Validate Inputs' )
    logger.info( '=' * 72 )
    logger.info( f'Self-BLAST reports dir:  {args.self_blast_reports_dir}' )
    logger.info( f'Gene coordinates dir:    {args.gene_coordinates_dir}' )
    logger.info( f'Proteomes dir:           {args.proteomes_dir}' )
    logger.info( f'Species list:            {args.gigantic_species_list}' )
    logger.info( f'Output dir:              {args.output_dir}' )
    logger.info( '' )

    # ---- Validate required dirs / files ----
    for label, path in [
        ( 'Self-BLAST reports', args.self_blast_reports_dir ),
        ( 'Gene coordinates',   args.gene_coordinates_dir ),
        ( 'Proteomes',          args.proteomes_dir ),
    ]:
        if not path.is_dir():
            logger.error( f'CRITICAL ERROR: {label} directory not found: {path}' )
            logger.error( 'Fix: Edit START_HERE-user_config.yaml to point at the correct directory.' )
            return 1
    if not args.gigantic_species_list.is_file():
        logger.error( f'CRITICAL ERROR: Species list not found: {args.gigantic_species_list}' )
        return 1

    # ---- Index inputs ----
    logger.info( 'Indexing proteomes...' )
    genus_species___proteome_paths = index_proteomes( args.proteomes_dir, logger )
    logger.info( '' )

    species_names = read_species_list( args.gigantic_species_list, logger )
    if not species_names:
        logger.error( 'CRITICAL ERROR: No species in list (file empty after stripping comments).' )
        return 1
    logger.info( '' )

    # ---- Match species against inputs ----
    logger.info( 'Matching species against required inputs...' )

    processable_records = []   # ( genus_species, blast_path, coords_path, proteome_path )
    excluded_records = []      # ( genus_species, reason )
    status_records = []        # ( genus_species, status )

    for genus_species in species_names:
        blast_path = args.self_blast_reports_dir / f'{genus_species}-self_blast.tsv'
        coords_path = args.gene_coordinates_dir / f'{genus_species}-gene_coordinates.tsv'
        proteome_path = genus_species___proteome_paths.get( genus_species )

        if not blast_path.exists():
            status = 'SKIPPED_NO_SELF_BLAST_REPORT'
            reason = f'Self-BLAST report missing: {blast_path.name}. Run BLOCK_self_blast for this species first.'
            excluded_records.append( ( genus_species, reason ) )
            status_records.append( ( genus_species, status ) )
            continue

        if proteome_path is None:
            status = 'SKIPPED_NO_PROTEOME'
            reason = f'No proteome file for {genus_species} in {args.proteomes_dir.name}.'
            excluded_records.append( ( genus_species, reason ) )
            status_records.append( ( genus_species, status ) )
            continue

        coords_ok, coords_err = validate_gene_coordinates_file( coords_path )
        if not coords_ok:
            status = 'SKIPPED_NO_GENE_COORDINATES' if 'not found' in coords_err else 'SKIPPED_BAD_GENE_COORDINATES'
            reason = coords_err
            excluded_records.append( ( genus_species, reason ) )
            status_records.append( ( genus_species, status ) )
            continue

        processable_records.append( ( genus_species, blast_path, coords_path, proteome_path ) )
        status_records.append( ( genus_species, 'PROCESSABLE' ) )

    logger.info( f'  PROCESSABLE: {len( processable_records )}' )
    logger.info( f'  EXCLUDED:    {len( excluded_records )}' )
    logger.info( '' )

    # ---- Write outputs ----
    manifest_path = args.output_dir / '1_ai-processable_species_manifest.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Self_Blast_Report_Path (absolute path to BLOCK_self_blast per-species report)\t'
    output += 'Gene_Coordinates_Path (absolute path to user-provided gene coordinates TSV)\t'
    output += 'Proteome_Path (absolute path to GIGANTIC T1 proteome aa file)\n'
    for genus_species, blast_path, coords_path, proteome_path in processable_records:
        output += genus_species + '\t' + str( blast_path.resolve() ) + '\t' + str( coords_path.resolve() ) + '\t' + str( proteome_path.resolve() ) + '\n'
    with open( manifest_path, 'w' ) as output_manifest:
        output_manifest.write( output )
    logger.info( f'  Wrote {manifest_path.name} ({len( processable_records )} rows)' )

    excluded_path = args.output_dir / '1_ai-excluded_species.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Reason_Excluded (description of why this species could not be processed)\n'
    for genus_species, reason in excluded_records:
        output += genus_species + '\t' + reason + '\n'
    with open( excluded_path, 'w' ) as output_excluded:
        output_excluded.write( output )
    logger.info( f'  Wrote {excluded_path.name} ({len( excluded_records )} rows)' )

    status_path = args.output_dir / '1_ai-species_processing_status.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Status (PROCESSABLE, SKIPPED_NO_SELF_BLAST_REPORT, SKIPPED_NO_PROTEOME, SKIPPED_NO_GENE_COORDINATES, SKIPPED_BAD_GENE_COORDINATES)\n'
    for genus_species, status in status_records:
        output += genus_species + '\t' + status + '\n'
    with open( status_path, 'w' ) as output_status:
        output_status.write( output )
    logger.info( f'  Wrote {status_path.name} ({len( status_records )} rows)' )

    if not processable_records:
        logger.error( '' )
        logger.error( 'CRITICAL ERROR: Zero species are processable. Nothing to compute.' )
        logger.error( f'See {excluded_path.name} for per-species reasons.' )
        return 1

    logger.info( '' )
    logger.info( 'Validation complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
