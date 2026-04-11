# workflow-COPYME-gigantic_species_tree

**AI**: Claude Code | Opus 4.6 | 2026 April 10
**Human**: Eric Edsinger

---

## Purpose

Standardize and label a user-provided species tree for the GIGANTIC framework.

**Part of**: `trees_species/BLOCK_gigantic_species_tree/` (see `../AI_GUIDE-gigantic_species_tree.md`)

---

## What This Workflow Does

Takes a raw user-supplied Newick species tree (`Genus_species` at leaves, optional
user-provided clade names at internal nodes) and produces a fully standardized,
labeled, validated species tree in all canonical GIGANTIC formats.

1. **Validate Input Species Tree** (Script 001)
   - Parses and validates the Newick syntax
   - Hard-fails on polytomies (the tree must be binary)
   - Replaces invalid characters in user-provided names with underscores
   - Standardizes branch lengths to 1.0 (GIGANTIC convention)
   - Emits a name-mapping table showing every input name alongside its standardized form

2. **Assign Clade Identifiers** (Script 002)
   - Fills in `ancestral_clade_NNN` names for any unlabeled internal nodes
   - Assigns `CXXX_` clade identifier prefixes to every node
     (leaves `C001-CNN` in DFS preorder; internals `C(N+1)+` in BFS from root)

3. **Write Newick Variants** (Script 003)
   - Three formats: simple (`Genus_species` only), full (`CXXX_Name` everywhere),
     and ids-only (`CXXX` only)

4. **Generate Clade Map** (Script 004)
   - TSV lookup table: clade name ↔ clade ID ↔ node kind (leaf or internal)

5. **Visualize Species Tree** (Script 005, SOFT-FAIL)
   - Renders the species tree as SVG using ete3
   - Soft-fails with a placeholder file if ete3 tooling is unavailable

6. **Cross-Validate Outputs** (Script 006)
   - Verifies all outputs are internally consistent

7. **Write Run Log** (Script 007)
   - Timestamped record in `ai/logs/`

---

## Usage

**Copy this template to create a run directory:**
```bash
cp -r workflow-COPYME-gigantic_species_tree workflow-RUN_01-gigantic_species_tree
cd workflow-RUN_01-gigantic_species_tree
```

**Configure your run:**
```bash
# Place your species tree Newick file
cp /path/to/your/species_tree.newick INPUT_user/species_tree.newick

# Edit the configuration
nano START_HERE-user_config.yaml
#   - Set species_set_name (e.g., "species70")
```

**Run locally:**
```bash
bash RUN-workflow.sh
```

**Run on SLURM:**
```bash
# Edit RUN-workflow.sbatch to set --account and --qos
sbatch RUN-workflow.sbatch
```

See `INPUT_user/README.md` for the required species tree format and examples.

---

## Prerequisites

- **Species tree** in Newick format with `Genus_species` at leaves (see `INPUT_user/README.md`)
- **Conda environment**: `ai_gigantic_trees_species` with ete3 + NextFlow installed
- **No upstream dependencies**: this BLOCK is typically the first step for a new species set

---

## Directory Structure

```
workflow-COPYME-gigantic_species_tree/
├── README.md                                 # THIS FILE
├── RUN-workflow.sh                           # Local runner (calls NextFlow)
├── RUN-workflow.sbatch                       # SLURM wrapper
├── START_HERE-user_config.yaml               # User-editable configuration
├── INPUT_user/                               # User inputs
│   ├── README.md                             # Input format documentation
│   └── species_tree.newick                   # Your species tree (you provide)
├── OUTPUT_pipeline/                          # Workflow outputs (auto-created)
│   ├── 1-output/                             # Canonical tree + name mapping + validation
│   ├── 2-output/                             # Fully labeled tree
│   ├── 3-output/                             # Three Newick variants
│   ├── 4-output/                             # Clade map TSV
│   ├── 5-output/                             # Visualization (SVG or placeholder)
│   └── 6-output/                             # Cross-validation report
└── ai/
    ├── AI_GUIDE-gigantic_species_tree_workflow.md   # Detailed runbook
    ├── main.nf                               # NextFlow pipeline definition
    ├── nextflow.config                       # NextFlow settings
    ├── logs/                                 # Run logs (populated on run)
    ├── validation/                           # Validation scripts (future)
    └── scripts/
        ├── 001_ai-python-validate_input_species_tree.py
        ├── 002_ai-python-assign_clade_identifiers.py
        ├── 003_ai-python-write_newick_variants.py
        ├── 004_ai-python-generate_clade_map.py
        ├── 005_ai-python-visualize_species_tree.py
        ├── 006_ai-python-validate_outputs.py
        └── 007_ai-python-write_run_log.py
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Canonical input tree | `1-output/1_ai-input_species_tree-canonical.newick` | User's tree after validation + standardization |
| Input name mapping | `1-output/1_ai-input_user_name_X_gigantic_name.tsv` | Mapping from user names to standardized names |
| Labeled tree | `2-output/2_ai-species_tree-with_clade_ids_and_names.newick` | All nodes labeled `CXXX_Name` |
| Simple Newick | `3-output/3_ai-{species_set}-species_tree-simple.newick` | `Genus_species` at leaves only, internals unlabeled |
| Full Newick | `3-output/3_ai-{species_set}-species_tree-with_clade_ids_and_names.newick` | `CXXX_Name` everywhere |
| IDs-only Newick | `3-output/3_ai-{species_set}-species_tree-clade_ids_only.newick` | `CXXX` at every node |
| Clade map | `4-output/4_ai-{species_set}-clade_name_X_clade_id.tsv` | Lookup table |
| Visualization | `5-output/5_ai-{species_set}-species_tree.svg` | SVG rendering (or placeholder on soft-fail) |
| Cross-validation report | `6-output/6_ai-validation_report.tsv` | Consistency check results |
| Run log | `ai/logs/run_YYYYMMDD_HHMMSS-trees_species_success.log` | Timestamped run record |

---

## Final Outputs in output_to_input/

The workflow automatically creates symlinks in `../../output_to_input/BLOCK_gigantic_species_tree/`:
- `{species_set}-species_tree-with_clade_ids_and_names.newick` - full format (most downstream consumers use this)
- `{species_set}-species_tree-simple.newick` - plain format for external tree viewers
- `{species_set}-species_tree-clade_ids_only.newick` - compact format
- `{species_set}-clade_name_X_clade_id.tsv` - clade map lookup

Where `{species_set}` is the value of `species_set_name` in the config (e.g., `species70`).

---

## Next Steps

After this workflow completes, downstream subprojects can access the labeled species tree from:
```
trees_species/output_to_input/BLOCK_gigantic_species_tree/
```

The most direct downstream consumer is **`BLOCK_permutations_and_features`** (sibling BLOCK within `trees_species/`), which takes the full-format labeled tree and enumerates topology permutations for user-specified unresolved clades.

See `../AI_GUIDE-gigantic_species_tree.md` (BLOCK-level concepts) and
`ai/AI_GUIDE-gigantic_species_tree_workflow.md` (workflow execution runbook) for more detail.
