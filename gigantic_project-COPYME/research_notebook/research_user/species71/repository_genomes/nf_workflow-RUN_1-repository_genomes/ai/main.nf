#!/usr/bin/env nextflow
/*
 * Repository Genomes Pipeline
 * AI: Claude Code | Opus 4 | 2026 February 12
 * Human: Eric Edsinger
 *
 * Purpose: Download genomes, annotations, and protein sequences from various
 * external repositories, organize with GIGANTIC naming conventions, and extract
 * T1 (longest transcript per gene) proteomes.
 *
 * Source: Various repositories (FigShare, Zenodo, Dryad, GigaDB, OIST, etc.)
 * Input:  INPUT_user/repository_genomes_manifest.tsv (genus_species + URLs)
 *         ai/scripts/per_species/{genus_species}/download.sh (per-species scripts)
 *
 * Process flow:
 *   1. Download source data (loops over per-species scripts)
 *   2. Organize and rename to GIGANTIC convention
 *   3. Extract T1 proteomes (flexible: protein+annotation, gffread, or protein-only)
 *   4. Create symlinks in output_to_input/ for downstream subprojects
 *
 * Pattern: A (Sequential) - All processes run in one job
 * Typical runtime: Variable (depends on download speed and number of species)
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.output_dir = "OUTPUT_pipeline"
params.manifest = "INPUT_user/repository_genomes_manifest.tsv"

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Download source data from various repositories
 * Calls: scripts/001_ai-bash-download_repository_genomes.sh
 *
 * This master script loops over per-species download scripts located in
 * scripts/per_species/{genus_species}/download.sh
 *
 * Output: 1-output/{genus_species}/ (one directory per species)
 *   Each containing: genome.fasta, annotation.gff3/gtf, protein.faa
 *   (whichever are available from the repository)
 */
process download_source_data {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output", emit: downloads_dir

    script:
    """
    bash ${projectDir}/scripts/001_ai-bash-download_repository_genomes.sh \
        "${projectDir}/scripts" \
        "${projectDir}/../${params.manifest}"
    """
}

/*
 * Process 2: Organize and rename to GIGANTIC convention
 * Calls: scripts/002_ai-python-organize_rename.py
 *
 * Input:  1-output/{genus_species}/ (per-species download directories)
 * Output: 2-output/genome/{genus_species}-repository_genomes.fasta
 *         2-output/annotation/{genus_species}-repository_genomes.gff3 (or .gtf)
 *         2-output/protein/{genus_species}-repository_genomes.faa
 */
process organize_rename {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path downloads_dir

    output:
        path "2-output/genome", emit: genome_dir
        path "2-output/annotation", emit: annotation_dir
        path "2-output/protein", emit: protein_dir

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-organize_rename.py \
        --input-dir ${downloads_dir} \
        --output-dir 2-output
    """
}

/*
 * Process 3: Extract T1 (longest transcript per gene) proteomes
 * Calls: scripts/003_ai-python-extract_longest_transcript_proteomes.py
 *
 * Flexibly handles multiple input scenarios per species:
 *   Path A: protein.faa + GFF3 -> filter for longest per gene
 *   Path B: protein.faa + GTF  -> filter for longest per gene
 *   Path C: genome + annotation -> gffread extraction + T1 filter
 *   Path D: protein only        -> use all proteins (no T1 filtering)
 *
 * Input:  2-output/ (genome/, annotation/, protein/ subdirectories)
 * Output: 3-output/T1_proteomes/{genus_species}-repository_genomes-T1_proteome.aa
 */
process extract_longest_transcript_proteomes {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path genome_dir
        path annotation_dir
        path protein_dir

    output:
        path "3-output/T1_proteomes", emit: t1_proteomes_dir

    script:
    """
    mkdir -p 2-output
    ln -s \${PWD}/${genome_dir} 2-output/genome
    ln -s \${PWD}/${annotation_dir} 2-output/annotation
    ln -s \${PWD}/${protein_dir} 2-output/protein

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
 *
 * Uses 3-argument pattern: enumerate from NextFlow work dir (guaranteed complete),
 * create symlinks pointing to final publishDir location.
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

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Download source data from repositories
    download_source_data()

    // Step 2: Organize and rename files
    organize_rename(
        download_source_data.out.downloads_dir
    )

    // Step 3: Extract T1 proteomes
    extract_longest_transcript_proteomes(
        organize_rename.out.genome_dir,
        organize_rename.out.annotation_dir,
        organize_rename.out.protein_dir
    )

    // Step 4: Symlink proteomes to output_to_input/ for downstream subprojects
    publish_to_output_to_input(
        extract_longest_transcript_proteomes.out.t1_proteomes_dir
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "Repository Genomes Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in: ${params.output_dir}/"
        println "  1-output/  Per-species download directories"
        println "  2-output/  Organized + renamed (genome/, annotation/, protein/)"
        println "  3-output/  T1 proteomes (longest transcript per gene)"
        println "  4-output/  Symlink manifest"
        println ""
        println "T1 proteomes: ${params.output_dir}/3-output/T1_proteomes/"
        println "Symlinks for downstream: output_to_input/T1_proteomes/"
    }
    println "========================================================================"
}
