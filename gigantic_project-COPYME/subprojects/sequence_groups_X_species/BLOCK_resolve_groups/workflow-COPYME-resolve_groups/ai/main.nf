#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * SEQUENCE_GROUPS_X_SPECIES : RESOLVE A SEQUENCE-GROUP SET ONTO THE SPECIES TREE
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow. Reads ONE sequence-group set (orthogroups,
 * annogroups, gene families, ...) and overlays its membership onto the species-tree
 * clades. Producer-agnostic: Script 001 adapts the producer's native output into a
 * STANDARD membership; everything downstream reads only that.
 *
 *   001 adapt_membership          (once)  -> 1-output  standard membership
 *   002 species_tree_deconvolution (once) -> 2-output  member sequence+species counts per clade
 *   003 per_species_sequence_map  (once)  -> 3-output  member sequence ids per species
 *   004 composite_clades          (once)  -> 4-output  composite clades (4 algorithms)
 *   005 write_run_log             (once)  -> ai/logs   (gigantic_conventions §45)
 *
 * 002/003/004 are independent (all read the membership), so they run in parallel.
 *
 * AI: Claude Code | Opus 4.8 | 2026 June 28
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    GIGANTIC sequence_groups_X_species - resolve a sequence-group set onto the species tree
    Usage: bash RUN-workflow.sh   (edit START_HERE-user_config.yaml first)
    """.stripIndent()
    exit 0
}

// All configuration comes from START_HERE-user_config.yaml via -params-file.
// projectDir is ai/, so the workflow root is ${projectDir}/...

// ============================================================================
// PROCESS 001: ADAPT MEMBERSHIP (producer -> standard membership)
// ============================================================================
process adapt_membership {
    label 'local'

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-adapt_sequence_group_membership.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: SPECIES-TREE DECONVOLUTION (sequence + species counts per clade)
// ============================================================================
process species_tree_deconvolution {
    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-species_tree_deconvolution.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 003: PER-SPECIES SEQUENCE MAP
// ============================================================================
process per_species_sequence_map {
    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-per_species_sequence_map.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 004: COMPOSITE CLADES (four algorithms)
// ============================================================================
process composite_clades {
    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-composite_clades.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 005: WRITE RUN LOG
// ============================================================================
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \
        --workflow-name "resolve_groups" \
        --subproject-name "sequence_groups_X_species-BLOCK_resolve_groups" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================
workflow {
    // 001 adapt the producer membership; then the three overlays in parallel.
    adapt_membership()
    species_tree_deconvolution( adapt_membership.out.done )
    per_species_sequence_map( adapt_membership.out.done )
    composite_clades( adapt_membership.out.done )

    // Run log once all three overlays complete.
    write_run_log(
        species_tree_deconvolution.out.done
            .mix( per_species_sequence_map.out.done, composite_clades.out.done )
            .collect()
    )
}

// Completion summary handled by RUN-workflow.sh (orchestrator-level).
