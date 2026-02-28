# AI Guide: STEP_3-phylogenetic_analysis (trees_gene_families)

**For AI Assistants**: This guide covers STEP_3 of the trees_gene_families subproject. For subproject overview, see `../AI_GUIDE-trees_gene_families.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_families/STEP_3-phylogenetic_analysis/`

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
| STEP_3 phylogenetic analysis concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-phylogenetic_analysis_workflow.md` |

---

## What This Step Does

**Purpose**: Build phylogenetic trees from the AGS (All Gene Set) produced by STEP_2.

**Process**:
1. Stage AGS sequences from STEP_2 output
2. Clean sequences (remove special characters)
3. Multiple sequence alignment (MAFFT)
4. Alignment trimming (ClipKit)
5. Tree building (one or more methods)
6. Tree visualization (human-friendly and computer-vision)
7. Export to output_to_input

---

## Tree Methods

Four methods available, configurable in `phylogenetic_analysis_config.yaml`:

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
| AGS FASTA | `../../STEP_2-homolog_discovery/output_to_input/ags_fastas/<gene_family>/` | From STEP_2 |

**Note**: The workflow automatically finds the AGS file in STEP_2's output_to_input directory.

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
├── 5_d-output/     # PhyloBayes tree (if enabled)
├── 6-output/       # Human-friendly visualizations
└── 7-output/       # Computer-vision visualizations
```

### output_to_input

Trees and alignments exported to:

| Level | Path |
|-------|------|
| STEP-level | `output_to_input/trees/<gene_family>/` |
| Subproject-level | `../output_to_input/step_3/trees/<gene_family>/` |

---

## Directory Structure

```
STEP_3-phylogenetic_analysis/
├── AI_GUIDE-phylogenetic_analysis.md   # THIS FILE
├── README.md
├── output_to_input/
│   └── trees/                          # Trees by gene family
└── workflow-COPYME-phylogenetic_analysis/
    ├── README.md
    ├── RUN-phylogenetic_analysis.sh
    ├── RUN-phylogenetic_analysis.sbatch
    ├── phylogenetic_analysis_config.yaml
    ├── INPUT_user/
    ├── OUTPUT_pipeline/
    └── ai/
        ├── AI_GUIDE-phylogenetic_analysis_workflow.md
        ├── main.nf
        ├── nextflow.config
        └── scripts/
            ├── 001_ai-bash-prepare_alignment_input.sh
            ├── 002_ai-bash-replace_special_characters.sh
            ├── 003_ai-sbatch-run_mafft_alignment.sh
            ├── 004_ai-bash-run_clipkit_trimming.sh
            ├── 005_a_ai-bash-run_fasttree.sh
            ├── 005_b_ai-sbatch-run_iqtree.sh
            ├── 005_c_ai-bash-run_veryfasttree.sh
            ├── 005_d_ai-bash-run_phylobayes.sh
            ├── 006_ai-python-visualize_phylogenetic_trees-human_friendly.py
            └── 007_ai-python-visualize_phylogenetic_trees-computer_vision_friendly.py
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/phylogenetic_analysis_config.yaml` | Gene family, tree methods, alignment settings | **YES** |
| `workflow-*/RUN-*.sbatch` | SLURM account/qos | **YES** (SLURM users) |
| `output_to_input/trees/` | Final trees | No (auto-created) |

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
| "AGS file not found" | STEP_2 not complete | Run STEP_2 first |
| MAFFT out of memory | Large alignment | Increase memory in config |
| IQ-TREE timeout | Complex dataset | Increase time limit or use FastTree |
| PhyloBayes not converging | Too few generations | Increase generations in config |
| Empty tree file | Alignment had too few sequences | Check AGS has enough sequences |
| Visualization fails | ete3 not installed | Check conda environment |
| "ClipKit removed all columns" | Very divergent sequences | Try different ClipKit mode |

### Diagnostic Commands

```bash
# Check AGS from STEP_2
ls ../../STEP_2-homolog_discovery/output_to_input/ags_fastas/*/
grep -c ">" ../../STEP_2-homolog_discovery/output_to_input/ags_fastas/*/*.aa

# Check alignment
grep -c ">" OUTPUT_pipeline/3-output/*.mafft

# Check trimmed alignment
grep -c ">" OUTPUT_pipeline/4-output/*.clipkit*

# Check tree files
ls OUTPUT_pipeline/5_*-output/

# Check visualizations
ls OUTPUT_pipeline/6-output/ OUTPUT_pipeline/7-output/
```

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting STEP_3 | "Which tree methods do you want? FastTree (default) is usually sufficient for exploration." |
| Publication analysis | "For publication, I recommend enabling IQ-TREE alongside FastTree for comparison." |
| Large dataset | "How many sequences in the AGS? If >10,000, VeryFastTree may be faster than FastTree." |
| Bayesian needed | "PhyloBayes takes days-weeks. Are you sure you need Bayesian analysis?" |
| SLURM users | "Have you edited the .sbatch file with your cluster account and QOS?" |
