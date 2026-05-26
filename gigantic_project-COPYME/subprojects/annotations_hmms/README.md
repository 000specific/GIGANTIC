# annotations_hmms - Proteome Functional Annotation Database

**AI**: Claude Code | Opus 4.6 | 2026 March 03
**Human**: Eric Edsinger

---

## Purpose

Build a comprehensive functional annotation database for all species proteomes using four independent annotation tools. Each tool predicts different functional properties (protein domains, subcellular localization + membrane topology, signal peptides, intrinsic disorder), and their results are parsed into a standardized 7-column database format for downstream analyses.

---

## Architecture

Five independent, self-contained projects:

| Project | Tool | What It Predicts |
|---------|------|-----------------|
| `BLOCK_interproscan/` | InterProScan 5 | Protein domains, families, GO terms (19 component databases) |
| `BLOCK_deeploc/` | DeepLoc 2.1 | Subcellular localization + TM/lipid/peripheral/soluble probabilities (GPU) |
| `BLOCK_signalp/` | SignalP 6 | Signal peptides and cleavage sites |
| `BLOCK_metapredict/` | MetaPredict | Intrinsic disorder regions |
| `BLOCK_build_annotation_database/` | Integration | Parses all tool outputs into standardized database, statistics, analyses |

BLOCKs 1-4 are independent (run in any order, any subset). BLOCK 5 auto-discovers which tool outputs are available and builds the database from whatever is present.

> **Note on transmembrane topology**: DeepLoc 2 reports per-protein TM / lipid-anchor / peripheral / soluble probabilities, so a dedicated TM-topology BLOCK is not separately included.

---

## Prerequisites

1. **genomesDB complete**: Proteomes in `genomesDB/output_to_input/gigantic_proteomes/`
2. **Conda environments**: One per tool (see Quick Start)
3. **Nextflow**: `module load nextflow`
4. **Tool installations**: InterProScan (standalone, in `BLOCK_interproscan/software/`), DeepLoc 2.1 (DTU license, in `BLOCK_deeploc/software/`), SignalP (DTU license)

---

## Quick Start

```bash
# 1. Copy a tool workflow template for your run
cp -r BLOCK_interproscan/workflow-COPYME-run_interproscan BLOCK_interproscan/workflow-RUN_01-run_interproscan
cd BLOCK_interproscan/workflow-RUN_01-run_interproscan/

# 2. Edit configuration
vi START_HERE-user_config.yaml

# 3. Run (conda environment is activated automatically by the script)
bash RUN-workflow.sh       # unified entry point; self-submits to SLURM
                           # if execution_mode in the YAML is "slurm" or
                           # "slurm_burst" (set in START_HERE-user_config.yaml).
```

Same pattern for all 5 BLOCKs. Run tool BLOCKs first, then BLOCK_build_annotation_database.

**Note:** Each `RUN-workflow.sh` automatically activates and deactivates its own conda environment. No manual activation required. The legacy `RUN-workflow.sbatch` is deprecated — use `RUN-workflow.sh` with `execution_mode` set in the YAML.

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

23 database subdirectories are produced: pfam, gene3d, superfamily, smart, panther, cdd, prints, prositepatterns, prositeprofiles, hamap, sfld, funfam, ncbifam, pirsf, coils, mobidblite, antifam, interproscan, go, deeploc, signalp, metapredict.

---

## Directory Structure

```
annotations_hmms/
├── README.md                                # This file
├── AI_GUIDE-annotations_hmms.md             # AI assistant guide (Level 2)
├── upload_to_server/
├── RUN-update_upload_to_server.sh
│
├── output_to_input/                         # Consolidated outputs for downstream
│   ├── BLOCK_interproscan/                  #   InterProScan results (symlinked)
│   ├── BLOCK_deeploc/                       #   DeepLoc results (symlinked)
│   ├── BLOCK_signalp/                       #   SignalP results (symlinked)
│   ├── BLOCK_metapredict/                   #   MetaPredict results (symlinked)
│   └── BLOCK_build_annotation_database/     #   Integrated database (symlinked)
│
├── BLOCK_interproscan/                      # InterProScan (4 scripts)
│   ├── AI_GUIDE-interproscan.md
│   └── workflow-COPYME-run_interproscan/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── START_HERE-user_config.yaml
│
├── BLOCK_deeploc/                           # DeepLoc (2 scripts)
│   ├── AI_GUIDE-deeploc.md
│   └── workflow-COPYME-run_deeploc/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── START_HERE-user_config.yaml
│
├── BLOCK_signalp/                           # SignalP (2 scripts)
│   ├── AI_GUIDE-signalp.md
│   └── workflow-COPYME-run_signalp/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── START_HERE-user_config.yaml
│
├── BLOCK_metapredict/                       # MetaPredict (2 scripts)
│   ├── AI_GUIDE-metapredict.md
│   └── workflow-COPYME-run_metapredict/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── START_HERE-user_config.yaml
│
└── BLOCK_build_annotation_database/         # Database builder (15 scripts)
    ├── AI_GUIDE-build_annotation_database.md
    └── workflow-COPYME-build_annotation_database/
        ├── ai/ (main.nf, nextflow.config, scripts/)
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        └── START_HERE-user_config.yaml
```

---

## Cluster-Side Failure Pattern: Drain-Node Race (HiPerGator post-upgrade)

Since the HiPerGator OS/SLURM upgrade (~May 2026), a small fraction of burst-submitted chunk jobs die in 0-1 sec with `ExitCode 0:53` (SIGRTMIN+19) and `Reason=ReqNodeNotAvail` — the SLURM scheduler allocates jobs to nodes that have already begun their DRAIN transition (most commonly observed on `c0706a-s7`, `c0706a-s9`, `c0706a-s10`, `c0706a-s12`). The chunk has no `.command.log` because bash never started.

This is **not a workflow bug** — it is a cluster-side scheduler bug. The empirical hit rate on high-volume burst runs is roughly 1-3% of submissions.

**Canonical handling pattern (implemented in BLOCK_interproscan, reference for other chunked workflows):**

1. `errorStrategy = 'ignore'` on the chunked process — failed chunks are silently dropped instead of killing the pipeline. This is an **explicit, documented override** of the project CLAUDE.md default ("NEVER use 'ignore'"), justified by this known cluster-side failure mode.
2. A gap-detection step (`detect_failed_chunks`, script 006) compares expected chunks (publishDir 2-output) against successful chunks (publishDir 3-output) and writes `6_ai-failed_chunks.tsv` listing what to rerun.
3. User drives a follow-up RUN_N targeting just the failed chunks.

See [BLOCK_interproscan/AI_GUIDE-interproscan.md](BLOCK_interproscan/AI_GUIDE-interproscan.md) for full details.

---

## See Also

- `AI_GUIDE-annotations_hmms.md` - AI assistant guidance
- `BLOCK_{tool}/AI_GUIDE-{tool}.md` - Tool-specific AI guides
