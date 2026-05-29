# AI Guide: workflow-COPYME-hgnc_user_gene_group_names (STEP_0 / HGNC-Based RGS)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29 (initial)
AI:      Claude Code | Opus 4.7 | 2026 May 29 (parity-finishing pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (template AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sister workflows:
  - [`../../workflow-COPYME-hgnc_database/`](../../workflow-COPYME-hgnc_database/) — MODE 1, all HGNC groups, same sequence source
  - [`../../workflow-COPYME-hgnc_user_gene_symbols/`](../../workflow-COPYME-hgnc_user_gene_symbols/) — MODE 2, user-supplied gene symbols, UniProt REST
- Reads from: HGNC public database (network download) + user-supplied
  `../../INPUT_user/user_gene_group_names.tsv` + the same local human T1
  proteome MODE 1 uses
- Outputs to: per-gene-group RGS FASTAs in `OUTPUT_pipeline/` + a side-car
  `3_ai-gene_symbol_to_hgnc_group_map.tsv` annotation map; downstream
  `../../../STEP_1-homolog_discovery/`
- Conda env: `aiG-trees_gene_groups-hgnc_based_rgs` (shared with MODE 1 + MODE 2)

---

**For AI Assistants**: Read `../../../../../AI_GUIDE.md`,
`../../../../AI_GUIDE.md`,
`../../../AI_GUIDE.md`, and
`../../AI_GUIDE.md` first. This file is the workflow-level execution
guide for `workflow-COPYME-hgnc_user_gene_group_names`.

**Location**: `gene_groups_hgnc-COPYME/STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_group_names/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## What This Workflow Does

Takes a **user-supplied list of HGNC gene-group names or `gg<N>` IDs**
and emits one per-group RGS FASTA each, using sequences from the local
GIGANTIC human T1 proteome. Reuses MODE 1's download + aggregation
machinery; the only mode-specific script is `002`, which filters the
aggregated gene sets to the user's named groups before script 003
materializes the RGS files.

Additionally emits a side-car
`3_ai-gene_symbol_to_hgnc_group_map.tsv` annotation map — long-format
gene_symbol -> hgnc_group_id -> hgnc_group_name — for downstream tree-tip
subgroup coloring (e.g., color collagen tree tips by
`Fibrillar collagens` vs `Network-forming collagens` rather than only the
`Collagens` parent).

### Inputs

| Path | Source |
|---|---|
| `START_HERE-user_config.yaml inputs.user_gene_group_names_file` (default `../../INPUT_user/user_gene_group_names.tsv`) | User-supplied TSV at the instance level |
| `START_HERE-user_config.yaml inputs.human_proteome_path` | A `.aa` file from a sibling genomesDB subproject (same path MODE 1 uses) |
| HGNC reference data | Downloaded automatically by scripts 000 + 001 |

#### User gene-group names TSV format

Tab-delimited; `#`-comments allowed; first non-comment line is the header.

| Column | Required | Description |
|---|---|---|
| `group_input_identifier` | yes | What you type. Either an HGNC group NAME (e.g. `Collagens`) or a `gg`-prefixed HGNC family ID (e.g. `gg483`). |
| `identifier_type` | yes | One of `name`, `id`, or `auto`. `auto` lets the script decide: `gg<N>` -> `id`; otherwise -> `name`. |
| `group_display_name` | optional | Human-readable label used in logs and the annotation map. If empty, the resolved HGNC name is used. |
| `notes` | optional | Free text; preserved in the resolution trail for your lab notebook. |

See `../../INPUT_user/user_gene_group_names_EXAMPLE.tsv` for a worked example.

### Outputs

```
OUTPUT_pipeline/
├── 0-output/hgnc_complete_set.txt                  (from script 000)
├── 1-output/                                       (from script 001)
│   ├── family.csv, hierarchy*.csv, gene_has_family.csv,
│   ├── hgnc_gene_groups_all.tsv
│   └── 1_ai-download_manifest.tsv
├── 2-output/                                       (from script 002)
│   ├── 2_ai-aggregated_gene_sets.tsv               (filtered to user groups; SAME columns as MODE 1 so script 003 is reused)
│   ├── 2_ai-gene_group_metadata.tsv                (filtered)
│   ├── 2_ai-resolved_user_groups.tsv               (per-entry resolution trail)
│   ├── 2_ai-unresolved_groups.tsv                  (only if any group failed -> sys.exit(1))
│   ├── 2_ai-hgnc_group_catalog.tsv                 (all HGNC groups; grep-able)
│   ├── 2_ai-filter_policy.tsv                      (locus-type allowlist used)
│   └── 2_ai-log-filter_aggregated_gene_sets_by_user_names.log
└── 3-output/                                       (from script 003)
    ├── rgs_fastas/rgs_hugo_hgnc-human-<sanitized_group_name>.aa   (× user-named groups)
    ├── 3_ai-rgs_generation_summary.tsv             (STEP_1 reads this)
    ├── 3_ai-rgs_generation_manifest.tsv            (per-group detail incl. missing symbols)
    ├── 3_ai-gene_symbol_to_hgnc_group_map.tsv      (SIDE-CAR annotation map)
    └── 3_ai-log-generate_rgs_fasta_files.log
```

### Hand-off to downstream

`RUN-workflow.sh` post-pipeline creates symlinks at:

- `trees_gene_groups/output_to_input/hugo_hgnc_database/hgnc_complete_set.txt` (subproject-level shared reference)
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/rgs_fastas/*.aa` (per-instance)
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/3_ai-rgs_generation_summary.tsv` (per-instance; STEP_1 reads this)
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/3_ai-rgs_generation_manifest.tsv`
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/3_ai-gene_symbol_to_hgnc_group_map.tsv` (side-car annotation map)
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/2_ai-resolved_user_groups.tsv`
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/2_ai-hgnc_group_catalog.tsv`
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/2_ai-filter_policy.tsv`

---

## NextFlow Process Chain (ai/main.nf)

| Process | Script | Inputs | Outputs |
|---|---|---|---|
| `download_hgnc_complete_set` | `000_*.py` | (canonical-source check) | `0-output/hgnc_complete_set.txt` |
| `download_hgnc_data` | `001_*.py` | (genenames.org URLs hardcoded in script) | `1-output/family.csv` etc. |
| `filter_aggregated_gene_sets_by_user_names` | `002_*.py` | `1-output/`, `params.user_gene_group_names_file`, filter flags | `2-output/2_ai-aggregated_gene_sets.tsv` (filtered) + resolution trail + catalog + filter-policy record |
| `generate_rgs_fasta_files` | `003_*.py` | `2-output/...tsv`, `params.human_proteome_path` | `3-output/rgs_fastas/*.aa`, `3-output/3_ai-rgs_generation_summary.tsv`, `3-output/3_ai-gene_symbol_to_hgnc_group_map.tsv` |
| `write_run_log` | `004_*.py` | `generate_rgs_fasta_files.out.rgs_output_dir` (gate) | `ai/logs/run_<timestamp>-trees_gene_groups_success.log` (GIGANTIC §45 final step) |

Process 0 (`download_hgnc_complete_set`) is parallel; processes 1 → 2 →
3 form a chain with explicit data dependencies. Process 3's
`generate_rgs_fasta_files` is the SAME process name and the SAME I/O
contract as MODE 1's process 3; the side-car annotation map is emitted
inline (additive change, not a separate process).

---

## Group resolution strategy (Script 002)

For each row in the user TSV:

- `identifier_type = id` (or `auto` + `/^gg\d+$/`): strip `gg` prefix,
  int(), look up in `family.csv` by id.
- `identifier_type = name` (or `auto` + non-id): **case-insensitive,
  whitespace-collapsed** match against `family.csv`'s `name` column.
  Hyphens, accents, and punctuation are matched literally.
- On miss: up to 5 "did you mean..." candidates (substring +
  `difflib.get_close_matches`) are written to
  `OUTPUT_pipeline/2-output/2_ai-unresolved_groups.tsv` and the workflow
  fails fast.
- For browsing the HGNC group universe: every run also writes
  `OUTPUT_pipeline/2-output/2_ai-hgnc_group_catalog.tsv` (all HGNC groups,
  IDs, sanitized names, and aggregated gene counts).

---

## Locus-type filter policy

By default, the same locus-type allowlist that
`workflow-COPYME-hgnc_database` uses is applied:

- `gene with protein product`
- `complex locus constituent`

Pseudogenes, RNA genes, V/D/J segments, Ig pseudogenes, T cell receptors,
endogenous retroviruses, and readthrough loci are all dropped.

Two YAML flags can expand the allowlist:

```yaml
filters:
  include_pseudogenes: false       # set true to ADD 'pseudogene'
  include_non_protein_coding: false # set true to ADD RNA/Ig/TR/readthrough/ERV
```

When either flag is true the change is logged loudly at INFO and recorded
in `OUTPUT_pipeline/2-output/2_ai-filter_policy.tsv` for the lab notebook.

---

## Configuring (START_HERE-user_config.yaml)

Things you typically edit:

```yaml
inputs:
  user_gene_group_names_file: "../../INPUT_user/user_gene_group_names.tsv"
  human_proteome_path: "../../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes/Metazoa_Chordata_..._Homo_sapiens-T1-proteome.aa"

filters:
  include_pseudogenes: false
  include_non_protein_coding: false

execution_mode: "local"   # "local" or "slurm"

cpus: 4
memory_gb: 16
time_hours: 1

slurm_account: "your_account"
slurm_qos: "your_qos"
```

Both `inputs.user_gene_group_names_file` and `inputs.human_proteome_path`
are resolved relative to this workflow directory by `RUN-workflow.sh`'s
`PYTHON_FLATTEN` step before being passed to NextFlow.

---

## Typical Use: Instantiate + Run

```bash
cd gigantic_project-COPYME/subprojects/trees_gene_groups/

# 1. Instantiate the template
cp -r gene_groups_hgnc-COPYME gene_groups-my_groups/

# 2. Provide the user TSV
cd gene_groups-my_groups/INPUT_user/
cp user_gene_group_names_EXAMPLE.tsv user_gene_group_names.tsv
# Edit user_gene_group_names.tsv with your HGNC group names / gg<N> IDs.

# 3. Run STEP_0
cd ../STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_group_names/
# Confirm human_proteome_path is correct
bash RUN-workflow.sh
```

Runtime is dominated by script 003 extracting sequences from the human
proteome — typically seconds-to-minutes for a handful of groups, since
it's a single pass through the proteome with in-memory dictionaries.

---

## Failure Semantics (Fail-Fast)

Every Python script in this workflow exits with code 1 if a critical
expectation isn't met. NextFlow's `errorStrategy = 'terminate'` and
`maxErrors = 0` enforce strict fail-fast: any per-process error stops
the pipeline immediately.

| Script | Trigger | Resolution |
|---|---|---|
| 000 | `hgnc_complete_set.txt` download fails AND no canonical copy exists | Network check; ensure compute node can reach genenames.org / storage.googleapis.com |
| 001 | Any of the 5 HGNC TSVs fails to download | Same as above |
| 002 | Any user-supplied group fails to resolve (name typo, wrong ID, deprecated name) | Inspect `2_ai-unresolved_groups.tsv`; grep `2_ai-hgnc_group_catalog.tsv` for the right spelling; edit the input TSV |
| 003 | `human_proteome_path` doesn't exist | Set the correct path in `START_HERE-user_config.yaml` |
| 003 | All RGS FASTAs would be empty (no symbol → proteome matches) | Header convention in proteome may have changed; verify proteome file format |

---

## Differences From sibling workflows

| | `hgnc_database` (MODE 1) | `hgnc_user_gene_symbols` (MODE 2) | `hgnc_user_gene_group_names` (this, MODE 3) |
|---|---|---|---|
| Group definition source | HGNC's gene-group taxonomy | User-supplied TSV of (group, symbol) rows | User-supplied TSV of HGNC group NAMES or `gg<N>` IDs |
| Sequence source | Local human proteome | UniProt REST API | Local human proteome (same as MODE 1) |
| Scripts | 000 + 001 + 002 + 003 | 000 + 001 + 002 | 000 + 001 + 002 + 003 (002 is `filter_aggregated_gene_sets_by_user_names`) |
| Output dirs | 0, 1, 2, 3 | 0, 1, 2 | 0, 1, 2, 3 (same N as MODE 1) |
| Number of groups processed | ~2060 (all HGNC groups) | 1+ (whatever the user defines) | 1+ (whatever the user names) |
| RGS filename prefix | `rgs_hugo_hgnc-` | `rgs_hgnc_user-` | `rgs_hugo_hgnc-` (same as MODE 1) |
| RGS FASTA header format | 5-field hgnc/ncbi-sourced | 4-field uniprot-sourced | 5-field hgnc/ncbi-sourced (same as MODE 1) |
| Side-car annotation map | no | no | yes — `3_ai-gene_symbol_to_hgnc_group_map.tsv` for tree-tip subgroup coloring |
| Network calls | 1 (hgnc_complete_set) + 5 (gene-group tables) | 1 (hgnc_complete_set) + N (1 per gene; UniProt FASTA) | 1 (hgnc_complete_set) + 5 (gene-group tables) — same as MODE 1 |

---

## See Also

- `../README.md` — workflow-level README (user-facing companion to this guide)
- `../AI_GUIDE.md` — STEP_0 concepts
- `../../AI_GUIDE.md` — template-level guide
- `../workflow-COPYME-hgnc_database/ai/AI_GUIDE.md` — sibling MODE 1
- `../workflow-COPYME-hgnc_user_gene_symbols/ai/AI_GUIDE.md` — sibling MODE 2
- `../../INPUT_user/README.md` — instance-level user inputs
- `../../../output_to_input/hugo_hgnc_database/README.md` — canonical reference data
