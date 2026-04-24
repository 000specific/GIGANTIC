#!/usr/bin/env python3
# AI: Claude Code | Opus 4 | 2026 February 11 17:45 | Purpose: Extract CDS from genomes using GTF annotations, filter to longest transcript per gene (T1), and translate to proteomes
# Human: Eric Edsinger

"""
003_ai-python-extract_longest_transcript_proteomes.py

Extract T1 (longest transcript per gene) proteomes from genome FASTA + GTF annotations.

Pipeline:
  1. Validate GTF coordinates against genome scaffolds (filter out-of-bounds entries)
  2. Use gffread to extract protein sequences for ALL transcripts from genome + GTF
  3. Parse gffread output FASTA
  4. Group transcripts by gene (using GTF gene_id -> transcript_id mapping)
  5. Select longest protein per gene (T1 = longest transcript)
  6. Write T1 proteome with headers: >Genus_species_geneID_transcriptID

Usage:
  python3 003_ai-python-extract_longest_transcript_proteomes.py --input-dir 2-output --output-dir 3-output

Requires:
  - gffread (module load gffread)
  - Genome FASTA files in input-dir/genome/
  - GTF annotation files in input-dir/gene_annotation/

Output:
  3-output/T1_proteomes/Genus_species-kim_2025-T1_proteome.aa
  3-output/gffread_all_transcripts/  (intermediate all-transcript proteins)
"""

import argparse
import os
import sys
import subprocess
import re
import logging
from pathlib import Path
from collections import defaultdict

# ============================================================================
# Configuration
# ============================================================================

species___genus_species = {
    'Capsaspora_owczarzaki': 'Capsaspora_owczarzaki',
    'Cladtertia_collaboinventa': 'Cladtertia_collaboinventa',
    'Ephydatia_muelleri': 'Ephydatia_muelleri',
    'Mnemiopsis_leidyi': 'Mnemiopsis_leidyi',
    'Salpingoeca_rosetta': 'Salpingoeca_rosetta',
    'Sphaeroforma_arctica': 'Sphaeroforma_arctica',
    'Trichoplax_adhaerens': 'Trichoplax_adhaerens',
}

# ============================================================================
# Setup logging
# ============================================================================

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s | %(levelname)s | %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger( __name__ )


# ============================================================================
# Functions
# ============================================================================

def parse_fasta( fasta_path ):
    """Parse a FASTA file into a dictionary of identifier -> sequence."""
    identifiers___sequences = {}
    current_identifier = None
    current_sequence_parts = []

    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            line = line.strip()
            if line.startswith( '>' ):
                if current_identifier is not None:
                    identifiers___sequences[ current_identifier ] = ''.join( current_sequence_parts )
                current_identifier = line[ 1: ].split()[ 0 ]
                current_sequence_parts = []
            else:
                current_sequence_parts.append( line )

        if current_identifier is not None:
            identifiers___sequences[ current_identifier ] = ''.join( current_sequence_parts )

    return identifiers___sequences


def parse_gtf_attributes( attributes_string ):
    """
    Parse a GTF attributes column (column 9) into a dictionary.

    GTF attribute format per the GTF2/GFF2 specification:
        key "value"; key "value"; ...

    This function handles edge cases that a naive regex like
    `re.search( r'gene_id "([^"]+)"', ... )` would get wrong:
      - Escaped quotes inside values:  key "value with \\"quote\\" inside"
      - Semicolons inside values (preserved because values are fully quoted)
      - Multiple spaces between key and opening quote
      - Unusual attribute names (still alphanumeric + underscore)

    The regex uses an escape-aware quoted-string pattern:
        (\\w+)                    - group 1: attribute key
        \\s+                      - whitespace between key and value
        "                         - opening quote
        ((?:[^"\\\\]|\\\\.)*)     - group 2: value contents — any char that
                                    is not a quote or backslash, OR any
                                    backslash followed by any char
        "                         - closing quote

    Why proper parsing matters for peer-review GIGANTIC:
        The kim_2025 GTFs currently in use don't contain escaped quotes, so
        a naive attribute regex happens to work today. But GTFs from other
        sources (custom pipelines, third-party databases, older tools) may
        contain quote characters or other oddities. A silent partial match
        on gene_id would truncate the identifier — silently producing a
        WRONG gene ID in T1 output. Using a proper parser guards against
        any such future input.

    Parameters:
        attributes_string (str): The column-9 string of a GTF line

    Returns:
        dict: attribute_name -> value. If the same key appears more than
              once in the string, the first occurrence wins (matches what
              `re.search` would return; preserves behavioral compatibility).
    """
    attributes = {}
    for match in re.finditer( r'(\w+)\s+"((?:[^"\\]|\\.)*)"', attributes_string ):
        key = match.group( 1 )
        value = match.group( 2 )
        # Unescape common GTF escape sequences: \" -> " and \\ -> \
        value = value.replace( '\\"', '"' ).replace( '\\\\', '\\' )
        if key not in attributes:
            attributes[ key ] = value
    return attributes


