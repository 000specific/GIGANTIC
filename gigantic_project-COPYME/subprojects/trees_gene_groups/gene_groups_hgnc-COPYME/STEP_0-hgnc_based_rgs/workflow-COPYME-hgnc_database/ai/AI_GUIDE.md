# AI Guide: workflow-COPYME-hgnc_database (STEP_0 / HGNC-Based RGS)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (template AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sister workflow: [`../../workflow-COPYME-hgnc_user_list/`](../../workflow-COPYME-hgnc_user_list/) — curated subset variant
- Reads from: HGNC public database (network download)
- Outputs to: per-gene-group RGS FASTAs in `OUTPUT_pipeline/` for downstream `../../../STEP_1-homolog_discovery/`
- Conda env: `aiG-trees_gene_groups-hgnc_based_rgs` (urllib stdlib only — no `requests`)

---

**For AI Assistants**: Read `../../../../../AI_GUIDE.md`,
`../../../../AI_GUIDE.md`,
`../../../AI_GUIDE.md`, and
`../../AI_GUIDE.md` first. This file is the workflow-level
execution guide for `workflow-COPYME-hgnc_database`.

**Location**: `gene_groups_hgnc-COPYME/STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_database/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## What This Workflow Does

Batch-processes **all** HGNC-curated gene groups (~2060) and emits one
per-group RGS FASTA each. Sequences come from a **local GIGANTIC human
T1 proteome** — NOT from UniProt REST. The workflow is appropriate when
you want comprehensive coverage of HGNC's classification (e.g.,
"generate RGS for every HGNC gene group, then run STEP_1 across all of
them").

### Inputs

| Path | Source |
|---|---|
| `START_HERE-user_config.yaml inputs.human_proteome_path` | A `.aa` file from a sibling genomesDB subproject (e.g., `species70_gigantic_T1_proteomes/Metazoa_Chordata_..._Homo_sapiens-T1-proteome.aa`) |
| HGNC reference data | Downloaded automatically by scripts 000 + 001 |

### Outputs

```
OUTPUT_pipeline/
├── 0-output/hgnc_complete_set.txt                  (from script 000)
├── 1-output/                                       (from script 001)
│   ├── family.csv, hierarchy.csv, hierarchy_closure.csv,
│   ├── gene_has_family.csv, hgnc_gene_groups_all.tsv
│   └── 1_ai-download_manifest.tsv
├── 2-output/                                       (from script 002)
│   ├── 2_ai-aggregated_gene_sets.tsv
│   └── 2_ai-aggregation_log.tsv
└── 3-output/                                       (from script 003)
    ├── rgs_fastas/rgs_hugo_hgnc-human-<sanitized_group_name>.aa   (× ~2060)
    ├── 3_ai-rgs_generation_summary.tsv             (STEP_1 reads this)
    └── 3_ai-rgs_generation_manifest.tsv
