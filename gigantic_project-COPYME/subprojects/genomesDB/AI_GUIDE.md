# AI Guide: genomesDB Subproject

**For AI Assistants**: Read `../../AI_GUIDE.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers genomesDB-specific concepts and the four-step architecture.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/`

**Status**: The active genomesDB. Build outputs live in `workflow-RUN_1` of each STEP. The specific species set is determined by the source manifest provided in STEP_1.

---

## ⚠️ CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- ❌ **NEVER** silently do something different than requested
- ❌ **NEVER** assume you know better and proceed without asking
- ✅ **ALWAYS** stop and explain the discrepancy
- ✅ **ALWAYS** ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| Conventions (§1–§41) | `../../ai/ai_FYIs/gigantic_conventions.md` |
| Research-grade behavior / posture | `../../AI_BEHAVIOR.md` |
| genomesDB concepts, pipeline structure | This file |
| STEP_1 sources (overview) | `STEP_1-sources/AI_GUIDE.md` |
| STEP_1 workflow (operational) | `STEP_1-sources/workflow-COPYME-ingest_source_data/ai/AI_GUIDE.md` |
| STEP_2 standardize_and_evaluate (overview) | `STEP_2-standardize_and_evaluate/AI_GUIDE.md` |
| STEP_2 workflow (operational) | `STEP_2-standardize_and_evaluate/workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/ai/AI_GUIDE.md` |
| STEP_3 databases (overview) | `STEP_3-databases/AI_GUIDE.md` |
| STEP_3 workflow (operational) | `STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/ai/AI_GUIDE.md` |
| STEP_4 create_final_species_set (overview) | `STEP_4-create_final_species_set/AI_GUIDE.md` |
| STEP_4 workflow (operational) | `STEP_4-create_final_species_set/workflow-COPYME-create_final_species_set/ai/AI_GUIDE.md` |

---

## What This Subproject Does

**Purpose**: Manage genome and proteome data for GIGANTIC projects.

**Pipeline** (4 STEPs):
1. **Sources** — Ingest user-provided proteome files (USER-DRIVEN, no auto-downloads)
2. **Standardize and Evaluate** — Standardize formats, apply phylonames, evaluate quality (BUSCO + gfastats)
3. **Databases** — Build per-species BLASTP databases
4. **Create Final Species Set** — Select and copy final species set for downstream subprojects

**For evigene transcriptomes**: extract T1 proteome user-side in
`research_notebook/research_user/<species>/` from the okayset
(`evgclass` headers), then symlink into
`INPUT_user/genomic_resources/proteomes/` per §17, §18. STEP_1 then
ingests it like any other proteome. (Older designs had a separate
STEP_0-prepare_proteomes inside genomesDB; that has been deprecated
in favor of the user-side prep + INPUT_user staging pattern.)

**Critical**: Run phylonames subproject FIRST - genomesDB depends on phylonames for species naming.

---

## T0 and T1 Proteome Concepts

GIGANTIC distinguishes two proteome types based on transcript representation:

| Type | Definition | Use in GIGANTIC |
|------|-----------|-----------------|
| **T1** | One protein per gene/locus | Default for all analyses (orthogroups, gene trees, annotations) |
| **T0** | All transcripts per locus | Retained as reference, not used in standard pipelines |

**How T1 is obtained depends on the data source**:

| Data Source | T1 Extraction Method | Where It Happens |
|-------------|----------------------|------------------|
| **NCBI genomes** | Longest transcript per gene, extracted from `protein.faa` using GFF3 annotation | STEP_2, Script 003 |
| **Evigene transcriptomes** | Main transcript per locus, selected from okayset using `evgclass` headers | **User-side, in `research_notebook/research_user/`** before staging into `INPUT_user/` (per §17, §18) |

**T0 composition by source**:

| Data Source | T0 Contains |
|-------------|-------------|
| **NCBI genomes** | All protein isoforms from `protein.faa` |
| **Evigene transcriptomes** | Main + alt transcripts from okayset |

**Key principle**: GIGANTIC uses T1 by default for homolog discovery. One representative protein per gene avoids inflating BLAST hits and orthogroup assignments with redundant isoforms.

