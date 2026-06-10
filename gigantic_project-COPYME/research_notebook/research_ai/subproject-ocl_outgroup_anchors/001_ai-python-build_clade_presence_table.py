# AI: Claude Code | Opus 4.8 | 2026 June 03 | Purpose: Build per-feature clade-level present/absent table (outgroup + 5 high-confidence metazoan clades) from orthogroups — the shared primitive for OCL outgroup-anchored loss analysis
# Human: Eric Edsinger
#
# For each orthogroup (feature) record how many species are present in each of:
#   Outgroup (non-Metazoa), Ctenophora, Porifera, Placozoa, Cnidaria, Bilateria.
# A group is "present" if its count > 0, "absent/lost" if 0. For an outgroup-present
# (ancestral) feature, a metazoan clade with 0 = a clade-level loss.
# Clade memberships are read from trees_species structure_001 (the 5 clades are
# high-confidence monophyletic, so their membership is the same across all 105 structures).

import sys
from pathlib import Path

PROJECT_ROOT = Path( __file__ ).resolve().parents[ 3 ]
SANDBOX_DIR = Path( __file__ ).resolve().parent

input_clade_mappings = PROJECT_ROOT / 'subprojects/trees_species/output_to_input/BLOCK_permutations_and_features/Species_Clade_Species_Mappings/9_ai-clade_species_mappings-all_structures.tsv'
# Most-recent orthogroup set (2026-05-01, 202,994 orthogroups) — the same set the OCL pipeline ran on.
# (Superseded the older BLOCK_orthohmm RUN_3 set: 2026-03-30, 170,027.)
input_orthogroups = PROJECT_ROOT / 'subprojects/orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv'
output_table = SANDBOX_DIR / '1_ai-clade_presence_table.tsv'
output_summary = SANDBOX_DIR / '1_ai-clade_presence_table-summary.txt'

target_structure = 'structure_001'
high_confidence_clades = [ 'Ctenophora', 'Porifera', 'Placozoa', 'Cnidaria', 'Bilateria' ]
group_order = [ 'Outgroup' ] + high_confidence_clades

# ----------------------------------------------------------------------------
# 1. Read clade -> species from structure_001
# Structure_ID	Clade_ID_Name	Phylogenetic_Block	Descendant_Species_Count	Descendant_Species_List	...
# structure_001	C086_Ctenophora	C082_Metazoa::C086_Ctenophora	5	Beroe_ovata,Bolinopsis_microptera,...	...
# ----------------------------------------------------------------------------
clade_names___species_sets = {}
all_species = set()
metazoa_species = set()

with open( input_clade_mappings ) as input_file:
    input_file.readline()  # header
    for line in input_file:
        line = line.rstrip( '\n' )
        parts = line.split( '\t' )
        if parts[ 0 ] != target_structure:
            continue
        clade_id_name = parts[ 1 ]
        species_list_field = parts[ 4 ] if len( parts ) > 4 else ''
        species = set( s for s in species_list_field.split( ',' ) if s )
        all_species |= species
        name_part = clade_id_name.split( '_', 1 )[ 1 ] if '_' in clade_id_name else clade_id_name
        if name_part == 'Metazoa':
            metazoa_species = species
        if name_part in high_confidence_clades:
            clade_names___species_sets[ name_part ] = species

clade_names___species_sets[ 'Outgroup' ] = all_species - metazoa_species

# map each species to exactly one group
species___groups = {}
for group in group_order:
    for sp in clade_names___species_sets.get( group, set() ):
        species___groups[ sp ] = group

group_sizes = { g: len( clade_names___species_sets.get( g, set() ) ) for g in group_order }

# fail-fast sanity checks
if sum( group_sizes[ g ] for g in high_confidence_clades ) != len( metazoa_species ):
    sys.exit( f"ERROR: 5 clades ({sum( group_sizes[g] for g in high_confidence_clades )}) do not sum to Metazoa ({len( metazoa_species )})" )
print( f"Species groups (structure_001): total={len( all_species )}  Metazoa={len( metazoa_species )}" )
for g in group_order:
    print( f"  {g:12s} {group_sizes[ g ]:3d}" )

