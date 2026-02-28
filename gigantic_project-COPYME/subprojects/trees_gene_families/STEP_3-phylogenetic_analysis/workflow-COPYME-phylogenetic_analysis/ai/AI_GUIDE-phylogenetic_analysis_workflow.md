# AI Guide: Phylogenetic Analysis Workflow

**For AI Assistants**: This guide covers workflow execution. For STEP_3 concepts, see `../../AI_GUIDE-phylogenetic_analysis.md`. For trees_gene_families overview, see `../../../AI_GUIDE-trees_gene_families.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `trees_gene_families/STEP_3-phylogenetic_analysis/workflow-COPYME-phylogenetic_analysis/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE-project.md` |
| trees_gene_families concepts | `../../../AI_GUIDE-trees_gene_families.md` |
| STEP_3 phylogenetic analysis | `../../AI_GUIDE-phylogenetic_analysis.md` |
| Running the workflow | This file |

---

## Architecture: 8 Processes, Conditional Tree Building

```
workflow-COPYME-phylogenetic_analysis/
│
├── README.md
├── RUN-phylogenetic_analysis.sh       # Local: bash RUN-phylogenetic_analysis.sh
├── RUN-phylogenetic_analysis.sbatch   # SLURM: sbatch RUN-phylogenetic_analysis.sbatch
├── phylogenetic_analysis_config.yaml  # User configuration
│
├── INPUT_user/                        # (empty - reads from STEP_2 output_to_input)
│
├── OUTPUT_pipeline/
│   ├── 1-output/       # Staged AGS
│   ├── 2-output/       # Cleaned sequences
│   ├── 3-output/       # MAFFT alignment
│   ├── 4-output/       # ClipKit trimmed alignment
│   ├── 5_a-output/     # FastTree (if enabled)
│   ├── 5_b-output/     # IQ-TREE (if enabled)
│   ├── 5_c-output/     # VeryFastTree (if enabled)
│   ├── 5_d-output/     # PhyloBayes (if enabled)
│   ├── 6-output/       # Human-friendly visualizations
│   └── 7-output/       # Computer-vision visualizations
│
└── ai/
    ├── AI_GUIDE-phylogenetic_analysis_workflow.md  # THIS FILE
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

### Script Pipeline

| Process | Scripts | Does |
|---------|---------|------|
| prepare_alignment_input | 001 | Copies AGS from STEP_2 output_to_input |
| clean_sequences | 002 | Removes leading/trailing dashes from sequences |
| run_mafft_alignment | 003 | MAFFT multiple sequence alignment |
| run_clipkit_trimming | 004 | ClipKit smart-gap trimming |
| run_fasttree | 005_a | FastTree ML tree (default, fast) |
| run_iqtree | 005_b | IQ-TREE ML tree (publication quality) |
| run_veryfasttree | 005_c | VeryFastTree (multi-threaded FastTree alternative) |
| run_phylobayes | 005_d | PhyloBayes Bayesian MCMC (2 chains + convergence) |
| visualize_trees_human | 006 | Human-friendly tree visualizations (SVG/PDF) |
| visualize_trees_cv | 007 | Computer-vision-friendly visualizations |
| copy_to_output_to_input | - | Export trees and alignments |

### Conditional Tree Building

Tree methods are controlled by boolean flags in config:

```yaml
tree_methods:
  fasttree: true        # DEFAULT - always recommended
  iqtree: false         # Enable for publication
  veryfasttree: false   # Enable for large datasets
  phylobayes: false     # Enable for Bayesian analysis
```

Only enabled methods run. All enabled tree outputs are collected and passed to visualization processes.

---

## User Workflow

### Step 1: Copy Template

```bash
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
cd workflow-RUN_01-phylogenetic_analysis/
```

### Step 2: Configure

Edit `phylogenetic_analysis_config.yaml`:

```yaml
gene_family:
  name: "innexin_pannexin"

input:
  step2_ags_fastas_dir: "../../STEP_2-homolog_discovery/output_to_input/ags_fastas"

project:
  database: "species67_T1-species67"

tree_methods:
  fasttree: true       # Enable/disable as needed
  iqtree: false
  veryfasttree: false
  phylobayes: false
```

### Step 3: Run

**Local**:
```bash
bash RUN-phylogenetic_analysis.sh
```

**SLURM** (edit account/qos first):
```bash
sbatch RUN-phylogenetic_analysis.sbatch
```

---

