#!/usr/bin/env nextflow
/*
 * GIGANTIC dark_proteome - BLOCK_classify_dark_proteome main.nf
 * AI: Claude Code | Opus 4.7 | 2026 May 04
 * Human: Eric Edsinger
 *
 * ===========================================================================
 * DESIGN OVERVIEW
 * ===========================================================================
 *
 * Three-axis dark-matter classification (Edsinger 2024) per species:
 *   axis_a — reference BLAST (one_direction_homologs top hits)
 *   axis_b — reference orthogroup membership (orthogroups OG → reference species)
 *   axis_c — HMM annotation (Pfam/PANTHER from annotations_hmms)
 *
 * A gene is DARK if and only if all three axes are False.
 *
 * Pipeline:
 *   1. validate_inputs                  - pair every species with its 4 inputs
 *   2. build_reference_orthogroup_set   - one-time pre-process; OGs containing reference species
 *   3. classify_per_species             - per-species fan-out: 3-axis check
 *   4. summarize_dark_proteome          - cross-species aggregate
 *   5. write_run_log                    - timestamped run log
 *
 * Strict NextFlow 26 DSL: no top-level def/import/onComplete; -params-file
 * for params, env vars (set by RUN-workflow.sh) for executor decisions.
 */

nextflow.enable.dsl = 2


// ============================================================================
// PARAMETERS (defaults; -params-file overrides)
// ============================================================================

params.proteomes_dir          = '../../../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes'
params.reference_blast_dir    = '../../../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits'
params.orthogroups_file       = '../../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv'
params.hmm_annotations_dir    = '../../../annotations_hmms/output_to_input/BLOCK_interproscan_parsed'
params.gigantic_species_list  = 'INPUT_user/gigantic_species_list.txt'
params.output_dir             = 'OUTPUT_pipeline'
params.reference_blast_mode   = 'strict_reference'
// Reference species and HMM databases come in as YAML lists; -params-file
// converts them to comma-joinable forms in the script blocks below.
params.reference_species      = [ 'Homo_sapiens', 'Drosophila_melanogaster', 'Caenorhabditis_elegans' ]
params.hmm_databases          = [ 'pfam', 'panther' ]
params.project_name           = 'GIGANTIC'
params.conda_environment      = 'ai_gigantic_hotspots'


// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate inputs.
 * Pairs species with proteome, reference BLAST, HMM annotations.
 * Verifies reference species are present in proteomes_dir.
 */
process validate_inputs {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-processable_species_manifest.tsv", emit: processable_manifest
        path "1-output/1_ai-excluded_species.tsv",             emit: excluded
        path "1-output/1_ai-species_processing_status.tsv",    emit: status
        path "1-output/1_ai-reference_species_audit.tsv",      emit: reference_audit
        path "1-output/1_ai-log-validate_inputs.log"

    script:
    def hmm_dbs_csv = (params.hmm_databases instanceof List) ? params.hmm_databases.join(',') : params.hmm_databases.toString()
    def ref_species_csv = (params.reference_species instanceof List) ? params.reference_species.join(',') : params.reference_species.toString()
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_inputs.py \\
        --proteomes-dir ${projectDir}/../${params.proteomes_dir} \\
        --reference-blast-dir ${projectDir}/../${params.reference_blast_dir} \\
        --orthogroups-file ${projectDir}/../${params.orthogroups_file} \\
        --hmm-annotations-dir ${projectDir}/../${params.hmm_annotations_dir} \\
        --hmm-databases "${hmm_dbs_csv}" \\
        --reference-species "${ref_species_csv}" \\
        --gigantic-species-list ${projectDir}/../${params.gigantic_species_list} \\
        --output-dir 1-output
    """
}


/*
 * Process 2: Build reference orthogroup set.
 * One-time project-level pre-processing: identifies OGs with reference species.
 * Emits per-gene index used by all per-species classification tasks.
 */
process build_reference_orthogroup_set {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "2-output/2_ai-reference_orthogroups.tsv",          emit: reference_orthogroups
        path "2-output/2_ai-orthogroup_membership_index.tsv",    emit: membership_index
        path "2-output/2_ai-reference_orthogroup_summary.tsv",   emit: summary
        path "2-output/2_ai-log-build_reference_orthogroup_set.log"

    script:
    def ref_species_csv = (params.reference_species instanceof List) ? params.reference_species.join(',') : params.reference_species.toString()
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-build_reference_orthogroup_set.py \\
        --orthogroups-file ${projectDir}/../${params.orthogroups_file} \\
        --reference-species "${ref_species_csv}" \\
        --output-dir 2-output
    """
}


