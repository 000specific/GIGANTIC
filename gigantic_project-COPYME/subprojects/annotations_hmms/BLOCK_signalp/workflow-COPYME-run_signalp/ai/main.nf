#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Nextflow pipeline for SignalP signal peptide prediction
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// SignalP Signal Peptide Prediction Pipeline
// =============================================================================
//
// Three-step pipeline:
//   0. Preprocess proteomes - filter out records whose FASTA header line exceeds
//      a filesystem-safe length (default 253 chars). Avoids SignalP6's
//      "File name too long" failure when per-protein output filenames would
//      exceed the 255-byte Linux limit (e.g., for EvidentialGene multi-locus
//      concatenated identifiers).
//   1. Validate the FILTERED proteome manifest (paths exist, FASTA parseable).
//   2. Run SignalP 6 signal peptide prediction on each (filtered) species
//      proteome - per-species sub-jobs via the SLURM executor.
//
// Symlinks for output_to_input/BLOCK_signalp/ are created by RUN-workflow.sh
// after pipeline completes.
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
        --max-header-length ${params.max_header_length ?: 253}
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

process run_signalp {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        tuple val( species_name ), val( proteome_path ), val( phyloname )

    output:
        // Emit the full tuple including the raw output dir so the downstream
        // consolidate process gets proteome_path + phyloname + raw_dir in one
        // tuple ( no manual channel-joining needed ).
        tuple val( species_name ), val( proteome_path ), val( phyloname ), path( "signalp_raw_output_${phyloname}" ), emit: signalp_raw_full
        path "2_ai-log-run_signalp_${phyloname}.log"

    script:
    """
    bash ${scripts_dir}/002_ai-bash-run_signalp.sh \
        --input-fasta ${proteome_path} \
        --output-dir . \
        --phyloname ${phyloname} \
        --organism-type ${params.organism_type} \
        --mode ${params.mode}
    """
}

/*
 * Process 3: Consolidate raw outputs into one descriptive-header TSV per species
 * Calls: scripts/003_ai-python-consolidate_signalp_outputs.py
 *
 * Reads the canonical proteome FASTA plus the per-species signalp raw dir
 * ( containing prediction_results.txt ) and writes a mode-tagged file:
 *     <phyloname>_signalp_FAST_predictions.tsv   ( when params.mode == 'fast' )
 *     <phyloname>_signalp_SLOW_predictions.tsv   ( when params.mode == 'slow' )
 * GIGANTIC self-documenting header schema:
 *     Protein_Identifier, Sequence_Length, Signal_Peptide_Call,
 *     Signal_Peptide_Start, Signal_Peptide_End, OTHER_Probability,
 *     SP_Probability, LIPO_Probability, TAT_Probability,
 *     Cleavage_Site_String
 * SignalP6 Prediction = OTHER -> Signal_Peptide_Call = None ( probabilities
 * still kept ). Proteins not annotated by SignalP6 -> all values None.
 */
process consolidate_signalp_outputs {
    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        tuple val( species_name ), val( proteome_path ), val( phyloname ), path( signalp_raw_dir )

    output:
        path "${phyloname}_signalp_*_predictions.tsv", emit: consolidated_tsv
        path "3_ai-log-consolidate_signalp_outputs_${phyloname}.log"

    script:
    """
    python3 ${scripts_dir}/003_ai-python-consolidate_signalp_outputs.py \
        --input-fasta ${proteome_path} \
        --raw-output-dir ${signalp_raw_dir} \
        --output-dir . \
        --phyloname ${phyloname} \
        --mode ${params.mode}
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
        --workflow-name "run_signalp" \
        --subproject-name "annotations_hmms" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/BLOCK_signalp/ are created by
// RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    // Step 0: Filter proteome FASTAs - drop records with overlong header lines.
    // Emits a NEW manifest pointing at filtered local copies (absolute paths).
    preprocess_proteomes_filter_long_headers( params.proteome_manifest )

    // Step 1: Validate the FILTERED manifest (not the original user manifest).
    validate_proteome_manifest( preprocess_proteomes_filter_long_headers.out.filtered_manifest )

    // Step 2: Parse validated manifest into per-species channel, then run SignalP
    // Validated manifest columns (tab-separated):
    //   [0] Species_Name  [1] Proteome_Path  [2] Phyloname  [3] Sequence_Count
    // Skip header line, split by tab, map to tuple for parallel processing
    validated_channel = validate_proteome_manifest.out.validated_manifest
        .splitCsv( sep: '\t', skip: 1 )
        .map { row -> tuple( row[ 0 ], row[ 1 ], row[ 2 ] ) }

    run_signalp( validated_channel )

    // Step 3: Consolidate raw outputs into one descriptive-header TSV per species
    consolidate_signalp_outputs( run_signalp.out.signalp_raw_full )

    // Step 4: Write run log (FINAL STEP)
    write_run_log( consolidate_signalp_outputs.out.consolidated_tsv.collect() )
}
