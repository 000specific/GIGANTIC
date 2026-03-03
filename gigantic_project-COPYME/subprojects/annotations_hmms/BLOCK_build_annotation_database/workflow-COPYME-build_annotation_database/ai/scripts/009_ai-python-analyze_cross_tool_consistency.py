#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Analyze agreement between tools that predict overlapping features
# Human: Eric Edsinger

"""
009_ai-python-analyze_cross_tool_consistency.py

Analyzes agreement between annotation tools that predict overlapping biological
features. When two tools independently predict the same type of feature for the
same protein, their agreement provides cross-validation of the predictions.

This script compares two pairs of tools:

1. SignalP versus DeepLoc (signal peptide predictions):
   - SignalP directly predicts signal peptides with cleavage site positions
   - DeepLoc predicts subcellular localization; proteins localized to "Signal"
     are predicted to have signal peptides
   - Agreement: proteins predicted by both tools to have signal peptides

2. tmbed versus DeepLoc (membrane-associated predictions):
   - tmbed directly predicts transmembrane helices and beta-barrels
   - DeepLoc predicts "Membrane" localization for membrane-bound proteins
   - Agreement: proteins predicted by both tools to be membrane-associated

For each species, the script loads the relevant database files, extracts the
set of proteins predicted by each tool, and calculates intersection (agreement)
and union statistics. The Jaccard similarity (intersection / union) provides
a normalized measure of tool agreement.

Input:
    --statistics: Path to 8_ai-annotation_statistics.tsv from script 008
    --database-dir: Directory containing database_* directories
    --output-dir: Output directory

Output:
    9_ai-cross_tool_consistency.tsv
        Per-species, per-comparison agreement statistics with columns:
        - Phyloname (phylogenetic name of species)
        - Comparison_Type (pair of tools being compared)
        - Tool_A_Proteins (count of proteins predicted by tool A)
        - Tool_B_Proteins (count of proteins predicted by tool B)
        - Both_Tools_Proteins (count of proteins predicted by both tools)
        - Agreement_Rate_Percent (both tools divided by union times 100)

    9_ai-log-analyze_cross_tool_consistency.log

Usage:
    python3 009_ai-python-analyze_cross_tool_consistency.py \\
        --statistics 8_ai-annotation_statistics.tsv \\
        --database-dir . \\
        --output-dir .
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '009_analyze_cross_tool_consistency' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '9_ai-log-analyze_cross_tool_consistency.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def validate_statistics_file( statistics_path: Path, logger: logging.Logger ) -> None:
    """
    Validate that the statistics file from script 008 exists and is not empty.
    This confirms that script 008 completed successfully before running script 009.
    """

    if not statistics_path.exists():
        logger.error( "CRITICAL ERROR: Statistics file does not exist!" )
        logger.error( f"Expected path: {statistics_path}" )
        logger.error( "Run script 008 (compile_annotation_statistics) first." )
        sys.exit( 1 )

    # Check the file has data rows (not just header)
    line_count = 0
    with open( statistics_path, 'r' ) as input_statistics:
        for line in input_statistics:
            line = line.strip()
            if line and not line.startswith( 'Phyloname' ):
                line_count += 1

    if line_count == 0:
        logger.error( "CRITICAL ERROR: Statistics file has no data rows!" )
        logger.error( f"File: {statistics_path}" )
        logger.error( "Script 008 may have failed or produced an empty output." )
        sys.exit( 1 )

    logger.info( f"Statistics file validated: {line_count} data rows" )


def discover_species_from_database_directory( database_directory: Path, database_name: str,
                                                logger: logging.Logger ) -> list:
    """
    Find all species (phylonames) that have files in a given database directory.
    Returns a sorted list of phylonames extracted from the filenames.
    """

    phylonames = []

    if not database_directory.exists():
        return phylonames

    database_files = sorted( database_directory.glob( f"gigantic_annotations-database_{database_name}-*.tsv" ) )

    prefix = f"gigantic_annotations-database_{database_name}-"
    suffix = '.tsv'

    for database_file in database_files:
        filename = database_file.name
        if filename.startswith( prefix ) and filename.endswith( suffix ):
            phyloname = filename[ len( prefix ) : -len( suffix ) ]
            phylonames.append( phyloname )

    return sorted( phylonames )


def load_proteins_from_database_file( file_path: Path, logger: logging.Logger ) -> set:
    """
    Load all unique protein identifiers from a standardized 7-column database TSV file.
    Returns a set of protein identifier strings.
    """

    unique_proteins = set()

    if not file_path.exists():
        return unique_proteins

    with open( file_path, 'r' ) as input_database_file:
        # Phyloname (GIGANTIC phyloname for the species)	Sequence_Identifier (...)	...
        # Metazoa_...Homo_sapiens	XP_027047018.1	1	22	signalp	Sec/SPI	Sec/SPI,probability=0.9876
        for line in input_database_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            sequence_identifier = parts[ 1 ]

            if sequence_identifier:
                unique_proteins.add( sequence_identifier )

    return unique_proteins


def load_deeploc_proteins_with_annotation( file_path: Path, target_annotation: str,
                                             logger: logging.Logger ) -> set:
    """
    Load protein identifiers from a DeepLoc database file that have a specific
    annotation identifier (e.g., "Signal" or "Membrane").

    DeepLoc database files have the annotation identifier in column 5
    (Annotation_Identifier), which contains the predicted localization.

    Returns a set of protein identifier strings.
    """

    matching_proteins = set()

    if not file_path.exists():
        return matching_proteins

    with open( file_path, 'r' ) as input_deeploc_file:
        # Phyloname (...)	Sequence_Identifier (...)	Domain_Start (...)	Domain_Stop (...)	Database_Name (...)	Annotation_Identifier (...)	Annotation_Details (...)
        # Metazoa_...Homo_sapiens	XP_027047018.1	NA	NA	deeploc	Signal	Signal,probability=0.95
        for line in input_deeploc_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            sequence_identifier = parts[ 1 ]
            annotation_identifier = parts[ 5 ]

            # Check if this protein has the target annotation
            if annotation_identifier.lower() == target_annotation.lower():
                matching_proteins.add( sequence_identifier )

    return matching_proteins


def load_tmbed_proteins_with_transmembrane( file_path: Path, logger: logging.Logger ) -> set:
    """
    Load protein identifiers from a tmbed database file that have transmembrane
    annotations (TM_helix or TM_beta_barrel, but NOT signal_peptide).

    Returns a set of protein identifiers with at least one TM region.
    """

    transmembrane_proteins = set()

    if not file_path.exists():
        return transmembrane_proteins

    with open( file_path, 'r' ) as input_tmbed_file:
        # Phyloname (...)	Sequence_Identifier (...)	...	Annotation_Identifier (topology type TM_helix or TM_beta_barrel or signal_peptide)	...
        # Metazoa_...Homo_sapiens	XP_027047018.1	25	48	tmbed	TM_helix	TM_helix,start=25,stop=48
        for line in input_tmbed_file:
            line = line.strip()

            # Skip header and empty lines
            if not line or line.startswith( 'Phyloname' ):
                continue

            parts = line.split( '\t' )

            if len( parts ) < 7:
                continue

            sequence_identifier = parts[ 1 ]
            annotation_identifier = parts[ 5 ]

            # Only count transmembrane annotations, not signal peptides
            if annotation_identifier in [ 'TM_helix', 'TM_beta_barrel' ]:
                transmembrane_proteins.add( sequence_identifier )

    return transmembrane_proteins


def analyze_cross_tool_consistency( database_directory: Path, output_directory: Path,
                                     logger: logging.Logger ) -> None:
    """
    Compare tool predictions for overlapping features and compute agreement rates.
    Write the cross-tool consistency output file.
    """

    # =========================================================================
    # Check which database directories are available
    # =========================================================================

    signalp_directory = database_directory / 'database_signalp'
    deeploc_directory = database_directory / 'database_deeploc'
    tmbed_directory = database_directory / 'database_tmbed'

    signalp_available = signalp_directory.exists() and signalp_directory.is_dir()
    deeploc_available = deeploc_directory.exists() and deeploc_directory.is_dir()
    tmbed_available = tmbed_directory.exists() and tmbed_directory.is_dir()

    logger.info( "Tool database availability:" )
    logger.info( f"  SignalP:  {'available' if signalp_available else 'not available'}" )
    logger.info( f"  DeepLoc:  {'available' if deeploc_available else 'not available'}" )
    logger.info( f"  tmbed:    {'available' if tmbed_available else 'not available'}" )

    # Determine which comparisons can be performed
    can_compare_signalp_deeploc = signalp_available and deeploc_available
    can_compare_tmbed_deeploc = tmbed_available and deeploc_available

    if not can_compare_signalp_deeploc and not can_compare_tmbed_deeploc:
        logger.warning( "WARNING: No cross-tool comparisons can be performed!" )
        logger.warning( "Cross-tool consistency requires at least two overlapping tools." )
        logger.warning( "Comparisons available:" )
        logger.warning( "  SignalP vs DeepLoc: requires both signalp and deeploc" )
        logger.warning( "  tmbed vs DeepLoc: requires both tmbed and deeploc" )
        logger.warning( "" )
        logger.warning( "Creating output file with header only (no data rows)." )

        # Write header-only output file
        output_consistency_path = output_directory / '9_ai-cross_tool_consistency.tsv'
        with open( output_consistency_path, 'w' ) as output_consistency_file:
            header = 'Phyloname (phylogenetic name of species)' + '\t'
            header += 'Comparison_Type (pair of tools being compared e.g. signalp_versus_deeploc_signal)' + '\t'
            header += 'Tool_A_Proteins (count of proteins predicted by tool A)' + '\t'
            header += 'Tool_B_Proteins (count of proteins predicted by tool B)' + '\t'
            header += 'Both_Tools_Proteins (count of proteins predicted by both tools)' + '\t'
            header += 'Agreement_Rate_Percent (both tools divided by union of tool A and tool B times 100)' + '\n'
            output_consistency_file.write( header )

        logger.info( f"Wrote header-only output to: {output_consistency_path}" )
        return

    # =========================================================================
    # Discover species present in each database
    # =========================================================================

    signalp_species = discover_species_from_database_directory( signalp_directory, 'signalp', logger ) if signalp_available else []
    deeploc_species = discover_species_from_database_directory( deeploc_directory, 'deeploc', logger ) if deeploc_available else []
    tmbed_species = discover_species_from_database_directory( tmbed_directory, 'tmbed', logger ) if tmbed_available else []

    logger.info( f"Species with SignalP data: {len( signalp_species )}" )
    logger.info( f"Species with DeepLoc data: {len( deeploc_species )}" )
    logger.info( f"Species with tmbed data: {len( tmbed_species )}" )

    # =========================================================================
    # Perform comparisons
    # =========================================================================

    consistency_records = []

    # ----- Comparison 1: SignalP versus DeepLoc (signal peptide) -----

    if can_compare_signalp_deeploc:
        logger.info( "" )
        logger.info( "Comparison: SignalP versus DeepLoc (signal peptide predictions)" )

        # Species present in both SignalP and DeepLoc
        common_species_signalp_deeploc = sorted( set( signalp_species ) & set( deeploc_species ) )
        logger.info( f"  Species in common: {len( common_species_signalp_deeploc )}" )

        if len( common_species_signalp_deeploc ) == 0:
            logger.warning( "  WARNING: No species have both SignalP and DeepLoc data" )
            logger.warning( "  Cannot compare these tools - skipping this comparison" )
        else:
            for phyloname in common_species_signalp_deeploc:
                # Load SignalP proteins (all proteins with signal peptide predictions)
                signalp_file_path = signalp_directory / f"gigantic_annotations-database_signalp-{phyloname}.tsv"
                signalp_proteins = load_proteins_from_database_file( signalp_file_path, logger )

                # Load DeepLoc proteins with "Signal" annotation
                deeploc_file_path = deeploc_directory / f"gigantic_annotations-database_deeploc-{phyloname}.tsv"
                deeploc_signal_proteins = load_deeploc_proteins_with_annotation( deeploc_file_path, 'Signal', logger )

                # Calculate agreement
                both_tools_proteins = signalp_proteins & deeploc_signal_proteins
                union_proteins = signalp_proteins | deeploc_signal_proteins

                tool_a_count = len( signalp_proteins )
                tool_b_count = len( deeploc_signal_proteins )
                both_count = len( both_tools_proteins )
                union_count = len( union_proteins )

                if union_count > 0:
                    agreement_rate = ( both_count / union_count ) * 100
                else:
                    agreement_rate = 0.0

                consistency_records.append( {
                    'phyloname': phyloname,
                    'comparison_type': 'signalp_versus_deeploc_signal',
                    'tool_a_proteins': tool_a_count,
                    'tool_b_proteins': tool_b_count,
                    'both_tools_proteins': both_count,
                    'agreement_rate_percent': agreement_rate,
                } )

                logger.debug( f"    {phyloname}: SignalP={tool_a_count}, DeepLoc_Signal={tool_b_count}, Both={both_count}, Agreement={agreement_rate:.1f}%" )

            logger.info( f"  Completed comparison for {len( common_species_signalp_deeploc )} species" )

    # ----- Comparison 2: tmbed versus DeepLoc (membrane predictions) -----

    if can_compare_tmbed_deeploc:
        logger.info( "" )
        logger.info( "Comparison: tmbed versus DeepLoc (membrane-associated predictions)" )

        # Species present in both tmbed and DeepLoc
        common_species_tmbed_deeploc = sorted( set( tmbed_species ) & set( deeploc_species ) )
        logger.info( f"  Species in common: {len( common_species_tmbed_deeploc )}" )

        if len( common_species_tmbed_deeploc ) == 0:
            logger.warning( "  WARNING: No species have both tmbed and DeepLoc data" )
            logger.warning( "  Cannot compare these tools - skipping this comparison" )
        else:
            for phyloname in common_species_tmbed_deeploc:
                # Load tmbed proteins with TM regions (excluding signal peptides)
                tmbed_file_path = tmbed_directory / f"gigantic_annotations-database_tmbed-{phyloname}.tsv"
                tmbed_transmembrane_proteins = load_tmbed_proteins_with_transmembrane( tmbed_file_path, logger )

                # Load DeepLoc proteins with "Membrane" annotation
                deeploc_file_path = deeploc_directory / f"gigantic_annotations-database_deeploc-{phyloname}.tsv"
                deeploc_membrane_proteins = load_deeploc_proteins_with_annotation( deeploc_file_path, 'Membrane', logger )

                # Calculate agreement
                both_tools_proteins = tmbed_transmembrane_proteins & deeploc_membrane_proteins
                union_proteins = tmbed_transmembrane_proteins | deeploc_membrane_proteins

                tool_a_count = len( tmbed_transmembrane_proteins )
                tool_b_count = len( deeploc_membrane_proteins )
                both_count = len( both_tools_proteins )
                union_count = len( union_proteins )

                if union_count > 0:
                    agreement_rate = ( both_count / union_count ) * 100
                else:
                    agreement_rate = 0.0

                consistency_records.append( {
                    'phyloname': phyloname,
                    'comparison_type': 'tmbed_versus_deeploc_membrane',
                    'tool_a_proteins': tool_a_count,
                    'tool_b_proteins': tool_b_count,
                    'both_tools_proteins': both_count,
                    'agreement_rate_percent': agreement_rate,
                } )

                logger.debug( f"    {phyloname}: tmbed_TM={tool_a_count}, DeepLoc_Membrane={tool_b_count}, Both={both_count}, Agreement={agreement_rate:.1f}%" )

            logger.info( f"  Completed comparison for {len( common_species_tmbed_deeploc )} species" )

    # =========================================================================
    # Validate that we produced results
    # =========================================================================

    if len( consistency_records ) == 0:
        logger.warning( "WARNING: No cross-tool consistency records were generated!" )
        logger.warning( "This may occur if no species have overlapping tool data." )
        logger.warning( "Creating output file with header only." )

    # =========================================================================
    # Write cross-tool consistency output file
    # =========================================================================

    output_consistency_path = output_directory / '9_ai-cross_tool_consistency.tsv'

    with open( output_consistency_path, 'w' ) as output_consistency_file:
        # Write header
        header = 'Phyloname (phylogenetic name of species)' + '\t'
        header += 'Comparison_Type (pair of tools being compared e.g. signalp_versus_deeploc_signal)' + '\t'
        header += 'Tool_A_Proteins (count of proteins predicted by tool A)' + '\t'
        header += 'Tool_B_Proteins (count of proteins predicted by tool B)' + '\t'
        header += 'Both_Tools_Proteins (count of proteins predicted by both tools)' + '\t'
        header += 'Agreement_Rate_Percent (both tools divided by union of tool A and tool B times 100)' + '\n'
        output_consistency_file.write( header )

        # Sort records by phyloname then comparison type
        sorted_records = sorted( consistency_records, key = lambda record: ( record[ 'phyloname' ], record[ 'comparison_type' ] ) )

        for record in sorted_records:
            output = record[ 'phyloname' ] + '\t'
            output += record[ 'comparison_type' ] + '\t'
            output += str( record[ 'tool_a_proteins' ] ) + '\t'
            output += str( record[ 'tool_b_proteins' ] ) + '\t'
            output += str( record[ 'both_tools_proteins' ] ) + '\t'
            output += f"{record[ 'agreement_rate_percent' ]:.2f}" + '\n'
            output_consistency_file.write( output )

    logger.info( f"Wrote cross-tool consistency to: {output_consistency_path}" )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 009 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Total consistency records: {len( consistency_records )}" )

    if can_compare_signalp_deeploc:
        signalp_deeploc_records = [ record for record in consistency_records if record[ 'comparison_type' ] == 'signalp_versus_deeploc_signal' ]
        if len( signalp_deeploc_records ) > 0:
            average_agreement = sum( record[ 'agreement_rate_percent' ] for record in signalp_deeploc_records ) / len( signalp_deeploc_records )
            logger.info( f"  SignalP vs DeepLoc (signal):" )
            logger.info( f"    Species compared: {len( signalp_deeploc_records )}" )
            logger.info( f"    Average agreement rate: {average_agreement:.1f}%" )

    if can_compare_tmbed_deeploc:
        tmbed_deeploc_records = [ record for record in consistency_records if record[ 'comparison_type' ] == 'tmbed_versus_deeploc_membrane' ]
        if len( tmbed_deeploc_records ) > 0:
            average_agreement = sum( record[ 'agreement_rate_percent' ] for record in tmbed_deeploc_records ) / len( tmbed_deeploc_records )
            logger.info( f"  tmbed vs DeepLoc (membrane):" )
            logger.info( f"    Species compared: {len( tmbed_deeploc_records )}" )
            logger.info( f"    Average agreement rate: {average_agreement:.1f}%" )

    logger.info( "" )
    logger.info( f"  Output file: {output_consistency_path}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Analyze agreement between tools that predict overlapping features'
    )

    parser.add_argument(
        '--statistics',
        type = str,
        required = True,
        help = 'Path to 8_ai-annotation_statistics.tsv from script 008'
    )

    parser.add_argument(
        '--database-dir',
        type = str,
        default = '.',
        help = 'Directory containing database_* directories (default: current directory)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = '.',
        help = 'Output directory for consistency analysis (default: current directory)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    statistics_path = Path( arguments.statistics )
    database_directory = Path( arguments.database_dir )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 009: Analyze Cross-Tool Consistency" )
    logger.info( "=" * 70 )

    # =========================================================================
    # Validate inputs
    # =========================================================================

    validate_statistics_file( statistics_path, logger )

    if not database_directory.exists():
        logger.error( "CRITICAL ERROR: Database directory does not exist!" )
        logger.error( f"Expected path: {database_directory}" )
        logger.error( "Ensure parser scripts (003-007) have been run to create database directories." )
        sys.exit( 1 )

    # =========================================================================
    # Analyze cross-tool consistency
    # =========================================================================

    analyze_cross_tool_consistency( database_directory, output_directory, logger )


if __name__ == '__main__':
    main()
