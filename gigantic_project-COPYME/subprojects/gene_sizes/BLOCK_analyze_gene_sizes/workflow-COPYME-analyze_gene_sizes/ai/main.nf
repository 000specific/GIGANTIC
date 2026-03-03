#!/usr/bin/env nextflow
/*
 * GIGANTIC gene_sizes - Analyze Gene Sizes Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 March 04
 * Human: Eric Edsinger
 *
 * Purpose: Compute gene structure metrics from user-provided CDS interval data,
 *          compute genome-wide statistics and relative ranks, and compile
 *          cross-species summaries for downstream analyses.
 *
 * Input Design:
 *   The user provides per-species gene structure TSV files in INPUT_user/.
 *   Each file contains Source_Gene_ID + CDS intervals pre-extracted from
 *   species-specific GFF/GTF files. This follows GIGANTIC's established
 *   pattern where users handle species-specific parsing.
 *
 * Scripts:
 *   001: Validate user-provided gene structure inputs
 *   002: Extract gene metrics per species (parallelized)
 *   003: Compute genome-wide statistics and ranks per species (parallelized)
 *   004: Compile cross-species summary
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.input_user_dir = "INPUT_user"
params.gigantic_species_list = ""
params.proteome_dir = ""
params.output_dir = "OUTPUT_pipeline"

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate Gene Size Inputs
 * Calls: scripts/001_ai-python-validate_gene_size_inputs.py
 *
 * Validates user-provided per-species TSV files against the GIGANTIC species
 * set. Determines which species have valid gene structure data (PROCESSED),
 * which have no data (SKIPPED_NO_DATA), and which have incomplete data
 * (SKIPPED_INCOMPLETE).
 */
process validate_gene_size_inputs {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-species_processing_status.tsv", emit: status
        path "1-output/1_ai-processable_species_list.txt", emit: species_list
        path "1-output/1_ai-species_count.txt", emit: species_count
        path "1-output/1_ai-log-validate_gene_size_inputs.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_gene_size_inputs.py \\
        --input-dir ${projectDir}/../${params.input_user_dir} \\
        --gigantic-species-list ${projectDir}/../${params.gigantic_species_list} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Extract Gene Metrics (per species, parallelized)
 * Calls: scripts/002_ai-python-extract_gene_metrics.py
 *
 * Reads user-provided CDS intervals and computes per-gene metrics.
 * Optionally links source gene IDs to GIGANTIC identifiers via proteome.
 */
process extract_gene_metrics {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}/2-output", mode: 'copy', overwrite: true

    input:
        tuple val(genus_species), val(gene_structure_file), val(proteome_file)

    output:
        path "2_ai-gene_metrics-${genus_species}.tsv", emit: metrics
        path "2_ai-log-extract_gene_metrics-${genus_species}.log", emit: log

    script:
    def proteome_arg = proteome_file ? "--proteome-file ${proteome_file}" : ""
    """
    python3 ${projectDir}/scripts/002_ai-python-extract_gene_metrics.py \\
        --gene-structure-file ${gene_structure_file} \\
        ${proteome_arg} \\
        --genus-species ${genus_species} \\
        --output-dir .
    """
}

/*
 * Process 3: Compute Genome-Wide Statistics and Ranks (per species)
 * Calls: scripts/003_ai-python-compute_genome_wide_statistics.py
 */
