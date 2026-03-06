#!/usr/bin/env nextflow
/*
 * GIGANTIC Orthogroups - BLOCK OrthoHMM Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 March 06
 * Human: Eric Edsinger
 *
 * Purpose: Run OrthoHMM orthogroup detection with validation, statistics, and QC
 *
 * Scripts:
 *   001: Validate proteomes from genomesDB
 *   002: Convert headers to short IDs (Genus_species-N)
 *   003: Run OrthoHMM clustering
 *   004: Restore full GIGANTIC identifiers
 *   005: Generate summary statistics
 *   006: Per-species QC analysis
 *   007: Write run log
 *
 * Symlinks for output_to_input/ are created by RUN-workflow.sh after pipeline completes
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from nextflow.config)
// ============================================================================

params.proteomes_dir = '../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes'
params.output_dir = 'OUTPUT_pipeline'
params.cpus = 0
params.memory = '0 GB'
params.evalue = '0.0001'
params.single_copy_threshold = '0.5'
params.project_name = 'GIGANTIC'
params.conda_environment = 'ai_gigantic_orthogroups_orthohmm'

// ============================================================================
// VALIDATE REQUIRED CONFIGURATION
// ============================================================================
// OrthoHMM is resource-intensive. Users MUST set cpus and memory in
// START_HERE-user_config.yaml before running.

if (params.cpus == 0) {
    error """
    ========================================================================
    CONFIGURATION ERROR: cpus not set!

    You must set orthohmm.cpus in START_HERE-user_config.yaml before running.
    Example:
        orthohmm:
          cpus: 100

    OrthoHMM is CPU-intensive. Set this to the number of cores available.
    ========================================================================
    """.stripIndent()
}

if (params.memory == '0 GB') {
    error """
    ========================================================================
    CONFIGURATION ERROR: memory not set!

    You must set orthohmm.memory in START_HERE-user_config.yaml before running.
    Example:
        orthohmm:
          memory: "750 GB"

    OrthoHMM is memory-intensive. Set this to match your available RAM.
    ========================================================================
    """.stripIndent()
}

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate and List Proteomes
 * Calls: scripts/001_ai-python-validate_proteomes.py
 */
