#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * INTEGRATOR PIPELINE: ORTHOGROUPS_OCL_X_FEATURES
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow that integrates OCL orthogroup analysis (per
 * phylogenetic species-tree structure) with three per-gene feature sources:
 * dark proteome, hotspots, secretome.
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly under OUTPUT_pipeline/
 * - A single structure-invariant gene->feature lookup is built ONCE
 *   (build_feature_lookup), then every per-structure task reads it.
 * - NextFlow passes only val structure_id between per-structure processes.
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow dir).
 *
 * AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC integrator - orthogroups_ocl_X_features
    ==============================================================================

    Usage:
        nextflow run main.nf -params-file ../START_HERE-user_config.yaml

    All configuration is read from START_HERE-user_config.yaml:
      - run_label, species_set_name
      - inputs.{ocl_orthogroups_dir, dark_proteome_dir, hotspots_dir,
                secretome_filtered_dir, secretome_evidence_dir,
                structure_manifest}
      - output.base_dir
    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// INPUT CHANNEL — structure IDs from manifest
// ============================================================================
// projectDir is ai/; the workflow root is one level up.

Channel
    .fromPath( "${projectDir}/../${params.inputs.structure_manifest}" )
    .splitCsv( header: true, sep: '\t' )
    .map { row -> row.structure_id }
    .set { structure_ids_channel }

// ============================================================================
// PROCESS 001: BUILD FEATURE LOOKUP (singleton, structure-invariant)
// ============================================================================
// Orthogroup membership and per-gene features do not change with tree
// structure, so the gene->feature lookup is built ONCE and reused by every
// per-structure task. Writes OUTPUT_pipeline/_shared/1-output/.

process build_feature_lookup {
    label 'local'

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-build_feature_lookup.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: BUILD INTEGRATED ORTHOGROUP SUMMARY (per structure) — Table 1
// ============================================================================

process build_integrated_summary {
    tag "structure_${structure_id}"

    input:
        val structure_id
        val lookup_ready

    output:
        val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-build_integrated_summary.py \\
        --structure_id ${structure_id} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 003: BUILD BLOCK-STATE EXPANDED TABLE (per structure) — Table 2
// ============================================================================

process build_block_state_expanded {
    tag "structure_${structure_id}"

    input:
        val structure_id

    output:
        val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-build_block_state_expanded.py \\
        --structure_id ${structure_id} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 004: BUILD GENE-LEVEL DRILL-DOWN TABLE (per structure) — Table 3
// ============================================================================

process build_gene_drilldown {
    tag "structure_${structure_id}"

    input:
        val structure_id

    output:
        val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-build_gene_drilldown.py \\
        --structure_id ${structure_id} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 005: VALIDATE RESULTS (per structure, fail-fast per §36)
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
// PROCESS 006: WRITE RUN LOG (per §45)
// ============================================================================

process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/006_ai-python-write_run_log.py \\
        --workflow-name "orthogroups_ocl_X_features" \\
        --subproject-name "integrator-BLOCK_orthogroups_ocl_X_features" \\
        --project-name "${params.species_set_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Build the structure-invariant feature lookup once.
    build_feature_lookup()

    // Value channel so the single readiness signal broadcasts to every
    // per-structure task (each structure_id pairs with the same ready value).
    ready = build_feature_lookup.out.ready.first()

    // Per-structure chain (parallel across structures, sequential per structure).
    build_integrated_summary( structure_ids_channel, ready )
    build_block_state_expanded( build_integrated_summary.out.structure_id )
    build_gene_drilldown( build_block_state_expanded.out.structure_id )

    // Barrier before validate_results: collect().flatten() forces every
    // upstream `val structure_id` emission to land before validation
    // dispatches (mirrors the orthogroups_X_ocl pattern that worked around a
    // channel-propagation issue leaving some structures unvalidated).
    validate_results( build_gene_drilldown.out.structure_id.collect().flatten() )

    // Write run log after all structures validate.
    write_run_log( validate_results.out.structure_id.collect() )
}

// Completion summary handled by RUN-workflow.sh (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
