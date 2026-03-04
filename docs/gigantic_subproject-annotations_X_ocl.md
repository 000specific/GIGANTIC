# The GIGANTIC Origin-Conservation-Loss System (annotations_X_ocl)

The annotations_X_ocl subproject performs Origin-Conservation-Loss (OCL) analysis of annotation groups ("annogroups") across phylogenetic tree structures. Annogroups are the annotation-centric counterpart to orthogroups: sets of proteins grouped by shared annotation pattern from a specific database. For every annogroup, the pipeline determines the evolutionary origin (MRCA), quantifies conservation across descendant lineages, and distinguishes first-time loss from continued absence using the TEMPLATE_03 dual-metric tracking algorithm.

annotations_X_ocl depends on two upstream subprojects:
- [trees_species](gigantic_subproject-trees_species.md) for phylogenetic blocks, parent-child relationships, and phylogenetic paths
- [annotations_hmms](gigantic_subproject-annotations_hmms.md) for standardized annotation databases (24 databases across 5 annotation tools)

---

## Annogroup Concept

Annogroups are sets of proteins that share the same annotation pattern from a given database. They encompass diverse grouping logic: some annotations are explicitly evolutionary (protein domain families), others are functional but not evolutionary (subcellular localization), and others are structural features (transmembrane domains).

### Annogroup IDs

**Format**: `annogroup_{db}_N`

Where `{db}` is the annotation database name (pfam, gene3d, deeploc, etc.) and `N` is a sequential integer unique within each database. The database name prevents collisions across independent COPYME runs.

All detail (subtype, accessions, species, sequences) lives in the annogroup map — the ID is a handle.

### The 3 Annogroup Subtypes

Each subtype is a direct evaluation of an individual protein by the annotation tool:

| Subtype | Groups | Basis |
|---------|--------|-------|
| **single** | Proteins with exactly one annotation from this database | Tool reported one hit |
| **combo** | Proteins with identical multi-annotation architecture | Tool reported multiple hits |
| **zero** | Individual proteins with zero annotations (singletons) | Tool reported no hits |

**Domain databases** (pfam, gene3d, superfamily, etc.) use all 3 subtypes. **Simple databases** (deeploc, signalp, tmbed, metapredict) use `single` only (each protein gets one prediction).

Higher-level groupings (clans, "all proteins with PF00069", supergroups) are NOT annogroups — they are downstream processing that operates on annogroups + additional knowledge.

### The Annogroup Map

Script 001 produces `1_ai-annogroup_map.tsv` — the lookup table linking IDs to full details:

| Column | Description |
|--------|-------------|
| Annogroup_ID | Identifier format `annogroup_{db}_N` |
| Annogroup_Subtype | single, combo, or zero |
| Annotation_Database | Name of annotation database |
| Annotation_Accessions | Comma-delimited annotation accessions or unannotated identifier |
| Species_Count | Number of unique species with at least one member sequence |
| Sequence_Count | Total number of member sequences |
| Species_List | Comma-delimited list of species names |
| Sequence_IDs | Comma-delimited list of GIGANTIC sequence identifiers |

---

## Single-Block COPYME Architecture

```
BLOCK_ocl_analysis/     Create Annogroups → Origins → Conservation/Loss → Summaries → Validate
```

Each exploration (one combination of species set and annotation database) gets its own COPYME copy:

```
BLOCK_ocl_analysis/
├── workflow-COPYME-ocl_analysis/    # Template
├── workflow-RUN_01-ocl_analysis/    # Species71 Pfam
├── workflow-RUN_02-ocl_analysis/    # Species71 Gene3D
├── workflow-RUN_03-ocl_analysis/    # Species71 DeepLoc
└── workflow-RUN_04-ocl_analysis/    # Species71 SignalP
```

Different runs coexist through the `run_label` configuration parameter, which determines the `output_to_input/` subdirectory name.

---

## The 5-Script Pipeline

```
Process 1: Create annogroups from annotation files + annogroup map
    |
Process 2: Determine MRCA origin of each annogroup
    |
Process 3: Quantify conservation and loss (TEMPLATE_03 dual-metric)
    |
Process 4: Generate comprehensive summaries (per-subtype + all-types + clade + species)
    |
Process 5: Validate all results (strict fail-fast, 8 checks)
```

Structures are processed in parallel (NextFlow manages parallelism). Within each structure, scripts execute sequentially.

---

## TEMPLATE_03 Dual-Metric Loss Tracking

