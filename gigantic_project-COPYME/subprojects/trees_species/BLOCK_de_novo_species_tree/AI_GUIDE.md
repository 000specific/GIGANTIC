# AI Guide: BLOCK_de_novo_species_tree

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 04 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**Status**: SKELETAL PLACEHOLDER - Future development

## Where this fits

- Parent subproject: [`../AI_GUIDE.md`](../AI_GUIDE.md) — trees_species overview
- Parent project: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling BLOCK that consumes this BLOCK's eventual output: [`../BLOCK_gigantic_species_tree/`](../BLOCK_gigantic_species_tree/) (its `INPUT_user/species_tree.newick` would be the Newick this BLOCK builds)

---

## What This BLOCK Will Do (Future)

Build species phylogenetic trees de novo from sequence data using a classical
phylogenomics supermatrix approach:

1. **Input**: BUSCO single-copy protein sequences from genomesDB
2. **MAFFT alignment**: Multiple sequence alignment per gene
3. **ClipKit trimming**: Remove low-quality alignment regions
4. **Supermatrix construction**: Concatenate aligned genes across species
5. **Tree inference**: IQ-TREE (LG+C60) and/or FastTree

### GIGANTIC_0 Reference Implementations

When developing this BLOCK, reference the working GIGANTIC_0 pipelines:

- `/orange/moroz/eric-edsinger/projects/aplysia/species-tree/` - 7-script pipeline
- `/orange/moroz/eric-edsinger/projects/aplysia/02-species_trees/` - Multi-stage archive
- Key parameters: MAFFT L-INS-i, ClipKit smart-gap, IQ-TREE LG+C60 with 5000 bootstraps

### Output

A species tree in Newick format that can be used as input to
BLOCK_permutations_and_features.

---

## Current State

This BLOCK is **planned future work** — not implemented. Only this
`AI_GUIDE.md` exists; there is no `workflow-COPYME-build_species_tree/`
scaffolding. (An earlier version shipped a non-functional `RUN-workflow.sh`
stub that exited with "NOT YET IMPLEMENTED"; that was deleted 2026-05-26
because it actively misled users who tried to run it.)

When development begins, create `workflow-COPYME-build_species_tree/`
following the standard GIGANTIC workflow pattern (§29 unified driver +
`ai/main.nf` + `ai/scripts/NNN_ai-...` + `ai/conda_environment.yml` +
`START_HERE-user_config.yaml`).