def parse_gtf_gene_transcript_mapping( gtf_path ):
    """
    Parse a GTF file to extract gene -> transcripts mapping AND track which
    transcripts have at least one CDS line in the source GTF.

    Returning both is essential for accurate gene-drop classification:
      - A gene with ZERO transcripts having CDS is non-coding by definition
        in this source GTF (e.g., lncRNAs, tRNAs, rRNAs) and legitimately
        drops out of T1.
      - A gene with >=1 transcript having CDS is protein-coding-eligible
        and is EXPECTED to appear in T1. If it doesn't, something downstream
        filtered it (bounds filter or gffread skip) and we need to say so.

    Uses parse_gtf_attributes for correctness on any well-formed GTF.

    Parameters:
        gtf_path (Path): Path to the GTF annotation file

    Returns:
        dict: gene_id -> sorted list of transcript_ids (all transcripts
              associated with this gene, regardless of biotype)
        set:  transcript_ids that have at least one CDS line in the GTF
              (i.e., the source annotation marks them as protein-coding)
    """
    gene_identifiers___transcript_identifiers = defaultdict( set )
    transcripts_with_cds_in_gtf = set()

    with open( gtf_path, 'r' ) as input_gtf:
        for line in input_gtf:
            line = line.rstrip( '\n' )
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )
            if len( parts ) < 9:
                continue

            attributes = parse_gtf_attributes( parts[ 8 ] )
            gene_identifier = attributes.get( 'gene_id', '' )
            transcript_identifier = attributes.get( 'transcript_id', '' )

            # Record every (gene, transcript) pair we encounter. Multiple
            # feature lines per transcript (gene, transcript, exon, CDS)
            # collapse to the same set element - redundant adds are harmless
            # due to set semantics.
            if gene_identifier and transcript_identifier:
                gene_identifiers___transcript_identifiers[ gene_identifier ].add( transcript_identifier )

            # Mark the transcript as protein-coding-eligible if we see any
            # CDS line for it. One CDS is enough (multi-exon CDS contribute
            # multiple CDS lines per transcript - all map to the same set entry).
            if transcript_identifier and parts[ 2 ] == 'CDS':
                transcripts_with_cds_in_gtf.add( transcript_identifier )

    # Convert sets to sorted lists for deterministic downstream iteration
    # and stable TSV output across runs.
    for gene_identifier in gene_identifiers___transcript_identifiers:
        gene_identifiers___transcript_identifiers[ gene_identifier ] = sorted(
            gene_identifiers___transcript_identifiers[ gene_identifier ]
        )

    return gene_identifiers___transcript_identifiers, transcripts_with_cds_in_gtf


def read_fasta_index( fai_path ):
    """Read a FASTA index (.fai) file to get scaffold/chromosome lengths."""
    scaffold_names___lengths = {}

    with open( fai_path, 'r' ) as input_fai:
        # scaffold_name    length    offset    linebases    linewidth
        # chr_1    16344884    7    60    61
        for line in input_fai:
            line = line.strip()
            if not line:
                continue
            parts = line.split( '\t' )
            scaffold_name = parts[ 0 ]
            scaffold_length = int( parts[ 1 ] )
            scaffold_names___lengths[ scaffold_name ] = scaffold_length

    return scaffold_names___lengths


