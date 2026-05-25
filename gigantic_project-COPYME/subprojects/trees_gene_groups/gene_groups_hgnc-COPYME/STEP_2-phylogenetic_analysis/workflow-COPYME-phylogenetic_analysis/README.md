# workflow-COPYME-phylogenetic_analysis

STEP_2 workflow template (orchestrator) for trees_gene_groups. Builds phylogenetic
trees per gene group from STEP_1's AGS output.

## Single user-runnable script

```bash
# 1. Copy this COPYME → RUN_NN at the same level
#    (e.g., inside gene_groups-<INSTANCE>/STEP_2-phylogenetic_analysis/):
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_1-phylogenetic_analysis
cd workflow-RUN_1-phylogenetic_analysis

# 2. Edit START_HERE-user_config.yaml (set execution_mode, tree_methods, resources)

# 3. Run
bash RUN-workflow.sh
```

## What `RUN-workflow.sh` does (orchestrator)

1. Creates the conda env `aiG-trees_gene_groups-phylogenetic_analysis` once on the
   login node from `ai/conda_environment.yml` (if missing)
2. Iterates the STEP_0 summary TSV (`gene_group_source_tsv` in config)
3. For each gene group **with a STEP_1 AGS file** (skips those without):
   - Creates `gene_group-X/workflow-RUN_01-phylogenetic_analysis/` as a sibling at this STEP_2 directory level
   - Sed-patches `gene_family.name` in its YAML
4. Categorizes by RGS sequence count (small/large tier)
5. Dispatches per `execution_mode`:
   - `local` — sequential nextflow runs
   - `slurm-standard` — 1 sbatch per gene group, standard QOS
   - `slurm-burst` — chunked, 1 sbatch per block, burst QOS

## Configuration

| Setting | Choices | What |
|---------|---------|------|
| `execution_mode` | `local` \| `slurm-standard` \| `slurm-burst` | Dispatch strategy |
| `gene_group_source_tsv` | Path | STEP_0 summary |
| `step1_output_to_input_dir` | Path | Where STEP_1 AGS files live |
| `large_threshold` | Integer | RGS seq count splitting small/large tiers |
| `slurm_*` | Strings/numbers | SLURM identifiers and resources per tier |
| `tree_methods` | Booleans | fasttree / iqtree / veryfasttree / phylobayes |

## Per-gene-group pipeline

NextFlow pipeline:
- Stage AGS → clean dashes → MAFFT align → ClipKit trim → tree (1-4 methods) → log

See `ai/AI_GUIDE-phylogenetic_analysis_workflow.md` for details.

## Outputs

| Output | Location |
|--------|----------|
| Newick trees (per method) | `../gene_group-X/workflow-RUN_01-phylogenetic_analysis/OUTPUT_pipeline/5_{a,b,c,d}-output/*.{fasttree,treefile,veryfasttree,phylobayes.nwk}` |
| Newick symlinks for STEP_3 | `../../../../output_to_input/<source>/STEP_2-phylogenetic_analysis/gene_group-X/*.{fasttree,treefile,veryfasttree,phylobayes.nwk}` |
| Alignment + trimmed alignment | Same OUTPUT_pipeline (3-output, 4-output) |
| SLURM logs | `../slurm_logs/` (when execution_mode is slurm-*) |

## Next step

After STEP_2, the newicks are STEP_3's input. See `../../STEP_3-tree_visualization/`.
