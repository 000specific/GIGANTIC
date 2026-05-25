#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * PARSIMONY TREE STRUCTURES — BLOCK_ocl_orthogroups
 * Score species tree structures by parsimony of orthogroup OCL data.
 * ==============================================================================
 *
 * Design: Linear 7-step pipeline. Each script reads/writes directly to
 * OUTPUT_pipeline/N-output/. NextFlow passes only a `val ready` signal between
 * processes for sequencing.
 *
 * Why no fan-out across structures: each script's per-structure work is a
 * single small read + sum, so the entire manifest is processed in one Python
 * pass per script. SLURM submission overhead would dominate any benefit from
 * fan-out at this scale.
 *
 * AI: Claude Code | Opus 4.7 | 2026 May 11
 * Human: Eric Edsinger
 * ==============================================================================
 */

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config + -params-file)
// ============================================================================
// All defaults live in nextflow.config; users edit START_HERE-user_config.yaml,
// not this file. Nested params (params.X.Y.Z) mirror the yaml shape.

params.help = false

if ( params.help ) {
    log.info """
    ==============================================================================
    parsimony_tree_structures — BLOCK_ocl_orthogroups
    ==============================================================================

    Usage:
        nextflow run main.nf [options]

    Options:
        --config   Path to START_HERE-user_config.yaml
                   (default: ../START_HERE-user_config.yaml)
        --help     Show this help message

    Configuration lives in START_HERE-user_config.yaml.
    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// PROCESSES
// ============================================================================

process validate_inputs {
    input:
        val start_signal

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-validate_inputs.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process aggregate_ocl_per_structure {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-aggregate_ocl_per_structure.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process compute_parsimony_scores {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-compute_parsimony_scores.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process bootstrap_ranking_confidence {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-bootstrap_ranking_confidence.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process rank_structures_and_summarize {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-rank_structures_and_summarize.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process visualize_ranking {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/006_ai-python-visualize_ranking.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process diagnose_criteria_divergence {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/008_ai-python-diagnose_criteria_divergence.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process clade_binarized_parsimony {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/010_ai-python-clade_binarized_parsimony.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process clade_binarized_parsimony_subsampled {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/011_ai-python-clade_binarized_parsimony-subsampled_metazoans.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

process write_run_log {
    input:
        val ready

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/007_ai-python-write_run_log.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --workflow_dir ${projectDir}/..
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    start = Channel.of( true )

    validate_inputs( start )
    aggregate_ocl_per_structure( validate_inputs.out.ready )
    compute_parsimony_scores( aggregate_ocl_per_structure.out.ready )
    bootstrap_ranking_confidence( compute_parsimony_scores.out.ready )
    rank_structures_and_summarize( bootstrap_ranking_confidence.out.ready )
    visualize_ranking( rank_structures_and_summarize.out.ready )
    diagnose_criteria_divergence( visualize_ranking.out.ready )
    clade_binarized_parsimony( diagnose_criteria_divergence.out.ready )
    clade_binarized_parsimony_subsampled( clade_binarized_parsimony.out.ready )
    write_run_log( clade_binarized_parsimony_subsampled.out.ready )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
