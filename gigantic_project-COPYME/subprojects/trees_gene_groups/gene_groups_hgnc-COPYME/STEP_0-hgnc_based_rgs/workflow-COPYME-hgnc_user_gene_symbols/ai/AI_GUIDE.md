# AI Guide: workflow-COPYME-hgnc_user_gene_symbols (STEP_0 / HGNC-Based RGS)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
AI:      Claude Code | Opus 4.7 | 2026 May 29 (parity-finishing pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (template AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sister workflows:
  - [`../../workflow-COPYME-hgnc_database/`](../../workflow-COPYME-hgnc_database/) — MODE 1 (all ~2060 HGNC groups; full sweep)
  - [`../../workflow-COPYME-hgnc_user_gene_group_names/`](../../workflow-COPYME-hgnc_user_gene_group_names/) — MODE 3 (curated subset by HGNC group NAMES/IDs)
- Reads from: `../../../INPUT_user/user_gene_set_*.tsv` (user-curated subset) + HGNC public database
- Outputs to: per-gene-group RGS FASTAs in `OUTPUT_pipeline/` for downstream `../../../STEP_1-homolog_discovery/`
- Conda env: `aiG-trees_gene_groups-hgnc_based_rgs`

---

**For AI Assistants**: Read `../../../../../AI_GUIDE.md`,
`../../../../AI_GUIDE.md`,
`../../../AI_GUIDE.md`, and
`../../AI_GUIDE.md` first. This file is the workflow-level
execution guide for `workflow-COPYME-hgnc_user_gene_symbols`.

**Location**: `gene_groups_hgnc-COPYME/STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_symbols/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## What This Workflow Does

Takes a **user-supplied gene set** (one or more named groups, each with
a list of HGNC-approved human gene symbols) and emits one RGS FASTA per
group. Each sequence is the canonical Swiss-Prot record from UniProt,
keyed to the gene symbol via HGNC's `uniprot_ids` cross-reference.

The killer case this enables: gene families that **HGNC doesn't curate
as one gene group**. Example: the **SNAP family** (SNAP23, SNAP25, SNAP29,
SNAP47). HGNC has a "SNAREs" gene group (1124) containing SNAP23/25/29
plus syntaxins and VAMPs, but SNARE is a protein-complex category, not
a gene family, and SNAP47 isn't in any HGNC group. The user-gene-symbols mode (MODE 2)
handles this cleanly — declare your gene set by listing the symbols, and
HGNC's complete_set table is used only as a symbol → UniProt mapping.

### Inputs

| Path | Source |
|---|---|
| `START_HERE-user_config.yaml inputs.user_gene_set_file` (default `../../INPUT_user/user_gene_set.tsv`) | User-supplied TSV at the instance level |
| HGNC `hgnc_complete_set.txt` | Downloaded automatically by script 000 (or reused from canonical) |

#### User gene set TSV format

```
# Comments allowed; header required.
group_sanitized_name	group_display_name	gene_symbol
snap_family	Synaptosomal-Associated Proteins	SNAP23
snap_family	Synaptosomal-Associated Proteins	SNAP25
snap_family	Synaptosomal-Associated Proteins	SNAP29
snap_family	Synaptosomal-Associated Proteins	SNAP47
```

Each row = one gene's membership in one group. To define a multi-gene
group, repeat the group columns across rows. Multiple groups in one
file are allowed (each gets its own RGS FASTA).

### Outputs

```
OUTPUT_pipeline/
├── 0-output/hgnc_complete_set.txt                  (from script 000)
├── 1-output/                                       (from script 001)
│   ├── 1_ai-resolved_symbols.tsv                   (per-gene resolution audit trail)
│   └── 1_ai-log-resolve_user_symbols_to_uniprot.log
└── 2-output/                                       (from script 002)
    ├── rgs_fastas/rgs_hgnc_user-human-<sanitized>.aa   (× number_of_groups)
    ├── 2_ai-rgs_generation_manifest.tsv            (per-gene fetch record)
    └── 2_ai-rgs_generation_summary.tsv             (per-group; STEP_1 reads this)
```

### Hand-off to downstream

`RUN-workflow.sh` post-pipeline creates symlinks at:

- `trees_gene_groups/output_to_input/hugo_hgnc_database/hgnc_complete_set.txt` (subproject-level shared reference; same as `workflow-COPYME-hgnc_database`)
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/rgs_fastas/*.aa`
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/2_ai-rgs_generation_summary.tsv` (STEP_1 reads this)
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/2_ai-rgs_generation_manifest.tsv`
- `trees_gene_groups/output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/1_ai-resolved_symbols.tsv`

---

## NextFlow Process Chain (ai/main.nf)

| Process | Script | Inputs | Outputs |
|---|---|---|---|
| `download_hgnc_complete_set` | `000_*.py` | (canonical-source check) | `0-output/hgnc_complete_set.txt` |
| `resolve_user_symbols_to_uniprot` | `001_*.py` | `0-output/hgnc_complete_set.txt`, user_gene_set_file | `1-output/1_ai-resolved_symbols.tsv` |
| `fetch_uniprot_fastas_and_emit_rgs` | `002_*.py` | `1-output/1_ai-resolved_symbols.tsv` | `2-output/rgs_fastas/*.aa`, `2-output/2_ai-rgs_generation_summary.tsv`, `2-output/2_ai-rgs_generation_manifest.tsv` |
| `write_run_log` | `003_*.py` | `fetch_uniprot_fastas_and_emit_rgs.out.rgs_dir` (gate) | `ai/logs/run_<timestamp>-trees_gene_groups_success.log` (GIGANTIC §45 final step) |

Processes 0 → 1 → 2 → 3 form a strict chain.

---

## Symbol Resolution Strategy (Script 001)

For each user-supplied gene symbol, script 001 tries these in order:

1. **DIRECT_MATCH** — symbol matches HGNC's `symbol` column.
2. **ALIAS_MATCH** — symbol matches one of HGNC's `alias_symbol`
   pipe-delimited entries; resolved to the canonical symbol.
3. **PREV_SYMBOL_MATCH** — symbol matches one of HGNC's `prev_symbol`
   entries (withdrawn / renamed symbols); resolved to the canonical symbol.

If a symbol can't be resolved, **the workflow fails fast** — STEP_1
expects a complete RGS, never a partial one. The user must fix
`user_gene_set.tsv` (typo, deprecated name, etc.).

If a symbol resolves but has no `uniprot_ids` entry (non-protein-coding,
pseudogene, etc.), the workflow also fails fast with a clear error
message including the canonical symbol and what to do (substitute a
protein-coding family member, or remove from the user set).

### Canonical UniProt accession picking

HGNC's `uniprot_ids` column is pipe-delimited when a gene has multiple
UniProt entries. Script 001 picks the **first** — in nearly every case
this is the Swiss-Prot canonical record. The full list is preserved in
the audit-trail TSV (`uniprot_accessions_all` column) for transparency.

---

## UniProt FASTA Fetch (Script 002)

For each (group, symbol, accession) row in the resolved manifest:

1. Fetch: `GET https://rest.uniprot.org/uniprotkb/<accession>.fasta`
   (no auth, polite User-Agent + 0.1s inter-request delay).
2. Retries: 3 attempts with exponential backoff (1 s, 2 s, 4 s) on
   transient failure. **Does not retry 404** (wrong accession).
3. Parse: strip the UniProt header, concatenate sequence lines.
4. Build the GIGANTIC 4-field uniprot-sourced header:
   `>rgs_<group>-<species>-<symbol>-uniprot<accession>`
   - Source token (`uniprot`) + accession (`P60880`) are **concatenated** with
     no separator: `uniprotP60880` (not `uniprot-P60880`, which would imply a
     5-field header). This keeps the dash count unambiguous for STEP_1's parser.
   - Example: `>rgs_snap_family-human-SNAP25-uniprotP60880`
5. Append to the per-group RGS file.

STEP_1's script 008 dispatches on the 4-field shape + the `uniprot` prefix in
field 4: it runs **Improvement 0** (strict gene-symbol search against the
local proteome's `>g_<SYMBOL>-` headers, exactly one match required) and
fails fast on any unresolved RGS. There is no BLAST fallback for these
headers — Improvement 0 is the entire path.

If any fetch fails after retries, the workflow fails fast — STEP_1 needs
a complete RGS, and the per-group RGS file is only written once all
fetches for that group succeed.

---

## Configuring (START_HERE-user_config.yaml)

Things you typically edit:

```yaml
inputs:
  user_gene_set_file: "../../INPUT_user/user_gene_set.tsv"   # default; rarely changed

execution_mode: "local"   # "local" (recommended for this lightweight workflow) or "slurm"

cpus: 2
memory_gb: 4
time_hours: 1
```

This workflow is **lightweight** (small HTTP fetches + TSV parsing).
`execution_mode: "local"` is the default and recommended. SLURM is
supported for consistency but adds queue latency to a workflow that
completes in seconds.

---

## Typical Use: SNAP Family End-to-End

```bash
cd gigantic_project-COPYME/subprojects/trees_gene_groups/

# 1. Instantiate the template
cp -r gene_groups_hgnc-COPYME gene_groups-snap_family/

# 2. Configure the user gene set
cd gene_groups-snap_family/INPUT_user/
mv user_gene_set_EXAMPLE.tsv user_gene_set.tsv
# (edit if needed — the EXAMPLE happens to be SNAP family)

# 3. Run
cd ../STEP_0-hgnc_based_rgs/workflow-COPYME-hgnc_user_gene_symbols/
bash RUN-workflow.sh
```

End-to-end runtime on a clean compute node: ~3 seconds (4 UniProt
fetches, no SLURM queuing).

After this completes, STEP_1's `START_HERE-user_config.yaml` needs to
point at this workflow's summary TSV:

```yaml
gene_group_source_tsv: "../../../output_to_input/gene_groups-snap_family/STEP_0-hgnc_based_rgs/2_ai-rgs_generation_summary.tsv"
rgs_fastas_dir:        "../../../output_to_input/gene_groups-snap_family/STEP_0-hgnc_based_rgs/rgs_fastas"
project:
  database: "species70_T1-species70"   # match the blastdb-keeper combo
```

Then `cd ../../STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/ && bash RUN-workflow.sh`.

---

## Failure Semantics (Fail-Fast)

| Script | Trigger | Resolution |
|---|---|---|
| 000 | `hgnc_complete_set.txt` download fails AND no canonical copy exists | Network check; run from login node first to populate canonical |
| 001 | Any user symbol cannot be resolved (`NOT_FOUND` or `NO_UNIPROT`) | Inspect log; fix `user_gene_set.tsv` (typo, deprecated symbol, non-protein-coding gene) |
| 001 | `user_gene_set.tsv` header isn't `group_sanitized_name<TAB>group_display_name<TAB>gene_symbol` | Fix the header row of the TSV |
| 002 | Any UniProt FASTA fetch fails after 3 retries | Re-run later; if persistent, verify accession on UniProt directly |

---

## Differences From `workflow-COPYME-hgnc_database`

See the comparison table in
`../workflow-COPYME-hgnc_database/ai/AI_GUIDE.md`.

The key axis: this workflow defines its gene groups from a **user TSV**
and fetches sequences from **UniProt REST**, whereas the database
workflow uses HGNC's curated gene-group taxonomy and extracts sequences
from a **local human proteome**.

---

## See Also

- `../AI_GUIDE.md` — STEP_0 concepts
- `../../AI_GUIDE.md` — template-level guide
- `../workflow-COPYME-hgnc_database/ai/AI_GUIDE.md` — sibling workflow (MODE 1)
- `../workflow-COPYME-hgnc_user_gene_group_names/ai/AI_GUIDE.md` — sibling workflow (MODE 3)
- `../../INPUT_user/README.md` — user_gene_set.tsv format and location
- `../../../output_to_input/hugo_hgnc_database/README.md` — canonical reference data
