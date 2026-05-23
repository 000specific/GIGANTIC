# AI_GUIDE - Publishing Subproject Data to the GIGANTIC Server

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 05 01:00
Human:   Eric Edsinger
Purpose: How to publish a subproject's pipeline outputs to the GIGANTIC data
         server. Covers manifest format, the canonical-RUN gotcha, the
         pre-flight checks, the dry-run / live-run procedure, and known
         pitfalls. Companion to AI_GUIDE-server.md (server-side config).
Scope:   Subproject-agnostic. Examples reference trees_gene_families because
         that is the subproject this guide was written from.
History:
  2026-05-05 01:00  Initial version (Opus 4.7). Distilled from the
                    trees_gene_families publish on 2026-05-05 that fixed the
                    30-of-76 partial-publish state to 68-of-76 complete.
============================================================================ -->

**For AI Assistants**: Read `../AI_GUIDE-project.md` first for GIGANTIC overview. This guide covers the *publishing process* — how a subproject's pipeline outputs reach the server. For server-side operation (start/stop, config), see `AI_GUIDE-server.md`.

| You need... | Go to... |
|---|---|
| GIGANTIC overview, directory structure | `../AI_GUIDE-project.md` |
| Server start/stop, config, troubleshooting | `AI_GUIDE-server.md` |
| Publishing subproject data to the server | This file |
| Subproject-specific quirks | `../subprojects/<name>/AI_GUIDE-<name>.md` |

## Architecture

```
per-workflow upload_manifest.tsv      ┐
  (one per workflow-RUN_*/ dir)       │
                                      ├── <subproject>/RUN-update_upload_to_server.sh
gigantic_project-COPYME/server/ai/    │   (thin wrapper around shared helper)
  update_upload_to_server.py          ┘
                                      │
                                      v
<subproject>/upload_to_server/<unit>/STEP_*/workflow-RUN_*/N-output/
  <symlinks to actual output files>
  .section_metadata.tsv  (auto-generated sidecar for the UI)
                                      │
                                      v
gigantic_server.py reads upload_to_server/ directly
  (auto-refreshes every refresh_interval_seconds — default 300s — no restart)
```

The server is a long-running SLURM job (job name `gigantic_server`). For data updates you do not touch it — publish, wait up to 5 min, refresh the browser.

## Discovery rules (important)

The shared helper does `rglob('upload_manifest.tsv')` over the subproject and **only processes manifests whose direct parent dir name starts with `workflow-RUN_`**:

- `workflow-COPYME-*/upload_manifest.tsv` — **ignored** (template only)
- `workflow-RUN_1-*/upload_manifest.tsv` — **picked up**
- `workflow-RUN_2-*/upload_manifest.tsv` — **also picked up**

That last point is the canonical-RUN gotcha (next section).

## Manifest format

Tab-separated, header row required, lives at `<workflow-RUN_*>/upload_manifest.tsv`:

| column | meaning |
|---|---|
| `source_path` | glob, relative to the workflow dir (e.g. `OUTPUT_pipeline/3-output/*.mafft`) |
| `include` | `yes` or `no` (only `yes` publishes; `no` is silently skipped) |
| `dest_name` | optional override of filename in `upload_to_server/` (blank = source basename) |
| `display_label` | UI title (blank = filename) |
| `file_category` | grouping label — suggested set: `tree`, `alignment`, `visualization`, `qc`, `summary`, `sequences` |
| `description` | UI tooltip / subtitle |
| `order` | integer sort key within category (lower = earlier; default 100) |

Lines starting with `#` are comments. Each subproject's per-step COPYME template lives at `<subproject>/<unit>_COPYME/STEP_N-*/workflow-COPYME-*/upload_manifest.tsv`.

## The canonical-RUN problem (CRITICAL — research integrity)

When a workflow fails and gets retried, you can end up with `workflow-RUN_1`, `workflow-RUN_2`, `workflow-RUN_3` in the same step directory. The "real" outputs live in the latest successful one, and `<subproject>/output_to_input/<unit>/STEP_*/` symlinks point to it. That target RUN is **canonical**. The others are stale.

If you place a manifest in a stale RUN dir, the helper publishes whatever partial outputs are in it, side-by-side with the canonical RUN, with no UI hint that one is stale. Collaborators see two trees / two alignments for the same unit with no idea which is current. **This is a research-integrity failure under CLAUDE.md's zero-tolerance rule for silent artifacts.**

**Rule: only place a manifest in the canonical RUN per unit.**

How to find canonical (example for `trees_gene_families`, key file = `*.fasttree`; adapt the file pattern to other subprojects):

