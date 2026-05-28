<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 28
Human:   Eric Edsinger
Purpose: User-facing quick start for the NCBI Genomes T1 Toolkit. The
         canonical seed GIGANTIC toolkit per §59. Lives in
         research_notebook/research_ai/subproject-genomesDB/ and follows
         GIGANTIC framework conventions internally (§28, §29, §36, §45,
         §17/§18 staging).
Scope:   This toolkit-COPYME-ncbi_genomes_T1/ template and any
         toolkit-RUN_*-ncbi_genomes_T1/ run instances copied from it.
History:
  2026-05-28  Ground-up rebuild + relocation to research_ai/ per §59.
============================================================================ -->

# NCBI Genomes T1 Toolkit

Download NCBI RefSeq (and compatible) genome bundles, T1-extract protein
sequences (longest isoform per gene) with alternate-loci filtering, rename
to GIGANTIC convention, and auto-bridge into the project's
`INPUT_user/genomic_resources/` staging arena.

## Where this fits

This toolkit lives in `research_notebook/research_ai/subproject-genomesDB/`
(the canonical toolkit home per `ai/ai_FYIs/gigantic_conventions.md` §59)
and produces inputs that GIGANTIC's `genomesDB` subproject consumes via
`INPUT_user/genomic_resources/`.

- **Parent project**: [`../../../../`](../../../../) (the renamed `gigantic_project-*/` root)
- **Parent toolkit dir**: [`../`](../) — has the cross-RUN `output_to_input/`
- **Downstream consumer**: `subprojects/genomesDB/STEP_1-sources/` reads from
  `INPUT_user/genomic_resources/{proteomes,genomes,annotations}/`
- **Prerequisite**: `subprojects/phylonames/` should have run first (downstream
  STEP_2 needs the phylonames mapping to standardize file names + FASTA headers)

## Quick start

```bash
# 1. Copy the COPYME template into a RUN-instance dir
cd ..   # to the parent toolkit dir
cp -r toolkit-COPYME-ncbi_genomes_T1 toolkit-RUN_1-ncbi_genomes_T1

# 2. Edit the manifest with your species + NCBI accessions
cd toolkit-RUN_1-ncbi_genomes_T1
vi INPUT_user/ncbi_genomes_manifest.tsv

# 3. Edit configuration (only needed if running on SLURM)
vi START_HERE-user_config.yaml

# 4. Run
bash RUN-workflow.sh
```

`RUN-workflow.sh` is the unified entry point per `gigantic_conventions.md` §29.
It refuses to run from a `*COPYME*` directory; copy first, then run from the
RUN-instance.

## Manifest format

`INPUT_user/ncbi_genomes_manifest.tsv` — 2 tab-separated columns:

```
genus_species	accession
Homo_sapiens	GCF_000001405.40
Strongylocentrotus_purpuratus	GCF_000002235.5
Branchiostoma_floridae	GCF_000003815.2
```

- Lines starting with `#` are comments.
- The header row `genus_species` is skipped.
- **Designed for**: NCBI RefSeq (`GCF_*`) assemblies. Built and tested
  against the structure RefSeq guarantees (notably the `Dbxref=GeneID:`
  GFF3 attribute that the alt-loci filter keys on).
- **NCBI GenBank (`GCA_*`) — works often, but not guaranteed.** The
  toolkit will run on many GCAs that ship with `protein.faa` + GFF3,
  but the alt-loci filter becomes a **silent no-op** on GCAs because
  GenBank GFF3 lacks `Dbxref=GeneID:` attributes. The filter relies on
  GeneID grouping to detect primary-vs-alternate-haplotype duplicates;
  with no GeneID to group on, every protein passes through as if
  unique. For a GCA with no alt-haplotype duplicates this is correct
  behavior (matches gene_biotype=protein_coding 1:1). For a GCA that
  does have alt-haplotype duplicates, the toolkit would silently
  include them as separate proteins. **If you use GCAs**: evaluate
  each species's GFF3 against a comparable GCF for the same lineage,
  inspect the T1 output, and compare protein counts to
  `gene_biotype=protein_coding` from NCBI before trusting downstream
  use.
- **Non-NCBI sources (figshare / Zenodo / Dryad / lab websites)**:
  handle separately. See [`INPUT_user/README.md`](INPUT_user/README.md)
  "What to do for non-RefSeq sources".

## Configuration

Edit `START_HERE-user_config.yaml`:

| Key | Purpose | Common values |
|---|---|---|
| `toolkit.name` | Audit-log filename component | `"ncbi_genomes_T1_toolkit"` (default) |
| `toolkit.manifest_path` | Path to the manifest TSV | `"INPUT_user/ncbi_genomes_manifest.tsv"` (default) |
| `toolkit.download_date` | Date stamp embedded in output filenames | `"auto"` (today), or `"20260528"`, or `"downloaded_20260528"` |
| `execution_mode` | Where the NextFlow driver runs | `"local"` or `"slurm"` |
| `slurm_account` / `slurm_qos` | SLURM allocation (only when slurm) | e.g. `"moroz"` / `"moroz"` |
| `cpus`, `memory_gb`, `time_hours` | SLURM job resources | `4`, `16`, `6` (defaults) |
| `resume` | Use NextFlow `-resume` (re-use cached work) | `false` (default; explicit opt-in for reproducibility) |

