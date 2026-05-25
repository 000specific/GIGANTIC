# STEP_2 — Phylogenetic Analysis

Per-source STEP_2: build phylogenetic trees from the AGS produced by STEP_1.

## Single user-runnable script

```bash
# 1. Inside the per-source instance (e.g., gene_groups-<INSTANCE>/STEP_2-phylogenetic_analysis/),
#    copy the COPYME → RUN_NN at the same level:
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_1-phylogenetic_analysis

# 2. Edit RUN's config (execution_mode, paths, tree methods):
cd workflow-RUN_1-phylogenetic_analysis
# edit START_HERE-user_config.yaml

# 3. Run the single user-facing script
bash RUN-workflow.sh
```

`RUN-workflow.sh` is an **orchestrator**:

1. Creates the per-workflow conda env on the login node (first run only)
2. For each gene group with a STEP_1 AGS file: sets up `gene_group-X/workflow-RUN_01-phylogenetic_analysis/` as a sibling
3. Dispatches per `execution_mode`:
   - `local` — sequential nextflow runs
   - `slurm-standard` — one sbatch per gene group, standard QOS
   - `slurm-burst` — chunked, one sbatch per block, burst QOS

## Prerequisites

STEP_1 must have completed: AGS files present at
`../../../output_to_input/<source>/STEP_1-homolog_discovery/gene_group-*/16_ai-ags-*.aa`

Gene groups without an AGS are skipped.

## Pipeline (inside each per-gene-group nextflow run)

| Process | Tool | What |
|---------|------|------|
| 1 | (bash) | Stage AGS sequences from STEP_1 output_to_input |
| 2 | (bash) | Clean leading/trailing dashes |
| 3 | MAFFT | Multiple sequence alignment |
| 4 | ClipKit | Smart-gap trimming |
| 5_a | FastTree | Fast approximate ML tree (default) |
| 5_b | IQ-TREE | Full ML with model selection + bootstrap |
| 5_c | VeryFastTree | Parallel FastTree alternative |
| 5_d | PhyloBayes | Bayesian MCMC |
| 6 | python | Run log |

Enable tree methods via the `tree_methods:` block in YAML.

## Output

Tree newick files symlinked at:
```
trees_gene_groups/output_to_input/<source>/STEP_2-phylogenetic_analysis/gene_group-<name>/*.{fasttree,treefile,veryfasttree,phylobayes.nwk}
```

These are STEP_3's input.

## See also

- `AI_GUIDE-phylogenetic_analysis.md` — detailed AI guide
- `workflow-COPYME-phylogenetic_analysis/ai/AI_GUIDE-phylogenetic_analysis_workflow.md` — workflow execution guide
