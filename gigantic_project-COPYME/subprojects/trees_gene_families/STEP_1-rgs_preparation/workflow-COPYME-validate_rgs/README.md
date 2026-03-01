# workflow-COPYME-validate_rgs

**AI**: Claude Code | Opus 4.6 | 2026 February 27
**Human**: Eric Edsinger

---

## Purpose

STEP_1 workflow template for validating and preparing a single RGS (Reference Gene Set) FASTA file for downstream homolog discovery. **One gene family per workflow copy.**

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

**Copy this template for each gene family:**
```bash
# For innexin_pannexin:
cp -r workflow-COPYME-validate_rgs workflow-RUN_01-validate_rgs
cd workflow-RUN_01-validate_rgs

# For piezo (separate copy):
cp -r workflow-COPYME-validate_rgs workflow-RUN_02-validate_rgs
```

**Configure your run:**
```bash
# Edit the configuration file - set gene_family name and rgs_file path
nano rgs_config.yaml
```

**Example rgs_config.yaml settings:**
```yaml
gene_family:
  name: "innexin_pannexin"
  rgs_file: "INPUT_user/rgs3-innexin_pannexin-uniprot-2025november01.aa"
```

**Prepare input files:**
```bash
# Place your RGS FASTA file in INPUT_user/
cp /path/to/your/rgs_file.aa INPUT_user/
```

**Run locally:**
```bash
bash RUN-workflow.sh
```

**Run on SLURM:**
```bash
sbatch RUN-workflow.sbatch
```

---

## Prerequisites

- **RGS FASTA file** prepared with proper naming convention
- **NextFlow** installed and available in PATH
- **Python 3** available

---

## Directory Structure

```
workflow-COPYME-validate_rgs/
├── README.md                              # This file
├── RUN-workflow.sh                    # Local runner
├── RUN-workflow.sbatch                # SLURM wrapper
├── rgs_config.yaml                        # Configuration
├── INPUT_user/                            # User-provided RGS file
├── OUTPUT_pipeline/                       # Workflow outputs (flat structure)
│   └── 1-output/                          # Validated RGS + report
│       ├── 1_ai-rgs-<family>-validated.aa
│       ├── 1_ai-rgs-<family>-validation_report.txt
│       └── 1_ai-log-validate_rgs-<family>.log
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
| Validated RGS | `1-output/1_ai-rgs-<family>-validated.aa` | Validated RGS FASTA |
| Validation report | `1-output/1_ai-rgs-<family>-validation_report.txt` | Detailed validation results |
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

After this workflow completes, copy the STEP_2 template and run homolog discovery:
```bash
cd ../../STEP_2-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
```
