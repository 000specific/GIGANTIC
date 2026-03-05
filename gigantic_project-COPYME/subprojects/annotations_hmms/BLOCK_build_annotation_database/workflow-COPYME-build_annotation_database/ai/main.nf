#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Nextflow pipeline for building standardized annotation database
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// Annotation Database Builder Pipeline
// =============================================================================
//
// Sixteen-step pipeline:
//   1.  Discover available tool outputs from sibling BLOCKs
//   2.  Download GO ontology (with caching)
//   3.  Parse InterProScan results into 19 flat database directories + GO
//   4.  Parse DeepLoc results
//   5.  Parse SignalP results
//   6.  Parse tmbed results
//   7.  Parse MetaPredict results
//   8.  Compile annotation statistics across all databases
//   9.  Analyze cross-tool consistency
//   10. Analyze annotation quality
//   11. Analyze protein complexity
//   12. Analyze functional categories (GO)
//   13. Analyze domain architecture
//   14. Detect annotation outliers
//   15. Generate visualization data
//   16. Analyze phylogenetic patterns
//
// Database structure:
//   All 24 databases are flat peers under OUTPUT_pipeline/annotation_databases/:
//     annotation_databases/database_pfam/
//     annotation_databases/database_gene3d/
//     annotation_databases/database_interproscan/
//     annotation_databases/database_go/
//     annotation_databases/database_deeploc/
//     annotation_databases/database_signalp/
//     annotation_databases/database_tmbed/
//     annotation_databases/database_metapredict/
//     ... (24 total)
//
// The pipeline auto-discovers which tool outputs are available.
// Parsers 003-007 only run if their corresponding tool BLOCK has results.
//
// Scripts read databases from OUTPUT_pipeline/annotation_databases/ (not from
// Nextflow work directories). Parser log files serve as ordering signals so
// that downstream scripts wait for parsers to finish publishing.
//
// Symlinks for output_to_input/BLOCK_build_annotation_database/ are created by RUN-workflow.sh after pipeline completes
// =============================================================================

scripts_dir = "${projectDir}/scripts"

process discover_tool_outputs {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    output:
        path '1_ai-tool_discovery_manifest.tsv', emit: discovery_manifest
        path '1_ai-log-discover_tool_outputs.log'

    script:
    """
    python3 ${scripts_dir}/001_ai-python-discover_tool_outputs.py \
        --annotations-dir ${projectDir}/../../../ \
        --output-dir .
    """
}

process download_go_ontology {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    output:
        path '2_ai-go_term_lookup.tsv', emit: go_lookup
        path '2_ai-go_basic.obo', emit: go_obo
        path '2_ai-log-download_go_ontology.log'

    script:
    """
    python3 ${scripts_dir}/002_ai-python-download_go_ontology.py \
        --go-url '${params.go_ontology_url}' \
        --cache-days ${params.go_ontology_cache_days} \
        --output-dir .
    """
}

// =============================================================================
// Parser processes (003-007)
//
// Each parser publishes database directories to annotation_databases/ and
// log files to N-output/. The log file is emitted as a signal channel so
// downstream processes can wait for parsers to finish without staging the
// (potentially large) database directories into their work directories.
// =============================================================================

process parse_interproscan {
    publishDir "${params.output_dir}/annotation_databases", mode: 'copy', pattern: 'database_*/'
    publishDir "${params.output_dir}/3-output", mode: 'copy', pattern: '*.log'

    input:
        path discovery_manifest
        path go_lookup

    output:
        path 'database_*/', emit: databases
        path '3_ai-log-parse_interproscan.log', emit: log

    when:
        discovery_manifest.text.contains("interproscan\tyes")

    script:
    def proteomes_arg = params.proteomes_dir ? "--proteomes-dir ${projectDir}/../${params.proteomes_dir}" : ""
    """
    python3 ${scripts_dir}/003_ai-python-parse_interproscan.py \
        --discovery-manifest ${discovery_manifest} \
        --go-lookup ${go_lookup} \
        --annotations-dir ${projectDir}/../../../ \
        ${proteomes_arg} \
        --output-dir .
    """
}

