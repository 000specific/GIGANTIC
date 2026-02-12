#!/usr/bin/env nextflow
/*
 * GIGANTIC Source Proteome Ingestion Pipeline
 * AI: Claude Code | Opus 4.5 | 2026 February 12
 * Human: Eric Edsinger
 *
 * Purpose: Ingest user-provided proteome files into GIGANTIC structure
 *
 * Pattern: A (Sequential) - Simple file copy workflow
 * Typical runtime: ~1-5 minutes (depends on file sizes)
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.project_name = "my_project"
params.source_manifest = "INPUT_user/source_manifest.tsv"
params.output_dir = "OUTPUT_pipeline"
params.overwrite_existing = false
params.missing_file_action = "error"

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Ingest Source Proteomes
 * Calls: scripts/001_ai-python-ingest_proteomes.py
 *
 * Reads the source manifest and copies proteomes to OUTPUT_pipeline/1-output/
 */
process ingest_proteomes {
    label 'local'

    // Publish to OUTPUT_pipeline with full directory structure
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path source_manifest

    output:
        path "1-output/proteomes/*", emit: proteomes
        path "1-output/ingestion_log.tsv", emit: ingestion_log

    script:
    """
    # Create output directory
    mkdir -p 1-output/proteomes

    # Run proteome ingestion
    python3 ${projectDir}/scripts/001_ai-python-ingest_proteomes.py \\
        --manifest ${source_manifest} \\
        --output-dir 1-output \\
        --project-name "${params.project_name}" \\
        --missing-action ${params.missing_file_action} \\
        ${params.overwrite_existing ? '--overwrite' : ''}
    """
}

/*
 * Process 2: Create Output Symlinks
 * Calls: scripts/002_ai-bash-create_output_symlinks.sh
 *
 * Creates symlinks from STEP_1-sources/output_to_input/proteomes/
 * to the hard-copied proteomes in OUTPUT_pipeline/1-output/proteomes/
 */
process create_output_symlinks {
    label 'local'

    input:
        path proteomes

    output:
        val true, emit: symlinks_complete

    script:
    """
    # Run symlink creation
    # Note: We pass the absolute path to the published proteome directory
    # and the output_to_input directory (relative to STEP_1-sources)
    bash ${projectDir}/scripts/002_ai-bash-create_output_symlinks.sh \\
        "${projectDir}/../${params.output_dir}/1-output/proteomes" \\
        "${projectDir}/../../output_to_input"
    """
}

/*
 * Process 3: Write Run Log
 * Calls: scripts/003_ai-python-write_run_log.py
 *
 * Creates a timestamped log in research_notebook for reproducibility.
 */
process write_run_log {
    label 'local'

    input:
        val symlinks_complete
        path source_manifest

    output:
        val true, emit: log_complete

    script:
    """
    # Count proteomes in manifest
    PROTEOME_COUNT=\$(grep -v '^#' ${source_manifest} | grep -v '^\$' | wc -l)

    # Write run log to research notebook
    python3 ${projectDir}/scripts/003_ai-python-write_run_log.py \\
        --project-name "${params.project_name}" \\
        --proteome-count \$PROTEOME_COUNT \\
        --manifest-file ${source_manifest} \\
        --output-dir "${params.output_dir}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Get source manifest from INPUT_user/ (relative to workflow root, not ai/)
    source_manifest_ch = Channel.fromPath("${projectDir}/../${params.source_manifest}")

    // Step 1: Ingest proteomes (copy to OUTPUT_pipeline)
    ingest_proteomes(source_manifest_ch)

    // Step 2: Create symlinks in output_to_input
    create_output_symlinks(ingest_proteomes.out.proteomes)

    // Step 3: Write run log to research notebook (FINAL STEP)
    write_run_log(
        create_output_symlinks.out.symlinks_complete,
        source_manifest_ch
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Source Proteome Ingestion Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files:"
        println "  - ${params.output_dir}/1-output/proteomes/  (archived copies)"
        println "  - ${params.output_dir}/1-output/ingestion_log.tsv"
        println ""
        println "Symlinks created in:"
        println "  - ../../output_to_input/proteomes/  (for STEP_2)"
        println ""
        println "Run log written to:"
        println "  - research_notebook/research_ai/subproject-genomesDB/logs/"
        println ""
        println "Next step: Run STEP_2-standardize_and_evaluate workflow"
    }
    println "========================================================================"
}
