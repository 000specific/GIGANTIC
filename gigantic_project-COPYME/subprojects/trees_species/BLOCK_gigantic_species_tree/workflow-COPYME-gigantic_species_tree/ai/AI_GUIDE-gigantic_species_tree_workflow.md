# AI Guide: gigantic_species_tree Workflow (Runbook)

**For AI Assistants**: This is the execution runbook for the `gigantic_species_tree` workflow. Read the BLOCK guide first (`../../AI_GUIDE-gigantic_species_tree.md`) for concepts, then this file for runbook specifics. For trees_species overview see `../../../AI_GUIDE-trees_species.md`. For GIGANTIC overview see `../../../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/trees_species/BLOCK_gigantic_species_tree/workflow-COPYME-gigantic_species_tree/ai/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE-project.md` |
| trees_species concepts | `../../../AI_GUIDE-trees_species.md` |
| BLOCK concepts (structure, standardization, ancestral_clade_NNN, CXXX) | `../../AI_GUIDE-gigantic_species_tree.md` |
| Running the workflow (this guide) | This file |

---

## Step-by-Step Execution

### 1. Copy the template

```bash
cd trees_species/BLOCK_gigantic_species_tree/
cp -r workflow-COPYME-gigantic_species_tree workflow-RUN_01-gigantic_species_tree
cd workflow-RUN_01-gigantic_species_tree
```

### 2. Place your species tree

```bash
cp /path/to/your/species_tree.newick INPUT_user/species_tree.newick
```

Required format (see `INPUT_user/README.md` for full details):
- Leaves: `Genus_species` format
- Internal nodes: optional clade names (`Metazoa`, `Bilateria`, etc.) or unlabeled
- Binary tree (no polytomies)

### 3. Configure

Edit `START_HERE-user_config.yaml`:

```yaml
species_set_name: "species70"    # or whatever identifies your species set
input_files:
  species_tree: "INPUT_user/species_tree.newick"
output:
  base_dir: "OUTPUT_pipeline"
```

### 4. Run

**Local**:
```bash
bash RUN-workflow.sh
```

**SLURM cluster** (edit `--account` and `--qos` in the sbatch file first):
```bash
sbatch RUN-workflow.sbatch
```

### 5. Verify

See verification commands in the next section.

---

## Script Pipeline

| Order | Script | Purpose | Key Input | Key Output |
|-------|--------|---------|-----------|------------|
| 1 | `001_ai-python-validate_input_species_tree.py` | Parse, validate, standardize input | `INPUT_user/species_tree.newick` | `1-output/1_ai-input_species_tree-canonical.newick`, `1_ai-input_user_name_X_gigantic_name.tsv` |
| 2 | `002_ai-python-assign_clade_identifiers.py` | Fill `ancestral_clade_NNN` + assign `CXXX_` | `1-output/1_ai-input_species_tree-canonical.newick` | `2-output/2_ai-species_tree-with_clade_ids_and_names.newick` |
| 3 | `003_ai-python-write_newick_variants.py` | Emit 3 Newick formats | `2-output/2_ai-species_tree-with_clade_ids_and_names.newick` | `3-output/` three variants |
| 4 | `004_ai-python-generate_clade_map.py` | Emit clade map TSV | `2-output/2_ai-species_tree-with_clade_ids_and_names.newick` | `4-output/4_ai-*-clade_name_X_clade_id.tsv` |
| 5 | `005_ai-python-visualize_species_tree.py` | Render SVG (soft-fail) | `2-output/2_ai-species_tree-with_clade_ids_and_names.newick` | `5-output/5_ai-*-species_tree.svg` or placeholder |
| 6 | `006_ai-python-validate_outputs.py` | Cross-validate all outputs | All prior outputs | `6-output/6_ai-validation_report.tsv` |
| 7 | `007_ai-python-write_run_log.py` | Timestamped run log | (metadata only) | `ai/logs/run_*.log` |

**Parallelism**: Scripts 3, 4, and 5 all consume Script 2's output and run in parallel. Script 6 is the synchronization point waiting for all three.

---

## Verification Commands

After the workflow completes, verify outputs:

### Check pipeline completed successfully