process parse_deeploc {
    publishDir "${params.output_dir}/annotation_databases", mode: 'copy', pattern: 'database_*/'
    publishDir "${params.output_dir}/4-output", mode: 'copy', pattern: '*.log'

    input:
        path discovery_manifest

    output:
        path 'database_deeploc/', emit: databases
        path '4_ai-log-parse_deeploc.log', emit: log

    when:
        discovery_manifest.text.contains("deeploc\tyes")

    script:
    def proteomes_arg = params.proteomes_dir ? "--proteomes-dir ${projectDir}/../${params.proteomes_dir}" : ""
    """
    python3 ${scripts_dir}/004_ai-python-parse_deeploc.py \
        --discovery-manifest ${discovery_manifest} \
        --annotations-dir ${projectDir}/../../../ \
        ${proteomes_arg} \
        --output-dir .
    """
}

process parse_signalp {
    publishDir "${params.output_dir}/annotation_databases", mode: 'copy', pattern: 'database_*/'
    publishDir "${params.output_dir}/5-output", mode: 'copy', pattern: '*.log'

    input:
        path discovery_manifest

    output:
        path 'database_signalp/', emit: databases
        path '5_ai-log-parse_signalp.log', emit: log

    when:
        discovery_manifest.text.contains("signalp\tyes")

    script:
    def proteomes_arg = params.proteomes_dir ? "--proteomes-dir ${projectDir}/../${params.proteomes_dir}" : ""
    """
    python3 ${scripts_dir}/005_ai-python-parse_signalp.py \
        --discovery-manifest ${discovery_manifest} \
        --annotations-dir ${projectDir}/../../../ \
        ${proteomes_arg} \
        --output-dir .
    """
}

process parse_tmbed {
    publishDir "${params.output_dir}/annotation_databases", mode: 'copy', pattern: 'database_*/'
    publishDir "${params.output_dir}/6-output", mode: 'copy', pattern: '*.log'

    input:
        path discovery_manifest

    output:
        path 'database_tmbed/', emit: databases
        path '6_ai-log-parse_tmbed.log', emit: log

    when:
        discovery_manifest.text.contains("tmbed\tyes")

    script:
    def proteomes_arg = params.proteomes_dir ? "--proteomes-dir ${projectDir}/../${params.proteomes_dir}" : ""
    """
    python3 ${scripts_dir}/006_ai-python-parse_tmbed.py \
        --discovery-manifest ${discovery_manifest} \
        --annotations-dir ${projectDir}/../../../ \
        ${proteomes_arg} \
        --output-dir .
    """
}

process parse_metapredict {
    publishDir "${params.output_dir}/annotation_databases", mode: 'copy', pattern: 'database_*/'
    publishDir "${params.output_dir}/7-output", mode: 'copy', pattern: '*.log'

    input:
        path discovery_manifest

    output:
        path 'database_metapredict/', emit: databases
        path '7_ai-log-parse_metapredict.log', emit: log

    when:
        discovery_manifest.text.contains("metapredict\tyes")

    script:
    def proteomes_arg = params.proteomes_dir ? "--proteomes-dir ${projectDir}/../${params.proteomes_dir}" : ""
    """
    python3 ${scripts_dir}/007_ai-python-parse_metapredict.py \
        --discovery-manifest ${discovery_manifest} \
        --annotations-dir ${projectDir}/../../../ \
        ${proteomes_arg} \
        --output-dir .
    """
}

// =============================================================================
// Step 8: Compile annotation statistics
//
// Reads from the published annotation_databases/ directory (not from Nextflow
// work dirs). Parser log signals (val inputs) ensure this process waits for
// all parsers to finish publishing before it reads the databases.
// =============================================================================