process compute_genome_wide_statistics {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}/3-output", mode: 'copy', overwrite: true

    input:
        tuple val(genus_species), path(gene_metrics_file)

    output:
        path "3_ai-ranked_gene_metrics-${genus_species}.tsv", emit: ranked_metrics
        path "3_ai-genome_summary-${genus_species}.tsv", emit: genome_summary
        path "3_ai-log-compute_genome_wide_statistics-${genus_species}.log", emit: log

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-compute_genome_wide_statistics.py \\
        --gene-metrics ${gene_metrics_file} \\
        --genus-species ${genus_species} \\
        --output-dir .
    """
}

/*
 * Process 4: Compile Cross-Species Summary
 * Calls: scripts/004_ai-python-compile_cross_species_summary.py
 */
process compile_cross_species_summary {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path genome_summaries
        path ranked_metrics
        path species_status_file
        val species_count
        val gigantic_species_count

    output:
        path "4-output/4_ai-cross_species_summary.tsv", emit: summary
        path "4-output/4_ai-species_processing_status.tsv", emit: status
        path "4-output/species*_gigantic_gene_metrics", emit: gene_metrics_dir
        path "4-output/species*_gigantic_gene_sizes_summary", emit: gene_sizes_summary_dir
        path "4-output/4_ai-log-compile_cross_species_summary.log", emit: log

    script:
    """
    mkdir -p 4-output
    mkdir -p genome_summaries_collected
    mkdir -p ranked_metrics_collected

    cp ${genome_summaries} genome_summaries_collected/
    cp ${ranked_metrics} ranked_metrics_collected/

    python3 ${projectDir}/scripts/004_ai-python-compile_cross_species_summary.py \\
        --genome-summaries-dir genome_summaries_collected \\
        --ranked-metrics-dir ranked_metrics_collected \\
        --species-status-file ${species_status_file} \\
        --species-count ${species_count} \\
        --gigantic-species-count ${gigantic_species_count} \\
        --output-dir 4-output
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Validate user-provided gene structure inputs
    validate_gene_size_inputs()

    // Read species count (processable species)
    species_count = validate_gene_size_inputs.out.species_count
        .map { file -> file.text.trim().toInteger() }

    // Count total GIGANTIC species from species list file
    gigantic_species_count = Channel
        .fromPath( "${projectDir}/../${params.gigantic_species_list}" )
        .splitText()
        .map { it.trim() }
        .filter { it && !it.startsWith('#') }
        .count()

    // Parse processable species list to create per-species channel
    // Each line is a Genus_species name
    species_channel = validate_gene_size_inputs.out.species_list
        .splitText()
        .map { it.trim() }
        .filter { it }
        .map { genus_species ->
            def gene_structure_file = "${projectDir}/../${params.input_user_dir}/${genus_species}-gene_coordinates.tsv"
            def proteome_file = params.proteome_dir ? file("${projectDir}/../${params.proteome_dir}/${genus_species}.aa") : null
            def proteome_path = ( proteome_file && proteome_file.exists() ) ? proteome_file.toString() : ""
            tuple( genus_species, gene_structure_file, proteome_path )
        }

    // Step 2: Extract gene metrics (parallelized per species)
    extract_gene_metrics( species_channel )

    // Create channel for Step 3: pair species name with metrics file
    metrics_for_ranking = extract_gene_metrics.out.metrics
        .map { metrics_file ->
            def genus_species = metrics_file.name.replaceAll( '2_ai-gene_metrics-', '' ).replaceAll( '\\.tsv$', '' )
            tuple( genus_species, metrics_file )
        }

    // Step 3: Compute genome-wide statistics and ranks (parallelized per species)
    compute_genome_wide_statistics( metrics_for_ranking )

    // Step 4: Compile cross-species summary (collects all species)
    compile_cross_species_summary(
        compute_genome_wide_statistics.out.genome_summary.collect(),
        compute_genome_wide_statistics.out.ranked_metrics.collect(),
        validate_gene_size_inputs.out.status,
        species_count,
        gigantic_species_count
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC gene_sizes Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Species processing status and processable species list"
        println "  2-output/: Per-species gene metrics"
        println "  3-output/: Ranked metrics and genome summaries"
        println "  4-output/: Cross-species summary and downstream directories"
        println ""
        println "Symlinks created in output_to_input/BLOCK_analyze_gene_sizes/ (by RUN-workflow.sh)"
        println "  speciesN_gigantic_gene_metrics/         Per-species ranked gene metrics"
        println "  speciesN_gigantic_gene_sizes_summary/   Cross-species summary statistics"
    }
    println "========================================================================"
}
