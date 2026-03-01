# AI_GUIDE-orthogroups.md (Level 2: Subproject Guide)

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers orthogroups-specific concepts and structure.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| Orthogroups subproject concepts | This file |
| OrthoFinder details | `orthofinder/AI_GUIDE-orthofinder.md` |
| OrthoHMM details | `orthohmm/AI_GUIDE-orthohmm.md` |
| Broccoli details | `broccoli/AI_GUIDE-broccoli.md` |
| Comparison details | `comparison/AI_GUIDE-comparison.md` |
| Running a specific workflow | `{tool}/workflow-COPYME-run_{tool}/ai/AI_GUIDE-{tool}_workflow.md` |

---

## Purpose

The orthogroups subproject identifies orthologous gene groups across species using three independent methods, then compares their results. Orthogroups are fundamental units of comparative genomics - groups of genes descended from a single gene in the last common ancestor of the species being compared.

## Architecture

The orthogroups subproject contains **four equivalent, self-contained projects** that mirror the genomesDB STEP pattern:

```
orthogroups/                          # Subproject root (mirrors genomesDB root)
├── orthofinder/                      # Tool project (mirrors a genomesDB STEP)
├── orthohmm/                         # Tool project
├── broccoli/                         # Tool project
└── comparison/                       # Cross-method comparison project
```

Each tool project is fully self-contained: it validates inputs, runs its tool, standardizes output, generates statistics, and performs QC. The comparison project reads standardized output from all three tools.

**Design principle**: Adding a new orthogroup tool = copy any tool project, replace the tool execution script (003), adjust the output parser (004). Everything else (validation, stats, QC, project structure) works as-is.

---

## Tool Comparison

| Feature | OrthoFinder | OrthoHMM | Broccoli |
|---------|-------------|----------|----------|
| **Method** | Diamond + MCL clustering | Profile HMM (HMMER) + MCL | Phylogeny (FastTree) + network |
| **Speed** | Fast | Moderate | Moderate |
| **Sensitivity** | Good for close relatives | Better for divergent sequences | Phylogeny-aware |
| **Header handling** | Preserves original (-X flag) | Needs short headers (convert + restore) | Needs short headers (convert + restore) |
| **Script count** | 6 (no header conversion) | 6 (with header conversion + restoration) | 6 (with header conversion + restoration) |
| **Extra output** | Species tree, gene trees | HMM profiles, single-copy orthologs | Chimeric protein detection |
| **When to use** | Standard comparative genomics | Divergent species | Gene-fusion detection |

**All three can and should be run** - comparing results across methods gives higher confidence.

---

## Directory Structure

```
orthogroups/
├── AI_GUIDE-orthogroups.md              # THIS FILE (Level 2)
├── README.md
├── TODO.md
├── output_to_input/                     # Final outputs for downstream
├── upload_to_server/
├── RUN-clean_and_record_subproject.sh
├── RUN-update_upload_to_server.sh
│
├── orthofinder/                         # OrthoFinder tool project (6 scripts)
│   ├── AI_GUIDE-orthofinder.md          # Level 2 per-project guide
│   ├── output_to_input/                 # Standardized outputs
│   └── workflow-COPYME-run_orthofinder/
│       ├── ai/                          # Pipeline (main.nf, scripts/)
│       ├── INPUT_user/
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── orthofinder_config.yaml
│
├── orthohmm/                            # OrthoHMM tool project (6 scripts)
│   ├── AI_GUIDE-orthohmm.md
│   ├── output_to_input/
│   └── workflow-COPYME-run_orthohmm/
│       ├── ai/
│       ├── INPUT_user/
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── orthohmm_config.yaml
│
├── broccoli/                            # Broccoli tool project (6 scripts)
│   ├── AI_GUIDE-broccoli.md
│   ├── output_to_input/
│   └── workflow-COPYME-run_broccoli/
│       ├── ai/
│       ├── INPUT_user/
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── broccoli_config.yaml
│
└── comparison/                          # Cross-method comparison project (2 scripts)
    ├── AI_GUIDE-comparison.md
    ├── output_to_input/
    └── workflow-COPYME-compare_methods/
        ├── ai/
        ├── INPUT_user/
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        └── comparison_config.yaml
```

---

## Standardized Output Format

All three tools produce **identical output** in their `output_to_input/` directories:

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
genomesDB/output_to_input/gigantic_proteomes/
              │
    ┌─────────┼──────────┬───────────┐
    ▼         ▼          ▼           │
orthofinder/ orthohmm/  broccoli/    │
(6 scripts)  (6 scripts) (6 scripts)  │
    │         │          │           │
    ▼         ▼          ▼           │
  output_   output_    output_       │
  to_input/ to_input/  to_input/     │
    │         │          │           │
    └─────────┼──────────┘           │
              ▼                      │
         comparison/ ◄───────────────┘
         (2 scripts)
              │
              ▼
    orthogroups/output_to_input/ → downstream subprojects
```

---

## Prerequisites

1. **genomesDB complete**: `genomesDB/output_to_input/gigantic_proteomes/` populated
2. **Conda environment**: `ai_gigantic_orthogroups` (with OrthoFinder, OrthoHMM, Broccoli, Diamond)
3. **Nextflow**: `module load nextflow`

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No proteome files found | Proteomes directory empty or wrong path | Check genomesDB output_to_input is populated |
| Header mapping mismatch | Short IDs don't match header mapping file | Rerun script 002 |
| Tool not found | Conda environment not activated | `conda activate ai_gigantic_orthogroups` |
| No orthogroups produced | Tool failed silently | Check script 003 log for tool-specific errors |
| Comparison needs 2+ tools | Only one tool completed | Run at least 2 tool pipelines first |
| Nextflow cache stale | Updated scripts not taking effect | Delete `work/` and `.nextflow*`, rerun without `-resume` |

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `{tool}_config.yaml` | Tool parameters | **Yes** - edit before running |
| `RUN-workflow.sh` | Run pipeline locally | No |
| `RUN-workflow.sbatch` | Submit to SLURM | **Yes** - edit account/qos |
| `ai/main.nf` | Nextflow pipeline | No |
| `ai/nextflow.config` | Nextflow settings | Rarely - resource adjustments |
| `ai/scripts/001-006*.py` | Pipeline scripts (001-006 for tool projects, 001-002 for comparison) | No |

---

## Questions to Ask User

| Situation | Ask |
|-----------|-----|
| First run | "Which proteomes directory should I use?" |
| Resource errors | "What SLURM account and QOS should I use?" |
| Tool selection | "Which tool(s) should we run?" |
| Comparison timing | "Have all desired tools completed their pipelines?" |
| Species set | "Which species set are you analyzing?" |
