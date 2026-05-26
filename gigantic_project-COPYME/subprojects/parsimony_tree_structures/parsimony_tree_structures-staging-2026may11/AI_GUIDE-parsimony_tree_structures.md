# AI Guide: parsimony_tree_structures Subproject

**AI**: Claude Code | Opus 4.7 | 2026 May 11
**Human**: Eric Edsinger

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC
overview, directory structure, and general patterns. This guide covers
parsimony_tree_structures-specific concepts and troubleshooting.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| parsimony_tree_structures concepts, troubleshooting | This file |
| BLOCK_ocl_orthogroups concepts | `BLOCK_ocl_orthogroups/AI_GUIDE-ocl_orthogroups.md` |
| Running the workflow | `BLOCK_ocl_orthogroups/workflow-COPYME-score_structures_by_ocl_orthogroups/ai/AI_GUIDE-score_structures_by_ocl_orthogroups_workflow.md` |

---

## What This Subproject Does

For each candidate species tree `structure_NNN` produced upstream by
`trees_species/`, compute one or more **parsimony scores** that summarize how
much evolutionary change the structure requires to explain the observed OCL
feature data, then rank the structures from most parsimonious to least.

The classical parsimony score is `Score_Total_Losses` — the sum of
`Loss_Events` across all orthogroups (or all annotations, etc.). The
structure with the fewest summed losses minimizes ad-hoc evolutionary events
and is the most parsimonious explanation of the feature data under that tree.

Because `trees_species/` always assigns `structure_001` to the user-provided
input species tree, the ranking directly answers: **is the user's input
species tree better, equal, or worse than every alternative resolution of
its unresolved zone, under this feature set?**

## Conceptual Framing — Why This Subproject Exists

OCL takes (species tree, features) as input and produces (per-feature OCL
events) as output. That mapping is one-to-many: each tree structure produces
its own OCL classification of the same features. The aggregate count of
`L` events across the OCL output for a given structure is the feature-set's
**parsimony cost** of that structure.

`orthogroups_X_ocl/README.md` describes a planned `STEP_2-occams_tree/` that
would do this for orthogroups only. This subproject generalizes that idea:

1. **Feature-agnostic** — the algorithm is identical for orthogroups,
   annotations, gene groups, etc. Each gets its own BLOCK that consumes that
   feature's `output_to_input/` and emits a structure ranking.
2. **Multi-score** — Total Losses is the default, but Conservation/Loss
   ratio, Mean Losses per feature, etc. are reported side-by-side so the
   analyst can interpret the ranking under several scoring choices.
3. **Bootstrap-aware** — orthogroup-level bootstrap resampling produces a
   95% CI on the rank of each structure under `Score_Total_Losses`, so the
   analyst can say not just "structure_017 is best" but "structures
   {017, 042, 088} are statistically tied for best (P > 0.05)".

## Directory Structure

```
parsimony_tree_structures/
├── README.md
├── AI_GUIDE-parsimony_tree_structures.md      # THIS FILE
├── RUN-update_upload_to_server.sh
│
├── output_to_input/                            # Downstream output
│   └── BLOCK_ocl_orthogroups/                  # Contains run_label subdirs
│       └── <run_label>/                        # e.g., species70_X_OrthoHMM_GIGANTIC
│           ├── 4_ai-parsimony_ranking-structures.tsv
│           └── 4_ai-parsimony_best_structure.txt
│
├── upload_to_server/
├── research_notebook/
│
└── BLOCK_ocl_orthogroups/                      # First BLOCK implemented
    ├── AI_GUIDE-ocl_orthogroups.md
    └── workflow-COPYME-score_structures_by_ocl_orthogroups/
        ├── README.md
        ├── RUN-workflow.sh
        ├── START_HERE-user_config.yaml
        ├── INPUT_user/
        │   ├── README.md
        │   └── structure_manifest.tsv
        ├── OUTPUT_pipeline/                    # Created at runtime
        └── ai/
            ├── AI_GUIDE-score_structures_by_ocl_orthogroups_workflow.md
            ├── conda_environment.yml
            ├── main.nf
            ├── nextflow.config
            └── scripts/
                ├── 001_ai-python-validate_inputs.py
                ├── 002_ai-python-aggregate_ocl_per_structure.py
                ├── 003_ai-python-compute_parsimony_scores.py
                ├── 004_ai-python-bootstrap_ranking_confidence.py
                ├── 005_ai-python-rank_structures_and_summarize.py
                ├── 006_ai-python-visualize_ranking.py
                └── 007_ai-python-write_run_log.py
```

### Planned BLOCKs

| BLOCK | Feature | Upstream subproject (output_to_input source) |
|---|---|---|
| `BLOCK_ocl_orthogroups/` | OCL over orthogroups | `orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/` |
| `BLOCK_ocl_annotations/` (planned) | OCL over HMM annotations | `annotations_X_ocl/output_to_input/BLOCK_ocl_analysis/` |
| `BLOCK_ocl_gene_groups/` (planned) | OCL over gene groups | `gene_groups_X_ocl/output_to_input/BLOCK_ocl_analysis/` |
| `BLOCK_comparison/` (planned) | Cross-feature ranking agreement | This subproject's own BLOCK outputs |

Each BLOCK ranks the same set of `structure_NNN` identifiers, so
`BLOCK_comparison/` is a straightforward join on `Structure_ID`.

---

## Key Concepts

### Parsimony Score Variants

