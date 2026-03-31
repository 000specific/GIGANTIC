# AI Guide: trees_gene_groups Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. Also read the sibling `../trees_gene_families/AI_GUIDE-trees_gene_families.md` for shared concepts (gene set terminology, RBH/RBF methodology, tree building methods) - the homolog discovery and phylogenetic analysis pipelines are identical.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/`

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
| trees_gene_groups concepts, source-based structure | This file |
| HUGO HGNC-specific guidance (STEP_0, RGS naming) | `gene_groups-hugo_hgnc/AI_GUIDE-hugo_hgnc.md` |
| Homolog discovery (STEP_1) details | `gene_groups-COPYME/STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` |
| Phylogenetic analysis (STEP_2) details | `gene_groups-COPYME/STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` |
| Shared methodology (RBH/RBF, tree building) | `../trees_gene_families/AI_GUIDE-trees_gene_families.md` |

---

## What This Subproject Does

**Purpose**: Build phylogenetic trees for gene groups across GIGANTIC species. Gene groups are sets of related genes defined by external classification systems (e.g., HUGO HGNC gene groups, Pfam clans, custom gene lists).

**Relationship to trees_gene_families**: This subproject shares the **identical homolog discovery and tree building pipelines** with trees_gene_families. The difference is how Reference Gene Sets (RGS) are generated:

| Aspect | trees_gene_families | trees_gene_groups |
|--------|--------------------|--------------------|
| RGS source | Hand-curated per gene family | Generated from external classification systems |
| Scale | Typically a few families at a time | Potentially hundreds or thousands of groups |
| STEP_0 | N/A (user provides RGS manually) | Source-specific RGS generation (e.g., HGNC download) |
| Organization | One directory per gene family | Source-based hierarchy with gene groups inside |

---

## Source-Based Architecture

### Design Philosophy

Gene groups can come from many different sources (databases, classification systems, custom analyses). Each source has its own method for defining gene groups and generating RGS files. The subproject is organized by **source**, with a shared template for the downstream pipeline:

```
trees_gene_groups/
├── gene_groups-COPYME/              # Template for any new gene group source
│   ├── STEP_0-placeholder/          # Each source defines its own STEP_0
│   ├── STEP_1-homolog_discovery/    # Shared: RBH/RBF homolog finding
│   │   └── workflow-COPYME-rbh_rbf_homologs/
│   └── STEP_2-phylogenetic_analysis/# Shared: alignment + tree building
│       └── workflow-COPYME-phylogenetic_analysis/
│
├── gene_groups-hugo_hgnc/           # HUGO HGNC gene groups (first source)
│   ├── STEP_0-hgnc_gene_groups/     # Downloads HGNC data, generates RGS
│   ├── STEP_1-homolog_discovery/    # Per-gene-group homolog discovery
│   └── STEP_2-phylogenetic_analysis/# Per-gene-group tree building
│
└── gene_groups-[future_source]/     # Future: Pfam, InterPro, custom, etc.
```

### Two Levels of Templating

1. **Source level**: `gene_groups-COPYME` is copied to create a new source (e.g., `gene_groups-pfam`). The new source adds its own STEP_0 for RGS generation and inherits STEP_1 + STEP_2 pipelines.

2. **Gene group level**: Within each source, individual gene groups are processed by copying `workflow-COPYME-*` templates inside each STEP. This is automated by burst scripts.

### Adding a New Gene Group Source

```bash
# 1. Copy the source-level template
cp -r gene_groups-COPYME gene_groups-pfam

# 2. Replace STEP_0-placeholder with source-specific RGS generation
rm -r gene_groups-pfam/STEP_0-placeholder
# Create gene_groups-pfam/STEP_0-pfam_clans/ with custom pipeline

# 3. Adjust paths in STEP_1 and STEP_2 configs if needed
# 4. Create an AI_GUIDE-pfam.md with source-specific documentation
```

---

## Three-Step Pipeline (Within Each Source)

### STEP_0 - RGS Generation (Source-Specific)

Each source has its own STEP_0 that generates Reference Gene Set (RGS) FASTA files. This step runs **once** and produces RGS files for **all** gene groups in that source.

