#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: STEP_2 - Apply secretome filter manifest to STEP_1 evidence tables
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// STEP_2: secretome filter pipeline
// =============================================================================
//
// One run = one secretome variant defined by ONE filter manifest. Per-species
// processing (parallel via NextFlow local executor). No cross-species combine
// stage (per user direction 2026-05-25).
//
// STAGE 1 (this scaffold):
//   001 validate_filter_manifest    — JSON syntax + minimum structure
//   002 apply_filters_per_species   — apply filter chain → keep matching rows
//   003 augment_with_derived_columns — add cysteine_count + pfam max-per-accession
//   004 write_run_log
//
// STAGE 2 (next iteration):
//   005 augment_with_orthogroups        — OG_ID + members + model species orthologs
//   006 augment_with_blastp_top10       — top 10 NCBI nr hits + e-values
//
// All process outputs are tagged with `params.run_label` (e.g.
// `secretome_001` or `secretome_001_moroz_strict`) for cross-run provenance.
// =============================================================================

scripts_dir = "${projectDir}/scripts"

process validate_filter_manifest {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        path manifest_path

    output:
        path "${params.run_label}_validated_manifest.json", emit: validated_manifest
        path "${params.run_label}_log-validate_filter_manifest.log"

    script:
    """
    python3 ${scripts_dir}/001_ai-python-validate_filter_manifest.py \
        --manifest-path ${manifest_path} \
        --run-label ${params.run_label} \
        --output-dir .
    """
}

process apply_filters_per_species {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        tuple val( phyloname ), path( evidence_table )
        path validated_manifest

    output:
        tuple val( phyloname ), path( "${phyloname}_${params.run_label}_filtered.tsv" ), emit: filtered
        path "${phyloname}_${params.run_label}_log-apply_filters.log"

    script:
    """
    python3 ${scripts_dir}/002_ai-python-apply_filters_per_species.py \
        --evidence-table ${evidence_table} \
        --manifest ${validated_manifest} \
        --run-label ${params.run_label} \
        --phyloname ${phyloname} \
        --output-dir .
    """
}

process augment_with_derived_columns {
    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        tuple val( phyloname ), path( filtered_tsv )

    output:
        tuple val( phyloname ), path( "${phyloname}_${params.run_label}_secretome.tsv" ), emit: secretome
        path "${phyloname}_${params.run_label}_log-augment_derived.log"

    script:
    """
    python3 ${scripts_dir}/003_ai-python-augment_with_derived_columns.py \
        --filtered-tsv ${filtered_tsv} \
        --proteome-fasta ${params.proteome_dir}/${phyloname}-T1-proteome.aa \
        --pfam-long-format-tsv ${params.annotation_database_dir}/database_pfam/gigantic_annotations-database_pfam-${phyloname}.tsv \
        --run-label ${params.run_label} \
        --phyloname ${phyloname} \
        --output-dir .
    """
}

process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${scripts_dir}/004_ai-python-write_run_log.py \
        --workflow-name "filter_secretome" \
        --subproject-name "secretome" \
        --project-name "${params.project_name}" \
        --run-label "${params.run_label}" \
        --status success
    """
}

// =============================================================================
// Workflow
// =============================================================================
workflow {
    // Step 1: validate manifest
    validate_filter_manifest( params.filter_manifest_path )

    // Step 2: per-species filter
    // Channel: each evidence table file in the input dir → tuple (phyloname, path)
    species_channel = Channel
        .fromPath( "${params.evidence_table_dir}/*_evidence_table.tsv" )
        .map { f ->
            def name = f.getName()
            def phyloname = name.replaceFirst( /_evidence_table\.tsv$/, '' )
            tuple( phyloname, f )
        }

    apply_filters_per_species(
        species_channel,
        validate_filter_manifest.out.validated_manifest
    )

    // Step 3: augment with derived columns
    augment_with_derived_columns( apply_filters_per_species.out.filtered )

    // Step 4: write run log (after all augment outputs land)
    write_run_log( augment_with_derived_columns.out.secretome.collect() )
}
