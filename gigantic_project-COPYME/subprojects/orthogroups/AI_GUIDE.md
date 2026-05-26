# AI_GUIDE — orthogroups Subproject

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: Read `../../AI_GUIDE.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers orthogroups-specific concepts and structure.

## Where this fits

- Parent project: [`../../AI_GUIDE.md`](../../AI_GUIDE.md), [`../../README.md`](../../README.md)
- This subproject: [`README.md`](README.md), this file
- Prerequisite: [`../genomesDB/STEP_4-create_final_species_set/`](../genomesDB/STEP_4-create_final_species_set/) — provides standardized proteomes
- Prerequisite (naming): [`../phylonames/`](../phylonames/) — clade naming conventions
- Downstream consumers: `orthogroups_X_ocl`, plus orthogroup-aware analyses (`gene_sizes`, `dark_proteomes`, `hotspots`, `secretome`, `one_direction_homologs`)

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| Conventions (§1–§48) | `../../ai/ai_FYIs/gigantic_conventions.md` |
| Orthogroups subproject concepts (this file) | This file |
| OrthoFinder details (standard) | `BLOCK_orthofinder/AI_GUIDE.md` |
| OrthoFinder details (DIAMOND fan-out, ≥30 species) | `BLOCK_orthofinder_array/AI_GUIDE.md` |
| OrthoHMM details (standard) | `BLOCK_orthohmm/AI_GUIDE.md` |
| OrthoHMM details (phmmer fan-out, ≥30 species) | `BLOCK_orthohmm_GIGANTIC/AI_GUIDE.md` |
| Broccoli details | `BLOCK_broccoli/AI_GUIDE.md` |
| Cross-method comparison details | `BLOCK_comparison/AI_GUIDE.md` |
| Running a specific BLOCK's workflow | `BLOCK_<tool>/workflow-COPYME-run_<tool>/ai/AI_GUIDE.md` |

---

## Purpose

The orthogroups subproject identifies orthologous gene groups across species using three independent methods, then compares their results. Orthogroups are fundamental units of comparative genomics - groups of genes descended from a single gene in the last common ancestor of the species being compared.

## Architecture

The orthogroups subproject contains **multiple equivalent, self-contained projects** that mirror the genomesDB STEP pattern:

```
orthogroups/                                    # Subproject root (mirrors genomesDB root)
├── BLOCK_orthofinder/                                  # Standard OrthoFinder (smaller species sets)
├── BLOCK_orthofinder_array/                            # Parallel-DIAMOND fan-out for ≥30 species
├── BLOCK_orthohmm/                                     # Standard OrthoHMM (smaller species sets)
├── BLOCK_orthohmm_GIGANTIC/                            # Parallel-phmmer fan-out for ≥30 species
├── BLOCK_broccoli/                                     # Tool project
└── BLOCK_comparison/                                   # Cross-method comparison project
```

Each tool project is fully self-contained: it validates inputs, runs its tool, standardizes output, generates statistics, and performs QC. The comparison project reads standardized output from any tool BLOCK (standard or array).

**Design principle**: Adding a new orthogroup tool = copy any tool project, replace the tool execution script (003), adjust the output parser. Everything else (validation, stats, QC, project structure) works as-is.

### Standard vs Array Variants

For each search-based tool (OrthoFinder, OrthoHMM) there are two BLOCK
variants:

- **Standard** (`BLOCK_orthofinder/`, `BLOCK_orthohmm/`) — single-process
  invocation, simpler to set up. Use for small species sets (< ~20).
- **Array** (`BLOCK_orthofinder_array/`, `BLOCK_orthohmm_GIGANTIC/`) —
  the slow all-vs-all search step is parallelized across SLURM burst
  job arrays via `process.array = 100`. Each pair is its own task,
  ~4,830 tasks bundled into ~49 array submissions. Etiquette-correct
  on shared HPC. Use for ≥ 30 species where standard would take days.

Both variants produce **identical biological output** (same orthogroup
table format, same downstream consumability). The array variants use the
tools' built-in escape hatches (`--stop prepare` / `-op` to extract
canonical search commands; `--start search_res` / `-b` to resume from
pre-computed search results) — phmmer/DIAMOND invocations are bit-identical
to what the standard tools would have run.

---

## Tool Comparison

| Feature | OrthoFinder | OrthoHMM | Broccoli |
|---------|-------------|----------|----------|
| **Method** | Diamond + MCL clustering | Profile HMM (HMMER) + MCL | Phylogeny (FastTree) + network |
| **Speed** | Fast | Moderate | Moderate |
| **Sensitivity** | Good for close relatives | Better for divergent sequences | Phylogeny-aware |
| **Header handling** | Preserves original (-X flag) | Needs short headers (convert + restore) | Needs short headers (convert + restore) |
| **Script count** | 7 (no header conversion) | 7 (with header conversion + restoration) | 7 (with header conversion + restoration) |
| **Extra output** | Species tree, gene trees | HMM profiles, single-copy orthologs | Chimeric protein detection |
| **When to use** | Standard comparative genomics | Divergent species | Gene-fusion detection |

**All three can and should be run** - comparing results across methods gives higher confidence.

---

## Directory Structure

See the [README.md](README.md) "Directory Structure" section for the
canonical tree (six BLOCKs: orthofinder + orthofinder_array +
orthohmm + orthohmm_GIGANTIC + broccoli + comparison). Don't duplicate
the tree here — keep it in one place to avoid drift.

---

## Standardized Output Format

All three tools produce **identical output** in the subproject-root `output_to_input/BLOCK_*/` directories:

| File | Contents |
|------|----------|
| `orthogroups_gigantic_ids.tsv` | `OG_ID<TAB>gene1<TAB>gene2<TAB>...` with full GIGANTIC headers |
| `gene_count_gigantic_ids.tsv` | Gene counts per orthogroup per species |
| `summary_statistics.tsv` | Overall clustering statistics |
| `per_species_summary.tsv` | Per-species orthogroup statistics |

This standardization enables:
- The comparison project to consume any tool's output uniformly
- Downstream subprojects to use results from any tool interchangeably
- Easy validation that tools are producing comparable output

---

## Data Flow

```
genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/
              │
    ┌─────────┼──────────┬───────────┐
    ▼         ▼          ▼           │
