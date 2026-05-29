# toolkit-COPYME-gene_coordinates_extractor

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent toolkit overview: [`../README.md`](../README.md)
- Parent toolkit AI guide: [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This template's workflow AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Downstream consumer: `subprojects/hotspots/BLOCK_identify_hotspots/`

---

Extracts per-species gene-coordinate TSVs (`<Genus_species>-gene_coordinates.tsv`) from GFF3 annotation files for the hotspots subproject. Produces the canonical 5-column schema (`Source_Gene_ID, Seqid, Gene_Start, Gene_End, Strand`) matching the existing species70 convention.

## Why this is a user-side tool

GFF / GTF format varies too widely across sources (NCBI RefSeq, GenBank, AUGUSTUS, BRAKER, custom-curated, ...) for the hotspots subproject to safely guess extraction logic. The hotspots framework deliberately declares per-species gene-coordinate TSVs a USER responsibility — this toolkit fulfills that responsibility for the GFF flavors present in this project.

## Prerequisites

- A directory of GFF3 annotation files following the genomesDB STEP_4 filename convention `<phyloname>-genome.gff3` (default points at `subprojects/genomesDB/output_to_input/STEP_4-create_final_species_set/species42_gigantic_genome_annotations/`)
- A target directory for the bridged outputs (default: `research_notebook/research_user/subproject-hotspots/gene_coordinates/`)
- `aiG-research_ai-gene_coordinates_extractor` conda environment (auto-created on first run from `ai/conda_environment.yml`)

`RUN-workflow.sh` activates and deactivates the conda env automatically.

## Usage

```bash
# Instantiate
cp -r toolkit-COPYME-gene_coordinates_extractor toolkit-RUN_1-gene_coordinates_extractor
cd toolkit-RUN_1-gene_coordinates_extractor

# Verify paths
$EDITOR START_HERE-user_config.yaml

# Run
bash RUN-workflow.sh
```

## Pipeline

4 steps:

1. **Extract** — parse every GFF3, emit one TSV per species (handles NCBI / AUGUSTUS / BRAKER flavors automatically; fail-fast on zero rows)
2. **Validate** — per-row schema + sanity checks
3. **Bridge** — symlink TSVs into the hotspots subproject's expected input location
4. **Run-log** — GIGANTIC §45 audit log

See [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for the detailed execution guide, flavor-detection logic, and failure semantics.
