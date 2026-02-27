# workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb

**AI**: Claude Code | Opus 4.5 | 2026 February 26
**Human**: Eric Edsinger

---

## Purpose

STEP_2 workflow template for standardizing genomic data with GIGANTIC phylonames and calculating quality metrics.

**Part of**: STEP_2-standardize_and_evaluate (see `../README.md`)

---

## What This Workflow Does

1. **Proteome Standardization** (Script 001)
   - Renames proteome files: `Genus_species-genome-*.aa` → `phyloname-proteome.aa`
   - Transforms FASTA headers: includes gene/transcript/protein IDs and phyloname

2. **Genome/Annotation Standardization** (Script 002)
   - Creates phyloname-named symlinks to original files
   - Preserves source data while providing consistent naming

3. **Assembly Quality Statistics** (Script 003)
   - Uses `gfastats` to calculate N50, scaffold counts, etc.
   - Outputs summary table for all genomes

---

## Usage

**Copy this template to create a run directory:**
```bash
cp -r workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb workflow-RUN_01-standardize_evaluate_build_gigantic_genomesdb
cd workflow-RUN_01-standardize_evaluate_build_gigantic_genomesdb
```

**Run locally:**
```bash
bash RUN-workflow.sh
```

**Run on SLURM:**
```bash
# Edit SLURM-workflow.sbatch to set --account and --qos
sbatch SLURM-workflow.sbatch
```

---

## Prerequisites

- **STEP_1-sources** complete (provides proteomes, genomes, annotations)
- **phylonames subproject** complete (provides species naming)
- **Conda environment**: `ai_gigantic_genomesdb` with `gfastats` installed

---

## Directory Structure

```
workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
├── README.md                    # This file
├── RUN-workflow.sh              # Main workflow script
├── SLURM-workflow.sbatch        # SLURM job wrapper
├── INPUT_user/                  # Empty (inputs come from output_to_input directories)
├── OUTPUT_pipeline/             # Workflow outputs
│   ├── 1-output/                # Standardized proteomes
│   ├── 2-output/                # Genome/annotation symlinks
│   ├── 3-output/                # Assembly statistics
│   ├── 4-output/                # (Reserved for future analyses)
│   └── 5-output/                # (Reserved for future analyses)
└── ai/
    ├── AI_GUIDE-standardize_evaluate_workflow.md
    └── scripts/
        ├── 001_ai-python-standardize_proteome_phylonames.py
        ├── 002_ai-python-standardize_genome_and_annotation_phylonames.py
        └── 003_ai-python-calculate_genome_assembly_statistics.py
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Standardized proteomes | `OUTPUT_pipeline/1-output/gigantic_proteomes/` | Ready for BLAST database building |
| Transformation manifest | `OUTPUT_pipeline/1-output/1_ai-standardization_manifest.tsv` | Maps original → standardized names |
| Genome symlinks | `OUTPUT_pipeline/2-output/gigantic_genomes/` | Phyloname-named links to originals |
| Annotation symlinks | `OUTPUT_pipeline/2-output/gigantic_gene_annotations/` | Phyloname-named links to originals |
| Assembly statistics | `OUTPUT_pipeline/3-output/3_ai-genome_assembly_statistics.tsv` | N50, scaffold counts, etc. |

---

## Next Step

After this workflow completes, proceed to:
```
STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/
```
