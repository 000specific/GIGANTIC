# Workflow Run Summary: species70_X_OrthoHMM

**Status**: ✅ **SUCCESS** -- All 5 scripts completed for 105 structure(s). All validation checks passed. (Scripts 1, 2, 3 fully cached from prior run -- no fresh stats this run)

**Generated**: 2026-05-05 05:23:10

## Configuration

- Run label: `species70_X_OrthoHMM`
- Species set: `species70`
- Orthogroup tool: `OrthoHMM`
- Include FASTA in output: `False`
- Structures requested: **105** (001, 002, 003, 004, 005, 006, 007, 008, 009, 010...)
- Execution mode: `slurm` / parallelism: `local`

---

## Script 001: Prepare Inputs
- **CACHED FROM PRIOR RUN** (105/105 structures complete on disk; no fresh stats from this run)

## Script 002: Determine Origins
- **CACHED FROM PRIOR RUN** (105/105 structures complete on disk; no fresh stats from this run)

## Script 003: Quantify Conservation and Loss (Rule 7 block-states)
- **CACHED FROM PRIOR RUN** (105/105 structures complete on disk; no fresh stats from this run)

## Script 004: Comprehensive OCL Summaries
- Duration: 76s median (75.0s min / 80.0s max across 24 structures)
- Orthogroup summaries: **4,871,856.00** total (202,994.00 min / 202,994.00 median / 202,994.00 max across 24 structures)
- Clades analyzed: **3,336.00** total (139.00 min / 139.00 median / 139.00 max across 24 structures)
- Species analyzed: **1,680.00** total (70.00 min / 70.00 median / 70.00 max across 24 structures)
- Path-state rows (orthogroup x species): **341,029,920.00** total (14,209,580.00 min / 14,209,580.00 median / 14,209,580.00 max across 24 structures)

## Script 005: Validation (Rule 7 fail-fast)
- Duration: 62s median (59.6s min / 66.6s max across 105 structures)
- **ALL validation checks PASSED** (1555979460/1555979460 checks across 105 structure(s))
- Per-check results:
    - Conservation/Loss Arithmetic: 14,595/14,595 pass ✓
    - Cross-Script Consistency: 315/315 pass ✓
    - File Integrity: 945/945 pass ✓
    - No Orphan Orthogroups: 21,314,370/21,314,370 pass ✓
    - Origin in Species Paths: 21,314,370/21,314,370 pass ✓
    - Per-Block Count Consistency: 14,595/14,595 pass ✓
    - Per-Orthogroup Block-State Counts: 21,314,370/21,314,370 pass ✓
    - Phylogenetic Path-State Integrity: 1,492,005,900/1,492,005,900 pass ✓

---

## Primary Output Files

Per-structure orthogroup complete summary (primary downstream file):
```
OUTPUT_pipeline/structure_001/4-output/4_ai-orthogroups-complete_ocl_summary.tsv
OUTPUT_pipeline/structure_002/4-output/4_ai-orthogroups-complete_ocl_summary.tsv
OUTPUT_pipeline/structure_003/4-output/4_ai-orthogroups-complete_ocl_summary.tsv
OUTPUT_pipeline/structure_004/4-output/4_ai-orthogroups-complete_ocl_summary.tsv
OUTPUT_pipeline/structure_005/4-output/4_ai-orthogroups-complete_ocl_summary.tsv
... plus 100 more
```

Downstream symlinks: `../../output_to_input/BLOCK_ocl_analysis/species70_X_OrthoHMM/`

