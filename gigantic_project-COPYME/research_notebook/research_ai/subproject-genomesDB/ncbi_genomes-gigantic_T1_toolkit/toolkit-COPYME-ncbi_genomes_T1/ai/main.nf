#!/usr/bin/env nextflow
/*
 * NCBI Genomes T1 Toolkit -- main.nf
 *
 * AI: Claude Code | Opus 4.7 (1M context) | 2026 May 28
 * Human: Eric Edsinger
 *
 * Purpose:
 *   Download NCBI RefSeq (and compatible) genome bundles, T1-extract with
 *   alternate-loci filtering, rename to GIGANTIC convention, and auto-bridge
 *   into the project's INPUT_user/genomic_resources/ staging arena. The
 *   canonical seed GIGANTIC toolkit per gigantic_conventions.md §59. Lives
 *   in research_notebook/research_ai/subproject-genomesDB/ and follows
 *   GIGANTIC framework conventions internally (§28 conda env, §29 unified
 *   RUN-workflow.sh, §36 fail-fast, §45 write_run_log, §17/§18
 *   staging-arena bridging).
 *
 * Pipeline (5 processes, sequential):
 *   1. download_ncbi_bundles               (datasets CLI per accession)
 *   2. unzip_organize_rename               (intermediate naming)
 *   3. extract_t1_with_alt_loci_filter     (T1 + alt-loci dedup + GIGANTIC naming + maps)
 *   4. bridge_to_input_user                (two-hop relative symlinks per §17, §18)
 *   5. write_run_log                       (audit log per §45)
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS
// ============================================================================
// All params come from .params.json (built by RUN-workflow.sh from
// START_HERE-user_config.yaml). Defaults live in nextflow.config under the
// same nested shape (params.toolkit.*, params.output.*).
//
// Referenced below:
//   params.toolkit.manifest_path
//   params.toolkit.download_date   (resolved from 'auto' by RUN-workflow.sh)
//   params.toolkit.name
//   params.output.base_dir

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Download NCBI bundles via datasets CLI
 *   Reads:  ../INPUT_user/ncbi_genomes_manifest.tsv
 *   Writes: 1-output/downloads/*.zip
 */
process download_ncbi_bundles {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    output:
        path '1-output/downloads', emit: downloads_dir

    script:
    """
    bash ${projectDir}/scripts/001_ai-bash-download_ncbi_bundles.sh \\
        "${projectDir}/../${params.toolkit.manifest_path}"
    """
}

/*
 * Process 2: Unzip + organize + intermediate rename
 *   Reads:  1-output/downloads/*.zip
 *   Writes: 2-output/{genome,gff3,protein}/
 */
process unzip_organize_rename {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path downloads_dir

    output:
        path '2-output/genome',  emit: genome_dir
        path '2-output/gff3',    emit: gff3_dir
        path '2-output/protein', emit: protein_dir

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-unzip_organize_rename.py \\
        --input-dir ${downloads_dir} \\
        --output-dir 2-output
    """
}

/*
 * Process 3: T1 extraction with alt-loci filter + GIGANTIC convention rename + identifier maps
 *   Reads:  2-output/{genome,gff3,protein}/ + manifest
 *   Writes: 3-output/{T1_proteomes,genomes,gene_annotations,maps}/
 *
 * Carries the months-of-work alt-loci filter design from prior toolkit
 * iterations. The filter prevents proteome inflation from NCBI's
 * alternate haplotype scaffolds (NT_*) and unplaced contigs (NW_*).
 */
process extract_t1_with_alt_loci_filter {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path genome_dir
        path gff3_dir
        path protein_dir

    output:
        path '3-output/T1_proteomes',     emit: t1_proteomes_dir
        path '3-output/genomes',          emit: genomes_dir
        path '3-output/gene_annotations', emit: gene_annotations_dir
        path '3-output/maps',             emit: maps_dir

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-extract_t1_with_alt_loci_filter.py \\
        --manifest      ${projectDir}/../${params.toolkit.manifest_path} \\
        --genome-dir    ${genome_dir} \\
        --gff3-dir      ${gff3_dir} \\
        --protein-dir   ${protein_dir} \\
        --output-dir    3-output \\
        --download-date "${params.download_date}"
    """
}