process validate_proteomes {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        val proteomes_dir

    output:
        path "1-output/1_ai-proteome_list.tsv", emit: proteome_list
        path "1-output/1_ai-log-validate_proteomes.log"

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_proteomes.py \\
        --proteomes-dir ${projectDir}/../${proteomes_dir} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Convert Headers to Short IDs
 * Calls: scripts/002_ai-python-convert_headers_to_short_ids.py
 */
process convert_headers {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list

    output:
        path "2-output/2_ai-header_mapping.tsv", emit: header_mapping
        path "2-output/short_header_proteomes/*.pep", emit: short_header_proteomes
        path "2-output/2_ai-log-convert_headers_to_short_ids.log"

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-convert_headers_to_short_ids.py \\
        --proteome-list ${proteome_list} \\
        --output-dir 2-output
    """
}

/*
 * Process 3: Run OrthoHMM Clustering
 * Calls: scripts/003_ai-bash-run_orthohmm.sh
 */
process run_orthohmm {
    label 'orthohmm'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path short_header_proteomes

    output:
        path "3-output/orthohmm_orthogroups.txt", emit: orthogroups
        path "3-output/orthohmm_gene_count.txt", emit: gene_count
        path "3-output/orthohmm_single_copy_orthogroups.txt", emit: single_copy_orthogroups
        path "3-output/3_ai-log-run_orthohmm.log"

    script:
    """
    mkdir -p 3-output/input_proteomes

    cp ${short_header_proteomes} 3-output/input_proteomes/

    bash ${projectDir}/scripts/003_ai-bash-run_orthohmm.sh \\
        --input-dir 3-output/input_proteomes \\
        --output-dir 3-output \\
        --cpus ${params.cpus} \\
        --evalue ${params.evalue} \\
        --single-copy-threshold ${params.single_copy_threshold}
    """
}

/*
 * Process 4: Restore GIGANTIC Identifiers
 * Calls: scripts/004_ai-python-restore_gigantic_identifiers.py
 */
process restore_identifiers {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path header_mapping
        path orthogroups
        path gene_count

    output:
        path "4-output/4_ai-orthogroups_gigantic_ids.tsv", emit: orthogroups_gigantic
        path "4-output/4_ai-gene_count_gigantic_ids.tsv", emit: gene_count_gigantic
        path "4-output/4_ai-log-restore_gigantic_identifiers.log"

    script:
    """
    mkdir -p 4-output/orthohmm_output

    cp ${orthogroups} 4-output/orthohmm_output/
    cp ${gene_count} 4-output/orthohmm_output/

    python3 ${projectDir}/scripts/004_ai-python-restore_gigantic_identifiers.py \\
        --header-mapping ${header_mapping} \\
        --orthohmm-dir 4-output/orthohmm_output \\
        --output-dir 4-output
    """
}

/*
 * Process 5: Generate Summary Statistics
 * Calls: scripts/005_ai-python-generate_summary_statistics.py
 */
process generate_summary_statistics {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list
        path orthogroups_gigantic

    output:
        path "5-output/5_ai-summary_statistics.tsv", emit: summary_statistics
        path "5-output/5_ai-orthogroup_size_distribution.tsv", emit: size_distribution
        path "5-output/5_ai-log-generate_summary_statistics.log"

    script:
    """
    mkdir -p 5-output

    python3 ${projectDir}/scripts/005_ai-python-generate_summary_statistics.py \\
        --proteome-list ${proteome_list} \\
        --orthogroups-file ${orthogroups_gigantic} \\
        --output-dir 5-output
    """
}

/*
 * Process 6: Per-Species QC Analysis
 * Calls: scripts/006_ai-python-qc_analysis_per_species.py
 */
process qc_analysis_per_species {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list
        path orthogroups_gigantic

    output:
        path "6-output/6_ai-per_species_summary.tsv", emit: per_species_summary
        path "6-output/6_ai-log-qc_analysis_per_species.log"

    script:
    """
    mkdir -p 6-output

    python3 ${projectDir}/scripts/006_ai-python-qc_analysis_per_species.py \\
        --proteome-list ${proteome_list} \\
        --orthogroups-file ${orthogroups_gigantic} \\
        --output-dir 6-output
    """
}

/*
 * Process 7: Write Run Log
 * Calls: scripts/007_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/007_ai-python-write_run_log.py \\
        --workflow-name "run_orthohmm" \\
        --subproject-name "orthogroups" \\
        --project-name "${params.project_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================
// NOTE: Symlinks for output_to_input/BLOCK_orthohmm/ are created
// by RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.

workflow {
    // Step 1: Validate proteomes
    validate_proteomes( params.proteomes_dir )

    // Step 2: Convert headers to short IDs
    convert_headers( validate_proteomes.out.proteome_list )

    // Step 3: Run OrthoHMM
    run_orthohmm( convert_headers.out.short_header_proteomes )

    // Step 4: Restore GIGANTIC identifiers
    restore_identifiers(
        convert_headers.out.header_mapping,
        run_orthohmm.out.orthogroups,
        run_orthohmm.out.gene_count
    )

    // Step 5: Generate summary statistics
    generate_summary_statistics(
        validate_proteomes.out.proteome_list,
        restore_identifiers.out.orthogroups_gigantic
    )

    // Step 6: Per-species QC analysis
    qc_analysis_per_species(
        validate_proteomes.out.proteome_list,
        restore_identifiers.out.orthogroups_gigantic
    )

    // Step 7: Write run log (FINAL STEP)
    write_run_log( qc_analysis_per_species.out.per_species_summary )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Orthogroups - OrthoHMM Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Validated proteome list"
        println "  2-output/: Short-header proteomes and mapping"
        println "  3-output/: OrthoHMM clustering results"
        println "  4-output/: Orthogroups with restored GIGANTIC identifiers"
        println "  5-output/: Summary statistics"
        println "  6-output/: Per-species QC analysis"
        println ""
        println "Symlinks created in output_to_input/BLOCK_orthohmm/ (by RUN-workflow.sh)"
        println "Run log written to ai/logs/ in this workflow directory"
    }
    println "========================================================================"
}