def filter_gtf_by_genome_bounds( gtf_path, genome_fasta_path, filtered_gtf_path ):
    """
    Filter a GTF file to remove entries with coordinates beyond scaffold
    boundaries OR on scaffolds absent from the genome FASTA.

    Why this matters in practice: GTFs are often lifted between assemblies
    (e.g., with Liftoff). A lifted GTF may reference scaffolds that don't
    exist in the target genome, or extend past scaffold ends because the
    source assembly had longer scaffolds. gffread will fail or produce
    corrupt output on such entries; removing them is correct.

    Per-transcript accounting (added for bombproofing):
      The function now records, per transcript, how many CDS lines it had
      BEFORE filtering and how many remain AFTER filtering. From this we
      derive the set of transcripts whose CDS was entirely eliminated by
      the filter - those transcripts can no longer produce a protein and
      their parent gene may be silently dropped from T1. Surfacing this
      set is critical for peer-review transparency: every dropped coding
      gene must be explainable.

    Parameters:
        gtf_path (Path): Input GTF
        genome_fasta_path (Path): Genome FASTA; used to obtain scaffold
            lengths from its .fai index (generated on demand via gffread)
        filtered_gtf_path (Path): Output path for the filtered GTF

    Returns:
        dict with keys:
            total_line_count:
                total GTF lines read (incl. comments)
            kept_line_count:
                lines written to the filtered GTF
            removed_line_count:
                lines dropped because of out-of-bounds or missing scaffold
            removed_transcript_identifiers:
                set of transcript_ids touched by ANY line removal (even if
                the transcript still has other lines retained)
            transcripts_cds_entirely_removed:
                set of transcript_ids that had >=1 CDS line before filtering
                but 0 CDS lines after - these cannot produce a protein via
                gffread, so their parent genes are at risk of dropping from T1
    """
    fai_path = Path( str( genome_fasta_path ) + '.fai' )
    if not fai_path.exists():
        logger.info( f'Creating FASTA index for {genome_fasta_path}...' )
        subprocess.run(
            [ 'gffread', '-g', str( genome_fasta_path ), '/dev/null' ],
            capture_output = True, text = True
        )

    scaffold_names___lengths = read_fasta_index( fai_path )
    logger.info( f'  Genome has {len( scaffold_names___lengths )} scaffolds/chromosomes' )

    # Per-transcript CDS accounting. We need both pre-filter and post-filter
    # counts so we can identify transcripts whose CDS went from >0 to 0.
    transcripts___input_cds_line_counts = defaultdict( int )
    transcripts___kept_cds_line_counts = defaultdict( int )

    total_line_count = 0
    kept_line_count = 0
    removed_line_count = 0
    removed_transcript_identifiers = set()

    with open( gtf_path, 'r' ) as input_gtf, open( filtered_gtf_path, 'w' ) as output_gtf:
        for line in input_gtf:
            total_line_count += 1
            line_stripped = line.strip()

            # Comments are preserved as-is (GTF structural headers).
            if line_stripped.startswith( '#' ):
                output_gtf.write( line )
                kept_line_count += 1
                continue

            parts = line_stripped.split( '\t' )
            if len( parts ) < 9:
                # Malformed line (fewer than 9 columns) - pass through to
                # preserve any tool-specific directive lines. If the line
                # is truly junk, gffread will flag it later.
                output_gtf.write( line )
                kept_line_count += 1
                continue

            scaffold_name = parts[ 0 ]
            feature_type = parts[ 2 ]
            try:
                end_coordinate = int( parts[ 4 ] )
            except ValueError:
                # Non-integer end coordinate - pass through; gffread will reject.
                output_gtf.write( line )
                kept_line_count += 1
                continue

            attributes = parse_gtf_attributes( parts[ 8 ] )
            transcript_identifier = attributes.get( 'transcript_id', '' )

            # Count pre-filter CDS per transcript regardless of whether the
            # line ends up kept or removed.
            if feature_type == 'CDS' and transcript_identifier:
                transcripts___input_cds_line_counts[ transcript_identifier ] += 1

            # Classify as out-of-bounds in one of two ways:
            #   (a) scaffold name not present in genome index (missing scaffold)
            #   (b) end coordinate > scaffold length (lifted past scaffold end)
            scaffold_length = scaffold_names___lengths.get( scaffold_name, None )

            if scaffold_length is None:
                removed_line_count += 1
                if transcript_identifier:
                    removed_transcript_identifiers.add( transcript_identifier )
                logger.warning(
                    f'  Scaffold {scaffold_name} not found in genome index, removing line '
                    f'(transcript={transcript_identifier or "-"}, feature={feature_type})'
                )
                continue

            if end_coordinate > scaffold_length:
                removed_line_count += 1
                if transcript_identifier:
                    removed_transcript_identifiers.add( transcript_identifier )
                    if feature_type == 'CDS':
                        logger.warning(
                            f'  Out-of-bounds CDS: {transcript_identifier} on {scaffold_name} '
                            f'(end={end_coordinate} > scaffold_length={scaffold_length})'
                        )
                continue

            # Line is within bounds - keep it, and count CDS toward the
            # transcript's post-filter CDS tally.
            output_gtf.write( line )
            kept_line_count += 1
            if feature_type == 'CDS' and transcript_identifier:
                transcripts___kept_cds_line_counts[ transcript_identifier ] += 1

    # Derive the set of transcripts whose CDS was entirely eliminated by
    # the filter. A transcript is "bounds-dropped" if it had >=1 CDS line
    # in the input and 0 CDS lines in the output. This is exactly the set
    # of transcripts that CANNOT produce a protein via gffread due to
    # bounds filtering alone.
    transcripts_cds_entirely_removed = set()
    for transcript_identifier, input_count in transcripts___input_cds_line_counts.items():
        if input_count > 0 and transcripts___kept_cds_line_counts.get( transcript_identifier, 0 ) == 0:
            transcripts_cds_entirely_removed.add( transcript_identifier )

    return {
        'total_line_count': total_line_count,
        'kept_line_count': kept_line_count,
        'removed_line_count': removed_line_count,
        'removed_transcript_identifiers': removed_transcript_identifiers,
        'transcripts_cds_entirely_removed': transcripts_cds_entirely_removed,
    }


