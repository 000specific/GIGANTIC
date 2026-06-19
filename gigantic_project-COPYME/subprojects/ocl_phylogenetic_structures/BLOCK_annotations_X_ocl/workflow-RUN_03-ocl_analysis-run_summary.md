# Workflow Run Summary: species70_pfam

**Status**: ✅ **SUCCESS** -- All 5 scripts completed for 105 structure(s). All validation checks passed.

**Generated**: 2026-06-19 04:58:47

## Configuration

- Run label: `species70_pfam`
- Species set: `species70`
- Annotation source: `pfam`
- Structures requested: **105** (001, 002, 003, 004, 005, 006, 007, 008, 009, 010...)
- Execution mode: `slurm` / parallelism: `slurm`

---

## Script 001: Create Annogroups
- Duration: 1s median (0.7s min / 1.5s max across 105 structures)
- Annogroups created: **14,464,905** total (137,761 min / 137,761 median / 137,761 max across 105 structures)
- By type:
    - architecture: 80,280
    - combination: 46,846
    - feature: 10,635
- Annotation source: **pfam**

## Script 002: Determine Origins
- Duration: 5s median (3.2s min / 6.8s max across 105 structures)
- Origins found: **14,464,905** total (137,761 min / 137,761 median / 137,761 max across 105 structures)
- Origins not found: 0 (100% success)
- Single-species annogroups: **8,696,310** total (82,822 min / 82,822 median / 82,822 max across 105 structures)
- Multi-species annogroups: **5,768,595** total (54,939 min / 54,939 median / 54,939 max across 105 structures)
- Distinct origin transition blocks: **14,595** total (139 min / 139 median / 139 max across 105 structures)

## Script 003: Quantify Conservation and Loss (Rule 7 block-states)
- Duration: 17s median (11.3s min / 24.1s max across 105 structures)
- Phylogenetic blocks analyzed: **14,595** total (139 min / 139 median / 139 max across 105 structures)
- Total block-states classified: **582,053,692** total (5,461,942 min / 5,549,836 median / 5,593,634 max across 105 structures)
- Block-state counts:
    P (Inherited Presence / Conservation): **280,239,960** total (2,659,080 min / 2,668,836 median / 2,678,680 max across 105 structures)
    L (Loss event): **69,267,240** total (649,816 min / 659,572 median / 669,416 max across 105 structures)
    X (Inherited Loss): **232,546,492** total (2,134,264 min / 2,217,870 median / 2,279,488 max across 105 structures)

## Script 004: Comprehensive OCL Summaries
- Duration: 107s median (64.3s min / 142.7s max across 105 structures)
- Annogroup summaries (all subtypes): **14,464,905** total (137,761 min / 137,761 median / 137,761 max across 105 structures)
- Clades analyzed: **14,595** total (139 min / 139 median / 139 max across 105 structures)
- Species analyzed: **7,350** total (70 min / 70 median / 70 max across 105 structures)
- Path-state rows (annogroup x species): **1,012,543,350** total (9,643,270 min / 9,643,270 median / 9,643,270 max across 105 structures)

## Script 005: Validation (Rule 7 fail-fast)
- Duration: 53s median (31.2s min / 62.4s max across 105 structures)
- **ALL validation checks PASSED** (840/840 checks across 105 structure(s))
- Per-check results:
    - Conservation/Loss Arithmetic: 14,595/14,595 pass ✓
    - Cross-Script Consistency: 315/315 pass ✓
    - File Integrity: 945/945 pass ✓
    - No Orphan Annogroups: 14,464,905/14,464,905 pass ✓
    - Origin in Species Paths: 14,464,905/14,464,905 pass ✓
    - Per-Annogroup Block-State Counts: 14,464,905/14,464,905 pass ✓
    - Per-Block Count Consistency: 14,595/14,595 pass ✓
    - Phylogenetic Path-State Integrity: 1,012,543,350/1,012,543,350 pass ✓

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

Downstream symlinks: `../../output_to_input/BLOCK_annotations_X_ocl/species70_pfam/`

