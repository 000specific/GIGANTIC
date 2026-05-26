# AI Guide: STEP_2-standardize_and_evaluate (genomesDB)

**For AI Assistants**: This guide covers STEP_2 of the genomesDB subproject. For genomesDB overview and four-step architecture, see `../AI_GUIDE.md`. For GIGANTIC overview, see `../../../AI_GUIDE.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_2-standardize_and_evaluate/`

---

## ⚠️ CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- ❌ **NEVER** silently do something different than requested
- ❌ **NEVER** assume you know better and proceed without asking
- ✅ **ALWAYS** stop and explain the discrepancy
- ✅ **ALWAYS** ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE.md` |
| genomesDB concepts, four-step structure | `../AI_GUIDE.md` |
| STEP_2 standardize_and_evaluate concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Step Does

**Purpose**: Standardize data formats, apply phylonames, and evaluate genome/proteome quality through six analysis areas.

**Seven scripts** (six analysis steps + audit log):

| # | Analysis | Input | Script |
|---|---|---|---|
| 1 | Proteome phyloname standardization | T1 proteomes + phylonames mapping | `001_ai-python-standardize_proteome_phylonames.py` |
| 2 | Proteome cleaning (invalid residues) | Standardized proteomes | `002_ai-python-clean_proteome_invalid_residues.py` |
| 3 | Genome/annotation phyloname standardization | Genomes + genome annotations + phylonames | `003_ai-python-standardize_genome_and_annotation_phylonames.py` |
| 4 | Assembly quality statistics (gfastats) | Phyloname-named genomes | `004_ai-python-calculate_genome_assembly_statistics.py` |
| 5 | BUSCO proteome evaluation (conditional on `busco.enabled` in YAML) | Cleaned proteomes + lineage assignments | `005_ai-python-run_busco_proteome_evaluation.py` |
| 6 | Quality summary (BUSCO + gfastats merged) | All quality data | `006_ai-python-summarize_quality.py` |
| 7 | Per-run audit log | n/a | `007_ai-python-write_run_log.py` |

**Note on species selection**: STEP_2 produces a comprehensive quality
summary but does **NOT** produce a species selection manifest. The user
reviews the quality summary, decides which species to keep, and then
writes the selection in STEP_4's `INPUT_user/selected_species.txt`.
STEP_3 builds BLAST databases for **all** species from STEP_2 — STEP_4
is where filtering happens.

---

## Inputs from STEP_1

STEP_2 reads from STEP_1's outputs in the subproject-root `output_to_input/` directory (relative path: `../output_to_input/STEP_1-sources/`):

| Data Type | Count | Subdirectory | File Types |
|-----------|-------|--------------|------------|
| T1 proteomes | 71 | `T1_proteomes/` | `.aa` files |
| Genomes | 64 | `genomes/` | `.fasta` files |
| Genome annotations | 69 | `genome_annotations/` | `.gff3` and `.gtf` files |

**Phylonames mapping** (from phylonames subproject, via output_to_input per §2):
- `../../../phylonames/output_to_input/maps/[project]_map-genus_species_X_phylonames.tsv`
  — the convenience symlink that auto-points at STEP_2 output (with user
  overrides) if STEP_2 was run, otherwise STEP_1 (NCBI-only)

---

## Script Architecture

All scripts are standalone Python (no external dependencies beyond standard library) and reside in:
```
workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/ai/scripts/
```

Each script:
- Can be run independently from the command line
- Will also be integrated into the NextFlow workflow
- Outputs to its own numbered subdirectory: `OUTPUT_pipeline/N-output/`
- Produces comprehensive logs

---

## Analysis Area Details

### 1. Proteome Phyloname Standardization

**What it does**: Renames proteome files and FASTA headers to use GIGANTIC phylonames.

**Filename convention**: `phyloname-proteome.aa`
- Example: `Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens-proteome.aa`

**Header convention**: `>g_(source_gene_id)-t_(source_transcript_id)-p_(source_protein_id)-n_(phyloname)`
- Example: `>g_GeneID123-t_XM_456-p_XP_789-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens`

**Key mapping**: genus_species extracted from input filenames --> looked up in phylonames mapping --> phyloname applied to filename and all headers.

### 2. Proteome Cleaning

**What it does**: Replaces invalid amino acid characters ('.' used for stop codons in some proteomes) with 'X'.

**Why needed**: BLAST and BUSCO require valid amino acid characters. Some source proteomes use '.' for stop codons.

### 3. Genome/Annotation Standardization

**What it does**: Creates phyloname-named symlinks to original genome and annotation files.

**Preserves source data** while providing consistent naming across the pipeline.

### 4. Assembly Quality Statistics

**What it does**: Uses `gfastats` to calculate assembly quality metrics for all available genomes.

**Statistics produced per genome**:
- Scaffold/contig count
- Assembly size (total bp)
- Largest scaffold size
- N50 (bp) - weighted median scaffold length at 50% of total size
- N90 (bp) - weighted median scaffold length at 90% of total size

**Requires**: `aiG-genomesDB` conda environment with `gfastats` installed.

### 5. BUSCO Proteome Evaluation

**What it does**: Runs BUSCO to assess proteome completeness using lineage-specific databases.

**Requires**: `aiG-genomesDB` conda environment with `busco` installed. BUSCO lineage assignments in `INPUT_user/busco_lineages.txt`.

### 6. Quality Summary

**What it does**: Combines all quality metrics (BUSCO + gfastats + per-proteome counts) into a single comprehensive quality summary table.

**Important**: STEP_2 does NOT produce a "species selection manifest".
Species selection is the user's call after reviewing the quality
summary, and it's recorded in STEP_4's
`INPUT_user/selected_species.txt`. STEP_3 builds BLAST DBs for every
proteome from STEP_2; filtering happens only in STEP_4.

### 7. Per-Run Audit Log

**What it does**: Writes a timestamped log to `ai/logs/` documenting
the run (project name, status, etc.) for reproducibility.

---

## Path Depth

From this step directory, project root is at `../../../`:

| Location | Relative path to project root |
|----------|-------------------------------|
| `STEP_2-standardize_and_evaluate/` | `../../../` |
| `STEP_2-standardize_and_evaluate/workflow-COPYME-*/` | `../../../../` |

---

## Output Structure

```
workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
├── OUTPUT_pipeline/
│   ├── 1-output/                          # Proteome standardization
│   │   ├── gigantic_proteomes/            # Standardized .aa files
│   │   ├── 1_ai-standardization_manifest.tsv
│   │   └── 1_ai-log-standardize_proteome_phylonames.log
│   ├── 2-output/                          # Cleaned proteomes
│   │   ├── gigantic_proteomes_cleaned/
│   │   ├── 2_ai-proteome_cleaning_summary.tsv
│   │   ├── 2_ai-proteome_residue_corrections.tsv
│   │   └── 2_ai-log-clean_proteome_invalid_residues.log
│   ├── 3-output/                          # Genome/annotation symlinks
│   │   ├── gigantic_genomes/
│   │   ├── gigantic_genome_annotations/
│   │   ├── 3_ai-standardization_manifest.tsv
│   │   └── 3_ai-log-standardize_genome_and_annotation_phylonames.log
│   ├── 4-output/                          # Assembly statistics
│   │   ├── 4_ai-genome_assembly_statistics.tsv
│   │   └── 4_ai-log-calculate_genome_assembly_statistics.log
│   ├── 5-output/                          # BUSCO reports (or skip-stub if busco.enabled=false)
│   │   ├── 5_ai-busco_summary.tsv
│   │   ├── busco_results/
│   │   └── 5_ai-log-run_busco_proteome_evaluation.log
│   └── 6-output/                          # Comprehensive quality summary (BUSCO + gfastats merged)
│       ├── 6_ai-comprehensive_quality_summary.tsv
│       └── 6_ai-log-summarize_quality.log
└── ai/
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

