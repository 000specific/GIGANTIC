#!/usr/bin/env nextflow
/*
 * GIGANTIC Orthogroups - BLOCK_orthofinder_array main.nf
 * AI: Claude Code | Opus 4.7 | 2026 April 27
 * Human: Eric Edsinger
 *
 * ===========================================================================
 * DESIGN OVERVIEW
 * ===========================================================================
 *
 * OrthoFinder's all-vs-all sequence-search step (DIAMOND by default, BLAST
 * optionally) is the dominant cost for large species sets. For 70 species
 * the search step is N² = 4,900 pairwise alignments; even DIAMOND is
 * single-machine-bound and accumulates real wall time.
 *
 * BLOCK_orthofinder_array fixes this by parallelizing the search step
 * ACROSS species pairs rather than within a single OrthoFinder process:
 *
 *   1. Run OrthoFinder with `-op` to extract the canonical DIAMOND/BLAST
 *      command set (also runs makeblastdb internally; printed commands
 *      reference the prepared proteomes/databases)
 *   2. Submit each pair as its own SLURM job-array task in burst mode
 *      via NextFlow's slurm executor with process.array = 100
 *   3. Pool the search outputs into the directory layout OrthoFinder
 *      expects for `-b` resume
 *   4. Run OrthoFinder with `-b <pooled_dir>` to skip search and execute
 *      the downstream pipeline (orthogroup clustering + gene-tree
 *      inference + species-tree + duplication/loss reconciliation)
 *
 * Why faster: the per-pair DIAMOND calls run in parallel SLURM tasks
 * (each at DIAMOND's natural multi-thread sweet spot of ~2-4 cpus).
 * Burst QOS (moroz-b) provides the wide concurrency budget.
 *
 * Why consistent: by extracting commands via OrthoFinder's own `-op`
 * mechanism, we use exactly the search invocation OrthoFinder would have
 * used internally. No custom DIAMOND wrapper, no hand-coded flags.
 *
 * ===========================================================================
 * INTERFACE CONVENTIONS (matched to BLOCK_orthofinder proven pattern)
 * ===========================================================================
 *
 * Each numbered script writes to OUTPUT_pipeline/N-output/ via:
 *   - script invocation:  --output-dir N-output  (relative to work dir)
 *   - publishDir:         "${projectDir}/../${params.output.base_dir}"
 *                         which resolves to workflow_root/OUTPUT_pipeline/
 *   - filenames:          N_ai-<description>.<ext>
 *
 * Data flow uses a proteome_list.tsv (from script 001) as the canonical
 * proteome inventory between scripts (consistent with BLOCK_orthofinder
 * and BLOCK_orthohmm_array).
 *
 * ===========================================================================
 * PROCESS LABELS (defined in nextflow.config)
 * ===========================================================================
 *
 *   local_step           - Lightweight steps inside the driver SLURM job
 *                          (validate, prepare, extract commands, pool,
 *                          standardize, summary, QC, log).
 *
 *   diamond_pair         - One SLURM array-task per pair on burst QOS.
 *                          process.array = 100 bundles tasks into actual
 *                          SLURM job arrays for scheduler-friendly fan-out.
 *                          Retries on transient failures.
 *
 *   orthofinder_finalize - Single OrthoFinder `-b` call. Runs inside the
 *                          driver job with elevated cpu/memory to handle
 *                          orthogroup clustering, tree inference, and
 *                          reconciliation.
 *
 * ===========================================================================
 */

nextflow.enable.dsl = 2


// ============================================================================
// PARAMETERS (sourced from nextflow.config defaults + -params-file overrides)
// ============================================================================
// All defaults live in nextflow.config; users edit START_HERE-user_config.yaml,
// not this file. Nested params (params.X.Y.Z) mirror the yaml shape.


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
 * Fails the pipeline if any file is malformed (fail-fast: research integrity
 * over permissive continuation).
 */
