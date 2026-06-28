<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: Describe the user inputs staged for the species_X_all_annotations
         integration workflow.
============================================================================ -->

# INPUT_user — species_X_all_annotations

This workflow integrates *already-produced* upstream outputs (the proteome spine
plus every per-gene annotation subproject). It needs **no user-supplied data
files** — there is no manifest to edit.

Everything is read from sibling subprojects, with the paths set in
`../START_HERE-user_config.yaml` (`inputs.*`):

- **Spine** — genomesDB STEP_4 per-species sequence tables
  (`genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_sequence_tables/`)
- **gene_sizes**, **hotspots**, **one_direction_homologs** (nr), **annotations_hmms**,
  **annogroups**, **orthogroups**, **secretome**, **dark_proteomes** — each from
  its subproject's `output_to_input/`
- **trees_gene_groups** / **trees_gene_families** AGS FASTA roots
- **orthogroups OCL** / **annogroup OCL** — per-structure, from
  `ocl_phylogenetic_structures/output_to_input/`

The only choices you make are in `../START_HERE-user_config.yaml`:
`run_label`, `species_set_name`, `structures` (`all` or a list of `structure_NNN`),
`nr_top_n`, `annogroup_sources`, the OCL run labels, the input paths, and
execution settings.

See the workflow `ai/AI_GUIDE.md` for the full input contract.