---

## GIGANTIC Source Data Naming Conventions

### Source Manifest Format

The source manifest is a **four-column TSV**:

```
genus_species	genome_path	genome_annotation_path	proteome_path
```

**Example** (using relative paths to project-level INPUT_user):
```tsv
genus_species	genome_path	genome_annotation_path	proteome_path
Homo_sapiens	../../../../INPUT_user/genomic_resources/genomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa
Mus_musculus	../../../../INPUT_user/genomic_resources/genomes/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.aa
```

### File Naming Convention

**All source files follow this structure**:

```
genus_species-genome_source_identifier-downloaded_date.extension
```

| Component | Description | Example |
|-----------|-------------|---------|
| `genus_species` | Species name | `Homo_sapiens` |
| `genome_source_identifier` | "genome" joined with source database + assembly ID | `genome_ncbi_GCF_000001405.40` |
| `downloaded_date` | downloaded_YYYYMMDD format | `downloaded_20240115` |
| `extension` | File type | `.fasta`, `.gff3`, `.aa` |

**File type extensions**:
- `.fasta` - Genome sequence (nucleotide)
- `.gff3` - Genome annotation
- `.aa` - Proteome (amino acid sequences)

**Examples**:
```
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa
```

### Sequence Header Convention

**FASTA headers follow this structure**:

