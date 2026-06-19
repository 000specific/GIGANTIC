#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * ANNOTATIONS OCL PIPELINE: ORIGIN-CONSERVATION-LOSS ANALYSIS OF ANNOGROUPS
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow for analyzing annotation group (annogroup) origins,
 * conservation, and loss across phylogenetic species tree structures.
 *
 * Annogroups are the annotation analog to orthogroups -- sets of proteins grouped
 * by their annotation pattern from a specific database. Each annogroup has a
 * simple ID (annogroup_{db}_N) with full details in a companion map.
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly to OUTPUT_pipeline/structure_NNN/N-output/
 * - NextFlow passes only val structure_id between processes (done signal)
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow directory)
 *
 * AI: Claude Code | Opus 4.6 | 2026 April 18
 * Human: Eric Edsinger
 * ==============================================================================
 */

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config + .params.json)
// ============================================================================
// All defaults live in nextflow.config; users edit START_HERE-user_config.yaml,
// not this file. Nested params (params.X.Y.Z) mirror the yaml shape.
// RUN-workflow.sh passes the yaml directly via -params-file at runtime.

params.help = false

// Show help message
if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC ANNOTATIONS OCL PIPELINE
    ==============================================================================

    Usage:
        nextflow run main.nf [options]

    Options:
        --config               Path to START_HERE-user_config.yaml
                               (default: ../START_HERE-user_config.yaml)

        --structure_manifest   Path to structure manifest TSV file
                               (overrides config value)

        --output_dir           Output directory for all results
                               (overrides config value)

        --help                 Show this help message

    The pipeline reads all configuration from START_HERE-user_config.yaml including:
      - run_label (for output_to_input namespacing)
      - annotation_database (pfam, gene3d, deeploc, etc.)
      - annogroup_subtypes (single, combo, zero)
      - Input paths to upstream subprojects

    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// INPUT CHANNELS
// ============================================================================
// Workflow root = ${projectDir}/.. (since projectDir is ai/, the workflow root
// is one level up). All workflow-relative paths use that convention.

// Read structure IDs from manifest (path resolved from params.inputs.structure_manifest)
Channel
    .fromPath( "${projectDir}/../${params.inputs.structure_manifest}" )
    .splitCsv( header: true, sep: '\t' )
    .map { row -> row.structure_id }
    .set { structure_ids_channel }

// ============================================================================
// PROCESS 001: CREATE ANNOGROUPS
// ============================================================================

process load_annogroups {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-load_annogroups.py \\
        --structure_id ${structure_id} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: DETERMINE ORIGINS
// ============================================================================

process determine_origins {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-determine_origins.py \\
        --structure_id ${structure_id} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 003: QUANTIFY CONSERVATION AND LOSS
// ============================================================================

process quantify_conservation_loss {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-quantify_conservation_loss.py \\
        --structure_id ${structure_id} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 004: COMPREHENSIVE OCL ANALYSIS
// ============================================================================

process comprehensive_ocl_analysis {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-comprehensive_ocl_analysis.py \\
        --structure_id ${structure_id} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 005: VALIDATE RESULTS
// ============================================================================

process validate_results {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-validate_results.py \\
        --structure_id ${structure_id} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 006: WRITE RUN LOG
// ============================================================================

/*
 * Process 6: Write Run Log
 * Calls: scripts/006_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/006_ai-python-write_run_log.py \
        --workflow-name "ocl_analysis" \
        --subproject-name "ocl_phylogenetic_structures-BLOCK_annotations_X_ocl" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// PROCESS 007: AGGREGATE RUN SUMMARY
// ============================================================================

/*
 * Process 7: Aggregate Run Summary
 * Calls: scripts/007_ai-python-aggregate_run_summary.py
 *
 * Reads per-structure JSON fragments emitted by Scripts 001-005 and builds
 * RUN_SUMMARY.md at the workflow root. This is the final step -- gives users
 * a glanceable success/failure + key stats view without entering OUTPUT_pipeline/.
 */
process aggregate_run_summary {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: summary_complete

    script:
    """
    python3 ${projectDir}/scripts/007_ai-python-aggregate_run_summary.py \
        --config ${projectDir}/../START_HERE-user_config.yaml \
        --workflow_dir ${projectDir}/..
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Run pipeline for each structure (parallel across structures, sequential per structure)
    load_annogroups( structure_ids_channel )
    determine_origins( load_annogroups.out.structure_id )
    quantify_conservation_loss( determine_origins.out.structure_id )
    comprehensive_ocl_analysis( quantify_conservation_loss.out.structure_id )
    validate_results( comprehensive_ocl_analysis.out.structure_id )

    // Write run log after all structures complete validation
    write_run_log( validate_results.out.structure_id.collect() )

    // Aggregate run summary into RUN_SUMMARY.md at workflow root (FINAL STEP)
    aggregate_run_summary( write_run_log.out.log_complete )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
