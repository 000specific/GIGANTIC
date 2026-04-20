# Workflow Run Summary: species70_pfam

**Status**: ✅ **SUCCESS** -- All 5 scripts completed for 105 structure(s). All validation checks passed.

**Generated**: 2026-04-18 14:43:01

## Configuration

- Run label: `species70_pfam`
- Species set: `species70`
- Annotation database: `pfam`
- Annogroup subtypes: single, combo, zero
- Structures requested: **105** (001, 002, 003, 004, 005, 006, 007, 008, 009, 010...)
- Execution mode: `slurm` / parallelism: `local`

---

## Script 001: Create Annogroups
- Duration: 9s median (9.1s min / 9.9s max across 105 structures)
- Annogroups created: **7,767,165** total (73,973 min / 73,973 median / 73,973 max across 105 structures)
- By subtype:
    - combo: 65,528
    - single: 8,445
    - zero: 0
- Species with annotations: **7,560** total (72 min / 72 median / 72 max across 105 structures)
- Annotation database: **pfam**

## Script 002: Determine Origins
- Duration: 0s median (0.6s min / 0.7s max across 105 structures)
- Origins found: **7,767,165** total (73,973 min / 73,973 median / 73,973 max across 105 structures)
- Origins not found: 0 (100% success)
- Single-species annogroups: **4,961,880** total (47,256 min / 47,256 median / 47,256 max across 105 structures)
- Multi-species annogroups: **2,805,285** total (26,717 min / 26,717 median / 26,717 max across 105 structures)
- Distinct origin transition blocks: **14,595** total (139 min / 139 median / 139 max across 105 structures)

## Script 003: Quantify Conservation and Loss (Rule 7 block-states)
- Duration: 3s median (3.0s min / 3.2s max across 105 structures)
- Phylogenetic blocks analyzed: **14,595** total (139 min / 139 median / 139 max across 105 structures)
- Total block-states classified: **268,734,046** total (2,518,272 min / 2,563,236 median / 2,585,670 max across 105 structures)
- Block-state counts:
    P (Inherited Presence / Conservation): **107,182,027** total (1,015,653 min / 1,020,725 median / 1,026,047 max across 105 structures)
    L (Loss event): **36,034,867** total (338,061 min / 343,133 median / 348,455 max across 105 structures)
    X (Inherited Loss): **125,517,152** total (1,154,604 min / 1,196,370 median / 1,228,788 max across 105 structures)

## Script 004: Comprehensive OCL Summaries
- Duration: 16s median (15.9s min / 17.8s max across 105 structures)
- Annogroup summaries (all subtypes): **7,767,165** total (73,973 min / 73,973 median / 73,973 max across 105 structures)
- Clades analyzed: **14,595** total (139 min / 139 median / 139 max across 105 structures)
- Species analyzed: **7,350** total (70 min / 70 median / 70 max across 105 structures)
- Path-state rows (annogroup x species): **543,701,550** total (5,178,110 min / 5,178,110 median / 5,178,110 max across 105 structures)

## Script 005: Validation (Rule 7 fail-fast)
- Duration: 11s median (10.9s min / 12.2s max across 105 structures)
- **ALL validation checks PASSED** (840/840 checks across 105 structure(s))
- Per-check results:
    - Conservation/Loss Arithmetic: 14,595/14,595 pass ✓
    - Cross-Script Consistency: 315/315 pass ✓
    - File Integrity: 945/945 pass ✓
    - No Orphan Annogroups: 7,767,165/7,767,165 pass ✓
    - Origin in Species Paths: 7,767,165/7,767,165 pass ✓
    - Per-Annogroup Block-State Counts: 7,767,165/7,767,165 pass ✓
    - Per-Block Count Consistency: 14,595/14,595 pass ✓
    - Phylogenetic Path-State Integrity: 543,701,550/543,701,550 pass ✓

---

## Primary Output Files

Per-structure all-subtypes summary (primary downstream file):
```
OUTPUT_pipeline/structure_001/4-output/4_ai-structure_001_annogroups-complete_ocl_summary-all_types.tsv
OUTPUT_pipeline/structure_002/4-output/4_ai-structure_002_annogroups-complete_ocl_summary-all_types.tsv
OUTPUT_pipeline/structure_003/4-output/4_ai-structure_003_annogroups-complete_ocl_summary-all_types.tsv
OUTPUT_pipeline/structure_004/4-output/4_ai-structure_004_annogroups-complete_ocl_summary-all_types.tsv
OUTPUT_pipeline/structure_005/4-output/4_ai-structure_005_annogroups-complete_ocl_summary-all_types.tsv
... plus 100 more
```

Downstream symlinks: `../../output_to_input/BLOCK_ocl_analysis/species70_pfam/`