def run_gffread( genome_fasta_path, gtf_path, output_protein_path ):
    """
    Run gffread to extract protein sequences for all transcripts in the GTF.

    Pipeline:
      1. Bounds-filter the GTF against the genome FASTA (removes lines that
         would cause gffread to fail - out-of-bounds coords, missing scaffolds)
      2. Invoke gffread with the filtered GTF to produce a per-transcript
         protein FASTA
      3. Clean up the temporary filtered GTF
      4. Return the filter result (needed by caller to classify dropped genes)

    Return value changed (bombproofing):
      Previously returned True/False. Now returns the filter_result dict
      from filter_gtf_by_genome_bounds on success, or None on gffread failure.
      Callers use the filter_result to accurately classify genes that
      disappeared because of bounds filtering vs. gffread-internal skips.

    Parameters:
        genome_fasta_path (Path): Input genome FASTA
        gtf_path (Path): Input GTF
        output_protein_path (Path): Output per-transcript protein FASTA

    Returns:
        dict | None: filter_result dict on success (keys documented in
            filter_gtf_by_genome_bounds); None if gffread returned a
            non-zero exit code (pipeline should treat as a fatal error).
    """
    filtered_gtf_path = Path( str( gtf_path ) + '.filtered.tmp' )
    logger.info( f'Validating GTF coordinates against genome...' )
    filter_result = filter_gtf_by_genome_bounds(
        gtf_path, genome_fasta_path, filtered_gtf_path
    )

    removed_line_count = filter_result[ 'removed_line_count' ]
    removed_transcript_identifiers = filter_result[ 'removed_transcript_identifiers' ]
    transcripts_cds_entirely_removed = filter_result[ 'transcripts_cds_entirely_removed' ]

    if removed_line_count > 0:
        logger.warning(
            f'  Removed {removed_line_count} GTF lines '
            f'({len( removed_transcript_identifiers )} transcripts touched; '
            f'{len( transcripts_cds_entirely_removed )} with ALL CDS removed) '
            f'due to out-of-bounds coordinates'
        )
        gtf_to_use = filtered_gtf_path
    else:
        logger.info( f'  All GTF coordinates within genome bounds' )
        gtf_to_use = gtf_path

    command = [
        'gffread',
        '-y', str( output_protein_path ),
        '-g', str( genome_fasta_path ),
        str( gtf_to_use )
    ]

    logger.info( f'Running gffread: {" ".join( command )}' )

    result = subprocess.run( command, capture_output = True, text = True )

    # Always clean up the temporary filtered GTF.
    if filtered_gtf_path.exists():
        filtered_gtf_path.unlink()

    if result.returncode != 0:
        logger.error( f'gffread failed with return code {result.returncode}' )
        logger.error( f'stderr: {result.stderr}' )
        return None

    if result.stderr:
        logger.info( f'gffread messages: {result.stderr.strip()}' )

    return filter_result