```bash
# Final validation report
cat OUTPUT_pipeline/6-output/6_ai-validation_report.tsv

# Run log (replace with actual timestamp)
ls ai/logs/
cat ai/logs/run_*-trees_species_success.log
```

### Check the three Newick variants

```bash
# Simple format (plain Genus_species at leaves)
head -c 200 OUTPUT_pipeline/3-output/3_ai-*-species_tree-simple.newick

# Full format (CXXX_Name everywhere)
head -c 200 OUTPUT_pipeline/3-output/3_ai-*-species_tree-with_clade_ids_and_names.newick

# IDs-only format (CXXX at every node)
head -c 200 OUTPUT_pipeline/3-output/3_ai-*-species_tree-clade_ids_only.newick
```

### Check the clade map

```bash
# First 10 rows of the lookup table
head OUTPUT_pipeline/4-output/4_ai-*-clade_name_X_clade_id.tsv

# Total entries (should equal leaves + internals)
wc -l OUTPUT_pipeline/4-output/4_ai-*-clade_name_X_clade_id.tsv

# Find all ancestral_clade_NNN auto-assigned names
grep ancestral_clade OUTPUT_pipeline/4-output/4_ai-*-clade_name_X_clade_id.tsv
```

### Check the name mapping table

```bash
# See which names were changed during standardization
awk -F'\t' '$4 == "true"' OUTPUT_pipeline/1-output/1_ai-input_user_name_X_gigantic_name.tsv
```

### Check the visualization

```bash
# SVG (normal case)
ls OUTPUT_pipeline/5-output/5_ai-*-species_tree.svg

# OR placeholder (soft-fail case)
ls OUTPUT_pipeline/5-output/5_ai-visualization-placeholder.txt 2>/dev/null && cat OUTPUT_pipeline/5-output/5_ai-visualization-placeholder.txt
```

### Check downstream symlinks

```bash
ls -la ../../output_to_input/BLOCK_gigantic_species_tree/
# Should show symlinks to the three Newick variants + clade map
```

---

## Expected Runtime

| Tree size | Approximate runtime |
|---|---|
| < 100 species | < 30 seconds (excluding NextFlow startup) |
| 100–500 species | < 1 minute |
| 500–5000 species | 1–5 minutes |
| > 5000 species | Possibly several minutes (ete3 visualization dominates) |

The pipeline is dominated by Newick parsing and ete3 visualization. The parsing is linear in tree size; ete3 rendering scales more steeply but is typically still fast for species trees (which are small compared to gene trees).

---

## Common Execution Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Input newick file not found` | `INPUT_user/species_tree.newick` is missing | Place your species tree Newick file in `INPUT_user/` |
| `Configuration file not found: START_HERE-user_config.yaml` | Config file missing or wrong location | Verify `START_HERE-user_config.yaml` exists in the workflow root |
| `CRITICAL ERROR: Non-binary internal node` | Input tree has polytomies | Resolve polytomies manually, or pass the tree to `BLOCK_permutations_and_features` which handles unresolved clades |
| `CRITICAL ERROR: ... collide with the reserved ancestral_clade_NNN namespace` | User-provided name matches the reserved pattern | Rename the conflicting node(s) in `INPUT_user/species_tree.newick` |
| `CRITICAL ERROR: Duplicate leaf (species) names found` | Two leaves have the same name (possibly after standardization) | Check for duplicate species; if two different input names collapsed to the same standardized name, rename one |
| `CRITICAL ERROR: Failed to parse input newick` | Malformed Newick syntax | Check for unmatched parentheses, missing commas, stray characters |
| NextFlow `command not found` | Conda environment not activated | Run `module load conda && conda activate aiG-trees_species-gigantic_species_tree` (or just rerun `bash RUN-workflow.sh` — it activates and on-demand creates the env from `ai/conda_environment.yml`) |
| Visualization placeholder instead of SVG | ete3 tooling unavailable in current env | **Not an error** — visualization is soft-fail. Other outputs are still valid. Investigate `5-output/5_ai-log-visualize_species_tree.log` if you need the SVG. |
| Stale cached results | NextFlow `-resume` used old `work/` | Delete `work/`, `.nextflow/`, `.nextflow.log*` and re-run fresh |

---

## NextFlow Details

