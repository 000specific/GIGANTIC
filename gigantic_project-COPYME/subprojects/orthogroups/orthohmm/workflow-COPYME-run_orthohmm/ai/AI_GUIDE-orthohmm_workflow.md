# AI Guide: OrthoHMM Workflow

**For AI Assistants**: This guide covers workflow execution. For OrthoHMM concepts, see `../../AI_GUIDE-orthohmm.md`. For orthogroups overview, see `../../../AI_GUIDE-orthogroups.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `orthogroups/orthohmm/workflow-COPYME-run_orthohmm/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE-project.md` |
| Orthogroups concepts | `../../../AI_GUIDE-orthogroups.md` |
| OrthoHMM tool overview | `../../AI_GUIDE-orthohmm.md` |
| Running the workflow | This file |

---

## Architecture: 6 Scripts, 6 NextFlow Processes

```
workflow-COPYME-run_orthohmm/
│
├── RUN-orthohmm.sh               # Local: bash RUN-orthohmm.sh
├── RUN-orthohmm.sbatch           # SLURM: sbatch RUN-orthohmm.sbatch
├── orthohmm_config.yaml          # User configuration
│
├── INPUT_user/                    # (empty - reads from genomesDB output_to_input)
│
├── OUTPUT_pipeline/
│   ├── 1-output/   # Validated proteome list
│   ├── 2-output/   # Short-header proteomes + mapping
│   ├── 3-output/   # OrthoHMM clustering results
│   ├── 4-output/   # Summary statistics
│   ├── 5-output/   # Per-species QC
│   └── 6-output/   # GIGANTIC IDs restored + per-species files
│
└── ai/
    ├── AI_GUIDE-orthohmm_workflow.md  # THIS FILE
    ├── main.nf
    ├── nextflow.config
    └── scripts/
        ├── 001_ai-python-validate_and_list_proteomes.py
        ├── 002_ai-python-convert_headers_to_short_ids.py
        ├── 003_ai-bash-run_orthohmm.sh
        ├── 004_ai-python-generate_summary_statistics.py
        ├── 005_ai-python-qc_analysis_per_species.py
        └── 006_ai-python-restore_gigantic_identifiers.py
```

### Script Pipeline

| Process | Script | Does |
|---------|--------|------|
| validate_and_list_proteomes | 001 | Validates proteome directory, creates inventory with sequence counts |
| convert_headers_to_short_ids | 002 | Converts GIGANTIC headers to `Genus_species-N` format for OrthoHMM |
| run_orthohmm | 003 | Runs OrthoHMM HMM-based clustering (heavy compute) |
| generate_summary_statistics | 004 | Calculates orthogroup statistics (sizes, coverage, universal OGs) |
| qc_analysis_per_species | 005 | Per-species coverage analysis, identifies unassigned sequences |
| restore_gigantic_identifiers | 006 | Restores full GIGANTIC IDs, creates per-species assignment files |

---

## User Workflow

### Step 1: Copy Template

```bash
cp -r workflow-COPYME-run_orthohmm workflow-RUN_01-run_orthohmm
cd workflow-RUN_01-run_orthohmm/
```

### Step 2: Configure

Edit `orthohmm_config.yaml`:

```yaml
inputs:
  # Replace speciesN with actual species count (e.g., species69)
  proteomes: "../../../genomesDB/output_to_input/speciesN_gigantic_T1_proteomes"

orthohmm:
  cpus: 100
  evalue: "0.0001"
  single_copy_threshold: "0.5"
```

### Step 3: Run

**Local**:
```bash
module load conda
conda activate ai_gigantic_orthogroups
bash RUN-orthohmm.sh
```

**SLURM** (edit account/qos first):
```bash
sbatch RUN-orthohmm.sbatch
```

---

## SLURM Execution Details

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | `moroz` | **May need to edit** |
| `--qos` | `moroz` | **May need to edit** |
| `--cpus-per-task` | `100` | OrthoHMM benefits from parallelism |
| `--mem` | `700gb` | Large HMM databases |
| `--time` | `200:00:00` | O(n^2) scaling with species count |

---

## Expected Runtime

| Scenario | Duration |
|----------|----------|
| 10 species | 1-4 hours |
| 30 species | 12-48 hours |
| 67 species | 100-200 hours |

Runtime scales roughly O(n^2) with species count due to all-vs-all HMM searches.

---

## Verification Commands

```bash
# Check proteome validation
cat OUTPUT_pipeline/1-output/1_ai-proteome_list.txt | wc -l

# Check header conversion
wc -l OUTPUT_pipeline/2-output/2_ai-header_mapping.tsv
ls OUTPUT_pipeline/2-output/short_header_proteomes/ | wc -l

# Check OrthoHMM completed
wc -l OUTPUT_pipeline/3-output/orthohmm_orthogroups.txt

# Check summary statistics
cat OUTPUT_pipeline/4-output/4_ai-orthohmm_summary_statistics.tsv

# Check per-species QC
cat OUTPUT_pipeline/5-output/5_ai-orthogroups_per_species_summary.tsv

# Check GIGANTIC ID restoration
wc -l OUTPUT_pipeline/6-output/6_ai-orthogroups_gigantic_ids.txt

# Check per-species assignment files
ls OUTPUT_pipeline/6-output/6_ai-per_species/ | wc -l

# Check output_to_input
ls ../../output_to_input/
```

---

## Troubleshooting

### "proteomes directory not found"

**Cause**: genomesDB output_to_input path incorrect or genomesDB not yet complete

**Diagnose**:
```bash
ls ../../../genomesDB/output_to_input/
```

**Fix**: Complete genomesDB STEP_2, or update `proteomes` path in `orthohmm_config.yaml`.

### OrthoHMM out of memory

**Cause**: Large number of species/sequences

**Fix**: Increase SLURM memory. OrthoHMM builds large HMM databases internally.

### OrthoHMM timeout

**Cause**: Many species (O(n^2) scaling)

**Fix**: Increase SLURM time limit. For 67+ species, allow 200+ hours.

### "orthohmm command not found"

**Cause**: Conda environment not activated

**Fix**:
```bash
module load conda
conda activate ai_gigantic_orthogroups
```

### Header mapping mismatch

**Cause**: Proteomes changed between script 002 and 006

**Fix**: Clean and rerun from scratch:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-orthohmm.sh
```

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-orthohmm.sh
```

---

## Per-Species Assignment Files

Script 006 generates per-species files in `6-output/6_ai-per_species/`:

```
6_ai-Homo_sapiens-orthogroups_per_sequence.tsv
6_ai-Mus_musculus-orthogroups_per_sequence.tsv
...
```

Each file lists every sequence for that species with its orthogroup assignment (or `NONE` if unassigned). These files are useful for QC and exploration but may be removed in future versions if not needed by downstream subprojects.

---

## After Successful Run

1. **Verify**: Check orthogroup count and summary statistics
2. **Review QC**: Check per-species coverage in `5-output/`
3. **Check output_to_input**: `ls ../../output_to_input/`
4. **Compare**: If also running OrthoFinder, compare orthogroup counts
5. **Done**: Orthogroups ready for downstream subprojects
