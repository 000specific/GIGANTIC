# AI Guide: gene_groups_hgnc-COPYME (HGNC-Anchored Template)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
AI:      Claude Code | Opus 4.7 | 2026 May 29 (parity-finishing pass — MODE 3 added)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (template README): [`README.md`](README.md)
- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md)
- Parent (project): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling template (generic): [`../gene_groups-COPYME/`](../gene_groups-COPYME/) — for non-HGNC sources
- STEP_0: [`STEP_0-hgnc_based_rgs/AI_GUIDE.md`](STEP_0-hgnc_based_rgs/AI_GUIDE.md) — three workflow modes

---

**For AI Assistants**: Read `../../../AI_GUIDE.md` first for the
GIGANTIC project overview. Then `../AI_GUIDE.md` for
the subproject's concepts. This file covers the HGNC-anchored template
specifically.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups_hgnc-COPYME/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain any discrepancy before proceeding

---

## CRITICAL: Old Instances Are Frozen Research Artifacts

`gene_groups-hugo_hgnc/` is an instance of the **sibling generic
template** `gene_groups-COPYME/` (plus a source-specific STEP_0 named
`STEP_0-hgnc_gene_groups/`). It is **not** an instance of this template
and must never be retroactively "migrated" to use this template — even
as a "cleanup later." Old instances are research notebooks + data
archives of the code path that originally ran them. The codebase
deliberately keeps both `gene_groups-COPYME` and `gene_groups_hgnc-COPYME`
forever, and both keep accumulating their own instances.

This is research, not app development. Refactoring an old instance
erases the historical record of which scripts ran, which fixes were
applied mid-flight, which manifests were used, and what intermediate
state existed. That record is part of reproducibility.

---

## Quick Reference

| User needs… | Go to… |
|---|---|
| GIGANTIC project overview | `../../../AI_GUIDE.md` |
| trees_gene_groups subproject concepts | `../AI_GUIDE.md` |
| This template's overview (this file) | this file |
| STEP_0 concepts (HGNC-based RGS generation) | `STEP_0-hgnc_based_rgs/AI_GUIDE.md` |
| STEP_0 workflow: process all HGNC gene groups | `STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_database/ai/AI_GUIDE.md` |
| STEP_0 workflow: ad-hoc user-supplied gene set | `STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_symbols/ai/AI_GUIDE.md` |
| STEP_0 workflow: user-supplied HGNC group names/IDs | `STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_group_names/ai/AI_GUIDE.md` |
| STEP_1 concepts (RBH/RBF homolog discovery) | `STEP_1-homolog_discovery/AI_GUIDE.md` |
| STEP_2 concepts (alignment + tree) | `STEP_2-phylogenetic_analysis/AI_GUIDE.md` |
| STEP_3 concepts (tree visualization) | `STEP_3-tree_visualization/AI_GUIDE.md` |

---

## What This Template Is For

This template is for analyses **anchored on HUGO HGNC** human-gene
nomenclature. It exists as a sibling to the source-agnostic
`gene_groups-COPYME/` so that everything about "how to materialize a
gene group's RGS from HGNC" lives in one specialized template, with the
generic RBH/RBF homolog discovery + phylogenetic analysis + visualization
machinery inherited unchanged below.

The hallmark of "HGNC-anchored": the gene-membership of each group is
defined in terms of **HGNC-approved human gene symbols** (e.g., SNAP25,
PIEZO1, NLGN4X), and the RGS sequence for each symbol is sourced via
HGNC's curated `uniprot_ids` cross-reference (the canonical Swiss-Prot
accession), either fetched from UniProt REST (user-gene-symbols mode) or
extracted from a local GIGANTIC human T1 proteome (database mode).

---

## Three STEP_0 Workflow Modes

This template has **one** STEP_0 (`STEP_0-hgnc_based_rgs/`) that contains
**three** workflow subdirectories — pick the one that matches your use
case:

### Mode 1: `workflow-COPYME-hgnc_database` — Batch all HGNC gene groups

Process every gene group HGNC curates (~2060 groups). Sequences come
from a GIGANTIC human T1 proteome (configured in the workflow's
`START_HERE-user_config.yaml`). Outputs one RGS FASTA per gene group.

