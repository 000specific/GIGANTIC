#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Compare annotation frequencies across user-defined phylogenetic clades from config YAML
# Human: Eric Edsinger

"""
016_ai-python-analyze_phylogenetic_patterns.py

Compares annotation frequencies across user-defined phylogenetic clade groups
from the START_HERE-user_config.yaml file. This analysis reveals whether
certain annotation types are enriched or depleted in specific phylogenetic
clades (e.g., ctenophores vs. cnidarians vs. bilaterians).

For each clade group:
    - Identifies which species from the config are present in the statistics data
    - Computes per-clade mean Total_Annotations and mean Unique_Proteins per database

For each pair of clades:
    - Computes fold-change of mean annotations between clades
    - Reports enrichment direction (which clade has higher mean)

The YAML config file is parsed using standard library string operations only
(no PyYAML dependency). The expected config format is:
    clade_comparison:
      - group_name: "name"
        species:
          - "Genus_species"
          - "Genus_species"

Input:
    --statistics: Path to 8_ai-annotation_statistics.tsv from script 008
    --config-file: Path to START_HERE-user_config.yaml
    --output-dir: Directory for output files

Output:
    16_ai-phylogenetic_patterns.tsv
        Per-clade per-database summary statistics.

    16_ai-clade_comparisons.tsv
        Pairwise clade comparisons with fold-change and enrichment direction.

    16_ai-log-analyze_phylogenetic_patterns.log

Usage:
    python3 016_ai-python-analyze_phylogenetic_patterns.py \\
        --statistics 8_ai-annotation_statistics.tsv \\
        --config-file START_HERE-user_config.yaml \\
        --output-dir .
"""

