#!/usr/bin/env nextflow
/*
 * GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 February 27
 * Human: Eric Edsinger
 *
 * Purpose: Discover homologs via Reciprocal Best Hit (RBH) / Reciprocal Best Family (RBF)
 *          BLAST methodology for a SINGLE gene family.
 *
 * Usage: Each workflow copy processes ONE gene family. Copy the template,
 *        configure rbh_rbf_homologs_config.yaml, then run.
 *
 * Process Overview:
 *    1: List BLAST databases
 *    2: BLAST RGS vs project database (script 002 + execute generated commands)
 *    3: Extract blast gene sequences (script 004)
 *    4: BLAST RGS vs RGS source genomes (script 005 + execute generated commands)
 *    5: Prepare reciprocal BLAST (scripts 007, 008, 009 + combine + makeblastdb)
 *    6: Run reciprocal BLAST (script 011 + execute generated commands)
 *    7: Extract candidate gene sequences (script 013)
 *    8: Filter species by keeper list (script 014)
 *    9: Remap CGS identifiers to GIGANTIC phylonames (script 015)
 *   10: Concatenate RGS + CGS into final AGS (script 016)
 *   11: Copy AGS to output_to_input for STEP_3
 *
 * Data Flow:
 *   Config gene_family + rgs_file → single gene family through all 11 processes
 *   Final AGS fasta → output_to_input/ags_fastas/<gene_family>/
 *
 * Script Generators:
 *   Scripts 002, 005, 011 generate bash scripts that are then executed.
 *   The generated scripts (003, 006, 012) produce BLAST reports.
 *   All intermediate files are published to OUTPUT_pipeline/N-output/
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config)
// ============================================================================

params.gene_family = null
params.rgs_file = null
params.species_keeper_list = "INPUT_user/species_keeper_list.tsv"
params.rgs_species_map = "INPUT_user/rgs_species_map.tsv"
params.blast_databases_dir = null
params.rgs_genomes_dir = null
params.cgs_mapping_file = null
params.project_database = "species67_T1-species67"
params.blast_evalue = "1e-3"
params.blast_threads = 50
params.blast_conda_env = "blast"
params.output_dir = "OUTPUT_pipeline"

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

def load_species_map( map_path ) {
    /*
     * Load RGS species mapping from short names to GIGANTIC Genus_species.
     * Returns empty map if file doesn't exist.
     */
    def map_file = file( map_path )
    def species_map = [:]

    if ( !map_file.exists() ) {
        log.warn "RGS species map not found: ${map_path} (using RGS headers directly)"
        return species_map
    }

    map_file.eachLine { line ->
        if ( !line.trim() || line.startsWith( '#' ) ) return
        def parts = line.split( '\t' )
        if ( parts.size() >= 2 ) {
            species_map[ parts[0].trim() ] = parts[1].trim()
        }
    }

    log.info "Loaded ${species_map.size()} species mappings from RGS species map"
    return species_map
}

def extract_rgs_species( rgs_file_path ) {
    /*
     * Extract unique species short names from RGS FASTA headers.
     * Header format: >rgsN-species_short_name-source-identifier
     */
    def species_set = [] as Set
    def rgs_file = file( rgs_file_path )

    rgs_file.eachLine { line ->
        if ( line.startsWith( '>' ) ) {
            def header = line.substring( 1 ).trim()
            def parts = header.split( '-' )
            if ( parts.size() >= 2 ) {
                def species_short_name = parts[1]
                if ( species_short_name && species_short_name[0].isLetter() ) {
                    species_set.add( species_short_name )
                }
            }
        }
    }

    return species_set
}

def determine_rbh_species( rgs_file_path, species_map, blast_db_dir ) {
    /*
     * Determine which RGS species have available genomes for reciprocal BLAST.
     * Returns list of species short names that have matching genome databases.
     */
    def rgs_species = extract_rgs_species( rgs_file_path )
    log.info "  RGS species found: ${rgs_species.join( ', ' )}"

    def rbh_species = []
    def blast_db_path = file( blast_db_dir )

    if ( !blast_db_path.exists() ) {
        error "BLAST database directory does not exist: ${blast_db_dir}"
    }

    def all_files = blast_db_path.listFiles()

    rgs_species.each { short_name ->
        def genus_species = species_map.containsKey( short_name ) ? species_map[ short_name ] : short_name

        def genome_files = all_files.findAll {
            it.name.contains( genus_species ) && it.name.endsWith( '.aa' ) && !it.name.contains( 'blastdb' )
        }

        if ( genome_files ) {
            rbh_species << short_name
            log.info "    ${short_name} -> ${genus_species}: genome available"
        } else {
            log.warn "    ${short_name} -> ${genus_species}: NO genome found"
        }
    }

    if ( rbh_species.isEmpty() ) {
        error "No RBH species have available genomes! Cannot proceed with reciprocal BLAST."
    }

    log.info "  RBH species (${rbh_species.size()}): ${rbh_species.join( ', ' )}"
    return rbh_species
}

