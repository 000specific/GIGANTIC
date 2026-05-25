#!/usr/bin/env nextflow
/*
 * GIGANTIC Source Data Ingestion Pipeline
 * AI: Claude Code | Opus 4.5 | 2026 February 13
 * Human: Eric Edsinger
 *
 * Purpose: Ingest user-provided source data (proteomes, genomes, genome annotations)
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
// PARAMETERS (from config.yaml via nextflow.config + .params.json)
// ============================================================================
// All defaults live in nextflow.config; users edit START_HERE-user_config.yaml,
// not this file. Nested params (params.X.Y.Z) mirror the yaml shape.

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
        --manifest ${params.workflow_root}/${params.project.source_manifest} \
        --output-dir ${params.workflow_root}/${params.output.base_dir}/1-output \
        --workflow-dir ${params.workflow_root} \
        --missing-action ${params.ingestion.missing_file_action}
    """
}

/*
 * Process 2: Ingest Source Data
 * Calls: scripts/002_ai-python-ingest_source_data.py
 *
 * Hard-copies all source files into OUTPUT_pipeline/2-output/
 * organized by data type (T1_proteomes, genomes, genome_annotations).
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
        --manifest ${params.workflow_root}/${params.project.source_manifest} \
        --output-dir ${params.workflow_root}/${params.output.base_dir}/2-output \
        --workflow-dir ${params.workflow_root} \
        --project-name ${params.project.name} \
        --missing-action ${params.ingestion.missing_file_action} \
        ${params.ingestion.overwrite_existing ? '--overwrite' : ''}
    """
}

/*
 * Process 3: Write Run Log
 * Calls: scripts/004_ai-python-write_run_log.py
 *
 * Creates a timestamped log in ai/logs/ within this workflow directory
 * for transparency and reproducibility.
 */
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-write_run_log.py \
        --workflow-name "ingest_source_data" \
        --subproject-name "genomesDB" \
        --project-name "${params.project.name}" \
        --status success
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

    // Write run log (FINAL STEP)
    write_run_log( ingest_source_data.out.ingestion_complete )

    // NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh
    // AFTER this pipeline completes successfully.
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
