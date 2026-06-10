# Workflow Run Summary: species70_pfam

**Status**: ⚠️ **PARTIAL** -- Incomplete run. Missing fragments: Script 001: 0/105, Script 002: 1/105, Script 003: 1/105, Script 004: 1/105, Script 005: 1/105

**Generated**: 2026-06-06 14:14:24

## Configuration

- Run label: `species70_pfam`
- Species set: `species70`
- Annotation database: `pfam`
- Annogroup subtypes: single, combo, zero
- Structures requested: **105** (001, 002, 003, 004, 005, 006, 007, 008, 009, 010...)
- Execution mode: `slurm` / parallelism: `local`

---

## Script 001: Create Annogroups
- **NOT RUN** (no fragments found for this script)

## Script 002: Determine Origins
- Duration: 1.0s
- Origins found: 73,954
- Origins not found: 0 (100% success)
- Single-species annogroups: 47,245
- Multi-species annogroups: 26,709
- Distinct origin transition blocks: 139

## Script 003: Quantify Conservation and Loss (Rule 7 block-states)
- Duration: 3.6s
- Phylogenetic blocks analyzed: 139
- Total block-states classified: 2,571,352
- Block-state counts:
    P (Inherited Presence / Conservation): 1,018,867
    L (Loss event): 341,373
    X (Inherited Loss): 1,211,112

## Script 004: Comprehensive OCL Summaries
- Duration: 19.6s
- Annogroup summaries (all subtypes): 73,954
- Clades analyzed: 139
- Species analyzed: 70
- Path-state rows (annogroup x species): 5,176,780

## Script 005: Validation (Rule 7 fail-fast)
- Duration: 11.3s
- **ALL validation checks PASSED** (8/8 checks across 1 structure(s))
- Per-check results:
    - Conservation/Loss Arithmetic: 139/139 pass ✓
    - Cross-Script Consistency: 3/3 pass ✓
    - File Integrity: 9/9 pass ✓
    - No Orphan Annogroups: 73,954/73,954 pass ✓
    - Origin in Species Paths: 73,954/73,954 pass ✓
    - Per-Annogroup Block-State Counts: 73,954/73,954 pass ✓
    - Per-Block Count Consistency: 139/139 pass ✓
    - Phylogenetic Path-State Integrity: 5,176,780/5,176,780 pass ✓

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