```

### Hand-off to downstream

`RUN-workflow.sh` post-pipeline creates symlinks at:

- `trees_gene_groups/output_to_input/hugo_hgnc_database/hgnc_complete_set.txt` (subproject-level shared reference)
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/rgs_fastas/*.aa` (per-instance)
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/3_ai-rgs_generation_summary.tsv` (per-instance; STEP_1 reads this)

---

## Single-Script Orchestrator Pattern

The workflow has **one user-runnable script**: `RUN-workflow.sh`.

What it does:

1. **Derive `INSTANCE_NAME` + `STEP_NAME`** dynamically from the
   directory hierarchy (no hardcoded names).
2. **COPYME-guard**: refuses to run if invoked from a `*COPYME*`
   directory.
3. **Activate conda env** `aiG-trees_gene_groups-hgnc_based_rgs`
   (auto-created from `ai/conda_environment.yml` on first run).
4. **Read execution mode** from `START_HERE-user_config.yaml`. If
   `slurm`, sbatch self-submit and exit.
5. **Flatten YAML** to `.params.json` and run NextFlow with
   `-params-file`.
6. **Create symlinks** at the canonical subproject `output_to_input/`
   locations (both subproject-level for hgnc_complete_set.txt and
   per-instance for the RGS FASTAs / summaries).

---

## NextFlow Process Chain (ai/main.nf)

| Process | Script | Inputs | Outputs |
|---|---|---|---|
| `download_hgnc_complete_set` | `000_*.py` | (canonical-source check) | `0-output/hgnc_complete_set.txt` |
| `download_hgnc_data` | `001_*.py` | (genenames.org URLs hardcoded in script) | `1-output/family.csv` etc. |
| `build_aggregated_gene_sets` | `002_*.py` | `1-output/` | `2-output/2_ai-aggregated_gene_sets.tsv` |
| `generate_rgs_fasta_files` | `003_*.py` | `2-output/...tsv`, `params.human_proteome_path` | `3-output/rgs_fastas/*.aa`, `3-output/3_ai-rgs_generation_summary.tsv` |

Process 0 (`download_hgnc_complete_set`) is **parallel** to the others
(no data dependency from it to processes 1-3 in this workflow — it
exists here so the canonical reference data is populated for the
sibling `workflow-COPYME-hgnc_user_list`).

Processes 1 → 2 → 3 form a chain with explicit data dependencies.

---

## Configuring (START_HERE-user_config.yaml)

Things you typically edit:

```yaml
inputs:
  # REQUIRED: absolute path to GIGANTIC human T1 proteome
  human_proteome_path: "../../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes/Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens-T1-proteome.aa"

execution_mode: "local"   # "local" or "slurm"

cpus: 4
memory_gb: 16
time_hours: 1

slurm_account: "your_account"
slurm_qos: "your_qos"
```

The `inputs.human_proteome_path` is resolved relative to this workflow
directory by `RUN-workflow.sh`'s `PYTHON_FLATTEN` step before being
passed to NextFlow. Adjust the relative path if your `genomesDB`
subproject layout differs.

---

## Typical Use: Instantiate + Run

```bash
cd gigantic_project-COPYME/subprojects/trees_gene_groups/

# 1. Instantiate the template
cp -r gene_groups_hgnc-COPYME gene_groups-hgnc_all/

# 2. Configure
cd gene_groups-hgnc_all/STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_database/
# Edit START_HERE-user_config.yaml: confirm human_proteome_path

# 3. Run
bash RUN-workflow.sh
```

Runtime is dominated by script 003 extracting sequences from the human
proteome — typically minutes (not hours) for the full ~2060 HGNC gene
groups, since it's a single pass through the proteome with in-memory
dictionaries.

---

## Failure Semantics (Fail-Fast)

Every Python script in this workflow exits with code 1 if a critical
expectation isn't met. NextFlow's `errorStrategy = 'terminate'` and
`maxErrors = 0` enforce strict fail-fast: any per-process error stops
the pipeline immediately.

Common fail-fast conditions:

| Script | Trigger | Resolution |
|---|---|---|
| 000 | `hgnc_complete_set.txt` download fails AND no canonical copy exists | Network check; ensure compute node can reach genenames.org / storage.googleapis.com |
| 001 | Any of the 5 HGNC TSVs fails to download | Same as above |
| 002 | `gene_has_family.csv` missing or malformed | Inspect 1-output; the upstream download succeeded but the file is wrong |
| 003 | `human_proteome_path` doesn't exist | Set the correct path in `START_HERE-user_config.yaml` |
| 003 | All ~2060 RGS FASTAs would be empty (no symbol → proteome matches) | Header convention in proteome may have changed; verify proteome file format |

---

## Differences From `workflow-COPYME-hgnc_user_list`

| | `workflow-COPYME-hgnc_database` | `workflow-COPYME-hgnc_user_list` |
|---|---|---|
| Group definition source | HGNC's gene-group taxonomy | User-supplied TSV |
| Sequence source | Local human proteome | UniProt REST API |
| Scripts | 000 + 001 + 002 + 003 | 000 + 001 + 002 |
| Output dirs | 0, 1, 2, 3 | 0, 1, 2 |
| Number of groups processed | ~2060 (all HGNC groups) | 1+ (whatever the user defines) |
| RGS filename prefix | `rgs_hugo_hgnc-` | `rgs_hgnc_user-` |
| Network calls | 1 (hgnc_complete_set) + 5 (gene-group tables) | 1 (hgnc_complete_set) + N (1 per gene; UniProt FASTA) |

---

## See Also

- `../AI_GUIDE.md` — STEP_0 concepts
- `../../AI_GUIDE.md` — template-level guide
- `../workflow-COPYME-hgnc_user_list/ai/AI_GUIDE.md` — sibling workflow
- `../../../output_to_input/hugo_hgnc_database/README.md` — canonical reference data
