# AI Guide: trees_gene_families Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers trees_gene_families-specific concepts and the three-step architecture.

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
| trees_gene_families concepts, three-step structure | This file |
| STEP_1 RGS preparation | `STEP_1-rgs_preparation/AI_GUIDE-rgs_preparation.md` |
| STEP_2 homolog discovery | `STEP_2-homolog_discovery/AI_GUIDE-homolog_discovery.md` |
| STEP_3 phylogenetic analysis | `STEP_3-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` |

---

## What This Subproject Does

**Purpose**: Build phylogenetic trees for individual gene families across GIGANTIC species.

**Three-Step Pipeline**:
1. **RGS Preparation** - Validate Reference Gene Set (RGS) FASTA files
2. **Homolog Discovery** - Find homologs via Reciprocal Best Hit / Reciprocal Best Family (RBH/RBF)
3. **Phylogenetic Analysis** - Align sequences, trim, build trees, visualize

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

### One Gene Family Per Run

Each workflow copy processes **one gene family at a time**:

```bash
# Example: Processing innexin/pannexin gene family
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
cd workflow-RUN_01-rbh_rbf_homologs
# Edit config with gene family name, then run
```

To process multiple gene families, create multiple RUN copies.

### RGS File Format

RGS files are user-curated FASTA files with specific header conventions:

```
>rgsN-species-source-identifier
MAEIPDETIQQFM...
```

Where N is the total sequence count in the file.

---

## Three-Step Architecture

### STEP_1-rgs_preparation

**Directory**: `STEP_1-rgs_preparation/`
**Workflow template**: `workflow-COPYME-validate_rgs`
**Run scripts**: `RUN-workflow.sh` (local), `RUN-workflow.sbatch` (SLURM)

**Function**:
- Validate RGS FASTA file format (headers, sequences)
- Check for duplicates and formatting issues
- Copy validated RGS to output_to_input

**Outputs**:
- `STEP_1-rgs_preparation/output_to_input/rgs_fastas/<gene_family>/rgs-<gene_family>.aa`

### STEP_2-homolog_discovery

**Directory**: `STEP_2-homolog_discovery/`
**Workflow template**: `workflow-COPYME-rbh_rbf_homologs`
**Run scripts**: `RUN-workflow.sh` (local), `RUN-workflow.sbatch` (SLURM)

**Function**:
- BLAST RGS against all project species (forward search)
- Extract blast gene sequences (BGS)
- Build reciprocal BLAST databases
- Reciprocal BLAST to confirm homologs --> candidate gene set (CGS)
- Filter by species keeper list
- Remap identifiers to GIGANTIC phylonames
- Concatenate into final AGS

**Outputs**:
- `STEP_2-homolog_discovery/output_to_input/ags_fastas/<gene_family>/16_ai-ags-*.aa`

### STEP_3-phylogenetic_analysis

**Directory**: `STEP_3-phylogenetic_analysis/`
**Workflow template**: `workflow-COPYME-phylogenetic_analysis`
**Run scripts**: `RUN-workflow.sh` (local), `RUN-workflow.sbatch` (SLURM)

**Function**:
- Multiple sequence alignment (MAFFT)
- Alignment trimming (ClipKit)
- Tree building (FastTree, IQ-TREE, VeryFastTree, PhyloBayes)
- Tree visualization (human-friendly and computer-vision)

**Outputs**:
- `STEP_3-phylogenetic_analysis/output_to_input/trees/<gene_family>/*.newick, *.svg`

---

## Directory Structure

```
trees_gene_families/
├── AI_GUIDE-trees_gene_families.md    # THIS FILE
├── README.md                          # Human documentation
├── RUN-clean_and_record_subproject.sh # Cleanup + session recording
├── RUN-update_upload_to_server.sh     # Update server symlinks
│
├── user_research/                     # Personal workspace
├── upload_to_server/                  # Server sharing
│
├── output_to_input/                   # FINAL OUTPUTS for downstream
│   ├── step_1/rgs_fastas/             # Validated RGS by gene family
│   ├── step_2/ags_fastas/             # AGS homolog sequences by gene family
│   └── step_3/trees/                  # Phylogenetic trees by gene family
│
├── STEP_1-rgs_preparation/
│   ├── AI_GUIDE-rgs_preparation.md
│   ├── README.md
│   ├── output_to_input/rgs_fastas/
│   └── workflow-COPYME-validate_rgs/
│
├── STEP_2-homolog_discovery/
│   ├── AI_GUIDE-homolog_discovery.md
│   ├── README.md
│   ├── output_to_input/ags_fastas/
│   └── workflow-COPYME-rbh_rbf_homologs/
│
└── STEP_3-phylogenetic_analysis/
    ├── AI_GUIDE-phylogenetic_analysis.md
    ├── README.md
    ├── output_to_input/trees/
    └── workflow-COPYME-phylogenetic_analysis/
```

---

## Data Flow Between Steps

```
User provides RGS FASTA + species keeper list
       │
       ▼
STEP_1-rgs_preparation/output_to_input/rgs_fastas/
       │ (optional - user can also provide RGS directly to STEP_2)
       ▼
STEP_2-homolog_discovery/output_to_input/ags_fastas/
       │
       ▼
STEP_3-phylogenetic_analysis/output_to_input/trees/
       │
       ▼
trees_gene_families/output_to_input/step_3/trees/
       │
       ▼
(Downstream subprojects or publication)
```

