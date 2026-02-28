#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: STEP_3 phylogenetic analysis workflow with configurable tree methods
// Human: Eric Edsinger

nextflow.enable.dsl=2

// ============================================================================
// STEP_3 Phylogenetic Analysis Pipeline
// ============================================================================
//
// PURPOSE:
// Run phylogenetic analysis on AGS (All Gene Set) sequences from STEP_2
// for a SINGLE gene family. Users choose which tree-building methods to run
// via config.yaml.
//
// Usage: Each workflow copy processes ONE gene family. Copy the template,
//        configure phylogenetic_analysis_config.yaml, then run.
//
// PROCESSES:
// 1. prepare_alignment_input       - Stage AGS sequences from STEP_2
// 2. clean_sequences               - Remove leading/trailing dashes
// 3. run_mafft_alignment           - MAFFT multiple sequence alignment
// 4. run_clipkit_trimming          - ClipKit alignment trimming
// 5a. run_fasttree                 - FastTree ML phylogeny (default, recommended)
// 5b. run_iqtree                   - IQ-TREE ML phylogeny (publication-quality)
// 5c. run_veryfasttree             - VeryFastTree parallelized ML (large datasets)
// 5d. run_phylobayes               - PhyloBayes Bayesian phylogeny
// 6. visualize_trees_human         - Human-friendly tree visualization
// 7. visualize_trees_computer_vision - Computer-vision tree visualization
// 8. copy_to_output_to_input       - Export alignment + trimmed + trees
//
// output_to_input:
//   STEP-level:       output_to_input/trees/<gene_family>/
//   Subproject-level:  output_to_input/step_3/trees/<gene_family>/
//
// ============================================================================

// Load configuration from YAML
import org.yaml.snakeyaml.Yaml

def load_config() {
    def yaml = new Yaml()
    def config_file = file( "${projectDir}/../phylogenetic_analysis_config.yaml" )
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

// Input: AGS sequences from STEP_2
params.step2_ags_fastas_dir = config.input?.step2_ags_fastas_dir ?: '../../STEP_2-homolog_discovery/output_to_input/ags_fastas'

// Project database name (for file naming)
params.project_database = config.project?.database ?: 'species67_T1-species67'

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

// Process 1: Prepare alignment input (stage AGS from STEP_2)
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
    def step2_dir = file( "${projectDir}/../${params.step2_ags_fastas_dir}" ).toAbsolutePath()
    """
    mkdir -p 1-output

    # Find AGS file from STEP_2 output_to_input
    AGS_FILE=\$(find "${step2_dir}/${gene_family}/" -name "*.aa" -type f | head -1)

    if [ -z "\${AGS_FILE}" ] || [ ! -f "\${AGS_FILE}" ]; then
        echo "ERROR: AGS file not found in: ${step2_dir}/${gene_family}/"
        echo "Ensure STEP_2 has completed and output_to_input/ags_fastas/${gene_family}/ contains results."
        exit 1
    fi

    HOMOLOG_ID="ags-${project_db}-${gene_family}"
    cp "\${AGS_FILE}" "1-output/1_ai-\${HOMOLOG_ID}.aa"

    echo "Staged alignment input: 1-output/1_ai-\${HOMOLOG_ID}.aa"
    echo "Source: \${AGS_FILE}"
    """
}

// Process 2: Clean sequences (remove leading/trailing dashes)
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

    # Remove leading and trailing dashes from sequences (not headers)
    sed 's/^-//g' ${ags_fasta} | sed 's/-\$//g' > "2-output/2_ai-\${HOMOLOG_ID}.aa"

    echo "Cleaned sequences: 2-output/2_ai-\${HOMOLOG_ID}.aa"
    """
}

// Process 3: MAFFT multiple sequence alignment
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

    mafft --originalseqonly --maxiterate ${params.mafft_maxiterate} \\
        --reorder --bl ${params.mafft_bl} \\
        --thread ${params.mafft_threads} \\
        ${cleaned_fasta} > "3-output/3_ai-\${HOMOLOG_ID}.mafft"

    echo "MAFFT alignment complete: 3-output/3_ai-\${HOMOLOG_ID}.mafft"
    """
}

// Process 4: ClipKit alignment trimming
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

    clipkit ${alignment} \\
        -m ${params.clipkit_mode} \\
        -o "4-output/4_ai-\${HOMOLOG_ID}.clipkit-smartgap" \\
        -l

    echo "ClipKit trimming complete: 4-output/4_ai-\${HOMOLOG_ID}.clipkit-smartgap"
    """
}

// Process 5a: FastTree ML phylogeny (conditional - default, recommended)
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

    FastTree ${trimmed_alignment} \\
        > "5_a-output/5_a_ai-\${HOMOLOG_ID}.fasttree" \\
        2> "5_a-output/5_a_ai-\${HOMOLOG_ID}-log"

    echo "FastTree complete: 5_a-output/5_a_ai-\${HOMOLOG_ID}.fasttree"
    """
}

