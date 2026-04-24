#!/usr/bin/env nextflow
/*
 * Kim et al. 2025 Genome Pipeline
 * AI: Claude Code | Opus 4 | 2026 February 11
 * Human: Eric Edsinger
 *
 * Purpose: Download, decompress, rename, and extract T1 proteomes from
 * Kim et al. 2025 early metazoa genome/gene annotation data.
 *
 * Source: https://github.com/sebepedroslab/early-metazoa-3D-chromatin
 * Paper:  Kim et al. 2025 "Evolutionary origin of animal genome regulation"
 *         Nature, https://www.nature.com/articles/s41586-025-08960-w
 *
 * Pattern: A (Sequential) - All processes run in one job
 * Typical runtime: ~2 minutes
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.output_dir = "OUTPUT_pipeline"

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Download source data from GitHub
 * Calls: scripts/001_ai-bash-download_source_data.sh
 *
 * Output: 1-output/genome/*.fasta.gz
 *         1-output/gene_annotation/*.gtf.gz
 */
process download_source_data {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/genome", emit: genome_gz_dir
        path "1-output/gene_annotation", emit: annotation_gz_dir

    script:
    """
    bash ${projectDir}/scripts/001_ai-bash-download_source_data.sh
    """
}

/*
 * Process 2: Decompress and rename to Genus_species convention
 * Calls: scripts/002_ai-bash-unzip_rename_source_data.sh
 *
 * Input:  1-output/ (genome + gene_annotation .gz files)
 * Output: 2-output/genome/Genus_species-kim_2025.fasta
 *         2-output/gene_annotation/Genus_species-kim_2025.gtf
 */
process unzip_rename_source_data {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path genome_gz_dir
        path annotation_gz_dir

    output:
        path "2-output/genome", emit: genome_dir
        path "2-output/gene_annotation", emit: annotation_dir

    script:
    """
    # Reconstruct the input directory structure that script 002 expects
    mkdir -p 1-output
    ln -s \$(readlink -f ${genome_gz_dir}) 1-output/genome
    ln -s \$(readlink -f ${annotation_gz_dir}) 1-output/gene_annotation

    bash ${projectDir}/scripts/002_ai-bash-unzip_rename_source_data.sh 1-output
    """
}

/*
 * Process 3: Extract T1 (longest transcript per gene) proteomes
 * Calls: scripts/003_ai-python-extract_longest_transcript_proteomes.py
 *
 * Input:  2-output/ (genome FASTA + gene annotation GTF)
 * Output: 3-output/T1_proteomes/Genus_species-kim_2025-T1_proteome.aa
 *         3-output/gffread_all_transcripts/ (intermediate)
 */
process extract_longest_transcript_proteomes {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path genome_dir
        path annotation_dir

    output:
        path "3-output/T1_proteomes", emit: t1_proteomes_dir
        path "3-output/gffread_all_transcripts", emit: gffread_intermediate_dir

    script:
    """
    # Reconstruct the input directory structure that script 003 expects
    mkdir -p 2-output
    ln -s \$(readlink -f ${genome_dir}) 2-output/genome
    ln -s \$(readlink -f ${annotation_dir}) 2-output/gene_annotation

    python3 ${projectDir}/scripts/003_ai-python-extract_longest_transcript_proteomes.py \
        --input-dir 2-output \
        --output-dir 3-output
    """
}

/*
 * Process 4: Publish T1 proteomes to output_to_input/ via symlinks
 * Calls: scripts/004_ai-bash-create_output_to_input_symlinks.sh
 *
 * Creates relative symlinks in the subproject-level output_to_input/T1_proteomes/
 * pointing back to OUTPUT_pipeline/3-output/T1_proteomes/*.aa files.
 * This makes proteomes available to downstream GIGANTIC subprojects without
 * duplicating data.
 */
process publish_to_output_to_input {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path t1_proteomes_dir

    output:
        path "4-output/symlinks_manifest.tsv", emit: manifest

    script:
    """
    bash ${projectDir}/scripts/004_ai-bash-create_output_to_input_symlinks.sh \
        "${t1_proteomes_dir}" \
        "${projectDir}/../${params.output_dir}/3-output/T1_proteomes" \
        "${projectDir}/../../output_to_input/T1_proteomes"
    """
}

/*
 * Process 5: Rename files to GIGANTIC convention and create full output_to_input
 * Calls: scripts/005_ai-python-reformat_genomesdb_input.py
 *
 * Renames intermediate files to standardized GIGANTIC convention
 * (Genus_species-genome_kim_2025-downloaded_DATE.ext) with reformatted
 * proteome headers and identifier mapping files.
 */
process reformat_genomesdb_input {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path genome_dir
        path annotation_dir
        path t1_proteomes_dir

    output:
        path "5-output/**", emit: reformatted_output

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-reformat_genomesdb_input.py \
        --genome-dir ${genome_dir} \
        --annotation-dir ${annotation_dir} \
        --proteome-dir ${t1_proteomes_dir} \
        --output-dir 5-output
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Download source data from GitHub
    download_source_data()

    // Step 2: Decompress and rename files
    unzip_rename_source_data(
        download_source_data.out.genome_gz_dir,
        download_source_data.out.annotation_gz_dir
    )

    // Step 3: Extract T1 proteomes
    extract_longest_transcript_proteomes(
        unzip_rename_source_data.out.genome_dir,
        unzip_rename_source_data.out.annotation_dir
    )

    // Step 4: Symlink proteomes to output_to_input/ for downstream subprojects
    publish_to_output_to_input(
        extract_longest_transcript_proteomes.out.t1_proteomes_dir
    )

    // Step 5: Rename to GIGANTIC convention with reformatted headers and maps
    reformat_genomesdb_input(
        unzip_rename_source_data.out.genome_dir,
        unzip_rename_source_data.out.annotation_dir,
        extract_longest_transcript_proteomes.out.t1_proteomes_dir
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "Kim et al. 2025 Genome Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in: ${params.output_dir}/"
        println "  1-output/  Downloaded .gz files (genome + gene_annotation)"
        println "  2-output/  Decompressed + renamed (Genus_species-kim_2025.*)"
        println "  3-output/  T1 proteomes (longest transcript per gene)"
        println "  4-output/  Symlink manifest"
        println ""
        println "T1 proteomes: ${params.output_dir}/3-output/T1_proteomes/"
        println "Symlinks for downstream: output_to_input/T1_proteomes/"
    }
    println "========================================================================"
}
