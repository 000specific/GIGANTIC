#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: STEP_2 phylogenetic analysis workflow with configurable tree methods
// Human: Eric Edsinger

nextflow.enable.dsl=2

// ============================================================================
// STEP_2 Phylogenetic Analysis Pipeline
// ============================================================================
//
// PURPOSE:
// Run phylogenetic analysis on AGS (All Gene Set) sequences from STEP_1
// for a SINGLE gene family. Users choose which tree-building methods to run
// via config.yaml.
//
// Usage: Each workflow copy processes ONE gene family. Copy the template,
//        configure START_HERE-user_config.yaml, then run.
//
// PROCESSES (each calls an external script in ai/scripts/):
// 1. prepare_alignment_input       - Calls: 001_ai-bash-prepare_alignment_input.sh
// 2. clean_sequences               - Calls: 002_ai-bash-replace_special_characters.sh
// 3. run_mafft_alignment           - Calls: 003_ai-bash-run_mafft_alignment.sh
// 4. run_clipkit_trimming          - Calls: 004_ai-bash-run_clipkit_trimming.sh
// 5a. run_fasttree                 - Calls: 005_a_ai-bash-run_fasttree.sh
// 5b. run_iqtree                   - Calls: 005_b_ai-bash-run_iqtree.sh
// 5c. run_veryfasttree             - Calls: 005_c_ai-bash-run_veryfasttree.sh
// 5d. run_phylobayes               - Calls: 005_d_ai-bash-run_phylobayes.sh
// 6. write_run_log                 - Calls: 006_ai-python-write_run_log.py
//
// Visualization is handled by STEP_3-tree_visualization (separate workflow)
// which consumes the tree newick files produced here.
// (Symlinks for output_to_input created by RUN-workflow.sh after pipeline completes)
//
// ============================================================================

// Load configuration from YAML
import org.yaml.snakeyaml.Yaml

def load_config() {
    def yaml = new Yaml()
    def config_file = file( "${projectDir}/../START_HERE-user_config.yaml" )
    if ( !config_file.exists() ) {
        error "Configuration file not found: ${config_file}"
    }
    return yaml.load( config_file.text )
}

// Load the configuration
def config = load_config()

// ============================================================================
// Parameters (from config.yaml)
// ============================================================================

params.output_dir = config.output?.base_dir ?: 'OUTPUT_pipeline'

// Gene family (single gene family per workflow copy)
params.gene_family = config.gene_family?.name ?: null

// Input: output_to_input directory (AGS found at <dir>/<gene_family>/STEP_1-homolog_discovery/)
params.output_to_input_dir = config.input?.output_to_input_dir ?: '../../../output_to_input'

// Project database name (for file naming)
params.project_database = config.project?.database ?: 'speciesN_T1-speciesN'

// Project name (for run log)
params.project_name = config.project?.name ?: 'gene_families'

// MAFFT parameters
params.mafft_maxiterate = config.phylogenetics?.mafft?.maxiterate ?: 1000
params.mafft_bl = config.phylogenetics?.mafft?.bl ?: 45
params.mafft_threads = config.phylogenetics?.mafft?.threads ?: 50

// ClipKit parameters
params.clipkit_mode = config.phylogenetics?.clipkit?.mode ?: 'smart-gap'

// IQ-TREE parameters
params.iqtree_model = config.phylogenetics?.iqtree?.model ?: 'MFP'
params.iqtree_bootstrap = config.phylogenetics?.iqtree?.bootstrap ?: 2000
params.iqtree_alrt = config.phylogenetics?.iqtree?.alrt ?: 2000
params.iqtree_threads = config.phylogenetics?.iqtree?.threads ?: 'AUTO'

// VeryFastTree parameters
params.veryfasttree_threads = config.phylogenetics?.veryfasttree?.threads ?: 4

// PhyloBayes parameters
params.phylobayes_model = config.phylogenetics?.phylobayes?.model ?: '-cat -gtr'
params.phylobayes_generations = config.phylogenetics?.phylobayes?.generations ?: 10000
params.phylobayes_burnin = config.phylogenetics?.phylobayes?.burnin ?: 2500
params.phylobayes_every = config.phylogenetics?.phylobayes?.every ?: 1

