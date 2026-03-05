#!/usr/bin/env nextflow
/*
 * GIGANTIC Phylonames Pipeline - STEP 2: Apply User Phylonames
 * AI: Claude Code | Opus 4.6 | 2026 March 04
 * Human: Eric Edsinger
 *
 * Purpose: Apply user-provided custom phylonames to override STEP 1 output
 *
 * This is STEP 2 of a 2-STEP workflow:
 *   STEP 1: Generate phylonames from NCBI taxonomy. User reviews output.
 *   STEP 2 (this): Apply user-provided custom phylonames after review.
 *
 * INPUTS:
 *   - Project mapping from STEP 1 (via output_to_input/STEP_1-generate_and_evaluate/maps/)
 *   - User-provided phylonames (INPUT_user/user_phylonames.tsv)
 *
 * Pattern: A (Sequential) - All processes run in one job
 * Typical runtime: < 1 minute
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.project_name = "my_project"
params.step1_mapping = "../../output_to_input/STEP_1-generate_and_evaluate/maps"
params.user_phylonames = "INPUT_user/user_phylonames.tsv"
params.mark_unofficial = true
params.output_dir = "OUTPUT_pipeline"

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Apply User-Provided Phylonames
 * Calls: scripts/001_ai-python-apply_user_phylonames.py
 *
 * Reads the STEP 1 project mapping from output_to_input (subproject-level symlinks)
 * and applies user-provided overrides. Clades that differ from NCBI are marked
 * UNOFFICIAL (unless mark_unofficial is false).
 *
 * KEY CONCEPT: Assigning a clade to a species is a taxonomic DECISION.
 * When users override NCBI, their decision is "unofficial" regardless of
 * whether the clade name exists in NCBI taxonomy.
 */
process apply_user_phylonames {
    label 'local'

    // Publish to OUTPUT_pipeline with full directory structure
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path project_mapping
        path user_phylonames

    output:
        path "1-output/final_project_mapping.tsv", emit: final_mapping
        path "1-output/unofficial_clades_report.tsv", emit: unofficial_report

    script:
    // Build the command with optional --no-mark-unofficial flag
    def unofficial_flag = params.mark_unofficial ? "" : "--no-mark-unofficial"
    """
    # Create output directory
    mkdir -p 1-output

    # Apply user phylonames
    # By default, ALL user-provided clades are marked UNOFFICIAL
    # Use mark_unofficial: false in config to disable this
    python3 ${projectDir}/scripts/001_ai-python-apply_user_phylonames.py \\
        --project-mapping ${project_mapping} \\
        --user-phylonames ${user_phylonames} \\
        --output-dir 1-output \\
        ${unofficial_flag}
    """
}

/*
 * Process 2: Generate Taxonomy Summary
 * Calls: scripts/002_ai-python-generate_taxonomy_summary.py
 *
 * Generates readable summary of the UPDATED phylonames showing:
 * - Taxonomic distribution (species counts by clade)
 * - UNOFFICIAL clades (user-provided classifications)
 * - Numbered clades remaining (NCBI gaps not yet named)
 */
process generate_taxonomy_summary {
    label 'local'

    // Publish to OUTPUT_pipeline
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    // Also publish to upload_to_server for web viewing
    publishDir "${projectDir}/../../upload_to_server/taxonomy_summaries", mode: 'copy', overwrite: true,
               saveAs: { filename ->
                   if (filename.endsWith('.html') || filename.endsWith('.md')) {
                       return filename.tokenize('/').last()
                   }
                   return null
               }

    input:
        path final_mapping

    output:
        path "2-output/${params.project_name}_taxonomy_summary.md", emit: summary_md
        path "2-output/${params.project_name}_taxonomy_summary.html", emit: summary_html

    script:
    """
    # Create output directory
    mkdir -p 2-output

    # Generate taxonomy summary (both markdown and HTML)
    python3 ${projectDir}/scripts/002_ai-python-generate_taxonomy_summary.py \\
        --input ${final_mapping} \\
        --output-dir 2-output \\
        --project-name "${params.project_name}"
    """
}

/*
 * Process 3: Write Run Log to Research Notebook
 * Calls: scripts/003_ai-python-write_run_log.py
 *
 * Creates a timestamped log in research_notebook/research_ai/subproject-phylonames/logs/
 * for transparency and reproducibility.
 * This is the FINAL step in STEP 2.
 */
process write_run_log {
    label 'local'

    input:
        path final_mapping

    output:
        val true, emit: log_complete

    script:
    """
    # Count species in the final mapping (excluding header)
    SPECIES_COUNT=\$(tail -n +2 ${final_mapping} | wc -l)

    # Write run log to research notebook
    python3 ${projectDir}/scripts/003_ai-python-write_run_log.py \\
        --project-name "${params.project_name}" \\
        --species-count \$SPECIES_COUNT \\
        --species-file ${final_mapping} \\
        --output-file ${final_mapping} \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Get STEP 1 project mapping from output_to_input (subproject-level symlinks)
    // This follows GIGANTIC convention: between STEPs, read from output_to_input/
    step1_mapping_ch = Channel
        .fromPath("${projectDir}/../${params.step1_mapping}/${params.project_name}_map-genus_species_X_phylonames.tsv")

    // Get user-provided phylonames from INPUT_user/
    user_phylonames_ch = Channel.fromPath("${projectDir}/../${params.user_phylonames}")

    // Step 1: Apply user phylonames
    apply_user_phylonames(
        step1_mapping_ch,
        user_phylonames_ch
    )

    // Step 2: Generate taxonomy summary for updated mapping
    generate_taxonomy_summary(
        apply_user_phylonames.out.final_mapping
    )

    // Step 3: Write run log to research notebook (FINAL STEP)
    write_run_log(
        apply_user_phylonames.out.final_mapping
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Phylonames Pipeline - STEP 2 Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files:"
        println "  - ${params.output_dir}/1-output/final_project_mapping.tsv"
        println "  - ${params.output_dir}/1-output/unofficial_clades_report.tsv"
        println "  - ${params.output_dir}/2-output/${params.project_name}_taxonomy_summary.md"
        println "  - ${params.output_dir}/2-output/${params.project_name}_taxonomy_summary.html"
        println ""
        println "Symlinks updated in output_to_input/ (by RUN-workflow.sh)"
        println "Taxonomy summary copied to upload_to_server/taxonomy_summaries/"
        println "Run log written to research_notebook/research_ai/subproject-phylonames/logs/"
        println ""
        println "User phylonames applied. Clades differing from NCBI are marked UNOFFICIAL."
    }
    println "========================================================================"
}
