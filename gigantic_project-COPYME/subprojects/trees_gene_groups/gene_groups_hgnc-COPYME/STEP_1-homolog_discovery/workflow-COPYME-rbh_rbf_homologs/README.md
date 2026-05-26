# workflow-COPYME-rbh_rbf_homologs

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP: [`../README.md`](../README.md)
- Parent (template): [`../../../README.md`](../../../README.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: per-gene-group RGS FASTAs from STEP_0 + `../../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/`
- Outputs to: `../../../../../output_to_input/<gene_group>/STEP_1-homolog_discovery/`
- Downstream STEP: `../../STEP_2-phylogenetic_analysis/workflow-COPYME-phylogenetic_analysis/`
- BLAST-fallback chain REMOVED in this variant (vs gene_groups-COPYME STEP_1)

---

STEP_1 workflow template (orchestrator) for trees_gene_groups. Processes all
gene groups for a source via RBH/RBF homolog discovery.

## Single user-runnable script

```bash
# 1. Copy this COPYME to a RUN_NN at the same level
#    (e.g., inside gene_groups-<INSTANCE>/STEP_1-homolog_discovery/):
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs
cd workflow-RUN_1-rbh_rbf_homologs

# 2. Edit START_HERE-user_config.yaml (set execution_mode + paths)

# 3. Run
bash RUN-workflow.sh
```

## What `RUN-workflow.sh` does (orchestrator)

1. Creates the conda env `aiG-trees_gene_groups-rbh_rbf_homologs` once on the
   login node from `ai/conda_environment.yml` (if missing)
2. Iterates the STEP_0 summary TSV (`gene_group_source_tsv` in config)
3. For each gene group: creates `gene_group-X/workflow-RUN_01-rbh_rbf_homologs/`
   as a sibling at the STEP_1 directory level; copies the RGS file, species
   keeper list, and species map into its `INPUT_user/`; sed-patches its
   `gene_family.name` and `rgs_full_length_file`
4. Categorizes gene groups as small (≤ `large_threshold` RGS seqs) or large
5. Dispatches per `execution_mode`:
   - `local` — sequential nextflow runs
   - `slurm-standard` — 1 sbatch per gene group, standard QOS, per-tier resources
   - `slurm-burst` — chunk into blocks of `burst_block_size`, 1 sbatch per block, burst QOS, blocks run gene groups sequentially

## Configuration

All settings live in `START_HERE-user_config.yaml`. Key options:

| Setting | Choices | What |
|---------|---------|------|
| `execution_mode` | `local` \| `slurm-standard` \| `slurm-burst` | Dispatch strategy |
| `gene_group_source_tsv` | Path | STEP_0 summary (one row per gene group) |
| `rgs_fastas_dir` | Path | STEP_0 RGS output directory |
| `large_threshold` | Integer | RGS seq count splitting small/large tiers |
| `slurm_account`, `slurm_qos_standard`, `slurm_qos_burst` | Strings | SLURM identifiers |
| `small_*`, `large_*` | Numbers | CPUs, memory, time, burst block size per tier |

## Per-gene-group pipeline (inside each sub-RUN_01)

NextFlow pipeline running 16 steps (validate RGS → forward BLAST → BGS extract → RGS-genome BLAST → map RGS to genomes → modified genomes → reciprocal BLAST → CGS extract → species filter → AGS). See `ai/AI_GUIDE.md` for details.

## Outputs

| Output | Location |
|--------|----------|
| Final AGS per gene group | `../gene_group-X/workflow-RUN_01-rbh_rbf_homologs/OUTPUT_pipeline/16-output/16_ai-ags-*.aa` |
| AGS symlinks for STEP_2 | `../../../../output_to_input/<source>/STEP_1-homolog_discovery/gene_group-X/*.aa` |
| RGS identification audit | `OUTPUT_pipeline/8-output/8_ai-rgs_identification_report.tsv` |
| SLURM logs | `../slurm_logs/` (when execution_mode is slurm-*) |

## Next step

After STEP_1 completes, the AGS files are STEP_2's input. See `../../STEP_2-phylogenetic_analysis/`.
