# AI Guide: genomesDB Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers genomesDB-specific concepts and the three-step architecture.

**Location**: `gigantic_project-*/subprojects/genomesDB/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| genomesDB concepts, three-step structure | This file |
| STEP_1 sources workflow | `STEP_1-sources/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_2 standardize_and_evaluate workflow | `STEP_2-standardize_and_evaluate/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_3 databases workflow | `STEP_3-databases/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Subproject Does

**Purpose**: Manage genome and proteome data for GIGANTIC projects.

**Three-Step Pipeline**:
1. **Sources** - Collect proteome files from NCBI, UniProt, user sources
2. **Standardize and Evaluate** - Standardize formats, apply phylonames, evaluate quality
3. **Databases** - Build BLAST databases and search indices

**Critical**: Run phylonames subproject FIRST - genomesDB depends on phylonames for species naming.

---

## Three-Step Architecture

### STEP_1-sources

**Directory**: `STEP_1-sources/`
**Workflow**: `workflow-COPYME-collect_source_genomes`

**Function**:
- Download proteomes from NCBI
- Fetch from UniProt
- Accept user-provided files
- Organize by source

**Outputs**:
- `STEP_1-sources/output_to_input/raw_proteomes/` - Raw files for STEP_2

### STEP_2-standardize_and_evaluate

**Directory**: `STEP_2-standardize_and_evaluate/`
**Workflow**: `workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb`

**Function**:
- Rename files using phyloname convention
- Validate FASTA format
- Calculate genome statistics
- Flag quality issues

**Outputs**:
- `STEP_2-standardize_and_evaluate/output_to_input/standardized_proteomes/` - Clean files for STEP_3
- Evaluation reports

### STEP_3-databases

**Directory**: `STEP_3-databases/`
**Workflow**: `workflow-COPYME-build_gigantic_genomesDB`

**Function**:
- Build BLAST databases (blastp)
- Create species manifests
- Generate proteome indices

**Outputs**:
- `STEP_3-databases/output_to_input/` - BLAST databases
- `genomesDB/output_to_input/` - Shared with downstream subprojects

---

## Directory Structure (relative to subproject root)

```
genomesDB/
├── README.md                           # Human documentation
├── AI_GUIDE-genomesDB.md               # THIS FILE
├── RUN-clean_and_record_subproject.sh  # Cleanup for entire subproject
├── RUN-update_upload_to_server.sh      # Update server symlinks
│
├── user_research/                      # Personal workspace
├── output_to_input/                    # Final outputs for downstream
├── upload_to_server/                   # Server sharing
│
├── STEP_1-sources/
│   ├── README.md
│   ├── AI_GUIDE-sources.md
│   ├── RUN-clean_and_record_subproject.sh
│   ├── user_research/
│   ├── output_to_input/                # → STEP_2 inputs
│   └── workflow-COPYME-collect_source_genomes/
│       ├── INPUT_user/
│       ├── OUTPUT_pipeline/
│       └── ai/
│
├── STEP_2-standardize_and_evaluate/
│   ├── README.md
│   ├── AI_GUIDE-standardize_and_evaluate.md
│   ├── RUN-clean_and_record_subproject.sh
│   ├── user_research/
│   ├── output_to_input/                # → STEP_3 inputs
│   └── workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
│       ├── INPUT_user/
│       ├── OUTPUT_pipeline/
│       └── ai/
│
└── STEP_3-databases/
    ├── README.md
    ├── AI_GUIDE-databases.md
    ├── RUN-clean_and_record_subproject.sh
    ├── user_research/
    ├── output_to_input/                # → genomesDB/output_to_input
    └── workflow-COPYME-build_gigantic_genomesDB/
        ├── INPUT_user/
        ├── OUTPUT_pipeline/
        └── ai/
```

---

## Data Flow Between Steps

```
STEP_1-sources/output_to_input/ → STEP_2-standardize_and_evaluate/INPUT_user/
                                              ↓
STEP_2-standardize_and_evaluate/output_to_input/ → STEP_3-databases/INPUT_user/
                                                            ↓
                        STEP_3-databases/output_to_input/ → genomesDB/output_to_input/
                                                                  ↓
                                              (Other GIGANTIC subprojects)
```

---

## Path Depth Adjustment

Step directories are nested ONE level deeper than standard subprojects:

| Location | Relative path to project root |
|----------|-------------------------------|
| `genomesDB/` | `../../` |
| `genomesDB/STEP_1-sources/` | `../../../` |
| `genomesDB/STEP_1-sources/workflow-COPYME-*/` | `../../../../` |
| `genomesDB/STEP_1-sources/workflow-COPYME-*/ai/` | `../../../../../` |

---

## Research Notebook Location

All genomesDB AI sessions (from ANY step) save to ONE location:
```
research_notebook/research_ai/subproject-genomesDB/
├── logs/
└── sessions/
```

This consolidates documentation regardless of which step generated it.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Species not found" | phylonames not run | Run phylonames subproject first |
| STEP_2 can't find inputs | STEP_1 not run | Run STEP_1-sources workflow first |
| STEP_3 can't find inputs | STEP_2 not run | Run STEP_2-standardize_and_evaluate first |
| BLAST database empty | No proteomes passed QC | Check STEP_2 evaluation reports |
| Download failed | Network or NCBI down | Check connectivity, retry |
| "No phyloname mapping" | Missing mapping file | Run phylonames, check output_to_input |

### Diagnostic Commands

```bash
# Check phylonames dependency
ls ../phylonames/output_to_input/maps/

# Check STEP_1 outputs
ls STEP_1-sources/output_to_input/

# Check STEP_2 outputs
ls STEP_2-standardize_and_evaluate/output_to_input/

# Check STEP_3 outputs (final)
ls STEP_3-databases/output_to_input/
ls output_to_input/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `STEP_1-sources/workflow-*/INPUT_user/source_manifest.tsv` | What to download | **YES** |
| `STEP_2-standardize_and_evaluate/workflow-*/INPUT_user/` | (from STEP_1) | No |
| `STEP_3-databases/workflow-*/INPUT_user/` | (from STEP_2) | No |
| `output_to_input/` | Final databases | No |
| `upload_to_server/upload_manifest.tsv` | What to share | **YES** |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting genomesDB | "Have you run the phylonames subproject first?" |
| Species sources | "Which sources should we collect from? (NCBI, UniProt, custom)" |
| Quality thresholds | "What quality thresholds should we use for evaluation?" |
| BLAST database type | "What type of BLAST database? (protein, nucleotide)" |
| Error occurred | "Which step failed? What error message?" |

---

## Next Steps After genomesDB

Guide users to:
1. **annotations_hmms** - Run functional annotations on proteomes
2. **orthogroups** - Identify ortholog groups across species
3. **trees_gene_families** - Build gene family phylogenies
