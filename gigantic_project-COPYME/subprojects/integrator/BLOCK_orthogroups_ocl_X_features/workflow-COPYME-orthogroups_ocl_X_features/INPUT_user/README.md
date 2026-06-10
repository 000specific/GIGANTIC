<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: Describe the user inputs staged for the orthogroups_ocl_X_features
         integration workflow.
============================================================================ -->

# INPUT_user — orthogroups_ocl_X_features

This workflow integrates *already-produced* upstream outputs (OCL orthogroups +
dark/hotspot/secretome features). It therefore needs almost no user-supplied
data — only a choice of **which tree structures to integrate**.

## `structure_manifest.tsv`

TSV with a single column `structure_id`, one structure per line:

```
structure_id
001
002
...
105
```

- The listed structures **must be a subset** of the structures the upstream OCL
  run (`ocl_orthogroups_dir` in `START_HERE-user_config.yaml`) actually produced.
- For a full run, list all 105. For a quick test, list one (`001` — the
  user-provided input species tree; see `trees_species`).

## Everything else comes from upstream `output_to_input/`

All feature data is read from sibling subprojects' `output_to_input/`
directories (paths set in `START_HERE-user_config.yaml`); none of it is staged
here. See the workflow `ai/AI_GUIDE.md` for the full input contract.
