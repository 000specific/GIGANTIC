# AI_GUIDE.md (Level 2: Subproject Guide) — hotspots

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (project): [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — GIGANTIC overview + general patterns
- Subproject README: [`README.md`](README.md)
- Two BLOCKs, sequentially dependent:
  - [`BLOCK_self_blast/AI_GUIDE.md`](BLOCK_self_blast/AI_GUIDE.md) — chunked self-blastp; runs first
  - [`BLOCK_identify_hotspots/AI_GUIDE.md`](BLOCK_identify_hotspots/AI_GUIDE.md) — hotspot calling; depends on BLOCK_self_blast output
- Reads FROM:
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
  - `../../research_notebook/research_user/subproject-hotspots/gene_coordinates/` (per-species TSVs, user-prepared)
- Outputs TO:
  - `output_to_input/BLOCK_self_blast/self_blast_reports/`
  - `output_to_input/BLOCK_identify_hotspots/`
- Downstream consumers: `upload_to_server/`, comparative analyses

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Subproject overview + method summary | `README.md` |
| Subproject concepts (this file) | This file |
| BLOCK_self_blast concepts | `BLOCK_self_blast/AI_GUIDE.md` |
| BLOCK_identify_hotspots concepts | `BLOCK_identify_hotspots/AI_GUIDE.md` |
| Running BLOCK_self_blast | `BLOCK_self_blast/workflow-COPYME-self_blast/ai/AI_GUIDE.md` |
| Running BLOCK_identify_hotspots | `BLOCK_identify_hotspots/workflow-COPYME-identify_hotspots/ai/AI_GUIDE.md` |

## Two-BLOCK Sequential Pipeline

| Order | BLOCK | What | Why this order |
|-------|-------|------|----------------|
| 1 | self_blast | per-species blastp vs self (chunked + burst-fan-out) | Produces self_blast_reports consumed by step 2 |
| 2 | identify_hotspots | per-species hotspot calling | Reads self_blast_reports + gene_coordinates; builds paralog graph; emits connected components as hotspots |

## Conda Env

`aiG-hotspots` (shared across both BLOCKs per §53 short-form tolerance —
both BLOCKs use the same Python dependencies + blast). Auto-created on
first run from `BLOCK_self_blast/workflow-COPYME-self_blast/ai/conda_environment.yml`.

Note: this is a slight relaxation of strict §28 (`aiG-<subproject>-<block>`)
because the two BLOCKs share dependencies and there's no meaningful per-BLOCK
env divergence. Documented + tolerated per §53.

## Method (BLOCK_identify_hotspots)

From Edsinger 2024 (*Front. Mar. Sci.*, doi:10.3389/fmars.2024.1434130):

1. Filter self-BLAST hits by stringent e-value (default 1e-60)
2. For each retained hit, check if query + subject sit within a window of
   N gene-positions on the same chromosome (default 20 genes — ±10 around
   query)
3. Build paralog graph: nodes = genes, edges = (query, subject) pairs
   satisfying step 2
4. Connected components of the graph = hotspots

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| BLOCK_identify_hotspots fails: "gene_coordinates not found for species X" | User hasn't prepared the TSV for that species | Add `Genus_species-gene_coordinates.tsv` to `../../research_notebook/research_user/subproject-hotspots/gene_coordinates/` |
| BLOCK_self_blast: chunk dies in 0-1 sec | HiPerGator drain-node race (same root cause as annotations_hmms BLOCK_interproscan) | See annotations_hmms AI_GUIDE for canonical handling — `errorStrategy='ignore'` + gap detection |
| BLOCK_identify_hotspots: zero hotspots for species X | E-value too stringent for that species's divergence, or gene_coordinates_dir wrong | Verify path; consider relaxing e-value |
| Source_Gene_ID mismatch | gene_coordinates TSV uses different ID than GIGANTIC proteome's `g_` field | The id-mapping step (script 003 — `identify_hotspots.py`) uses proteome FASTA to translate; ensure proteomes_dir matches |

## §17 Deviation Note

`BLOCK_identify_hotspots` reads gene_coordinates directly from the
project-root `research_notebook/research_user/subproject-hotspots/gene_coordinates/`
rather than going through `INPUT_user/` symlinks as §17 prefers. This is a
known interim — refactoring to the §17 pattern (workflow reads from
`INPUT_user/gene_coordinates/` populated by user-managed symlinks into the
sandbox) is queued as future work.

## Questions to Ask User

| Situation | Ask |
|-----------|-----|
| First run | "Have you prepared per-species gene-coordinate TSVs in the sandbox?" |
| BLOCK_self_blast resource sizing | "How many species + how large are the proteomes? Default targets species70 with ~50 chunks per species; for larger sets adjust queueSize and chunk size." |
| BLOCK_identify_hotspots parameter tuning | "E-value 1e-60 is the default from the 2024 paper; relax if you expect deep divergence within a species. Window 20 genes is also from the paper." |
