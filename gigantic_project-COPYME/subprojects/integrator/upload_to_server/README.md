<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: Document integrator's publish destination for the project data server.
============================================================================ -->

# integrator/upload_to_server

Curated, collaborator-facing outputs published to the project data server (per
`ai/ai_FYIs/gigantic_conventions.md` §38). Symlinks assembled from each
canonical `workflow-RUN_*/upload_manifest.tsv` by the subproject-level
`RUN-update_upload_to_server.sh`.

**Status (2026-06-09): wired.** Server publishing follows the canonical pattern
(per-RUN `upload_manifest.tsv` + subproject-level `RUN-update_upload_to_server.sh`
invoking the shared `server/ai/update_upload_to_server.py`).

- `BLOCK_annotations_X_orthogroups` publishes its two integration tables (+ the
  orthogroup composition table and the validation report) — manifest template at
  `BLOCK_annotations_X_orthogroups/workflow-COPYME-annotations_X_orthogroups/upload_manifest.tsv`.
- `BLOCK_orthogroups_ocl_X_features` is not yet published (no manifest); it will
  be wired after its first end-to-end run is reviewed.

`integrator` is listed in the server `subproject_order` allowlist. Published
symlinks under this directory are runtime artifacts (gitignored); only this
README + `.gitkeep` ship.

The integrated tables are intended for browsing by Eric Edsinger and Leonid
Moroz (Moroz lab, UF) via the server and direct HiPerGator access.
