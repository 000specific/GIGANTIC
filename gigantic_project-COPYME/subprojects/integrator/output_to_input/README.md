<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: Document what integrator exposes to downstream subprojects.
============================================================================ -->

# integrator/output_to_input

Symlinks to integrator's sharable outputs, for downstream subprojects (per
`ai/ai_FYIs/gigantic_conventions.md` §2). Entries point into the canonical
`workflow-RUN_*/OUTPUT_pipeline/` of each BLOCK; real files never live here.

## Structure

```
output_to_input/
└── BLOCK_orthogroups_ocl_X_features/
    └── <run_label>/                       # e.g. species70_X_OrthoHMM
        └── structure_NNN/
            ├── 2_ai-orthogroups-integrated_summary.tsv      (Table 1)
            ├── 3_ai-block_states-integrated_expanded.tsv    (Table 2)
            └── 4_ai-genes-integrated_drilldown.tsv          (Table 3)
```

`<run_label>` namespaces independent integration runs so they coexist. The
symlinks are created by the BLOCK's `RUN-workflow.sh` after a successful run;
they are gitignored runtime content (only this README + `.gitkeep` ship).