## What it does

Five sequential NextFlow processes:

| # | Process | Reads | Writes |
|---|---|---|---|
| 1 | **download_ncbi_bundles** | manifest | `OUTPUT_pipeline/1-output/downloads/*.zip` |
| 2 | **unzip_organize_rename** | downloads zips | `OUTPUT_pipeline/2-output/{genome,gff3,protein}/Genus_species-ncbi_genomes.{fasta,gff3,faa}` |
| 3 | **extract_t1_with_alt_loci_filter** | step 2 outputs + manifest | `OUTPUT_pipeline/3-output/{T1_proteomes,genomes,gene_annotations,maps}/` — GIGANTIC-named, alt-loci-filtered, identifier maps |
| 4 | **bridge_to_input_user** | step 3 outputs | Two-hop relative symlinks: `../output_to_input/` then `INPUT_user/genomic_resources/` |
| 5 | **write_run_log** | everything above | `ai/logs/run_<timestamp>-<toolkit_name>_success.log` |

### Output file naming (GIGANTIC convention)

```
Genus_species-genome_ncbi_<ACCESSION>-downloaded_<YYYYMMDD>.{aa, fasta, gff3}

Example: Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20260528.aa
```

### FASTA proteome header format

```
>Genus_species-gene_id-transcript_id-protein_id

Example: >Homo_sapiens-LOC107984094-XM_016862692.2-XP_016862692.2
```

Identifiers are sanitized (dashes inside source IDs replaced with underscores)
so the dash positions are unambiguous.

## The alternate-loci filter (months-of-work fix from the RUN_2 lineage)

NCBI RefSeq assemblies for some species include alternate haplotype scaffolds
(NT_*) and unplaced contigs (NW_*) alongside the primary chromosomes (NC_*).
The same biological gene is annotated on multiple scaffolds, sharing one NCBI
`GeneID` but with different gene feature IDs (`gene-AAAS`, `gene-AAAS-2`,
`gene-AAAS-3`).

Without filtering, T1 extraction would treat each as an independent gene,
inflating the proteome. For *Homo sapiens* alone this affects 3,379 genes (~7%
inflation). Affected species in the original benchmark set: *Homo sapiens*
(3,379), *Hydra vulgaris* (47), *Aplysia californica* (25), *Caenorhabditis
elegans* (4); all other species are no-op.

Script 003 groups gene entries by `Dbxref=GeneID:` and keeps only the primary
(no `-N` suffix), or the lowest-numbered alternate if no primary exists.
The design rationale was developed over several iterations during a prior
demo session — the current script 003 carries that fix forward.

## Outputs

```
toolkit-RUN_N-ncbi_genomes_T1/
├── OUTPUT_pipeline/
│   ├── 1-output/downloads/                   # raw NCBI zips (kept for re-runs)
│   ├── 2-output/{genome,gff3,protein}/       # intermediate-named
│   ├── 3-output/                             # real GIGANTIC-named files
│   │   ├── T1_proteomes/Genus_species-genome_ncbi_<ACC>-downloaded_<DATE>.aa
│   │   ├── genomes/Genus_species-genome_ncbi_<ACC>-downloaded_<DATE>.fasta
│   │   ├── gene_annotations/Genus_species-genome_ncbi_<ACC>-downloaded_<DATE>.gff3
│   │   └── maps/
│   │       ├── ncbi_genomes-map-genome_identifiers.tsv
│   │       ├── ncbi_genomes-map-sequence_identifiers.tsv
│   │       └── ncbi_genomes-alternate_loci_log.tsv
│   ├── 4-output/bridge_done.marker
│   └── 5-output/run_log_written.marker
└── ai/logs/run_<timestamp>-ncbi_genomes_T1_toolkit_success.log

../output_to_input/{T1_proteomes,genomes,gene_annotations,maps}/   # parent (sandbox, stable)
    -> symlinks point at this RUN's 3-output/

../../../../../INPUT_user/genomic_resources/{proteomes,genomes,annotations}/   # GIGANTIC staging arena
    -> symlinks point at ../output_to_input/
```

## Failure modes worth knowing

- **GCA_* assemblies** that lack annotation/protein.faa → script 002 fails
  loudly per §36. (The toolkit is designed for `GCF_*` RefSeq; many GCAs
  work but support is best-effort — see the Manifest format section above
  for the GCF/GCA tier breakdown and the silent-no-op caveat for the
  alt-loci filter on GenBank assemblies.)
- **Network failures** during download → script 001 has retry+backoff (4
  attempts, 10s/20s/30s/40s) and zip integrity checks. Persistent failure
  → script exits non-zero (manifest count must equal download count).
- **Existing zip files** → script 001 verifies integrity and skips
  re-downloading. Idempotent re-runs are safe.
- **Stale NextFlow cache** can cause confusing partial results. If a re-run
  behaves unexpectedly:
  ```bash
  rm -rf work .nextflow .nextflow.log*
  ```
  then re-run without `resume: true`.

## See also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — AI-facing operational details
- [`INPUT_user/ncbi_genomes_manifest.tsv`](INPUT_user/ncbi_genomes_manifest.tsv) — manifest template
- [`../README.md`](../README.md) — parent toolkit dir overview
- [`../../../../../subprojects/genomesDB/`](../../../../../subprojects/genomesDB/) — downstream consumer