def select_longest_transcript_per_gene( gene_identifiers___transcript_identifiers, transcript_identifiers___sequences ):
    """For each gene, select the transcript with the longest protein sequence."""
    gene_identifiers___longest_transcript_data = {}

    for gene_identifier in gene_identifiers___transcript_identifiers:
        transcript_identifiers = gene_identifiers___transcript_identifiers[ gene_identifier ]

        longest_transcript_identifier = None
        longest_sequence = ''
        longest_length = 0

        for transcript_identifier in transcript_identifiers:
            if transcript_identifier in transcript_identifiers___sequences:
                sequence = transcript_identifiers___sequences[ transcript_identifier ]
                sequence_clean = sequence.rstrip( '.' )
                sequence_length = len( sequence_clean )

                if sequence_length > longest_length:
                    longest_length = sequence_length
                    longest_sequence = sequence_clean
                    longest_transcript_identifier = transcript_identifier
            else:
                logger.warning(
                    f'Transcript {transcript_identifier} from gene {gene_identifier} '
                    f'not found in gffread protein output'
                )

        if longest_transcript_identifier is not None:
            gene_identifiers___longest_transcript_data[ gene_identifier ] = {
                'transcript_identifier': longest_transcript_identifier,
                'sequence': longest_sequence,
                'length': longest_length,
            }
        else:
            logger.warning(
                f'No protein sequences found for gene {gene_identifier} '
                f'(transcripts: {transcript_identifiers})'
            )

    return gene_identifiers___longest_transcript_data


def write_t1_proteome( gene_identifiers___longest_transcript_data, genus_species, output_path ):
    """Write the T1 proteome FASTA file with formatted headers."""
    sorted_gene_identifiers = sorted( gene_identifiers___longest_transcript_data.keys() )

    with open( output_path, 'w' ) as output_proteome:
        for gene_identifier in sorted_gene_identifiers:
            transcript_data = gene_identifiers___longest_transcript_data[ gene_identifier ]
            transcript_identifier = transcript_data[ 'transcript_identifier' ]
            sequence = transcript_data[ 'sequence' ]

            header = f'>{genus_species}_{gene_identifier}_{transcript_identifier}'
            output = header + '\n' + sequence + '\n'
            output_proteome.write( output )


def classify_dropped_genes(
    gene_identifiers___transcript_identifiers,
    transcripts_with_cds_in_gtf,
    transcripts_cds_entirely_removed_by_bounds_filter,
    transcripts_in_gffread_protein_output,
):
    """
    For each gene in the input GTF that did NOT produce any protein output,
    classify the reason into one of three mutually-exclusive categories:

      'non_coding':
          The gene has ZERO transcripts with a CDS line in the source GTF.
          This is legitimate filtering - the source annotates the gene as
          non-coding (lncRNA, tRNA, rRNA, etc.), so no protein is expected.

      'bounds_filter':
          The gene has >=1 transcript with a CDS line in the source GTF,
          but ALL of its CDS-bearing transcripts had their CDS lines fully
          removed by the bounds filter (scaffold absent or coords past end).
          The source annotated the gene as coding, but gffread could not
          translate it due to GTF-genome assembly mismatches. This is a
          data-integrity issue in the input, surfaced for peer review.

      'gffread_skip':
          The gene has >=1 CDS-bearing transcript that survived bounds
          filtering, but gffread still did not produce any protein output
          for any of them. Common reasons include: CDS length not divisible
          by 3, premature stop codons, inconsistent strand, gffread rejection
          of malformed records. Each is a legitimate translation failure.

    Genes that DID produce at least one protein output are not classified
    here - they appear in the T1 proteome and need no drop explanation.

    Parameters:
        gene_identifiers___transcript_identifiers:
            dict gene_id -> list of transcript_ids (from the source GTF)
        transcripts_with_cds_in_gtf:
            set of transcript_ids that had >=1 CDS line in source GTF
        transcripts_cds_entirely_removed_by_bounds_filter:
            set of transcript_ids whose CDS was reduced from >0 to 0 by
            the bounds filter
        transcripts_in_gffread_protein_output:
            set of transcript_ids present in the gffread protein FASTA

    Returns:
        list of dicts, each with keys:
            gene_id, reason, transcripts
        plus a counters dict with keys:
            non_coding, bounds_filter, gffread_skip
    """
    drops = []
    counters = { 'non_coding': 0, 'bounds_filter': 0, 'gffread_skip': 0 }

    for gene_identifier in sorted( gene_identifiers___transcript_identifiers.keys() ):
        transcripts = gene_identifiers___transcript_identifiers[ gene_identifier ]

        # Gene is in T1 if ANY of its transcripts produced a gffread protein.
        if any( t in transcripts_in_gffread_protein_output for t in transcripts ):
            continue

        # Gene is NOT in T1 - classify why.
        coding_transcripts = [ t for t in transcripts if t in transcripts_with_cds_in_gtf ]

        if len( coding_transcripts ) == 0:
            reason = 'non_coding'
        elif all( t in transcripts_cds_entirely_removed_by_bounds_filter for t in coding_transcripts ):
            # Every CDS-bearing transcript had all its CDS lines stripped
            # by the bounds filter. The gene cannot produce a protein
            # because the input GTF-genome combination is inconsistent.
            reason = 'bounds_filter'
        else:
            # At least one CDS-bearing transcript survived the bounds filter
            # (still has >=1 CDS line after filtering), but gffread produced
            # no protein for it. Translation-level rejection by gffread.
            reason = 'gffread_skip'

        counters[ reason ] += 1
        drops.append( {
            'gene_id': gene_identifier,
            'reason': reason,
            'transcripts': transcripts,
        } )

    return drops, counters


