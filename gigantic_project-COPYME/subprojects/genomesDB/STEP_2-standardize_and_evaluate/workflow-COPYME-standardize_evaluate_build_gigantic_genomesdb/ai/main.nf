#!/usr/bin/env nextflow
/*
 * GIGANTIC genomesDB STEP_2 - Standardize and Evaluate Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 February 27
 * Human: Eric Edsinger
 *
 * Purpose: Standardize proteomes/genomes with phylonames, clean data, run BUSCO,
 *          calculate assembly statistics, and generate quality summary
 *
 * Scripts:
 *   001: Standardize proteome phylonames
 *   002: Clean proteome invalid residues
 *   003: Standardize genome and annotation phylonames
 *   004: Calculate genome assembly statistics
 *   005: Run BUSCO proteome evaluation
 *   006: Summarize quality and generate species manifest
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.phylonames_mapping = "../../../phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv"
params.input_proteomes = "../../STEP_1-sources/output_to_input/T1_proteomes"
params.input_genomes = "../../STEP_1-sources/output_to_input/genomes"
params.input_gene_annotations = "../../STEP_1-sources/output_to_input/gene_annotations"
params.busco_lineages = "INPUT_user/busco_lineages.txt"
params.output_dir = "OUTPUT_pipeline"
params.busco_parallel = 4
params.busco_cpus_per_job = 4

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Standardize Proteome Phylonames
 * Calls: scripts/001_ai-python-standardize_proteome_phylonames.py
 */
