# INPUT_user — Phyloname Tree Generator Toolkit

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

The toolkit reads a single configuration file from this directory:

- **`tree_config.yaml`** — backbone topology + backbone-leaf assignment
  rules + optional internal-clade constraints + RNG seed.

The default `tree_config.yaml` is calibrated for the species42 deuterostome
demo project. To adapt for another species set:

1. **Backbone topology** — edit `backbone_topology:` to declare the
   high-level shape of the tree (e.g. protostome/deuterostome split,
   Ambulacraria, Olfactores).
2. **Backbone-leaf assignment rules** — edit `backbone_leaves:` to map
   phyloname token positions to backbone-leaf names. Each rule's
   `skip_depth` specifies how many phyloname tokens are absorbed by the
   leaf (the rest form the subtree below it).
3. **Internal-clade constraints** — declare any monophyletic clades the
   phyloname hierarchy doesn't encode. Each constraint names a clade and
   lists the sibling phyloname tokens (typically Family names) that
   should be grouped under it. Common examples:
   - `Cetacea: [ Balaenopteridae, Delphinidae, Phocoenidae ]` (under Artiodactyla)
   - `Whippomorpha: [ Cetacea, Hippopotamidae ]` (one level up; composable)
   - `Holozoa: [ ... ]` (above Metazoa, if your set includes choanoflagellates)
4. **Seed** — change `seed:` to draw a different random sample from the
   polytomy resolution space.

After editing, run `bash RUN-workflow.sh` from the toolkit RUN dir.
