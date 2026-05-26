# AI Guide: permutations_and_features Workflow

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read the BLOCK guide (`../../AI_GUIDE-permutations_and_features.md`) first.
This guide focuses on running the workflow. The canonical Terminology definitions
(Structure vs Topology, Resolved vs Unresolved input species tree, species-tree-vs-gene-tree
explicitness) live in `../../../README.md`.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE-project.md` |
| trees_species concepts | `../../../AI_GUIDE-trees_species.md` |
| BLOCK overview | `../../AI_GUIDE-permutations_and_features.md` |
| Running this workflow | This file |

---

## Step-by-Step Execution

### Prerequisites
1. Species tree in Newick format with CXXX_Name labels placed in `INPUT_user/species_tree.newick`
2. `START_HERE-user_config.yaml` edited with:
   - `species_set_name` (e.g., "species71")
   - `unresolved_clades` list (clade names matching the Newick tree)
3. Conda environment `aiG-trees_species-permutations_and_features` installed (for Script 008 visualization) — auto-created from `ai/conda_environment.yml` on first run via mamba

### Running

```bash
cd workflow-COPYME-permutations_and_features/

# Local execution
bash RUN-workflow.sh

# SLURM cluster
sbatch RUN-workflow.sbatch
```

### What Happens

1. **Script 001** parses the species tree, extracts components, identifies fixed vs variable structure
2. **Script 002** generates (2N-3)!! topology permutations for unresolved clades
3. **Script 003** assigns persistent CXXX clade identifiers to all topologies
4. **Script 004** builds complete species trees by grafting subtrees onto topology skeletons
5. **Script 005** extracts parent-child (4-col) and parent-sibling (9-col) relationships
6. **Script 006** generates phylogenetic blocks (Parent::Child transitions)
7. **Script 007** integrates all data into 24-column master clade table
8. **Script 008** creates SVG and PDF species tree visualizations (requires ete3)
9. **Script 009** generates clade-to-descendant-species mappings
10. **RUN-workflow.sh** creates symlinks in output_to_input/BLOCK_permutations_and_features/

---

## Script Pipeline

| Process | Script | Key Output |
|---------|--------|------------|
| 1 | 001_ai-python-extract_tree_components.py | `1_ai-tree-metadata.tsv`, `1_ai-tree-clade_registry.tsv`, `1_ai-tree-phylogenetic_paths.tsv` |
| 2 | 002_ai-python-generate_topology_permutations.py | `2_ai-topology_permutations.tsv` |
| 3 | 003_ai-python-assign_clade_identifiers.py | `3_ai-clade_topology_registry.tsv`, `newick_trees/3_ai-structure_XXX_topology_with_clade_ids.newick` |
| 4 | 004_ai-python-build_complete_trees.py | `4_ai-clade_registry.tsv`, `4_ai-phylogenetic_paths-all_structures.tsv`, `newick_trees/4_ai-structure_XXX_complete_tree.newick` |
| 5 | 005_ai-python-extract_parent_child_relationships.py | `{species_set}_Parent_Sibling_Sets/`, `{species_set}_Parent_Child_Relationships/` |
| 6 | 006_ai-python-generate_phylogenetic_blocks.py | `6_ai-phylogenetic_blocks-all_{N}_structures.tsv` |
| 7 | 007_ai-python-integrate_clade_data.py | `7_ai-integrated_clade_data-all_structures.tsv` |
| 8 | 008_ai-python-visualize_species_trees.py | `8_ai-structure_XXX-species_tree.svg/.pdf` |
| 9 | 009_ai-python-generate_clade_species_mappings.py | `9_ai-clade_species_mappings-all_structures.tsv` |

---

## Verification Commands

```bash
# Check pipeline completed (final output)
ls OUTPUT_pipeline/9-output/9_ai-clade_species_mappings-all_structures.tsv

# Check topology count matches expectation (5 unresolved clades = 105)
wc -l OUTPUT_pipeline/2-output/2_ai-topology_permutations.tsv

# Check clade registry
head OUTPUT_pipeline/4-output/4_ai-clade_registry.tsv

# Count complete trees built
ls OUTPUT_pipeline/4-output/newick_trees/*.newick | wc -l

# Check integrated master table columns (should be 24)
head -1 OUTPUT_pipeline/7-output/7_ai-integrated_clade_data-all_structures.tsv | tr '\t' '\n' | wc -l

# Check species tree visualizations
ls OUTPUT_pipeline/8-output/*.svg | wc -l

# Check downstream symlinks
ls ../../output_to_input/BLOCK_permutations_and_features/
```

---

## Expected Runtime

| N Unresolved Clades | Topologies | Approximate Runtime |
|---------------------|------------|---------------------|
| 0 (single species tree, resolved input) | 1 | < 1 minute |
| 3 | 3 | < 1 minute |
| 5 | 105 | 1-5 minutes |
| 7 | 10395 | 10-30 minutes |

Script 008 (visualization) is typically the slowest process due to ete3 rendering.

---

## Common Execution Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Species tree not found` | Missing INPUT_user/species_tree.newick | Place Newick file in INPUT_user/ |
| `Clade 'X' not found in tree` | Unresolved clade name doesn't match Newick labels | Check clade names match exactly (after CXXX_ prefix) |
| `Variable root label: NONE` | No common ancestor found for unresolved clades | Verify unresolved clades share a common ancestor in tree |
| `ete3 library not available` | Conda environment missing or not activated | Rerun `bash RUN-workflow.sh` — it on-demand creates `aiG-trees_species-permutations_and_features` from `ai/conda_environment.yml` if missing |
| `No .newick files found in 4-output` | Script 004 failed | Check 3-output/ has annotated topology skeletons |
| `No parent-sibling table files` | Script 005 failed | Check 4-output/newick_trees/ has complete trees |

---

## Key Files

| File | User Edits? | Purpose |
|------|-------------|---------|
| `START_HERE-user_config.yaml` | Yes | Species set name, unresolved clades, paths |
| `INPUT_user/species_tree.newick` | Yes | Annotated species tree (CXXX_Name:branch_length format) |
| `INPUT_user/clade_names.tsv` | Optional | Clade ID to human-readable name mapping |
| `RUN-workflow.sh` | No | Local runner |
| `RUN-workflow.sbatch` | Yes (account/qos) | SLURM runner |
| `ai/main.nf` | No | Pipeline definition |
| `ai/nextflow.config` | No | Nextflow settings |

---

## Manual Execution (for debugging)

Run individual scripts directly:

```bash
# Run a single script manually
python3 ai/scripts/001_ai-python-extract_tree_components.py --workflow-dir .

# Run with verbose Python output
python3 -u ai/scripts/004_ai-python-build_complete_trees.py --workflow-dir .

# Skip visualization (run scripts 001-007 and 009 manually)
for script_num in 001 002 003 004 005 006 007 009; do
    script=$(ls ai/scripts/${script_num}_ai-python-*.py)
    echo "Running ${script}..."
    python3 "${script}" --workflow-dir .
done
```
