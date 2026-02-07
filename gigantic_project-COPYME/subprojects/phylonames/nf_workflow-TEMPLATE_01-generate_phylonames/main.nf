#!/usr/bin/env nextflow
/*
 * GIGANTIC Phylonames Pipeline
 * AI: Claude Code | Opus 4.5 | 2026 February 06
 * Human: Eric Edsinger
 *
 * Purpose: Download NCBI taxonomy and generate phylonames for species mapping
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
 * Calls: ai_scripts/001_ai-bash-download_ncbi_taxonomy.sh
 */
process download_ncbi_taxonomy {
    label 'local'

    output:
        path "database-ncbi_taxonomy_*", emit: database_dir
        path "database-ncbi_taxonomy_latest", emit: database_link

    script:
    """
    # Check if database already exists (skip download if so)
    if [ -d "${projectDir}/database-ncbi_taxonomy_latest" ] && [ "${params.force_download}" != "true" ]; then
        echo "NCBI taxonomy database already exists. Skipping download."
        echo "To force re-download, set force_download: true in config.yaml"
        # Create symlinks to existing database for NextFlow output tracking
        ln -s ${projectDir}/database-ncbi_taxonomy_latest database-ncbi_taxonomy_latest
        # Get the actual directory name
        ACTUAL_DIR=\$(readlink -f ${projectDir}/database-ncbi_taxonomy_latest)
        ln -s \$ACTUAL_DIR \$(basename \$ACTUAL_DIR)
    else
        echo "Downloading NCBI taxonomy database..."
        bash ${projectDir}/ai_scripts/001_ai-bash-download_ncbi_taxonomy.sh
        # Move downloaded files to work directory for NextFlow tracking
        mv ${projectDir}/database-ncbi_taxonomy_* .
    fi
    """
}

/*
 * Process 2: Generate Phylonames from NCBI Taxonomy
 * Calls: ai_scripts/002_ai-python-generate_phylonames.py
 */
process generate_phylonames {
    label 'local'

    input:
        path database_link

    output:
        path "output/2-output/phylonames", emit: phylonames
        path "output/2-output/phylonames_taxonid", emit: phylonames_taxonid
        path "output/2-output/map-phyloname_X_ncbi_taxonomy_info.tsv", emit: master_mapping
        path "output/2-output/failed-entries.txt", emit: failed_entries
        path "output/2-output/generation_metadata.txt", emit: metadata

    script:
    """
    # Create output directory structure
    mkdir -p output/2-output

    # Run phyloname generation
    # The script looks for database-ncbi_taxonomy_latest in current directory
    # The input already has this name from NextFlow staging, so we just use it directly
    python3 ${projectDir}/ai_scripts/002_ai-python-generate_phylonames.py
    """
}

/*
 * Process 3: Create Project-Specific Species Mapping
 * Calls: ai_scripts/003_ai-python-create_species_mapping.py
 */
process create_species_mapping {
    label 'local'

    // Publish to OUTPUT_pipeline with full directory structure
    publishDir "${projectDir}/${params.output_dir}", mode: 'copy', overwrite: true

    // Publish ONLY the mapping file to output_to_input/maps (flatten structure)
    publishDir "${projectDir}/../output_to_input/maps", mode: 'copy', overwrite: true,
               saveAs: { filename ->
                   if (filename.contains('map-genus_species')) {
                       // Extract just the filename, not the full path
                       return filename.tokenize('/').last()
                   }
                   return null
               }

    input:
        path master_mapping
        path species_list

    output:
        path "output/3-output/${params.project_name}_map-genus_species_X_phylonames.tsv", emit: project_mapping

    script:
    """
    # Create output directory
    mkdir -p output/3-output

    # Create project-specific mapping
    python3 ${projectDir}/ai_scripts/003_ai-python-create_species_mapping.py \\
        --species-list ${species_list} \\
        --master-mapping ${master_mapping} \\
        --output output/3-output/${params.project_name}_map-genus_species_X_phylonames.tsv
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Get species list from INPUT_user/
    species_list_ch = Channel.fromPath("${projectDir}/${params.species_list}")

    // Step 1: Download NCBI taxonomy (if needed)
    download_ncbi_taxonomy()

    // Step 2: Generate all phylonames
    generate_phylonames(download_ncbi_taxonomy.out.database_link)

    // Step 3: Create project-specific mapping
    create_species_mapping(
        generate_phylonames.out.master_mapping,
        species_list_ch
    )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Phylonames Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files:"
        println "  - ${params.output_dir}/output/3-output/${params.project_name}_map-genus_species_X_phylonames.tsv"
        println ""
        println "Symlink for downstream subprojects:"
        println "  - ../output_to_input/maps/${params.project_name}_map-genus_species_X_phylonames.tsv"
    }
    println "========================================================================"
}
