#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 14 | Purpose: Generate Leonid's 4 innovations tables + 3 pairwise-shared tables from structure_001 OCL summary
# Human: Eric Edsinger
"""
Exploratory script — lives in research_notebook/ai_research/planning-leonid/ and is
NOT part of the STEP_1 / BLOCK_ocl_analysis pipeline. Not for GitHub as a canonical
pipeline artifact; stays in this subproject's research notebook until/unless
generalized into the planned `gigantic_data_diver` subproject.

Answers Leonid's specific questions from his April 11 email:

    Specifically, for 4 nodes as we discussed
    1) Metazoan innovations
    2) Ctenophora innovations
    3) Placozoa innovations
    4) Cnidaria innovations

    In addition, I particularly interested in genes/orthogroups/gene families
    among metazoans innovation (#1 above) that are uniquely shared between
    Ctenophora and Placozoa, but not others; Placozoa and Bilateria, but not
    others; Ctenophora and Bilateria, but not others.

Outputs:
    4 innovations tables — origin at each of {Metazoa, Ctenophora, Placozoa, Cnidaria}
    3 pairwise-shared tables — Metazoa-origin orthogroups present exclusively in
      exactly two of the 5 major metazoan clades (Cteno+Plac, Plac+Bilateria,
      Cteno+Bilateria), absent in the other three.

Inputs:
    - OCL structure_001 complete summary:
      {run}/OUTPUT_pipeline/structure_001/4-output/4_ai-orthogroups-complete_ocl_summary.tsv
    - Clade-species mappings (from trees_species):
      trees_species/output_to_input/BLOCK_permutations_and_features/
          Species_Clade_Species_Mappings/9_ai-clade_species_mappings-all_structures.tsv

Run:
    python3 generate_leonid_tables.py
"""

import csv
from pathlib import Path
from datetime import datetime
import sys

# Raise CSV field size limit — some rows in the OCL summary have Species_List /
# Sequence_IDs columns containing thousands of entries, exceeding the default
# 131072-char field cap.
csv.field_size_limit( sys.maxsize )

# ============================================================================
# CONFIG — paths are relative to this script's location for portability
# ============================================================================

SCRIPT_DIR = Path( __file__ ).resolve().parent
# planning-leonid -> ai_research -> research_notebook -> orthogroups_X_ocl
SUBPROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
SUBPROJECTS_DIR = SUBPROJECT_ROOT.parent  # subprojects/

input_ocl_summary = SUBPROJECT_ROOT / 'BLOCK_ocl_analysis' / 'workflow-RUN_01-ocl_analysis' / 'OUTPUT_pipeline' / 'structure_001' / '4-output' / '4_ai-orthogroups-complete_ocl_summary.tsv'
input_clade_species_mappings = SUBPROJECTS_DIR / 'trees_species' / 'output_to_input' / 'BLOCK_permutations_and_features' / 'Species_Clade_Species_Mappings' / '9_ai-clade_species_mappings-all_structures.tsv'

output_dir = SCRIPT_DIR / 'OUTPUT_tables_for_leonid'
output_dir.mkdir( exist_ok = True )

# Major metazoan clades Leonid asked about
MAJOR_CLADES = [ 'Metazoa', 'Ctenophora', 'Placozoa', 'Cnidaria', 'Bilateria', 'Porifera' ]
INNOVATIONS_CLADES = [ 'Metazoa', 'Ctenophora', 'Placozoa', 'Cnidaria' ]
PAIRWISE_EXCLUSIVE_PAIRS = [
    ( 'Ctenophora', 'Placozoa' ),
    ( 'Placozoa', 'Bilateria' ),
    ( 'Ctenophora', 'Bilateria' ),
]

# ============================================================================
# LOAD SPECIES -> MAJOR_CLADE MAP from trees_species clade-species mappings
# ============================================================================

