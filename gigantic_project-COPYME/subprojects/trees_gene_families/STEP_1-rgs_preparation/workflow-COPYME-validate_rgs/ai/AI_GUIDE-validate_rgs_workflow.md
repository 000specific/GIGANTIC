# AI Guide: RGS Validation Workflow

**For AI Assistants**: This guide covers workflow execution. For STEP_1 concepts, see `../../AI_GUIDE-rgs_preparation.md`. For trees_gene_families overview, see `../../../AI_GUIDE-trees_gene_families.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `trees_gene_families/STEP_1-rgs_preparation/workflow-COPYME-validate_rgs/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE-project.md` |
| trees_gene_families concepts | `../../../AI_GUIDE-trees_gene_families.md` |
| STEP_1 concepts | `../../AI_GUIDE-rgs_preparation.md` |
| Running the workflow | This file |

---

## Workflow Naming Convention

| Type | Pattern | Description |
|------|---------|-------------|
| **COPYME** (template) | `workflow-COPYME-validate_rgs` | Template - copy this |
| **RUN** (instance) | `workflow-RUN_XX-validate_rgs` | Numbered copies for actual runs |

```bash
cp -r workflow-COPYME-validate_rgs workflow-RUN_01-validate_rgs
cd workflow-RUN_01-validate_rgs/
```

---

## Architecture: 1 Script, 1 Output Directory

```
workflow-COPYME-validate_rgs/
│
├── README.md
├── RUN-validate_rgs.sh            # Local: bash RUN-validate_rgs.sh
├── RUN-validate_rgs.sbatch        # SLURM: sbatch RUN-validate_rgs.sbatch
├── rgs_config.yaml                # User configuration
│
├── INPUT_user/                    # User places RGS file here
│   ├── rgs_species_map.tsv        # Short name → Genus_species (if needed)
│   └── [rgs FASTA files]
│
├── OUTPUT_pipeline/
│   └── 1-output/                  # Validation results
│       ├── 1_ai-rgs-<family>-validated.aa
│       ├── 1_ai-rgs-<family>-validation_report.txt
│       └── 1_ai-log-validate_rgs-<family>.log
│
└── ai/                            # Internal - users don't touch
    ├── AI_GUIDE-validate_rgs_workflow.md  # THIS FILE
    ├── main.nf
    ├── nextflow.config
    └── scripts/
        └── 001_ai-python-validate_rgs.py
```

### Script Pipeline

| Script | Does | Creates |
|--------|------|---------|
| 001 | Validates RGS filename, headers, sequences, duplicates | `1-output/1_ai-rgs-<family>-validated.aa`, validation report, log |

Then a second NextFlow process copies the validated RGS to output_to_input.

---

## User Workflow

### Step 1: Copy Template

```bash
cp -r workflow-COPYME-validate_rgs workflow-RUN_01-validate_rgs
cd workflow-RUN_01-validate_rgs/
```

### Step 2: Configure

Edit `rgs_config.yaml`:
```yaml
gene_family:
  name: "innexin_pannexin"
  rgs_file: "INPUT_user/rgs3-innexin_pannexin-uniprot-2025november01.aa"
```

### Step 3: Place Input Files

Copy your RGS FASTA file to `INPUT_user/`:
```bash
cp /path/to/your/rgs_file.aa INPUT_user/
```

If your RGS headers use short species names, create `INPUT_user/rgs_species_map.tsv`.

### Step 4: Run

**Local**:
```bash
bash RUN-validate_rgs.sh
```

**SLURM** (edit account/qos first):
```bash
sbatch RUN-validate_rgs.sbatch
```

---

## SLURM Execution Details

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | `YOUR_ACCOUNT` | **Must edit** |
| `--qos` | `YOUR_QOS` | **Must edit** |
| `--mem` | `8gb` | Usually sufficient |
| `--time` | `1:00:00` | Very fast |

---

## Verification Commands

```bash
# Did validation pass?
cat OUTPUT_pipeline/1-output/1_ai-rgs-*-validation_report.txt

# Check validated file
grep -c ">" OUTPUT_pipeline/1-output/1_ai-rgs-*-validated.aa

# Check output_to_input
ls ../../output_to_input/rgs_fastas/*/

# Check log
cat OUTPUT_pipeline/1-output/1_ai-log-validate_rgs-*.log
```

---

## Troubleshooting

### "RGS file not found"

**Cause**: Path in rgs_config.yaml doesn't match actual file location

**Fix**:
```bash
ls INPUT_user/
# Update rgs_config.yaml with correct filename
```

### Validation fails

**Cause**: RGS file has formatting issues

**Diagnose**:
```bash
cat OUTPUT_pipeline/1-output/1_ai-rgs-*-validation_report.txt
```

**Common fixes**:
- Headers must follow `>rgsN-species-source-identifier` pattern
- Remove duplicate sequence IDs
- Ensure sequences are amino acid (not nucleotide)

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-validate_rgs.sh
```

---

## After Successful Run

1. **Verify**: Check validation report shows all sequences passed
2. **Check output_to_input**: `ls ../../output_to_input/rgs_fastas/`
3. **Next step**: Proceed to STEP_2 homolog discovery