// Tree methods (configurable)
params.run_fasttree = config.tree_methods?.fasttree ?: true
params.run_iqtree = config.tree_methods?.iqtree ?: false
params.run_veryfasttree = config.tree_methods?.veryfasttree ?: false
params.run_phylobayes = config.tree_methods?.phylobayes ?: false

// ============================================================================
// Processes
// ============================================================================

// Process 1: Prepare alignment input (stage AGS from STEP_1)
// Calls: scripts/001_ai-bash-prepare_alignment_input.sh
process prepare_alignment_input {
    tag "${gene_family}"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        val gene_family

    output:
        tuple val( gene_family ), path( "1-output/1_ai-ags-*.aa" ), emit: staged_ags
        path "1-output"

    script:
    def project_db = params.project_database
    def oti_dir = file( "${projectDir}/../${params.output_to_input_dir}" ).toAbsolutePath()
    """
    mkdir -p 1-output

    # Find AGS file from output_to_input/<gene_family>/STEP_1-homolog_discovery/
    AGS_FILE=\$(find -L "${oti_dir}/${gene_family}/STEP_1-homolog_discovery/" -name "*.aa" -type f | head -1)

    if [ -z "\${AGS_FILE}" ] || [ ! -f "\${AGS_FILE}" ]; then
        echo "ERROR: AGS file not found in: ${oti_dir}/${gene_family}/STEP_1-homolog_discovery/"
        echo "Ensure STEP_1 has completed and output_to_input/${gene_family}/STEP_1-homolog_discovery/ contains results."
        echo "Expected directory: ${oti_dir}/${gene_family}/STEP_1-homolog_discovery/"
        exit 1
    fi

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    bash ${projectDir}/scripts/001_ai-bash-prepare_alignment_input.sh \\
        "\${AGS_FILE}" \\
        "1-output/1_ai-\${HOMOLOG_ID}.aa"
    """
}

// Process 2: Clean sequences (remove leading/trailing dashes)
// Calls: scripts/002_ai-bash-replace_special_characters.sh
process clean_sequences {
    tag "${gene_family}"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( ags_fasta )

    output:
        tuple val( gene_family ), path( "2-output/2_ai-ags-*.aa" ), emit: cleaned_fasta
        path "2-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 2-output

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    bash ${projectDir}/scripts/002_ai-bash-replace_special_characters.sh \\
        ${ags_fasta} \\
        "2-output/2_ai-\${HOMOLOG_ID}.aa"
    """
}

// Process 3: MAFFT multiple sequence alignment
// Calls: scripts/003_ai-bash-run_mafft_alignment.sh
process run_mafft_alignment {
    tag "${gene_family}"
    label 'mafft'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( cleaned_fasta )

    output:
        tuple val( gene_family ), path( "3-output/3_ai-ags-*.mafft" ), emit: alignment
        path "3-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 3-output

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    bash ${projectDir}/scripts/003_ai-bash-run_mafft_alignment.sh \\
        ${cleaned_fasta} \\
        "3-output/3_ai-\${HOMOLOG_ID}.mafft" \\
        ${params.mafft_maxiterate} \\
        ${params.mafft_bl} \\
        ${params.mafft_threads}
    """
}

// Process 4: ClipKit alignment trimming
// Calls: scripts/004_ai-bash-run_clipkit_trimming.sh
process run_clipkit_trimming {
    tag "${gene_family}"
    label 'clipkit'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( alignment )

    output:
        tuple val( gene_family ), path( "4-output/4_ai-ags-*.clipkit-smartgap" ), emit: trimmed_alignment
        path "4-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 4-output

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    bash ${projectDir}/scripts/004_ai-bash-run_clipkit_trimming.sh \\
        ${alignment} \\
        "4-output/4_ai-\${HOMOLOG_ID}.clipkit-smartgap" \\
        ${params.clipkit_mode}
    """
}

// Process 5a: FastTree ML phylogeny (conditional - default, recommended)
// Calls: scripts/005_a_ai-bash-run_fasttree.sh
process run_fasttree {
    tag "${gene_family}"
    label 'fasttree'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    when:
        params.run_fasttree

    input:
        tuple val( gene_family ), path( trimmed_alignment )

    output:
        tuple val( gene_family ), path( "5_a-output/5_a_ai-ags-*.fasttree" ), emit: fasttree
        path "5_a-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 5_a-output

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    bash ${projectDir}/scripts/005_a_ai-bash-run_fasttree.sh \\
        ${trimmed_alignment} \\
        "5_a-output/5_a_ai-\${HOMOLOG_ID}.fasttree" \\
        "5_a-output/5_a_ai-\${HOMOLOG_ID}-log"
    """
}

