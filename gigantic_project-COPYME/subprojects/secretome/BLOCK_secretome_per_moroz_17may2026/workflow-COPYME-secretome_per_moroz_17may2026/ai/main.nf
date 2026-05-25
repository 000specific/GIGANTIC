#!/usr/bin/env nextflow
/*
 * GIGANTIC secretome - BLOCK secretome_per_moroz_17may2026 Pipeline
 * AI: Claude Code | Opus 4.7 | 2026 May 21 | Purpose: secretome analysis per Moroz lab spec (2026-05-17)
 * Human: Eric Edsinger
 *
 * Purpose: TODO - fill in once scripts are specified.
 *
 * Scripts:
 *   TODO - list scripts and their interactions here once defined.
 *
 * Symlinks for output_to_input/BLOCK_secretome_per_moroz_17may2026/ are created
 * by RUN-workflow.sh AFTER this pipeline completes.
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (resolved from nextflow.config which reads START_HERE-user_config.yaml)
// ============================================================================

params.species70_phyloname_map  = ''
params.output_dir               = 'OUTPUT_pipeline'
params.project_name             = 'secretome'

// TODO: add additional input params here as upstream sources are wired in.

// ============================================================================
// VALIDATE REQUIRED INPUTS
// ============================================================================

if ( !params.species70_phyloname_map || !file( params.species70_phyloname_map ).exists() ) {
    error """
    ========================================================================
    CONFIGURATION ERROR: species70_phyloname_map not set or file missing.

    Set inputs.species70_phyloname_map in START_HERE-user_config.yaml to the
    canonical species70 mapping file (columns: genus_species | phyloname | phyloname_taxonid).
    ========================================================================
    """.stripIndent()
}

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * SKELETON PROCESS — replace with real processes once scripts are defined.
 *
 * Convention reminder:
 *   - publishDir to ${projectDir}/../${params.output_dir}
 *   - Numbered output directories: N-output/
 *   - Output filenames: N_ai-<details>.<ext>
 *   - Log filename:     N_ai-log-<details>.log
 *   - NO `optional: true` on outputs (fail-fast)
 *   - label 'local' for lightweight (1 cpu, 2 GB, 30m)
 *   - label 'heavy' / 'counting' / etc. for sized work (defined in nextflow.config)
 */
process placeholder_first_step {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-placeholder_skeleton.txt"
        path "1-output/1_ai-log-placeholder_skeleton.log"

    script:
    """
    mkdir -p 1-output
    echo "Skeleton placeholder — replace with real script invocation." > 1-output/1_ai-placeholder_skeleton.txt
    echo "Ran at: \$(date)" > 1-output/1_ai-log-placeholder_skeleton.log
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // TODO: replace the placeholder with the real pipeline DAG once scripts exist.
    placeholder_first_step()
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC secretome Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if ( workflow.success ) {
        println "Output files in ${params.output_dir}/"
        println ""
        println "Symlinks created in output_to_input/BLOCK_secretome_per_moroz_17may2026/ (by RUN-workflow.sh)"
    }
    println "========================================================================"
}
