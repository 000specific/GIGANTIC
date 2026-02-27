# orthogroups - Ortholog Group Identification

**AI**: Claude Code | Opus 4.5 | 2026 February 26
**Human**: Eric Edsinger

---

## Purpose

Identify orthologous gene groups (orthogroups) across species. An orthogroup is a set of genes from different species that descended from a single gene in the last common ancestor.

This subproject provides two complementary tools:

1. **OrthoFinder** - Sequence similarity based ortholog detection (all-vs-all Diamond/BLAST)
2. **OrthoHMM** - Profile HMM based ortholog detection (better sensitivity for divergent sequences)

---

## Prerequisites

1. **genomesDB complete**: Proteomes in `genomesDB/STEP_2.../output_to_input/gigantic_proteomes/`

---

## OrthoFinder vs OrthoHMM

| Feature | OrthoFinder | OrthoHMM |
|---------|-------------|----------|
| Method | All-vs-all Diamond | Profile HMM |
| Speed | Fast | Slower |
| Sensitivity | Good for close relatives | Better for divergent sequences |
| Extra output | Species tree, gene trees | HMM profiles for annotation |
| When to use | Standard comparative genomics | Divergent species, HMM annotation |

**Both tools can be run** - they provide complementary information.

---

## Quick Start

### OrthoFinder

```bash
cd orthofinder/workflow-COPYME-run_orthofinder/

# Copy proteomes
cp /path/to/proteomes/*.aa INPUT_user/

# Run
bash RUN-orthofinder.sh      # Local
sbatch RUN-orthofinder.sbatch # SLURM
```

### OrthoHMM

```bash
cd orthohmm/workflow-COPYME-run_orthohmm/

# Copy proteomes
cp /path/to/proteomes/*.aa INPUT_user/

# Run
bash RUN-orthohmm.sh      # Local
sbatch RUN-orthohmm.sbatch # SLURM
```

---

## Directory Structure

```
orthogroups/
├── README.md                          # This file
├── AI_GUIDE-orthogroups.md            # AI assistant guide
├── RUN-clean_and_record_subproject.sh # Cleanup utility
├── RUN-update_upload_to_server.sh     # Server update utility
│
├── orthofinder/                       # OrthoFinder workspace
│   ├── README.md
│   ├── AI_GUIDE-orthofinder.md
│   ├── workflow-COPYME-run_orthofinder/
│   │   ├── RUN-orthofinder.sh
│   │   ├── RUN-orthofinder.sbatch
│   │   ├── orthofinder_config.yaml
│   │   ├── INPUT_user/
│   │   ├── OUTPUT_pipeline/
│   │   └── ai/
│   ├── output_to_input/
│   ├── upload_to_server/
│   └── user_research/
│
└── orthohmm/                          # OrthoHMM workspace
    ├── README.md
    ├── AI_GUIDE-orthohmm.md
    ├── workflow-COPYME-run_orthohmm/
    │   ├── RUN-orthohmm.sh
    │   ├── RUN-orthohmm.sbatch
    │   ├── orthohmm_config.yaml
    │   ├── INPUT_user/
    │   ├── OUTPUT_pipeline/
    │   └── ai/
    ├── output_to_input/
    ├── upload_to_server/
    └── user_research/
```

---

## Outputs

| Tool | Output | Location |
|------|--------|----------|
| OrthoFinder | Orthogroups.txt | `orthofinder/output_to_input/Orthogroups/` |
| OrthoFinder | Species_Tree | `orthofinder/output_to_input/Species_Tree/` |
| OrthoHMM | orthohmm_orthogroups.txt | `orthohmm/output_to_input/OrthoHMM/` |
| OrthoHMM | orthohmm_gene_count.txt | `orthohmm/output_to_input/OrthoHMM/` |

---

## Orthogroup Output Format

### OrthoFinder Orthogroups.txt
```
OG0000001: gene1_speciesA gene2_speciesA gene1_speciesB gene3_speciesC
OG0000002: gene5_speciesA gene4_speciesB gene6_speciesC gene7_speciesC
```

### OrthoHMM orthohmm_orthogroups.txt
```
OrthoHMM0001	gene1_speciesA,gene2_speciesA,gene1_speciesB
OrthoHMM0002	gene5_speciesA,gene4_speciesB,gene6_speciesC
```

---

## Dependencies

All dependencies are provided by the `ai_gigantic_orthogroups` conda environment:

```bash
# Set up (from project root - run once)
bash RUN-setup_environments.sh

# Activate before running workflows
conda activate ai_gigantic_orthogroups
```

---

## See Also

- `orthofinder/README.md` - OrthoFinder details
- `orthohmm/README.md` - OrthoHMM details
- `AI_GUIDE-orthogroups.md` - AI assistant guidance
