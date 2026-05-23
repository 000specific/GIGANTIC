#!/usr/bin/env nextflow
/*
 * GIGANTIC Orthogroups - BLOCK_orthohmm_GIGANTIC main.nf
 * AI: Claude Code | Opus 4.7 | 2026 April 26
 * Human: Eric Edsinger
 *
 * ===========================================================================
 * DESIGN OVERVIEW
 * ===========================================================================
 *
 * OrthoHMM's all-vs-all phmmer step is the dominant cost (~95% of runtime
 * for 70 species) and phmmer scales poorly past ~8 cpus per process (HMMER
 * docs; OrthoHMM Issue #13). A native OrthoHMM run on 70 species at 100 cpus
 * achieved only 5.7% CPU efficiency before hitting NextFlow's 48h per-process
 * timeout in BLOCK_orthohmm RUN_4.
 *
 * BLOCK_orthohmm_GIGANTIC fixes this by parallelizing phmmer ACROSS species
 * pairs rather than within each phmmer call:
 *
 *   1. Extract OrthoHMM's exact phmmer command set via `orthohmm --stop prepare`
 *      (guarantees bit-identical phmmer invocation as native OrthoHMM)
 *   2. Submit each phmmer pair as its own SLURM burst-mode job (~4,830 jobs)
 *      via NextFlow's slurm executor on the 'phmmer_pair' label
 *   3. Pool the phmmer outputs into the directory layout OrthoHMM expects
 *   4. Run OrthoHMM with `--start search_res` to skip phmmer and execute
 *      Steps 2-5 (edge thresholds, network edges, MCL clustering, write)
 *
 * Why faster: phmmer's poor multi-threading is sidestepped because the 4,830
 * pairs run in parallel SLURM jobs (each with phmmer's sweet spot of ~5 cpus).
 * Burst QOS (moroz-b) provides the wide concurrency budget.
 *
 * Why consistent: by extracting commands via OrthoHMM's own `--stop prepare`
 * mechanism, we use exactly the flags OrthoHMM would have used internally.
 * No custom phmmer wrapper, no hand-coded flags.
 *
 * ===========================================================================
 * INTERFACE CONVENTIONS (matched to BLOCK_orthohmm proven pattern)
 * ===========================================================================
 *
 * Each numbered script writes to OUTPUT_pipeline/N-output/ via:
 *   - script invocation:  --output-dir N-output  (relative to work dir)
 *   - publishDir:         "${projectDir}/../${params.output_dir}"
 *                         which resolves to workflow_root/OUTPUT_pipeline/
 *   - filenames:          N_ai-<description>.<ext>
 *
 * Data flow uses a proteome_list.tsv (from script 001) as the canonical
 * proteome inventory between scripts (consistent with BLOCK_orthohmm).
 *
 * ===========================================================================
 * PROCESS LABELS (defined in nextflow.config)
 * ===========================================================================
 *
 *   local_step        - Lightweight steps inside the driver SLURM job
 *                       (validate, convert headers, extract commands, pool,
 *                       restore IDs, summary, QC, log).
 *
 *   phmmer_pair       - One SLURM job per phmmer pair on burst QOS. Retries
 *                       on transient failures (4,830 jobs means a few will
 *                       hit network/scheduler glitches; per-pair retry is
 *                       far cheaper than restarting the whole step).
 *
 *   orthohmm_finalize - Single OrthoHMM `--start search_res` call. Runs
 *                       inside the driver job with elevated cpu/memory to
 *                       handle MCL clustering and edge graph building.
 *
 * ===========================================================================
 */

nextflow.enable.dsl = 2


// ============================================================================
// PARAMETERS (sourced from nextflow.config which loads START_HERE-user_config.yaml)
// ============================================================================
// All defaults below match the COPYME yaml; users edit yaml, not main.nf.

params.proteomes_dir = '../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes'
params.output_dir = 'OUTPUT_pipeline'
params.evalue = '0.0001'
params.single_copy_threshold = '0.5'
params.project_name = 'GIGANTIC'
params.conda_environment = 'ai_gigantic_orthogroups_orthohmm'


