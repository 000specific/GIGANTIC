# STEP_2-standardize_and_evaluate - Standardize and Evaluate Genomes

**AI**: Claude Code | Opus 4.5 | 2026 February 13
**Human**: Eric Edsinger

---

## Purpose

STEP_2 of the genomesDB pipeline. Takes source data from STEP_1, applies GIGANTIC naming conventions (phylonames), and evaluates genome/proteome quality through multiple analyses.

**Part of**: genomesDB subproject (see `../README.md`)

---

## Five Analysis Areas

STEP_2 performs five distinct analyses, each implemented as a standalone Python script within the NextFlow workflow:

### 1. Proteome Phyloname Standardization (Complete)

**Script**: `001_ai-python-standardize_proteome_phylonames.py`

Standardizes proteome filenames and FASTA headers to use GIGANTIC phylonames:
- **Filenames**: `phyloname-proteome.aa`
- **Headers**: `>g_(source_gene_id)-t_(source_transcript_id)-p_(source_protein_id)-n_(phyloname)`
- **Input**: 71 T1 proteomes from STEP_1 + phylonames mapping from phylonames subproject
- **Output**: `OUTPUT_pipeline/1-output/gigantic_proteomes/` (71 standardized proteomes)
- **Log**: Every header transformation recorded

### 2. Genome N50 Statistics

**Script**: `002_ai-python-calculate_genome_n50_statistics.py`

Calculates assembly quality statistics for all available genomes:
- Scaffold/contig count
- Assembly size (total bp)
- Largest scaffold size
- N50 and N90 statistics
- **Input**: 64 genomes from STEP_1
- **Output**: Summary TSV table with statistics per species

### 3. BUSCO Quality Assessment

**Script**: TBD

Runs BUSCO (Benchmarking Universal Single-Copy Orthologs) to assess proteome completeness.

### 4. Gene Structure Statistics (from GFFs)

**Script**: TBD

Calculates gene lengths, intron counts and lengths, and exon counts and lengths from GFF annotation files:
- **Input**: 69 gene annotation files (.gff3/.gtf) from STEP_1

### 5. Protein Length Statistics

**Script**: TBD

Calculates protein length distributions from proteome FASTA files:
- **Input**: 71 T1 proteomes from STEP_1

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
| N50 statistics | 002 | `2-output/` (TBD) |
| BUSCO reports | 003 | `3-output/` (TBD) |
| Gene structure stats | 004 | `4-output/` (TBD) |
| Protein length stats | 005 | `5-output/` (TBD) |

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
- **BUSCO** (conda environment with BUSCO installed, for analysis area 3)

---

## Research Notebook

All logs and sessions saved to:
```
research_notebook/research_ai/subproject-genomesDB/
```
