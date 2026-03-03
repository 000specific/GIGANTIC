# The GIGANTIC Species Tree Topology System (trees_species)

The trees_species subproject generates all possible species tree topologies for a set of phylogenetically unresolved clades, then extracts the phylogenetic features (paths, blocks, parent-child relationships, clade-species mappings) that downstream origin-conservation-loss (OCL) analyses require. When only one topology is biologically reasonable, the pipeline operates in single-tree mode and simply extracts features from the provided tree.

trees_species depends on the [genomesDB subproject](gigantic_subproject-genomesDB.md) for the species list and on the [phylonames subproject](gigantic_subproject-phylonames.md) for the GIGANTIC clade naming system (CXXX_Name format used in annotated Newick trees).

---

## Two-BLOCK Architecture

```
BLOCK_permutations_and_features/     Extract → Permute → Annotate → Build → Features
BLOCK_de_novo_species_tree/          (placeholder) De novo inference from molecular data
```

**BLOCK_permutations_and_features** (functional): Nine-process pipeline that takes an annotated species tree and generates all topology permutations with comprehensive phylogenetic feature extraction.

**BLOCK_de_novo_species_tree** (placeholder): Future block for inferring species trees from molecular sequence data using tools like ASTRAL or concatenated alignment approaches. Currently a directory skeleton only.

---

## The Topology Permutation Problem

For phylogenetically controversial branching orders (e.g., where Ctenophora, Porifera, and Cnidaria diverge relative to Bilateria), there is no single consensus tree. Rather than choosing one topology, GIGANTIC generates **all possible binary topologies** for the unresolved clades and runs every downstream analysis on every topology.

### The Math

For N unresolved taxa, the number of unrooted binary trees is the **double factorial**:

```
(2N - 3)!! = (2N-3) x (2N-5) x ... x 3 x 1
```

| Unresolved Clades | Topologies |
|--------------------|------------|
| 3 | 3 |
| 4 | 15 |
| 5 | 105 |
| 6 | 945 |
| 7 | 10,395 |

The default GIGANTIC configuration uses 5 unresolved clades (Ctenophora, Porifera, Placozoa, Cnidaria, Bilateria), producing **105 topologies**.

### Single-Tree Mode

When the `unresolved_clades` list is empty in the configuration, the pipeline generates exactly one structure (structure_001) and extracts features from the input tree as-is. This mode is useful when the phylogenetic placement is settled or when working with a specific hypothesis.

---

## Nine-Process Pipeline

```
Process 1: Extract tree components (outgroups, major clades, species assignments)
    |
Process 2: Generate topology permutations ((2N-3)!! skeleton trees)
    |
Process 3: Assign permanent clade IDs (CXXX identifiers per structure)
    |
Process 4: Build complete species trees (graft subtrees onto skeletons)
    |
Process 5: Extract parent-child and parent-sibling relationships
    |
Process 6: Generate phylogenetic blocks (Parent::Child transitions)
    |
Process 7: Integrate all clade data into comprehensive master table
    |
Process 8: Visualize species trees (SVG + PDF per structure)
    |
Process 9: Generate clade-to-species membership mappings
```

**Design principle**: "Scripts Own the Data, NextFlow Manages Execution." Every script reads from `OUTPUT_pipeline/(N-1)-output/` and writes to `OUTPUT_pipeline/N-output/`. NextFlow enforces sequential order but does not pass data through channels. This means every script is independently testable from the command line.

**No external bioinformatics tools**: All computation is pure Python 3 (plus PyYAML for config parsing and ete3 for visualization). No alignment tools, no tree inference software.

---

## Input Design: Annotated Newick Species Trees

### The CXXX_Name Label System

Every node in the input tree (leaf and internal) carries a GIGANTIC clade identifier:

```
((C054_Homo_sapiens,C055_Mus_musculus)C053_Euarchontoglires,C056_Canis_lupus_familiaris)C052_Boreoeutheria;
```

