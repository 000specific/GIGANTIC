#!/usr/bin/env nextflow
/*
 * NCBI Genomes Pipeline
 * AI: Claude Code | Opus 4 | 2026 February 12
 * Human: Eric Edsinger
 *
 * Purpose: Download genomes, GFF3 annotations, and protein sequences from NCBI,
 * organize with GIGANTIC naming conventions, and extract T1 (longest transcript
 * per gene) proteomes.
 *
 * Source: NCBI Datasets CLI (datasets download genome accession)
 * Input:  INPUT_user/ncbi_genomes_manifest.tsv (genus_species + accession)
 *
 * Pattern: A (Sequential) - All processes run in one job
 * Typical runtime: ~30 minutes to 2 hours (depends on download speed)
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.output_dir = "OUTPUT_pipeline"
params.manifest = "INPUT_user/ncbi_genomes_manifest.tsv"
params.download_date = "20260211"

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Download source data from NCBI
 * Calls: scripts/001_ai-bash-download_ncbi_datasets.sh
 *
 * Output: 1-output/downloads/*.zip (one zip per species)
 */
process download_source_data {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/downloads", emit: downloads_dir

    script:
    """
    bash ${projectDir}/scripts/001_ai-bash-download_ncbi_datasets.sh \
        "${projectDir}/../${params.manifest}"
    """
}

/*
 * Process 2: Unzip, organize, and rename to GIGANTIC convention
 * Calls: scripts/002_ai-python-unzip_organize_rename.py
 *
 * Input:  1-output/downloads/*.zip
 * Output: 2-output/genome/Genus_species-ncbi_genomes.fasta
 *         2-output/gff3/Genus_species-ncbi_genomes.gff3
 *         2-output/protein/Genus_species-ncbi_genomes.faa
 */
process unzip_organize_rename {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path downloads_dir

    output:
        path "2-output/genome", emit: genome_dir
        path "2-output/gff3", emit: gff3_dir
        path "2-output/protein", emit: protein_dir

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-unzip_organize_rename.py \
        --input-dir ${downloads_dir} \
        --output-dir 2-output
    """
}

/*
 * Process 3: Extract T1 (longest transcript per gene) proteomes
 * Calls: scripts/003_ai-python-extract_longest_transcript_proteomes.py
 *
 * Input:  2-output/gff3/ + 2-output/protein/
 * Output: 3-output/T1_proteomes/Genus_species-ncbi_genomes-T1_proteome.aa
 */
process extract_longest_transcript_proteomes {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path genome_dir
        path gff3_dir
        path protein_dir

    output:
        path "3-output/T1_proteomes", emit: t1_proteomes_dir

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-extract_longest_transcript_proteomes.py \
        --manifest ${projectDir}/../INPUT_user/ncbi_genomes_manifest.tsv \
        --genome-dir ${genome_dir} \
        --gff3-dir ${gff3_dir} \
        --protein-dir ${protein_dir} \
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
 * The script enumerates files from the NextFlow channel input (work dir, which
 * is guaranteed complete via channel dependency), but creates symlinks pointing
 * to the final publishDir location. This avoids the async publishDir timing
 * issue where the published directory may not yet be fully populated.
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
 * Renames intermediate files (Genus_species-ncbi_genomes-T1_proteome.aa) to
 * standardized GIGANTIC convention (Genus_species-genome_ncbi_ACCESSION-downloaded_DATE.aa)
 * and creates the complete output_to_input structure with genomes, annotations,
 * proteomes, and identifier maps.
 */
process reformat_genomesdb_input {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path t1_proteomes_dir
        path genome_dir
        path gff3_dir

    output:
        path "5-output/**", emit: reformatted_output

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-reformat_genomesdb_input.py \
        --manifest "${projectDir}/../${params.manifest}" \
        --genome-dir ${genome_dir} \
        --gff3-dir ${gff3_dir} \
        --proteome-dir ${t1_proteomes_dir} \
        --output-dir 5-output \
        --output-to-input-dir "${projectDir}/../../output_to_input" \
        --download-date "${params.download_date}"
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Download source data from NCBI
    download_source_data()

    // Step 2: Unzip, organize, and rename files
    unzip_organize_rename(
        download_source_data.out.downloads_dir
    )

    // Step 3: Extract T1 proteomes (needs genome_dir for alt-loci filter's scaffold-type detection)
    extract_longest_transcript_proteomes(
        unzip_organize_rename.out.genome_dir,
        unzip_organize_rename.out.gff3_dir,
        unzip_organize_rename.out.protein_dir
    )

    // Step 4: Symlink proteomes to output_to_input/ for downstream subprojects
    publish_to_output_to_input(
        extract_longest_transcript_proteomes.out.t1_proteomes_dir
    )

    // Step 5: Rename to GIGANTIC convention and create full output_to_input structure
    reformat_genomesdb_input(
        extract_longest_transcript_proteomes.out.t1_proteomes_dir,
        unzip_organize_rename.out.genome_dir,
        unzip_organize_rename.out.gff3_dir
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "NCBI Genomes Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in: ${params.output_dir}/"
        println "  1-output/  Downloaded zip files (one per species)"
        println "  2-output/  Unzipped + renamed (genome/, gff3/, protein/)"
        println "  3-output/  T1 proteomes (longest transcript per gene)"
        println "  4-output/  Symlink manifest"
        println ""
        println "T1 proteomes: ${params.output_dir}/3-output/T1_proteomes/"
        println "Symlinks for downstream: output_to_input/T1_proteomes/"
    }
    println "========================================================================"
}