import argparse
import logging
import statistics as statistics_module
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '016_analyze_phylogenetic_patterns' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '16_ai-log-analyze_phylogenetic_patterns.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def parse_yaml_config( config_path: Path, logger: logging.Logger ) -> list:
    """
    Parse the clade_comparison section from the START_HERE-user_config.yaml
    using standard library string operations only (no PyYAML dependency).

    The expected format is:
        clade_comparison:
          - group_name: "name"
            species:
              - "Genus_species"
              - "Genus_species"

    Returns a list of dictionaries:
        [ { 'group_name': 'ctenophora', 'species': [ 'Mnemiopsis_leidyi', ... ] }, ... ]
    """

    logger.info( f"Parsing YAML config file: {config_path}" )

    if not config_path.exists():
        logger.error( "CRITICAL ERROR: Config file does not exist!" )
        logger.error( f"Expected path: {config_path}" )
        logger.error( "Ensure START_HERE-user_config.yaml is available." )
        sys.exit( 1 )

    with open( config_path, 'r' ) as input_config:
        config_lines = input_config.readlines()

    # =========================================================================
    # Find the clade_comparison section
    # =========================================================================

    clade_comparison_groups = []
    inside_clade_comparison_section = False
    current_group = None
    inside_species_list = False

    for line in config_lines:
        # Remove trailing whitespace but preserve leading whitespace for indentation
        stripped_line = line.rstrip()

        # Skip empty lines and comment-only lines
        if not stripped_line or stripped_line.lstrip().startswith( '#' ):
            continue

        # Calculate indentation level (number of leading spaces)
        indentation = len( stripped_line ) - len( stripped_line.lstrip() )
        content = stripped_line.lstrip()

        # Detect start of clade_comparison section
        if content == 'clade_comparison:':
            inside_clade_comparison_section = True
            logger.debug( "  Found clade_comparison section" )
            continue

        # If not inside clade_comparison section, skip
        if not inside_clade_comparison_section:
            continue

        # Detect end of clade_comparison section (a new top-level key)
        if indentation == 0 and ':' in content:
            inside_clade_comparison_section = False
            # Save any current group being built
            if current_group is not None:
                clade_comparison_groups.append( current_group )
                current_group = None
            break

        # Detect new group entry (starts with "- group_name:")
        if content.startswith( '- group_name:' ):
            # Save previous group if exists
            if current_group is not None:
                clade_comparison_groups.append( current_group )

            # Extract group name (remove quotes)
            group_name_raw = content.split( ':', 1 )[ 1 ].strip()
            group_name = group_name_raw.strip( '"' ).strip( "'" )

            current_group = {
                'group_name': group_name,
                'species': [],
            }
            inside_species_list = False
            logger.debug( f"  Found group: {group_name}" )
            continue

        # Detect species: key
        if content == 'species:':
            inside_species_list = True
            continue

        # Detect species list entries (lines starting with "- " inside species section)
        if inside_species_list and content.startswith( '- ' ):
            species_name_raw = content[ 2: ].strip()
            species_name = species_name_raw.strip( '"' ).strip( "'" )

            if current_group is not None:
                current_group[ 'species' ].append( species_name )
                logger.debug( f"    Species: {species_name}" )
            continue

        # If we hit a non-list line while inside species list, species list is done
        if inside_species_list and not content.startswith( '- ' ):
            inside_species_list = False
            # This line might be the start of a new attribute at the group level
            # Re-check if it's a new group
            if content.startswith( '- group_name:' ):
                # Save previous group
                if current_group is not None:
                    clade_comparison_groups.append( current_group )

                group_name_raw = content.split( ':', 1 )[ 1 ].strip()
                group_name = group_name_raw.strip( '"' ).strip( "'" )

                current_group = {
                    'group_name': group_name,
                    'species': [],
                }
                logger.debug( f"  Found group: {group_name}" )

    # Save last group if exists
    if current_group is not None:
        clade_comparison_groups.append( current_group )

    # =========================================================================
    # Validate parsed config
    # =========================================================================

    if len( clade_comparison_groups ) == 0:
        logger.error( "CRITICAL ERROR: No clade comparison groups found in config!" )
        logger.error( f"Config file: {config_path}" )
        logger.error( "Ensure the clade_comparison section is properly formatted." )
        sys.exit( 1 )

    if len( clade_comparison_groups ) < 2:
        logger.error( "CRITICAL ERROR: Need at least 2 clade groups for comparison!" )
        logger.error( f"Found only {len( clade_comparison_groups )} group(s)." )
        logger.error( "Add more groups to the clade_comparison section." )
        sys.exit( 1 )

    logger.info( f"  Parsed {len( clade_comparison_groups )} clade comparison groups:" )
    for group in clade_comparison_groups:
        logger.info( f"    {group[ 'group_name' ]}: {len( group[ 'species' ] )} species" )
        for species_name in group[ 'species' ]:
            logger.debug( f"      {species_name}" )

    return clade_comparison_groups


def load_statistics( statistics_path: Path, logger: logging.Logger ) -> list:
    """
    Read the annotation statistics table from script 008.
    Returns a list of dictionaries, one per row.
    """

    logger.info( f"Reading annotation statistics: {statistics_path}" )

    if not statistics_path.exists():
        logger.error( "CRITICAL ERROR: Statistics file does not exist!" )
        logger.error( f"Expected path: {statistics_path}" )
        logger.error( "Run script 008 (annotation_statistics) first." )
        sys.exit( 1 )

    statistics_records = []

    with open( statistics_path, 'r' ) as input_statistics:
        # Phyloname (phylogenetic name of species)	Database_Name (annotation database name)	Total_Annotations (total annotation rows for this species and database)	Unique_Proteins_Annotated (count of distinct proteins with annotations)	Unique_Identifiers (count of distinct annotation identifiers)	Annotations_Per_Protein (average annotations per annotated protein)
        # Metazoa_Ctenophora_Tentaculata_Lobata_Bolinopsidae_Bolinopsis_microptera	pfam	12345	5678	1234	2.17
        for line in input_statistics:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 6:
                logger.warning( f"WARNING: Line has fewer than 6 columns ({len( parts )}), skipping" )
                logger.debug( f"Skipped line: {line[ :200 ]}" )
                continue

            phyloname = parts[ 0 ]
            database_name = parts[ 1 ]
            total_annotations = int( parts[ 2 ] )
            unique_proteins_annotated = int( parts[ 3 ] )

            statistics_records.append( {
                'phyloname': phyloname,
                'database_name': database_name,
                'total_annotations': total_annotations,
                'unique_proteins_annotated': unique_proteins_annotated,
            } )

    if len( statistics_records ) == 0:
        logger.error( "CRITICAL ERROR: No data rows found in statistics file!" )
        logger.error( f"File path: {statistics_path}" )
        logger.error( "The statistics file may be empty or have an unexpected format." )
        sys.exit( 1 )

    logger.info( f"  Loaded {len( statistics_records )} statistics records" )

    return statistics_records