Same algorithm as orthogroups_X_ocl. For each phylogenetic block (parent-to-child transition), the algorithm classifies every annogroup into one of four event types:

| Event | Parent Has It | Child Has It | Interpretation |
|-------|:------------:|:------------:|----------------|
| **Conservation** | Present | Present | Annotation group retained across transition |
| **Loss at Origin** | Present | Absent | First loss event - annotation disappears here |
| **Continued Absence** | Absent | Absent | Already lost upstream, absence continues |
| **Loss Coverage** | - | Absent | Total absence = Loss at Origin + Continued Absence |

---

## MRCA Origin Algorithm

Same algorithm as orthogroups_X_ocl. Single-species annogroups get the species as origin. Multi-species annogroups use phylogenetic path intersection to find the deepest divergence point.

---

## Configuration

Each COPYME copy has its own `ocl_config.yaml`:

```yaml
run_label: "Species71_pfam"
species_set_name: "species71"
annotation_database: "pfam"

annogroup_subtypes:
  - "single"
  - "combo"
  - "zero"

inputs:
  structure_manifest: "INPUT_user/structure_manifest.tsv"
  trees_species_dir: "../../../../trees_species/output_to_input/BLOCK_permutations_and_features"
  annotations_dir: "../../../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/annotation_databases/database_pfam"
```

Key parameters:
- **run_label**: Names the output_to_input subdirectory for multi-database coexistence
- **annotation_database**: Identifies which database the annogroups are built from
- **annogroup_subtypes**: Which subtypes to generate (domain databases: all 3; simple databases: single only)

---

## Output Per Structure

```
OUTPUT_pipeline/structure_NNN/
├── 1-output/    Annogroup map + per-subtype files + phylogenetic data
├── 2-output/    Annogroup origins + per-clade files + summary
├── 3-output/    Per-block statistics + per-annogroup conservation patterns
├── 4-output/    Complete OCL summaries (per-subtype + all-types) + clade + species stats
├── 5-output/    Validation report + error log + QC metrics
└── logs/        Per-script execution logs
```

The primary downstream file is `4_ai-annogroups-complete_ocl_summary-all_types.tsv`, which integrates all subtypes into a single comprehensive table.

---

## Downstream Integration

The complete OCL summary is shared via `output_to_input/BLOCK_ocl_analysis/{run_label}/`:

```
output_to_input/BLOCK_ocl_analysis/
├── Species71_pfam/
│   ├── structure_001/
│   │   └── 4_ai-annogroups-complete_ocl_summary-all_types.tsv
│   ├── structure_002/
│   │   └── ...
│   └── structure_105/
├── Species71_gene3d/
│   └── ...
└── Species71_deeploc/
    └── ...
```

---

## Validation

Script 005 performs 8 validation checks with strict fail-fast behavior (exit code 1 on ANY failure):

1. **File Integrity** - All expected output files exist and have content
2. **Cross-Script Consistency** - Annogroup counts match across Scripts 001, 002, and 004
3. **Conservation/Loss Arithmetic** - inherited = conserved + lost for every block
4. **Conservation Rate Bounds** - All rates between 0 and 100, cons + loss = 100
5. **TEMPLATE_03 Metrics** - Event arithmetic, loss coverage, rate sums
6. **Origin in Species Paths** - Origin clade exists in phylogenetic paths
7. **No Orphan Annogroups** - No annogroups with zero species
8. **Annogroup Subtype Consistency** - No duplicate IDs within database, ID format validation

Edge cases (zero inherited transitions, floating-point rounding) are handled explicitly in Scripts 003-004 so they never appear as validation failures.

---

## Relationship to orthogroups_X_ocl

Both subprojects share the same TEMPLATE_03 algorithm and pipeline structure. The differences:

| Aspect | orthogroups_X_ocl | annotations_X_ocl |
|--------|-------------------|-------------------|
| Input units | Orthogroups (clustering-based) | Annogroups (annotation-based) |
| Input source | orthogroups subproject | annotations_hmms subproject |
| Subtypes | None | single, combo, zero |
| Scripts per structure | 5 | 5 |
| Validation checks | 7 | 8 (adds subtype consistency) |
| COPYME copies per tool | 1 per clustering method | 1 per annotation database (up to 24) |

---

## Environment

```yaml
name: ai_gigantic_annotations_X_ocl
dependencies:
  - python>=3.11
  - nextflow>=23.0
  - pyyaml
```

No external bioinformatics tools required. All computation is pure Python 3 with PyYAML for configuration parsing.
