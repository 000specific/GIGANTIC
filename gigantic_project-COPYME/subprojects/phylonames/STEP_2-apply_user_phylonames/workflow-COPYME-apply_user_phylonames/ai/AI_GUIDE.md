<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26
Human:   Eric Edsinger
Purpose: AI-facing operational guide for the phylonames STEP_2 workflow
         (apply_user_phylonames). Pairs with the user-facing README.md at
         the workflow root.
Scope:   gigantic_project-COPYME/subprojects/phylonames/STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/
History:
  2026-05-26  Initial version (the workflow previously had no AI_GUIDE).
============================================================================ -->

# `workflow-COPYME-apply_user_phylonames/ai/` — AI Guide

You are working in the phylonames STEP_2 workflow (apply_user_phylonames).
This applies user-provided custom phylonames on top of the STEP_1
NCBI-generated mapping.

| You need... | Go to... |
|---|---|
| GIGANTIC overview, conventions | `../../../../../AI_GUIDE.md` (project root) + `../../../../../ai/ai_FYIs/gigantic_conventions.md` |
| Research-grade behavior / posture | `../../../../../AI_BEHAVIOR.md` |
| Phylonames concepts (numbered clades, UNOFFICIAL, the 2-STEP architecture) | `../../../AI_GUIDE.md` (subproject) |
| STEP_2 overview | `../../AI_GUIDE.md` (STEP) |
| Running this STEP_2 workflow | This file |
| User-facing quick start | `../README.md` |

---

## What this workflow does

Applies a user-provided `user_phylonames.tsv` to STEP_1's output mapping,
optionally marking divergent clades with `UNOFFICIAL`. Produces the
project's authoritative final mapping plus an updated taxonomy summary.

## Workflow Directory Structure

```
workflow-COPYME-apply_user_phylonames/
│
├── README.md                    # User-facing quick start
├── RUN-workflow.sh              # Unified driver (§29; local or SLURM via execution_mode)
├── START_HERE-user_config.yaml  # project.name (must match STEP_1), user_phylonames,
│                                # mark_unofficial, execution_mode, slurm_account/qos
├── upload_manifest.tsv          # Server publish manifest (§38, §39)
│
├── INPUT_user/                  # User-provided phylonames input (staged from project INPUT_user/phylonames/)
│   ├── user_phylonames_example.tsv
│   └── user_phylonames.tsv      # Real file (or symlink); read by script 001
│
├── OUTPUT_pipeline/             # All outputs
│   ├── 1-output/                # Final mapping + unofficial_clades_report.tsv
│   └── 2-output/                # Updated taxonomy summary (Markdown + HTML)
│
└── ai/                          # Internal — users don't touch by hand
    ├── AI_GUIDE.md              # THIS FILE
    ├── main.nf                  # NextFlow workflow definition
    ├── nextflow.config          # NextFlow config
    ├── conda_environment.yml    # env name: aiG-phylonames (shared with STEP_1; auto-created)
    ├── logs/                    # Per-run audit logs (lab notebook)
    ├── validation/              # Validation outputs
    └── scripts/
        ├── 001_ai-python-apply_user_phylonames.py
        ├── 002_ai-python-generate_taxonomy_summary.py
        └── 003_ai-python-write_run_log.py
```

## Pipeline (3 scripts)

| # | Script | Output dir | Purpose |
|---|---|---|---|
| 001 | `001_ai-python-apply_user_phylonames.py` | `OUTPUT_pipeline/1-output/` | Apply user phylonames overrides; mark UNOFFICIAL where divergent |
| 002 | `002_ai-python-generate_taxonomy_summary.py` | `OUTPUT_pipeline/2-output/` | Generate updated taxonomy summary (Markdown + HTML) |
| 003 | `003_ai-python-write_run_log.py` | `ai/logs/` | Per-run audit log |

## Configuration

The user edits `START_HERE-user_config.yaml`:

| Key | Purpose |
|---|---|
| `project_name` | Must match STEP_1 project name (so the mapping is recognized) |
| `user_phylonames` | Path to the user's custom phylonames TSV (default: `INPUT_user/user_phylonames.tsv`) |
| `mark_unofficial` | true (default) marks clades that differ from NCBI; false leaves them unmarked |
| `execution_mode` | `local` (default) or `slurm` |
| `slurm.*` | Required when `execution_mode: "slurm"` |

## Running

```bash
bash RUN-workflow.sh
```

The unified driver (per §29) reads `execution_mode` from the YAML and
either runs in foreground or generates+submits an sbatch wrapper. There
is no `RUN-workflow.sbatch`.

## Inter-STEP data flow

STEP_2 reads from `../../output_to_input/STEP_1-generate_and_evaluate/maps/`
(per GIGANTIC §2: between STEPs, read from the subproject's
`output_to_input/`, not from another STEP's `OUTPUT_pipeline/`).

After STEP_2 runs:
- Its mapping ships to `../../output_to_input/STEP_2-apply_user_phylonames/maps/`
- The `../../output_to_input/maps/` convenience symlink is updated to
  point at the STEP_2 mapping (so downstream subprojects automatically
  pick up the user-overridden version)

## Publishing to the data server

`upload_manifest.tsv` at the workflow root (sibling to this `ai/` dir)
declares which outputs publish. The actual publish is invoked at the
subproject level:

```bash
bash ../../../RUN-update_upload_to_server.sh
```

This invokes the shared helper at
`gigantic_project-COPYME/server/ai/update_upload_to_server.py` and
assembles the subproject-level `phylonames/upload_to_server/` tree
(per §38). There is no per-STEP `upload_to_server/`.

## Common errors

| Symptom | Cause | Fix |
|---|---|---|
| `STEP_1 mapping not found` | STEP_1 not run yet | Run STEP_1 first; verify `../../output_to_input/STEP_1-generate_and_evaluate/maps/` is populated |
| `user_phylonames file not found` | Neither workflow-local nor project-level user_phylonames.tsv exists | Stage `INPUT_user/phylonames/user_phylonames.tsv` at project root (canonical INPUT_user arena per §17, §18) OR create workflow-local `INPUT_user/user_phylonames.tsv`. Workflow-local takes priority over project-level. |
| Species in user_phylonames not found in mapping | Typo in genus_species, or species not in STEP_1 species list | Cross-check spellings; ensure the species made it through STEP_1 |
| All clades marked UNOFFICIAL | Disagree with NCBI on every taxonomic rank (rare) | Expected behavior; or set `mark_unofficial: false` if you don't want the marking |

## Questions to ask the user

| Situation | Ask |
|---|---|
| First-time setup | "Which species in STEP_1 output need overrides? Let's create user_phylonames.tsv together." |
| Massive overrides | "Are you sure these species really differ from NCBI? UNOFFICIAL marking will be very visible." |
| Disabling UNOFFICIAL | "Why do you want to suppress the UNOFFICIAL marking? It exists for transparency." |
| Project name mismatch with STEP_1 | "STEP_2's project_name must match STEP_1's — confirming you want the same name." |
