# toolkit-COPYME-phyloname_tree_generator

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent toolkit overview: [`../README.md`](../README.md)
- Parent toolkit AI guide: [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This template's workflow AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Downstream consumer: `subprojects/trees_species/BLOCK_gigantic_species_tree/`

---

Generates a binary species-tree Newick from a phylonames TSV map. Honors a user-specified backbone topology, optional internal-clade constraints (named monophyletic sub-clades not encoded in phylonames), and reproducible random polytomy resolution.

## Why this is a user-side tool

Producing a Newick from raw phylonames is a user-judgment step (which backbone topology, which internal clades). The canonical `BLOCK_gigantic_species_tree` workflow consumes a binary Newick but does not derive one. This toolkit fills that gap.

## Prerequisites

- A phylonames TSV (default points at `subprojects/phylonames/output_to_input/maps/<set>-genus_species_X_phylonames.tsv`)
- A `tree_config.yaml` at `INPUT_user/` (default is calibrated for the species42 deuterostome demo)
- `aiG-research_ai-phyloname_tree_generator` conda env (auto-created on first run)

`RUN-workflow.sh` activates and deactivates the conda env automatically.

## Usage

```bash
cp -r toolkit-COPYME-phyloname_tree_generator toolkit-RUN_1-phyloname_tree_generator
cd toolkit-RUN_1-phyloname_tree_generator

# Adjust backbone + constraints + seed if needed
$EDITOR INPUT_user/tree_config.yaml

# Confirm paths
$EDITOR START_HERE-user_config.yaml

bash RUN-workflow.sh
```

## Pipeline

4 steps:

1. **Generate** — parse phylonames + apply backbone + apply internal-clade constraints + resolve polytomies + emit Newick + decision log + constraint log + summary
2. **Validate** — binary, N-1 internals, no duplicate leaves, no reserved `ancestral_clade_NNN` labels
3. **Bridge** — symlink the Newick into `trees_species/BLOCK_gigantic_species_tree/workflow-COPYME-gigantic_species_tree/INPUT_user/species_tree.newick`
4. **Run-log** — GIGANTIC §45 audit log

See [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for algorithm details + failure semantics.
