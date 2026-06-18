<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: Document the annogroups upload_to_server tree for the data server.
Scope:   annogroups/upload_to_server/.
============================================================================ -->

# annogroups / upload_to_server

Curated deliverables published to the GIGANTIC data server (§38/§39). Built by
[`../RUN-update_upload_to_server.sh`](../RUN-update_upload_to_server.sh), which
reads each `BLOCK_*/workflow-RUN_*/upload_manifest.tsv` and symlinks the included
files here, preserving the `N-output/` structure and writing the server UI's
sidecar metadata.

## How to publish

```bash
cd ..                              # annogroups subproject root
bash RUN-update_upload_to_server.sh            # (--dry-run to preview)
```

**Canonical-RUN rule (§39)**: only the canonical `workflow-RUN_*` dir's manifest
publishes (manifests in `workflow-COPYME-*` are ignored). To publish, the
`upload_manifest.tsv` must be copied into that canonical RUN dir.

## What gets published

Per source: the annogroup map + membership tables, plus the shared proteome
universe / sources manifest and the per-source validation report and
dropped-orphan audit. See
[`../BLOCK_build_annogroups/workflow-COPYME-build_annogroups/upload_manifest.tsv`](../BLOCK_build_annogroups/workflow-COPYME-build_annogroups/upload_manifest.tsv)
for the exact list and descriptions.
