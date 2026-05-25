# The GIGANTIC Gene Size Analysis System (gene_sizes)

The gene_sizes subproject computes gene structure metrics across all GIGANTIC species and enables cross-species comparison of gene size distributions using quantile-based ranking. Gene size variation across animal lineages has been linked to nervous system complexity, motivating systematic characterization across the GIGANTIC species set.

gene_sizes depends on the [genomesDB subproject](gigantic_subproject-genomesDB.md) for GIGANTIC proteome files (used for identifier linkage) and a GIGANTIC species list.

---

## Single-Block Architecture

```
BLOCK_analyze_gene_sizes/     Validate → Extract metrics → Rank → Cross-species summary
```

The analysis block follows a four-process pipeline:

```
Process 1: Validate inputs and classify species (3-tier status)
    |
Process 2: Extract 8 per-gene metrics (parallelized across species)
    |
Process 3: Compute genome-wide statistics + quantile ranks (parallelized)
    |
Process 4: Compile cross-species summary table + organize outputs
```

**No external bioinformatics tools**: All computation is pure Python 3 using only standard library modules. The pipeline operates on pre-extracted gene coordinates rather than raw annotation files.

---

## Input Design: User-Provided CDS Intervals

### Why Users Prepare Input Files

GFF and GTF formats vary substantially across genome annotation sources (NCBI, Ensembl, species-specific databases). Rather than building a brittle automated parser, GIGANTIC places the species-specific parsing burden on the user, who understands their annotation format.

### Input File Format

**Filename**: `Genus_species-gene_coordinates.tsv`

**Location**: `INPUT_user/` directory

**Format** (6 columns, tab-separated):

| Column | Description |
|--------|-------------|
| Source_Gene_ID | Gene identifier from the source annotation |
| Seqid | Chromosome or scaffold identifier |
| Gene_Start | Gene start coordinate (1-based) |
| Gene_End | Gene end coordinate (1-based, inclusive) |
| Strand | `+` or `-` |
| CDS_Intervals | Comma-separated start-end pairs (e.g., `100-200,300-450,600-800`) |

**Example**:
```
Source_Gene_ID	Seqid	Gene_Start	Gene_End	Strand	CDS_Intervals
ENSG00000139618	chr13	32315474	32400266	+	32316422-32316527,32319077-32319325,32325076-32325184
```

**UTR exclusion**: CDS intervals represent coding sequence boundaries only. UTR annotations are incomplete or absent in many assemblies, and including them would introduce systematic bias.

**CDS interval merging**: When multiple transcript isoforms overlap, the pipeline merges overlapping intervals before computing exonic length to avoid double-counting.

---

## Three-Tier Species Processing

Not all species in a GIGANTIC project will have gene structure annotations. The pipeline uses graceful degradation rather than failing on missing data.

| Status | Meaning | When It Happens |
|--------|---------|-----------------|
| **PROCESSED** | Valid gene structure file, all metrics computed | File exists and passed validation |
| **SKIPPED_NO_DATA** | No input file provided | User hasn't created TSV for this species |
| **SKIPPED_INCOMPLETE** | File exists but failed validation | Wrong columns, invalid coordinates, malformed CDS |

The pipeline exits with an error only if **zero** species have valid data. Output directories are named with the count of processed species (e.g., `speciesN_gigantic_gene_metrics/`).

---

## Process 1: Input Validation and Species Classification

**Script**: `001_ai-python-validate_gene_size_inputs.py`

### Validation Checks

For each species file:

- File exists (→ SKIPPED_NO_DATA if missing)
- Contains expected six columns
- Gene start/end are valid integers with start < end
- Strand is `+` or `-`
- CDS intervals parse correctly (comma-separated `start-end` pairs, each start < end)

### Outputs

| File | Description |
|------|-------------|
| `1_ai-species_processing_status.tsv` | Every species with status, reason, gene count |
| `1_ai-processable_species_list.txt` | Only PROCESSED species (one per line) |
| `1_ai-species_count.txt` | Integer count of processable species |

---

## Process 2: Gene Metric Extraction

**Script**: `002_ai-python-extract_gene_metrics.py`

