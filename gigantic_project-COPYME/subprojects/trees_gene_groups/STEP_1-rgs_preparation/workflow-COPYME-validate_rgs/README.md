# workflow-COPYME-validate_rgs

**AI**: Claude Code | Opus 4.6 | 2026 February 27
**Human**: Eric Edsinger

---

## Purpose

STEP_1 workflow template for validating and preparing RGS (Reference Gene Set) FASTA files for downstream homolog discovery.

**Part of**: STEP_1-rgs_preparation (see `../README.md`)

---

## What This Workflow Does

1. **Validate RGS** (Process 1)
   - Validates filename format (rgsN-name-source-date.ext)
   - Validates FASTA header format (>rgsN-species-source-identifier)
   - Checks sequence count matches header N value
   - Detects duplicate sequence IDs
   - Extracts species short names
   - Creates standardized output and validation report

2. **Export** (Process 2)
   - Copies validated RGS to output_to_input for STEP_2

---

## Usage

**Copy this template to create a run directory:**
```bash
cp -r workflow-COPYME-validate_rgs workflow-RUN_01-validate_rgs
cd workflow-RUN_01-validate_rgs
```

**Prepare input files:**
```bash
# Place your RGS FASTA files in INPUT_user/
cp /path/to/your/rgs_files/*.aa INPUT_user/

# Create RGS manifest (gene_family<TAB>rgs_filename)
nano INPUT_user/rgs_manifest.tsv
```

**Example rgs_manifest.tsv:**
```
innexin_pannexin	rgs3-innexin_pannexin-uniprot-2025november01.aa
piezo	rgs5-piezo-ncbi-2025november15.aa
```

**Run locally:**
```bash
bash RUN-validate_rgs.sh
```

**Run on SLURM:**
```bash
sbatch RUN-validate_rgs.sbatch
```

---

## Prerequisites

- **RGS FASTA files** prepared with proper naming convention
- **NextFlow** installed and available in PATH
- **Python 3** available

---

## Directory Structure

```
workflow-COPYME-validate_rgs/
├── README.md                              # This file
├── RUN-validate_rgs.sh                    # Local runner
├── RUN-validate_rgs.sbatch                # SLURM wrapper
├── rgs_config.yaml                        # Configuration
├── INPUT_user/                            # User-provided RGS files
│   └── rgs_manifest.tsv                   # Gene family manifest
├── OUTPUT_pipeline/                       # Workflow outputs
│   └── <gene_family>/
│       └── 1-output/                      # Validated RGS + report
│           ├── 1_ai-RGS-<family>-validated.aa
│           ├── 1_ai-RGS-<family>-validation_report.txt
│           └── 1_ai-log-validate_rgs-<family>.log
└── ai/
    ├── main.nf                            # NextFlow pipeline
    ├── nextflow.config                    # NextFlow settings
    └── scripts/
        └── 001_ai-python-validate_rgs.py  # Validation script
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Validated RGS | `1-output/1_ai-RGS-<family>-validated.aa` | Validated RGS FASTA |
| Validation report | `1-output/1_ai-RGS-<family>-validation_report.txt` | Detailed validation results |
| Log | `1-output/1_ai-log-validate_rgs-<family>.log` | Execution log |

---

## RGS Naming Convention

**Filename format:**
```
rgsN-gene_family-source-date_YYYYmonthDD.ext
```

**Example:**
```
rgs3-innexin_pannexin-uniprot-2025november01.aa
```

**Header format:**
```
>rgsN-species_short_name-source-identifier
```

**Example:**
```
>rgs3-human-uniprot-Q9NQ92
>rgs3-fly-uniprot-Q9VRG2
>rgs3-worm-uniprot-P34802
```

---

## Next Step

After this workflow completes, proceed to:
```
STEP_2-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/
```
