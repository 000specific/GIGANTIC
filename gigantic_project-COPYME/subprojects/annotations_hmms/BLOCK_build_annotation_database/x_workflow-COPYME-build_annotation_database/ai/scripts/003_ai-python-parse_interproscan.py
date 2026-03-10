#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Parse InterProScan results into 19 component databases plus GO plus interproscan summary
# Human: Eric Edsinger

"""
003_ai-python-parse_interproscan.py

Parses InterProScan TSV result files (one per species) into standardized
GIGANTIC annotation database files. InterProScan annotates proteins against
up to 17 member databases and also provides InterPro integrated annotations
and GO term mappings.

This script splits each InterProScan result file by analysis database
(column 4) into separate per-database, per-species TSV files with a
standardized 7-column format. It also extracts GO terms from column 14
and validates them against the GO ontology lookup table.

InterProScan 15-column TSV format (no header):
    Col 0:  protein_id          - Protein accession (e.g., XP_027047018.1)
    Col 1:  md5                 - MD5 hash of protein sequence
    Col 2:  length              - Protein sequence length
    Col 3:  analysis_db         - Analysis database name (e.g., Pfam, Gene3D)
    Col 4:  sig_accession       - Signature accession (e.g., PF00069)
    Col 5:  sig_description     - Signature description
    Col 6:  start               - Domain start position
    Col 7:  stop                - Domain stop position
    Col 8:  score               - E-value or score
    Col 9:  status              - Match status (T = true match)
    Col 10: date                - Date of analysis
    Col 11: interpro_id         - InterPro accession (e.g., IPR000719) or empty
    Col 12: interpro_description - InterPro description or empty
    Col 13: go_terms            - GO terms, pipe-separated (e.g., GO:0005524|GO:0004674) or empty
    Col 14: pathway             - Pathway annotations or empty

Output standardized 7-column TSV format per database:
    Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop,
    Database_Name, Annotation_Identifier, Annotation_Details

Output directory structure (flat - all databases at same level):
    database_pfam/
        gigantic_annotations-database_pfam-{phyloname}.tsv
    database_gene3d/
        gigantic_annotations-database_gene3d-{phyloname}.tsv
    ...
    database_interproscan/
        gigantic_annotations-database_interproscan-{phyloname}.tsv
    database_go/
        gigantic_annotations-database_go-{phyloname}.tsv

Input:
    --discovery-manifest: Path to 1_ai-tool_discovery_manifest.tsv from script 001
    --go-lookup: Path to 2_ai-go_term_lookup.tsv from script 002
    --output-dir: Directory for output files

Output:
    database_pfam/, database_gene3d/, ..., database_go/ directories (flat, one per database)
    3_ai-log-parse_interproscan.log

Usage:
    python3 003_ai-python-parse_interproscan.py \\
        --discovery-manifest 1_ai-tool_discovery_manifest.tsv \\
        --go-lookup 2_ai-go_term_lookup.tsv \\
        --proteomes-dir /path/to/proteomes \\
        --output-dir .

If --proteomes-dir is provided, the script also identifies proteins in each
species proteome that have NO annotations from each database and adds
unannotated entries with identifiers like unannotated_pfam-1, unannotated_pfam-2,
etc. The counter is global across all species per database.
"""

import argparse
import logging
import sys
from pathlib import Path


# =============================================================================
# InterProScan analysis database name mapping
# =============================================================================
# Maps InterProScan's analysis_db names (column 3) to GIGANTIC database names.
# Keys are as they appear in InterProScan output (case-sensitive).
# =============================================================================