# ----------------------------------------------------------------------------
# 2. Parse orthogroups -> per-group present counts
# OG000000	g_g23117-t_g23117.t3-p_g23117.t3-n_HolozoaUNOFFICIAL_..._Abeoforma_whisleri	g_...
# member id -> phyloname after '-n_' -> Genus_species = parts[5] + '_' + parts[6:]
# ----------------------------------------------------------------------------
unmatched_species = set()
species_seen = set()
orthogroup_count = 0

# clades-lost distribution among ancestral (outgroup-present) features
clades_lost_distribution = { n: 0 for n in range( 0, 6 ) }
ancestral_count = 0
informative_count = 0   # ancestral AND >=1 clade present AND >=2 clades lost

header_cols = [ 'Orthogroup_ID' ]
for g in group_order:
    header_cols.append( f"{g}_present (species count present out of {group_sizes[ g ]})" )
header_cols.append( f"Total_present (out of {len( all_species )})" )

with open( input_orthogroups ) as input_file, open( output_table, 'w' ) as output_file_table:
    output_file_table.write( '\t'.join( header_cols ) + '\n' )
    for line in input_file:
        line = line.rstrip( '\n' )
        parts = line.split( '\t' )
        orthogroup_id = parts[ 0 ]
        species_present = set()
        for member in parts[ 1: ]:
            phyloname = member.split( '-n_', 1 )[ -1 ]
            phylo_parts = phyloname.split( '_' )
            if len( phylo_parts ) < 7:
                continue
            genus_species = phylo_parts[ 5 ] + '_' + '_'.join( phylo_parts[ 6: ] )
            species_present.add( genus_species )

        group_counts = { g: 0 for g in group_order }
        for sp in species_present:
            species_seen.add( sp )
            group = species___groups.get( sp )
            if group is None:
                unmatched_species.add( sp )
            else:
                group_counts[ group ] += 1

        total_present = sum( group_counts.values() )
        output = orthogroup_id + '\t' + '\t'.join( str( group_counts[ g ] ) for g in group_order ) + '\t' + str( total_present ) + '\n'
        output_file_table.write( output )
        orthogroup_count += 1

        # summary accounting
        if group_counts[ 'Outgroup' ] > 0:
            ancestral_count += 1
            clades_present = sum( 1 for c in high_confidence_clades if group_counts[ c ] > 0 )
            clades_lost = 5 - clades_present
            clades_lost_distribution[ clades_lost ] += 1
            if clades_present >= 1 and clades_lost >= 2:
                informative_count += 1

# ----------------------------------------------------------------------------
# 3. Summary
# ----------------------------------------------------------------------------
summary_lines = []
summary_lines.append( f"Orthogroups processed: {orthogroup_count}" )
summary_lines.append( f"Species parsed and matched to a group: {len( species_seen - unmatched_species )} / {len( all_species )}" )
summary_lines.append( f"Unmatched parsed species (should be 0): {len( unmatched_species )}" )
if unmatched_species:
    summary_lines.append( "  examples: " + ', '.join( sorted( unmatched_species )[ :10 ] ) )
summary_lines.append( "" )
summary_lines.append( f"Ancestral features (present in >=1 outgroup species): {ancestral_count}" )
summary_lines.append( f"Informative loss features (ancestral, >=1 clade present, >=2 clades in loss): {informative_count}" )
summary_lines.append( "" )
summary_lines.append( "Among ancestral features, number of the 5 clades in loss state (count of clades with 0 species):" )
for n in range( 0, 6 ):
    summary_lines.append( f"  {n} clades lost: {clades_lost_distribution[ n ]}" )

summary_text = '\n'.join( summary_lines )
print( "\n" + summary_text )
with open( output_summary, 'w' ) as output_file_summary:
    output_file_summary.write( summary_text + '\n' )

print( f"\nWrote table   -> {output_table}" )
print( f"Wrote summary -> {output_summary}" )

# fail-fast on parsing problems
if len( unmatched_species ) > 0:
    sys.exit( f"\nERROR: {len( unmatched_species )} parsed species did not match any clade group — species parsing is likely off. Investigate before trusting the table." )
