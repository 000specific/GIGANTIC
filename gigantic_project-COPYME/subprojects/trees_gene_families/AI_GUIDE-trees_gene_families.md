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
| trees_gene_families concepts, pipeline architecture | This file |
| RGS preparation, naming conventions | `research_notebook/README.md` |
| STEP_1 homolog discovery | `gene_family_COPYME/STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` |
| STEP_2 phylogenetic analysis | `gene_family_COPYME/STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` |
| STEP_3 tree visualization | `gene_family_COPYME/STEP_3-tree_visualization/AI_GUIDE-phylogenetic_visualization.md` |

---

## What This Subproject Does

**Purpose**: Build phylogenetic trees for individual gene families across GIGANTIC species.

**Current scale (sono project)**: 8 mechanosensitive channel gene families for Salk sonogenetics collaboration.

**The 8 Gene Families**:

| Gene Family | RGS Mode | RGS Seeds | Description |
|-------------|----------|-----------|-------------|
| acid_sensing_ion_channel_subunits | full-length | HGNC human | ASIC channels |
| piezo_type_mechanosensitive_ion_channel_components | full-length | HGNC human | Piezo mechanosensors |
| potassium_two_pore_domain_channel_subfamily_k | full-length | HGNC human | KCNK channels |
| solute_carrier_family_26 | full-length | HGNC human | SLC26 / Prestin family |
| stomatin_family | full-length | HGNC human | Stomatin scaffold proteins |
| tmem63_osca_flyc1_mechanosensitive | full-length | HGNC human + venus flytrap | TMEM63/OSCA/FLYC1 |
| transmembrane_channel_like_family | full-length | HGNC human | TMC channels |
| transient_receptor_potential_cation_channels | **subsequence** | multi-species pore regions | TRP channels (pore-region RGS) |

**Four-Phase Workflow**:
1. **RGS Preparation** - Source, curate, and format reference gene sequences in `research_notebook/`
2. **Homolog Discovery (STEP_1)** - Validate RGS, then find homologs via Reciprocal Best Hit / Reciprocal Best Family (RBH/RBF)
3. **Phylogenetic Analysis (STEP_2)** - Align sequences, trim, build tree newick files (FastTree, IQ-TREE, VeryFastTree, PhyloBayes)
4. **Tree Visualization (STEP_3)** - Render newick files as PDF + SVG using toytree (decoupled from STEP_2)

**Note**: RGS validation is built into STEP_1 as its first process. If validation fails, the pipeline stops immediately before expensive BLAST runs.

**STEP_2 / STEP_3 decoupling rationale** (important):
- STEP_2's scientific artifact is the newick tree file
- STEP_3 is PDF/SVG rendering and is explicitly **soft-fail**: a render failure writes a placeholder and exits 0, never invalidating STEP_2 trees
- toytree + toyplot + reportlab (pure Python) replaces ete3/PyQt5, which has perennial install issues on conda-forge
- Visualization iteration (seconds per render) is orders of magnitude faster than tree rebuilding (days for IQ-TREE), so keeping them separate enables quick figure iteration

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

Each gene family is a **self-contained unit** with its own copy of all three steps:

```bash
# 1. Copy the gene family template
cp -r gene_family_COPYME gene_family-innexin_pannexin

# 2. Inside, create workflow RUN copies for each step
cd gene_family-innexin_pannexin/STEP_1-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs
cd workflow-RUN_1-rbh_rbf_homologs
# Edit START_HERE-user_config.yaml, then run
# Repeat for STEP_2 and STEP_3
```

To analyze multiple gene families, create multiple `gene_family-[name]` copies from the template.

### RGS File Format

RGS files are user-curated FASTA files with specific header and filename conventions. Within each dash-separated field, **only letters, numbers, and underscores** are allowed (no dots, dashes, or special characters).

**Filename**: `rgs_<category>-<source_species>-<description>.aa`

| Component | Description | Examples |
|-----------|-------------|----------|
| category | Functional category | `channel`, `receptor`, `enzyme`, `ligand`, `tf`, `transporter`, `structure` |
| source_species | Species in the RGS | `human`, `human_fly_worm`, `human_mouse_fly_worm_anemone` |
| description | Full descriptive name | `kinases_AGC`, `transient_receptor_potential_cation_channels` |

**Header**: `>rgs_<family_subfamily>-<species>-<gene>-<source>-<accession>`

| Field | Description | Examples |
|-------|-------------|----------|
| family_subfamily | Family with optional hierarchy | `kinases_AGC_Akt`, `transient_receptor_potential_cation_TRPML` |
| species | Source organism | `human`, `fly`, `worm` |
| gene | Gene symbol | `AKT1`, `MCLN1`, `GRM1` |
| source | Database source | `uniprot`, `kinase_database`, `hgnc`, `phosphatome_database` |
| accession | Sequence ID | `Q9GZU1`, `Hs_AKT1_AA`, `NP_000830_2` |