ANALYSIS_DATABASE_NAMES___GIGANTIC_DATABASE_NAMES = {
    'Pfam': 'pfam',
    'Gene3D': 'gene3d',
    'SUPERFAMILY': 'superfamily',
    'SMART': 'smart',
    'PANTHER': 'panther',
    'CDD': 'cdd',
    'PRINTS': 'prints',
    'ProSitePatterns': 'prositepatterns',
    'ProSiteProfiles': 'prositeprofiles',
    'HAMAP': 'hamap',
    'SFLD': 'sfld',
    'FunFam': 'funfam',
    'NCBIfam': 'ncbifam',
    'PIRSF': 'pirsf',
    'Coils': 'coils',
    'MobiDBLite': 'mobidblite',
    'AntiFam': 'antifam',
}


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '003_parse_interproscan' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '3_ai-log-parse_interproscan.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def load_discovery_manifest( manifest_path: Path, logger: logging.Logger ) -> dict:
    """
    Read the discovery manifest and return the interproscan tool record.
    Returns a dictionary with tool information or exits if interproscan is not available.
    """

    logger.info( f"Reading discovery manifest: {manifest_path}" )

    if not manifest_path.exists():
        logger.error( "CRITICAL ERROR: Discovery manifest does not exist!" )
        logger.error( f"Expected path: {manifest_path}" )
        logger.error( "Run script 001 (discover_tool_outputs) first." )
        sys.exit( 1 )

    interproscan_record = None

    with open( manifest_path, 'r' ) as input_manifest:
        # Tool_Name (name of annotation tool)	Tool_Available (yes or no ...)	...
        # interproscan	yes	output_to_input/BLOCK_interproscan	5	*_interproscan_results.tsv
        for line in input_manifest:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Tool_Name' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 5:
                continue

            tool_name = parts[ 0 ]

            if tool_name == 'interproscan':
                interproscan_record = {
                    'tool_name': tool_name,
                    'tool_available': parts[ 1 ],
                    'output_directory': parts[ 2 ],
                    'file_count': int( parts[ 3 ] ),
                    'file_pattern': parts[ 4 ],
                }
                break

    if interproscan_record is None:
        logger.error( "CRITICAL ERROR: No interproscan entry found in discovery manifest!" )
        logger.error( f"Manifest path: {manifest_path}" )
        logger.error( "The discovery manifest may be corrupted or incomplete." )
        sys.exit( 1 )

    if interproscan_record[ 'tool_available' ] != 'yes':
        logger.error( "CRITICAL ERROR: InterProScan results are not available!" )
        logger.error( "The discovery manifest shows interproscan as unavailable." )
        logger.error( "Complete the BLOCK_interproscan workflow before running this script." )
        sys.exit( 1 )

    logger.info( f"  InterProScan output directory: {interproscan_record[ 'output_directory' ]}" )
    logger.info( f"  Expected file count: {interproscan_record[ 'file_count' ]}" )

    return interproscan_record


def load_go_lookup( go_lookup_path: Path, logger: logging.Logger ) -> dict:
    """
    Load the GO term lookup table into a dictionary for fast validation.
    Returns go_ids___go_records: { 'GO:0000001': { 'go_name': ..., 'go_namespace': ..., 'is_obsolete': ... } }
    """

    logger.info( f"Loading GO term lookup table: {go_lookup_path}" )

    if not go_lookup_path.exists():
        logger.error( "CRITICAL ERROR: GO lookup table does not exist!" )
        logger.error( f"Expected path: {go_lookup_path}" )
        logger.error( "Run script 002 (download_go_ontology) first." )
        sys.exit( 1 )

    go_ids___go_records = {}

    with open( go_lookup_path, 'r' ) as input_go_lookup:
        # GO_ID (gene ontology identifier format GO:NNNNNNN)	GO_Name (...)	GO_Namespace (...)	Is_Obsolete (...)
        # GO:0000001	mitochondrion inheritance	biological_process	false
        for line in input_go_lookup:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'GO_ID' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 4:
                continue

            go_id = parts[ 0 ]
            go_name = parts[ 1 ]
            go_namespace = parts[ 2 ]
            is_obsolete = parts[ 3 ]

            go_ids___go_records[ go_id ] = {
                'go_name': go_name,
                'go_namespace': go_namespace,
                'is_obsolete': is_obsolete,
            }

    logger.info( f"  Loaded {len( go_ids___go_records )} GO terms" )

    if len( go_ids___go_records ) == 0:
        logger.error( "CRITICAL ERROR: GO lookup table is empty!" )
        logger.error( "Re-run script 002 to download and parse the GO ontology." )
        sys.exit( 1 )

    return go_ids___go_records


def extract_phyloname_from_filename( filename: str, logger: logging.Logger ) -> str:
    """
    Extract the GIGANTIC phyloname from an InterProScan result filename.
    Expected format: {phyloname}_interproscan_results.tsv
    """

    suffix = '_interproscan_results.tsv'

    if filename.endswith( suffix ):
        phyloname = filename[ : -len( suffix ) ]
    else:
        # Fallback: remove .tsv extension and try to use as phyloname
        phyloname = filename.replace( '.tsv', '' )
        logger.warning( f"  WARNING: Filename does not match expected pattern: {filename}" )
        logger.warning( f"  Using extracted name: {phyloname}" )

    return phyloname


