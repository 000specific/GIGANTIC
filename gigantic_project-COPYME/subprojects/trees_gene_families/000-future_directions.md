# 000-future_directions.md — trees_gene_families

Ideas recorded for future work. Not blocking; not scheduled. If you pick one
up, strike it from this file or move it to an issue tracker.

Filename starts with `000-` so it sorts first in the subproject root and is
easy to discover.

---

## Idea 1: Color deep nodes + internal branches by species-MRCA

### What

Today, STEP_3 colors **tip labels** by species (one color per species, 20-color
colorblind-safe palette). Internal edges of the gene tree are all the same
dark gray.

The proposed extension: for every species that has multiple tips in the gene
tree, compute the MRCA (most recent common ancestor) of those tips on the
gene tree, and color the subtree rooted at that MRCA in the species' color.
That subtree's edges all take the species color; downstream tip labels keep
their per-tip color.

### Why

In a gene tree with lots of species-specific paralog expansions (very common
in metazoan ion channels, kinomes, GPCRs), the clusters of same-species
copies are the biological story:

- "Nematostella has 8 copies here" → there was a Nematostella-lineage
  expansion → the 8 sit on a monophyletic subtree
- "Drosophila has 4 copies scattered across the tree" → deep orthologs that
  were lost in other lineages, not a lineage-specific expansion

Colored species-MRCA subtrees make both patterns jump out at a glance. The
user does this by hand in FigTree today; it's worth automating for the ~30
published gene family trees and for any future analysis.

It's also the most-compact visualization of **species evolution mapped onto
the gene family tree** — a complement to the OCL/path-state analyses that
operate on the species tree side.

### How (sketch)

```python
# Per species:
#   tips = [ t for t in tree.get_tip_nodes() if extract_species(t) == species ]
#   if len( tips ) < 2:  continue
#   mrca = tree.get_mrca_node( tips )
#   color = species_palette[ species ]
#   # Color every edge in the subtree rooted at mrca
#   for descendant in mrca.get_descendants():
#       edge_colors_map[ descendant.idx ] = color
# Pass edge_colors_map to tree.draw( edge_colors=... )
```

toytree (v3) exposes:
- `tree.get_mrca_node( [ tip_ids or tip_names ] )`
- per-edge styling via `edge_colors` (list aligned to node order)
- `tree.get_node_mask(...)` and `treenode.get_descendants()` for subtree walks

### Tricky cases to handle

1. **Nested species MRCAs**: species A's MRCA subtree may contain species
   B's MRCA subtree. Options:
   - Innermost-wins (B's color shows over A's within the overlap)
   - Outermost-wins (A's color dominates)
   - Stripe/blend (probably too fancy)
   - Recommend: innermost-wins, with a tie-breaker on tip count

2. **Tips of the "painted" species under a non-monophyletic
   arrangement**: species A has 5 tips, 3 cluster together (one subtree),
   2 are elsewhere. MRCA-of-all-5 is probably deep — painting that big
   subtree is misleading (it contains many other species). Options:
   - Paint only monophyletic clusters of ≥2 same-species tips
   - (i.e. find all *maximal monophyletic same-species subtrees*,
     paint each one)
   - This matches the biological intuition: a paralog cluster is a
     monophyletic group of same-species paralogs.

3. **Single-tip species**: leave uncolored at the internal-branch level
   (their tip label already carries the species color).

### Reference to the OCL origins algorithm

Conceptually related — OCL on the species tree side asks "where on the
species tree did this orthogroup originate?" by finding the MRCA on the
species tree of all species that carry a copy. Here we'd be asking the
mirror-image question on the gene tree side: "where on the gene tree did
this species-lineage's paralogs originate?" by finding the MRCA on the
gene tree of all tips from a given species.

If we later integrate these two views (species-tree origin × gene-tree
species-MRCA subtrees), we'd get a compact visual story of gene family
evolution: phylogenetic origin on the species tree × lineage-specific
expansions on the gene tree.

### Where to implement

`gene_family_COPYME/STEP_3-tree_visualization/workflow-COPYME-tree_visualization/ai/scripts/001_ai-python-render_trees.py`

Add a `build_species_mrca_edge_colors()` helper alongside `build_tip_colors()`,
and pass `edge_colors=...` into `tree.draw(...)` when
`color_species_mrca_subtrees: true` in the config. Default to false until
the monophyletic-vs-deep-MRCA UX is validated on real gene trees.

### Estimated effort

Half-day implementation, half-day tuning on real trees (pick a few gene
families with known lineage-specific expansions — e.g. innexins in
ctenophores, TRP channels in cnidarians — and verify the output reads
correctly).

---

*(Add more ideas below. Keep the format: What / Why / How / Where / Effort.)*
