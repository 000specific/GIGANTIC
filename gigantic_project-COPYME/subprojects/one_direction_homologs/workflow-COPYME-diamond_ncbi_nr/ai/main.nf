#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: DIAMOND NCBI nr one-direction homolog search pipeline
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// ============================================================================
// GIGANTIC One-Direction Homologs Pipeline
// ============================================================================
//
// Searches species proteomes against NCBI nr database using DIAMOND.
// Identifies top hits, self-hits vs non-self-hits, per-species statistics.
//
// 6-step pipeline (each step publishes documented output to OUTPUT_pipeline/):
//   001: Validate proteomes          -> 1-output/
//   002: Split proteomes into N parts -> 2-output/
//   003: DIAMOND search per split     -> 3-output/  (massively parallel)
//   004: Combine results per species  -> 4-output/
//   005: Identify top self/non-self   -> 5-output/
//   006: Compile master statistics    -> 6-output/
//
// All real output files go to OUTPUT_pipeline/N-output/ directories.
// Symlinks for output_to_input/ are created by
// RUN-workflow.sh after the pipeline completes (not by NextFlow).
//
// Research documentation: Every step produces visible, documented output
// in OUTPUT_pipeline/. Nothing is passed silently between steps.
//
// ============================================================================


// ----------------------------------------------------------------------------
// Process 1: Validate proteomes and manifest
// ----------------------------------------------------------------------------
// Input:  User-provided proteome manifest (species_name, proteome_path, phyloname)
// Output: Validated manifest with sequence counts added
// Log:    1_ai-log-validate_proteomes.log
// ----------------------------------------------------------------------------
process validate_proteomes {
    tag "validate"

    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        path manifest

    output:
        path "1_ai-validated_proteome_manifest.tsv", emit: validated_manifest
        path "1_ai-log-validate_proteomes.log", emit: log

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-validate_proteomes.py \
        --manifest ${manifest} \
        --output-dir .
    """
}


// ----------------------------------------------------------------------------
// Process 2: Split proteomes into N parts for parallel DIAMOND search
// ----------------------------------------------------------------------------
// Input:  Validated manifest from step 1
// Output: Split FASTA files + job manifest documenting every split
// Log:    2_ai-log-split_proteomes.log
// ----------------------------------------------------------------------------
process split_proteomes {
    tag "split"

    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        path validated_manifest

    output:
        path "splits/*.fasta", emit: split_fastas
        path "2_ai-diamond_job_manifest.tsv", emit: job_manifest
        path "2_ai-log-split_proteomes.log", emit: log

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-split_proteomes_for_diamond.py \
        --manifest ${validated_manifest} \
        --output-dir . \
        --num-parts ${params.num_parts}
    """
}


// ----------------------------------------------------------------------------
// Process 3: DIAMOND blastp search per split file
// ----------------------------------------------------------------------------
// Input:  One split FASTA file
// Output: DIAMOND results (15-column TSV including stitle, full_qseq, full_sseq)
// Note:   This process runs massively in parallel (species x parts)
// ----------------------------------------------------------------------------
process diamond_search {
    tag "${split_fasta.simpleName}"

    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        path split_fasta

    output:
        path "${split_fasta.simpleName}_diamond.tsv", emit: diamond_results

    script:
    """
    bash ${projectDir}/scripts/003_ai-bash-run_diamond_search.sh \
        ${split_fasta} \
        ${params.diamond_database} \
        ${split_fasta.simpleName}_diamond.tsv \
        ${params.evalue} \
        ${params.max_target_sequences} \
        ${params.threads_per_job}
    """
}


