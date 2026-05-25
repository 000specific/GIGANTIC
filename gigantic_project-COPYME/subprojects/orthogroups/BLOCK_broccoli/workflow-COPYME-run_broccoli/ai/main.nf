#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Nextflow pipeline for Broccoli orthogroup detection
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// Broccoli Orthogroup Detection Pipeline
// =============================================================================
//
// Six-step pipeline:
//   1. Validate proteomes from genomesDB
//   2. Convert headers to short IDs (Genus_species-N)
//   3. Run Broccoli orthogroup detection
//   4. Restore full GIGANTIC identifiers
//   5. Generate summary statistics
//   6. Per-species QC analysis
//
// Symlinks for output_to_input/ are created by RUN-workflow.sh after pipeline completes
// =============================================================================

scripts_dir = "${projectDir}/scripts"

process validate_proteomes {
    publishDir "${params.output.base_dir}/1-output", mode: 'copy'

    input:
        val proteomes_dir

    output:
        path '1_ai-proteome_list.tsv', emit: proteome_list
        path '1_ai-log-validate_proteomes.log'

    script:
    """
    python3 ${scripts_dir}/001_ai-python-validate_proteomes.py \
        --proteomes-dir ${proteomes_dir} \
        --output-dir .
    """
}

process convert_headers {
    publishDir "${params.output.base_dir}/2-output", mode: 'copy', pattern: '2_ai-*'
    publishDir "${params.output.base_dir}/2-output/short_header_proteomes", mode: 'copy', pattern: 'short_header_proteomes/*'

    input:
        path proteome_list

    output:
        path '2_ai-header_mapping.tsv', emit: header_mapping
        path 'short_header_proteomes/*.aa', emit: short_header_proteomes
        path '2_ai-log-convert_headers_to_short_ids.log'

    script:
    """
    python3 ${scripts_dir}/002_ai-python-convert_headers_to_short_ids.py \
        --proteome-list ${proteome_list} \
        --output-dir .
    """
}

process run_broccoli {
    publishDir "${params.output.base_dir}/3-output", mode: 'copy'

    input:
        path short_header_proteomes

    output:
        path '3_ai-orthologous_groups.txt', emit: orthogroups
        path '3_ai-table_OGs_protein_counts.txt'
        path '3_ai-table_OGs_protein_names.txt'
        path '3_ai-chimeric_proteins.txt'
        path '3_ai-unclassified_proteins.txt'
        path '3_ai-statistics_per_OG.txt'
        path '3_ai-statistics_per_species.txt'
        path '3_ai-statistics_nb_OGs_VS_nb_species.txt'
        path '3_ai-orthologous_pairs.txt'
        path '3_ai-log-run_broccoli.log'

    script:
    """
    mkdir -p input_proteomes
    cp ${short_header_proteomes} input_proteomes/

    bash ${scripts_dir}/003_ai-bash-run_broccoli.sh \
        --input-dir input_proteomes \
        --output-dir . \
        --cpus ${params.resources.run_broccoli.cpus} \
        --tree-method ${params.broccoli.tree_method}
    """
}

process restore_identifiers {
    publishDir "${params.output.base_dir}/4-output", mode: 'copy'

    input:
        path header_mapping
        path orthogroups

    output:
        path '4_ai-orthologous_groups-gigantic_ids.tsv', emit: orthogroups_gigantic
        path '4_ai-log-restore_gigantic_identifiers.log'

    script:
    """
    python3 ${scripts_dir}/004_ai-python-restore_gigantic_identifiers.py \
        --header-mapping ${header_mapping} \
        --orthogroups-file ${orthogroups} \
        --output-dir .
    """
}

process generate_summary_statistics {
    publishDir "${params.output.base_dir}/5-output", mode: 'copy'

    input:
        path proteome_list
        path orthogroups_gigantic

    output:
        path '5_ai-summary_statistics.tsv', emit: summary_statistics
        path '5_ai-orthogroup_size_distribution.tsv', emit: size_distribution
        path '5_ai-log-generate_summary_statistics.log'

    script:
    """
    python3 ${scripts_dir}/005_ai-python-generate_summary_statistics.py \
        --proteome-list ${proteome_list} \
        --orthogroups-file ${orthogroups_gigantic} \
        --output-dir .
    """
}

process qc_analysis_per_species {
    publishDir "${params.output.base_dir}/6-output", mode: 'copy'

    input:
        path proteome_list
        path orthogroups_gigantic

    output:
        path '6_ai-per_species_summary.tsv', emit: per_species_summary
        path '6_ai-log-qc_analysis_per_species.log'

    script:
    """
    python3 ${scripts_dir}/006_ai-python-qc_analysis_per_species.py \
        --proteome-list ${proteome_list} \
        --orthogroups-file ${orthogroups_gigantic} \
        --output-dir .
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
    python3 ${projectDir}/scripts/007_ai-python-write_run_log.py \
        --workflow-name "run_broccoli" \
        --subproject-name "orthogroups" \
        --project-name "${params.project.name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/BLOCK_broccoli/ are created
// by RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    validate_proteomes( params.inputs.proteomes_dir )
    convert_headers( validate_proteomes.out.proteome_list )
    run_broccoli( convert_headers.out.short_header_proteomes )
    restore_identifiers(
        convert_headers.out.header_mapping,
        run_broccoli.out.orthogroups
    )
    generate_summary_statistics(
        validate_proteomes.out.proteome_list,
        restore_identifiers.out.orthogroups_gigantic
    )
    qc_analysis_per_species(
        validate_proteomes.out.proteome_list,
        restore_identifiers.out.orthogroups_gigantic
    )
    write_run_log( qc_analysis_per_species.out.per_species_summary )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