// Process 5b: IQ-TREE ML phylogeny (conditional - publication-quality)
// Calls: scripts/005_b_ai-bash-run_iqtree.sh
process run_iqtree {
    tag "${gene_family}"
    label 'iqtree'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    when:
        params.run_iqtree

    input:
        tuple val( gene_family ), path( trimmed_alignment )

    output:
        tuple val( gene_family ), path( "5_b-output/5_b_ai-ags-*.treefile" ), emit: iqtree
        path "5_b-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 5_b-output

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    bash ${projectDir}/scripts/005_b_ai-bash-run_iqtree.sh \\
        ${trimmed_alignment} \\
        "5_b-output/5_b_ai-\${HOMOLOG_ID}" \\
        ${params.iqtree_model} \\
        ${params.iqtree_bootstrap} \\
        ${params.iqtree_alrt} \\
        ${params.iqtree_threads}
    """
}

// Process 5c: VeryFastTree parallelized ML phylogeny (conditional - large datasets)
// Calls: scripts/005_c_ai-bash-run_veryfasttree.sh
// VeryFastTree is a drop-in FastTree replacement optimized for parallelization.
// Best suited for datasets with >10,000 sequences where threading provides real speedup.
// For typical GIGANTIC datasets (50-500 sequences), FastTree produces better-quality trees.
process run_veryfasttree {
    tag "${gene_family}"
    label 'veryfasttree'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    when:
        params.run_veryfasttree

    input:
        tuple val( gene_family ), path( trimmed_alignment )

    output:
        tuple val( gene_family ), path( "5_c-output/5_c_ai-ags-*.veryfasttree" ), emit: veryfasttree
        path "5_c-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 5_c-output

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    bash ${projectDir}/scripts/005_c_ai-bash-run_veryfasttree.sh \\
        ${trimmed_alignment} \\
        "5_c-output/5_c_ai-\${HOMOLOG_ID}.veryfasttree" \\
        "5_c-output/5_c_ai-\${HOMOLOG_ID}-log" \\
        ${params.veryfasttree_threads}
    """
}

