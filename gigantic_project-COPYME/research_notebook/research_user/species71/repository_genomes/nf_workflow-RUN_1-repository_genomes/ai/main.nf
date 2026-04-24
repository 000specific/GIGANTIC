#!/usr/bin/env nextflow
/*
 * Repository Genomes Pipeline
 * AI: Claude Code | Opus 4.7 | 2026 April 23
 * Human: Eric Edsinger
 *
 * Purpose: Download genomes, annotations, and protein sequences from various
 * external repositories; backfill missing protein data via gffread where possible;
 * integrate user-provided data; extract T1 (longest transcript per gene) proteomes
 * using per-species header-parsing strategies; publish via symlinks for downstream.
 *
 * Source: Various repositories (FigShare, Zenodo, Dryad, GigaDB, OIST, etc.) and
 * user-provided data (user_research/) for species lacking public releases.
 *
 * Scripts (numbered sequentially 001-005):
 *   001_ai-bash-download_repository_genomes.sh
 *       Orchestrates per-species downloaders at ai/scripts/per_species/{species}/download.sh.
 *       Produces 1-output/{species}/ with whichever files each repository provided
 *       (genome.fasta, annotation.gff3 / .gtf, protein.faa).
 *
 *   002_ai-python-extract_protein_from_genome_annotation.py
 *       Conditional: for species with genome + GFF3 but NO protein.faa, runs gffread
 *       to translate CDS and selects the longest transcript per gene. Writes the
 *       resulting protein.faa back into 1-output/{species}/ (in-place backfill)
 *       and produces 2-output/{species}/protein.faa alongside a gffread intermediate.
 *       Species with existing protein.faa are skipped (no-op).
 *
 *   003_ai-python-copy_user_research_species.py
 *       Conditional: copies user-provided species data from ../../user_research/
 *       into 1-output/{species}/ for species lacking public releases. Applies to
 *       Beroe_ovata, Pleurobrachia_bachei, Urechis_unicinctus, Membranipora_membranacea.
 *
 *   004_ai-python-select_t1_longest_transcript.py
 *       Reads 1-output/{species}/protein.faa for every species, applies the per-species
 *       T1 header-parsing strategy (one of: already_done, gene_attribute, tab_Gene_attribute,
 *       dot_t, dot_i, no_grouping, trinity, fragment_range, ncbi_gff), selects the longest
 *       isoform per gene, and reformats to GIGANTIC naming. Writes:
 *         2-output/{species}/protein_T1.faa       (per-species T1 proteomes)
 *         3-output/T1_proteomes/{species}-genome-{source}-downloaded_{date}.aa
 *                                                 (final GIGANTIC-named T1 proteomes)
 *
 *   005_ai-bash-create_output_to_input_symlinks.sh
 *       Publishes relative symlinks in output_to_input/T1_proteomes/ (at the
 *       subproject root) pointing back into 3-output/T1_proteomes/*.aa so that
 *       downstream subprojects (genomesDB, etc.) can consume the proteomes via
 *       a stable inter-subproject path.
 *
 * Pattern: A (Sequential) - all processes run in one job.
 * Typical runtime: Variable (dominated by downloads and gffread).
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS
// ============================================================================
//
// Output directories (1-output, 2-output, 3-output) are written directly at
// the workflow root (nf_workflow-*/) rather than inside an OUTPUT_pipeline
// subfolder. This is how the actual production runs of this pipeline land on
// disk, and it matches the relative paths expected by the output_to_input
// symlinks created at the subproject root.

params.manifest = "INPUT_user/repository_genomes_manifest.tsv"

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Download source data from various repositories.
 */
process download_source_data {
    label 'local'

    publishDir "${projectDir}/..", mode: 'copy', overwrite: true

    output:
        path "1-output", emit: downloads_dir

    script:
    """
    bash ${projectDir}/scripts/001_ai-bash-download_repository_genomes.sh \
        "${projectDir}/scripts" \
        "${projectDir}/../${params.manifest}"
    """
}

/*
 * Process 2: Backfill protein.faa for species with genome + GFF3 but no protein.
 *
 * Staging pattern: NextFlow stages in the upstream 1-output, we write the
 * modified 1-output back out (with backfilled protein.faa files) so the next
 * process in the chain can consume the fully-populated downloads directory.
 * The 2-output/ directory carries the gffread intermediate outputs for
 * traceability.
 */
