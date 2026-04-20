#!/usr/bin/env nextflow
/*
 * GIGANTIC trees_gene_families STEP_1 - RBH/RBF Homolog Discovery Pipeline
 * AI: Claude Code | Opus 4.6 | 2026 March 10
 * Human: Eric Edsinger
 *
 * Purpose: Validate RGS and discover homologs via Reciprocal Best Hit (RBH) /
 *          Reciprocal Best Family (RBF) BLAST methodology for a SINGLE gene family.
 *
 * Usage: Each workflow copy processes ONE gene family. Copy the template,
 *        configure START_HERE-user_config.yaml, then run.
 *
 * Process Overview:
 *    1: Validate RGS file (script 001) - fails fast if invalid
 *    2: List BLAST databases
 *    3: BLAST RGS vs project database (script 002 + execute generated commands)
 *    4: Extract blast gene sequences (script 004)
 *    5: BLAST RGS vs RGS source genomes (script 005 + execute, parallel with 3-4)
 *    6: Prepare reciprocal BLAST (scripts 007, 008, 009 + combine + makeblastdb)
 *    7: Run reciprocal BLAST (script 011 + execute generated commands)
 *    8: Extract candidate gene sequences (script 013)
 *    9: Filter species by keeper list (script 014)
 *   10: Concatenate RGS + CGS into final AGS (script 016)
 *   11: Write run log (script 017)
 *   (Symlinks for output_to_input created by RUN-workflow.sh after pipeline completes)
 *
 * Data Flow:
 *   Config gene_family + rgs_file → validate → all processes
 *   Final AGS fasta → OUTPUT_pipeline/16-output/ (symlinks in ../../../output_to_input/STEP_1-homolog_discovery/ by RUN-workflow.sh)
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
params.project_database = "speciesN_T1-speciesN"
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
     * 5-field GIGANTIC format: >rgs_{family}-{species}-{gene_symbol}-{source}-{identifier}
     */
    def species_set = [] as Set
    def rgs_file = file( rgs_file_path )

    rgs_file.eachLine { line ->
        if ( line.startsWith( '>' ) ) {
            def header = line.substring( 1 ).trim()
            def parts = header.split( '-' )
            if ( parts.size() >= 5 && parts[0].startsWith( 'rgs_' ) ) {
                def species_short_name = parts[1]
                if ( species_short_name && Character.isLetter( species_short_name.charAt( 0 ) ) ) {
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
// PROCESS 1: Validate RGS File
// Script: 001 - Fails fast if RGS file has issues before expensive BLAST runs
// ============================================================================

process validate_rgs {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta)

    output:
        tuple val(gene_family), path("1-output/1_ai-validated-${gene_family}-rgs.aa"), emit: validated_rgs
        path "1-output"

    script:
    """
    mkdir -p 1-output

    echo "Validating RGS file for ${gene_family}..."
    python3 ${projectDir}/scripts/001_ai-python-validate_rgs.py \
        --input ${rgs_fasta} \
        --output 1-output/1_ai-validated-${gene_family}-rgs.aa \
        --gene-family ${gene_family} \
        --report 1-output/1_ai-validation-report-${gene_family}.txt \
        --log-file 1-output/1_ai-log-validate_rgs-${gene_family}.log

    echo "RGS validation complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 2: List BLAST Databases
// ============================================================================

process setup_blast_database_list {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta)

    output:
        tuple val(gene_family), path(rgs_fasta), path("2-output/2_ai-list-projectdb-blastdbs"), emit: setup_done
        path "2-output"

    script:
    """
    mkdir -p 2-output

    echo "Listing BLAST databases from: ${params.blast_databases_dir}"
    find ${params.blast_databases_dir} -name "*.aa" -not -name "*blastdb*" | sort > 2-output/2_ai-list-projectdb-blastdbs

    DB_COUNT=\$(wc -l < 2-output/2_ai-list-projectdb-blastdbs)
    echo "Found \${DB_COUNT} BLAST databases for gene family: ${gene_family}"

    if [ "\${DB_COUNT}" -eq 0 ]; then
        echo "ERROR: No BLAST databases found in ${params.blast_databases_dir}"
        exit 1
    fi
    """
}

// ============================================================================
// PROCESS 3: BLAST RGS vs Project Database
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
    for f in 3-output/*.blastp; do
        [ -e "\$f" ] && readlink -f "\$f"
    done | sort > 2-output/2_ai-list-projectdb-blast-reports

    REPORT_COUNT=\$(wc -l < 2-output/2_ai-list-projectdb-blast-reports)
    echo "Generated \${REPORT_COUNT} BLAST reports for ${gene_family}"

    if [ "\${REPORT_COUNT}" -eq 0 ]; then
        echo "ERROR: No BLAST reports generated for ${gene_family}"
        exit 1
    fi
    """
}

// ============================================================================
// PROCESS 4: Extract Blast Gene Sequences
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
// PROCESS 5: BLAST RGS vs RGS Source Genomes
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
    for f in 6-output/*.blastp; do
        [ -e "\$f" ] && readlink -f "\$f"
    done | sort > 5-output/5_ai-list-rgs-blast-reports

    echo "RGS genome BLASTP complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 6: Prepare Reciprocal BLAST
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
        --input-blast-report-list ${rgs_blast_report_list} \\
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
        --log-file 9-output/9_ai-log-create-modified-genomes.log \\
        ${params.include_orphan_rgs ? '--include-orphan-rgs' : ''}

    echo "=== Step 010: Combine modified genomes and create BLAST database ==="
    # Combine modified genomes (and orphan RGS if present)
    cat 9-output/9_ai-*.aa-rgs > 10-output/10_ai-rgs-all-genomes-combined.fasta
    if [ -f 9-output/9_ai-orphan-rgs-sequences.aa ]; then
        cat 9-output/9_ai-orphan-rgs-sequences.aa >> 10-output/10_ai-rgs-all-genomes-combined.fasta
        echo "Appended orphan RGS sequences to combined database"
    fi

    makeblastdb \\
        -in 10-output/10_ai-rgs-all-genomes-combined.fasta \\
        -dbtype prot \\
        -out 10-output/10_ai-rgs-all-genomes-combined-blastdb

    # Append orphan RGS mappings so Script 013 and STEP_3 recognize
    # orphan truncated headers as valid rgs- hits
    if [ -f 9-output/9_ai-orphan-rgs-mapping.txt ]; then
        cat 9-output/9_ai-orphan-rgs-mapping.txt >> 8-output/8_ai-map-rgs-to-genome-identifiers.txt
        # Also append to truncation map (for STEP_3 gene assignment)
        awk -F'\\t' '{print \$3"\\t"\$2}' 9-output/9_ai-orphan-rgs-mapping.txt >> 8-output/8_ai-header_truncation_map.txt
        echo "Appended orphan RGS mappings to identifier mapping and truncation map"
    fi

    echo "Reciprocal BLAST preparation complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 7: Run Reciprocal BLAST
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
// PROCESS 8: Extract Reciprocal Best Hits
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
// PROCESS 9: Filter Species by Keeper List
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
// PROCESS 10: Concatenate Final Gene Set (AGS = RGS + CGS)
// Script: 016
// NOTE: BLAST v5 databases preserve full identifiers, so no remapping needed.
//       CGS sequences already have full GIGANTIC headers from the database.
// ============================================================================

process concatenate_final_gene_set {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(rgs_fasta), path(filtered_cgs_fasta)

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
        --cgs-file ${filtered_cgs_fasta} \\
        --output-file 16-output/16_ai-ags-${params.project_database}-${gene_family}-homologs.aa \\
        --gene-family ${gene_family} \\
        --project-db ${params.project_database}

    echo "AGS concatenation complete for ${gene_family}"
    """
}

// ============================================================================
// PROCESS 10b: Restore Full-Length RGS in AGS (CONDITIONAL)
// Script: 018
// Only runs when rgs_sequence_is_full_length is false (subsequence RGS).
// Replaces domain-length RGS sequences in the AGS with full-length versions
// so the final phylogenetic tree uses full-length proteins.
// ============================================================================

process restore_full_length_rgs {
    tag "${gene_family}"
    label 'local'

    publishDir "${projectDir}/../${params.output_dir}", mode: 'copy', overwrite: true

    input:
        tuple val(gene_family), path(ags_fasta)

    output:
        tuple val(gene_family),
              path("18-output/*full_length_rgs*"),
              emit: restored_done
        path "18-output"

    script:
    """
    mkdir -p 18-output

    echo "Restoring full-length RGS sequences for ${gene_family}..."
    python3 ${projectDir}/scripts/018_ai-python-restore_full_length_rgs_sequences.py \\
        --ags-fasta ${ags_fasta} \\
        --full-length-rgs ${projectDir}/../${params.rgs_full_length_file} \\
        --output-dir 18-output

    echo "Full-length RGS restoration complete for ${gene_family}"
    """
}

/*
 * Process 11: Write Run Log (FINAL)
 * Calls: scripts/017_ai-python-write_run_log.py
 *
 * Creates a timestamped log in ai/logs/ within this workflow directory
 * for transparency and reproducibility.
 */
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/017_ai-python-write_run_log.py \
        --workflow-name "rbh_rbf_homologs" \
        --subproject-name "trees_gene_families" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================
// NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
// pipeline completes. Real files only live in OUTPUT_pipeline/N-output/.

workflow {
    log.info """
    ========================================================================
    GIGANTIC trees_gene_families STEP_1 - RBH/RBF Homolog Discovery
    ========================================================================
    Gene family         : ${params.gene_family}
    RGS file (for BLAST): ${params.rgs_file}
    RGS full-length     : ${params.rgs_full_length_file}
    RGS is full-length  : ${params.rgs_sequence_is_full_length}
    Species keeper list : ${params.species_keeper_list}
    BLAST databases     : ${params.blast_databases_dir}
    Project database    : ${params.project_database}
    Output directory    : ${params.output_dir}
    ========================================================================
    """.stripIndent()

    // ---- Validate critical parameters ----
    def workflow_dir = "${projectDir}/.."

    if ( !params.gene_family ) {
        error "gene_family not set in config! Edit START_HERE-user_config.yaml."
    }
    if ( !params.rgs_full_length_file ) {
        error "rgs_full_length_file not set in config! Edit START_HERE-user_config.yaml."
    }
    if ( !params.blast_databases_dir ) {
        error "blast_databases_dir must be set in config. This is the path to BLAST protein databases."
    }
    if ( !params.rgs_genomes_dir ) {
        error "rgs_genomes_dir must be set in config. This is the path to RGS source genome databases."
    }

    // ---- Validate BLAST paths (resolved to absolute by nextflow.config) ----
    if ( !file( params.blast_databases_dir ).exists() ) {
        error "BLAST databases directory not found: ${params.blast_databases_dir}\nCheck blast_databases_dir in START_HERE-user_config.yaml"
    }
    if ( !file( params.rgs_genomes_dir ).exists() ) {
        error "RGS genomes directory not found: ${params.rgs_genomes_dir}\nCheck rgs_genomes_dir in START_HERE-user_config.yaml"
    }

    // ---- Validate subsequence RGS configuration ----
    if ( !params.rgs_sequence_is_full_length ) {
        log.info "RGS mode: SUBSEQUENCE (rgs_sequence_is_full_length = false)"
        log.info "  -> Reciprocal BLAST will use hit-region subsequences"
        log.info "  -> Script 018 will restore full-length RGS in final AGS"
        if ( !params.rgs_subsequence_file ) {
            error "rgs_sequence_is_full_length is false but rgs_subsequence_file is not set!\n" +
                  "When using subsequence RGS, you must provide the domain subsequence file.\n" +
                  "Set rgs_subsequence_file in START_HERE-user_config.yaml under gene_family:"
        }
    } else {
        log.info "RGS mode: FULL-LENGTH (default)"
    }

    log.info "BLAST databases: ${params.blast_databases_dir}"
    log.info "RGS genomes:     ${params.rgs_genomes_dir}"

    // ---- Resolve RGS file path ----
    def rgs_path = file( "${workflow_dir}/${params.rgs_file}" )
    if ( !rgs_path.exists() ) {
        error "RGS file not found: ${params.rgs_file}\nExpected at: ${rgs_path}\nEnsure the RGS file path is correct in START_HERE-user_config.yaml."
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

    // ---- Process 1: Validate RGS file (fails fast before expensive BLAST runs) ----
    validate_rgs( gene_family_channel )

    // ---- Process 2: Setup and list BLAST databases ----
    setup_blast_database_list( validate_rgs.out.validated_rgs )

    // ---- Process 3: BLAST RGS vs project database ----
    blast_rgs_versus_project_database( setup_blast_database_list.out.setup_done )

    // ---- Process 4: Extract blast gene sequences ----
    extract_blast_gene_sequences( blast_rgs_versus_project_database.out.blast_done )

    // ---- Process 5: BLAST RGS vs RGS source genomes (runs in parallel with 3-4) ----
    def rgs_for_genome_blast = validate_rgs.out.validated_rgs
    blast_rgs_versus_rgs_genomes( rgs_for_genome_blast )

    // ---- Process 6: Prepare reciprocal BLAST ----
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

    // ---- Process 7: Run reciprocal BLAST ----
    // When RGS is domain-only (rgs_sequence_is_full_length = false),
    // use hit-region subsequences for the reciprocal BLAST instead of
    // full-length BGS. This ensures the reciprocal query length matches
    // the subsequence RGS spliced into the modified genomes,
    // preventing BLAST from preferring full-length genome proteins over
    // the shorter RGS sequences.
    def use_hitregions = !params.rgs_sequence_is_full_length
    def reciprocal_input = extract_blast_gene_sequences.out.bgs_done
        .map { gene_family, rgs_fasta, bgs_fullseqs, bgs_hitregions ->
            [ gene_family, use_hitregions ? bgs_hitregions : bgs_fullseqs ]
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

    // ---- Process 8: Extract reciprocal best hits ----
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

    // ---- Process 9: Filter species ----
    filter_species( extract_reciprocal_best_hits.out.rbh_done, species_keeper_path )

    // ---- Process 10: Concatenate final gene set ----
    def concat_input = setup_blast_database_list.out.setup_done
        .map { gene_family, rgs_fasta, db_list -> [ gene_family, rgs_fasta ] }
        .join( filter_species.out.filtered_done )
        .map { gene_family, rgs_fasta, filtered_fasta ->
            [ gene_family, rgs_fasta, filtered_fasta ]
        }

    concatenate_final_gene_set( concat_input )

    // ---- Process 10b: Restore full-length RGS (conditional) ----
    // Only runs when rgs_sequence_is_full_length is false (subsequence RGS).
    // When RGS is already full-length, skip this step entirely.
    if ( !params.rgs_sequence_is_full_length ) {
        restore_full_length_rgs( concatenate_final_gene_set.out.ags_done )
        write_run_log( restore_full_length_rgs.out.restored_done.map { true } )
    } else {
        write_run_log( concatenate_final_gene_set.out.ags_done.map { true } )
    }

    // NOTE: Symlinks for output_to_input/ are created by RUN-workflow.sh after
    // pipeline completes. Real files only live in OUTPUT_pipeline/16-output/.
}

// ============================================================================
// COMPLETION HANDLER
// ============================================================================

workflow.onComplete {
    println ""
    println "========================================================================"
    println "GIGANTIC trees_gene_families STEP_1 Pipeline Complete!"
    println "========================================================================"
    println "Gene family: ${params.gene_family}"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    println ""
    if ( workflow.success ) {
        println "Run log written to ai/logs/ in this workflow directory"
        println ""
        println "Output files in ${params.output_dir}/:"
        println "   1-output/: RGS validation (validated FASTA + report)"
        println "   2-output/: BLAST database listing"
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
        println "  16-output/: Final AGS (All Gene Set)"
        println ""
        println "Symlinks created by RUN-workflow.sh in:"
        println "  ../../../output_to_input/STEP_1-homolog_discovery/ags_fastas/${params.gene_family}/"
        println ""
        println "Next: Run STEP_2 phylogenetic analysis with AGS file"
    }
    println "========================================================================"
}
