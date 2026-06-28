#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * ANNOGROUPS PIPELINE: BUILD_ANNOGROUPS
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow that builds the four canonical annogroup types
 * (feature, combination, architecture, absent) PER SOURCE annotation database,
 * from annotations_hmms outputs.
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly under OUTPUT_pipeline/
 * - Script 001 runs ONCE: it resolves which sources have a parser plugin
 *   (parsers/<source>.py) and builds the proteome universe (membership universe
 *   for `absent`). It writes 1_ai-sources_manifest.tsv.
 * - The manifest is split into a per-source channel; 002 (build) and 003
 *   (validate) then FAN OUT per source. New source = new parser plugin only.
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow dir).
 *
 * Pipeline:
 *   001 resolve_sources_and_universe     -> 1-output (sources manifest + universe)
 *   002 build_annogroups       (per source) -> 2-output/<source>/ (map + membership)
 *   003 validate_results       (per source) -> 3-output/<source>/ (fail-fast, §36)
 *   004 species_tree_deconvolution (per source) -> 4-output/<source>/ (per-clade member-protein counts)
 *   005 per_species_sequence_map   (per source) -> 5-output/<source>/ (member sequence IDs per species)
 *   006 composite_clades       (per source) -> 6-output/<source>/ (exact/absent/core_urclade/core_early_clade)
 *   007 write_summary          (once)        -> 7-output (per source / species / phylum)
 *   008 write_run_log          (once)        -> ai/logs (§45)
 *
 * AI: Claude Code | Opus 4.8 (1M context) | 2026 June 18
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC annogroups - build_annogroups
    ==============================================================================

    Usage:
        nextflow run main.nf -params-file ../START_HERE-user_config.yaml

    All configuration is read from START_HERE-user_config.yaml:
      - species_set_name, sources ("all" or a subset)
      - inputs.{annotations_hmms_dir, proteomes_dir}
      - output.base_dir
    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// PROCESS 001: RESOLVE SOURCES + BUILD PROTEOME UNIVERSE (runs once)
// ============================================================================
// Discovers parser plugins, intersects with the config `sources:` request, and
// writes 1_ai-sources_manifest.tsv. Builds the proteome universe (every sequence
// identifier across the species set's proteomes) used for `absent`.

process resolve_sources_and_universe {
    label 'local'

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-resolve_sources_and_universe.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: BUILD ANNOGROUPS (per source)
// ============================================================================
// Loads parsers/<source>.py, builds feature/combination/architecture/absent
// for that source, writes the map + membership tables (+ dropped-orphan audit).

process build_annogroups {
    label 'local'

    input:
        val source

    output:
        val source, emit: built

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-build_annogroups.py \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 003: VALIDATE RESULTS (per source, fail-fast per §36)
// ============================================================================

process validate_results {
    label 'local'

    input:
        val source

    output:
        val source, emit: validated

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-validate_results.py \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 004: SPECIES TREE DECONVOLUTION (per source)
// ============================================================================
// Per-annogroup member-protein count within EVERY species-tree clade (node or
// tip): the non-redundant union across all structures + one file per structure.

process species_tree_deconvolution {
    label 'local'

    input:
        val source

    output:
        val source, emit: deconvolved

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-species_tree_deconvolution.py \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 005: PER-SPECIES SEQUENCE MAP (per source)
// ============================================================================
// The wide per-species companion to the deconvolution: per annogroup (feature /
// combination / architecture; absent excluded), the member sequence identifiers
// in each species, carrying annotation definitions.

process per_species_sequence_map {
    label 'local'

    input:
        val source

    output:
        val source, emit: mapped

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-per_species_sequence_map.py \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 006: COMPOSITE CLADES (per source)
// ============================================================================
// Each annogroup classified by four algorithms (exact, absent, core_urclade,
// core_early_clade), plus the curated manifest's summary counts and per-composite-
// clade detail tables.

process composite_clades {
    label 'local'

    input:
        val source

    output:
        val source, emit: composited

    script:
    """
    python3 ${projectDir}/scripts/006_ai-python-composite_clades.py \\
        --source ${source} \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 007: WRITE CROSS-SOURCE SUMMARY (once, after all sources validated)
// ============================================================================
// Per-source per-type annogroup breakdown + per-species and per-phylum matrices
// (annotation sources as columns).

process write_summary {
    label 'local'

    input:
        val all_sources_validated

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/007_ai-python-write_summary.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 008: WRITE RUN LOG (per §45)
// ============================================================================

process write_run_log {
    label 'local'

    input:
        val summary_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/008_ai-python-write_run_log.py \\
        --workflow-name "build_annogroups" \\
        --subproject-name "annogroups-BLOCK_build_annogroups" \\
        --project-name "${params.species_set_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // 001 runs once: resolve sources + build the proteome universe.
    resolve_sources_and_universe()

    // Read the resolved sources manifest (written by 001) and fan out per source.
    // The manifest lives under OUTPUT_pipeline/ (scripts own the data), so we
    // gate on 001's `ready` signal, then read the file and splitCsv it.
    sources_ch = resolve_sources_and_universe.out.ready
        .map { file( "${projectDir}/../${params.output.base_dir}/1-output/1_ai-sources_manifest.tsv" ) }
        .splitCsv( header: true )
        .map { row -> row.source }

    // 002 build -> 003 validate -> 004 species_tree_deconvolution -> 005
    // per_species_sequence_map -> 006 composite_clades, pipelined per source.
    built = build_annogroups( sources_ch )
    validated = validate_results( built.built )
    deconvolved = species_tree_deconvolution( validated.validated )
    mapped = per_species_sequence_map( deconvolved.deconvolved )
    composited = composite_clades( mapped.mapped )

    // Barrier: write the cross-source summary only after ALL sources are processed.
    write_summary( composited.composited.collect() )

    // Write the run log after the summary completes.
    write_run_log( write_summary.out.done )
}

// Completion summary handled by RUN-workflow.sh (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
