# gene_groups-COPYME - Source-Level Template

This is the template directory for creating a new gene group source. Copy this entire directory and customize it for your specific gene group classification system.

## How to Use

```bash
# 1. Copy the template
cp -r gene_groups-COPYME gene_groups-pfam

# 2. Replace STEP_0-placeholder with source-specific RGS generation
rm -r gene_groups-pfam/STEP_0-placeholder/
mkdir -p gene_groups-pfam/STEP_0-pfam_clans/
# Create your STEP_0 pipeline here (download data, generate RGS files)

# 3. Adjust paths in STEP_1 and STEP_2 workflow configs
# Edit STEP_1-*/workflow-COPYME-*/START_HERE-user_config.yaml
# Edit STEP_2-*/workflow-COPYME-*/START_HERE-user_config.yaml

# 4. Create documentation
# Create gene_groups-pfam/AI_GUIDE-pfam.md

# 5. Create output_to_input structure
mkdir -p ../output_to_input/gene_groups-pfam/STEP_0-pfam_clans
mkdir -p ../output_to_input/gene_groups-pfam/STEP_1-homolog_discovery
mkdir -p ../output_to_input/gene_groups-pfam/STEP_2-phylogenetic_analysis
```

## Template Contents

```
gene_groups-COPYME/
├── README.md                          # This file
├── STEP_0-placeholder/                # Replace with source-specific RGS generation
├── STEP_1-homolog_discovery/          # Shared RBH/RBF homolog finding pipeline
│   ├── AI_GUIDE-homolog_discovery.md
│   ├── README.md
│   └── workflow-COPYME-rbh_rbf_homologs/
│       ├── START_HERE-user_config.yaml
│       ├── RUN-workflow.sh
│       ├── INPUT_user/
│       └── ai/
│           ├── main.nf
│           ├── nextflow.config
│           └── scripts/
└── STEP_2-phylogenetic_analysis/      # Shared alignment + tree building pipeline
    ├── AI_GUIDE-phylogenetic_analysis.md
    ├── README.md
    └── workflow-COPYME-phylogenetic_analysis/
        ├── START_HERE-user_config.yaml
        ├── RUN-workflow.sh
        └── ai/
            ├── main.nf
            ├── nextflow.config
            └── scripts/
```

## STEP_0: What Your Source Needs to Provide

Your custom STEP_0 should produce RGS FASTA files that STEP_1 can consume:

**RGS File Requirements**:
- Standard FASTA format (.aa extension)
- One file per gene group
- Header format should include gene group identifiers and species info
- Sequences must be amino acid protein sequences

**Recommended Outputs**:
- `rgs_fastas/` directory with one .aa file per gene group
- A manifest TSV listing all generated RGS files with metadata
- A summary TSV with generation statistics

## Path Notes

The workflow-COPYME templates have paths configured for the **running depth** - i.e., from `gene_group-X/workflow-RUN_01/` (one level deeper than the COPYME location itself). This is intentional: COPYME should never be run directly, only copied into gene_group directories.

## See Also

- `../AI_GUIDE-trees_gene_groups.md` - Subproject-level guide
- `../gene_groups-hugo_hgnc/` - First implemented source (HUGO HGNC) - use as a reference
- `../../trees_gene_families/AI_GUIDE-trees_gene_families.md` - Shared pipeline methodology