Parallelized across species via Nextflow channels.

### The Eight Metrics

| # | Metric | Calculation | Ranked? |
|---|--------|-------------|---------|
| 1 | **Gene Length** | `end - start + 1` (genomic span in bp) | Yes |
| 2 | **Exonic Length** | Sum of merged CDS interval lengths (bp) | Yes |
| 3 | **Intronic Length** | Gene Length minus Exonic Length (bp) | Yes |
| 4 | **Exon Count** | Number of merged CDS intervals | Yes |
| 5 | **CDS Length** | Equal to Exonic Length (total coding bp) | No |
| 6 | **Protein Size** | CDS Length // 3 (predicted amino acids) | Yes |
| 7 | **Exon Sizes Ordered** | Individual exon sizes, 5'-to-3' transcript order | No |
| 8 | **Intron Sizes Ordered** | Individual intron sizes, 5'-to-3' transcript order | No |

### CDS Interval Merging

Overlapping intervals are merged using a sort-and-sweep algorithm: intervals are sorted by start position, then consecutive intervals that overlap or are adjacent are merged into a single interval.

### Strand-Aware Ordering

- **+ strand**: Genomic low-to-high = 5'-to-3' (kept as-is)
- **- strand**: Lists are reversed so the first element is always the 5'-most exon/intron

This preserves biologically meaningful positional information such as the known enrichment of conserved sequences in 5' introns.

### GIGANTIC Identifier Linkage

When a GIGANTIC proteome file is available, each source gene identifier is linked to its corresponding GIGANTIC identifier by parsing proteome FASTA headers for the `g_` gene identifier prefix. This enables downstream integration with orthogroups, annotations, and other subprojects.

### Output

14-column TSV per species: Source_Gene_ID, GIGANTIC_Identifier, Seqid, Start, End, Strand, Gene_Length, Exonic_Length, Intronic_Length, Exon_Count, CDS_Length, Protein_Size, Exon_Sizes_Ordered, Intron_Sizes_Ordered.

---

## Process 3: Genome-Wide Statistics and Quantile Ranking

**Script**: `003_ai-python-compute_genome_wide_statistics.py`

Parallelized across species.

### Quantile Ranking

Each gene receives a quantile rank (0.0 to 1.0) within its genome for five metrics: gene length, exonic length, intronic length, exon count, and protein size. Ranks are computed using the **average rank method** to handle ties.

**Why quantile ranks?** A gene in the 95th percentile for gene length in a compact genome (e.g., *C. elegans*) and a gene in the 95th percentile in an expanded genome (e.g., *Homo sapiens*) occupy equivalent positions within their respective genomes, regardless of orders-of-magnitude difference in absolute size.

The two ordered-size columns (exon sizes, intron sizes) are carried through as structural data but are not ranked, as they represent multi-value fields rather than single scalar metrics.

### Genome-Wide Summary Statistics

For each of the five ranked metrics, seven statistics are computed:

| Statistic | Description |
|-----------|-------------|
| Gene_Count | Number of genes analyzed |
| Mean | Arithmetic mean |
| Median | Middle value (average of two middle if even count) |
| Minimum | Smallest value |
| Maximum | Largest value |
| Percentile_25 | 25th percentile (nearest rank method) |
| Percentile_75 | 75th percentile (nearest rank method) |

### Outputs

| File | Description |
|------|-------------|
| `3_ai-ranked_gene_metrics-{Species}.tsv` | Original 14 columns + 5 rank columns = 19 columns |
| `3_ai-genome_summary-{Species}.tsv` | 5 metrics x 7 statistics per species |

---

## Process 4: Cross-Species Summary Compilation

**Script**: `004_ai-python-compile_cross_species_summary.py`

### Cross-Species Summary Table

Collects all per-species genome summaries into a wide-format table:

- **Rows**: One per processed species (sorted alphabetically)
- **Columns**: Genus_Species + 25 data columns (5 metrics x 5 statistics)
- **Statistics included**: Gene count, median, mean, minimum, maximum
- **Statistics excluded**: Percentile_25 and Percentile_75 (available in per-species summaries but not carried into the cross-species overview)

