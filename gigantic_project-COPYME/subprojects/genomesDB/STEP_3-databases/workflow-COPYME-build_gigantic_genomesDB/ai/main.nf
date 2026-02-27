#!/usr/bin/env nextflow
/*
 * GIGANTIC genomesDB STEP_3 - Build BLAST Databases
 * AI: Claude Code | Opus 4.5 | 2026 February 27
 * Human: Eric Edsinger
 *
 * Purpose: Build per-genome BLAST protein databases for selected species
 *
 * Scripts:
 *   001: Filter species manifest (Include=YES only)
 *   002: Build per-genome BLAST databases
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.species_manifest = "../../output_to_input/species_selection_manifest.tsv"
params.proteomes_dir = "../../output_to_input/gigantic_proteomes"
params.output_dir = "OUTPUT_pipeline"
params.database_name = "gigantic-T1-blastp"
params.parallel_jobs = 4

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Filter Species Manifest
 * Calls: scripts/001_ai-python-filter_species_manifest.py
 */
process filter_species_manifest {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-filtered_species_manifest.tsv", emit: filtered_manifest
        path "1-output/1_ai-log-filter_species_manifest.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-filter_species_manifest.py \\
        --input-manifest ${projectDir}/../${params.species_manifest} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Build Per-Genome BLAST Databases
 * Calls: scripts/002_ai-python-build_per_genome_blastdbs.py
 */
process build_blast_databases {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    // Also publish to output_to_input for downstream subprojects
    publishDir "${projectDir}/../../output_to_input", mode: 'copy', overwrite: true, pattern: "2-output/${params.database_name}/**", saveAs: { filename -> filename.replace("2-output/", "") }

    input:
        path filtered_manifest

    output:
        path "2-output/${params.database_name}", emit: blastdb_dir
        path "2-output/2_ai-makeblastdb_commands.sh", emit: commands_log
        path "2-output/2_ai-log-build_per_genome_blastdbs.log", emit: log

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-build_per_genome_blastdbs.py \\
        --filtered-manifest ${filtered_manifest} \\
        --proteomes-dir ${projectDir}/../${params.proteomes_dir} \\
        --output-dir 2-output \\
        --output-to-input-dir 2-output \\
        --database-name ${params.database_name} \\
        --parallel ${params.parallel_jobs}
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Filter species manifest to Include=YES only
    filter_species_manifest()

    // Step 2: Build BLAST databases (depends on step 1)
    build_blast_databases(filter_species_manifest.out.filtered_manifest)
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC genomesDB STEP_3 Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Filtered species manifest (Include=YES only)"
        println "  2-output/: Per-genome BLAST protein databases"
        println ""
        println "BLAST databases copied to: ../../output_to_input/${params.database_name}/"
        println ""
        println "To use with blastp:"
        println "  blastp -db OUTPUT_pipeline/2-output/${params.database_name}/PHYLONAME-proteome.aa -query sequences.fasta"
    }
    println "========================================================================"
}
