#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Compile cross-species hotspot summary table
# Human: Eric Edsinger

"""
GIGANTIC hotspots BLOCK_identify_hotspots - Script 004: Summarize Hotspots

Purpose:
    Aggregates per-species hotspot summaries into a single cross-species
    summary TSV. Reports per-species hotspot counts plus a project-level
    aggregate. Drives at-a-glance comparison across species70.

Inputs (CLI):
    --hotspot-summaries-dir   Directory of 3_ai-hotspot_summary-<sp>.tsv files
    --hotspots-dir            Directory of 3_ai-hotspots-<sp>.tsv files
    --excluded-species        Path to 1_ai-excluded_species.tsv
    --output-dir              Output directory (typically 4-output)

Outputs (in --output-dir):
    4_ai-cross_species_hotspot_summary.tsv
        Per-row: Genus_Species, Window_Size, Hotspot_Count, Hotspot_Member_Total,
                 Average_Paralogs_Per_Hotspot, Largest_Hotspot_Paralog_Count,
                 Status (PROCESSED, EXCLUDED).

    4_ai-project_hotspot_summary.tsv
        Single-row project-level summary (totals across all processed species).

    4_ai-log-summarize_hotspots.log
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    logger = logging.getLogger( 'summarize_hotspots' )
    logger.setLevel( logging.INFO )
    log_file = output_dir / '4_ai-log-summarize_hotspots.log'
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


def read_hotspot_summary( summary_path: Path ) -> dict:
    """Read a single per-species 3_ai-hotspot_summary TSV (1 header + 1 data row).

    Returns: dict of column header (without "(...)") → value.
    """
    with open( summary_path, 'r' ) as input_summary:
        header_line = input_summary.readline().rstrip( '\n' )
        data_line = input_summary.readline().rstrip( '\n' )
    header_columns = [ raw.split( ' (' )[ 0 ].strip() for raw in header_line.split( '\t' ) ]
    parts_data = data_line.split( '\t' )
    return dict( zip( header_columns, parts_data ) )


def count_largest_paralog_count( hotspots_path: Path ) -> int:
    """Find max Paralog_Count from a 3_ai-hotspots-<sp>.tsv file."""
    if not hotspots_path.is_file():
        return 0
    largest = 0
    with open( hotspots_path, 'r' ) as input_hotspots:
        header_line = input_hotspots.readline().rstrip( '\n' )
        header_columns = [ raw.split( ' (' )[ 0 ].strip() for raw in header_line.split( '\t' ) ]
        if 'Paralog_Count' not in header_columns:
            return 0
        paralog_col_index = header_columns.index( 'Paralog_Count' )
        for line in input_hotspots:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if len( parts ) <= paralog_col_index:
                continue
            try:
                count = int( parts[ paralog_col_index ] )
            except ValueError:
                continue
            if count > largest:
                largest = count
    return largest


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--hotspot-summaries-dir', required = True, type = Path )
    parser.add_argument( '--hotspots-dir', required = True, type = Path )
    parser.add_argument( '--excluded-species', required = True, type = Path )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir )

    logger.info( '=' * 72 )
    logger.info( 'GIGANTIC hotspots BLOCK_identify_hotspots - Script 004: Summarize Hotspots' )
    logger.info( '=' * 72 )

    if not args.hotspot_summaries_dir.is_dir():
        logger.error( f'CRITICAL ERROR: hotspot summaries dir not found: {args.hotspot_summaries_dir}' )
        return 1
    if not args.hotspots_dir.is_dir():
        logger.error( f'CRITICAL ERROR: hotspots dir not found: {args.hotspots_dir}' )
        return 1

    summary_paths = sorted( args.hotspot_summaries_dir.glob( '3_ai-hotspot_summary-*.tsv' ) )
    logger.info( f'  Found {len( summary_paths )} per-species hotspot summaries' )

    cross_species_rows = []   # ( genus_species, window_size, hotspot_count, member_total,
                              #   avg_paralogs, largest_paralog_count, status )
    project_hotspot_count = 0
    project_member_total = 0
    project_largest = 0

    processed_species = set()

    for summary_path in summary_paths:
        # 3_ai-hotspot_summary-<Genus_species>.tsv
        genus_species = summary_path.name.replace( '3_ai-hotspot_summary-', '' ).replace( '.tsv', '' )
        record = read_hotspot_summary( summary_path )
        try:
            window_size = int( record.get( 'Window_Size', '0' ) )
            hotspot_count = int( record.get( 'Hotspot_Count', '0' ) )
            member_total = int( record.get( 'Hotspot_Member_Total', '0' ) )
        except ValueError as exc:
            logger.error( f'CRITICAL ERROR: Unparseable summary in {summary_path.name}: {exc}' )
            return 1

        hotspots_path = args.hotspots_dir / f'3_ai-hotspots-{genus_species}.tsv'
        largest = count_largest_paralog_count( hotspots_path )

        avg_paralogs = ( member_total / hotspot_count ) if hotspot_count > 0 else 0.0
        cross_species_rows.append( (
            genus_species,
            window_size,
            hotspot_count,
            member_total,
            avg_paralogs,
            largest,
            'PROCESSED',
        ) )
        processed_species.add( genus_species )
        project_hotspot_count += hotspot_count
        project_member_total += member_total
        if largest > project_largest:
            project_largest = largest

    # ---- Add EXCLUDED species rows for the cross-species table ----
    if args.excluded_species.is_file():
        # Genus_Species\tReason_Excluded
        with open( args.excluded_species, 'r' ) as input_excluded:
            header_seen = False
            for line in input_excluded:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                if not header_seen:
                    header_seen = True
                    continue
                parts = line.split( '\t' )
                excluded_species = parts[ 0 ]
                if excluded_species in processed_species:
                    continue
                cross_species_rows.append( ( excluded_species, 0, 0, 0, 0.0, 0, 'EXCLUDED' ) )

    # Sort cross-species rows alphabetically by species
    cross_species_rows.sort( key = lambda r: r[ 0 ] )

    # ---- Write cross-species summary ----
    cross_path = args.output_dir / '4_ai-cross_species_hotspot_summary.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Window_Size (gene-position window total used in this run; 0 for excluded)\t'
    output += 'Hotspot_Count (number of hotspots called in this species)\t'
    output += 'Hotspot_Member_Total (sum of Paralog_Count across this species hotspots)\t'
    output += 'Average_Paralogs_Per_Hotspot (Hotspot_Member_Total divided by Hotspot_Count rounded to 3 places)\t'
    output += 'Largest_Hotspot_Paralog_Count (size of the biggest hotspot in this species)\t'
    output += 'Status (PROCESSED if hotspots were computed else EXCLUDED)\n'
    for genus_species, window_size, hotspot_count, member_total, avg_paralogs, largest, status in cross_species_rows:
        output += genus_species + '\t' + str( window_size ) + '\t' + str( hotspot_count ) + '\t' + str( member_total ) + '\t' + f'{avg_paralogs:.3f}' + '\t' + str( largest ) + '\t' + status + '\n'
    with open( cross_path, 'w' ) as output_cross:
        output_cross.write( output )
    logger.info( f'  Wrote {cross_path.name} ({len( cross_species_rows )} rows)' )

    # ---- Write project-level summary ----
    project_path = args.output_dir / '4_ai-project_hotspot_summary.tsv'
    project_avg = ( project_member_total / project_hotspot_count ) if project_hotspot_count > 0 else 0.0
    project_output = 'Processed_Species_Count (species with successful hotspot calling)\t'
    project_output += 'Excluded_Species_Count (species in the GIGANTIC list but not processed)\t'
    project_output += 'Project_Hotspot_Count (sum of hotspots across all processed species)\t'
    project_output += 'Project_Member_Total (sum of paralog gene memberships across all hotspots)\t'
    project_output += 'Project_Average_Paralogs_Per_Hotspot (member total divided by hotspot count)\t'
    project_output += 'Project_Largest_Hotspot_Paralog_Count (largest single-species hotspot across project)\n'
    excluded_count = sum( 1 for r in cross_species_rows if r[ -1 ] == 'EXCLUDED' )
    project_output += f'{len( processed_species )}\t{excluded_count}\t{project_hotspot_count}\t{project_member_total}\t{project_avg:.3f}\t{project_largest}\n'
    with open( project_path, 'w' ) as output_project:
        output_project.write( project_output )
    logger.info( f'  Wrote {project_path.name}' )

    logger.info( '' )
    logger.info( f'  Project totals: {len( processed_species )} species, {project_hotspot_count} hotspots, {project_member_total} paralogous gene memberships' )
    logger.info( 'Summarization complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
