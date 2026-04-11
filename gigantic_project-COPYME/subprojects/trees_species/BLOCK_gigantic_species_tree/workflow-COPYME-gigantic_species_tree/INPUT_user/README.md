# INPUT_user — Input Species Tree for BLOCK_gigantic_species_tree

**AI**: Claude Code | Opus 4.6 | 2026 April 10
**Human**: Eric Edsinger

---

## Required Input

### `species_tree.newick`

A phylogenetic species tree in Newick format. This is the **only required input**
for the workflow. The file name must be exactly `species_tree.newick` (or match
the `input_files.species_tree` path in `../START_HERE-user_config.yaml`).

---

## Required Format

### Leaves (species)

Leaves must use `Genus_species` format — the same format as the genus_species portion
of GIGANTIC phylonames. Multi-word species names and strain suffixes are supported
and should be joined with underscores.

**Valid examples**:
```
Fonticula_alba
Parvularia_atlantis
Homo_sapiens
Trichoplax_adhaerens
Trichoplax_sp_H2                   # strain suffix OK
Hoilungia_hongkongensis_H13        # strain identifier OK
Chaetoderma_sp_LZ_2023a            # extended identifier OK
Gordionus_sp_m_RMFG_2023           # extended identifier OK
```

**Invalid examples** (will be auto-corrected by Script 001, see "Name Standardization" below):
```
Homo sapiens                       # has space (auto → Homo_sapiens)
Homo-sapiens                       # has hyphen (auto → Homo_sapiens)
Homo.sapiens                       # has period (auto → Homo_sapiens)
```

### Internal Nodes (clades)

Internal nodes can be labeled with clade names OR left unlabeled:

- **User-labeled internal nodes**: Use descriptive clade names like `Metazoa`, `Bilateria`,
  `Chordata`, `Holomycota`. These names will be preserved (after character
  standardization).
- **Unlabeled internal nodes**: Leave them blank in the Newick. Script 002 will
  automatically assign names of the form `ancestral_clade_NNN` (e.g.,
  `ancestral_clade_001`, `ancestral_clade_002`) in breadth-first order from the
  root of the species tree.

**Mixed labeling is fine** — some internals named, others unlabeled. Only truly
unlabeled internals get auto-named.

### Branch Lengths

Branch lengths are **optional**. If present, they will be **replaced with `1.0`** by
Script 001 (GIGANTIC convention: downstream analyses do not use branch lengths,
so standardization keeps tree structures consistent across the framework).

**This is the exception to GIGANTIC's general "never destroy user data" rule** and is
documented as such. If you need to preserve branch lengths for another purpose,
save a copy of your original tree elsewhere before running this workflow.

### Tree Structure

- The species tree **must be binary** (every internal node has exactly 2 children).
  Polytomies will cause a hard validation failure.
- If your tree has unresolved clades, resolve them manually before running this
  BLOCK, or pass the labeled tree to `BLOCK_permutations_and_features` which
  handles unresolved clades via its config-specified `unresolved_clades` list.

### Reserved Namespace

**The name pattern `ancestral_clade_NNN` (where NNN is a 3-digit number) is
RESERVED** by this BLOCK for auto-naming unlabeled internal nodes. Do NOT use
names matching this pattern for your user-labeled internal nodes — Script 001
will hard-fail with a collision error.

---

## Minimal Example

```
((Apple,Banana)Fruits,(Carrot,Potato));
```

This is a valid input:
- 4 leaves: `Apple`, `Banana`, `Carrot`, `Potato`
- 2 internal nodes: one named `Fruits`, one unlabeled (will become `ancestral_clade_001` after Script 002)
- Binary tree ✓
- No branch lengths (will be set to `1.0`)

After running the workflow, the tree gains clade IDs and names:
```
((C001_Apple:1.0,C002_Banana:1.0)C006_Fruits:1.0,(C003_Carrot:1.0,C004_Potato:1.0)C007_ancestral_clade_002:1.0)C005_ancestral_clade_001:1.0;
```

---

## More Complete Example (10 species, mixed labeling)

```
((Fonticula_alba,Parvularia_atlantis)Holomycota,((Homo_sapiens,Mus_musculus)Mammalia,(Drosophila_melanogaster,Caenorhabditis_elegans))Bilateria,(Trichoplax_adhaerens,Hydra_vulgaris));
```

Wait — the outer grouping has 3 children, which is a polytomy. This would FAIL validation.
The correct binary version would be:

```
((Fonticula_alba,Parvularia_atlantis)Holomycota,(((Homo_sapiens,Mus_musculus)Mammalia,(Drosophila_melanogaster,Caenorhabditis_elegans))Bilateria,(Trichoplax_adhaerens,Hydra_vulgaris)));
```

This has:
- 8 leaves (4 labeled internals: `Holomycota`, `Mammalia`, `Bilateria`, and 3 unlabeled)
- All internal nodes binary ✓
- The unlabeled internals will become `ancestral_clade_001`, `ancestral_clade_002`, `ancestral_clade_003` (BFS order from the root)

---

## Name Standardization (automatic)

Script 001 automatically replaces invalid characters in ALL user-provided names
(both leaf and internal) with underscores:

- **Allowed characters**: `[A-Za-z0-9_]` (ASCII letters, digits, underscore)
- **Anything else** becomes `_` (spaces, hyphens, periods, parentheses, etc.)
- **Consecutive underscores** are collapsed to a single underscore
- **Leading and trailing underscores** are stripped

A mapping table `1-output/1_ai-input_user_name_X_gigantic_name.tsv` is always
emitted showing every input name alongside its standardized form, with a
`was_changed` column flagging which names were modified.

**Examples**:
| Input name | Standardized | Changed? |
|---|---|---|
| `Homo_sapiens` | `Homo_sapiens` | no |
| `Homo sapiens` | `Homo_sapiens` | yes |
| `Homo-sapiens` | `Homo_sapiens` | yes |
| `Trichoplax_sp_H2` | `Trichoplax_sp_H2` | no |
| `Ancient_clade (unresolved)` | `Ancient_clade_unresolved` | yes |

---

## Validation Failures (Hard-Fail)

Script 001 will hard-fail with a clear error message if:

1. The input file does not exist or is empty
2. The Newick syntax is unparseable
3. Any leaf has an empty name
4. The tree has any polytomies (non-binary internal nodes)
5. Any user-provided name (after standardization) matches the reserved
   `ancestral_clade_NNN` pattern
6. Two leaves have the same name (after standardization)
7. Two internal nodes have the same name (after standardization) — including
   the case where two different input names collapse to the same standardized name

When validation fails, the script exits with code 1 and the pipeline stops.
Read the error log carefully for guidance on how to fix your input.

---

## How to Populate

1. Obtain or build a species tree in Newick format with:
   - `Genus_species` leaves (matching your GIGANTIC phylonames)
   - Optional user-labeled internal nodes (clade names)
   - Binary structure (no polytomies)

2. Save it as `species_tree.newick` in this directory:
   ```bash
   cp /path/to/your/tree.newick INPUT_user/species_tree.newick
   ```

3. Verify the format with a quick sanity check:
   ```bash
   cat INPUT_user/species_tree.newick | head
   ```

4. Go back up to the workflow root and edit `START_HERE-user_config.yaml`:
   - Set `species_set_name` (e.g., `"species70"`)

5. Run the workflow:
   ```bash
   bash RUN-workflow.sh
   ```

If Script 001 reports a validation failure, edit your input tree and re-run.
