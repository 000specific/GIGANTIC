# INPUT_user - trees_species Permutations and Features

## Required Input

### species_tree.newick

Your species phylogenetic tree in Newick format. Each node must be labeled with
a clade identifier and name in the format `CXXX_Clade_Name`:

```
((C001_Fonticula_alba:1.0,C002_Parvularia_atlantis:1.0)C069_Holomycota:1.0,...)C068_Basal:1.0
```

**Requirements:**
- Standard Newick notation with branch lengths
- Node labels: `CXXX_Name` format (C followed by 3+ digit number, underscore, name)
- Internal nodes labeled (not just terminal species)
- Single-line file (standard Newick)

## Optional Input

### clade_names.tsv

Custom mapping of clade IDs to human-readable names. If not provided, names are
extracted directly from the Newick tree node labels.

**Format** (tab-separated):
```
Clade_ID	Clade_Name
C001	Fonticula_alba
C068	Basal
C079	Metazoa
```

## Configuration

Edit `START_HERE-user_config.yaml` (one directory up) to specify:
- `species_set_name`: Identifier for your species set (e.g., "species71")
- `unresolved_clades`: Which clades to permute (empty = single tree mode)
