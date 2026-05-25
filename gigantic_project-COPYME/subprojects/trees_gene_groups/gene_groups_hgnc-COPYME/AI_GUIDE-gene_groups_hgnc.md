# AI Guide: gene_groups_hgnc-COPYME (HGNC-Anchored Template)

**For AI Assistants**: Read `../../../AI_GUIDE-project.md` first for the
GIGANTIC project overview. Then `../AI_GUIDE-trees_gene_groups.md` for
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
| GIGANTIC project overview | `../../../AI_GUIDE-project.md` |
| trees_gene_groups subproject concepts | `../AI_GUIDE-trees_gene_groups.md` |
| This template's overview (this file) | this file |
| STEP_0 concepts (HGNC-based RGS generation) | `STEP_0-hgnc_based_rgs/AI_GUIDE-hgnc_based_rgs.md` |
| STEP_0 workflow: process all HGNC gene groups | `STEP_0-hgnc_based_rgs/workflow-hgnc_database/ai/AI_GUIDE-hgnc_database_workflow.md` |
| STEP_0 workflow: ad-hoc user-supplied gene set | `STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/ai/AI_GUIDE-hgnc_user_list_workflow.md` |
| STEP_1 concepts (RBH/RBF homolog discovery) | `STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` |
| STEP_2 concepts (alignment + tree) | `STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` |
| STEP_3 concepts (tree visualization) | `STEP_3-tree_visualization/AI_GUIDE-phylogenetic_visualization.md` |

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
accession), either fetched from UniProt REST (user-list mode) or
extracted from a local GIGANTIC human T1 proteome (database mode).

---

## Two STEP_0 Workflow Modes

This template has **one** STEP_0 (`STEP_0-hgnc_based_rgs/`) that contains
**two** workflow subdirectories — pick the one that matches your use
case:

### Mode 1: `workflow-hgnc_database` — Batch all HGNC gene groups

Process every gene group HGNC curates (~2060 groups). Sequences come
from a GIGANTIC human T1 proteome (configured in the workflow's
`START_HERE-user_config.yaml`). Outputs one RGS FASTA per gene group.

Run this when you want comprehensive coverage of HGNC's curated
classification — useful for whole-proteome questions like "which
membrane transporter families are conserved across X clade."

### Mode 2: `workflow-hgnc_user_list` — Ad-hoc user gene set

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

Both modes produce the same downstream output shape: per-group RGS FASTA
in `OUTPUT_pipeline/<N>-output/rgs_fastas/` + a per-group summary TSV.
STEP_1 reads from a single canonical location regardless of which mode
generated the RGS.

---

## Architecture: Why Mode Plurality Is at STEP_0 Only

STEP_0 has two workflows because RGS generation is the only place the
two use cases differ. STEP_1 (homolog discovery), STEP_2 (alignment +
tree), and STEP_3 (visualization) are identical for both — they read a
per-group summary TSV + a `rgs_fastas/` directory and don't care how
either was made. This keeps the heavy machinery (BLAST, MAFFT, FastTree)
unduplicated.

Architectural decoupling note: STEP_1 and STEP_2 are deliberately
separable. STEP_1 happily produces a useful AGS (RGS + homologs) for any
coherent gene set — phylogenetic family, functional complex, or ad-hoc
curiosity. STEP_2 should only run when tree-building is biologically
meaningful (one gene family, not a complex). The `_user_list` mode
inherits this decoupling for free — define a complex like SNARE in the
user TSV, run STEP_0 + STEP_1, stop before STEP_2.

---

## Subproject-Level Shared HGNC Reference

Both STEP_0 workflows share a single canonical copy of HGNC's
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

### Conda env shared across the two workflows

Both `workflow-hgnc_database` and `workflow-hgnc_user_list` declare the
same conda env (`aiG-trees_gene_groups-hgnc_based_rgs`) — same
dependencies (python + pyyaml + nextflow stdlib only; UniProt fetches
use urllib, not `requests`). The env is auto-created on first run of
either workflow.

### Per-sequence RGS FASTA header (5 dash-delimited fields)

Both modes emit per-sequence headers in the GIGANTIC 5-field convention
that STEP_1's parser expects:

```
>rgs_<group_sanitized>-human-<symbol>-<source>-<accession>
```

`<source>` is:
- `hgnc_gg<NNNN>_<group_name>` for `workflow-hgnc_database` (preserves
  HGNC's gene-group ID + name; sequence source is the local human
  proteome, which itself derives from NCBI RefSeq / UniProt — the
  accession field carries that)
- `uniprot` for `workflow-hgnc_user_list` (sequence fetched directly
  from UniProt REST)

### Per-group summary TSV (STEP_1 reads this)

Both modes produce a per-group summary TSV with 5 columns:
`Gene_Group_ID`, `Gene_Group_Name`, `Sanitized_Name`, `RGS_Filename`,
`Sequence_Count`. STEP_1's orchestrator iterates over this TSV to
materialize one `gene_group-<sanitized>/workflow-RUN_01-*/` per gene
group.

For `workflow-hgnc_database` this is `3_ai-rgs_generation_summary.tsv`
(emitted by script 003). For `workflow-hgnc_user_list` this is
`2_ai-rgs_generation_summary.tsv` (emitted by script 002).

---

## See Also

- [README.md](README.md) — User-facing instantiation guide
- [../output_to_input/hugo_hgnc_database/README.md](../output_to_input/hugo_hgnc_database/README.md) — canonical reference data
- [STEP_0-hgnc_based_rgs/AI_GUIDE-hgnc_based_rgs.md](STEP_0-hgnc_based_rgs/AI_GUIDE-hgnc_based_rgs.md) — STEP_0 concepts
- [STEP_0-hgnc_based_rgs/workflow-hgnc_database/ai/AI_GUIDE-hgnc_database_workflow.md](STEP_0-hgnc_based_rgs/workflow-hgnc_database/ai/AI_GUIDE-hgnc_database_workflow.md)
- [STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/ai/AI_GUIDE-hgnc_user_list_workflow.md](STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/ai/AI_GUIDE-hgnc_user_list_workflow.md)
