# homolog_counts — Cross-Subproject Homolog Counts per species70

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 22 (initial scripts; in commit 8486969 sweep)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial README)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from:
  - `../orthogroups/output_to_input/BLOCK_orthohmm/` — orthogroup IDs
  - `../trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/` — gene group names
  - `../trees_gene_families/output_to_input/` — gene family names
  - species70 phyloname map (from genomesDB / phylonames)
- Outputs to: `output_to_input/BLOCK_homolog_counts/` — one wide TSV per source (Feature_ID × 70 species columns)
- Downstream consumers:
  - GIGANTIC server (`upload_to_server/`) — counts hosted for web access
  - Comparative-analysis pipelines that need per-species homolog tallies

---

## Purpose

Counts homologs per species70 species across multiple upstream GIGANTIC
subprojects, producing one wide TSV per source. Each TSV is keyed on a
source-specific feature group (orthogroup, gene group, or gene family)
with counts per species70 species.

Three count axes are produced (one TSV each):

| Source | Feature_ID unit | Count meaning |
|--------|-----------------|---------------|
| OrthoHMM orthogroups | orthogroup ID | # of OrthoHMM-assigned proteins per species per OG |
| HGNC gene groups (hugo_hgnc) | gene group name | # of homologs per species per HGNC group |
| Curated gene families | gene family name | # of homologs per species per family |

`one_direction_homologs` is intentionally excluded — its feature axis is
per-query NCBI top hits, which doesn't map cleanly to "homolog group × species"
counts.

## Output Schema

Each counting script writes ONE wide TSV (73 columns total):

| # | Column | Description |
|---|--------|-------------|
| 1 | `Feature_ID (...)` | Source-specific group identifier |
| 2 | `Total_Count (...)` | Sum across all 70 species |
| 3 | `Total_Species_Count (...)` | Number of species with count ≥1 |
| 4–73 | per-species counts | 70 columns, ordered alphabetically by phyloname |

The 70-species column order is derived ONCE by script 001 from
`species70_map-genus_species_X_phylonames.tsv` (sorted by phyloname, not
genus_species) so it's identical across all three source TSVs.

Headers follow the self-documenting convention:
`Header_ID (description with spaces)`.

## Prerequisites

- **orthogroups** subproject complete (BLOCK_orthohmm)
- **trees_gene_groups** subproject complete (gene_groups-hugo_hgnc instance)
- **trees_gene_families** subproject complete
- **species70 phyloname map** available (from genomesDB / phylonames)
- Conda env auto-created on first run from `BLOCK_homolog_counts/workflow-COPYME-homolog_counts/ai/conda_environment.yml`

## Architecture

Single BLOCK (independently runnable; no internal sequencing). Each
counting script is independent — only script 001 (manifest validation)
must run first to produce the canonical species70 column order shared
across all count TSVs.

```
homolog_counts/
├── README.md                                    # this file
├── AI_GUIDE.md                                  # Level 2 AI guide
├── RUN-update_upload_to_server.sh               # publisher (one per subproject per §38)
├── upload_to_server/                            # curated count TSVs + per-run log for server
├── output_to_input/BLOCK_homolog_counts/        # workflow outputs (symlinked)
└── BLOCK_homolog_counts/
    └── workflow-COPYME-homolog_counts/          # single template
        ├── INPUT_user/
        ├── START_HERE-user_config.yaml          # execution_mode + paths to upstream subprojects
        ├── RUN-workflow.sh                      # single entry per §29
        └── ai/                                  # main.nf, nextflow.config, scripts, conda_environment.yml
```

(No per-subproject `research_notebook/`.)

## Quick Start

```bash
cd BLOCK_homolog_counts
cp -r workflow-COPYME-homolog_counts workflow-RUN_1-homolog_counts
cd workflow-RUN_1-homolog_counts

# Edit: execution_mode + paths to ../orthogroups/, ../trees_gene_groups/, ../trees_gene_families/
vi START_HERE-user_config.yaml

# Run (auto-creates conda env on first run)
bash RUN-workflow.sh
```

## See Also

- [`AI_GUIDE.md`](AI_GUIDE.md) — Level 2 AI guide (subproject concepts, schema, server-hosting notes)
- [`BLOCK_homolog_counts/workflow-COPYME-homolog_counts/README.md`](BLOCK_homolog_counts/workflow-COPYME-homolog_counts/README.md) — workflow-level quick start
- [`BLOCK_homolog_counts/workflow-COPYME-homolog_counts/ai/AI_GUIDE.md`](BLOCK_homolog_counts/workflow-COPYME-homolog_counts/ai/AI_GUIDE.md) — workflow execution guide
