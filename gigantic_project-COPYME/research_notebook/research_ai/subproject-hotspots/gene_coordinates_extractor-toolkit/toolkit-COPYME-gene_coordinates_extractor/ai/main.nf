#!/usr/bin/env nextflow
/*
 * Gene Coordinates Extractor Toolkit - main pipeline
 * AI: Claude Code | Opus 4.7 | 2026 May 29
 * Human: Eric Edsinger
 *
 * Purpose:
 *   Extract per-species gene-coordinate TSVs from GFF3 annotation files
 *   for downstream consumption by the hotspots subproject
 *   (BLOCK_identify_hotspots).
 *
 *   GFF/GTF formats vary so widely across genome annotation sources that
 *   the hotspots subproject deliberately does NOT attempt extraction
 *   itself. Producing the per-species TSVs is a user responsibility; this
 *   toolkit is the canonical GIGANTIC tool for fulfilling that
 *   responsibility for NCBI / AUGUSTUS / BRAKER GFF flavors.
 *
 * Process Overview:
 *    1: Extract per-species gene-coordinate TSVs from GFF3 files
 *    2: Validate the emitted TSVs (header, row shape, coords sanity)
 *    3: Symlink TSVs into the hotspots subproject's gene_coordinates dir
 *    4: Write workflow run log (GIGANTIC convention §45)
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (defaults; overridden via -params-file)
// ============================================================================

params.annotations_dir   = null
params.hotspots_gene_coordinates_dir = null
params.species_whitelist = ""          // optional comma-separated list
params.output_dir        = "OUTPUT_pipeline"
params.project_name      = "gigantic_project"

// ============================================================================
// PROCESS 1: Extract gene coordinates from GFF3 files
// ============================================================================

process extract_gene_coordinates {
    tag "extract"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output", emit: out_dir

    script:
    def whitelist_arg = params.species_whitelist?.trim() ?
        "--species " + params.species_whitelist.split(",").collect{ it.trim() }.findAll{ it }.join(" ") : ""
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-extract_gene_coordinates.py \\
        --annotations-dir ${params.annotations_dir} \\
        --output-dir 1-output \\
        --log-file 1-output/1_ai-log-extract_gene_coordinates.log \\
        ${whitelist_arg}
    """
}

// ============================================================================
// PROCESS 2: Validate per-species TSVs
// ============================================================================

process validate_outputs {
    tag "validate"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path extract_out

    output:
        path "2-output", emit: out_dir

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-validate_outputs.py \\
        --input-dir ${extract_out} \\
        --output-dir 2-output \\
        --log-file 2-output/2_ai-log-validate_outputs.log
    """
}

// ============================================================================
// PROCESS 3: Bridge to hotspots subproject
// ============================================================================

process bridge_to_hotspots {
    tag "bridge"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path extract_out
        val validate_done

    output:
        path "3-output", emit: out_dir

    script:
    """
    mkdir -p 3-output

    python3 ${projectDir}/scripts/003_ai-python-bridge_to_hotspots.py \\
        --input-dir ${extract_out} \\
        --target-dir ${params.hotspots_gene_coordinates_dir} \\
        --log-file 3-output/3_ai-log-bridge_to_hotspots.log
    """
}

// ============================================================================
// PROCESS 4: Write run log (GIGANTIC §45)
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
        --workflow-name "gene_coordinates_extractor" \\
        --subproject-name "subproject-hotspots" \\
        --project-name "${params.project_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    log.info """
    ========================================================================
    Gene Coordinates Extractor (research_notebook/research_ai/subproject-hotspots)
    ========================================================================
    annotations-dir         : ${params.annotations_dir}
    hotspots gene_coords dir: ${params.hotspots_gene_coordinates_dir}
    species whitelist       : ${params.species_whitelist ?: '(none; process all)'}
    output dir              : ${params.output_dir}
    ========================================================================
    """.stripIndent()

    if ( !params.annotations_dir ) {
        error "annotations_dir not set! Edit START_HERE-user_config.yaml."
    }
    if ( !params.hotspots_gene_coordinates_dir ) {
        error "hotspots_gene_coordinates_dir not set! Edit START_HERE-user_config.yaml."
    }

    extract_gene_coordinates()
    validate_outputs( extract_gene_coordinates.out.out_dir )
    bridge_to_hotspots(
        extract_gene_coordinates.out.out_dir,
        validate_outputs.out.out_dir
    )
    write_run_log( bridge_to_hotspots.out.out_dir )
}
