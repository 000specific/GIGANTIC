#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * INTEGRATOR PIPELINE: ANNOTATIONS_X_ORTHOGROUPS
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow that integrates pfam ANNOGROUPS (annotation
 * groups) with ORTHOGROUPS, focused on non-bilaterian-only orthogroups.
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly under OUTPUT_pipeline/
 * - This is a STRUCTURE-INDEPENDENT integration: annogroup membership,
 *   orthogroup membership, and the Bilateria species set are all invariant
 *   across the 105 species-tree structures, so there is no per-structure
 *   fan-out — a handful of singleton processes.
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow dir).
 *
 * Pipeline:
 *   001 classify_orthogroups          -> 1-output (orthogroup species composition)
 *   002 build_nonbilaterian_orthogroups -> 2-output (Table 2)
 *   003 build_annogroup_X_orthogroups -> 3-output (Table 1)
 *   004 validate_results              -> 4-output (fail-fast, §36)
 *   005 write_run_log                 -> ai/logs (§45)
 *
 * AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC integrator - annotations_X_orthogroups
    ==============================================================================

    Usage:
        nextflow run main.nf -params-file ../START_HERE-user_config.yaml

    All configuration is read from START_HERE-user_config.yaml:
      - run_label, species_set_name, annotation_database, annogroup_subtypes
      - inputs.{annogroups_dir, reference_structure, orthogroups_file,
                bilateria_clade_species_mappings, bilateria_clade_id_name,
                bilateria_reference_structure}
      - output.base_dir
    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// PROCESS 001: CLASSIFY ORTHOGROUPS BY SPECIES COMPOSITION
// ============================================================================
// Reads the full orthogroups table; per orthogroup, resolves member species and
// classifies the orthogroup as bilaterian_only / non_bilaterian_only / mixed
// using the Bilateria clade species set from trees_species.

process classify_orthogroups {
    label 'local'

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-classify_orthogroups.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: BUILD NON-BILATERIAN-ONLY ORTHOGROUPS TABLE (Table 2)
// ============================================================================

process build_nonbilaterian_orthogroups {
    label 'local'

    input:
        val classify_ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-build_nonbilaterian_orthogroups.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 003: BUILD ANNOGROUP X ORTHOGROUPS TABLE (Table 1)
// ============================================================================

process build_annogroup_X_orthogroups {
    label 'local'

    input:
        val classify_ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-build_annogroup_X_orthogroups.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 004: VALIDATE RESULTS (fail-fast per §36)
// ============================================================================

process validate_results {
    label 'local'

    input:
        val previous_steps_done

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-validate_results.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 005: WRITE RUN LOG (per §45)
// ============================================================================

process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \\
        --workflow-name "annotations_X_orthogroups" \\
        --subproject-name "integrator-BLOCK_annotations_X_orthogroups" \\
        --project-name "${params.species_set_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Classify all orthogroups once (the shared spine for both tables).
    classify_orthogroups()

    // Both table-builders depend only on the classification being ready.
    build_nonbilaterian_orthogroups( classify_orthogroups.out.ready )
    build_annogroup_X_orthogroups( classify_orthogroups.out.ready )

    // Barrier: validate only after BOTH tables are written.
    validate_results(
        build_nonbilaterian_orthogroups.out.done
            .mix( build_annogroup_X_orthogroups.out.done )
            .collect()
    )

    // Write run log after validation passes.
    write_run_log( validate_results.out.done )
}

// Completion summary handled by RUN-workflow.sh (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
