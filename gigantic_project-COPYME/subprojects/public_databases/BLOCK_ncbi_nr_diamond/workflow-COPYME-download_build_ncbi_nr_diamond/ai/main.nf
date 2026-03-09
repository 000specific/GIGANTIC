#!/usr/bin/env nextflow
/*
 * GIGANTIC Public Databases - NCBI nr DIAMOND Database Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 March 09
 * Human: Eric Edsinger
 *
 * Purpose: Download NCBI nr protein database and build DIAMOND search database
 *
 * Pipeline:
 *   001 - Download NCBI nr FASTA (nr.gz)
 *   002 - Build DIAMOND database (nr.dmnd)
 *   003 - Validate database integrity
 *   004 - Write timestamped run log
 *
 * Pattern: A (Sequential) - All processes run in one job
 * Typical runtime: 3-16 hours (download + build)
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from nextflow.config via START_HERE-user_config.yaml)
// ============================================================================

params.project_name = "my_project"
params.nr_url = "https://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz"
params.output_dir = "OUTPUT_pipeline"
params.diamond_threads = 15

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Download NCBI nr Protein Database
 * Calls: scripts/001_ai-bash-download_ncbi_nr.sh
 */
process download_ncbi_nr {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/nr.gz", emit: nr_fasta_gz

    script:
    """
    bash ${projectDir}/scripts/001_ai-bash-download_ncbi_nr.sh \
        --output-dir 1-output \
        --url "${params.nr_url}"
    """
}

/*
 * Process 2: Build DIAMOND Database
 * Calls: scripts/002_ai-bash-build_diamond_database.sh
 */
process build_diamond_database {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path nr_fasta_gz

    output:
        path "2-output/nr.dmnd", emit: diamond_database

    script:
    """
    bash ${projectDir}/scripts/002_ai-bash-build_diamond_database.sh \
        --input-file ${nr_fasta_gz} \
        --output-dir 2-output \
        --threads ${params.diamond_threads}
    """
}

/*
 * Process 3: Validate DIAMOND Database
 * Calls: scripts/003_ai-python-validate_database.py
 */
process validate_database {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path diamond_database

    output:
        path "3-output/validation_report.txt", emit: validation_report

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-validate_database.py \
        --database-path ${diamond_database} \
        --output-dir 3-output
    """
}

/*
 * Process 4: Write Run Log
 * Calls: scripts/004_ai-python-write_run_log.py
 */
process write_run_log {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path validation_report

    output:
        path "4-output/run_log.txt", emit: run_log

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-write_run_log.py \
        --validation-report ${validation_report} \
        --output-dir 4-output
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Download NCBI nr protein database
    download_ncbi_nr()

    // Step 2: Build DIAMOND database from nr.gz
    build_diamond_database( download_ncbi_nr.out.nr_fasta_gz )

    // Step 3: Validate database integrity
    validate_database( build_diamond_database.out.diamond_database )

    // Step 4: Write run log
    write_run_log( validate_database.out.validation_report )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Public Databases - NCBI nr DIAMOND Database Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files:"
        println "  - ${params.output_dir}/1-output/nr.gz (NCBI nr FASTA)"
        println "  - ${params.output_dir}/2-output/nr.dmnd (DIAMOND database)"
        println "  - ${params.output_dir}/3-output/validation_report.txt"
        println "  - ${params.output_dir}/4-output/run_log.txt"
        println ""
        println "Symlinks created in output_to_input/ (by RUN-workflow.sh)"
        println ""
        println "USAGE: diamond blastp -d ${params.output_dir}/2-output/nr.dmnd -q query.fasta -o results.tsv"
    }
    println "========================================================================"
}