Run this when you want comprehensive coverage of HGNC's curated
classification — useful for whole-proteome questions like "which
membrane transporter families are conserved across X clade."

### Mode 2: `workflow-COPYME-hgnc_user_gene_symbols` — Ad-hoc user gene set

Take a user-supplied TSV of (group_name, gene_symbol) rows and produce
one RGS FASTA per group. Symbols resolve to UniProt accessions via the
local `hgnc_complete_set.txt` (alias/prev_symbol fallback for outdated
symbols); sequences are fetched from UniProt's REST API.

Run this when:
- You want a group HGNC doesn't curate as one (e.g., the **SNAP family**
  SNAP23/25/29/47 — three are in HGNC's "SNAREs" group but SNAP47 isn't).
- You're testing a custom hypothesis with a small ad-hoc gene set.
- You want a "functional complex" or "module" that isn't a single
  evolutionary family (STEP_1 still produces a useful AGS; you'd skip
  STEP_2's tree-building for a non-family set).

### Mode 3: `workflow-COPYME-hgnc_user_gene_group_names` — User-specified HGNC gene groups

Take a user-supplied TSV of HGNC gene-group NAMES (e.g. `Collagens`) or
`gg<N>` IDs (e.g. `gg483`) and produce one RGS FASTA per resolved group.
Reuses MODE 1's HGNC download + aggregation steps; the only mode-specific
script is `002_ai-python-filter_aggregated_gene_sets_by_user_names.py`,
which filters the aggregated gene-set table to the user's groups before
MODE 1's familiar script 003 materializes the RGS files. Sequences come
from the SAME local human T1 proteome MODE 1 uses, and the RGS file
prefix + 5-field header format are reused verbatim.

Additionally emits a side-car
`3_ai-gene_symbol_to_hgnc_group_map.tsv` annotation map — long-format
gene_symbol -> hgnc_group_id -> hgnc_group_name — for downstream
tree-tip subgroup coloring.

Run this when:
- You already know the HGNC group(s) of interest by name or ID
  (e.g., "Collagens", "Gap junction proteins") and want sequences sourced
  from the same human T1 proteome MODE 1 uses.
- You want a small, named subset of HGNC's curated taxonomy without the
  cost of processing all ~2060 groups.

All three modes produce the same downstream output shape: per-group RGS
FASTA in `OUTPUT_pipeline/<N>-output/rgs_fastas/` + a per-group summary
TSV. STEP_1 reads from a single canonical location regardless of which
mode generated the RGS.

---

## Architecture: Why Mode Plurality Is at STEP_0 Only

STEP_0 has three workflows because RGS generation is the only place the
three use cases differ. STEP_1 (homolog discovery), STEP_2 (alignment +
tree), and STEP_3 (visualization) are identical for all three — they
read a per-group summary TSV + a `rgs_fastas/` directory and don't care
how any of them were made. This keeps the heavy machinery (BLAST, MAFFT,
FastTree) unduplicated.

Architectural decoupling note: STEP_1 and STEP_2 are deliberately
separable. STEP_1 happily produces a useful AGS (RGS + homologs) for any
coherent gene set — phylogenetic family, functional complex, or ad-hoc
curiosity. STEP_2 should only run when tree-building is biologically
meaningful (one gene family, not a complex). The user-gene-symbols mode
(MODE 2) inherits this decoupling for free — define a complex like SNARE
in the user TSV, run STEP_0 + STEP_1, stop before STEP_2.

---

## Subproject-Level Shared HGNC Reference

All three STEP_0 workflows share a single canonical copy of HGNC's
`hgnc_complete_set.txt` at
[`../output_to_input/hugo_hgnc_database/`](../output_to_input/hugo_hgnc_database/).

The 000-prefix download script in each workflow (`000_ai-python-download_hgnc_complete_set.py`)
is idempotent against that location: first run populates it; later runs
(across instances, across workflow modes) just copy from the canonical
symlink target. To force a fresh HGNC fetch, delete the canonical
directory.

---

## Conventions Worth Knowing

### COPYME-guard

Every `RUN-workflow.sh` in this template refuses to run when invoked
from a directory whose name contains `COPYME`. Users must instantiate
first:

```bash
cp -r gene_groups_hgnc-COPYME gene_groups-<my_instance>
cd gene_groups-<my_instance>/
```

### Dynamic instance name derivation

`RUN-workflow.sh` derives `INSTANCE_NAME` and `STEP_NAME` from the
directory hierarchy at run time. There are no hardcoded
`gene_groups-<name>` paths in the scripts. This is what makes the
template portable to arbitrary instance names.

### Conda env shared across the three workflows

All of `workflow-COPYME-hgnc_database`, `workflow-COPYME-hgnc_user_gene_symbols`,
and `workflow-COPYME-hgnc_user_gene_group_names` declare the
same conda env (`aiG-trees_gene_groups-hgnc_based_rgs`) — same
dependencies (python + pyyaml + nextflow stdlib only; UniProt fetches
use urllib, not `requests`; `difflib` used by MODE 3's script 002 is
stdlib). The env is auto-created on first run of any workflow.

### Per-sequence RGS FASTA headers — TWO formats by source

The three STEP_0 workflows emit only TWO distinct header shapes;
STEP_1's script 008 dispatches on shape. MODE 1 (`hgnc_database`) and
MODE 3 (`hgnc_user_gene_group_names`) share the same 5-field
hgnc/ncbi-sourced format because they both extract sequences from the
local human T1 proteome via the same script 003. MODE 2
(`hgnc_user_gene_symbols`) emits a distinct 4-field uniprot-sourced
format because it fetches from UniProt REST.

```
# workflow-COPYME-hgnc_database AND workflow-COPYME-hgnc_user_gene_group_names (5-field):
>rgs_<group>-<species>-<symbol>-hgnc_gg<NNN>_<group_name>-<NP_or_XP_accession>
# example: rgs_syntaxins-human-STX10-hgnc_gg818_Syntaxins-NP_003756_1

# workflow-COPYME-hgnc_user_gene_symbols (4-field, source+id concatenated):
>rgs_<group>-<species>-<symbol>-uniprot<accession>
# example: rgs_snap_family-human-SNAP25-uniprotP60880
```

The 4-field user-gene-symbols shape concatenates source and accession
into a single field (`uniprotP60880`, not `uniprot-P60880`) — this keeps
the dash count unambiguous for parsers and avoids confusion with the
5-field database shape. STEP_1's script 008 detects the 4-vs-5-field
shape and the `uniprot` prefix in field 4 to dispatch:

- 4-field uniprot-sourced → Improvement 0 (strict gene-symbol search)
- 5-field hgnc/ncbi-sourced → Improvement 1 (exact NCBI accession match)

Both are strict and fail-fast; there is no BLAST rescue (removed
2026-05-26 — see STEP_1 docs).

### Per-group summary TSV (STEP_1 reads this)

All three modes produce a per-group summary TSV with 5 columns:
`Gene_Group_ID`, `Gene_Group_Name`, `Sanitized_Name`, `RGS_Filename`,
`Sequence_Count`. STEP_1's orchestrator iterates over this TSV to
materialize one `gene_group-<sanitized>/workflow-RUN_01-*/` per gene
group.

For `workflow-COPYME-hgnc_database` this is `3_ai-rgs_generation_summary.tsv`
(emitted by script 003). For `workflow-COPYME-hgnc_user_gene_symbols` this is
`2_ai-rgs_generation_summary.tsv` (emitted by script 002). For
`workflow-COPYME-hgnc_user_gene_group_names` this is
`3_ai-rgs_generation_summary.tsv` (emitted by script 003 — same N as MODE 1).

---

## See Also

- [README.md](README.md) — User-facing instantiation guide
- [../output_to_input/hugo_hgnc_database/README.md](../output_to_input/hugo_hgnc_database/README.md) — canonical reference data
- [STEP_0-hgnc_based_rgs/AI_GUIDE.md](STEP_0-hgnc_based_rgs/AI_GUIDE.md) — STEP_0 concepts
- [STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_database/ai/AI_GUIDE.md](STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_database/ai/AI_GUIDE.md)
- [STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_symbols/ai/AI_GUIDE.md](STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_symbols/ai/AI_GUIDE.md)
- [STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_group_names/ai/AI_GUIDE.md](STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_group_names/ai/AI_GUIDE.md)
