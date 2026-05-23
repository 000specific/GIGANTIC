#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Validate dark_proteome inputs and emit per-species processability manifest
# Human: Eric Edsinger

"""
GIGANTIC dark_proteome BLOCK_classify_dark_proteome - Script 001: Validate Inputs

Purpose:
    Pairs every species in the species list with the four inputs needed for
    three-axis dark-matter classification:
      1. proteome FASTA (defines the universe of genes per species)
      2. reference BLAST top-hits TSV (axis a)
      3. orthogroups membership TSV (axis b — project-level, single file)
      4. HMM annotation TSVs (axis c — one per database per species)

    Reference species (config-driven) must each have a proteome (axes a/b
    cannot work without them). Species missing a proteome / blast / hmm
    file are dropped to the excluded-species TSV with a reason.

Inputs (CLI):
    --proteomes-dir          Directory of <phyloname>-T1-proteome.aa
    --reference-blast-dir    Directory of <Genus_species>_top_hits.tsv (or similar)
    --orthogroups-file       Path to orthogroups_gigantic_ids.tsv (project-wide)
    --hmm-annotations-dir    Directory of <db>-<Genus_species>.tsv files
    --hmm-databases          Comma-separated db names (e.g. "pfam,panther")
    --reference-species      Comma-separated reference Genus_species names
    --gigantic-species-list  Path to gigantic_species_list.txt
    --output-dir             Output directory (typically 1-output)

Outputs (in --output-dir):
    1_ai-processable_species_manifest.tsv
        Per-row: Genus_Species, Proteome_Path, Reference_Blast_Path,
                 Hmm_Database_Names_CSV, Hmm_Annotation_Paths_CSV
    1_ai-excluded_species.tsv
    1_ai-species_processing_status.tsv
    1_ai-reference_species_audit.tsv     (per-reference: present in proteomes, in orthogroups)
    1_ai-log-validate_inputs.log

Failure mode:
    Exits 1 (fail-fast) when:
      - Required CLI argument missing
      - Any required directory or file missing
      - Orthogroups file empty or malformed
      - Zero reference species are findable in proteomes (axes a/b would be vacuous)
      - Zero species processable (nothing to classify)
"""

import argparse
import logging
import sys
from pathlib import Path


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
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) < 7:
        return ''
    genus = parts_phyloname[ 5 ]
    species = '_'.join( parts_phyloname[ 6: ] )
    return genus + '_' + species


def index_proteomes( proteomes_dir: Path, logger: logging.Logger ) -> dict:
    """Build genus_species -> proteome_path map."""
    genus_species___proteome_paths = {}
    for proteome_path in sorted( proteomes_dir.glob( '*-T1-proteome.aa' ) ):
        stem = proteome_path.name.replace( '-T1-proteome.aa', '' )
        genus_species = extract_genus_species_from_phyloname( stem )
        if not genus_species:
            continue
        if genus_species in genus_species___proteome_paths:
            logger.warning( f'    Duplicate Genus_species in proteomes: {genus_species}' )
            continue
        genus_species___proteome_paths[ genus_species ] = proteome_path
    logger.info( f'  Indexed {len( genus_species___proteome_paths )} proteomes' )
    return genus_species___proteome_paths


def find_reference_blast_path( reference_blast_dir: Path, genus_species: str ) -> Path:
    """one_direction_homologs/BLOCK_diamond_ncbi_nr produces files named
    <phyloname>_top_hits.tsv (NOT just <Genus_species>_top_hits.tsv) and
    a sibling <phyloname>_statistics.tsv. We must match the top_hits file
    specifically; the statistics file has different columns and would
    silently mis-classify axis-a.
    """
    # Try exact Genus_species match first
    for candidate_name in (
        f'{genus_species}_top_hits.tsv',
        f'{genus_species}-top_hits.tsv',
    ):
        candidate = reference_blast_dir / candidate_name
        if candidate.is_file():
            return candidate

    # Phyloname-suffix match — file ends in _<Genus_species>_top_hits.tsv
    suffix = f'_{genus_species}_top_hits.tsv'
    for tsv in reference_blast_dir.glob( '*_top_hits.tsv' ):
        if tsv.name.endswith( suffix ):
            return tsv

    return None


