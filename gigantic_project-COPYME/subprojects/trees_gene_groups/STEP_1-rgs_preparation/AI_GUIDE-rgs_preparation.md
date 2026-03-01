# AI Guide: STEP_1-rgs_preparation (trees_gene_groups)

**For AI Assistants**: This guide covers STEP_1 of the trees_gene_groups subproject. For subproject overview and three-step architecture, see `../AI_GUIDE-trees_gene_groups.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/STEP_1-rgs_preparation/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| trees_gene_groups concepts | `../AI_GUIDE-trees_gene_groups.md` |
| STEP_1 RGS concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-validate_rgs_workflow.md` |

---

## What This Step Does

**Purpose**: Validate a Reference Gene Set (RGS) FASTA file before running STEP_2 homolog discovery.

**Process**:
1. User provides an RGS FASTA file with curated protein sequences
2. Workflow validates filename format, header format, and sequence content
3. Validated RGS is symlinked to output_to_input for STEP_2 (by RUN-workflow.sh)

**Note**: STEP_1 is optional. Users can also provide RGS files directly to STEP_2 via INPUT_user/. STEP_1 adds validation and standardization.

---

## RGS File Format

### Filename Convention

```
rgsN-gene_group-source-date.aa
```

Example: `rgs3-orthogroup_OG0001234-uniprot-2025november01.aa`

Where N = total number of sequences in the file.

### Header Convention

```
>rgsN-species-source-identifier
```

Example: `>rgs3-human-uniprot-Q9NQ92`

### Species Map

If RGS headers use short species names (e.g., "human", "fly"), provide a species map file:

```
# INPUT_user/rgs_species_map.tsv
human	Homo_sapiens
fly	Drosophila_melanogaster
worm	Caenorhabditis_elegans
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Validated FASTA | `OUTPUT_pipeline/1-output/1_ai-rgs-<group>-validated.aa` | Validated RGS file |
| Validation report | `OUTPUT_pipeline/1-output/1_ai-rgs-<group>-validation_report.txt` | Detailed validation results |
| Log | `OUTPUT_pipeline/1-output/1_ai-log-validate_rgs-<group>.log` | Execution log |

### output_to_input

Validated RGS is published to two locations:

| Level | Path |
|-------|------|
| STEP-level | `output_to_input/rgs_fastas/<gene_group>/rgs-<gene_group>.aa` |
| Subproject-level | `../output_to_input/step_1/rgs_fastas/<gene_group>/rgs-<gene_group>.aa` |

---

## Directory Structure

```
STEP_1-rgs_preparation/
├── AI_GUIDE-rgs_preparation.md     # THIS FILE
├── README.md
├── output_to_input/
│   └── rgs_fastas/                 # Validated RGS by gene group
└── workflow-COPYME-validate_rgs/
    ├── README.md
    ├── RUN-workflow.sh
    ├── RUN-workflow.sbatch
    ├── rgs_config.yaml
    ├── INPUT_user/
    │   ├── rgs_species_map.tsv
    │   └── [rgs FASTA files]
    ├── OUTPUT_pipeline/
    │   └── 1-output/
    └── ai/
        ├── AI_GUIDE-validate_rgs_workflow.md
        ├── main.nf
        ├── nextflow.config
        └── scripts/
            └── 001_ai-python-validate_rgs.py
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/rgs_config.yaml` | Gene group name, RGS file path | **YES** |
| `workflow-*/INPUT_user/*.aa` | RGS FASTA file | **YES** (user provides) |
| `workflow-*/INPUT_user/rgs_species_map.tsv` | Short name to Genus_species mapping | **YES** (if needed) |
| `output_to_input/rgs_fastas/` | Validated RGS | No (auto-created) |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "RGS file not found" | Wrong path in rgs_config.yaml | Check rgs_file path |
| "Invalid header format" | Headers don't match rgsN-species-source-id pattern | Fix headers or update validation |
| "Duplicate sequences" | Same sequence ID appears twice | Remove duplicates from RGS file |
| Validation fails | RGS file has formatting issues | Check validation report for details |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| User wants to skip STEP_1 | "You can place RGS files directly in STEP_2's INPUT_user/. STEP_1 adds validation. Would you like to skip it?" |
| Headers use short names | "Do your RGS headers use short species names (human, fly)? If so, you'll need an rgs_species_map.tsv file." |
| Multiple gene groups | "Each workflow copy handles one gene group. Create one RUN copy per group." |
