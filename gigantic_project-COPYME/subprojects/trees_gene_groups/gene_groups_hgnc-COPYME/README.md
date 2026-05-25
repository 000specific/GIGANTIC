# gene_groups_hgnc-COPYME — HGNC-Anchored Gene-Group Template

Sibling template to [gene_groups-COPYME](../gene_groups-COPYME/) within the
`trees_gene_groups` subproject. This template is specialized for analyses
anchored on **HUGO HGNC** human-gene nomenclature: it bundles a STEP_0 that
emits per-group RGS FASTAs from HGNC-resolved UniProt accessions, then
reuses the generic STEP_1 / STEP_2 / STEP_3 below.

> The generic `gene_groups-COPYME/` is source-agnostic (Pfam, InterPro,
> custom lists, etc.). `gene_groups_hgnc-COPYME/` is the HGNC-flavored
> sibling. They coexist forever — instances of either are research
> artifacts and are not migrated retroactively.

---

## When to use this template vs. its sibling

| Want to … | Use … |
|---|---|
| Process **all ~2060 HGNC-curated gene groups** as a batch | This template → `STEP_0-hgnc_based_rgs/workflow-hgnc_database/` |
| Build an **ad-hoc gene set** anchored on specific human gene symbols (incl. groups HGNC doesn't curate, e.g. SNAP family with SNAP47) | This template → `STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/` |
| Build gene groups from a **non-HGNC source** (Pfam, InterPro, custom TSV) | `gene_groups-COPYME/` (sibling) |

---

## Two STEP_0 workflows under this template

```
gene_groups_hgnc-COPYME/
├── README.md                                              (this file)
├── INPUT_user/
│   ├── README.md
│   └── user_gene_set_EXAMPLE.tsv                          # used by hgnc_user_list mode
├── STEP_0-hgnc_based_rgs/                                 # NEW (HGNC-specific)
│   ├── workflow-hgnc_database/                            # MODE 1: all HGNC groups
│   │   ├── RUN-workflow.sh
│   │   ├── START_HERE-user_config.yaml
│   │   └── ai/
│   │       ├── main.nf, nextflow.config, conda_environment.yml
│   │       └── scripts/
│   │           ├── 000_ai-python-download_hgnc_complete_set.py
│   │           ├── 001_ai-python-download_hgnc_gene_group_data.py
│   │           ├── 002_ai-python-build_aggregated_gene_sets.py
│   │           └── 003_ai-python-generate_rgs_fasta_files.py
│   └── workflow-hgnc_user_list/                           # MODE 2: ad-hoc user set
│       ├── RUN-workflow.sh
│       ├── START_HERE-user_config.yaml
│       └── ai/
│           ├── main.nf, nextflow.config, conda_environment.yml
│           └── scripts/
│               ├── 000_ai-python-download_hgnc_complete_set.py    (same as database mode)
│               ├── 001_ai-python-resolve_user_symbols_to_uniprot.py
│               └── 002_ai-python-fetch_uniprot_fastas-emit_rgs.py
├── STEP_1-homolog_discovery/                              # shared with gene_groups-COPYME
├── STEP_2-phylogenetic_analysis/                          # shared
└── STEP_3-tree_visualization/                             # shared
```

Both STEP_0 workflows produce the **same output shape** — per-group RGS
FASTAs at `OUTPUT_pipeline/<N>-output/rgs_fastas/` + a per-group summary
TSV (the file STEP_1 iterates over) — so STEP_1 / STEP_2 / STEP_3
downstream are oblivious to which mode generated the input.

---

## Subproject-level HGNC reference

Both STEP_0 workflows share a single canonical copy of HGNC's
`hgnc_complete_set.txt` at
[`../output_to_input/hugo_hgnc_database/`](../output_to_input/hugo_hgnc_database/).
The 000-prefix download script is idempotent against that location —
the first STEP_0 run in a fresh subproject populates it; subsequent
runs (including those in unrelated instances of this template) skip the
network fetch and copy from the canonical symlink target.

See [`../output_to_input/hugo_hgnc_database/README.md`](../output_to_input/hugo_hgnc_database/README.md)
for details on the symlink convention.

---

## Instantiating: the canonical SNAP family workflow

This is the user-experience for the "ad-hoc gene family from human anchors"
case. End-to-end it took ~3 seconds (excluding the HGNC download, which
is one-time per subproject):

```bash
cd gigantic_project-COPYME/subprojects/trees_gene_groups/

# 1. Copy the template to a real instance (a "research notebook" for SNAP family)
cp -r gene_groups_hgnc-COPYME gene_groups-snap_family

# 2. Replace the example user gene set with your own
cd gene_groups-snap_family/INPUT_user/
mv user_gene_set_EXAMPLE.tsv user_gene_set.tsv
# Edit user_gene_set.tsv: header row + one row per (group, symbol).
# For SNAP family, four rows:
#   snap_family<TAB>Synaptosomal-Associated Proteins<TAB>SNAP23
#   snap_family<TAB>...<TAB>SNAP25
#   snap_family<TAB>...<TAB>SNAP29
#   snap_family<TAB>...<TAB>SNAP47

# 3. Run STEP_0 (the user_list mode for this case)
cd ../STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/
bash RUN-workflow.sh
# → 000 downloads hgnc_complete_set.txt (or reuses canonical)
# → 001 resolves SNAP23/25/29/47 → UniProt accessions via HGNC
# → 002 fetches Swiss-Prot FASTA from UniProt REST → emits rgs_hgnc_user-human-snap_family.aa
# → symlinks land in trees_gene_groups/output_to_input/gene_groups-snap_family/STEP_0-hgnc_based_rgs/

# 4. Run STEP_1, STEP_2, STEP_3 from the instance (each has its own RUN-workflow.sh)
```

For the **HGNC database mode** (process all HGNC gene groups), instantiate
similarly but run `STEP_0-hgnc_based_rgs/workflow-hgnc_database/RUN-workflow.sh`
instead — and provide the path to a GIGANTIC human T1 proteome in that
workflow's START_HERE config (it extracts sequences from the proteome
rather than fetching from UniProt).

