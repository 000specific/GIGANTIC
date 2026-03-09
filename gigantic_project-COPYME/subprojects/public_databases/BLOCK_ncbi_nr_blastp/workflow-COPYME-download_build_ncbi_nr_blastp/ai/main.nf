#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Nextflow pipeline to download NCBI nr and build BLAST protein database
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// NCBI nr BLAST Protein Database Pipeline
// =============================================================================
//
// Four-step pipeline:
//   1. Download NCBI nr FASTA (nr.gz) from NCBI FTP
//   2. Decompress nr.gz and build BLAST protein database with makeblastdb
//   3. Validate database with blastdbcmd -info
//   4. Write timestamped run log
//
// GIGANTIC convention: makeblastdb runs WITHOUT -parse_seqids because many
// NCBI nr identifiers exceed the 50-character limit imposed by that flag.
//
// Symlinks for output_to_input/BLOCK_ncbi_nr_blastp/ are created by
// RUN-workflow.sh after pipeline completes.
// =============================================================================

// Script directory
scripts_dir = "${projectDir}/scripts"

process download_ncbi_nr {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        val nr_url

    output:
        path 'nr.gz', emit: nr_compressed

    script:
    """
    bash ${scripts_dir}/001_ai-bash-download_ncbi_nr.sh \
        --url "${nr_url}" \
        --output-file nr.gz
    """
}

process build_blastp_database {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        path nr_compressed

    output:
        path 'nr.pdb', emit: database_pdb
        path 'nr.phr', emit: database_phr
        path 'nr.pin', emit: database_pin
        path 'nr.psq', emit: database_psq
        path 'nr.pot', emit: database_pot
        path 'nr.ptf', emit: database_ptf
        path 'nr.pto', emit: database_pto

    script:
    """
    bash ${scripts_dir}/002_ai-bash-build_blastp_database.sh \
        --input-file ${nr_compressed} \
        --output-dir .
    """
}

process validate_database {
    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        path database_pdb
        path database_phr
        path database_pin
        path database_psq
        path database_pot
        path database_ptf
        path database_pto

    output:
        path '3_ai-validation_report.txt', emit: validation_report

    script:
    """
    python3 ${scripts_dir}/003_ai-python-validate_database.py \
        --database-path nr \
        --output-file 3_ai-validation_report.txt
    """
}

process write_run_log {
    publishDir "${params.output_dir}/4-output", mode: 'copy'

    input:
        path validation_report

    output:
        path '4_ai-run_log.txt', emit: run_log

    script:
    """
    python3 ${scripts_dir}/004_ai-python-write_run_log.py \
        --validation-report ${validation_report} \
        --output-file 4_ai-run_log.txt
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/BLOCK_ncbi_nr_blastp/ are created by
// RUN-workflow.sh AFTER this pipeline completes. NextFlow only writes
// real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    // Step 1: Download NCBI nr FASTA
    download_ncbi_nr( params.nr_url )

    // Step 2: Build BLAST protein database
    build_blastp_database( download_ncbi_nr.out.nr_compressed )

    // Step 3: Validate database
    validate_database(
        build_blastp_database.out.database_pdb,
        build_blastp_database.out.database_phr,
        build_blastp_database.out.database_pin,
        build_blastp_database.out.database_psq,
        build_blastp_database.out.database_pot,
        build_blastp_database.out.database_ptf,
        build_blastp_database.out.database_pto
    )

    // Step 4: Write run log
    write_run_log( validate_database.out.validation_report )
}