### Output Organization

```
4-output/
├── 4_ai-cross_species_summary.tsv
├── 4_ai-species_processing_status.tsv
├── speciesN_gigantic_gene_metrics/
│   ├── 3_ai-ranked_gene_metrics-Homo_sapiens.tsv
│   ├── 3_ai-ranked_gene_metrics-Mus_musculus.tsv
│   └── ...
└── speciesN_gigantic_gene_sizes_summary/
    ├── 4_ai-cross_species_summary.tsv
    ├── 3_ai-genome_summary-Homo_sapiens.tsv
    ├── 3_ai-genome_summary-Mus_musculus.tsv
    ├── 4_ai-species_processing_status.tsv
    └── ...
```

Where N = number of processed species (e.g., `speciesN_gigantic_gene_metrics/`).

---

## Data Flow

### Input

```
INPUT_user/
├── gigantic_species_list.txt                    (from genomesDB STEP_4)
├── Homo_sapiens-gene_coordinates.tsv            (user-prepared)
├── Mus_musculus-gene_coordinates.tsv
└── ...
```

Species list and optional proteome directory path are configured in `gene_sizes_config.yaml`.

### Output

```
gene_sizes/output_to_input/
├── speciesN_gigantic_gene_metrics/              (ranked metrics per species)
└── speciesN_gigantic_gene_sizes_summary/         (cross-species + per-species summaries)
```

### Downstream Consumers

| Subproject | What It Uses |
|------------|-------------|
| **gene_sizes_X_integrations** | Gene metrics + orthogroup pairs for dN/dS analysis, rank deviation, functional enrichment |
| **orthogroups** integration | Gene sizes linked to ortholog groups via GIGANTIC identifiers for orthologous gene size comparison |
| **annotations_hmms** integration | Gene size quantile ranks + functional annotations for size-function enrichment |

---

## Configuration

Edit `gene_sizes_config.yaml`:

```yaml
inputs:
  input_user_dir: "INPUT_user"
  gigantic_species_list: "INPUT_user/gigantic_species_list.txt"
  proteome_dir: ""                    # Optional: path to .aa files for ID linkage

output:
  base_dir: "OUTPUT_pipeline"
```

---

## Running

```bash
cd subprojects/gene_sizes/BLOCK_analyze_gene_sizes/workflow-COPYME-analyze_gene_sizes/
# Prepare input files
cp your_species_list.txt INPUT_user/gigantic_species_list.txt
cp your_gene_coordinate_files INPUT_user/
nano gene_sizes_config.yaml
# Execute
bash RUN-workflow.sh          # Local
sbatch RUN-workflow.sbatch    # SLURM
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Zero processable species` | No valid gene structure files in INPUT_user/ | Check file naming (`Genus_species-gene_coordinates.tsv`) and format |
| `SKIPPED_INCOMPLETE` for a species | File exists but failed validation | Check column count (need 6), coordinate format, CDS interval syntax |
| `No GIGANTIC identifier found` | Proteome file missing or gene ID mismatch | Check proteome_dir config; verify Source_Gene_ID matches `g_` field in proteome headers |
| Cross-species summary has fewer species than expected | Some species classified as SKIPPED | Check `4_ai-species_processing_status.tsv` for per-species status and reasons |
| All genes show 0 intronic length | CDS intervals span entire gene region | Verify CDS intervals represent exons only, not full gene span |

---

## External Tools and References

| Tool | Purpose | Citation | Repository |
|------|---------|----------|------------|
| **Nextflow** | Workflow orchestration | Di Tommaso et al. (2017) *Nature Biotechnology* 35:316-319. [DOI](https://doi.org/10.1038/nbt.3820) | [github.com/nextflow-io/nextflow](https://github.com/nextflow-io/nextflow) |

All computation is performed using Python 3 standard library only. No external bioinformatics tools are required. The `ai_gigantic_gene_sizes` conda environment provides Python and Nextflow.

---

*For AI assistant guidance, see `AI_GUIDE-gene_sizes.md` and workflow-level `ai/AI_GUIDE-gene_sizes_workflow.md`.*