| Label Component | Meaning |
|-----------------|---------|
| `C054` | Permanent GIGANTIC clade ID (assigned by phylonames subproject) |
| `Homo_sapiens` | Clade name (Genus_species for leaves, taxonomic group for internal nodes) |
| `C054_Homo_sapiens` | Full clade identifier used throughout GIGANTIC |

### Input File Format

**Filename**: `species_tree.newick`

**Location**: `INPUT_user/` directory

**Format**: Standard Newick with CXXX_Name labels at every node. The tree should be rooted and fully resolved except for the clades listed in the `unresolved_clades` configuration.

### Optional: Clade Names File

**Filename**: `clade_names.tsv` (optional)

**Location**: `INPUT_user/` directory

Provides human-readable names for clades when the Newick labels use abbreviated or coded identifiers.

---

## Process 1: Extract Tree Components

**Script**: `001_ai-python-extract_tree_components.py`

Parses the annotated Newick tree and identifies:

- **Fixed outgroups**: Branches that are not part of the unresolved polytomy
- **Major clades**: The unresolved taxa listed in the configuration
- **Species assignments**: Which species belong to which major clade
- **Clade registry**: All CXXX identifiers with their names and tree positions

### Outputs

| File | Description |
|------|-------------|
| `1_ai-fixed_outgroups.tsv` | Outgroup clades and their species |
| `1_ai-major_clades.tsv` | The N unresolved clades with member species |
| `1_ai-clade_registry.tsv` | Complete CXXX identifier registry |
| `1_ai-species_assignments.tsv` | Every species mapped to its major clade |

---

## Process 2: Generate Topology Permutations

**Script**: `002_ai-python-generate_topology_permutations.py`

Generates all (2N-3)!! unrooted binary tree topologies for the N unresolved clades using a recursive insertion algorithm. Each topology is a skeleton tree where leaves are major clade names (not individual species).

### Output

| File | Description |
|------|-------------|
| `newick_trees/2_ai-structure_XXX_topology.newick` | One skeleton Newick per topology (105 files for 5 clades) |
| `2_ai-topology_summary.tsv` | Summary of all generated topologies |

---

## Process 3: Assign Permanent Clade IDs

**Script**: `003_ai-python-assign_clade_identifiers.py`

Assigns CXXX identifiers to every internal node in each topology. Structure_001 preserves the original clade IDs from the input tree. Structures 002+ receive new identifiers to distinguish structurally different nodes across topologies.

### Output

| File | Description |
|------|-------------|
| `newick_trees/3_ai-structure_XXX_annotated_topology.newick` | Annotated skeleton with CXXX_Name labels |
| `3_ai-clade_id_assignments.tsv` | All clade ID assignments across all structures |

---

## Process 4: Build Complete Species Trees

**Script**: `004_ai-python-build_complete_trees.py`

Grafts the full species subtrees from the original input tree onto each annotated skeleton topology, producing complete species trees with all leaf taxa.

### Outputs

| File | Description |
|------|-------------|
| `newick_trees/4_ai-structure_XXX_complete_tree.newick` | Complete species tree per topology |
| `4_ai-evolutionary_paths.tsv` | Root-to-leaf phylogenetic paths for every species in every structure |
| `4_ai-clade_registry.tsv` | Updated clade registry with structure membership |

The evolutionary paths file contains 4 columns (species-only): Structure_ID, Species_Clade_ID_Name, Species_Name, Phylogenetic_Path. The path field uses `>` separators showing the complete lineage from root to leaf.

---

## Process 5: Extract Parent-Child Relationships

**Script**: `005_ai-python-extract_parent_child_relationships.py`

Parses each complete tree to extract every parent-child branching point. Produces two complementary formats: parent-child pairs (4 columns) and parent-sibling sets (9 columns) that include both children of each internal node.

### Outputs

| File | Description |
|------|-------------|
| `{species_set}_Parent_Sibling_Sets/5_ai-structure_XXX_parent_child_table.tsv` | 9-column parent-sibling format per structure |
| `{species_set}_Parent_Child_Relationships/5_ai-structure_XXX_parent_child.tsv` | 4-column parent-child pairs per structure |

Self-referential leaf entries (where parent = child_1 = child_2) represent terminal taxa and are included for completeness.

---

