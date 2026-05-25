# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: One-shot helper to build RUN_2 (short proteins) + RUN_3 (long proteins) inputs for TMBed rerun
# Human: Eric Edsinger
"""
One-shot helper for the TMBed rerun:
  - takes the 65 species from RUN_1 manifest that have not yet produced a .3line output
  - applies the two filters required for safe TMBed execution:
       (a) drop FASTA records whose header line (incl. '>') exceeds the
           filename-safe max ( 239 chars, same as RUN_1 preprocess step )
       (b) length split: short ( seq <= max_length aa ) vs long ( seq > max_length aa )
  - writes the resulting per-species FASTAs into staging dirs under the two
    new workflow-RUN dirs:
       workflow-RUN_2-run_tmbed_short/INPUT_user/filtered_proteomes_short/
       workflow-RUN_3-run_tmbed_long/INPUT_user/filtered_proteomes_long/
  - writes two manifests ( one per RUN ), each with absolute paths

Run from BLOCK_tmbed/.
"""

import sys
from pathlib import Path


BLOCK_DIR = Path( __file__ ).resolve().parent
RUN_1_DIR = BLOCK_DIR / 'workflow-RUN_1-run_tmbed'
RUN_2_DIR = BLOCK_DIR / 'workflow-RUN_2-run_tmbed_short'
RUN_3_DIR = BLOCK_DIR / 'workflow-RUN_3-run_tmbed_long'

MAX_HEADER_LENGTH = 239
MAX_SEQUENCE_LENGTH = 4000   # short: seq <= 4000 ; long: seq > 4000


def read_fasta( path ):
    """
    Yield ( header_line_without_leading_gt, sequence_string ) for each record.
    """
    header = None
    parts_sequence = []
    with open( path ) as f:
        for line in f:
            line = line.rstrip( '\n' )
            if not line:
                continue
            if line.startswith( '>' ):
                if header is not None:
                    yield header, ''.join( parts_sequence )
                header = line[ 1: ]
                parts_sequence = []
            else:
                parts_sequence.append( line )
        if header is not None:
            yield header, ''.join( parts_sequence )


def write_fasta_record( fh, header, sequence ):
    fh.write( '>' + header + '\n' )
    # 60-char line wrap is conventional; many tools accept any wrap or unwrapped
    for i in range( 0, len( sequence ), 60 ):
        fh.write( sequence[ i : i + 60 ] + '\n' )