**Note**: there is no `6_ai-species_selection_manifest.tsv` — earlier
docs claimed STEP_2 generated one, but it does not. Species selection
is the user's call in STEP_4 (`INPUT_user/selected_species.txt`).

---

## Research Notebook Location

Workflow run logs are saved to each workflow's `ai/logs/` directory. AI sessions are extracted project-wide to `research_notebook/research_ai/sessions/`.

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/INPUT_user/` | Input from STEP_1 | No |
| `workflow-*/ai/scripts/` | Analysis scripts | No (AI-generated) |
| `output_to_input/` | Standardized data for STEP_3 | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No input proteomes | STEP_1 not run | Run STEP_1-sources workflow first |
| No input genomes | STEP_1 not run or no genomes available | Check `../output_to_input/STEP_1-sources/genomes/` |
| Phyloname lookup fails | phylonames not run | Run phylonames subproject first |
| genus_species not in mapping | Naming inconsistency | Check upstream naming in STEP_1 source data |
| Invalid FASTA | Corrupted download | Re-run STEP_1 source download |
| Missing GFF/GTF | Not all species have annotations | 69 of 71 species have annotations; 2 are expected missing |

---

## Species Coverage

Not all 71 species have all three data types:

| Data Type | Species Count | Notes |
|-----------|---------------|-------|
| T1 proteomes | 71 | All species |
| Genomes | 64 | 7 species without genomes |
| Genome annotations | 69 | 2 species without GFF/GTF |

Scripts must handle cases where a species has proteomes but not genomes or annotations.
