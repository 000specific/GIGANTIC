# AI Guide: RBH/RBF Homolog Discovery Workflow (trees_gene_groups STEP_1)

**For AI Assistants**: Read `../../AI_GUIDE-homolog_discovery.md` first for STEP_1 concepts. This guide covers workflow execution and orchestrator internals.

**Location**: `gene_groups_COPYME/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/`

---

## Single user-runnable script

The COPYME's `RUN-workflow.sh` is the ONE script the user invokes. Always orchestrator mode (no per-gene-group invocation by the user). User flow:

```bash
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs
cd workflow-RUN_1-rbh_rbf_homologs
# edit START_HERE-user_config.yaml
bash RUN-workflow.sh
```

## Orchestrator behavior

`RUN-workflow.sh` reads `START_HERE-user_config.yaml` and:

1. Creates the conda env `aiG-trees_gene_groups-rbh_rbf_homologs` ONCE on the
   login node, before any sbatch (avoids many-job env-creation races).
2. Iterates `gene_group_source_tsv` (STEP_0 summary).
3. For each gene group: creates sibling `gene_group-X/workflow-RUN_01-rbh_rbf_homologs/`
   at the parent STEP_1 dir level. Customizes:
   - `INPUT_user/<rgs_filename>.aa` (RGS FASTA from STEP_0)
   - `INPUT_user/species_keeper_list.tsv` (auto-generated from `inputs.blast_databases_dir`)
   - `INPUT_user/rgs_species_map.tsv` (copied from the COPYME)
   - `START_HERE-user_config.yaml` (sed-patches `gene_family.name` and `rgs_full_length_file`)
4. Categorizes by RGS sequence count (small ≤ `large_threshold`, large > threshold).
5. Dispatches per `execution_mode`:
   - `local` — sequential nextflow runs
   - `slurm-standard` — 1 sbatch per gene group to standard QOS
   - `slurm-burst` — chunked: 1 sbatch per BLOCK to burst QOS

## Pipeline steps (per gene group, inside nextflow)

The 16-step pipeline groups into 10 NextFlow processes:

| Step | Script | NextFlow Process | What |
|------|--------|------------------|------|
| 001 | python | validate_rgs | Validate RGS FASTA |
| 002 | python | generate_and_run_forward_blast | Forward BLAST commands |
| 003 | bash | generate_and_run_forward_blast | Execute forward BLAST |
| 004 | python | extract_bgs_sequences | Extract BGS (fullseqs + hitregions) |
| 005 | python | generate_and_run_rgs_blast | RGS genome BLAST commands |
| 006 | bash | generate_and_run_rgs_blast | Execute RGS genome BLAST |
| 007 | python | map_rgs_and_build_reciprocal_db | List RGS BLAST files |
| 008 | python | map_rgs_and_build_reciprocal_db | Map RGS→genome IDs (NCBI accession + Hungarian + fail-fast) |
| 009 | python | map_rgs_and_build_reciprocal_db | Create modified genomes |
| 010 | python | map_rgs_and_build_reciprocal_db | Build combined BLAST DB |
| 011 | python | run_reciprocal_blast | Reciprocal BLAST commands |
| 012 | bash | run_reciprocal_blast | Execute reciprocal BLAST |
| 013 | python | extract_cgs_sequences | Extract CGS (with QUERY-side RGS-source protection) |
| 014 | python | filter_species | Filter by keeper list |
| 016 | python | create_ags_and_export | Final AGS |
| 017 | python | write_run_log | Pipeline run log |
| 018 | python | restore_full_length_rgs | Conditional, subsequence mode only |

## Script 008 — RGS identification

Script 008 maps each RGS protein to its cognate genome protein via 5 mechanisms
(see [../../PLAN-rgs_identification_improvements.md](../../PLAN-rgs_identification_improvements.md)):

1. **NCBI accession match** (primary) — direct lookup, zero ambiguity
2. **BLAST identity ≥95% AND symmetric coverage ≥95%** with T1 length-invariant check
3. **Bidirectional best hit** validation
4. **Hungarian optimal assignment** (scipy)
5. **Strict fail-fast** on any unresolved RGS

Output adds `mechanism` column to the mapping file plus a sidecar
`8_ai-rgs_identification_report.tsv`.

## Script 013 — RBH/RBF filter (format-independent)

Script 013 uses pure set membership (`hit in rgs_identifiers_set`) AND
QUERY-side protection (drops queries that are themselves project-DB proteins
corresponding to RGS) so that:
- Header format doesn't matter (works with any RGS header schema)
- `g_*-<rgs_source>` self-hits are excluded from CGS (prevents the historic
  RGS↔genome duplication in AGS)

## Conda env

`aiG-trees_gene_groups-rbh_rbf_homologs` — defined in `ai/conda_environment.yml`,
auto-created on first run from this dir's COPYME. Includes python, pyyaml,
nextflow, blast, numpy, scipy.

## YAML schema (key fields)

```yaml
execution_mode: "slurm-burst"           # local | slurm-standard | slurm-burst
gene_group_source_tsv: "<path to STEP_0 summary>"
rgs_fastas_dir: "<path to STEP_0 RGS dir>"
large_threshold: 50
slurm_account: "moroz"
slurm_qos_standard: "moroz"
slurm_qos_burst: "moroz-b"
small_cpus: 2; small_memory_gb: 15; small_time_hours: 12; small_time_hours_burst: 96; small_burst_block_size: 10
large_cpus: 8; large_memory_gb: 60; large_time_hours: 12; large_time_hours_burst: 96; large_burst_block_size: 3

# Nested keys consumed by nextflow.config:
gene_family: { name, rgs_full_length_file, rgs_sequence_is_full_length, include_orphan_rgs }
inputs:      { species_keeper_list, rgs_species_map, blast_databases_dir, rgs_genomes_dir }
project:     { database }
blast:       { evalue, threads, conda_env }
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "STEP_0 summary TSV not found" | STEP_0 hasn't run | Run STEP_0 first |
| "BLAST database not found" | genomesDB path wrong / not run | Verify `inputs.blast_databases_dir` |
| "CRITICAL ERROR: RGS identification failed" | Script 008 fail-fast on orphans | Inspect diagnostics; fix RGS input or species set |
| All blocks fail on conda activate | Env didn't get created on login node | Run `bash RUN-workflow.sh` from a login node; check that mamba/conda is available |

## Verification (after a successful run)

```bash
# AGS counts per gene group
ls ../gene_group-*/workflow-RUN_01-rbh_rbf_homologs/OUTPUT_pipeline/16-output/16_ai-ags-*.aa | wc -l

# Output_to_input symlinks for STEP_2
ls -l ../../../../output_to_input/<source>/STEP_1-homolog_discovery/gene_group-*/

# Audit script 008's mapping mechanisms across all gene groups
for f in ../gene_group-*/workflow-RUN_01-rbh_rbf_homologs/OUTPUT_pipeline/8-output/8_ai-rgs_identification_report.tsv; do
  awk -F'\t' 'NR>1 {print $3}' "$f"   # mechanism column
done | sort | uniq -c
```
