# AI Guide: OrthoFinder Workflow

**For AI Assistants**: This guide covers workflow execution. For OrthoFinder concepts, see `../../AI_GUIDE-orthofinder.md`. For orthogroups overview, see `../../../AI_GUIDE-orthogroups.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `orthogroups/orthofinder/workflow-COPYME-run_orthofinder/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE-project.md` |
| Orthogroups concepts | `../../../AI_GUIDE-orthogroups.md` |
| OrthoFinder tool overview | `../../AI_GUIDE-orthofinder.md` |
| Running the workflow | This file |

---

## Architecture: Bash Script (No NextFlow)

Unlike OrthoHMM, the OrthoFinder workflow is a **single bash script** that calls OrthoFinder directly. OrthoFinder manages its own internal pipeline.

```
workflow-COPYME-run_orthofinder/
│
├── RUN_orthofinder.sh              # Local: bash RUN_orthofinder.sh
├── SLURM_orthofinder.sbatch        # SLURM: sbatch SLURM_orthofinder.sbatch
│
├── INPUT_user/
│   ├── README.md                   # Input preparation guide
│   ├── speciesNN_species_tree.newick  # User-provided species tree
│   └── proteomes/                  # Symlinks or copies of proteome FASTAs
│
├── OUTPUT_pipeline/
│   └── orthofinder_results/        # All OrthoFinder output
│       ├── Orthogroups/
│       ├── Species_Tree/
│       ├── Phylogenetic_Hierarchical_Orthogroups/
│       └── Comparative_Genomics_Statistics/
│
└── ai/
    └── AI_GUIDE-orthofinder_workflow.md  # THIS FILE
```

---

## User Workflow

### Step 1: Copy Template

```bash
cp -r workflow-COPYME-run_orthofinder workflow-RUN_01-run_orthofinder
cd workflow-RUN_01-run_orthofinder/
```

### Step 2: Prepare Inputs

See `INPUT_user/README.md` for detailed instructions:

1. **Species tree**: Place Newick-format species tree in `INPUT_user/`
   - Must be named `speciesNN_species_tree.newick` (NN = species count)
   - Leaf names must match proteome filenames (without extension)

2. **Proteomes**: Create symlinks or copy FASTAs to `INPUT_user/proteomes/`
   - From genomesDB: `ln -s ../../../genomesDB/output_to_input/speciesN_gigantic_T1_proteomes INPUT_user/proteomes`

### Step 3: Run

**Local**:
```bash
module load conda
conda activate ai_gigantic_orthogroups
bash RUN_orthofinder.sh
```

**SLURM** (edit account/qos/email first):
```bash
sbatch SLURM_orthofinder.sbatch
```

---

## OrthoFinder Settings

| Flag | Value | Purpose |
|------|-------|---------|
| `-t` | 128 | Sequence search threads |
| `-a` | 128 | Analysis threads |
| `-X` | (flag) | Don't modify sequence IDs (GIGANTIC proteomes have phylonames) |
| `-S` | diamond_ultra_sens | Ultra-sensitive Diamond search |
| `-T` | fasttree | Gene tree inference method |
| `-s` | species_tree.newick | Use user-provided species tree |

---

## SLURM Execution Details

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | YOUR_ACCOUNT | **Must edit** |
| `--qos` | YOUR_QOS | **Must edit** |
| `--mail-user` | YOUR_EMAIL@ufl.edu | **Must edit** |
| `--cpus-per-task` | 128 | Full node for Diamond parallelism |
| `--mem` | 500gb | All-vs-all comparisons need memory |
| `--time` | 120:00:00 | 5 days; increase for 67+ species |

---

## Expected Runtime

| Scenario | Duration | Memory |
|----------|----------|--------|
| ~20 species | 1-2 days | 200 GB |
| ~67 species | 4-7 days | 500 GB |
| ~100+ species | 7-14 days | 700+ GB |

---

## Verification Commands

```bash
# Check OrthoFinder completed
ls OUTPUT_pipeline/orthofinder_results/

# Check orthogroups
wc -l OUTPUT_pipeline/orthofinder_results/Orthogroups/Orthogroups.tsv

# Check HOGs
ls OUTPUT_pipeline/orthofinder_results/Phylogenetic_Hierarchical_Orthogroups/

# Check species tree
cat OUTPUT_pipeline/orthofinder_results/Species_Tree/SpeciesTree_rooted.txt

# Check statistics
ls OUTPUT_pipeline/orthofinder_results/Comparative_Genomics_Statistics/
```

---

## Troubleshooting

### "No FASTA files found"

**Cause**: Proteomes not in INPUT_user/proteomes/ or wrong file extensions

**Diagnose**:
```bash
ls INPUT_user/proteomes/
```

**Fix**: Add proteome symlinks or copies with recognized extensions (.fasta, .fa, .faa, .pep).

### "Species tree leaf names don't match"

**Cause**: Leaf names in species tree don't match proteome filenames

**Fix**: Ensure proteome filenames (without extension) match species tree leaf names exactly.

### OrthoFinder out of memory

**Cause**: Large number of species or sequences

**Fix**: Increase SLURM memory in SLURM_orthofinder.sbatch.

### Diamond/OrthoFinder not found

**Cause**: Conda environment not activated

**Fix**:
```bash
module load conda
conda activate ai_gigantic_orthogroups
```

---

## After Successful Run

1. **Verify**: Check Orthogroups.tsv has expected species and gene counts
2. **Review HOGs**: Check hierarchical orthogroups at key phylogenetic levels
3. **Compare**: If also running OrthoHMM, compare orthogroup counts
4. **Copy outputs**: Key results should be copied to `../../output_to_input/` for downstream use
5. **Done**: Orthogroups ready for downstream subprojects
