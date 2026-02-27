# INPUT_user - OrthoFinder Workflow

Place your input files here before running the workflow.

## Required Files

### 1. Species Tree

**File**: `speciesNN_species_tree.newick`

Where NN is the number of species (e.g., `species67_species_tree.newick`)

- Newick format
- Species names must match proteome filenames (without extension)
- Used by OrthoFinder to infer Hierarchical Orthogroups (HOGs)

### 2. Proteomes Directory

**Directory**: `proteomes/`

Contains one FASTA file per species:
- Accepted extensions: `.fasta`, `.fa`, `.faa`, `.pep`
- Files can be actual files or symlinks
- Filename (without extension) must match species tree names

## Example Structure

```
INPUT_user/
├── species67_species_tree.newick
├── proteomes/
│   ├── Homo_sapiens.fasta
│   ├── Drosophila_melanogaster.fasta
│   ├── Caenorhabditis_elegans.fasta
│   └── ... (one per species)
└── README.md (this file)
```

## Creating Symlinks to GIGANTIC Proteomes

If your proteomes are in the GIGANTIC databases directory:

```bash
# Create proteomes directory
mkdir -p proteomes

# Link to Species67 proteomes (example)
PROTEOMES_DIR="/path/to/gigantic/databases-AI/000_user/species67-T1-fastas"
for f in "$PROTEOMES_DIR"/*.aa; do
    ln -s "$f" proteomes/
done
```

## Validation

The workflow will validate:
- Species tree exists and is named correctly
- Proteomes directory exists
- Proteome count matches species count in tree filename
