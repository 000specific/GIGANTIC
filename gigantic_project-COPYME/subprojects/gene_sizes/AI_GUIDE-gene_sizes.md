# AI Guide: gene_sizes Subproject

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview,
directory structure, and general patterns. This guide covers gene_sizes-specific
concepts and troubleshooting.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| gene_sizes concepts, troubleshooting | This file |
| Running the workflow | `BLOCK_analyze_gene_sizes/workflow-COPYME-analyze_gene_sizes/ai/AI_GUIDE-analyze_gene_sizes_workflow.md` |

---

## What This Subproject Does

Computes gene structure metrics from user-provided CDS interval data for species in the
GIGANTIC set. Produces per-species gene metrics, genome-wide statistics, relative size
ranks, and cross-species summaries. This is a FROM SCRATCH subproject (no GIGANTIC_0 reference).

---

## Directory Structure

```
gene_sizes/
├── README.md
├── AI_GUIDE-gene_sizes.md              # THIS FILE
├── user_research/
├── research_notebook/
│   ├── ai_research/                    # Paper summaries
│   └── user_research/                  # User notes
├── output_to_input/                    # Symlinks → BLOCK output
├── upload_to_server/
└── BLOCK_analyze_gene_sizes/
    ├── AI_GUIDE-analyze_gene_sizes.md
    ├── RUN-clean_and_record_subproject.sh
    ├── output_to_input/                # Canonical downstream output
    └── workflow-COPYME-analyze_gene_sizes/
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        ├── gene_sizes_config.yaml
        ├── INPUT_user/
        ├── OUTPUT_pipeline/
        └── ai/
            ├── AI_GUIDE-analyze_gene_sizes_workflow.md
            ├── main.nf
            ├── nextflow.config
            ├── output_to_input/
            └── scripts/
                ├── 001_ai-python-validate_gene_size_inputs.py
                ├── 002_ai-python-extract_gene_metrics.py
                ├── 003_ai-python-compute_genome_wide_statistics.py
                └── 004_ai-python-compile_cross_species_summary.py
```

---

## Key Concepts

### User-Provided Input Design

This subproject follows GIGANTIC's established pattern: the **user** handles species-specific
GFF/GTF parsing and provides standardized gene structure data. The pipeline does NOT parse
GFF/GTF files directly because:

1. GFF/GTF format varies enormously across species, databases, and publications
2. genomesDB does not parse GFF content (carries files as opaque blobs)
3. T1 transcript selection and gene structure extraction require species-specific knowledge
4. Making this the user's responsibility matches how GIGANTIC handles all input data

### Input Format

One TSV file per species in `INPUT_user/`, named `Genus_species-gene_coordinates.tsv`:

```
Source_Gene_ID	Seqid	Gene_Start	Gene_End	Strand	CDS_Intervals
ENSG00000139618	chr13	32315474	32400266	+	32316422-32316527,32319077-32319325
```

- **Source_Gene_ID**: Must match the `g_` field in GIGANTIC proteome FASTA headers
- **CDS_Intervals**: Comma-separated `start-end` pairs for coding sequence coordinates
- GIGANTIC does NOT use gene names or symbols - purely accession-based identifiers

### Graceful Species Dropping

The pipeline uses a three-tier status system instead of fail-hard:

| Status | Meaning |
|--------|---------|
| PROCESSED | Valid gene structure data, fully processed |
| SKIPPED_NO_DATA | No input file provided (expected for many species) |
| SKIPPED_INCOMPLETE | File exists but data failed validation |

**Why not fail-hard?** Missing gene structure data is a data availability limitation
(not all species have published gene annotations), not a pipeline error. The pipeline
processes what it can and clearly reports what was skipped and why.

### Metrics Computed

| Metric | How Computed |
|--------|-------------|
| Gene length | `gene_end - gene_start + 1` (genomic span) |
| Exonic length | Sum of merged CDS interval lengths |
| Intronic length | Gene length - exonic length |
| Exon count | Number of merged CDS intervals |
| CDS length | Same as exonic length (both use CDS features) |
| Protein size | CDS length / 3 (estimated) |

