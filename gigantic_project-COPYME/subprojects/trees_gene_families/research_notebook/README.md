# research_notebook - RGS Preparation and Exploratory Work

Personal workspace for preparing Reference Gene Set (RGS) FASTA files and exploratory analyses related to trees_gene_families.

## Purpose

The research_notebook is the **staging area** where RGS files are sourced, curated, reformatted, and organized before being fed into the gene family analysis pipeline. This is the critical step that happens **before STEP_1** (homolog discovery).

## RGS Preparation Workflow

```
research_notebook/
└── rgs_from_before/
    ├── rgs_sources/                    # Raw/original RGS files from various databases
    │   ├── <gene_family>-rgs.aa        # Individual source files (varied formats)
    │   └── 000_todo-gene_families/     # Gene families needing processing
    │       ├── processing_rgs_kinome/  # Kinome processing pipeline
    │       └── processing_rgs_phosphatome/  # Phosphatome processing pipeline
    │
    ├── rgs_for_trees/                  # Formatted RGS files ready for analysis
    │   ├── rgs_<category>-<source>-<description>.aa  # GIGANTIC-format RGS files
    │   ├── new_rgs_25mar2026/          # Batch of new RGS files (channels)
    │   └── new_rgs_31mar2026/          # Batch of new RGS files (TRP, kinome, phosphatome, etc.)
    │       ├── convert_rgs_to_gigantic_format.py  # Conversion script
    │       ├── rgs_*.aa                # Formatted output files
    │       └── mapping-*.tsv           # Original-to-new header mappings
    │
    └── species_keeper_list-species70.tsv  # Species list for filtering
```

## Data Flow: RGS to Gene Family Analysis

```
1. Source RGS files          rgs_sources/<various formats>
        |
2. Format to GIGANTIC        convert_rgs_to_gigantic_format.py
        |
3. Formatted RGS files       rgs_for_trees/new_rgs_*/<GIGANTIC format>.aa
        |
4. Burst setup script        RUN-setup_and_submit_*_burst.sh
        |
5. Gene family directories   gene_family-<name>/STEP_1/workflow-RUN_1/INPUT_user/
        |
6. Pipeline execution        STEP_1 (homolog discovery) -> STEP_2 (phylogenetic analysis)
```

## GIGANTIC RGS File Naming Convention

**Filename**: `rgs_<category>-<source_species>-<description>.aa`

| Component | Description | Examples |
|-----------|-------------|----------|
| category | Functional category | `channel`, `receptor`, `enzyme`, `ligand`, `tf`, `transporter`, `structure` |
| source_species | Species in the RGS (underscore-separated) | `human`, `human_fly_worm`, `human_mouse_fly_worm_anemone` |
| description | Descriptive name (full words, underscores) | `kinases`, `transient_receptor_potential_cation_channels` |

**Examples**:
- `rgs_channel-human_mouse_fly_worm_anemone-transient_receptor_potential_cation_channels.aa`
- `rgs_enzyme-human_fly_worm-kinases_AGC.aa`
- `rgs_receptor-human-glutamate_metabotropic_receptors.aa`
- `rgs_transporter-human-solute_carriers.aa`

## GIGANTIC RGS Header Format

**Header**: `>rgs_<family_subfamily>-<species>-<gene>-<source>-<accession>`

Each dash-separated field contains only letters, numbers, and underscores (no dots, dashes, or special characters within fields).

| Field | Description | Examples |
|-------|-------------|----------|
| family_subfamily | Gene family with optional subfamily hierarchy | `kinases_AGC_Akt`, `transient_receptor_potential_cation_TRPML`, `phosphatases_CC1_CC1_DSP_CDC14` |
| species | Source organism (short name) | `human`, `fly`, `worm`, `mouse` |
| gene | Gene symbol or identifier | `AKT1`, `MCLN1`, `TRPC_aTRPC_TRPC1` |
| source | Database or source | `uniprot`, `kinase_database`, `phosphatome_database`, `hgnc` |
| accession | Sequence identifier | `Q9GZU1`, `Hs_AKT1_AA`, `NP_000830_2` |

**Examples**:
```
>rgs_kinases_AGC_Akt-human-AKT1-kinase_database-Hs_AKT1_AA
>rgs_transient_receptor_potential_cation_TRPML-human-TRPML_TRPML_MCLN1-uniprot-Q9GZU1
>rgs_phosphatases_AP_AP_AP_AP-human-ALPI-phosphatome_database-Hsap_ALPI
>rgs_glutamate_metabotropic_receptors-human-GRM1-hgnc_gg281_Glutamate_metabotropic_receptors-XP_011534084_1
```

## Header Mapping Files

Each batch of reformatted RGS files includes TSV mapping files (`mapping-*.tsv`) that record the original header alongside the new GIGANTIC header. These provide full traceability back to source databases.

## Not Tracked by Git

Contents of research_notebook/ are personal/exploratory data and are excluded from version control via `.gitignore`. Only this README and `.gitkeep` are tracked.

## See Also

- `RUN-setup_and_submit_step1_burst.sh` - Burst script for original RGS set
- `RUN-setup_and_submit_new_rgs_31mar2026_burst.sh` - Burst script for new RGS set (TRP, kinome, phosphatome, solute carriers, metabotropic glutamate receptors)
- `gene_family_COPYME/` - Template used by burst scripts to create gene family directories
