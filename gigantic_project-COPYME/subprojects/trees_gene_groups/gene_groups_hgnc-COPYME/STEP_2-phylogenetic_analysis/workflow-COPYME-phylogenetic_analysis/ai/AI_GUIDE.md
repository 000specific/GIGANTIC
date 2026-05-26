# AI Guide: Phylogenetic Analysis Workflow (trees_gene_groups STEP_2)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Conda env: `aiG-trees_gene_groups-phylogenetic_analysis`

---

**For AI Assistants**: Read `../../AI_GUIDE.md` first for STEP_2 concepts. This guide covers workflow execution.

**Location**: `gene_groups-COPYME/STEP_2-phylogenetic_analysis/workflow-COPYME-phylogenetic_analysis/`

---

## Single user-runnable script

The COPYME's `RUN-workflow.sh` is the ONE script the user invokes. Always orchestrator mode. User flow:

```bash
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_1-phylogenetic_analysis
cd workflow-RUN_1-phylogenetic_analysis
# edit START_HERE-user_config.yaml
bash RUN-workflow.sh
```

## Orchestrator behavior

`RUN-workflow.sh` reads `START_HERE-user_config.yaml` and:

1. Creates the conda env `aiG-trees_gene_groups-phylogenetic_analysis` ONCE on the
   login node, before any sbatch.
2. Iterates `gene_group_source_tsv` (STEP_0 summary).
3. For each gene group with a STEP_1 AGS file at `step1_output_to_input_dir/gene_group-<name>/`:
   - Creates sibling `gene_group-X/workflow-RUN_01-phylogenetic_analysis/` at the parent STEP_2 dir level
   - Sed-patches `gene_family.name` in its YAML
   - Skips if STEP_1 AGS for that gene group is missing (STEP_1 still running)
4. Categorizes by RGS sequence count (from STEP_0 summary's `sequence_count` column).
5. Dispatches per `execution_mode`:
   - `local` — sequential nextflow runs
   - `slurm-standard` — 1 sbatch per gene group, standard QOS
   - `slurm-burst` — chunked, 1 sbatch per BLOCK to burst QOS

## Pipeline (per gene group, inside nextflow)

| Process | Tool | What |
|---------|------|------|
| 1 | bash | Stage AGS from STEP_1 output_to_input |
| 2 | bash | Strip leading/trailing dashes |
| 3 | MAFFT | Multiple sequence alignment |
| 4 | ClipKit | Smart-gap trimming |
| 5_a | FastTree | Fast approximate ML (default ON) |
| 5_b | IQ-TREE | Full ML + bootstrap (slow) |
| 5_c | VeryFastTree | Parallel FastTree alternative |
| 5_d | PhyloBayes | Bayesian MCMC (very slow) |
| 6 | python | Run log |

Tree methods are independently toggled in `tree_methods:` YAML. At least one must be enabled.

## YAML schema (key fields)

```yaml
execution_mode: "slurm-burst"
gene_group_source_tsv: "<path to STEP_0 summary>"
step1_output_to_input_dir: "<path to STEP_1 output_to_input dir>"
large_threshold: 50
slurm_account: "moroz"
slurm_qos_standard: "moroz"
slurm_qos_burst: "moroz-b"
small_cpus: 4; small_memory_gb: 16; small_time_hours: 12; small_time_hours_burst: 96; small_burst_block_size: 10
large_cpus: 16; large_memory_gb: 64; large_time_hours: 24; large_time_hours_burst: 168; large_burst_block_size: 3

# Nested, consumed by nextflow.config:
gene_family:       { name }
input:             { output_to_input_dir }
project:           { name, database }
tree_methods:      { fasttree, iqtree, veryfasttree, phylobayes }
phylogenetics:     { mafft, clipkit, iqtree, veryfasttree, phylobayes }
output:            { base_dir }
```

## Conda env

`aiG-trees_gene_groups-phylogenetic_analysis` — defined in `ai/conda_environment.yml`,
auto-created on first run. Includes: python, pyyaml, nextflow, mafft, clipkit,
fasttree, iqtree, veryfasttree.

## Verification (after a successful run)

```bash
# Count trees produced per gene group
for d in ../gene_group-*/workflow-RUN_01-phylogenetic_analysis/OUTPUT_pipeline; do
  echo "$d"
  ls "$d"/5_*-output/*.{fasttree,treefile,veryfasttree,phylobayes.nwk} 2>/dev/null | wc -l
done

# Output_to_input symlinks for STEP_3
ls -l ../../../../output_to_input/<source>/STEP_2-phylogenetic_analysis/gene_group-*/
```
