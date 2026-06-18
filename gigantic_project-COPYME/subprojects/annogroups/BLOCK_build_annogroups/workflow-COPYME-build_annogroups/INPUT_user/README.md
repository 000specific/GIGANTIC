<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: Describe the user inputs staged for the build_annogroups workflow.
============================================================================ -->

# INPUT_user — build_annogroups

This workflow builds annogroups from *already-produced* upstream outputs (each
annotation source's parsed output + the species-set proteomes). It needs **no
user-supplied data files** — there is no manifest to edit.

Everything is read from sibling subprojects' `output_to_input/` directories (§2),
with the paths set in `../START_HERE-user_config.yaml`:

- **Annotation sources** (per source; each parser knows its own subpath) —
  `annotations_hmms/output_to_input/` — e.g. the pfam parser reads
  `BLOCK_interproscan_parsed/pfam/pfam-<phyloname>.tsv`.
- **Proteome universe** (membership universe for `absent`) —
  `genomesDB/output_to_input/STEP_4-create_final_species_set/<set>_gigantic_T1_proteomes/*.aa`.

The only choices you make are in `../START_HERE-user_config.yaml`:

- `species_set_name` — drives the proteome universe (e.g. `species70`).
- `sources` — `"all"` (every source with a parser plugin and data) or an
  explicit subset like `[ pfam, gene3d ]` (each subset entry must have a
  `ai/scripts/parsers/<source>.py` plugin).
- the input paths above, and execution settings (`execution_mode`,
  `parallelism_mode`, `slurm_account`, `slurm_qos`, `cpus`, `memory_gb`).

Adding a new source = adding one parser plugin (`ai/scripts/parsers/<source>.py`)
that implements `parse_source_features(workflow_root, config)`. Nothing else
changes. See the workflow `ai/AI_GUIDE.md` for the parser contract.