def write_standardized_header() -> str:
    """Return the standardized 7-column header string for database TSV files."""

    header = 'Phyloname (GIGANTIC phyloname for the species)' + '\t'
    header += 'Sequence_Identifier (protein identifier from proteome)' + '\t'
    header += 'Domain_Start (start position of annotation on protein sequence)' + '\t'
    header += 'Domain_Stop (stop position of annotation on protein sequence)' + '\t'
    header += 'Database_Name (name of annotation database)' + '\t'
    header += 'Annotation_Identifier (accession or identifier from annotation database)' + '\t'
    header += 'Annotation_Details (description or details of the annotation)' + '\n'

    return header


def write_go_header() -> str:
    """Return the header string for GO database TSV files."""

    header = 'Phyloname (GIGANTIC phyloname for the species)' + '\t'
    header += 'Sequence_Identifier (protein identifier from proteome)' + '\t'
    header += 'Domain_Start (start position of annotated region on protein sequence)' + '\t'
    header += 'Domain_Stop (stop position of annotated region on protein sequence)' + '\t'
    header += 'Database_Name (always go for gene ontology annotations)' + '\t'
    header += 'Annotation_Identifier (GO term identifier format GO:NNNNNNN)' + '\t'
    header += 'Annotation_Details (GO term name and namespace separated by vertical bar)' + '\n'

    return header


def load_proteome_protein_identifiers( proteomes_directory: Path, logger: logging.Logger ) -> dict:
    """
    Load protein identifiers from FASTA proteome files.

    Reads all .aa files in the proteomes directory, extracting protein IDs
    from FASTA headers. Returns a dictionary mapping phylonames to sets of
    protein identifiers.

    Proteome files follow GIGANTIC cleaned naming: {phyloname}-T1-proteome.aa
    FASTA headers: >protein_id description...

    Returns:
        phylonames___protein_identifiers: dict mapping phyloname -> set of protein IDs
    """

    logger.info( f"Loading proteome protein identifiers from: {proteomes_directory}" )

    if not proteomes_directory.exists():
        logger.error( "CRITICAL ERROR: Proteomes directory does not exist!" )
        logger.error( f"Expected path: {proteomes_directory}" )
        logger.error( "Verify proteomes_dir path in the configuration file." )
        logger.error( "Expected: genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/" )
        sys.exit( 1 )

    proteome_files = sorted( proteomes_directory.glob( '*.aa' ) )

    if len( proteome_files ) == 0:
        logger.error( "CRITICAL ERROR: No proteome files (*.aa) found!" )
        logger.error( f"Directory: {proteomes_directory}" )
        logger.error( "The proteomes directory should contain .aa FASTA files." )
        sys.exit( 1 )

    phylonames___protein_identifiers = {}

    for proteome_file in proteome_files:
        # Extract phyloname from filename: {phyloname}-T1-proteome.aa
        filename_without_extension = proteome_file.stem
        parts_filename = filename_without_extension.split( '-T1-proteome' )
        if len( parts_filename ) < 2:
            logger.error( f"CRITICAL ERROR: Filename does not follow GIGANTIC cleaned proteome format: {proteome_file.name}" )
            logger.error( "Expected format: phyloname-T1-proteome.aa" )
            sys.exit( 1 )
        phyloname = parts_filename[ 0 ]

        # Read FASTA headers to get protein IDs
        protein_identifiers = set()

        with open( proteome_file, 'r' ) as input_proteome:
            # >XP_027047018.1 description text
            # MSTLKQVFYILCLFSGHWAEQPADMQ...
            for line in input_proteome:
                if line.startswith( '>' ):
                    # Protein ID is the first word after >
                    header = line[ 1: ].strip()
                    protein_identifier = header.split()[ 0 ] if header else ''
                    if protein_identifier:
                        protein_identifiers.add( protein_identifier )

        phylonames___protein_identifiers[ phyloname ] = protein_identifiers
        logger.debug( f"  {phyloname}: {len( protein_identifiers )} proteins" )

    logger.info( f"  Loaded proteomes for {len( phylonames___protein_identifiers )} species" )

    total_proteins = sum( len( identifiers ) for identifiers in phylonames___protein_identifiers.values() )
    logger.info( f"  Total protein identifiers: {total_proteins:,d}" )

    return phylonames___protein_identifiers