process standardize_proteome_phylonames {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/gigantic_proteomes", emit: proteomes
        path "1-output/1_ai-standardization_manifest.tsv", emit: manifest
        path "1-output/1_ai-log-standardize_proteome_phylonames.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-standardize_proteome_phylonames.py \\
        --phylonames-mapping ${projectDir}/../${params.phylonames_mapping} \\
        --input-proteomes ${projectDir}/../${params.input_proteomes} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Clean Proteome Invalid Residues
 * Calls: scripts/002_ai-python-clean_proteome_invalid_residues.py
 */
process clean_proteome_invalid_residues {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteomes

    output:
        path "2-output/gigantic_proteomes_cleaned", emit: cleaned_proteomes
        path "2-output/2_ai-proteome_cleaning_summary.tsv", emit: summary
        path "2-output/2_ai-proteome_residue_corrections.tsv", emit: corrections
        path "2-output/2_ai-log-clean_proteome_invalid_residues.log", emit: log

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-clean_proteome_invalid_residues.py \\
        --proteomes-dir ${proteomes} \\
        --output-dir 2-output

    # Copy modified proteomes to expected output location
    # (script modifies in-place, NextFlow needs explicit output path)
    cp -r ${proteomes} 2-output/gigantic_proteomes_cleaned
    """
}

/*
 * Process 3: Standardize Genome and Annotation Phylonames
 * Calls: scripts/003_ai-python-standardize_genome_and_annotation_phylonames.py
 */
process standardize_genome_annotation_phylonames {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "3-output/gigantic_genomes", emit: genomes, optional: true
        path "3-output/gigantic_gene_annotations", emit: annotations, optional: true
        path "3-output/3_ai-standardization_manifest.tsv", emit: manifest
        path "3-output/3_ai-log-standardize_genome_and_annotation_phylonames.log", emit: log

    script:
    def genomes_arg = file("${projectDir}/../${params.input_genomes}").exists() ? "--input-genomes ${projectDir}/../${params.input_genomes}" : ""
    def annotations_arg = file("${projectDir}/../${params.input_gene_annotations}").exists() ? "--input-gene-annotations ${projectDir}/../${params.input_gene_annotations}" : ""
    """
    mkdir -p 3-output

    python3 ${projectDir}/scripts/003_ai-python-standardize_genome_and_annotation_phylonames.py \\
        --phylonames-mapping ${projectDir}/../${params.phylonames_mapping} \\
        --output-dir 3-output \\
        ${genomes_arg} \\
        ${annotations_arg}
    """
}

/*
 * Process 4: Calculate Genome Assembly Statistics
 * Calls: scripts/004_ai-python-calculate_genome_assembly_statistics.py
 */
process calculate_assembly_statistics {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path genomes

    output:
        path "4-output/4_ai-genome_assembly_statistics.tsv", emit: stats
        path "4-output/4_ai-log-calculate_genome_assembly_statistics.log", emit: log

    script:
    """
    mkdir -p 4-output

    python3 ${projectDir}/scripts/004_ai-python-calculate_genome_assembly_statistics.py \\
        --input-genomes ${genomes} \\
        --phylonames-mapping ${projectDir}/../${params.phylonames_mapping} \\
        --output-dir 4-output
    """
}

/*
 * Process 5: Run BUSCO Proteome Evaluation
 * Calls: scripts/005_ai-python-run_busco_proteome_evaluation.py
 */
process run_busco_evaluation {
    label 'busco'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path cleaned_proteomes

    output:
        path "5-output/5_ai-busco_summary.tsv", emit: summary
        path "5-output/busco_results", emit: results
        path "5-output/5_ai-log-run_busco_proteome_evaluation.log", emit: log

    script:
    """
    mkdir -p 5-output

    python3 ${projectDir}/scripts/005_ai-python-run_busco_proteome_evaluation.py \\
        --lineage-manifest ${projectDir}/../${params.busco_lineages} \\
        --input-proteomes ${cleaned_proteomes} \\
        --output-dir 5-output \\
        --parallel ${params.busco_parallel} \\
        --cpus-per-job ${params.busco_cpus_per_job}
    """
}

/*
 * Process 6: Summarize Quality and Generate Species Manifest
 * Calls: scripts/006_ai-python-summarize_quality_and_generate_species_manifest.py
 */
process summarize_quality {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    // NOTE: output_to_input is populated by STEP_4, not STEP_2
    // STEP_2 only produces OUTPUT_pipeline/ results for user evaluation

    input:
        path assembly_stats
        path busco_summary
        path proteome_manifest

    output:
        path "6-output/6_ai-comprehensive_quality_summary.tsv", emit: summary
        path "6-output/6_ai-species_selection_manifest.tsv", emit: manifest
        path "6-output/6_ai-log-summarize_quality.log", emit: log

    script:
    """
    mkdir -p 6-output

    python3 ${projectDir}/scripts/006_ai-python-summarize_quality_and_generate_species_manifest.py \\
        --assembly-stats ${assembly_stats} \\
        --busco-summary ${busco_summary} \\
        --proteome-manifest ${proteome_manifest} \\
        --output-dir 6-output \\
        --output-to-input-dir 6-output
    """
}

/*
 * Process 7: Copy species manifest to output_to_input
 * Note: Proteomes are NOT copied here. STEP_4 creates the final species set in output_to_input/ after user review.
 */
process copy_manifest_to_output_to_input {
    label 'local'

    input:
        path species_manifest

    output:
        path "output_to_input_done.txt", emit: done

    script:
    """
    # Create output_to_input directory
    mkdir -p ${projectDir}/../../output_to_input

    # Copy species manifest
    cp ${species_manifest} ${projectDir}/../../output_to_input/species_selection_manifest.tsv

    echo "Copied manifest to output_to_input at \$(date)" > output_to_input_done.txt
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Standardize proteome phylonames
    standardize_proteome_phylonames()

    // Step 2: Clean proteome invalid residues
    clean_proteome_invalid_residues(standardize_proteome_phylonames.out.proteomes)

    // Step 3: Standardize genome and annotation phylonames
    standardize_genome_annotation_phylonames()

    // Step 4: Calculate assembly statistics (depends on step 3)
    calculate_assembly_statistics(standardize_genome_annotation_phylonames.out.genomes)

    // Step 5: Run BUSCO evaluation (depends on step 2)
    run_busco_evaluation(clean_proteome_invalid_residues.out.cleaned_proteomes)

    // Step 6: Summarize quality (depends on steps 1, 4, 5)
    summarize_quality(
        calculate_assembly_statistics.out.stats,
        run_busco_evaluation.out.summary,
        standardize_proteome_phylonames.out.manifest
    )

    // Step 7: Copy manifest to output_to_input
    // Note: Proteomes are copied to output_to_input by STEP_4 (after user review)
    copy_manifest_to_output_to_input(
        summarize_quality.out.manifest
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC genomesDB STEP_2 Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Standardized proteomes with phylonames"
        println "  2-output/: Cleaned proteomes (invalid residues fixed)"
        println "  3-output/: Standardized genomes and annotations (symlinks)"
        println "  4-output/: Genome assembly statistics"
        println "  5-output/: BUSCO proteome completeness evaluation"
        println "  6-output/: Quality summary and species manifest"
        println ""
        println "Next: Run STEP_4 to create final species set in output_to_input/"
    }
    println "========================================================================"
}
