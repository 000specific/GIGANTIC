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
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

// Default parameter values (overridden by nextflow.config which loads from YAML)
params.step2_proteomes = "../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned"
params.step3_blastp = "../../output_to_input/STEP_3-databases/gigantic-T1-blastp"
params.step2_genome_annotations = "../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_genome_annotations"
params.selected_species = "INPUT_user/selected_species.txt"
params.output_dir = "OUTPUT_pipeline"
// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate Species Selection
 * Calls: scripts/001_ai-python-validate_species_selection.py
 */
process validate_species_selection {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-validated_species_list.txt", emit: validated_list
        path "1-output/1_ai-species_count.txt", emit: species_count
        path "1-output/1_ai-species_with_genome_annotations.txt", emit: species_with_annotations
        path "1-output/1_ai-log-validate_species_selection.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_species_selection.py \\
        --step2-proteomes ${projectDir}/../${params.step2_proteomes} \\
        --step3-blastp ${projectDir}/../${params.step3_blastp} \\
        --step2-genome-annotations ${projectDir}/../${params.step2_genome_annotations} \\
        --selected-species ${projectDir}/../${params.selected_species} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Copy Selected Files
 * Calls: scripts/002_ai-python-copy_selected_files.py
 */
process copy_selected_files {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

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
        --step2-proteomes ${projectDir}/../${params.step2_proteomes} \\
        --step3-blastp ${projectDir}/../${params.step3_blastp} \\
        --step2-genome-annotations ${projectDir}/../${params.step2_genome_annotations} \\
        --output-dir 2-output
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
        --workflow-name "create_final_species_set" \
        --subproject-name "genomesDB" \
        --project-name "${params.project_name}" \
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

    // Write run log (FINAL STEP)
    write_run_log( copy_selected_files.out.manifest )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC genomesDB STEP_4 Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Validated species list, count, and annotation availability"
        println "  2-output/: Final species set directories"
        println ""
        println "Symlinks created in output_to_input/ (by RUN-workflow.sh)"
        println "  speciesN_gigantic_T1_proteomes/       -> OUTPUT_pipeline/2-output/"
        println "  speciesN_gigantic_T1_blastp/           -> OUTPUT_pipeline/2-output/"
        println "  speciesN_gigantic_genome_annotations/    -> OUTPUT_pipeline/2-output/"
        println "Run log written to ai/logs/ in this workflow directory"
    }
    println "========================================================================"
}
