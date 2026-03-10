# AI Guide: trees_gene_families Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers trees_gene_families-specific concepts and the two-step architecture.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_families/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain the discrepancy
- ALWAYS ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| trees_gene_families concepts, two-step structure | This file |
| STEP_1 homolog discovery | `gene_family_COPYME/STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` |
| STEP_2 phylogenetic analysis | `gene_family_COPYME/STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` |

---

## What This Subproject Does

**Purpose**: Build phylogenetic trees for individual gene families across GIGANTIC species.

**Two-Step Pipeline**:
1. **Homolog Discovery** - Validate RGS, then find homologs via Reciprocal Best Hit / Reciprocal Best Family (RBH/RBF)
2. **Phylogenetic Analysis** - Align sequences, trim, build trees, visualize

**Note**: RGS validation is built into STEP_1 as its first process. If validation fails, the pipeline stops immediately before expensive BLAST runs.

**Critical**: Run genomesDB subproject FIRST - trees_gene_families depends on genomesDB for BLAST databases and proteome files.

---

## Key Concepts

### Gene Set Terminology

| Term | Abbreviation | Meaning |
|------|-------------|---------|
| Reference Gene Set | rgs | Curated sequences from model organisms (e.g., UniProt) |
| Blast Gene Set | bgs | Sequences found by forward BLAST against project species |
| Candidate Gene Set | cgs | BGS sequences confirmed as homologs by reciprocal BLAST |
| All Gene Set | ags | Final combined set (rgs + cgs after filtering) |

**Filenames always use lowercase**: `rgs-`, `bgs-`, `cgs-`, `ags-`

### One Gene Family Per Directory

Each gene family is a **self-contained unit** with its own copy of both steps:

```bash
# 1. Copy the gene family template
cp -r gene_family_COPYME gene_family-innexin_pannexin

# 2. Inside, create workflow RUN copies for each step
cd gene_family-innexin_pannexin/STEP_1-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs
cd workflow-RUN_1-rbh_rbf_homologs
# Edit START_HERE-user_config.yaml, then run
```

To analyze multiple gene families, create multiple `gene_family-[name]` copies from the template.

### RGS File Format

RGS files are user-curated FASTA files with specific header and filename conventions:

**Filename**: `rgs_{category}-{species_short_names}-{gene_family_details}.aa`

**Header**: 5 dash-separated fields:
```
>rgs_{family}-{species}-{gene_symbol}-{source_details}-{sequence_identifier}
MAEIPDETIQQFM...
```

Example: `>rgs_innexins-human-PANX1-hgnc_gg305_Pannexin-NP_001229977.1`

---

## Two-Step Architecture

### STEP_1-homolog_discovery

**Directory**: `gene_family_COPYME/STEP_1-homolog_discovery/`
**Workflow template**: `workflow-COPYME-rbh_rbf_homologs`

**Function**:
- **Process 1**: Validate RGS FASTA file (fails fast if invalid)
- **Processes 2-10**: BLAST RGS against project species, reciprocal BLAST to confirm homologs, filter by species keeper list, concatenate into final AGS
- No remapping needed - BLAST v5 databases preserve full GIGANTIC identifiers

**Outputs**:
- `output_to_input/STEP_1-homolog_discovery/ags_fastas/<gene_family>/16_ai-ags-*.aa`

### STEP_2-phylogenetic_analysis

**Directory**: `gene_family_COPYME/STEP_2-phylogenetic_analysis/`
**Workflow template**: `workflow-COPYME-phylogenetic_analysis`

**Function**:
- Multiple sequence alignment (MAFFT)
- Alignment trimming (ClipKit)
- Tree building (FastTree, IQ-TREE, VeryFastTree, PhyloBayes)
- Tree visualization (human-friendly and computer-vision)

**Outputs**:
- `output_to_input/STEP_2-phylogenetic_analysis/trees/<gene_family>/*.newick, *.svg`

---

## Directory Structure

```
trees_gene_families/
├── AI_GUIDE-trees_gene_families.md    # THIS FILE
├── README.md                          # Human documentation
├── RUN-clean_and_record_subproject.sh # Cleanup + session recording
├── RUN-setup_and_submit_step1_burst.sh # Burst setup + submit for all gene families (STEP_1)
├── RUN-setup_and_submit_step2_burst.sh # Burst setup + submit for all gene families (STEP_2)
├── RUN-update_upload_to_server.sh     # Update server symlinks
│
├── research_notebook/                 # Personal workspace
├── upload_to_server/                  # Server sharing
│
├── output_to_input/                   # FINAL OUTPUTS for downstream (single location)
│   ├── STEP_1-homolog_discovery/ags_fastas/  # AGS homolog sequences by gene family
│   └── STEP_2-phylogenetic_analysis/trees/   # Phylogenetic trees by gene family
│
├── gene_family_COPYME/                # TEMPLATE (copy this for each gene family)
│   ├── STEP_1-homolog_discovery/
│   │   └── workflow-COPYME-rbh_rbf_homologs/
│   └── STEP_2-phylogenetic_analysis/
│       └── workflow-COPYME-phylogenetic_analysis/
│
└── gene_family-innexin_pannexin/      # USER COPY (example)
    ├── STEP_1-homolog_discovery/
    │   └── workflow-RUN_1-rbh_rbf_homologs/
    └── STEP_2-phylogenetic_analysis/
        └── workflow-RUN_1-phylogenetic_analysis/
```

