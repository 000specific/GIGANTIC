#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * ANNOTATIONS OCL PIPELINE: ORIGIN-CONSERVATION-LOSS ANALYSIS OF ANNOGROUPS
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow for analyzing annotation group (annogroup) origins,
 * conservation, and loss across phylogenetic species tree structures.
 *
 * Annogroups are the annotation analog to orthogroups -- sets of proteins grouped
 * by their annotation pattern from a specific database. Each annogroup has a
 * simple ID (annogroup_{db}_N) with full details in a companion map.
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly to OUTPUT_pipeline/structure_NNN/N-output/
 * - NextFlow passes only val structure_id between processes (done signal)
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow directory)
 *
 * AI: Claude Code | Opus 4.6 | 2026 April 18
 * Human: Eric Edsinger
 * ==============================================================================
 */

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config + .params.json)
// ============================================================================
// All defaults live in nextflow.config; users edit START_HERE-user_config.yaml,
// not this file. Nested params (params.X.Y.Z) mirror the yaml shape.
// RUN-workflow.sh passes the yaml directly via -params-file at runtime.

params.help = false

// Show help message
if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC ANNOTATIONS OCL PIPELINE
    ==============================================================================

    Usage:
        nextflow run main.nf [options]

    Options:
        --config               Path to START_HERE-user_config.yaml
                               (default: ../START_HERE-user_config.yaml)

        --structure_manifest   Path to structure manifest TSV file
                               (overrides config value)

        --output_dir           Output directory for all results
                               (overrides config value)

        --help                 Show this help message

    The pipeline reads all configuration from START_HERE-user_config.yaml including:
      - run_label (for output_to_input namespacing)
      - annotation_database (pfam, gene3d, deeploc, etc.)
      - annogroup_subtypes (single, combo, zero)
      - Input paths to upstream subprojects

    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// INPUT CHANNELS
// ============================================================================
// Workflow root = ${projectDir}/.. (since projectDir is ai/, the workflow root
// is one level up). All workflow-relative paths use that convention.
//
// This run fans out over SOURCES x STRUCTURES. Each (source, structure) pair runs
// the per-structure chain independently, writing to OUTPUT_pipeline/<source>/.

// Resolve the annotation sources to analyze (params.annotation_databases):
//   "all"        -> every source dir present in the annogroups output_to_input
//                   (<annogroups_dir>/<species_set>/<source>/)
//   [ pfam, go ] -> an explicit list
//   "pfam"       -> a single source string
def sources_param = params.annotation_databases
if ( sources_param instanceof List ) {
    Channel.fromList( sources_param ).set { sources_channel }
} else if ( sources_param.toString() == 'all' ) {
    def annogroups_species_dir = "${projectDir}/../${params.inputs.annogroups_dir}/${params.species_set_name}"
    Channel.fromPath( "${annogroups_species_dir}/*", type: 'dir' )
        .map { it.name }
        .set { sources_channel }
} else {
    Channel.of( sources_param.toString() ).set { sources_channel }
}

// Read structure IDs from manifest (path resolved from params.inputs.structure_manifest)
Channel
    .fromPath( "${projectDir}/../${params.inputs.structure_manifest}" )
    .splitCsv( header: true, sep: '\t' )
    .map { row -> row.structure_id }
    .set { structure_ids_channel }

// Cartesian product: one [source, structure_id] tuple per (source, structure)
sources_channel
    .combine( structure_ids_channel )
    .set { source_structure_pairs }

// ============================================================================
// PROCESS 001: CREATE ANNOGROUPS
// ============================================================================

process load_annogroups {
    tag "${source}/structure_${structure_id}"

    input:
    tuple val(source), val(structure_id)

    output:
    tuple val(source), val(structure_id)

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-load_annogroups.py \\
        --structure_id ${structure_id} \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${source}
    """
}

// ============================================================================
// PROCESS 002: DETERMINE ORIGINS
// ============================================================================

process determine_origins {
    tag "${source}/structure_${structure_id}"

    input:
    tuple val(source), val(structure_id)

    output:
    tuple val(source), val(structure_id)

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-determine_origins.py \\
        --structure_id ${structure_id} \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${source}
    """
}

// ============================================================================
// PROCESS 003: QUANTIFY CONSERVATION AND LOSS
// ============================================================================