def process_species( genus_species, genome_fasta_path, gtf_path, intermediate_directory, output_directory ):
    """
    Full pipeline for one species:
        gffread -> bounds-filter -> select longest transcript per gene ->
        classify dropped genes -> write T1 proteome.

    The classification step documents every gene present in the input GTF
    that does NOT appear in the output T1 proteome, with a specific reason
    (non_coding, bounds_filter, or gffread_skip). See classify_dropped_genes
    for reason definitions. This data is later aggregated across species
    into maps/kim_2025-log-dropped_genes.tsv for peer-review transparency.
    """
    logger.info( f'========================================' )
    logger.info( f'Processing: {genus_species}' )
    logger.info( f'  Genome: {genome_fasta_path}' )
    logger.info( f'  GTF: {gtf_path}' )
    logger.info( f'========================================' )

    intermediate_protein_path = intermediate_directory / f'{genus_species}-kim_2025-all_transcripts.fa'

    # Run gffread; returns filter_result dict on success (or None on fail).
    # filter_result carries per-transcript bounds-filter accounting needed
    # to distinguish bounds-drops from gffread-skips below.
    filter_result = run_gffread( genome_fasta_path, gtf_path, intermediate_protein_path )
    if filter_result is None:
        logger.error( f'CRITICAL ERROR: gffread failed for {genus_species}' )
        logger.error( f'Cannot proceed without protein sequences' )
        sys.exit( 1 )

    logger.info( f'Parsing gffread protein output...' )
    transcript_identifiers___sequences = parse_fasta( intermediate_protein_path )
    total_transcript_count = len( transcript_identifiers___sequences )
    logger.info( f'  Total transcripts from gffread: {total_transcript_count}' )

    logger.info( f'Parsing GTF for gene-transcript mapping...' )
    gene_identifiers___transcript_identifiers, transcripts_with_cds_in_gtf = parse_gtf_gene_transcript_mapping( gtf_path )
    total_gene_count = len( gene_identifiers___transcript_identifiers )
    logger.info( f'  Total genes in GTF: {total_gene_count}' )
    logger.info( f'  Transcripts with CDS in GTF: {len( transcripts_with_cds_in_gtf )}' )

    logger.info( f'Selecting longest transcript per gene (T1)...' )
    gene_identifiers___longest_transcript_data = select_longest_transcript_per_gene(
        gene_identifiers___transcript_identifiers,
        transcript_identifiers___sequences
    )
    t1_gene_count = len( gene_identifiers___longest_transcript_data )
    logger.info( f'  T1 genes with protein: {t1_gene_count}' )

    # Classify dropped genes by reason. This data is aggregated across
    # species in main() and written to a TSV for peer-review audit.
    transcripts_in_gffread_protein_output = set( transcript_identifiers___sequences.keys() )
    drops, drop_counters = classify_dropped_genes(
        gene_identifiers___transcript_identifiers,
        transcripts_with_cds_in_gtf,
        filter_result[ 'transcripts_cds_entirely_removed' ],
        transcripts_in_gffread_protein_output,
    )
    logger.info( f'  Dropped genes: non_coding={drop_counters[ "non_coding" ]} '
                 f'bounds_filter={drop_counters[ "bounds_filter" ]} '
                 f'gffread_skip={drop_counters[ "gffread_skip" ]}' )

    output_proteome_path = output_directory / f'{genus_species}-kim_2025-T1_proteome.aa'
    logger.info( f'Writing T1 proteome: {output_proteome_path}' )
    write_t1_proteome(
        gene_identifiers___longest_transcript_data,
        genus_species,
        output_proteome_path
    )

    multi_transcript_gene_count = sum(
        1 for gene_identifier in gene_identifiers___transcript_identifiers
        if len( gene_identifiers___transcript_identifiers[ gene_identifier ] ) > 1
    )

    summary = {
        'genus_species': genus_species,
        'total_genes': total_gene_count,
        'total_transcripts': total_transcript_count,
        'transcripts_with_cds': len( transcripts_with_cds_in_gtf ),
        'multi_transcript_genes': multi_transcript_gene_count,
        't1_genes_with_protein': t1_gene_count,
        'non_coding_gene_count': drop_counters[ 'non_coding' ],
        'bounds_filter_gene_count': drop_counters[ 'bounds_filter' ],
        'gffread_skip_gene_count': drop_counters[ 'gffread_skip' ],
        'drops': drops,
        'output_file': str( output_proteome_path ),
    }

    logger.info( f'  Summary for {genus_species}:' )
    logger.info( f'    Total genes in GTF:         {total_gene_count}' )
    logger.info( f'    Total transcripts (gffread):{total_transcript_count}' )
    logger.info( f'    Multi-transcript genes:     {multi_transcript_gene_count}' )
    logger.info( f'    T1 genes with protein:      {t1_gene_count}' )
    logger.info( f'    Dropped (non_coding):       {drop_counters[ "non_coding" ]}' )
    logger.info( f'    Dropped (bounds_filter):    {drop_counters[ "bounds_filter" ]}' )
    logger.info( f'    Dropped (gffread_skip):     {drop_counters[ "gffread_skip" ]}' )

    return summary