**Examples**:
```
>rgs_kinases_AGC_Akt-human-AKT1-kinase_database-Hs_AKT1_AA
>rgs_transient_receptor_potential_cation_TRPML-human-TRPML_TRPML_MCLN1-uniprot-Q9GZU1
>rgs_phosphatases_AP_AP_AP_AP-human-ALPI-phosphatome_database-Hsap_ALPI
```

### Two RGS Modes: Full-Length vs Subsequence

STEP_1 supports two modes for RGS sequences, controlled by three config fields in `START_HERE-user_config.yaml`:

```yaml
gene_family:
  rgs_full_length_file: "INPUT_user/rgs_channel-human-family_name.aa"   # ALWAYS required
  rgs_sequence_is_full_length: true                                      # true (default) or false
  rgs_subsequence_file: "INPUT_user/rgs_channel-species-family_subsequence.aa"  # Required when false
```

**Full-length mode** ( `rgs_sequence_is_full_length: true`, default, 7 of 8 families ):
- Pipeline uses `rgs_full_length_file` for BLAST discovery
- Script 018 does NOT run
- Standard flow: BLAST with full-length RGS, reciprocal BLAST with full-length BGS

**Subsequence mode** ( `rgs_sequence_is_full_length: false`, TRP channels ):
- Pipeline uses `rgs_subsequence_file` for BLAST discovery (e.g., pore-region-only sequences)
- Reciprocal BLAST uses hit-region subsequences instead of full-length BGS (prevents length mismatch bias)
- Script 018 runs after Script 016: swaps subsequence RGS in the AGS with full-length versions from `rgs_full_length_file`
- The restored full-length AGS goes to `18-output/` and is copied back to `16-output/` for STEP_2

**Why subsequence mode exists**: Full-length TRP channel sequences contain ankyrin repeats and other conserved domains that dominate BLAST results, pulling in thousands of unrelated proteins. Using pore-region-only sequences as RGS seeds finds true TRP homologs cleanly, then full-length sequences are restored for phylogenetic analysis.

**Subsequence RGS header convention**: Headers in the subsequence file must match the full-length file exactly, with `_subsequence` appended:
```
Full-length:   >rgs_channel-human-TRPV1-uniprot-Q8NER1
Subsequence:   >rgs_channel-human-TRPV1-uniprot-Q8NER1_subsequence
```

### RGS Preparation (research_notebook)

RGS files are sourced, curated, and reformatted in `research_notebook/rgs_from_before/`. The flow:

1. **Raw sources** in `rgs_sources/` - varied legacy formats from HGNC, UniProt, kinase/phosphatome databases
2. **Conversion scripts** in `rgs_for_trees/new_rgs_*/` - reformat to GIGANTIC standard, produce mapping TSVs
3. **Formatted RGS files** ready for pipeline input
4. **Burst setup scripts** at subproject root - automate gene_family directory creation and SLURM submission

Each conversion batch includes `mapping-*.tsv` files mapping original headers to new GIGANTIC headers for traceability.

See `research_notebook/README.md` for full specification.

---

## Three-Step Architecture

### STEP_1-homolog_discovery

**Directory**: `gene_family_COPYME/STEP_1-homolog_discovery/`
**Workflow template**: `workflow-COPYME-rbh_rbf_homologs`

**Function**:
- **Process 1**: Validate RGS FASTA file (fails fast if invalid)
- **Processes 2-10**: BLAST RGS against project species, reciprocal BLAST to confirm homologs, filter by species keeper list, concatenate into final AGS
- **Process 10b** (conditional): Script 018 restores full-length RGS sequences in the AGS when using subsequence mode ( `rgs_sequence_is_full_length: false` )
- No remapping needed - BLAST v5 databases preserve full GIGANTIC identifiers

**Outputs**:
- `output_to_input/<gene_family>/STEP_1-homolog_discovery/` (symlinks to workflow OUTPUT_pipeline/)

### STEP_2-phylogenetic_analysis

**Directory**: `gene_family_COPYME/STEP_2-phylogenetic_analysis/`
**Workflow template**: `workflow-COPYME-phylogenetic_analysis`

**Function**:
- Multiple sequence alignment (MAFFT)
- Alignment trimming (ClipKit)
- Tree building (FastTree, IQ-TREE, VeryFastTree, PhyloBayes) — produces newick files

**Outputs**:
- `output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/` — symlinks to alignment + tree newick files in workflow OUTPUT_pipeline/
- Visualization is handled separately by STEP_3

### STEP_3-tree_visualization

**Directory**: `gene_family_COPYME/STEP_3-tree_visualization/`
**Workflow template**: `workflow-COPYME-tree_visualization`

