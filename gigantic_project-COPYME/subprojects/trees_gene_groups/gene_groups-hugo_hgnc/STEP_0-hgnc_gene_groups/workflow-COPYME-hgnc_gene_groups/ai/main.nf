#!/usr/bin/env nextflow
/*
 * GIGANTIC trees_gene_groups STEP_0 - HGNC Gene Group RGS Generation Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 March 30
 * Human: Eric Edsinger
 *
 * Purpose: Download HGNC gene group data and generate RGS (Reference Gene Set)
 *          FASTA files for ALL gene groups by extracting protein sequences from
 *          the GIGANTIC human T1 proteome.
 *
 * Usage: Copy the workflow template, configure START_HERE-user_config.yaml
 *        with the human proteome path, then run.
 *
 * Process Overview:
 *    1: Download HGNC gene group database tables (script 001)
 *    2: Build aggregated gene symbol sets per group (script 002)
 *    3: Generate RGS FASTA files from human proteome (script 003)
 *    (Symlinks for output_to_input created by RUN-workflow.sh after pipeline completes)
 *
 * Data Flow:
 *   Download HGNC tables → aggregate gene symbols → extract sequences from proteome
 *   RGS FASTAs → OUTPUT_pipeline/3-output/rgs_fastas/rgs_hugo_hgnc-human-{name}.aa
 *   Manifests → OUTPUT_pipeline/3-output/
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.human_proteome_path = null
params.output_dir = "OUTPUT_pipeline"

// ============================================================================
// PROCESS 1: Download HGNC Gene Group Data
// Script: 001 - Downloads family.csv, hierarchy*.csv, gene_has_family.csv,
//               hgnc_gene_groups_all.tsv from genenames.org
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
    python3 ${projectDir}/scripts/001_ai-python-download_hgnc_gene_group_data.py \
        --output-directory 1-output \
        --log-file 1-output/1_ai-log-download_hgnc_gene_group_data.log

    echo "HGNC download complete"
    """
}

// ============================================================================
// PROCESS 2: Build Aggregated Gene Sets
// Script: 002 - Builds aggregated gene symbol sets per group using hierarchy
//               closure to include descendant genes
// ============================================================================

process build_aggregated_gene_sets {
    tag "build_gene_sets"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path download_dir

    output:
        path "2-output", emit: gene_sets_dir

    script:
    """
    mkdir -p 2-output

    echo "Building aggregated gene sets..."
    python3 ${projectDir}/scripts/002_ai-python-build_aggregated_gene_sets.py \
        --input-directory ${download_dir} \
        --output-directory 2-output \
        --log-file 2-output/2_ai-log-build_aggregated_gene_sets.log

    echo "Aggregated gene sets complete"
    """
}

// ============================================================================
// PROCESS 3: Generate RGS FASTA Files
// Script: 003 - Extracts protein sequences from GIGANTIC human T1 proteome
//               for each gene group and writes RGS FASTA files
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
    python3 ${projectDir}/scripts/003_ai-python-generate_rgs_fasta_files.py \
        --input-gene-sets ${gene_sets_dir}/2_ai-aggregated_gene_sets.tsv \
        --input-proteome ${human_proteome} \
        --output-directory 3-output \
        --log-file 3-output/3_ai-log-generate_rgs_fasta_files.log

    echo "RGS FASTA generation complete"
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================
// NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
// pipeline completes. Real files only live in OUTPUT_pipeline/N-output/.

workflow {
    log.info """
    ========================================================================
    GIGANTIC trees_gene_groups STEP_0 - HGNC Gene Group RGS Generation
    ========================================================================
    Human proteome  : ${params.human_proteome_path}
    Output directory: ${params.output_dir}
    ========================================================================
    """.stripIndent()

    // ---- Validate critical parameters ----
    if ( !params.human_proteome_path ) {
        error "human_proteome_path not configured! Edit START_HERE-user_config.yaml."
    }

    def human_proteome_file = file( params.human_proteome_path )
    if ( !human_proteome_file.exists() ) {
        error "Human proteome file not found: ${params.human_proteome_path}\nEnsure the genomesDB subproject has been run and the path in START_HERE-user_config.yaml is correct."
    }

    // ---- Process 1: Download HGNC data ----
    download_hgnc_data()

    // ---- Process 2: Build aggregated gene sets ----
    build_aggregated_gene_sets( download_hgnc_data.out.download_dir )

    // ---- Process 3: Generate RGS FASTA files ----
    generate_rgs_fasta_files(
        build_aggregated_gene_sets.out.gene_sets_dir,
        human_proteome_file
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC trees_gene_groups STEP_0 Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if ( workflow.success ) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Downloaded HGNC data (family.csv, hierarchy*.csv, bulk TSV)"
        println "  2-output/: Aggregated gene sets + metadata TSVs"
        println "  3-output/: RGS FASTA files + generation manifest/summary"
        println "  3-output/rgs_fastas/rgs_hugo_hgnc-human-{name}.aa"
        println ""
        println "Symlinks created by RUN-workflow.sh in:"
        println "  ../../output_to_input/STEP_0-hgnc_gene_groups/"
        println ""
        println "Next: Use individual RGS files in STEP_1 (validation) or STEP_2 (homolog discovery)"
    }
    println "========================================================================"
}