// ============================================================================
// PROCESS 1: List BLAST Databases
// ============================================================================

process setup_blast_database_list {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta)

    output:
        tuple val(gene_family), path(rgs_fasta), path("1-output/1_ai-list-projectdb-blastdbs"), emit: setup_done
        path "1-output"

    script:
    """
    mkdir -p 1-output

    echo "Listing BLAST databases from: ${params.blast_databases_dir}"
    find ${params.blast_databases_dir} -name "*.aa" -not -name "*blastdb*" | sort > 1-output/1_ai-list-projectdb-blastdbs

    DB_COUNT=\$(wc -l < 1-output/1_ai-list-projectdb-blastdbs)
    echo "Found \${DB_COUNT} BLAST databases for gene family: ${gene_family}"

    if [ "\${DB_COUNT}" -eq 0 ]; then
        echo "ERROR: No BLAST databases found in ${params.blast_databases_dir}"
        exit 1
    fi
    """
}

// ============================================================================
// PROCESS 2: BLAST RGS vs Project Database
// Scripts: 002 (generate commands) + execute generated script
// ============================================================================

process blast_rgs_versus_project_database {
    tag "${gene_family}"
    label 'blast'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta), path(db_list)

    output:
        tuple val(gene_family), path(rgs_fasta), path(db_list),
              path("2-output/2_ai-list-projectdb-blast-reports"),
              emit: blast_done
        path "2-output"
        path "3-output"

    script:
    """
    mkdir -p 2-output 3-output

    echo "Generating BLASTP commands for ${gene_family}..."
    python3 ${projectDir}/scripts/002_ai-python-generate_blastp_commands-project_database.py \\
        --database-list ${db_list} \\
        --rgs-fasta ${rgs_fasta} \\
        --output-dir . \\
        --output-script 3-blastp-project_database.sh \\
        --evalue ${params.blast_evalue} \\
        --threads ${params.blast_threads} \\
        --conda-env ${params.blast_conda_env}

    echo "Executing BLASTP searches against project database..."
    chmod +x 3-blastp-project_database.sh
    bash 3-blastp-project_database.sh

    echo "Cataloging BLAST reports..."
    ls 3-output/*.blastp 2>/dev/null | sort > 2-output/2_ai-list-projectdb-blast-reports

    REPORT_COUNT=\$(wc -l < 2-output/2_ai-list-projectdb-blast-reports)
    echo "Generated \${REPORT_COUNT} BLAST reports for ${gene_family}"

    if [ "\${REPORT_COUNT}" -eq 0 ]; then
        echo "ERROR: No BLAST reports generated for ${gene_family}"
        exit 1
    fi
    """
}

// ============================================================================
// PROCESS 3: Extract Blast Gene Sequences
// Script: 004
// ============================================================================

