#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Nextflow pipeline for TMbed transmembrane topology prediction
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// TMbed Transmembrane Topology Prediction Pipeline
// =============================================================================
//
// Two-step pipeline:
//   1. Validate proteome manifest and check all files exist
//   2. Run TMbed transmembrane topology prediction on each species proteome (parallel)
//
// TMbed predicts transmembrane topology using protein language models.
// Output is in 3-line format per protein:
//   >protein_id
//   SEQUENCE...
//   ....HHHHHHHHHH....  (topology string)
//
// Where: H/h = TM helix, B/b = beta barrel, S = signal peptide, . = other
//
// Symlinks for output_to_input/ are created by RUN-workflow.sh after pipeline completes
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

process run_tmbed {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        tuple val( species_name ), val( proteome_path ), val( phyloname )

    output:
        path "${phyloname}_tmbed_predictions.3line", emit: tmbed_results
        path "2_ai-log-run_tmbed_${phyloname}.log"

    script:
    """
    bash ${scripts_dir}/002_ai-bash-run_tmbed.sh \
        --input-fasta ${proteome_path} \
        --output-dir . \
        --phyloname ${phyloname} \
        --batch-size ${params.batch_size} \
        --use-gpu ${params.use_gpu} \
        --cpu-fallback ${params.cpu_fallback}
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
    // Step 1: Validate proteome manifest
    validate_proteome_manifest( params.proteome_manifest )

    // Step 2: Parse validated manifest into per-species channel, then run TMbed
    // Validated manifest columns (tab-separated):
    //   [0] Species_Name  [1] Proteome_Path  [2] Phyloname  [3] Sequence_Count
    // Skip header line, split by tab, map to tuple for parallel processing
    validated_channel = validate_proteome_manifest.out.validated_manifest
        .splitCsv( sep: '\t', skip: 1 )
        .map { row -> tuple( row[ 0 ], row[ 1 ], row[ 2 ] ) }

    run_tmbed( validated_channel )
}
