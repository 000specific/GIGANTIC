# OrthoFinder Workflow

Run OrthoFinder with high-quality settings using diamond_ultra_sens and a user-provided species tree.

## Quick Start

```bash
# 1. Copy this workflow to create a run instance
cp -r workflow-COPYME-run_orthofinder workflow-RUN_01-species67

# 2. Add your inputs (see INPUT_user/README.md)

# 3. Edit SLURM settings in SLURM_orthofinder.sbatch
#    - --mail-user
#    - --account
#    - --qos

# 4. Submit job
cd workflow-RUN_01-species67
sbatch SLURM_orthofinder.sbatch
```

## Input Requirements

| File | Description |
|------|-------------|
| `INPUT_user/speciesNN_species_tree.newick` | Species tree (NN = species count) |
| `INPUT_user/proteomes/` | Directory with proteome FASTA files |

## OrthoFinder Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `-t 128` | 128 threads | Sequence search parallelization |
| `-a 128` | 128 threads | Analysis parallelization |
| `-X` | Don't modify IDs | GIGANTIC proteomes already have phylonames |
| `-S diamond_ultra_sens` | Ultra-sensitive | Higher quality, slower |
| `-T fasttree` | FastTree | Gene tree inference |
| `-s` | User tree | Uses provided species tree |

## Outputs

All OrthoFinder output goes to `OUTPUT_pipeline/orthofinder_results/`

Key files:
- `Orthogroups/Orthogroups.tsv` - All orthogroups (OGs)
- `Orthogroups/Orthogroups_UnassignedGenes.tsv` - Singletons
- `Phylogenetic_Hierarchical_Orthogroups/N0.tsv` - HOGs at root level
- `Phylogenetic_Hierarchical_Orthogroups/N*.tsv` - HOGs at other tree nodes

## Resource Estimates

| Species Count | Time | Memory |
|---------------|------|--------|
| ~20 species | 1-2 days | 200 GB |
| ~67 species | 4-7 days | 500 GB |
| ~100+ species | 7-14 days | 700+ GB |

Adjust `--time` and `--mem` in SLURM_orthofinder.sbatch accordingly.

## Need Help?

Ask your AI assistant to read `../AI_GUIDE-orthofinder.md` for guidance.