```bash
SUB=<subproject>
for d in $SUB/output_to_input/*/; do
  fam=$(basename "$d")
  ftraw=$(ls $d/STEP_2-phylogenetic_analysis/*.fasttree 2>/dev/null | head -1)
  if [ -L "$ftraw" ]; then
    canonical=$(readlink "$ftraw" | grep -oE 'workflow-RUN_[0-9]+')
    echo "$fam -> $canonical"
  fi
done
```

Most are `workflow-RUN_1`. The exceptions need explicit handling. Verify no manifests sit in non-canonical RUN dirs:

```bash
find $SUB -path '*/workflow-RUN_*/upload_manifest.tsv' \
  | while read m; do
      run=$(echo "$m" | grep -oE 'workflow-RUN_[0-9]+')
      fam=$(echo "$m" | sed 's|.*/<unit>-||;s|/STEP_.*||')
      # cross-check against canonical map; report any mismatch
    done
```

## Procedure

### 1. Pre-flight survey (do not skip)

Answer these before touching anything:

- How many units (gene families, species sets, etc.) have completed outputs? (`ls <subproject>/output_to_input/`)
- How many `workflow-RUN_*` dirs exist per step? Extras = stale candidates.
- Which RUN is canonical per unit? (use the symlink-readlink trick above)
- Are there units with partial outputs that should NOT publish? (compare what's in `OUTPUT_pipeline/` vs what the manifest globs would catch)

### 2. Decide manifest defaults with the user

Common COPYME defaults for trees_gene_families (other subprojects similar):

| File category | Default | Notes |
|---|---|---|
| Tree newicks (FastTree, IQ-TREE, VeryFastTree, PhyloBayes) | `yes` | Primary scientific artifact |
| MAFFT alignment | `no` | Flip on for transparency |
| ClipKit-trimmed alignment | `no` | The actual tree input — useful for reproducibility |
| IQ-TREE companion (`.contree`, `.iqtree` report) | `no` | Optional QC |
| STEP_1 final FASTA (e.g. AGS) | `yes` (template) | Many old STEP_1 RUN dirs lack manifests entirely |
| STEP_3 visualizations (PDF, SVG, summary) | `yes` | Default for collaborator browsing |

**Do NOT silently flip defaults.** Surface every category to the user and ask. Document the resulting choices in your conversation.

### 3. Edit the COPYME manifest(s)

Use `Edit` on `<workflow-COPYME-*>/upload_manifest.tsv`. Single source of truth — never hand-edit individual RUN copies.

### 4. Propagate to canonical RUNs only

```bash
SUB=<subproject>
COPYME=$SUB/<unit>_COPYME/STEP_N-<name>/workflow-COPYME-<name>/upload_manifest.tsv

for d in $SUB/output_to_input/*/; do
  unit=$(basename "$d")
  # determine canonical_run for this unit (see "canonical-RUN problem" above)
  canonical_run="workflow-RUN_1-<name>"   # adjust per unit using the symlink-readlink trick
  dest=$SUB/<unit>-${unit}/STEP_N-<name>/${canonical_run}
  cp "$COPYME" "$dest/upload_manifest.tsv"
done
```

For units with no completed output ("stalled"): drop the manifest into RUN_1 — it will publish nothing now and pick up automatically when the workflow finishes.

### 5. Verify no stale manifests remain

```bash
find $SUB -path '*/workflow-RUN_*/upload_manifest.tsv'
# cross-check each path's RUN_N against the canonical map; remove any in non-canonical RUNs
```

### 6. Dry-run

```bash
bash $SUB/RUN-update_upload_to_server.sh --dry-run > /tmp/dryrun.log 2>&1
tail -10 /tmp/dryrun.log   # check Files linked / Warnings
```

Expect a high warnings count — these are empty-glob notices for tree methods you did not run (VeryFastTree, PhyloBayes, partial IQ-TREE coverage, fasttree on stalled units). They are NOT errors. Cross-check by computing expected misses (yes-entries in manifest × units that lack the matching files); the count should match exactly.

`--dry-run` does NOT exercise the stale-prune step unless you also pass `--clean`.

### 7. Live run

```bash
bash $SUB/RUN-update_upload_to_server.sh
```

Automatic: stale-symlink prune, broken-symlink removal, empty-dir cleanup, sidecar `.section_metadata.tsv` regeneration. Output reports:

```
Files linked: <N>
Warnings:     <M>
Stale symlinks removed:  <K>
Broken symlinks removed: <J>
Empty dirs pruned:       <L>
```

### 8. Verify on disk

```bash
find -L $SUB/upload_to_server -type f -name '*.fasttree' | wc -l
find -L $SUB/upload_to_server -type f -name '*.mafft'    | wc -l
# spot-check a unit you know used a non-RUN_1 canonical
```

### 9. Wait

Up to `refresh_interval_seconds` (default 300) for the live server to refresh its file listing. No restart needed.

## Server-side knobs (rarely needed)

`server/START_HERE-server_config.yaml`:

- `subproject_order:` — explicit allowlist of which subprojects appear on landing page
- `show_empty_subprojects: true|false` — show "NO DATA YET" placeholders for listed-but-empty subprojects
- `refresh_interval_seconds: 300` — file-listing refresh interval
- `exclude_file_patterns:` — substrings of filenames to hide (sidecar / state files already excluded)

Restart the server SLURM job only when changing `port`, `subproject_order`, or other config — never just for new data.

## Common errors / red flags

| Symptom | Cause | Fix |
|---|---|---|
| Unit appears empty on the server | No manifest in the canonical RUN, or manifest globs match no files | `find $SUB/<unit>-<name>/STEP_*/workflow-RUN_*/upload_manifest.tsv`; check `OUTPUT_pipeline/` contents |
| Two parallel RUN branches for one unit | Manifest exists in a stale RUN | Delete stale manifest, re-run publisher |
| `Files linked: 0` in real run | All `include=no`, or all globs miss | Inspect manifest content; inspect `OUTPUT_pipeline/` |
| Many broken symlinks | Workflow output moved/deleted | Re-run publisher (auto-cleans broken); fix the sources upstream |
| Server shows old data | Cache TTL not yet elapsed | Wait `refresh_interval_seconds`; or restart server SLURM job |
| Many warnings in dry-run | Tree methods listed `yes` but never ran (VeryFastTree, PhyloBayes, etc.) | Normal — informational, count should match expected misses |

## Reference example: trees_gene_families on 2026-05-05

Recorded as ground truth for future sessions:

- **Trigger**: 38 STEP_3 visualizations had just been rendered, expanding fasttree-PDF coverage from 30 to 68 of 76 families. Before publish: only 30 families on server, STEP_3 PDFs/SVGs only.
- **Manifest changes**: flipped `OUTPUT_pipeline/3-output/*.mafft` from `no` to `yes` in the STEP_2 COPYME. All other defaults preserved.
- **Propagation**: 76 canonical STEP_2 RUN dirs received the updated manifest (75 × `workflow-RUN_1-phylogenetic_analysis` + 1 × `workflow-RUN_2-phylogenetic_analysis` for `gpcr_g_protein_coupled_receptors`). 11 families had stale RUN_2/RUN_3 dirs from prior failed retries; these received no manifest. STEP_3 manifests already byte-identical to COPYME defaults across all 68 RUN_1 dirs — no STEP_3 action needed.
- **Dry-run**: Files linked 0 (dry-run), Warnings 571. The 571 warnings exactly matched predicted empty-glob misses ((76 fams × 5 yes-entries minus actual file presence) + (68 fams × 9 yes-entries minus actual presence)).
- **Live run**: 421 files linked (68 fasttree + 27 treefile + 68 mafft + 95 PDFs + 95 SVGs + 68 summaries), 571 warnings (same), 0 stale, 0 broken, 0 empty pruned.
- **Result on server**: 68 of 76 families visible. The 8 stalled families (`abc_transporters`, `kinases`, `kinases_CAMK`, `kinases_Other`, `kinases_TK`, `phosphatases`, `phosphatases_CC1`, `solute_carriers`) remain empty — their STEP_2 timed out on burst QOS in April and needs longer wall time. Manifests already in place; the next publisher run after STEP_2 finishes will pick them up.
- **Special case**: gpcr — 29,221-sequence family — RUN_1 was a partial failed run with `1-output/`, `2-output/`, `3-output/` only (no fasttree). RUN_2 has the canonical outputs. Manifest only in RUN_2; RUN_1 left alone. Verified on server: only one RUN_2 branch visible for gpcr.

## Reference docs

- `server/README.md` — server quick start
- `server/AI_GUIDE-server.md` — AI assistant guide for server-side operation/troubleshooting
- `../AI_GUIDE-project.md` — project-wide patterns and the AI_GUIDE hierarchy
- `../subprojects/<name>/AI_GUIDE-<name>.md` — per-subproject quirks
- `server/ai/update_upload_to_server.py` — shared helper (authoritative implementation)

## For AI Assistants: Honesty About Mistakes

(See `AI_GUIDE-server.md` for the canonical statement of this principle.) Briefly: when you make an error, say "I was wrong" — do not soften with "that was confusing." Especially relevant in publishing: silently shipping stale or duplicated data to collaborators is a research-integrity issue. Surface every uncertainty before propagating manifests.
