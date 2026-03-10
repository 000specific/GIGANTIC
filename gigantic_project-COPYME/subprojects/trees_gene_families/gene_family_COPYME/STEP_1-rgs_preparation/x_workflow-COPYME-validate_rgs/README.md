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
   - Validates filename format (rgs_{category}-{species}-{gene_family_details}.ext)
   - Validates FASTA header format (>rgs_{family}-{species}-{gene_symbol}-{source}-{identifier})
   - Checks all headers have consistent rgs_{family} prefix
   - Detects duplicate sequence IDs
   - Extracts species short names
   - Creates standardized output and validation report

2. **Export** (Process 2)
   - Symlinks validated RGS to subproject-root output_to_input/STEP_1-rgs_preparation/ for STEP_2

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
nano START_HERE-user_config.yaml
```

**Example START_HERE-user_config.yaml settings:**
```yaml
gene_family:
  name: "innexin_pannexin"
  rgs_file: "INPUT_user/rgs_channel-human_worm_fly-innexin_pannexin_channels.aa"
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
├── START_HERE-user_config.yaml                        # Configuration
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
rgs_{category}-{species_short_names}-{gene_family_details}.ext
```

**Example:**
```
rgs_channel-human_worm_fly-innexin_pannexin_channels.aa
```

**Header format:**
```
>rgs_{family}-{species}-{gene_symbol}-{source_details}-{sequence_identifier}
```

**Example:**
```
>rgs_innexins-human-PANX1-hgnc_gg305_Pannexin-NP_001229977.1
>rgs_innexins-fly-inx2-user-uniprotQ9VRG2_inx_2
>rgs_innexins-worm-inx_14-user-uniprotP34802_inx_14
```

---

## Next Step

After this workflow completes, copy the STEP_2 template and run homolog discovery:
```bash
cd ../../STEP_2-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
```
