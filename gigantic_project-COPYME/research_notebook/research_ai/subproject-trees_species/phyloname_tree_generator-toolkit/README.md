# Phyloname Tree Generator Toolkit

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## What this toolkit does

Generate a binary species-tree Newick from a phylonames TSV map for downstream consumption by `trees_species/BLOCK_gigantic_species_tree/` (which then standardizes labels, fills `ancestral_clade_NNN` for unlabeled internals, and emits the canonical Newick variants).

Three knobs:
1. **Backbone topology** — high-level tree shape at levels phylonames don't encode (e.g. protostome/deuterostome split, Ambulacraria, Olfactores).
2. **Internal-clade constraints** — named monophyletic clades NCBI doesn't encode as taxonomic levels (e.g. Cetacea grouping Balaenopteridae+Delphinidae+Phocoenidae so Hippopotamidae lands sister to Cetacea rather than nested inside).
3. **RNG seed** — reproducible random pairing for residual polytomies.

## Why this lives in research_ai (and not as a trees_species BLOCK)

The phylonames → tree mapping requires user-side biological judgment (backbone topology, named sub-clades) that varies per project and per species set. The canonical `trees_species/BLOCK_gigantic_species_tree/` workflow validates + standardizes an already-binary user-provided Newick; producing that Newick from raw phylonames is a research-tooling step. This toolkit is the canonical AI-built helper for that step.

## Where this fits

- **Parent project**: `../../../../`
- **Downstream consumer**: `subprojects/trees_species/BLOCK_gigantic_species_tree/workflow-COPYME-gigantic_species_tree/INPUT_user/species_tree.newick`
- **Sibling research_ai tools**: `../subproject-hotspots/gene_coordinates_extractor-toolkit/`, `../subproject-trees_gene_groups/`

## Layout

```
phyloname_tree_generator-toolkit/
├── README.md                                       (this file)
├── AI_GUIDE.md                                     (top-level AI guide)
├── output_to_input/
│   └── newick_trees/                               (placeholder; per-run outputs in each RUN dir)
├── toolkit-COPYME-phyloname_tree_generator/        (template; copy to instantiate a run)
│   ├── README.md
│   ├── RUN-workflow.sh
│   ├── START_HERE-user_config.yaml
│   ├── INPUT_user/
│   │   ├── README.md
│   │   └── tree_config.yaml                        (backbone + constraints + seed)
│   └── ai/
│       ├── AI_GUIDE.md
│       ├── main.nf
│       ├── nextflow.config
│       ├── conda_environment.yml
│       ├── logs/
│       └── scripts/
│           ├── 001_ai-python-generate_species_tree.py
│           ├── 002_ai-python-validate_outputs.py
│           ├── 003_ai-python-bridge_to_trees_species.py
│           └── 004_ai-python-write_run_log.py
└── toolkit-RUN_<N>-phyloname_tree_generator/       (each user-instantiated run)
```

## Usage

```bash
cp -r toolkit-COPYME-phyloname_tree_generator toolkit-RUN_1-phyloname_tree_generator
cd toolkit-RUN_1-phyloname_tree_generator

# Edit INPUT_user/tree_config.yaml — backbone + constraints + seed
$EDITOR INPUT_user/tree_config.yaml

# Verify paths in START_HERE-user_config.yaml (defaults point at species42)
bash RUN-workflow.sh
```

End-to-end runtime: seconds (single Python script + stdlib).

## See also

- `toolkit-COPYME-phyloname_tree_generator/README.md` — template-level user-facing README
- `toolkit-COPYME-phyloname_tree_generator/ai/AI_GUIDE.md` — workflow-level AI guide
- `subprojects/trees_species/BLOCK_gigantic_species_tree/` — downstream canonical workflow
