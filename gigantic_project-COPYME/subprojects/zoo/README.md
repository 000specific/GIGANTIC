# zoo

**A holding subproject for work that lives outside GIGANTIC conventions.**

`zoo` is "where the wild things are" — a single, clearly-labelled home for
analyses and deliverables that are intentionally *not* expected to follow
GIGANTIC's normal structure, naming, vocabulary, or reproducibility norms.
Bundling them here keeps the rest of `subprojects/` clean while preserving this
work as part of the scientific record. The name sorts last on both the command
line and the data server, which is intentional.

## How `zoo` differs from the `z_` and `x_` prefixes

These three are distinct lifecycle markers — do not conflate them:

| Marker | Meaning |
|---|---|
| `z_*` (e.g. `z_dark_sono`, `z_synteny`) | Auxiliary/experimental sibling **on track to eventually be incorporated into GIGANTIC**. |
| `x_*` | Material **being phased out of GIGANTIC**. |
| `zoo` | Permanent holding pen for work that is **outside GIGANTIC and not on either track** — neither being promoted in nor phased out. |

## Blocks

Each former standalone subproject was folded in as one block, moved verbatim
(the analyses themselves were not changed — only their location):

| Block | What it is |
|---|---|
| `BLOCK_moroz_innovations` | Clade-level "innovation" tables using Leonid's operational *innovation* vocabulary, kept deliberately distinct from GIGANTIC's *origin* (OCL) vocabulary. Currently a `structure_001`-only test run. See the block README. |
| `BLOCK_leonid_requests` | Ad-hoc delivery channel for one-off requests from Leonid Moroz. Holds the `build/` scripts for the **June 4** delivery (server tables re-served with each sequence's FASTA travelling in-row). The delivered data is under `upload_to_server/BLOCK_leonid_requests/june_4/`. |

## Directory layout

```
zoo/
  README.md  (this file)
  BLOCK_moroz_innovations/
    README.md
    workflow-COPYME-moroz_innovations_analysis/
  BLOCK_leonid_requests/
    build/                     (frozen reproduce-only scripts for the June 4 delivery)
  upload_to_server/            (served on the GIGANTIC data server)
    README.md
    BLOCK_moroz_innovations/   (structure_001 test-run outputs)
    BLOCK_leonid_requests/
      june_4/                  (the June 4 served-tables-with-sequences delivery)
```

## Conventions caveat

Contents of `zoo` may not follow GIGANTIC naming, vocabulary, manifest, or
reproducibility conventions. That is the point of this subproject. Read each
block's own README before assuming anything about its structure.
