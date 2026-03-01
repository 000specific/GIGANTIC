#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: STEP_1 RGS validation and preparation workflow
// Human: Eric Edsinger

nextflow.enable.dsl=2

// ============================================================================
// STEP_1 RGS Validation and Preparation Pipeline
// ============================================================================
//
// PURPOSE:
// Validate a single RGS (Reference Gene Set) FASTA file and prepare it for
// downstream STEP_2 homolog discovery.
//
// Usage: Each workflow copy processes ONE gene family. Copy the template,
//        configure rgs_config.yaml, then run.
//
// PROCESSES:
// 1. validate_rgs           - Validate RGS FASTA format, headers, duplicates
// (Symlinks for output_to_input created by RUN-workflow.sh after pipeline completes)
//
// INPUT:
// User places RGS FASTA file in INPUT_user/ and sets gene_family in config.
//
// OUTPUT:
// Validated RGS file in OUTPUT_pipeline/1-output/
//
// ============================================================================

// Load configuration from YAML
import org.yaml.snakeyaml.Yaml

def load_config() {
    def yaml = new Yaml()
    def config_file = file( "${projectDir}/../rgs_config.yaml" )
    if ( !config_file.exists() ) {
        error "Configuration file not found: ${config_file}"
    }
    return yaml.load( config_file.text )
}

def config = load_config()

// ============================================================================
// Parameters
// ============================================================================

params.output_dir = config.output?.base_dir ?: 'OUTPUT_pipeline'
params.gene_family = config.gene_family?.name ?: null
params.rgs_file = config.gene_family?.rgs_file ?: null

// ============================================================================
// Processes
// ============================================================================

// Process 1: Validate RGS FASTA file
process validate_rgs {
    tag "${gene_family}"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( rgs_fasta )

    output:
        tuple val( gene_family ), path( "1-output/1_ai-rgs-${gene_family}-validated.aa" ), emit: validated_rgs
        path "1-output"

    script:
    """
    mkdir -p 1-output

    # Run validation script
    python3 ${projectDir}/scripts/001_ai-python-validate_rgs.py \\
        --input ${rgs_fasta} \\
        --output "1-output/1_ai-rgs-${gene_family}-validated.aa" \\
        --gene-family "${gene_family}" \\
        --report "1-output/1_ai-rgs-${gene_family}-validation_report.txt" \\
        --log-file "1-output/1_ai-log-validate_rgs-${gene_family}.log"

    echo "RGS validation complete for ${gene_family}"
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
// pipeline completes. Real files only live in OUTPUT_pipeline/N-output/.

workflow {

    log.info """
    ========================================================================
    GIGANTIC trees_gene_families STEP_1 - RGS Validation and Preparation
    ========================================================================
    Gene family    : ${params.gene_family}
    RGS file       : ${params.rgs_file}
    Output directory: ${params.output_dir}
    ========================================================================
    """.stripIndent()

    // Validate critical parameters
    if ( !params.gene_family ) {
        error "gene_family not set in config! Edit rgs_config.yaml."
    }
    if ( !params.rgs_file ) {
        error "rgs_file not set in config! Edit rgs_config.yaml."
    }

    // Resolve RGS file path
    def workflow_dir = "${projectDir}/.."
    def rgs_path = file( "${workflow_dir}/${params.rgs_file}" )
    if ( !rgs_path.exists() ) {
        error "RGS file not found: ${params.rgs_file}\nExpected at: ${rgs_path}"
    }

    log.info "Validating: ${rgs_path}"

    // Create single-item channel
    rgs_channel = Channel.of( [ params.gene_family, rgs_path ] )

    // Process 1: Validate RGS file
    validate_rgs( rgs_channel )

    // NOTE: Symlinks from output_to_input/ to OUTPUT_pipeline/1-output/
    // are created by RUN-workflow.sh after pipeline completes.
}
