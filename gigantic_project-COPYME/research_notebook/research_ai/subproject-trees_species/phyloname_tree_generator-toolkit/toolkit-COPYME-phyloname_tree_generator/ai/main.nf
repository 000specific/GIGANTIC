#!/usr/bin/env nextflow
/*
 * Phyloname Tree Generator Toolkit - main pipeline
 * AI: Claude Code | Opus 4.7 | 2026 May 29
 * Human: Eric Edsinger
 *
 * Purpose:
 *   Generate a binary species-tree Newick from a phylonames TSV map,
 *   honoring a user-specified backbone topology, optional internal-clade
 *   constraints, and reproducible random polytomy resolution. Symlink the
 *   emitted Newick into trees_species/BLOCK_gigantic_species_tree/
 *   workflow-COPYME-gigantic_species_tree/INPUT_user/ for the canonical
 *   GIGANTIC workflow to consume.
 *
 * Process Overview:
 *    1: Generate species tree (parse phylonames + apply backbone + apply
 *       internal-clade constraints + resolve polytomies + emit Newick +
 *       decision log + summary)
 *    2: Validate the emitted Newick (binary, N-1 internals, no duplicates,
 *       no reserved internal labels)
 *    3: Symlink into trees_species BLOCK_gigantic_species_tree INPUT_user/
 *    4: Write workflow run log (GIGANTIC §45)
 */

nextflow.enable.dsl = 2

params.phylonames                     = null
params.config_file                    = null
params.trees_species_input_user_dir   = null
params.prefix                         = "species_tree"
params.seed                           = 42
params.output_dir                     = "OUTPUT_pipeline"
params.project_name                   = "gigantic_project"


process generate_species_tree {
    tag "generate"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output", emit: out_dir

    script:
    """
    mkdir -p 1-output
    python3 ${projectDir}/scripts/001_ai-python-generate_species_tree.py \\
        --phylonames ${params.phylonames} \\
        --config ${params.config_file} \\
        --output-dir 1-output \\
        --prefix ${params.prefix} \\
        --seed ${params.seed} \\
        --log-file 1-output/1_ai-log-generate_species_tree.log
    """
}


process validate_outputs {
    tag "validate"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path generate_out

    output:
        path "2-output", emit: out_dir

    script:
    """
    mkdir -p 2-output
    python3 ${projectDir}/scripts/002_ai-python-validate_outputs.py \\
        --newick ${generate_out}/${params.prefix}-seed${params.seed}-species_tree.newick \\
        --log-file 2-output/2_ai-log-validate_outputs.log
    echo "ok" > 2-output/2_ai-validation_pass.txt
    """
}


process bridge_to_trees_species {
    tag "bridge"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        path generate_out
        val validate_done

    output:
        path "3-output", emit: out_dir

    script:
    """
    mkdir -p 3-output
    python3 ${projectDir}/scripts/003_ai-python-bridge_to_trees_species.py \\
        --newick ${generate_out}/${params.prefix}-seed${params.seed}-species_tree.newick \\
        --target-dir ${params.trees_species_input_user_dir} \\
        --log-file 3-output/3_ai-log-bridge_to_trees_species.log
    """
}


process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-write_run_log.py \\
        --workflow-name "phyloname_tree_generator" \\
        --subproject-name "subproject-trees_species" \\
        --project-name "${params.project_name}" \\
        --status success
    """
}


workflow {
    log.info """
    ========================================================================
    Phyloname Tree Generator (research_notebook/research_ai/subproject-trees_species)
    ========================================================================
    phylonames                : ${params.phylonames}
    config                    : ${params.config_file}
    trees_species INPUT_user  : ${params.trees_species_input_user_dir}
    prefix                    : ${params.prefix}
    seed                      : ${params.seed}
    ========================================================================
    """.stripIndent()

    if ( !params.phylonames )                   error "params.phylonames not set"
    if ( !params.config_file )                  error "params.config_file not set"
    if ( !params.trees_species_input_user_dir ) error "params.trees_species_input_user_dir not set"

    generate_species_tree()
    validate_outputs( generate_species_tree.out.out_dir )
    bridge_to_trees_species(
        generate_species_tree.out.out_dir,
        validate_outputs.out.out_dir
    )
    write_run_log( bridge_to_trees_species.out.out_dir )
}
