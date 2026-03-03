#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Auto-scan consolidated output_to_input/BLOCK_*/ directories for available tool results
# Human: Eric Edsinger

"""
001_ai-python-discover_tool_outputs.py

Auto-discovers which annotation tool BLOCKs have produced results by scanning
the consolidated output_to_input/BLOCK_*/ directories under the annotations_hmms
subproject root. Creates a discovery manifest TSV that downstream scripts use to
determine which parsers to run.

The script looks for these tool BLOCKs:
    BLOCK_interproscan  - InterProScan protein domain/function annotations
    BLOCK_deeploc       - DeepLoc subcellular localization predictions
    BLOCK_signalp       - SignalP signal peptide predictions
    BLOCK_tmbed         - tmbed transmembrane topology predictions
    BLOCK_metapredict   - MetaPredict intrinsically disordered region predictions

Each tool BLOCK publishes its results to output_to_input/BLOCK_name/ at the
subproject root when its workflow completes. This script checks which of those
directories contain result files matching each tool's expected file pattern.

Input:
    --annotations-dir: Path to annotations_hmms root directory (parent of BLOCK_* directories)
    --output-dir: Directory for output files

Output:
    1_ai-tool_discovery_manifest.tsv
        Tab-separated file with columns:
        - Tool_Name (name of annotation tool)
        - Tool_Available (yes or no)
        - Output_Directory (path to output_to_input)
        - File_Count (number of result files found)
        - File_Pattern (glob pattern of files found)

    1_ai-log-discover_tool_outputs.log

Usage:
    python3 001_ai-python-discover_tool_outputs.py \\
        --annotations-dir ../../.. \\
        --output-dir .
"""

import argparse
import logging
import sys
from pathlib import Path


# =============================================================================
# Tool definitions: name, BLOCK directory name, expected file glob pattern
# =============================================================================

