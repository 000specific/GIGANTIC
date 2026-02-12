#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Generate taxonomy summary from phylonames mapping
# Human: Eric Edsinger

"""
Generate Taxonomy Summary

This script analyzes a GIGANTIC phylonames mapping file and generates a readable
summary showing:
1. Taxonomic distribution - species counts at each taxonomic level
2. UNOFFICIAL clades - user-provided classifications differing from NCBI
3. Numbered clades - NCBI gaps filled with neutral placeholder names

Input:
    Phylonames mapping TSV file (genus_species<TAB>phyloname)

Output:
    - Markdown summary file
    - HTML summary file (for web viewing)

Usage:
    python 006_ai-python-generate_taxonomy_summary.py --input mapping.tsv --output-dir 6-output/
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime


def parse_phyloname( phyloname ):
    """
    Parse a GIGANTIC phyloname into taxonomic levels.

    Phyloname format: Kingdom_Phylum_Class_Order_Family_Genus_species

    Returns dict with keys: kingdom, phylum, class, order, family, genus, species
    """

    parts = phyloname.split( '_' )

    if len( parts ) < 7:
        return None

    return {
        'kingdom': parts[ 0 ],
        'phylum': parts[ 1 ],
        'class': parts[ 2 ],
        'order': parts[ 3 ],
        'family': parts[ 4 ],
        'genus': parts[ 5 ],
        'species': '_'.join( parts[ 6: ] )  # Handle multi-word species names
    }


def is_unofficial( clade_name ):
    """Check if a clade name has the UNOFFICIAL suffix."""
    return 'UNOFFICIAL' in clade_name


def is_numbered_clade( clade_name ):
    """
    Check if a clade name is a numbered placeholder.

    Numbered clades match patterns like: Kingdom6555, Family16247, Order4294, Class1886
    These are GIGANTIC's neutral gap-filling for incomplete NCBI taxonomy.
    """

    # Match taxonomic rank followed by numbers
    pattern = r'^(Kingdom|Phylum|Class|Order|Family)\d+$'
    return bool( re.match( pattern, clade_name ) )


def analyze_mapping_file( input_path ):
    """
    Analyze a phylonames mapping file and extract statistics.

    Returns dict with:
        - species_by_level: nested dict of species counts by taxonomic level
        - unofficial_clades: dict of unofficial clade names -> list of species
        - numbered_clades: dict of numbered clade names -> list of species
        - total_species: count of species
        - all_entries: list of (genus_species, parsed_phyloname) tuples
    """

    # Track species at each taxonomic level
    species_by_kingdom = defaultdict( list )
    species_by_phylum = defaultdict( list )
    species_by_class = defaultdict( list )
    species_by_order = defaultdict( list )
    species_by_family = defaultdict( list )

    # Track special clades
    unofficial_clades = defaultdict( list )
    numbered_clades = defaultdict( list )

    # Store all entries
    all_entries = []

    # genus_species	phyloname
    # Parvularia_atlantis	Holomycota_CristidiscozoaUNOFFICIAL_Cristidiscoidea_Nucleariida_Family16247_Parvularia_atlantis
    with open( input_path, 'r' ) as input_file:
        for line in input_file:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )
            if len( parts ) < 2:
                continue

            genus_species = parts[ 0 ]
            phyloname = parts[ 1 ]

            parsed = parse_phyloname( phyloname )
            if not parsed:
                print( f"WARNING: Could not parse phyloname: {phyloname}", file = sys.stderr )
                continue

            all_entries.append( ( genus_species, parsed, phyloname ) )

            # Build hierarchical keys for counting
            kingdom = parsed[ 'kingdom' ]
            phylum = parsed[ 'phylum' ]
            class_name = parsed[ 'class' ]
            order = parsed[ 'order' ]
            family = parsed[ 'family' ]

            species_by_kingdom[ kingdom ].append( genus_species )
            species_by_phylum[ ( kingdom, phylum ) ].append( genus_species )
            species_by_class[ ( kingdom, phylum, class_name ) ].append( genus_species )
            species_by_order[ ( kingdom, phylum, class_name, order ) ].append( genus_species )
            species_by_family[ ( kingdom, phylum, class_name, order, family ) ].append( genus_species )

            # Check for unofficial clades at each level
            for level_name, clade_name in [ ( 'kingdom', kingdom ), ( 'phylum', phylum ),
                                            ( 'class', class_name ), ( 'order', order ),
                                            ( 'family', family ) ]:
                if is_unofficial( clade_name ):
                    key = f"{level_name}: {clade_name}"
                    if genus_species not in unofficial_clades[ key ]:
                        unofficial_clades[ key ].append( genus_species )

                if is_numbered_clade( clade_name ):
                    key = f"{level_name}: {clade_name}"
                    if genus_species not in numbered_clades[ key ]:
                        numbered_clades[ key ].append( genus_species )

    return {
        'species_by_kingdom': dict( species_by_kingdom ),
        'species_by_phylum': dict( species_by_phylum ),
        'species_by_class': dict( species_by_class ),
        'species_by_order': dict( species_by_order ),
        'species_by_family': dict( species_by_family ),
        'unofficial_clades': dict( unofficial_clades ),
        'numbered_clades': dict( numbered_clades ),
        'total_species': len( all_entries ),
        'all_entries': all_entries
    }


def generate_markdown_summary( analysis, input_filename, project_name ):
    """Generate a Markdown summary from the analysis results."""

    lines = []
    timestamp = datetime.now().strftime( '%Y-%m-%d %H:%M' )

    # Header
    lines.append( f"# GIGANTIC Phylonames Summary: {project_name}" )
    lines.append( f"" )
    lines.append( f"**Source file**: `{input_filename}`" )
    lines.append( f"**Generated**: {timestamp}" )
    lines.append( f"**Total species**: {analysis[ 'total_species' ]}" )
    lines.append( f"" )
    lines.append( f"---" )
    lines.append( f"" )

    # Taxonomic Distribution
    lines.append( f"## Taxonomic Distribution" )
    lines.append( f"" )

    # Kingdom level
    lines.append( f"### By Kingdom" )
    lines.append( f"" )
    for kingdom in sorted( analysis[ 'species_by_kingdom' ].keys() ):
        count = len( analysis[ 'species_by_kingdom' ][ kingdom ] )
        lines.append( f"- **{kingdom}**: {count} species" )
    lines.append( f"" )

    # Hierarchical view by Kingdom > Phylum
    lines.append( f"### Hierarchical View (Kingdom > Phylum)" )
    lines.append( f"" )

    # Group phyla by kingdom
    phyla_by_kingdom = defaultdict( list )
    for ( kingdom, phylum ), species_list in analysis[ 'species_by_phylum' ].items():
        phyla_by_kingdom[ kingdom ].append( ( phylum, len( species_list ) ) )

    for kingdom in sorted( phyla_by_kingdom.keys() ):
        kingdom_total = len( analysis[ 'species_by_kingdom' ][ kingdom ] )
        lines.append( f"**{kingdom}** ({kingdom_total} species)" )

        for phylum, count in sorted( phyla_by_kingdom[ kingdom ], key = lambda x: -x[ 1 ] ):
            unofficial_mark = " *UNOFFICIAL*" if is_unofficial( phylum ) else ""
            numbered_mark = " *[numbered]*" if is_numbered_clade( phylum ) else ""
            lines.append( f"  - {phylum}: {count} species{unofficial_mark}{numbered_mark}" )

        lines.append( f"" )

    # UNOFFICIAL Clades section
    lines.append( f"---" )
    lines.append( f"" )
    lines.append( f"## UNOFFICIAL Clades" )
    lines.append( f"" )

    if analysis[ 'unofficial_clades' ]:
        lines.append( f"These clades have user-provided classifications that differ from NCBI taxonomy." )
        lines.append( f"The `UNOFFICIAL` suffix indicates human curation." )
        lines.append( f"" )

        for clade_key in sorted( analysis[ 'unofficial_clades' ].keys() ):
            species_list = analysis[ 'unofficial_clades' ][ clade_key ]
            lines.append( f"### {clade_key}" )
            lines.append( f"" )
            lines.append( f"**Species ({len( species_list )}):**" )
            for species in sorted( species_list ):
                lines.append( f"- {species}" )
            lines.append( f"" )
    else:
        lines.append( f"*No UNOFFICIAL clades found.*" )
        lines.append( f"" )

    # Numbered Clades section
    lines.append( f"---" )
    lines.append( f"" )
    lines.append( f"## Numbered Clades (NCBI Gaps)" )
    lines.append( f"" )

    if analysis[ 'numbered_clades' ]:
        lines.append( f"These are GIGANTIC's neutral placeholder names for gaps in NCBI taxonomy." )
        lines.append( f"Consider providing user-defined clade names for these via `user_phylonames.tsv`." )
        lines.append( f"" )

        for clade_key in sorted( analysis[ 'numbered_clades' ].keys() ):
            species_list = analysis[ 'numbered_clades' ][ clade_key ]
            lines.append( f"### {clade_key}" )
            lines.append( f"" )
            lines.append( f"**Species ({len( species_list )}):**" )
            for species in sorted( species_list ):
                lines.append( f"- {species}" )
            lines.append( f"" )
    else:
        lines.append( f"*No numbered clades found - NCBI taxonomy is complete for all species.*" )
        lines.append( f"" )

    # Full species list
    lines.append( f"---" )
    lines.append( f"" )
    lines.append( f"## Full Species List" )
    lines.append( f"" )
    lines.append( f"| Genus_species | Full Phyloname |" )
    lines.append( f"|---------------|----------------|" )

    for genus_species, parsed, phyloname in sorted( analysis[ 'all_entries' ], key = lambda x: x[ 2 ] ):
        lines.append( f"| {genus_species} | {phyloname} |" )

    lines.append( f"" )

    return '\n'.join( lines )


def generate_html_summary( analysis, input_filename, project_name ):
    """Generate an HTML summary from the analysis results."""

    timestamp = datetime.now().strftime( '%Y-%m-%d %H:%M' )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GIGANTIC Phylonames Summary: {project_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        .meta {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .meta strong {{ color: #2c3e50; }}
        .kingdom-block {{
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 5px 5px 0;
        }}
        .kingdom-name {{ font-weight: bold; font-size: 1.1em; color: #2c3e50; }}
        .phylum-list {{ margin-left: 20px; margin-top: 10px; }}
        .unofficial {{ color: #e74c3c; font-style: italic; }}
        .numbered {{ color: #f39c12; font-style: italic; }}
        .clade-section {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .clade-section.unofficial {{ background: #f8d7da; border-color: #f5c6cb; }}
        .clade-section.numbered {{ background: #fff3cd; border-color: #ffc107; }}
        .species-list {{
            column-count: 3;
            column-gap: 20px;
            margin-top: 10px;
        }}
        .species-list li {{ break-inside: avoid; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{ background: #3498db; color: white; }}
        tr:nth-child(even) {{ background: #f2f2f2; }}
        tr:hover {{ background: #e8f4f8; }}
        .collapsible {{
            cursor: pointer;
            user-select: none;
        }}
        .collapsible:after {{
            content: ' [+]';
            color: #3498db;
        }}
        .collapsible.active:after {{
            content: ' [-]';
        }}
        .content {{ display: none; overflow: hidden; }}
    </style>
</head>
<body>
    <h1>GIGANTIC Phylonames Summary: {project_name}</h1>

    <div class="meta">
        <p><strong>Source file:</strong> <code>{input_filename}</code></p>
        <p><strong>Generated:</strong> {timestamp}</p>
        <p><strong>Total species:</strong> {analysis[ 'total_species' ]}</p>
    </div>

    <h2>Taxonomic Distribution</h2>
"""

    # Kingdom blocks
    phyla_by_kingdom = defaultdict( list )
    for ( kingdom, phylum ), species_list in analysis[ 'species_by_phylum' ].items():
        phyla_by_kingdom[ kingdom ].append( ( phylum, len( species_list ) ) )

    for kingdom in sorted( phyla_by_kingdom.keys() ):
        kingdom_total = len( analysis[ 'species_by_kingdom' ][ kingdom ] )
        html += f"""
    <div class="kingdom-block">
        <div class="kingdom-name">{kingdom} ({kingdom_total} species)</div>
        <div class="phylum-list">
            <ul>
"""
        for phylum, count in sorted( phyla_by_kingdom[ kingdom ], key = lambda x: -x[ 1 ] ):
            unofficial_class = ' class="unofficial"' if is_unofficial( phylum ) else ''
            numbered_class = ' class="numbered"' if is_numbered_clade( phylum ) else ''
            extra_class = unofficial_class or numbered_class
            unofficial_mark = ' <span class="unofficial">(UNOFFICIAL)</span>' if is_unofficial( phylum ) else ''
            numbered_mark = ' <span class="numbered">(numbered)</span>' if is_numbered_clade( phylum ) else ''
            html += f'                <li{extra_class}>{phylum}: {count} species{unofficial_mark}{numbered_mark}</li>\n'

        html += """            </ul>
        </div>
    </div>
"""

    # UNOFFICIAL clades section
    html += """
    <h2>UNOFFICIAL Clades</h2>
    <p>These clades have user-provided classifications that differ from NCBI taxonomy.
    The <code>UNOFFICIAL</code> suffix indicates human curation.</p>
"""

    if analysis[ 'unofficial_clades' ]:
        for clade_key in sorted( analysis[ 'unofficial_clades' ].keys() ):
            species_list = analysis[ 'unofficial_clades' ][ clade_key ]
            html += f"""
    <div class="clade-section unofficial">
        <h3 class="collapsible">{clade_key} ({len( species_list )} species)</h3>
        <div class="content">
            <ul class="species-list">
"""
            for species in sorted( species_list ):
                html += f'                <li>{species}</li>\n'
            html += """            </ul>
        </div>
    </div>
"""
    else:
        html += '    <p><em>No UNOFFICIAL clades found.</em></p>\n'

    # Numbered clades section
    html += """
    <h2>Numbered Clades (NCBI Gaps)</h2>
    <p>These are GIGANTIC's neutral placeholder names for gaps in NCBI taxonomy.
    Consider providing user-defined clade names for these via <code>user_phylonames.tsv</code>.</p>
"""

    if analysis[ 'numbered_clades' ]:
        for clade_key in sorted( analysis[ 'numbered_clades' ].keys() ):
            species_list = analysis[ 'numbered_clades' ][ clade_key ]
            html += f"""
    <div class="clade-section numbered">
        <h3 class="collapsible">{clade_key} ({len( species_list )} species)</h3>
        <div class="content">
            <ul class="species-list">
"""
            for species in sorted( species_list ):
                html += f'                <li>{species}</li>\n'
            html += """            </ul>
        </div>
    </div>
"""
    else:
        html += '    <p><em>No numbered clades found - NCBI taxonomy is complete for all species.</em></p>\n'

    # Full species table
    html += """
    <h2>Full Species List</h2>
    <table>
        <thead>
            <tr>
                <th>Genus_species</th>
                <th>Full Phyloname</th>
            </tr>
        </thead>
        <tbody>
"""

    for genus_species, parsed, phyloname in sorted( analysis[ 'all_entries' ], key = lambda x: x[ 2 ] ):
        html += f'            <tr><td>{genus_species}</td><td>{phyloname}</td></tr>\n'

    html += """        </tbody>
    </table>

    <script>
        // Collapsible sections
        var coll = document.getElementsByClassName("collapsible");
        for (var i = 0; i < coll.length; i++) {
            coll[i].addEventListener("click", function() {
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                if (content.style.display === "block") {
                    content.style.display = "none";
                } else {
                    content.style.display = "block";
                }
            });
        }
    </script>
</body>
</html>
"""

    return html


