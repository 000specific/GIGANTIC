#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Nextflow pipeline for MetaPredict disorder prediction
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// MetaPredict Disorder Prediction Pipeline
// =============================================================================
//
// Two-step pipeline:
//   1. Validate proteome manifest and check all files exist
//   2. Run MetaPredict disorder prediction on each species proteome (parallel)
//
// Symlinks for output_to_input/BLOCK_metapredict/ are created by RUN-workflow.sh after pipeline completes
// =============================================================================

// Script directory
scripts_dir = "${projectDir}/scripts"

process validate_proteome_manifest {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        val manifest_path

    output:
        path '1_ai-validated_manifest.tsv', emit: validated_manifest
        path '1_ai-log-validate_proteome_manifest.log'

    script:
    """
    python3 ${scripts_dir}/001_ai-python-validate_proteome_manifest.py \
        --manifest-path ${manifest_path} \
        --output-dir .
    """
}

process run_metapredict {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        tuple val( species_name ), val( proteome_path ), val( phyloname )

    output:
        path "${phyloname}_metapredict_disorder.tsv", emit: disorder_results
        path "${phyloname}_metapredict_idrs.tsv", emit: idr_results
        path "2_ai-log-run_metapredict_${phyloname}.log"

    script:
    """
    bash ${scripts_dir}/002_ai-bash-run_metapredict.sh \
        --input-fasta ${proteome_path} \
        --output-dir . \
        --phyloname ${phyloname} \
        --prediction-types ${params.prediction_types}
    """
}

/*
 * Process 3: Write Run Log
 * Calls: scripts/003_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/003_ai-python-write_run_log.py \
        --workflow-name "run_metapredict" \
        --subproject-name "annotations_hmms" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/BLOCK_metapredict/ are created by
// RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    // Step 1: Validate proteome manifest
    validate_proteome_manifest( params.proteome_manifest )

    // Step 2: Parse validated manifest into per-species channel, then run MetaPredict
    // Validated manifest columns (tab-separated):
    //   [0] Species_Name  [1] Proteome_Path  [2] Phyloname  [3] Sequence_Count
    // Skip header line, split by tab, map to tuple for parallel processing
    validated_channel = validate_proteome_manifest.out.validated_manifest
        .splitCsv( sep: '\t', skip: 1 )
        .map { row -> tuple( row[ 0 ], row[ 1 ], row[ 2 ] ) }

    run_metapredict( validated_channel )

    // Write run log (FINAL STEP)
    write_run_log( run_metapredict.out.disorder_results.collect() )
}
