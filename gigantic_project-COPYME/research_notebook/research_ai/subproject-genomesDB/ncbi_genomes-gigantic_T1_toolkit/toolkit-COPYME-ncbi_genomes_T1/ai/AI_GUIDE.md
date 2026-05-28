<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 28
Human:   Eric Edsinger
Purpose: AI-facing operational guide for the NCBI Genomes T1 Toolkit. Tells
         the next AI session what each script does, how the data flows, and
         what failure modes are known.
Scope:   The ai/ directory of toolkit-COPYME-ncbi_genomes_T1/ and any
         toolkit-RUN_*-ncbi_genomes_T1/ instance.
History:
  2026-05-28  Ground-up rebuild + relocation to research_ai/ per §59.
============================================================================ -->

# `ai/` — AI Guide for the NCBI Genomes T1 Toolkit

You are an AI assistant working inside the NCBI Genomes T1 Toolkit. Read
[`../README.md`](../README.md) next to this file for the user-facing overview
and quick start. This guide tells you **how to operate**.

## Where this fits

- **Parent project**: [`../../../../../`](../../../../../) (renamed `gigantic_project-*/`)
- **Parent toolkit dir**: [`../../`](../../) — has the cross-RUN `output_to_input/`
- **This unit's user docs**: [`../README.md`](../README.md)
- **Downstream consumer**: `subprojects/genomesDB/STEP_1-sources/` reads from
  `INPUT_user/genomic_resources/{proteomes,genomes,annotations}/` — populated
  by this toolkit's process 4 (`bridge_to_input_user`).

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC conventions | `../../../../../ai/ai_FYIs/gigantic_conventions.md` |
| What this toolkit does (user-facing) | [`../README.md`](../README.md) |
| Manifest format | [`../INPUT_user/README.md`](../INPUT_user/README.md) |
| User config knobs | [`../START_HERE-user_config.yaml`](../START_HERE-user_config.yaml) |
| Run the toolkit | [`../RUN-workflow.sh`](../RUN-workflow.sh) |
| Pipeline (NextFlow) | [`main.nf`](main.nf) |
| Pipeline scripts | [`scripts/`](scripts/) |
| Conda env spec | [`conda_environment.yml`](conda_environment.yml) (env name: `aiG-toolkit-ncbi_genomes`) |
| Per-run audit logs | `logs/run_<timestamp>-<toolkit_name>_success.log` |

## Pipeline anatomy (5 processes, sequential)

```
Process 1  -- download_ncbi_bundles
   reads:  ../INPUT_user/ncbi_genomes_manifest.tsv
   writes: OUTPUT_pipeline/1-output/downloads/<Genus_species>.zip
   script: scripts/001_ai-bash-download_ncbi_bundles.sh

Process 2  -- unzip_organize_rename
   reads:  OUTPUT_pipeline/1-output/downloads/*.zip
   writes: OUTPUT_pipeline/2-output/{genome,gff3,protein}/<Genus_species>-ncbi_genomes.{fasta,gff3,faa}
   script: scripts/002_ai-python-unzip_organize_rename.py

Process 3  -- extract_t1_with_alt_loci_filter
   reads:  OUTPUT_pipeline/2-output/{genome,gff3,protein}/  +  manifest
   writes: OUTPUT_pipeline/3-output/T1_proteomes/<...>-genome_ncbi_<ACC>-downloaded_<DATE>.aa
           OUTPUT_pipeline/3-output/genomes/<...>.fasta
           OUTPUT_pipeline/3-output/gene_annotations/<...>.gff3
           OUTPUT_pipeline/3-output/maps/{genome_identifiers,sequence_identifiers,alternate_loci_log}.tsv
   script: scripts/003_ai-python-extract_t1_with_alt_loci_filter.py
   notes:  carries the months-of-work alt-loci filter design from prior
           toolkit iterations. See in-code comment block at the
           new_basename assignment for the GIGANTIC INPUT_user filename
           spec match (`-genome_` not `-genome-`).

Process 4  -- bridge_to_input_user
   reads:  OUTPUT_pipeline/3-output/{T1_proteomes,genomes,gene_annotations,maps}/
   writes: ../../output_to_input/<subdir>/<file>                                  (parent stable symlinks)
           ../../../../../../INPUT_user/genomic_resources/{proteomes,genomes,annotations}/<file>
                                                                                  (GIGANTIC staging arena)
           OUTPUT_pipeline/4-output/bridge_done.marker                            (NextFlow marker)
   script: scripts/004_ai-python-bridge_to_input_user.py
   notes:  NEW for the ground-up rebuild. Per gigantic_conventions.md §17, §18.
           Subdir name mapping is encoded in SUBDIR_MAPPING constant inside the script.

Process 5  -- write_run_log
   reads:  everything upstream
   writes: ai/logs/run_<timestamp>-<toolkit_name>_success.log
           OUTPUT_pipeline/5-output/run_log_written.marker
   script: scripts/005_ai-python-write_run_log.py
   notes:  per gigantic_conventions.md §45 (canonical final script).
```