def write_dropped_genes_log( all_summaries, output_path ):
    """
    Aggregate dropped-gene records across all species and write a TSV log.

    For each gene that appears in an input GTF but does NOT appear in the
    output T1 proteome, record the species, gene_id, reason, and the list
    of transcripts associated with that gene.

    Drop reasons (see classify_dropped_genes for full definitions):
        non_coding:     zero CDS in input GTF (legitimate non-coding gene)
        bounds_filter:  had CDS in GTF but all CDS dropped by bounds check
        gffread_skip:   had CDS after bounds filter but gffread translated
                        to nothing (e.g. non-divisible-by-3 CDS, internal
                        stop, or other gffread-internal rejection)

    Why this log exists (peer-review relevance):
        Without this log, the T1 extraction silently drops genes for three
        distinct reasons that look identical from the outside. This TSV
        makes every drop decision auditable - a reviewer can verify that
        the "missing" genes are accounted for by legitimate filtering
        rather than unexplained pipeline loss.

    Parameters:
        all_summaries (list): List of per-species summary dicts, each
            with a 'drops' list entry (built by classify_dropped_genes)
        output_path (Path): Output TSV path (typically in maps/ directory)
    """
    total_drop_count = 0
    with open( output_path, 'w' ) as output_log:
        output = (
            'Genus_Species (species name as Genus_species)'
            '\t'
            'Gene_ID (gene identifier from GTF gene_id attribute)'
            '\t'
            'Drop_Reason (one of: non_coding, bounds_filter, gffread_skip)'
            '\t'
            'Transcripts (comma delimited list of transcript identifiers associated with this gene)'
            '\n'
        )
        output_log.write( output )

        for summary in all_summaries:
            species = summary[ 'genus_species' ]
            for drop in summary[ 'drops' ]:
                transcripts_string = ','.join( drop[ 'transcripts' ] )
                output = f'{species}\t{drop[ "gene_id" ]}\t{drop[ "reason" ]}\t{transcripts_string}\n'
                output_log.write( output )
                total_drop_count += 1

    logger.info( f'  Dropped genes log: {total_drop_count} entries written to {output_path.name}' )


# ============================================================================
# Main
# ============================================================================

