#!/usr/bin/env nextflow
/*
 * GIGANTIC trees_species - BLOCK_gigantic_species_tree Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 April 10
 * Human: Eric Edsinger
 *
 * Purpose: Standardize and label a user-provided species tree for the
 *          GIGANTIC framework. Takes a raw Newick tree (Genus_species at
 *          leaves, optional user-provided clade names at internals),
 *          validates and standardizes it, fills in ancestral_clade_NNN
 *          names for any unlabeled internal nodes, assigns CXXX_ clade
 *          identifiers to every node, and emits three Newick variants +
 *          a clade map TSV + an SVG visualization (soft-fail).
 *
 * Scripts (each called explicitly with --input and --output arguments):
 *   001: Validate input species tree (hard-fail validation + standardization)
 *   002: Assign clade identifiers (ancestral_clade_NNN + CXXX_)
 *   003: Write three Newick variants (simple, full, ids-only)
 *   004: Generate clade name <-> clade ID lookup map TSV
 *   005: Visualize species tree (SVG, soft-fail on tooling errors)
 *   006: Cross-validate all outputs for consistency
 *   007: Write workflow run log
 *
 * Design principle: "Scripts Own the Data, NextFlow Manages Execution"
 *   Every script reads from concrete input files and writes to concrete
 *   output files in OUTPUT_pipeline/N-output/. NextFlow uses publishDir
 *   to copy process outputs from work/ directories to OUTPUT_pipeline/
 *   so that real files are accessible without digging into NextFlow's
 *   cryptic work directory structure.
 *
 * Dependency graph:
 *   001 -> 002 -> { 003, 004, 005 } (parallel) -> 006 -> 007
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

// Default parameter values (overridden by nextflow.config which loads from YAML)
params.species_set_name = "speciesN"
params.input_species_tree = "INPUT_user/species_tree.newick"
params.output_dir = "OUTPUT_pipeline"


// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate Input Species Tree
 * Calls: scripts/001_ai-python-validate_input_species_tree.py
 *
 * Parses the user's Newick, validates it (binary, unique names, reserved
 * namespace un-collided, etc.), standardizes names (invalid char replacement,
 * branch length normalization to 1.0), and emits a canonical tree.
 */
