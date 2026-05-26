# AI Guide: RBH/RBF Homolog Discovery Workflow (trees_gene_groups STEP_1)

**For AI Assistants**: Read `../../AI_GUIDE-homolog_discovery.md` first for
STEP_1 concepts. This guide covers workflow execution and orchestrator
internals.

**Location**: `gene_groups_hgnc-COPYME/STEP_1-homolog_discovery/workflow-rbh_rbf_homologs/`

---

## 2026-05-26 simplification: STEP_1 is now BLAST-free for RGS identification

The RGS-to-source-genome BLAST chain (the entire "Improvement 2 + 3 + 4"
fallback path in script 008) was removed as dead code for
gene_groups_hgnc. RGS produced by either STEP_0 workflow now resolves to
its source-genome cognate via a single deterministic mechanism:

| RGS header format | Producer | Resolution mechanism |
|---|---|---|
| 4-field uniprot-sourced (`rgs_<group>-<species>-<symbol>-uniprot<id>`) | `workflow-hgnc_user_list` | **Improvement 0**: strict gene-symbol lookup against the proteome's `g_<SYMBOL>-` headers (exactly one match required, else fail-fast) |
| 5-field hgnc/ncbi-sourced (`rgs_<group>-<species>-<symbol>-<source>-<NP_id>`) | `workflow-hgnc_database` | **Improvement 1**: exact NCBI accession match against the proteome's `p_<accession>` |

Both mechanisms are strict and **fail-fast** — there is no BLAST rescue
path for RGS that doesn't cleanly resolve via its header's primary key.
The forward and reciprocal BLAST work (project_database BLAST + the
reciprocal BLAST that defines homologs) is unchanged and still used.

What was removed:
- Script 005 (`generate_blastp_commands-rgs_genomes.py`) — deleted entirely
- NextFlow process `blast_rgs_versus_rgs_genomes` — deleted from main.nf
- Output dirs `5-output/` and `6-output/` — no longer produced
- 264 lines from script 008 (Improvements 2, 3, 4 + helpers; scipy/numpy deps removed from conda env)
- `--input-blast-report-list` / `--output-blast-reports` args from script 007 + main.nf invocation

This applies only to gene_groups_hgnc-COPYME. The sibling
`gene_groups-COPYME` (and its frozen `gene_groups-hugo_hgnc` instance)
still retain the BLAST fallback chain.

---

## Single user-runnable script

The COPYME's `RUN-workflow.sh` is the ONE script the user invokes.
Always orchestrator mode (no per-gene-group invocation by the user):

```bash
# After instantiating the template (gene_groups_hgnc-<your_name>):
cd <instance>/STEP_1-homolog_discovery/workflow-rbh_rbf_homologs
# edit START_HERE-user_config.yaml (gene_group_source_tsv + rgs_fastas_dir)
bash RUN-workflow.sh
```

## Orchestrator behavior

`RUN-workflow.sh` reads `START_HERE-user_config.yaml` and:

1. Creates the conda env `aiG-trees_gene_groups-rbh_rbf_homologs` ONCE on
   the login node, before any sbatch (avoids many-job env-creation races).
2. Iterates `gene_group_source_tsv` (STEP_0 summary).
3. For each gene group: creates sibling
   `gene_group-X/workflow-RUN_01-rbh_rbf_homologs/` at the parent STEP_1
   dir level. Customizes:
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

After the 2026-05-26 simplification, the per-gene-group pipeline groups
into 9 NextFlow processes (one fewer than before — the
`blast_rgs_versus_rgs_genomes` process was removed):

| Step | Script | NextFlow Process | What |
|------|--------|------------------|------|
| 001 | python | validate_rgs | Validate RGS FASTA |
| 002 | python | blast_rgs_versus_project_database | Forward BLAST commands |
| 003 | bash | blast_rgs_versus_project_database | Execute forward BLAST |
| 004 | python | extract_blast_gene_sequences | Extract BGS (fullseqs + hitregions) |
| 007 | python | prepare_reciprocal_blast | List per-species proteome FASTAs |
| 008 | python | prepare_reciprocal_blast | Map RGS→genome IDs (gene-symbol OR NCBI accession; strict fail-fast) |
| 009 | python | prepare_reciprocal_blast | Create modified genomes |
| 010 | python | prepare_reciprocal_blast | Build combined BLAST DB |
| 011 | python | run_reciprocal_blast | Reciprocal BLAST commands |
| 012 | bash | run_reciprocal_blast | Execute reciprocal BLAST |
| 013 | python | extract_reciprocal_best_hits | Extract CGS (with QUERY-side RGS-source protection) |
| 014 | python | filter_species | Filter by keeper list |
| 016 | python | concatenate_final_gene_set | Final AGS |
| 017 | python | write_run_log | Pipeline run log |
| 018 | python | restore_full_length_rgs | Conditional, subsequence mode only |

