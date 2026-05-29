#!/usr/bin/env nextflow
/*
 * GIGANTIC trees_gene_groups STEP_0-hgnc_based_rgs
 * workflow-COPYME-hgnc_user_gene_group_names
 *
 * AI: Claude Code | Opus 4.7 | 2026 May 29
 * Human: Eric Edsinger
 *
 * Purpose:
 *   Like workflow-COPYME-hgnc_database, but emits RGS FASTAs for ONLY the
 *   HGNC gene groups the user names (by HGNC group name OR by HGNC group ID
 *   like gg483). Also emits a side-car gene_symbol -> hgnc_group annotation
 *   map for downstream tree-tip-coloring by HGNC subgroup membership.
 *
 * Process Overview:
 *    0: Download HGNC complete_set TSV (script 000) - idempotent
 *    1: Download HGNC gene-group database tables (script 001)
 *    2: Filter aggregated gene sets to the user's groups (script 002, NEW)
 *    3: Generate RGS FASTA files from human proteome + emit side-car
 *       annotation map (script 003)
 *    4: Write workflow run log to ai/logs/ (script 004; GIGANTIC §45)
 *
 * Data Flow:
 *   HGNC download -> user-supplied names/IDs resolve -> aggregate gene symbols
 *   (filtered to user groups) -> extract sequences from human proteome
 *   RGS FASTAs                 -> OUTPUT_pipeline/3-output/rgs_fastas/
 *   Side-car annotation map    -> OUTPUT_pipeline/3-output/3_ai-gene_symbol_to_hgnc_group_map.tsv
 *   complete_set               -> OUTPUT_pipeline/0-output/hgnc_complete_set.txt
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (defaults; -params-file overrides)
// ============================================================================
// Flat names match the .params.json structure produced by RUN-workflow.sh,
// which flattens the nested START_HERE-user_config.yaml. See nextflow.config
// for rationale.

params.user_gene_group_names_file = null
params.human_proteome_path = null
params.include_pseudogenes = false
params.include_non_protein_coding = false
params.output_dir = "OUTPUT_pipeline"
params.project_name = "gigantic_project"

// ============================================================================
// PROCESS 0: Download HGNC complete_set TSV
// Script: 000 - Idempotent download of hgnc_complete_set.txt (with uniprot_ids
//               column). Skips network fetch if a valid canonical copy exists
//               at subproject-level output_to_input/hugo_hgnc_database/.
// ============================================================================

process download_hgnc_complete_set {
    tag "download_complete_set"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "0-output", emit: complete_set_dir

    script:
    """
    mkdir -p 0-output

    echo "Downloading HGNC complete_set TSV..."
    python3 ${projectDir}/scripts/000_ai-python-download_hgnc_complete_set.py \\
        --output-directory 0-output \\
        --canonical-source "${projectDir}/../../../../output_to_input/hugo_hgnc_database/hgnc_complete_set.txt" \\
        --log-file 0-output/0_ai-log-download_hgnc_complete_set.log

    echo "HGNC complete_set download complete"
    """
}

// ============================================================================
// PROCESS 1: Download HGNC Gene Group Data
// Script: 001 - Downloads family.csv, hierarchy*.csv, gene_has_family.csv,
//               hgnc_gene_groups_all.tsv from genenames.org.
// ============================================================================

process download_hgnc_data {
    tag "download_hgnc"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output", emit: download_dir

    script:
    """
    mkdir -p 1-output

    echo "Downloading HGNC gene group data..."
    python3 ${projectDir}/scripts/001_ai-python-download_hgnc_gene_group_data.py \\
        --output-directory 1-output \\
        --log-file 1-output/1_ai-log-download_hgnc_gene_group_data.log

    echo "HGNC download complete"
    """
}

// ============================================================================
// PROCESS 2: Filter Aggregated Gene Sets by User-Supplied Names/IDs
// Script: 002 - Resolves user TSV entries -> HGNC family ids, applies the
//               locus-type allowlist, and emits the filtered aggregated TSV
//               + resolution trail + catalog + filter-policy record.
// ============================================================================

process filter_aggregated_gene_sets_by_user_names {
    tag "filter_user_groups"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path download_dir
        path user_gene_group_names_file

    output:
        path "2-output", emit: gene_sets_dir

    script:
    def include_pseudogenes_flag = params.include_pseudogenes ? '--include-pseudogenes' : ''
    def include_non_pc_flag = params.include_non_protein_coding ? '--include-non-protein-coding' : ''
    """
    mkdir -p 2-output

    echo "Filtering aggregated gene sets by user-supplied group names/IDs..."
    python3 ${projectDir}/scripts/002_ai-python-filter_aggregated_gene_sets_by_user_names.py \\
        --input-directory ${download_dir} \\
        --input-user-gene-groups ${user_gene_group_names_file} \\
        ${include_pseudogenes_flag} \\
        ${include_non_pc_flag} \\
        --output-directory 2-output \\
        --log-file 2-output/2_ai-log-filter_aggregated_gene_sets_by_user_names.log

    echo "Filtered aggregated gene sets complete"
    """
}

// ============================================================================
// PROCESS 3: Generate RGS FASTA Files + Side-Car Annotation Map
// Script: 003 - Extracts protein sequences from the GIGANTIC human T1 proteome
//               for each (now filtered) gene group, writes RGS FASTAs, and
//               writes the side-car gene_symbol -> hgnc_group annotation map.
// ============================================================================

process generate_rgs_fasta_files {
    tag "generate_rgs"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path gene_sets_dir
        path human_proteome

    output:
        path "3-output", emit: rgs_output_dir

    script:
    """
    mkdir -p 3-output

    echo "Generating RGS FASTA files from human proteome..."
    python3 ${projectDir}/scripts/003_ai-python-generate_rgs_fasta_files.py \\
        --input-gene-sets ${gene_sets_dir}/2_ai-aggregated_gene_sets.tsv \\
        --input-proteome ${human_proteome} \\
        --output-directory 3-output \\
        --log-file 3-output/3_ai-log-generate_rgs_fasta_files.log

    echo "RGS FASTA generation complete"
    """
}

// ============================================================================
// PROCESS 4: Write Run Log (GIGANTIC §45)
// Script: 004 - Writes a timestamped run log to ai/logs/ documenting the run
//               (workflow name, subproject, project, status, timestamp).
// Final step. Gated on Process 3 completion.
// ============================================================================

process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-write_run_log.py \\
        --workflow-name "hgnc_user_gene_group_names" \\
        --subproject-name "trees_gene_groups" \\
        --project-name "${params.project_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================
// NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
// the pipeline completes. Real files only live in OUTPUT_pipeline/N-output/.

workflow {
    log.info """
    ========================================================================
    GIGANTIC trees_gene_groups STEP_0 - HGNC User Gene Group NAMES RGS
    ========================================================================
    User gene-groups TSV    : ${params.user_gene_group_names_file}
    Human proteome          : ${params.human_proteome_path}
    Include pseudogenes     : ${params.include_pseudogenes}
    Include non-protein-coding: ${params.include_non_protein_coding}
    Output directory        : ${params.output_dir}
    ========================================================================
    """.stripIndent()

    // ---- Validate critical parameters ----
    if ( !params.user_gene_group_names_file ) {
        error "user_gene_group_names_file not configured! Edit START_HERE-user_config.yaml (inputs.user_gene_group_names_file)."
    }
    def user_gene_group_names_file_obj = file( params.user_gene_group_names_file )
    if ( !user_gene_group_names_file_obj.exists() ) {
        error "User gene-group names TSV not found: ${params.user_gene_group_names_file}\nProvide it at ../../INPUT_user/user_gene_group_names.tsv (see INPUT_user/user_gene_group_names_EXAMPLE.tsv for format)."
    }

    if ( !params.human_proteome_path ) {
        error "human_proteome_path not configured! Edit START_HERE-user_config.yaml (inputs.human_proteome_path)."
    }
    def human_proteome_file = file( params.human_proteome_path )
    if ( !human_proteome_file.exists() ) {
        error "Human proteome file not found: ${params.human_proteome_path}\nEnsure the genomesDB subproject has been run and the path in START_HERE-user_config.yaml is correct."
    }

    // ---- Process 0: Download HGNC complete_set (independent) ----
    download_hgnc_complete_set()

    // ---- Process 1: Download HGNC gene-group data ----
    download_hgnc_data()

    // ---- Process 2: Filter aggregated gene sets by user-supplied names/IDs ----
    filter_aggregated_gene_sets_by_user_names(
        download_hgnc_data.out.download_dir,
        user_gene_group_names_file_obj
    )

    // ---- Process 3: Generate RGS FASTA files + side-car annotation map ----
    generate_rgs_fasta_files(
        filter_aggregated_gene_sets_by_user_names.out.gene_sets_dir,
        human_proteome_file
    )

    // ---- Process 4: Write run log (FINAL STEP; §45) ----
    write_run_log( generate_rgs_fasta_files.out.rgs_output_dir )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
