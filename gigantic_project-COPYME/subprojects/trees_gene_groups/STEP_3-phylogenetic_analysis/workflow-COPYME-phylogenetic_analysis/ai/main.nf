#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: STEP_3 phylogenetic analysis workflow with configurable tree methods
// Human: Eric Edsinger

nextflow.enable.dsl=2

// ============================================================================
// STEP_3 Phylogenetic Analysis Pipeline
// ============================================================================
//
// PURPOSE:
// Run phylogenetic analysis on AGS (All Gene Set) sequences from STEP_2.
// Users choose which tree-building methods to run via config.yaml.
//
// PROCESSES:
// 1. prepare_alignment_input       - Stage AGS sequences from STEP_2
// 2. clean_sequences               - Remove leading/trailing dashes
// 3. run_mafft_alignment           - MAFFT multiple sequence alignment
// 4. run_clipkit_trimming          - ClipKit alignment trimming
// 5a. run_fasttree                 - FastTree ML phylogeny (configurable)
// 5c. run_iqtree                   - IQ-TREE ML phylogeny (configurable)
// 6. visualize_trees_human         - Human-friendly tree visualization
// 7. visualize_trees_computer_vision - Computer-vision tree visualization
// (Symlinks for output_to_input created by RUN-workflow.sh after pipeline completes)
//
// CONFIGURABLE TREE METHODS:
// Set in phylogenetic_analysis_config.yaml under tree_methods:
//   fasttree: true/false
//   superfasttree: true/false (FUTURE)
//   iqtree: true/false
//   phylobayes: true/false (FUTURE)
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

// Input: AGS sequences from STEP_2
params.step2_homolog_sequences_dir = config.input?.step2_homolog_sequences_dir ?: '../../STEP_2-homolog_discovery/output_to_input/homolog_sequences'

// RGS manifest for gene family names
params.rgs_manifest = "${projectDir}/../INPUT_user/rgs_manifest.tsv"

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

// Tree methods (configurable)
params.run_fasttree = config.tree_methods?.fasttree ?: true
params.run_superfasttree = config.tree_methods?.superfasttree ?: false
params.run_iqtree = config.tree_methods?.iqtree ?: false
params.run_phylobayes = config.tree_methods?.phylobayes ?: false

// Conda environments
params.mafft_conda_env = config.conda?.env_mafft ?: 'mafft'
params.clipkit_conda_env = config.conda?.env_clipkit ?: 'clipkit'
params.fasttree_conda_env = config.conda?.env_fasttree ?: 'fasttree'
params.iqtree_conda_env = config.conda?.env_iqtree ?: 'iqtree'
params.visualization_conda_env = config.conda?.env_visualization ?: 'ai_tree_visualization'

// ============================================================================
// Helper Functions
// ============================================================================

def load_rgs_manifest() {
    // Read manifest to get gene family names
    def manifest_file = file( params.rgs_manifest )
    if ( !manifest_file.exists() ) {
        error "RGS manifest not found: ${params.rgs_manifest}"
    }

    def gene_families = []
    manifest_file.eachLine { line ->
        line = line.trim()
        if ( line && !line.startsWith( '#' ) ) {
            def parts = line.split( '\t' )
            if ( parts.size() >= 1 ) {
                gene_families.add( parts[ 0 ].trim() )
            }
        }
    }

    if ( gene_families.isEmpty() ) {
        error "No gene families found in manifest: ${params.rgs_manifest}"
    }

    return gene_families
}

// ============================================================================
// Processes
// ============================================================================

// Process 1: Prepare alignment input (stage AGS from STEP_2)
process prepare_alignment_input {
    tag "${gene_family}"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    input:
        val gene_family

    output:
        tuple val( gene_family ), path( "1-output/1_ai-AGS-*.aa" ), emit: staged_ags
        path "1-output"

    script:
    def project_db = params.project_database
    def step2_dir = file( "${projectDir}/../${params.step2_homolog_sequences_dir}" ).toAbsolutePath()
    """
    mkdir -p 1-output

    # Find AGS file from STEP_2 output_to_input
    AGS_FILE="${step2_dir}/${gene_family}/16_ai-AGS-${project_db}-${gene_family}-homologs.aa"

    if [ ! -f "\${AGS_FILE}" ]; then
        echo "ERROR: AGS file not found: \${AGS_FILE}"
        echo "Ensure STEP_2 has completed and output_to_input/homolog_sequences/ contains results."
        exit 1
    fi

    HOMOLOG_ID="AGS-${project_db}-${gene_family}"
    cp "\${AGS_FILE}" "1-output/1_ai-\${HOMOLOG_ID}.aa"

    echo "Staged alignment input: 1-output/1_ai-\${HOMOLOG_ID}.aa"
    echo "Source: \${AGS_FILE}"
    """
}

