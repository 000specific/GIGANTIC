# annotations_hmms - Proteome Functional Annotation Database

**AI**: Claude Code | Opus 4.6 | 2026 March 03
**Human**: Eric Edsinger

---

## Purpose

Build a comprehensive functional annotation database for all species proteomes using five independent annotation tools. Each tool predicts different functional properties (protein domains, subcellular localization, signal peptides, transmembrane topology, intrinsic disorder), and their results are parsed into a standardized 7-column database format for downstream analyses.

---

## Architecture

Six independent, self-contained projects:

| Project | Tool | What It Predicts |
|---------|------|-----------------|
| `BLOCK_interproscan/` | InterProScan 5 | Protein domains, families, GO terms (19 component databases) |
| `BLOCK_deeploc/` | DeepLoc 2.1 | Subcellular localization (GPU) |
| `BLOCK_signalp/` | SignalP 6 | Signal peptides and cleavage sites |
| `BLOCK_tmbed/` | tmbed | Transmembrane topology (GPU) |
| `BLOCK_metapredict/` | MetaPredict | Intrinsic disorder regions |
| `BLOCK_build_annotation_database/` | Integration | Parses all tool outputs into standardized database, statistics, analyses |

BLOCKs 1-5 are independent (run in any order, any subset). BLOCK 6 auto-discovers which tool outputs are available and builds the database from whatever is present.

---

## Prerequisites

1. **genomesDB complete**: Proteomes in `genomesDB/output_to_input/gigantic_proteomes/`
2. **Conda environments**: One per tool (see Quick Start)
3. **Nextflow**: `module load nextflow`
4. **Tool installations**: InterProScan (standalone), DeepLoc (DTU license), SignalP (DTU license)

---

## Quick Start

```bash
# 1. Copy a tool workflow template for your run
cp -r BLOCK_interproscan/workflow-COPYME-run_interproscan BLOCK_interproscan/workflow-RUN_01-run_interproscan
cd BLOCK_interproscan/workflow-RUN_01-run_interproscan/

# 2. Edit configuration
vi interproscan_config.yaml

# 3. Run (conda environment is activated automatically by the script)
bash RUN-workflow.sh       # Local
sbatch RUN-workflow.sbatch # SLURM (edit account/qos first)
```

Same pattern for all 6 BLOCKs. Run tool BLOCKs first, then BLOCK_build_annotation_database.

**Note:** Each `RUN-workflow.sh` automatically activates and deactivates its own conda environment. No manual activation required.

---

## Standardized Database Format

All tool outputs are parsed into a common 7-column TSV format:

| Column | Description |
|--------|-------------|
| `Phyloname` | GIGANTIC phylogenetic name |
| `Sequence_Identifier` | Protein sequence identifier |
| `Domain_Start` | Start coordinate (NA for whole-protein predictions) |
| `Domain_Stop` | Stop coordinate (NA for whole-protein predictions) |
| `Database_Name` | Source database (e.g., pfam, deeploc, signalp) |
| `Annotation_Identifier` | Annotation ID (e.g., PF00001, SP, TM) |
| `Annotation_Details` | Human-readable description |

24 database subdirectories are produced: pfam, gene3d, superfamily, smart, panther, cdd, prints, prositepatterns, prositeprofiles, hamap, sfld, funfam, ncbifam, pirsf, coils, mobidblite, antifam, interproscan, go, deeploc, signalp, tmbed, metapredict.

---

## Directory Structure

```
annotations_hmms/
├── README.md                                # This file
├── AI_GUIDE-annotations_hmms.md             # AI assistant guide (Level 2)
├── upload_to_server/
├── RUN-clean_and_record_subproject.sh
├── RUN-update_upload_to_server.sh
│
├── output_to_input/                         # Consolidated outputs for downstream
│   ├── BLOCK_interproscan/                  #   InterProScan results (symlinked)
│   ├── BLOCK_deeploc/                       #   DeepLoc results (symlinked)
│   ├── BLOCK_signalp/                       #   SignalP results (symlinked)
│   ├── BLOCK_tmbed/                         #   tmbed results (symlinked)
│   ├── BLOCK_metapredict/                   #   MetaPredict results (symlinked)
│   └── BLOCK_build_annotation_database/     #   Integrated database (symlinked)
│
├── BLOCK_interproscan/                      # InterProScan (4 scripts)
│   ├── AI_GUIDE-interproscan.md
│   └── workflow-COPYME-run_interproscan/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── interproscan_config.yaml
│
├── BLOCK_deeploc/                           # DeepLoc (2 scripts)
│   ├── AI_GUIDE-deeploc.md
│   └── workflow-COPYME-run_deeploc/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── deeploc_config.yaml
│
├── BLOCK_signalp/                           # SignalP (2 scripts)
│   ├── AI_GUIDE-signalp.md
│   └── workflow-COPYME-run_signalp/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── signalp_config.yaml
│
├── BLOCK_tmbed/                             # tmbed (2 scripts)
│   ├── AI_GUIDE-tmbed.md
│   └── workflow-COPYME-run_tmbed/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── tmbed_config.yaml
│
├── BLOCK_metapredict/                       # MetaPredict (2 scripts)
│   ├── AI_GUIDE-metapredict.md
│   └── workflow-COPYME-run_metapredict/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── metapredict_config.yaml
│
└── BLOCK_build_annotation_database/         # Database builder (16 scripts)
    ├── AI_GUIDE-build_annotation_database.md
    └── workflow-COPYME-build_annotation_database/
        ├── ai/ (main.nf, nextflow.config, scripts/)
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        └── annotation_database_config.yaml
```

---

## See Also

- `AI_GUIDE-annotations_hmms.md` - AI assistant guidance
- `BLOCK_{tool}/AI_GUIDE-{tool}.md` - Tool-specific AI guides
