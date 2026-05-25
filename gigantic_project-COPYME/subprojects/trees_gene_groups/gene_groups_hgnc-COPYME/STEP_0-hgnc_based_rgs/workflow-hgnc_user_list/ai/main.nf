#!/usr/bin/env nextflow
/*
 * GIGANTIC trees_gene_groups STEP_0-hgnc_based_rgs / workflow-hgnc_user_list
 * AI: Claude Code | Opus 4.7 | 2026 May 25
 * Human: Eric Edsinger
 *
 * Purpose: Convert a user-supplied list of human gene symbols (organized
 *          into one or more named groups) into per-group RGS FASTAs in the
 *          format STEP_1 (homolog discovery) expects.
 *
 * Pipeline:
 *    0: Download HGNC complete_set TSV (script 000) — idempotent against
 *       subproject-level output_to_input/hugo_hgnc_database/.
 *    1: Resolve each user-supplied symbol → UniProt accession via the
 *       HGNC complete_set (script 001). Handles aliases and withdrawn
 *       symbols; fails fast if any symbol cannot be resolved.
 *    2: Fetch the canonical Swiss-Prot FASTA from the UniProt REST API
 *       for each accession and emit per-group RGS FASTAs (script 002).
 *
 * Output Layout:
 *   OUTPUT_pipeline/0-output/hgnc_complete_set.txt
 *   OUTPUT_pipeline/1-output/1_ai-resolved_symbols.tsv
 *   OUTPUT_pipeline/2-output/rgs_fastas/rgs_hgnc_user-human-{group}.aa
 *   OUTPUT_pipeline/2-output/2_ai-rgs_generation_manifest.tsv
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from START_HERE-user_config.yaml via -params-file)
// ============================================================================

params.user_gene_set_file = null
params.output_dir = "OUTPUT_pipeline"

// ============================================================================
// PROCESS 0: Download HGNC complete_set TSV
// Script: 000 (identical to workflow-hgnc_database/000) - idempotent
// download with canonical-source check.
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
// PROCESS 1: Resolve User Symbols to UniProt Accessions
// Script: 001 - Reads user_gene_set.tsv + hgnc_complete_set.txt; resolves
// every symbol (with alias/prev_symbol fallback) to a UniProt accession;
// fails fast if any symbol cannot be resolved.
// ============================================================================

process resolve_user_symbols_to_uniprot {
    tag "resolve_symbols"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path complete_set_dir
        path user_gene_set_file

    output:
        path "1-output", emit: resolved_dir

    script:
    """
    mkdir -p 1-output

    echo "Resolving user gene symbols to UniProt accessions..."
    python3 ${projectDir}/scripts/001_ai-python-resolve_user_symbols_to_uniprot.py \\
        --input-user-gene-set ${user_gene_set_file} \\
        --input-hgnc-complete-set ${complete_set_dir}/hgnc_complete_set.txt \\
        --output-directory 1-output \\
        --log-file 1-output/1_ai-log-resolve_user_symbols_to_uniprot.log

    echo "Symbol resolution complete"
    """
}

// ============================================================================
// PROCESS 2: Fetch UniProt FASTAs and Emit Per-Group RGS
// Script: 002 - Reads resolved-symbols manifest; for each entry, fetches
// canonical Swiss-Prot FASTA from UniProt REST API; writes per-group RGS
// FASTAs with GIGANTIC 5-field headers compatible with STEP_1's parser.
// ============================================================================

process fetch_uniprot_fastas_and_emit_rgs {
    tag "fetch_fastas"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path resolved_dir

    output:
        path "2-output", emit: rgs_dir

    script:
    """
    mkdir -p 2-output

    echo "Fetching UniProt FASTAs and emitting per-group RGS..."
    python3 ${projectDir}/scripts/002_ai-python-fetch_uniprot_fastas-emit_rgs.py \\
        --input-resolved-symbols ${resolved_dir}/1_ai-resolved_symbols.tsv \\
        --output-directory 2-output \\
        --log-file 2-output/2_ai-log-fetch_uniprot_fastas-emit_rgs.log

    echo "RGS FASTA generation complete"
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================
// NOTE: Symlinks to subproject output_to_input/ are created by RUN-workflow.sh
// after the pipeline completes. Real files only live in OUTPUT_pipeline/N-output/.

workflow {
    log.info """
    ========================================================================
    GIGANTIC trees_gene_groups STEP_0-hgnc_based_rgs / workflow-hgnc_user_list
    ========================================================================
    User gene set : ${params.user_gene_set_file}
    Output dir    : ${params.output_dir}
    ========================================================================
    """.stripIndent()

    // ---- Validate critical parameters ----
    if ( !params.user_gene_set_file ) {
        error "user_gene_set_file not configured! Edit START_HERE-user_config.yaml."
    }

    def user_gene_set = file( params.user_gene_set_file )
    if ( !user_gene_set.exists() ) {
        error "User gene set TSV not found: ${params.user_gene_set_file}\nCreate <instance>/INPUT_user/user_gene_set.tsv (see user_gene_set_EXAMPLE.tsv in the template)."
    }

    // ---- Process 0: Download HGNC complete_set (idempotent) ----
    download_hgnc_complete_set()

    // ---- Process 1: Resolve symbols ----
    resolve_user_symbols_to_uniprot(
        download_hgnc_complete_set.out.complete_set_dir,
        user_gene_set
    )

    // ---- Process 2: Fetch FASTAs + emit RGS ----
    fetch_uniprot_fastas_and_emit_rgs( resolve_user_symbols_to_uniprot.out.resolved_dir )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
