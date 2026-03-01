#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Nextflow pipeline for cross-method orthogroup comparison
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// Cross-Method Orthogroup Comparison Pipeline
// =============================================================================
//
// Two-step pipeline:
//   1. Load standardized results from each tool's output_to_input/
//   2. Compare orthogroup methods (overlap, statistics, size distributions)
//
// Reads from:
//   - BLOCK_orthofinder/output_to_input/
//   - BLOCK_orthohmm/output_to_input/
//   - BLOCK_broccoli/output_to_input/
//
// Symlinks for output_to_input/ are created by RUN-workflow.sh after pipeline completes
// =============================================================================

scripts_dir = "${projectDir}/scripts"

process load_tool_results {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        val orthofinder_dir
        val orthohmm_dir
        val broccoli_dir

    output:
        path '1_ai-loaded_tool_results_summary.tsv', emit: results_summary
        path 'tool_orthogroups/', emit: tool_orthogroups_dir
        path '1_ai-log-load_tool_results.log'

    script:
    """
    python3 ${scripts_dir}/001_ai-python-load_tool_results.py \
        --orthofinder-dir ${orthofinder_dir} \
        --orthohmm-dir ${orthohmm_dir} \
        --broccoli-dir ${broccoli_dir} \
        --output-dir .
    """
}

process compare_methods {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        path tool_orthogroups_dir

    output:
        path '2_ai-method_comparison_summary.tsv', emit: method_comparison
        path '2_ai-gene_overlap_between_methods.tsv', emit: gene_overlap
        path '2_ai-orthogroup_size_comparison.tsv', emit: size_comparison
        path '2_ai-log-compare_orthogroup_methods.log'

    script:
    """
    python3 ${scripts_dir}/002_ai-python-compare_orthogroup_methods.py \
        --tool-results-dir ${tool_orthogroups_dir} \
        --output-dir .
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/ and ai/output_to_input/ are created
// by RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    load_tool_results(
        params.orthofinder_dir,
        params.orthohmm_dir,
        params.broccoli_dir
    )
    compare_methods( load_tool_results.out.tool_orthogroups_dir )
}
