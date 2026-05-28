# z_dark_sono — Dark Sonogenetic Candidate Discovery

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 27
Human:   Eric Edsinger
============================================================================ -->

## Status

**Early development** (the `z_` prefix marks this as not-yet-canonical
under active development). The first end-to-end run is intended for
2026-05-27 evening; QC and follow-up are planned for 2026-05-28 onward.

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from:
  - `../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/` — per-species Pfam annotations
  - `../orthogroups/output_to_input/BLOCK_orthohmm/orthogroups_gigantic_ids.tsv` — orthogroup assignments
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes/` — proteome FASTAs
  - `../../INPUT_user/species_set/species_list.txt` — project species70 list
  - `../../research_notebook/research_ai/subproject-dark_sono/` — curated Pfam + capture-target manifests (symlinked into the workflow's `INPUT_user/`)
- Outputs to:
  - `output_to_input/BLOCK_dark_sono/` — dark_sono orthogroup tables and per-species dark_sono proteome FASTAs (symlinks created by `RUN-workflow.sh`)

## Purpose

Identify all proteins in the species70 set that

1. Are likely ion channels (carry a domain from the curated 24-Pfam keeper
   list — channel-architecture-specific Pfams covering Nav/Cav/Kv/TRP,
   K2P/Kir, Cys-loop, iGluR, ENaC/ASIC, P2X, Piezo, OSCA/TMEM63, MscS/MscL,
   RyR/IP3R, connexins/innexins, CLC, TMEM16, bestrophins), and
2. Have no obvious human ortholog (their orthogroup, from
   `orthogroups/BLOCK_orthohmm`, contains no *Homo sapiens* member).

These are candidates for heterologous expression in HEK cells and
ultrasound responsiveness testing in the Shrek Chalasani lab (Salk
Institute, sonogenetic rig).

Channels lacking a clean channel-specific Pfam (CFTR, TMC1/2, CLIC1–6)
are intentionally out of scope; see
`../../research_notebook/research_ai/subproject-dark_sono/out_of_scope_channels-2026may27.tsv`.

## Method summary

The Pfam audit + reasoning lives in
[`../../research_notebook/research_ai/subproject-dark_sono/`](../../research_notebook/research_ai/subproject-dark_sono/).
See `2026may27-pfam_ion_channel_research.md` there for the full
architecture table, the 24-keeper list, the excluded promiscuous Pfams,
and the verification methodology.

The operational pipeline is a single NextFlow workflow under
[`BLOCK_dark_sono/`](BLOCK_dark_sono/), with six scripts:

| # | Script | Purpose |
|---|--------|---------|
| 001 | validate_inputs | Verify Pfam manifest, per-species pfam TSVs, orthogroups, proteomes |
| 002 | scan_pfam_per_species | Per species, extract proteins with any keeper Pfam hit |
| 003 | classify_ion_channel_orthogroups | Join hits to orthogroups; classify human_present vs no_human |
| 004 | build_dark_sono_proteomes | Per species, write FASTA of proteins in no_human orthogroups |
| 005 | summarize_dark_sono | Cross-species rollup tables + overview.md |
| 006 | write_run_log | Standard timestamped run log |

## Output structure

After a successful run, the workflow's `OUTPUT_pipeline/` contains:

```
OUTPUT_pipeline/
├── 1-output/   validated manifests + excluded species
├── 2-output/   per-species Pfam-based ion channel proteins
├── 3-output/   3 orthogroup classification TSVs + classification summary
├── 4-output/   per-species dark_sono proteome FASTAs
├── 5-output/   cross-species summary table + overview.md
└── 6-output/   run log
```

And the subproject's `output_to_input/BLOCK_dark_sono/` is populated with
symlinks pointing to the canonical results in the workflow's
`OUTPUT_pipeline/`, ready for downstream consumers.

## Reserved future-script slots

Per planning discussions, additional scripts are anticipated as
discussions with Shrek Chalasani and Jason Nathanson proceed:

- **008** — mechanosensitive-architecture priority weighting (Piezo, OSCA, MscS, K2P TREK/TRAAK, TRP)
- **009** — cross-reference with SignalP / TMBed / MetaPredict outputs
- **010** — phylogenetic distribution heatmap (clade enrichment)
- **011** — cross-reference with `trees_gene_groups` memberships
- **012** — BLAST-vs-full-human-proteome double-check (relax pure-orthogroup filter)
- **013** — top-N candidate dossier per orthogroup

These are placeholders, not implemented. They will be added incrementally
as the design solidifies through discussions and first-run QC.

## Conda env

`aiG-dark_sono` — single-BLOCK subproject convention (matches
`aiG-hotspots`). Plain Python; no BLAST or other heavyweight tools.
Auto-created on first run from
`BLOCK_dark_sono/workflow-COPYME-dark_sono/ai/conda_environment.yml`.

## Running the workflow

1. Copy the COPYME template to a fresh RUN_N instance:
   ```
   cd subprojects/z_dark_sono/BLOCK_dark_sono/
   cp -r workflow-COPYME-dark_sono workflow-RUN_1-dark_sono-species70
   cd workflow-RUN_1-dark_sono-species70
   ```
2. Create the required `pfam_manifest.tsv` symlink (see `INPUT_user/README.md` in that directory).
3. Edit `START_HERE-user_config.yaml` (defaults are sensible; confirm `execution_mode`).
4. `bash RUN-workflow.sh`

---

## Session hygiene (per §61 in `ai/ai_FYIs/gigantic_conventions.md`)

GIGANTIC's chat-as-research-notebook convention (§9) works best with
disciplined session hygiene. Two recommendations.

### Always root at the named gigantic_project-COPYME

Every chat session for project work should be initiated rooted at the
user's renamed copy of `gigantic_project-COPYME/` — e.g.,
`gigantic_project-cephalopod_evolution/`.

**Not** at:
- `GIGANTIC/` (the framework root, reserved for framework-development
  sessions per §16)
- `subprojects/<X>/` (a subproject directory)
- `subprojects/<X>/<BLOCK_or_STEP>/workflow-COPYME-*/` (a workflow directory)
- Any other directory deeper than the named project root

Why: the renamed project copy is the canonical session root. All
project conventions, INPUT_user paths, research_notebook captures,
and AI guidance are scoped to that directory. Rooting deeper than
that scopes the AI's view too narrowly and loses cross-subproject
context (and the AI guides at lower levels assume the session was
rooted above them). Rooting at `GIGANTIC/` is reserved for
framework-development sessions per §16.

### One chat session per subproject + a side channel for small questions

For productive project work:

- **One session per subproject** you're actively working in. A session
  focused on `phylonames/` is different from one focused on
  `genomesDB/` is different from one focused on `trees_species/` —
  each maintains its own context, convention reminders, and recent
  state.
- **Continue the same session over many compactions** until it
  becomes overly reactive, muddled, or slow. Compactions are
  lossless (per §9 the full transcript is captured), so a long
  session isn't a problem until it starts feeling like one.
- **When a session goes muddled, start a fresh one** at the same
  named `gigantic_project-*/` root, focused on the same subproject,
  and bring it back up to speed (read the relevant AI_GUIDEs, recent
  commits, etc.).
- **Keep a separate "small questions" session** for random or
  cross-cutting questions (e.g., "what does this convention mean?"
  or "is this NCBI accession a GCF or GCA?"). This keeps the
  subproject sessions focused on their actual work and prevents
  context pollution.

### What this prevents

- Sessions that try to hold every subproject's state in context and
  end up confused about which one they're operating on.
- Sessions that get derailed by one-off questions and lose their
  thread on the subproject work.
- Session captures (per §9) that mix multiple unrelated subprojects
  into a single transcript, making the lab-notebook record harder
  to grep later.
