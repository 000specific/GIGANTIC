# workflow-COPYME-phylogenetic_analysis

**AI**: Claude Code | Opus 4.6 | 2026 February 27
**Human**: Eric Edsinger

---

## Purpose

STEP_3 workflow template for phylogenetic analysis with configurable tree-building methods.

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
   - **5a. FastTree** - Fast approximate ML phylogeny (default: enabled)
   - **5b. SuperFastTree** - Parallelized FastTree (FUTURE)
   - **5c. IQ-TREE** - Full ML phylogeny with bootstrap (default: disabled)
   - **5d. PhyloBayes** - Bayesian phylogenetic inference (FUTURE)

6. **Visualization** (Processes 6-7)
   - Human-friendly tree visualization (script 006)
   - Computer-vision tree visualization (script 007)

7. **Export** (Process 8)
   - Copies alignment, trimmed alignment, and tree files to output_to_input

---

## Usage

**Copy this template to create a run directory:**
```bash
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
cd workflow-RUN_01-phylogenetic_analysis
```

**Configure your run:**
```bash
# Edit the configuration file with your project settings
nano phylogenetic_analysis_config.yaml
```

**Prepare input files:**
```bash
# Create RGS manifest (gene_family names, same as STEP_2)
nano INPUT_user/rgs_manifest.tsv
```

**Choose tree-building methods:**
Edit `phylogenetic_analysis_config.yaml`:
```yaml
tree_methods:
  fasttree: true        # Fast ML (default)
  superfasttree: false  # FUTURE
  iqtree: false         # Full ML with bootstrap
  phylobayes: false     # FUTURE
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

- **STEP_2-homolog_discovery** complete (provides AGS files in output_to_input/)
- **Conda environments** with `mafft`, `clipkit`, `fasttree`, and/or `iqtree` installed
- **NextFlow** installed and available in PATH
- **INPUT_user/** manifest prepared

---

## Directory Structure

```
workflow-COPYME-phylogenetic_analysis/
├── README.md                              # This file
├── RUN-phylogenetic_analysis.sh           # Local runner (calls NextFlow)
├── RUN-phylogenetic_analysis.sbatch       # SLURM wrapper
├── phylogenetic_analysis_config.yaml      # User-editable configuration
├── INPUT_user/                            # User-provided inputs
│   └── rgs_manifest.tsv                   # Gene family names
├── OUTPUT_pipeline/                       # Workflow outputs (per gene family)
│   └── <gene_family>/
│       ├── 1-output/                      # Staged AGS sequences
│       ├── 2-output/                      # Cleaned sequences
│       ├── 3-output/                      # MAFFT alignment
│       ├── 4-output/                      # ClipKit trimmed alignment
│       ├── 5_a-output/                    # FastTree output (if enabled)
│       ├── 5_b-output/                    # SuperFastTree output (FUTURE)
│       ├── 5_c-output/                    # IQ-TREE output (if enabled)
│       ├── 5_d-output/                    # PhyloBayes output (FUTURE)
│       ├── 6-output/                      # Human-friendly visualizations
│       └── 7-output/                      # Computer-vision visualizations
└── ai/
    ├── main.nf                            # NextFlow pipeline definition
    ├── nextflow.config                    # NextFlow settings
    └── scripts/
        ├── 001_ai-bash-prepare_alignment_input.sh
        ├── 002_ai-bash-replace_special_characters.sh
        ├── 003_ai-sbatch-run_mafft_alignment.sh
        ├── 004_ai-bash-run_clipkit_trimming.sh
        ├── 005_a_ai-bash-run_fasttree.sh
        ├── 005_b_ai-bash-run_superfasttree.sh          # FUTURE placeholder
        ├── 005_c_ai-sbatch-run_iqtree.sh
        ├── 005_d_ai-bash-run_phylobayes.sh             # FUTURE placeholder
        ├── 006_ai-python-visualize_phylogenetic_trees-human_friendly.py
        └── 007_ai-python-visualize_phylogenetic_trees-computer_vision_friendly.py
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Staged AGS | `1-output/1_ai-AGS-*.aa` | AGS sequences from STEP_2 |
| Cleaned sequences | `2-output/2_ai-AGS-*.aa` | Sequences with dashes removed |
| MAFFT alignment | `3-output/3_ai-AGS-*.mafft` | Multiple sequence alignment |
| Trimmed alignment | `4-output/4_ai-AGS-*.clipkit-smartgap` | ClipKit-trimmed alignment |
| FastTree | `5_a-output/5_a_ai-AGS-*.fasttree` | FastTree ML phylogeny |
| IQ-TREE | `5_c-output/5_c_ai-AGS-*.treefile` | IQ-TREE ML phylogeny |
| Human visualization | `6-output/6_ai-AGS-*-human_friendly.{svg,pdf}` | Human-readable tree images |
| CV visualization | `7-output/7_ai-AGS-*-computer_vision_friendly.{svg,pdf}` | Computer-vision tree images |

---

## Tree Method Comparison

| Method | Speed | Quality | Best For |
|--------|-------|---------|----------|
| **FastTree** | Fast (min-hrs) | Good approximation | Exploratory analysis, large datasets |
| **SuperFastTree** | Fast (parallel) | Good approximation | Very large datasets (FUTURE) |
| **IQ-TREE** | Slow (hrs-days) | Publication quality | Final analysis, statistical rigor |
| **PhyloBayes** | Very slow | Bayesian posterior | Complex models, deep divergences (FUTURE) |

---

## Data Flow

```
STEP_2 output_to_input/homolog_sequences/<gene_family>/
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
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
   5a: FastTree   5c: IQ-TREE    (future methods)
       │              │
       └──────┬───────┘
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
trees_gene_families/output_to_input/STEP_3-trees/<gene_family>/
```
