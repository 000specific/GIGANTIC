# AI_GUIDE-annotations_hmms.md (Level 2: Subproject Guide)

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers annotations_hmms-specific concepts and structure.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| Annotations subproject concepts | This file |
| InterProScan details | `BLOCK_interproscan/AI_GUIDE-interproscan.md` |
| DeepLoc details | `BLOCK_deeploc/AI_GUIDE-deeploc.md` |
| SignalP details | `BLOCK_signalp/AI_GUIDE-signalp.md` |
| tmbed details | `BLOCK_tmbed/AI_GUIDE-tmbed.md` |
| MetaPredict details | `BLOCK_metapredict/AI_GUIDE-metapredict.md` |
| Database builder details | `BLOCK_build_annotation_database/AI_GUIDE-build_annotation_database.md` |
| Running a specific workflow | `BLOCK_{tool}/workflow-COPYME-run_{tool}/ai/AI_GUIDE-{tool}_workflow.md` |

---

## Purpose

The annotations_hmms subproject runs five independent annotation tools on species proteomes and builds a standardized annotation database from their outputs. This database provides functional characterization of every protein across all species, enabling downstream comparative analyses.

## Architecture

Six independent, self-contained projects using the flat BLOCK pattern (same as orthogroups):

```
annotations_hmms/
├── BLOCK_interproscan/              # InterProScan 5 (19 component databases + GO)
├── BLOCK_deeploc/                   # DeepLoc 2.1 (subcellular localization, GPU)
├── BLOCK_signalp/                   # SignalP 6 (signal peptides)
├── BLOCK_tmbed/                     # tmbed (transmembrane topology, GPU)
├── BLOCK_metapredict/               # MetaPredict (intrinsic disorder)
└── BLOCK_build_annotation_database/ # Integration: parse, database, statistics, analyses
```

BLOCKs 1-5 are independent (run in any order or subset). BLOCK 6 depends on outputs from BLOCKs 1-5 and auto-discovers which are available.

**Design principle**: Adding a new annotation tool = create a new BLOCK with validate + run scripts. The database builder auto-discovers new tool outputs without modification.

---

## Tool Comparison

| Feature | InterProScan | DeepLoc | SignalP | tmbed | MetaPredict |
|---------|-------------|---------|---------|-------|-------------|
| **Predicts** | Domains, families, GO | Subcellular location | Signal peptides | TM topology | Disorder regions |
| **Method** | 19 HMM/pattern databases | Deep learning | Deep learning | Protein language model | Deep learning |
| **Compute** | CPU-heavy | GPU | CPU | GPU | CPU-light |
| **Output per protein** | Multiple domains | One location | Signal/No signal | Topology string | Disorder regions |
| **Coordinates** | Real domain boundaries | NA (whole-protein) | 1 to cleavage site | TM helix boundaries | IDR boundaries |
| **Database count** | 19 + interproscan + GO | 1 | 1 | 1 | 1 |
| **Conda env** | ai_gigantic_interproscan | ai_gigantic_deeploc | ai_gigantic_signalp | ai_gigantic_tmbed | ai_gigantic_metapredict |

---

## Standardized Database Format

All tool outputs are parsed into a common 7-column TSV:

```
Phyloname	Sequence_Identifier	Domain_Start	Domain_Stop	Database_Name	Annotation_Identifier	Annotation_Details
```

**Coordinate handling per tool**:
- **InterProScan databases**: Real domain start/stop coordinates
- **MetaPredict**: IDR region start/stop boundaries
- **SignalP**: 1 to cleavage_site_position
- **tmbed**: Transmembrane helix boundary coordinates (multiple rows per multi-pass protein)
- **DeepLoc**: Start=NA, Stop=NA (whole-protein prediction)

**24 database subdirectories**: pfam, gene3d, superfamily, smart, panther, cdd, prints, prositepatterns, prositeprofiles, hamap, sfld, funfam, ncbifam, pirsf, coils, mobidblite, antifam, interproscan, go, deeploc, signalp, tmbed, metapredict

**File naming**: `gigantic_annotations-database_{database_name}-{phyloname}.tsv`

---

## Data Flow

```
genomesDB/output_to_input/gigantic_proteomes/
              │
    ┌─────────┼───────────┬──────────┬──────────┐
    ▼         ▼           ▼          ▼          ▼
BLOCK_       BLOCK_      BLOCK_    BLOCK_     BLOCK_
interpro-    deeploc/    signalp/  tmbed/     meta-
scan/                                         predict/
(4 scripts)  (2 scripts) (2 scripts) (2 scripts) (2 scripts)
    │            │           │          │          │
    ▼            ▼           ▼          ▼          ▼
output_to_input/  (consolidated at subproject root)
  BLOCK_interproscan/
  BLOCK_deeploc/
  BLOCK_signalp/
  BLOCK_tmbed/
  BLOCK_metapredict/
                             │
                             ▼
              BLOCK_build_annotation_database/
              (16 scripts: discover, download GO,
               parse x5, statistics, analyses x8)
                             │
                             ▼
              output_to_input/BLOCK_build_annotation_database/
              → downstream subprojects
```

---

## Prerequisites

1. **genomesDB complete**: `genomesDB/output_to_input/gigantic_proteomes/` populated
2. **Conda environments**: One per tool (created by `RUN-setup_environments.sh`)
3. **Nextflow**: `module load nextflow`
4. **Tool installations**: InterProScan (standalone Java), DeepLoc (DTU license), SignalP (DTU license)

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No proteome files found | Proteomes directory empty or wrong path | Check genomesDB output_to_input is populated |
| InterProScan out of memory | Proteome too large for single run | Reduce chunk_size in config |
| GPU not available | SLURM partition wrong | Use gpu partition for DeepLoc and tmbed |
| DeepLoc model not found | Manual installation required | Download from DTU website |
| SignalP license error | Requires academic license | Register at DTU website |
| No tool outputs found | Database builder cannot find sibling BLOCKs | Run at least one tool BLOCK first |
| GO ontology download failed | Network issue or URL changed | Check go_ontology_url in config |
| Nextflow cache stale | Updated scripts not taking effect | Delete `work/` and `.nextflow*`, rerun without `-resume` |

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `START_HERE-user_config.yaml` | Workflow configuration | **Yes** - edit before running |
| `RUN-workflow.sh` | Run pipeline locally | No |
| `RUN-workflow.sbatch` | Submit to SLURM | **Yes** - edit account/qos |
| `ai/main.nf` | Nextflow pipeline | No |
| `ai/nextflow.config` | Nextflow settings | Rarely - resource adjustments |
| `ai/scripts/*.py` | Pipeline scripts | No |

---

## Questions to Ask User

| Situation | Ask |
|-----------|-----|
| First run | "Which proteomes directory should I use?" |
| Resource errors | "What SLURM account and QOS should I use?" |
| Tool selection | "Which annotation tools should we run?" |
| Database build timing | "Have all desired tool BLOCKs completed?" |
| Species set | "Which species set are you analyzing?" |
| InterProScan install | "Where is InterProScan installed on your system?" |
| GPU availability | "Does your cluster have GPU nodes for DeepLoc and tmbed?" |
