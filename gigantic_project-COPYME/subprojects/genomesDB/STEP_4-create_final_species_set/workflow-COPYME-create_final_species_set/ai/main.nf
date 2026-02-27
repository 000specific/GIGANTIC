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

params.step2_proteomes = "../STEP_2-standardize_and_evaluate/workflow-RUN_01-standardize_evaluate_build_gigantic_genomesdb/OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned"
params.step3_blastp = "../STEP_3-databases/workflow-RUN_01-build_gigantic_blastp_databases/OUTPUT_pipeline/1-output/gigantic_blastp"
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
        path "1-output/1_ai-log-validate_species_selection.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_species_selection.py \\
        --step2-proteomes ${projectDir}/../${params.step2_proteomes} \\
        --step3-blastp ${projectDir}/../${params.step3_blastp} \\
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

    // Also publish to output_to_input for downstream subprojects
    publishDir "${projectDir}/../../output_to_input", mode: 'copy', overwrite: true,
               saveAs: { filename ->
                   if (filename.contains('species') && filename.contains('gigantic_T1')) {
                       return filename.tokenize('/').last()
                   }
                   return null
               }

    input:
        path validated_list
        path species_count

    output:
        path "2-output/species*_gigantic_T1_proteomes", emit: proteomes_dir
        path "2-output/species*_gigantic_T1_blastp", emit: blastp_dir
        path "2-output/2_ai-copy_manifest.tsv", emit: manifest
        path "2-output/2_ai-log-copy_selected_files.log", emit: log

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-copy_selected_files.py \\
        --validated-species ${validated_list} \\
        --species-count ${species_count} \\
        --step2-proteomes ${projectDir}/../${params.step2_proteomes} \\
        --step3-blastp ${projectDir}/../${params.step3_blastp} \\
        --output-dir 2-output
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
        validate_species_selection.out.species_count
    )
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
        println "  1-output/: Validated species list and count"
        println "  2-output/: Final species set directories"
        println ""
        println "Final outputs copied to: ../../output_to_input/"
        println "  speciesN_gigantic_T1_proteomes/"
        println "  speciesN_gigantic_T1_blastp/"
    }
    println "========================================================================"
}
