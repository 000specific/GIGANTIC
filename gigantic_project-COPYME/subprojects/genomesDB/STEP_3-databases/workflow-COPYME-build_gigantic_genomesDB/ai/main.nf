#!/usr/bin/env nextflow
/*
 * GIGANTIC genomesDB STEP_3 - Build BLAST Databases
 * AI: Claude Code | Opus 4.6 | 2026 March 06
 * Human: Eric Edsinger
 *
 * Purpose: Build per-genome BLAST protein databases for all species from STEP_2
 *
 * Scripts:
 *   001: Build per-genome BLAST databases (all proteomes from STEP_2)
 *   002: Write run log
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from nextflow.config which reads START_HERE-user_config.yaml)
// ============================================================================

params.proteomes_dir = "../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned"
params.output_dir = "OUTPUT_pipeline"
params.database_name = "gigantic-T1-blastp"
params.parallel_jobs = 4

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Build Per-Genome BLAST Databases
 * Calls: scripts/001_ai-python-build_per_genome_blastdbs.py
 *
 * Builds a BLAST database for every .aa proteome file in the STEP_2
 * cleaned proteomes directory. No filtering - all species get databases.
 */
process build_blast_databases {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    // NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
    // pipeline completes. Real files only live in OUTPUT_pipeline/1-output/.

    output:
        path "1-output/${params.database_name}", emit: blastdb_dir
        path "1-output/1_ai-makeblastdb_commands.sh", emit: commands_log
        path "1-output/1_ai-log-build_per_genome_blastdbs.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-build_per_genome_blastdbs.py \\
        --proteomes-dir ${projectDir}/../${params.proteomes_dir} \\
        --output-dir 1-output \\
        --database-name ${params.database_name} \\
        --parallel ${params.parallel_jobs}
    """
}

/*
 * Process 2: Write Run Log
 * Calls: scripts/002_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/002_ai-python-write_run_log.py \
        --workflow-name "build_gigantic_genomesDB" \
        --subproject-name "genomesDB" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Build BLAST databases for all proteomes from STEP_2
    build_blast_databases()

    // Write run log (FINAL STEP)
    write_run_log( build_blast_databases.out.blastdb_dir )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC genomesDB STEP_3 Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Per-genome BLAST protein databases"
        println ""
        println "BLAST database symlinks created in output_to_input/ (by RUN-workflow.sh)"
        println ""
        println "To use with blastp:"
        println "  blastp -db OUTPUT_pipeline/1-output/${params.database_name}/PHYLONAME-proteome.aa -query sequences.fasta"
        println "Run log written to ai/logs/ in this workflow directory"
    }
    println "========================================================================"
}