def extract_genus_species_from_phyloname( phyloname: str ) -> str:
    """
    Extract genus_species from a GIGANTIC phyloname.
    Phyloname format: Kingdom_Phylum_Class_Order_Family_Genus_species
    Returns: Genus_species (e.g., 'Homo_sapiens')
    """

    parts_phyloname = phyloname.split( '_' )

    if len( parts_phyloname ) < 7:
        # Not a standard phyloname - return as-is for matching
        return phyloname

    genus = parts_phyloname[ 5 ]
    species = '_'.join( parts_phyloname[ 6: ] )
    genus_species = genus + '_' + species

    return genus_species


def analyze_phylogenetic_patterns( clade_comparison_groups: list, statistics_records: list,
                                    output_directory: Path, logger: logging.Logger ) -> None:
    """
    Compute per-clade per-database averages and pairwise clade comparisons.
    """

    # =========================================================================
    # Build lookup: genus_species -> phyloname
    # =========================================================================

    genus_species_names___phylonames = {}

    for record in statistics_records:
        phyloname = record[ 'phyloname' ]
        genus_species = extract_genus_species_from_phyloname( phyloname )
        genus_species_names___phylonames[ genus_species ] = phyloname

    logger.info( f"  Built genus_species -> phyloname mapping for {len( genus_species_names___phylonames )} species" )

    # =========================================================================
    # Build lookup: (phyloname, database_name) -> record
    # =========================================================================

    species_database_keys___records = {}

    for record in statistics_records:
        key = ( record[ 'phyloname' ], record[ 'database_name' ] )
        species_database_keys___records[ key ] = record

    # Collect all database names
    database_names_found = set()
    for record in statistics_records:
        database_names_found.add( record[ 'database_name' ] )
    sorted_database_names = sorted( database_names_found )

    logger.info( f"  Databases found: {len( sorted_database_names )}" )

    # =========================================================================
    # Map config species to phylonames and check availability
    # =========================================================================

    resolved_clade_groups = []

    for group in clade_comparison_groups:
        group_name = group[ 'group_name' ]
        species_in_config = group[ 'species' ]

        resolved_phylonames = []
        missing_species = []

        for species_name in species_in_config:
            if species_name in genus_species_names___phylonames:
                resolved_phyloname = genus_species_names___phylonames[ species_name ]
                resolved_phylonames.append( resolved_phyloname )
                logger.debug( f"    Resolved {species_name} -> {resolved_phyloname}" )
            else:
                missing_species.append( species_name )
                logger.warning( f"  WARNING: Species {species_name} from clade {group_name} not found in statistics data" )

        if len( missing_species ) > 0:
            logger.warning( f"  Clade {group_name}: {len( missing_species )} of {len( species_in_config )} species not found in data" )
            logger.warning( f"  Missing: {', '.join( missing_species )}" )

        resolved_clade_groups.append( {
            'group_name': group_name,
            'phylonames': resolved_phylonames,
            'species_names': [ extract_genus_species_from_phyloname( phyloname ) for phyloname in resolved_phylonames ],
            'missing_species': missing_species,
        } )

    # =========================================================================
    # Compute per-clade per-database averages
    # =========================================================================

    clade_pattern_records = []

    for resolved_group in resolved_clade_groups:
        group_name = resolved_group[ 'group_name' ]
        group_phylonames = resolved_group[ 'phylonames' ]

        if len( group_phylonames ) == 0:
            logger.warning( f"  WARNING: Clade {group_name} has no species in the statistics data" )
            logger.warning( "  Skipping this clade for per-database averages" )

            # Still create rows with 0 values so the output is complete
            for database_name in sorted_database_names:
                clade_pattern_records.append( {
                    'clade_name': group_name,
                    'database_name': database_name,
                    'species_in_clade_count': 0,
                    'species_in_clade_list': '',
                    'mean_annotations_per_species': 0.0,
                    'mean_unique_proteins_per_species': 0.0,
                } )
            continue

        logger.info( f"  Computing averages for clade: {group_name} ({len( group_phylonames )} species)" )

        for database_name in sorted_database_names:
            annotation_counts_for_clade = []
            unique_protein_counts_for_clade = []

            for phyloname in group_phylonames:
                key = ( phyloname, database_name )

                if key in species_database_keys___records:
                    record = species_database_keys___records[ key ]
                    annotation_counts_for_clade.append( record[ 'total_annotations' ] )
                    unique_protein_counts_for_clade.append( record[ 'unique_proteins_annotated' ] )
                else:
                    # Species exists in clade but has no data for this database
                    annotation_counts_for_clade.append( 0 )
                    unique_protein_counts_for_clade.append( 0 )

            mean_annotations = statistics_module.mean( annotation_counts_for_clade )
            mean_unique_proteins = statistics_module.mean( unique_protein_counts_for_clade )

            species_names_in_clade = resolved_group[ 'species_names' ]
            species_list_string = ','.join( sorted( species_names_in_clade ) )

            clade_pattern_records.append( {
                'clade_name': group_name,
                'database_name': database_name,
                'species_in_clade_count': len( group_phylonames ),
                'species_in_clade_list': species_list_string,
                'mean_annotations_per_species': mean_annotations,
                'mean_unique_proteins_per_species': mean_unique_proteins,
            } )

            logger.debug( f"    {database_name}: mean_annotations={mean_annotations:.2f}, mean_proteins={mean_unique_proteins:.2f}" )

    # =========================================================================
    # Validate clade patterns were generated
    # =========================================================================

    if len( clade_pattern_records ) == 0:
        logger.error( "CRITICAL ERROR: No clade pattern records were generated!" )
        logger.error( "This indicates all clades had zero species in the statistics data." )
        sys.exit( 1 )

    # =========================================================================
    # Write per-clade patterns
    # =========================================================================

    output_patterns_file = output_directory / '16_ai-phylogenetic_patterns.tsv'

    with open( output_patterns_file, 'w' ) as output_patterns:
        # Write header
        header = 'Clade_Name (name of phylogenetic clade from configuration)' + '\t'
        header += 'Database_Name (annotation database name)' + '\t'
        header += 'Species_In_Clade_Count (number of species in this clade found in statistics data)' + '\t'
        header += 'Species_In_Clade_List (comma delimited list of species in this clade)' + '\t'
        header += 'Mean_Annotations_Per_Species (average total annotations per species in this clade for this database)' + '\t'
        header += 'Mean_Unique_Proteins_Per_Species (average unique annotated proteins per species in this clade)' + '\n'
        output_patterns.write( header )

        # Write data rows
        for pattern_record in clade_pattern_records:
            output = pattern_record[ 'clade_name' ] + '\t'
            output += pattern_record[ 'database_name' ] + '\t'
            output += str( pattern_record[ 'species_in_clade_count' ] ) + '\t'
            output += pattern_record[ 'species_in_clade_list' ] + '\t'
            output += f"{pattern_record[ 'mean_annotations_per_species' ]:.2f}" + '\t'
            output += f"{pattern_record[ 'mean_unique_proteins_per_species' ]:.2f}" + '\n'
            output_patterns.write( output )

    logger.info( f"Wrote per-clade patterns to: {output_patterns_file}" )

    # =========================================================================
    # Build lookup for clade comparisons: (clade_name, database_name) -> record
    # =========================================================================

    clade_database_keys___pattern_records = {}

    for pattern_record in clade_pattern_records:
        key = ( pattern_record[ 'clade_name' ], pattern_record[ 'database_name' ] )
        clade_database_keys___pattern_records[ key ] = pattern_record

    # =========================================================================
    # Compute pairwise clade comparisons
    # =========================================================================

    comparison_records = []
    clade_names = [ group[ 'group_name' ] for group in resolved_clade_groups ]

    logger.info( "" )
    logger.info( "Computing pairwise clade comparisons..." )

    for index_a in range( len( clade_names ) ):
        for index_b in range( index_a + 1, len( clade_names ) ):
            clade_a_name = clade_names[ index_a ]
            clade_b_name = clade_names[ index_b ]

            logger.info( f"  Comparing: {clade_a_name} vs. {clade_b_name}" )

            for database_name in sorted_database_names:
                key_a = ( clade_a_name, database_name )
                key_b = ( clade_b_name, database_name )

                record_a = clade_database_keys___pattern_records.get( key_a, None )
                record_b = clade_database_keys___pattern_records.get( key_b, None )

                clade_a_mean = record_a[ 'mean_annotations_per_species' ] if record_a is not None else 0.0
                clade_b_mean = record_b[ 'mean_annotations_per_species' ] if record_b is not None else 0.0

                # Compute fold change (A / B)
                if clade_b_mean == 0.0:
                    if clade_a_mean == 0.0:
                        fold_change = 'NA'
                        enrichment_direction = 'equal'
                    else:
                        fold_change = 'NA'
                        enrichment_direction = 'enriched_in_' + clade_a_name
                else:
                    fold_change_value = clade_a_mean / clade_b_mean
                    fold_change = f"{fold_change_value:.4f}"

                    if clade_a_mean > clade_b_mean:
                        enrichment_direction = 'enriched_in_' + clade_a_name
                    elif clade_b_mean > clade_a_mean:
                        enrichment_direction = 'enriched_in_' + clade_b_name
                    else:
                        enrichment_direction = 'equal'

                comparison_records.append( {
                    'clade_a': clade_a_name,
                    'clade_b': clade_b_name,
                    'database_name': database_name,
                    'clade_a_mean_annotations': clade_a_mean,
                    'clade_b_mean_annotations': clade_b_mean,
                    'fold_change_a_over_b': fold_change,
                    'enrichment_direction': enrichment_direction,
                } )

                logger.debug(
                    f"    {database_name}: "
                    f"{clade_a_name}={clade_a_mean:.2f}, "
                    f"{clade_b_name}={clade_b_mean:.2f}, "
                    f"fold_change={fold_change}, "
                    f"{enrichment_direction}"
                )

    # =========================================================================
    # Validate comparisons were generated
    # =========================================================================

    if len( comparison_records ) == 0:
        logger.error( "CRITICAL ERROR: No clade comparison records were generated!" )
        logger.error( "This indicates a logic error in the pairwise comparison." )
        sys.exit( 1 )

    # =========================================================================
    # Write clade comparisons
    # =========================================================================

    output_comparisons_file = output_directory / '16_ai-clade_comparisons.tsv'

    with open( output_comparisons_file, 'w' ) as output_comparisons:
        # Write header
        header = 'Clade_A (first clade name in comparison)' + '\t'
        header += 'Clade_B (second clade name in comparison)' + '\t'
        header += 'Database_Name (annotation database name)' + '\t'
        header += 'Clade_A_Mean_Annotations (mean annotations per species in clade A)' + '\t'
        header += 'Clade_B_Mean_Annotations (mean annotations per species in clade B)' + '\t'
        header += 'Fold_Change_A_Over_B (clade A mean divided by clade B mean or NA if clade B mean is zero)' + '\t'
        header += 'Enrichment_Direction (enriched_in_A or enriched_in_B or equal based on which clade has higher mean)' + '\n'
        output_comparisons.write( header )

        # Write data rows
        for comparison_record in comparison_records:
            output = comparison_record[ 'clade_a' ] + '\t'
            output += comparison_record[ 'clade_b' ] + '\t'
            output += comparison_record[ 'database_name' ] + '\t'
            output += f"{comparison_record[ 'clade_a_mean_annotations' ]:.2f}" + '\t'
            output += f"{comparison_record[ 'clade_b_mean_annotations' ]:.2f}" + '\t'
            output += str( comparison_record[ 'fold_change_a_over_b' ] ) + '\t'
            output += comparison_record[ 'enrichment_direction' ] + '\n'
            output_comparisons.write( output )

    logger.info( f"Wrote clade comparisons to: {output_comparisons_file}" )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 016 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Clade groups: {len( clade_comparison_groups )}" )
    for resolved_group in resolved_clade_groups:
        group_name = resolved_group[ 'group_name' ]
        species_count = len( resolved_group[ 'phylonames' ] )
        missing_count = len( resolved_group[ 'missing_species' ] )
        logger.info( f"    {group_name}: {species_count} species in data" + ( f" ({missing_count} missing)" if missing_count > 0 else "" ) )
    logger.info( f"  Databases analyzed: {len( sorted_database_names )}" )
    logger.info( f"  Clade pattern records: {len( clade_pattern_records )}" )
    logger.info( f"  Pairwise comparisons: {len( comparison_records )}" )
    logger.info( f"  Output (patterns): {output_patterns_file}" )
    logger.info( f"  Output (comparisons): {output_comparisons_file}" )

    # Log notable enrichments (fold change > 2 or < 0.5)
    notable_enrichments = [ record for record in comparison_records
                            if record[ 'fold_change_a_over_b' ] != 'NA'
                            and ( float( record[ 'fold_change_a_over_b' ] ) > 2.0
                                  or float( record[ 'fold_change_a_over_b' ] ) < 0.5 ) ]

    if len( notable_enrichments ) > 0:
        logger.info( "" )
        logger.info( f"Notable enrichments (fold change > 2x or < 0.5x): {len( notable_enrichments )}" )
        for enrichment in sorted( notable_enrichments, key = lambda record: record[ 'database_name' ] ):
            logger.info(
                f"  {enrichment[ 'database_name' ]:<20s} "
                f"{enrichment[ 'clade_a' ]} vs {enrichment[ 'clade_b' ]}: "
                f"fold_change={enrichment[ 'fold_change_a_over_b' ]}  "
                f"({enrichment[ 'enrichment_direction' ]})"
            )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Compare annotation frequencies across user-defined phylogenetic clades from config YAML'
    )

    parser.add_argument(
        '--statistics',
        type = str,
        required = True,
        help = 'Path to 8_ai-annotation_statistics.tsv from script 008'
    )

    parser.add_argument(
        '--config-file',
        type = str,
        required = True,
        help = 'Path to START_HERE-user_config.yaml'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Output directory for phylogenetic pattern analysis and log (default: current directory)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    statistics_path = Path( arguments.statistics )
    config_path = Path( arguments.config_file )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 016: Analyze Phylogenetic Patterns" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Load inputs
    # =========================================================================

    clade_comparison_groups = parse_yaml_config( config_path, logger )
    statistics_records = load_statistics( statistics_path, logger )

    # =========================================================================
    # Analyze phylogenetic patterns
    # =========================================================================

    analyze_phylogenetic_patterns( clade_comparison_groups, statistics_records, output_directory, logger )


if __name__ == '__main__':
    main()
