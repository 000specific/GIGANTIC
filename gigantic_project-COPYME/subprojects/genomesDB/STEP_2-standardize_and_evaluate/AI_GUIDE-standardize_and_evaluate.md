# AI Guide: STEP_2-standardize_and_evaluate (genomesDB)

**For AI Assistants**: This guide covers STEP_2 of the genomesDB subproject. For genomesDB overview and four-step architecture, see `../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

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
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| genomesDB concepts, four-step structure | `../AI_GUIDE-genomesDB.md` |
| STEP_2 standardize_and_evaluate concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Step Does

**Purpose**: Standardize data formats, apply phylonames, and evaluate genome/proteome quality through six analysis areas.

**Six Analysis Areas**:

| # | Analysis | Input | Script | Status |
|---|----------|-------|--------|--------|
| 1 | Proteome phyloname standardization | T1 proteomes + phylonames mapping | `001_ai-python-standardize_proteome_phylonames.py` | Complete |
| 2 | Proteome cleaning (invalid residues) | Standardized proteomes | `002_ai-python-clean_proteome_invalid_residues.py` | Complete |
| 3 | Genome/annotation phyloname standardization | Genomes + gene annotations + phylonames | `003_ai-python-standardize_genome_and_annotation_phylonames.py` | Complete |
| 4 | Assembly quality statistics (gfastats) | Phyloname-named genomes | `004_ai-python-calculate_genome_assembly_statistics.py` | Complete |
| 5 | BUSCO proteome evaluation | Cleaned proteomes + lineage assignments | `005_ai-python-run_busco_proteome_evaluation.py` | Complete |
| 6 | Quality summary and species manifest | All quality data | `006_ai-python-summarize_quality_and_generate_species_manifest.py` | Complete |

---

## Inputs from STEP_1

STEP_2 reads from STEP_1's `output_to_input/` directory (relative path: `../STEP_1-sources/output_to_input/`):

| Data Type | Count | Subdirectory | File Types |
|-----------|-------|--------------|------------|
| T1 proteomes | 71 | `T1_proteomes/` | `.aa` files |
| Genomes | 64 | `genomes/` | `.fasta` files |
| Gene annotations | 69 | `gene_annotations/` | `.gff3` and `.gtf` files |

**Phylonames mapping** (from phylonames subproject):
- `../../phylonames/workflow-RUN_01-generate_phylonames/OUTPUT_pipeline/4-output/final_project_mapping.tsv`

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

**Requires**: `ai_gigantic_genomesdb` conda environment with `gfastats` installed.

### 5. BUSCO Proteome Evaluation

**What it does**: Runs BUSCO to assess proteome completeness using lineage-specific databases.

**Requires**: `ai_gigantic_genomesdb` conda environment with `busco` installed. BUSCO lineage assignments in `INPUT_user/busco_lineages.txt`.

### 6. Quality Summary and Species Manifest

**What it does**: Combines all quality metrics into summary tables and generates a species selection manifest for STEP_3/STEP_4.

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
│   │   └── 1_ai-standardization_manifest.tsv
│   ├── 2-output/                          # Cleaned proteomes
│   │   └── gigantic_proteomes_cleaned/
│   ├── 3-output/                          # Genome/annotation symlinks
│   │   ├── gigantic_genomes/
│   │   └── gigantic_gene_annotations/
│   ├── 4-output/                          # Assembly statistics
│   │   └── 4_ai-genome_assembly_statistics.tsv
│   ├── 5-output/                          # BUSCO reports
│   │   └── 5_ai-busco_summary.tsv
│   └── 6-output/                          # Quality summary and species manifest
│       ├── 6_ai-quality_summary.tsv
│       └── 6_ai-species_selection_manifest.tsv
└── ai/
    └── scripts/
        ├── 001_ai-python-standardize_proteome_phylonames.py
        ├── 002_ai-python-clean_proteome_invalid_residues.py
        ├── 003_ai-python-standardize_genome_and_annotation_phylonames.py
        ├── 004_ai-python-calculate_genome_assembly_statistics.py
        ├── 005_ai-python-run_busco_proteome_evaluation.py
        └── 006_ai-python-summarize_quality_and_generate_species_manifest.py
```

---

## Research Notebook Location

All STEP_2 logs save to the genomesDB subproject location:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/INPUT_user/` | Input from STEP_1 | No |
| `workflow-*/RUN-*.sbatch` | SLURM account/qos | **YES** (SLURM) |
| `workflow-*/ai/scripts/` | Analysis scripts | No (AI-generated) |
| `output_to_input/` | Standardized data for STEP_3 | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No input proteomes | STEP_1 not run | Run STEP_1-sources workflow first |
| No input genomes | STEP_1 not run or no genomes available | Check `../STEP_1-sources/output_to_input/genomes/` |
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
| Gene annotations | 69 | 2 species without GFF/GTF |

Scripts must handle cases where a species has proteomes but not genomes or annotations.
