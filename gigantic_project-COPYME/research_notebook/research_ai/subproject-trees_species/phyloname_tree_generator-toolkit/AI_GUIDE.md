# AI_GUIDE — Phyloname Tree Generator Toolkit

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Top-level user-facing README: [`README.md`](README.md)
- Template AI guide: [`toolkit-COPYME-phyloname_tree_generator/ai/AI_GUIDE.md`](toolkit-COPYME-phyloname_tree_generator/ai/AI_GUIDE.md)
- Downstream consumer: `subprojects/trees_species/BLOCK_gigantic_species_tree/`

---

## What this toolkit does

Generates a binary species-tree Newick from a phylonames TSV map. The Newick is then symlinked into `trees_species/BLOCK_gigantic_species_tree/workflow-COPYME-gigantic_species_tree/INPUT_user/species_tree.newick` for the canonical GIGANTIC workflow to consume.

## Why this is a research_ai tool, not a trees_species BLOCK

The phylonames → tree mapping is a user-judgment step: the backbone topology and any internal-clade groupings (e.g. Cetacea, Whippomorpha) depend on the species set and the user's preferred biological model. The canonical `BLOCK_gigantic_species_tree` workflow assumes the user has already produced a binary Newick — it does NOT try to derive one from phylonames. This toolkit is the canonical AI-built helper for that user-side step.

## Algorithm

1. Parse phylonames TSV (positional columns: col 0 = `genus_species`, col 1 = `phyloname`).
2. Assign each species to one backbone leaf using user-declared match rules (which `phyloname` token positions must equal which values).
3. For each backbone leaf, build a nested taxonomic dict from the species' below-leaf tokens.
4. Recursively walk each subtree:
   - Apply any `internal_clade_constraints` whose declared siblings all appear as children of the current node (collapses them into one composite child named for the constraint).
   - If > 2 children remain after constraints, randomly pair (seeded RNG); every pairing logged.
5. Substitute the resolved subtrees into the user's backbone topology; strip the outermost single-child wrapper.
6. Emit a clean binary Newick with NO internal labels (downstream `trees_species/BLOCK_gigantic_species_tree/` reserves the `ancestral_clade_NNN` pattern for its own auto-naming pass and hard-fails on labels matching the pattern).

## Process chain (ai/main.nf)

| # | Process | Script | Purpose |
|---|---|---|---|
| 1 | `generate_species_tree` | `001_*.py` | Parse + backbone + constraints + polytomy resolve + emit Newick / decision log / constraint log / summary |
| 2 | `validate_outputs` | `002_*.py` | Binary, N-1 internals, no duplicate leaves, no reserved internal labels |
| 3 | `bridge_to_trees_species` | `003_*.py` | Symlink the Newick into trees_species INPUT_user as `species_tree.newick` |
| 4 | `write_run_log` | `004_*.py` | GIGANTIC §45 audit log |

## Failure semantics

- Any species that cannot be assigned to a backbone leaf → script 001 exits 1
- Any internal-clade constraint whose declared siblings can't all be matched → script 001 exits 1 (rule: a constraint must apply cleanly or the tree's intent is ambiguous)
- Newick parse failure / non-binary / duplicate leaves / reserved internal labels → script 002 exits 1

NextFlow: `errorStrategy = 'terminate'`, `maxErrors = 0`.

## Resource sizing

CPU- and IO-cheap (stdlib Python, single phylonames TSV). `local` execution recommended. Default per-process: 2 cpus, 15 GB (per the project RAM rule CPUs × 7.5 GB).

## See also

- `README.md` — user-facing top-level overview
- `toolkit-COPYME-phyloname_tree_generator/README.md` — template-level user-facing README
- `toolkit-COPYME-phyloname_tree_generator/INPUT_user/README.md` — tree_config.yaml schema
- `toolkit-COPYME-phyloname_tree_generator/ai/AI_GUIDE.md` — workflow-level AI guide
- `subprojects/trees_species/BLOCK_gigantic_species_tree/AI_GUIDE.md` — downstream canonical workflow
