#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * OCL PIPELINE: ORIGIN-CONSERVATION-LOSS ANALYSIS
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow for analyzing orthogroup origins, conservation,
 * and loss across phylogenetic tree structures.
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly to OUTPUT_pipeline/structure_NNN/N-output/
 * - NextFlow passes only val structure_id between processes (done signal)
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow directory)
 *
 * AI: Claude Code | Opus 4.6 | 2026 March 04
 * Human: Eric Edsinger
 * ==============================================================================
 */

// ============================================================================
// PARAMETERS
// ============================================================================

params.config = "${projectDir}/../START_HERE-user_config.yaml"
params.structure_manifest = null  // Read from config if not provided
params.output_dir = null          // Read from config if not provided
params.help = false

// Show help message
if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC OCL PIPELINE
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
      - orthogroup_tool (OrthoFinder, OrthoHMM, Broccoli)
      - Input paths to upstream subprojects
      - FASTA embedding flag

    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// CONFIGURATION FROM YAML
// ============================================================================

// Load START_HERE-user_config.yaml
def config_file = file( params.config )
if ( !config_file.exists() ) {
    log.error "Configuration file not found: ${params.config}"
    System.exit( 1 )
}

def config = new org.yaml.snakeyaml.Yaml().load( config_file.text )

// Resolve parameters (CLI overrides config)
def workflow_dir = config_file.parent  // Directory containing START_HERE-user_config.yaml
def structure_manifest = params.structure_manifest ?: "${workflow_dir}/${config.inputs.structure_manifest}"
def output_dir = params.output_dir ?: "${workflow_dir}/${config.output.base_dir}"
def config_path = params.config

// Log resolved parameters
log.info """
==============================================================================
GIGANTIC OCL PIPELINE
==============================================================================
Run Label           : ${config.run_label}
Species Set         : ${config.species_set_name}
Orthogroup Tool     : ${config.orthogroup_tool}
FASTA Embedding     : ${config.include_fasta_in_output}
Structure Manifest  : ${structure_manifest}
Output Directory    : ${output_dir}
Config File         : ${config_path}
==============================================================================
""".stripIndent()

// ============================================================================
// INPUT CHANNELS
// ============================================================================

// Read structure IDs from manifest
Channel
    .fromPath( structure_manifest )
    .splitCsv( header: true, sep: '\t' )
    .map { row -> row.structure_id }
    .set { structure_ids_channel }

// ============================================================================
// PROCESS 001: PREPARE INPUTS
// ============================================================================

process prepare_inputs {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-prepare_inputs.py \\
        --structure_id ${structure_id} \\
        --config ${config_path} \\
        --output_dir ${output_dir}
    """
}

// ============================================================================
// PROCESS 002: DETERMINE ORIGINS
// ============================================================================

process determine_origins {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-determine_origins.py \\
        --structure_id ${structure_id} \\
        --config ${config_path} \\
        --output_dir ${output_dir}
    """
}

// ============================================================================
// PROCESS 003: QUANTIFY CONSERVATION AND LOSS
// ============================================================================

process quantify_conservation_loss {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-quantify_conservation_loss.py \\
        --structure_id ${structure_id} \\
        --config ${config_path} \\
        --output_dir ${output_dir}
    """
}

// ============================================================================
// PROCESS 004: COMPREHENSIVE OCL ANALYSIS
// ============================================================================

process comprehensive_ocl_analysis {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-comprehensive_ocl_analysis.py \\
        --structure_id ${structure_id} \\
        --config ${config_path} \\
        --output_dir ${output_dir}
    """
}

// ============================================================================
// PROCESS 005: VALIDATE RESULTS
// ============================================================================

process validate_results {
    tag "structure_${structure_id}"

    input:
    val structure_id

    output:
    val structure_id, emit: structure_id

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-validate_results.py \\
        --structure_id ${structure_id} \\
        --config ${config_path} \\
        --output_dir ${output_dir}
    """
}

// ============================================================================
// PROCESS 006: WRITE RUN LOG
// ============================================================================

/*
 * Process 6: Write Run Log
 * Calls: scripts/006_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/006_ai-python-write_run_log.py \
        --workflow-name "ocl_analysis" \
        --subproject-name "orthogroups_X_ocl" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Run pipeline for each structure (parallel across structures, sequential per structure)
    prepare_inputs( structure_ids_channel )
    determine_origins( prepare_inputs.out.structure_id )
    quantify_conservation_loss( determine_origins.out.structure_id )
    comprehensive_ocl_analysis( quantify_conservation_loss.out.structure_id )
    validate_results( comprehensive_ocl_analysis.out.structure_id )

    // Write run log (FINAL STEP)
    write_run_log( validate_results.out.structure_id.collect() )
}

// ============================================================================
// WORKFLOW COMPLETION
// ============================================================================

workflow.onComplete {
    log.info """
    ==============================================================================
    GIGANTIC OCL PIPELINE - COMPLETED
    ==============================================================================
    Status      : ${workflow.success ? 'SUCCESS' : 'FAILED'}
    Duration    : ${workflow.duration}
    Run Label   : ${config.run_label}
    Results     : ${output_dir}
    Run log written to ai/logs/ in this workflow directory
    ==============================================================================
    """.stripIndent()
}

workflow.onError {
    log.error """
    ==============================================================================
    GIGANTIC OCL PIPELINE - ERROR
    ==============================================================================
    Error message: ${workflow.errorMessage}
    ==============================================================================
    """.stripIndent()
}
