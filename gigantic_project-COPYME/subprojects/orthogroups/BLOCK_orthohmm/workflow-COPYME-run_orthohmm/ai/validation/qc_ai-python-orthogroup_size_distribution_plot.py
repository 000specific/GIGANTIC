#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 30 13:05 | Purpose: QC plot of orthogroup size distribution
# Human: Eric Edsinger

"""
qc_ai-python-orthogroup_size_distribution_plot.py

Generates a histogram-style plot showing orthogroup size (x-axis) vs
number of orthogroups at that size (y-axis). Uses log10 scale on both
axes due to the extreme range of values (singletons dominate).

Input:
    OUTPUT_pipeline/5-output/5_ai-orthogroup_size_distribution.tsv
    (produced by script 005)

Output:
    OUTPUT_pipeline/5-output/5_ai-orthogroup_size_distribution.png

Usage:
    conda activate ai_paper_figures
    python3 ai/validation/qc_ai-python-orthogroup_size_distribution_plot.py

    Or with custom paths:
    python3 ai/validation/qc_ai-python-orthogroup_size_distribution_plot.py \\
        --input-file OUTPUT_pipeline/5-output/5_ai-orthogroup_size_distribution.tsv \\
        --output-file OUTPUT_pipeline/5-output/5_ai-orthogroup_size_distribution.png \\
        --title "RUN_1: e=0.0001, mcl=0.5"
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Plot orthogroup size distribution'
    )

    parser.add_argument(
        '--input-file',
        type = str,
        default = 'OUTPUT_pipeline/5-output/5_ai-orthogroup_size_distribution.tsv',
        help = 'Path to size distribution TSV from script 005'
    )

    parser.add_argument(
        '--output-file',
        type = str,
        default = 'OUTPUT_pipeline/5-output/5_ai-orthogroup_size_distribution.png',
        help = 'Output PNG file path'
    )

    parser.add_argument(
        '--title',
        type = str,
        default = '',
        help = 'Plot title (e.g. "RUN_1: e=0.0001, mcl=0.5")'
    )

    arguments = parser.parse_args()

    input_path = Path( arguments.input_file )
    output_path = Path( arguments.output_file )

    # =========================================================================
    # Validate input
    # =========================================================================

    if not input_path.exists():
        print( f"ERROR: Input file not found: {input_path}" )
        print( "Run script 005 first to generate the size distribution." )
        sys.exit( 1 )

    # =========================================================================
    # Read size distribution
    # =========================================================================

    orthogroup_sizes = []
    orthogroup_counts = []

    with open( input_path, 'r' ) as input_file:
        # Orthogroup_Size (number of genes in orthogroup)	Count (number of orthogroups with this size)
        # 1	167575
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_size = int( parts[ 0 ] )
            orthogroup_count = int( parts[ 1 ] )
            orthogroup_sizes.append( orthogroup_size )
            orthogroup_counts.append( orthogroup_count )

    if not orthogroup_sizes:
        print( "ERROR: No data found in input file." )
        sys.exit( 1 )

    total_orthogroups = sum( orthogroup_counts )
    total_singletons = orthogroup_counts[ 0 ] if orthogroup_sizes[ 0 ] == 1 else 0
    max_size = max( orthogroup_sizes )

    print( f"Loaded {len( orthogroup_sizes )} unique sizes" )
    print( f"Total orthogroups: {total_orthogroups:,}" )
    print( f"Singletons: {total_singletons:,} ({total_singletons / total_orthogroups * 100:.1f}%)" )
    print( f"Max orthogroup size: {max_size:,}" )

    # =========================================================================
    # Create plot
    # =========================================================================

    # Colorblind-safe palette (CLAUDE.md: LightBlue2DarkBlue10Steps)
    color_dark_blue = '#003FFF'
    color_light_blue = '#7FD4FF'

    figure, axes = plt.subplots( 1, 1, figsize = ( 10, 6 ) )

    # Scatter plot with log-log scale (data is sparse at large sizes)
    axes.scatter(
        orthogroup_sizes,
        orthogroup_counts,
        s = 8,
        color = color_dark_blue,
        alpha = 0.6,
        edgecolors = 'none'
    )

    axes.set_xscale( 'log' )
    axes.set_yscale( 'log' )

    axes.set_xlabel( 'Orthogroup Size (number of genes)', fontsize = 12 )
    axes.set_ylabel( 'Number of Orthogroups', fontsize = 12 )

    # Build title
    title_text = 'Orthogroup Size Distribution'
    if arguments.title:
        title_text = f'{title_text}\n{arguments.title}'

    subtitle_text = f'{total_orthogroups:,} orthogroups | {total_singletons:,} singletons ({total_singletons / total_orthogroups * 100:.1f}%) | max size: {max_size:,}'
    axes.set_title( title_text, fontsize = 14, fontweight = 'bold', pad = 20 )
    axes.text(
        0.5, 1.02,
        subtitle_text,
        transform = axes.transAxes,
        fontsize = 9,
        ha = 'center',
        va = 'bottom',
        color = 'gray'
    )

    axes.grid( True, alpha = 0.3, which = 'both' )
    axes.tick_params( labelsize = 10 )

    plt.tight_layout()
    plt.subplots_adjust( top = 0.85 )

    # =========================================================================
    # Save
    # =========================================================================

    output_path.parent.mkdir( parents = True, exist_ok = True )
    figure.savefig( output_path, dpi = 200, bbox_inches = 'tight' )
    plt.close( figure )

    print( f"Saved plot to: {output_path}" )


if __name__ == '__main__':
    main()
