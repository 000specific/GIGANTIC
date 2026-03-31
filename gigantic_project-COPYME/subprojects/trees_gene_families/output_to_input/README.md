# output_to_input - Inter-Subproject Data Sharing

Standardized location for trees_gene_families outputs that downstream GIGANTIC subprojects consume as inputs.

## Structure

```
output_to_input/
├── <gene_family_name>/
│   ├── STEP_1-homolog_discovery/
│   │   └── 16_ai-ags-<gene_family>-<database>.aa    # All Gene Set (AGS) FASTA
│   └── STEP_2-phylogenetic_analysis/
│       ├── phylogenetic_trees/                       # Newick tree files
│       └── visualizations/                           # Tree figures (PDF, SVG)
```

## How It Works

- **Populated automatically**: Each workflow's `RUN-workflow.sh` creates symlinks here after successful completion
- **One directory per gene family**: Named by the gene family (e.g., `innexin_pannexin/`, `kinases_AGC/`)
- **Symlinks, not copies**: Files point back to the real data in each workflow's `OUTPUT_pipeline/`
- **Consumed by**: orthogroups, annotations, and other downstream GIGANTIC subprojects

## Not Tracked by Git

Contents of this directory are generated data (symlinks to workflow outputs) and are excluded from version control via `.gitignore`. Only this README and `.gitkeep` are tracked.

## See Also

- `upload_to_server/` - Curated data for the centralized GIGANTIC server (different purpose)
- `gene_family_COPYME/` - Template for creating new gene family analyses
