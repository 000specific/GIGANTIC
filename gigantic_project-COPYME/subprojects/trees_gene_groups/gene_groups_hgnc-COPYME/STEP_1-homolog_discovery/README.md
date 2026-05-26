# STEP_1 — Homolog Discovery (RBH/RBF)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (template): [`../README.md`](../README.md)
- Parent (subproject): [`../../README.md`](../../README.md)
- STEP-level AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow template: [`workflow-rbh_rbf_homologs/`](workflow-rbh_rbf_homologs/) (pre-§3 name — lacks COPYME prefix)
- Reads FROM: per-gene-group RGS FASTAs from STEP_0 + `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/`
- Outputs TO: `../../../output_to_input/<gene_group>/STEP_1-homolog_discovery/`
- Downstream STEP: `../STEP_2-phylogenetic_analysis/`
- 2026-05-26: BLAST-fallback chain removed in THIS variant (RGS from STEP_0 resolves cleanly via gene-symbol or NCBI-accession); sibling `gene_groups-COPYME/STEP_1` still has fallback
- Conda env: `aiG-trees_gene_groups-rbh_rbf_homologs`

---

Per-source STEP_1: find homologs of each gene group's Reference Gene Set (RGS)
across all project species via reciprocal best hit / reciprocal best family BLAST.

## Single user-runnable script

The workflow inside `workflow-COPYME-rbh_rbf_homologs/` is the template. To run
STEP_1 for a source:

```bash
# 1. Inside the per-source instance (e.g., gene_groups-<INSTANCE>/STEP_1-homolog_discovery/),
#    copy the COPYME → RUN_NN at the same level:
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs

# 2. Edit the RUN's config (execution_mode, paths, SLURM resources):
cd workflow-RUN_1-rbh_rbf_homologs
# edit START_HERE-user_config.yaml

# 3. Run the single user-facing script
bash RUN-workflow.sh
```

`RUN-workflow.sh` is an **orchestrator** that processes all gene groups in the
STEP_0 summary TSV:

1. Creates the per-workflow conda env on the login node (first run only)
2. For each gene group: sets up `gene_group-X/workflow-RUN_01-rbh_rbf_homologs/` as a sibling at this STEP_1 directory
3. Dispatches per `execution_mode` from the YAML:
   - `local` — sequential local nextflow runs
   - `slurm-standard` — one `sbatch` per gene group to the standard QOS
   - `slurm-burst` — chunked: one `sbatch` per BLOCK of gene groups, burst QOS

## Prerequisites

- STEP_0 must have completed for this source (produces the RGS FASTAs in `output_to_input/`)
- genomesDB subproject must be complete (BLAST databases)

## Pipeline steps (inside each per-gene-group nextflow run)

| # | Script | What it does |
|---|--------|-------------|
| 001 | validate_rgs | Validate RGS FASTA file (fail-fast on invalid) |
| 002–003 | generate + run forward BLAST | RGS vs project species DBs |
| 004 | extract_gene_set_sequences | Extract BGS (full-length + hit regions) |
| 005–006 | generate + run RGS-genome BLAST | RGS vs source-organism genomes |
| 007 | list_rgs_blast_files | Inventory RGS BLAST files |
| 008 | map_rgs_to_reference_genomes | NCBI-accession + Hungarian-optimal mapping with fail-fast on orphans |
| 009 | create_modified_genomes | Splice RGS into source genomes for reciprocal BLAST |
| 010 | generate_makeblastdb_commands | Build combined reciprocal BLAST DB |
| 011–012 | generate + run reciprocal BLAST | CGS vs combined DB |
| 013 | extract_reciprocal_best_hits | Filter for QUERY-side and HIT-side RGS-protected RBH/RBF |
| 014 | filter_species_for_tree_building | Keep only species in the keeper list |
| 016 | concatenate_sequences | Concatenate RGS + filtered CGS into final AGS |
| 017 | write_run_log | Pipeline run log |
| 018 | restore_full_length_rgs_sequences | Conditional: subsequence mode only |

## Output

Final AGS files are symlinked at the subproject root:

```
trees_gene_groups/output_to_input/<source>/STEP_1-homolog_discovery/gene_group-<name>/16_ai-ags-*.aa
```

These are STEP_2's input.

## See also

- `AI_GUIDE.md` — detailed AI guide for this STEP
- `workflow-COPYME-rbh_rbf_homologs/ai/AI_GUIDE.md` — workflow execution guide
- `PLAN-rgs_identification_improvements.md` — design doc for script 008's RGS mapping