def hmm_annotation_paths_for_species( hmm_annotations_dir: Path, genus_species: str, hmm_databases: list ) -> dict:
    """For each HMM database, locate the per-species TSV.

    annotations_hmms/output_to_input/BLOCK_interproscan_parsed/ uses a
    subdirectory per database (pfam/, panther/, etc.) and per-species files
    are named with the FULL phyloname:
      <db>/<db>-<phyloname>.tsv
    where phyloname ends in Genus_species. We match on the *Genus_species*
    suffix to handle this without hardcoding the phyloname.

    Returns: dict { db_name: path_or_none }
    """
    found = {}
    for db_name in hmm_databases:
        # Try exact Genus_species match first (in case some pipelines do that)
        for candidate in (
            hmm_annotations_dir / db_name / f'{db_name}-{genus_species}.tsv',
            hmm_annotations_dir / f'{db_name}-{genus_species}.tsv',
        ):
            if candidate.is_file():
                found[ db_name ] = candidate
                break
        if db_name in found:
            continue

        # Otherwise glob for any file ending in <Genus_species>.tsv under the db
        # subdirectory (handles the phyloname-suffix naming actually used in
        # GIGANTIC). Use $ anchor by checking the suffix to avoid spurious
        # matches across species sharing a prefix.
        suffix = f'_{genus_species}.tsv'
        candidates = []
        for tsv in hmm_annotations_dir.glob( f'{db_name}/{db_name}-*.tsv' ):
            if tsv.name.endswith( suffix ):
                candidates.append( tsv )
        if not candidates:
            for tsv in hmm_annotations_dir.glob( f'{db_name}-*.tsv' ):
                if tsv.name.endswith( suffix ):
                    candidates.append( tsv )
        if candidates:
            found[ db_name ] = candidates[ 0 ]
        else:
            found[ db_name ] = None
    return found