**Function**:
- Auto-discover tree newick files produced by STEP_2
- Render each to PDF + SVG using `toytree` (pure Python, no Qt dependency)
- Species color-coding, branch support overlays, auto-hidden tip labels for very large trees
- **Soft-fail**: render failures write a placeholder and exit 0; STEP_2 newicks remain the valid artifact

**Engine**: `toytree` + `toyplot` + `reportlab` (pip-installed in conda env `aiG-trees_gene_families-visualization`). Replaces ete3/PyQt5, which had recurring install-instability problems on conda-forge.

**Orchestration**: Plain bash in `RUN-workflow.sh` (no NextFlow) — STEP_3 is a single lightweight process. Includes broken-env self-heal: if the conda env directory exists but is missing Python, it's rebuilt.

**Outputs**:
- `output_to_input/<gene_family>/STEP_3-tree_visualization/` (symlinks to rendered PDFs/SVGs in workflow OUTPUT_pipeline/)

---

## Directory Structure

```
trees_gene_families/
├── AI_GUIDE-trees_gene_families.md    # THIS FILE
├── README.md                          # Human documentation
├── RUN-clean_and_record_subproject.sh # Cleanup + session recording
├── RUN-setup_and_submit_step1_burst.sh                # Burst: STEP_1 for original RGS set
├── RUN-setup_and_submit_step2_burst.sh                # Burst: STEP_2 with size filter
├── RUN-setup_and_submit_new_rgs_31mar2026_burst.sh    # Burst: STEP_1 for new RGS set
├── RUN-setup_and_submit_sono_mechanosensitive_burst.sh # Burst: STEP_1 for 8 sono gene families
├── RUN-clean_and_record_subproject.sh                 # Cleanup + AI session recording
├── RUN-update_upload_to_server.sh                     # Update server symlinks
│
├── research_notebook/                 # RGS preparation + personal workspace
│   └── rgs_from_before/              # RGS sources and formatted files
│       ├── rgs_sources/              # Raw/legacy RGS files
│       └── rgs_for_trees/            # GIGANTIC-formatted RGS files
│           ├── new_rgs_25mar2026/    # Batch: channel subfamilies
│           └── new_rgs_31mar2026/    # Batch: TRP, kinome, phosphatome, etc.
├── upload_to_server/                  # Server sharing
│
├── output_to_input/                   # FINAL OUTPUTS for downstream (gene family first)
│   └── <gene_family>/                # One directory per gene family
│       ├── STEP_1-homolog_discovery/      # Symlinks to AGS homolog sequences
│       ├── STEP_2-phylogenetic_analysis/  # Symlinks to tree newick files + alignments
│       └── STEP_3-tree_visualization/     # Symlinks to PDF + SVG renderings
│
├── gene_family_COPYME/                # TEMPLATE (copy this for each gene family)
│   ├── STEP_1-homolog_discovery/
│   │   └── workflow-COPYME-rbh_rbf_homologs/
│   ├── STEP_2-phylogenetic_analysis/
│   │   └── workflow-COPYME-phylogenetic_analysis/
│   └── STEP_3-tree_visualization/
│       └── workflow-COPYME-tree_visualization/
│
└── gene_family-innexin_pannexin/      # USER COPY (example)
    ├── STEP_1-homolog_discovery/
    │   └── workflow-RUN_1-rbh_rbf_homologs/
    ├── STEP_2-phylogenetic_analysis/
    │   └── workflow-RUN_1-phylogenetic_analysis/
    └── STEP_3-tree_visualization/
        └── workflow-RUN_1-tree_visualization/
```

---

## Data Flow: Full Pipeline

```
research_notebook/rgs_sources/         Raw/legacy RGS files from databases
       │
       ▼
research_notebook/rgs_for_trees/       Format to GIGANTIC standard (conversion scripts + mapping TSVs)
       │
       ▼
RUN-setup_and_submit_*_burst.sh        Automate: create gene_family dirs, populate inputs, submit SLURM
       │
       ▼
gene_family-*/STEP_1/workflow-RUN_1/   INPUT_user/ populated with RGS + species keeper list
       │
       ▼
STEP_1: Validate RGS → BLAST → Reciprocal BLAST → Filter → AGS [→ Restore full-length RGS if subsequence mode]
       │
       ▼
output_to_input/<gene_family>/STEP_1-homolog_discovery/
       │
       ▼
STEP_2: Align → Trim → Build Trees (produces newick files)
       │
       ▼
output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/
       │
       ▼
STEP_3: Render trees → PDF + SVG (toytree; soft-fail)
       │
       ▼
output_to_input/<gene_family>/STEP_3-tree_visualization/
       │
       ▼
(Downstream subprojects, server publishing, or publication)
```

---

## Inter-Subproject Dependencies

### Inputs FROM