/*
 * Process 4: Auto-bridge to INPUT_user/genomic_resources/ via two-hop relative symlinks
 *   Reads:  3-output/{T1_proteomes,genomes,gene_annotations,maps}/
 *   Writes: ../output_to_input/<subdir>/        (parent's stable symlinks -> this RUN's 3-output)
 *           ../../../../../INPUT_user/genomic_resources/{proteomes,genomes,annotations}/
 *                                              (project-level symlinks -> parent's output_to_input)
 *
 * The 4-output/ path that NextFlow expects as `published output` exists only
 * to satisfy publishDir; the real work is the symlinks created outside the
 * RUN dir. Per §36 no missing-output failures, the script always writes the
 * marker file even if zero symlinks were created (it would then fail-fast
 * earlier via sys.exit).
 */
process bridge_to_input_user {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path t1_proteomes_dir
        path genomes_dir
        path gene_annotations_dir
        path maps_dir

    output:
        path '4-output/bridge_done.marker', emit: bridge_marker

    script:
    """
    mkdir -p 4-output
    python3 ${projectDir}/scripts/004_ai-python-bridge_to_input_user.py \\
        --t1-proteomes-staged     ${t1_proteomes_dir} \\
        --genomes-staged          ${genomes_dir} \\
        --gene-annotations-staged ${gene_annotations_dir} \\
        --maps-staged             ${maps_dir} \\
        --published-3-output-dir  "${projectDir}/../${params.output.base_dir}/3-output" \\
        --parent-output-to-input-dir "${projectDir}/../../output_to_input" \\
        --input-user-genomic-resources-dir "${projectDir}/../../../../../../INPUT_user/genomic_resources"

    # Bridge step uses absolute paths because it crosses out of the workflow tree
    # into ../../output_to_input/ (sandbox sibling) and ../../../../../../INPUT_user/
    # (project root). All symlinks created are RELATIVE per §18.

    # Marker file satisfies NextFlow's required-output contract per §36
    echo "bridge_to_input_user completed at \$( date -Iseconds )" > 4-output/bridge_done.marker
    """
}

/*
 * Process 5: Write per-run audit log to ai/logs/ per §45
 *   Reads:  Everything produced upstream
 *   Writes: ../ai/logs/run_<timestamp>-<toolkit_name>_success.log
 *
 * The 5-output/ path satisfies publishDir; the real artifact is the log file
 * outside the RUN dir's OUTPUT_pipeline/.
 */
process write_run_log {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path bridge_marker

    output:
        path '5-output/run_log_written.marker', emit: log_marker

    script:
    """
    mkdir -p 5-output
    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \\
        --toolkit-name        "${params.toolkit.name}" \\
        --manifest            "${projectDir}/../${params.toolkit.manifest_path}" \\
        --run-3-output-dir    "${projectDir}/../${params.output.base_dir}/3-output" \\
        --parent-oti-dir      "${projectDir}/../../output_to_input" \\
        --input-user-gr-dir   "${projectDir}/../../../../../../INPUT_user/genomic_resources" \\
        --log-dir             "${projectDir}/logs"

    echo "write_run_log completed at \$( date -Iseconds )" > 5-output/run_log_written.marker
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    download_ncbi_bundles()

    unzip_organize_rename(
        download_ncbi_bundles.out.downloads_dir
    )

    extract_t1_with_alt_loci_filter(
        unzip_organize_rename.out.genome_dir,
        unzip_organize_rename.out.gff3_dir,
        unzip_organize_rename.out.protein_dir
    )

    bridge_to_input_user(
        extract_t1_with_alt_loci_filter.out.t1_proteomes_dir,
        extract_t1_with_alt_loci_filter.out.genomes_dir,
        extract_t1_with_alt_loci_filter.out.gene_annotations_dir,
        extract_t1_with_alt_loci_filter.out.maps_dir
    )

    write_run_log(
        bridge_to_input_user.out.bridge_marker
    )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
