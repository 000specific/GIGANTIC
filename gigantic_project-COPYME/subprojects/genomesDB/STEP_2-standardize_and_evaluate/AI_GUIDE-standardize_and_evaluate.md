# AI Guide: STEP_2-standardize_and_evaluate (genomesDB)

**For AI Assistants**: This guide covers STEP_2 of the genomesDB subproject. For genomesDB overview and three-step architecture, see `../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_2-standardize_and_evaluate/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| genomesDB concepts, three-step structure | `../AI_GUIDE-genomesDB.md` |
| STEP_2 standardize_and_evaluate concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Step Does

**Purpose**: Standardize data formats, apply phylonames, and evaluate genome/proteome quality through five analysis areas.

**Five Analysis Areas**:

| # | Analysis | Input | Script | Status |
|---|----------|-------|--------|--------|
| 1 | Proteome phyloname standardization | T1 proteomes (71) + phylonames mapping | `001_ai-python-standardize_proteome_phylonames.py` | Complete |
| 2 | Genome N50 statistics | Genomes (64) | `002_ai-python-calculate_genome_n50_statistics.py` | Planned |
| 3 | BUSCO quality assessment | Proteomes (71) | TBD | Planned |
| 4 | Gene structure stats (GFFs) | Gene annotations (69) | TBD | Planned |
| 5 | Protein length stats | T1 proteomes (71) | TBD | Planned |

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

### 1. Proteome Phyloname Standardization (Complete)

**What it does**: Renames proteome files and FASTA headers to use GIGANTIC phylonames.

**Filename convention**: `phyloname-proteome.aa`
- Example: `Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens-proteome.aa`

**Header convention**: `>g_(source_gene_id)-t_(source_transcript_id)-p_(source_protein_id)-n_(phyloname)`
- Example: `>g_GeneID123-t_XM_456-p_XP_789-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens`

**Key mapping**: genus_species extracted from input filenames → looked up in phylonames mapping → phyloname applied to filename and all headers.

### 2. Genome N50 Statistics (Next)

**What it does**: Calculates assembly quality metrics for all available genomes.

**Statistics produced per genome**:
- Scaffold/contig count
- Assembly size (total bp)
- Largest scaffold size
- N50 (bp) - weighted median scaffold length at 50% of total size
- N90 (bp) - weighted median scaffold length at 90% of total size

**GIGANTIC_0 reference**: The original workflow used an external `N50.sh` bash script. GIGANTIC_1 reimplements this as pure Python for portability and to eliminate the external dependency.

**Input**: 64 genome files from `../STEP_1-sources/output_to_input/genomes/`

### 3-5. Remaining Analyses

See `README.md` for current status and planned scope.

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
│   │   ├── gigantic_proteomes/            # 71 standardized .aa files
│   │   └── 1_ai-standardization_manifest.tsv
│   ├── 2-output/                          # N50 statistics
│   ├── 3-output/                          # BUSCO reports
│   ├── 4-output/                          # Gene structure stats
│   └── 5-output/                          # Protein length stats
└── ai/
    └── scripts/
        ├── 001_ai-python-standardize_proteome_phylonames.py
        ├── 002_ai-python-calculate_genome_n50_statistics.py  (planned)
        └── ...
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
