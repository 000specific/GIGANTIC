# AI Guide: STEP_2-phylogenetic_analysis (trees_gene_families)

**For AI Assistants**: This guide covers STEP_2 of the trees_gene_families subproject. For subproject overview, see `../AI_GUIDE-trees_gene_families.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_families/STEP_2-phylogenetic_analysis/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| trees_gene_families concepts | `../AI_GUIDE-trees_gene_families.md` |
| STEP_2 phylogenetic analysis concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-phylogenetic_analysis_workflow.md` |

---

## What This Step Does

**Purpose**: Build phylogenetic trees from the AGS (All Gene Set) produced by STEP_1.

**Process**:
1. Stage AGS sequences from STEP_1 output
2. Clean sequences (remove special characters)
3. Multiple sequence alignment (MAFFT)
4. Alignment trimming (ClipKit)
5. Tree building (one or more methods)
6. Write run log
7. Export to subproject-root output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/

**Visualization** (PDF/SVG rendering) is the separate **STEP_3-tree_visualization** workflow. STEP_2 produces the scientific artifact (tree newick files); STEP_3 renders them. This decoupling keeps STEP_2 robust against visualization library quirks (ete3/PyQt5 instability).

---

## Tree Methods

Four methods available, configurable in `START_HERE-user_config.yaml`:

| Method | Script | Default | Speed | Best For |
|--------|--------|---------|-------|----------|
| **FastTree** | 005_a | ON | Minutes | Default analysis, good ML approximation |
| **IQ-TREE** | 005_b | OFF | Hours-days | Publication-quality, automatic model selection |
| **VeryFastTree** | 005_c | OFF | Very fast | Large datasets (>10,000 sequences) |
| **PhyloBayes** | 005_d | OFF | Days-weeks | Bayesian analysis, site-heterogeneous models |

### When to Use Each

- **FastTree**: Always run this. Good quality, fast results. Default choice.
- **IQ-TREE**: For publication. Runs ModelFinder for optimal substitution model. Supports ultrafast bootstrap.
- **VeryFastTree**: Drop-in FastTree replacement with multi-threading. Use when FastTree is too slow.
- **PhyloBayes**: Bayesian MCMC. Provides posterior probabilities instead of bootstrap. Uses CAT-GTR model for site-heterogeneous evolution. Very slow but provides different perspective than ML.

---

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| AGS FASTA | `../../output_to_input/<gene_family>/STEP_1-homolog_discovery/` | From STEP_1 |

**Note**: The workflow automatically finds the AGS file in the subproject-root output_to_input/<gene_family>/STEP_1-homolog_discovery/ directory. Uses `find -L` to follow symlinks.

---

## Outputs

### Pipeline Outputs

```
OUTPUT_pipeline/
├── 1-output/       # Staged AGS sequences
├── 2-output/       # Cleaned sequences
├── 3-output/       # MAFFT alignment
├── 4-output/       # ClipKit trimmed alignment
├── 5_a-output/     # FastTree tree (if enabled)
├── 5_b-output/     # IQ-TREE tree (if enabled)
├── 5_c-output/     # VeryFastTree tree (if enabled)
└── 5_d-output/     # PhyloBayes tree (if enabled)
```

Tree newick files are symlinked into `output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/` for downstream consumption (STEP_3 visualization, etc.).

### output_to_input

Trees and alignments exported to the subproject-root output_to_input/:

| Level | Path |
|-------|------|
| Subproject-root | `../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/` (symlinks to OUTPUT_pipeline/) |

---

## Directory Structure

```
STEP_2-phylogenetic_analysis/
├── AI_GUIDE-phylogenetic_analysis.md   # THIS FILE
├── README.md
└── workflow-COPYME-phylogenetic_analysis/
# Note: output symlinked to ../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/
    ├── README.md
    ├── RUN-workflow.sh
    ├── START_HERE-user_config.yaml
    ├── INPUT_user/
    ├── OUTPUT_pipeline/
    └── ai/
        ├── AI_GUIDE-phylogenetic_analysis_workflow.md
        ├── main.nf
        ├── nextflow.config
        └── scripts/
            ├── 001_ai-bash-prepare_alignment_input.sh
            ├── 002_ai-bash-replace_special_characters.sh
            ├── 003_ai-bash-run_mafft_alignment.sh
            ├── 004_ai-bash-run_clipkit_trimming.sh
            ├── 005_a_ai-bash-run_fasttree.sh
            ├── 005_b_ai-bash-run_iqtree.sh
            ├── 005_c_ai-bash-run_veryfasttree.sh
            ├── 005_d_ai-bash-run_phylobayes.sh
            └── 006_ai-python-write_run_log.py
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/START_HERE-user_config.yaml` | Gene family, tree methods, alignment settings | **YES** |
| `../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/` | Final trees | No (auto-created symlinks) |

---

## Resource Requirements

| Process | CPU | Memory | Time |
|---------|-----|--------|------|
| MAFFT alignment | 50 | 64 GB | 48 hours |
| ClipKit trimming | 4 | 16 GB | 4 hours |
| FastTree | 4 | 16 GB | 4 hours |
| IQ-TREE | 50 | 64 GB | 100 hours |
| VeryFastTree | configurable | 16 GB | 4 hours |
| PhyloBayes | 4 | 32 GB | 336 hours (2 weeks) |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "AGS file not found" | STEP_1 not complete | Run STEP_1 first |
| MAFFT out of memory | Large alignment | Increase memory in config |
| IQ-TREE timeout | Complex dataset | Increase time limit or use FastTree |
| PhyloBayes not converging | Too few generations | Increase generations in config |
| Empty tree file | Alignment had too few sequences | Check AGS has enough sequences |
| "ClipKit removed all columns" | Very divergent sequences | Try different ClipKit mode |

### Diagnostic Commands

```bash
# Check AGS from STEP_1 (use find -L to follow symlinks)
find -L ../../output_to_input/*/STEP_1-homolog_discovery/ -name "*.aa" -type f
grep -c ">" ../../output_to_input/*/STEP_1-homolog_discovery/*.aa

# Check alignment
grep -c ">" OUTPUT_pipeline/3-output/*.mafft

# Check trimmed alignment
grep -c ">" OUTPUT_pipeline/4-output/*.clipkit*

# Check tree files
ls OUTPUT_pipeline/5_*-output/
```

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting STEP_2 | "Which tree methods? FastTree (default) is usually sufficient for exploration." |
| Publication analysis | "For publication, I recommend enabling IQ-TREE alongside FastTree for comparison." |
| Large dataset | "How many sequences in the AGS? If >10,000, VeryFastTree may be faster than FastTree." |
| Bayesian needed | "PhyloBayes takes days-weeks. Are you sure you need Bayesian analysis?" |
| SLURM users | "Set execution_mode: slurm, slurm_account, slurm_qos, slurm_cpus, slurm_memory_gb, slurm_time_hours in START_HERE-user_config.yaml" |
