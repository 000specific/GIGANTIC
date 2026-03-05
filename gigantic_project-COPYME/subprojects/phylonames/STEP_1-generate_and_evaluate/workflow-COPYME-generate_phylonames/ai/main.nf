#!/usr/bin/env nextflow
/*
 * GIGANTIC Phylonames Pipeline - STEP 1: Generate and Evaluate
 * AI: Claude Code | Opus 4.6 | 2026 March 04
 * Human: Eric Edsinger
 *
 * Purpose: Download NCBI taxonomy and generate phylonames for species mapping
 *
 * This is STEP 1 of a 2-STEP workflow:
 *   STEP 1 (this): Generate phylonames from NCBI taxonomy. User reviews output.
 *   STEP 2: Apply user-provided custom phylonames (after reviewing STEP 1 output).
 *
 * Pattern: A (Sequential) - All processes run in one job
 * Typical runtime: ~15 minutes
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.project_name = "my_project"
params.species_list = "INPUT_user/species_list.txt"
params.output_dir = "OUTPUT_pipeline"
params.force_download = false

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Download NCBI Taxonomy Database
 * Calls: scripts/001_ai-bash-download_ncbi_taxonomy.sh
 */
process download_ncbi_taxonomy {
    label 'local'

    output:
        path "database-ncbi_taxonomy_*", emit: database_dir
        path "database-ncbi_taxonomy_latest", emit: database_link

    script:
    """
    # Check if database already exists (skip download if so)
    if [ -d "${projectDir}/../database-ncbi_taxonomy_latest" ] && [ "${params.force_download}" != "true" ]; then
        echo "NCBI taxonomy database already exists. Skipping download."
        echo "To force re-download, set force_download: true in config.yaml"
        # Create symlinks to existing database for NextFlow output tracking
        ln -s ${projectDir}/../database-ncbi_taxonomy_latest database-ncbi_taxonomy_latest
        # Get the actual directory name
        ACTUAL_DIR=\$(readlink -f ${projectDir}/../database-ncbi_taxonomy_latest)
        ln -s \$ACTUAL_DIR \$(basename \$ACTUAL_DIR)
    else
        echo "Downloading NCBI taxonomy database..."
        # The download script creates the database in the current directory (NextFlow work dir)
        # It also creates the database-ncbi_taxonomy_latest symlink
        bash ${projectDir}/scripts/001_ai-bash-download_ncbi_taxonomy.sh
    fi
    """
}

/*
 * Process 2: Generate Phylonames from NCBI Taxonomy
 * Calls: scripts/002_ai-python-generate_phylonames.py
 */
process generate_phylonames {
    label 'local'

    input:
        path database_link

    output:
        path "2-output/phylonames", emit: phylonames
        path "2-output/phylonames_taxonid", emit: phylonames_taxonid
        path "2-output/map-phyloname_X_ncbi_taxonomy_info.tsv", emit: master_mapping
        path "2-output/map-numbered_clades_X_defining_clades.tsv", emit: numbered_clades_reference
        path "2-output/failed-entries.txt", emit: failed_entries
        path "2-output/generation_metadata.txt", emit: metadata

    script:
    """
    # Create output directory structure
    mkdir -p 2-output

    # Run phyloname generation
    # The script looks for database-ncbi_taxonomy_latest in current directory
    # The input already has this name from NextFlow staging, so we just use it directly
    python3 ${projectDir}/scripts/002_ai-python-generate_phylonames.py
    """
}

/*
 * Process 3: Create Project-Specific Species Mapping
 * Calls: scripts/003_ai-python-create_species_mapping.py
 */
process create_species_mapping {
    label 'local'

    // Publish to OUTPUT_pipeline with full directory structure
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    // NOTE: Symlinks for output_to_input/maps/ are created by RUN-workflow.sh
    // after pipeline completes. Real files only live in OUTPUT_pipeline/N-output/.

    input:
        path master_mapping
        path species_list

    output:
        path "3-output/${params.project_name}_map-genus_species_X_phylonames.tsv", emit: project_mapping

    script:
    """
    # Create output directory
    mkdir -p 3-output

    # Create project-specific mapping
    python3 ${projectDir}/scripts/003_ai-python-create_species_mapping.py \\
        --species-list ${species_list} \\
        --master-mapping ${master_mapping} \\
        --output 3-output/${params.project_name}_map-genus_species_X_phylonames.tsv
    """
}

