# AI Guide: STEP_0 — HGNC-Based RGS (trees_gene_groups)

**For AI Assistants**: Read `../../../AI_GUIDE-project.md` first, then
`../../AI_GUIDE-trees_gene_groups.md` for the subproject, then
`../AI_GUIDE-gene_groups_hgnc.md` for this template. This file covers
STEP_0 specifically.

**Location**: `gene_groups_hgnc-COPYME/STEP_0-hgnc_based_rgs/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## What This STEP Does

**Purpose**: Materialize a per-gene-group Reference Gene Set (RGS) FASTA
where each sequence is a **human protein anchor** for the group.

**Output (shared shape across both workflow modes)**:
- `OUTPUT_pipeline/<N>-output/rgs_fastas/rgs_<source-tag>-human-<group>.aa` — one per group
- `OUTPUT_pipeline/<N>-output/<N>_ai-rgs_generation_summary.tsv` — per-group summary
  (5 columns: `Gene_Group_ID`, `Gene_Group_Name`, `Sanitized_Name`,
  `RGS_Filename`, `Sequence_Count`) — this is the file STEP_1 reads.
- Symlinks at `../../../output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/`
  pointing back at the real files in OUTPUT_pipeline.

These outputs are independent of which workflow mode produced them —
STEP_1 doesn't know or care.

---

## Two Workflow Modes Under This STEP

```
STEP_0-hgnc_based_rgs/
├── workflow-hgnc_database/      # MODE 1: batch process all ~2060 HGNC gene groups
└── workflow-hgnc_user_list/     # MODE 2: ad-hoc user-supplied gene set
```

| Mode | Group source | Sequence source | When to use |
|---|---|---|---|
| `workflow-hgnc_database` | HGNC's curated `family.csv` + `hgnc_gene_groups_all.tsv` | Local GIGANTIC human T1 proteome (`.aa`) | Comprehensive coverage of HGNC's classification |
| `workflow-hgnc_user_list` | User TSV at instance-level `INPUT_user/user_gene_set.tsv` | UniProt REST API (per-accession FASTA fetch) | Custom gene sets, especially groups HGNC doesn't curate (e.g., SNAP family with SNAP47) |

Each mode has its own AI_GUIDE under `ai/AI_GUIDE-*_workflow.md`.

---

## Why Both Modes Exist

HGNC's gene-group classification is curated for one organizing principle
(roughly: shared biological/functional context), and not every
research-relevant gene set fits neatly into one of HGNC's ~2060 groups.

The motivating case is the **SNAP family** (Synaptosomal-Associated
Proteins SNAP23/25/29/47): three of those are in HGNC group 1124
("SNAREs"), but SNARE is a protein-complex category, not a gene family,
and SNAP47 isn't in any HGNC group at all. The user-list mode handles
that case cleanly — the user declares the gene set by listing the
symbols, and HGNC's `hgnc_complete_set.txt` is used only as a
**symbol-to-UniProt-accession resolution table**, not as the source of
group membership.

---

## Shared Subproject-Level HGNC Reference

Both workflows read/produce a single canonical HGNC TSV at
`../../../output_to_input/hugo_hgnc_database/hgnc_complete_set.txt`.

The 000-prefix download script (`ai/scripts/000_ai-python-download_hgnc_complete_set.py`)
in each workflow is idempotent against that location:

1. If the canonical TSV exists, the script copies it into the workflow's
   local `OUTPUT_pipeline/0-output/` (skip network fetch).
2. Otherwise, it downloads fresh from
   `https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt`.

After the workflow completes, `RUN-workflow.sh` (re)creates the symlink
at the canonical location pointing back into the most recent run's
OUTPUT_pipeline.

This pattern lets the first STEP_0 run in a fresh subproject populate
the reference data, and every subsequent run — across instances, across
workflow modes — skip the network fetch.

To **force a refresh** from HGNC, delete the canonical directory:

```bash
rm -rf ../../../output_to_input/hugo_hgnc_database/
```

---

## Naming Conventions

### Workflow output dirs

- `workflow-hgnc_database` produces 4 N-output dirs: 0, 1, 2, 3
  (one per script: 000 → 001 → 002 → 003).
- `workflow-hgnc_user_list` produces 3 N-output dirs: 0, 1, 2.

### Per-group RGS filenames

- `workflow-hgnc_database`: `rgs_hugo_hgnc-human-<sanitized_group_name>.aa`
- `workflow-hgnc_user_list`: `rgs_hgnc_user-human-<sanitized_group_name>.aa`

The different filename prefixes (`hugo_hgnc` vs `hgnc_user`) document
which mode produced the RGS at a glance. STEP_1 doesn't care about the
filename prefix — it reads the per-group summary TSV to find the
filename.

### Per-sequence FASTA headers (5 dash-delimited fields)

Both modes use the GIGANTIC 5-field convention STEP_1's parser
expects:

```
>rgs_<group_sanitized>-human-<symbol>-<source>-<accession>
```

| Mode | source field | accession field |
|---|---|---|
| `workflow-hgnc_database` | `hgnc_gg<NNNN>_<group_name>` | NCBI RefSeq protein accession (e.g., `NP_003756_1`) |
| `workflow-hgnc_user_list` | `uniprot` | UniProt accession (e.g., `O00161`) |

---

## How STEP_0 Hands Off to STEP_1

STEP_1's `START_HERE-user_config.yaml` has two keys that point at STEP_0
outputs:

```yaml
gene_group_source_tsv: "../../../output_to_input/<INSTANCE>/STEP_0-hgnc_based_rgs/<N>_ai-rgs_generation_summary.tsv"
rgs_fastas_dir:        "../../../output_to_input/<INSTANCE>/STEP_0-hgnc_based_rgs/rgs_fastas"
```

Per workflow mode:
- `workflow-hgnc_database` → `3_ai-rgs_generation_summary.tsv`
- `workflow-hgnc_user_list` → `2_ai-rgs_generation_summary.tsv`

STEP_1 iterates the summary TSV's rows, copies its `workflow-rbh_rbf_homologs`
template once per gene group into `gene_group-<sanitized>/workflow-RUN_01-rbh_rbf_homologs/`,
and dispatches BLAST.

---

## Troubleshooting (Common Errors)

| Symptom | Likely Cause | Fix |
|---|---|---|
| `RUN-workflow.sh: refuses to run from COPYME directory` | Running from the template instead of an instance | `cp -r gene_groups_hgnc-COPYME gene_groups-<your_name>` and run from the instance |
| `hgnc_complete_set.txt download failed` | No network from compute node, or genenames.org unreachable | Check `curl https://storage.googleapis.com/...` from the node; consider running STEP_0 on the login node first to populate canonical |
| `workflow-hgnc_user_list` 001 prints `NOT_FOUND: <symbol>` and exits | User-supplied symbol isn't an HGNC-approved symbol or alias | Check spelling, consult genenames.org for the current canonical symbol |
| `workflow-hgnc_user_list` 002 reports `FAILED_FETCH` for an accession | UniProt API unavailable, or accession withdrawn | Re-run later; or check `https://rest.uniprot.org/uniprotkb/<accession>.fasta` directly |
| STEP_1 says "no such file or directory" for the summary TSV | STEP_1 config still has `<INSTANCE>` placeholder | Edit `STEP_1-homolog_discovery/workflow-rbh_rbf_homologs/START_HERE-user_config.yaml`, replace placeholders with actual instance name + workflow's N-output number |

---

## See Also

- `workflow-hgnc_database/ai/AI_GUIDE-hgnc_database_workflow.md` — batch HGNC workflow
- `workflow-hgnc_user_list/ai/AI_GUIDE-hgnc_user_list_workflow.md` — user-list workflow
- `../README.md` — instantiation guide for the template
- `../AI_GUIDE-gene_groups_hgnc.md` — template-level AI guide
- `../../output_to_input/hugo_hgnc_database/README.md` — canonical reference data