def parse_interproscan_files( interproscan_record: dict, go_ids___go_records: dict,
                               proteomes_directory: Path, output_directory: Path,
                               logger: logging.Logger ) -> None:
    """
    Parse all InterProScan result files found in the tool output directory.
    Split annotations by analysis database and create standardized TSV files.
    If proteomes_directory is provided, also adds unannotated protein entries
    for each database with identifiers like unannotated_{database}-N.
    """

    interproscan_output_directory = Path( interproscan_record[ 'output_directory' ] )
    file_pattern = interproscan_record[ 'file_pattern' ]

    # =========================================================================
    # Find InterProScan result files
    # =========================================================================

    result_files = sorted( interproscan_output_directory.glob( file_pattern ) )

    if len( result_files ) == 0:
        logger.error( "CRITICAL ERROR: No InterProScan result files found!" )
        logger.error( f"Searched directory: {interproscan_output_directory}" )
        logger.error( f"File pattern: {file_pattern}" )
        sys.exit( 1 )

    logger.info( f"Found {len( result_files )} InterProScan result file(s) to parse" )

    # =========================================================================
    # Create output directory structure
    # =========================================================================

    # All databases are flat at the same level: database_{name}/
    all_gigantic_database_names = list( ANALYSIS_DATABASE_NAMES___GIGANTIC_DATABASE_NAMES.values() )
    all_gigantic_database_names.append( 'interproscan' )
    all_gigantic_database_names.append( 'go' )

    for gigantic_database_name in all_gigantic_database_names:
        database_directory = output_directory / f"database_{gigantic_database_name}"
        database_directory.mkdir( parents = True, exist_ok = True )

    # =========================================================================
    # Global statistics tracking
    # =========================================================================

    total_annotation_lines_read = 0
    total_annotations_written = 0
    total_go_annotations_written = 0
    total_interproscan_annotations_written = 0
    total_obsolete_go_terms_found = 0
    total_unknown_go_terms_found = 0
    species_count = 0

    # Track annotations per database across all species
    gigantic_database_names___total_counts = {}
    # Track unknown analysis_db names encountered
    unknown_analysis_databases = set()

    # =========================================================================
    # Load proteome protein identifiers (if proteomes directory provided)
    # =========================================================================

    phylonames___protein_identifiers = None
    if proteomes_directory is not None:
        phylonames___protein_identifiers = load_proteome_protein_identifiers( proteomes_directory, logger )

    # Track unannotated counts per database (global across all species)
    gigantic_database_names___unannotated_counters = {}
    total_unannotated_entries_written = 0

    # =========================================================================
    # Process each species result file
    # =========================================================================

    for result_file in result_files:
        species_count += 1
        phyloname = extract_phyloname_from_filename( result_file.name, logger )

        logger.info( f"  Processing species {species_count}/{len( result_files )}: {phyloname}" )
        logger.debug( f"    File: {result_file}" )

        # =====================================================================
        # Collect annotations per database for this species
        # =====================================================================

        # Dictionary: gigantic_database_name -> list of annotation tuples
        gigantic_database_names___annotation_rows = {}

        # Separate collection for GO terms
        go_annotation_rows = []

        # Separate collection for interproscan summary (rows with InterPro IDs)
        interproscan_annotation_rows = []

        species_annotation_count = 0
        species_go_term_count = 0
        species_obsolete_go_count = 0
        species_unknown_go_count = 0

        with open( result_file, 'r' ) as input_interproscan_results:
            # No header in InterProScan TSV output
            # XP_027047018.1	abc123def456	543	Pfam	PF00069	Protein kinase domain	27	283	1.2E-40	T	04-11-2024	IPR000719	Protein kinase domain	GO:0005524|GO:0004674
            for line in input_interproscan_results:
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                total_annotation_lines_read += 1
                species_annotation_count += 1

                parts = line.split( '\t' )

                # InterProScan TSV has 11-15 columns depending on matches
                if len( parts ) < 11:
                    logger.warning( f"    WARNING: Line has fewer than 11 columns ({len( parts )}), skipping" )
                    logger.debug( f"    Skipped line: {line[ :200 ]}" )
                    continue

                protein_id = parts[ 0 ]
                # parts[ 1 ] = md5 (not used)
                # parts[ 2 ] = length (not used)
                analysis_database = parts[ 3 ]
                signature_accession = parts[ 4 ]
                signature_description = parts[ 5 ] if len( parts ) > 5 else ''
                domain_start = parts[ 6 ] if len( parts ) > 6 else ''
                domain_stop = parts[ 7 ] if len( parts ) > 7 else ''
                # parts[ 8 ] = score (not used in standardized output)
                # parts[ 9 ] = status (not used in standardized output)
                # parts[ 10 ] = date (not used in standardized output)
                interpro_id = parts[ 11 ] if len( parts ) > 11 else ''
                interpro_description = parts[ 12 ] if len( parts ) > 12 else ''
                go_terms_string = parts[ 13 ] if len( parts ) > 13 else ''
                # parts[ 14 ] = pathway (not used currently)

                # =============================================================
                # Route annotation to the appropriate database
                # =============================================================

                if analysis_database in ANALYSIS_DATABASE_NAMES___GIGANTIC_DATABASE_NAMES:
                    gigantic_database_name = ANALYSIS_DATABASE_NAMES___GIGANTIC_DATABASE_NAMES[ analysis_database ]

                    annotation_row = (
                        phyloname,
                        protein_id,
                        domain_start,
                        domain_stop,
                        gigantic_database_name,
                        signature_accession,
                        signature_description,
                    )

                    if gigantic_database_name not in gigantic_database_names___annotation_rows:
                        gigantic_database_names___annotation_rows[ gigantic_database_name ] = []

                    gigantic_database_names___annotation_rows[ gigantic_database_name ].append( annotation_row )

                else:
                    # Unknown analysis database - log but do not fail
                    if analysis_database not in unknown_analysis_databases:
                        unknown_analysis_databases.add( analysis_database )
                        logger.warning( f"    WARNING: Unknown analysis database encountered: {analysis_database}" )
                        logger.warning( "    This database is not in the GIGANTIC mapping and will be skipped." )

                # =============================================================
                # Extract InterPro summary annotation (if present)
                # =============================================================

                if interpro_id and interpro_id != '-' and interpro_id.strip():
                    interpro_details = interpro_description if interpro_description and interpro_description != '-' else ''

                    interproscan_annotation_row = (
                        phyloname,
                        protein_id,
                        domain_start,
                        domain_stop,
                        'interproscan',
                        interpro_id,
                        interpro_details,
                    )

                    interproscan_annotation_rows.append( interproscan_annotation_row )

                # =============================================================
                # Extract GO terms (if present, pipe-separated in column 13)
                # =============================================================

                if go_terms_string and go_terms_string != '-' and go_terms_string.strip():
                    individual_go_terms = go_terms_string.split( '|' )

                    for go_term_id in individual_go_terms:
                        go_term_id = go_term_id.strip()

                        if not go_term_id:
                            continue

                        # Validate GO term against lookup table
                        if go_term_id in go_ids___go_records:
                            go_record = go_ids___go_records[ go_term_id ]

                            # Check for obsolete terms
                            if go_record[ 'is_obsolete' ] == 'true':
                                species_obsolete_go_count += 1
                                total_obsolete_go_terms_found += 1
                                logger.debug( f"    Obsolete GO term: {go_term_id} ({go_record[ 'go_name' ]})" )

                            # Build annotation details: name|namespace
                            go_annotation_details = go_record[ 'go_name' ] + '|' + go_record[ 'go_namespace' ]

                        else:
                            # GO term not in lookup table
                            species_unknown_go_count += 1
                            total_unknown_go_terms_found += 1
                            logger.debug( f"    Unknown GO term (not in ontology): {go_term_id}" )
                            go_annotation_details = 'unknown GO term|unknown'

                        go_annotation_row = (
                            phyloname,
                            protein_id,
                            domain_start,
                            domain_stop,
                            'go',
                            go_term_id,
                            go_annotation_details,
                        )

                        go_annotation_rows.append( go_annotation_row )
                        species_go_term_count += 1

        # =====================================================================
        # Add unannotated protein entries (if proteomes were loaded)
        # =====================================================================

        if phylonames___protein_identifiers is not None and phyloname in phylonames___protein_identifiers:
            all_protein_identifiers = phylonames___protein_identifiers[ phyloname ]

            # --- Component databases ---
            component_database_names = list( ANALYSIS_DATABASE_NAMES___GIGANTIC_DATABASE_NAMES.values() )

            for gigantic_database_name in component_database_names:
                # Get protein IDs that have annotations for this database
                annotated_protein_identifiers = set()
                if gigantic_database_name in gigantic_database_names___annotation_rows:
                    for annotation_row in gigantic_database_names___annotation_rows[ gigantic_database_name ]:
                        annotated_protein_identifiers.add( annotation_row[ 1 ] )

                # Compute unannotated proteins
                unannotated_protein_identifiers = all_protein_identifiers - annotated_protein_identifiers

                if len( unannotated_protein_identifiers ) > 0:
                    # Initialize counter for this database if needed
                    if gigantic_database_name not in gigantic_database_names___unannotated_counters:
                        gigantic_database_names___unannotated_counters[ gigantic_database_name ] = 0

                    # Initialize annotation rows list if needed
                    if gigantic_database_name not in gigantic_database_names___annotation_rows:
                        gigantic_database_names___annotation_rows[ gigantic_database_name ] = []

                    for protein_identifier in sorted( unannotated_protein_identifiers ):
                        gigantic_database_names___unannotated_counters[ gigantic_database_name ] += 1
                        unannotated_counter = gigantic_database_names___unannotated_counters[ gigantic_database_name ]
                        unannotated_identifier = f"unannotated_{gigantic_database_name}-{unannotated_counter}"

                        unannotated_row = (
                            phyloname,
                            protein_identifier,
                            '0',
                            '0',
                            gigantic_database_name,
                            unannotated_identifier,
                            'no annotation',
                        )

                        gigantic_database_names___annotation_rows[ gigantic_database_name ].append( unannotated_row )

                    total_unannotated_entries_written += len( unannotated_protein_identifiers )

            # --- InterProScan database ---
            interproscan_annotated_protein_identifiers = set()
            for annotation_row in interproscan_annotation_rows:
                interproscan_annotated_protein_identifiers.add( annotation_row[ 1 ] )

            interproscan_unannotated_protein_identifiers = all_protein_identifiers - interproscan_annotated_protein_identifiers

            if len( interproscan_unannotated_protein_identifiers ) > 0:
                if 'interproscan' not in gigantic_database_names___unannotated_counters:
                    gigantic_database_names___unannotated_counters[ 'interproscan' ] = 0

                for protein_identifier in sorted( interproscan_unannotated_protein_identifiers ):
                    gigantic_database_names___unannotated_counters[ 'interproscan' ] += 1
                    unannotated_counter = gigantic_database_names___unannotated_counters[ 'interproscan' ]
                    unannotated_identifier = f"unannotated_interproscan-{unannotated_counter}"

                    unannotated_row = (
                        phyloname,
                        protein_identifier,
                        '0',
                        '0',
                        'interproscan',
                        unannotated_identifier,
                        'no annotation',
                    )

                    interproscan_annotation_rows.append( unannotated_row )

                total_unannotated_entries_written += len( interproscan_unannotated_protein_identifiers )

            # --- GO database ---
            go_annotated_protein_identifiers = set()
            for annotation_row in go_annotation_rows:
                go_annotated_protein_identifiers.add( annotation_row[ 1 ] )

            go_unannotated_protein_identifiers = all_protein_identifiers - go_annotated_protein_identifiers

            if len( go_unannotated_protein_identifiers ) > 0:
                if 'go' not in gigantic_database_names___unannotated_counters:
                    gigantic_database_names___unannotated_counters[ 'go' ] = 0

                for protein_identifier in sorted( go_unannotated_protein_identifiers ):
                    gigantic_database_names___unannotated_counters[ 'go' ] += 1
                    unannotated_counter = gigantic_database_names___unannotated_counters[ 'go' ]
                    unannotated_identifier = f"unannotated_go-{unannotated_counter}"

                    unannotated_row = (
                        phyloname,
                        protein_identifier,
                        '0',
                        '0',
                        'go',
                        unannotated_identifier,
                        'no annotation',
                    )

                    go_annotation_rows.append( unannotated_row )

                total_unannotated_entries_written += len( go_unannotated_protein_identifiers )

            logger.debug( f"    Unannotated entries added for {phyloname}" )

        elif phylonames___protein_identifiers is not None and phyloname not in phylonames___protein_identifiers:
            logger.warning( f"    WARNING: No proteome found for phyloname: {phyloname}" )
            logger.warning( "    Unannotated entries will NOT be added for this species." )

        # =====================================================================
        # Write per-database files for this species
        # =====================================================================

        # Write component database files
        for gigantic_database_name in sorted( gigantic_database_names___annotation_rows.keys() ):
            annotation_rows = gigantic_database_names___annotation_rows[ gigantic_database_name ]
            annotation_count = len( annotation_rows )

            output_file_path = output_directory / f"database_{gigantic_database_name}" / f"gigantic_annotations-database_{gigantic_database_name}-{phyloname}.tsv"

            with open( output_file_path, 'w' ) as output_database_file:
                # Write header
                output_database_file.write( write_standardized_header() )

                # Write annotation rows
                for annotation_row in annotation_rows:
                    output = annotation_row[ 0 ] + '\t'
                    output += annotation_row[ 1 ] + '\t'
                    output += annotation_row[ 2 ] + '\t'
                    output += annotation_row[ 3 ] + '\t'
                    output += annotation_row[ 4 ] + '\t'
                    output += annotation_row[ 5 ] + '\t'
                    output += annotation_row[ 6 ] + '\n'
                    output_database_file.write( output )

            total_annotations_written += annotation_count

            # Track per-database totals
            if gigantic_database_name in gigantic_database_names___total_counts:
                gigantic_database_names___total_counts[ gigantic_database_name ] += annotation_count
            else:
                gigantic_database_names___total_counts[ gigantic_database_name ] = annotation_count

            logger.debug( f"    {gigantic_database_name}: {annotation_count} annotations" )

        # Write interproscan summary file
        if len( interproscan_annotation_rows ) > 0:
            output_interproscan_path = output_directory / 'database_interproscan' / f"gigantic_annotations-database_interproscan-{phyloname}.tsv"

            with open( output_interproscan_path, 'w' ) as output_interproscan_file:
                output_interproscan_file.write( write_standardized_header() )

                for annotation_row in interproscan_annotation_rows:
                    output = annotation_row[ 0 ] + '\t'
                    output += annotation_row[ 1 ] + '\t'
                    output += annotation_row[ 2 ] + '\t'
                    output += annotation_row[ 3 ] + '\t'
                    output += annotation_row[ 4 ] + '\t'
                    output += annotation_row[ 5 ] + '\t'
                    output += annotation_row[ 6 ] + '\n'
                    output_interproscan_file.write( output )

            total_interproscan_annotations_written += len( interproscan_annotation_rows )

            if 'interproscan' in gigantic_database_names___total_counts:
                gigantic_database_names___total_counts[ 'interproscan' ] += len( interproscan_annotation_rows )
            else:
                gigantic_database_names___total_counts[ 'interproscan' ] = len( interproscan_annotation_rows )

            logger.debug( f"    interproscan: {len( interproscan_annotation_rows )} annotations" )

        # Write GO file
        if len( go_annotation_rows ) > 0:
            output_go_path = output_directory / 'database_go' / f"gigantic_annotations-database_go-{phyloname}.tsv"

            with open( output_go_path, 'w' ) as output_go_file:
                output_go_file.write( write_go_header() )

                for annotation_row in go_annotation_rows:
                    output = annotation_row[ 0 ] + '\t'
                    output += annotation_row[ 1 ] + '\t'
                    output += annotation_row[ 2 ] + '\t'
                    output += annotation_row[ 3 ] + '\t'
                    output += annotation_row[ 4 ] + '\t'
                    output += annotation_row[ 5 ] + '\t'
                    output += annotation_row[ 6 ] + '\n'
                    output_go_file.write( output )

            total_go_annotations_written += len( go_annotation_rows )

            if 'go' in gigantic_database_names___total_counts:
                gigantic_database_names___total_counts[ 'go' ] += len( go_annotation_rows )
            else:
                gigantic_database_names___total_counts[ 'go' ] = len( go_annotation_rows )

            logger.debug( f"    go: {len( go_annotation_rows )} annotations" )

        # Per-species summary
        logger.info( f"    Total annotations: {species_annotation_count}" )
        logger.info( f"    GO term assignments: {species_go_term_count}" )
        if species_obsolete_go_count > 0:
            logger.info( f"    Obsolete GO terms: {species_obsolete_go_count}" )
        if species_unknown_go_count > 0:
            logger.info( f"    Unknown GO terms: {species_unknown_go_count}" )

    # =========================================================================
    # Validate outputs
    # =========================================================================

    if total_annotations_written == 0 and total_interproscan_annotations_written == 0 and total_go_annotations_written == 0:
        logger.error( "CRITICAL ERROR: No annotations were written to any database files!" )
        logger.error( f"Read {total_annotation_lines_read} lines from {len( result_files )} files" )
        logger.error( "InterProScan result files may be empty or in unexpected format." )
        sys.exit( 1 )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 003 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species processed: {species_count}" )
    logger.info( f"  Total annotation lines read: {total_annotation_lines_read}" )
    logger.info( f"  Component database annotations written: {total_annotations_written}" )
    logger.info( f"  InterPro summary annotations written: {total_interproscan_annotations_written}" )
    logger.info( f"  GO annotations written: {total_go_annotations_written}" )
    logger.info( f"  Obsolete GO terms encountered: {total_obsolete_go_terms_found}" )
    logger.info( f"  Unknown GO terms encountered: {total_unknown_go_terms_found}" )
    logger.info( f"  Unannotated protein entries added: {total_unannotated_entries_written:,d}" )
    logger.info( f"  Output directory: {output_directory}" )

    if gigantic_database_names___unannotated_counters:
        logger.info( "" )
        logger.info( "Unannotated entries per database:" )
        for gigantic_database_name in sorted( gigantic_database_names___unannotated_counters.keys() ):
            count = gigantic_database_names___unannotated_counters[ gigantic_database_name ]
            logger.info( f"  {gigantic_database_name:<20s} {count:>10,d}" )

    if unknown_analysis_databases:
        logger.info( "" )
        logger.info( "Unknown analysis databases (not mapped to GIGANTIC names):" )
        for unknown_database in sorted( unknown_analysis_databases ):
            logger.info( f"    {unknown_database}" )

    logger.info( "" )
    logger.info( "Annotations per database:" )
    for gigantic_database_name in sorted( gigantic_database_names___total_counts.keys() ):
        count = gigantic_database_names___total_counts[ gigantic_database_name ]
        logger.info( f"  {gigantic_database_name:<20s} {count:>10,d}" )

    # Count output files per database
    logger.info( "" )
    logger.info( "Output files per database:" )
    for gigantic_database_name in sorted( all_gigantic_database_names ):
        database_directory = output_directory / f"database_{gigantic_database_name}"
        output_files_in_database = list( database_directory.glob( '*.tsv' ) )
        logger.info( f"  {gigantic_database_name:<20s} {len( output_files_in_database ):>5d} file(s)" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Parse InterProScan results into 19 component databases plus GO plus interproscan summary'
    )

    parser.add_argument(
        '--discovery-manifest',
        type = str,
        required = True,
        help = 'Path to 1_ai-tool_discovery_manifest.tsv from script 001'
    )

    parser.add_argument(
        '--go-lookup',
        type = str,
        required = True,
        help = 'Path to 2_ai-go_term_lookup.tsv from script 002'
    )

    parser.add_argument(
        '--annotations-dir',
        type = str,
        required = True,
        help = 'Path to annotations_hmms root directory containing BLOCK_* directories'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Output directory for database files (default: current directory)'
    )

    parser.add_argument(
        '--proteomes-dir',
        type = str,
        required = False,
        default = None,
        help = 'Path to proteomes directory containing .aa FASTA files (optional - if provided, unannotated protein entries are added to each database)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    discovery_manifest_path = Path( arguments.discovery_manifest )
    go_lookup_path = Path( arguments.go_lookup )
    annotations_directory = Path( arguments.annotations_dir ).resolve()
    output_directory = Path( arguments.output_dir )
    proteomes_directory = Path( arguments.proteomes_dir ).resolve() if arguments.proteomes_dir else None

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 003: Parse InterProScan Results" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load inputs
    # =========================================================================

    interproscan_record = load_discovery_manifest( discovery_manifest_path, logger )

    # Resolve relative output_directory from manifest against annotations_hmms root
    interproscan_record[ 'output_directory' ] = str( annotations_directory / interproscan_record[ 'output_directory' ] )

    go_ids___go_records = load_go_lookup( go_lookup_path, logger )

    # =========================================================================
    # Parse InterProScan files
    # =========================================================================

    parse_interproscan_files( interproscan_record, go_ids___go_records, proteomes_directory, output_directory, logger )


if __name__ == '__main__':
    main()
