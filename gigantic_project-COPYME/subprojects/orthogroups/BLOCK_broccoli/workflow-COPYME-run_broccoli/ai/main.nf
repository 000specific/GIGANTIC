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
// Final step copies standardized results to output_to_input/ for downstream use
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

process convert_headers {
    publishDir "${params.output_dir}/2-output", mode: 'copy', pattern: '2_ai-*'
    publishDir "${params.output_dir}/2-output/short_header_proteomes", mode: 'copy', pattern: 'short_header_proteomes/*'

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
    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        path short_header_proteomes

    output:
        path 'orthologous_groups.txt', emit: orthogroups
        path 'table_OGs_protein_counts.txt', emit: protein_counts
        path '3_ai-log-run_broccoli.log'

    script:
    """
    mkdir -p input_proteomes
    cp ${short_header_proteomes} input_proteomes/

    bash ${scripts_dir}/003_ai-bash-run_broccoli.sh \
        --input-dir input_proteomes \
        --output-dir . \
        --cpus ${params.cpus} \
        --tree-method ${params.tree_method}
    """
}

process restore_identifiers {
    publishDir "${params.output_dir}/4-output", mode: 'copy'

    input:
        path header_mapping
        path orthogroups
        path protein_counts

    output:
        path '4_ai-orthogroups_gigantic_ids.tsv', emit: orthogroups_gigantic
        path '4_ai-gene_count_gigantic_ids.tsv', emit: gene_count_gigantic
        path '4_ai-log-restore_gigantic_identifiers.log'

    script:
    """
    mkdir -p broccoli_output
    cp ${orthogroups} broccoli_output/
    cp ${protein_counts} broccoli_output/

    python3 ${scripts_dir}/004_ai-python-restore_gigantic_identifiers.py \
        --header-mapping ${header_mapping} \
        --broccoli-dir broccoli_output \
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

process copy_to_output_to_input {
    publishDir "${projectDir}/OUTPUT_to_input", mode: 'copy', overwrite: true
    publishDir "${projectDir}/../../output_to_input", mode: 'copy', overwrite: true

    input:
        path orthogroups_gigantic
        path gene_count_gigantic
        path summary_statistics
        path per_species_summary

    output:
        path 'orthogroups_gigantic_ids.tsv'
        path 'gene_count_gigantic_ids.tsv'
        path 'summary_statistics.tsv'
        path 'per_species_summary.tsv'

    script:
    """
    cp ${orthogroups_gigantic} orthogroups_gigantic_ids.tsv
    cp ${gene_count_gigantic} gene_count_gigantic_ids.tsv
    cp ${summary_statistics} summary_statistics.tsv
    cp ${per_species_summary} per_species_summary.tsv
    """
}

workflow {
    validate_proteomes( params.proteomes_dir )
    convert_headers( validate_proteomes.out.proteome_list )
    run_broccoli( convert_headers.out.short_header_proteomes )
    restore_identifiers(
        convert_headers.out.header_mapping,
        run_broccoli.out.orthogroups,
        run_broccoli.out.protein_counts
    )
    generate_summary_statistics(
        validate_proteomes.out.proteome_list,
        restore_identifiers.out.orthogroups_gigantic
    )
    qc_analysis_per_species(
        validate_proteomes.out.proteome_list,
        restore_identifiers.out.orthogroups_gigantic
    )
    copy_to_output_to_input(
        restore_identifiers.out.orthogroups_gigantic,
        restore_identifiers.out.gene_count_gigantic,
        generate_summary_statistics.out.summary_statistics,
        qc_analysis_per_species.out.per_species_summary
    )
}
