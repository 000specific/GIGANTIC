# AI Guide: BLOCK_identify_hotspots

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — two-BLOCK sequential pipeline
- Parent (subproject README): [`../README.md`](../README.md)
- Upstream BLOCK: [`../BLOCK_self_blast/`](../BLOCK_self_blast/) (must run first)
- Workflow template: [`workflow-COPYME-identify_hotspots/`](workflow-COPYME-identify_hotspots/)
- This BLOCK's workflow AI guide: [`workflow-COPYME-identify_hotspots/ai/AI_GUIDE.md`](workflow-COPYME-identify_hotspots/ai/AI_GUIDE.md)
- Reads FROM:
  - `../output_to_input/BLOCK_self_blast/self_blast_reports/` (from upstream BLOCK)
  - `../../../research_notebook/research_user/subproject-hotspots/gene_coordinates/` (user-prepared per-species TSVs; per §1 / §17 deviation noted below)
  - `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs TO: `../output_to_input/BLOCK_identify_hotspots/`
- 5 scripts (validate / filter_by_evalue / identify_hotspots / summarize / `write_run_log` per §45)
- Conda env: `aiG-hotspots` (shared with BLOCK_self_blast per §53)

---

## Purpose

Per-species hotspot calling. Reads the per-species self-BLAST reports
produced by BLOCK_self_blast plus the user-provided gene coordinate TSVs
and emits per-species hotspot tables.

## Method

1. Filter self-BLAST hits by stringent e-value (default 1e-60)
2. For each retained hit, check whether query + subject sit within a
   window of N gene-positions on the same chromosome (default 20 genes —
   ±10 around query)
3. Build paralog graph: nodes = genes, edges = (query, subject) pairs
   satisfying step 2
4. Connected components of the graph = hotspots

(Source: Edsinger 2024, *Front. Mar. Sci.*, doi:10.3389/fmars.2024.1434130)

## Pipeline (5 scripts)

| # | Script | Function |
|---|--------|----------|
| 001 | `validate_inputs.py` | Pair every species with its 3 inputs (self-BLAST report, gene_coordinates TSV, proteome); fail-fast on missing |
| 002 | `filter_blast_by_evalue.py` | Per-species: keep hits ≤ 1e-60, drop self-hits |
| 003 | `identify_hotspots.py` | Per-species: window scan + union-find merge → hotspots |
| 004 | `summarize_hotspots.py` | Cross-species aggregate (hotspot counts, size distribution) |
| 005 | `write_run_log.py` | Timestamped run log per §45 |

## §1 + §17 Deviation Note

This BLOCK currently reads `gene_coordinates_dir` from
`../../../../research_notebook/research_user/subproject-hotspots/gene_coordinates/`
(the project-root sandbox per §1 consolidation, 2026-05-26).

Strictly per §17, the workflow should instead read from
`INPUT_user/gene_coordinates/` populated by user-managed symlinks into the
sandbox. Refactoring to that pattern is queued as future work — until
then, the workflow accesses the sandbox directly via the default
`gene_coordinates_dir` YAML param.

The 2026-05-26 path update (from per-subproject `research_notebook/` to
project-root `research_notebook/research_user/subproject-hotspots/`) is
the §1 part of compliance.

## See Also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — subproject overview
- [`../README.md`](../README.md) — method summary + gene_coordinates TSV schema
- [`workflow-COPYME-identify_hotspots/ai/AI_GUIDE.md`](workflow-COPYME-identify_hotspots/ai/AI_GUIDE.md) — workflow execution
- [`../BLOCK_self_blast/AI_GUIDE.md`](../BLOCK_self_blast/AI_GUIDE.md) — upstream BLOCK
