# STEP_3 Workflow: Build GIGANTIC GenomesDB BLAST Databases

**AI**: Claude Code | Opus 4.6 | 2026 March 06
**Human**: Eric Edsinger

---

## Purpose

Build per-genome BLAST protein databases from ALL standardized proteomes in STEP_2. Each species gets its own individual BLAST database, enabling flexible searches against specific genomes. No filtering -- all species from STEP_2 get databases built.

---

## Prerequisites

1. **STEP_2 complete**: Standardized proteomes in `output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/`
2. **BLAST+ tools available**: `makeblastdb` must be in PATH (available in `ai_gigantic_genomesdb` conda environment)

---

## Quick Start

```bash
cd workflow-COPYME-build_gigantic_genomesDB/

# Local:
bash RUN-workflow.sh

# SLURM:
sbatch RUN-workflow.sbatch
```

---

## Workflow Steps

| Step | Script | Purpose |
|------|--------|---------|
| 1 | `001_ai-python-build_per_genome_blastdbs.py` | Build per-genome BLAST databases for all proteomes |
| 2 | `002_ai-python-write_run_log.py` | Write run log to ai/logs/ |

---

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Proteomes | `output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/` | All .aa proteome files from STEP_2 |

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| BLAST databases | `OUTPUT_pipeline/1-output/gigantic-T1-blastp/` | Per-genome BLAST databases |
| makeblastdb commands | `OUTPUT_pipeline/1-output/1_ai-makeblastdb_commands.sh` | Log of all makeblastdb commands |

**Shared with other subprojects via**: `output_to_input/STEP_3-databases/gigantic-T1-blastp/`

---

## Using the BLAST Databases

```bash
# Search against a single species database
blastp \
    -db OUTPUT_pipeline/1-output/gigantic-T1-blastp/PHYLONAME-proteome.aa \
    -query your_sequences.fasta \
    -out results.txt

# Example with specific species
blastp \
    -db OUTPUT_pipeline/1-output/gigantic-T1-blastp/Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens-proteome.aa \
    -query query.fasta \
    -out human_blast_results.txt
```

---

## Directory Structure

```
workflow-COPYME-build_gigantic_genomesDB/
├── RUN-workflow.sh              # Local execution script
├── RUN-workflow.sbatch          # SLURM submission script
├── README.md                    # This file
├── START_HERE-user_config.yaml  # Workflow configuration
├── OUTPUT_pipeline/
│   └── 1-output/                # Script 001 outputs
│       ├── gigantic-T1-blastp/  # Per-genome BLAST databases
│       └── 1_ai-makeblastdb_commands.sh
└── ai/
    ├── main.nf
    ├── nextflow.config
    ├── logs/                    # Run logs from write_run_log
    └── scripts/
        ├── 001_ai-python-build_per_genome_blastdbs.py
        └── 002_ai-python-write_run_log.py
```

---

## Next Step

After this workflow completes, proceed to:
```
STEP_4-create_final_species_set/workflow-COPYME-create_final_species_set/
```

STEP_4 selects and copies the final species set (proteomes + BLAST databases) for downstream subprojects.

---

## Notes

- The `T1` in directory names indicates these are Transcript 1 (longest isoform) proteomes
- Each BLAST database consists of multiple files (`.pdb`, `.phr`, `.pin`, `.pjs`, `.pog`, `.pos`, `.pot`, `.psq`, `.ptf`, `.pto`)
- The FASTA file is kept alongside the BLAST database files for reference