Script numbering preserves the original 001-018 sequence; gaps at 003,
005, 006, 015 reflect bash sub-scripts or removed steps and are not
typos.

## Script 008 — RGS identification (BLAST-free)

After the 2026-05-26 simplification, script 008 dispatches on RGS header
format and uses one of two mechanisms:

1. **Improvement 0 — Gene-symbol search** (uniprot-sourced 4-field headers)
   - Parse gene_symbol from header field 3 (0-indexed 2)
   - Look up in the proteome's `g_<SYMBOL>-` headers
   - Exactly ONE match required; 0 matches → `no_proteome_protein_for_gene_symbol`,
     >1 matches → `multiple_proteome_proteins_for_gene_symbol`; either fails fast.
2. **Improvement 1 — NCBI accession match** (ncbi-sourced 5-field headers)
   - Extract NP_/XP_ accession from header's last field
   - Direct lookup in the genome accession index
   - T1 length invariant check (RGS must NOT exceed the genome T1 length)
   - No match → `accession_not_in_genome`, fails fast.
3. **Improvement 5 — Strict fail-fast** on anything still unresolved
   - The pipeline cannot proceed; the per-RGS audit report
     (`8_ai-rgs_identification_report.tsv`) identifies the exact reason.

Output adds `mechanism` column (`gene_symbol` or `ncbi_accession`) to
the mapping file plus the audit report sidecar.

## Script 013 — RBH/RBF filter (format-independent)

Script 013 uses pure set membership (`hit in rgs_identifiers_set`) AND
QUERY-side protection (drops queries that are themselves project-DB
proteins corresponding to RGS) so that:

- Header format doesn't matter (works with any RGS header schema —
  4-field uniprot or 5-field hgnc/ncbi)
- `g_*-<rgs_source>` self-hits are excluded from CGS (prevents the
  historic RGS↔genome duplication in AGS)

## Conda env

`aiG-trees_gene_groups-rbh_rbf_homologs` — defined in
`ai/conda_environment.yml`, auto-created on first run. After the
BLAST-fallback removal, dependencies are: python>=3.10, pyyaml, nextflow
(pinned <26.0), blast. (numpy + scipy were removed; they were only used
by the Hungarian assignment in the dropped fallback chain.)

## YAML schema (key fields)

```yaml
execution_mode: "slurm-burst"           # local | slurm-standard | slurm-burst
gene_group_source_tsv: "<path to STEP_0 summary TSV>"
rgs_fastas_dir: "<path to STEP_0 rgs_fastas/>"
large_threshold: 50
slurm_account: "moroz"
slurm_qos_standard: "moroz"
slurm_qos_burst: "moroz-b"
small_cpus: 10; small_memory_gb: 75; small_time_hours: 48; small_time_hours_burst: 96; small_burst_block_size: 10
large_cpus: 10; large_memory_gb: 75; large_time_hours: 48; large_time_hours_burst: 96; large_burst_block_size: 3

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
| "no_proteome_protein_for_gene_symbol" (uniprot RGS) | Symbol isn't HGNC-canonical | Check spelling; consult genenames.org. The script 001 in `workflow-hgnc_user_list` STEP_0 should have caught this — if it reached here, the proteome build may be missing the gene |
| "multiple_proteome_proteins_for_gene_symbol" (uniprot RGS) | T1 proteome has duplicates for the gene | Investigate the proteome build — T1 should have exactly one protein per gene_symbol |
| "accession_not_in_genome" (ncbi RGS) | RGS NCBI accession isn't in the proteome | Either rebuild proteome from a newer release or regenerate RGS from the same proteome version |
| "CRITICAL ERROR: RGS identification failed" | Script 008 fail-fast | Inspect `8_ai-rgs_identification_report.tsv` for the per-RGS reason |
| All blocks fail on conda activate | Env didn't get created on login node | Run `bash RUN-workflow.sh` from a login node; check that mamba/conda is available |

## Verification (after a successful run)

```bash
# AGS counts per gene group
ls ../gene_group-*/workflow-RUN_01-rbh_rbf_homologs/OUTPUT_pipeline/16-output/16_ai-ags-*.aa | wc -l

# output_to_input symlinks for STEP_2
ls -l ../../../../output_to_input/<instance>/STEP_1-homolog_discovery/gene_group-*/

# Audit script 008's mapping mechanisms across all gene groups
# Expected mechanisms: 'gene_symbol' (uniprot RGS) or 'ncbi_accession' (hgnc/ncbi RGS).
# 'blast_high_confidence' or 'hungarian_optimal' would indicate the old fallback chain — should never appear.
for f in ../gene_group-*/workflow-RUN_01-rbh_rbf_homologs/OUTPUT_pipeline/8-output/8_ai-rgs_identification_report.tsv; do
  awk -F'\t' 'NR>1 {print $3}' "$f"   # mechanism column
done | sort | uniq -c
```
