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
//   - orthofinder/output_to_input/
//   - orthohmm/output_to_input/
//   - broccoli/output_to_input/
//
// Final step copies comparison results to output_to_input/ for downstream use
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

process copy_to_output_to_input {
    publishDir "${projectDir}/OUTPUT_to_input", mode: 'copy', overwrite: true
    publishDir "${projectDir}/../../output_to_input", mode: 'copy', overwrite: true

    input:
        path method_comparison
        path gene_overlap
        path size_comparison

    output:
        path 'method_comparison_summary.tsv'
        path 'gene_overlap_between_methods.tsv'
        path 'orthogroup_size_comparison.tsv'

    script:
    """
    cp ${method_comparison} method_comparison_summary.tsv
    cp ${gene_overlap} gene_overlap_between_methods.tsv
    cp ${size_comparison} orthogroup_size_comparison.tsv
    """
}

workflow {
    load_tool_results(
        params.orthofinder_dir,
        params.orthohmm_dir,
        params.broccoli_dir
    )
    compare_methods( load_tool_results.out.tool_orthogroups_dir )
    copy_to_output_to_input(
        compare_methods.out.method_comparison,
        compare_methods.out.gene_overlap,
        compare_methods.out.size_comparison
    )
}
