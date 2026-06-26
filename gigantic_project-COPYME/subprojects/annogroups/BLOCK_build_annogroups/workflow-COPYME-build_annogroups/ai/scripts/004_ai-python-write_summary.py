#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 18 | Purpose: Write cross-source annogroups summary tables (per source, per species, per phylum)
# Human: Eric Edsinger

"""
Script 004 — Cross-source annogroups summary.

Aggregates every built source into summary tables. Runs ONCE, after all sources
have been built + validated.

Three output tables (OUTPUT_pipeline/4-output/):

  4_ai-annogroups_summary.tsv
      One row per SOURCE: the per-type annogroup breakdown
      (feature / combination / architecture / absent) that the per-source
      validation report (Script 003) does NOT carry, plus universe / annotated /
      absent sequence counts, the dropped-orphan count, and validation status.

  4_ai-annogroups_summary-per_species.tsv
      One row per SPECIES (Genus_species); annotation SOURCES are the columns.
      Each source cell = the species' annotated sequence count for that source
      (sequences with >=1 feature). Universe count is the leading context column.

  4_ai-annogroups_summary-per_phylum.tsv
      One row per PHYLUM; annotation SOURCES are the columns (same cell meaning).

Reads, per source:
  - 2-output/<source>/2_ai-<source>-annogroup_map.tsv          (per-type counts)
  - 2-output/<source>/2_ai-<source>-annogroup_membership.tsv   (absent rows -> per species/phylum)
  - 2-output/<source>/2_ai-<source>-dropped_orphan_sequences.tsv (dropped count)
  - 3-output/<source>/3_ai-<source>-validation_report.txt       (PASS/FAIL)
and the global proteome universe (1-output/1_ai-proteome_universe.tsv) for the
per-species / per-phylum universe denominators.

Fail-fast: exits 1 if the sources manifest, universe, or a source's map/membership
is missing.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_annogroups as U

ANNOGROUP_TYPES = [ "feature", "combination", "architecture", "absent" ]


def build_universe_breakdown( universe_path: Path ) -> dict:
    """
    Tally the proteome universe by species and by phylum.
    Returns dict with:
      total                          : int
      genus_species___universe_count : { Genus_species: count }
      genus_species___phylum         : { Genus_species: Phylum }
      phylum___universe_count        : { Phylum: count }
      phylum___species               : { Phylum: set(Genus_species) }
    """
    total = 0
    genus_species___universe_count = defaultdict( int )
    genus_species___phylum = {}
    phylum___universe_count = defaultdict( int )
    phylum___species = defaultdict( set )

    # Sequence_Identifier (...)\tGenus_Species (...)
    # g_..._n_<phyloname>\tSphaeroforma_arctica
    with open( universe_path, 'r' ) as input_universe:
        header_ids___indices = U.build_header_index( input_universe.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_genus_species = header_ids___indices[ "Genus_Species" ]
        for line in input_universe:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_identifier = parts[ index_sequence ]
            genus_species = parts[ index_genus_species ]
            phylum = U.phylum_from_full_id( sequence_identifier )
            total += 1
            genus_species___universe_count[ genus_species ] += 1
            genus_species___phylum[ genus_species ] = phylum
            phylum___universe_count[ phylum ] += 1
            phylum___species[ phylum ].add( genus_species )

    return {
        "total": total,
        "genus_species___universe_count": genus_species___universe_count,
        "genus_species___phylum": genus_species___phylum,
        "phylum___universe_count": phylum___universe_count,
        "phylum___species": phylum___species,
    }


def build_absent_breakdown( membership_path: Path ) -> dict:
    """
    Tally a source's absent sequences by species and by phylum (from the
    type==absent membership rows). Returns:
      genus_species___absent_count : { Genus_species: count }
      phylum___absent_count        : { Phylum: count }
    """
    genus_species___absent_count = defaultdict( int )
    phylum___absent_count = defaultdict( int )

    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_genus_species = header_ids___indices[ "Genus_Species" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_type ] != "absent":
                continue
            genus_species = parts[ index_genus_species ]
            phylum = U.phylum_from_full_id( parts[ index_sequence ] )
            genus_species___absent_count[ genus_species ] += 1
            phylum___absent_count[ phylum ] += 1

    return {
        "genus_species___absent_count": genus_species___absent_count,
        "phylum___absent_count": phylum___absent_count,
    }


def read_validation_status( report_path: Path ) -> str:
    """Extract 'PASS' / 'FAIL' from a Script 003 report, else a marker."""
    if not report_path.is_file():
        return "MISSING"
    with open( report_path, 'r' ) as input_report:
        for line in input_report:
            if line.startswith( "Status:" ):
                return line.split( ':', 1 )[ 1 ].strip()
    return "UNKNOWN"


def count_dropped_orphans( dropped_path: Path ) -> int:
    """Number of dropped orphan identifiers (excludes header); 0 if file absent."""
    if not dropped_path.is_file():
        return 0
    dropped_count = 0
    with open( dropped_path, 'r' ) as input_dropped:
        input_dropped.readline()
        for line in input_dropped:
            if line.strip():
                dropped_count += 1
    return dropped_count


def summarize_source_map( map_path: Path ) -> dict:
    """Per-type annogroup counts + the absent-sequence count, from a source's map."""
    types___annogroup_counts = defaultdict( int )
    absent_sequences = 0
    with open( map_path, 'r' ) as input_map:
        header_ids___indices = U.build_header_index( input_map.readline() )
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_sequence_count = header_ids___indices[ "Sequence_Count" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_type = parts[ index_type ]
            types___annogroup_counts[ annogroup_type ] += 1
            if annogroup_type == "absent":
                absent_sequences += int( parts[ index_sequence_count ] )
    summary = { annogroup_type: types___annogroup_counts.get( annogroup_type, 0 ) for annogroup_type in ANNOGROUP_TYPES }
    summary[ "absent_sequences" ] = absent_sequences
    summary[ "total" ] = sum( types___annogroup_counts.values() )
    return summary


def load_phylum_species_sets( config, workflow_root ):
    """
    Load the five metazoan-group species sets + Metazoa (trees_species clades) for
    the reference structure and FAIL-FAST that the five phyla PARTITION Metazoa
    (pairwise disjoint AND union == Metazoa). Returns ( phyla___species,
    metazoan_species ). A silent partition error would misclassify annogroups.
    """
    mappings_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "clade_species_mappings" ] )
    if not mappings_path.is_file():
        print( f"CRITICAL ERROR: clade-species mapping not found: {mappings_path}", file = sys.stderr )
        print( "  Needed to classify annogroups into metazoan phylum-composition classes.", file = sys.stderr )
        sys.exit( 1 )
    reference_structure = config[ "inputs" ][ "phylum_reference_structure" ]
    phyla___clade_id_names = {
        "Ctenophora": config[ "inputs" ][ "ctenophora_clade_id_name" ],
        "Porifera":   config[ "inputs" ][ "porifera_clade_id_name" ],
        "Placozoa":   config[ "inputs" ][ "placozoa_clade_id_name" ],
        "Cnidaria":   config[ "inputs" ][ "cnidaria_clade_id_name" ],
        "Bilateria":  config[ "inputs" ][ "bilateria_clade_id_name" ],
    }
    metazoan_species = U.load_clade_species( mappings_path, reference_structure, config[ "inputs" ][ "metazoa_clade_id_name" ] )
    phyla___species = {}
    for phylum, clade_id_name in phyla___clade_id_names.items():
        phyla___species[ phylum ] = U.load_clade_species( mappings_path, reference_structure, clade_id_name )
        if not phyla___species[ phylum ]:
            print( f"CRITICAL ERROR: phylum clade '{clade_id_name}' resolved to zero species for {reference_structure}", file = sys.stderr )
            sys.exit( 1 )
    if not metazoan_species:
        print( f"CRITICAL ERROR: Metazoa clade resolved to zero species for {reference_structure}", file = sys.stderr )
        sys.exit( 1 )

    union_species = set()
    for phylum in U.METAZOAN_PHYLA:
        if union_species & phyla___species[ phylum ]:
            print( f"CRITICAL ERROR: metazoan phylum clades are NOT disjoint at {phylum}", file = sys.stderr )
            sys.exit( 1 )
        union_species |= phyla___species[ phylum ]
    if union_species != metazoan_species:
        print( "CRITICAL ERROR: the five metazoan phylum clades do not partition Metazoa", file = sys.stderr )
        print( f"  Metazoa ({len( metazoan_species )}) != union of phyla ({len( union_species )})", file = sys.stderr )
        sys.exit( 1 )
    print( f"[004] phylum partition verified: {len( union_species )} species across {', '.join( U.METAZOAN_PHYLA )} == Metazoa" )
    return phyla___species, metazoan_species