process compile_annotation_statistics {
    publishDir "${params.output_dir}/8-output", mode: 'copy'

    input:
        path discovery_manifest
        val interproscan_signal
        val deeploc_signal
        val signalp_signal
        val tmbed_signal
        val metapredict_signal

    output:
        path '8_ai-annotation_statistics.tsv', emit: statistics
        path '8_ai-database_completeness.tsv', emit: completeness
        path '8_ai-log-compile_annotation_statistics.log'

    script:
    """
    python3 ${scripts_dir}/008_ai-python-compile_annotation_statistics.py \
        --discovery-manifest ${discovery_manifest} \
        --database-dir ${params.output_dir}/annotation_databases \
        --output-dir .
    """
}

// =============================================================================
// Steps 9-16: Analysis processes
//
// Scripts 009, 011, 012, 013 need --database-dir to read annotation databases.
// They use the published annotation_databases/ path (not Nextflow work dirs).
// Scripts 010, 014, 015, 016 only need the statistics TSV from script 008.
//
// All analysis processes run in parallel after statistics compilation.
// =============================================================================

process analyze_cross_tool_consistency {
    publishDir "${params.output_dir}/9-output", mode: 'copy'

    input:
        path statistics

    output:
        path '9_ai-cross_tool_consistency.tsv', emit: consistency
        path '9_ai-log-analyze_cross_tool_consistency.log'

    script:
    """
    python3 ${scripts_dir}/009_ai-python-analyze_cross_tool_consistency.py \
        --statistics ${statistics} \
        --database-dir ${params.output_dir}/annotation_databases \
        --output-dir .
    """
}

process analyze_annotation_quality {
    publishDir "${params.output_dir}/10-output", mode: 'copy'

    input:
        path statistics

    output:
        path '10_ai-annotation_quality.tsv', emit: quality
        path '10_ai-log-analyze_annotation_quality.log'

    script:
    """
    python3 ${scripts_dir}/010_ai-python-analyze_annotation_quality.py \
        --statistics ${statistics} \
        --output-dir .
    """
}

process analyze_protein_complexity {
    publishDir "${params.output_dir}/11-output", mode: 'copy'

    input:
        path statistics

    output:
        path '11_ai-protein_complexity.tsv', emit: complexity
        path '11_ai-log-analyze_protein_complexity.log'

    script:
    """
    python3 ${scripts_dir}/011_ai-python-analyze_protein_complexity.py \
        --statistics ${statistics} \
        --database-dir ${params.output_dir}/annotation_databases \
        --output-dir .
    """
}

process analyze_functional_categories {
    publishDir "${params.output_dir}/12-output", mode: 'copy'

    input:
        path statistics

    output:
        path '12_ai-functional_categories.tsv', emit: categories
        path '12_ai-log-analyze_functional_categories.log'

    script:
    """
    python3 ${scripts_dir}/012_ai-python-analyze_functional_categories.py \
        --statistics ${statistics} \
        --database-dir ${params.output_dir}/annotation_databases \
        --output-dir .
    """
}

process analyze_domain_architecture {
    publishDir "${params.output_dir}/13-output", mode: 'copy'

    input:
        path statistics

    output:
        path '13_ai-domain_architecture.tsv', emit: architecture
        path '13_ai-log-analyze_domain_architecture.log'

    script:
    """
    python3 ${scripts_dir}/013_ai-python-analyze_domain_architecture.py \
        --statistics ${statistics} \
        --database-dir ${params.output_dir}/annotation_databases \
        --output-dir .
    """
}

process detect_annotation_outliers {
    publishDir "${params.output_dir}/14-output", mode: 'copy'

    input:
        path statistics

    output:
        path '14_ai-annotation_outliers.tsv', emit: outliers
        path '14_ai-log-detect_annotation_outliers.log'

    script:
    """
    python3 ${scripts_dir}/014_ai-python-detect_annotation_outliers.py \
        --statistics ${statistics} \
        --output-dir .
    """
}