---

## Data Flow Between Steps

```
User provides RGS FASTA + species keeper list
       │
       ▼
STEP_1: Validate RGS → BLAST → Reciprocal BLAST → Filter → AGS
       │
       ▼
output_to_input/STEP_1-homolog_discovery/ags_fastas/
       │
       ▼
STEP_2: Align → Trim → Build Trees → Visualize
       │
       ▼
output_to_input/STEP_2-phylogenetic_analysis/trees/
       │
       ▼
(Downstream subprojects or publication)
```

---

## Inter-Subproject Dependencies

### Inputs FROM

| Subproject | What | Path |
|------------|------|------|
| genomesDB | BLAST databases (per-species .aa files) | `../genomesDB-species70/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_blastp/` |
| phylonames | Species name mappings | `../phylonames/output_to_input/maps/` |

### Outputs TO

| Location | What | Consumers |
|----------|------|-----------|
| `output_to_input/STEP_1-homolog_discovery/ags_fastas/` | AGS homolog sets | Internal (STEP_2) |
| `output_to_input/STEP_2-phylogenetic_analysis/trees/` | Phylogenetic trees | Publication, downstream |

---

## Path Depth Adjustment

Gene family directories are nested TWO levels deeper than standard subprojects (gene_family_COPYME + STEP):

| Location | Relative path to project root |
|----------|-------------------------------|
| `trees_gene_families/` | `../../` |
| `trees_gene_families/gene_family_COPYME/` | `../../../` |
| `trees_gene_families/gene_family_COPYME/STEP_N-*/` | `../../../../` |
| `trees_gene_families/gene_family_COPYME/STEP_N-*/workflow-COPYME-*/` | `../../../../../` |
| `trees_gene_families/gene_family_COPYME/STEP_N-*/workflow-COPYME-*/ai/` | `../../../../../../` |

---

## Conda Environment

**Environment name**: `ai_gigantic_trees_gene_families`
**Definition file**: `../../conda_environments/ai_gigantic_trees_gene_families.yml`

**Includes**: Python, NextFlow, BLAST, MAFFT, ClipKit, FastTree, IQ-TREE, VeryFastTree, PhyloBayes-MPI, ete3

Both STEPs use this single environment.

---

## Research Notebook Location

AI sessions save to the project-wide sessions directory:
```
research_notebook/research_ai/sessions/
```

Workflow run logs save to each workflow's own `ai/logs/` directory:
```
workflow-*/ai/logs/
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "BLAST database not found" | genomesDB not run | Run genomesDB subproject first |
| "RGS file not found" | Wrong path in config | Check `rgs_file` path in config YAML |
| "RGS validation failed" | Invalid headers or filename | Fix RGS file format per the header/filename conventions above |
| "Species not in keeper list" | Species not in species_keeper_list.tsv | Add species to INPUT_user/species_keeper_list.tsv |
| "No BLAST hits" | E-value too stringent or wrong RGS | Try less stringent E-value or check RGS sequences |
| STEP_2 can't find AGS | STEP_1 not complete | Run STEP_1 first, check output_to_input/STEP_1-homolog_discovery/ags_fastas/ |
| Tree building fails | Insufficient sequences after filtering | Check species keeper list, may need more species |

### Diagnostic Commands

```bash
# Check genomesDB dependency
ls ../genomesDB-species70/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_blastp/ | head

# Check STEP_1 outputs
ls output_to_input/STEP_1-homolog_discovery/ags_fastas/

# Check STEP_2 outputs
ls output_to_input/STEP_2-phylogenetic_analysis/trees/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `gene_family_COPYME/STEP_1-*/workflow-*/START_HERE-user_config.yaml` | Gene family, BLAST settings, species DB | **YES** |
| `gene_family_COPYME/STEP_1-*/workflow-*/INPUT_user/species_keeper_list.tsv` | Species to include in final AGS | **YES** |
| `gene_family_COPYME/STEP_1-*/workflow-*/INPUT_user/rgs_species_map.tsv` | Map RGS short names to Genus_species | **YES** (if needed) |
| `gene_family_COPYME/STEP_2-*/workflow-*/START_HERE-user_config.yaml` | Tree methods, alignment settings | **YES** |
| `gene_family-*/STEP_N-*/workflow-*/RUN-workflow.sh` | Run pipeline | **YES** (SLURM settings) |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting trees_gene_families | "Have you run the genomesDB subproject? We need BLAST databases." |
| Before STEP_1 | "What gene family? Do you have a curated RGS FASTA file and species keeper list?" |
| Before STEP_2 | "Which tree method? FastTree (fast, default), IQ-TREE (publication), VeryFastTree (large datasets), or PhyloBayes (Bayesian)?" |
| Multiple gene families | "How many gene families? You'll need one gene_family-[name] directory per family." |
| Error occurred | "Which step failed? What error message?" |

---

## Next Steps After trees_gene_families

Guide users to:
1. **Publication** - Trees are ready for figures and manuscript
2. **Comparative analysis** - Cross-reference trees with annotations or orthogroups
3. **Additional gene families** - Create more RUN copies for other families