/*
 * Process 3 (FAN-OUT): Classify dark proteome per species.
 * Each species gets a 3-axis check producing per-gene DARK/ANNOTATED labels.
 */
process classify_per_species {
    label 'classify_per_species'

    publishDir "${projectDir}/../${params.output_dir}/3-output", mode: 'copy', overwrite: true

    input:
        tuple val(genus_species), val(proteome), val(reference_blast), val(hmm_db_names_csv), val(hmm_paths_csv)
        path membership_index

    output:
        path "3_ai-dark_proteome-${genus_species}.tsv",           emit: classification
        path "3_ai-dark_proteome_summary-${genus_species}.tsv",   emit: per_species_summary
        path "3_ai-log-classify_per_species-${genus_species}.log"

    script:
    def ref_species_csv = (params.reference_species instanceof List) ? params.reference_species.join(',') : params.reference_species.toString()
    """
    python3 ${projectDir}/scripts/003_ai-python-classify_per_species.py \\
        --proteome ${proteome} \\
        --reference-blast ${reference_blast} \\
        --orthogroup-membership-index ${membership_index} \\
        --hmm-database-names "${hmm_db_names_csv}" \\
        --hmm-annotation-paths "${hmm_paths_csv}" \\
        --reference-blast-mode ${params.reference_blast_mode} \\
        --reference-species "${ref_species_csv}" \\
        --genus-species ${genus_species} \\
        --output-dir .
    """
}


/*
 * Process 4: Summarize across species.
 */
process summarize_dark_proteome {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path per_species_summaries
        path excluded_species
        path reference_orthogroup_summary

    output:
        path "4-output/4_ai-cross_species_dark_proteome_summary.tsv", emit: cross_species
        path "4-output/4_ai-project_dark_proteome_summary.tsv",        emit: project
        path "4-output/4_ai-log-summarize_dark_proteome.log"

    script:
    """
    mkdir -p 4-output
    mkdir -p staged_summaries
    cp ${per_species_summaries} staged_summaries/

    python3 ${projectDir}/scripts/004_ai-python-summarize_dark_proteome.py \\
        --dark-proteome-summaries-dir staged_summaries \\
        --excluded-species ${excluded_species} \\
        --reference-orthogroup-summary ${reference_orthogroup_summary} \\
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
        --workflow-name "classify_dark_proteome" \\
        --subproject-name "dark_proteome" \\
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

    // Stage 2: Build project-wide reference orthogroup index (runs in parallel
    // with validate_inputs would be possible, but cleaner to wait so any
    // validation failure stops the pipeline before this expensive step).
    build_reference_orthogroup_set()

    // Stage 3: Per-species fan-out
    species_channel = validate_inputs.out.processable_manifest
        .splitCsv( header: true, sep: '\t' )
        .map { row ->
            def headers = row.keySet() as List
            def gs_key       = headers.find { it.startsWith( 'Genus_Species' ) }
            def proteome_key = headers.find { it.startsWith( 'Proteome_Path' ) }
            def blast_key    = headers.find { it.startsWith( 'Reference_Blast_Path' ) }
            def db_key       = headers.find { it.startsWith( 'Hmm_Database_Names_CSV' ) }
            def paths_key    = headers.find { it.startsWith( 'Hmm_Annotation_Paths_CSV' ) }
            tuple(
                row[ gs_key ],
                row[ proteome_key ],
                row[ blast_key ],
                row[ db_key ],
                row[ paths_key ]
            )
        }

    classify_per_species( species_channel, build_reference_orthogroup_set.out.membership_index )

    // Stage 4: Summarize
    summarize_dark_proteome(
        classify_per_species.out.per_species_summary.collect(),
        validate_inputs.out.excluded,
        build_reference_orthogroup_set.out.summary
    )

    // Stage 5: Run log
    write_run_log( summarize_dark_proteome.out.cross_species.map { true } )
}
