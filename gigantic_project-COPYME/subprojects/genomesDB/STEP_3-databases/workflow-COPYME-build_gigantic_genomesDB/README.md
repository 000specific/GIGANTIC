# STEP_3 Workflow: Build GIGANTIC GenomesDB BLAST Databases

**AI**: Claude Code | Opus 4.5 | 2026 February 26
**Human**: Eric Edsinger

---

## Purpose

Build per-genome BLAST protein databases from standardized proteomes. Each species gets its own individual BLAST database, enabling flexible searches against specific genomes.

---

## Prerequisites

1. **STEP_2 complete**: Standardized proteomes in `STEP_2/output_to_input/gigantic_proteomes/`
2. **Species manifest edited**: User has reviewed and set `Include=YES/NO` in the species selection manifest
3. **BLAST+ tools available**: `makeblastdb` must be in PATH (available in `ai_gigantic_genomesdb` conda environment)

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
| 1 | `001_ai-python-filter_species_manifest.py` | Filter species to Include=YES only |
| 2 | `002_ai-python-build_per_genome_blastdbs.py` | Build per-genome BLAST databases |

---

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Species manifest | `STEP_2/output_to_input/species_selection_manifest.tsv` | User-edited manifest with Include=YES/NO |
| Proteomes | `STEP_2/output_to_input/gigantic_proteomes/` | Standardized T1 proteomes |

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Filtered manifest | `OUTPUT_pipeline/1-output/1_ai-filtered_species_manifest.tsv` | Species with Include=YES |
| BLAST databases | `OUTPUT_pipeline/2-output/gigantic-T1-blastp/` | Per-genome BLAST databases |
| makeblastdb commands | `OUTPUT_pipeline/2-output/2_ai-makeblastdb_commands.sh` | Log of all makeblastdb commands |

**Shared with other subprojects via**: `output_to_input/gigantic-T1-blastp/`

---

## Using the BLAST Databases

```bash
# Search against a single species database
blastp \
    -db OUTPUT_pipeline/2-output/gigantic-T1-blastp/PHYLONAME-proteome.aa \
    -query your_sequences.fasta \
    -out results.txt

# Example with specific species
blastp \
    -db OUTPUT_pipeline/2-output/gigantic-T1-blastp/Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens-proteome.aa \
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
├── INPUT_user/                  # User inputs (if any)
├── OUTPUT_pipeline/
│   ├── 1-output/                # Script 001 outputs
│   │   └── 1_ai-filtered_species_manifest.tsv
│   └── 2-output/                # Script 002 outputs
│       ├── gigantic-T1-blastp/  # Per-genome BLAST databases
│       └── 2_ai-makeblastdb_commands.sh
└── ai/
    └── scripts/
        ├── 001_ai-python-filter_species_manifest.py
        └── 002_ai-python-build_per_genome_blastdbs.py
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
