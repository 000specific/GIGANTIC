# STEP_3-databases — Build Per-Species BLAST Databases

<!-- ============================================================================
AI:      Claude Code | Opus 4.5 | 2026 February 12 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) — genomesDB overview
- Parent project: [`../../../README.md`](../../../README.md)
- This STEP's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow to run: [`workflow-COPYME-build_gigantic_genomesDB/README.md`](workflow-COPYME-build_gigantic_genomesDB/README.md)
- Reads from: [`../STEP_2-standardize_and_evaluate/`](../STEP_2-standardize_and_evaluate/) (standardized proteomes)
- **Next STEP**: [`../STEP_4-create_final_species_set/`](../STEP_4-create_final_species_set/) — assemble final species set
- **Downstream consumers** (per §40): `trees_gene_families`, `trees_gene_groups` (homolog discovery via BLAST)

---

## Purpose

STEP_3 of the genomesDB pipeline. Builds **per-species BLAST protein databases** from STEP_2 standardized proteomes.

**Part of**: genomesDB subproject (see `../README.md`)

---

## Workflow

```bash
cd workflow-COPYME-build_gigantic_genomesDB/

bash RUN-workflow.sh
```

The unified driver runs locally or self-submits to SLURM based on
`execution_mode` in `START_HERE-user_config.yaml` (per §29).

---

## Inputs

Standardized proteomes from STEP_2-standardize_and_evaluate.

**Location**: `workflow-COPYME-build_gigantic_genomesDB/INPUT_user/`
**From**: `../output_to_input/STEP_2-standardize_and_evaluate/`

---

## Outputs

- BLAST databases (blastp)
- Species manifests
- Proteome indices

**Shared with other subprojects via**: `../output_to_input/` (genomesDB root)

---

## Research Notebook

Workflow run logs are saved to each workflow's `ai/logs/` directory. AI sessions are extracted project-wide to `research_notebook/research_ai/sessions/`.

---

## Dependencies

- STEP_2-standardize_and_evaluate must complete first
- BLAST+ tools (available in `aiG-genomesDB` conda environment)

---

## Notes

- BLAST databases require substantial disk space
- The complete STEP_3 pipeline may take several hours for large species sets
