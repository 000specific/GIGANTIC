# AI Guide: STEP_0 — HGNC-Based RGS (trees_gene_groups)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
AI:      Claude Code | Opus 4.7 | 2026 May 29 (parity-finishing pass — MODE 3 added)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (template AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md)
- Parent (template README): [`../README.md`](../README.md)
- Parent (subproject AI guide): [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Three workflow modes (pick the one that fits your case):
-   - [`workflow-COPYME-hgnc_database/`](workflow-COPYME-hgnc_database/) — downloads HGNC + produces ALL gene-group RGSs (MODE 1)
-   - [`workflow-COPYME-hgnc_user_gene_symbols/`](workflow-COPYME-hgnc_user_gene_symbols/) — curated user subset by gene SYMBOLS (MODE 2)
-   - [`workflow-COPYME-hgnc_user_gene_group_names/`](workflow-COPYME-hgnc_user_gene_group_names/) — user-supplied HGNC group NAMES or `gg<N>` IDs, sequences from local human T1 proteome (MODE 3)
- Reads FROM: HGNC public database (network download by workflow-COPYME-hgnc_database) + `INPUT_user/user_gene_set_*.tsv` (workflow-COPYME-hgnc_user_gene_symbols mode) + `INPUT_user/user_gene_group_names_*.tsv` (workflow-COPYME-hgnc_user_gene_group_names mode)
- Outputs TO: per-gene-group RGS FASTAs consumed by `../STEP_1-homolog_discovery/`
- Conda env: `aiG-trees_gene_groups-hgnc_based_rgs`
- 2026-05-26: BLAST-fallback in STEP_1 was removed; all three STEP_0 workflows produce RGS that resolve cleanly via gene-symbol or NCBI-accession matching (no source-genome BLAST chain needed)

---

**For AI Assistants**: Read `../../../AI_GUIDE.md` first, then
`../../AI_GUIDE.md` for the subproject, then
`../AI_GUIDE.md` for this template. This file covers
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

**Output (shared shape across all three workflow modes)**:
- `OUTPUT_pipeline/<N>-output/rgs_fastas/rgs_<source-tag>-human-<group>.aa` — one per group
- `OUTPUT_pipeline/<N>-output/<N>_ai-rgs_generation_summary.tsv` — per-group summary
  (5 columns: `Gene_Group_ID`, `Gene_Group_Name`, `Sanitized_Name`,
  `RGS_Filename`, `Sequence_Count`) — this is the file STEP_1 reads.
- Symlinks at `../../../output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/`
  pointing back at the real files in OUTPUT_pipeline.

These outputs are independent of which workflow mode produced them —
STEP_1 doesn't know or care.

---

## Three Workflow Modes Under This STEP

```
STEP_0-hgnc_based_rgs/
├── workflow-COPYME-hgnc_database/                 # MODE 1: batch process all ~2060 HGNC gene groups
├── workflow-COPYME-hgnc_user_gene_symbols/        # MODE 2: ad-hoc user-supplied gene SYMBOLS
└── workflow-COPYME-hgnc_user_gene_group_names/    # MODE 3: user-supplied HGNC group names/IDs
```

| Mode | Group source | Sequence source | When to use |
|---|---|---|---|
| `workflow-COPYME-hgnc_database` | HGNC's curated `family.csv` + `hgnc_gene_groups_all.tsv` | Local GIGANTIC human T1 proteome (`.aa`) | Comprehensive coverage of HGNC's classification |
| `workflow-COPYME-hgnc_user_gene_symbols` | User TSV at instance-level `INPUT_user/user_gene_set.tsv` | UniProt REST API (per-accession FASTA fetch) | Custom gene sets, especially groups HGNC doesn't curate (e.g., SNAP family with SNAP47) |
| `workflow-COPYME-hgnc_user_gene_group_names` | User TSV at instance-level `INPUT_user/user_gene_group_names.tsv` — HGNC group NAMES (e.g. `Collagens`) or `gg<N>` IDs | Local GIGANTIC human T1 proteome (`.aa`) | Materialize a subset of HGNC groups you already know by name/ID, with same sequence source + RGS shape as MODE 1 — plus a side-car `gene_symbol -> hgnc_group` annotation map for tree-tip subgroup coloring |

Each mode has its own AI_GUIDE under `ai/AI_GUIDE-*_workflow.md`.

---

## Why Multiple Modes Exist

HGNC's gene-group classification is curated for one organizing principle
(roughly: shared biological/functional context), and not every
research-relevant gene set fits neatly into one of HGNC's ~2060 groups.

The motivating case for **MODE 2** is the **SNAP family**
(Synaptosomal-Associated Proteins SNAP23/25/29/47): three of those are
in HGNC group 1124 ("SNAREs"), but SNARE is a protein-complex category,
not a gene family, and SNAP47 isn't in any HGNC group at all. The
user-gene-symbols mode (MODE 2) handles that case cleanly — the user
declares the gene set by listing the symbols, and HGNC's
`hgnc_complete_set.txt` is used only as a
**symbol-to-UniProt-accession resolution table**, not as the source of
group membership.

The motivating case for **MODE 3** is the inverse: the user knows which
HGNC groups they want (e.g. `Collagens`, `Cannabinoid receptors`) but
not the full symbol list, or the family spans several HGNC groups
(collagens are split across 7). MODE 3 takes a list of group NAMES or
`gg<N>` IDs and produces the per-group RGS FASTAs MODE 1 would have
emitted — plus a side-car gene_symbol → hgnc_group annotation map for
post-tree subgroup coloring. Sequence source is the local human T1
proteome, same as MODE 1.

---

## Shared Subproject-Level HGNC Reference

All three workflows read/produce a single canonical HGNC TSV at
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

- `workflow-COPYME-hgnc_database` produces 4 N-output dirs: 0, 1, 2, 3
  (one per script: 000 → 001 → 002 → 003).
- `workflow-COPYME-hgnc_user_gene_symbols` produces 3 N-output dirs: 0, 1, 2.
- `workflow-COPYME-hgnc_user_gene_group_names` produces 4 N-output dirs: 0, 1, 2, 3
  (same N as MODE 1; script 002 is `filter_aggregated_gene_sets_by_user_names`).

### Per-group RGS filenames

- `workflow-COPYME-hgnc_database`: `rgs_hugo_hgnc-human-<sanitized_group_name>.aa`
- `workflow-COPYME-hgnc_user_gene_symbols`: `rgs_hgnc_user-human-<sanitized_group_name>.aa`
- `workflow-COPYME-hgnc_user_gene_group_names`: `rgs_hugo_hgnc-human-<sanitized_group_name>.aa`
  (SAME prefix as MODE 1 — sequences come from the same human T1 proteome and
  are emitted by the same script 003).

The different filename prefixes (`hugo_hgnc` vs `hgnc_user`) document
which mode produced the RGS at a glance. STEP_1 doesn't care about the
filename prefix — it reads the per-group summary TSV to find the
filename.

### Per-sequence FASTA headers (two formats by source)

The workflows emit two distinct per-sequence header formats (MODE 1 + MODE 3 share one; MODE 2 has the other); STEP_1's
script 008 dispatches on the format and uses a different identification
mechanism for each:

```
# workflow-COPYME-hgnc_database (5-field, hgnc/ncbi-sourced):
>rgs_<group>-<species>-<symbol>-hgnc_gg<NNN>_<group_name>-<NP_or_XP_accession>

# workflow-COPYME-hgnc_user_gene_symbols (4-field, uniprot-sourced; concatenated source+id):
>rgs_<group>-<species>-<symbol>-uniprot<accession>
```

| Mode | Field count | Field 4 | Field 5 | STEP_1 mechanism |
|---|---|---|---|---|
| `workflow-COPYME-hgnc_database` | 5 | `hgnc_gg<NNNN>_<group_name>` | NCBI RefSeq accession (`NP_003756_1`) | Improvement 1 (exact NCBI accession match) |
| `workflow-COPYME-hgnc_user_gene_symbols` | 4 | `uniprot<accession>` (concatenated, e.g. `uniprotO00161`) | — | Improvement 0 (strict gene-symbol search) |
| `workflow-COPYME-hgnc_user_gene_group_names` | 5 | `hgnc_gg<NNNN>_<group_name>` | NCBI RefSeq accession (`NP_003756_1`) | Improvement 1 (exact NCBI accession match) — same as MODE 1 |

The concatenation of source + accession in the 4-field format
(`uniprotP60880` rather than `uniprot-P60880`) is deliberate — it keeps
the dash count unambiguous when STEP_1's parser splits the header on
dashes, while remaining compact for embedding in downstream identifiers.

---

## How STEP_0 Hands Off to STEP_1

STEP_1's `START_HERE-user_config.yaml` has two keys that point at STEP_0
outputs:

```yaml
gene_group_source_tsv: "../../../output_to_input/<INSTANCE>/STEP_0-hgnc_based_rgs/<N>_ai-rgs_generation_summary.tsv"
rgs_fastas_dir:        "../../../output_to_input/<INSTANCE>/STEP_0-hgnc_based_rgs/rgs_fastas"
```

Per workflow mode:
- `workflow-COPYME-hgnc_database` → `3_ai-rgs_generation_summary.tsv`
- `workflow-COPYME-hgnc_user_gene_symbols` → `2_ai-rgs_generation_summary.tsv`
- `workflow-COPYME-hgnc_user_gene_group_names` → `3_ai-rgs_generation_summary.tsv` (same N as MODE 1)

STEP_1 iterates the summary TSV's rows, copies its `workflow-COPYME-rbh_rbf_homologs`
template once per gene group into `gene_group-<sanitized>/workflow-RUN_01-rbh_rbf_homologs/`,
and dispatches BLAST.

---

## Troubleshooting (Common Errors)

| Symptom | Likely Cause | Fix |
|---|---|---|
| `RUN-workflow.sh: refuses to run from COPYME directory` | Running from the template instead of an instance | `cp -r gene_groups_hgnc-COPYME gene_groups-<your_name>` and run from the instance |
| `hgnc_complete_set.txt download failed` | No network from compute node, or genenames.org unreachable | Check `curl https://storage.googleapis.com/...` from the node; consider running STEP_0 on the login node first to populate canonical |
| `workflow-COPYME-hgnc_user_gene_symbols` 001 prints `NOT_FOUND: <symbol>` and exits | User-supplied symbol isn't an HGNC-approved symbol or alias | Check spelling, consult genenames.org for the current canonical symbol |
| `workflow-COPYME-hgnc_user_gene_symbols` 002 reports `FAILED_FETCH` for an accession | UniProt API unavailable, or accession withdrawn | Re-run later; or check `https://rest.uniprot.org/uniprotkb/<accession>.fasta` directly |
| `workflow-COPYME-hgnc_user_gene_group_names` 002 reports `NOT_FOUND` for a user-named group | User-typed name doesn't match a current HGNC group name (or the `gg<N>` ID doesn't exist) | The workflow writes `OUTPUT_pipeline/2-output/2_ai-unresolved_groups.tsv` with up to 5 "did you mean..." candidates; grep `2_ai-hgnc_group_catalog.tsv` for the canonical spelling, then fix the input TSV |
| `workflow-COPYME-hgnc_user_gene_group_names` drops loci the user expected to keep | Locus-type allowlist excluded pseudogenes / RNA / Ig / TR / readthrough / ERV by default (matches MODE 1) | Flip `filters.include_pseudogenes` or `filters.include_non_protein_coding` to `true` in `START_HERE-user_config.yaml`; the change is recorded in `2_ai-filter_policy.tsv` |
| STEP_1 says "no such file or directory" for the summary TSV | STEP_1 config still has `<INSTANCE>` placeholder | Edit `STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/START_HERE-user_config.yaml`, replace placeholders with actual instance name + workflow's N-output number |

---

## See Also

- `workflow-COPYME-hgnc_database/ai/AI_GUIDE.md` — batch HGNC workflow (MODE 1)
- `workflow-COPYME-hgnc_user_gene_symbols/ai/AI_GUIDE.md` — user-gene-symbols workflow (MODE 2)
- `workflow-COPYME-hgnc_user_gene_group_names/ai/AI_GUIDE.md` — user-HGNC-group-names workflow (MODE 3)
- `../README.md` — instantiation guide for the template
- `../AI_GUIDE.md` — template-level AI guide
- `../../output_to_input/hugo_hgnc_database/README.md` — canonical reference data
