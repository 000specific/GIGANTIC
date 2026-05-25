# AI Guide: HUGO HGNC Gene Groups

**For AI Assistants**: Read `../../../AI_GUIDE-project.md` first for GIGANTIC project patterns. Then `../AI_GUIDE-trees_gene_groups.md` for subproject architecture (source-based, two-workflow). This guide covers HGNC-specific details.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups-hugo_hgnc/`

**Source**: [HUGO Gene Nomenclature Committee (HGNC)](https://www.genenames.org/) — worldwide authority for human gene nomenclature and functional grouping.

---

## What This Source Is

`gene_groups-hugo_hgnc/` is the per-source instance of `gene_groups_COPYME` customized for HGNC. It contains:

- A **STEP_0-hgnc_gene_groups/** workflow with HGNC-specific code (downloads HGNC data, generates RGS FASTAs per gene group) — replaces the empty `STEP_0-placeholder/` from the master.
- **STEP_1**, **STEP_2**, **STEP_3** workflow-COPYME-* dirs identical to the master's. The user copies each STEP's COPYME → RUN_NN to run.

Created by: `cp -r gene_groups_COPYME gene_groups-hugo_hgnc` plus replacing STEP_0-placeholder with STEP_0-hgnc_gene_groups.

## HGNC RGS Naming Convention

5-field naming. Within each dash-separated field, only letters, numbers, and underscores.

### Filename

```
rgs_hugo_hgnc-human-{sanitized_group_name}.aa
```

Examples:
- `rgs_hugo_hgnc-human-gap_junction_proteins.aa`
- `rgs_hugo_hgnc-human-fascin_family.aa`

### Header (per sequence)

```
>rgs_{sanitized_name}-human-{GENE_SYMBOL}-hgnc_gg{FAMILY_ID}_{Gene_Group_Name}-{PROTEIN_ID}
```

Example:
```
>rgs_gap_junction_proteins-human-GJA1-hgnc_gg2_Gap_junction_proteins-NP_000156_1
```

Fields:
1. `rgs_{sanitized_name}` — RGS identifier
2. `human` — Species short name (HGNC is human-only)
3. `{GENE_SYMBOL}` — HGNC approved gene symbol
4. `hgnc_gg{ID}_{Gene_Group_Name}` — Source and traceability (HGNC family ID + name)
5. `{PROTEIN_ID}` — NCBI protein accession (dots replaced with underscores)

## STEP_0: HGNC RGS Generation

**Runs once.** Produces ~1,974 RGS FASTA files.

Three-script pipeline at `STEP_0-hgnc_gene_groups/workflow-COPYME-hgnc_gene_groups/ai/scripts/`:

| Script | What |
|--------|------|
| `001_ai-python-download_hgnc_gene_group_data.py` | Downloads 5 data files from genenames.org + Google Cloud Storage |
| `002_ai-python-build_aggregated_gene_sets.py` | Builds aggregated gene symbol sets per group (uses hierarchy closure); filters for protein-coding |
| `003_ai-python-generate_rgs_fasta_files.py` | Extracts sequences from human T1 proteome matching gene symbols |

### Statistics (latest run)

| Metric | Value |
|--------|-------|
| Total HGNC gene groups | 2,129 |
| Groups with protein-coding genes | 1,993 |
| RGS files generated | 1,974 |
| Groups skipped (no proteome matches) | 19 |
| Unique gene symbols | 15,293 |

## How a user runs HGNC end-to-end

STEPs are sequentially dependent: STEP_0 → STEP_1 → STEP_2 → STEP_3.

### STEP_0 (one-time RGS generation)

```bash
cd gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/
cp -r workflow-COPYME-hgnc_gene_groups workflow-RUN_1-hgnc_gene_groups
cd workflow-RUN_1-hgnc_gene_groups
# Edit START_HERE-user_config.yaml (set human_proteome_path)
bash RUN-workflow.sh
```

### STEP_1 (homolog discovery, runs over all gene groups)

```bash
cd gene_groups-hugo_hgnc/STEP_1-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs
cd workflow-RUN_1-rbh_rbf_homologs
# Edit START_HERE-user_config.yaml (execution_mode + paths to STEP_0 output)
bash RUN-workflow.sh
```

The STEP_1 `RUN-workflow.sh` is an **orchestrator**: it iterates the 1,974 gene groups from the STEP_0 summary, creates `gene_group-X/workflow-RUN_01-rbh_rbf_homologs/` per gene group, and dispatches per `execution_mode` (local | slurm-standard | slurm-burst).

### STEP_2 + STEP_3

Same orchestrator pattern. Each STEP's RUN-workflow.sh handles all gene groups.

## Directory Structure

```
gene_groups-hugo_hgnc/
├── AI_GUIDE-hugo_hgnc.md                         # THIS FILE
├── INPUT_user/                                    # HGNC-level manifests (if any)
├── STEP_0-hgnc_gene_groups/
│   └── workflow-COPYME-hgnc_gene_groups/         # HGNC-specific STEP_0
│       ├── RUN-workflow.sh
│       ├── START_HERE-user_config.yaml
│       └── ai/                                    # main.nf, scripts, conda_environment.yml
├── STEP_1-homolog_discovery/
│   ├── AI_GUIDE-homolog_discovery.md
│   ├── README.md
│   └── workflow-COPYME-rbh_rbf_homologs/         # = master gene_groups_COPYME's (refreshed)
├── STEP_2-phylogenetic_analysis/
│   ├── AI_GUIDE-phylogenetic_analysis.md
│   ├── README.md
│   └── workflow-COPYME-phylogenetic_analysis/    # = master
└── STEP_3-tree_visualization/
    ├── AI_GUIDE-phylogenetic_visualization.md
    ├── README.md
    └── workflow-COPYME-tree_visualization/       # = master
```

## Conda Environments (per-workflow, auto-created on first run)

| Workflow | Env name | Key deps |
|----------|----------|----------|
| STEP_0 | (HGNC's STEP_0 env; see its conda_environment.yml) | python, requests, etc. |
| STEP_1 rbh_rbf_homologs | `aiG-trees_gene_groups-rbh_rbf_homologs` | python, nextflow, blast, numpy, scipy |
| STEP_2 phylogenetic_analysis | `aiG-trees_gene_groups-phylogenetic_analysis` | python, nextflow, mafft, clipkit, fasttree, iqtree, veryfasttree |
| STEP_3 tree_visualization | `aiG-trees_gene_groups-visualization` | python, pip → toytree, toyplot, reportlab |

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "human_proteome_path not found" | Wrong path in STEP_0 config | Verify path to GIGANTIC human T1 proteome |
| STEP_1: "STEP_0 summary TSV not found" | STEP_0 hasn't run | Run STEP_0 first |
| STEP_2: many gene groups skipped (no STEP_1 AGS) | STEP_1 still in progress | Wait, then rerun STEP_2 |
| STEP_3: many skipped (no STEP_2 newicks) | STEP_2 still in progress | Wait, then rerun STEP_3 |

## Adding a new gene-groups source

To process gene groups from a different source (Pfam, InterPro, custom):

```bash
# 1. Copy the master template
cp -r gene_groups_COPYME gene_groups-mysource

# 2. Replace STEP_0-placeholder with source-specific RGS generation
rm -r gene_groups-mysource/STEP_0-placeholder/
mkdir -p gene_groups-mysource/STEP_0-mysource/workflow-COPYME-mysource/
# ... populate STEP_0 with downloader + RGS generator ...

# 3. Create AI_GUIDE-mysource.md describing source specifics
```
