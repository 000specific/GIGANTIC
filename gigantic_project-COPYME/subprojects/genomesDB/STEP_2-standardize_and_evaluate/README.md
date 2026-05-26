# STEP_2-standardize_and_evaluate — Standardize and Evaluate Genomes/Proteomes

<!-- ============================================================================
AI:      Claude Code | Opus 4.5 | 2026 February 13 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) — genomesDB overview
- Parent project: [`../../../README.md`](../../../README.md)
- This STEP's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow to run: [`workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/README.md`](workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/README.md)
- Reads from: [`../STEP_1-sources/`](../STEP_1-sources/) (ingested raw)
  + [`../../phylonames/output_to_input/maps/`](../../phylonames/output_to_input/maps/) (species naming mapping)
- **Next STEP**: [`../STEP_3-databases/`](../STEP_3-databases/) — build BLAST databases

---

## Purpose

STEP_2 of the genomesDB pipeline. Takes source data from STEP_1, applies GIGANTIC naming conventions (phylonames), and evaluates genome/proteome quality through multiple analyses.

**Part of**: genomesDB subproject (see `../README.md`)

---

## Six Analysis Areas

STEP_2 performs six distinct analyses, each implemented as a standalone Python script within the NextFlow workflow:

### 1. Proteome Phyloname Standardization

**Script**: `001_ai-python-standardize_proteome_phylonames.py`

Standardizes proteome filenames and FASTA headers to use GIGANTIC phylonames:
- **Filenames**: `phyloname-proteome.aa`
- **Headers**: `>g_(source_gene_id)-t_(source_transcript_id)-p_(source_protein_id)-n_(phyloname)`
- **Input**: T1 proteomes from STEP_1 + phylonames mapping from phylonames subproject
- **Output**: `OUTPUT_pipeline/1-output/gigantic_proteomes/` (standardized proteomes)
- **Log**: Every header transformation recorded

### 2. Proteome Cleaning

**Script**: `002_ai-python-clean_proteome_invalid_residues.py`

Replaces invalid amino acid characters ('.' used for stop codons in some proteomes) with 'X':
- Required for BLAST and BUSCO compatibility
- **Input**: Standardized proteomes from script 001
- **Output**: `OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned/`

### 3. Genome/Annotation Standardization

**Script**: `003_ai-python-standardize_genome_and_annotation_phylonames.py`

Creates phyloname-named symlinks to original genome and annotation files:
- Preserves source data while providing consistent naming
- **Input**: Genomes and genome annotations from STEP_1 + phylonames mapping
- **Output**: `OUTPUT_pipeline/3-output/gigantic_genomes/`, `OUTPUT_pipeline/3-output/gigantic_genome_annotations/`

### 4. Assembly Quality Statistics

**Script**: `004_ai-python-calculate_genome_assembly_statistics.py`

Uses `gfastats` to calculate assembly quality metrics:
- Scaffold/contig count, assembly size, largest scaffold, N50, N90
- **Input**: Phyloname-named genomes from script 003
- **Output**: `OUTPUT_pipeline/4-output/4_ai-genome_assembly_statistics.tsv`

### 5. BUSCO Proteome Evaluation

**Script**: `005_ai-python-run_busco_proteome_evaluation.py`

Runs BUSCO (Benchmarking Universal Single-Copy Orthologs) to assess proteome completeness:
- Uses lineage-specific databases from INPUT_user/busco_lineages.txt
- Runs as a separate SLURM sub-job for parallelization
- **Input**: Cleaned proteomes from script 002 + BUSCO lineage assignments
- **Output**: `OUTPUT_pipeline/5-output/5_ai-busco_summary.tsv`

### 6. Quality Summary

**Script**: `006_ai-python-summarize_quality.py`

Combines all quality metrics (BUSCO + gfastats + proteome counts) into
a single comprehensive quality summary table.

- **Input**: Assembly stats (script 004) + BUSCO summary (script 005) + standardization manifest (script 001)
- **Output**: `OUTPUT_pipeline/6-output/6_ai-comprehensive_quality_summary.tsv`

**Note**: STEP_2 does NOT produce a "species selection manifest".
Species selection happens in STEP_4 (user-driven via
`INPUT_user/selected_species.txt`). STEP_3 builds BLAST DBs for every
proteome from STEP_2 — filtering happens only in STEP_4.

### 7. Per-Run Audit Log

**Script**: `007_ai-python-write_run_log.py`

Writes a timestamped log to `ai/logs/` documenting the run (project
name, status, etc.) for reproducibility.

---

## Inputs

Source data from STEP_1-sources, accessed via `output_to_input/`:

| Data Type | Count | Location |
|-----------|-------|----------|
| T1 proteomes | 71 | `../output_to_input/STEP_1-sources/T1_proteomes/` |
| Genomes | 64 | `../output_to_input/STEP_1-sources/genomes/` |
| Genome annotations | 69 | `../output_to_input/STEP_1-sources/genome_annotations/` |

Also requires:
- **Phylonames mapping** (read from `output_to_input/` per §2): `../../../phylonames/output_to_input/maps/[project]_map-genus_species_X_phylonames.tsv`
  — the convenience symlink that auto-points at phylonames STEP_2 output
  (with user overrides) if it was run, otherwise STEP_1 (NCBI-only).

---

## Outputs

All outputs in `workflow-*/OUTPUT_pipeline/`:

| Output | Script | Location |
|---|---|---|
| Standardized proteomes | 001 | `1-output/gigantic_proteomes/` |
| Standardization manifest | 001 | `1-output/1_ai-standardization_manifest.tsv` |
| Cleaned proteomes | 002 | `2-output/gigantic_proteomes_cleaned/` |
| Cleaning summary + residue corrections | 002 | `2-output/2_ai-proteome_cleaning_summary.tsv`, `2-output/2_ai-proteome_residue_corrections.tsv` |
| Genome symlinks | 003 | `3-output/gigantic_genomes/` |
| Annotation symlinks | 003 | `3-output/gigantic_genome_annotations/` |
| Assembly statistics | 004 | `4-output/4_ai-genome_assembly_statistics.tsv` |
| BUSCO summary (or skip-stub if `busco.enabled: false`) | 005 | `5-output/5_ai-busco_summary.tsv` + `5-output/busco_results/` |
| Comprehensive quality summary | 006 | `6-output/6_ai-comprehensive_quality_summary.tsv` |
| Per-run audit log | 007 | `ai/logs/run_*.log` |

**Passed to STEP_3 via**: `output_to_input/`

---

## Workflow

```bash
cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/

bash RUN-workflow.sh
```

The unified driver runs locally or self-submits to SLURM based on
`execution_mode` in `START_HERE-user_config.yaml` (per §29).

---

## Dependencies

- **STEP_1-sources** must complete first (provides proteomes, genomes, GFFs)
- **phylonames** subproject must complete first (provides species naming)
- **Conda environment**: `aiG-genomesDB` with `gfastats` and `busco` installed

---

## Research Notebook

Workflow run logs are saved to each workflow's `ai/logs/` directory. AI sessions are extracted project-wide to `research_notebook/research_ai/sessions/`.
