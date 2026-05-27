# AI_GUIDE.md (Level 2: Subproject Guide) — dark_proteomes

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (project): [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — GIGANTIC overview + general patterns
- Subproject README: [`README.md`](README.md)
- BLOCK guide: [`BLOCK_classify_dark_proteome/AI_GUIDE.md`](BLOCK_classify_dark_proteome/AI_GUIDE.md)
- Workflow guide: [`BLOCK_classify_dark_proteome/workflow-COPYME-classify_dark_proteome/ai/AI_GUIDE.md`](BLOCK_classify_dark_proteome/workflow-COPYME-classify_dark_proteome/ai/AI_GUIDE.md)
- Reads FROM (per axis):
  - axis_a: `../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/`
  - axis_b: `../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv` (or other standardized OG table)
  - axis_c: `../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/`
  - species set: `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs TO: `output_to_input/BLOCK_classify_dark_proteome/`
- Downstream: `upload_to_server/` — curated subset for GIGANTIC server

---

**For AI Assistants**: Read `../../AI_GUIDE.md` first for GIGANTIC overview.
This guide covers dark_proteomes concepts.

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Subproject overview | `README.md` |
| BLOCK + workflow concepts | `BLOCK_classify_dark_proteome/AI_GUIDE.md` |
| Running the workflow | `BLOCK_classify_dark_proteome/workflow-COPYME-classify_dark_proteome/ai/AI_GUIDE.md` |

---

## Purpose

Classify every gene in every project species as DARK (genomic dark matter)
or ANNOTATED, using the three-axis test from Edsinger 2024
(*Frontiers in Marine Science*). A gene is DARK if and only if all three
independent axes fail.

## The Three Axes

| Axis | Test (signal for "annotated") | Data source |
|------|-------------------------------|-------------|
| **a** | BLAST hit to a reference species | `one_direction_homologs` (diamond vs NCBI nr top hits, filtered to the reference set) |
| **b** | Membership in an orthogroup that contains a reference species gene | `orthogroups` (orthoHMM_GIGANTIC table by default) |
| **c** | Pfam or PANTHER domain annotation | `annotations_hmms/BLOCK_interproscan_parsed/` |

**Strict definition**: DARK = NOT axis_a AND NOT axis_b AND NOT axis_c.
The intersection isolates genes too divergent from model organisms to be
detected by any standard annotation method, while remaining valid gene
predictions in the species's proteome.

Default reference species: human, *Drosophila*, *C. elegans* (the paper's
three). Configurable in `START_HERE-user_config.yaml`.

## Architecture

Single BLOCK, no internal sequencing — the pipeline is a fan-out per
species after one shared pre-processing step:

1. **validate_inputs** — pair every species with its 4 inputs; fail-fast if any missing
2. **build_reference_orthogroup_set** — one-time pre-process; the set of OGs containing reference species
3. **classify_per_species** — per-species fan-out; 3-axis check per gene → DARK/ANNOTATED label
4. **summarize_dark_proteome** — cross-species aggregate (dark counts, percentages, by species/clade)
5. **write_run_log** — per §45

## Subproject Dependencies

Run order across GIGANTIC subprojects (axes are independent — each requires its own upstream BLOCK):

```
genomesDB                  ──┐
one_direction_homologs (axis_a) ──┐
orthogroups (axis_b)              ├──→ dark_proteomes
annotations_hmms (axis_c)         ──┘
```

Any subset can be skipped by leaving its input dir empty, but a meaningful
classification requires at least one signal — and the strict DARK
definition assumes all three.

## Conda Env

`aiG-dark_proteomes` (single-BLOCK subproject; not strictly the §28 form
`aiG-<subproject>-<block>` — minor deviation flagged for future
consideration, functionally fine since there's only one BLOCK).

Auto-created from `BLOCK_classify_dark_proteome/workflow-COPYME-classify_dark_proteome/ai/conda_environment.yml` on first run of `RUN-workflow.sh`.

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| Missing input for species X (axis_a) | one_direction_homologs incomplete or different species set | Check `../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/` |
| Missing input for species X (axis_b) | orthogroups subproject incomplete | Check the OG table path; usually orthoHMM_GIGANTIC |
| Missing input for species X (axis_c) | annotations_hmms incomplete | Check `../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/` |
| Unexpectedly high dark % | Species set mismatch with upstream subprojects | Verify all four input directories use the same species set (species70 / speciesN) |

## Questions to Ask User

| Situation | Ask |
|-----------|-----|
| First run | "Which species set? speciesN must be consistent across the 4 upstream subprojects." |
| Reference species choice | "Default is human + Drosophila + C. elegans. Want different references? Edit `reference_species` in the YAML." |
| Partial upstream | "Have all three upstream subprojects (one_direction_homologs, orthogroups, annotations_hmms) completed? Strict 3-axis DARK requires all three." |
