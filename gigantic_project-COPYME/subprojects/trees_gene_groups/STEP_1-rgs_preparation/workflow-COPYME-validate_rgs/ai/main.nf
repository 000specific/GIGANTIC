#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: STEP_1 RGS validation and preparation workflow
// Human: Eric Edsinger

nextflow.enable.dsl=2

// ============================================================================
// STEP_1 RGS Validation and Preparation Pipeline
// ============================================================================
//
// PURPOSE:
// Validate RGS (Reference Gene Set) FASTA files and prepare them for
// downstream STEP_2 homolog discovery.
//
// PROCESSES:
// 1. validate_rgs           - Validate RGS FASTA format, headers, duplicates
// (Symlinks for output_to_input created by RUN-workflow.sh after pipeline completes)
//
// INPUT:
// User places RGS FASTA files in INPUT_user/ and creates rgs_manifest.tsv
//
// OUTPUT:
// Validated RGS files in OUTPUT_pipeline/<gene_family>/1-output/
// Validated RGS symlinked to output_to_input/ (by RUN-workflow.sh)
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
params.rgs_manifest = "${projectDir}/../INPUT_user/rgs_manifest.tsv"
params.input_user_dir = "${projectDir}/../INPUT_user"

// ============================================================================
// Helper Functions
// ============================================================================

def load_rgs_manifest() {
    // Read manifest to get gene family names and RGS filenames
    def manifest_file = file( params.rgs_manifest )
    if ( !manifest_file.exists() ) {
        error "RGS manifest not found: ${params.rgs_manifest}"
    }

    def entries = []
    manifest_file.eachLine { line ->
        line = line.trim()
        if ( line && !line.startsWith( '#' ) ) {
            def parts = line.split( '\t' )
            if ( parts.size() >= 2 ) {
                entries.add( [ parts[ 0 ].trim(), parts[ 1 ].trim() ] )
            }
        }
    }

    if ( entries.isEmpty() ) {
        error "No gene families found in manifest: ${params.rgs_manifest}"
    }

    return entries
}

// ============================================================================
// Processes
// ============================================================================

// Process 1: Validate RGS FASTA files
process validate_rgs {
    tag "${gene_family}"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( rgs_fasta )

    output:
        tuple val( gene_family ), path( "1-output/1_ai-RGS-${gene_family}-validated.aa" ), emit: validated_rgs
        path "1-output"

    script:
    """
    mkdir -p 1-output

    # Run validation script
    python3 ${projectDir}/scripts/001_ai-python-validate_rgs.py \\
        --input ${rgs_fasta} \\
        --output "1-output/1_ai-RGS-${gene_family}-validated.aa" \\
        --gene-family "${gene_family}" \\
        --report "1-output/1_ai-RGS-${gene_family}-validation_report.txt" \\
        --log-file "1-output/1_ai-log-validate_rgs-${gene_family}.log"

    echo "RGS validation complete for ${gene_family}"
    """
}

// NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
// pipeline completes. Real files only live in OUTPUT_pipeline/<gene_family>/1-output/.

// ============================================================================
// Workflow
// ============================================================================

workflow {

    log.info """
    ========================================================================
    GIGANTIC trees_gene_families STEP_1 - RGS Validation and Preparation
    ========================================================================
    RGS manifest  : ${params.rgs_manifest}
    Input directory: ${params.input_user_dir}
    Output directory: ${params.output_dir}
    ========================================================================
    """.stripIndent()

    // Load gene families and RGS filenames from manifest
    def manifest_entries = load_rgs_manifest()
    log.info "Gene families to validate: ${manifest_entries.collect{ it[0] }.join( ', ' )}"

    // Create channel from manifest entries [gene_family, rgs_fasta_path]
    rgs_channel = Channel.from( manifest_entries )
        .map { gene_family, rgs_filename ->
            def rgs_file = file( "${params.input_user_dir}/${rgs_filename}" )
            if ( !rgs_file.exists() ) {
                error "RGS file not found: ${rgs_file} (from manifest entry: ${gene_family}\t${rgs_filename})"
            }
            [ gene_family, rgs_file ]
        }

    // Process 1: Validate RGS files
    validate_rgs( rgs_channel )

    // NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
    // pipeline completes. Real files only live in OUTPUT_pipeline/<gene_family>/1-output/.
}
