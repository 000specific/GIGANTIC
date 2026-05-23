#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Validate hotspots self-BLAST inputs and emit per-species processability manifest
# Human: Eric Edsinger

"""
GIGANTIC hotspots BLOCK_self_blast - Script 001: Validate Inputs

Purpose:
    Pairs every species in the GIGANTIC species list with its proteome FASTA
    and its pre-built blastp database. Emits a per-species processability
    manifest used to drive the fan-out in main.nf.

    Species missing a proteome OR a BLAST database are reported in an
    excluded-species TSV (with reason) and dropped from the processable
    list. The pipeline continues with the remaining species — silent
    omission is forbidden, so every drop is documented.

Inputs (CLI):
    --proteomes-dir          Directory of <phyloname>-T1-proteome.aa files
    --blast-db-dir           Directory of pre-built blastp DBs (file stems
                             match the proteome filenames; presence of a
                             .pdb or .pin file indicates a usable DB)
    --gigantic-species-list  Path to gigantic_species_list.txt (one
                             Genus_species per line; comments allowed)
    --output-dir             Output directory (typically 1-output)

Outputs (in --output-dir):
    1_ai-processable_species_manifest.tsv
        Per-row: Genus_species, Phyloname, Proteome_Path, Blast_Db_Stem
        Only species with both a proteome and a BLAST DB.

    1_ai-excluded_species.tsv
        Per-row: Genus_species, Reason_Excluded
        Species that could not be processed.

    1_ai-species_processing_status.tsv
        Per-row: Genus_species, Status (PROCESSABLE, SKIPPED_NO_PROTEOME,
                 SKIPPED_NO_BLAST_DB, SKIPPED_DUPLICATE_PROTEOME)
        Full audit trail of every species in the input list.

    1_ai-log-validate_inputs.log

Failure mode:
    Exits 1 (fail-fast) when:
      - Any required CLI argument is missing
      - The species list is empty or unreadable
      - The proteomes/blast-db dirs do not exist
      - Zero species are processable (nothing to BLAST)
    Per-species missing inputs do NOT fail the pipeline — they are reported
    in the excluded-species TSV. The drop is documented, not silent.
"""

import argparse
import logging
import re
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    """Set up logging to both file and console."""
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
    """Extract Genus_species from a GIGANTIC phyloname.

    Phyloname format (per CLAUDE.md):
        Kingdom_Phylum_Class_Order_Family_Genus_species
        positions:   0       1      2     3      4     5     6:

    Multi-word species names (e.g., 'sapiens_neanderthalensis') are
    preserved by joining parts[6:].

    Returns empty string when phyloname has fewer than 7 fields.
    """
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) < 7:
        return ''
    genus = parts_phyloname[ 5 ]
    species = '_'.join( parts_phyloname[ 6: ] )
    return genus + '_' + species


def index_proteomes( proteomes_dir: Path, logger: logging.Logger ) -> dict:
    """Build genus_species -> (phyloname, proteome_path) mapping.

    Walks proteomes_dir for <phyloname>-T1-proteome.aa files. Uses CLAUDE.md
    phyloname convention to derive Genus_species per file.

    Returns: genus_species___proteome_records dictionary
        value = ( phyloname, proteome_path )
    Duplicate Genus_species entries (two proteomes for the same species) are
    flagged in the log AND in the returned duplicates list.
    """
    genus_species___proteome_records = {}
    duplicate_genus_species = []

    proteome_files = sorted( proteomes_dir.glob( '*-T1-proteome.aa' ) )
    logger.info( f'  Indexing {len( proteome_files )} proteome files in {proteomes_dir}' )

    for proteome_file in proteome_files:
        # Strip the trailing -T1-proteome.aa to get phyloname
        # Example basename: Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens-T1-proteome.aa
        stem = proteome_file.name.replace( '-T1-proteome.aa', '' )
        genus_species = extract_genus_species_from_phyloname( stem )

        if not genus_species:
            logger.warning( f'    Could not extract Genus_species from phyloname: {stem}' )
            continue

        if genus_species in genus_species___proteome_records:
            duplicate_genus_species.append( genus_species )
            logger.warning( f'    Duplicate Genus_species: {genus_species} ({proteome_file.name})' )
            continue

        genus_species___proteome_records[ genus_species ] = ( stem, proteome_file )

    logger.info( f'  Indexed {len( genus_species___proteome_records )} unique Genus_species from proteomes' )
    if duplicate_genus_species:
        logger.warning( f'  {len( duplicate_genus_species )} duplicate Genus_species detected (excluded from processable set)' )

    return genus_species___proteome_records, duplicate_genus_species


