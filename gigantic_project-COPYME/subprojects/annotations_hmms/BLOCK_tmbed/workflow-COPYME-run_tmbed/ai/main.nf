#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Nextflow pipeline for TMbed transmembrane topology prediction
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// TMbed Transmembrane Topology Prediction Pipeline
// =============================================================================
//
// Three-step pipeline:
//   0. Preprocess proteomes - filter out FASTA records whose header line exceeds
//      a filesystem-safe length (default 239 chars). Avoids OSError [Errno 36]
//      "File name too long" on EvidentialGene multi-locus concatenated
//      identifiers (e.g., Sphaeroforma_arctica).
//   1. Validate the FILTERED proteome manifest (paths exist, FASTA parseable).
//   2. Run TMbed transmembrane topology prediction on each (filtered) species
//      proteome.
//
// TMbed predicts transmembrane topology using protein language models.
// Output is in 3-line format per protein:
//   >protein_id
//   SEQUENCE...
//   ....HHHHHHHHHH....  (topology string)
//
// Where: H/h = TM helix, B/b = beta barrel, S = signal peptide, . = other
//
// Symlinks for output_to_input/BLOCK_tmbed/ are created by RUN-workflow.sh after pipeline completes
// =============================================================================

// Script directory
scripts_dir = "${projectDir}/scripts"

process preprocess_proteomes_filter_long_headers {
    publishDir "${params.output_dir}/0-output", mode: 'copy'

    input:
        val input_manifest_path

    output:
        path '0_ai-filtered_proteome_manifest.tsv', emit: filtered_manifest
        path '0_ai-log-filter_proteome_long_headers.log'
        path 'filtered_proteomes/**'

    script:
    """
    python3 ${scripts_dir}/000_ai-python-filter_proteome_long_headers.py \
        --input-manifest ${input_manifest_path} \
        --output-dir . \
        --max-header-length ${params.max_header_length ?: 239}
    """
}

process validate_proteome_manifest {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        path manifest_path

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
        // Emit the full tuple including the .3line so the downstream
        // consolidate process gets proteome_path + phyloname + .3line path
        // in one tuple ( no manual channel-joining needed ).
        tuple val( species_name ), val( proteome_path ), val( phyloname ), path( "${phyloname}_tmbed_predictions.3line" ), emit: tmbed_results_full
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

/*
 * Process 3: Consolidate raw .3line output into one descriptive-header TSV per species
 * Calls: scripts/003_ai-python-consolidate_tmbed_outputs.py
 *
 * Reads the canonical proteome FASTA plus the per-species .3line file and
 * writes:
 *     <phyloname>_tmbed_predictions.tsv
 * with the GIGANTIC self-documenting header schema:
 *     Protein_Identifier, Sequence_Length,
 *     TM_Helix_Count, TM_Helix_Identifiers, TM_Helix_Starts, TM_Helix_Ends,
 *     Beta_Barrel_Count, Beta_Barrel_Identifiers, Beta_Barrel_Starts, Beta_Barrel_Ends,
 *     Signal_Peptide_Count, Signal_Peptide_Identifiers, Signal_Peptide_Starts, Signal_Peptide_Ends
 * Per-RUN scope: only consolidates proteins this RUN processed. Cross-RUN
 * union ( RUN_1 + RUN_2 short + RUN_3 long ) is a separate later step.
 */
process consolidate_tmbed_outputs {
    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        tuple val( species_name ), val( proteome_path ), val( phyloname ), path( tmbed_3line_file )

    output:
        path "${phyloname}_tmbed_predictions.tsv", emit: consolidated_tsv
        path "3_ai-log-consolidate_tmbed_outputs_${phyloname}.log"

    script:
    """
    python3 ${scripts_dir}/003_ai-python-consolidate_tmbed_outputs.py \
        --input-fasta ${proteome_path} \
        --input-3line ${tmbed_3line_file} \
        --output-dir . \
        --phyloname ${phyloname}
    """
}

/*
 * Process 4: Write Run Log ( renamed from 003 → 004 on 2026-05-23 to make
 * room for the new consolidate step at 003 )
 * Calls: scripts/004_ai-python-write_run_log.py
 */
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-write_run_log.py \
        --workflow-name "run_tmbed" \
        --subproject-name "annotations_hmms" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/BLOCK_tmbed/ are created by
// RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    // Step 0: Filter proteome FASTAs - drop records with overlong header lines.
    // Emits a NEW manifest pointing at filtered local copies (absolute paths).
    preprocess_proteomes_filter_long_headers( params.proteome_manifest )

    // Step 1: Validate the FILTERED manifest (not the original user manifest).
    validate_proteome_manifest( preprocess_proteomes_filter_long_headers.out.filtered_manifest )

    // Step 2: Parse validated manifest into per-species channel, then run TMbed
    validated_channel = validate_proteome_manifest.out.validated_manifest
        .splitCsv( sep: '\t', skip: 1 )
        .map { row -> tuple( row[ 0 ], row[ 1 ], row[ 2 ] ) }

    run_tmbed( validated_channel )

    // Step 3: Consolidate raw .3line output into one descriptive-header TSV per species
    consolidate_tmbed_outputs( run_tmbed.out.tmbed_results_full )

    // Step 4: Write run log (FINAL STEP)
    write_run_log( consolidate_tmbed_outputs.out.consolidated_tsv.collect() )
}
