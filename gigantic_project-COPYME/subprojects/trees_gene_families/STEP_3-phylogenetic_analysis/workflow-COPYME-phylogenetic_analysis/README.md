# workflow-COPYME-phylogenetic_analysis

**AI**: Claude Code | Opus 4.6 | 2026 February 27
**Human**: Eric Edsinger

---

## Purpose

STEP_3 workflow template for phylogenetic analysis with configurable tree-building methods for **one gene family per workflow copy**.

**Part of**: STEP_3-phylogenetic_analysis (see `../README.md`)

---

## What This Workflow Does

1. **Prepare Input** (Process 1)
   - Stages AGS sequences from STEP_2 output_to_input

2. **Clean Sequences** (Process 2)
   - Removes leading/trailing dashes from sequences

3. **MAFFT Alignment** (Process 3)
   - Multiple sequence alignment with MAFFT

4. **ClipKit Trimming** (Process 4)
   - Alignment trimming with ClipKit smart-gap mode

5. **Tree Building** (Processes 5a-5d, configurable)
   - **5a. FastTree** - Fast approximate ML phylogeny (default, recommended)
   - **5b. IQ-TREE** - Full ML phylogeny with bootstrap (publication-quality)
   - **5c. VeryFastTree** - Parallelized FastTree (large datasets only)
   - **5d. PhyloBayes** - Bayesian phylogenetic inference (Bayesian counterpoint)

6. **Visualization** (Processes 6-7)
   - Human-friendly tree visualization (script 006)
   - Computer-vision tree visualization (script 007)

7. **Export** (Process 8)
   - Copies alignment, trimmed alignment, and tree files to output_to_input

---

## Usage

**Copy this template for each gene family:**
```bash
# For innexin_pannexin:
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
cd workflow-RUN_01-phylogenetic_analysis

# For piezo (separate copy):
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_02-phylogenetic_analysis
```

**Configure your run:**
```bash
# Edit the configuration file - set gene_family name and tree methods
nano phylogenetic_analysis_config.yaml
```

**Example config settings:**
```yaml
gene_family:
  name: "innexin_pannexin"

tree_methods:
  fasttree: true        # Fast ML (default, recommended)
  iqtree: false         # Publication-quality ML with bootstrap
  veryfasttree: false   # Parallelized FastTree (large datasets)
  phylobayes: false     # Bayesian inference (very slow)
```

**Run locally:**
```bash
bash RUN-phylogenetic_analysis.sh
```

**Run on SLURM:**
```bash
# Edit RUN-phylogenetic_analysis.sbatch to set --account and --qos
sbatch RUN-phylogenetic_analysis.sbatch
```

---

## Prerequisites

- **STEP_2-homolog_discovery** complete for this gene family (AGS file in output_to_input/)
- **Conda environment** `ai_gigantic_trees` with `mafft`, `clipkit`, `fasttree`, and optionally `iqtree`, `VeryFastTree`, `phylobayes`
- **NextFlow** installed and available in PATH

---

## Directory Structure

```
workflow-COPYME-phylogenetic_analysis/
├── README.md                              # This file
├── RUN-phylogenetic_analysis.sh           # Local runner (calls NextFlow)
├── RUN-phylogenetic_analysis.sbatch       # SLURM wrapper
├── phylogenetic_analysis_config.yaml      # User-editable configuration
├── INPUT_user/                            # User-provided inputs (if any)
├── OUTPUT_pipeline/                       # Workflow outputs (flat structure)
│   ├── 1-output/                          # Staged AGS sequences
│   ├── 2-output/                          # Cleaned sequences
│   ├── 3-output/                          # MAFFT alignment
│   ├── 4-output/                          # ClipKit trimmed alignment
│   ├── 5_a-output/                        # FastTree output (if enabled)
│   ├── 5_b-output/                        # IQ-TREE output (if enabled)
│   ├── 5_c-output/                        # VeryFastTree output (if enabled)
│   ├── 5_d-output/                        # PhyloBayes output (if enabled)
│   ├── 6-output/                          # Human-friendly visualizations
│   └── 7-output/                          # Computer-vision visualizations
└── ai/
    ├── main.nf                            # NextFlow pipeline definition
    ├── nextflow.config                    # NextFlow settings
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

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Staged AGS | `1-output/1_ai-ags-*.aa` | AGS sequences from STEP_2 |
| Cleaned sequences | `2-output/2_ai-ags-*.aa` | Sequences with dashes removed |
| MAFFT alignment | `3-output/3_ai-ags-*.mafft` | Multiple sequence alignment |
| Trimmed alignment | `4-output/4_ai-ags-*.clipkit-smartgap` | ClipKit-trimmed alignment |
| FastTree | `5_a-output/5_a_ai-ags-*.fasttree` | FastTree ML phylogeny |
| IQ-TREE | `5_b-output/5_b_ai-ags-*.treefile` | IQ-TREE ML phylogeny |
| VeryFastTree | `5_c-output/5_c_ai-ags-*.veryfasttree` | VeryFastTree ML phylogeny |
| PhyloBayes | `5_d-output/5_d_ai-ags-*.phylobayes.nwk` | PhyloBayes Bayesian consensus tree |
| Human visualization | `6-output/6_ai-*-human_friendly.{svg,pdf}` | Human-readable tree images |
| CV visualization | `7-output/7_ai-*-computer_vision_friendly.{svg,pdf}` | Computer-vision tree images |

---

## Tree Method Comparison

| Method | Speed | Quality | Best For |
|--------|-------|---------|----------|
| **FastTree** | Fast (min-hrs) | Best approximate ML | General-purpose, 50-500 sequences (default) |
| **IQ-TREE** | Slow (hrs-days) | Publication quality | Final analysis, rigorous statistical support |
| **VeryFastTree** | Fast (parallel) | Slightly worse than FastTree | Very large datasets (>10,000 sequences) |
| **PhyloBayes** | Very slow (days-weeks) | Bayesian posterior | Bayesian counterpoint to ML, deep divergences |

---

## Data Flow

```
STEP_2 output_to_input/ags_fastas/<gene_family>/
       │
       ▼
Process 1: Stage AGS → 1-output/
       │
       ▼
Process 2: Clean → 2-output/
       │
       ▼
Process 3: MAFFT → 3-output/
       │
       ▼
Process 4: ClipKit → 4-output/
       │
       ├──────────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
   5a: FastTree   5b: IQ-TREE   5c: VeryFastTree  5d: PhyloBayes
       │              │              │              │
       └──────┬───────┴──────────────┴──────────────┘
              ▼
     Processes 6-7: Visualizations
              │
              ▼
     Process 8: output_to_input/
```

---

## Next Step

After this workflow completes, phylogenetic trees are available in:
```
STEP_3-phylogenetic_analysis/output_to_input/trees/<gene_family>/
trees_gene_families/output_to_input/step_3/trees/<gene_family>/
```