def main():
    """Main function to run the taxonomy summary generator."""

    parser = argparse.ArgumentParser(
        description = 'Generate a taxonomy summary from GIGANTIC phylonames mapping file',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
    # Generate summary to output directory
    python 006_ai-python-generate_taxonomy_summary.py --input mapping.tsv --output-dir 6-output/

    # Specify project name
    python 006_ai-python-generate_taxonomy_summary.py --input mapping.tsv --output-dir 6-output/ --project-name species67
"""
    )

    parser.add_argument(
        '--input', '-i',
        required = True,
        help = 'Input phylonames mapping TSV file (genus_species<TAB>phyloname)'
    )

    parser.add_argument(
        '--output-dir', '-o',
        required = True,
        help = 'Output directory for summary files'
    )

    parser.add_argument(
        '--project-name', '-p',
        default = 'my_project',
        help = 'Project name for summary title (default: my_project)'
    )

    args = parser.parse_args()

    # Validate input file exists
    input_path = Path( args.input )
    if not input_path.exists():
        print( f"ERROR: Input file not found: {input_path}", file = sys.stderr )
        sys.exit( 1 )

    # Create output directory
    output_dir = Path( args.output_dir )
    output_dir.mkdir( parents = True, exist_ok = True )

    # Analyze the mapping file
    print( f"Analyzing: {input_path}" )
    analysis = analyze_mapping_file( input_path )

    print( f"Found {analysis[ 'total_species' ]} species" )
    print( f"  - Kingdoms: {len( analysis[ 'species_by_kingdom' ] )}" )
    print( f"  - UNOFFICIAL clades: {len( analysis[ 'unofficial_clades' ] )}" )
    print( f"  - Numbered clades: {len( analysis[ 'numbered_clades' ] )}" )

    # Generate markdown summary
    markdown_content = generate_markdown_summary( analysis, input_path.name, args.project_name )
    markdown_path = output_dir / f"{args.project_name}_taxonomy_summary.md"
    with open( markdown_path, 'w' ) as output_file:
        output_file.write( markdown_content )
    print( f"Markdown summary: {markdown_path}" )

    # Generate HTML summary
    html_content = generate_html_summary( analysis, input_path.name, args.project_name )
    html_path = output_dir / f"{args.project_name}_taxonomy_summary.html"
    with open( html_path, 'w' ) as output_file:
        output_file.write( html_content )
    print( f"HTML summary: {html_path}" )


if __name__ == '__main__':
    main()
