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
params.user_phylonames = ""  // Optional: user-provided custom phylonames file
params.mark_unofficial = true  // Default: mark ALL user-provided clades as UNOFFICIAL
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
        path "output/2-output/map-numbered_clades_X_defining_clades.tsv", emit: numbered_clades_reference
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

/*
 * Process 4: Apply User-Provided Phylonames (OPTIONAL)
 * Calls: ai_scripts/004_ai-python-apply_user_phylonames.py
 *
 * This process only runs if user_phylonames parameter is set.
 * It applies custom phylonames and marks ALL user-provided clades as UNOFFICIAL
 * (unless mark_unofficial is set to false in config).
 *
 * KEY CONCEPT: Assigning a clade to a species is a taxonomic DECISION.
 * When users override NCBI, their decision is "unofficial" regardless of
 * whether the clade name exists in NCBI taxonomy.
 */
process apply_user_phylonames {
    label 'local'

    // Publish to OUTPUT_pipeline with full directory structure
    publishDir "${projectDir}/${params.output_dir}", mode: 'copy', overwrite: true

    // Publish final mapping to output_to_input/maps (flatten structure)
    publishDir "${projectDir}/../output_to_input/maps", mode: 'copy', overwrite: true,
               saveAs: { filename ->
                   if (filename.contains('final_project_mapping')) {
                       // Extract just the filename, add project name prefix
                       return "${params.project_name}_" + filename.tokenize('/').last()
                   }
                   return null
               }

    input:
        path project_mapping
        path user_phylonames

    output:
        path "output/4-output/final_project_mapping.tsv", emit: final_mapping
        path "output/4-output/unofficial_clades_report.tsv", emit: unofficial_report, optional: true

    script:
    // Build the command with optional --no-mark-unofficial flag
    def unofficial_flag = params.mark_unofficial ? "" : "--no-mark-unofficial"
    """
    # Create output directory
    mkdir -p output/4-output

    # Apply user phylonames
    # By default, ALL user-provided clades are marked UNOFFICIAL
    # Use mark_unofficial: false in config to disable this
    python3 ${projectDir}/ai_scripts/004_ai-python-apply_user_phylonames.py \\
        --project-mapping ${project_mapping} \\
        --user-phylonames ${user_phylonames} \\
        --output-dir output/4-output \\
        ${unofficial_flag}
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

    // Step 4: Apply user phylonames (OPTIONAL - only if user_phylonames is specified)
    // ALL user-provided clades are marked UNOFFICIAL by default
    // (unless mark_unofficial: false in config)
    if (params.user_phylonames) {
        user_phylonames_ch = Channel.fromPath("${projectDir}/${params.user_phylonames}")

        apply_user_phylonames(
            create_species_mapping.out.project_mapping,
            user_phylonames_ch
        )
    }
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
        if (params.user_phylonames) {
            println "  - ${params.output_dir}/output/4-output/final_project_mapping.tsv (with user phylonames)"
            println "  - ${params.output_dir}/output/4-output/unofficial_clades_report.tsv (if any unofficial clades)"
        }
        println ""
        println "Files copied to output_to_input/maps/ for downstream subprojects"
        if (params.user_phylonames) {
            println ""
            println "Note: User phylonames applied. Clades not in NCBI taxonomy are marked UNOFFICIAL."
        }
    }
    println "========================================================================"
}
