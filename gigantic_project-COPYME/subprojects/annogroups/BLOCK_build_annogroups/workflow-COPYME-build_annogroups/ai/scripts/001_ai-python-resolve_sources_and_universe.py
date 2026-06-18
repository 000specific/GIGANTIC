#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 18 | Purpose: Resolve which annotation sources to process and build the proteome sequence universe
# Human: Eric Edsinger

"""
Script 001 — Resolve sources + build the proteome universe.

Two jobs, both shared across all sources:

1. Resolve the **sources** to process. The config requests `all` or an explicit
   subset; a source is processable only if a `parsers/<source>.py` plugin exists.
   Writes the resolved list to a manifest the per-source build step fans out over.

2. Build the **proteome universe** — every sequence identifier across the species
   set's proteomes (genomesDB STEP_4). This is the membership universe used to
   compute `annogroup_<source>_absent` (universe − sequences with an S-feature)
   and to make membership enumeration complete.

Fail-fast: exits 1 if the proteomes are missing, no parsers exist, or a
requested source has no parser.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_annogroups as U


def discover_parsers() -> list:
    """Source names that have a parsers/<source>.py plugin (sorted)."""
    parsers_dir = Path( __file__ ).parent / "parsers"
    sources = []
    for parser_file in sorted( parsers_dir.glob( "*.py" ) ):
        if parser_file.name == "__init__.py":
            continue
        sources.append( parser_file.stem )
    return sources


def resolve_requested_sources( config: dict, available_sources: list ) -> list:
    """Intersect the config request (`all` or a list) with available parsers."""
    requested = config.get( "sources", "all" )
    if requested == "all" or requested == [ "all" ]:
        return available_sources
    if isinstance( requested, str ):
        requested = [ requested ]

    resolved = []
    for source in requested:
        if source not in available_sources:
            print( f"CRITICAL ERROR: requested source '{source}' has no parser", file = sys.stderr )
            print( f"  Available parsers: {', '.join( available_sources )}", file = sys.stderr )
            print( f"  Add parsers/{source}.py or correct the `sources:` list in the config.", file = sys.stderr )
            sys.exit( 1 )
        resolved.append( source )
    return resolved


def build_proteome_universe( proteomes_dir: Path, output_universe_path: Path ) -> int:
    """
    Write every sequence identifier across the species-set proteomes (one row per
    sequence). Returns the sequence count. Universe = the union over all proteome
    FASTAs of their header IDs (the full GIGANTIC identifiers).
    """
    proteome_files = sorted( proteomes_dir.glob( "*.aa" ) )
    if not proteome_files:
        print( f"CRITICAL ERROR: no proteome (*.aa) files in {proteomes_dir}", file = sys.stderr )
        print( "  Verify inputs.proteomes_dir points at genomesDB STEP_4 species proteomes.", file = sys.stderr )
        sys.exit( 1 )

    header_columns = [
        "Sequence_Identifier (full GIGANTIC protein identifier g_GENE-t_RNA-p_PROTEIN-n_PHYLONAME)",
        "Genus_Species (Genus_species parsed from the sequence identifier phyloname)",
    ]

    sequence_count = 0
    with open( output_universe_path, 'w' ) as output_universe:
        output_universe.write( '\t'.join( header_columns ) + '\n' )
        for proteome_file in proteome_files:
            with open( proteome_file, 'r' ) as input_proteome:
                for line in input_proteome:
                    if not line.startswith( '>' ):
                        continue
                    # '>g_..._n_<phyloname>' (id is the first whitespace token)
                    sequence_identifier = line[ 1: ].strip().split()[ 0 ]
                    genus_species = U.genus_species_from_full_id( sequence_identifier )
                    output = sequence_identifier + '\t' + genus_species + '\n'
                    output_universe.write( output )
                    sequence_count += 1
    return sequence_count


def main():
    parser = argparse.ArgumentParser( description = "Resolve sources + build the proteome universe" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    # ---- sources ------------------------------------------------------------
    available_sources = discover_parsers()
    if not available_sources:
        print( "CRITICAL ERROR: no source parsers found in parsers/", file = sys.stderr )
        sys.exit( 1 )
    resolved_sources = resolve_requested_sources( config, available_sources )
    print( f"[001] available parsers: {', '.join( available_sources )}" )
    print( f"[001] sources to process: {', '.join( resolved_sources )}" )

    output_dir = Path( args.output_dir ) / "1-output"
    output_dir.mkdir( parents = True, exist_ok = True )

    output_sources_manifest_path = output_dir / "1_ai-sources_manifest.tsv"
    with open( output_sources_manifest_path, 'w' ) as output_manifest:
        output_manifest.write( "source\n" )   # simple header for NextFlow splitCsv
        for source in resolved_sources:
            output_manifest.write( source + '\n' )

    # ---- proteome universe --------------------------------------------------
    proteomes_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "proteomes_dir" ] )
    output_universe_path = output_dir / "1_ai-proteome_universe.tsv"
    sequence_count = build_proteome_universe( proteomes_dir, output_universe_path )
    print( f"[001] proteome universe: {sequence_count} sequences -> {output_universe_path}" )

    if sequence_count == 0:
        print( "CRITICAL ERROR: proteome universe is empty", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