---

## STEP_1 / STEP_2 / STEP_3 (inherited)

These are unchanged from the sibling `gene_groups-COPYME/` template —
both STEP_0 workflows produce the same per-group RGS FASTA + per-group
summary TSV, so the downstream pipeline runs identically. See the
sibling template's STEP-level AI_GUIDEs for details:

- `STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` — RBH/RBF homolog discovery
- `STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` — alignment + tree
- `STEP_3-tree_visualization/AI_GUIDE-phylogenetic_visualization.md` — rendering

Each instance run uses the per-STEP `RUN-workflow.sh` orchestrator
(single user-runnable script): it creates its conda env once on the
login node, iterates over the gene groups from STEP_0's summary TSV,
materializes one `gene_group-<name>/workflow-RUN_01-<stepname>/` per
gene group, and dispatches per `execution_mode` (`local`,
`slurm-standard`, or `slurm-burst`).

---

## Important conventions

- The **template** (this directory) ends in `-COPYME`; the COPYME-guard
  in every `RUN-workflow.sh` refuses to run from a `*COPYME*` directory.
  You must instantiate first.
- **Instance names** are derived dynamically by `RUN-workflow.sh` from
  the directory hierarchy — there are no hardcoded `gene_groups-<name>`
  paths in the scripts. Any instance name works (`gene_groups-snap_family`,
  `gene_groups-my_curiosity`, …).
- **Don't migrate old instances** onto this template. `gene_groups-hugo_hgnc`
  is built on the sibling generic template (`gene_groups-COPYME`) plus a
  source-specific STEP_0 named `STEP_0-hgnc_gene_groups/`. It stays that
  way as a research notebook + data archive of the older code path.

---

## See also

- [../AI_GUIDE-trees_gene_groups.md](../AI_GUIDE-trees_gene_groups.md) — subproject-level AI guide
- [../README.md](../README.md) — subproject overview
- [AI_GUIDE-gene_groups_hgnc.md](AI_GUIDE-gene_groups_hgnc.md) — this template's AI guide
- [STEP_0-hgnc_based_rgs/AI_GUIDE-hgnc_based_rgs.md](STEP_0-hgnc_based_rgs/AI_GUIDE-hgnc_based_rgs.md) — STEP_0 concepts
- [STEP_0-hgnc_based_rgs/workflow-hgnc_database/ai/AI_GUIDE-hgnc_database_workflow.md](STEP_0-hgnc_based_rgs/workflow-hgnc_database/ai/AI_GUIDE-hgnc_database_workflow.md) — batch HGNC mode
- [STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/ai/AI_GUIDE-hgnc_user_list_workflow.md](STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/ai/AI_GUIDE-hgnc_user_list_workflow.md) — user-list mode
