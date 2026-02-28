# Broccoli Workflow

**Status**: Template - scripts pending implementation

Run Broccoli to identify orthogroups using phylogeny-network analysis.

## Quick Start

1. Copy proteomes to `INPUT_user/` or create symlinks
2. Edit configuration (once implemented)
3. Run the workflow:
   - **Local**: `bash RUN-broccoli.sh`
   - **SLURM**: Edit account/qos, then `sbatch RUN-broccoli.sbatch`

## Inputs

- **Proteomes**: FASTA files from genomesDB (`genomesDB/output_to_input/speciesN_gigantic_T1_proteomes/`)

## Results

Output will appear in `OUTPUT_pipeline/` and key results copied to `../output_to_input/` for downstream use.

Key Broccoli outputs:
- `orthologous_groups.txt` - Orthogroup assignments
- `table_OGs_protein_counts.txt` - Species-by-orthogroup count matrix
- `chimeric_proteins.txt` - Gene-fusion events
- `orthologous_pairs.txt` - Pairwise ortholog relationships

## Need Help?

Ask your AI assistant to read `../AI_GUIDE-broccoli.md` for guidance.
