#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * INTEGRATOR PIPELINE: AMBIGUOUS_NODES_X_ANNOGROUPS
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow that COLLAPSES the annogroups species-tree
 * deconvolution down to ONLY the AMBIGUOUS NODES (clades present in some but not
 * all species-tree structures), in three structure scopes (one / some / all),
 * for each annotation source (pfam, go, panther).
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly under OUTPUT_pipeline/.
 * - Each script loops over the resolved annotation sources internally (the
 *   source dial lives in START_HERE-user_config.yaml: "all" or an explicit
 *   subset), so there is no per-source NextFlow fan-out — a few singletons.
 * - This is a PURE COLUMN PROJECTION of annogroups' own deconvolution; no count
 *   is recomputed (Rule 6). It introduces no new biology.
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow dir).
 *
 * Pipeline:
 *   001 resolve_ambiguous_nodes  -> 1-output (ambiguous-node registry + structure sets)
 *   002 project_annogroups       -> 2-output (projected annogroup x ambiguous-node tables, per scope)
 *   003 validate_results         -> 3-output (fail-fast, §36)
 *   004 write_run_log            -> ai/logs (§45)
 *
 * AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC integrator - ambiguous_nodes_X_annogroups
    ==============================================================================

    Usage:
        nextflow run main.nf -params-file ../START_HERE-user_config.yaml

    All configuration is read from START_HERE-user_config.yaml:
      - run_label, species_set_name, annotation_sources
      - inputs.annogroups_dir
      - structure_scopes.{all, one, some}
      - output.base_dir
    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// PROCESS 001: RESOLVE AMBIGUOUS NODES + STRUCTURE SCOPES
// ============================================================================
// Reads the deconvolution headers (no data rows); writes, per source, the
// ambiguous-node registry and the resolved one/some/all structure sets.

process resolve_ambiguous_nodes {
    label 'local'

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-resolve_ambiguous_nodes.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: PROJECT ANNOGROUPS ONTO AMBIGUOUS-NODE COLUMNS (per scope)
// ============================================================================

process project_annogroups {
    label 'local'

    input:
        val resolve_ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-project_annogroups_to_ambiguous_nodes.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 003: VALIDATE RESULTS (fail-fast per §36)
// ============================================================================

process validate_results {
    label 'local'

    input:
        val project_done

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-validate_results.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 004: WRITE RUN LOG (per §45)
// ============================================================================

process write_run_log {
    label 'local'

    input:
        val validate_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-write_run_log.py \\
        --workflow-name "ambiguous_nodes_X_annogroups" \\
        --subproject-name "integrator-BLOCK_ambiguous_nodes_X_annogroups" \\
        --project-name "${params.species_set_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    resolve_ambiguous_nodes()
    project_annogroups( resolve_ambiguous_nodes.out.ready )
    validate_results( project_annogroups.out.done )
    write_run_log( validate_results.out.done )
}

// Completion summary handled by RUN-workflow.sh (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