## SLURM Execution Details

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | `YOUR_ACCOUNT` | **Must edit** |
| `--qos` | `YOUR_QOS` | **Must edit** |
| `--cpus-per-task` | `100` | For MAFFT and IQ-TREE parallelism |
| `--mem` | `700gb` | IQ-TREE/PhyloBayes may need large memory |
| `--time` | `100:00:00` | Depends on tree methods enabled |

**Adjust resources based on enabled methods**:
- FastTree only: 4 CPUs, 16 GB, 4 hours
- With IQ-TREE: 50+ CPUs, 64 GB, 100 hours
- With PhyloBayes: 4 CPUs, 32 GB, 336 hours (2 weeks)

---

## Expected Runtime

| Method | Typical Runtime | Notes |
|--------|----------------|-------|
| Stages 1-4 (align/trim) | 10 min - 2 hours | Depends on sequence count |
| FastTree | 1 min - 1 hour | Very fast |
| IQ-TREE | 2 hours - 5 days | Model selection is slow |
| VeryFastTree | 30 sec - 30 min | Fastest tree method |
| PhyloBayes | 1 day - 2 weeks | MCMC convergence varies |
| Visualization | 1-10 minutes | Depends on tree count |

---

## Verification Commands

```bash
# Check MAFFT alignment
grep -c ">" OUTPUT_pipeline/3-output/*.mafft

# Check trimmed alignment
grep -c ">" OUTPUT_pipeline/4-output/*.clipkit*

# Check tree files exist
ls -la OUTPUT_pipeline/5_*-output/*

# Check FastTree
cat OUTPUT_pipeline/5_a-output/*.fasttree | head -1

# Check IQ-TREE (if enabled)
cat OUTPUT_pipeline/5_b-output/*.treefile | head -1

# Check visualizations
ls OUTPUT_pipeline/6-output/ OUTPUT_pipeline/7-output/

# Check output_to_input export
ls ../../output_to_input/trees/*/
```

---

## Troubleshooting

### "AGS file not found"

**Cause**: STEP_2 output not in expected location

**Diagnose**:
```bash
ls ../../STEP_2-homolog_discovery/output_to_input/ags_fastas/*/
```

**Fix**: Run STEP_2 first, or update `step2_ags_fastas_dir` in config.

### MAFFT out of memory

**Cause**: Very large sequence set

**Fix**: Increase memory in `phylogenetic_analysis_config.yaml`:
```yaml
phylogenetics:
  mafft:
    memory: "128gb"
```

### IQ-TREE timeout

**Cause**: Complex dataset with many models to test

**Fix**: Increase time limit, or use FastTree instead for initial exploration.

### PhyloBayes not converging

**Cause**: Too few MCMC generations or very divergent sequences

**Diagnose**:
```bash
# Check convergence diagnostics
cat OUTPUT_pipeline/5_d-output/*tracecomp* 2>/dev/null
cat OUTPUT_pipeline/5_d-output/*bpcomp* 2>/dev/null
```

**Fix**: Increase generations in config:
```yaml
phylogenetics:
  phylobayes:
    generations: 50000
    burnin: 12500
```

### ClipKit removes all columns

**Cause**: Very divergent sequences in alignment

**Fix**: Try different ClipKit mode:
```yaml
phylogenetics:
  clipkit:
    mode: "kpic-smart-gap"  # Less aggressive than smart-gap
```

### Visualization fails

**Cause**: ete3 library issue or no tree files

**Diagnose**:
```bash
python3 -c "import ete3; print(ete3.__version__)"
ls OUTPUT_pipeline/5_*-output/*
```

**Fix**: Check conda environment has ete3 installed.

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-phylogenetic_analysis.sh
```

---

## Manual Execution (for debugging)

```bash
cd workflow-RUN_XX-phylogenetic_analysis

# Run alignment manually
mafft --originalseqonly --maxiterate 1000 --reorder --bl 62 \
    --thread 4 INPUT_FILE > aligned.mafft

# Run trimming manually
clipkit aligned.mafft -m smart-gap -o trimmed.clipkit -l

# Run FastTree manually
FastTree trimmed.clipkit > tree.fasttree

# Run IQ-TREE manually
iqtree2 -s trimmed.clipkit -m MFP -bb 1000 -nt AUTO
```

---

## After Successful Run

1. **Verify**: Check tree files exist and are non-empty
2. **Review visualizations**: Check SVG/PDF files in `6-output/`
3. **Check output_to_input**: `ls ../../output_to_input/trees/`
4. **Compare methods**: If multiple methods ran, compare tree topologies
5. **Done**: Trees are ready for publication or further analysis