**Example (HUGO HGNC)**:
- Downloads gene group tables from genenames.org
- Builds aggregated gene symbol sets per group (including hierarchy)
- Extracts protein sequences from human T1 proteome
- Produces ~1,974 RGS FASTA files

### STEP_1 - Homolog Discovery (Shared Pipeline)

Identical to trees_gene_families STEP_1. Processes **one gene group at a time**:
- Validates RGS FASTA file
- Forward BLAST (RGS vs project species proteomes)
- Reciprocal BLAST to confirm homologs
- Filter by species keeper list
- Concatenate into final AGS (All Gene Set)

### STEP_2 - Phylogenetic Analysis (Shared Pipeline)

Identical to trees_gene_families STEP_2. Processes **one gene group at a time**:
- Multiple sequence alignment (MAFFT)
- Alignment trimming (ClipKit)
- Tree building (FastTree, IQ-TREE, VeryFastTree, PhyloBayes)
- Tree visualization (human-friendly and computer-vision)

---

## Gene Set Terminology

| Term | Abbreviation | Meaning |
|------|-------------|---------|
| Reference Gene Set | rgs | Curated sequences from model organisms |
| Blast Gene Set | bgs | Sequences found by forward BLAST against project species |
| Candidate Gene Set | cgs | BGS sequences confirmed as homologs by reciprocal BLAST |
| All Gene Set | ags | Final combined set (rgs + cgs after filtering) |

**Filenames always use lowercase**: `rgs-`, `bgs-`, `cgs-`, `ags-`

---

## Directory Structure

```
trees_gene_groups/
├── AI_GUIDE-trees_gene_groups.md         # THIS FILE
├── README.md                             # Human documentation
├── research_notebook/                    # Personal workspace
├── upload_to_server/                     # Server sharing
│
├── output_to_input/                      # FINAL OUTPUTS (step-centric, by source)
│   └── gene_groups-hugo_hgnc/
│       ├── STEP_0-hgnc_gene_groups/      # All RGS files (symlinks)
│       │   ├── rgs_fastas/
│       │   ├── 3_ai-rgs_generation_manifest.tsv
│       │   └── 3_ai-rgs_generation_summary.tsv
│       ├── STEP_1-homolog_discovery/     # Per-gene-group AGS (symlinks)
│       │   └── gene_group-gap_junction_proteins/
│       └── STEP_2-phylogenetic_analysis/ # Per-gene-group trees (symlinks)
│           └── gene_group-gap_junction_proteins/
│
├── gene_groups-COPYME/                   # SOURCE-LEVEL TEMPLATE
│   ├── STEP_0-placeholder/               # Each source replaces this
│   ├── STEP_1-homolog_discovery/         # Per-gene-group template
│   │   ├── AI_GUIDE-homolog_discovery.md
│   │   ├── README.md
│   │   └── workflow-COPYME-rbh_rbf_homologs/
│   └── STEP_2-phylogenetic_analysis/     # Per-gene-group template
│       ├── AI_GUIDE-phylogenetic_analysis.md
│       ├── README.md
│       └── workflow-COPYME-phylogenetic_analysis/
│
└── gene_groups-hugo_hgnc/                # HUGO HGNC SOURCE INSTANCE
    ├── AI_GUIDE-hugo_hgnc.md
    ├── INPUT_user/                        # Manifest for batch processing
    │   └── gene_group_manifest.tsv
    ├── STEP_0-hgnc_gene_groups/           # RGS generation (runs once)
    │   ├── workflow-COPYME-hgnc_gene_groups/
    │   └── workflow-RUN_01-hgnc_gene_groups/
    ├── STEP_1-homolog_discovery/          # Homolog discovery (per gene group)
    │   ├── AI_GUIDE-homolog_discovery.md
    │   ├── README.md
    │   ├── workflow-COPYME-rbh_rbf_homologs/
    │   ├── gene_group-gap_junction_proteins/  (created by burst script)
    │   │   └── workflow-RUN_01-rbh_rbf_homologs/
    │   └── gene_group-fascin_family/
    │       └── workflow-RUN_01-rbh_rbf_homologs/
    └── STEP_2-phylogenetic_analysis/      # Tree building (per gene group)
        ├── AI_GUIDE-phylogenetic_analysis.md
        ├── README.md
        ├── workflow-COPYME-phylogenetic_analysis/
        ├── gene_group-gap_junction_proteins/
        │   └── workflow-RUN_01-phylogenetic_analysis/
        └── gene_group-fascin_family/
            └── workflow-RUN_01-phylogenetic_analysis/
```