## Data flow at a glance

```
User-edited manifest:
   <toolkit-RUN_N>/INPUT_user/ncbi_genomes_manifest.tsv
        |
        v
Real files produced by pipeline:
   <toolkit-RUN_N>/OUTPUT_pipeline/3-output/<subdir>/<GIGANTIC-named files>
        |
        v   (hop A: relative symlinks created by script 004)
Parent's stable view (RUN-independent):
   ../output_to_input/<subdir>/<file>  ->  <toolkit-RUN_N>/OUTPUT_pipeline/3-output/<subdir>/<file>
        |
        v   (hop B: relative symlinks created by script 004)
GIGANTIC staging arena (read by genomesDB STEP_1):
   <project_root>/INPUT_user/genomic_resources/<dest_subdir>/<file>  ->  ../output_to_input/<subdir>/<file>

Subdir mapping (hop B):
   T1_proteomes     ->  proteomes
   genomes          ->  genomes
   gene_annotations ->  annotations
   maps             ->  (parent only; not bridged)
```

## Conventions adopted

- **§28 conda env**: single env `aiG-toolkit-ncbi_genomes` provides nextflow,
  ncbi-datasets-cli, python, unzip, pyyaml. No env switching mid-pipeline.
  Auto-created by `RUN-workflow.sh` from `conda_environment.yml` on first run.
- **§29 unified `RUN-workflow.sh`**: one entry point; reads `execution_mode`
  from YAML; self-submits to SLURM when set to `slurm`, runs locally otherwise.
  Refuses to run from `*COPYME*` (template) dirs.
- **§17, §18 INPUT_user staging**: process 4 auto-creates relative symlinks
  from `INPUT_user/genomic_resources/` into this toolkit's outputs. Real
  files live in the sandbox per §1; GIGANTIC subprojects read via the symlinks.
- **§36 fail-fast**: scripts use `sys.exit(1)` on missing/invalid inputs.
  No `optional: true` outputs in `main.nf`. NextFlow process `errorStrategy = 'terminate'`.
- **§45 write_run_log**: script 005 is the canonical final step; writes
  timestamped audit logs to `ai/logs/`.
- **§12 AI attribution headers**: every file has the AI/Human/Purpose block.
- **§34 self-documenting TSV headers**: identifier maps use prose-style
  column headers in parentheses.
- **§35 workflow-RUN naming**: instances are `toolkit-RUN_NN-ncbi_genomes_T1/`
  (single-digit OK for low N; can be two-digit `RUN_01` if you prefer
  alphabetic-sortability at high N).
- **§47 frozen-artifact rule**: do not edit `toolkit-RUN_*/` dirs after they've
  successfully completed (per-run records of how the toolkit was at that time).
  Only edit `toolkit-COPYME-ncbi_genomes_T1/` for forward improvements.

## Known failure modes and how to respond

