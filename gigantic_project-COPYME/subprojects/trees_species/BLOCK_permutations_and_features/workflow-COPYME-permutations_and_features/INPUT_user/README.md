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

### Don't have a labeled tree yet?

If you have a raw species tree with `Genus_species` at leaves and optional
clade names at internals (but no `CXXX_` prefixes), run
**`BLOCK_gigantic_species_tree`** first (sibling BLOCK within `trees_species/`).
It standardizes, validates, and labels your tree, producing the
`CXXX_Clade_Name` format this BLOCK expects. The labeled output will be
available at:

```
../../output_to_input/BLOCK_gigantic_species_tree/{species_set}-species_tree-with_clade_ids_and_names.newick
```

You can then symlink that labeled tree into this BLOCK's `INPUT_user/`:

```bash
ln -sf ../../../output_to_input/BLOCK_gigantic_species_tree/{species_set}-species_tree-with_clade_ids_and_names.newick \
    INPUT_user/species_tree.newick
```

See `../../../BLOCK_gigantic_species_tree/AI_GUIDE-gigantic_species_tree.md` for details.

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