// Process 5b: IQ-TREE ML phylogeny (conditional - publication-quality)
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

    iqtree -s ${trimmed_alignment} \\
        -m ${params.iqtree_model} \\
        --prefix "5_b-output/5_b_ai-\${HOMOLOG_ID}" \\
        --rate \\
        -B ${params.iqtree_bootstrap} \\
        -alrt ${params.iqtree_alrt} \\
        -T ${params.iqtree_threads} \\
        -bnni

    echo "IQ-TREE complete: 5_b-output/5_b_ai-\${HOMOLOG_ID}.treefile"
    """
}

// Process 5c: VeryFastTree parallelized ML phylogeny (conditional - large datasets)
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

    VeryFastTree \\
        -threads ${params.veryfasttree_threads} \\
        ${trimmed_alignment} \\
        > "5_c-output/5_c_ai-\${HOMOLOG_ID}.veryfasttree" \\
        2> "5_c-output/5_c_ai-\${HOMOLOG_ID}-log"

    echo "VeryFastTree complete: 5_c-output/5_c_ai-\${HOMOLOG_ID}.veryfasttree"
    """
}

// Process 5d: PhyloBayes Bayesian phylogeny (conditional - Bayesian counterpoint to ML)
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
    def generations = params.phylobayes_generations
    def burnin = params.phylobayes_burnin
    def every = params.phylobayes_every
    """
    mkdir -p 5_d-output

    HOMOLOG_ID="ags-${project_db}-${gene_family}"

    # Convert FASTA alignment to PHYLIP format (required by PhyloBayes)
    python3 -c "
import sys
identifiers___sequences = {}
current_identifier = None
with open( sys.argv[1] ) as f:
    for line in f:
        line = line.strip()
        if line.startswith( '>' ):
            current_identifier = line[1:].split()[0]
            identifiers___sequences[ current_identifier ] = ''
        elif current_identifier:
            identifiers___sequences[ current_identifier ] += line
sequence_count = len( identifiers___sequences )
alignment_length = len( next( iter( identifiers___sequences.values() ) ) )
print( f'{sequence_count} {alignment_length}' )
for identifier in identifiers___sequences:
    sequence = identifiers___sequences[ identifier ]
    print( f'{identifier}  {sequence}' )
" ${trimmed_alignment} > 5_d-output/alignment.phy

    # Run two independent MCMC chains for convergence assessment
    cd 5_d-output

    pb -d alignment.phy ${params.phylobayes_model} -x ${every} ${generations} chain1 &
    pb -d alignment.phy ${params.phylobayes_model} -x ${every} ${generations} chain2 &
    wait

    # Assess convergence between chains
    bpcomp -x ${burnin} ${every} chain1 chain2 2>&1 | tee bpcomp_report.txt || true
    tracecomp -x ${burnin} ${every} chain1 chain2 2>&1 | tee tracecomp_report.txt || true

    # Rename consensus tree to standard output name
    if [ -f "bpcomp.con.tre" ]; then
        cp bpcomp.con.tre "5_d_ai-\${HOMOLOG_ID}.phylobayes.nwk"
        echo "PhyloBayes complete: 5_d-output/5_d_ai-\${HOMOLOG_ID}.phylobayes.nwk"
    else
        echo "ERROR: PhyloBayes consensus tree not generated."
        echo "Check chain convergence in bpcomp_report.txt and tracecomp_report.txt"
        exit 1
    fi

    cd ..
    """
}

// Process 6: Visualize trees (human-friendly)
process visualize_trees_human_friendly {
    tag "${gene_family}"
    label 'visualization'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( tree_files )

    output:
        path "6-output"

    script:
    """
    mkdir -p 6-output

    # Copy tree files to 6-output for the visualization script to find
    for tree_file in ${tree_files}; do
        cp "\${tree_file}" 6-output/
    done

    # Run visualization script (auto-discovers tree files in output dir)
    cd 6-output
    python3 ${projectDir}/scripts/006_ai-python-visualize_phylogenetic_trees-human_friendly.py \\
        2>&1 || true
    cd ..

    # Verify at least one visualization was created
    VIZ_COUNT=\$(ls 6-output/6_ai-*.svg 6-output/6_ai-*.pdf 2>/dev/null | wc -l)
    if [ "\${VIZ_COUNT}" -eq 0 ]; then
        echo "WARNING: No human-friendly visualizations were created."
        echo "This may be expected if ete3 is not available."
        # Create placeholder to ensure output directory is not empty
        touch "6-output/6_ai-visualization-placeholder.txt"
    else
        echo "Created \${VIZ_COUNT} human-friendly tree visualizations"
    fi
    """
}

