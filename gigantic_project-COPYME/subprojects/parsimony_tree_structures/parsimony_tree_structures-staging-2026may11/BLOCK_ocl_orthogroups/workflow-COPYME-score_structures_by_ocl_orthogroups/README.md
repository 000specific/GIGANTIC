# workflow-COPYME-score_structures_by_ocl_orthogroups

Template workflow that ranks species tree structures by parsimony scores
derived from orthogroup OCL data. Copy this directory to a `workflow-RUN_N-...`
sibling before running.

## Quick Start

```bash
# 1. Copy this template
cp -r workflow-COPYME-score_structures_by_ocl_orthogroups \
      workflow-RUN_1-score_structures_by_ocl_orthogroups

# 2. Move into the run dir
cd workflow-RUN_1-score_structures_by_ocl_orthogroups

# 3. Edit configuration
$EDITOR START_HERE-user_config.yaml       # run_label, paths, execution_mode
$EDITOR INPUT_user/structure_manifest.tsv # structure IDs to rank

# 4. Run
bash RUN-workflow.sh
```

## What This Workflow Does

For each `structure_NNN` listed in `INPUT_user/structure_manifest.tsv`:

1. Loads the per-structure complete OCL summary from
   `inputs.ocl_orthogroups_dir/structure_NNN/4_ai-orthogroups-complete_ocl_summary.tsv`
2. Aggregates per-orthogroup `Conservation_Events`, `Loss_Events`,
   `Continued_Absence_Events` into structure-level totals.
3. Computes multiple parsimony scores side-by-side:
   - `Score_Total_Losses` (primary)
   - `Score_Total_State_Transitions`
   - `Score_Total_Continued_Absence`
   - `Score_Conservation_to_Loss_Ratio`
   - `Score_Mean_Losses_Per_Orthogroup`
4. Bootstraps orthogroups (default 1000 iterations) to estimate 95% rank CI
   under `Score_Total_Losses`.
5. Writes the final ranking, identifies the best structure (or set of
   statistically tied structures), and produces colorblind-safe figures.

## Output Layout

```
OUTPUT_pipeline/
├── 1-output/1_ai-input_validation_report.tsv
├── 2-output/
│   ├── 2_ai-aggregate_ocl-per_structure.tsv
│   └── 2_ai-gain_distribution-per_block.tsv
├── 3-output/3_ai-parsimony_scores-per_structure.tsv
├── 4-output/4_ai-bootstrap_confidence-per_structure.tsv     # paired bootstrap (losses + depth)
├── 5-output/
│   ├── 5_ai-parsimony_ranking-structures.tsv      # FINAL dual ranking (Final_Rank_Losses + Final_Rank_Depth)
│   └── 5_ai-parsimony_best_structure.txt          # winning structure under each criterion
├── 6-output/figures/
│   ├── 6_ai-score_total_losses-bar_chart.png
│   ├── 6_ai-shallow_gain-bar_chart.png
│   ├── 6_ai-five_state_counts-stacked_bar.png
│   ├── 6_ai-all_scores-heatmap.png
│   └── 6_ai-rank_agreement-scatter.png
└── 8-output/
    ├── 8_ai-criteria_divergence_summary.txt              # Spearman + Pearson + best-per-criterion
    ├── 8_ai-orthogroup_shifts-user_001_vs_best_by_losses.tsv
    ├── 8_ai-orthogroup_shifts-user_001_vs_best_by_depth.tsv
    ├── 8_ai-orthogroup_shifts-best_by_losses_vs_best_by_depth.tsv
    └── 8_ai-unresolved_zone_topology-per_structure.tsv   # uniform 5-clade newick per structure
```

Downstream-facing symlinks (created by `RUN-workflow.sh` at the end):

```
../../output_to_input/BLOCK_ocl_orthogroups/<run_label>/
    ├── 5_ai-parsimony_ranking-structures.tsv  → OUTPUT_pipeline/5-output/...
    └── 5_ai-parsimony_best_structure.txt      → OUTPUT_pipeline/5-output/...
```

## Configuration

All configuration lives in `START_HERE-user_config.yaml`:

| Key | Description |
|-----|-------------|
| `run_label` | Names the `output_to_input/BLOCK_ocl_orthogroups/<run_label>/` subdir. Conventionally `<upstream_ocl_run_label>` so the parsimony output sits alongside the OCL input. |
| `species_set_name` | e.g., `species70` |
| `orthogroup_tool` | `OrthoFinder` / `OrthoHMM` / `Broccoli` — descriptive only; informs filenames |
| `inputs.ocl_orthogroups_dir` | Path to `orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/<run_label>/` |
| `inputs.trees_species_dir` | Path to `trees_species/output_to_input/BLOCK_permutations_and_features/` |
| `bootstrap_iterations` | Default 1000 |
| `bootstrap_seed` | Default 42 (reproducible bootstrap) |
| `execution_mode` | `local` or `slurm` |
| `slurm_account` / `slurm_qos` | Used only if `execution_mode: "slurm"` |
| `cpus` / `memory_gb` / `time_hours` | SLURM resources |

## Prerequisites

Upstream OCL output must exist:

```
orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/<run_label>/
    structure_001/4_ai-orthogroups-complete_ocl_summary.tsv
    structure_002/4_ai-orthogroups-complete_ocl_summary.tsv
    ...
```

Each summary TSV must contain columns:
`Orthogroup_ID`, `Loss_Events`, `Conservation_Events`,
`Continued_Absence_Events`, `Total_Scored_Blocks`.

Script 001 validates these and fails fast if anything is missing.
