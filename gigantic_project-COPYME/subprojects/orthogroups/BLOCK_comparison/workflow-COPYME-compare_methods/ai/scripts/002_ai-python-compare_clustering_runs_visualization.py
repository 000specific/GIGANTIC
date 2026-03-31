#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 30 18:00 | Purpose: Visualize orthogroup comparison metrics across clustering runs
# Human: Eric Edsinger

"""
002_ai-python-compare_clustering_runs_visualization.py

Generates comparative visualizations across multiple orthogroup clustering
runs. Supports both OrthoHMM and OrthoFinder formats via the manifest's
clustering_method column.

Produces five plots:
  1. Overlay scatter: log-log size distributions
  2. Summary bar chart: key metrics side-by-side
  3. Single-copy thresholds: line plot
  4. Species completeness: grouped bars
  5. Taxonomic breadth: phyla per orthogroup histogram

Input:
    --manifest: Path to clustering_manifest.tsv in INPUT_user/

Output (written to --output-dir):
    2_ai-compare_clustering_runs-size_distribution.png
    2_ai-compare_clustering_runs-summary_bar_chart.png
    2_ai-compare_clustering_runs-single_copy_thresholds.png
    2_ai-compare_clustering_runs-species_completeness.png
    2_ai-compare_clustering_runs-taxonomic_breadth.png

Usage:
    conda activate ai_paper_figures

    python3 ai/scripts/002_ai-python-compare_clustering_runs_visualization.py \\
        --manifest INPUT_user/clustering_manifest.tsv \\
        --output-dir OUTPUT_pipeline/2-output
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
import numpy


# =============================================================================
# Manifest parsing
# =============================================================================

def parse_manifest( manifest_path: Path ) -> tuple:
    """Parse GIGANTIC clustering manifest. Returns ( labels, dirs, methods )."""

    if not manifest_path.exists():
        print( f"ERROR: Manifest file not found: {manifest_path}" )
        sys.exit( 1 )

    run_labels = []
    run_directories = []
    clustering_methods = []

    with open( manifest_path, 'r' ) as input_file:
        header_found = False
        for line in input_file:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue
            parts = line.split( '\t' )
            if not header_found:
                if parts[ 0 ] == 'run_label':
                    header_found = True
                    continue
                else:
                    print( f"ERROR: Expected header row with 'run_label'." )
                    sys.exit( 1 )
            if len( parts ) < 3:
                print( f"ERROR: Need 3 columns. Got: {line}" )
                sys.exit( 1 )
            output_pipeline_path = Path( parts[ 1 ] )
            if not output_pipeline_path.is_absolute():
                output_pipeline_path = ( manifest_path.parent / output_pipeline_path ).resolve()
            run_labels.append( parts[ 0 ] )
            run_directories.append( output_pipeline_path )
            clustering_methods.append( parts[ 2 ].strip().lower() )

    if len( run_labels ) < 2:
        print( f"ERROR: Need at least 2 runs." )
        sys.exit( 1 )

    return run_labels, run_directories, clustering_methods


# =============================================================================
# Colorblind-safe palette
# =============================================================================

COLORS = [ '#003FFF', '#00BB00', '#FF6600', '#9933FF', '#FF0066', '#00CCCC' ]


# =============================================================================
# File locators and phylum mapping
# =============================================================================

def find_orthohmm_gene_count( run_directory: Path ) -> Path:
    path = run_directory / '4-output' / '4_ai-gene_count_gigantic_ids.tsv'
    if path.exists():
        return path
    for candidate in ( run_directory / '3-output' ).glob( '*gene_count*' ):
        return candidate
    return path


def find_orthofinder_files( run_directory: Path ) -> dict:
    return {
        'gene_count': run_directory / 'Orthogroups' / 'Orthogroups.GeneCount.tsv',
        'orthogroups': run_directory / 'Orthogroups' / 'Orthogroups.tsv',
        'unassigned': run_directory / 'Orthogroups' / 'Orthogroups_UnassignedGenes.tsv',
    }


def find_orthogroups_for_phylum( run_directory: Path, method: str ) -> Path:
    if method == 'orthofinder':
        return run_directory / 'Orthogroups' / 'Orthogroups.tsv'
    path = run_directory / '4-output' / '4_ai-orthogroups_gigantic_ids.tsv'
    if path.exists():
        return path
    for candidate in ( run_directory / '3-output' ).glob( '*orthogroups*' ):
        return candidate
    return path


def build_species_phylum_map( orthogroups_path: Path ) -> dict:
    species_names___phyla = {}
    with open( orthogroups_path, 'r' ) as input_file:
        for line in input_file:
            parts = line.strip().split( '\t' )
            for column_index in range( 1, len( parts ) ):
                cell = parts[ column_index ]
                if not cell:
                    continue
                gene_identifiers = [ g.strip() for g in cell.split( ',' ) ] if ',' in cell else [ cell ]
                for gene_identifier in gene_identifiers:
                    if '-n_' not in gene_identifier:
                        continue
                    phyloname = gene_identifier.split( '-n_' )[ 1 ]
                    parts_phyloname = phyloname.split( '_' )
                    if len( parts_phyloname ) >= 7:
                        genus_species = parts_phyloname[ 5 ] + '_' + '_'.join( parts_phyloname[ 6: ] )
                        if genus_species not in species_names___phyla:
                            species_names___phyla[ genus_species ] = parts_phyloname[ 1 ]
            if len( species_names___phyla ) >= 70:
                break
    return species_names___phyla


# =============================================================================
# Gene count parsers -> unified data dict for plotting
# =============================================================================

def parse_run_data( run_directory: Path, clustering_method: str, species_names___phyla: dict ) -> dict:
    """
    Parse a clustering run and return a unified data dict for plotting.
    Dispatches to method-specific parser.
    """

    if clustering_method == 'orthofinder':
        files = find_orthofinder_files( run_directory )
        return parse_orthofinder_for_plotting( files, species_names___phyla )
    else:
        gene_count_path = find_orthohmm_gene_count( run_directory )
        return parse_orthohmm_for_plotting( gene_count_path, species_names___phyla )


def parse_orthohmm_for_plotting( gene_count_path: Path, species_names___phyla: dict ) -> dict:
    """Parse OrthoHMM gene count into plotting data."""

    with open( gene_count_path, 'r' ) as input_file:
        header_line = input_file.readline().strip()
        parts_header = header_line.split()
        species_names = [ name.replace( '.pep', '' ) for name in parts_header[ 1: ] ]

        all_counts = []
        for line in input_file:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            all_counts.append( [ int( v ) for v in parts[ 1: ] ] )

    return compute_plot_data( species_names, all_counts, species_names___phyla )


def parse_orthofinder_for_plotting( files: dict, species_names___phyla: dict ) -> dict:
    """Parse OrthoFinder GeneCount + Unassigned into plotting data."""

    species_names = []
    all_counts = []

    with open( files[ 'gene_count' ], 'r' ) as input_file:
        header_line = input_file.readline().strip()
        parts_header = header_line.split( '\t' )
        for col in range( 1, len( parts_header ) ):
            if parts_header[ col ] == 'Total':
                break
            species_names.append( parts_header[ col ] )

        species_count = len( species_names )

        for line in input_file:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            all_counts.append( [ int( parts[ i ] ) for i in range( 1, species_count + 1 ) ] )

    # Add unassigned genes
    if files[ 'unassigned' ].exists():
        with open( files[ 'unassigned' ], 'r' ) as input_file:
            input_file.readline()  # skip header
            for line in input_file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split( '\t' )
                counts = []
                for col in range( 1, species_count + 1 ):
                    if col < len( parts ) and parts[ col ]:
                        counts.append( len( [ g for g in parts[ col ].split( ', ' ) if g.strip() ] ) )
                    else:
                        counts.append( 0 )
                all_counts.append( counts )

    return compute_plot_data( species_names, all_counts, species_names___phyla )


def compute_plot_data( species_names: list, all_counts: list, species_names___phyla: dict ) -> dict:
    """Compute all metrics needed for plotting from standardized count vectors."""

    species_count = len( species_names )
    half_species = species_count // 2

    species_indices___phyla = {}
    for i in range( species_count ):
        species_indices___phyla[ i ] = species_names___phyla.get( species_names[ i ], 'Unknown' )

    sizes___counts = {}
    total_orthogroups = 0
    total_sequences = 0
    singleton_count = 0

    single_copy_one_species_count = 0
    single_copy_two_or_more_species_count = 0
    single_copy_all_species_count = 0
    single_copy_threshold_50_count = 0
    single_copy_threshold_75_count = 0
    single_copy_threshold_90_count = 0

    completeness_universal = 0
    completeness_near_universal = 0
    completeness_half_plus = 0
    completeness_some = 0
    completeness_few = 0

    phyla_per_orthogroup_values = []

    for counts in all_counts:
        orthogroup_size = sum( counts )
        total_sequences += orthogroup_size
        total_orthogroups += 1

        if orthogroup_size not in sizes___counts:
            sizes___counts[ orthogroup_size ] = 0
        sizes___counts[ orthogroup_size ] += 1

        if orthogroup_size == 1:
            singleton_count += 1

        species_present = 0
        single_copy_species = 0
        phyla_in_og = set()

        for i in range( species_count ):
            if counts[ i ] > 0:
                species_present += 1
                phyla_in_og.add( species_indices___phyla[ i ] )
                if counts[ i ] == 1:
                    single_copy_species += 1

        all_sc = ( single_copy_species == species_present )

        if all_sc and species_present == 1:
            single_copy_one_species_count += 1
        if all_sc and species_present >= 2:
            single_copy_two_or_more_species_count += 1
        if all_sc and species_present == species_count:
            single_copy_all_species_count += 1

        if species_present >= 2:
            frac = single_copy_species / species_present
            if frac >= 0.50:
                single_copy_threshold_50_count += 1
            if frac >= 0.75:
                single_copy_threshold_75_count += 1
            if frac >= 0.90:
                single_copy_threshold_90_count += 1
            phyla_per_orthogroup_values.append( len( phyla_in_og ) )

        if species_present == species_count:
            completeness_universal += 1
        elif species_present >= 50:
            completeness_near_universal += 1
        elif species_present >= half_species:
            completeness_half_plus += 1
        elif species_present >= 10:
            completeness_some += 1
        elif species_present >= 2:
            completeness_few += 1

    return {
        'sizes___counts': sizes___counts,
        'total_orthogroups': total_orthogroups,
        'total_sequences': total_sequences,
        'singleton_count': singleton_count,
        'species_count': species_count,
        'max_size': max( sizes___counts.keys() ) if sizes___counts else 0,
        'single_copy_one_species_count': single_copy_one_species_count,
        'single_copy_two_or_more_species_count': single_copy_two_or_more_species_count,
        'single_copy_all_species_count': single_copy_all_species_count,
        'single_copy_threshold_50_count': single_copy_threshold_50_count,
        'single_copy_threshold_75_count': single_copy_threshold_75_count,
        'single_copy_threshold_90_count': single_copy_threshold_90_count,
        'completeness_universal': completeness_universal,
        'completeness_near_universal': completeness_near_universal,
        'completeness_half_plus': completeness_half_plus,
        'completeness_some': completeness_some,
        'completeness_few': completeness_few,
        'phyla_per_orthogroup_values': phyla_per_orthogroup_values,
    }


# =============================================================================
# Plot functions (unchanged from previous version)
# =============================================================================

def plot_size_distributions( runs_data, output_path ):
    figure, axes = plt.subplots( 1, 1, figsize = ( 12, 7 ) )
    for index in range( len( runs_data ) ):
        label, data = runs_data[ index ]
        color = COLORS[ index % len( COLORS ) ]
        sizes = sorted( data[ 'sizes___counts' ].keys() )
        counts = [ data[ 'sizes___counts' ][ s ] for s in sizes ]
        total = data[ 'total_orthogroups' ]
        sp = data[ 'singleton_count' ] / total * 100 if total > 0 else 0
        axes.scatter( sizes, counts, s = 12, color = color, alpha = 0.5, edgecolors = 'none', label = f"{label} ({total:,} OGs, {sp:.0f}% singletons)" )
    axes.set_xscale( 'log' ); axes.set_yscale( 'log' )
    axes.set_xlabel( 'Orthogroup Size (number of genes)', fontsize = 12 )
    axes.set_ylabel( 'Number of Orthogroups', fontsize = 12 )
    axes.set_title( 'Orthogroup Size Distribution - Clustering Run Comparison', fontsize = 14, fontweight = 'bold' )
    axes.legend( fontsize = 9, loc = 'upper right', framealpha = 0.9 )
    axes.grid( True, alpha = 0.3, which = 'both' )
    plt.tight_layout()
    figure.savefig( output_path, dpi = 200, bbox_inches = 'tight' ); plt.close( figure )
    print( f"Saved: {output_path.name}" )


def plot_summary_bar_chart( runs_data, output_path ):
    metric_keys = [
        ( 'total_orthogroups', 'Total\nOrthogroups' ), ( 'singleton_count', 'Singleton\nOrthogroups' ),
        ( 'single_copy_one_species_count', 'Single-Copy\n(1 Species)' ),
        ( 'single_copy_two_or_more_species_count', 'Single-Copy\n(2+ Species)' ),
        ( 'single_copy_all_species_count', 'Single-Copy\n(All Species)' ),
        ( 'completeness_universal', 'Universal\nOrthogroups' ),
    ]
    n_runs = len( runs_data ); n_metrics = len( metric_keys ); bw = 0.8 / n_runs
    figure, axes = plt.subplots( 1, 1, figsize = ( 16, 7 ) )
    for ri in range( n_runs ):
        label, data = runs_data[ ri ]; color = COLORS[ ri % len( COLORS ) ]
        xp = [ i + ( ri - n_runs / 2 + 0.5 ) * bw for i in range( n_metrics ) ]
        vals = [ data[ k ] for k, _ in metric_keys ]
        bars = axes.bar( xp, vals, width = bw, color = color, alpha = 0.8, label = label, edgecolor = 'white', linewidth = 0.5 )
        for b, v in zip( bars, vals ):
            if v > 0:
                axes.text( b.get_x() + b.get_width() / 2, b.get_height(), f'{v:,}', ha = 'center', va = 'bottom', fontsize = 6, rotation = 45 )
    axes.set_xticks( range( n_metrics ) ); axes.set_xticklabels( [ l for _, l in metric_keys ], fontsize = 9 )
    axes.set_ylabel( 'Count', fontsize = 12 )
    axes.set_title( 'Clustering Run Comparison - Key Metrics', fontsize = 14, fontweight = 'bold' )
    axes.legend( fontsize = 10, loc = 'upper right' ); axes.grid( True, alpha = 0.3, axis = 'y' )
    all_v = [ data[ k ] for _, data in runs_data for k, _ in metric_keys ]
    nz = [ v for v in all_v if v > 0 ]
    if nz and max( nz ) / max( min( nz ), 1 ) > 1000:
        axes.set_yscale( 'log' ); axes.set_ylabel( 'Count (log scale)', fontsize = 12 )
    plt.tight_layout(); figure.savefig( output_path, dpi = 200, bbox_inches = 'tight' ); plt.close( figure )
    print( f"Saved: {output_path.name}" )


def plot_single_copy_thresholds( runs_data, output_path ):
    thresholds = [
        ( 'single_copy_threshold_50_count', '>=50%' ), ( 'single_copy_threshold_75_count', '>=75%' ),
        ( 'single_copy_threshold_90_count', '>=90%' ),
        ( 'single_copy_two_or_more_species_count', '100%\n(2+ sp)' ),
        ( 'single_copy_all_species_count', '100%\n(all sp)' ),
    ]
    figure, axes = plt.subplots( 1, 1, figsize = ( 10, 6 ) )
    xp = list( range( len( thresholds ) ) )
    for ri in range( len( runs_data ) ):
        label, data = runs_data[ ri ]; color = COLORS[ ri % len( COLORS ) ]
        vals = [ data[ k ] for k, _ in thresholds ]
        axes.plot( xp, vals, marker = 'o', markersize = 8, linewidth = 2, color = color, label = label, alpha = 0.8 )
        for x, v in zip( xp, vals ):
            axes.annotate( f'{v:,}', ( x, v ), textcoords = 'offset points', xytext = ( 0, 10 ), ha = 'center', fontsize = 8, color = color )
    axes.set_xticks( xp ); axes.set_xticklabels( [ l for _, l in thresholds ], fontsize = 10 )
    axes.set_xlabel( 'Single-Copy Threshold', fontsize = 11 ); axes.set_ylabel( 'Number of Orthogroups', fontsize = 12 )
    axes.set_title( 'Single-Copy Orthogroups by Threshold Stringency', fontsize = 14, fontweight = 'bold' )
    axes.legend( fontsize = 10 ); axes.grid( True, alpha = 0.3 )
    plt.tight_layout(); figure.savefig( output_path, dpi = 200, bbox_inches = 'tight' ); plt.close( figure )
    print( f"Saved: {output_path.name}" )


def plot_species_completeness( runs_data, output_path ):
    keys = [
        ( 'completeness_universal', 'Universal\n(all species)' ), ( 'completeness_near_universal', 'Near-Universal\n(50+ species)' ),
        ( 'completeness_half_plus', 'Half-Plus\n(35-49 species)' ), ( 'completeness_some', 'Some\n(10-34 species)' ),
        ( 'completeness_few', 'Few\n(2-9 species)' ),
    ]
    n_runs = len( runs_data ); n_bins = len( keys ); bw = 0.8 / n_runs
    figure, axes = plt.subplots( 1, 1, figsize = ( 12, 6 ) )
    for ri in range( n_runs ):
        label, data = runs_data[ ri ]; color = COLORS[ ri % len( COLORS ) ]
        xp = [ i + ( ri - n_runs / 2 + 0.5 ) * bw for i in range( n_bins ) ]
        vals = [ data[ k ] for k, _ in keys ]
        bars = axes.bar( xp, vals, width = bw, color = color, alpha = 0.8, label = label, edgecolor = 'white', linewidth = 0.5 )
        for b, v in zip( bars, vals ):
            if v > 0:
                axes.text( b.get_x() + b.get_width() / 2, b.get_height(), f'{v:,}', ha = 'center', va = 'bottom', fontsize = 7, rotation = 45 )
    axes.set_xticks( range( n_bins ) ); axes.set_xticklabels( [ l for _, l in keys ], fontsize = 9 )
    axes.set_ylabel( 'Number of Orthogroups', fontsize = 12 )
    axes.set_title( 'Species Completeness - Clustering Run Comparison', fontsize = 14, fontweight = 'bold' )
    axes.legend( fontsize = 10 ); axes.grid( True, alpha = 0.3, axis = 'y' )
    plt.tight_layout(); figure.savefig( output_path, dpi = 200, bbox_inches = 'tight' ); plt.close( figure )
    print( f"Saved: {output_path.name}" )


def plot_taxonomic_breadth( runs_data, output_path ):
    figure, axes = plt.subplots( 1, 1, figsize = ( 12, 6 ) )
    max_phyla = max( max( data[ 'phyla_per_orthogroup_values' ] ) for _, data in runs_data if data[ 'phyla_per_orthogroup_values' ] )
    bins = numpy.arange( 0.5, max_phyla + 1.5, 1 )
    for ri in range( len( runs_data ) ):
        label, data = runs_data[ ri ]; color = COLORS[ ri % len( COLORS ) ]
        vals = data[ 'phyla_per_orthogroup_values' ]
        if vals:
            axes.hist( vals, bins = bins, color = color, alpha = 0.4, label = f"{label} (mean={numpy.mean( vals ):.1f})", edgecolor = color, linewidth = 1.0 )
    axes.set_xlabel( 'Number of Phyla in Orthogroup', fontsize = 12 )
    axes.set_ylabel( 'Number of Orthogroups (log scale)', fontsize = 12 )
    axes.set_title( 'Taxonomic Breadth - Phyla per Orthogroup', fontsize = 14, fontweight = 'bold' )
    axes.legend( fontsize = 10 ); axes.grid( True, alpha = 0.3, axis = 'y' ); axes.set_yscale( 'log' )
    plt.tight_layout(); figure.savefig( output_path, dpi = 200, bbox_inches = 'tight' ); plt.close( figure )
    print( f"Saved: {output_path.name}" )


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser( description = 'Visualize orthogroup comparison metrics' )
    parser.add_argument( '--manifest', type = str, required = True, help = 'Path to clustering_manifest.tsv' )
    parser.add_argument( '--output-dir', type = str, default = '.', help = 'Output directory for PNG files' )

    arguments = parser.parse_args()
    manifest_path = Path( arguments.manifest )
    output_directory = Path( arguments.output_dir )

    run_labels, run_directories, clustering_methods = parse_manifest( manifest_path )
    print( f"Loaded manifest: {manifest_path} ({len( run_labels )} runs)" )

    # Build species -> phylum mapping
    og_path = find_orthogroups_for_phylum( run_directories[ 0 ], clustering_methods[ 0 ] )
    if not og_path.exists():
        print( f"ERROR: Orthogroups file not found: {og_path}" )
        sys.exit( 1 )
    print( "Building species -> phylum mapping..." )
    species_names___phyla = build_species_phylum_map( og_path )

    # Parse all runs
    runs_data = []
    for index in range( len( run_directories ) ):
        print( f"Loading {run_labels[ index ]} ({clustering_methods[ index ]}): {run_directories[ index ]}" )
        data = parse_run_data( run_directories[ index ], clustering_methods[ index ], species_names___phyla )
        runs_data.append( ( run_labels[ index ], data ) )

    # Generate plots
    output_directory.mkdir( parents = True, exist_ok = True )
    plot_size_distributions( runs_data, output_directory / '2_ai-compare_clustering_runs-size_distribution.png' )
    plot_summary_bar_chart( runs_data, output_directory / '2_ai-compare_clustering_runs-summary_bar_chart.png' )
    plot_single_copy_thresholds( runs_data, output_directory / '2_ai-compare_clustering_runs-single_copy_thresholds.png' )
    plot_species_completeness( runs_data, output_directory / '2_ai-compare_clustering_runs-species_completeness.png' )
    plot_taxonomic_breadth( runs_data, output_directory / '2_ai-compare_clustering_runs-taxonomic_breadth.png' )

    print( f"\nAll 5 plots saved to: {output_directory}" )


if __name__ == '__main__':
    main()
