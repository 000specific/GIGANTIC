# Gene Coordinates Extractor Toolkit

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
Purpose: Top-level README for the Gene Coordinates Extractor toolkit. Lives
         in research_notebook/research_ai/ because GFF/GTF variability is a
         USER responsibility, not a GIGANTIC framework guarantee.
============================================================================ -->

## What this toolkit does

Extracts per-species **gene-coordinate TSVs** from GFF3 annotation files for downstream consumption by the **hotspots** subproject (`BLOCK_identify_hotspots`).

Output schema (5 columns; matches the existing species70 convention):

| Column | Description |
|---|---|
| `Source_Gene_ID` | Gene identifier that matches the `g_<…>` field in GIGANTIC proteome headers |
| `Seqid` | Chromosome / scaffold ID (GFF column 1) |
| `Gene_Start` | 1-based inclusive start (GFF column 4) |
| `Gene_End` | 1-based inclusive end (GFF column 5) |
| `Strand` | `+` or `-` (GFF column 7) |

One TSV per species, named `<Genus_species>-gene_coordinates.tsv`. Symlinked into the hotspots subproject's expected input location after each run.

## Why this lives OUTSIDE the hotspots subproject

GFF and GTF formats vary widely across genome annotation sources — NCBI RefSeq, NCBI GenBank, AUGUSTUS de-novo predictions, BRAKER, custom-curated, etc. — and the right way to derive a per-gene coordinate row from a GFF differs case by case (which feature type to use, how to extract the gene ID from column 9, how to collapse multiple transcripts into one gene, etc.).

The hotspots subproject deliberately does **not** attempt extraction itself. Producing the per-species TSVs is a **user responsibility**. This toolkit is the canonical GIGANTIC tool for fulfilling that responsibility for the three GFF flavors used in this project (NCBI / AUGUSTUS / BRAKER). Users with other GFF/GTF flavors may need to extend `001_ai-python-extract_gene_coordinates.py` or build their own extractor following the same 5-column output schema.

## Where this fits

- **Parent project**: [`../../../../`](../../../../)
- **Downstream consumer**: `subprojects/hotspots/BLOCK_identify_hotspots/` reads from `research_notebook/research_user/subproject-hotspots/gene_coordinates/`
- **Sibling research_ai tool**: [`../../subproject-trees_species/generate_species_tree.py`](../../subproject-trees_species/generate_species_tree.py) — phylonames → binary Newick (similar role: AI-built tool that lives in research_ai because it's research-tooling rather than framework-canonical)

## Layout

```
gene_coordinates_extractor-toolkit/
├── README.md                                       (this file — top-level overview)
├── AI_GUIDE.md                                     (AI-deep guide for the toolkit)
├── output_to_input/
│   └── gene_coordinates/                           (placeholder; per-run output_to_input symlinks live in each RUN dir)
├── toolkit-COPYME-gene_coordinates_extractor/      (template; copy to instantiate a run)
│   ├── README.md
│   ├── RUN-workflow.sh
│   ├── START_HERE-user_config.yaml
│   ├── INPUT_user/
│   │   └── README.md
│   └── ai/
│       ├── AI_GUIDE.md
│       ├── main.nf
│       ├── nextflow.config
│       ├── conda_environment.yml
│       ├── logs/
│       └── scripts/
│           ├── 001_ai-python-extract_gene_coordinates.py
│           ├── 002_ai-python-validate_outputs.py
│           ├── 003_ai-python-bridge_to_hotspots.py
│           └── 004_ai-python-write_run_log.py
└── toolkit-RUN_<N>-gene_coordinates_extractor/     (each user-instantiated run lives here)
```

## Usage

```bash
# 1. Instantiate
cp -r toolkit-COPYME-gene_coordinates_extractor toolkit-RUN_1-gene_coordinates_extractor
cd toolkit-RUN_1-gene_coordinates_extractor

# 2. Verify paths in START_HERE-user_config.yaml
#    (defaults point at species42 genomesDB STEP_4 output + the
#    research_user/subproject-hotspots/gene_coordinates target dir).

# 3. Run
bash RUN-workflow.sh
```

End-to-end runtime on a clean compute node: a few seconds to a couple minutes for ~40 species (all stdlib Python, no third-party parsers).

## See also

- `toolkit-COPYME-gene_coordinates_extractor/README.md` — user-facing template README
- `toolkit-COPYME-gene_coordinates_extractor/ai/AI_GUIDE.md` — workflow-level AI guide
- `subprojects/hotspots/BLOCK_identify_hotspots/` — the canonical consumer of the per-species TSVs