```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

| Component | Description | Example |
|-----------|-------------|---------|
| `genus_species` | Must match filename species | `Homo_sapiens` |
| `source_gene_id` | Gene ID from source database | `ENSG00000139618` |
| `source_transcript_id` | Transcript ID from source | `ENST00000380152` |
| `source_protein_id` | Protein ID from source | `ENSP00000369497` |

**Example headers**:
```
>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
>Mus_musculus-MGI:87853-NM_007393-NP_031419
>Drosophila_melanogaster-FBgn0000003-FBtr0071763-FBpp0071429
```

**Why this format?**
- Species is immediately identifiable from any sequence
- Full provenance chain: gene → transcript → protein
- Enables tracing back to source databases
- Consistent across all GIGANTIC analyses

---

## Pipeline Architecture

### Evigene T1 prep happens user-side, not in genomesDB

**When users have evigene transcriptome assemblies** (not NCBI genomes):
the T1 extraction (parsing the okayset's `evgclass` headers to select
the main transcript per locus) is **user-side prep work**, not a STEP
of genomesDB.

- Do the prep in `research_notebook/research_user/<species>/` (your
  wild-west sandbox per §1, §25)
- Symlink the resulting T1 `.aa` file into
  `INPUT_user/genomic_resources/proteomes/` per §17, §18
- STEP_1 then ingests it via the source_manifest like any other proteome

An older design (deprecated) had this as a separate
`STEP_0-prepare_proteomes/` inside genomesDB. The current architecture
moves it outside the GIGANTIC subproject because (a) it's irregular
per-source prep work, (b) the INPUT_user staging pattern is the
universal user → GIGANTIC handoff, and (c) keeping genomesDB focused on
the 4 standardization STEPs is cleaner.

### STEP_1-sources (USER-DRIVEN)

**Directory**: `STEP_1-sources/`
**Workflow**: `workflow-COPYME-ingest_source_data`

**Critical Concept**: STEP_1 does NOT download data automatically. Users
stage their source files into `INPUT_user/` (per §17, §18) and STEP_1
reads from there via `source_manifest.tsv`. For NCBI genomes, provide
the full `protein.faa` file (T1 extraction happens in STEP_2). For
evigene transcriptomes, do the T1 extraction in
`research_notebook/research_user/` first (see above) and provide the
extracted T1 proteome via INPUT_user.

**Function**:
- Accept user-provided manifest with genome, GTF, proteome paths
- Validate source files exist
- Hard copy proteomes to OUTPUT_pipeline
- Create symlinks in output_to_input for STEP_2

**Outputs**:
- `output_to_input/STEP_1-sources/proteomes/` - Symlinks for STEP_2

### STEP_2-standardize_and_evaluate

**Directory**: `STEP_2-standardize_and_evaluate/`
**Workflow**: `workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb`

**Function**:
- Rename files using phyloname convention
- Validate FASTA format
- Calculate genome statistics
- Flag quality issues

**Outputs**:
- `output_to_input/STEP_2-standardize_and_evaluate/standardized_proteomes/` - Clean files for STEP_3
- Evaluation reports

### STEP_3-databases

**Directory**: `STEP_3-databases/`
**Workflow**: `workflow-COPYME-build_gigantic_genomesDB`

**Function**:
- Build BLAST databases (blastp)
- Create species manifests
- Generate proteome indices

**Outputs**:
- `output_to_input/STEP_3-databases/` - BLAST databases

### STEP_4-create_final_species_set

**Directory**: `STEP_4-create_final_species_set/`
**Workflow**: `workflow-COPYME-create_final_species_set`

**Function**:
- User reviews STEP_2 quality metrics and selects species to keep
- Validates species selection against STEP_2 and STEP_3 outputs
- Copies selected proteomes and BLAST databases
- Creates `speciesN_` named directories for downstream subprojects

**Outputs**:
- `output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` - Final proteomes
- `output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/` - Final BLAST databases

---

## Directory Structure (relative to subproject root)

```
genomesDB/
├── README.md                                # User-facing documentation
├── AI_GUIDE.md                              # THIS FILE
│
├── RUN-update_upload_to_server.sh           # Subproject-level publisher (§38; thin wrapper around shared helper)
│
├── upload_to_server/                        # Single publish destination (§38)
│
├── output_to_input/                         # Outputs for downstream subprojects (§2)
│   ├── STEP_1-sources/
│   ├── STEP_2-standardize_and_evaluate/
│   ├── STEP_3-databases/
│   └── STEP_4-create_final_species_set/
│
│   (no per-subproject research_notebook/ — single project-root sandbox at
│   gigantic_project-COPYME/research_notebook/ per §1, §25; chat captures
│   land at research_notebook/research_ai/sessions/ per §9)
│
├── STEP_1-sources/
│   ├── README.md
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-ingest_source_data/
│       ├── README.md
│       ├── RUN-workflow.sh                  # Unified driver (§29)
│       ├── START_HERE-user_config.yaml
│       ├── upload_manifest.tsv              # Server publish manifest (§38, §39)
│       ├── INPUT_user/
│       │   └── source_manifest.tsv          # User creates this
│       ├── OUTPUT_pipeline/
│       └── ai/                              # NextFlow pipeline + scripts
│
├── STEP_2-standardize_and_evaluate/
│   ├── README.md
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
│       ├── README.md, RUN-workflow.sh, START_HERE-user_config.yaml
│       ├── upload_manifest.tsv
│       ├── INPUT_user/, OUTPUT_pipeline/
│       └── ai/
│
├── STEP_3-databases/
│   ├── README.md
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-build_gigantic_genomesDB/
│       ├── README.md, RUN-workflow.sh, START_HERE-user_config.yaml
│       ├── upload_manifest.tsv
│       ├── INPUT_user/, OUTPUT_pipeline/
│       └── ai/
│
└── STEP_4-create_final_species_set/
    ├── README.md
    ├── AI_GUIDE.md
    └── workflow-COPYME-create_final_species_set/
        ├── README.md, RUN-workflow.sh, START_HERE-user_config.yaml
        ├── upload_manifest.tsv
        ├── INPUT_user/, OUTPUT_pipeline/
        └── ai/
```

Per §38 + §41, genomesDB is a STEP-organized subproject with ONE
subproject-level `upload_to_server/` and one subproject-level
`output_to_input/` (no per-STEP duplicates of either; deleted in the
2026-05-26 cleanup). Per §29, unified `RUN-workflow.sh` drives both
local and SLURM execution via the YAML `execution_mode` key.

---

## Data Flow Between Steps

```
[user prep in research_notebook/research_user/ if needed (e.g., evigene T1 extraction)]
                                              ↓
INPUT_user/genomic_resources/  (symlinks per §17, §18)
                                              ↓
output_to_input/STEP_1-sources/ → STEP_2-standardize_and_evaluate/INPUT_user/
                                              ↓