// ============================================================================
// PROCESS DEFINITIONS
// ============================================================================

/*
 * Process 1: Validate proteomes and emit canonical proteome list.
 *
 * Reads the genomesDB STEP_4 proteomes directory, verifies all .aa files are
 * valid FASTA with GIGANTIC-style headers, counts sequences, writes a
 * proteome_list.tsv that drives all downstream scripts.
 *
 * Fails the pipeline if any file is malformed (fail-fast: research
 * integrity over permissive continuation).
 */
process validate_proteomes {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        val proteomes_dir

    output:
        path "1-output/1_ai-proteome_list.tsv", emit: proteome_list
        path "1-output/1_ai-log-validate_proteomes.log"

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_proteomes.py \\
        --proteomes-dir ${projectDir}/../${proteomes_dir} \\
        --output-dir 1-output
    """
}


/*
 * Process 2: Convert GIGANTIC headers to OrthoHMM-compatible short IDs.
 *
 * OrthoHMM's HMMER pipeline requires short FASTA headers (Genus_species-N).
 * Long GIGANTIC identifiers (e.g., g_GENEID-t_TRANSID-p_PROTID-n_Kingdom_...)
 * exceed phmmer's parser limits.
 *
 * The header_mapping.tsv is propagated to script 006 to restore full
 * GIGANTIC identifiers in the final output. Downstream tools see canonical
 * GIGANTIC long-form IDs.
 */
process convert_headers {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list

    output:
        path "2-output/2_ai-header_mapping.tsv", emit: header_mapping
        path "2-output/short_header_proteomes/*.pep", emit: short_header_proteomes
        path "2-output/2_ai-log-convert_headers_to_short_ids.log"

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-convert_headers_to_short_ids.py \\
        --proteome-list ${proteome_list} \\
        --output-dir 2-output
    """
}


/*
 * Process 3: Extract OrthoHMM's phmmer commands via `orthohmm --stop prepare`.
 *
 * CONSISTENCY GUARANTEE step. Rather than hand-construct phmmer commands and
 * risk drifting from OrthoHMM's internal behavior across versions, we let
 * OrthoHMM itself enumerate the commands it would run.
 *
 * `orthohmm --stop prepare` exits BEFORE running phmmer, printing the exact
 * command lines OrthoHMM would have executed. The script:
 *   - Captures these commands
 *   - Parses them into structured (taxa_a, taxa_b) pair records
 *   - Stores the canonical phmmer flag string (--mx BLOSUM62 --noali --notextw)
 *
 * Output is a TSV with one row per pair (taxa_a, taxa_b, output_filename).
 * This drives the fan-out channel feeding run_phmmer_pair.
 */
process extract_phmmer_commands {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path short_header_proteomes

    output:
        path "3-output/3_ai-phmmer_pair_manifest.tsv", emit: pair_manifest
        path "3-output/3_ai-orthohmm_prepare_stdout.txt"
        path "3-output/3_ai-log-extract_phmmer_commands.log"

    script:
    """
    mkdir -p 3-output/short_header_proteomes
    cp ${short_header_proteomes} 3-output/short_header_proteomes/

    python3 ${projectDir}/scripts/003_ai-python-extract_phmmer_commands.py \\
        --proteomes-dir 3-output/short_header_proteomes \\
        --evalue ${params.evalue} \\
        --output-dir 3-output
    """
}


/*
 * Process 4 (FAN-OUT): Run a single phmmer pair.
 *
 * Receives one (taxa_a, taxa_b) pair plus the two proteome files. Runs phmmer
 * using the canonical OrthoHMM flag set. Each invocation becomes its own SLURM
 * burst-mode job via the 'phmmer_pair' label in nextflow.config.
 *
 * The phmmer command structure here matches OrthoHMM's internal generator
 * (helpers.py:generate_phmmer_cmds in the orthohmm Python package) exactly.
 * Script 003 verifies the flag set against `orthohmm --stop prepare` output;
 * we only run this process if the flags match what we hardcode here.
 *
 * publishDir is intentionally NOT set here. With ~4,830 fan-out tasks, copying
 * each output to OUTPUT_pipeline would be wasteful. pool_and_verify_phmmer
 * gathers them into one publishDir at 4-output/.
 */
