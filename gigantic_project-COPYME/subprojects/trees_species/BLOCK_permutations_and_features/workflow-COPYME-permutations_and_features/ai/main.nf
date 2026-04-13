#!/usr/bin/env nextflow
/*
 * GIGANTIC trees_species - Permutations and Features Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 March 04
 * Human: Eric Edsinger
 *
 * Purpose: Generate species tree topology permutations for user-specified
 *          unresolved clades and extract phylogenetic features (paths, blocks,
 *          parent-child relationships, clade-species mappings, visualizations).
 *
 * Design Principle: Scripts Own the Data, NextFlow Manages Execution
 *   Every script reads its inputs from OUTPUT_pipeline/N-output/ and writes
 *   its outputs to OUTPUT_pipeline/N-output/. NextFlow orchestrates the
 *   execution ORDER but does not pass data between processes via channels.
 *   This ensures every intermediate result is inspectable in OUTPUT_pipeline/.
 *
 * Scripts:
 *   001: Extract tree components and generate phylogenetic paths
 *   002: Generate topology permutations for unresolved clades
 *   003: Assign clade identifiers to all topologies
 *   004: Build complete species trees by grafting subtrees
 *   005: Extract parent-child relationships (two formats)
 *   006: Generate phylogenetic blocks
 *   007: Integrate all clade data into comprehensive table
 *   008: Visualize species trees (SVG/PDF)
 *   009: Generate clade-to-species mappings
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS
// ============================================================================

// Workflow root directory (parent of ai/)
params.workflow_dir = "${projectDir}/.."

// Project name (used by run-log script for the run log header)
params.project_name = 'GIGANTIC'

// ============================================================================
// PROCESSES
// ============================================================================
// Each process calls one script with --workflow-dir.
// Scripts read from OUTPUT_pipeline/(N-1)-output/ and write to OUTPUT_pipeline/N-output/.
// The "done" signal pattern enforces sequential execution without data channels.

/*
 * Process 1: Extract Tree Components
 * Parses the user-provided species tree and extracts components.
 */
process extract_tree_components {
    label 'local'

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-extract_tree_components.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 2: Generate Topology Permutations
 * Generates all possible topologies for unresolved clades.
 */
process generate_topology_permutations {
    label 'local'

    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-generate_topology_permutations.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 3: Assign Clade Identifiers
 * Assigns consistent clade IDs to all topology permutations.
 */
process assign_clade_identifiers {
    label 'local'

    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-assign_clade_identifiers.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 4: Build Complete Trees
 * Grafts clade subtrees onto topology skeletons to build full species trees.
 */
process build_complete_trees {
    label 'local'

    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-build_complete_trees.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 5: Extract Parent-Child Relationships
 * Generates parent-child and parent-sibling tables for all structures.
 */
process extract_parent_child_relationships {
    label 'local'

    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-extract_parent_child_relationships.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 6: Generate Phylogenetic Blocks
 * Generates phylogenetic blocks (Parent::Child) for all structures.
 */
process generate_phylogenetic_blocks {
    label 'local'

    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/006_ai-python-generate_phylogenetic_blocks.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 7: Integrate Clade Data
 * Combines all clade data into a comprehensive table.
 */
process integrate_clade_data {
    label 'local'

    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/007_ai-python-integrate_clade_data.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 8: Visualize Species Trees
 * Generates SVG and PDF visualizations using ete3.
 * Requires conda environment: ai_tree_visualization
 */
process visualize_species_trees {
    label 'local'
    conda 'aiG-trees_species-permutations_and_features'

    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/008_ai-python-visualize_species_trees.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 9: Generate Clade-Species Mappings
 * Maps each clade to its descendant species across all structures.
 */
process generate_clade_species_mappings {
    label 'local'

    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/009_ai-python-generate_clade_species_mappings.py \
        --workflow-dir ${params.workflow_dir}
    """
}

/*
 * Process 10: Write Run Log
 * Calls: scripts/010_ai-python-write_run_log.py
 *
 * Creates a timestamped log in ai/logs/ within this workflow directory
 * for transparency and reproducibility.
 */
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/010_ai-python-write_run_log.py \
        --workflow-name "permutations_and_features" \
        --subproject-name "trees_species" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Sequential execution: each step waits for the previous to complete.
    // Scripts read/write through OUTPUT_pipeline/ - no data passes through channels.

    // Step 1: Extract tree components
    extract_tree_components()

    // Step 2: Generate topology permutations
    generate_topology_permutations( extract_tree_components.out.done )

    // Step 3: Assign clade identifiers
    assign_clade_identifiers( generate_topology_permutations.out.done )

    // Step 4: Build complete trees
    build_complete_trees( assign_clade_identifiers.out.done )

    // Step 5: Extract parent-child relationships
    extract_parent_child_relationships( build_complete_trees.out.done )

    // Step 6: Generate phylogenetic blocks
    generate_phylogenetic_blocks( extract_parent_child_relationships.out.done )

    // Step 7: Integrate clade data
    integrate_clade_data( generate_phylogenetic_blocks.out.done )

    // Step 8: Visualize species trees
    visualize_species_trees( integrate_clade_data.out.done )

    // Step 9: Generate clade-species mappings
    generate_clade_species_mappings( visualize_species_trees.out.done )

    // Step 10: Write run log
    write_run_log( generate_clade_species_mappings.out.done )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC trees_species - Permutations and Features Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Run log written to ai/logs/ in this workflow directory"
        println ""
        println "Output files in OUTPUT_pipeline/:"
        println "  1-output/: Tree components and phylogenetic paths"
        println "  2-output/: Topology permutations (Newick files)"
        println "  3-output/: Annotated topologies with clade IDs"
        println "  4-output/: Complete species trees and clade registry"
        println "  5-output/: Parent-child relationship tables"
        println "  6-output/: Phylogenetic blocks"
        println "  7-output/: Integrated clade data table"
        println "  8-output/: Tree visualizations (SVG/PDF)"
        println "  9-output/: Clade-to-species mappings"
        println ""
        println "Symlinks created in output_to_input/ (by RUN-workflow.sh)"
    }
    println "========================================================================"
}