## Process 6: Generate Phylogenetic Blocks

**Script**: `006_ai-python-generate_phylogenetic_blocks.py`

A phylogenetic block represents a branch in the tree, identified by `Parent::Child` notation (e.g., `Metazoa::Bilateria`). Each internal node produces exactly two blocks (one for each child). The tree root receives a synthetic `C000_Pre_Basal` parent.

### Outputs

| File | Description |
|------|-------------|
| `6_ai-phylogenetic_blocks-all_{N}_structures.tsv` | Combined blocks across all structures (10 columns) |
| `6_ai-structure_XXX_phylogenetic_blocks.tsv` | Per-structure block files |

The 10 columns include: Structure_ID, Clade_ID, Clade_Name, Clade_ID_Name, Parent_Clade_ID, Parent_Clade_Name, Parent_Clade_ID_Name, Phylogenetic_Block_Name, Phylogenetic_Block_ID, Phylogenetic_Block_ID_Name.

---

## Process 7: Integrate All Clade Data

**Script**: `007_ai-python-integrate_clade_data.py`

Creates a comprehensive master table combining data from all previous steps. Parses Newick trees directly (rather than reading the species-only paths file) to generate phylogenetic paths for **all** clades including internal nodes.

### Output

| File | Description |
|------|-------------|
| `7_ai-integrated_clade_data-all_{N}_structures.tsv` | 24-column master table |
| `7_ai-structure_XXX_integrated_clade_data.tsv` | Per-structure integrated files |

The 24 columns include clade identity, structure membership, phylogenetic paths, parent-child relationships, block assignments, species membership, and four Newick tree representations (structure-only, IDs-only, names-only, IDs-and-names).

---

## Process 8: Visualize Species Trees

**Script**: `008_ai-python-visualize_species_trees.py`

Generates publication-quality tree visualizations using the ete3 library with headless rendering (Qt offscreen). Each structure receives SVG and PDF versions.

### Features

- Leaf nodes: circles with Genus_species labels
- Internal nodes: squares with optional CXXX clade ID labels
- GIGANTIC colorblind-safe palette (dark blue `#003FFF`, light blue `#7FD4FF`)
- Configurable branch length display and clade ID visibility

### Output

| File | Description |
|------|-------------|
| `8_ai-structure_XXX-species_tree.svg` | Scalable vector visualization |
| `8_ai-structure_XXX-species_tree.pdf` | PDF visualization |

---

## Process 9: Clade-Species Membership Mappings

**Script**: `009_ai-python-generate_clade_species_mappings.py`

For every clade in every structure, computes the complete set of descendant species. This mapping is essential for OCL analyses that need to know which species belong to each evolutionary branch.

### Output

| File | Description |
|------|-------------|
| `9_ai-clade_species_mappings-all_{N}_structures.tsv` | Combined mappings (9 columns) |
| `9_ai-structure_XXX_clade_species_mappings.tsv` | Per-structure mapping files |

Columns include descendant species count, comma-delimited species list, descendant node list, and the full phylogenetic path for each clade.

---

## Data Flow

### Input

```
INPUT_user/
├── species_tree.newick              (annotated Newick with CXXX_Name labels)
└── clade_names.tsv                  (optional: human-readable clade names)
```

Configuration in `permutations_and_features_config.yaml`:
- `species_set_name`: Identifier for this species set (e.g., "species71")
- `unresolved_clades`: List of clade names to permute (empty for single-tree mode)

### Output

```
OUTPUT_pipeline/
├── 1-output/     Tree components (outgroups, clades, species assignments)
├── 2-output/     Topology skeletons (newick_trees/)
├── 3-output/     Annotated topologies with clade IDs (newick_trees/)
├── 4-output/     Complete species trees + evolutionary paths (newick_trees/)
├── 5-output/     Parent-child and parent-sibling relationships
├── 6-output/     Phylogenetic blocks (Parent::Child)
├── 7-output/     Integrated master table (24 columns)
├── 8-output/     Tree visualizations (SVG + PDF)
└── 9-output/     Clade-species membership mappings
```

### Downstream Sharing (output_to_input)