process generate_visualization_data {
    publishDir "${params.output_dir}/15-output", mode: 'copy'

    input:
        path statistics

    output:
        path '15_ai-visualization_heatmap_data.tsv', emit: heatmap
        path '15_ai-visualization_zscore_data.tsv', emit: zscore
        path '15_ai-log-generate_visualization_data.log'

    script:
    """
    python3 ${scripts_dir}/015_ai-python-generate_visualization_data.py \
        --statistics ${statistics} \
        --output-dir .
    """
}

process analyze_phylogenetic_patterns {
    publishDir "${params.output_dir}/16-output", mode: 'copy'

    input:
        path statistics

    output:
        path '16_ai-phylogenetic_patterns.tsv', emit: patterns
        path '16_ai-log-analyze_phylogenetic_patterns.log'

    script:
    """
    python3 ${scripts_dir}/016_ai-python-analyze_phylogenetic_patterns.py \
        --statistics ${statistics} \
        --config-file ${projectDir}/../annotation_database_config.yaml \
        --output-dir .
    """
}

/*
 * Process 17: Write Run Log
 * Calls: scripts/017_ai-python-write_run_log.py
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
    python3 ${projectDir}/scripts/017_ai-python-write_run_log.py \
        --workflow-name "build_annotation_database" \
        --subproject-name "annotations_hmms" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================
// Parsers 003-007 use `when:` to conditionally run based on tool availability.
// Their log files serve as ordering signals (val inputs) for compile_statistics.
// Analysis processes 009-016 run in parallel after statistics compilation.
// ============================================================================
workflow {
    // Step 1-2: Discovery and GO ontology
    discover_tool_outputs()
    download_go_ontology()

    // Step 3-7: Parse tool outputs (conditional on availability)
    parse_interproscan( discover_tool_outputs.out.discovery_manifest, download_go_ontology.out.go_lookup )
    parse_deeploc( discover_tool_outputs.out.discovery_manifest )
    parse_signalp( discover_tool_outputs.out.discovery_manifest )
    parse_tmbed( discover_tool_outputs.out.discovery_manifest )
    parse_metapredict( discover_tool_outputs.out.discovery_manifest )

    // Step 8: Compile statistics from published annotation_databases/
    // Parser log signals (val inputs) ensure ordering without staging databases
    compile_annotation_statistics(
        discover_tool_outputs.out.discovery_manifest,
        parse_interproscan.out.log.ifEmpty( 'SKIP' ),
        parse_deeploc.out.log.ifEmpty( 'SKIP' ),
        parse_signalp.out.log.ifEmpty( 'SKIP' ),
        parse_tmbed.out.log.ifEmpty( 'SKIP' ),
        parse_metapredict.out.log.ifEmpty( 'SKIP' )
    )

    // Step 9-16: Analysis processes (run in parallel after statistics)
    analyze_cross_tool_consistency( compile_annotation_statistics.out.statistics )
    analyze_annotation_quality( compile_annotation_statistics.out.statistics )
    analyze_protein_complexity( compile_annotation_statistics.out.statistics )
    analyze_functional_categories( compile_annotation_statistics.out.statistics )
    analyze_domain_architecture( compile_annotation_statistics.out.statistics )
    detect_annotation_outliers( compile_annotation_statistics.out.statistics )
    generate_visualization_data( compile_annotation_statistics.out.statistics )
    analyze_phylogenetic_patterns( compile_annotation_statistics.out.statistics )

    // Write run log (FINAL STEP)
    // Wait for all 8 parallel analysis processes to complete
    all_analyses_done = analyze_cross_tool_consistency.out.consistency
        .mix( analyze_annotation_quality.out.quality )
        .mix( analyze_protein_complexity.out.complexity )
        .mix( analyze_functional_categories.out.categories )
        .mix( analyze_domain_architecture.out.architecture )
        .mix( detect_annotation_outliers.out.outliers )
        .mix( generate_visualization_data.out.heatmap )
        .mix( analyze_phylogenetic_patterns.out.patterns )
        .collect()
    write_run_log( all_analyses_done )
}
