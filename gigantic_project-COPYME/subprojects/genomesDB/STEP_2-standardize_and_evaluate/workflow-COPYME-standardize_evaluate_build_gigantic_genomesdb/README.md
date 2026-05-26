# workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 27 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP: [`../README.md`](../README.md) — STEP_2-standardize_and_evaluate overview
- Parent subproject: [`../../README.md`](../../README.md) — genomesDB overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../output_to_input/STEP_1-sources/` (T1_proteomes, genomes, genome_annotations)
  + `../../../phylonames/output_to_input/maps/` (species naming mapping)
- **Next workflow**: `../../STEP_3-databases/workflow-COPYME-*/`

---

## Purpose

STEP_2 workflow template for standardizing genomic data with GIGANTIC phylonames and calculating quality metrics.

**Part of**: STEP_2-standardize_and_evaluate (see `../README.md`)

---

## What This Workflow Does (7 scripts)

1. **Proteome Standardization** (Script 001)
   - Renames proteome files: `Genus_species-genome_*.aa` → `phyloname-proteome.aa`
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

5. **BUSCO Proteome Evaluation** (Script 005, conditional on `busco.enabled: true` in YAML)
   - Runs BUSCO to assess proteome completeness
   - Uses lineage-specific databases from INPUT_user/busco_lineages.txt
   - If `busco.enabled: false`, a skip-stub writes an explanatory placeholder
     so STEP_2 still completes

6. **Quality Summary** (Script 006)
   - Combines all quality metrics into a single comprehensive quality summary table
   - Output: `6-output/6_ai-comprehensive_quality_summary.tsv`
   - Does NOT produce a "species selection manifest" — species selection
     is the user's call in STEP_4 (`INPUT_user/selected_species.txt`).
     STEP_3 builds BLAST DBs for every species; filtering only in STEP_4.

7. **Per-Run Audit Log** (Script 007)
   - Writes a timestamped log to `ai/logs/` documenting the run

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
nano START_HERE-user_config.yaml
```

**Run:**
```bash
bash RUN-workflow.sh
```

The unified driver runs locally or self-submits to SLURM based on
`execution_mode` in `START_HERE-user_config.yaml` (per §29). For SLURM,
also set `slurm_account` / `slurm_qos` in that YAML.

The workflow uses NextFlow internally (`ai/main.nf`) to orchestrate all 6 scripts sequentially, with explicit outputs at each step for research transparency.

---

## Prerequisites

- **STEP_1-sources** complete (provides proteomes, genomes, annotations)
- **phylonames subproject** complete (provides species naming)
- **Conda environment**: `aiG-genomesDB` with `gfastats` and `busco` installed
- **INPUT_user/busco_lineages.txt**: BUSCO lineage assignments for each species

---

## Directory Structure

```
workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
├── README.md                              # This file
├── RUN-workflow.sh            # Local runner (calls NextFlow)
├── START_HERE-user_config.yaml       # User-editable configuration
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
    ├── conda_environment.yml              # env: aiG-genomesDB (shared across all 4 STEPs)
    ├── AI_GUIDE.md
    ├── logs/                              # Per-run audit logs from script 007
    └── scripts/
        ├── 001_ai-python-standardize_proteome_phylonames.py
        ├── 002_ai-python-clean_proteome_invalid_residues.py
        ├── 003_ai-python-standardize_genome_and_annotation_phylonames.py
        ├── 004_ai-python-calculate_genome_assembly_statistics.py
        ├── 005_ai-python-run_busco_proteome_evaluation.py
        ├── 006_ai-python-summarize_quality.py
        └── 007_ai-python-write_run_log.py
```

---

## Outputs

| Output | Location | Description |
|---|---|---|
| Standardized proteomes | `1-output/gigantic_proteomes/` | Phyloname-formatted proteomes |
| Standardization manifest | `1-output/1_ai-standardization_manifest.tsv` | Maps original to standardized names |
| Cleaned proteomes | `2-output/gigantic_proteomes_cleaned/` | Ready for BLAST/BUSCO |
| Cleaning summary + residue corrections | `2-output/2_ai-proteome_cleaning_summary.tsv`, `2-output/2_ai-proteome_residue_corrections.tsv` | Audit of '.' → 'X' substitutions |
| Genome symlinks | `3-output/gigantic_genomes/` | Phyloname-named links |
| Annotation symlinks | `3-output/gigantic_genome_annotations/` | Phyloname-named links |
| Assembly statistics | `4-output/4_ai-genome_assembly_statistics.tsv` | N50, scaffold counts, etc. |
| BUSCO summary | `5-output/5_ai-busco_summary.tsv` (+ `5-output/busco_results/`) | Proteome completeness scores; skip-stub if `busco.enabled: false` |
| Comprehensive quality summary | `6-output/6_ai-comprehensive_quality_summary.tsv` | BUSCO + gfastats + proteome counts merged |
| Per-run audit log | `ai/logs/run_*.log` | Per-run reproducibility log |

**Removed**: There is no `6_ai-species_selection_manifest.tsv` —
earlier docs claimed STEP_2 generated one; it doesn't. Species
selection happens in STEP_4 via `INPUT_user/selected_species.txt`.

---

## Next Step

After this workflow completes, proceed to:
```
STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/
```