def index_blast_dbs( blast_db_dir: Path, logger: logging.Logger ) -> set:
    """Return set of file stems for which a usable blastp DB exists.

    A DB is considered usable when both a .pdb and .pin file are present
    (those are the protein-DB blastp metadata + index files). The stem is
    the proteome filename including '.aa' (BLAST DBs in genomesDB are built
    on the .aa file directly).
    """
    blast_db_stems = set()

    pdb_files = sorted( blast_db_dir.glob( '*-T1-proteome.aa.pdb' ) )
    pin_files = { f.name for f in blast_db_dir.glob( '*-T1-proteome.aa.pin' ) }

    for pdb in pdb_files:
        stem_with_aa = pdb.name[ : -len( '.pdb' ) ]   # strip .pdb only
        pin_name = stem_with_aa + '.pin'
        if pin_name in pin_files:
            blast_db_stems.add( stem_with_aa )

    logger.info( f'  Found {len( blast_db_stems )} usable blastp DBs in {blast_db_dir}' )
    return blast_db_stems


def read_species_list( species_list_path: Path, logger: logging.Logger ) -> list:
    """Read the GIGANTIC species list file.

    File format:
        # Optional comment lines start with #
        Homo_sapiens
        Mus_musculus
        ...
    Returns ordered list (preserves input order; dedupes silently).
    """
    seen = set()
    species_names = []

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

    logger.info( f'  Read {len( species_names )} unique species names from {species_list_path.name}' )
    return species_names


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--proteomes-dir', required = True, type = Path )
    parser.add_argument( '--blast-db-dir', required = True, type = Path )
    parser.add_argument( '--gigantic-species-list', required = True, type = Path )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir )

    logger.info( '=' * 72 )
    logger.info( 'GIGANTIC hotspots BLOCK_self_blast - Script 001: Validate Inputs' )
    logger.info( '=' * 72 )
    logger.info( f'Proteomes dir:     {args.proteomes_dir}' )
    logger.info( f'BLAST DB dir:      {args.blast_db_dir}' )
    logger.info( f'Species list:      {args.gigantic_species_list}' )
    logger.info( f'Output dir:        {args.output_dir}' )
    logger.info( '' )

    # ---- Fail-fast validation of required inputs ----
    if not args.proteomes_dir.is_dir():
        logger.error( f'CRITICAL ERROR: Proteomes directory not found or not a directory: {args.proteomes_dir}' )
        logger.error( 'Fix: Edit START_HERE-user_config.yaml to point at the correct directory.' )
        return 1
    if not args.blast_db_dir.is_dir():
        logger.error( f'CRITICAL ERROR: BLAST DB directory not found or not a directory: {args.blast_db_dir}' )
        logger.error( 'Fix: Edit START_HERE-user_config.yaml to point at the correct directory.' )
        return 1
    if not args.gigantic_species_list.is_file():
        logger.error( f'CRITICAL ERROR: GIGANTIC species list not found: {args.gigantic_species_list}' )
        logger.error( 'Fix: Copy the species list from genomesDB/output_to_input/STEP_4-create_final_species_set/' )
        logger.error( '     speciesN_gigantic_species_list/species_list.txt into INPUT_user/gigantic_species_list.txt' )
        return 1

    # ---- Index inputs ----
    logger.info( 'Indexing proteomes...' )
    genus_species___proteome_records, duplicate_genus_species = index_proteomes( args.proteomes_dir, logger )
    logger.info( '' )

    logger.info( 'Indexing BLAST DBs...' )
    blast_db_stems = index_blast_dbs( args.blast_db_dir, logger )
    logger.info( '' )

    species_names = read_species_list( args.gigantic_species_list, logger )
    if not species_names:
        logger.error( 'CRITICAL ERROR: No species found in species list (file empty after stripping comments).' )
        return 1
    logger.info( '' )

    # ---- Match species against indexes ----
    logger.info( 'Matching species against proteomes and BLAST DBs...' )

    processable_records = []     # ( genus_species, phyloname, proteome_path, blast_db_stem )
    excluded_records = []        # ( genus_species, reason )
    status_records = []          # ( genus_species, status )

    for genus_species in species_names:
        if genus_species in duplicate_genus_species:
            status = 'SKIPPED_DUPLICATE_PROTEOME'
            reason = 'Multiple proteome files map to this Genus_species; ambiguous which to use.'
            excluded_records.append( ( genus_species, reason ) )
            status_records.append( ( genus_species, status ) )
            continue

        if genus_species not in genus_species___proteome_records:
            status = 'SKIPPED_NO_PROTEOME'
            reason = f'No proteome file matching {genus_species} found in {args.proteomes_dir.name}.'
            excluded_records.append( ( genus_species, reason ) )
            status_records.append( ( genus_species, status ) )
            continue

        phyloname, proteome_path = genus_species___proteome_records[ genus_species ]
        blast_db_stem_expected = proteome_path.name   # blastp DB stem = full proteome basename including .aa

        if blast_db_stem_expected not in blast_db_stems:
            status = 'SKIPPED_NO_BLAST_DB'
            reason = f'No blastp DB matching {blast_db_stem_expected} found in {args.blast_db_dir.name}.'
            excluded_records.append( ( genus_species, reason ) )
            status_records.append( ( genus_species, status ) )
            continue

        processable_records.append( ( genus_species, phyloname, proteome_path, blast_db_stem_expected ) )
        status_records.append( ( genus_species, 'PROCESSABLE' ) )

    logger.info( f'  PROCESSABLE: {len( processable_records )}' )
    logger.info( f'  EXCLUDED:    {len( excluded_records )}' )
    logger.info( '' )

    # ---- Write outputs ----
    manifest_path = args.output_dir / '1_ai-processable_species_manifest.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Phyloname (full GIGANTIC phylogenetic name with underscores)\t'
    output += 'Proteome_Path (absolute path to the species T1 proteome aa file)\t'
    output += 'Blast_Db_Stem (basename stem of pre-built blastp database for this species)\n'
    for genus_species, phyloname, proteome_path, blast_db_stem in processable_records:
        output += genus_species + '\t' + phyloname + '\t' + str( proteome_path.resolve() ) + '\t' + blast_db_stem + '\n'
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
    output += 'Status (one of PROCESSABLE, SKIPPED_NO_PROTEOME, SKIPPED_NO_BLAST_DB, SKIPPED_DUPLICATE_PROTEOME)\n'
    for genus_species, status in status_records:
        output += genus_species + '\t' + status + '\n'
    with open( status_path, 'w' ) as output_status:
        output_status.write( output )
    logger.info( f'  Wrote {status_path.name} ({len( status_records )} rows)' )

    # ---- Fail if nothing processable ----
    if not processable_records:
        logger.error( '' )
        logger.error( 'CRITICAL ERROR: Zero species are processable. Nothing to BLAST.' )
        logger.error( f'See {excluded_path.name} for per-species reasons.' )
        logger.error( 'Common fixes:' )
        logger.error( '  - Confirm proteomes_dir and blast_db_dir paths in START_HERE-user_config.yaml' )
        logger.error( '  - Confirm species_list contains GIGANTIC Genus_species names matching the proteome filenames' )
        return 1

    logger.info( '' )
    logger.info( 'Validation complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
