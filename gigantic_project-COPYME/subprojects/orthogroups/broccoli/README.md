# Broccoli - Phylogeny-Network Orthology Inference

**AI**: Claude Code | Opus 4.6 | 2026 February 28
**Human**: Eric Edsinger

**Status**: Skeleton - workflow pending implementation

---

## Purpose

Run Broccoli to identify orthologous groups using a mixed phylogeny-network approach. Broccoli performs ultra-fast phylogenetic analyses on proteins, builds a network of orthologous relationships, and identifies orthogroups using label propagation (a parameter-free machine learning algorithm). It also detects chimeric proteins from gene-fusion events.

**Reference**: Derelle et al. (2020) "Broccoli: Combining Phylogenetic and Network Analyses for Orthology Assignment" *Molecular Biology and Evolution* 37(11):3389-3396.

---

## Prerequisites

1. **genomesDB complete**: Proteomes available in `genomesDB/output_to_input/speciesN_gigantic_T1_proteomes/`
2. **Broccoli installed**: Python 3.6+, ete3 library, Diamond (0.9.30+), FastTree (single-thread version)
3. **Conda environment**: To be determined (may use `ai_gigantic_orthogroups` or a dedicated environment)

---

## Quick Start

```bash
# Copy workflow template to create a run instance
cp -r workflow-COPYME-run_broccoli workflow-RUN_01-run_broccoli
cd workflow-RUN_01-run_broccoli/

# Run locally (ensure conda environment is active)
module load conda  # HiPerGator only
conda activate ai_gigantic_orthogroups
bash RUN-broccoli.sh

# Or run on SLURM (edit account/qos first)
sbatch RUN-broccoli.sbatch
```

**Note**: Workflow scripts not yet implemented. See TODO.md at subproject root.

---

## Broccoli Pipeline (4 Steps)

| Step | Name | Description |
|------|------|-------------|
| 1 | Kmer Clustering | Groups proteins by kmer similarity |
| 2 | Phylomes | Diamond similarity search + phylogenetic tree construction |
| 3 | Network Analysis | Builds orthology network, identifies orthogroups and chimeric proteins |
| 4 | Orthologous Pairs | Identifies pairwise ortholog relationships |

---

## Key Outputs (from Broccoli dir_step3/)

| Output | File | Description |
|--------|------|-------------|
| Orthogroups | `orthologous_groups.txt` | Gene family assignments (OG ID + member proteins) |
| Protein counts | `table_OGs_protein_counts.txt` | Matrix of species vs orthogroups with counts |
| Protein names | `table_OGs_protein_names.txt` | Matrix of species vs orthogroups with protein names |
| Chimeric proteins | `chimeric_proteins.txt` | Gene-fusion events detected |
| Unclassified | `unclassified_proteins.txt` | Proteins not assigned to any orthogroup |
| Statistics | `statistics_per_OG.txt` | Per-orthogroup metrics |
| Per-species stats | `statistics_per_species.txt` | Assignment rates per species |

From dir_step4/:

| Output | File | Description |
|--------|------|-------------|
| Ortholog pairs | `orthologous_pairs.txt` | Pairwise ortholog relationships |

---

## Directory Structure

```
broccoli/
├── README.md                        # This file
├── AI_GUIDE-broccoli.md             # AI assistant guide
├── user_research/                   # Personal workspace
├── output_to_input/                 # Outputs for downstream
├── upload_to_server/                # Server sharing
└── workflow-COPYME-run_broccoli/    # Workflow template (pending implementation)
    ├── INPUT_user/
    ├── OUTPUT_pipeline/
    └── ai/
```

---

## See Also

- `../AI_GUIDE-orthogroups.md` - Overview of orthogroup tools
- `../orthofinder/` - Sequence-similarity based ortholog detection
- `../orthohmm/` - HMM-based ortholog detection
- [Broccoli GitHub](https://github.com/rderelle/Broccoli) - Source code and documentation
