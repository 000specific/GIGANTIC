#!/usr/bin/env nextflow
/*
 * GIGANTIC genomesDB STEP_4 - Create Final Species Set Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 February 27
 * Human: Eric Edsinger
 *
 * Purpose: Copy user-selected species from STEP_2 and STEP_3 to output_to_input/
 *          with proper speciesN_ naming convention for downstream subprojects
 *
 * Scripts:
 *   001: Validate species selection against STEP_2 and STEP_3 outputs
 *   002: Copy selected proteomes and blastp databases with speciesN naming
 *   003: Build per-species (Phyloname, GIGANTIC ID, Length, Sequence) TSV
 *        tables from the T1 proteome FASTAs (added 2026 June 27)
 *   004: Write workflow run log to ai/logs/
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config + .params.json)
// ============================================================================
// All defaults live in nextflow.config; users edit START_HERE-user_config.yaml,
// not this file. Nested params (params.X.Y.Z) mirror the yaml shape.

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate Species Selection
 * Calls: scripts/001_ai-python-validate_species_selection.py
 */
process validate_species_selection {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-validated_species_list.txt", emit: validated_list
        path "1-output/1_ai-species_count.txt", emit: species_count
        path "1-output/1_ai-species_with_genome_annotations.txt", emit: species_with_annotations
        path "1-output/1_ai-log-validate_species_selection.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_species_selection.py \\
        --step2-proteomes ${projectDir}/../${params.inputs.step2_proteomes} \\
        --step3-blastp ${projectDir}/../${params.inputs.step3_blastp} \\
        --step2-genome-annotations ${projectDir}/../${params.inputs.step2_genome_annotations} \\
        --selected-species ${projectDir}/../${params.inputs.selected_species} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Copy Selected Files
 * Calls: scripts/002_ai-python-copy_selected_files.py
 */
process copy_selected_files {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    // NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
    // pipeline completes. Real files only live in OUTPUT_pipeline/N-output/.

    input:
        path validated_list
        path species_count
        path species_with_annotations

    output:
        path "2-output/species*_gigantic_T1_proteomes", emit: proteomes_dir
        path "2-output/species*_gigantic_T1_blastp", emit: blastp_dir
        path "2-output/species*_gigantic_genome_annotations", emit: genome_annotations_dir
        path "2-output/2_ai-copy_manifest.tsv", emit: manifest
        path "2-output/2_ai-log-copy_selected_files.log", emit: log

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-copy_selected_files.py \\
        --validated-species ${validated_list} \\
        --species-count ${species_count} \\
        --species-with-annotations ${species_with_annotations} \\
        --step2-proteomes ${projectDir}/../${params.inputs.step2_proteomes} \\
        --step3-blastp ${projectDir}/../${params.inputs.step3_blastp} \\
        --step2-genome-annotations ${projectDir}/../${params.inputs.step2_genome_annotations} \\
        --output-dir 2-output
    """
}

/*
 * Process 3: Build Per-Species Sequence Tables
 * Calls: scripts/003_ai-python-build_per_species_sequence_tables.py
 *
 * For every <phyloname>-T1-proteome.aa in the proteomes dir produced by
 * Process 2, emits <phyloname>-T1-proteome-sequence_table.tsv (columns:
 * Phyloname | Gigantic_Protein_Identifier | Sequence_Length | Protein_Sequence)
 * into a clean named resource subdir 3-output/<species_set>_gigantic_T1_sequence_tables/
 * (mirrors the sibling proteomes resource dir; exposed via output_to_input by
 * RUN-workflow.sh, per conventions §2). Also emits a per-species protein-count
 * summary and a build log at the 3-output root.
 */
process build_per_species_sequence_tables {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path proteomes_dir

    output:
        path "3-output/*_gigantic_T1_sequence_tables", emit: sequence_tables
        path "3-output/3_ai-summary.tsv", emit: summary
        path "3-output/3_ai-log-build_per_species_sequence_tables.log", emit: log

    script:
    """
    mkdir -p 3-output

    python3 ${projectDir}/scripts/003_ai-python-build_per_species_sequence_tables.py \\
        --proteomes-dir ${proteomes_dir} \\
        --output-dir 3-output
    """
}

/*
 * Process 4: Write Run Log
 * Calls: scripts/004_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/004_ai-python-write_run_log.py \
        --workflow-name "create_final_species_set" \
        --subproject-name "genomesDB" \
        --project-name "${params.project.name}" \
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Validate species selection
    validate_species_selection()

    // Step 2: Copy selected files with speciesN naming
    copy_selected_files(
        validate_species_selection.out.validated_list,
        validate_species_selection.out.species_count,
        validate_species_selection.out.species_with_annotations
    )

    // Step 3: Build per-species (Phyloname, ID, Length, Sequence) TSV tables
    build_per_species_sequence_tables( copy_selected_files.out.proteomes_dir )

    // Write run log (FINAL STEP) — triggered by sequence-tables summary
    write_run_log( build_per_species_sequence_tables.out.summary )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