BLOCK_orthofinder/ BLOCK_orthohmm/ BLOCK_broccoli/ │
(7 scripts)       (7 scripts)     (7 scripts)     │
    │                │               │            │
    ▼                ▼               ▼            │
output_to_input/  output_to_input/ output_to_input/│
  BLOCK_ortho       BLOCK_ortho      BLOCK_        │
  finder/           hmm/             broccoli/     │
    │                │               │            │
    └────────────────┼───────────────┘            │
                     ▼                            │
         BLOCK_comparison/ ◄──────────────────────┘
         (2 scripts)
              │
              ▼
    output_to_input/BLOCK_comparison/ → downstream subprojects
```

All outputs are consolidated under a single `orthogroups/output_to_input/` directory at the subproject root.

---

## Prerequisites

1. **genomesDB STEP_4 complete**: `genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` populated
2. **Conda environment**: `aiG-orthogroups-<tool>` (specific name: `aiG-orthogroups-orthofinder` / `aiG-orthogroups-orthohmm` / `aiG-orthogroups-broccoli` / `aiG-orthogroups-comparison` — see each BLOCK) (with OrthoFinder, OrthoHMM, Broccoli, Diamond)
3. **Nextflow**: `module load nextflow`

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No proteome files found | Proteomes directory empty or wrong path | Check genomesDB output_to_input is populated |
| Header mapping mismatch | Short IDs don't match header mapping file | Rerun script 002 |
| Tool not found | Conda environment not activated | `conda activate aiG-orthogroups-<tool>` |
| No orthogroups produced | Tool failed silently | Check script 003 log for tool-specific errors |
| Comparison needs 2+ tools | Only one tool completed | Run at least 2 tool pipelines first |
| Nextflow cache stale | Updated scripts not taking effect | Delete `work/` and `.nextflow*`, rerun without `-resume` |

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `START_HERE-user_config.yaml` | Workflow configuration | **Yes** - edit before running |
| `RUN-workflow.sh` | Run pipeline locally | No |
| `RUN-workflow.sh` | Submit to SLURM | **Yes** - edit account/qos |
| `ai/main.nf` | Nextflow pipeline | No |
| `ai/nextflow.config` | Nextflow settings | Rarely - resource adjustments |
| `ai/scripts/001-007*` | Pipeline scripts (001-007 for tool projects, 001-002 for comparison) | No |

---

## Questions to Ask User

| Situation | Ask |
|-----------|-----|
| First run | "Which proteomes directory should I use?" |
| Resource errors | "What SLURM account and QOS should I use?" |
| Tool selection | "Which tool(s) should we run?" |
| Comparison timing | "Have all desired tools completed their pipelines?" |
| Species set | "Which species set are you analyzing?" |
