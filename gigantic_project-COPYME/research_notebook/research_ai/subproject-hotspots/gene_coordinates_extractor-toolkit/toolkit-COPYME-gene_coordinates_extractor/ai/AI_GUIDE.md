# AI Guide — Gene Coordinates Extractor (workflow layer)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent template README: [`../README.md`](../README.md)
- Parent toolkit AI guide:  [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Top-level toolkit README: [`../../README.md`](../../README.md)

---

## What this workflow does

Produces `<Genus_species>-gene_coordinates.tsv` files (5-col schema) from GFF3 annotation files, then symlinks them into the location `subprojects/hotspots/BLOCK_identify_hotspots/` reads from.

## Inputs

| YAML key | Default | Description |
|---|---|---|
| `inputs.annotations_dir` | `../../.../species42_gigantic_genome_annotations` | Directory of `<phyloname>-genome.gff3` files |
| `inputs.hotspots_gene_coordinates_dir` | `../../../../research_user/subproject-hotspots/gene_coordinates` | Where bridge step (script 003) symlinks the validated TSVs |
| `inputs.species_whitelist` | `""` | Optional comma-separated `Genus_species` filter |
| `output.base_dir` | `OUTPUT_pipeline` | NextFlow publishDir root |
| `project.name` | `gigantic_project` | Recorded in the §45 run log |

## Outputs

```
OUTPUT_pipeline/
├── 1-output/                                          (extract)
│   ├── <Genus_species>-gene_coordinates.tsv           (× N species)
│   └── 1_ai-log-extract_gene_coordinates.log
├── 2-output/                                          (validate)
│   ├── 2_ai-validation_summary.tsv
│   └── 2_ai-log-validate_outputs.log
└── 3-output/                                          (bridge)
    └── 3_ai-log-bridge_to_hotspots.log

ai/logs/run_<timestamp>-subproject-hotspots_success.log  (§45 run log)
```

After a successful run, each `<hotspots_gene_coordinates_dir>/<Genus_species>-gene_coordinates.tsv` is an absolute symlink to the real file in `OUTPUT_pipeline/1-output/`.

## Process chain

| Process | Script | Inputs | Outputs |
|---|---|---|---|
| `extract_gene_coordinates` | `001_*.py` | `params.annotations_dir`, `params.species_whitelist` | `1-output/*.tsv` + log |
| `validate_outputs`         | `002_*.py` | `1-output/` | `2-output/2_ai-validation_summary.tsv` + log |
| `bridge_to_hotspots`       | `003_*.py` | `1-output/`, `params.hotspots_gene_coordinates_dir` | symlinks in target dir + `3-output/` log |
| `write_run_log`            | `004_*.py` | gate from bridge | `ai/logs/run_<timestamp>-*.log` |

## GFF flavor handling (script 001)

1. **NCBI RefSeq / GenBank** — feature type `gene`, key=value attributes; Source_Gene_ID resolved from `gene=` ⟶ `ID=` (strip `gene-`) ⟶ `Name=`.
2. **AUGUSTUS** — feature type `gene`, bare attribute column (e.g. `g1`); Source_Gene_ID = bare token.
3. **BRAKER fallback** — no `gene` rows; `mRNA` / `transcript` rows grouped by `Parent=` (preferred) or by stripping `.tN` from `ID=`. Per-gene coordinates use `min(starts) .. max(ends)`.

The extractor auto-detects which path applies per file. A species producing zero rows hard-fails the whole pipeline (script 002 will also reject any empty TSV, so a silently-wrong flavor detection cannot pass).

## Failure semantics

- Script 001: zero rows for any species → exit 1
- Script 002: any per-row validation error → exit 1
- Script 003: any symlink failure → exit 1
- NextFlow: `errorStrategy = 'terminate'`, `maxErrors = 0`

## Configuring

Edit `../START_HERE-user_config.yaml`. The two paths are the only typical edits; defaults work for the species42 demo project as-is.

## See also

- `../README.md`           — template-level user-facing README
- `../../AI_GUIDE.md`      — toolkit-level AI guide
- `subprojects/hotspots/BLOCK_identify_hotspots/AI_GUIDE.md` — downstream consumer