// ----------------------------------------------------------------------------
// Process 4: Combine DIAMOND results per species
// ----------------------------------------------------------------------------
// Input:  All N split DIAMOND result files for one species
// Output: Single combined file per species + log documenting parts combined
// Log:    4_ai-log-combine_diamond_results.log
// ----------------------------------------------------------------------------
process combine_results {
    tag "${species_name}"

    publishDir "${params.output_dir}/4-output", mode: 'copy'

    input:
        tuple val(species_name), path(diamond_files)

    output:
        path "combined_${species_name}.tsv", emit: combined_results
        path "4_ai-log-combine_diamond_results.log", emit: log

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-combine_diamond_results.py \
        --species-name ${species_name} \
        --input-files ${diamond_files} \
        --output-dir .
    """
}


// ----------------------------------------------------------------------------
// Process 5: Identify top self/non-self hits per species
// ----------------------------------------------------------------------------
// Input:  Combined DIAMOND results for one species
// Output: Per-protein top hit analysis + species-level statistics
// Log:    5_ai-log-identify_top_hits.log
//
// This is the core analysis step:
//   - For each query protein, finds top 10 NCBI nr hits
//   - Identifies top non-self hit (first hit with different sequence)
//   - Identifies top self-hit (first hit with identical sequence)
//   - Records NCBI headers and full sequences for each
// ----------------------------------------------------------------------------
process identify_top_hits {
    tag "${combined_file.simpleName}"

    publishDir "${params.output_dir}/5-output", mode: 'copy'

    input:
        path combined_file

    output:
        path "*_top_hits.tsv", emit: top_hits
        path "*_statistics.tsv", emit: statistics
        path "5_ai-log-identify_top_hits.log", emit: log

    script:
    // Extract species name from filename: combined_{species_name}.tsv
    def species_name = combined_file.simpleName.replaceFirst( /^combined_/, '' )
    """
    python3 ${projectDir}/scripts/005_ai-python-identify_top_hits.py \
        --input-file ${combined_file} \
        --output-dir . \
        --species-name ${species_name}
    """
}


// ----------------------------------------------------------------------------
// Process 6: Compile master statistics across all species
// ----------------------------------------------------------------------------
// Input:  Individual per-species statistics files from step 5
// Output: Master summary table (one row per species)
// Log:    6_ai-log-compile_statistics.log
// ----------------------------------------------------------------------------
process compile_statistics {
    tag "compile"

    publishDir "${params.output_dir}/6-output", mode: 'copy'

    input:
        path statistics_files

    output:
        path "6_ai-all_species_statistics.tsv", emit: master_statistics
        path "6_ai-log-compile_statistics.log", emit: log

    script:
    """
    python3 ${projectDir}/scripts/006_ai-python-compile_statistics.py \
        --input-files ${statistics_files} \
        --output-dir .
    """
}


// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/ and ai/output_to_input/ are created
// by RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {

    // Input channel: proteome manifest
    manifest_channel = Channel.fromPath( params.proteome_manifest )

    // Step 1: Validate proteomes
    validate_proteomes( manifest_channel )

    // Step 2: Split proteomes into N parts
    split_proteomes( validate_proteomes.out.validated_manifest )

    // Step 3: DIAMOND search (parallel across all splits)
    diamond_search( split_proteomes.out.split_fastas.flatten() )

    // Step 4: Combine results per species
    // Group DIAMOND results by species name (extracted from filename)
    diamond_search.out.diamond_results
        .map { file ->
            // Filename format: {species_name}_part_{NNN}_diamond.tsv
            def name = file.simpleName.replaceFirst( /_part_\d+_diamond$/, '' )
            return tuple( name, file )
        }
        .groupTuple()
        .set { grouped_results }

    combine_results( grouped_results )

    // Step 5: Identify top hits per species
    identify_top_hits( combine_results.out.combined_results )

    // Step 6: Compile master statistics
    compile_statistics( identify_top_hits.out.statistics.collect() )
}


// ============================================================================
// Completion handler
// ============================================================================
workflow.onComplete {
    println ""
    println "========================================================================"
    if ( workflow.success ) {
        println "Pipeline completed successfully!"
        println ""
        println "Research outputs (per-step documentation):"
        println "  Step 1: ${params.output_dir}/1-output/  (validated manifest + log)"
        println "  Step 2: ${params.output_dir}/2-output/  (split FASTAs + job manifest + log)"
        println "  Step 3: ${params.output_dir}/3-output/  (DIAMOND results per split)"
        println "  Step 4: ${params.output_dir}/4-output/  (combined results per species + log)"
        println "  Step 5: ${params.output_dir}/5-output/  (top hits + statistics per species + log)"
        println "  Step 6: ${params.output_dir}/6-output/  (master statistics + log)"
        println ""
        println "Symlinks for downstream subprojects will be created by RUN-workflow.sh"
    } else {
        println "Pipeline FAILED!"
        println "Check error logs above for details."
    }
    println ""
    println "Duration: ${workflow.duration}"
    println "========================================================================"
}