process extract_protein_from_genome_annotation {
    label 'local'

    publishDir "${projectDir}/..", mode: 'copy', overwrite: true

    input:
        path downloads_dir

    output:
        path "1-output", emit: downloads_backfilled
        path "2-output/**"

    script:
    """
    # Stage the incoming 1-output into this process's working area so the
    # script can modify it in place without mutating the NextFlow input.
    mkdir -p 1-output
    cp -a ${downloads_dir}/. 1-output/

    python3 ${projectDir}/scripts/002_ai-python-extract_protein_from_genome_annotation.py \
        --input-dir 1-output \
        --output-dir 2-output
    """
}

/*
 * Process 3: Copy user-provided species data for species lacking public releases.
 *
 * Staging pattern: reads the post-002 1-output and writes a further-modified
 * 1-output with user-research data added for the applicable species.
 */
process copy_user_research_species {
    label 'local'

    publishDir "${projectDir}/..", mode: 'copy', overwrite: true

    input:
        path downloads_dir

    output:
        path "1-output", emit: downloads_complete

    script:
    """
    mkdir -p 1-output
    cp -a ${downloads_dir}/. 1-output/

    python3 ${projectDir}/scripts/003_ai-python-copy_user_research_species.py \
        --user-research-dir ${projectDir}/../../user_research \
        --output-dir 1-output
    """
}

/*
 * Process 4: Select T1 (longest transcript per gene) with per-species strategies
 * and reformat to GIGANTIC-naming outputs in 3-output/T1_proteomes/.
 */
process select_t1_longest_transcript {
    label 'local'

    publishDir "${projectDir}/..", mode: 'copy', overwrite: true

    input:
        path downloads_dir

    output:
        path "3-output/T1_proteomes", emit: t1_proteomes_dir
        path "2-output/**"
        path "3-output/**"

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-select_t1_longest_transcript.py \
        --input-dir ${downloads_dir} \
        --output-dir 2-output
    """
}

/*
 * Process 5: Publish T1 proteomes to output_to_input/ via relative symlinks
 * for inter-subproject consumption (genomesDB, etc.).
 */
process publish_to_output_to_input {
    label 'local'

    publishDir "${projectDir}/..", mode: 'copy', overwrite: true

    input:
        path t1_proteomes_dir

    output:
        path "4-output/symlinks_manifest.tsv", emit: manifest

    script:
    """
    bash ${projectDir}/scripts/005_ai-bash-create_output_to_input_symlinks.sh \
        "${t1_proteomes_dir}" \
        "${projectDir}/../3-output/T1_proteomes" \
        "${projectDir}/../../output_to_input/T1_proteomes"
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // 1. Download source data from repositories
    download_source_data()

    // 2. Backfill protein.faa for species with genome+GFF3 but no protein
    extract_protein_from_genome_annotation(
        download_source_data.out.downloads_dir
    )

    // 3. Copy user-provided species data into the downloads tree
    copy_user_research_species(
        extract_protein_from_genome_annotation.out.downloads_backfilled
    )

    // 4. Select T1 (longest transcript per gene) with per-species strategies
    select_t1_longest_transcript(
        copy_user_research_species.out.downloads_complete
    )

    // 5. Publish T1 proteomes as symlinks at output_to_input/ for downstream
    publish_to_output_to_input(
        select_t1_longest_transcript.out.t1_proteomes_dir
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "Repository Genomes Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Outputs (at workflow root, nf_workflow-*/):"
        println "  1-output/  Per-species download directories (with protein.faa backfilled where needed)"
        println "  2-output/  Per-species intermediate (gffread all-transcripts) and T1 proteomes"
        println "  3-output/  Final T1 proteomes in GIGANTIC-named form (T1_proteomes/, genomes/, gene_annotations/, maps/)"
        println "  4-output/  Symlink manifest"
        println ""
        println "T1 proteomes: 3-output/T1_proteomes/"
        println "Symlinks for downstream: output_to_input/T1_proteomes/"
    }
    println "========================================================================"
}