process run_phmmer_pair {
    label 'phmmer_pair'

    // Stage the entire short-header proteomes directory once per task. The
    // bash command then references files INSIDE that directory by their
    // taxa_a / taxa_b basenames. This avoids NextFlow's per-file staging
    // collision when taxa_a == taxa_b (self-pair, e.g. A_2_A.phmmerout.txt) —
    // staging the same file twice as separate path inputs triggers
    // "input file name collision -- multiple input files for: A.pep".
    input:
        tuple val(taxa_a), val(taxa_b), path(proteomes_dir)

    output:
        path "${taxa_a}_2_${taxa_b}.phmmerout.txt"

    script:
    // Canonical OrthoHMM phmmer flags (verified by script 003).
    // task.cpus comes from the phmmer_pair label resource block.
    """
    phmmer --mx BLOSUM62 --noali --notextw --cpu ${task.cpus} \\
        --tblout ${taxa_a}_2_${taxa_b}.phmmerout.txt \\
        ${proteomes_dir}/${taxa_a} ${proteomes_dir}/${taxa_b}
    """
}


/*
 * Process 5: Pool and verify all phmmer outputs.
 *
 * After the 4,830 phmmer_pair tasks complete, this process:
 *   (a) collects all phmmerout.txt files into orthohmm_working_res/, the
 *       directory layout OrthoHMM expects for `--start search_res`
 *   (b) verifies every expected pair is present (count matches the manifest
 *       from script 003)
 *   (c) verifies each file is well-formed (last line == "# [ok]" per phmmer
 *       convention; empty/truncated files indicate phmmer failure)
 *
 * Fails the pipeline (fail-fast) if any pair is missing or malformed.
 * Without this gate, OrthoHMM `--start search_res` could silently produce
 * incomplete orthogroup assignments — exactly the silent-artifact failure
 * mode CLAUDE.md prohibits.
 */
process pool_and_verify_phmmer {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path "phmmer_outputs/*"
        path pair_manifest

    output:
        path "4-output/orthohmm_working_res/*.phmmerout.txt", emit: pooled_phmmer_outputs
        path "4-output/4_ai-pool_verification_report.tsv", emit: verification_report
        path "4-output/4_ai-log-pool_and_verify_phmmer.log"

    script:
    """
    mkdir -p 4-output/orthohmm_working_res

    python3 ${projectDir}/scripts/004_ai-python-pool_and_verify_phmmer_outputs.py \\
        --phmmer-outputs-dir phmmer_outputs \\
        --pair-manifest ${pair_manifest} \\
        --output-dir 4-output
    """
}


/*
 * Process 6: Run OrthoHMM with --start search_res (Steps 2-5).
 *
 * With pooled phmmer outputs in place, OrthoHMM skips Step 1 (phmmer) and
 * runs Steps 2-5 in a single invocation:
 *   Step 2: Determining edge thresholds
 *   Step 3: Identifying network edges
 *   Step 4: Conducting clustering (MCL)
 *   Step 5: Writing orthogroup information
 *
 * These are read/compute-on-existing-data steps — much cheaper than Step 1
 * (already done in parallel). Total Steps 2-5 on 70 species typically a few
 * hours.
 *
 * Sized via the orthohmm_finalize label (40 cpu / 300 GB by default) to cover
 * the peak memory observed in BLOCK_orthohmm RUN_4 (216 GB) plus margin.
 * MCL is the typical memory bottleneck for the finalize step.
 */
process run_orthohmm_from_search_res {
    label 'orthohmm_finalize'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path pooled_phmmer_outputs
        path short_header_proteomes

    output:
        path "5-output/orthohmm_orthogroups.txt", emit: orthogroups
        path "5-output/orthohmm_gene_count.txt", emit: gene_count
        path "5-output/orthohmm_single_copy_orthogroups.txt", emit: single_copy_orthogroups
        path "5-output/5_ai-log-run_orthohmm_from_search_res.log"

    script:
    """
    mkdir -p 5-output/input_proteomes
    mkdir -p 5-output/orthohmm_working_res

    cp ${short_header_proteomes} 5-output/input_proteomes/
    cp ${pooled_phmmer_outputs} 5-output/orthohmm_working_res/

    bash ${projectDir}/scripts/005_ai-bash-run_orthohmm_from_search_res.sh \\
        --input-dir 5-output/input_proteomes \\
        --working-res-dir 5-output/orthohmm_working_res \\
        --output-dir 5-output \\
        --cpus ${task.cpus} \\
        --evalue ${params.evalue} \\
        --single-copy-threshold ${params.single_copy_threshold}
    """
}