def write_source_phylum_composition_counts( map_path, source, phyla___species, metazoan_species, output_dir ):
    """
    Classify every annogroup of one source by its member-species metazoan
    phylum-composition class (the trees_species metazoan-group partition) and write
    a counts table: one row per named class (paired _Only / _With_NonMetazoan) plus
    'unclassified', with the annogroup count and percentage. Reads Species_List from
    the source's annogroup map.
    """
    classes___counts = { class_key: 0 for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS }
    classes___counts[ "unclassified" ] = 0

    with open( map_path, 'r' ) as input_map:
        header_ids___indices = U.build_header_index( input_map.readline() )
        index_species_list = header_ids___indices[ "Species_List" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            species_cell = parts[ index_species_list ] if index_species_list < len( parts ) else ""
            member_species = { s for s in species_cell.split( ',' ) if s }
            signature_cell, has_nonmetazoan = U.phylum_signature_of_species( member_species, phyla___species, metazoan_species )
            phylum_composition_class = U.named_phylum_class( U.parse_signature_cell( signature_cell ), has_nonmetazoan )
            classes___counts[ phylum_composition_class ] += 1

    total_annogroups = sum( classes___counts.values() )
    output_path = output_dir / f"4_ai-{source}-annogroup_phylum_composition_counts.tsv"
    with open( output_path, 'w' ) as output_counts:
        output = 'Phylum_Composition_Class (metazoan-group phylum-composition class of the annogroup member species using the trees_species partition Ctenophora Porifera Placozoa Cnidaria Bilateria; _With_NonMetazoan = same metazoan phyla plus non-metazoan outgroups; unclassified = signature not one of the named classes; NOT the raw NCBI Phylum field)\t'
        output += 'Annogroup_Count (count of annogroups of this source in this phylum-composition class)\t'
        output += 'Percentage (percentage of this source annogroups in this class calculated as count divided by total times 100)\n'
        output_counts.write( output )
        for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS + [ "unclassified" ]:
            count = classes___counts.get( class_key, 0 )
            percentage = 100.0 * count / total_annogroups if total_annogroups > 0 else 0.0
            output_counts.write( f"{class_key}\t{count}\t{percentage:.2f}\n" )

    return output_path, total_annogroups


def main():
    parser = argparse.ArgumentParser( description = "Write cross-source annogroups summary tables" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    output_base = Path( args.output_dir )
    universe_path = output_base / "1-output" / "1_ai-proteome_universe.tsv"
    sources_manifest_path = output_base / "1-output" / "1_ai-sources_manifest.tsv"

    for required in ( universe_path, sources_manifest_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required file not found: {required}", file = sys.stderr )
            print( "  Script 001 (resolve_sources_and_universe) must run before this script.", file = sys.stderr )
            sys.exit( 1 )

    universe = build_universe_breakdown( universe_path )
    universe_total = universe[ "total" ]

    # sources to summarize (the resolved set Script 001 wrote)
    sources = []
    with open( sources_manifest_path, 'r' ) as input_manifest:
        input_manifest.readline()  # 'source' header
        for line in input_manifest:
            source = line.strip()
            if source:
                sources.append( source )
    if not sources:
        print( "CRITICAL ERROR: sources manifest is empty", file = sys.stderr )
        sys.exit( 1 )

    # Metazoan-group phylum species sets (for phylum-composition classification).
    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    phyla___species, metazoan_species = load_phylum_species_sets( config, workflow_root )

    # ---- gather per-source rows + per-source absent breakdowns --------------
    source_rows = []
    sources___genus_species_absent = {}
    sources___phylum_absent = {}

    for source in sources:
        map_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_map.tsv"
        membership_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_membership.tsv"
        if not map_path.is_file() or not membership_path.is_file():
            print( f"CRITICAL ERROR: annogroup outputs missing for source '{source}' ({map_path} / {membership_path})", file = sys.stderr )
            print( "  Script 002 (build_annogroups) must run for every source before this script.", file = sys.stderr )
            sys.exit( 1 )
        dropped_path = output_base / "2-output" / source / f"2_ai-{source}-dropped_orphan_sequences.tsv"
        report_path = output_base / "3-output" / source / f"3_ai-{source}-validation_report.txt"

        source_summary = summarize_source_map( map_path )
        absent_sequences = source_summary[ "absent_sequences" ]
        annotated_sequences = universe_total - absent_sequences
        annotated_percent = ( 100.0 * annotated_sequences / universe_total ) if universe_total else 0.0

        source_rows.append( {
            "source": source,
            "validation_status": read_validation_status( report_path ),
            "annotated": annotated_sequences,
            "annotated_percent": annotated_percent,
            "absent": absent_sequences,
            "feature": source_summary[ "feature" ],
            "combination": source_summary[ "combination" ],
            "architecture": source_summary[ "architecture" ],
            "absent_annogroup": source_summary[ "absent" ],
            "total": source_summary[ "total" ],
            "dropped": count_dropped_orphans( dropped_path ),
        } )

        absent_breakdown = build_absent_breakdown( membership_path )
        sources___genus_species_absent[ source ] = absent_breakdown[ "genus_species___absent_count" ]
        sources___phylum_absent[ source ] = absent_breakdown[ "phylum___absent_count" ]

    output_dir = output_base / "4-output"
    output_dir.mkdir( parents = True, exist_ok = True )

    # ========================================================================
    # Table 0: per-source metazoan phylum-composition counts
    # (trees_species metazoan-group partition; one file per source)
    # ========================================================================
    for source in sources:
        map_path = output_base / "2-output" / source / f"2_ai-{source}-annogroup_map.tsv"
        phylum_counts_path, phylum_total = write_source_phylum_composition_counts(
            map_path, source, phyla___species, metazoan_species, output_dir
        )
        print( f"[004] wrote phylum-composition counts for {source} ({phylum_total} annogroups) -> {phylum_counts_path}" )

    # ========================================================================
    # Table 1: per source (with the per-type annogroup breakdown)
    # ========================================================================
    output_summary_path = output_dir / "4_ai-annogroups_summary.tsv"
    summary_header = [
        "Source (annotation source database)",
        "Validation_Status (PASS or FAIL from the Script 003 per source validation report)",
        "Universe_Sequence_Count (total sequences in the species set proteome universe)",
        "Annotated_Sequence_Count (sequences with at least one feature from this source calculated as universe minus absent)",
        "Annotated_Percent (percentage of universe sequences with at least one feature from this source calculated as annotated divided by universe times 100)",
        "Absent_Sequence_Count (sequences in the universe with no feature from this source, i.e. members of annogroup_<source>_absent)",
        "Feature_Annogroup_Count (number of feature annogroups, equals distinct annotation accessions observed in at least one sequence)",
        "Combination_Annogroup_Count (number of combination annogroups, equals distinct alphabetical feature sets observed)",
        "Architecture_Annogroup_Count (number of architecture annogroups, equals distinct N to C ordered positional feature patterns observed)",
        "Absent_Annogroup_Count (number of absent annogroups, always 1 per source)",
        "Total_Annogroup_Count (sum of feature, combination, architecture, and absent annogroups for this source)",
        "Dropped_Orphan_Count (annotation identifiers dropped because not present in the proteome universe; see WARNING-truncated_orphan_annotations.md)",
    ]
    with open( output_summary_path, 'w' ) as output_summary:
        output_summary.write( '\t'.join( summary_header ) + '\n' )
        for row in source_rows:
            output = '\t'.join( [
                row[ "source" ], row[ "validation_status" ], str( universe_total ),
                str( row[ "annotated" ] ), f"{row[ 'annotated_percent' ]:.1f}", str( row[ "absent" ] ),
                str( row[ "feature" ] ), str( row[ "combination" ] ), str( row[ "architecture" ] ),
                str( row[ "absent_annogroup" ] ), str( row[ "total" ] ), str( row[ "dropped" ] ),
            ] ) + '\n'
            output_summary.write( output )

    # ========================================================================
    # Table 2: per species (annotation SOURCES are the columns)
    # ========================================================================
    # Each source column cell = the species' annotated sequence count for that
    # source (universe count for the species minus its absent count).
    output_per_species_path = output_dir / "4_ai-annogroups_summary-per_species.tsv"
    per_species_header = [
        "Phylum (Phylum field of the species phyloname)",
        "Genus_Species (Genus_species of the species)",
        "Universe_Sequence_Count (number of sequences this species contributes to the proteome universe)",
    ] + [ f"{source} (annotated sequence count: sequences of this species with at least one {source} feature)" for source in sources ]

    genus_species___phylum = universe[ "genus_species___phylum" ]
    genus_species___universe_count = universe[ "genus_species___universe_count" ]
    ordered_species = sorted( genus_species___universe_count, key = lambda gs: ( genus_species___phylum.get( gs, '' ), gs ) )

    with open( output_per_species_path, 'w' ) as output_per_species:
        output_per_species.write( '\t'.join( per_species_header ) + '\n' )
        for genus_species in ordered_species:
            phylum = genus_species___phylum.get( genus_species, '' )
            species_universe = genus_species___universe_count[ genus_species ]
            source_cells = []
            for source in sources:
                absent_for_species = sources___genus_species_absent[ source ].get( genus_species, 0 )
                annotated_for_species = species_universe - absent_for_species
                source_cells.append( str( annotated_for_species ) )
            output = '\t'.join( [ phylum, genus_species, str( species_universe ) ] + source_cells ) + '\n'
            output_per_species.write( output )

    # ========================================================================
    # Table 3: per phylum (annotation SOURCES are the columns)
    # ========================================================================
    output_per_phylum_path = output_dir / "4_ai-annogroups_summary-per_phylum.tsv"
    per_phylum_header = [
        "Phylum (Phylum field of the species phyloname)",
        "Species_Count (number of distinct species in this phylum)",
        "Universe_Sequence_Count (number of sequences this phylum contributes to the proteome universe)",
    ] + [ f"{source} (annotated sequence count: sequences in this phylum with at least one {source} feature)" for source in sources ]

    phylum___universe_count = universe[ "phylum___universe_count" ]
    phylum___species = universe[ "phylum___species" ]
    ordered_phyla = sorted( phylum___universe_count )

    with open( output_per_phylum_path, 'w' ) as output_per_phylum:
        output_per_phylum.write( '\t'.join( per_phylum_header ) + '\n' )
        for phylum in ordered_phyla:
            phylum_universe = phylum___universe_count[ phylum ]
            species_count = len( phylum___species[ phylum ] )
            source_cells = []
            for source in sources:
                absent_for_phylum = sources___phylum_absent[ source ].get( phylum, 0 )
                annotated_for_phylum = phylum_universe - absent_for_phylum
                source_cells.append( str( annotated_for_phylum ) )
            output = '\t'.join( [ phylum, str( species_count ), str( phylum_universe ) ] + source_cells ) + '\n'
            output_per_phylum.write( output )

    # ---- console summary ----------------------------------------------------
    print( f"[004] universe: {universe_total} sequences across {len( genus_species___universe_count )} species, {len( phylum___universe_count )} phyla" )
    print( f"[004] wrote per-source summary -> {output_summary_path}" )
    print( f"[004] wrote per-species matrix ({len( ordered_species )} species x {len( sources )} source(s)) -> {output_per_species_path}" )
    print( f"[004] wrote per-phylum matrix ({len( ordered_phyla )} phyla x {len( sources )} source(s)) -> {output_per_phylum_path}" )
    for row in source_rows:
        print( f"[004]   {row[ 'source' ]}: {row[ 'validation_status' ]} | "
               f"annotated={row[ 'annotated' ]} ({row[ 'annotated_percent' ]:.1f}%) absent={row[ 'absent' ]} | "
               f"feature={row[ 'feature' ]} combination={row[ 'combination' ]} "
               f"architecture={row[ 'architecture' ]} absent={row[ 'absent_annogroup' ]} total={row[ 'total' ]}" )


if __name__ == '__main__':
    main()