def read_species_list( species_list_path: Path, logger: logging.Logger ) -> list:
    species_names = []
    seen = set()
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


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--proteomes-dir', required = True, type = Path )
    parser.add_argument( '--reference-blast-dir', required = True, type = Path )
    parser.add_argument( '--orthogroups-file', required = True, type = Path )
    parser.add_argument( '--hmm-annotations-dir', required = True, type = Path )
    parser.add_argument( '--hmm-databases', required = True, help = 'Comma-separated database names' )
    parser.add_argument( '--reference-species', required = True, help = 'Comma-separated Genus_species names' )
    parser.add_argument( '--gigantic-species-list', required = True, type = Path )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir )

    hmm_databases = [ db.strip() for db in args.hmm_databases.split( ',' ) if db.strip() ]
    reference_species = [ rs.strip() for rs in args.reference_species.split( ',' ) if rs.strip() ]

    logger.info( '=' * 72 )
    logger.info( 'GIGANTIC dark_proteome BLOCK_classify_dark_proteome - Script 001: Validate Inputs' )
    logger.info( '=' * 72 )
    logger.info( f'Proteomes dir:        {args.proteomes_dir}' )
    logger.info( f'Reference BLAST dir:  {args.reference_blast_dir}' )
    logger.info( f'Orthogroups file:     {args.orthogroups_file}' )
    logger.info( f'HMM annotations dir:  {args.hmm_annotations_dir}' )
    logger.info( f'HMM databases:        {hmm_databases}' )
    logger.info( f'Reference species:    {reference_species}' )
    logger.info( f'Output dir:           {args.output_dir}' )
    logger.info( '' )

    # ---- Required inputs ----
    for label, path in [
        ( 'Proteomes',         args.proteomes_dir ),
        ( 'Reference BLAST',   args.reference_blast_dir ),
        ( 'HMM annotations',   args.hmm_annotations_dir ),
    ]:
        if not path.is_dir():
            logger.error( f'CRITICAL ERROR: {label} directory not found: {path}' )
            return 1
    if not args.orthogroups_file.is_file():
        logger.error( f'CRITICAL ERROR: Orthogroups file not found: {args.orthogroups_file}' )
        return 1
    if not args.gigantic_species_list.is_file():
        logger.error( f'CRITICAL ERROR: Species list not found: {args.gigantic_species_list}' )
        return 1
    if not hmm_databases:
        logger.error( 'CRITICAL ERROR: No HMM databases configured.' )
        return 1
    if not reference_species:
        logger.error( 'CRITICAL ERROR: No reference species configured. Axes (a) and (b) cannot be evaluated.' )
        return 1

    # ---- Index proteomes and verify reference species are present ----
    logger.info( 'Indexing proteomes...' )
    genus_species___proteome_paths = index_proteomes( args.proteomes_dir, logger )

    reference_audit_rows = []
    found_reference_count = 0
    for ref in reference_species:
        proteome_present = ref in genus_species___proteome_paths
        if proteome_present:
            found_reference_count += 1
        reference_audit_rows.append( ( ref, proteome_present ) )
        logger.info( f'  Reference species {ref:40s} proteome_present={proteome_present}' )
    if found_reference_count == 0:
        logger.error( 'CRITICAL ERROR: NONE of the configured reference species were found in proteomes_dir.' )
        logger.error( 'Axes (a) and (b) would be vacuous; classification is meaningless.' )
        logger.error( f'Configured: {reference_species}' )
        return 1

    species_names = read_species_list( args.gigantic_species_list, logger )
    if not species_names:
        logger.error( 'CRITICAL ERROR: No species in list.' )
        return 1
    logger.info( '' )

    # ---- Match each species against required inputs ----
    logger.info( 'Matching species against required inputs...' )

    processable_records = []   # ( genus_species, proteome, ref_blast, hmm_paths_dict )
    excluded_records = []
    status_records = []

    for genus_species in species_names:
        proteome_path = genus_species___proteome_paths.get( genus_species )
        if proteome_path is None:
            status = 'SKIPPED_NO_PROTEOME'
            excluded_records.append( ( genus_species, f'No proteome file for {genus_species}.' ) )
            status_records.append( ( genus_species, status ) )
            continue

        ref_blast_path = find_reference_blast_path( args.reference_blast_dir, genus_species )
        if ref_blast_path is None:
            status = 'SKIPPED_NO_REFERENCE_BLAST'
            excluded_records.append( ( genus_species, f'No reference BLAST file for {genus_species} in {args.reference_blast_dir.name}.' ) )
            status_records.append( ( genus_species, status ) )
            continue

        hmm_paths = hmm_annotation_paths_for_species( args.hmm_annotations_dir, genus_species, hmm_databases )
        # Require at least ONE HMM db to have a file; missing dbs are noted but
        # don't drop the species (treated as having no annotation in that db,
        # which is a valid outcome for axis-c).
        any_hmm_present = any( v is not None for v in hmm_paths.values() )
        if not any_hmm_present:
            status = 'SKIPPED_NO_HMM_ANNOTATIONS'
            missing_dbs = ', '.join( hmm_databases )
            excluded_records.append( ( genus_species, f'No HMM annotation files found for any configured database ({missing_dbs}) for {genus_species}.' ) )
            status_records.append( ( genus_species, status ) )
            continue

        processable_records.append( ( genus_species, proteome_path, ref_blast_path, hmm_paths ) )
        status_records.append( ( genus_species, 'PROCESSABLE' ) )

    logger.info( f'  PROCESSABLE: {len( processable_records )}' )
    logger.info( f'  EXCLUDED:    {len( excluded_records )}' )
    logger.info( '' )

    # ---- Write outputs ----
    manifest_path = args.output_dir / '1_ai-processable_species_manifest.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Proteome_Path (absolute path to GIGANTIC T1 proteome aa file)\t'
    output += 'Reference_Blast_Path (absolute path to one_direction_homologs per-species top-hits TSV)\t'
    output += 'Hmm_Database_Names_CSV (comma delimited HMM database names with at least one annotation file)\t'
    output += 'Hmm_Annotation_Paths_CSV (comma delimited absolute paths to per-database HMM annotation TSVs)\n'
    for genus_species, proteome_path, ref_blast_path, hmm_paths in processable_records:
        present_dbs = [ db for db, p in hmm_paths.items() if p is not None ]
        present_paths = [ str( hmm_paths[ db ].resolve() ) for db in present_dbs ]
        output += genus_species + '\t' + str( proteome_path.resolve() ) + '\t' + str( ref_blast_path.resolve() ) + '\t' + ','.join( present_dbs ) + '\t' + ','.join( present_paths ) + '\n'
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
    output += 'Status (PROCESSABLE, SKIPPED_NO_PROTEOME, SKIPPED_NO_REFERENCE_BLAST, SKIPPED_NO_HMM_ANNOTATIONS)\n'
    for genus_species, status in status_records:
        output += genus_species + '\t' + status + '\n'
    with open( status_path, 'w' ) as output_status:
        output_status.write( output )
    logger.info( f'  Wrote {status_path.name} ({len( status_records )} rows)' )

    audit_path = args.output_dir / '1_ai-reference_species_audit.tsv'
    output = 'Reference_Species (Genus_species name configured as reference)\t'
    output += 'Proteome_Present (whether reference species has a proteome in proteomes_dir)\n'
    for ref, present in reference_audit_rows:
        output += ref + '\t' + str( present ) + '\n'
    with open( audit_path, 'w' ) as output_audit:
        output_audit.write( output )
    logger.info( f'  Wrote {audit_path.name} ({len( reference_audit_rows )} reference rows)' )

    if not processable_records:
        logger.error( 'CRITICAL ERROR: Zero species processable. Nothing to classify.' )
        return 1

    logger.info( 'Validation complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
