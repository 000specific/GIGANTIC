# research_notebook/

Personal workspace for `parsimony_tree_structures` development.

This directory is for AI-assisted research notes, exploratory analyses,
session documentation, and anything else that supports development of this
subproject but is not itself a workflow input or downstream output.

## Suggested Structure

```
research_notebook/
├── ai_research/                # AI-generated research notes
│   └── sessions/               # Session compactions (extracted via RUN-record_project.sh)
├── planning/                   # Design docs for future BLOCKs (annotations, gene_groups, comparison)
└── exploratory/                # Ad-hoc analyses, draft figures
```

## What Belongs Here

- Design notes for the planned `BLOCK_ocl_annotations/`,
  `BLOCK_ocl_gene_groups/`, and `BLOCK_comparison/`.
- Score variants under consideration but not yet implemented in the pipeline.
- Sanity-check analyses comparing `parsimony_tree_structures` output to
  alternative ranking criteria.
- Session documentation (auto-populated by
  `RUN-clean_and_record_subproject.sh --record-sessions`).

## What Does NOT Belong Here

- Workflow inputs → goes in `BLOCK_*/workflow-COPYME-*/INPUT_user/`
- Workflow outputs → produced inside `BLOCK_*/workflow-RUN_N-*/OUTPUT_pipeline/`
- Downstream-facing data → goes in `output_to_input/`
- Server-bound data → produced via `RUN-update_upload_to_server.sh` into `upload_to_server/`