/*
 * Process 7: Restore GIGANTIC identifiers in the final orthogroup tables.
 *
 * OrthoHMM produces orthogroups using the short IDs from script 002. This
 * process replaces them with the original GIGANTIC long-form identifiers
 * using the header_mapping.tsv from script 002. Output filenames match the
 * canonical names BLOCK_orthohmm publishes so downstream subprojects can
 * consume either workflow's output.
 */
process restore_identifiers {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path header_mapping
        path orthogroups
        path gene_count

    output:
        path "6-output/6_ai-orthogroups_gigantic_ids.tsv", emit: orthogroups_gigantic
        path "6-output/6_ai-gene_count_gigantic_ids.tsv", emit: gene_count_gigantic
        path "6-output/6_ai-log-restore_gigantic_identifiers.log"

    script:
    """
    mkdir -p 6-output/orthohmm_output

    cp ${orthogroups} 6-output/orthohmm_output/
    cp ${gene_count} 6-output/orthohmm_output/

    python3 ${projectDir}/scripts/006_ai-python-restore_gigantic_identifiers.py \\
        --header-mapping ${header_mapping} \\
        --orthohmm-dir 6-output/orthohmm_output \\
        --output-dir 6-output
    """
}


/*
 * Process 8: Generate orthogroup-level summary statistics.
 *
 * Counts (total orthogroups, single-copy count, size distribution, etc.)
 * across all 70 species. Output is a single self-documenting TSV.
 */
process generate_summary_statistics {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list
        path orthogroups_gigantic

    output:
        path "7-output/7_ai-summary_statistics.tsv", emit: summary_statistics
        path "7-output/7_ai-orthogroup_size_distribution.tsv", emit: size_distribution
        path "7-output/7_ai-log-generate_summary_statistics.log"

    script:
    """
    mkdir -p 7-output

    python3 ${projectDir}/scripts/007_ai-python-generate_summary_statistics.py \\
        --proteome-list ${proteome_list} \\
        --orthogroups-file ${orthogroups_gigantic} \\
        --output-dir 7-output
    """
}


/*
 * Process 9: Per-species QC analysis.
 *
 * Per-species checks (gene count, orthogroup membership rate, single-copy
 * gene count, etc.) so a user can spot outlier species (e.g., low recovery
 * suggesting proteome quality issues). One row per species.
 */
process qc_analysis_per_species {
    label 'local_step'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list
        path orthogroups_gigantic

    output:
        path "8-output/8_ai-per_species_summary.tsv", emit: per_species_summary
        path "8-output/8_ai-log-qc_analysis_per_species.log"

    script:
    """
    mkdir -p 8-output

    python3 ${projectDir}/scripts/008_ai-python-qc_analysis_per_species.py \\
        --proteome-list ${proteome_list} \\
        --orthogroups-file ${orthogroups_gigantic} \\
        --output-dir 8-output
    """
}


/*
 * Process 10: Write timestamped run log.
 *
 * Final process; depends on per_species_summary to ensure ordering. Writes
 * a structured log to ai/logs/ documenting parameters and outputs. Helps
 * reproduce / audit specific runs.
 */
