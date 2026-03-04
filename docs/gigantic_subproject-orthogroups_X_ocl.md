# The GIGANTIC Origin-Conservation-Loss System (orthogroups_X_ocl)

The orthogroups_X_ocl subproject performs Origin-Conservation-Loss (OCL) analysis of orthogroups across phylogenetic tree structures. For every orthogroup, it determines the evolutionary origin (MRCA), quantifies conservation across descendant lineages, and distinguishes first-time gene loss from continued absence using the TEMPLATE_03 dual-metric tracking algorithm.

orthogroups_X_ocl depends on three upstream subprojects:
- [trees_species](gigantic_subproject-trees_species.md) for phylogenetic blocks, parent-child relationships, and phylogenetic paths
- [orthogroups](gigantic_subproject-orthogroups.md) for orthogroup assignments (OrthoFinder, OrthoHMM, or Broccoli)
- [genomesDB](gigantic_subproject-genomesDB.md) for species proteomes (sequence data)

---

## Single-Block COPYME Architecture

```
BLOCK_ocl_analysis/     Prepare → Origins → Conservation/Loss → Summaries → Validate
```

The analysis block contains a single `workflow-COPYME` template. Each exploration (combination of species set and orthogroup tool) gets its own COPYME copy:

```
BLOCK_ocl_analysis/
├── workflow-COPYME-ocl_analysis/    # Template
├── workflow-RUN_01-ocl_analysis/    # Species71 X OrthoFinder
├── workflow-RUN_02-ocl_analysis/    # Species71 X OrthoHMM
└── workflow-RUN_03-ocl_analysis/    # Species71 X Broccoli
```

Different runs coexist through the `run_label` configuration parameter, which determines the `output_to_input/` subdirectory name.

---

## The 5-Script Pipeline

```
Process 1: Prepare inputs from upstream subprojects
    |
Process 2: Determine MRCA origin of each orthogroup
    |
Process 3: Quantify conservation and loss (TEMPLATE_03 dual-metric)
    |
Process 4: Generate comprehensive summaries (orthogroups, clades, species)
    |
Process 5: Validate all results (strict fail-fast)
```

Structures are processed in parallel (NextFlow manages parallelism). Within each structure, scripts execute sequentially.

---

## TEMPLATE_03 Dual-Metric Loss Tracking

The core algorithmic contribution of OCL analysis. For each phylogenetic block (parent-to-child transition), the algorithm classifies every orthogroup into one of four event types:

| Event | Parent Has It | Child Has It | Interpretation |
|-------|:------------:|:------------:|----------------|
| **Conservation** | Present | Present | Gene family retained across transition |
| **Loss at Origin** | Present | Absent | First loss event - gene disappears here |
| **Continued Absence** | Absent | Absent | Already lost upstream, absence continues |
| **Loss Coverage** | - | Absent | Total absence = Loss at Origin + Continued Absence |

The distinction between "Loss at Origin" and "Continued Absence" is biologically critical: it separates where gene loss actually occurred from where the absence merely persists.

### Dual Metrics

Two perspectives on each transition:

1. **Phylogenetically inherited** (theoretical): Should the orthogroup be present based on its origin in the tree?
2. **Actually present in species** (genomic reality): Is the orthogroup found in descendant species?

These dual metrics allow computing both:
- **Conservation/Loss Origin Rate**: Among transitions where the parent had the orthogroup, what fraction conserved vs. lost it?
- **Tree Coverage**: What fraction of the total tree shows the orthogroup as present vs. absent?

---

## MRCA Origin Algorithm

For each orthogroup, the origin clade is determined as the Most Recent Common Ancestor of all species containing the orthogroup:

- **Single-species orthogroups** (~86% of all orthogroups): Origin = the species itself
- **Multi-species orthogroups**: Find the intersection of phylogenetic paths for all species, then identify the deepest divergence point

---

## Configuration

Each COPYME copy has its own `ocl_config.yaml`:

```yaml
run_label: "Species71_X_OrthoFinder"
species_set_name: "species71"
orthogroup_tool: "OrthoFinder"

inputs:
  structure_manifest: "INPUT_user/structure_manifest.tsv"
  trees_species_dir: "../../../../trees_species/output_to_input/BLOCK_permutations_and_features"
  orthogroups_dir: "../../../../orthogroups/output_to_input/BLOCK_orthofinder"
  proteomes_dir: "../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes"

include_fasta_in_output: false
```

Key parameters:
- **run_label**: Names the output_to_input subdirectory for multi-tool coexistence
- **orthogroup_tool**: Identifies which clustering tool produced the input data
- **include_fasta_in_output**: When true, embeds protein sequences in summary tables (~1GB per structure)

---

## Output Per Structure

```
OUTPUT_pipeline/structure_NNN/
├── 1-output/    Standardized inputs (blocks, paths, orthogroups, clade mappings)
├── 2-output/    Orthogroup origins + per-clade species files + summary
├── 3-output/    Per-block statistics + per-orthogroup conservation patterns
├── 4-output/    Complete OCL summary + clade statistics + species summaries
├── 5-output/    Validation report + error log + QC metrics
└── logs/        Per-script execution logs
```

The primary downstream file is `4_ai-orthogroups-complete_ocl_summary.tsv`, which contains per-orthogroup origin, conservation rate, loss rate, and species composition in TEMPLATE_03 format.

---

## Downstream Integration

The complete OCL summary is shared via `output_to_input/BLOCK_ocl_analysis/{run_label}/`:

```
output_to_input/BLOCK_ocl_analysis/
├── Species71_X_OrthoFinder/
│   ├── structure_001/
│   │   └── 4_ai-orthogroups-complete_ocl_summary.tsv
│   ├── structure_002/
│   │   └── ...
│   └── structure_105/
└── Species71_X_OrthoHMM/
    └── ...
```

These files are used by downstream subprojects (annotations_X_ocl) that integrate annotation data with conservation patterns.

---

## Validation

Script 005 performs 7 validation checks with strict fail-fast behavior (exit code 1 on ANY failure):

1. **File Integrity** - All expected output files exist and have content
2. **Cross-Script Consistency** - Orthogroup counts match across Scripts 001, 002, and 004
3. **Conservation/Loss Arithmetic** - inherited = conserved + lost for every block
4. **Conservation Rate Bounds** - All rates between 0 and 100, cons + loss = 100
5. **TEMPLATE_03 Metrics** - Event arithmetic, loss coverage, rate sums
6. **Origin in Species Paths** - Origin clade exists in phylogenetic paths
7. **No Orphan Orthogroups** - No orthogroups with zero species

Edge cases (zero inherited transitions, floating-point rounding) are handled explicitly in Scripts 003-004 so they never appear as validation failures.

---

## Environment

```yaml
name: ai_gigantic_orthogroups_X_ocl
dependencies:
  - python>=3.11
  - nextflow>=23.0
  - pyyaml
```

No external bioinformatics tools required. All computation is pure Python 3 with PyYAML for configuration parsing.