output_to_input/STEP_2-standardize_and_evaluate/ → STEP_3-databases/INPUT_user/
                                                            ↓
          STEP_2 + STEP_3 outputs → STEP_4-create_final_species_set
                                              ↓
                   output_to_input/STEP_4-create_final_species_set/
                                              ↓
                              (Other GIGANTIC subprojects)
```

**T1 extraction paths**: For NCBI genomes, T1 is extracted in STEP_2
(Script 003) from the full `protein.faa` using GFF3. For evigene
transcriptomes, T1 is extracted user-side in
`research_notebook/research_user/` from the okayset using `evgclass`
headers, then symlinked into `INPUT_user/genomic_resources/proteomes/`
so STEP_1 receives an already-filtered T1 proteome.

---

## Path Depth Adjustment

Step directories are nested ONE level deeper than standard subprojects:

| Location | Relative path to project root |
|----------|-------------------------------|
| `genomesDB/` | `../../` |
| `genomesDB/STEP_1-sources/` | `../../../` |
| `genomesDB/STEP_1-sources/workflow-COPYME-*/` | `../../../../` |
| `genomesDB/STEP_1-sources/workflow-COPYME-*/ai/` | `../../../../../` |

---

## Research Notebook Location

genomesDB logging uses two locations:

- **AI sessions** (project-wide): `research_notebook/research_ai/sessions/`
- **Workflow run logs** (per-workflow): `workflow-*/ai/logs/`

```
research_notebook/research_ai/sessions/    # All AI sessions (project-wide, not per-subproject)
workflow-*/ai/logs/                         # Run logs specific to each workflow
workflow-*/ai/validation/                   # Validation outputs specific to each workflow
```

Sessions are consolidated project-wide. Run logs stay with the workflow that generated them.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Species not found" | phylonames not run | Run phylonames subproject first |
| "Source file not found" | Path in manifest doesn't exist | Verify paths with `ls` |
| STEP_2 can't find inputs | STEP_1 not run | Run STEP_1-sources workflow first |
| STEP_3 can't find inputs | STEP_2 not run | Run STEP_2-standardize_and_evaluate first |
| BLAST database empty | No proteomes passed QC | Check STEP_2 evaluation reports |
| STEP_4 can't find inputs | STEP_2 or STEP_3 not run | Run STEP_2 and STEP_3 first |
| STEP_4 species not found | Species in selection but not in STEP_2/STEP_3 | Check spelling in selected_species.txt |
| "No phyloname mapping" | Missing mapping file | Run phylonames, check output_to_input |
| Manifest format error | Wrong columns or delimiter | Use 4 tab-separated columns |
| Evigene T1 prep needed | Source includes evigene transcriptome assemblies | Do T1 extraction user-side in `research_notebook/research_user/<species>/` from the okayset's `evgclass` headers, then symlink the T1 `.aa` into `INPUT_user/genomic_resources/proteomes/` per §17, §18 |

### Diagnostic Commands

```bash
# Check phylonames dependency
ls ../phylonames/output_to_input/maps/

# Check INPUT_user staging (per §17, §18)
ls ../../INPUT_user/genomic_resources/proteomes/

# Check STEP_1 outputs
ls output_to_input/STEP_1-sources/

# Check STEP_2 outputs
ls output_to_input/STEP_2-standardize_and_evaluate/

# Check STEP_3 outputs
ls output_to_input/STEP_3-databases/