| Symptom | Cause | What to do |
|---|---|---|
| `Error nextflow.config:N:M: Unexpected input: 'import'` | Old config tried to load YAML via Groovy `import` (rejected by Nextflow 25+) | Already fixed in this rebuild; RUN-workflow.sh now passes params via CLI. Don't reintroduce the import. |
| Script 002 `CRITICAL: No protein file for <species>` | The assembly bundle lacks `protein.faa` — common with bare GenBank `GCA_*` assemblies that ship only sequence, no annotation | The toolkit fails fast per §36. Either pick a GCF (RefSeq) for the species, or hand-prep separately and stage via §17/§18. |
| Alt-loci filter is a no-op for a `GCA_*` species (alternate_loci_log shows zero dedup) | GenBank GFF3 lacks `Dbxref=GeneID:` — the alt-loci filter keys on GeneID and has no group structure to dedup against. **Silent** behavior: a GCA with no actual alt-haplotype duplicates passes through correctly; a GCA WITH duplicates would include them as separate proteins. | Validate the species's GFF3 against a comparable GCF and compare the T1 protein count to NCBI's `gene_biotype=protein_coding` count for that assembly. If they match 1:1, the no-op was correct. If they don't, the GCA needs hand-prep. |
| `datasets` CLI download fails repeatedly | Transient NCBI network issues | Script 001 retries 4 times with exponential backoff. If all 4 fail, the species is dropped and the run exits non-zero (manifest count must equal download count). Re-run later. |
| Stale NextFlow cache produces unexpected results | `work/` and `.nextflow/` weren't cleared between runs after script changes | `rm -rf work .nextflow .nextflow.log*` then re-run without `resume: true`. |
| `Refusing to overwrite non-symlink at <path>` from script 004 | Real file (not a symlink) sits where INPUT_user symlink should go | Resolve manually: move the conflicting real file out of the way, re-run. Don't bypass the check; it protects real data from accidental clobber. |
| Alt-loci filter doesn't trigger for a species you expect | NCBI's GFF3 for that species doesn't have `Dbxref=GeneID:<N>` attributes, or the species lacks duplicate GeneIDs | Read `OUTPUT_pipeline/3-output/maps/ncbi_genomes-alternate_loci_log.tsv` for the per-species decision log. No-op for species without alt-loci is expected behavior. |

## When you add or modify a script

1. Use `NNN_ai-<lang>-<descriptor>.<ext>` per §21.
2. Add the attribution header (§12).
3. If you're porting from an archived RUN_*, preserve the original attribution
   AND add a `# Ported: ...` line documenting the import.
4. Update `main.nf` to call the new script and declare its outputs.
5. Update the **Pipeline anatomy** table in this AI_GUIDE.

## When you modify the bridge (script 004)

The two-hop symlink chain (RUN 3-output → parent output_to_input → INPUT_user)
is load-bearing: every downstream GIGANTIC subproject reads from the
INPUT_user end of that chain. Changes here have wide blast radius. Specifically:

- Don't change the `SUBDIR_MAPPING` constant casually — adding/removing entries
  changes what gets bridged.
- Always use `os.path.relpath`-based symlinks so the entire project remains
  movable / archivable / cloneable (§18).
- Never overwrite a real file at a target path. Always check `is_symlink()`
  first; abort with a clear error if the target is a real file.

## Toolkit / framework boundary

This toolkit lives in `research_notebook/research_ai/subproject-genomesDB/`
per §59 (the canonical toolkit home). The bridge step (process 4) is
the explicit handoff from toolkit outputs into the project-level
`INPUT_user/genomic_resources/` staging arena. GIGANTIC subprojects
read from `INPUT_user/`, not from this toolkit directly.

Per §60: this toolkit is **permanent in this category** — it does not
become a subproject. The framework intentionally does not own its
inputs because the choice of genome assemblies, alt-loci policy,
GCA-vs-GCF handling, etc. varies too much across projects to be
standardized.
