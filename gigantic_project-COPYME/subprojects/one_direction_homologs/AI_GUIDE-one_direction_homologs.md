# AI Guide: one_direction_homologs Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers one_direction_homologs-specific concepts and troubleshooting.

**Location**: `gigantic_project-*/subprojects/one_direction_homologs/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| one_direction_homologs concepts, troubleshooting | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-diamond_ncbi_nr_workflow.md` |

---

## What This Subproject Does

**Purpose**: Search species proteomes against NCBI nr using DIAMOND to identify one-directional homologs.

**Input**: Species proteomes from genomesDB `output_to_input/`

**Output**: Per-protein top hits (with NCBI headers and sequences), self/non-self hit identification, per-species statistics

**Prerequisites**: genomesDB must be complete, NCBI nr DIAMOND database must exist

---

## Directory Structure

```
one_direction_homologs/
├── README.md                        # Human documentation
├── AI_GUIDE-one_direction_homologs.md  # THIS FILE
├── TODO.md                          # Project tracking
├── RUN-clean_and_record_subproject.sh
├── RUN-update_upload_to_server.sh
│
├── user_research/                   # Personal workspace
│
├── output_to_input/                 # Outputs for downstream subprojects
│   └── ncbi_nr_top_hits/            # Top hits + statistics for downstream
│
├── upload_to_server/                # Server sharing
│   └── upload_manifest.tsv
│
└── workflow-COPYME-diamond_ncbi_nr/
    ├── RUN-workflow.sh              # bash RUN-workflow.sh
    ├── RUN-workflow.sbatch          # sbatch RUN-workflow.sbatch
    ├── diamond_ncbi_nr_config.yaml  # User edits DIAMOND settings here
    ├── INPUT_user/                  # Proteome manifest
    ├── OUTPUT_pipeline/             # Results (6 numbered directories)
    └── ai/                          # Internal
```

---

## Key Concepts

### One-Directional vs. Reciprocal Homologs

**One-directional**: Query protein A finds hit protein B in NCBI nr. We do NOT check whether B finds A. This is a simple "what does this protein look like in the broader database?"

**Reciprocal** (used in orthogroups): Query A finds B, AND B finds A. This establishes orthology. That analysis is done in the orthogroups subproject, not here.

### Self-Hit vs. Non-Self-Hit

| Type | Definition | Meaning |
|------|-----------|---------|
| **Self-hit** | Query sequence == subject sequence (identical) | Protein exists in NCBI nr |
| **Non-self-hit** | Query sequence != subject sequence | True homolog (different protein) |

**Why track both?**
- Self-hit rates reveal how well a species is represented in NCBI databases
- Non-self hits provide the closest evolutionary relatives
- Proteins with only self-hits have no close homologs in nr
- Proteins with no hits at all are potentially novel or highly divergent

### DIAMOND vs. BLAST

DIAMOND is ~1000x faster than NCBI BLAST for protein similarity searches while maintaining comparable sensitivity. The pipeline uses DIAMOND because:
- Searching 67 species against the full NCBI nr is computationally intensive
- DIAMOND enables massive parallelization (2,680 concurrent jobs)
- The `stitle` output field captures full NCBI headers for annotation

### Proteome Splitting Strategy

Each species proteome is split into N parts (default: 40) for parallel DIAMOND searches. This:
- Enables thousands of concurrent SLURM jobs
- Stays within cluster CPU limits (e.g., moroz-b account: 3,000 CPUs)
- Uses 1 CPU per job (DIAMOND is I/O bound, not CPU bound)
- Results are combined per species after all parts complete

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "DIAMOND database not found" | Path incorrect in config | Check `diamond_ncbi_nr_config.yaml` database path |
| "Proteome file not found" | Missing from genomesDB | Verify genomesDB output_to_input/ is populated |
| "No results for species X" | DIAMOND search failed | Check SLURM logs, verify database is valid |
| "Permission denied" | Scripts not executable | `chmod +x ai/scripts/*.sh` |
| Memory errors | Insufficient RAM for DIAMOND | Increase memory in nextflow.config (default: 21 GB) |
| "Zero non-self hits" | Species very unique or database issue | Normal for some species; check database completeness |

### Diagnostic Commands

```bash
# Check proteome manifest exists
cat INPUT_user/proteome_manifest.tsv | head -5

# Check DIAMOND database exists and is valid
diamond dbinfo --db /path/to/nr.dmnd

# Check split files were created
ls OUTPUT_pipeline/2-output/splits/ | head -20

# Check DIAMOND results per species
wc -l OUTPUT_pipeline/4-output/combined_*.tsv

# Check top hits output
head -2 OUTPUT_pipeline/5-output/*_top_hits.tsv

# Check final statistics
cat OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv
```

---

## Data Flow

```
genomesDB/output_to_input/proteomes/
    │
    ▼
[001] Validate proteomes
    │
    ▼
[002] Split proteomes (67 species × 40 parts = 2,680 splits)
    │
    ▼
[003] DIAMOND search per split (2,680 parallel jobs)
    │
    ▼
[004] Combine results per species (67 combined files)
    │
    ▼
[005] Identify top self/non-self hits per protein (67 species)
    │
    ▼
[006] Compile master statistics table
    │
    ▼
output_to_input/ncbi_nr_top_hits/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/diamond_ncbi_nr_config.yaml` | Project name, database path, options | **YES** |
| `workflow-*/RUN-workflow.sbatch` | SLURM account/qos | **YES** (SLURM) |
| `workflow-*/INPUT_user/proteome_manifest.tsv` | Species and proteome paths | **YES** (or auto-generated) |
| `output_to_input/ncbi_nr_top_hits/*.tsv` | Top hits + statistics for downstream | No |
| `ai/scripts/*` | Pipeline scripts | No |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| General help | "How many species are you searching? Where is your DIAMOND database?" |
| Configuration | "What e-value threshold do you want? How many parts per species?" |
| Error occurred | "Which script failed? Can you show me the SLURM log?" |
| Missing results | "Did all DIAMOND jobs complete? Check SLURM accounting." |
| Slow performance | "Are you using local scratch for DIAMOND I/O? What queue/account?" |
