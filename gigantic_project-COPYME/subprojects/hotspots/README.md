# hotspots — Paralog Cluster (Hotspot) Identification

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from:
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` — proteomes (for both BLOCKs)
  - `../../research_notebook/research_user/subproject-hotspots/gene_coordinates/` — user-provided per-species gene coordinate TSVs (per §1 consolidation; see §17 deviation note in BLOCK_identify_hotspots AI guide)
- Internal dependency chain: BLOCK_self_blast → BLOCK_identify_hotspots
- Outputs to (`output_to_input/`):
  - `BLOCK_self_blast/self_blast_reports/` — per-species self-BLAST tabular reports
  - `BLOCK_identify_hotspots/` — per-species hotspot tables + cross-species summary
- Downstream consumers:
  - `upload_to_server/` — curated hotspot tables for the GIGANTIC server
  - Comparative analyses (paralog cluster size by species, conservation of hotspots)

---

## Purpose

Identify **hotspots** — chromosomal clusters of paralogous gene copies — in
every project species, per the method from Edsinger 2024
(*Frontiers in Marine Science*, doi:10.3389/fmars.2024.1434130).

Pipeline (two sequential BLOCKs):

1. **BLOCK_self_blast** — blastp each species' proteome against itself.
   Chunked + burst-parallelized; ~3,500 fan-out tasks for species70.
2. **BLOCK_identify_hotspots** — per-species hotspot calling from self-BLAST
   reports + user-provided gene coordinates. Filters by stringent e-value,
   checks for paralogs within a chromosomal window, builds a paralog graph,
   and identifies connected components as hotspots.

## Method (BLOCK_identify_hotspots)

1. Filter self-BLAST hits by stringent e-value (default 1e-60)
2. For each retained hit, check whether query + subject sit within a
   window of N gene-positions on the same chromosome (default 20 genes
   total — ±10 around query)
3. Build a paralog graph: nodes = genes, edges = (query, subject) pairs
   that satisfy step 2
4. Connected components of the graph = hotspots

## Prerequisites

- **genomesDB** complete (proteomes for both BLOCKs)
- Per-species gene-coordinate TSVs at
  `../../research_notebook/research_user/subproject-hotspots/gene_coordinates/`
  (user produces these from species-specific GFF/GTF — same TSV schema as
  `gene_sizes` Tier 2 / Tier 1, see gene_sizes README for column spec)
- Conda env `aiG-hotspots` auto-created on first run (shared by both
  BLOCKs per §53 short-form tolerance — both BLOCKs use the same
  Python dependencies)

## Architecture

```
hotspots/
├── README.md                                            # this file
├── AI_GUIDE.md
├── RUN-update_upload_to_server.sh                       # publisher (one per subproject per §38)
├── upload_to_server/
├── output_to_input/
│   ├── BLOCK_self_blast/self_blast_reports/             # per-species tab reports
│   └── BLOCK_identify_hotspots/                         # per-species hotspot tables
│
├── BLOCK_self_blast/                                    # 5 scripts incl. write_run_log
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-self_blast/                      # chunked + burst-parallelized
│       └── (RUN-workflow.sh + START_HERE-user_config.yaml + ai/)
│
└── BLOCK_identify_hotspots/                             # 5 scripts incl. write_run_log
    ├── AI_GUIDE.md
    └── workflow-COPYME-identify_hotspots/               # per-species fan-out
        └── (RUN-workflow.sh + START_HERE-user_config.yaml + ai/)
```

(No per-subproject `research_notebook/` — per §1, sandbox content lives at
`../../research_notebook/research_user/subproject-hotspots/`. Migration
done 2026-05-26.)

## Quick Start (run BLOCKs in order)

```bash
# 1. BLOCK_self_blast (slow; chunks + burst-fans-out)
cd BLOCK_self_blast
cp -r workflow-COPYME-self_blast workflow-RUN_1-self_blast
cd workflow-RUN_1-self_blast
vi START_HERE-user_config.yaml   # set execution_mode (slurm_burst recommended)
bash RUN-workflow.sh

# 2. After BLOCK_self_blast completes, BLOCK_identify_hotspots
cd ../../BLOCK_identify_hotspots
cp -r workflow-COPYME-identify_hotspots workflow-RUN_1-identify_hotspots
cd workflow-RUN_1-identify_hotspots
vi START_HERE-user_config.yaml   # verify gene_coordinates_dir path
bash RUN-workflow.sh
```

## Reference

Edsinger E (2024). *Front. Mar. Sci.* — hotspot methodology.
doi:10.3389/fmars.2024.1434130

## See Also

- [`AI_GUIDE.md`](AI_GUIDE.md) — Level 2 AI guide with troubleshooting
- `BLOCK_self_blast/AI_GUIDE.md`
- `BLOCK_identify_hotspots/AI_GUIDE.md`
