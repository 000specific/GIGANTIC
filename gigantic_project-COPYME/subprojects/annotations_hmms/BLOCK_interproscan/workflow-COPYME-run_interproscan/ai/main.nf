#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Nextflow pipeline for InterProScan protein domain and function annotation with proteome chunking
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// InterProScan Protein Domain and Function Annotation Pipeline
// =============================================================================
//
// Four-step pipeline:
//   1. Validate proteome manifest and check all files exist
//   2. Chunk proteomes into smaller FASTA files for parallel InterProScan
//   3. Run InterProScan on each chunk (highly parallel across species and chunks)
//   4. Combine chunk results back into per-species annotation files
//
// This is the most complex annotation tool BLOCK because it includes proteome
// chunking for parallel processing. Large proteomes are split into configurable-
// size chunks (default 1000 sequences) before running InterProScan, then results
// are merged back per species.
//
// Symlinks for output_to_input/BLOCK_interproscan/ are created by RUN-workflow.sh after pipeline completes
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

process chunk_proteomes {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        tuple val( species_name ), val( proteome_path ), val( phyloname )

    output:
        tuple val( phyloname ), path( "${phyloname}_chunk_*.fasta" ), emit: chunks

    script:
    """
    python3 ${scripts_dir}/002_ai-python-chunk_proteomes.py \
        --input-fasta ${proteome_path} \
        --output-dir . \
        --phyloname ${phyloname} \
        --chunk-size ${params.chunk_size}
    """
}

process run_interproscan {
    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        tuple val( phyloname ), path( chunk_fasta )

    output:
        tuple val( phyloname ), path( "${chunk_fasta.baseName}_interproscan.tsv" ), emit: interproscan_results

    script:
    """
    bash ${scripts_dir}/003_ai-bash-run_interproscan.sh \
        --input-fasta ${chunk_fasta} \
        --output-dir . \
        --interproscan-path ${params.interproscan_install_path} \
        --cpus ${task.cpus} \
        --applications ${params.applications}
    """
}

process combine_interproscan_results {
    publishDir "${params.output_dir}/4-output", mode: 'copy'

    input:
        tuple val( phyloname ), path( result_files )

    output:
        path "${phyloname}_interproscan_results.tsv", emit: combined_results
        path "4_ai-log-combine_interproscan_results_${phyloname}.log"

    script:
    """
    python3 ${scripts_dir}/004_ai-python-combine_interproscan_results.py \
        --input-dir . \
        --output-dir . \
        --phyloname ${phyloname}
    """
}

/*
 * Process: detect_failed_chunks
 * Calls: scripts/006_ai-python-detect_failed_chunks.py
 *
 * Gap-detection step. With errorStrategy='ignore' on run_interproscan, failed
 * chunks produce no output rather than killing the pipeline. This step compares
 * expected chunks (2-output/*.fasta) against successful chunks
 * (3-output/*_interproscan.tsv) and emits a manifest of missing chunks the
 * user can drive a follow-up RUN_N from.
 *
 * Runs locally (no SLURM submission) -- pure filesystem walk.
 * Triggered by combine_interproscan_results so it runs AFTER all chunks
 * have had a chance to complete or fail.
 */
process detect_failed_chunks {
    label 'local'
    publishDir "${params.output_dir}/6-output", mode: 'copy'

    input:
        val previous_step_done

    output:
        path '6_ai-failed_chunks.tsv',          emit: failed_chunks_manifest
        path '6_ai-log-detect_failed_chunks.log'

    script:
    """
    python3 ${scripts_dir}/006_ai-python-detect_failed_chunks.py \
        --chunks-dir  ${projectDir}/../${params.output_dir}/2-output \
        --results-dir ${projectDir}/../${params.output_dir}/3-output \
        --output-dir  .
    """
}

/*
 * Process 5: Write Run Log
 * Calls: scripts/005_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \
        --workflow-name "run_interproscan" \
        --subproject-name "annotations_hmms" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/BLOCK_interproscan/ are created by
// RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    // Step 1: Validate proteome manifest
    validate_proteome_manifest( params.proteome_manifest )

    // Step 2: Parse validated manifest into per-species channel, then chunk proteomes
    // Validated manifest columns (tab-separated):
    //   [0] Species_Name  [1] Proteome_Path  [2] Phyloname  [3] Sequence_Count
    // Skip header line, split by tab, map to tuple for parallel processing
    validated_channel = validate_proteome_manifest.out.validated_manifest
        .splitCsv( sep: '\t', skip: 1 )
        .map { row -> tuple( row[ 0 ], row[ 1 ], row[ 2 ] ) }

    chunk_proteomes( validated_channel )

    // Step 3: Run InterProScan on each chunk
    // transpose() flattens the list of chunk files per species so that each
    // individual chunk becomes its own tuple: [phyloname, chunk_file]
    // This enables maximum parallelism - each chunk runs independently
    run_interproscan( chunk_proteomes.out.chunks.transpose() )

    // Step 4: Combine chunk results back per species
    // groupTuple() collects all InterProScan result files for each phyloname
    // into a single tuple: [phyloname, [result_1.tsv, result_2.tsv, ...]]
    // NOTE: With errorStrategy='ignore' on run_interproscan, groupTuple
    // receives only SUCCESSFUL chunks; failed chunks are silently dropped.
    // Step 5 below detects which chunks were dropped.
    combine_interproscan_results( run_interproscan.out.interproscan_results.groupTuple() )

    // Step 5: Detect failed chunks (gap detection)
    // Compares 2-output/*.fasta (expected) vs 3-output/*_interproscan.tsv
    // (successful) and writes 6-output/6_ai-failed_chunks.tsv for follow-up runs.
    detect_failed_chunks( combine_interproscan_results.out.combined_results.collect() )

    // Write run log (FINAL STEP) -- waits on the gap-detection manifest
    write_run_log( detect_failed_chunks.out.failed_chunks_manifest.collect() )
}
