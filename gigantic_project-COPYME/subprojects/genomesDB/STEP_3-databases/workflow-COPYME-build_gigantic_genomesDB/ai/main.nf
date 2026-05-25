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
// PARAMETERS (from config.yaml via nextflow.config + .params.json)
// ============================================================================
// All defaults live in nextflow.config; users edit START_HERE-user_config.yaml,
// not this file. Nested params (params.X.Y.Z) mirror the yaml shape.

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

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    // NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
    // pipeline completes. Real files only live in OUTPUT_pipeline/1-output/.

    output:
        path "1-output/${params.blast.database_name}", emit: blastdb_dir
        path "1-output/1_ai-makeblastdb_commands.sh", emit: commands_log
        path "1-output/1_ai-log-build_per_genome_blastdbs.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-build_per_genome_blastdbs.py \\
        --proteomes-dir ${projectDir}/../${params.inputs.proteomes_dir} \\
        --output-dir 1-output \\
        --database-name ${params.blast.database_name} \\
        --parallel ${params.blast.parallel_jobs}
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
        --project-name "${params.project.name}" \
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

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