### CDS Interval Merging

When a user provides overlapping CDS intervals (e.g., from multiple isoforms merged
at the user level), the pipeline merges them:
1. Sort intervals by start position
2. Merge any overlapping or adjacent intervals
3. The merged set represents the gene's coding region
4. This avoids double-counting shared exonic sequences

### UTR Exclusion

UTRs are excluded from exonic measurements because:
- Annotation quality varies widely across species
- 3-prime UTR annotations are often incomplete
- CDS features are more reliably annotated
- Scientific precedent (McCoy & Fire papers exclude UTRs)

### Relative Rank (Quantile)

For cross-species comparison, absolute sizes are meaningless (genome sizes vary 30x+).
Instead, each gene is ranked by percentile within its own genome:
- Gene in top 10% for gene_length → rank 0.90-1.00
- Gene in bottom 10% → rank 0.00-0.10

This enables detecting conserved patterns: "is this gene consistently among the longest
genes in every species where it occurs?"

### GIGANTIC ID Linkage

Source_Gene_IDs are optionally linked to GIGANTIC identifiers by parsing the `g_` prefix
from proteome FASTA headers:

```
>g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_Chordata_...
```

The `g_` field (`ENSG00000139618`) matches the user-provided Source_Gene_ID, enabling
linkage to the full GIGANTIC identifier system.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No species have valid gene structure data | INPUT_user/ is empty or files have wrong format | Add Genus_species-gene_coordinates.tsv files to INPUT_user/ |
| Species list not found | Wrong path in config | Verify gigantic_species_list path in gene_sizes_config.yaml |
| Zero genes extracted for a species | TSV file has wrong column format | Check TSV matches expected 6-column format with CDS_Intervals |
| Protein size = 0 | CDS intervals are empty or invalid | Verify CDS_Intervals column has valid start-end pairs |
| Many species SKIPPED_INCOMPLETE | Files exist but validation fails | Check field counts, integer values, interval format |
| GIGANTIC IDs not linked | Proteome directory not set or files not found | Set proteome_dir in config with Genus_species.aa files |

---

## Data Flow

```
INPUT_user/Genus_species-gene_coordinates.tsv (user-provided gene structure data)
    │
    ▼
Script 001: Validate gene size inputs
    │  → 1-output/: species processing status, processable species list
    ▼
Script 002: Extract gene metrics (per species, parallelized)
    │  → 2-output/: per-species gene metrics with GIGANTIC ID linkage
    ▼
Script 003: Compute genome-wide statistics and ranks (per species)
    │  → 3-output/: ranked metrics, genome summaries
    ▼
Script 004: Compile cross-species summary
    │  → 4-output/: combined tables, processing status, downstream directories
    ▼
output_to_input/ (symlinks for downstream subprojects)
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `gene_sizes_config.yaml` | Input paths, output settings | Yes |
| `INPUT_user/*.tsv` | Per-species gene structure data | Yes (user creates these) |
| `INPUT_user/gigantic_species_list.txt` | GIGANTIC species list | Yes (copy from genomesDB) |
| `RUN-workflow.sh` | Local pipeline runner | No |
| `RUN-workflow.sbatch` | SLURM wrapper | Yes (account, qos) |
| `ai/main.nf` | Nextflow pipeline definition | No |
| `ai/scripts/001-004` | Processing scripts | No |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Setting up for first time | "Have you created the per-species TSV files from your GFF/GTF annotations?" |
| New species added to genomesDB | "Do you have gene annotation data for the new species to add to INPUT_user/?" |
| Unexpected gene counts | "Which annotation source did you use for this species (NCBI, Ensembl, custom)?" |
| Cross-species comparison needed | "Do you have orthogroup assignments for linking genes across species?" |
| Many species skipped | "Is it expected that these species lack gene annotations, or should we investigate?" |

---

## Dependencies

**Upstream**: genomesDB (species list from STEP_4)

**Downstream**: Other subprojects that need gene structure information for their analyses.

**Conda environment**: `ai_gigantic_gene_sizes` (Python 3, Nextflow)
