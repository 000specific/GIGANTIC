# AI Guide: HUGO HGNC Gene Groups

**For AI Assistants**: Read the parent guide `../AI_GUIDE-trees_gene_groups.md` first for the overall source-based architecture and shared pipeline concepts. Also read `../../AI_GUIDE-project.md` for GIGANTIC project patterns. This guide covers HGNC-specific details.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups-hugo_hgnc/`

**Source**: [HUGO Gene Nomenclature Committee (HGNC)](https://www.genenames.org/) - the worldwide authority for standardizing human gene nomenclature and organizing genes into functional groups.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE-project.md` |
| trees_gene_groups architecture | `../AI_GUIDE-trees_gene_groups.md` |
| HGNC-specific details | This file |
| Homolog discovery details | `STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` |
| Phylogenetic analysis details | `STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` |
| Shared methodology (RBH/RBF) | `../../trees_gene_families/AI_GUIDE-trees_gene_families.md` |

---

## What This Source Does

HUGO HGNC provides a curated hierarchy of human gene groups (families, subfamilies, superfamilies). STEP_0 downloads this data and generates Reference Gene Set (RGS) FASTA files for all protein-coding gene groups by extracting sequences from the GIGANTIC human T1 proteome.

**Scale**: ~1,974 protein-coding gene groups, ranging from 1 to 1,636 sequences per group.

**Key Data Files Downloaded** (from genenames.org):
- `family.csv` - Gene group metadata (ID, name, abbreviation, description)
- `hierarchy.csv` - Direct parent-child relationships
- `hierarchy_closure.csv` - Full transitive hierarchy with distance
- `gene_has_family.csv` - HGNC gene ID to family ID mappings
- `hgnc_gene_groups_all.tsv` - Bulk gene-to-group assignments

---

## HGNC RGS Naming Convention

Follows the same 5-field convention as trees_gene_families RGS files.

### RGS Filename Format

```
rgs_hugo_hgnc-human-{sanitized_group_name}.aa
```

**Examples**:
- `rgs_hugo_hgnc-human-gap_junction_proteins.aa`
- `rgs_hugo_hgnc-human-fascin_family.aa`
- `rgs_hugo_hgnc-human-cytochrome_p450_family_1.aa`

**Components** (dash-separated):
- `rgs_hugo_hgnc` - RGS category identifier (source: HUGO HGNC)
- `human` - Species common name (all HGNC gene groups are human)
- `{sanitized_group_name}` - Group name with spaces/hyphens converted to underscores, lowercase

**Compare with trees_gene_families filenames**:
- `rgs_channel-human-aquaporin_channels.aa`
- `rgs_ligand-human-wnt_ligands.aa`
- `rgs_enzyme-human_fly_worm-kinases.aa`

### RGS Header Format (Per Sequence)

```
>rgs_{sanitized_name}-human-{GENE_SYMBOL}-hgnc_gg{FAMILY_ID}_{Gene_Group_Name}-{PROTEIN_ID}
```

**Example**:
```
>rgs_gap_junction_proteins-human-GJA1-hgnc_gg2_Gap_junction_proteins-NP_000156_1
```

**Compare with trees_gene_families headers**:
```
>rgs_aquaporins-human-MIP-hgnc_gg305_Aquaporin-NP_036196_1
>rgs_wnts-human-WNT1-hgnc_gg360_Wnt_family-NP_005421.1
```

**Fields** (5 dash-separated fields, matching trees_gene_families convention):
1. `rgs_{sanitized_name}` - RGS identifier
2. `human` - Species common name
3. `{GENE_SYMBOL}` - HGNC approved gene symbol
4. `hgnc_gg{ID}_{Gene_Group_Name}` - Source and traceability (HGNC family ID + name)
5. `{PROTEIN_ID}` - NCBI protein accession (dots replaced with underscores)

---

## STEP_0 Pipeline Details

### Three-Script Pipeline

| Script | What It Does |
|--------|-------------|
| `001_ai-python-download_hgnc_gene_group_data.py` | Downloads 5 data files from genenames.org and Google Cloud Storage |
| `002_ai-python-build_aggregated_gene_sets.py` | Builds aggregated gene symbol sets per group using hierarchy closure. Filters for protein-coding genes only. |
| `003_ai-python-generate_rgs_fasta_files.py` | Extracts sequences from human T1 proteome matching gene symbols. Handles hyphen-to-underscore conversion and allele/copy suffixes. |

### Gene Symbol Matching Strategy (Script 003)

The script uses a three-tier matching strategy to find human proteome sequences:

