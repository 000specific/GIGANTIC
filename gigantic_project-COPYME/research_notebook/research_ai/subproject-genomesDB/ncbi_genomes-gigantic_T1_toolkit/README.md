<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 28
Human:   Eric Edsinger
Purpose: Parent-dir overview of the NCBI Genomes T1 Toolkit (the canonical
         seed GIGANTIC toolkit per §59). Lives in
         research_notebook/research_ai/subproject-genomesDB/ and follows
         GIGANTIC framework conventions internally (§28, §29, §17/§18,
         §36, §45).
Scope:   The ncbi_genomes-gigantic_T1_toolkit/ parent dir, its
         toolkit-COPYME-* template, and any toolkit-RUN_*-* run instances.
History:
  2026-05-28  Ground-up rebuild and relocation from
              research_notebook/research_user/ to research_notebook/research_ai/
              per the §59 rewrite (commit 818cb1b). Now ships as the
              canonical seed toolkit on GitHub.
============================================================================ -->

# NCBI Genomes T1 Toolkit

Sandbox-side toolkit that downloads NCBI RefSeq genome bundles, T1-extracts
proteomes with alternate-loci filtering, renames to GIGANTIC convention, and
auto-bridges into the project's `INPUT_user/genomic_resources/` staging arena.

## Where this fits

- **Parent project**: [`../../../../`](../../../../) (renamed `gigantic_project-*/`)
- **Toolkit template**: [`toolkit-COPYME-ncbi_genomes_T1/`](toolkit-COPYME-ncbi_genomes_T1/)
- **Run instances**: `toolkit-RUN_<N>-ncbi_genomes_T1/` (gitignored; copies of the template)
- **Cross-RUN stable output view**: [`output_to_input/`](output_to_input/)
- **Downstream consumer**: `subprojects/genomesDB/STEP_1-sources/` reads from
  `<project_root>/INPUT_user/genomic_resources/{proteomes,genomes,annotations}/`
  — populated by this toolkit's process 4.

## Directory layout

```
ncbi_genomes-gigantic_T1_toolkit/
├── README.md                                   # this file
├── AI_GUIDE.md                                 # AI-facing operational guide
│
├── output_to_input/                            # stable, cross-RUN view
│   ├── T1_proteomes/                           # symlinks -> current RUN's 3-output/T1_proteomes/
│   ├── genomes/                                # symlinks -> current RUN's 3-output/genomes/
│   ├── gene_annotations/                       # symlinks -> current RUN's 3-output/gene_annotations/
│   └── maps/                                   # symlinks -> current RUN's 3-output/maps/
│
└── toolkit-COPYME-ncbi_genomes_T1/             # the template (copy before running)
    ├── README.md                               # user-facing quick start
    ├── RUN-workflow.sh                         # unified entry point per §29
    ├── START_HERE-user_config.yaml             # execution_mode, SLURM, knobs
    ├── INPUT_user/
    │   ├── README.md                           # manifest format
    │   └── ncbi_genomes_manifest.tsv           # 2-col TSV (genus_species, accession)
    └── ai/
        ├── AI_GUIDE.md                         # toolkit AI guide
        ├── main.nf                             # 5-process NextFlow pipeline
        ├── nextflow.config
        ├── conda_environment.yml               # env: aiG-toolkit-ncbi_genomes
        └── scripts/
            ├── 001_ai-bash-download_ncbi_bundles.sh
            ├── 002_ai-python-unzip_organize_rename.py
            ├── 003_ai-python-extract_t1_with_alt_loci_filter.py
            ├── 004_ai-python-bridge_to_input_user.py
            └── 005_ai-python-write_run_log.py
```

## Quick start

```bash
# 1. Copy the COPYME template into a RUN-instance dir
cp -r toolkit-COPYME-ncbi_genomes_T1 toolkit-RUN_1-ncbi_genomes_T1

# 2. Edit the manifest with your species + NCBI accessions
vi toolkit-RUN_1-ncbi_genomes_T1/INPUT_user/ncbi_genomes_manifest.tsv

# 3. Edit config (needed if running on SLURM)
vi toolkit-RUN_1-ncbi_genomes_T1/START_HERE-user_config.yaml

# 4. Run
cd toolkit-RUN_1-ncbi_genomes_T1
bash RUN-workflow.sh
```

The full quick start is in [`toolkit-COPYME-ncbi_genomes_T1/README.md`](toolkit-COPYME-ncbi_genomes_T1/README.md).

## Toolkit / framework boundary

This toolkit lives in `research_notebook/research_ai/subproject-genomesDB/`
per §59 (the canonical home for GIGANTIC toolkits). GIGANTIC subprojects
do **not** read from `research_ai/` directly. Instead, this toolkit's
process 4 (`bridge_to_input_user`) creates **relative symlinks** from the
project-level `INPUT_user/genomic_resources/` staging arena (per §17,
§18) into this toolkit's outputs. That symlink bridge is the only
handoff between the toolkit and the framework.

Per §60: this toolkit is **permanent in this category** — it does not
become a subproject. The framework intentionally does not own its
inputs because the choice of genome assemblies, alt-loci policy,
GCA-vs-GCF handling, and so on varies too much across projects.

## See also

- [`toolkit-COPYME-ncbi_genomes_T1/README.md`](toolkit-COPYME-ncbi_genomes_T1/README.md) — user-facing quick start
- [`toolkit-COPYME-ncbi_genomes_T1/ai/AI_GUIDE.md`](toolkit-COPYME-ncbi_genomes_T1/ai/AI_GUIDE.md) — AI-facing operational details
- [`AI_GUIDE.md`](AI_GUIDE.md) — parent-dir AI guide
- §59 and §60 in `ai/ai_FYIs/gigantic_conventions.md` — toolkit category definition + framework-extension scope
