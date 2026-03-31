#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: Nextflow pipeline for orthogroup clustering comparison
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// Orthogroup Clustering Comparison Pipeline
// =============================================================================
//
// Three-step pipeline:
//   1. Compare clustering runs - summary table (32 metrics, 7 sections)
//   2. Compare clustering runs - 5 visualization plots
//   3. Write run log
//
// Input: clustering_manifest.tsv in INPUT_user/
//   Each row points to one completed clustering run's OUTPUT_pipeline directory.
//
// Symlinks for output_to_input/ are created by RUN-workflow.sh after pipeline completes.
// =============================================================================

scripts_dir = "${projectDir}/scripts"

process compare_clustering_runs_table {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        val manifest_path

    output:
        path '1_ai-compare_clustering_runs.tsv', emit: comparison_table
        path '1_ai-per_species_copy_number_profiles.tsv'
        path '1_ai-pairwise_run_overlap.tsv'
        path '1_ai-log-compare_clustering_runs_table.log'

    script:
    """
    python3 ${scripts_dir}/001_ai-python-compare_clustering_runs_table.py \
        --manifest ${manifest_path} \
        --output-dir . \
        --overlap-sample-size ${params.overlap_sample_size}
    """
}

process compare_clustering_runs_visualization {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        val manifest_path
        val table_done

    output:
        path '2_ai-compare_clustering_runs-size_distribution.png'
        path '2_ai-compare_clustering_runs-summary_bar_chart.png'
        path '2_ai-compare_clustering_runs-single_copy_thresholds.png'
        path '2_ai-compare_clustering_runs-species_completeness.png'
        path '2_ai-compare_clustering_runs-taxonomic_breadth.png'

    script:
    """
    python3 ${scripts_dir}/002_ai-python-compare_clustering_runs_visualization.py \
        --manifest ${manifest_path} \
        --output-dir .
    """
}

process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-write_run_log.py \
        --workflow-name "compare_methods" \
        --subproject-name "orthogroups" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================

workflow {
    // Resolve manifest to absolute path so scripts can find relative paths
    manifest_absolute = file( params.manifest ).toAbsolutePath().toString()

    compare_clustering_runs_table( manifest_absolute )

    compare_clustering_runs_visualization(
        manifest_absolute,
        compare_clustering_runs_table.out.comparison_table
    )

    write_run_log( compare_clustering_runs_visualization.out )
}

workflow.onComplete {
    if ( workflow.success ) {
        log.info "Pipeline complete. Run log written to ai/logs/"
    }
}