**Note**: STEP_2 can accept RGS files directly from INPUT_user/ without running STEP_1. STEP_1 is recommended but not required.

---

## Inter-Subproject Dependencies

### Inputs FROM

| Subproject | What | Path |
|------------|------|------|
| genomesDB | BLAST databases (per-species .aa files) | `../genomesDB/output_to_input/gigantic_T1_blastp/` |
| genomesDB | Header mapping file (short → full IDs) | `../genomesDB/output_to_input/gigantic_T1_blastp_header_map` |
| phylonames | Species name mappings | `../phylonames/output_to_input/maps/` |

### Outputs TO

| Location | What | Consumers |
|----------|------|-----------|
| `output_to_input/step_1/rgs_fastas/` | Validated RGS files | Internal (STEP_2) |
| `output_to_input/step_2/ags_fastas/` | AGS homolog sets | Internal (STEP_3) |
| `output_to_input/step_3/trees/` | Phylogenetic trees | Publication, downstream |

---

## Path Depth Adjustment

Step directories are nested ONE level deeper than standard subprojects:

| Location | Relative path to project root |
|----------|-------------------------------|
| `trees_gene_families/` | `../../` |
| `trees_gene_families/STEP_N-*/` | `../../../` |
| `trees_gene_families/STEP_N-*/workflow-COPYME-*/` | `../../../../` |
| `trees_gene_families/STEP_N-*/workflow-COPYME-*/ai/` | `../../../../../` |

---

## Conda Environment

**Environment name**: `ai_gigantic_trees_gene_families`
**Definition file**: `../../conda_environments/ai_gigantic_trees_gene_families.yml`

**Includes**: Python, NextFlow, BLAST, MAFFT, ClipKit, FastTree, IQ-TREE, VeryFastTree, PhyloBayes-MPI, ete3

All three STEPs use this single environment.

---

## Research Notebook Location

All trees_gene_families AI sessions save to:
```
research_notebook/research_ai/subproject-trees_gene_families/
├── logs/
└── sessions/
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "BLAST database not found" | genomesDB not run | Run genomesDB subproject first |
| "RGS file not found" | Wrong path in config | Check `rgs_file` path in config YAML |
| "Species not in keeper list" | Species not in species_keeper_list.tsv | Add species to INPUT_user/species_keeper_list.tsv |
| "No BLAST hits" | E-value too stringent or wrong RGS | Try less stringent E-value or check RGS sequences |
| STEP_3 can't find AGS | STEP_2 not complete | Run STEP_2 first, check output_to_input/ags_fastas/ |
| Tree building fails | Insufficient sequences after filtering | Check species keeper list, may need more species |
| "Header mapping not found" | genomesDB header map missing | Check genomesDB/output_to_input/gigantic_T1_blastp_header_map |

### Diagnostic Commands

```bash
# Check genomesDB dependency
ls ../genomesDB/output_to_input/gigantic_T1_blastp/ | head

# Check STEP_1 outputs
ls STEP_1-rgs_preparation/output_to_input/rgs_fastas/

# Check STEP_2 outputs
ls STEP_2-homolog_discovery/output_to_input/ags_fastas/

# Check STEP_3 outputs
ls STEP_3-phylogenetic_analysis/output_to_input/trees/

# Check subproject-level outputs
ls output_to_input/step_1/rgs_fastas/
ls output_to_input/step_2/ags_fastas/
ls output_to_input/step_3/trees/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `STEP_1-*/workflow-*/rgs_config.yaml` | Gene family name, RGS file path | **YES** |
| `STEP_2-*/workflow-*/rbh_rbf_homologs_config.yaml` | Gene family, BLAST settings, species DB | **YES** |
| `STEP_2-*/workflow-*/INPUT_user/species_keeper_list.tsv` | Species to include in final AGS | **YES** |
| `STEP_2-*/workflow-*/INPUT_user/rgs_species_map.tsv` | Map RGS short names to Genus_species | **YES** (if needed) |
| `STEP_3-*/workflow-*/phylogenetic_analysis_config.yaml` | Tree methods, alignment settings | **YES** |
| `RUN-*.sbatch` files | SLURM account/qos | **YES** (SLURM users) |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting trees_gene_families | "Have you run the genomesDB subproject? We need BLAST databases." |
| Before STEP_1 | "What gene family? Do you have a curated RGS FASTA file?" |
| Before STEP_2 | "Which species should be included? Do you have a species keeper list?" |
| Before STEP_3 | "Which tree method? FastTree (fast, default), IQ-TREE (publication), VeryFastTree (large datasets), or PhyloBayes (Bayesian)?" |
| Multiple gene families | "How many gene families? You'll need one workflow copy per family." |
| Error occurred | "Which step failed? What error message?" |

---

## Next Steps After trees_gene_families

Guide users to:
1. **Publication** - Trees are ready for figures and manuscript
2. **Comparative analysis** - Cross-reference trees with annotations or orthogroups
3. **Additional gene families** - Create more RUN copies for other families