// Process 5d: PhyloBayes Bayesian phylogeny (conditional - Bayesian counterpoint to ML)
// Calls: scripts/005_d_ai-bash-run_phylobayes.sh
// PhyloBayes uses site-heterogeneous CAT-GTR models and MCMC sampling.
// Requires PHYLIP format input. Runs 2 independent chains for convergence assessment.
// Very slow (days to weeks) - use only when Bayesian analysis is needed.
process run_phylobayes {
    tag "${gene_family}"
    label 'phylobayes'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    when:
        params.run_phylobayes

    input:
        tuple val( gene_family ), path( trimmed_alignment )

    output:
        tuple val( gene_family ), path( "5_d-output/5_d_ai-ags-*.phylobayes.nwk" ), emit: phylobayes_tree
        path "5_d-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 5_d-output

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    bash ${projectDir}/scripts/005_d_ai-bash-run_phylobayes.sh \\
        ${trimmed_alignment} \\
        "5_d-output" \\
        "5_d_ai-\${HOMOLOG_ID}.phylobayes.nwk" \\
        "${params.phylobayes_model}" \\
        ${params.phylobayes_generations} \\
        ${params.phylobayes_burnin} \\
        ${params.phylobayes_every}
    """
}

/*
 * Process 6: Write Run Log
 * Calls: scripts/006_ai-python-write_run_log.py
 *
 * Creates a timestamped log in ai/logs/ within this workflow directory
 * for transparency and reproducibility.
 *
 * NOTE: Visualization is handled by STEP_3-tree_visualization as a
 * separate workflow. STEP_2 produces tree newick files; STEP_3 renders them.
 * This decoupling keeps scientific computation (STEP_2) independent of
 * visualization library quirks (ete3/PyQt5 instability).
 */
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/006_ai-python-write_run_log.py \
        --workflow-name "phylogenetic_analysis" \
        --subproject-name "trees_gene_families" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
// pipeline completes. Real files only live in OUTPUT_pipeline/N-output/.

workflow {

    // Log configuration
    log.info """
    ========================================================================
    GIGANTIC trees_gene_families STEP_2 - Phylogenetic Analysis
    ========================================================================
    Gene family      : ${params.gene_family}
    Project database : ${params.project_database}
    output_to_input  : ${params.output_to_input_dir}
    Output directory : ${params.output_dir}

    Tree methods enabled:
      FastTree       : ${params.run_fasttree} (default, recommended)
      IQ-TREE        : ${params.run_iqtree} (publication-quality ML)
      VeryFastTree   : ${params.run_veryfasttree} (large datasets only)
      PhyloBayes     : ${params.run_phylobayes} (Bayesian counterpoint)

    MAFFT settings:
      maxiterate     : ${params.mafft_maxiterate}
      bl             : ${params.mafft_bl}
      threads        : ${params.mafft_threads}

    ClipKit mode     : ${params.clipkit_mode}
    ========================================================================
    """.stripIndent()

    // Validate critical parameters
    if ( !params.gene_family ) {
        error "gene_family not set in config! Edit START_HERE-user_config.yaml."
    }

    // Validate at least one tree method is enabled
    if ( !params.run_fasttree && !params.run_iqtree && !params.run_veryfasttree && !params.run_phylobayes ) {
        error "No tree-building methods enabled! Enable at least one in START_HERE-user_config.yaml (tree_methods section)."
    }

    // Create single-item channel for the gene family
    gene_family_channel = Channel.of( params.gene_family )

    // Process 1: Stage AGS sequences from STEP_1
    prepare_alignment_input( gene_family_channel )

    // Process 2: Clean sequences
    clean_sequences( prepare_alignment_input.out.staged_ags )

    // Process 3: MAFFT alignment
    run_mafft_alignment( clean_sequences.out.cleaned_fasta )

    // Process 4: ClipKit trimming
    run_clipkit_trimming( run_mafft_alignment.out.alignment )

    // Process 5a-5d: Tree building (all conditional via when: directive)
    // Disabled methods produce empty output channels automatically
    run_fasttree( run_clipkit_trimming.out.trimmed_alignment )
    run_iqtree( run_clipkit_trimming.out.trimmed_alignment )
    run_veryfasttree( run_clipkit_trimming.out.trimmed_alignment )
    run_phylobayes( run_clipkit_trimming.out.trimmed_alignment )

    // Collect tree outputs dynamically from all enabled methods
    // Each process emits [gene_family, tree_file] when enabled, nothing when disabled
    tree_collected = Channel.empty()
        .mix( run_fasttree.out.fasttree )
        .mix( run_iqtree.out.iqtree )
        .mix( run_veryfasttree.out.veryfasttree )
        .mix( run_phylobayes.out.phylobayes_tree )
        .groupTuple()
        .map { gene_family, tree_files ->
            [ gene_family, tree_files.flatten() ]
        }

    // NOTE: Symlinks from output_to_input/ to OUTPUT_pipeline/ files
    // are created by RUN-workflow.sh after pipeline completes. Trees are then
    // rendered by STEP_3-phylogenetic_visualization (separate workflow).

    // Process 6: Write run log (gated on trees being ready)
    write_run_log( tree_collected.collect().map { true } )
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC trees_gene_families STEP_2 Pipeline Complete!"
    println "========================================================================"
    println "Gene family: ${params.gene_family}"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if ( workflow.success ) {
        println "Run log written to ai/logs/ in this workflow directory"
    }
    println "========================================================================"
}
