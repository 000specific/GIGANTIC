# STEP_2-standardize_and_evaluate - Standardize and Evaluate Genomes

**AI**: Claude Code | Opus 4.5 | 2026 February 13
**Human**: Eric Edsinger

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
- **Input**: Genomes and gene annotations from STEP_1 + phylonames mapping
- **Output**: `OUTPUT_pipeline/3-output/gigantic_genomes/`, `OUTPUT_pipeline/3-output/gigantic_gene_annotations/`

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

### 6. Quality Summary and Species Manifest

**Script**: `006_ai-python-summarize_quality_and_generate_species_manifest.py`

Combines all quality metrics into summary tables:
- Generates species selection manifest for STEP_3/STEP_4
- **Input**: All quality data from scripts 001-005
- **Output**: `OUTPUT_pipeline/6-output/6_ai-quality_summary.tsv`, `OUTPUT_pipeline/6-output/6_ai-species_selection_manifest.tsv`

---

## Inputs

Source data from STEP_1-sources, accessed via `output_to_input/`:

| Data Type | Count | Location |
|-----------|-------|----------|
| T1 proteomes | 71 | `../STEP_1-sources/output_to_input/T1_proteomes/` |
| Genomes | 64 | `../STEP_1-sources/output_to_input/genomes/` |
| Gene annotations | 69 | `../STEP_1-sources/output_to_input/gene_annotations/` |

Also requires:
- **Phylonames mapping**: `../../phylonames/workflow-RUN_01-generate_phylonames/OUTPUT_pipeline/4-output/final_project_mapping.tsv`

---

## Outputs

All outputs in `workflow-*/OUTPUT_pipeline/`:

| Output | Script | Location |
|--------|--------|----------|
| Standardized proteomes | 001 | `1-output/gigantic_proteomes/` |
| Standardization manifest | 001 | `1-output/1_ai-standardization_manifest.tsv` |
| Cleaned proteomes | 002 | `2-output/gigantic_proteomes_cleaned/` |
| Genome symlinks | 003 | `3-output/gigantic_genomes/` |
| Annotation symlinks | 003 | `3-output/gigantic_gene_annotations/` |
| Assembly statistics | 004 | `4-output/4_ai-genome_assembly_statistics.tsv` |
| BUSCO summary | 005 | `5-output/5_ai-busco_summary.tsv` |
| Quality summary | 006 | `6-output/6_ai-quality_summary.tsv` |
| Species manifest | 006 | `6-output/6_ai-species_selection_manifest.tsv` |

**Passed to STEP_3 via**: `output_to_input/`

---

## Workflow

```bash
cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/

# Local:
bash RUN-workflow.sh

# SLURM:
sbatch RUN-workflow.sbatch
```

---

## Dependencies

- **STEP_1-sources** must complete first (provides proteomes, genomes, GFFs)
- **phylonames** subproject must complete first (provides species naming)
- **Conda environment**: `ai_gigantic_genomesdb` with `gfastats` and `busco` installed

---

## Research Notebook

All logs and sessions saved to:
```
research_notebook/research_ai/subproject-genomesDB/
```