def load_species_to_major_clade_map( mappings_path ):
    """
    Build {genus_species: major_clade_name} for each species present in the
    species70 set, using the clade-species mappings for structure_001.

    The mappings TSV has rows {Structure_ID, Clade_ID, Clade_Name, ..., Descendant_Species_List}
    where Descendant_Species_List is comma-delimited. We look up rows for each
    major clade and every descendant species is tagged with that clade.

    Species may appear under multiple clades in the mapping (e.g., a human
    descends from Metazoa, Bilateria, and more specific clades). We resolve
    by assigning each species to its MOST SPECIFIC major clade from the
    {Cteno, Plac, Cnid, Bilateria, Porifera} set. Metazoa is a superset of
    the other four — species are never tagged as "Metazoa" if they're also
    in one of those, which is the normal case for species70.
    """
    # First pass: find Clade_Name column + Descendant_Species_List column by header
    species_names___major_clades = {}

    with open( mappings_path, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )
        header = next( csv_reader )

        # Find relevant column indices
        structure_id_col = None
        clade_name_col = None
        species_list_col = None
        for index, header_cell in enumerate( header ):
            short_name = header_cell.split( ' (' )[ 0 ].strip()
            if short_name == 'Structure_ID':
                structure_id_col = index
            elif short_name == 'Clade_Name':
                clade_name_col = index
            elif short_name in ( 'Descendant_Species_List', 'Species_List', 'Descendant_Species' ):
                species_list_col = index

        if None in ( structure_id_col, clade_name_col, species_list_col ):
            raise ValueError(
                f"Could not find required columns in {mappings_path}. "
                f"Found headers: {header}"
            )

        # Check the 4 subclades first so species are tagged with most-specific membership.
        # If a species is in Cnidaria, it's also in Metazoa — we want the Cnidaria tag.
        priority_order = [ 'Ctenophora', 'Placozoa', 'Cnidaria', 'Bilateria', 'Porifera', 'Metazoa' ]

        # Read all rows for structure_001, bucket by clade name
        clade_names___species_sets = {}
        for row in csv_reader:
            if len( row ) <= max( structure_id_col, clade_name_col, species_list_col ):
                continue
            if row[ structure_id_col ] != 'structure_001':
                continue
            clade_name = row[ clade_name_col ]
            species_list_string = row[ species_list_col ]
            if not species_list_string or species_list_string == 'NA':
                continue
            species_names = [ s.strip() for s in species_list_string.split( ',' ) if s.strip() ]
            clade_names___species_sets.setdefault( clade_name, set() ).update( species_names )

        # Apply priority — most-specific tag wins
        for priority_clade_name in priority_order:
            species_set = clade_names___species_sets.get( priority_clade_name, set() )
            for species_name in species_set:
                if species_name not in species_names___major_clades:
                    species_names___major_clades[ species_name ] = priority_clade_name

    return species_names___major_clades


# ============================================================================
# MAIN
# ============================================================================

