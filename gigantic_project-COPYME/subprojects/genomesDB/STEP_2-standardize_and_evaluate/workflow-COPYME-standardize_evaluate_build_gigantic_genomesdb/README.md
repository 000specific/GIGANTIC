# workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb

**AI**: Claude Code | Opus 4.6 | 2026 February 27
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

2. **Proteome Cleaning** (Script 002)
   - Replaces invalid amino acid characters ('.' used for stop codons in some proteomes) with 'X'
   - Required for BLAST and BUSCO compatibility

3. **Genome/Annotation Standardization** (Script 003)
   - Creates phyloname-named symlinks to original files
   - Preserves source data while providing consistent naming

4. **Assembly Quality Statistics** (Script 004)
   - Uses `gfastats` to calculate N50, scaffold counts, etc.
   - Outputs summary table for all genomes

5. **BUSCO Proteome Evaluation** (Script 005)
   - Runs BUSCO to assess proteome completeness
   - Uses lineage-specific databases from INPUT_user/busco_lineages.txt
   - Runs as a separate SLURM sub-job for parallelization

6. **Quality Summary and Species Manifest** (Script 006)
   - Combines all quality metrics into summary tables
   - Generates species selection manifest for STEP_3

---

## Usage

**Copy this template to create a run directory:**
```bash
cp -r workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb workflow-RUN_01-standardize_evaluate_build_gigantic_genomesdb
cd workflow-RUN_01-standardize_evaluate_build_gigantic_genomesdb
```

**Configure your run:**
```bash
# Edit the configuration file with your project settings
nano standardize_evaluate_config.yaml
```

**Run locally:**
```bash
bash RUN-standardize_evaluate.sh
```

**Run on SLURM:**
```bash
# Edit RUN-standardize_evaluate.sbatch to set --account and --qos
sbatch RUN-standardize_evaluate.sbatch
```

The workflow uses NextFlow internally (`ai/main.nf`) to orchestrate all 6 scripts sequentially, with explicit outputs at each step for research transparency.

---

## Prerequisites

- **STEP_1-sources** complete (provides proteomes, genomes, annotations)
- **phylonames subproject** complete (provides species naming)
- **Conda environment**: `ai_gigantic_genomesdb` with `gfastats` and `busco` installed
- **INPUT_user/busco_lineages.txt**: BUSCO lineage assignments for each species

---

## Directory Structure

```
workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
├── README.md                              # This file
├── RUN-standardize_evaluate.sh            # Local runner (calls NextFlow)
├── RUN-standardize_evaluate.sbatch        # SLURM wrapper
├── standardize_evaluate_config.yaml       # User-editable configuration
├── INPUT_user/                            # User-provided inputs
│   └── busco_lineages.txt                 # BUSCO lineage assignments
├── OUTPUT_pipeline/                       # Workflow outputs
│   ├── 1-output/                          # Standardized proteomes
│   ├── 2-output/                          # Cleaned proteomes
│   ├── 3-output/                          # Genome/annotation symlinks
│   ├── 4-output/                          # Assembly statistics
│   ├── 5-output/                          # BUSCO results
│   └── 6-output/                          # Quality summary and manifest
└── ai/
    ├── main.nf                            # NextFlow pipeline definition
    ├── nextflow.config                    # NextFlow settings
    ├── AI_GUIDE-standardize_evaluate_workflow.md
    └── scripts/
        ├── 001_ai-python-standardize_proteome_phylonames.py
        ├── 002_ai-python-clean_proteome_invalid_residues.py
        ├── 003_ai-python-standardize_genome_and_annotation_phylonames.py
        ├── 004_ai-python-calculate_genome_assembly_statistics.py
        ├── 005_ai-python-run_busco_proteome_evaluation.py
        └── 006_ai-python-summarize_quality_and_generate_species_manifest.py
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Standardized proteomes | `1-output/gigantic_proteomes/` | Phyloname-formatted proteomes |
| Standardization manifest | `1-output/1_ai-standardization_manifest.tsv` | Maps original to standardized names |
| Cleaned proteomes | `2-output/gigantic_proteomes_cleaned/` | Ready for BLAST/BUSCO |
| Genome symlinks | `3-output/gigantic_genomes/` | Phyloname-named links |
| Annotation symlinks | `3-output/gigantic_gene_annotations/` | Phyloname-named links |
| Assembly statistics | `4-output/4_ai-genome_assembly_statistics.tsv` | N50, scaffold counts, etc. |
| BUSCO summary | `5-output/5_ai-busco_summary.tsv` | Proteome completeness scores |
| Quality summary | `6-output/6_ai-quality_summary.tsv` | Combined quality metrics |
| Species manifest | `6-output/6_ai-species_selection_manifest.tsv` | For STEP_3 filtering |

---

## Next Step

After this workflow completes, proceed to:
```
STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/
```