| Score column | Formula | Lower / Higher better? | Notes |
|---|---|---|---|
| `Score_Total_Losses` | sum(`Loss_Events`) over all OGs | Lower | Primary parsimony score. |
| `Score_Total_State_Transitions` | total_origins + total_losses | Lower | total_origins == orthogroup_count and is therefore constant across structures, so this varies only with losses. Presented for transparency. |
| `Score_Total_Continued_Absence` | sum(`Continued_Absence_Events`) | Lower | Loosely correlated with losses; higher when tree forces more post-loss inheritance. |
| `Score_Conservation_to_Loss_Ratio` | sum(`Conservation_Events`) / max(1, sum(`Loss_Events`)) | Higher | Robust to division by zero via `max(1, ·)`. |
| `Score_Mean_Losses_Per_Orthogroup` | sum(`Loss_Events`) / orthogroup_count | Lower | Identical ranking to `Score_Total_Losses` (orthogroup_count constant) but easier to compare across feature sets. |

### Bootstrap Confidence

The workflow resamples orthogroups with replacement (default 1000 iterations)
and recomputes `Score_Total_Losses` per structure on each resample. For each
structure, we record:

- `Bootstrap_Mean_Rank`
- `Bootstrap_Rank_CI_Lower_95` / `Bootstrap_Rank_CI_Upper_95`
- `Bootstrap_Pct_Times_Best` — fraction of resamples in which this structure
  had the lowest score.

A structure is reported as **tied with the best** when its
`Bootstrap_Pct_Times_Best` is non-trivial (default >= 5%).

### Structure 001 Is the User's Input Species Tree

`trees_species/BLOCK_permutations_and_features/scripts/002` always reserves
`structure_001` for the original, canonical input topology. The ranking
output therefore directly answers "how does my input tree compare?" — look
up the rank of `structure_001` in the ranking table.

### Run Label Namespacing (COPYME Coexistence)

The same workflow can run multiple times against different
`orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/<run_label>/` upstream
runs (e.g., one OrthoHMM-based run, one OrthoFinder-based run). Each parsimony
run picks up the upstream `run_label` plus its own descriptor and writes to:

```
output_to_input/BLOCK_ocl_orthogroups/<run_label>/
```

So orthogroup-tool comparisons coexist without overwriting.

---

## Upstream Dependencies

| Subproject | What It Provides | Config key |
|-----------|------------------|-------------|
| `trees_species` | `structure_NNN` identifiers + phylogenetic blocks per structure | `inputs.trees_species_dir` |
| `orthogroups_X_ocl` | `4_ai-orthogroups-complete_ocl_summary.tsv` per structure | `inputs.ocl_orthogroups_dir` |

---

## Downstream Dependencies

The primary downstream artifact is `4_ai-parsimony_ranking-structures.tsv`,
which provides per-structure parsimony scores, ranks, and bootstrap confidence.
The companion `4_ai-parsimony_best_structure.txt` names the winning structure
in one line. These are used by:

- A future `BLOCK_comparison/` within this subproject (cross-feature
  ranking agreement).
- Methods/results figures and text in the GIGANTIC paper.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | Missing START_HERE-user_config.yaml | Verify config file exists in workflow directory |
| "Structure manifest empty" | No structure IDs in manifest | Add structure IDs (001-105) to INPUT_user/structure_manifest.tsv |
| "OCL summary file not found for structure_NNN" | `orthogroups_X_ocl` not run for this `run_label` or structure | Verify `inputs.ocl_orthogroups_dir` matches a populated run_label folder under `orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/` |
| "OCL summary missing required column 'Loss_Events'" | Upstream schema drift in `orthogroups_X_ocl/` | Re-run `orthogroups_X_ocl/` with the current code, then re-run this workflow |
| "Bootstrap CI lower > upper" | Numerical edge case in tiny manifests | Use at least 5 structures in the manifest; bootstrap CI is undefined for very small sets |

---

## Key Files

| File | User Edits? | Purpose |
|------|------------|---------|
| `BLOCK_ocl_orthogroups/workflow-COPYME-.../START_HERE-user_config.yaml` | Yes | All configuration: `run_label`, `species_set_name`, `orthogroup_tool`, upstream paths, bootstrap iterations, `execution_mode` (local/slurm), SLURM resources |
| `BLOCK_ocl_orthogroups/workflow-COPYME-.../INPUT_user/structure_manifest.tsv` | Yes | Which `structure_NNN` to score (one ID per line) |
| `BLOCK_ocl_orthogroups/workflow-COPYME-.../RUN-workflow.sh` | No | Single entry point; self-submits to SLURM if `execution_mode: "slurm"` |
| `BLOCK_ocl_orthogroups/workflow-COPYME-.../ai/conda_environment.yml` | No | Per-BLOCK conda env (`aiG-parsimony_tree_structures-ocl_orthogroups`) |
| `BLOCK_ocl_orthogroups/workflow-COPYME-.../ai/main.nf` | No | NextFlow pipeline definition |
| `BLOCK_ocl_orthogroups/workflow-COPYME-.../ai/nextflow.config` | No | NextFlow executor / resource config |

---

## Questions to Ask

| Situation | Ask |
|-----------|-----|
| User wants to run the parsimony ranking | "Which `orthogroups_X_ocl` `run_label` should I read from? (e.g., `species70_X_OrthoHMM_GIGANTIC`)" |
| User wants a subset of structures | "Which structure IDs should I list in `structure_manifest.tsv`? (typical: all 001–105)" |
| User mentions a different feature | "We currently only have `BLOCK_ocl_orthogroups`. Should I create a sister `BLOCK_ocl_annotations` / `BLOCK_ocl_gene_groups` for that feature?" |
| User asks about score interpretation | "Are you looking at `Score_Total_Losses` (default parsimony) or one of the side-by-side variants?" |