process extract_blast_gene_sequences {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta), path(db_list), path(blast_report_list)

    output:
        tuple val(gene_family), path(rgs_fasta),
              path("4-output/4_ai-bgs-${params.project_database}-${gene_family}-fullseqs.aa"),
              path("4-output/4_ai-bgs-${params.project_database}-${gene_family}-hitregions.aa"),
              emit: bgs_done
        path "4-output"

    script:
    """
    mkdir -p 4-output

    echo "Extracting blast gene sequences for ${gene_family}..."
    python3 ${projectDir}/scripts/004_ai-python-extract_gene_set_sequences.py \\
        --database-list ${db_list} \\
        --report-list ${blast_report_list} \\
        --output-full 4-output/4_ai-bgs-${params.project_database}-${gene_family}-fullseqs.aa \\
        --output-regions 4-output/4_ai-bgs-${params.project_database}-${gene_family}-hitregions.aa

    echo "BGS extraction complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 4: BLAST RGS vs RGS Source Genomes
// Scripts: 005 (generate commands) + execute generated script
// ============================================================================

process blast_rgs_versus_rgs_genomes {
    tag "${gene_family}"
    label 'blast'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta)

    output:
        tuple val(gene_family),
              path("5-output/5_ai-list-rgs-blast-reports"),
              emit: rgs_blast_done
        path "5-output"
        path "6-output"

    script:
    def species_map_path = file("${projectDir}/../${params.rgs_species_map}")
    def species_map_arg = species_map_path.exists() ? "--rgs-species-map ${projectDir}/../${params.rgs_species_map}" : ""
    """
    mkdir -p 5-output 6-output

    echo "Generating RGS genome BLASTP commands for ${gene_family}..."
    python3 ${projectDir}/scripts/005_ai-python-generate_blastp_commands-rgs_genomes.py \\
        --rgs-fasta ${rgs_fasta} \\
        --rgs-genomes-dir ${params.rgs_genomes_dir} \\
        ${species_map_arg} \\
        --output-dir . \\
        --output-script 006-blastp-rgs_genomes.sh \\
        --evalue ${params.blast_evalue} \\
        --threads ${params.blast_threads} \\
        --conda-env ${params.blast_conda_env}

    echo "Executing RGS genome BLASTP searches..."
    chmod +x 006-blastp-rgs_genomes.sh
    bash 006-blastp-rgs_genomes.sh

    echo "Cataloging RGS BLAST reports..."
    ls 6-output/*.blastp 2>/dev/null | sort > 5-output/5_ai-list-rgs-blast-reports

    echo "RGS genome BLASTP complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 5: Prepare Reciprocal BLAST
// Scripts: 007 (list files), 008 (map RGS), 009 (modified genomes) + combine + makeblastdb
// ============================================================================

process prepare_reciprocal_blast {
    tag "${gene_family}"
    label 'blast'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta), path(rgs_blast_report_list)
        val rbh_species_list

    output:
        tuple val(gene_family),
              path("8-output/8_ai-map-rgs-to-genome-identifiers.txt"),
              path("10-output/10_ai-rgs-all-genomes-combined-blastdb*"),
              emit: reciprocal_prep_done
        path "7-output"
        path "8-output"
        path "9-output"
        path "10-output"

    script:
    def rbh_species = rbh_species_list.join( ' ' )
    """
    mkdir -p 7-output 8-output 9-output 10-output

    echo "=== Step 007: List RGS BLAST files and model organism FASTAs ==="
    python3 ${projectDir}/scripts/007_ai-python-list_rgs_blast_files.py \\
        --output-dir . \\
        --blast-databases-dir ${params.blast_databases_dir} \\
        --rbh-species "${rbh_species}" \\
        --output-blast-reports 7-output/7_ai-list-rgs-blast-reports.txt \\
        --output-model-fastas 7-output/7_ai-list-model-organism-fastas.txt

    echo "=== Step 008: Map RGS sequences to reference genome identifiers ==="
    python3 ${projectDir}/scripts/008_ai-python-map_rgs_to_reference_genomes.py \\
        --blast-reports-list 7-output/7_ai-list-rgs-blast-reports.txt \\
        --model-fastas-list 7-output/7_ai-list-model-organism-fastas.txt \\
        --rgs-fasta ${rgs_fasta} \\
        --output-mapping 8-output/8_ai-map-rgs-to-genome-identifiers.txt \\
        --output-rgs-fasta 8-output/8_ai-rgs-with-genome-identifiers.fasta \\
        --output-fasta-list 8-output/8_ai-list-model-organism-fastas-with-rgs-headers.txt \\
        --rbh-species "${rbh_species}"

    echo "=== Step 009: Create modified RBH genomes ==="
    python3 ${projectDir}/scripts/009_ai-python-create_modified_genomes.py \\
        --rgs-fasta ${rgs_fasta} \\
        --mapping-file 8-output/8_ai-map-rgs-to-genome-identifiers.txt \\
        --genome-list 7-output/7_ai-list-model-organism-fastas.txt \\
        --output-dir . \\
        --log-file 9-output/9_ai-log-create-modified-genomes.log

    echo "=== Step 010: Combine modified genomes and create BLAST database ==="
    cat 9-output/9_ai-*.aa-rgs > 10-output/10_ai-rgs-all-genomes-combined.fasta

    makeblastdb \\
        -in 10-output/10_ai-rgs-all-genomes-combined.fasta \\
        -dbtype prot \\
        -out 10-output/10_ai-rgs-all-genomes-combined-blastdb

    echo "Reciprocal BLAST preparation complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 6: Run Reciprocal BLAST
// Scripts: 011 (generate commands) + execute
// ============================================================================

process run_reciprocal_blast {
    tag "${gene_family}"
    label 'blast'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(bgs_fullseqs), path(blastdb_files)

    output:
        tuple val(gene_family),
              path("12-output/12_ai-reciprocal-blast-report.txt"),
              emit: reciprocal_blast_done
        path "11-output"
        path "12-output"

    script:
    // Extract the blastdb prefix from the files
    def blastdb_prefix = blastdb_files[0].toString().replaceAll( /\.[^.]+$/, '' )
    """
    mkdir -p 11-output 12-output

    echo "Generating reciprocal BLAST commands for ${gene_family}..."
    python3 ${projectDir}/scripts/011_ai-python-generate_reciprocal_blast_commands.py \\
        --query-fasta ${bgs_fullseqs} \\
        --database-prefix ${blastdb_prefix} \\
        --output-script 11-output/11_ai-bash-execute_reciprocal_blast.sh \\
        --output-report 12-output/12_ai-reciprocal-blast-report.txt \\
        --evalue ${params.blast_evalue} \\
        --threads ${params.blast_threads} \\
        --conda-env ${params.blast_conda_env}

    echo "Executing reciprocal BLAST..."
    chmod +x 11-output/11_ai-bash-execute_reciprocal_blast.sh
    bash 11-output/11_ai-bash-execute_reciprocal_blast.sh

    echo "Reciprocal BLAST complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 7: Extract Reciprocal Best Hits
// Script: 013
// ============================================================================

process extract_reciprocal_best_hits {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(db_list), path(reciprocal_report), path(rgs_mapping)
        val rbh_species_list

    output:
        tuple val(gene_family),
              path("13-output/13_ai-cgs-${params.project_database}-${gene_family}.aa"),
              emit: rbh_done
        path "13-output"

    script:
    def rbh_species = rbh_species_list.join( ' ' )
    """
    mkdir -p 13-output

    echo "Extracting reciprocal best hits for ${gene_family}..."
    python3 ${projectDir}/scripts/013_ai-python-extract_reciprocal_best_hits.py \\
        --database-list ${db_list} \\
        --blast-report ${reciprocal_report} \\
        --rgs-mapping ${rgs_mapping} \\
        --output-fasta 13-output/13_ai-cgs-${params.project_database}-${gene_family}.aa \\
        --output-filtered 13-output/13_ai-log-dropped-sequences-${gene_family} \\
        --rbh-species "${rbh_species}"

    echo "Reciprocal best hit extraction complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 8: Filter Species by Keeper List
// Script: 014
// ============================================================================

process filter_species {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(cgs_fasta)
        path species_keeper_list

    output:
        tuple val(gene_family),
              path("14-output/14_ai-cgs-${params.project_database}-${gene_family}-filtered.aa"),
              emit: filtered_done
        path "14-output"

    script:
    """
    mkdir -p 14-output

    echo "Filtering species for ${gene_family}..."
    python3 ${projectDir}/scripts/014_ai-python-filter_species_for_tree_building.py \\
        --input-fasta ${cgs_fasta} \\
        --species-keeper-list ${species_keeper_list} \\
        --output-fasta 14-output/14_ai-cgs-${params.project_database}-${gene_family}-filtered.aa

    echo "Species filtering complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 9: Remap CGS Identifiers to GIGANTIC Phylonames
// Script: 015
// ============================================================================

process remap_identifiers {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(filtered_fasta)

    output:
        tuple val(gene_family),
              path("15-output/15_ai-cgs-${params.project_database}-${gene_family}-remapped.aa"),
              emit: remapped_done
        path "15-output"

    script:
    """
    mkdir -p 15-output

    echo "Remapping CGS identifiers for ${gene_family}..."
    python3 ${projectDir}/scripts/015_ai-python-remap_cgs_identifiers_to_gigantic.py \\
        --input-fasta ${filtered_fasta} \\
        --output-fasta 15-output/15_ai-cgs-${params.project_database}-${gene_family}-remapped.aa \\
        --mapping-file ${params.cgs_mapping_file} \\
        --gene-family ${gene_family} \\
        --project-db ${params.project_database}

    echo "Identifier remapping complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 10: Concatenate Final Gene Set (AGS = RGS + CGS)
// Script: 016
// ============================================================================

process concatenate_final_gene_set {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta), path(remapped_fasta), path(rgs_mapping)

    output:
        tuple val(gene_family),
              path("16-output/16_ai-ags-${params.project_database}-${gene_family}-homologs.aa"),
              emit: ags_done
        path "16-output"

    script:
    """
    mkdir -p 16-output

    echo "Concatenating final gene set (AGS) for ${gene_family}..."
    python3 ${projectDir}/scripts/016_ai-python-concatenate_sequences.py \\
        --rgs-file ${rgs_fasta} \\
        --cgs-file ${remapped_fasta} \\
        --rgs-map-file ${rgs_mapping} \\
        --cgs-mapping-file ${params.cgs_mapping_file} \\
        --output-file 16-output/16_ai-ags-${params.project_database}-${gene_family}-homologs.aa \\
        --gene-family ${gene_family} \\
        --project-db ${params.project_database}

    echo "AGS concatenation complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 11: Copy AGS to output_to_input for STEP_3
// ============================================================================

process copy_to_output_to_input {
    tag "${gene_family}"
    label 'local'

    input:
        tuple val(gene_family), path(ags_fasta)

    output:
        path "output_to_input_done.txt", emit: done

    script:
    """
    # Copy to STEP-level output_to_input
    mkdir -p ${projectDir}/../../output_to_input/ags_fastas/${gene_family}
    cp ${ags_fasta} ${projectDir}/../../output_to_input/ags_fastas/${gene_family}/

    # Copy to subproject-level output_to_input
    mkdir -p ${projectDir}/../../../output_to_input/step_2/ags_fastas/${gene_family}
    cp ${ags_fasta} ${projectDir}/../../../output_to_input/step_2/ags_fastas/${gene_family}/

    echo "Copied AGS for ${gene_family} to output_to_input at \$(date)" > output_to_input_done.txt
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    log.info """
    ========================================================================
    GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery
    ========================================================================
    Gene family         : ${params.gene_family}
    RGS file            : ${params.rgs_file}
    Species keeper list : ${params.species_keeper_list}
    BLAST databases     : ${params.blast_databases_dir}
    Project database    : ${params.project_database}
    Output directory    : ${params.output_dir}
    ========================================================================
    """.stripIndent()

    // ---- Validate critical parameters ----
    def workflow_dir = "${projectDir}/.."

    if ( !params.gene_family ) {
        error "gene_family not set in config! Edit rbh_rbf_homologs_config.yaml."
    }
    if ( !params.rgs_file ) {
        error "rgs_file not set in config! Edit rbh_rbf_homologs_config.yaml."
    }
    if ( !params.blast_databases_dir ) {
        error "blast_databases_dir must be set in config. This is the path to BLAST protein databases."
    }
    if ( !params.rgs_genomes_dir ) {
        error "rgs_genomes_dir must be set in config. This is the path to RGS source genome databases."
    }
    if ( !params.cgs_mapping_file ) {
        error "cgs_mapping_file must be set in config. This maps short identifiers to full GIGANTIC phylonames."
    }

    // ---- Resolve RGS file path ----
    def rgs_path = file( "${workflow_dir}/${params.rgs_file}" )
    if ( !rgs_path.exists() ) {
        error "RGS file not found: ${params.rgs_file}\nExpected at: ${rgs_path}\nEnsure the RGS file path is correct in rbh_rbf_homologs_config.yaml."
    }

    def species_keeper_path = file( "${workflow_dir}/${params.species_keeper_list}" )
    if ( !species_keeper_path.exists() ) {
        error "Species keeper list not found: ${species_keeper_path}"
    }

    // ---- Determine RBH species ----
    def species_map_path = "${workflow_dir}/${params.rgs_species_map}"
    def species_map = load_species_map( species_map_path )

    log.info "\nDetermining RBH species for ${params.gene_family}..."
    def rbh_species = determine_rbh_species(
        rgs_path.toString(), species_map, params.blast_databases_dir
    )

    // ---- Create single-item channel for the gene family ----
    gene_family_channel = Channel.of( [ params.gene_family, rgs_path ] )

    // ---- Process 1: Setup and list BLAST databases ----
    setup_blast_database_list( gene_family_channel )

    // ---- Process 2: BLAST RGS vs project database ----
    blast_rgs_versus_project_database( setup_blast_database_list.out.setup_done )

    // ---- Process 3: Extract blast gene sequences ----
    extract_blast_gene_sequences( blast_rgs_versus_project_database.out.blast_done )

    // ---- Process 4: BLAST RGS vs RGS source genomes ----
    def rgs_for_genome_blast = Channel.of( [ params.gene_family, rgs_path ] )
    blast_rgs_versus_rgs_genomes( rgs_for_genome_blast )

    // ---- Process 5: Prepare reciprocal BLAST ----
    def prep_input = extract_blast_gene_sequences.out.bgs_done
        .map { gene_family, rgs_fasta, bgs_fullseqs, bgs_hitregions ->
            [ gene_family, rgs_fasta ]
        }
        .join( blast_rgs_versus_rgs_genomes.out.rgs_blast_done )
        .map { gene_family, rgs_fasta, rgs_blast_list ->
            [ gene_family, rgs_fasta, rgs_blast_list ]
        }

    def rbh_species_channel = Channel.of( rbh_species )

    prepare_reciprocal_blast( prep_input, rbh_species_channel )

    // ---- Process 6: Run reciprocal BLAST ----
    def reciprocal_input = extract_blast_gene_sequences.out.bgs_done
        .map { gene_family, rgs_fasta, bgs_fullseqs, bgs_hitregions ->
            [ gene_family, bgs_fullseqs ]
        }
        .join(
            prepare_reciprocal_blast.out.reciprocal_prep_done
                .map { gene_family, rgs_mapping, blastdb_files ->
                    [ gene_family, blastdb_files ]
                }
        )
        .map { gene_family, bgs_fullseqs, blastdb_files ->
            [ gene_family, bgs_fullseqs, blastdb_files ]
        }

    run_reciprocal_blast( reciprocal_input )

    // ---- Process 7: Extract reciprocal best hits ----
    def rbh_input = setup_blast_database_list.out.setup_done
        .map { gene_family, rgs_fasta, db_list -> [ gene_family, db_list ] }
        .join( run_reciprocal_blast.out.reciprocal_blast_done )
        .join(
            prepare_reciprocal_blast.out.reciprocal_prep_done
                .map { gene_family, rgs_mapping, blastdb_files -> [ gene_family, rgs_mapping ] }
        )
        .map { gene_family, db_list, reciprocal_report, rgs_mapping ->
            [ gene_family, db_list, reciprocal_report, rgs_mapping ]
        }

    def rbh_species_for_extract = Channel.of( rbh_species )

    extract_reciprocal_best_hits( rbh_input, rbh_species_for_extract )

    // ---- Process 8: Filter species ----
    filter_species( extract_reciprocal_best_hits.out.rbh_done, species_keeper_path )

    // ---- Process 9: Remap identifiers ----
    remap_identifiers( filter_species.out.filtered_done )

    // ---- Process 10: Concatenate final gene set ----
    def concat_input = setup_blast_database_list.out.setup_done
        .map { gene_family, rgs_fasta, db_list -> [ gene_family, rgs_fasta ] }
        .join( remap_identifiers.out.remapped_done )
        .join(
            prepare_reciprocal_blast.out.reciprocal_prep_done
                .map { gene_family, rgs_mapping, blastdb_files -> [ gene_family, rgs_mapping ] }
        )
        .map { gene_family, rgs_fasta, remapped_fasta, rgs_mapping ->
            [ gene_family, rgs_fasta, remapped_fasta, rgs_mapping ]
        }

    concatenate_final_gene_set( concat_input )

    // ---- Process 11: Copy to output_to_input ----
    copy_to_output_to_input( concatenate_final_gene_set.out.ags_done )
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
        println "Output files in ${params.output_dir}/:"
        println "   1-output/: BLAST database listing"
        println "   2-output/: Project database BLAST report listing"
        println "   3-output/: Project database BLAST reports"
        println "   4-output/: Blast gene sequences (BGS)"
        println "   5-output/: RGS genome BLAST report listing"
        println "   6-output/: RGS genome BLAST reports"
        println "   7-output/: RBH species file listings"
        println "   8-output/: RGS-to-genome identifier mapping"
        println "   9-output/: Modified genomes with RGS sequences"
        println "  10-output/: Combined genomes and BLAST database"
        println "  11-output/: Reciprocal BLAST commands"
        println "  12-output/: Reciprocal BLAST report"
        println "  13-output/: Candidate gene sequences (CGS)"
        println "  14-output/: Species-filtered sequences"
        println "  15-output/: Remapped CGS identifiers"
        println "  16-output/: Final AGS (All Gene Set)"
        println ""
        println "AGS files also copied to:"
        println "  STEP_2-homolog_discovery/output_to_input/ags_fastas/${params.gene_family}/"
        println "  trees_gene_families/output_to_input/step_2/ags_fastas/${params.gene_family}/"
        println ""
        println "Next: Run STEP_3 phylogenetic analysis with AGS file"
    }
    println "========================================================================"
}
