#!/usr/bin/env nextflow
/*
 * GIGANTIC hotspots - BLOCK_self_blast main.nf
 * AI: Claude Code | Opus 4.7 | 2026 May 04
 * Human: Eric Edsinger
 *
 * ===========================================================================
 * DESIGN OVERVIEW
 * ===========================================================================
 *
 * Runs blastp of each species' proteome against itself. Produces one
 * tabular report per species, consumed downstream by BLOCK_identify_hotspots.
 *
 * The per-species blastp would take many hours if run monolithically. This
 * workflow chunks each proteome into ~50 query chunks (~600 sequences each)
 * and fans the chunks out as a SLURM array on the burst QOS, then
 * concatenates per-species after all chunks complete.
 *
 * Per-species fan-out math (species70 defaults):
 *   ~30k sequences / 600 per chunk = ~50 chunks per species
 *   ~50 chunks × 70 species         = ~3500 fan-out tasks
 *   queueSize 200 × 5 cpus_per_task = ~1000 concurrent CPUs (under burst cap)
 *
 * ===========================================================================
 * INTERFACE CONVENTIONS
 * ===========================================================================
 *
 * Each numbered script writes to OUTPUT_pipeline/N-output/ via:
 *   - script invocation:  --output-dir N-output  (relative to work dir)
 *   - publishDir:         "${projectDir}/../${params.output_dir}"
 *                         which resolves to workflow_root/OUTPUT_pipeline/
 *   - filenames:          N_ai-<description>.<ext>
 *
 * ===========================================================================
 * PROCESS LABELS (defined in nextflow.config)
 * ===========================================================================
 *
 *   local_step    - Lightweight Python steps in the driver (validate, chunk,
 *                   merge, log).
 *   blastp_chunk  - One SLURM job per chunk on burst QOS. Retries on
 *                   transient failures with dynamic resource escalation.
 */

nextflow.enable.dsl = 2


// ============================================================================
// PARAMETERS (sourced from nextflow.config which loads START_HERE-user_config.yaml)
// ============================================================================

params.proteomes_dir = '../../../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes'
params.blast_db_dir = '../../../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_blastp'
params.gigantic_species_list = 'INPUT_user/gigantic_species_list.txt'
params.output_dir = 'OUTPUT_pipeline'
params.evalue = '1e-3'
params.outfmt = '6'
params.num_threads = 5
params.sequences_per_chunk = 600
params.project_name = 'GIGANTIC'
params.conda_environment = 'ai_gigantic_hotspots'


// ============================================================================
// PROCESS DEFINITIONS
// ============================================================================

/*
 * Process 1: Validate inputs.
 *
 * Pairs every species in the species list with its proteome and BLAST DB.
 * Emits processable manifest (drives chunking) and excluded-species TSV
 * (documents why species without inputs are dropped).
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
        --proteomes-dir ${projectDir}/../${params.proteomes_dir} \\
        --blast-db-dir ${projectDir}/../${params.blast_db_dir} \\
        --gigantic-species-list ${projectDir}/../${params.gigantic_species_list} \\
        --output-dir 1-output
    """
}


/*
 * Process 2: Chunk proteomes.
 *
 * Splits each processable proteome into FASTA chunks of N sequences. Emits
 * chunk_manifest.tsv (drives the fan-out channel) and per-species summary.
 */
