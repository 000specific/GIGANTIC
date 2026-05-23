#!/usr/bin/env nextflow
/*
 * GIGANTIC hotspots - BLOCK_identify_hotspots main.nf
 * AI: Claude Code | Opus 4.7 | 2026 May 04
 * Human: Eric Edsinger
 *
 * ===========================================================================
 * DESIGN OVERVIEW
 * ===========================================================================
 *
 * Per-species hotspot calling. Reads the per-species self-BLAST reports
 * produced by BLOCK_self_blast plus the user-provided gene coordinate
 * TSVs and emits per-species hotspot tables.
 *
 * Pipeline:
 *   1. validate_inputs           - pair every species with its 3 inputs
 *   2. filter_blast_by_evalue    - per-species: keep hits ≤ 1e-60, drop self-hits
 *   3. identify_hotspots          - per-species: window scan + union-find merge
 *   4. summarize_hotspots         - cross-species aggregate
 *   5. write_run_log              - timestamped run log to ai/logs/
 *
 * Per-species fan-out is via the 'identify_per_species' label. SLURM mode
 * is supported but typically not needed (light per-species cost).
 *
 * Strict NextFlow 26 DSL: no top-level def/import/onComplete; all dynamic
 * settings come from -params-file or environment variables exported by
 * RUN-workflow.sh from the user's yaml.
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (defaults; -params-file overrides)
// ============================================================================

params.self_blast_reports_dir = '../../output_to_input/BLOCK_self_blast/self_blast_reports'
params.gene_coordinates_dir   = '../../research_notebook/research_user/gene_coordinates'
params.proteomes_dir          = '../../../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes'
params.gigantic_species_list  = 'INPUT_user/gigantic_species_list.txt'
params.output_dir             = 'OUTPUT_pipeline'
params.evalue_threshold       = '1e-60'
params.window_size            = 20
params.minimum_paralog_count  = 2
params.project_name           = 'GIGANTIC'
params.conda_environment      = 'ai_gigantic_hotspots'


// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate inputs.
 * Pairs species with self-BLAST report, gene coordinates TSV, proteome.
 */
process validate_inputs {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-processable_species_manifest.tsv", emit: processable_manifest
        path "1-output/1_ai-excluded_species.tsv",             emit: excluded
        path "1-output/1_ai-species_processing_status.tsv",    emit: status
        path "1-output/1_ai-log-validate_inputs.log"

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_inputs.py \\
        --self-blast-reports-dir ${projectDir}/../${params.self_blast_reports_dir} \\
        --gene-coordinates-dir ${projectDir}/../${params.gene_coordinates_dir} \\
        --proteomes-dir ${projectDir}/../${params.proteomes_dir} \\
        --gigantic-species-list ${projectDir}/../${params.gigantic_species_list} \\
        --output-dir 1-output
    """
}


/*
 * Process 2: Filter self-BLAST hits by e-value (per species).
 * Drops self-vs-self diagonal hits and weak hits.
 */
process filter_blast_by_evalue {
    label 'identify_per_species'

    publishDir "${projectDir}/../${params.output_dir}/2-output", mode: 'copy', overwrite: true

    input:
        tuple val(genus_species), path(self_blast_report), path(gene_coordinates), path(proteome)

    output:
        tuple val(genus_species),
              path("2_ai-filtered_hits-${genus_species}.tsv"),
              path(gene_coordinates),
              path(proteome),                                              emit: per_species
        path "2_ai-filter_summary-${genus_species}.tsv",                   emit: filter_summary
        path "2_ai-log-filter_blast_by_evalue-${genus_species}.log"

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-filter_blast_by_evalue.py \\
        --self-blast-report ${self_blast_report} \\
        --genus-species ${genus_species} \\
        --evalue-threshold ${params.evalue_threshold} \\
        --output-dir .
    """
}


/*
 * Process 3: Identify hotspots (per species).
 * Modernized port of GIGANTIC_0 hotspots-003: window scan + union-find merge.
 */
process identify_hotspots {
    label 'identify_per_species'

    publishDir "${projectDir}/../${params.output_dir}/3-output", mode: 'copy', overwrite: true

    input:
        tuple val(genus_species), path(filtered_hits), path(gene_coordinates), path(proteome)

    output:
        path "3_ai-hotspots-${genus_species}.tsv",          emit: hotspots
        path "3_ai-hotspot_summary-${genus_species}.tsv",   emit: hotspot_summary
        path "3_ai-log-identify_hotspots-${genus_species}.log"

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-identify_hotspots.py \\
        --filtered-hits ${filtered_hits} \\
        --gene-coordinates ${gene_coordinates} \\
        --proteome ${proteome} \\
        --genus-species ${genus_species} \\
        --window-size ${params.window_size} \\
        --minimum-paralog-count ${params.minimum_paralog_count} \\
        --output-dir .
    """
}


/*
 * Process 4: Summarize hotspots across species.
 * Aggregates per-species hotspot summaries into project-level table.
 */
process summarize_hotspots {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path hotspot_summaries
        path hotspots
        path excluded_species

    output:
        path "4-output/4_ai-cross_species_hotspot_summary.tsv", emit: cross_species
        path "4-output/4_ai-project_hotspot_summary.tsv",        emit: project
        path "4-output/4_ai-log-summarize_hotspots.log"

    script:
    """
    mkdir -p 4-output
    mkdir -p staged_summaries
    mkdir -p staged_hotspots

    cp ${hotspot_summaries} staged_summaries/
    cp ${hotspots} staged_hotspots/

    python3 ${projectDir}/scripts/004_ai-python-summarize_hotspots.py \\
        --hotspot-summaries-dir staged_summaries \\
        --hotspots-dir staged_hotspots \\
        --excluded-species ${excluded_species} \\
        --output-dir 4-output
    """
}


/*
 * Process 5: Write run log.
 */
process write_run_log {
    label 'local_step'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \\
        --workflow-name "identify_hotspots" \\
        --subproject-name "hotspots" \\
        --project-name "${params.project_name}" \\
        --status success
    """
}


// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Stage 1: Validate inputs
    validate_inputs()

    // Build per-species channel from processable manifest
    species_channel = validate_inputs.out.processable_manifest
        .splitCsv( header: true, sep: '\t' )
        .map { row ->
            // Manifest headers carry self-documenting "(...)" suffix; match by prefix.
            def headers = row.keySet() as List
            def gs_key       = headers.find { it.startsWith( 'Genus_Species' ) }
            def blast_key    = headers.find { it.startsWith( 'Self_Blast_Report_Path' ) }
            def coords_key   = headers.find { it.startsWith( 'Gene_Coordinates_Path' ) }
            def proteome_key = headers.find { it.startsWith( 'Proteome_Path' ) }
            tuple(
                row[ gs_key ],
                file( row[ blast_key ] ),
                file( row[ coords_key ] ),
                file( row[ proteome_key ] )
            )
        }

    // Stage 2: Filter BLAST per species (parallel)
    filter_blast_by_evalue( species_channel )

    // Stage 3: Identify hotspots per species (parallel)
    identify_hotspots( filter_blast_by_evalue.out.per_species )

    // Stage 4: Summarize across species (collects all)
    summarize_hotspots(
        identify_hotspots.out.hotspot_summary.collect(),
        identify_hotspots.out.hotspots.collect(),
        validate_inputs.out.excluded
    )

    // Stage 5: Run log
    write_run_log( summarize_hotspots.out.cross_species.map { true } )
}