// Process 7: Visualize trees (computer-vision friendly)
process visualize_trees_computer_vision {
    tag "${gene_family}"
    label 'visualization'
    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( tree_files )

    output:
        path "7-output"

    script:
    """
    mkdir -p 7-output

    # Copy tree files to 7-output for the visualization script to find
    for tree_file in ${tree_files}; do
        cp "\${tree_file}" 7-output/
    done

    # Run visualization script (auto-discovers tree files in output dir)
    cd 7-output
    python3 ${projectDir}/scripts/007_ai-python-visualize_phylogenetic_trees-computer_vision_friendly.py \\
        2>&1 || true
    cd ..

    # Verify at least one visualization was created
    VIZ_COUNT=\$(ls 7-output/7_ai-*.svg 7-output/7_ai-*.pdf 2>/dev/null | wc -l)
    if [ "\${VIZ_COUNT}" -eq 0 ]; then
        echo "WARNING: No computer-vision visualizations were created."
        echo "This may be expected if ete3 is not available."
        # Create placeholder to ensure output directory is not empty
        touch "7-output/7_ai-visualization-placeholder.txt"
    else
        echo "Created \${VIZ_COUNT} computer-vision tree visualizations"
    fi
    """
}

// Process 8: Copy results to output_to_input (STEP-level and subproject-level)
process copy_to_output_to_input {
    tag "${gene_family}"
    label 'local'

    input:
        tuple val( gene_family ), path( all_files )

    output:
        path "output_to_input_done.txt", emit: done

    script:
    """
    # Copy to STEP-level output_to_input
    mkdir -p ${projectDir}/../../output_to_input/trees/${gene_family}
    for f in ${all_files}; do
        cp "\${f}" ${projectDir}/../../output_to_input/trees/${gene_family}/
    done

    # Copy to subproject-level output_to_input
    mkdir -p ${projectDir}/../../../output_to_input/step_3/trees/${gene_family}
    for f in ${all_files}; do
        cp "\${f}" ${projectDir}/../../../output_to_input/step_3/trees/${gene_family}/
    done

    echo "Copied files for ${gene_family} to output_to_input at \$(date)" > output_to_input_done.txt
    echo "Files exported:"
    ls -la ${all_files}
    """
}

// ============================================================================
// Workflow
// ============================================================================

workflow {

    // Log configuration
    log.info """
    ========================================================================
    GIGANTIC trees_gene_families STEP_3 - Phylogenetic Analysis
    ========================================================================
    Gene family      : ${params.gene_family}
    Project database : ${params.project_database}
    STEP_2 sequences : ${params.step2_ags_fastas_dir}
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
        error "gene_family not set in config! Edit phylogenetic_analysis_config.yaml."
    }

    // Validate at least one tree method is enabled
    if ( !params.run_fasttree && !params.run_iqtree && !params.run_veryfasttree && !params.run_phylobayes ) {
        error "No tree-building methods enabled! Enable at least one in phylogenetic_analysis_config.yaml (tree_methods section)."
    }

    // Create single-item channel for the gene family
    gene_family_channel = Channel.of( params.gene_family )

    // Process 1: Stage AGS sequences from STEP_2
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

    // Fork tree channel for multiple consumers (visualization + export)
    tree_collected
        .multiMap { gene_family, tree_files ->
            for_human_viz: [ gene_family, tree_files ]
            for_cv_viz: [ gene_family, tree_files ]
            for_export: [ gene_family, tree_files ]
        }
        .set { tree_forked }

    // Process 6: Human-friendly visualization
    visualize_trees_human_friendly( tree_forked.for_human_viz )

    // Process 7: Computer-vision visualization
    visualize_trees_computer_vision( tree_forked.for_cv_viz )

    // Process 8: Copy to output_to_input
    // Combine alignment, trimmed alignment, and tree files into a flat list
    output_to_input_channel = run_mafft_alignment.out.alignment
        .join( run_clipkit_trimming.out.trimmed_alignment )
        .join( tree_forked.for_export )
        .map { gene_family, alignment, trimmed, tree_files ->
            [ gene_family, [ alignment, trimmed ] + tree_files ]
        }

    copy_to_output_to_input( output_to_input_channel )
}