```
trees_species/output_to_input/BLOCK_permutations_and_features/
├── Species_Phylogenetic_Paths/           (from 4-output)
├── Species_Tree_Structures/              (from 2, 3, 4-output newick_trees)
├── Species_Parent_Sibling_Sets/          (from 5-output)
├── Species_Parent_Child_Relationships/   (from 5-output)
├── Species_Phylogenetic_Blocks/          (from 6-output)
└── Species_Clade_Species_Mappings/       (from 9-output)
```

Symlinks are created automatically by `RUN-workflow.sh` after the NextFlow pipeline completes.

### Downstream Consumers

| Subproject | What It Uses |
|------------|-------------|
| **orthogroups_ocl** | Phylogenetic blocks + clade-species mappings for origin-conservation-loss analysis of orthogroups |
| **annotations_ocl** | Phylogenetic blocks + clade-species mappings for origin-conservation-loss analysis of functional annotations |
| **orthogroups_X_species_tree** | Complete species trees + parent-child relationships for mapping orthogroup patterns onto phylogeny |

---

## Configuration

Edit `permutations_and_features_config.yaml`:

```yaml
species_set_name: "species71"

input_files:
  species_tree: "INPUT_user/species_tree.newick"
  clade_names: ""                      # Optional: path to clade names TSV

permutation:
  unresolved_clades:
    - Ctenophora
    - Porifera
    - Placozoa
    - Cnidaria
    - Bilateria

output:
  base_dir: "OUTPUT_pipeline"
```

**To run in single-tree mode**, leave `unresolved_clades` as an empty list:

```yaml
permutation:
  unresolved_clades: []
```

---

## Running

```bash
cd subprojects/trees_species/BLOCK_permutations_and_features/workflow-COPYME-permutations_and_features/
# Prepare input
cp your_annotated_tree.newick INPUT_user/species_tree.newick
nano permutations_and_features_config.yaml
# Execute
bash RUN-workflow.sh          # Local
sbatch RUN-workflow.sbatch    # SLURM
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Species tree not found` | Missing `INPUT_user/species_tree.newick` | Place annotated Newick file in INPUT_user/ |
| `No unresolved clades configured` but multiple topologies expected | Empty `unresolved_clades` list in config | Add clade names to the permutation section |
| `Clade not found in tree` | Clade name in config doesn't match Newick label | Verify clade names match the Name portion of CXXX_Name labels exactly |
| Tree visualization fails | ete3 or Qt not available | Ensure `ai_gigantic_trees_species` conda environment is activated; Qt offscreen mode requires PyQt5 |
| `Zero structures processed` | Script 005 output not found or malformed | Check OUTPUT_pipeline/4-output/ for complete tree files; verify Script 004 completed successfully |
| Block count mismatch in combined file | Interrupted previous run left partial files | Delete OUTPUT_pipeline/ and rerun from scratch |

---

## External Tools and References

| Tool | Purpose | Citation | Repository |
|------|---------|----------|------------|
| **Nextflow** | Workflow orchestration | Di Tommaso et al. (2017) *Nature Biotechnology* 35:316-319. [DOI](https://doi.org/10.1038/nbt.3820) | [github.com/nextflow-io/nextflow](https://github.com/nextflow-io/nextflow) |
| **ete3** | Tree visualization | Huerta-Cepas et al. (2016) *Molecular Biology and Evolution* 33:1635-1638. [DOI](https://doi.org/10.1093/molbev/msw046) | [github.com/etetoolkit/ete](https://github.com/etetoolkit/ete) |
| **PyYAML** | Configuration parsing | — | [github.com/yaml/pyyaml](https://github.com/yaml/pyyaml) |

All tree generation and feature extraction is performed using Python 3 standard library. ete3 is used only for visualization (Process 8). The `ai_gigantic_trees_species` conda environment provides Python, Nextflow, PyYAML, ete3, and PyQt5.

---

*For AI assistant guidance, see `AI_GUIDE-permutations_and_features.md` (BLOCK-level) and `ai/AI_GUIDE-permutations_and_features_workflow.md` (workflow-level).*
