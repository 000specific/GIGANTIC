# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Add sequences (one sequence per row) to all sequence-bearing upload_to_server tables of OCL + secretome; per-structure for structure-varying files, structure_001 only for files identical across all 105 structures
# Human: Eric Edsinger

import re
import sys
from pathlib import Path

input_proteomes_directory = Path(
    "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC"
    "/gigantic_project-COPYME/subprojects/genomesDB/output_to_input"
    "/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes"
)
input_ocl_upload_directory = Path(
    "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC"
    "/gigantic_project-COPYME/subprojects/ocl_phylogenetic_structures/upload_to_server"
)
input_secretome_upload_directory = Path(
    "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC"
    "/gigantic_project-COPYME/subprojects/secretome/upload_to_server"
)
output_base_directory = Path(
    "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC"
    "/gigantic_project-COPYME/subprojects/zoo/upload_to_server/BLOCK_leonid_requests/june_4"
)
missing_identifiers_report_path = Path(
    "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC"
    "/gigantic_project-COPYME/subprojects/zoo/BLOCK_leonid_requests/build/missing_identifiers_report.tsv"
)

# Block -> ( relative output key, workflow directory under upload_to_server ).
ocl_blocks = [
    ( "ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl",
      input_ocl_upload_directory / "BLOCK_orthogroups_X_ocl/workflow-RUN_1-ocl_analysis" ),
    ( "ocl_phylogenetic_structures/BLOCK_annotations_X_ocl",
      input_ocl_upload_directory / "BLOCK_annotations_X_ocl/workflow-RUN_01-ocl_analysis" ),
]

# Descriptive file keys ( filename with the leading "N_ai-structure_NNN_" and ".tsv" stripped )
# that are IDENTICAL across all 105 structures -> emit from structure_001 only.
keys_identical_across_structures = {
    "orthogroups-gigantic_identifiers",
    "annogroup_map", "annogroups-combo", "annogroups-single", "annogroups-zero",
}

MEMBER_LIST_COLUMN_MARKERS = [ "Sequence_IDs", "GIGANTIC_IDs" ]
GIGANTIC_ID_HEADER = ( "GIGANTIC_ID (single GIGANTIC identifier for this row's sequence; the table is "
    "one sequence per row, exploded from the original comma-delimited member list)" )
FASTA_HEADER_COLUMN = ( "Sequence_FASTA_Header (FASTA header line for this row's sequence, format >GIGANTIC_ID)" )
FASTA_SEQUENCE_COLUMN = ( "Sequence_Amino_Acid_Sequence (amino acid sequence for this row's sequence, sourced "
    "from genomesDB species70 T1 proteomes; [SEQUENCE_NOT_FOUND] if the identifier is absent from the proteomes)" )


def load_proteome_sequences( proteomes_directory ):
    identifiers___sequences = {}
    proteome_files = sorted( proteomes_directory.glob( "*.aa" ) )
    if not proteome_files:
        print( f"CRITICAL ERROR: no .aa proteomes in {proteomes_directory}" ); sys.exit( 1 )
    print( f"Loading sequences from {len( proteome_files )} proteome files ..." )
    for proteome_file in proteome_files:
        current_identifier = None; sequence_chunks = []
        with open( proteome_file ) as input_proteome:
            for line in input_proteome:
                line = line.rstrip( "\n" )
                if line.startswith( ">" ):
                    if current_identifier is not None:
                        identifiers___sequences[ current_identifier ] = "".join( sequence_chunks )
                    current_identifier = line[ 1: ].split()[ 0 ]; sequence_chunks = []
                else:
                    sequence_chunks.append( line )
            if current_identifier is not None:
                identifiers___sequences[ current_identifier ] = "".join( sequence_chunks )
    print( f"  loaded {len( identifiers___sequences )} sequences" )
    return identifiers___sequences


def build_fasta_columns( identifier, identifiers___sequences, missing_identifiers ):
    """Return ( header, sequence ) as two separate column values for one identifier.
    header = ">IDENTIFIER" ; sequence = single-line amino acids ( or [SEQUENCE_NOT_FOUND] )."""
    sequence = identifiers___sequences.get( identifier )
    if sequence is None:
        missing_identifiers.add( identifier )
        sequence = "[SEQUENCE_NOT_FOUND]"
    return ( f">{identifier}", sequence )


def split_member_identifiers( cell_value ):
    cell_value = cell_value.strip()
    return [ p.strip() for p in cell_value.split( "," ) if p.strip() != "" ] if cell_value else []


def find_member_list_column( header_parts ):
    for index, header_part in enumerate( header_parts ):
        if any( marker in header_part for marker in MEMBER_LIST_COLUMN_MARKERS ):
            return index
    return None


def descriptive_key( filename ):
    name = re.sub( r"^\d+_ai-structure_\d+_", "", filename )
    return re.sub( r"\.tsv$", "", name )


