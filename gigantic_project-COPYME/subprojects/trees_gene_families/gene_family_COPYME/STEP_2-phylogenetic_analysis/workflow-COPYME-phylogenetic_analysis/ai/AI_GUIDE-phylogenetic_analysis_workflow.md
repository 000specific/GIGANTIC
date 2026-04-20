# AI Guide: Phylogenetic Analysis Workflow

**For AI Assistants**: This guide covers workflow execution. For STEP_2 concepts, see `../../AI_GUIDE-phylogenetic_analysis.md`. For trees_gene_families overview, see `../../../AI_GUIDE-trees_gene_families.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `trees_gene_families/STEP_2-phylogenetic_analysis/workflow-COPYME-phylogenetic_analysis/`

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
| STEP_2 phylogenetic analysis | `../../AI_GUIDE-phylogenetic_analysis.md` |
| Running the workflow | This file |

---

## Architecture: 8 Processes, Conditional Tree Building

```
workflow-COPYME-phylogenetic_analysis/
│
├── README.md
├── RUN-workflow.sh       # Runner: bash RUN-workflow.sh (handles local + SLURM via config)
├── START_HERE-user_config.yaml  # User configuration (includes execution_mode, SLURM settings)
│
├── INPUT_user/                        # (empty - reads from subproject output_to_input/<gene_family>/STEP_1-homolog_discovery)
│
├── OUTPUT_pipeline/
│   ├── 1-output/       # Staged AGS
│   ├── 2-output/       # Cleaned sequences
│   ├── 3-output/       # MAFFT alignment
│   ├── 4-output/       # ClipKit trimmed alignment
│   ├── 5_a-output/     # FastTree (if enabled)
│   ├── 5_b-output/     # IQ-TREE (if enabled)
│   ├── 5_c-output/     # VeryFastTree (if enabled)
│   └── 5_d-output/     # PhyloBayes (if enabled)
│
└── ai/
    ├── AI_GUIDE-phylogenetic_analysis_workflow.md  # THIS FILE
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

### Script Pipeline

| Process | Scripts | Does |
|---------|---------|------|
| prepare_alignment_input | 001 | Copies AGS from output_to_input/<gene_family>/STEP_1-homolog_discovery |
| clean_sequences | 002 | Removes leading/trailing dashes from sequences |
| run_mafft_alignment | 003 | MAFFT multiple sequence alignment |
| run_clipkit_trimming | 004 | ClipKit smart-gap trimming |
| run_fasttree | 005_a | FastTree ML tree (default, fast) |
| run_iqtree | 005_b | IQ-TREE ML tree (publication quality) |
| run_veryfasttree | 005_c | VeryFastTree (multi-threaded FastTree alternative) |
| run_phylobayes | 005_d | PhyloBayes Bayesian MCMC (2 chains + convergence) |
| write_run_log | 006 | Write pipeline execution summary |
| *(symlinks by RUN-workflow.sh)* | - | Export tree newicks and alignments to output_to_input/<gene_family>/STEP_2-phylogenetic_analysis |

**Tree visualization** (PDF/SVG rendering) is handled by the separate **STEP_3-tree_visualization** workflow, which consumes the newick files produced here. This decouples scientific computation from visualization library quirks (e.g., ete3/PyQt5 instability).

### Conditional Tree Building

Tree methods are controlled by boolean flags in config:

```yaml
tree_methods:
  fasttree: true        # DEFAULT - always recommended
  iqtree: false         # Enable for publication
  veryfasttree: false   # Enable for large datasets
  phylobayes: false     # Enable for Bayesian analysis
```

Only enabled methods run. All enabled tree newick files are exported to `output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/` for downstream consumption.

---

## User Workflow

### Step 1: Copy Template

```bash
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
cd workflow-RUN_01-phylogenetic_analysis/
```

### Step 2: Configure

Edit `START_HERE-user_config.yaml`:

```yaml
gene_family:
  name: "innexin_pannexin"

input:
  output_to_input_dir: "../../../output_to_input"

project:
  database: "speciesN_T1-speciesN"

tree_methods:
  fasttree: true       # Enable/disable as needed
  iqtree: false
  veryfasttree: false
  phylobayes: false

execution_mode: "local"  # or "slurm"
slurm_account: "your_account"
slurm_qos: "your_qos"
slurm_cpus: 50
slurm_memory_gb: 350
slurm_time_hours: 198
```

### Step 3: Run

**Local**:
```bash
bash RUN-workflow.sh
```

**SLURM** (set execution_mode and SLURM settings in config first):
```bash
bash RUN-workflow.sh
```

---

## SLURM Execution Details

All SLURM settings are configured in `START_HERE-user_config.yaml`:

| Config Key | Default | Notes |
|------------|---------|-------|
| `execution_mode` | `"local"` | Set to `"slurm"` for cluster |
| `slurm_account` | `"your_account"` | **Must edit** |
| `slurm_qos` | `"your_qos"` | **Must edit** |
| `slurm_cpus` | `50` | For MAFFT and IQ-TREE parallelism |
| `slurm_memory_gb` | `350` | IQ-TREE/PhyloBayes may need large memory |
| `slurm_time_hours` | `198` | Depends on tree methods enabled |

Per-tool resources (cpus, memory_gb, time_hours) are also configurable under the `resources:` section in config.

**Adjust resources based on enabled methods**:
- FastTree only: 25 CPUs, 150 GB, 12 hours
- With IQ-TREE: 50+ CPUs, 350 GB, 198 hours
- With PhyloBayes: 50 CPUs, 350 GB, 336 hours (2 weeks)

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

# Check output_to_input export (use find -L for symlinks)
ls -l ../../../output_to_input/*/STEP_2-phylogenetic_analysis/
```

---

## Troubleshooting

### "AGS file not found"

**Cause**: STEP_1 output not in expected location

**Diagnose**:
```bash
find -L ../../../output_to_input/*/STEP_1-homolog_discovery/ -name "*.aa" -type f
```

**Fix**: Run STEP_1 first, or update `output_to_input_dir` in config.

### MAFFT out of memory

**Cause**: Very large sequence set

**Fix**: Increase memory in `START_HERE-user_config.yaml`:
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

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-workflow.sh
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
2. **Check output_to_input**: `ls -l ../../../output_to_input/*/STEP_2-phylogenetic_analysis/`
3. **Compare methods**: If multiple methods ran, compare tree topologies
4. **Run STEP_3-tree_visualization** to render trees as PDF/SVG
