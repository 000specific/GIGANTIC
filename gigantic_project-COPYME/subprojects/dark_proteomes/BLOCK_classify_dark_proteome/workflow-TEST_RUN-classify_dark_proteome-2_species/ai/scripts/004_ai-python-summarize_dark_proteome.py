#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Compile cross-species dark proteome summary table
# Human: Eric Edsinger

"""
GIGANTIC dark_proteome BLOCK_classify_dark_proteome - Script 004: Summarize Dark Proteome

Purpose:
    Aggregates per-species dark-proteome summaries into a single project-
    level table. Reports per-species + overall %dark statistics so the user
    can compare species at a glance.

Inputs (CLI):
    --dark-proteome-summaries-dir   Dir of 3_ai-dark_proteome_summary-<sp>.tsv
    --excluded-species              Path to 1_ai-excluded_species.tsv
    --reference-orthogroup-summary  Path to 2_ai-reference_orthogroup_summary.tsv
    --output-dir                    Output directory (typically 4-output)

Outputs (in --output-dir):
    4_ai-cross_species_dark_proteome_summary.tsv
        Per-species + EXCLUDED rows, sorted alphabetically.
    4_ai-project_dark_proteome_summary.tsv
        Single-row project totals.
    4_ai-log-summarize_dark_proteome.log
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_dir: Path ) -> logging.Logger:
    logger = logging.getLogger( 'summarize_dark_proteome' )
    logger.setLevel( logging.INFO )
    log_file = output_dir / '4_ai-log-summarize_dark_proteome.log'
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


def read_per_species_summary( path: Path ) -> dict:
    with open( path, 'r' ) as input_summary:
        header_line = input_summary.readline().rstrip( '\n' )
        data_line = input_summary.readline().rstrip( '\n' )
    header_columns = [ raw.split( ' (' )[ 0 ].strip() for raw in header_line.split( '\t' ) ]
    parts_data = data_line.split( '\t' )
    return dict( zip( header_columns, parts_data ) )


def main() -> int:
    parser = argparse.ArgumentParser( description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( '--dark-proteome-summaries-dir', required = True, type = Path )
    parser.add_argument( '--excluded-species', required = True, type = Path )
    parser.add_argument( '--reference-orthogroup-summary', required = True, type = Path )
    parser.add_argument( '--output-dir', required = True, type = Path )
    args = parser.parse_args()

    args.output_dir.mkdir( parents = True, exist_ok = True )
    logger = setup_logging( args.output_dir )

    logger.info( '=' * 72 )
    logger.info( 'GIGANTIC dark_proteome - Script 004: Summarize Dark Proteome' )
    logger.info( '=' * 72 )

    if not args.dark_proteome_summaries_dir.is_dir():
        logger.error( f'CRITICAL ERROR: dark proteome summaries dir not found: {args.dark_proteome_summaries_dir}' )
        return 1

    summary_paths = sorted( args.dark_proteome_summaries_dir.glob( '3_ai-dark_proteome_summary-*.tsv' ) )
    logger.info( f'  Found {len( summary_paths )} per-species dark proteome summaries' )

    cross_rows = []   # ( genus_species, gene_total, annotated, dark, dark_pct, a, b, c, status )
    processed_species = set()

    project_gene_total = 0
    project_annotated = 0
    project_dark = 0
    project_a = 0
    project_b = 0
    project_c = 0

    blast_mode = ''
    hmm_dbs = ''

    for summary_path in summary_paths:
        # 3_ai-dark_proteome_summary-<Genus_species>.tsv
        genus_species = summary_path.name.replace( '3_ai-dark_proteome_summary-', '' ).replace( '.tsv', '' )
        record = read_per_species_summary( summary_path )
        try:
            gene_total = int( record.get( 'Gene_Total', '0' ) )
            annotated = int( record.get( 'Annotated_Count', '0' ) )
            dark = int( record.get( 'Dark_Count', '0' ) )
            axis_a = int( record.get( 'Axis_A_Reference_Blast_Count', '0' ) )
            axis_b = int( record.get( 'Axis_B_Reference_Orthogroup_Count', '0' ) )
            axis_c = int( record.get( 'Axis_C_HMM_Annotation_Count', '0' ) )
        except ValueError as exc:
            logger.error( f'CRITICAL ERROR: Unparseable summary in {summary_path.name}: {exc}' )
            return 1
        if not blast_mode:
            blast_mode = record.get( 'Reference_Blast_Mode', '' )
            hmm_dbs = record.get( 'Hmm_Databases_CSV', '' )
        dark_pct = ( dark / gene_total * 100 ) if gene_total > 0 else 0.0
        cross_rows.append( ( genus_species, gene_total, annotated, dark, dark_pct, axis_a, axis_b, axis_c, 'PROCESSED' ) )
        processed_species.add( genus_species )
        project_gene_total += gene_total
        project_annotated += annotated
        project_dark += dark
        project_a += axis_a
        project_b += axis_b
        project_c += axis_c

    # Add EXCLUDED rows for species not processed
    if args.excluded_species.is_file():
        with open( args.excluded_species, 'r' ) as input_excluded:
            header_seen = False
            for line in input_excluded:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                if not header_seen:
                    header_seen = True
                    continue
                excluded_species = line.split( '\t' )[ 0 ]
                if excluded_species in processed_species:
                    continue
                cross_rows.append( ( excluded_species, 0, 0, 0, 0.0, 0, 0, 0, 'EXCLUDED' ) )

    cross_rows.sort( key = lambda r: r[ 0 ] )

    # ---- Write cross-species summary ----
    cross_path = args.output_dir / '4_ai-cross_species_dark_proteome_summary.tsv'
    output = 'Genus_Species (species name in Genus_species format)\t'
    output += 'Gene_Total (number of gene records in the proteome; 0 for excluded)\t'
    output += 'Annotated_Count (genes annotated by at least one of the three axes)\t'
    output += 'Dark_Count (genes failing all three axes)\t'
    output += 'Dark_Percent (Dark_Count divided by Gene_Total times 100 rounded to 3 places)\t'
    output += 'Axis_A_Reference_Blast_Count (genes passing axis_a)\t'
    output += 'Axis_B_Reference_Orthogroup_Count (genes passing axis_b)\t'
    output += 'Axis_C_HMM_Annotation_Count (genes passing axis_c)\t'
    output += 'Status (PROCESSED if classified else EXCLUDED)\n'
    for genus_species, gene_total, annotated, dark, dark_pct, axis_a, axis_b, axis_c, status in cross_rows:
        output += genus_species + '\t' + str( gene_total ) + '\t' + str( annotated ) + '\t' + str( dark ) + '\t' + f'{dark_pct:.3f}' + '\t' + str( axis_a ) + '\t' + str( axis_b ) + '\t' + str( axis_c ) + '\t' + status + '\n'
    with open( cross_path, 'w' ) as output_cross:
        output_cross.write( output )
    logger.info( f'  Wrote {cross_path.name} ({len( cross_rows )} rows)' )

    # ---- Project summary ----
    project_path = args.output_dir / '4_ai-project_dark_proteome_summary.tsv'
    project_dark_pct = ( project_dark / project_gene_total * 100 ) if project_gene_total > 0 else 0.0
    excluded_count = sum( 1 for r in cross_rows if r[ -1 ] == 'EXCLUDED' )
    project_output = 'Reference_Blast_Mode (strict_reference or broad_any_nr_hit applied to axis_a)\t'
    project_output += 'Hmm_Databases_CSV (comma delimited HMM databases used for axis_c)\t'
    project_output += 'Processed_Species_Count (species with successful classification)\t'
    project_output += 'Excluded_Species_Count (species in the GIGANTIC list but not processed)\t'
    project_output += 'Project_Gene_Total (sum of gene counts across processed species)\t'
    project_output += 'Project_Annotated_Count (sum of annotated genes across processed species)\t'
    project_output += 'Project_Dark_Count (sum of dark genes across processed species)\t'
    project_output += 'Project_Dark_Percent (Project_Dark_Count divided by Project_Gene_Total times 100)\t'
    project_output += 'Project_Axis_A_Count (sum of axis_a hits across processed species)\t'
    project_output += 'Project_Axis_B_Count (sum of axis_b hits across processed species)\t'
    project_output += 'Project_Axis_C_Count (sum of axis_c hits across processed species)\n'
    project_output += blast_mode + '\t' + hmm_dbs + '\t' + str( len( processed_species ) ) + '\t' + str( excluded_count ) + '\t' + str( project_gene_total ) + '\t' + str( project_annotated ) + '\t' + str( project_dark ) + '\t' + f'{project_dark_pct:.3f}' + '\t' + str( project_a ) + '\t' + str( project_b ) + '\t' + str( project_c ) + '\n'
    with open( project_path, 'w' ) as output_project:
        output_project.write( project_output )
    logger.info( f'  Wrote {project_path.name}' )

    logger.info( '' )
    logger.info( f'  Project totals: {len( processed_species )} species, {project_gene_total} genes, {project_dark} dark ({project_dark_pct:.2f}%)' )
    logger.info( 'Summarization complete.' )
    return 0


if __name__ == '__main__':
    sys.exit( main() )
