# INPUT_user - User-Provided Inputs

## structure_manifest.tsv

Lists which species tree structure(s) to rank for parsimony.

**Format**: TSV with a single column `structure_id`

**Values**: Three-digit structure identifiers matching `trees_species` output
(e.g., "001", "002", ..., "105")

**Default**: Single structure "001" — which is always the user-provided input
species tree (`trees_species/BLOCK_permutations_and_features/scripts/002`
reserves `structure_001` for the original, canonical topology).

For a parsimony ranking to be meaningful, you almost always want to list
**all 105 structures** (or whatever subset of resolutions of the unresolved
zone you want to compare). Ranking with only one structure produces a
trivially ranked output with that single structure at rank 1.

(For canonical definitions of structure, topology, and the resolved-vs-unresolved
input species tree distinction, see
`../../../../trees_species/README.md` Terminology section.)

**Examples**:
- Rank one structure (trivial sanity-check): just "001"
- Rank all 105 permutations: list "001" through "105" (typical case)
- Rank a subset: list specific structure IDs

## How to Populate

1. Check which structures are available in the upstream OCL output:
   ```
   ls ../../../orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/<run_label>/
   ```
   This should list `structure_001/`, `structure_002/`, ..., `structure_NNN/`.
   Every listed structure should appear in `structure_manifest.tsv` (so the
   ranking covers the full upstream run).

2. Edit `structure_manifest.tsv` to list desired structure IDs (one per line,
   under a `structure_id` header).

3. Edit `START_HERE-user_config.yaml` to set:
   - `run_label` matching the upstream OCL run (e.g., `species70_X_OrthoHMM_GIGANTIC`)
   - `species_set_name` (e.g., `species70`)
   - `inputs.ocl_orthogroups_dir` pointing to that upstream OCL run's output_to_input
   - `execution_mode` (`local` or `slurm`)
