# INPUT_user - User-Provided Inputs

## structure_manifest.tsv

Lists which species tree structure(s) to analyze for origin-conservation-loss.

**Format**: TSV with a single column `structure_id`

**Values**: Three-digit structure identifiers matching trees_species output
(e.g., "001", "002", ..., "105")

**Default**: Single structure "001" (the original input tree topology)

**Examples**:
- Analyze one structure: just "001"
- Analyze all 105 permutations: list "001" through "105"
- Analyze a subset: list specific structure IDs

## How to Populate

1. Check which structures are available in trees_species output:
   `ls ../../../../trees_species/output_to_input/BLOCK_permutations_and_features/Species_Phylogenetic_Blocks/`

2. Edit structure_manifest.tsv to list desired structure IDs (one per line)

3. Edit ocl_config.yaml to set:
   - `run_label` for this exploration
   - `orthogroup_tool` matching your input data
   - `orthogroups_dir` pointing to the correct BLOCK