def main():
    # ----------------------------------------------------------------
    # Read RUN_1 manifest + completed-species list to derive the 65 todo set
    # ----------------------------------------------------------------
    input_manifest = RUN_1_DIR / 'INPUT_user' / 'proteome_manifest.tsv'
    output_dir_done = RUN_1_DIR / 'OUTPUT_pipeline' / '2-output'

    done_phylos = {
        p.name.replace( '_tmbed_predictions.3line', '' )
        for p in output_dir_done.glob( '*_tmbed_predictions.3line' )
    }
    print( f'Completed in RUN_1: {len(done_phylos)} species' )

    # species_name  proteome_path  phyloname
    # parts[0]      parts[1]       parts[2]
    species_names = []
    species_names___proteome_paths = {}
    species_names___phylonames = {}

    with open( input_manifest ) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith( '#' ) or line.startswith( 'species_name' ):
                continue
            parts = line.split( '\t' )
            species_name = parts[ 0 ]
            proteome_path = parts[ 1 ]
            phyloname = parts[ 2 ]
            if phyloname in done_phylos:
                continue
            species_names.append( species_name )
            species_names___proteome_paths[ species_name ] = proteome_path
            species_names___phylonames[ species_name ] = phyloname

    print( f'Species needing rerun: {len(species_names)}' )

    # ----------------------------------------------------------------
    # Prepare staging dirs + manifests
    # ----------------------------------------------------------------
    short_staging_dir = RUN_2_DIR / 'INPUT_user' / 'filtered_proteomes_short'
    long_staging_dir = RUN_3_DIR / 'INPUT_user' / 'filtered_proteomes_long'
    short_staging_dir.mkdir( parents=True, exist_ok=True )
    long_staging_dir.mkdir( parents=True, exist_ok=True )

    short_manifest_path = RUN_2_DIR / 'INPUT_user' / 'proteome_manifest.tsv'
    long_manifest_path = RUN_3_DIR / 'INPUT_user' / 'proteome_manifest.tsv'
    output_short_manifest = open( short_manifest_path, 'w' )
    output_long_manifest = open( long_manifest_path, 'w' )
    output_short_manifest.write( 'species_name\tproteome_path\tphyloname\n' )
    output_long_manifest.write( 'species_name\tproteome_path\tphyloname\n' )

    # ----------------------------------------------------------------
    # Per-species: filter long headers, length-split, write FASTAs
    # ----------------------------------------------------------------
    total_short_records = 0
    total_long_records = 0
    total_dropped_long_header = 0
    species_with_no_long = 0
    species_with_no_short = 0

    print( '' )
    print( f'{"species":<70s} {"short":>7s} {"long":>5s} {"hdr_drop":>9s}' )

    for species_name in species_names:
        phyloname = species_names___phylonames[ species_name ]
        proteome_path = species_names___proteome_paths[ species_name ]

        short_records = []
        long_records = []
        dropped_long_header = 0

        for header, sequence in read_fasta( proteome_path ):
            # Filter (a): drop overlong headers ( '>' + header line )
            if len( header ) + 1 > MAX_HEADER_LENGTH:
                dropped_long_header += 1
                continue
            # Filter (b): split by length
            if len( sequence ) <= MAX_SEQUENCE_LENGTH:
                short_records.append( ( header, sequence ) )
            else:
                long_records.append( ( header, sequence ) )

        # Write short FASTA
        short_path = short_staging_dir / f'{phyloname}-T1-proteome-filtered_short.aa'
        with open( short_path, 'w' ) as fh:
            for header, sequence in short_records:
                write_fasta_record( fh, header, sequence )

        # Write long FASTA
        long_path = long_staging_dir / f'{phyloname}-T1-proteome-filtered_long.aa'
        with open( long_path, 'w' ) as fh:
            for header, sequence in long_records:
                write_fasta_record( fh, header, sequence )

        # Manifest entries — only include species that actually have records
        if short_records:
            output = species_name + '\t' + str( short_path ) + '\t' + phyloname + '\n'
            output_short_manifest.write( output )
        else:
            species_with_no_short += 1

        if long_records:
            output = species_name + '\t' + str( long_path ) + '\t' + phyloname + '\n'
            output_long_manifest.write( output )
        else:
            species_with_no_long += 1

        total_short_records += len( short_records )
        total_long_records += len( long_records )
        total_dropped_long_header += dropped_long_header

        print( f'{species_name[:70]:<70s} {len(short_records):>7d} {len(long_records):>5d} {dropped_long_header:>9d}' )

    output_short_manifest.close()
    output_long_manifest.close()

    print( '' )
    print( '========================================================================' )
    print( f'Total species processed: {len(species_names)}' )
    print( f'Total short ( <={MAX_SEQUENCE_LENGTH} aa ) records: {total_short_records}' )
    print( f'Total long  (  >{MAX_SEQUENCE_LENGTH} aa ) records: {total_long_records}' )
    print( f'Total dropped ( header > {MAX_HEADER_LENGTH} chars ): {total_dropped_long_header}' )
    print( f'Species with NO short  records ( excluded from RUN_2 manifest ): {species_with_no_short}' )
    print( f'Species with NO long   records ( excluded from RUN_3 manifest ): {species_with_no_long}' )
    print( '' )
    print( f'RUN_2 manifest: {short_manifest_path}' )
    print( f'RUN_3 manifest: {long_manifest_path}' )


if __name__ == '__main__':
    main()