1. **Exact match** - HGNC symbol matches proteome header gene symbol directly
2. **Hyphen-to-underscore** - Converts hyphens to underscores (e.g., `HLA-A` matches `HLA_A`)
3. **Prefix match** - For symbols with allele/copy suffixes (e.g., `HLA_A` matches `HLA_A_6`)

### Protein-Coding Filter (Script 002)

Only includes genes with locus types:
- "gene with protein product" (standard protein-coding)
- "complex locus constituent" (e.g., clustered protocadherins, UDP glucuronosyltransferases)

**Excludes**: pseudogenes, RNA genes, immunoglobulin segments, T-cell receptor segments, endogenous retroviruses

### Hierarchical Aggregation

Parent gene groups include all descendant genes. This means:
- A superfamily group contains genes from all its subfamilies
- 310 of 2,129 HGNC groups have descendants
- Aggregation produces 1,993 groups with protein-coding members

### STEP_0 Statistics (From Latest Run)

| Metric | Value |
|--------|-------|
| Total HGNC gene groups | 2,129 |
| Groups with protein-coding genes | 1,993 |
| RGS files generated | 1,974 |
| Groups skipped (no proteome matches) | 19 |
| Unique gene symbols | 15,293 |

### Gene Group Size Distribution

| Size Range | Count | Example |
|-----------|-------|---------|
| 1 sequence | 83 | - |
| 2-5 sequences | 878 | fascin_family (3) |
| 6-10 sequences | 397 | - |
| 11-20 sequences | 287 | gap_junction_proteins (21) |
| 21-50 sequences | 194 | - |
| 51-100 sequences | 76 | - |
| 101-200 sequences | 31 | - |
| 201-500 sequences | 21 | - |
| 501-1000 sequences | 6 | - |
| 1001+ sequences | 1 | zinc fingers (1,636) |

---

## Directory Structure

```
gene_groups-hugo_hgnc/
├── AI_GUIDE-hugo_hgnc.md                  # THIS FILE
├── INPUT_user/                            # User manifests for batch processing
│   └── gene_group_manifest.tsv            # Which groups to process
│
├── STEP_0-hgnc_gene_groups/               # RGS Generation (runs ONCE)
│   ├── workflow-COPYME-hgnc_gene_groups/  # Template
│   │   ├── START_HERE-user_config.yaml    # Set human_proteome_path
│   │   ├── RUN-workflow.sh               # Run pipeline + create symlinks
│   │   └── ai/
│   │       ├── main.nf                    # NextFlow pipeline definition
│   │       ├── nextflow.config            # NextFlow configuration
│   │       └── scripts/                   # 001, 002, 003 Python scripts
│   └── workflow-RUN_01-hgnc_gene_groups/  # Run instance
│       └── OUTPUT_pipeline/
│           ├── 1-output/                  # Downloaded HGNC data
│           ├── 2-output/                  # Aggregated gene sets + metadata
│           └── 3-output/                  # RGS FASTA files + manifests
│               ├── rgs_fastas/            # ~1,974 .aa files
│               ├── 3_ai-rgs_generation_manifest.tsv
│               └── 3_ai-rgs_generation_summary.tsv
│
├── STEP_1-homolog_discovery/              # Per-Gene-Group Homolog Discovery
│   ├── AI_GUIDE-homolog_discovery.md
│   ├── README.md
│   ├── workflow-COPYME-rbh_rbf_homologs/  # Template (copy into gene_group-X/)
│   ├── gene_group-gap_junction_proteins/  # Example gene group (created by burst script)
│   │   └── workflow-RUN_01-rbh_rbf_homologs/
│   └── gene_group-fascin_family/
│       └── workflow-RUN_01-rbh_rbf_homologs/
│
└── STEP_2-phylogenetic_analysis/          # Per-Gene-Group Tree Building
    ├── AI_GUIDE-phylogenetic_analysis.md
    ├── README.md
    ├── workflow-COPYME-phylogenetic_analysis/  # Template
    ├── gene_group-gap_junction_proteins/
    │   └── workflow-RUN_01-phylogenetic_analysis/
    └── gene_group-fascin_family/
        └── workflow-RUN_01-phylogenetic_analysis/
```

---

## Configuration Details

### STEP_0 Configuration (`START_HERE-user_config.yaml`)

| Setting | Description | User Edits? |
|---------|-------------|-------------|
| `inputs.human_proteome_path` | Path to GIGANTIC human T1 proteome | **YES** |
| `rgs.date_stamp` | Date stamp for filenames (empty = today) | Optional |
| `cpus`, `memory_gb`, `time_hours` | Resources (STEP_0 is lightweight) | Optional |
| `execution_mode` | "local" or "slurm" | **YES** (SLURM users) |
| `slurm_account`, `slurm_qos` | SLURM settings | **YES** (SLURM users) |

