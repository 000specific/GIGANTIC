#!/usr/bin/env nextflow
/*
 * GIGANTIC Source Data Ingestion Pipeline
 * AI: Claude Code | Opus 4.5 | 2026 February 13
 * Human: Eric Edsinger
 *
 * Purpose: Ingest user-provided source data (proteomes, genomes, GFFs)
 *          into GIGANTIC structure for downstream processing by STEP_2.
 *
 * Architecture: 3 scripts, 3 output directories, 1:1 match.
 *   Script 001 -> OUTPUT_pipeline/1-output/  (validation report)
 *   Script 002 -> OUTPUT_pipeline/2-output/  (ingested data copies)
 *   Script 003 -> OUTPUT_pipeline/3-output/  (symlink manifest)
 *
 * Scripts write DIRECTLY to OUTPUT_pipeline/ (no publishDir).
 * NextFlow sequences the scripts but does not move files.
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

/*
 * Process 3: Create output_to_input Symlinks
 * Calls: scripts/003_ai-bash-create_output_symlinks.sh
 *
 * Creates symlinks in ../../output_to_input/ pointing to the
 * hard copies in OUTPUT_pipeline/2-output/. Writes a symlink
 * manifest to OUTPUT_pipeline/3-output/.
 */
process create_output_symlinks {
    label 'local'

    input:
        val ingestion_done

    output:
        val true, emit: symlinks_complete

    script:
    """
    bash ${projectDir}/scripts/003_ai-bash-create_output_symlinks.sh \
        ${params.workflow_root}/${params.output_dir}/2-output \
        ${params.workflow_root}/../output_to_input \
        ${params.workflow_root}/${params.output_dir}/3-output
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

    // Step 3: Create symlinks (waits for ingestion)
    create_output_symlinks( ingest_source_data.out.ingestion_complete )
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
        println "  3-output/  Symlink manifest"
        println ""
        println "Symlinks for STEP_2:"
        println "  ../../output_to_input/T1_proteomes/"
        println "  ../../output_to_input/genomes/"
        println "  ../../output_to_input/gene_annotations/"
    }
    println "========================================================================"
}