process chunk_proteomes {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path processable_manifest

    output:
        path "2-output/2_ai-chunk_manifest.tsv",        emit: chunk_manifest
        path "2-output/2_ai-chunking_summary.tsv",      emit: chunking_summary
        path "2-output/chunks/**",                       emit: chunk_files
        path "2-output/2_ai-log-chunk_proteomes.log"

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-chunk_proteomes.py \\
        --processable-manifest ${processable_manifest} \\
        --blast-db-dir ${projectDir}/../${params.blast_db_dir} \\
        --sequences-per-chunk ${params.sequences_per_chunk} \\
        --output-dir 2-output
    """
}


/*
 * Process 3 (FAN-OUT): Run blastp for one query chunk vs its species DB.
 *
 * Each chunk becomes its own SLURM array task on burst QOS via the
 * 'blastp_chunk' label in nextflow.config. publishDir is intentionally NOT
 * set here to avoid copying ~3500 small files to OUTPUT_pipeline/. The pool
 * step (4) collects them via .collect() and the merged per-species reports
 * are the downstream-facing deliverable.
 */
process run_blastp_chunk {
    label 'blastp_chunk'

    input:
        tuple val(genus_species), val(chunk_index), path(query_chunk), val(blast_db_path), val(report_filename)

    output:
        path "${report_filename}"

    script:
    """
    bash ${projectDir}/scripts/003_ai-bash-run_blastp_chunk.sh \\
        --query-chunk ${query_chunk} \\
        --blast-db-path ${blast_db_path} \\
        --output-report ${report_filename} \\
        --evalue ${params.evalue} \\
        --outfmt ${params.outfmt} \\
        --num-threads ${task.cpus}
    """
}


/*
 * Process 4: Concatenate chunk reports per species.
 *
 * Verifies every chunk produced a report file (fail-fast on any missing)
 * and concatenates per-species into the deliverable per-species self-BLAST
 * reports.
 */
process concatenate_chunk_reports {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path "chunk_reports/*"
        path chunk_manifest

    output:
        path "4-output/self_blast_reports/*-self_blast.tsv",  emit: self_blast_reports
        path "4-output/4_ai-self_blast_summary.tsv",          emit: summary
        path "4-output/4_ai-log-concatenate_chunk_reports.log"

    script:
    """
    mkdir -p 4-output

    python3 ${projectDir}/scripts/004_ai-python-concatenate_chunk_reports.py \\
        --chunk-manifest ${chunk_manifest} \\
        --chunk-reports-dir chunk_reports \\
        --output-dir 4-output
    """
}


/*
 * Process 5: Write timestamped run log.
 *
 * Final process; depends on the per-species summary to ensure ordering.
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
        --workflow-name "self_blast" \\
        --subproject-name "hotspots" \\
        --project-name "${params.project_name}" \\
        --status success
    """
}


// ============================================================================
// WORKFLOW
// ============================================================================

workflow {

    // Stage 1: Validate inputs ----------------------------------------------
    validate_inputs()

    // Stage 2: Chunk proteomes ---------------------------------------------
    chunk_proteomes( validate_inputs.out.processable_manifest )

    // Stage 3: Fan-out blastp ----------------------------------------------
    //
    // Read the chunk manifest and emit one channel item per chunk.
    // Each item: ( genus_species, chunk_index, query_chunk_path, blast_db_path, report_filename )
    //
    // The chunk path comes through as a path() so NextFlow stages it into
    // each task's work dir. blast_db_path stays as a val() because the DB
    // is referenced by stem (multiple sidecar files); the bash wrapper
    // checks for .pdb/.pin presence at runtime.
    chunk_tasks_ch = chunk_proteomes.out.chunk_manifest
        .splitCsv( header: true, sep: '\t' )
        .map { row ->
            // CSV column header keys are quoted by Splitter as exact match;
            // the manifest uses self-documenting headers like
            // 'Genus_Species (species name in Genus_species format)'.
            // Use map.get with the long names rather than positional access.
            def headers = row.keySet() as List
            def gs_key      = headers.find { it.startsWith( 'Genus_Species' ) }
            def idx_key     = headers.find { it.startsWith( 'Chunk_Index' ) }
            def chunk_key   = headers.find { it.startsWith( 'Chunk_Path' ) }
            def db_key      = headers.find { it.startsWith( 'Blast_Db_Path' ) }
            def report_key  = headers.find { it.startsWith( 'Expected_Report_Filename' ) }
            tuple(
                row[ gs_key ],
                row[ idx_key ].toInteger(),
                file( row[ chunk_key ] ),
                row[ db_key ],
                row[ report_key ]
            )
        }

    run_blastp_chunk( chunk_tasks_ch )

    // Stage 4: Concatenate per species ------------------------------------
    concatenate_chunk_reports(
        run_blastp_chunk.out.collect(),
        chunk_proteomes.out.chunk_manifest
    )

    // Stage 5: Run log ----------------------------------------------------
    write_run_log( concatenate_chunk_reports.out.summary.map { true } )
}

// (NextFlow 26 strict DSL forbids workflow.onComplete and inline onComplete
// blocks; pipeline summary is printed by RUN-workflow.sh after exit code 0.)
