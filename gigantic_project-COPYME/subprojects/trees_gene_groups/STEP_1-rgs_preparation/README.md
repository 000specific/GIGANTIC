# STEP_1: RGS Preparation

Validate Reference Gene Set (RGS) FASTA files before homolog discovery.

## Purpose

Ensures RGS files are properly formatted before running the STEP_2 homolog discovery pipeline. Checks filename conventions, header formats, duplicate sequences, and sequence content.

## Quick Start

```bash
cp -r workflow-COPYME-validate_rgs workflow-RUN_01-validate_rgs
cd workflow-RUN_01-validate_rgs/
# Edit rgs_config.yaml (set gene_group name and rgs_file path)
# Place your RGS FASTA in INPUT_user/
bash RUN-workflow.sh
```

## Optional Step

STEP_1 is recommended but not required. You can provide RGS files directly to STEP_2 via its INPUT_user/ directory.

## Output

Validated RGS files are copied to:
- `output_to_input/rgs_fastas/<gene_group>/rgs-<gene_group>.aa`

## For AI Assistants

See `AI_GUIDE-rgs_preparation.md` for detailed AI guidance.
