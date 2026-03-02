# gene_sizes - Gene Structure Size Analysis

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

---

## Purpose

Compute gene structure metrics (gene length, exonic length, intronic length, exon count,
protein size, ordered exon sizes, ordered intron sizes) from user-provided CDS interval data
for all species in the GIGANTIC species set. Produces genome-wide statistics, relative size
ranks (quantiles), and cross-species summaries for downstream comparative analyses.

This subproject follows GIGANTIC's established input pattern: the **user** handles species-specific
GFF/GTF parsing and provides standardized gene structure data. The pipeline ingests and processes
what the user provides. Species without gene structure data are gracefully skipped (not a pipeline
failure).

---

## Scientific Context

Gene size (particularly intron size) varies dramatically across animal lineages and correlates
with nervous system complexity. The longest genes in animal genomes are enriched for neuronal
functions (synapse assembly, cell-cell recognition, axon guidance), and this pattern of
relative size ranking is conserved across >1 billion years of evolution.

Key references:
- McCoy & Fire 2020 (BMC Genomics): Intron and gene size expansion across 325 species
- McCoy & Fire 2024 (Current Biology): Gene size rank conservation and neuronal enrichment

### Key Concepts

**Gene length**: Genomic span from gene start to gene end (includes introns).

**Exonic length**: Sum of merged CDS (coding sequence) intervals. UTRs are excluded
because annotation quality varies across species.

**Intronic length**: Gene length minus exonic length.

**Exon count**: Number of distinct CDS intervals after merging overlapping intervals.

**Protein size**: Estimated from CDS length (total CDS nucleotides / 3).

**Relative rank (quantile)**: A gene's percentile position within its genome for a given
metric. Enables cross-species comparison despite enormous absolute size differences.

---

## Directory Structure

```
gene_sizes/
├── README.md                          # This file
├── AI_GUIDE-gene_sizes.md             # Subproject-level AI guidance
├── user_research/                     # User notes and exploratory work
├── research_notebook/                 # Literature summaries and analysis notes
│   ├── ai_research/                   # AI-generated paper summaries
│   └── user_research/                 # User research notes
├── output_to_input/                   # Symlinks to BLOCK output (downstream use)
├── upload_to_server/                  # Curated data for GIGANTIC server
└── BLOCK_analyze_gene_sizes/
    ├── AI_GUIDE-analyze_gene_sizes.md # BLOCK-level AI guidance
    ├── RUN-clean_and_record_subproject.sh
    ├── output_to_input/               # Canonical output location
    └── workflow-COPYME-analyze_gene_sizes/
        ├── README.md                  # Quick start guide
        ├── RUN-workflow.sh            # Run locally
        ├── RUN-workflow.sbatch        # Run on SLURM
        ├── gene_sizes_config.yaml     # User configuration
        ├── INPUT_user/                # User-provided gene structure TSV files
        ├── OUTPUT_pipeline/           # Workflow outputs
        └── ai/                        # Nextflow pipeline and scripts
```

---

## Quick Start

### Step 1: Prepare User Input

Create per-species gene structure TSV files in `INPUT_user/`. One file per species,
named `Genus_species-gene_coordinates.tsv`:

```
Source_Gene_ID	Seqid	Gene_Start	Gene_End	Strand	CDS_Intervals
ENSG00000139618	chr13	32315474	32400266	+	32316422-32316527,32319077-32319325
```

The user extracts this data from species-specific GFF/GTF annotation files. The
`Source_Gene_ID` must match the `g_` field in GIGANTIC proteome FASTA headers.

Also provide the GIGANTIC species list in `INPUT_user/gigantic_species_list.txt`.

### Step 2: Review Configuration
```bash
cd BLOCK_analyze_gene_sizes/workflow-COPYME-analyze_gene_sizes/
# Edit gene_sizes_config.yaml to verify input paths
```

### Step 3: Run the Pipeline
```bash
# Local
bash RUN-workflow.sh

# SLURM cluster
sbatch RUN-workflow.sbatch
```

---

## Input

User-provided per-species TSV files in `INPUT_user/`:

| Column | Description |
|--------|-------------|
| Source_Gene_ID | Gene identifier matching `g_` field in GIGANTIC proteome headers |
| Seqid | Chromosome or scaffold name |
| Gene_Start | Gene start position (bp) |
| Gene_End | Gene end position (bp) |
| Strand | Plus (+) or minus (-) strand |
| CDS_Intervals | Comma-separated start-end pairs for CDS intervals |

Species without input files are gracefully skipped (SKIPPED_NO_DATA).

---

## Output Files

| Directory | Contents |
|-----------|----------|
| `OUTPUT_pipeline/1-output/` | Species processing status, processable species list |
| `OUTPUT_pipeline/2-output/` | Per-species gene metrics (one TSV per species) |
| `OUTPUT_pipeline/3-output/` | Genome-wide statistics and ranked metrics |
| `OUTPUT_pipeline/4-output/` | Cross-species summary table, processing status |

### Outputs Shared Downstream

Via `output_to_input/`:
- `speciesN_gigantic_gene_metrics/` - Per-species gene structure metrics with ranks
- `speciesN_gigantic_gene_sizes_summary/` - Cross-species summary statistics

Where N = count of processable species (those with valid gene structure data).

---

## Species Processing Status

The pipeline uses a three-tier status system:

| Status | Meaning |
|--------|---------|
| PROCESSED | Species has valid gene structure data and was fully processed |
| SKIPPED_NO_DATA | No gene structure file provided by user (graceful skip) |
| SKIPPED_INCOMPLETE | File exists but data failed validation (graceful skip) |

This is a deliberate departure from GIGANTIC's typical fail-hard approach because missing
gene structure data is a data availability limitation, not a pipeline error.

---

## Dependencies

- **Conda environment**: `ai_gigantic_gene_sizes`
- **Tools**: Python 3, Nextflow
- **Upstream subprojects**: genomesDB (species list from STEP_4)

---

## Notes

- Gene structure data is OPTIONAL per species - not all species have GFF/GTF annotations
- UTRs are excluded from all exonic measurements (CDS features only)
- Protein size is estimated from CDS length, not from proteome files
- Overlapping CDS intervals are merged before computing metrics
- Source_Gene_ID links to GIGANTIC identifiers via the `g_` prefix in proteome headers
