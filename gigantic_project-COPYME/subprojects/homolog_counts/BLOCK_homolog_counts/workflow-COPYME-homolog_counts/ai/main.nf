#!/usr/bin/env nextflow
/*
 * GIGANTIC homolog_counts - BLOCK homolog_counts Pipeline
 * AI: Claude Code | Opus 4.7 | 2026 May 20
 * Human: Eric Edsinger
 *
 * Purpose: Produce per-species70 homolog count tables from multiple upstream
 * GIGANTIC subprojects. One wide TSV per source:
 *   Feature_ID | Total_Count | Total_Species_Count | <70 species cols, alpha by phyloname>
 *
 * Scripts:
 *   001: Validate species70 manifest + emit canonical alphabetical phyloname column order
 *   002: Count orthogroups from orthogroups/BLOCK_orthohmm
 *   003: Count HGNC gene group homologs from trees_gene_groups
 *   004: Count curated gene family homologs from trees_gene_families
 *   005: Write run log
 *
 * Scripts 002-004 are independent and run in parallel (all consume the species
 * column order from script 001 to guarantee identical column shape across TSVs).
 *
 * Symlinks for output_to_input/BLOCK_homolog_counts/ are created by
 * RUN-workflow.sh AFTER this pipeline completes.
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (resolved from nextflow.config which reads START_HERE-user_config.yaml)
// ============================================================================

params.species70_phyloname_map  = ''
params.orthogroups_orthohmm_dir = ''
params.trees_gene_groups_dir    = ''
params.trees_gene_families_dir  = ''
params.output_dir               = 'OUTPUT_pipeline'
params.project_name             = 'homolog_counts'

// ============================================================================
// VALIDATE REQUIRED INPUTS
// ============================================================================

if ( !params.species70_phyloname_map || !file( params.species70_phyloname_map ).exists() ) {
    error """
    ========================================================================
    CONFIGURATION ERROR: species70_phyloname_map not set or file missing.

    Set inputs.species70_phyloname_map in START_HERE-user_config.yaml to the
    canonical species70 mapping file (columns: genus_species | phyloname | phyloname_taxonid).
    ========================================================================
    """.stripIndent()
}

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate species70 manifest + emit canonical column order
 * Calls: scripts/001_ai-python-validate_species70_manifest.py
 *
 * The species_order output is the canonical column order shared by all
 * counting scripts to guarantee identical species column layout.
 */
process validate_species70_manifest {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-species70_alphabetical_phylonames.tsv", emit: species_order
        path "1-output/1_ai-log-validate_species70_manifest.log"

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_species70_manifest.py \\
        --phyloname-map ${params.species70_phyloname_map} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Count orthogroups from orthogroups/BLOCK_orthohmm
 * Calls: scripts/002_ai-python-count-orthogroups_orthohmm.py
 */
process count_orthogroups_orthohmm {
    label 'counting'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path species_order

    output:
        path "2-output/2_ai-counts-orthogroups_orthohmm.tsv", emit: counts
        path "2-output/2_ai-log-count-orthogroups_orthohmm.log"

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-count-orthogroups_orthohmm.py \\
        --species-order ${species_order} \\
        --orthogroups-dir ${params.orthogroups_orthohmm_dir} \\
        --output-dir 2-output
    """
}

/*
 * Process 3: Count HGNC gene group homologs from trees_gene_groups
 * Calls: scripts/003_ai-python-count-trees_gene_groups.py
 */
process count_trees_gene_groups {
    label 'counting'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path species_order

    output:
        path "3-output/3_ai-counts-trees_gene_groups.tsv", emit: counts
        path "3-output/3_ai-log-count-trees_gene_groups.log"

    script:
    """
    mkdir -p 3-output

    python3 ${projectDir}/scripts/003_ai-python-count-trees_gene_groups.py \\
        --species-order ${species_order} \\
        --gene-groups-dir ${params.trees_gene_groups_dir} \\
        --output-dir 3-output
    """
}

/*
 * Process 4: Count curated gene family homologs from trees_gene_families
 * Calls: scripts/004_ai-python-count-trees_gene_families.py
 */
process count_trees_gene_families {
    label 'counting'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path species_order

    output:
        path "4-output/4_ai-counts-trees_gene_families.tsv", emit: counts
        path "4-output/4_ai-log-count-trees_gene_families.log"

    script:
    """
    mkdir -p 4-output

    python3 ${projectDir}/scripts/004_ai-python-count-trees_gene_families.py \\
        --species-order ${species_order} \\
        --gene-families-dir ${params.trees_gene_families_dir} \\
        --output-dir 4-output
    """
}

/*
 * Process 5: Write Run Log
 * Calls: scripts/005_ai-python-write_run_log.py
 *
 * Runs only after all three counting processes complete (input collects
 * their .counts emissions).
 */
process write_run_log {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path all_count_outputs

    output:
        path "5-output/5_ai-run_log.md", emit: run_log

    script:
    """
    mkdir -p 5-output

    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \\
        --workflow-name "homolog_counts" \\
        --subproject-name "homolog_counts" \\
        --project-name "${params.project_name}" \\
        --status success \\
        --output-dir 5-output
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Validate species70 manifest (must run first; emits canonical column order)
    validate_species70_manifest()

    // Steps 2-4: Independent counters, run in parallel
    count_orthogroups_orthohmm( validate_species70_manifest.out.species_order )
    count_trees_gene_groups(   validate_species70_manifest.out.species_order )
    count_trees_gene_families( validate_species70_manifest.out.species_order )

    // Step 5: Run log (runs only after all three counters complete)
    all_counts = count_orthogroups_orthohmm.out.counts
        .mix( count_trees_gene_groups.out.counts, count_trees_gene_families.out.counts )
        .collect()

    write_run_log( all_counts )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC homolog_counts Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if ( workflow.success ) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: species70 alphabetical phyloname column order"
        println "  2-output/: counts from orthogroups/BLOCK_orthohmm"
        println "  3-output/: counts from trees_gene_groups"
        println "  4-output/: counts from trees_gene_families"
        println "  5-output/: run log"
        println ""
        println "Symlinks created in output_to_input/BLOCK_homolog_counts/ (by RUN-workflow.sh)"
    }
    println "========================================================================"
}
