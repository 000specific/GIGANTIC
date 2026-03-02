# AI Guide: BLOCK_analyze_gene_sizes

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read `../AI_GUIDE-gene_sizes.md` first for subproject concepts.
This guide covers the analyze_gene_sizes block specifically.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE-project.md` |
| gene_sizes concepts | `../AI_GUIDE-gene_sizes.md` |
| BLOCK overview | This file |
| Running the workflow | `workflow-COPYME-analyze_gene_sizes/ai/AI_GUIDE-analyze_gene_sizes_workflow.md` |

---

## What This Block Does

Analyzes gene structure from user-provided CDS interval data to produce size metrics,
genome-wide rankings, and cross-species summaries. This is the only block in the
gene_sizes subproject.

Species without gene structure data are gracefully skipped (three-tier status:
PROCESSED, SKIPPED_NO_DATA, SKIPPED_INCOMPLETE).

---

## Directory Structure

```
BLOCK_analyze_gene_sizes/
├── AI_GUIDE-analyze_gene_sizes.md    # THIS FILE
├── RUN-clean_and_record_subproject.sh
├── output_to_input/                  # Canonical downstream output (symlinks)
└── workflow-COPYME-analyze_gene_sizes/
    ├── README.md
    ├── RUN-workflow.sh
    ├── RUN-workflow.sbatch
    ├── gene_sizes_config.yaml
    ├── INPUT_user/                   # User-provided gene structure TSV files
    ├── OUTPUT_pipeline/
    └── ai/
```

---

## Pipeline Summary

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| 001 | Validate gene size inputs | INPUT_user/ TSV files | Species processing status |
| 002 | Extract gene metrics | User-provided CDS intervals | Per-species gene metrics |
| 003 | Compute ranks and stats | Gene metrics | Ranked metrics, genome summaries |
| 004 | Cross-species summary | All ranked metrics + status | Combined tables |

---

## Output to Downstream

This block publishes to `output_to_input/`:
- `speciesN_gigantic_gene_metrics/` - Per-species gene metrics with rank columns
- `speciesN_gigantic_gene_sizes_summary/` - Cross-species summary table and processing status

These are accessed by downstream subprojects via symlinks at the subproject root.