process validate_proteomes {
    label 'local_step'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

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
 * Process 2: Prepare proteomes for OrthoFinder input.
 *
 * Copies/renames proteomes into the directory layout OrthoFinder expects
 * (orthofinder_input_proteomes/). Reuses logic from BLOCK_orthofinder.
 */
process prepare_proteomes {
    label 'local_step'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list

    output:
        path "2-output/orthofinder_input_proteomes/*", emit: prepared_proteomes
        path "2-output/2_ai-prepared_proteomes_summary.tsv"
        path "2-output/2_ai-log-prepare_proteomes.log"

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-prepare_proteomes.py \\
        --proteome-list ${proteome_list} \\
        --output-dir 2-output
    """
}


/*
 * Process 3: Extract OrthoFinder's search commands via `orthofinder -op`.
 *
 * CONSISTENCY GUARANTEE step. Rather than hand-construct DIAMOND/BLAST
 * commands and risk drifting from OrthoFinder's internal behavior across
 * versions, we let OrthoFinder enumerate them itself.
 *
 * `orthofinder -op` (per the OrthoFinder manual): "prepare the files in the
 * format required by OrthoFinder and print the set of BLAST commands that
 * need to be run". Internally runs makeblastdb and prints all pairwise
 * search commands to stdout. Designed exactly for HPC fan-out workflows.
 *
 * Output is a TSV with one row per pair (taxa_a, taxa_b, output_filename).
 * This drives the fan-out channel feeding run_diamond_pair.
 */
process extract_orthofinder_search_commands {
    label 'local_step'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path prepared_proteomes

    output:
        path "3-output/3_ai-search_pair_manifest.tsv", emit: pair_manifest
        path "3-output/orthofinder_workdir/**", emit: orthofinder_workdir
        path "3-output/3_ai-orthofinder_op_stdout.txt"
        path "3-output/3_ai-log-extract_orthofinder_search_commands.log"

    script:
    """
    mkdir -p 3-output/orthofinder_input_proteomes
    cp ${prepared_proteomes} 3-output/orthofinder_input_proteomes/

    python3 ${projectDir}/scripts/003_ai-python-extract_orthofinder_search_commands.py \\
        --proteomes-dir 3-output/orthofinder_input_proteomes \\
        --search-method ${params.orthofinder.search_method} \\
        --output-dir 3-output
    """
}


/*
 * Process 4 (FAN-OUT): Run a single DIAMOND/BLAST pair.
 *
 * Receives one search command extracted by script 003. Runs the command as-is
 * (preserving OrthoFinder's exact flags). Each invocation becomes one SLURM
 * array-task via the 'diamond_pair' label in nextflow.config.
 *
 * Each task is given the prepared OrthoFinder workdir (containing the
 * makeblastdb-built databases and properly-renamed Species{N}.fa files) so
 * the search command (which references those exact paths) can find its
 * inputs.
 *
 * publishDir is intentionally NOT set here. With ~4,830 fan-out tasks,
 * copying each output to OUTPUT_pipeline would be wasteful.
 * pool_and_verify_diamond_outputs gathers them into one publishDir at
 * 5-output/.
 */
process run_diamond_pair {
    label 'diamond_pair'

    // The search_command was extracted by script 003 from `orthofinder -op`.
    // It uses ABSOLUTE paths into the published workdir for -d (database)
    // and -q (query), but a RELATIVE basename for -o (rewritten by script
    // 003). So the command:
    //   - reads inputs from the shared filesystem (Blue) via absolute paths
    //   - writes the output Blast{A}_{B}.txt INTO this task's work dir
    // NextFlow's `output: path output_filename` then matches the work-dir file.
    //
    // We do NOT stage the workdir as a path() input. Doing so would symlink/copy
    // the entire workdir into 4,830 task work dirs, which is wasteful and
    // unnecessary — the absolute paths already work because Blue is shared.
    // Process ordering is enforced because pair_tuples_ch derives from
    // extract_orthofinder_search_commands.out, so NextFlow won't start any
    // run_diamond_pair task until script 003 completes.
    input:
        tuple val(taxa_a), val(taxa_b), val(output_filename), val(search_command)

    output:
        path output_filename

    script:
    """
    ${search_command}
    """
}


/*
 * Process 5: Pool and verify all DIAMOND/BLAST outputs.
 *
 * After the ~4,830 diamond_pair tasks complete, this process:
 *   (a) collects all search-output files into the directory layout OrthoFinder
 *       expects for `-b` resume
 *   (b) verifies every expected pair from the manifest is present
 *   (c) verifies each file is non-empty (truncated/empty files indicate
 *       DIAMOND killed mid-run)
 *
 * Fails the pipeline (fail-fast) if any pair is missing or malformed.
 * Without this gate, OrthoFinder `-b` could silently produce incomplete
 * orthogroup assignments — exactly the silent-artifact failure mode
 * CLAUDE.md prohibits.
 */
process pool_and_verify_diamond_outputs {
    label 'local_step'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path "diamond_outputs/*"
        path pair_manifest
        path orthofinder_workdir

    output:
        path "5-output/orthofinder_workdir_with_results/**", emit: pooled_workdir
        path "5-output/5_ai-pool_verification_report.tsv"
        path "5-output/5_ai-log-pool_and_verify_diamond_outputs.log"

    script:
    """
    mkdir -p 5-output

    python3 ${projectDir}/scripts/005_ai-python-pool_and_verify_diamond_outputs.py \\
        --diamond-outputs-dir diamond_outputs \\
        --pair-manifest ${pair_manifest} \\
        --orthofinder-workdir ${orthofinder_workdir} \\
        --output-dir 5-output
    """
}


/*
 * Process 6: Run OrthoFinder with -b (resume from BLAST results).
 *
 * With pooled DIAMOND outputs in place, OrthoFinder skips the search step
 * and runs:
 *   - Orthogroup clustering (MCL)
 *   - Gene-tree inference (one tree per orthogroup — typically the new
 *     dominant cost; benefits from many cores)
 *   - Species-tree inference (STAG / consensus)
 *   - Duplication/loss reconciliation
 *
 * Sized via the orthofinder_finalize label (48 cpu / 360 GB / 96h by
 * default). Tree inference dominates here.
 */
process run_orthofinder_from_blast {
    label 'orthofinder_finalize'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path pooled_workdir

    output:
        path "6-output/orthofinder_output/**", emit: orthofinder_output
        path "6-output/6_ai-log-run_orthofinder_from_blast.log"

    script:
    """
    mkdir -p 6-output

    bash ${projectDir}/scripts/006_ai-bash-run_orthofinder_from_blast.sh \\
        --pooled-workdir ${pooled_workdir} \\
        --output-dir 6-output \\
        --cpus ${task.cpus} \\
        --search-method ${params.orthofinder.search_method} \\
        --mcl-inflation ${params.orthofinder.mcl_inflation}
    """
}


/*
 * Process 7: Standardize OrthoFinder output to GIGANTIC format.
 *
 * OrthoFinder publishes orthogroups in its own species×OG matrix format.
 * This process converts that into the GIGANTIC long-form orthogroup TSV
 * with restored GIGANTIC identifiers. Output filenames match the canonical
 * names BLOCK_orthofinder publishes so downstream subprojects can consume
 * either workflow's output.
 */
process standardize_output {
    label 'local_step'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path orthofinder_output
        path proteome_list

    output:
        path "7-output/7_ai-orthogroups_gigantic_ids.tsv", emit: orthogroups_gigantic
        path "7-output/7_ai-gene_count_gigantic_ids.tsv", emit: gene_count_gigantic
        path "7-output/7_ai-log-standardize_output.log"

    script:
    """
    mkdir -p 7-output

    python3 ${projectDir}/scripts/007_ai-python-standardize_output.py \\
        --orthofinder-dir ${orthofinder_output} \\
        --proteome-list ${proteome_list} \\
        --output-dir 7-output
    """
}


/*
 * Process 8: Generate orthogroup-level summary statistics.
 *
 * Counts (total orthogroups, single-copy count, size distribution, etc.)
 * across all species. Output is a single self-documenting TSV.
 */
process generate_summary_statistics {
    label 'local_step'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list
        path orthogroups_gigantic

    output:
        path "8-output/8_ai-summary_statistics.tsv", emit: summary_statistics
        path "8-output/8_ai-orthogroup_size_distribution.tsv", emit: size_distribution
        path "8-output/8_ai-log-generate_summary_statistics.log"

    script:
    """
    mkdir -p 8-output

    python3 ${projectDir}/scripts/008_ai-python-generate_summary_statistics.py \\
        --proteome-list ${proteome_list} \\
        --orthogroups-file ${orthogroups_gigantic} \\
        --output-dir 8-output
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

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path proteome_list
        path orthogroups_gigantic

    output:
        path "9-output/9_ai-per_species_summary.tsv", emit: per_species_summary
        path "9-output/9_ai-log-qc_analysis_per_species.log"

    script:
    """
    mkdir -p 9-output

    python3 ${projectDir}/scripts/009_ai-python-qc_analysis_per_species.py \\
        --proteome-list ${proteome_list} \\
        --orthogroups-file ${orthogroups_gigantic} \\
        --output-dir 9-output
    """
}


/*
 * Process 10: Write timestamped run log.
 *
 * Final process; depends on per_species_summary to ensure ordering.
 */
process write_run_log {
    label 'local_step'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/010_ai-python-write_run_log.py \\
        --workflow-name "run_orthofinder_array" \\
        --subproject-name "orthogroups" \\
        --project-name "${params.project.name}" \\
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
//   - The DIAMOND fan-out (process 4) is driven by splitting the pair manifest
//     from script 003 into one channel item per pair. NextFlow auto-submits
//     each tuple to the SLURM burst executor, bundled into job arrays via
//     process.array = 100.
//   - DIAMOND outputs are .collect()ed before pool_and_verify so the pool
//     process sees ALL outputs at once for presence/integrity verification.
//   - standardize_output fans into both summary and per-species QC, which
//     run in parallel. write_run_log waits for QC.
//
// NOTE: Symlinks for output_to_input/BLOCK_orthofinder_array/ are created
// by RUN-workflow.sh AFTER this pipeline completes.

workflow {

    // -------------------------------------------------------------------
    // Stage 1: Validate inputs and prep
    // -------------------------------------------------------------------
    validate_proteomes(params.inputs.proteomes_dir)

    prepare_proteomes(validate_proteomes.out.proteome_list)

    extract_orthofinder_search_commands(prepare_proteomes.out.prepared_proteomes)

    // -------------------------------------------------------------------
    // Stage 2: DIAMOND fan-out (one SLURM array task per pair)
    // -------------------------------------------------------------------
    //
    // Read the pair manifest and emit one channel item per pair.
    // Each item carries: (taxa_a, taxa_b, output_filename, search_command, workdir).
    //
    pair_tuples_ch = extract_orthofinder_search_commands.out.pair_manifest
        .splitCsv(header: true, sep: '\t')
        .map { row ->
            tuple( row.taxa_a, row.taxa_b, row.output_filename, row.search_command )
        }

    run_diamond_pair(pair_tuples_ch)

    // -------------------------------------------------------------------
    // Stage 3: Pool, verify, finalize
    // -------------------------------------------------------------------
    pool_and_verify_diamond_outputs(
        run_diamond_pair.out.collect(),
        extract_orthofinder_search_commands.out.pair_manifest,
        extract_orthofinder_search_commands.out.orthofinder_workdir.collect()
    )

    run_orthofinder_from_blast(
        pool_and_verify_diamond_outputs.out.pooled_workdir.collect()
    )

    // -------------------------------------------------------------------
    // Stage 4: Standardize and produce summaries
    // -------------------------------------------------------------------
    standardize_output(
        run_orthofinder_from_blast.out.orthofinder_output.collect(),
        validate_proteomes.out.proteome_list
    )

    generate_summary_statistics(
        validate_proteomes.out.proteome_list,
        standardize_output.out.orthogroups_gigantic
    )

    qc_analysis_per_species(
        validate_proteomes.out.proteome_list,
        standardize_output.out.orthogroups_gigantic
    )

    write_run_log(qc_analysis_per_species.out.per_species_summary)
}


// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