process validate_input_species_tree {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-input_species_tree-canonical.newick", emit: canonical_newick
        path "1-output/1_ai-input_user_name_X_gigantic_name.tsv", emit: name_mapping
        path "1-output/1_ai-validation_report.tsv", emit: validation_report
        path "1-output/1_ai-log-validate_input_species_tree.log", emit: log

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_input_species_tree.py \\
        --input-newick ${projectDir}/../${params.input_species_tree} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Assign Clade Identifiers
 * Calls: scripts/002_ai-python-assign_clade_identifiers.py
 *
 * Fills in ancestral_clade_NNN names for any unlabeled internal nodes
 * (BFS from root, counter only consumes numbers for unlabeled internals).
 * Then assigns CXXX_ clade identifier prefixes: leaves C001-CNN in DFS
 * preorder, internals C(N+1)+ in BFS from root.
 */
process assign_clade_identifiers {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path canonical_newick

    output:
        path "2-output/2_ai-species_tree-with_clade_ids_and_names.newick", emit: labeled_newick
        path "2-output/2_ai-validation_report.tsv", emit: validation_report
        path "2-output/2_ai-log-assign_clade_identifiers.log", emit: log

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-assign_clade_identifiers.py \\
        --input-newick ${canonical_newick} \\
        --output-dir 2-output
    """
}

/*
 * Process 3: Write Newick Variants
 * Calls: scripts/003_ai-python-write_newick_variants.py
 *
 * Emits three Newick format variants:
 *   - simple: Genus_species at leaves, internals unlabeled
 *   - full: CXXX_Genus_species at leaves, CXXX_Clade_Name at internals
 *   - ids-only: CXXX at every node, no names
 *
 * Runs in parallel with Process 4 (generate_clade_map) and Process 5
 * (visualize_species_tree) since all three consume Process 2's output.
 */
process write_newick_variants {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path labeled_newick

    output:
        path "3-output/3_ai-${params.species_set_name}-species_tree-simple.newick", emit: simple_newick
        path "3-output/3_ai-${params.species_set_name}-species_tree-with_clade_ids_and_names.newick", emit: full_newick
        path "3-output/3_ai-${params.species_set_name}-species_tree-clade_ids_only.newick", emit: ids_only_newick
        path "3-output/3_ai-log-write_newick_variants.log", emit: log

    script:
    """
    mkdir -p 3-output

    python3 ${projectDir}/scripts/003_ai-python-write_newick_variants.py \\
        --input-newick ${labeled_newick} \\
        --species-set-name ${params.species_set_name} \\
        --output-dir 3-output
    """
}

/*
 * Process 4: Generate Clade Map
 * Calls: scripts/004_ai-python-generate_clade_map.py
 *
 * Emits a TSV lookup table mapping each clade name to its clade ID.
 * One row per node (leaves + internals), in DFS preorder traversal.
 *
 * Runs in parallel with Process 3 and Process 5.
 */
process generate_clade_map {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path labeled_newick

    output:
        path "4-output/4_ai-${params.species_set_name}-clade_name_X_clade_id.tsv", emit: clade_map
        path "4-output/4_ai-log-generate_clade_map.log", emit: log

    script:
    """
    mkdir -p 4-output

    python3 ${projectDir}/scripts/004_ai-python-generate_clade_map.py \\
        --input-newick ${labeled_newick} \\
        --species-set-name ${params.species_set_name} \\
        --output-dir 4-output
    """
}

/*
 * Process 5: Visualize Species Tree (SOFT-FAIL)
 * Calls: scripts/005_ai-python-visualize_species_tree.py
 *
 * Renders the species tree as SVG using ete3. If ete3 rendering fails
 * (import error, Qt issues, etc.), the script soft-fails: creates a
 * placeholder file and exits with code 0. The pipeline continues.
 *
 * The QT_QPA_PLATFORM=offscreen environment variable is set to support
 * headless rendering on SLURM compute nodes.
 *
 * Runs in parallel with Process 3 and Process 4.
 */
process visualize_species_tree {
    label 'visualization'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path labeled_newick

    output:
        path "5-output"

    script:
    """
    mkdir -p 5-output

    export QT_QPA_PLATFORM=offscreen

    python3 ${projectDir}/scripts/005_ai-python-visualize_species_tree.py \\
        --input-newick ${labeled_newick} \\
        --species-set-name ${params.species_set_name} \\
        --output-dir 5-output
    """
}

/*
 * Process 6: Validate Outputs (Cross-Check)
 * Calls: scripts/006_ai-python-validate_outputs.py
 *
 * Loads all prior outputs (canonical newick, labeled newick, 3 variants,
 * clade map, visualization dir) and cross-validates them for internal
 * consistency. Hard-fails on any inconsistency. Visualization output is
 * soft-checked (placeholder OK).
 *
 * Synchronization point: runs after Processes 3, 4, and 5 all complete.
 */
process validate_outputs {
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path canonical_newick
        path labeled_newick
        path simple_newick
        path full_newick
        path ids_only_newick
        path clade_map
        path visualization_dir

    output:
        path "6-output/6_ai-validation_report.tsv", emit: validation_report
        path "6-output/6_ai-log-validate_outputs.log", emit: log

    script:
    """
    mkdir -p 6-output

    python3 ${projectDir}/scripts/006_ai-python-validate_outputs.py \\
        --canonical-newick ${canonical_newick} \\
        --labeled-newick ${labeled_newick} \\
        --simple-newick ${simple_newick} \\
        --full-newick ${full_newick} \\
        --ids-only-newick ${ids_only_newick} \\
        --clade-map ${clade_map} \\
        --visualization-dir ${visualization_dir} \\
        --output-dir 6-output
    """
}

/*
 * Process 7: Write Run Log (FINAL STEP)
 * Calls: scripts/007_ai-python-write_run_log.py
 *
 * Creates a timestamped log in ai/logs/ within this workflow directory
 * for transparency and reproducibility. This is the last process in the
 * pipeline and runs only after validate_outputs succeeds.
 */
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/007_ai-python-write_run_log.py \\
        --workflow-name "gigantic_species_tree" \\
        --subproject-name "trees_species" \\
        --species-set-name "${params.species_set_name}" \\
        --status success
    """
}


// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Validate and standardize input species tree
    validate_input_species_tree()

    // Step 2: Assign clade identifiers (ancestral_clade_NNN + CXXX_)
    assign_clade_identifiers( validate_input_species_tree.out.canonical_newick )

    // Steps 3, 4, 5: run in parallel (all consume labeled tree from Step 2)
    write_newick_variants( assign_clade_identifiers.out.labeled_newick )
    generate_clade_map( assign_clade_identifiers.out.labeled_newick )
    visualize_species_tree( assign_clade_identifiers.out.labeled_newick )

    // Step 6: Cross-validate all outputs (synchronization point)
    validate_outputs(
        validate_input_species_tree.out.canonical_newick,
        assign_clade_identifiers.out.labeled_newick,
        write_newick_variants.out.simple_newick,
        write_newick_variants.out.full_newick,
        write_newick_variants.out.ids_only_newick,
        generate_clade_map.out.clade_map,
        visualize_species_tree.out
    )

    // Step 7: Write run log (FINAL STEP)
    write_run_log( validate_outputs.out.validation_report )
}


// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC trees_species BLOCK_gigantic_species_tree Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Canonical validated input species tree + name mapping + validation report"
        println "  2-output/: Fully labeled species tree (CXXX_Name everywhere)"
        println "  3-output/: Three Newick variants (simple, full, ids-only)"
        println "  4-output/: Clade name <-> clade ID lookup map TSV"
        println "  5-output/: Species tree visualization (SVG or soft-fail placeholder)"
        println "  6-output/: Cross-validation report"
        println ""
        println "Run log written to ai/logs/ in this workflow directory"
        println "Downstream symlinks created in output_to_input/BLOCK_gigantic_species_tree/ by RUN-workflow.sh"
    }
    println "========================================================================"
}
