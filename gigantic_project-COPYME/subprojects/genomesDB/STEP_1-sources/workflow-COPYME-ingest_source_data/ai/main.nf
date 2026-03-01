#!/usr/bin/env nextflow
/*
 * GIGANTIC Source Data Ingestion Pipeline
 * AI: Claude Code | Opus 4.5 | 2026 February 13
 * Human: Eric Edsinger
 *
 * Purpose: Ingest user-provided source data (proteomes, genomes, GFFs)
 *          into GIGANTIC structure for downstream processing by STEP_2.
 *
 * Architecture: 2 scripts, 2 output directories, 1:1 match.
 *   Script 001 -> OUTPUT_pipeline/1-output/  (validation report)
 *   Script 002 -> OUTPUT_pipeline/2-output/  (ingested data copies)
 *
 * Scripts write DIRECTLY to OUTPUT_pipeline/ (no publishDir).
 * NextFlow sequences the scripts but does not move files.
 *
 * Symlinks for output_to_input/ are created by RUN-workflow.sh
 * AFTER the pipeline completes (not inside NextFlow).
 *
 * Typical runtime: ~1-10 minutes (depends on file sizes and count)
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

// Workflow root directory (parent of ai/ where main.nf lives)
params.workflow_root = "${projectDir}/.."

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate Source Manifest
 * Calls: scripts/001_ai-python-validate_source_manifest.py
 *
 * Reads the user manifest, checks every file exists, writes a
 * validation report to OUTPUT_pipeline/1-output/.
 */
process validate_source_manifest {
    label 'local'

    output:
        val true, emit: validation_complete

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-validate_source_manifest.py \
        --manifest ${params.workflow_root}/${params.source_manifest} \
        --output-dir ${params.workflow_root}/${params.output_dir}/1-output \
        --workflow-dir ${params.workflow_root} \
        --missing-action ${params.missing_file_action}
    """
}

/*
 * Process 2: Ingest Source Data
 * Calls: scripts/002_ai-python-ingest_source_data.py
 *
 * Hard-copies all source files into OUTPUT_pipeline/2-output/
 * organized by data type (T1_proteomes, genomes, gene_annotations).
 */
process ingest_source_data {
    label 'local'

    input:
        val validation_done

    output:
        val true, emit: ingestion_complete

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-ingest_source_data.py \
        --manifest ${params.workflow_root}/${params.source_manifest} \
        --output-dir ${params.workflow_root}/${params.output_dir}/2-output \
        --workflow-dir ${params.workflow_root} \
        --project-name ${params.project_name} \
        --missing-action ${params.missing_file_action} \
        ${params.overwrite_existing ? '--overwrite' : ''}
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Validate source manifest
    validate_source_manifest()

    // Step 2: Ingest source data (waits for validation)
    ingest_source_data( validate_source_manifest.out.validation_complete )

    // NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh
    // AFTER this pipeline completes successfully.
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Source Data Ingestion - Complete"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output:"
        println "  1-output/  Validation report"
        println "  2-output/  Ingested data (T1_proteomes, genomes, gene_annotations)"
        println ""
        println "Symlinks for STEP_2 will be created by RUN-workflow.sh"
    }
    println "========================================================================"
}
