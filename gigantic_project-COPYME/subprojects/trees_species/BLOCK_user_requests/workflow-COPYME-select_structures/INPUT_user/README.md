# INPUT_user - User-Provided Inputs

## query_manifest.yaml

Describes the topological queries you want to run against the 105 species
tree structures. Each query specifies a set of phylogenetic block
relationships that must all hold for a structure to match.

**Format**: YAML with a top-level `queries:` list. Each query has:
- `name` (required) -- short identifier, used as filename stem
- `description` (optional) -- human-readable description
- `require_direct_child` (optional list) -- parent-child relationships that must exist
- `require_sister` (optional list) -- pairs of clades that must be sister clades

All conditions in a query are AND-combined.

### Minimal example

```yaml
queries:
  - name: Ctenophora_sister_only
    description: "Any tree where Ctenophora is sister to all other animals"
    require_direct_child:
      - { parent: Metazoa, child: Ctenophora }
```

### Leonid's 4-tree example (default in COPYME template)

The default `query_manifest.yaml` shipping with the COPYME template has
Leonid's 4-tree 2x2 request (Ctenophora-vs-Porifera basal × two ParaHoxozoa
arrangements) already filled in. Use this as a starting point for your own
queries.

## How to Populate

1. Describe what the user wants in plain English. Example:
   > "Give me the tree where Porifera is basal and Placozoa+Cnidaria form a
   > clade sister to Bilateria."

2. Translate each topological claim into block relationships:
   - "Porifera is basal to other animals" -> `require_direct_child: [{parent: Metazoa, child: Porifera}]`
   - "Placozoa+Cnidaria form a clade" -> `require_sister: [[Placozoa, Cnidaria]]`

3. Add the query (with a descriptive `name`) to the manifest.

4. Run: `bash RUN-workflow.sh`

5. Check `OUTPUT_pipeline/1-output/1_ai-query_summary.md` for results.

## Using Bare Clade Names

Queries use **bare names** like `Metazoa`, `Ctenophora` -- not the atomic
`CXXX_Metazoa` / `CXXX_Ctenophora` identifiers. This keeps queries portable
across structures where the same biological clade has different clade IDs
because of Rule 6 (topologically-structured species sets).

To find out which bare names exist:
- View `OUTPUT_pipeline/1-output/1_ai-ascii_previews/structure_001_ascii_tree.txt`
  (after a test run) -- shows the full tree with all clade IDs and names.
- Or: `head -5 ../../output_to_input/BLOCK_permutations_and_features/Species_Phylogenetic_Blocks/*phylogenetic_blocks-all*.tsv`

Common bare names in the species70 set:
- Kingdom / top-level: `Metazoa`, `Holomycota`, `Holozoa`
- Animal-backbone clades: `Ctenophora`, `Porifera`, `Placozoa`, `Cnidaria`, `Bilateria`, `Parahoxozoa`
- Species: `Homo_sapiens`, `Drosophila_melanogaster`, etc. (Genus_species with underscore)
