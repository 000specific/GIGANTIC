# Workflow Run Summary: species70_pfam

**Status**: ✅ **SUCCESS** -- All 5 scripts completed for 105 structure(s). All validation checks passed.

**Generated**: 2026-05-05 02:19:22

## Configuration

- Run label: `species70_pfam`
- Species set: `species70`
- Annotation database: `pfam`
- Annogroup subtypes: single, combo, zero
- Structures requested: **105** (001, 002, 003, 004, 005, 006, 007, 008, 009, 010...)
- Execution mode: `slurm` / parallelism: `local`

---

## Script 001: Create Annogroups
- Duration: 13s median (12.6s min / 14.4s max across 105 structures)
- Annogroups created: **7,765,170** total (73,954 min / 73,954 median / 73,954 max across 105 structures)
- By subtype:
    - combo: 65,512
    - single: 8,442
    - zero: 0
- Species with annotations: **7,560** total (72 min / 72 median / 72 max across 105 structures)
- Annotation database: **pfam**

## Script 002: Determine Origins
- Duration: 1s median (1.1s min / 1.3s max across 105 structures)
- Origins found: **7,765,170** total (73,954 min / 73,954 median / 73,954 max across 105 structures)
- Origins not found: 0 (100% success)
- Single-species annogroups: **4,960,725** total (47,245 min / 47,245 median / 47,245 max across 105 structures)
- Multi-species annogroups: **2,804,445** total (26,709 min / 26,709 median / 26,709 max across 105 structures)
- Distinct origin transition blocks: **14,595** total (139 min / 139 median / 139 max across 105 structures)

## Script 003: Quantify Conservation and Loss (Rule 7 block-states)
- Duration: 4s median (4.2s min / 4.7s max across 105 structures)
- Phylogenetic blocks analyzed: **14,595** total (139 min / 139 median / 139 max across 105 structures)
- Total block-states classified: **268,668,836** total (2,517,698 min / 2,562,628 median / 2,585,014 max across 105 structures)
- Block-state counts:
    P (Inherited Presence / Conservation): **107,161,188** total (1,015,456 min / 1,020,529 median / 1,025,847 max across 105 structures)
    L (Loss event): **36,024,318** total (337,962 min / 343,035 median / 348,353 max across 105 structures)
    X (Inherited Loss): **125,483,330** total (1,154,322 min / 1,196,022 median / 1,228,432 max across 105 structures)

## Script 004: Comprehensive OCL Summaries
- Duration: 26s median (24.9s min / 29.4s max across 105 structures)
- Annogroup summaries (all subtypes): **7,765,170** total (73,954 min / 73,954 median / 73,954 max across 105 structures)
- Clades analyzed: **14,595** total (139 min / 139 median / 139 max across 105 structures)
- Species analyzed: **7,350** total (70 min / 70 median / 70 max across 105 structures)
- Path-state rows (annogroup x species): **543,561,900** total (5,176,780 min / 5,176,780 median / 5,176,780 max across 105 structures)

## Script 005: Validation (Rule 7 fail-fast)
- Duration: 16s median (15.3s min / 17.0s max across 105 structures)
- **ALL validation checks PASSED** (840/840 checks across 105 structure(s))
- Per-check results:
    - Conservation/Loss Arithmetic: 14,595/14,595 pass ✓
    - Cross-Script Consistency: 315/315 pass ✓
    - File Integrity: 945/945 pass ✓
    - No Orphan Annogroups: 7,765,170/7,765,170 pass ✓
    - Origin in Species Paths: 7,765,170/7,765,170 pass ✓
    - Per-Annogroup Block-State Counts: 7,765,170/7,765,170 pass ✓
    - Per-Block Count Consistency: 14,595/14,595 pass ✓
    - Phylogenetic Path-State Integrity: 543,561,900/543,561,900 pass ✓

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