def process_explode( input_table_path, output_table_path, list_column_index,
                     identifiers___sequences, missing_identifiers ):
    output_table_path.parent.mkdir( parents=True, exist_ok=True )
    output_rows = 0
    with open( input_table_path ) as input_table, open( output_table_path, "w" ) as output_table:
        header_parts = input_table.readline().rstrip( "\n" ).split( "\t" )
        kept = [ h for i, h in enumerate( header_parts ) if i != list_column_index ]
        output_table.write( "\t".join( kept ) + "\t" + GIGANTIC_ID_HEADER + "\t" + FASTA_HEADER_COLUMN + "\t" + FASTA_SEQUENCE_COLUMN + "\n" )
        for line in input_table:
            line = line.rstrip( "\n" )
            if line == "": continue
            parts = line.split( "\t" )
            cell_value = parts[ list_column_index ] if list_column_index < len( parts ) else ""
            kept_prefix = "\t".join( [ p for i, p in enumerate( parts ) if i != list_column_index ] )
            for member_identifier in split_member_identifiers( cell_value ):
                fasta_header, fasta_sequence = build_fasta_columns( member_identifier, identifiers___sequences, missing_identifiers )
                output_table.write( kept_prefix + "\t" + member_identifier + "\t" + fasta_header + "\t" + fasta_sequence + "\n" )
                output_rows += 1
    return output_rows


def process_append( input_table_path, output_table_path, identifier_column_match,
                    identifiers___sequences, missing_identifiers ):
    output_table_path.parent.mkdir( parents=True, exist_ok=True )
    rows = 0
    with open( input_table_path ) as input_table, open( output_table_path, "w" ) as output_table:
        header_parts = input_table.readline().rstrip( "\n" ).split( "\t" )
        idx = next( ( i for i, h in enumerate( header_parts ) if identifier_column_match in h ), None )
        if idx is None:
            print( f"CRITICAL ERROR: no '{identifier_column_match}' in {input_table_path}" ); sys.exit( 1 )
        output_table.write( "\t".join( header_parts ) + "\t" + FASTA_HEADER_COLUMN + "\t" + FASTA_SEQUENCE_COLUMN + "\n" )
        for line in input_table:
            line = line.rstrip( "\n" )
            if line == "": continue
            parts = line.split( "\t" )
            identifier = parts[ idx ].strip() if idx < len( parts ) else ""
            fasta_header, fasta_sequence = build_fasta_columns( identifier, identifiers___sequences, missing_identifiers )
            output_table.write( "\t".join( parts ) + "\t" + fasta_header + "\t" + fasta_sequence + "\n" )
            rows += 1
    return rows


def main():
    identifiers___sequences = load_proteome_sequences( input_proteomes_directory )
    missing_identifiers = set()

    for relative_key, workflow_directory in ocl_blocks:
        structure_directories = sorted( workflow_directory.glob( "structure_*" ) )
        print( f"\n{relative_key.split('/')[-1]}: {len( structure_directories )} structures" )
        for structure_directory in structure_directories:
            structure_name = structure_directory.name  # structure_NNN
            for input_table_path in sorted( structure_directory.rglob( "*.tsv" ) ):
                if input_table_path.name.startswith( "." ):
                    continue
                key = descriptive_key( input_table_path.name )
                # Files identical across structures: only emit from structure_001.
                if key in keys_identical_across_structures and structure_name != "structure_001":
                    continue
                with open( input_table_path ) as fh:
                    header_parts = fh.readline().rstrip( "\n" ).split( "\t" )
                list_column_index = find_member_list_column( header_parts )
                if list_column_index is None:
                    continue
                relative_within = input_table_path.relative_to( structure_directory )
                output_table_path = (
                    output_base_directory / relative_key / structure_name / relative_within.parent
                    / input_table_path.name.replace( ".tsv", "-one_sequence_per_row.tsv" )
                )
                n = process_explode( input_table_path, output_table_path, list_column_index,
                                     identifiers___sequences, missing_identifiers )
                print( f"  {structure_name}/{key}: {n} rows" )

    print( "\nsecretome ..." )
    for secretome_input in sorted( input_secretome_upload_directory.glob( "*_secretome_002_moroz_strict.tsv" ) ):
        process_append(
            secretome_input,
            output_base_directory / "secretome" / secretome_input.name.replace( ".tsv", "-with_sequences.tsv" ),
            "Protein_Identifier", identifiers___sequences, missing_identifiers )
    print( "  secretome done" )

    print( "\n" + "=" * 60 )
    if missing_identifiers:
        print( f"{len( missing_identifiers )} ids not found ( marked [SEQUENCE_NOT_FOUND] ); -> {missing_identifiers_report_path}" )
        missing_identifiers_report_path.parent.mkdir( parents=True, exist_ok=True )
        with open( missing_identifiers_report_path, "w" ) as output_report:
            output_report.write( "Missing_Identifier (absent from species70 T1 proteomes; known cause: upstream 255-char truncation of EvidentialGene multi-locus IDs)\n" )
            for missing_identifier in sorted( missing_identifiers ):
                output_report.write( missing_identifier + "\n" )
    else:
        print( "All identifiers found." )
    print( "=" * 60 + "\nDone." )


if __name__ == "__main__":
    main()
