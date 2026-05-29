# AI_GUIDE — Gene Coordinates Extractor Toolkit

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (project root): [`../../../../`](../../../../)
- User-facing top-level README: [`README.md`](README.md)
- Template AI guide: [`toolkit-COPYME-gene_coordinates_extractor/ai/AI_GUIDE.md`](toolkit-COPYME-gene_coordinates_extractor/ai/AI_GUIDE.md)
- Downstream consumer: `subprojects/hotspots/BLOCK_identify_hotspots/`

---

## What this toolkit does

Produces the per-species `<Genus_species>-gene_coordinates.tsv` files that the **hotspots** subproject's `BLOCK_identify_hotspots` workflow expects as input. The TSV schema is fixed (5 columns: `Source_Gene_ID, Seqid, Gene_Start, Gene_End, Strand`) and matches the existing species70 convention.

## Why this is a research_notebook tool, not a framework subproject

GFF / GTF format varies too widely across sources (NCBI RefSeq vs GenBank, AUGUSTUS de-novo, BRAKER, custom-curated...) for the hotspots subproject to safely guess the right extraction logic for an arbitrary input. The framework therefore declares the per-species TSV a **user-side input**, and this toolkit is the canonical AI-built tool for producing that input from the GFF flavors present in this project (NCBI / AUGUSTUS / BRAKER).

If a future project includes a GFF/GTF flavor this extractor doesn't handle correctly, the right response is to **extend `001_ai-python-extract_gene_coordinates.py`** (or write a per-species pre-processor) and re-run — not to push extraction logic into the hotspots subproject.

## GFF flavors handled

1. **NCBI RefSeq / GenBank**
   - Feature type `gene` with a key=value attribute column
   - Source_Gene_ID resolution: prefer `gene=` attribute, then `ID=` (strip `gene-` prefix), then `Name=`
2. **AUGUSTUS** (e.g. Schizocardium)
   - Feature type `gene` with a bare column 9 (`g1`, `g2`, ...)
   - Source_Gene_ID = bare token
3. **BRAKER** (e.g. Mesocentrotus) — fallback path
   - No `gene` rows present; only `mRNA` / `transcript` rows
   - Source_Gene_ID derived from `Parent=` attribute or by stripping a trailing `.tN` from `ID=`
   - Coordinates per gene = `min(transcript_starts) .. max(transcript_ends)`

The `001` script auto-detects which path applies per file. The `002` validator rejects any per-species TSV with zero rows, malformed coordinates, or invalid strand values, so a silently-wrong extraction (e.g. an unrecognized flavor) hard-fails the whole pipeline.

## Process chain (ai/main.nf)

| # | Process | Script | Purpose |
|---|---|---|---|
| 1 | `extract_gene_coordinates` | `001_*.py` | Parse every GFF in `annotations_dir`; emit one TSV per species |
| 2 | `validate_outputs`         | `002_*.py` | Per-row schema + sanity checks; fail-fast on any row error or empty TSV |
| 3 | `bridge_to_hotspots`       | `003_*.py` | Symlink validated TSVs into the hotspots subproject's expected location |
| 4 | `write_run_log`            | `004_*.py` | GIGANTIC §45 final-step audit log to `ai/logs/` |

## Resource sizing

This is a CPU-cheap, IO-cheap workflow. Default `local` execution is recommended. SLURM is supported for consistency with other toolkits but adds queue latency that's usually larger than the compute itself.

| Tier | Defaults | Comment |
|---|---|---|
| local (process) | 2 cpus, 15 GB, 1 hr | Per the project RAM rule (CPUs × 7.5 GB) |
| SLURM (block)   | 2 cpus, 15 GB, 1 hr | Only used if `execution_mode: "slurm"` |

## Failure semantics

Every script exits with code 1 (fail-fast) on:
- Any species with zero rows extracted (script 001)
- Header mismatch, bad coordinates, or invalid strand (script 002)
- Inability to symlink a validated TSV into the target dir (script 003)

NextFlow's `errorStrategy = 'terminate'` and `maxErrors = 0` enforce strict halt-on-error.

## See also

- `README.md` — user-facing top-level overview
- `toolkit-COPYME-gene_coordinates_extractor/README.md` — template-level user-facing README
- `toolkit-COPYME-gene_coordinates_extractor/ai/AI_GUIDE.md` — workflow-level AI guide
- `subprojects/hotspots/BLOCK_identify_hotspots/AI_GUIDE.md` — downstream consumer
- `research_notebook/research_user/subproject-hotspots/gene_coordinates/` — where outputs land for hotspots