# Check STEP_4 outputs (final species set)
ls output_to_input/STEP_4-create_final_species_set/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `../../INPUT_user/genomic_resources/proteomes/` | User-staged proteomes (symlinks per §17, §18; includes evigene T1 results from user-side prep) | **YES** |
| `STEP_1-sources/workflow-*/INPUT_user/source_manifest.tsv` | List of genomes/proteomes to ingest (paths into `../../../INPUT_user/`) | **YES** |
| `STEP_2-standardize_and_evaluate/workflow-*/INPUT_user/` | (from STEP_1) | No |
| `STEP_3-databases/workflow-*/INPUT_user/` | (from STEP_2) | No |
| `STEP_4-create_final_species_set/workflow-*/START_HERE-user_config.yaml` | Paths to STEP_2/STEP_3 outputs | **YES** |
| `STEP_4-create_final_species_set/workflow-*/INPUT_user/selected_species.txt` | Species selection (optional) | **YES** (optional) |
| `output_to_input/STEP_4-create_final_species_set/` | Final species set | No |
| `STEP_*/workflow-COPYME-*/upload_manifest.tsv` | Per-workflow publish manifest (§38) | **YES** (to customize what publishes) |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting genomesDB | "Have you run the phylonames subproject first?" |
| Starting genomesDB | "Are your species from NCBI genomes, evigene transcriptomes, or a mix? (Evigene needs user-side T1 extraction in research_notebook/research_user/ first — then symlink the T1 .aa into INPUT_user/genomic_resources/proteomes/ per §17, §18.)" |
| Before evigene T1 prep | "Where are your evigene okayset files? Do their FASTA headers carry `evgclass` classification info? (You'll do the T1 extraction in your sandbox, not inside genomesDB.)" |
| Before STEP_1 | "Where are your genome, GTF, and proteome files located?" |
| Manifest creation | "Are your files named with the GIGANTIC convention? (genus_species-genome_source_identifier-downloaded_date.ext)" |
| Header format | "Do your FASTA headers follow the convention? (genus_species-gene_id-transcript_id-protein_id)" |
| Quality thresholds | "What quality thresholds should we use for evaluation?" |
| Before STEP_4 | "Have STEP_2 and STEP_3 completed? Do you want all species or a subset?" |
| Error occurred | "Which step failed? What error message?" |

---

## Downstream consumers (per §40)

genomesDB feeds essentially every downstream subproject that operates on
standardized proteomes / genomes / annotations:

- **annotations_hmms** — reads standardized proteomes (`.aa` files) from
  `genomesDB/output_to_input/STEP_2-standardize_and_evaluate/proteomes/`
  to run InterProScan, DeepLoc, SignalP, TMBed, MetaPredict
- **orthogroups** — reads the same standardized proteomes to run
  OrthoHMM, OrthoFinder, Broccoli
- **trees_gene_families** — STEP_1 (homolog discovery) reads BLAST
  databases from `genomesDB/output_to_input/STEP_3-databases/` for
  RBH/RBF searches
- **trees_gene_groups** — same dependency as trees_gene_families
- **trees_species** — uses the species set defined in
  `genomesDB/output_to_input/STEP_4-create_final_species_set/` as input
  for species-tree topology generation
- **gene_sizes** — reads genomes + annotations from STEP_2 outputs
- **hotspots**, **secretome**, **one_direction_homologs**,
  **dark_proteomes**, etc. — all consume standardized proteomes
- **orthogroups_X_ocl**, **annotations_X_ocl** — indirect (through
  their producer subprojects)

In practice every "real" GIGANTIC subproject reads from
`genomesDB/output_to_input/` at some point. **genomesDB must run
second** in any GIGANTIC project (after phylonames).

## Next Steps After genomesDB

Guide users to:
1. **annotations_hmms** — run functional annotations on standardized
   proteomes
2. **orthogroups** — identify ortholog groups across species
3. **trees_species** — generate candidate species-tree topologies for
   the final species set
4. **trees_gene_families** / **trees_gene_groups** — build per-gene
   phylogenies (depend on BLAST databases from STEP_3)

---

## Session hygiene (per §61)

For productive project work:
- **Root every chat session at this named `gigantic_project-*/` directory**.
  Not at `GIGANTIC/` (framework root, reserved for framework dev per §16),
  not at `subprojects/<X>/`, not at a `workflow-COPYME-*/` dir, not at
  any directory deeper than the named project root.
- **One chat session per subproject** you're actively working in — keeps
  context focused and prevents cross-subproject confusion.
- **Continue the same session over many compactions** (lossless per §9)
  until it becomes muddled or slow; then start fresh in a new session,
  same root, same subproject focus.
- **Keep a separate "small questions" session** for one-off questions
  so subproject sessions stay focused.

See `ai/ai_FYIs/gigantic_conventions.md` §61 for the full rationale.
