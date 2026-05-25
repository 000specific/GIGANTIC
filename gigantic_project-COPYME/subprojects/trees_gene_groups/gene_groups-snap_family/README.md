# gene_groups_COPYME — Master Template for trees_gene_groups Sources

This is the master template directory for the `trees_gene_groups` subproject. To
analyze gene groups from a new classification source (HUGO HGNC, Pfam clans, a
custom list, etc.), copy this entire directory and customize STEP_0 for that
source.

## What's in here

```
gene_groups_COPYME/
├── README.md                                          (this file)
├── STEP_0-placeholder/                                # empty — replace with source-specific STEP_0
├── STEP_1-homolog_discovery/                          # shared RBH/RBF homolog discovery
│   ├── AI_GUIDE-homolog_discovery.md
│   ├── README.md
│   └── workflow-COPYME-rbh_rbf_homologs/              # the STEP_1 workflow template
│       ├── RUN-workflow.sh                            # the SINGLE user-runnable script
│       ├── START_HERE-user_config.yaml                # user config
│       ├── INPUT_user/
│       └── ai/                                        # main.nf, nextflow.config, scripts, conda_environment.yml
├── STEP_2-phylogenetic_analysis/                      # shared phylogenetic analysis
│   ├── AI_GUIDE-phylogenetic_analysis.md
│   ├── README.md
│   └── workflow-COPYME-phylogenetic_analysis/         # the STEP_2 workflow template
│       └── (same layout as STEP_1's workflow-COPYME-*)
└── STEP_3-tree_visualization/                         # shared tree rendering
    ├── AI_GUIDE-phylogenetic_visualization.md
    ├── README.md
    └── workflow-COPYME-tree_visualization/            # the STEP_3 workflow template
        └── (same layout)
```

## How a user creates a new source

```bash
# 1. Copy the master template to a per-source instance
cp -r gene_groups_COPYME gene_groups-mysource

# 2. Replace STEP_0-placeholder with source-specific RGS generation code
rm -r gene_groups-mysource/STEP_0-placeholder/
mkdir -p gene_groups-mysource/STEP_0-mysource/workflow-COPYME-mysource/
# ... populate with the source's STEP_0 pipeline ...

# 3. Per-source AI_GUIDE
# Create gene_groups-mysource/AI_GUIDE-mysource.md describing source specifics

# 4. Edit each STEP's START_HERE-user_config.yaml inside the per-source instance
#    to point at the right STEP_0 output and pick execution_mode (local | slurm-standard | slurm-burst)
```

## How a user runs a STEP (per source)

STEPs are sequentially dependent: STEP_0 → STEP_1 → STEP_2 → STEP_3.

Inside a per-source instance (e.g., `gene_groups-<INSTANCE>/`), for each STEP:

```bash
# 1. Copy the STEP's COPYME → a RUN_NN instance at the same level
cd gene_groups-<INSTANCE>/STEP_1-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs

# 2. Edit the RUN's START_HERE-user_config.yaml
cd workflow-RUN_1-rbh_rbf_homologs
# (set execution_mode, paths, etc.)

# 3. Run the single user-runnable script
bash RUN-workflow.sh
```

For STEP_1, STEP_2, STEP_3 the per-STEP `RUN-workflow.sh` is an **orchestrator**:
- Creates its conda env once on the login node
- Iterates over gene groups from the STEP_0 summary TSV
- Creates one `gene_group-X/workflow-RUN_01-<stepname>/` sub-instance per gene group as siblings at the STEP level
- Dispatches each per `execution_mode`:
  - `local` — sequential nextflow/python runs
  - `slurm-standard` — one sbatch per gene group (standard QOS)
  - `slurm-burst` — chunked into blocks (burst QOS), block size per tier

## The two-workflow pattern at the subproject level

The `trees_gene_groups/` subproject has exactly two workflows:

| Workflow | Purpose |
|----------|---------|
| `gene_groups_COPYME/` | This master template (never run from here) |
| `gene_groups-<source>/` | Per-source instance (copy of master + source-specific STEP_0) |

To add a new source (Pfam, InterPro, custom): make another `gene_groups-<source>/`.

## See also

- `../AI_GUIDE-trees_gene_groups.md` — subproject-level AI guide
- `../README.md` — subproject overview
- `../gene_groups-<INSTANCE>/` — current source instance (HUGO HGNC gene groups)