// Process 2: Clean sequences (remove leading/trailing dashes)
process clean_sequences {
    tag "${gene_family}"
    label 'local'
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( ags_fasta )

    output:
        tuple val( gene_family ), path( "2-output/2_ai-AGS-*.aa" ), emit: cleaned_fasta
        path "2-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 2-output

    HOMOLOG_ID="AGS-${project_db}-${gene_family}"

    # Remove leading and trailing dashes from sequences (not headers)
    sed 's/^-//g' ${ags_fasta} | sed 's/-\$//g' > "2-output/2_ai-\${HOMOLOG_ID}.aa"

    echo "Cleaned sequences: 2-output/2_ai-\${HOMOLOG_ID}.aa"
    """
}

// Process 3: MAFFT multiple sequence alignment
process run_mafft_alignment {
    tag "${gene_family}"
    label 'mafft'
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( cleaned_fasta )

    output:
        tuple val( gene_family ), path( "3-output/3_ai-AGS-*.mafft" ), emit: alignment
        path "3-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 3-output

    HOMOLOG_ID="AGS-${project_db}-${gene_family}"

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
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( alignment )

    output:
        tuple val( gene_family ), path( "4-output/4_ai-AGS-*.clipkit-smartgap" ), emit: trimmed_alignment
        path "4-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 4-output

    HOMOLOG_ID="AGS-${project_db}-${gene_family}"

    clipkit ${alignment} \\
        -m ${params.clipkit_mode} \\
        -o "4-output/4_ai-\${HOMOLOG_ID}.clipkit-smartgap" \\
        -l

    echo "ClipKit trimming complete: 4-output/4_ai-\${HOMOLOG_ID}.clipkit-smartgap"
    """
}

// Process 5a: FastTree ML phylogeny (conditional)
process run_fasttree {
    tag "${gene_family}"
    label 'fasttree'
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    when:
        params.run_fasttree

    input:
        tuple val( gene_family ), path( trimmed_alignment )

    output:
        tuple val( gene_family ), path( "5_a-output/5_a_ai-AGS-*.fasttree" ), emit: fasttree
        path "5_a-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 5_a-output

    HOMOLOG_ID="AGS-${project_db}-${gene_family}"

    FastTree ${trimmed_alignment} \\
        > "5_a-output/5_a_ai-\${HOMOLOG_ID}.fasttree" \\
        2> "5_a-output/5_a_ai-\${HOMOLOG_ID}-log"

    echo "FastTree complete: 5_a-output/5_a_ai-\${HOMOLOG_ID}.fasttree"
    """
}

// Process 5c: IQ-TREE ML phylogeny (conditional)
process run_iqtree {
    tag "${gene_family}"
    label 'iqtree'
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    when:
        params.run_iqtree

    input:
        tuple val( gene_family ), path( trimmed_alignment )

    output:
        tuple val( gene_family ), path( "5_c-output/5_c_ai-AGS-*.treefile" ), emit: iqtree
        path "5_c-output"

    script:
    def project_db = params.project_database
    """
    mkdir -p 5_c-output

    HOMOLOG_ID="AGS-${project_db}-${gene_family}"

    iqtree -s ${trimmed_alignment} \\
        -m ${params.iqtree_model} \\
        --prefix "5_c-output/5_c_ai-\${HOMOLOG_ID}" \\
        --rate \\
        -B ${params.iqtree_bootstrap} \\
        -alrt ${params.iqtree_alrt} \\
        -T ${params.iqtree_threads} \\
        -bnni

    echo "IQ-TREE complete: 5_c-output/5_c_ai-\${HOMOLOG_ID}.treefile"
    """
}

// Process 6: Visualize trees (human-friendly)
process visualize_trees_human_friendly {
    tag "${gene_family}"
    label 'visualization'
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( tree_files )

    output:
        tuple val( gene_family ), path( "6-output/6_ai-AGS-*-human_friendly.{pdf,svg}" ), emit: human_viz
        path "6-output"

    script:
    """
    mkdir -p 6-output

    # Copy tree files to 6-output for the visualization script to find
    for tree_file in ${tree_files}; do
        cp "\${tree_file}" 6-output/
    done

    # Run visualization script (auto-discovers .fasttree and .treefile in output dir)
    cd 6-output
    python3 ${projectDir}/scripts/006_ai-python-visualize_phylogenetic_trees-human_friendly.py \\
        2>&1 || true
    cd ..

    # Verify at least one visualization was created
    VIZ_COUNT=\$(ls 6-output/6_ai-*.svg 2>/dev/null | wc -l)
    if [ "\${VIZ_COUNT}" -eq 0 ]; then
        echo "WARNING: No human-friendly visualizations were created."
        echo "This may be expected if ete3 is not available."
        # Create placeholder to prevent pipeline failure
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
    publishDir "${projectDir}/../${params.output_dir}/${gene_family}", mode: 'copy', overwrite: true

    input:
        tuple val( gene_family ), path( tree_files )

    output:
        tuple val( gene_family ), path( "7-output/7_ai-AGS-*-computer_vision_friendly.{pdf,svg}" ), emit: cv_viz
        path "7-output"

    script:
    """
    mkdir -p 7-output

    # Copy tree files to 7-output for the visualization script to find
    for tree_file in ${tree_files}; do
        cp "\${tree_file}" 7-output/
    done

    # Run visualization script (auto-discovers .fasttree and .treefile in output dir)
    cd 7-output
    python3 ${projectDir}/scripts/007_ai-python-visualize_phylogenetic_trees-computer_vision_friendly.py \\
        2>&1 || true
    cd ..

    # Verify at least one visualization was created
    VIZ_COUNT=\$(ls 7-output/7_ai-*.svg 2>/dev/null | wc -l)
    if [ "\${VIZ_COUNT}" -eq 0 ]; then
        echo "WARNING: No computer-vision visualizations were created."
        echo "This may be expected if ete3 is not available."
        # Create placeholder to prevent pipeline failure
        touch "7-output/7_ai-visualization-placeholder.txt"
    else
        echo "Created \${VIZ_COUNT} computer-vision tree visualizations"
    fi
    """
}

// NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
// pipeline completes. Real files only live in OUTPUT_pipeline/<gene_family>/N-output/.

// ============================================================================
// Workflow
// ============================================================================

workflow {

    // Log configuration
    log.info """
    ========================================================================
    GIGANTIC trees_gene_families STEP_3 - Phylogenetic Analysis
    ========================================================================
    Project database : ${params.project_database}
    STEP_2 sequences : ${params.step2_homolog_sequences_dir}
    Output directory : ${params.output_dir}

    Tree methods enabled:
      FastTree       : ${params.run_fasttree}
      SuperFastTree  : ${params.run_superfasttree} (future)
      IQ-TREE        : ${params.run_iqtree}
      PhyloBayes     : ${params.run_phylobayes} (future)

    MAFFT settings:
      maxiterate     : ${params.mafft_maxiterate}
      bl             : ${params.mafft_bl}
      threads        : ${params.mafft_threads}

    ClipKit mode     : ${params.clipkit_mode}
    ========================================================================
    """.stripIndent()

    // Validate at least one tree method is enabled
    if ( !params.run_fasttree && !params.run_iqtree ) {
        error "No tree-building methods enabled! Enable at least one in phylogenetic_analysis_config.yaml (tree_methods section)."
    }

    // Load gene families from manifest
    def gene_families = load_rgs_manifest()
    log.info "Gene families to process: ${gene_families.join( ', ' )}"

    // Create channel from gene family names
    gene_family_channel = Channel.from( gene_families )

    // Process 1: Stage AGS sequences from STEP_2
    prepare_alignment_input( gene_family_channel )

    // Process 2: Clean sequences
    clean_sequences( prepare_alignment_input.out.staged_ags )

    // Process 3: MAFFT alignment
    run_mafft_alignment( clean_sequences.out.cleaned_fasta )

    // Process 4: ClipKit trimming
    run_clipkit_trimming( run_mafft_alignment.out.alignment )

    // Process 5a: FastTree (conditional)
    run_fasttree( run_clipkit_trimming.out.trimmed_alignment )

    // Process 5c: IQ-TREE (conditional)
    run_iqtree( run_clipkit_trimming.out.trimmed_alignment )

    // Collect tree files for visualization and output_to_input
    // Combine all available tree outputs into a single channel per gene family
    if ( params.run_fasttree && params.run_iqtree ) {
        // Both methods: join FastTree and IQ-TREE outputs
        tree_files_channel = run_fasttree.out.fasttree
            .join( run_iqtree.out.iqtree )
            .map { gene_family, fasttree_file, iqtree_file ->
                [ gene_family, [ fasttree_file, iqtree_file ] ]
            }
    } else if ( params.run_fasttree ) {
        // FastTree only
        tree_files_channel = run_fasttree.out.fasttree
            .map { gene_family, fasttree_file ->
                [ gene_family, [ fasttree_file ] ]
            }
    } else if ( params.run_iqtree ) {
        // IQ-TREE only
        tree_files_channel = run_iqtree.out.iqtree
            .map { gene_family, iqtree_file ->
                [ gene_family, [ iqtree_file ] ]
            }
    }

    // Process 6: Human-friendly visualization
    visualize_trees_human_friendly( tree_files_channel )

    // Process 7: Computer-vision visualization
    visualize_trees_computer_vision( tree_files_channel )

    // NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
    // pipeline completes. Real files only live in OUTPUT_pipeline/<gene_family>/N-output/.
}
