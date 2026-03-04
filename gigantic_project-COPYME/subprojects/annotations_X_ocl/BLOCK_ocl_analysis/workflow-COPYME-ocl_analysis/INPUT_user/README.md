# INPUT_user - User-Provided Inputs

## structure_manifest.tsv

Tab-separated file listing which phylogenetic tree structures to analyze.

**Format:**
```
structure_id
001
002
003
```

**Column:**
- `structure_id`: Three-digit structure identifier (001-105) from trees_species output

**Default:** Single structure `001` (the original input tree topology).

**To populate:** Check available structures in the trees_species output directory
specified by `trees_species_dir` in `ocl_config.yaml`, then list the desired
structure IDs (one per line after the header).

## Before Running

1. Edit `../ocl_config.yaml` to set:
   - `run_label` (e.g., "Species71_pfam", "Species71_deeploc")
   - `annotation_database` (pfam, gene3d, deeploc, etc.)
   - `annogroup_subtypes` (single, combo, zero - see config for guidance)
   - Input paths to upstream subprojects
2. Verify upstream subprojects have completed:
   - `trees_species` (phylogenetic structures)
   - `annotations_hmms` (annotation database files)