- **Pipeline definition**: `ai/main.nf`
- **Configuration**: `ai/nextflow.config` (loads `../START_HERE-user_config.yaml` via SnakeYAML)
- **Work directory**: `work/` (auto-created by NextFlow; safe to delete after success)
- **Resume**: `nextflow run ai/main.nf -resume` to skip already-completed processes

**Clearing cache** (required if scripts were updated):
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-workflow.sh
```

---

## Manual Script Execution (for debugging)

Every script in `ai/scripts/` is runnable standalone with `argparse` arguments. This is useful for debugging or testing outside NextFlow.

```bash
# Script 001: validate input
python3 ai/scripts/001_ai-python-validate_input_species_tree.py \
    --input-newick INPUT_user/species_tree.newick \
    --output-dir OUTPUT_pipeline/1-output

# Script 002: assign clade identifiers
python3 ai/scripts/002_ai-python-assign_clade_identifiers.py \
    --input-newick OUTPUT_pipeline/1-output/1_ai-input_species_tree-canonical.newick \
    --output-dir OUTPUT_pipeline/2-output

# Script 003: write newick variants
python3 ai/scripts/003_ai-python-write_newick_variants.py \
    --input-newick OUTPUT_pipeline/2-output/2_ai-species_tree-with_clade_ids_and_names.newick \
    --species-set-name species70 \
    --output-dir OUTPUT_pipeline/3-output

# Script 004: generate clade map
python3 ai/scripts/004_ai-python-generate_clade_map.py \
    --input-newick OUTPUT_pipeline/2-output/2_ai-species_tree-with_clade_ids_and_names.newick \
    --species-set-name species70 \
    --output-dir OUTPUT_pipeline/4-output

# Script 005: visualize (soft-fail)
export QT_QPA_PLATFORM=offscreen
python3 ai/scripts/005_ai-python-visualize_species_tree.py \
    --input-newick OUTPUT_pipeline/2-output/2_ai-species_tree-with_clade_ids_and_names.newick \
    --species-set-name species70 \
    --output-dir OUTPUT_pipeline/5-output

# Script 006: cross-validate all outputs
python3 ai/scripts/006_ai-python-validate_outputs.py \
    --canonical-newick OUTPUT_pipeline/1-output/1_ai-input_species_tree-canonical.newick \
    --labeled-newick OUTPUT_pipeline/2-output/2_ai-species_tree-with_clade_ids_and_names.newick \
    --simple-newick OUTPUT_pipeline/3-output/3_ai-species70-species_tree-simple.newick \
    --full-newick OUTPUT_pipeline/3-output/3_ai-species70-species_tree-with_clade_ids_and_names.newick \
    --ids-only-newick OUTPUT_pipeline/3-output/3_ai-species70-species_tree-clade_ids_only.newick \
    --clade-map OUTPUT_pipeline/4-output/4_ai-species70-clade_name_X_clade_id.tsv \
    --visualization-dir OUTPUT_pipeline/5-output \
    --output-dir OUTPUT_pipeline/6-output

# Script 007: run log
python3 ai/scripts/007_ai-python-write_run_log.py \
    --workflow-name gigantic_species_tree \
    --subproject-name trees_species \
    --species-set-name species70 \
    --status success \
    --leaf-count 70 \
    --internal-count 69
```

---

## What Happens After This Workflow

Downstream subprojects consume the labeled species tree from:
```
trees_species/output_to_input/BLOCK_gigantic_species_tree/
├── {species_set}-species_tree-with_clade_ids_and_names.newick    # full format
├── {species_set}-species_tree-simple.newick                       # simple format
├── {species_set}-species_tree-clade_ids_only.newick               # ids-only format
└── {species_set}-clade_name_X_clade_id.tsv                         # clade map
```

**Primary downstream consumer**: `BLOCK_permutations_and_features` (sibling BLOCK
within `trees_species/`). Its `INPUT_user/species_tree.newick` can be a symlink
to the full format tree:
```bash
cd ../../BLOCK_permutations_and_features/workflow-RUN_01-permutations_and_features/INPUT_user/
ln -sf ../../../output_to_input/BLOCK_gigantic_species_tree/{species_set}-species_tree-with_clade_ids_and_names.newick species_tree.newick
```

Or for other downstream subprojects (OCL pipelines), the full format tree and clade map TSV are the canonical references.