def main():
    print( "=" * 80 )
    print( "Leonid's Tables Generator" )
    print( "=" * 80 )
    print( f"Started: {datetime.now().isoformat(timespec='seconds')}" )
    print()

    # Validate inputs
    if not input_ocl_summary.exists():
        print( f"CRITICAL ERROR: OCL summary not found: {input_ocl_summary}" )
        print( f"Run BLOCK_ocl_analysis (structure_001) first." )
        sys.exit( 1 )
    if not input_clade_species_mappings.exists():
        print( f"CRITICAL ERROR: Clade-species mappings not found: {input_clade_species_mappings}" )
        sys.exit( 1 )

    print( f"OCL summary:              {input_ocl_summary}" )
    print( f"Clade-species mappings:   {input_clade_species_mappings}" )
    print()

    # Load species -> major clade map
    print( "Loading species -> major-clade map..." )
    species_names___major_clades = load_species_to_major_clade_map( input_clade_species_mappings )
    print( f"  Mapped {len( species_names___major_clades )} species to major clades." )
    print()

    # Sanity report: species count per major clade
    clade_species_counts = {}
    for species_name, clade_name in species_names___major_clades.items():
        clade_species_counts[ clade_name ] = clade_species_counts.get( clade_name, 0 ) + 1
    for clade_name in MAJOR_CLADES:
        print( f"  {clade_name:12s}: {clade_species_counts.get( clade_name, 0 )} species" )
    print()

    # Read the OCL summary once, stream rows
    print( "Processing OCL summary..." )
    with open( input_ocl_summary, 'r', newline = '', encoding = 'utf-8' ) as input_file:
        csv_reader = csv.reader( input_file, delimiter = '\t' )
        header = next( csv_reader )

        # Find columns
        orthogroup_id_col = None
        origin_clade_col = None
        species_list_col = None
        species_count_col = None
        for index, header_cell in enumerate( header ):
            short_name = header_cell.split( ' (' )[ 0 ].strip()
            if short_name == 'Orthogroup_ID':
                orthogroup_id_col = index
            elif short_name == 'Origin_Clade':
                origin_clade_col = index
            elif short_name == 'Species_List':
                species_list_col = index
            elif short_name == 'Species_Count':
                species_count_col = index

        if None in ( orthogroup_id_col, origin_clade_col, species_list_col, species_count_col ):
            raise ValueError( f"Required columns missing in OCL summary. Headers: {header}" )

        rows = list( csv_reader )

    print( f"  Loaded {len( rows )} orthogroup rows." )
    print()

    # --- 4 INNOVATIONS TABLES: filter by Origin_Clade ---
    print( "Generating 4 innovations tables..." )
    for clade_name in INNOVATIONS_CLADES:
        output_path = output_dir / f'innovations-origin_{clade_name}.tsv'
        matched_count = 0
        with open( output_path, 'w', newline = '' ) as output_file:
            csv_writer = csv.writer( output_file, delimiter = '\t' )
            csv_writer.writerow( header )
            for row in rows:
                if row[ origin_clade_col ] == clade_name:
                    csv_writer.writerow( row )
                    matched_count += 1
        print( f"  {output_path.name}: {matched_count} orthogroups" )
    print()

    # --- 3 PAIRWISE-EXCLUSIVE TABLES (within Metazoa-origin set) ---
    print( "Generating 3 pairwise-exclusive tables (within Metazoan innovations)..." )
    for clade_a, clade_b in PAIRWISE_EXCLUSIVE_PAIRS:
        output_path = output_dir / f'metazoan_innovations-shared_exclusively-{clade_a}_AND_{clade_b}.tsv'
        matched_count = 0
        with open( output_path, 'w', newline = '' ) as output_file:
            csv_writer = csv.writer( output_file, delimiter = '\t' )
            csv_writer.writerow( header )
            for row in rows:
                if row[ origin_clade_col ] != 'Metazoa':
                    continue
                species_list = [ s.strip() for s in row[ species_list_col ].split( ',' ) if s.strip() ]
                present_clades = set()
                for species_name in species_list:
                    major_clade = species_names___major_clades.get( species_name )
                    if major_clade:
                        present_clades.add( major_clade )
                # Keep only rows where present_clades is exactly {clade_a, clade_b}
                # AND no other major clade has any representative
                # (exclude Metazoa as it is the parent of all 5 subclades)
                present_clades_excluding_metazoa = present_clades - { 'Metazoa' }
                if present_clades_excluding_metazoa == { clade_a, clade_b }:
                    csv_writer.writerow( row )
                    matched_count += 1
        print( f"  {output_path.name}: {matched_count} orthogroups" )
    print()

    # --- README ---
    readme_path = output_dir / 'README.md'
    readme_content = f"""# OCL Tables for Leonid — Data Dive 1

**Generated:** {datetime.now().isoformat(timespec='seconds')}
**Source:** structure_001 complete OCL summary (user's input species tree)
**Species set:** species70
**Orthogroup source:** OrthoHMM

## Files

### 4 innovations tables (origin at each clade)

| File | Description |
|------|-------------|
| `innovations-origin_Metazoa.tsv` | Orthogroups with MRCA origin inferred at Metazoa |
| `innovations-origin_Ctenophora.tsv` | Orthogroups with origin at Ctenophora (Cteno-specific innovations) |
| `innovations-origin_Placozoa.tsv` | Orthogroups with origin at Placozoa |
| `innovations-origin_Cnidaria.tsv` | Orthogroups with origin at Cnidaria |

### 3 pairwise-exclusive tables (Metazoan-origin orthogroups shared in exactly two clades)

| File | Description |
|------|-------------|
| `metazoan_innovations-shared_exclusively-Ctenophora_AND_Placozoa.tsv` | Metazoa-origin; present in ≥1 Cteno + ≥1 Plac species; absent in Cnidaria + Bilateria + Porifera |
| `metazoan_innovations-shared_exclusively-Placozoa_AND_Bilateria.tsv` | Metazoa-origin; present in ≥1 Plac + ≥1 Bilateria species; absent in Cteno + Cnidaria + Porifera |
| `metazoan_innovations-shared_exclusively-Ctenophora_AND_Bilateria.tsv` | Metazoa-origin; present in ≥1 Cteno + ≥1 Bilateria species; absent in Plac + Cnidaria + Porifera |

## Column schema

All tables share the same columns as the source OCL summary. Key columns:
- `Orthogroup_ID` — orthogroup identifier (OG000000 style)
- `Origin_Clade` — MRCA clade where orthogroup first appears
- `Species_Count` — unique species containing this orthogroup
- `Species_List` — comma-delimited species names (genus_species)
- `Conservation_Rate_Percent` / `Loss_At_Origin_Rate_Percent` / etc. — see source summary header

## Caveats

1. "Exclusive" means no species from excluded clades has the orthogroup in this dataset
   (species70). A species-poor clade is more likely to show false exclusivity.
2. Single-species orthogroups (present in only one species) are included in innovations
   tables where the origin clade happens to match that single species' ancestry.
3. This is structure_001 only — the user's input species tree. Alternative topologies
   (104 others) are not evaluated here; cross-topology comparison is future work
   (planned `occams_tree` subproject).

## Regeneration

```bash
python3 generate_leonid_tables.py
```
"""
    readme_path.write_text( readme_content )
    print( f"Wrote: {readme_path.name}" )
    print()
    print( "=" * 80 )
    print( f"DONE — outputs in: {output_dir}" )
    print( "=" * 80 )

if __name__ == '__main__':
    main()