process write_run_log {
    label 'local_step'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/009_ai-python-write_run_log.py \\
        --workflow-name "run_orthohmm_GIGANTIC" \\
        --subproject-name "orthogroups" \\
        --project-name "${params.project_name}" \\
        --status success
    """
}


// ============================================================================
// WORKFLOW
// ============================================================================
//
// Channel design notes:
//
//   - proteomes_dir is a value channel (single directory).
//   - The phmmer fan-out (process 4) is driven by splitting the pair manifest
//     from script 003 into one channel item per pair. NextFlow auto-submits
//     one task per tuple to the SLURM burst executor.
//   - phmmer outputs are .collect()ed before pool_and_verify so the pool
//     process sees ALL outputs at once (it does presence/integrity verification
//     across the full set).
//   - restore_identifiers fans into both summary and per-species QC, which
//     run in parallel. write_run_log waits for QC.
//
// NOTE: Symlinks for output_to_input/BLOCK_orthohmm_GIGANTIC/ are created
// by RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.

workflow {

    // -------------------------------------------------------------------
    // Stage 1: Validate inputs and prep
    // -------------------------------------------------------------------
    validate_proteomes(params.proteomes_dir)

    convert_headers(validate_proteomes.out.proteome_list)

    extract_phmmer_commands(convert_headers.out.short_header_proteomes)

    // -------------------------------------------------------------------
    // Stage 2: Phmmer fan-out (one SLURM burst job per pair)
    // -------------------------------------------------------------------
    //
    // Read the pair manifest and emit one channel item per pair.
    // Each item carries: (taxa_a, taxa_b, path_to_proteome_a, path_to_proteome_b).
    // proteomes_path field in the manifest tells us where the .pep files live;
    // we resolve relative to the workflow root (projectDir/..).
    //
    // Stage the proteomes directory once per task; the bash command references
    // taxa_a / taxa_b files INSIDE it. Avoids NextFlow's per-file staging
    // collision when taxa_a == taxa_b (self-pairs).
    proteomes_dir_ch = Channel.value( file("${projectDir}/../${params.output_dir}/2-output/short_header_proteomes") )

    pair_tuples_ch = extract_phmmer_commands.out.pair_manifest
        .splitCsv(header: true, sep: '\t')
        .combine( proteomes_dir_ch )
        .map { row, proteomes_dir ->
            tuple( row.taxa_a, row.taxa_b, proteomes_dir )
        }

    run_phmmer_pair(pair_tuples_ch)

    // -------------------------------------------------------------------
    // Stage 3: Pool, verify, finalize
    // -------------------------------------------------------------------
    pool_and_verify_phmmer(
        run_phmmer_pair.out.collect(),
        extract_phmmer_commands.out.pair_manifest
    )

    run_orthohmm_from_search_res(
        pool_and_verify_phmmer.out.pooled_phmmer_outputs.collect(),
        convert_headers.out.short_header_proteomes.collect()
    )

    // -------------------------------------------------------------------
    // Stage 4: Restore IDs and produce summaries
    // -------------------------------------------------------------------
    restore_identifiers(
        convert_headers.out.header_mapping,
        run_orthohmm_from_search_res.out.orthogroups,
        run_orthohmm_from_search_res.out.gene_count
    )

    generate_summary_statistics(
        validate_proteomes.out.proteome_list,
        restore_identifiers.out.orthogroups_gigantic
    )

    qc_analysis_per_species(
        validate_proteomes.out.proteome_list,
        restore_identifiers.out.orthogroups_gigantic
    )

    write_run_log(qc_analysis_per_species.out.per_species_summary)
}


// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC Orthogroups - BLOCK_orthohmm_GIGANTIC Pipeline Complete!"
    println "========================================================================"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if (workflow.success) {
        println "Output files in ${params.output_dir}/:"
        println "  1-output/: Validated proteome list"
        println "  2-output/: Short-header proteomes and mapping"
        println "  3-output/: Phmmer pair manifest (extracted from OrthoHMM --stop prepare)"
        println "  4-output/: Pooled phmmer outputs and verification report"
        println "  5-output/: OrthoHMM finalization results (Steps 2-5)"
        println "  6-output/: Orthogroups with restored GIGANTIC identifiers"
        println "  7-output/: Summary statistics"
        println "  8-output/: Per-species QC analysis"
        println ""
        println "Symlinks created in output_to_input/BLOCK_orthohmm_GIGANTIC/ (by RUN-workflow.sh)"
        println "Run log written to ai/logs/ in this workflow directory"
    }
    println "========================================================================"
}