process quantify_conservation_loss {
    tag "${source}/structure_${structure_id}"

    input:
    tuple val(source), val(structure_id)

    output:
    tuple val(source), val(structure_id)

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-quantify_conservation_loss.py \\
        --structure_id ${structure_id} \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${source}
    """
}

// ============================================================================
// PROCESS 004: COMPREHENSIVE OCL ANALYSIS
// ============================================================================

process comprehensive_ocl_analysis {
    tag "${source}/structure_${structure_id}"

    input:
    tuple val(source), val(structure_id)

    output:
    tuple val(source), val(structure_id)

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-comprehensive_ocl_analysis.py \\
        --structure_id ${structure_id} \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${source}
    """
}

// ============================================================================
// PROCESS 005: SPECIES-TREE DECONVOLUTION (per structure)
// ============================================================================

process species_tree_deconvolution {
    tag "${source}/structure_${structure_id}"

    input:
    tuple val(source), val(structure_id)

    output:
    tuple val(source), val(structure_id)

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-species_tree_deconvolution.py \\
        --structure_id ${structure_id} \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${source}
    """
}

// ============================================================================
// PROCESS 006: VALIDATE RESULTS (per structure)
// ============================================================================

process validate_results {
    tag "${source}/structure_${structure_id}"

    input:
    tuple val(source), val(structure_id)

    output:
    tuple val(source), val(structure_id)

    script:
    """
    python3 ${projectDir}/scripts/006_ai-python-validate_results.py \\
        --structure_id ${structure_id} \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${source}
    """
}

// ============================================================================
// PROCESS 007: COMPOSITE CLADES (once -- structure-independent)
// ============================================================================

/*
 * Process 7: Composite Clades
 * Calls: scripts/007_ai-python-composite_clades.py
 *
 * Computed ONCE PER SOURCE -- annogroup member species and the building-block
 * clade species sets are stable across all structures (Rule 6). Runs after that
 * source's per-structure chain completes (per-source barrier via groupTuple()).
 */
process composite_clades {
    tag "${source}"
    label 'local'

    input:
        tuple val(source), val(done_structures)

    output:
        val source, emit: composite_complete

    script:
    """
    python3 ${projectDir}/scripts/007_ai-python-composite_clades.py \
        --source ${source} \
        --config ${projectDir}/../START_HERE-user_config.yaml \
        --output_dir ${projectDir}/../${params.output.base_dir}/${source}
    """
}

// ============================================================================
// PROCESS 008: WRITE RUN LOG
// ============================================================================

/*
 * Process 8: Write Run Log
 * Calls: scripts/008_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/008_ai-python-write_run_log.py \
        --workflow-name "ocl_analysis" \
        --subproject-name "ocl_phylogenetic_structures-BLOCK_annotations_X_ocl" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// PROCESS 009: AGGREGATE RUN SUMMARY
// ============================================================================

/*
 * Process 9: Aggregate Run Summary
 * Calls: scripts/009_ai-python-aggregate_run_summary.py
 *
 * Reads per-structure JSON fragments emitted by Scripts 001-004 + 006 and builds
 * the consolidated run summary at OUTPUT_pipeline/9-output/9_ai-run_summary.md.
 * This is the final step -- a glanceable success/failure + key stats view.
 */
process aggregate_run_summary {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: summary_complete

    script:
    """
    python3 ${projectDir}/scripts/009_ai-python-aggregate_run_summary.py \
        --config ${projectDir}/../START_HERE-user_config.yaml \
        --workflow_dir ${projectDir}/..
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Per-(source, structure) chain (parallel across both source and structure,
    // sequential within each source-structure pair). Every process threads the
    // [source, structure_id] tuple through and writes to OUTPUT_pipeline/<source>/.
    load_annogroups( source_structure_pairs )
    determine_origins( load_annogroups.out )
    quantify_conservation_loss( determine_origins.out )
    comprehensive_ocl_analysis( quantify_conservation_loss.out )
    species_tree_deconvolution( comprehensive_ocl_analysis.out )
    validate_results( species_tree_deconvolution.out )

    // Per-source barrier: group each source's validated structures, then compute
    // composite clades ONCE per source (structure-independent, Rule 6).
    validate_results.out
        .groupTuple()
        .set { validated_by_source }
    composite_clades( validated_by_source )

    // Global barrier: after every source's composite clades complete, write the run
    // log, then aggregate the run summary across all sources (FINAL STEP).
    write_run_log( composite_clades.out.composite_complete.collect() )
    aggregate_run_summary( write_run_log.out.log_complete )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
