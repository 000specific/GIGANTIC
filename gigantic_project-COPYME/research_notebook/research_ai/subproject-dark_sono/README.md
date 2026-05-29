<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 27
Human:   Eric Edsinger
Purpose: AI-staged research notebook for the z_dark_sono subproject — the
         "thinking and reasoning" side, distinct from the operational
         subproject scaffold under subprojects/z_dark_sono/.
============================================================================ -->

# `subproject-dark_sono/` — research_ai notebook

This directory is the **research-notebook side** for the `z_dark_sono`
subproject. It holds the design reasoning, the curated ion-channel Pfam
manifest, the auxiliary capture-target list, and any AI-staged artifacts
that the workflow consumes via `INPUT_user/` symlinks.

The **operational side** — the NextFlow workflow, scripts, configs — lives
at:
- [`../../../subprojects/z_dark_sono/`](../../../subprojects/z_dark_sono/)

The two are linked by relative symlinks from the workflow's `INPUT_user/`
back into this directory.

---

## Project concept

**dark_sono** = "the dark proteome of sonogenetic candidates."

The aim is to identify all proteins in the GIGANTIC species70 set that
are likely to be ion channels AND have no obvious human ortholog. Such
proteins are candidates for heterologous expression in HEK cells and
ultrasound responsiveness testing in the Shrek Chalasani lab at the Salk
Institute (sonogenetic rig).

Conceptual chain (six steps, the last one defines the dark_sono proteome):

1. Cluster species70 gene-model proteomes into orthogroups
   (completed upstream — `subprojects/orthogroups/BLOCK_orthohmm/`)
2. Annotate domains across all species70 proteomes
   (completed upstream — `subprojects/annotations_hmms/BLOCK_interproscan_parsed/pfam/`)
3. Identify Pfam IDs specific to ion channels (this notebook)
4. Identify all orthogroups containing ion channel Pfam annotations
5. Identify all ion-channel orthogroups that DO include human
6. Identify all ion-channel orthogroups that DO NOT include human
   → **dark_sono proteome** = species70 proteins from step 6

---

## Files in this directory

| File | Purpose | Status |
|------|---------|--------|
| `README.md` | This file | static |
| `2026may27-pfam_ion_channel_research.md` | Full Pfam audit writeup — architectures, the 24 keepers, the excluded promiscuous Pfams with reasoning, the verification methodology against local human annotations | static, dated |
| `ion_channel_pfam_manifest-2026may27.tsv` | The 24-keeper Pfam manifest read by the workflow (symlinked into `INPUT_user/`) | live, dated |
| `out_of_scope_channels-2026may27.tsv` | 9 channels with no clean Pfam (CFTR, TMC1/2, CLIC1–6) — DOCUMENTATION ONLY; the workflow does not consume this file. BLAST-based capture was considered and rejected (cross-family false positives at deep phylogenetic distance) | static, dated |
| `logs/` | (created on demand) any logs from interactive AI-staging sessions | as needed |

---

## How the workflow consumes this

The workflow's local `INPUT_user/` directory at
`subprojects/z_dark_sono/BLOCK_dark_sono/workflow-COPYME-dark_sono/INPUT_user/`
contains ONE **relative symlink** that the user creates after copying the
COPYME template to a RUN_N instance:

```
INPUT_user/pfam_manifest.tsv
  → ../../../../../research_notebook/research_ai/subproject-dark_sono/ion_channel_pfam_manifest-2026may27.tsv
```

The species70 list comes from the **project-level** `INPUT_user/species_set/species_list.txt`
and does NOT need to be staged in this notebook (it is project-wide, not
dark_sono-specific).

The COPYME template itself does NOT ship the symlink (everything under
`INPUT_user/` is gitignored). The workflow's `INPUT_user/README.md`
documents the exact `ln -srf` command the user should run.

`out_of_scope_channels-2026may27.tsv` is NOT consumed by the workflow —
it is a documentation record of which channels we deliberately do not
attempt to capture (CFTR, TMC1/2, CLIC1–6).

---

## History / provenance

- **2026-05-27** (Eric Edsinger + Claude Opus 4.7) — initial Pfam audit
  conversation. Eric asked which Pfam domains uniquely capture ion
  channels; together we built the architecture table and the 24-Pfam
  keeper list, with a strict-promiscuity-exclusion criterion validated
  against local human annotations from
  `subprojects/annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/pfam-Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens.tsv`.
  Eric drafted an email to Shrek Chalasani and Jason Nathanson the same
  day proposing this workflow.

- **Upstream completed (prior to 2026-05-27):**
  - `genomesDB/` STEP_4 — species70 finalized; T1 proteomes + blastp DBs built
  - `annotations_hmms/` — InterProScan-parsed Pfam annotations per species
  - `orthogroups/` BLOCK_orthohmm — orthogroup assignments with GIGANTIC IDs

---

## Related conversations (this is a placeholder; auto-capture populates it)

Look in `research_notebook/research_ai/sessions/` for the canonical
captured chat transcripts. The Pfam audit conversation will appear there
once captured (via the PreCompact hook or a "Save Chat!" trigger).

---

## Future additions to this notebook

As scripts 008+ get implemented (per the reserved future-script slots),
this directory may grow to include:

- `sonogenetic_priority_weights-YYYYmonthDD.tsv` — Pfam-level weights for
  the mechanosensitive priority pass (script 008)
- `dossier_template-YYYYmonthDD.md` — top-N candidate dossier template
  (script 013)
- Discussion notes from Shrek/Jason meetings, captured here as
  `discussion-YYYYmonthDD-shrek_jason-<topic>.md`

Anything that lives here is a deliberate, dated artifact. Ephemeral
exploratory work belongs in
`research_notebook/research_user/subproject-dark_sono/` instead.