def main():

    parser = argparse.ArgumentParser(
        description = 'Extract T1 (longest transcript per gene) proteomes from genome FASTA + GTF annotations'
    )
    parser.add_argument( '--input-dir', required = True, help = 'Directory containing genome/ and gene_annotation/ subdirectories' )
    parser.add_argument( '--output-dir', required = True, help = 'Output directory (will create T1_proteomes/, gffread_all_transcripts/, and maps/ inside)' )
    arguments = parser.parse_args()

    input_genome_directory = Path( arguments.input_dir ) / 'genome'
    input_gene_annotation_directory = Path( arguments.input_dir ) / 'gene_annotation'
    output_intermediate_directory = Path( arguments.output_dir ) / 'gffread_all_transcripts'
    output_proteome_directory = Path( arguments.output_dir ) / 'T1_proteomes'
    output_maps_directory = Path( arguments.output_dir ) / 'maps'

    logger.info( f'Input genome directory: {input_genome_directory}' )
    logger.info( f'Input annotation directory: {input_gene_annotation_directory}' )
    logger.info( f'Output proteome directory: {output_proteome_directory}' )
    logger.info( f'Intermediate directory: {output_intermediate_directory}' )
    logger.info( f'Maps directory: {output_maps_directory}' )

    if not input_genome_directory.exists():
        logger.error( f'CRITICAL ERROR: Genome directory not found: {input_genome_directory}' )
        sys.exit( 1 )

    if not input_gene_annotation_directory.exists():
        logger.error( f'CRITICAL ERROR: Gene annotation directory not found: {input_gene_annotation_directory}' )
        sys.exit( 1 )

    gffread_check = subprocess.run( [ 'which', 'gffread' ], capture_output = True, text = True )
    if gffread_check.returncode != 0:
        logger.error( 'CRITICAL ERROR: gffread not found in PATH' )
        logger.error( 'Run: module load gffread' )
        sys.exit( 1 )
    logger.info( f'Using gffread: {gffread_check.stdout.strip()}' )

    output_intermediate_directory.mkdir( parents = True, exist_ok = True )
    output_proteome_directory.mkdir( parents = True, exist_ok = True )
    output_maps_directory.mkdir( parents = True, exist_ok = True )

    all_summaries = []

    for genus_species in sorted( species___genus_species.keys() ):

        genome_fasta_path = input_genome_directory / f'{genus_species}-kim_2025.fasta'
        if not genome_fasta_path.exists():
            logger.error( f'CRITICAL ERROR: Genome FASTA not found: {genome_fasta_path}' )
            sys.exit( 1 )

        gtf_path = input_gene_annotation_directory / f'{genus_species}-kim_2025.gtf'
        if not gtf_path.exists():
            logger.error( f'CRITICAL ERROR: GTF not found: {gtf_path}' )
            sys.exit( 1 )

        summary = process_species(
            genus_species,
            genome_fasta_path,
            gtf_path,
            output_intermediate_directory,
            output_proteome_directory
        )

        if summary:
            all_summaries.append( summary )

    # Write the aggregate dropped-genes log TSV. This is the peer-review
    # audit trail: one row per gene in any input GTF that did not appear
    # in the corresponding output T1 proteome, with a specific reason.
    dropped_genes_log_path = output_maps_directory / 'kim_2025-log-dropped_genes.tsv'
    write_dropped_genes_log( all_summaries, dropped_genes_log_path )

    logger.info( '' )
    logger.info( '=' * 120 )
    logger.info( 'FINAL SUMMARY: T1 Proteome Extraction' )
    logger.info( '=' * 120 )
    logger.info(
        f'{"Species":<30} {"Genes":>8} {"Txs":>8} {"CDS-Txs":>8} {"Multi-T":>8} '
        f'{"T1":>8} {"NonCoding":>10} {"BoundsDrop":>11} {"GffreadSkip":>12}'
    )
    logger.info( '-' * 120 )

    for summary in all_summaries:
        logger.info(
            f'{summary[ "genus_species" ]:<30} '
            f'{summary[ "total_genes" ]:>8} '
            f'{summary[ "total_transcripts" ]:>8} '
            f'{summary[ "transcripts_with_cds" ]:>8} '
            f'{summary[ "multi_transcript_genes" ]:>8} '
            f'{summary[ "t1_genes_with_protein" ]:>8} '
            f'{summary[ "non_coding_gene_count" ]:>10} '
            f'{summary[ "bounds_filter_gene_count" ]:>11} '
            f'{summary[ "gffread_skip_gene_count" ]:>12}'
        )

    # Column totals aid quick cross-species comparison and sanity-checking
    # against the dropped_genes log row count.
    total_genes = sum( s[ 'total_genes' ] for s in all_summaries )
    total_t1 = sum( s[ 't1_genes_with_protein' ] for s in all_summaries )
    total_non_coding = sum( s[ 'non_coding_gene_count' ] for s in all_summaries )
    total_bounds = sum( s[ 'bounds_filter_gene_count' ] for s in all_summaries )
    total_gffread_skip = sum( s[ 'gffread_skip_gene_count' ] for s in all_summaries )
    logger.info( '-' * 120 )
    logger.info(
        f'{"TOTAL":<30} {total_genes:>8} {"":>8} {"":>8} {"":>8} '
        f'{total_t1:>8} {total_non_coding:>10} {total_bounds:>11} {total_gffread_skip:>12}'
    )
    logger.info( '' )
    logger.info( f'Species processed:     {len( all_summaries )}' )
    logger.info( f'T1 proteomes:          {output_proteome_directory}/' )
    logger.info( f'Dropped genes log:     {dropped_genes_log_path}' )
    logger.info( 'Done!' )


if __name__ == '__main__':
    main()
