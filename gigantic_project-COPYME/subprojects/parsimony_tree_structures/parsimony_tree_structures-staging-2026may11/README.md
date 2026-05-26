# parsimony_tree_structures

Rank candidate species tree structures by parsimony scores derived from OCL
(Origin-Conservation-Loss) feature data — the tree that requires the fewest
evolutionary changes (e.g., gene-family losses) to explain the data is the
most parsimonious species tree under that feature set.

## What This Subproject Does

`trees_species` produces N candidate species tree **structures** (105 for
species70). For each candidate structure, downstream `*_X_ocl` subprojects
score every feature (orthogroups, annotations, gene groups, ...) into
phylogenetic block-states A / O / P / L / X — origin, presence, loss,
inherited absence, inherited loss.

This subproject inverts that view: it holds the feature set fixed and asks
**which species tree structure minimizes total evolutionary change**.
A structure with fewer summed losses across all features is more parsimonious
— it explains the data with fewer ad-hoc evolutionary events.

Because `trees_species` always assigns `structure_001` to the user-provided
input species tree, the ranking directly reports how the user's input tree
compares to every alternative resolution of the unresolved zone of that tree.

## Design: BLOCK Architecture for Multi-Feature Parsimony

Each feature type is a separate BLOCK so the parsimony ranking is
feature-explicit and the BLOCKs can be compared in a future
`BLOCK_comparison/`.

| BLOCK | Status | Feature consumed | Upstream subproject |
|---|---|---|---|
| `BLOCK_ocl_orthogroups/` | Initial implementation | OCL over orthogroups | `orthogroups_X_ocl/` |
| `BLOCK_ocl_annotations/` | Planned | OCL over HMM annotations | `annotations_X_ocl/` |
| `BLOCK_ocl_gene_groups/` | Planned | OCL over gene groups | `gene_groups_X_ocl/` |
| `BLOCK_comparison/` | Planned | Cross-feature ranking | All of the above |

Each BLOCK produces a ranking of the same set of `structure_NNN` identifiers
(from `trees_species/output_to_input/`), so cross-BLOCK comparison is a
straightforward join on `Structure_ID` in `BLOCK_comparison/`.

## Running the Workflow

Single entry point — `bash RUN-workflow.sh` from inside the workflow
directory. Execution location is controlled by `execution_mode` in
`START_HERE-user_config.yaml`:

- `execution_mode: "local"` → runs on the current machine
- `execution_mode: "slurm"` → self-submits to SLURM with cpus/memory/time/account/qos from the same yaml

The conda environment (`aiG-parsimony_tree_structures-ocl_orthogroups`) is
created on-demand from `ai/conda_environment.yml` on first run — no separate
install step needed.

## Parsimony Scores Reported

For each species tree structure the workflow computes the following per-structure
aggregate scores from the OCL summary table. The ranking table reports them
all side-by-side so the analyst can compare:

| Score | Lower / Higher better? | Interpretation |
|---|---|---|
| `Score_Total_Losses` | Lower | Sum of `Loss_Events` across all orthogroups. Classical loss-minimization parsimony. |
| `Score_Total_State_Transitions` | Lower | `total_origins + total_losses`. Counts every evolutionary event. Origins constant across structures so this varies only by losses (presented for transparency). |
| `Score_Total_Continued_Absence` | Lower | Sum of `Continued_Absence_Events`. Lower means fewer post-loss inheritance blocks; loosely correlated with `Score_Total_Losses`. |
| `Score_Conservation_to_Loss_Ratio` | Higher | `total_conservation / total_losses`. Trees that retain more orthogroups along inheritance paths score higher. |
| `Score_Mean_Losses_Per_Orthogroup` | Lower | `total_losses / orthogroup_count`. Same ranking as Total_Losses (orthogroup count constant) but normalized for cross-run comparison. |

Bootstrap resampling over orthogroups gives a 95% confidence interval on
each structure's rank under `Score_Total_Losses`, identifying which
structures are statistically tied with the best.

## Directory Structure

```
parsimony_tree_structures/
├── README.md                                  # THIS FILE
├── AI_GUIDE-parsimony_tree_structures.md      # AI guidance
├── RUN-update_upload_to_server.sh
│
├── output_to_input/
│   └── BLOCK_ocl_orthogroups/                 # Populated by RUN-workflow.sh symlinks
│       └── <run_label>/                       # e.g., species70_X_OrthoHMM_GIGANTIC
│           ├── 4_ai-parsimony_ranking-structures.tsv
│           └── 4_ai-parsimony_best_structure.txt
│
├── upload_to_server/                          # Server publishing target
├── research_notebook/                         # Personal workspace / RGS notes
│
└── BLOCK_ocl_orthogroups/
    ├── AI_GUIDE-ocl_orthogroups.md
    └── workflow-COPYME-score_structures_by_ocl_orthogroups/
        ├── START_HERE-user_config.yaml
        ├── RUN-workflow.sh                    # Self-submits to SLURM if execution_mode=slurm
        ├── INPUT_user/
        │   ├── README.md
        │   └── structure_manifest.tsv
        ├── OUTPUT_pipeline/                   # Created at runtime
        └── ai/
            ├── conda_environment.yml          # Per-BLOCK env (on-demand create)
            ├── main.nf
            ├── nextflow.config
            ├── AI_GUIDE-score_structures_by_ocl_orthogroups_workflow.md
            └── scripts/                       # 7 Python scripts (001-007)
```

## Dependencies

### parsimony_tree_structures reads FROM:

- `trees_species/output_to_input/BLOCK_permutations_and_features/` —
  authoritative `structure_NNN` identifiers and phylogenetic blocks.
- `orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/<run_label>/` —
  per-structure `4_ai-orthogroups-complete_ocl_summary.tsv` files with
  `Conservation_Events` / `Loss_Events` / `Continued_Absence_Events` per
  orthogroup.

### parsimony_tree_structures provides TO:

- A future `BLOCK_comparison/` within this subproject (cross-feature
  parsimony agreement).
- The methods record of the GIGANTIC project: an Occam's-razor answer to
  "given my orthogroups, which alternative resolution of the unresolved zone
  of my input species tree is best supported?".

## Terminology

For canonical definitions of `phylogenetic` vs `evolutionary`, **structure**
vs **topology**, the resolved-vs-unresolved input species tree distinction,
the species-tree-vs-gene-tree explicitness rule, the topologically-structured
species sets rule for clade IDs, and the phylogenetic block / block-state
five-state vocabulary, see `../trees_species/README.md` (Terminology section)
and Rules 1–7 of `../../AI_GUIDE-project.md`.

Brief summary of the terms used most often here:

- **Structure** (`structure_NNN`): one resolved binary species tree variant
  tracked through `trees_species/`. `structure_001` is always the
  user-provided input species tree.
- **Phylogenetic block**: a parent→child edge on a species tree. The atom on
  which OCL classifies state.
- **Block-state letter**: one of A / O / P / L / X for a (block, feature)
  pair. `L` = loss event; `O` = origin event; `P` = inherited presence
  (conservation); `A` = pre-origin inherited absence; `X` = post-loss
  inherited absence.
- **Parsimony score**: a structure-level aggregate over block-state letters,
  e.g. `Score_Total_Losses` sums `L`s across all orthogroups for one
  structure.
