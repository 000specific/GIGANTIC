# AI Guide: BLOCK_analyze_gene_sizes

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 04 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject): [`../AI_GUIDE.md`](../AI_GUIDE.md) — dual-tier architecture
- Parent (subproject README): [`../README.md`](../README.md)
- This is the **only BLOCK** in gene_sizes; it ships as 2 sibling workflow templates:
  - [`workflow-COPYME-analyze_gene_sizes-all_inclusive/`](workflow-COPYME-analyze_gene_sizes-all_inclusive/) — Tier 1
  - [`workflow-COPYME-analyze_gene_sizes-gene_vs_protein/`](workflow-COPYME-analyze_gene_sizes-gene_vs_protein/) — Tier 2
- Reads FROM:
  - `../../genomesDB/output_to_input/STEP_4-create_final_species_set/` — species set
  - User-provided gene-coordinate TSVs in each workflow's `INPUT_user/`
- Outputs TO:
  - `../output_to_input/BLOCK_analyze_gene_sizes/all_inclusive/` (Tier 1)
  - `../output_to_input/BLOCK_analyze_gene_sizes/gene_vs_protein/` (Tier 2)
- 5 scripts per workflow (001 validate / 002 extract / 003 stats / 004 cross-species summary / 005 `write_run_log` per §45)
- Conda env: `aiG-gene_sizes-analyze_gene_sizes` (shared across both tier templates)

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject concepts,
including the dual-tier architecture. This guide covers the analyze_gene_sizes block
specifically.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE.md` |
| gene_sizes concepts (incl. dual-tier) | `../AI_GUIDE.md` |
| BLOCK overview | This file |
| Running Tier 1 (`all_inclusive`) | `workflow-COPYME-analyze_gene_sizes-all_inclusive/ai/AI_GUIDE.md` |
| Running Tier 2 (`gene_vs_protein`) | `workflow-COPYME-analyze_gene_sizes-gene_vs_protein/ai/AI_GUIDE.md` |

---

## What This Block Does

Analyzes gene structure from user-provided gene-coordinate TSVs to produce size metrics,
genome-wide rankings, and cross-species summaries. This is the only block in the
`gene_sizes` subproject and is implemented as **two parallel workflow templates** —
one per dual-tier output (see the subproject guide for the full tier comparison).

Species without gene structure data are gracefully skipped (three-tier status:
PROCESSED, SKIPPED_NO_DATA, SKIPPED_INCOMPLETE) within each tier.

---

## Directory Structure

```
BLOCK_analyze_gene_sizes/
├── AI_GUIDE.md                     # THIS FILE
├── workflow-COPYME-analyze_gene_sizes-all_inclusive/  # Tier 1 template (15-col input, 7 metrics)
│   ├── README.md
│   ├── RUN-workflow.sh                                # single entry per §29 (local or SLURM via execution_mode YAML)
│   ├── START_HERE-user_config.yaml
│   ├── INPUT_user/                                    # 15-col Tier 1 TSVs
│   ├── OUTPUT_pipeline/
│   └── ai/
└── workflow-COPYME-analyze_gene_sizes-gene_vs_protein/ # Tier 2 template (9-col input, 4 metrics)
    └── (same structure; 9-col Tier 2 TSVs in INPUT_user/)
```

Past pre-dual-tier templates and runs are preserved under
`x_workflow-COPYME-analyze_gene_sizes-pre_dual_tier_<date>/` and
`x_workflow-RUN_1-analyze_gene_sizes-pre_dual_tier_<date>/`.

---

## Pipeline Summary (per tier)

Both tiers run the same 5-script pipeline; only the column count and metric set differ.

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| 001 | Validate gene size inputs | INPUT_user/ TSV files (tier-specific schema) | Species processing status |
| 002 | Extract gene metrics | User-provided gene + (Tier 1) exon + CDS intervals | Per-species gene metrics |
| 003 | Compute ranks and stats | Gene metrics | Ranked metrics, genome summaries |
| 004 | Cross-species summary | All ranked metrics + status | Combined tables |
| 005 | Write run log | Workflow status | Timestamped run log in `ai/logs/` |

Tier-specific column counts:
- **Tier 1 (`all_inclusive`)**: 15-col input → 15-col gene metrics → 7 cross-species metrics
- **Tier 2 (`gene_vs_protein`)**: 9-col input → 11-col gene metrics → 4 cross-species metrics

---

## Output to Downstream

Each tier publishes to its own subdirectory under
`output_to_input/BLOCK_analyze_gene_sizes/` at the subproject root:

```
output_to_input/BLOCK_analyze_gene_sizes/
├── all_inclusive/
│   ├── speciesN_gigantic_gene_metrics/
│   └── speciesN_gigantic_gene_sizes_summary/
└── gene_vs_protein/
    ├── speciesN_gigantic_gene_metrics/
    └── speciesN_gigantic_gene_sizes_summary/
```

The tier subdirectory is derived at runtime from each workflow's directory name
in `RUN-workflow.sh`, so the two tiers never clobber each other. Symlink targets
use absolute paths so they resolve regardless of how the workflow directory is
renamed (COPYME vs RUN_N).

Downstream subprojects choose Tier 1 or Tier 2 based on whether they need
UTR/transcript-aware metrics (Tier 1) or just the universally-comparable subset
(Tier 2 — typically more species).
