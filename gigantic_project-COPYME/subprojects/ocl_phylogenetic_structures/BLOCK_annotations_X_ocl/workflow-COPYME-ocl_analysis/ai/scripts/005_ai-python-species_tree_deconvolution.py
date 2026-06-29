# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Species-tree deconvolution for one structure — per annogroup, member SPECIES and member PROTEIN counts within every clade of the structure
# Human: Eric Edsinger

"""
OCL Script 005 — Species-tree deconvolution (one structure).

The annogroups analog, adapted to OCL's per-structure fan-out. For TARGET_STRUCTURE,
per annogroup, two parallel overlays on the species tree:
  - member-SPECIES count within each clade (node or tip), computed here from the
    annogroup's Species_List intersected with each clade's descendant species
  - member-PROTEIN count within each clade, READ from the annogroups subproject's
    already-computed per-structure tree-counts (annogroups owns the membership;
    OCL imports only the map, so the protein counts come from output_to_input)

Both tables use the SAME clade columns (the structure's clades, root -> tips, taken
from the annogroups per-structure tree-counts header). The 'absent' annogroup type
is excluded (consistent with OCL, which is an origin engine and skips 'absent').

Inputs:
  - annogroups per-structure protein tree-counts (from output_to_input):
      <annogroups_dir>/<species_set>/<source>/annogroup_tree_counts_per_structure/
        4_ai-<source>-annogroup_tree_counts-<structure>.tsv
    (carries the annogroup map columns incl Species_List + one clade column per clade)
  - clade->species mapping (trees_species, this structure): inputs.clade_species_mappings

Outputs (structure_<NNN>/5-output/):
  - 5_ai-<structure>_annogroup_tree_counts-species.tsv   (member-species counts per clade)
  - 5_ai-<structure>_annogroup_tree_counts-proteins.tsv  (member-protein counts per clade)

Fail-fast (§36): exits 1 if inputs are missing or a full-coverage clade's species
count != the annogroup's Species_Count.
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_run_summary as U


def load_structure_clade_species( mappings_path, target_structure ):
    """clade_id_name -> set(Genus_species) for this structure (tips -> the one species)."""
    clades___species = {}
    with open( mappings_path, 'r' ) as input_mappings:
        header_ids___indices = U.build_header_index( input_mappings.readline() )
        index_structure = header_ids___indices[ "Structure_ID" ]
        index_clade = header_ids___indices[ "Clade_ID_Name" ]
        index_descendant_count = header_ids___indices[ "Descendant_Species_Count" ]
        index_species_list = header_ids___indices[ "Descendant_Species_List" ]
        for line in input_mappings:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_structure ] != target_structure:
                continue
            clade_id_name = parts[ index_clade ]
            descendant_count = int( parts[ index_descendant_count ] ) if parts[ index_descendant_count ] else 0
            species_cell = parts[ index_species_list ] if index_species_list < len( parts ) else ''
            species = { s for s in species_cell.split( ',' ) if s }
            if not species and descendant_count == 0:
                # tip clade: derive the species from the clade_id_name (CNNN_Genus_species)
                species = { clade_id_name.split( '_', 1 )[ 1 ] } if '_' in clade_id_name else { clade_id_name }
            clades___species[ clade_id_name ] = species
    return clades___species


def main():
    parser = argparse.ArgumentParser( description = "OCL species-tree deconvolution (one source, one structure)" )
    parser.add_argument( '--structure_id', required = True )
    parser.add_argument( '--source', required = True, help = 'Annotation source (e.g. pfam, go, panther)' )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    target_structure = f"structure_{args.structure_id}"
    config_path = Path( args.config )
    with open( config_path, 'r' ) as input_config:
        config = yaml.safe_load( input_config )
    config_directory = config_path.parent

    species_set = config[ 'species_set_name' ]
    source = args.source
    annogroup_types = set( config.get( 'annogroup_types', [ 'feature', 'combination', 'architecture' ] ) )

    annogroups_directory = config_directory / config[ 'inputs' ][ 'annogroups_dir' ] / species_set / source
    protein_file = ( annogroups_directory / 'annogroup_tree_counts_per_structure'
                     / f'4_ai-{source}-annogroup_tree_counts-{target_structure}.tsv' )
    mappings_path = config_directory / config[ 'inputs' ][ 'clade_species_mappings' ]
    for required in ( protein_file, mappings_path ):
        if not required.exists():
            print( f"CRITICAL ERROR: required input not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    clades___species = load_structure_clade_species( mappings_path, target_structure )
    if not clades___species:
        print( f"CRITICAL ERROR: no clades found for {target_structure} in {mappings_path}", file = sys.stderr )
        sys.exit( 1 )
    # full-coverage clades (their species set == all tip species) -> roots
    all_tip_species = set().union( *clades___species.values() )

    # ---- read the annogroups per-structure protein tree-counts -----------------------
    # header carries the annogroup map columns + one column per clade (clade_id_name header).
    with open( protein_file, 'r' ) as input_protein:
        header_line = input_protein.readline().rstrip( '\n' )
        header_ids = [ column.split( ' (' )[ 0 ].strip() for column in header_line.split( '\t' ) ]
        header_ids___indices = { header_id: index for index, header_id in enumerate( header_ids ) }
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        index_species_list = header_ids___indices[ "Species_List" ]
        index_species_count = header_ids___indices[ "Species_Count" ]
        # clade columns, IN FILE ORDER (root -> tips), are the headers that name a clade
        clade_columns = [ ( index, header_id ) for index, header_id in enumerate( header_ids )
                          if header_id in clades___species ]
        full_coverage_clades = { header_id for ( index, header_id ) in clade_columns
                                 if clades___species[ header_id ] == all_tip_species }

        rows = []   # ( annogroup_id, type, definitions, species_counts[], protein_counts[] )
        for line in input_protein:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_type ] not in annogroup_types:
                continue
            annogroup_id = parts[ index_annogroup ]
            annogroup_type = parts[ index_type ]
            definitions = parts[ index_definitions ] if index_definitions < len( parts ) else ''
            species_count_declared = int( parts[ index_species_count ] ) if parts[ index_species_count ] else 0
            member_species = { s for s in ( parts[ index_species_list ] if index_species_list < len( parts ) else '' ).split( ',' ) if s }

            species_counts = []
            protein_counts = []
            for ( index, clade_id_name ) in clade_columns:
                species_counts.append( len( member_species & clades___species[ clade_id_name ] ) )
                protein_counts.append( parts[ index ] if index < len( parts ) else '0' )
                # research-integrity: a full-coverage (root) clade must hold every member species
                if clade_id_name in full_coverage_clades and species_counts[ -1 ] != species_count_declared:
                    print( f"CRITICAL ERROR: {annogroup_id} species count at full-coverage clade {clade_id_name} "
                           f"({species_counts[ -1 ]}) != Species_Count {species_count_declared}", file = sys.stderr )
                    sys.exit( 1 )
            rows.append( ( annogroup_id, annogroup_type, definitions, species_counts, protein_counts ) )

    if not rows:
        print( f"CRITICAL ERROR: no annogroups read from {protein_file.name}", file = sys.stderr )
        sys.exit( 1 )

    # ---- write the two tables --------------------------------------------------------
    output_directory = Path( args.output_dir ) / target_structure / '5-output'
    output_directory.mkdir( parents = True, exist_ok = True )

    def clade_header( clade_id_name, unit ):
        return f"{clade_id_name} (member-{unit} count of this annogroup within clade {clade_id_name})"

    fixed_header = [
        "Annogroup_ID (canonical annogroup identifier)",
        "Annogroup_Type (feature or combination or architecture)",
        "Annotation_Definitions (semicolon delimited definition ==accession pairs)",
    ]
    species_path = output_directory / f"5_ai-{target_structure}_annogroup_tree_counts-species.tsv"
    protein_path = output_directory / f"5_ai-{target_structure}_annogroup_tree_counts-proteins.tsv"

    with open( species_path, 'w' ) as output_species, open( protein_path, 'w' ) as output_protein:
        output_species.write( '\t'.join( fixed_header + [ clade_header( clade_id_name, "species" ) for ( index, clade_id_name ) in clade_columns ] ) + '\n' )
        output_protein.write( '\t'.join( fixed_header + [ clade_header( clade_id_name, "protein" ) for ( index, clade_id_name ) in clade_columns ] ) + '\n' )
        for ( annogroup_id, annogroup_type, definitions, species_counts, protein_counts ) in rows:
            prefix = [ annogroup_id, annogroup_type, definitions ]
            output_species.write( '\t'.join( prefix + [ str( count ) for count in species_counts ] ) + '\n' )
            output_protein.write( '\t'.join( prefix + [ str( count ) for count in protein_counts ] ) + '\n' )

    print( f"[005 {target_structure}] {len( rows )} annogroups x {len( clade_columns )} clades -> "
           f"species + protein tree-counts ({len( full_coverage_clades )} full-coverage clade(s))" )


if __name__ == '__main__':
    main()