---

## Data Flow

```
Source database (e.g., HUGO HGNC genenames.org)
       |
       v
STEP_0: Download + generate RGS files (runs once per source)
       |
       v
output_to_input/<source>/STEP_0-*/rgs_fastas/  (all RGS files)
       |
       v  (individual RGS files fed to per-gene-group workflows)
STEP_1: Validate RGS -> BLAST -> Reciprocal BLAST -> Filter -> AGS
       |
       v
output_to_input/<source>/STEP_1-homolog_discovery/gene_group-X/
       |
       v
STEP_2: Align -> Trim -> Build Trees -> Visualize
       |
       v
output_to_input/<source>/STEP_2-phylogenetic_analysis/gene_group-X/
       |
       v
(Downstream subprojects or publication)
```

---

## Batch Processing Model

With potentially thousands of gene groups per source (e.g., ~1,974 from HGNC), manual setup is impractical. Each source provides **burst scripts** at the source level:

```bash
# Burst scripts (at the gene_groups-hugo_hgnc/ level):
gene_groups-hugo_hgnc/RUN-setup_and_submit_step1_burst.sh
gene_groups-hugo_hgnc/RUN-setup_and_submit_step2_burst.sh
```

**STEP_1 burst script** reads the STEP_0 summary TSV automatically and for each gene group:
1. Creates `gene_group-[name]/` directory inside STEP_1
2. Copies `workflow-COPYME-rbh_rbf_homologs` into it as `workflow-RUN_01-rbh_rbf_homologs`
3. Copies the RGS file, species keeper list, and species map to `INPUT_user/`
4. Updates `START_HERE-user_config.yaml` with the gene group name and RGS path
5. Submits to SLURM

**STEP_2 burst script** iterates over completed STEP_1 gene groups (those with AGS files in `output_to_input`) and for each:
1. Creates `gene_group-[name]/` directory inside STEP_2
2. Copies `workflow-COPYME-phylogenetic_analysis` into it as `workflow-RUN_01-phylogenetic_analysis`
3. Updates config with gene group name
4. Submits to SLURM

**Usage**:
```bash
# STEP_1: Set up and submit all gene groups
bash RUN-setup_and_submit_step1_burst.sh

# STEP_1: Dry run (preview what would happen)
bash RUN-setup_and_submit_step1_burst.sh --dry-run

# STEP_1: Single gene group only
bash RUN-setup_and_submit_step1_burst.sh --gene-group fascin_family

# STEP_2: Set up and submit all gene groups with completed STEP_1
bash RUN-setup_and_submit_step2_burst.sh

# Options: --dry-run, --setup-only, --submit-only, --gene-group NAME
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
| `output_to_input/<source>/STEP_0-*/rgs_fastas/` | RGS files | Internal (STEP_1) |
| `output_to_input/<source>/STEP_1-*/gene_group-*/` | AGS homolog sets | Internal (STEP_2) |
| `output_to_input/<source>/STEP_2-*/gene_group-*/` | Phylogenetic trees | Publication, downstream |

---

## Path Depth Adjustment

Workflows run from `gene_group-X/workflow-RUN_01/` which is deeply nested:

| Location | Relative path to project root |
|----------|-------------------------------|
| `trees_gene_groups/` | `../../` |
| `trees_gene_groups/gene_groups-hugo_hgnc/` | `../../../` |
| `.../STEP_N-*/` | `../../../../` |
| `.../STEP_N-*/workflow-COPYME-*/` | `../../../../../` |
| `.../STEP_N-*/gene_group-X/workflow-RUN_01/` | `../../../../../../` |
| `.../STEP_N-*/gene_group-X/workflow-RUN_01/ai/` | `../../../../../../../` |

**Note**: The workflow-COPYME templates have paths set for the **running depth** (gene_group-X/workflow-RUN_01), which is one level deeper than the COPYME location itself. This means paths don't resolve from the COPYME location, which is intentional - COPYME should never be run directly.

---

## Conda Environment

**Environment name**: `ai_gigantic_trees_gene_families` (shared with trees_gene_families)
**Definition file**: `../../conda_environments/ai_gigantic_trees_gene_families.yml`

**Includes**: Python, NextFlow, BLAST, MAFFT, ClipKit, FastTree, IQ-TREE, VeryFastTree, PhyloBayes-MPI, ete3

All STEPs across all sources use this single environment.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "BLAST database not found" | genomesDB not run | Run genomesDB subproject first |
| "RGS file not found" | Wrong path in config | Check `rgs_file` path in START_HERE-user_config.yaml |
| "Species not in keeper list" | Species not in species_keeper_list.tsv | Add species to INPUT_user/species_keeper_list.tsv |
| "No BLAST hits" | E-value too stringent or wrong RGS | Try less stringent E-value or check RGS sequences |
| STEP_2 can't find AGS | STEP_1 not complete | Run STEP_1 first, check output_to_input |
| Tree building fails | Insufficient sequences after filtering | Check species keeper list, may need more species |
| Symlinks broken after move | Directory restructuring | Re-run STEP_0 RUN-workflow.sh to recreate symlinks |

### Diagnostic Commands

```bash
# Check genomesDB dependency
ls ../genomesDB-species70/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_blastp/ | head

