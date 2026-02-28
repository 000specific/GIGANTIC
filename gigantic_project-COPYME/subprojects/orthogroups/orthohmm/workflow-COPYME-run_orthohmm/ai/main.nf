#!/usr/bin/env nextflow
/*
 * GIGANTIC Orthogroups - OrthoHMM Workflow
 * AI: Claude Code | Opus 4.5 | 2026 February 27
 * Human: Eric Edsinger
 *
 * Purpose: Run OrthoHMM clustering pipeline to identify orthogroups
 *
 * Scripts:
 *   001: Validate and list proteomes
 *   002: Convert headers to short IDs
 *   003: Run OrthoHMM clustering (heavy compute)
 *   004: Generate summary statistics
 *   005: Per-species QC analysis
 *   006: Restore GIGANTIC identifiers
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

// GIGANTIC RULE: Inter-subproject inputs from output_to_input/, NEVER from X-output/
params.input_proteomes = "../../../genomesDB/output_to_input/speciesN_gigantic_T1_proteomes"
params.output_dir = "OUTPUT_pipeline"

// OrthoHMM settings
params.orthohmm_cpus = 100
params.orthohmm_evalue = "0.0001"
params.orthohmm_single_copy_threshold = "0.5"

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate and List Proteomes
 * Calls: scripts/001_ai-python-validate_and_list_proteomes.py
 */
