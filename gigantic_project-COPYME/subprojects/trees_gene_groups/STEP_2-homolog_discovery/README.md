# STEP_2: Homolog Discovery

Find homologous sequences across project species using Reciprocal Best Hit/Family (RBH/RBF) BLAST.

## Purpose

Takes a Reference Gene Set (RGS) of curated protein sequences and finds homologs across all project species through forward BLAST, reciprocal BLAST confirmation, species filtering, and identifier remapping.

## Quick Start

```bash
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
cd workflow-RUN_01-rbh_rbf_homologs/
# Edit rbh_rbf_homologs_config.yaml (set gene_group name, rgs_file, database paths)
# Place RGS file and species_keeper_list.tsv in INPUT_user/
bash RUN-workflow.sh
```

## Prerequisites

- **genomesDB** subproject complete (provides BLAST databases and header mapping)
- RGS FASTA file with curated reference sequences
- Species keeper list (one Genus_species per line)

## 16-Step Pipeline

1. List BLAST databases
2. Generate forward BLAST commands
3. Execute forward BLAST
4. Extract blast gene sequences (BGS)
5. Generate RGS genome BLAST commands
6. Execute RGS genome BLAST
7. List RGS BLAST files
8. Map RGS to reference genome identifiers
9. Create modified genomes for reciprocal BLAST
10. Build combined reciprocal BLAST database
11. Generate reciprocal BLAST commands
12. Execute reciprocal BLAST
13. Extract candidate gene sequences (CGS)
14. Filter by species keeper list
15. Remap CGS identifiers to GIGANTIC phylonames
16. Concatenate RGS + CGS into final AGS (All Gene Set)

## Output

Final AGS files are copied to:
- `output_to_input/ags_fastas/<gene_group>/`

## For AI Assistants

See `AI_GUIDE-homolog_discovery.md` for detailed AI guidance.
