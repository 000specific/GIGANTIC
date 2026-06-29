<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: Document the one_direction_homologs upload_to_server tree for the data server.
Scope:   one_direction_homologs/upload_to_server/.
============================================================================ -->

# one_direction_homologs / upload_to_server

Curated deliverables published to the GIGANTIC data server (§38/§39). Built by
[`../RUN-update_upload_to_server.sh`](../RUN-update_upload_to_server.sh), which
reads each `BLOCK_*/workflow-RUN_*/upload_manifest.tsv` and symlinks the included
files here, preserving the `N-output/` structure and writing the server UI's
sidecar metadata.

## How to publish

```bash
cd ..                              # one_direction_homologs subproject root
bash RUN-update_upload_to_server.sh            # (--dry-run to preview)
```

**Canonical-RUN rule (§39)**: only the canonical `workflow-RUN_*` dir's manifest
publishes (manifests in `workflow-COPYME-*` are ignored). To publish, the
`upload_manifest.tsv` must be copied into that canonical RUN dir.

## What gets published

The cross-species NCBI nr hit statistics summary, the per-species hit statistics,
and the per-species top-hits tables (top 10 NCBI nr hits per protein, with
self / non-self classification). See
[`../BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr/upload_manifest.tsv`](../BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr/upload_manifest.tsv)
for the exact list and descriptions.
