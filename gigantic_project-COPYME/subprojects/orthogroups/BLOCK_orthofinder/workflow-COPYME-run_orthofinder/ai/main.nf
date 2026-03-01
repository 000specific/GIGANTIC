#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Nextflow pipeline for OrthoFinder orthogroup detection
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// OrthoFinder Orthogroup Detection Pipeline
// =============================================================================
//
// Six-step pipeline:
//   1. Validate proteomes from genomesDB
//   2. Prepare proteomes (copy to OrthoFinder input directory)
//   3. Run OrthoFinder with -X flag (preserves original identifiers)
//   4. Standardize OrthoFinder output to GIGANTIC format
//   5. Generate summary statistics
//   6. Per-species QC analysis
//
// OrthoFinder supports the -X flag to preserve original GIGANTIC identifiers,
// so no header conversion/restoration is needed (unlike OrthoHMM and Broccoli).
//
// Symlinks for output_to_input/ are created by RUN-workflow.sh after pipeline completes
// =============================================================================

scripts_dir = "${projectDir}/scripts"

process validate_proteomes {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

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

process prepare_proteomes {
    publishDir "${params.output_dir}/2-output", mode: 'copy', pattern: '2_ai-*'
    publishDir "${params.output_dir}/2-output/orthofinder_input_proteomes", mode: 'copy', pattern: 'orthofinder_input_proteomes/*'

    input:
        path proteome_list

    output:
        path 'orthofinder_input_proteomes/*.aa', emit: prepared_proteomes
        path '2_ai-prepared_proteomes_summary.tsv', emit: prepared_summary
        path '2_ai-log-prepare_proteomes.log'

    script:
    """
    python3 ${scripts_dir}/002_ai-python-prepare_proteomes.py \
        --proteome-list ${proteome_list} \
        --output-dir .
    """
}

process run_orthofinder {
    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        path prepared_proteomes

    output:
        path 'Orthogroups.tsv', emit: orthogroups
        path 'Orthogroups.GeneCount.tsv', emit: gene_count
        path '3_ai-log-run_orthofinder.log'

    script:
    """
    mkdir -p input_proteomes
    cp ${prepared_proteomes} input_proteomes/

    bash ${scripts_dir}/003_ai-bash-run_orthofinder.sh \
        --input-dir input_proteomes \
        --output-dir . \
        --cpus ${params.cpus} \
        --search-method ${params.search_method} \
        --mcl-inflation ${params.mcl_inflation}
    """
}

process standardize_output {
    publishDir "${params.output_dir}/4-output", mode: 'copy'

    input:
        path orthogroups
        path gene_count
        path proteome_list

    output:
        path '4_ai-orthogroups_gigantic_ids.tsv', emit: orthogroups_gigantic
        path '4_ai-gene_count_gigantic_ids.tsv', emit: gene_count_gigantic
        path '4_ai-log-standardize_output.log'

    script:
    """
    mkdir -p orthofinder_output
    cp ${orthogroups} orthofinder_output/
    cp ${gene_count} orthofinder_output/

    python3 ${scripts_dir}/004_ai-python-standardize_output.py \
        --orthofinder-dir orthofinder_output \
        --proteome-list ${proteome_list} \
        --output-dir .
    """
}

process generate_summary_statistics {
    publishDir "${params.output_dir}/5-output", mode: 'copy'

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
    publishDir "${params.output_dir}/6-output", mode: 'copy'

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

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/ and ai/output_to_input/ are created
// by RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    validate_proteomes( params.proteomes_dir )
    prepare_proteomes( validate_proteomes.out.proteome_list )
    run_orthofinder( prepare_proteomes.out.prepared_proteomes )
    standardize_output(
        run_orthofinder.out.orthogroups,
        run_orthofinder.out.gene_count,
        validate_proteomes.out.proteome_list
    )
    generate_summary_statistics(
        validate_proteomes.out.proteome_list,
        standardize_output.out.orthogroups_gigantic
    )
    qc_analysis_per_species(
        validate_proteomes.out.proteome_list,
        standardize_output.out.orthogroups_gigantic
    )
}
