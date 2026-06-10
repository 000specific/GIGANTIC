# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Write .section_metadata.tsv sidecars (with __DIR__ "what's inside" subtitle + per-file labels) into every leonid_requests june_4 output directory
# Human: Eric Edsinger
"""
The GIGANTIC server reads a .section_metadata.tsv sidecar in each directory.
Columns: filename  display_label  file_category  description  order
A reserved __DIR__ row's `description` becomes the short folder subtitle
( the 3-5 word "what's inside" line requested ).

This walks leonid_requests/upload_to_server/june_4/ and writes a sidecar into
every directory that contains output tables, keyed by the descriptive part of
each filename.
"""

import re
from pathlib import Path

june_4 = Path(
    "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC"
    "/gigantic_project-COPYME/subprojects/leonid_requests/upload_to_server/june_4"
)

HEADER = "# GIGANTIC server section metadata — auto-generated; do not edit\n" \
         "filename\tdisplay_label\tfile_category\tdescription\torder\n"

# Per-file metadata keyed by descriptive key ( filename with leading
# "N_ai-structure_NNN_" and trailing "-one_sequence_per_row.tsv" stripped ).
file_metadata = {
    "orthogroups-gigantic_identifiers": ( "Orthogroups — GIGANTIC identifiers (+ sequences)", "data",
        "Orthogroup membership; one row per sequence, each with its FASTA.", "10" ),
    "orthogroup_origins": ( "Orthogroups — origins (+ sequences)", "data",
        "Per-orthogroup origin block & path; one row per sequence, each with its FASTA.", "10" ),
    "conservation_patterns-per_orthogroup": ( "Orthogroups — conservation patterns (+ sequences)", "data",
        "Per-orthogroup conservation/loss pattern; one row per sequence, each with its FASTA.", "10" ),
    "orthogroups-complete_ocl_summary": ( "Orthogroups — complete OCL summary (+ sequences)", "summary",
        "Per-orthogroup OCL origin/conservation/loss summary; one row per sequence, each with its FASTA.", "10" ),
    "annogroup_map": ( "Annogroup map (+ sequences)", "data",
        "Annogroup→sequence map; one row per sequence, each with its FASTA.", "40" ),
    "annogroups-combo": ( "Annogroups — combo (+ sequences)", "data",
        "Combo annogroups; one row per sequence, each with its FASTA.", "20" ),
    "annogroups-single": ( "Annogroups — single (+ sequences)", "data",
        "Single annogroups; one row per sequence, each with its FASTA.", "10" ),
    "annogroups-zero": ( "Annogroups — zero (+ sequences)", "data",
        "Zero annogroups (header only).", "30" ),
}

# Short __DIR__ subtitle ( 3-5 words ) keyed by the descriptive key of the file(s) inside.
dir_label_by_key = {
    "orthogroups-gigantic_identifiers": "orthogroup identifiers + sequences",
    "orthogroup_origins": "orthogroup origins + sequences",
    "conservation_patterns-per_orthogroup": "conservation patterns + sequences",
    "orthogroups-complete_ocl_summary": "OCL summaries + sequences",
    "annogroup_map": "annogroup identifiers + sequences",
    "annogroups-combo": "annogroup identifiers + sequences",
    "annogroups-single": "annogroup identifiers + sequences",
    "annogroups-zero": "annogroup identifiers + sequences",
}


def descriptive_key( filename ):
    name = re.sub( r"^\d+_ai-structure_\d+_", "", filename )
    name = re.sub( r"-one_sequence_per_row\.tsv$", "", name )
    return re.sub( r"\.tsv$", "", name )


def species_display_from_secretome( filename ):
    """Genus species from a secretome phyloname filename."""
    base = filename.replace( "_secretome_002_moroz_strict-with_sequences.tsv", "" )
    parts = base.split( "_" )
    if len( parts ) >= 7:
        return parts[ 5 ] + " " + "_".join( parts[ 6: ] )
    return base


def write_sidecar( directory, file_rows, dir_label ):
    lines = [ HEADER ]
    for filename, ( label, category, description, order ) in file_rows:
        lines.append( f"{filename}\t{label}\t{category}\t{description}\t{order}\n" )
    if dir_label:
        lines.append( f"__DIR__\t\t\t{dir_label}\t0\n" )
    with open( directory / ".section_metadata.tsv", "w" ) as output_sidecar:
        output_sidecar.write( "".join( lines ) )


def main():
    written = 0

    # ---- OCL N-output directories ----
    for tsv_directory in sorted( ( june_4 / "ocl_phylogenetic_structures" ).rglob( "*-output" ) ):
        if not tsv_directory.is_dir():
            continue
        file_rows = []
        dir_label = ""
        for tsv in sorted( tsv_directory.glob( "*.tsv" ) ):
            key = descriptive_key( tsv.name )
            if key in file_metadata:
                file_rows.append( ( tsv.name, file_metadata[ key ] ) )
                dir_label = dir_label or dir_label_by_key.get( key, "" )
        if file_rows:
            write_sidecar( tsv_directory, file_rows, dir_label )
            written += 1

    # ---- secretome directory ----
    secretome_directory = june_4 / "secretome"
    if secretome_directory.is_dir():
        file_rows = []
        for tsv in sorted( secretome_directory.glob( "*_secretome_002_moroz_strict-with_sequences.tsv" ) ):
            display = species_display_from_secretome( tsv.name )
            file_rows.append( ( tsv.name, ( f"{display} — secretome (+ sequences)", "data",
                "Secreted-protein evidence; one row per protein, each with its FASTA.", "100" ) ) )
        if file_rows:
            write_sidecar( secretome_directory, file_rows, "secretome proteins + sequences" )
            written += 1

    print( f"Wrote {written} .section_metadata.tsv sidecars." )


if __name__ == "__main__":
    main()