| Subproject | What | Path |
|------------|------|------|
| genomesDB | BLAST databases (per-species .aa files) | `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/` |
| phylonames | Species name mappings | `../phylonames/output_to_input/maps/` |

### Outputs TO

| Location | What | Consumers |
|----------|------|-----------|
| `output_to_input/<gene_family>/STEP_1-homolog_discovery/` | AGS homolog sets | Internal (STEP_2) |
| `output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/` | Phylogenetic trees | Publication, downstream |

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

## Conda Environments

Two environments are used across the three steps:

**STEP_1 + STEP_2** — `ai_gigantic_trees_gene_families`
- Definition file: `../../conda_environments/ai_gigantic_trees_gene_families.yml`
- Includes: Python, NextFlow, BLAST, MAFFT, ClipKit, FastTree, IQ-TREE, VeryFastTree, PhyloBayes-MPI

**STEP_3** — `aiG-trees_gene_families-visualization`
- Definition file: `gene_family_COPYME/STEP_3-tree_visualization/workflow-COPYME-tree_visualization/ai/conda_environment.yml`
- Created on-demand by STEP_3's RUN-workflow.sh (self-heals if broken)
- Includes: Python, PyYAML, toytree, toyplot, reportlab (all pip-installed)
- No ete3 / PyQt5 — removes a major source of install instability

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
| STEP_2 can't find AGS | STEP_1 not complete | Run STEP_1 first, check output_to_input/<gene_family>/STEP_1-homolog_discovery/ |
| Tree building fails | Insufficient sequences after filtering | Check species keeper list, may need more species |

### Diagnostic Commands

```bash
# Check genomesDB dependency
ls ../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/ | head

# Check STEP_1 outputs (gene family first, then step)
ls output_to_input/*/STEP_1-homolog_discovery/

# Check STEP_2 outputs
ls output_to_input/*/STEP_2-phylogenetic_analysis/

# Check STEP_3 outputs (rendered PDFs/SVGs)
ls output_to_input/*/STEP_3-tree_visualization/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `research_notebook/rgs_from_before/rgs_for_trees/` | Formatted RGS FASTA files | **YES** (source data) |
| `RUN-setup_and_submit_step1_burst.sh` | Burst setup + submit STEP_1 (original RGS) | **YES** (SLURM settings) |
| `RUN-setup_and_submit_new_rgs_31mar2026_burst.sh` | Burst setup + submit STEP_1 (new RGS) | **YES** (SLURM settings, RGS path) |
| `RUN-setup_and_submit_sono_mechanosensitive_burst.sh` | Burst setup + submit STEP_1 (8 sono families) | **YES** (SLURM settings) |
| `RUN-setup_and_submit_step2_burst.sh` | Burst setup + submit STEP_2 (with size filter) | **YES** (SLURM settings, MAX_SEQS) |
| `gene_family_COPYME/STEP_1-*/workflow-*/START_HERE-user_config.yaml` | Gene family, BLAST settings, species DB, RGS mode | **YES** |
| `gene_family_COPYME/STEP_1-*/workflow-*/INPUT_user/species_keeper_list.tsv` | Species to include in final AGS | **YES** |
| `gene_family_COPYME/STEP_1-*/workflow-*/INPUT_user/rgs_species_map.tsv` | Map RGS short names to Genus_species | **YES** (if needed) |
| `gene_family_COPYME/STEP_2-*/workflow-*/START_HERE-user_config.yaml` | Tree methods, alignment settings | **YES** |
| `gene_family_COPYME/STEP_3-*/workflow-*/START_HERE-user_config.yaml` | Visualization styling (tip colors, branch support, canvas size) | **YES** (gene_family name; styling optional) |
| `gene_family-*/STEP_N-*/workflow-*/RUN-workflow.sh` | Run pipeline | No (reads from config) |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting trees_gene_families | "Have you run the genomesDB subproject? We need BLAST databases." |
| New gene families to add | "Do you have RGS FASTA files? Are they in GIGANTIC format (only letters/numbers/underscores within fields)? Do they need reformatting?" |
| Before STEP_1 | "What gene family? Do you have a curated RGS FASTA file and species keeper list?" |
| Before STEP_2 | "Which tree method? FastTree (fast, default), IQ-TREE (publication), VeryFastTree (large datasets), or PhyloBayes (Bayesian)?" |
| Before STEP_3 | "Has STEP_2 completed for this gene family? Which tree methods ran? Any styling preferences (hide labels for very large trees, show branch support)?" |
| Multiple gene families | "How many gene families? You'll need one gene_family-[name] directory per family." |
| Error occurred | "Which step failed? What error message?" |

---

## Next Steps After trees_gene_families

Guide users to:
1. **Publication** - Trees are ready for figures and manuscript
2. **Comparative analysis** - Cross-reference trees with annotations or orthogroups
3. **Additional gene families** - Create more RUN copies for other families