/*
 * Process 4: Generate Taxonomy Summary
 * Calls: scripts/004_ai-python-generate_taxonomy_summary.py
 *
 * Generates readable summary of phylonames showing:
 * - Taxonomic distribution (species counts by clade)
 * - Numbered clades (NCBI gaps that could be named)
 * - NOTINNCBI species (not found in NCBI taxonomy)
 *
 * USER ACTION: Review the taxonomy summary to identify species that need
 * custom phylonames, then use STEP 2 to apply overrides.
 */
process generate_taxonomy_summary {
    label 'local'

    // Publish to OUTPUT_pipeline
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    // Also publish to upload_to_server for web viewing
    publishDir "${projectDir}/../../upload_to_server/taxonomy_summaries", mode: 'copy', overwrite: true,
               saveAs: { filename ->
                   if (filename.endsWith('.html') || filename.endsWith('.md')) {
                       return filename.tokenize('/').last()
                   }
                   return null
               }

    input:
        path project_mapping

    output:
        path "4-output/${params.project_name}_taxonomy_summary.md", emit: summary_md
        path "4-output/${params.project_name}_taxonomy_summary.html", emit: summary_html

    script:
    """
    # Create output directory
    mkdir -p 4-output

    # Generate taxonomy summary (both markdown and HTML)
    python3 ${projectDir}/scripts/004_ai-python-generate_taxonomy_summary.py \\
        --input ${project_mapping} \\
        --output-dir 4-output \\
        --project-name "${params.project_name}"
    """
}

/*
 * Process 5: Write Run Log to Research Notebook
 * Calls: scripts/005_ai-python-write_run_log.py
 *
 * Creates a timestamped log in research_notebook/research_ai/subproject-phylonames/logs/
 * for transparency and reproducibility - like an AI lab notebook.
 * This is the FINAL step in the workflow.
 */
process write_run_log {
    label 'local'

    input:
        path project_mapping
        path species_list

    output:
        val true, emit: log_complete

    script:
    """
    # Count species in the list
    SPECIES_COUNT=\$(grep -v '^#' ${species_list} | grep -v '^\$' | wc -l)

    # Write run log to research notebook
    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \\
        --project-name "${params.project_name}" \\
        --species-count \$SPECIES_COUNT \\
        --species-file ${species_list} \\
        --output-file ${project_mapping} \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Get species list from INPUT_user/ (relative to workflow root, not ai/)
    species_list_ch = Channel.fromPath("${projectDir}/../${params.species_list}")

    // Step 1: Download NCBI taxonomy (if needed)
    download_ncbi_taxonomy()

    // Step 2: Generate all phylonames
    generate_phylonames(download_ncbi_taxonomy.out.database_link)

    // Step 3: Create project-specific mapping
    create_species_mapping(
        generate_phylonames.out.master_mapping,
        species_list_ch
    )

    // Step 4: Generate taxonomy summary for user review
    generate_taxonomy_summary(
        create_species_mapping.out.project_mapping
    )

    // Step 5: Write run log to research notebook (FINAL STEP)
    write_run_log(
        create_species_mapping.out.project_mapping,
        species_list_ch
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Phylonames Pipeline - STEP 1 Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files:"
        println "  - ${params.output_dir}/3-output/${params.project_name}_map-genus_species_X_phylonames.tsv"
        println "  - ${params.output_dir}/4-output/${params.project_name}_taxonomy_summary.md"
        println "  - ${params.output_dir}/4-output/${params.project_name}_taxonomy_summary.html"
        println ""
        println "Symlinks created in output_to_input/ (by RUN-workflow.sh)"
        println "Taxonomy summary copied to upload_to_server/taxonomy_summaries/"
        println "Run log written to research_notebook/research_ai/subproject-phylonames/logs/"
        println ""
        println "NEXT STEP: Review the taxonomy summary for:"
        println "  - NOTINNCBI species (not found in NCBI taxonomy)"
        println "  - Numbered clades (e.g., Kingdom6555) that need meaningful names"
        println "  - Any phylonames you want to override"
        println ""
        println "If changes are needed, use STEP 2 to apply custom phylonames."
    }
    println "========================================================================"
}
