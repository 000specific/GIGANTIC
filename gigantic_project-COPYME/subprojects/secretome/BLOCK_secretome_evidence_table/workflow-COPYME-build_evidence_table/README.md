# workflow-COPYME-build_evidence_table

Builds one wide per-protein **evidence table** TSV per species, pivoting from
the long-format standardized annotation database produced by
`annotations_hmms/BLOCK_build_annotation_database`. Each row in the output is
one protein. Each column group is one annotation tool's evidence for that
protein. Downstream code filters the evidence table into different secretome
variants ( strict, permissive, consensus, etc. ) with simple TSV queries —
no re-running of upstream tools required.

## Workflow inputs

Edit `START_HERE-user_config.yaml`. The workflow reads:

| Source | Path | Purpose |
|---|---|---|
| species manifest | `INPUT_user/proteome_manifest.tsv` | List of phylonames to process + paths to canonical proteome FASTAs |
| annotation database root | `START_HERE-user_config.yaml: annotation_database_dir` | Root of the long-format standardized DB produced by `BLOCK_build_annotation_database` ( contains `database_<name>/gigantic_annotations-database_<name>-<phyloname>.tsv` files ) |

## Workflow outputs

For each species in the manifest:
- `OUTPUT_pipeline/2-output/<phyloname>_evidence_table.tsv` — one row per protein, wide columns per annotation tool
- `OUTPUT_pipeline/2-output/2_ai-log-build_evidence_table_<phyloname>.log` — per-species build log

After successful completion, `RUN-workflow.sh` populates
`../../output_to_input/BLOCK_secretome_evidence_table/` with stable symlinks
to each per-species TSV for downstream subprojects.

## How to run

```
bash RUN-workflow.sh
```

When `execution_mode: "slurm"` in the config, `RUN-workflow.sh` self-submits.

## See also

- `ai/AI_GUIDE-build_evidence_table_workflow.md` — workflow execution detail
- `../AI_GUIDE-secretome_evidence_table.md` — BLOCK overview + schema
- `../../AI_GUIDE-secretome.md` — subproject overview