TOOL_DEFINITIONS = [
    {
        'tool_name': 'interproscan',
        'block_directory_name': 'BLOCK_interproscan',
        'file_pattern': '*_interproscan_results.tsv',
    },
    {
        'tool_name': 'deeploc',
        'block_directory_name': 'BLOCK_deeploc',
        'file_pattern': '*_deeploc_predictions.csv',
    },
    {
        'tool_name': 'signalp',
        'block_directory_name': 'BLOCK_signalp',
        'file_pattern': '*_signalp_predictions.tsv',
    },
    {
        'tool_name': 'tmbed',
        'block_directory_name': 'BLOCK_tmbed',
        'file_pattern': '*_tmbed_predictions.3line',
    },
    {
        'tool_name': 'metapredict',
        'block_directory_name': 'BLOCK_metapredict',
        'file_pattern': '*_metapredict_idrs.tsv',
    },
]


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '001_discover_tool_outputs' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '1_ai-log-discover_tool_outputs.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def discover_tool_outputs( annotations_directory: Path, output_directory: Path, logger: logging.Logger ) -> None:
    """
    Scan sibling BLOCK directories for available tool results and write
    a discovery manifest TSV listing what was found.
    """

    logger.info( f"Scanning for annotation tool outputs in: {annotations_directory}" )

    # =========================================================================
    # Validate annotations directory exists
    # =========================================================================

    if not annotations_directory.exists():
        logger.error( "CRITICAL ERROR: Annotations directory does not exist!" )
        logger.error( f"Expected path: {annotations_directory}" )
        logger.error( "Ensure --annotations-dir points to the annotations_hmms root directory" )
        logger.error( "that contains BLOCK_interproscan/, BLOCK_deeploc/, etc." )
        sys.exit( 1 )

    if not annotations_directory.is_dir():
        logger.error( "CRITICAL ERROR: Annotations path is not a directory!" )
        logger.error( f"Path: {annotations_directory}" )
        sys.exit( 1 )

    # =========================================================================
    # Scan each tool BLOCK for available results
    # =========================================================================

    discovery_records = []
    tools_available_count = 0
    tools_missing_count = 0

    for tool_definition in TOOL_DEFINITIONS:
        tool_name = tool_definition[ 'tool_name' ]
        block_directory_name = tool_definition[ 'block_directory_name' ]
        file_pattern = tool_definition[ 'file_pattern' ]

        # Construct path to this tool's output_to_input directory
        # Consolidated layout: annotations_hmms/output_to_input/BLOCK_name/
        output_to_input_directory = annotations_directory / 'output_to_input' / block_directory_name
        relative_output_directory = str( output_to_input_directory.relative_to( annotations_directory ) )

        logger.info( f"  Checking {tool_name}..." )
        logger.debug( f"    Expected directory: {output_to_input_directory}" )
        logger.debug( f"    File pattern: {file_pattern}" )

        # Check if the output_to_input directory exists
        if not output_to_input_directory.exists():
            logger.info( f"    NOT FOUND: output_to_input/{block_directory_name}/ does not exist" )
            tools_missing_count += 1
            discovery_records.append( {
                'tool_name': tool_name,
                'tool_available': 'no',
                'output_directory': relative_output_directory,
                'file_count': 0,
                'file_pattern': file_pattern,
            } )
            continue

        if not output_to_input_directory.is_dir():
            logger.warning( f"    WARNING: {output_to_input_directory} exists but is not a directory" )
            tools_missing_count += 1
            discovery_records.append( {
                'tool_name': tool_name,
                'tool_available': 'no',
                'output_directory': relative_output_directory,
                'file_count': 0,
                'file_pattern': file_pattern,
            } )
            continue

        # Search for result files matching the expected pattern
        result_files = sorted( output_to_input_directory.glob( file_pattern ) )
        file_count = len( result_files )

        if file_count == 0:
            logger.info( f"    NOT FOUND: Directory exists but no files matching {file_pattern}" )
            tools_missing_count += 1
            discovery_records.append( {
                'tool_name': tool_name,
                'tool_available': 'no',
                'output_directory': relative_output_directory,
                'file_count': 0,
                'file_pattern': file_pattern,
            } )
            continue

        # Tool has results
        tools_available_count += 1
        logger.info( f"    FOUND: {file_count} result file(s)" )

        for result_file in result_files:
            file_size = result_file.stat().st_size
            logger.debug( f"      {result_file.name} ({file_size} bytes)" )

        discovery_records.append( {
            'tool_name': tool_name,
            'tool_available': 'yes',
            'output_directory': relative_output_directory,
            'file_count': file_count,
            'file_pattern': file_pattern,
        } )

    # =========================================================================
    # Validate at least 1 tool has results
    # =========================================================================

    if tools_available_count == 0:
        logger.error( "CRITICAL ERROR: No annotation tool outputs found!" )
        logger.error( f"Scanned {len( TOOL_DEFINITIONS )} tool BLOCKs in: {annotations_directory}" )
        logger.error( "" )
        logger.error( "Expected at least one of these BLOCK directories with results:" )
        for tool_definition in TOOL_DEFINITIONS:
            block_directory_name = tool_definition[ 'block_directory_name' ]
            logger.error( f"  output_to_input/{block_directory_name}/" )
        logger.error( "" )
        logger.error( "Complete at least one annotation tool BLOCK workflow before running" )
        logger.error( "the annotation database builder." )
        sys.exit( 1 )

    # =========================================================================
    # Write discovery manifest
    # =========================================================================

    output_file = output_directory / '1_ai-tool_discovery_manifest.tsv'

    with open( output_file, 'w' ) as output_discovery_manifest:
        # Write header
        header = 'Tool_Name (name of annotation tool)' + '\t'
        header += 'Tool_Available (yes or no indicating if tool results were found)' + '\t'
        header += 'Output_Directory (path to output_to_input directory for this tool)' + '\t'
        header += 'File_Count (number of result files found matching expected pattern)' + '\t'
        header += 'File_Pattern (glob pattern used to find result files)' + '\n'
        output_discovery_manifest.write( header )

        # Write data rows
        for record in discovery_records:
            output = record[ 'tool_name' ] + '\t'
            output += record[ 'tool_available' ] + '\t'
            output += record[ 'output_directory' ] + '\t'
            output += str( record[ 'file_count' ] ) + '\t'
            output += record[ 'file_pattern' ] + '\n'
            output_discovery_manifest.write( output )

    logger.info( f"Wrote discovery manifest to: {output_file}" )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 001 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Tools available: {tools_available_count} of {len( TOOL_DEFINITIONS )}" )
    logger.info( f"  Tools missing:   {tools_missing_count} of {len( TOOL_DEFINITIONS )}" )
    logger.info( "" )
    logger.info( "Tool availability summary:" )
    for record in discovery_records:
        status = "AVAILABLE" if record[ 'tool_available' ] == 'yes' else "MISSING"
        file_info = f"({record[ 'file_count' ]} files)" if record[ 'tool_available' ] == 'yes' else ""
        logger.info( f"  {record[ 'tool_name' ]:<15s} {status:<12s} {file_info}" )
    logger.info( "" )
    logger.info( f"  Output file: {output_file}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Auto-scan sibling BLOCK output_to_input directories for available annotation tool results'
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
        help = 'Output directory for discovery manifest and log (default: current directory)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects and resolve
    annotations_directory = Path( arguments.annotations_dir ).resolve()
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 001: Discover Tool Outputs" )
    logger.info( "=" * 70 )

    # Run discovery
    discover_tool_outputs( annotations_directory, output_directory, logger )


if __name__ == '__main__':
    main()
