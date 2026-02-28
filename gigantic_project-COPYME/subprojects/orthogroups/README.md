# orthogroups - Ortholog Group Identification

**AI**: Claude Code | Opus 4.6 | 2026 February 28
**Human**: Eric Edsinger

---

## Purpose

Identify orthologous gene groups (orthogroups) across species. An orthogroup is a set of genes from different species that descended from a single gene in the last common ancestor.

This subproject provides three complementary tools:

1. **OrthoFinder** - Sequence similarity based ortholog detection (all-vs-all Diamond/BLAST)
2. **OrthoHMM** - Profile HMM based ortholog detection (better sensitivity for divergent sequences)
3. **Broccoli** - Phylogeny-network ortholog detection (fast phylogenetic analysis + label propagation)

---

## Prerequisites

1. **genomesDB complete**: Proteomes in `genomesDB/output_to_input/speciesN_gigantic_T1_proteomes/`
2. **Conda environment**: `ai_gigantic_orthogroups` (contains OrthoFinder, OrthoHMM, Diamond, HMMER, MCL)

---

## Tool Comparison

| Feature | OrthoFinder | OrthoHMM | Broccoli |
|---------|-------------|----------|----------|
| Method | All-vs-all Diamond | Profile HMM | Phylogeny + network |
| Speed | Fast | Slower (O(n^2)) | Moderate |
| Sensitivity | Good for close relatives | Better for divergent sequences | Phylogeny-aware |
| Extra output | Species tree, gene trees, HOGs | HMM profiles for annotation | Chimeric protein detection |
| When to use | Standard comparative genomics | Divergent species, HMM annotation | Gene-fusion detection, quick phylogenies |

**All three tools can be run** - they provide complementary information. Comparing results across methods gives higher confidence in orthogroup assignments.

---

## Quick Start

### OrthoFinder

```bash
cp -r orthofinder/workflow-COPYME-run_orthofinder orthofinder/workflow-RUN_01-run_orthofinder
cd orthofinder/workflow-RUN_01-run_orthofinder/

# Add inputs (see INPUT_user/README.md)
module load conda
conda activate ai_gigantic_orthogroups
bash RUN_orthofinder.sh        # Local
sbatch SLURM_orthofinder.sbatch  # SLURM
```

### OrthoHMM

```bash
cp -r orthohmm/workflow-COPYME-run_orthohmm orthohmm/workflow-RUN_01-run_orthohmm
cd orthohmm/workflow-RUN_01-run_orthohmm/

# Edit orthohmm_config.yaml (set proteomes path)
module load conda
conda activate ai_gigantic_orthogroups
bash RUN-orthohmm.sh          # Local
sbatch RUN-orthohmm.sbatch    # SLURM
```

### Broccoli

```bash
cp -r broccoli/workflow-COPYME-run_broccoli broccoli/workflow-RUN_01-run_broccoli
cd broccoli/workflow-RUN_01-run_broccoli/

# (workflow pending implementation - see broccoli/README.md)
```

---

## Directory Structure

```
orthogroups/
├── README.md                          # This file
├── AI_GUIDE-orthogroups.md            # AI assistant guide
├── TODO.md                            # Subproject tracking
├── RUN-clean_and_record_subproject.sh # Cleanup utility
├── RUN-update_upload_to_server.sh     # Server update utility
│
├── orthofinder/                       # OrthoFinder workspace
│   ├── README.md
│   ├── AI_GUIDE-orthofinder.md
│   ├── user_research/
│   ├── output_to_input/
│   ├── upload_to_server/
│   └── workflow-COPYME-run_orthofinder/
│       ├── RUN_orthofinder.sh
│       ├── SLURM_orthofinder.sbatch
│       ├── INPUT_user/
│       ├── OUTPUT_pipeline/
│       └── ai/
│
├── orthohmm/                          # OrthoHMM workspace
│   ├── README.md
│   ├── AI_GUIDE-orthohmm.md
│   ├── user_research/
│   ├── output_to_input/
│   ├── upload_to_server/
│   └── workflow-COPYME-run_orthohmm/
│       ├── RUN-orthohmm.sh
│       ├── RUN-orthohmm.sbatch
│       ├── orthohmm_config.yaml
│       ├── INPUT_user/
│       ├── OUTPUT_pipeline/
│       └── ai/
│
└── broccoli/                          # Broccoli workspace (pending implementation)
    ├── README.md
    ├── AI_GUIDE-broccoli.md
    ├── user_research/
    ├── output_to_input/
    ├── upload_to_server/
    └── workflow-COPYME-run_broccoli/
        ├── INPUT_user/
        ├── OUTPUT_pipeline/
        └── ai/
```

---

## Outputs

| Tool | Output | Location |
|------|--------|----------|
| OrthoFinder | Orthogroups.tsv | `orthofinder/output_to_input/` |
| OrthoFinder | Species tree, HOGs | `orthofinder/output_to_input/` |
| OrthoHMM | orthogroups_gigantic_ids.txt | `orthohmm/output_to_input/` |
| OrthoHMM | gene_count_gigantic_ids.tsv | `orthohmm/output_to_input/` |
| OrthoHMM | header_mapping.tsv | `orthohmm/output_to_input/` |
| Broccoli | orthologous_groups.txt | `broccoli/output_to_input/` (pending) |
| Broccoli | chimeric_proteins.txt | `broccoli/output_to_input/` (pending) |

---

## Orthogroup Output Formats

### OrthoFinder Orthogroups.tsv
```
OG0000001: gene1_speciesA gene2_speciesA gene1_speciesB gene3_speciesC
OG0000002: gene5_speciesA gene4_speciesB gene6_speciesC gene7_speciesC
```

### OrthoHMM orthohmm_orthogroups.txt
```
OrthoHMM0001	gene1_speciesA,gene2_speciesA,gene1_speciesB
OrthoHMM0002	gene5_speciesA,gene4_speciesB,gene6_speciesC
```

### Broccoli orthologous_groups.txt
```
#OG_name	protein_names
OG_0001	gene1_speciesA gene2_speciesA gene1_speciesB
OG_0002	gene5_speciesA gene4_speciesB gene6_speciesC
```

---

## Dependencies

All dependencies are provided by the `ai_gigantic_orthogroups` conda environment:

```bash
# Activate before running workflows
module load conda
conda activate ai_gigantic_orthogroups
```

---

## See Also

- `orthofinder/README.md` - OrthoFinder details
- `orthohmm/README.md` - OrthoHMM details
- `broccoli/README.md` - Broccoli details
- `AI_GUIDE-orthogroups.md` - AI assistant guidance
- `TODO.md` - Open items and tracking