# Check STEP_0 outputs (HGNC)
ls output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/rgs_fastas/ | wc -l

# Check STEP_1 outputs for a specific gene group
ls output_to_input/gene_groups-hugo_hgnc/STEP_1-homolog_discovery/gene_group-*/

# Check STEP_2 outputs for a specific gene group
ls output_to_input/gene_groups-hugo_hgnc/STEP_2-phylogenetic_analysis/gene_group-*/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `gene_groups-COPYME/` | Source-level template | No (copy it) |
| `gene_groups-hugo_hgnc/AI_GUIDE-hugo_hgnc.md` | HGNC-specific AI guidance | Read only |
| `gene_groups-hugo_hgnc/STEP_0-*/workflow-*/START_HERE-user_config.yaml` | Human proteome path | **YES** |
| `gene_groups-hugo_hgnc/STEP_1-*/workflow-*/START_HERE-user_config.yaml` | Gene group, BLAST settings | **YES** |
| `gene_groups-hugo_hgnc/STEP_1-*/workflow-*/INPUT_user/species_keeper_list.tsv` | Species to include | **YES** |
| `gene_groups-hugo_hgnc/STEP_2-*/workflow-*/START_HERE-user_config.yaml` | Tree methods, alignment | **YES** |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting trees_gene_groups | "Have you run the genomesDB subproject? We need BLAST databases." |
| Which source | "Where do your gene groups come from? HGNC? Pfam? Custom list?" |
| Before STEP_0 | "Do you need to regenerate RGS files, or use existing ones?" |
| Before STEP_1 | "Which gene groups? All ~1,974 HGNC groups, or a specific subset?" |
| Before STEP_2 | "Which tree method? FastTree (fast, default), IQ-TREE (publication), VeryFastTree (large), PhyloBayes (Bayesian)?" |
| Scale concerns | "How many gene groups? For large batches, we'll use burst scripts with manifests." |

---

## Current Sources

| Source | Directory | STEP_0 | Gene Groups | Status |
|--------|-----------|--------|-------------|--------|
| HUGO HGNC | `gene_groups-hugo_hgnc/` | Downloads from genenames.org | ~1,974 protein-coding gene groups | STEP_0 complete, STEP_1 submitted (all 1,974), STEP_2 burst script ready |

---

## Next Steps After trees_gene_groups

Guide users to:
1. **Publication** - Trees are ready for figures and manuscript
2. **Comparative analysis** - Cross-reference trees with annotations or orthogroups
3. **Additional sources** - Copy gene_groups-COPYME for new gene group sources (Pfam, custom)
4. **Batch analysis** - Use burst scripts for processing many gene groups