process validate_and_list_proteomes {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-proteome_list.txt", emit: proteome_list
        path "1-output/1_ai-log-validate_and_list_proteomes.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_and_list_proteomes.py \\
        --proteomes-dir ${projectDir}/../${params.input_proteomes} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Convert Headers to Short IDs
 * Calls: scripts/002_ai-python-convert_headers_to_short_ids.py
 */
process convert_headers_to_short_ids {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list

    output:
        path "2-output/short_header_proteomes", emit: short_header_proteomes
        path "2-output/2_ai-header_mapping.tsv", emit: header_mapping
        path "2-output/2_ai-log-convert_headers_to_short_ids.log", emit: log

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
 * NOTE: This is the heavy compute step - may run for hours/days
 */
process run_orthohmm {
    label 'heavy'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path short_header_proteomes

    output:
        path "3-output/orthohmm_orthogroups.txt", emit: orthogroups
        path "3-output/orthohmm_gene_count.txt", emit: gene_count
        path "3-output/orthohmm_single_copy_orthogroups.txt", emit: single_copy
        path "3-output/orthohmm_orthogroups", emit: orthogroup_fastas
        path "3-output/3_ai-log-run_orthohmm.log", emit: log

    script:
    """
    mkdir -p 3-output

    bash ${projectDir}/scripts/003_ai-bash-run_orthohmm.sh \\
        --input-dir ${short_header_proteomes} \\
        --output-dir 3-output \\
        --cpus ${params.orthohmm_cpus} \\
        --evalue ${params.orthohmm_evalue} \\
        --single-copy-threshold ${params.orthohmm_single_copy_threshold}
    """
}

/*
 * Process 4: Generate Summary Statistics
 * Calls: scripts/004_ai-python-generate_summary_statistics.py
 */
process generate_summary_statistics {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list
        path orthogroups

    output:
        path "4-output/4_ai-orthohmm_summary_statistics.tsv", emit: summary
        path "4-output/4_ai-orthogroup_size_distribution.tsv", emit: size_distribution
        path "4-output/4_ai-log-generate_summary_statistics.log", emit: log

    script:
    // The orthohmm directory for the script is the parent of orthohmm_orthogroups.txt
    """
    mkdir -p 4-output

    # Create a symlink structure that the script expects
    mkdir -p orthohmm_dir
    cp ${orthogroups} orthohmm_dir/

    python3 ${projectDir}/scripts/004_ai-python-generate_summary_statistics.py \\
        --proteome-list ${proteome_list} \\
        --orthohmm-dir orthohmm_dir \\
        --output-dir 4-output
    """
}

/*
 * Process 5: Per-Species QC Analysis
 * Calls: scripts/005_ai-python-qc_analysis_per_species.py
 */
process qc_analysis_per_species {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list
        path header_mapping
        path orthogroups

    output:
        path "5-output/5_ai-orthogroups_per_species_summary.tsv", emit: per_species_summary
        path "5-output/5_ai-sequences_without_orthogroup.tsv", emit: unassigned_sequences
        path "5-output/5_ai-log-qc_analysis_per_species.log", emit: log

    script:
    """
    mkdir -p 5-output

    # Create a symlink structure that the script expects
    mkdir -p orthohmm_dir
    cp ${orthogroups} orthohmm_dir/

    python3 ${projectDir}/scripts/005_ai-python-qc_analysis_per_species.py \\
        --proteome-list ${proteome_list} \\
        --header-mapping ${header_mapping} \\
        --orthohmm-dir orthohmm_dir \\
        --output-dir 5-output
    """
}

/*
 * Process 6: Restore GIGANTIC Identifiers
 * Calls: scripts/006_ai-python-restore_gigantic_identifiers.py
 */
process restore_gigantic_identifiers {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    // Also publish to output_to_input for downstream subprojects
    publishDir "${projectDir}/../../output_to_input", mode: 'copy', overwrite: true, pattern: "6-output/6_ai-orthogroups_gigantic_ids.txt", saveAs: { "6_ai-orthogroups_gigantic_ids.txt" }
    publishDir "${projectDir}/../../output_to_input", mode: 'copy', overwrite: true, pattern: "6-output/6_ai-gene_count_gigantic_ids.tsv", saveAs: { "6_ai-gene_count_gigantic_ids.tsv" }
    publishDir "${projectDir}/../../output_to_input", mode: 'copy', overwrite: true, pattern: "2-output/2_ai-header_mapping.tsv", saveAs: { "2_ai-header_mapping.tsv" }
    publishDir "${projectDir}/../../output_to_input", mode: 'copy', overwrite: true, pattern: "4-output/4_ai-orthohmm_summary_statistics.tsv", saveAs: { "4_ai-orthohmm_summary_statistics.tsv" }

    input:
        path header_mapping
        path orthogroups
        path orthogroup_fastas
        path summary_stats

    output:
        path "6-output/6_ai-orthogroups_gigantic_ids.txt", emit: orthogroups_gigantic
        path "6-output/6_ai-gene_count_gigantic_ids.tsv", emit: gene_count_gigantic
        path "6-output/orthogroup_fastas", emit: restored_fastas
        path "6-output/6_ai-per_species", emit: per_species_files
        path "6-output/6_ai-output_summary.txt", emit: output_summary
        path "6-output/6_ai-log-restore_gigantic_identifiers.log", emit: log
        // Pass through files for output_to_input publishing
        path "2-output/2_ai-header_mapping.tsv", emit: header_mapping_copy
        path "4-output/4_ai-orthohmm_summary_statistics.tsv", emit: summary_stats_copy

    script:
    """
    mkdir -p 6-output 2-output 4-output

    # Create a symlink structure that the script expects
    mkdir -p orthohmm_dir
    cp ${orthogroups} orthohmm_dir/

    # Copy orthogroup FASTAs if they exist
    if [ -d "${orthogroup_fastas}" ]; then
        cp -r ${orthogroup_fastas} orthohmm_dir/orthohmm_orthogroups
    fi

    python3 ${projectDir}/scripts/006_ai-python-restore_gigantic_identifiers.py \\
        --header-mapping ${header_mapping} \\
        --orthohmm-dir orthohmm_dir \\
        --output-dir 6-output

    # Copy pass-through files for output_to_input publishing
    cp ${header_mapping} 2-output/
    cp ${summary_stats} 4-output/
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Validate and list proteomes
    validate_and_list_proteomes()

    // Step 2: Convert headers to short IDs (depends on step 1)
    convert_headers_to_short_ids(validate_and_list_proteomes.out.proteome_list)

    // Step 3: Run OrthoHMM clustering (depends on step 2)
    run_orthohmm(convert_headers_to_short_ids.out.short_header_proteomes)

    // Step 4: Generate summary statistics (depends on steps 1 and 3)
    generate_summary_statistics(
        validate_and_list_proteomes.out.proteome_list,
        run_orthohmm.out.orthogroups
    )

    // Step 5: Per-species QC (depends on steps 1, 2, and 3)
    qc_analysis_per_species(
        validate_and_list_proteomes.out.proteome_list,
        convert_headers_to_short_ids.out.header_mapping,
        run_orthohmm.out.orthogroups
    )

    // Step 6: Restore GIGANTIC identifiers (depends on steps 2, 3, and 4)
    restore_gigantic_identifiers(
        convert_headers_to_short_ids.out.header_mapping,
        run_orthohmm.out.orthogroups,
        run_orthohmm.out.orthogroup_fastas,
        generate_summary_statistics.out.summary
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Orthogroups OrthoHMM Workflow Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Proteome validation and listing"
        println "  2-output/: Short-header proteomes and mapping"
        println "  3-output/: OrthoHMM clustering results"
        println "  4-output/: Summary statistics"
        println "  5-output/: Per-species QC analysis"
        println "  6-output/: Results with GIGANTIC identifiers"
        println ""
        println "Key outputs copied to: ../../output_to_input/"
    }
    println "========================================================================"
}