### STEP_1 Configuration

See `STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` and the `workflow-COPYME-rbh_rbf_homologs/START_HERE-user_config.yaml`.

Key settings for HGNC gene groups:
- `gene_family.name` - Set to the HGNC sanitized group name (e.g., `gap_junction_proteins`)
- `gene_family.rgs_file` - Path to RGS from STEP_0 output (e.g., `INPUT_user/rgs-hgnc_gg314-gap_junction_proteins.aa`)
- `inputs.blast_databases_dir` - Path to genomesDB BLAST databases
- `inputs.species_keeper_list` - Which species to include

### STEP_2 Configuration

See `STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` and the `workflow-COPYME-phylogenetic_analysis/START_HERE-user_config.yaml`.

---

## Data Flow: STEP_0 to STEP_1

STEP_0 generates RGS files in `OUTPUT_pipeline/3-output/rgs_fastas/` and symlinks them to `output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/rgs_fastas/`.

To use an RGS file in STEP_1:
1. The burst script (or manual setup) copies the relevant RGS file into the gene group's `INPUT_user/` directory
2. The `START_HERE-user_config.yaml` is configured with the RGS filename
3. STEP_1 validates the RGS and proceeds with BLAST searches

**Path from STEP_1 gene_group-X/workflow-RUN_01 to STEP_0 RGS files**:
```
../../../STEP_0-hgnc_gene_groups/workflow-RUN_01-hgnc_gene_groups/OUTPUT_pipeline/3-output/rgs_fastas/
```

Or via output_to_input:
```
../../../../output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/rgs_fastas/
```

---

## Symlink Structure

STEP_0's `RUN-workflow.sh` creates symlinks at:
```
trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/
├── rgs_fastas/                               # 1,974 symlinks to RGS .aa files
├── 3_ai-rgs_generation_manifest.tsv          # All groups (SUCCESS/SKIPPED)
└── 3_ai-rgs_generation_summary.tsv           # Successfully generated only
```

Symlink targets are **relative paths** from the symlink location back to the real files in `workflow-RUN_01/OUTPUT_pipeline/3-output/`.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "human_proteome_path not found" | Wrong path in STEP_0 config | Verify path to GIGANTIC human T1 proteome .aa file |
| "Download failed" | Network issue or genenames.org unavailable | Retry; check internet connection |
| "0 RGS files generated" | Proteome header format mismatch | Verify proteome uses GIGANTIC header format: `>g_SYMBOL-t_...-p_...-n_...` |
| "19 groups skipped" | Normal - some HGNC groups have no proteome matches | Check manifest for SKIPPED entries to understand why |
| Symlinks broken | STEP_0 output moved or deleted | Re-run STEP_0 RUN-workflow.sh |

---

## Batch Processing Considerations

With ~1,974 gene groups, consider:

1. **Size filtering** - Very large groups (500+ sequences) need more BLAST time and memory. Start with smaller groups.
2. **Priority sets** - Run biologically interesting groups first (ion channels, receptors, kinases)
3. **Resource planning** - Each STEP_1 run uses ~50 CPUs, ~187 GB RAM, up to 96 hours
4. **Manifest-driven** - Use `INPUT_user/gene_group_manifest.tsv` to specify exactly which groups to process

### Example Gene Group Selection Strategy

```
# Small groups (2-10 sequences) - fast, good for testing
# Medium groups (11-50 sequences) - standard analysis
# Large groups (51-200 sequences) - need more resources
# Very large groups (200+ sequences) - consider VeryFastTree in STEP_2
# Huge groups (1000+ sequences) - may need special handling
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `AI_GUIDE-hugo_hgnc.md` | This guide | Read only |
| `STEP_0-*/workflow-*/START_HERE-user_config.yaml` | Human proteome path, resources | **YES** |
| `STEP_0-*/workflow-*/OUTPUT_pipeline/3-output/3_ai-rgs_generation_summary.tsv` | List of generated RGS files | Read only |
| `STEP_0-*/workflow-*/OUTPUT_pipeline/3-output/3_ai-rgs_generation_manifest.tsv` | Full manifest with SUCCESS/SKIPPED | Read only |
| `INPUT_user/gene_group_manifest.tsv` | Which gene groups to process in batch | **YES** |
| `STEP_1-*/workflow-COPYME-*/START_HERE-user_config.yaml` | Gene group name, BLAST settings | **YES** |
| `STEP_2-*/workflow-COPYME-*/START_HERE-user_config.yaml` | Tree methods, alignment settings | **YES** |
