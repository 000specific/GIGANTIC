# INPUT_user - User-Provided Inputs

## structure_manifest.tsv

Lists which species tree structure(s) to analyze for origin-conservation-loss.

**Format**: TSV with a single column `structure_id`

**Values**: Three-digit structure identifiers matching trees_species output
(e.g., "001", "002", ..., "105")

**Default**: Single structure "001" -- which is always the user-provided input
species tree (trees_species script 002 reserves `structure_001` for the
original, canonical topology).

(For canonical definitions of structure, topology, and the resolved-vs-unresolved
input species tree distinction, see
`../../../../trees_species/README.md` Terminology section.)

**Examples**:
- Analyze one structure: just "001"
- Analyze all 105 permutations: list "001" through "105"
- Analyze a subset: list specific structure IDs

## How to Populate

1. Check which structures are available in trees_species output:
   `ls ../../../../trees_species/output_to_input/BLOCK_permutations_and_features/Species_Phylogenetic_Blocks/`

2. Edit structure_manifest.tsv to list desired structure IDs (one per line)

3. Edit START_HERE-user_config.yaml to set:
   - `run_label` for this exploration (e.g., `species70_pfam`)
   - `species_set_name` (e.g., `species70`)
   - `annotation_database` matching your input data (pfam, gene3d, deeploc, etc.)
   - `annogroup_subtypes` (domain databases: single/combo/zero; simple databases: single only)
   - `annotations_dir` pointing to the correct upstream database directory
   - `execution_mode` (`local` or `slurm`) and if slurm, `slurm_account` / `slurm_qos`
