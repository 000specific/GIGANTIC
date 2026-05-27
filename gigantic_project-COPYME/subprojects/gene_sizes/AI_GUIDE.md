# AI Guide: gene_sizes Subproject

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 04 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (project): [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — GIGANTIC overview + general patterns
- Subproject README: [`README.md`](README.md)
- Reads FROM:
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/` — species set definition
  - User-provided per-species gene-coordinate TSVs in each workflow's `INPUT_user/` (extracted from species-specific GFF/GTF by the user)
- Outputs TO (`output_to_input/BLOCK_analyze_gene_sizes/`):
  - `all_inclusive/` — Tier 1 (~40 species; 7 metrics with UTR awareness)
  - `gene_vs_protein/` — Tier 2 (~64 species; 4 metrics, superset of Tier 1)
- Downstream consumers:
  - Comparative genomics analyses (gene size vs nervous-system complexity, McCoy 2024 replication)
  - `upload_to_server/` — curated subset
- Dual-tier architecture: two parallel workflows in one BLOCK, sharing scripts but with tier-adapted column counts and metric sets

**For AI Assistants**: Read `../../AI_GUIDE.md` first for GIGANTIC overview,
directory structure, and general patterns. This guide covers gene_sizes-specific
concepts and troubleshooting.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| gene_sizes concepts, troubleshooting | This file |
| Running the all-inclusive (Tier 1) workflow | `BLOCK_analyze_gene_sizes/workflow-COPYME-analyze_gene_sizes-all_inclusive/ai/AI_GUIDE.md` |
| Running the gene-vs-protein (Tier 2) workflow | `BLOCK_analyze_gene_sizes/workflow-COPYME-analyze_gene_sizes-gene_vs_protein/ai/AI_GUIDE.md` |

---

## What This Subproject Does

Computes gene structure metrics from user-provided gene-coordinate TSVs for species
in the GIGANTIC set. Produces per-species gene metrics, genome-wide statistics,
relative size ranks, and cross-species summaries. This is a FROM SCRATCH
subproject (no GIGANTIC_0 reference).

The subproject runs as **two parallel workflow templates** (the dual-tier
architecture) — see "Dual-Tier Architecture" below.

---

## Directory Structure

```
gene_sizes/
├── README.md
├── AI_GUIDE.md                                  # THIS FILE
├── RUN-update_upload_to_server.sh               # publisher (one per subproject per §38)
├── output_to_input/                                        # Downstream-facing outputs
│   └── BLOCK_analyze_gene_sizes/
│       ├── all_inclusive/                                  # Tier 1 symlinks (~40 species)
│       │   ├── speciesN_gigantic_gene_metrics/
│       │   └── speciesN_gigantic_gene_sizes_summary/
│       └── gene_vs_protein/                                # Tier 2 symlinks (~64 species)
│           ├── speciesN_gigantic_gene_metrics/
│           └── speciesN_gigantic_gene_sizes_summary/
├── upload_to_server/
└── BLOCK_analyze_gene_sizes/
    ├── AI_GUIDE.md
    ├── workflow-COPYME-analyze_gene_sizes-all_inclusive/   # Tier 1 template
    │   ├── README.md
    │   ├── RUN-workflow.sh                                 # single entry point per §29
    │   ├── START_HERE-user_config.yaml
    │   ├── INPUT_user/                                     # 15-col Tier 1 TSVs go here
    │   ├── OUTPUT_pipeline/
    │   └── ai/
    │       ├── AI_GUIDE.md
    │       ├── main.nf
    │       ├── nextflow.config
    │       └── scripts/
    │           ├── 001_ai-python-validate_gene_size_inputs.py
    │           ├── 002_ai-python-extract_gene_metrics.py
    │           ├── 003_ai-python-compute_genome_wide_statistics.py
    │           ├── 004_ai-python-compile_cross_species_summary.py
    │           └── 005_ai-python-write_run_log.py
    └── workflow-COPYME-analyze_gene_sizes-gene_vs_protein/ # Tier 2 template
        └── (same structure; 9-col Tier 2 TSVs in INPUT_user/)
```

---

## Key Concepts

### Dual-Tier Architecture

The gene_sizes subproject runs as **two parallel workflow templates**, each
producing its own self-contained output. This implements the
**dual-tier outputs** pattern from the project-level "Highest-Quality Genomes
Only" tenet (`../../AI_GUIDE.md`).

| | Tier 1 — `all_inclusive` | Tier 2 — `gene_vs_protein` |
|---|---|---|
| **Workflow dir** | `workflow-COPYME-analyze_gene_sizes-all_inclusive/` | `workflow-COPYME-analyze_gene_sizes-gene_vs_protein/` |
| **Input filename suffix** | `-gene_coordinates_all_inclusive.tsv` | `-gene_coordinates_gene_vs_protein.tsv` |
| **Input TSV columns** | 15 (gene + exon + CDS + 5′ UTR + 3′ UTR + sizes) | 9 (gene + CDS + sizes) |
| **Required source-annotation features** | Gene + exon + CDS records, with ≥50% genes having derivable UTR | Gene + CDS records (no UTR/exon required) |
| **Final cross-species metrics** | 7 (Gene_Size, Transcript_Size, CDS_Size, Protein_Size, Exon_Count, Intron_Total_Size, UTR_Total_Size) | 4 (Gene_Size, CDS_Size, Protein_Size, CDS_Segment_Count) |
| **Approximate species count** | ~40 (Tier 1 ⊂ Tier 2) | ~64 (superset of Tier 1) |
| **Downstream output dir** | `output_to_input/BLOCK_analyze_gene_sizes/all_inclusive/` | `output_to_input/BLOCK_analyze_gene_sizes/gene_vs_protein/` |

**Tier 1 species are also written as Tier 2** (superset behavior): if a
species qualifies for `all_inclusive`, the upstream extractors emit both a
15-col and a 9-col TSV. Downstream consumers who only need the 4-metric
universally-comparable subset get the broader Tier 2 set automatically.

**When to use each tier**:

- Use **Tier 1** when transcript-level, intron, exon-count, or UTR-aware
  metrics matter and you want methodologically uniform UTR handling.
- Use **Tier 2** when only gene-genomic-span / coding-length / protein-length
  questions matter and you want the largest possible species count.

The two tiers share scripts 001–005 in structure but the scripts are
tier-adapted (different column counts, different metric sets). Do not
attempt to run both tiers from a single workflow — they are deliberately
separate to keep the methodology lines clean.

### Six Permanently Dropped Species

Six species in the species70 set produce neither tier and are
permanently dropped here:

| Species | Reason |
|---|---|
| `Abeoforma_whisleri` | No GFF available |
| `Pleurobrachia_bachei` | No GFF available |
| `Chondrosia_reniformis` | No genome-scale coordinate map |
| `Creolimax_fragrantissima` | No genome-scale coordinate map |
| `Hoilungia_hongkongensis_H13` | No CDS records in source annotation |
| `Hormiphora_californensis` | No CDS records in source annotation |

Script 001 reports these as `SKIPPED_NO_DATA` (Tier 2) /
`SKIPPED_NO_DATA` or `SKIPPED_INCOMPLETE` (Tier 1) and the pipeline
continues. They are **not** a bug; they are explicitly excluded by
the methodology gate (see project-level "Highest-Quality Genomes Only"
tenet).

### User-Provided Input Design

This subproject follows GIGANTIC's established pattern: the **user** handles
species-specific GFF/GTF parsing and provides standardized gene structure
data. The pipeline does NOT parse GFF/GTF files directly because:

1. GFF/GTF format varies enormously across species, databases, and publications
2. genomesDB does not parse GFF content (carries files as opaque blobs)
3. T1 transcript selection and gene structure extraction require species-specific knowledge
4. Making this the user's responsibility matches how GIGANTIC handles all input data

Reference extractors that produce both tier TSVs from species-specific GFF/GTF
live OUTSIDE GIGANTIC at
`research_notebook/research_user/<speciesN>/gene_coordinates/` (NCBI /
Kim_2025 / repository sources). Each extractor decides per species whether
to emit Tier 1 (≥50% UTR rate), Tier 2, or both.

### Input Format — Tier 1 (`all_inclusive`)

One TSV file per qualifying species in
`workflow-*-all_inclusive/INPUT_user/`, named
`Genus_species-gene_coordinates_all_inclusive.tsv` — **15 columns**:

```
Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  Gene_Size  Exon_Intervals  Transcript_Size  CDS_Intervals  CDS_Size  Protein_Size  UTR_5prime_Intervals  UTR_5prime_Size  UTR_3prime_Intervals  UTR_3prime_Size
```

- Pre-computed size fields (`Gene_Size`, `Transcript_Size`, `CDS_Size`, …) are
  written by the upstream extractor as a convenience; script 002 re-derives
  them from the intervals to stay self-consistent.
- `UTR_5prime_Intervals` / `UTR_3prime_Intervals` are derived as the set
  difference `merged_exons − merged_cds`, split by strand.

### Input Format — Tier 2 (`gene_vs_protein`)

One TSV file per qualifying species in
`workflow-*-gene_vs_protein/INPUT_user/`, named
`Genus_species-gene_coordinates_gene_vs_protein.tsv` — **9 columns**:

```
Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  Gene_Size  CDS_Intervals  CDS_Size  Protein_Size
```

- No exon, transcript, or UTR fields — only gene + CDS.
- `CDS_Segment_Count` (number of merged CDS intervals) is a Tier 2-only
  derived metric used as a coarse proxy for exon count when full exon
  records aren't available.

### Common to both tiers

- **Source_Gene_ID**: Must match the `g_` field in GIGANTIC proteome FASTA headers
- **CDS_Intervals**: Comma-separated `start-end` pairs for the T1 transcript's CDS features
- GIGANTIC does NOT use gene names or symbols — purely accession-based identifiers

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

### Metrics Computed (biologically-correct definitions)

#### Tier 1 (`all_inclusive`) — 7 metrics

The Tier 1 pipeline reads BOTH `Exon_Intervals` and `CDS_Intervals` from each
gene's TSV row, so transcript-level (mRNA) metrics are computed separately
from coding-level (CDS) metrics — they are NOT conflated.

| Metric | How Computed | What it measures |
|--------|-------------|------------------|
| `Gene_Size` | `Gene_End - Gene_Start + 1` | Genomic span on the scaffold; includes all introns + UTRs + CDS |
| `Transcript_Size` | Sum of merged `Exon_Intervals` lengths | Mature mRNA length; includes UTRs, excludes introns |
| `CDS_Size` | Sum of merged `CDS_Intervals` lengths | Protein-coding length; excludes UTRs and introns |
| `Protein_Size` | `CDS_Size / 3` | Estimated amino acids in the encoded protein |
| `Exon_Count` | Number of merged exon intervals | Number of exons in the T1 transcript |
| `Intron_Total_Size` | `Gene_Size - Transcript_Size` | Total intronic genomic span |
| `UTR_Total_Size` | `Transcript_Size - CDS_Size` | Total 5′ + 3′ UTR length |

#### Tier 2 (`gene_vs_protein`) — 4 metrics

The Tier 2 pipeline only has gene + CDS records to work with, so it computes
only the universally-comparable subset:

| Metric | How Computed | What it measures |
|--------|-------------|------------------|
| `Gene_Size` | `Gene_End - Gene_Start + 1` | Genomic span on the scaffold |
| `CDS_Size` | Sum of merged `CDS_Intervals` lengths | Protein-coding length |
| `Protein_Size` | `CDS_Size / 3` | Estimated amino acids in the encoded protein |
| `CDS_Segment_Count` | Number of merged `CDS_Intervals` | Coarse proxy for exon count when full exon records aren't available |

Within-genome **percentile ranks** are computed separately for each metric
within each tier in script 003, enabling cross-species comparisons that are
scale-invariant despite genomes varying 30×+ in size.

### Interval Merging

When a user provides overlapping intervals (e.g., from collapsed-isoform inputs), the pipeline
sorts and merges adjacent or overlapping intervals before computing metrics. This avoids
double-counting shared exonic or coding bases. In Tier 1, merging is applied to
`Exon_Intervals` and `CDS_Intervals` independently. In Tier 2, only `CDS_Intervals` is merged.

### UTR Inclusion / Exclusion (Tier 1 only)

UTRs are **included** in `Transcript_Size` (since exons contain UTRs) and **excluded** from
`CDS_Size` (since CDS records mark only the coding portion). The separate `UTR_Total_Size`
metric makes the UTR contribution explicit.

Tier 2 deliberately omits all UTR / transcript / intron metrics because the underlying
species' annotations don't reliably distinguish UTR from non-UTR exonic content — including
those metrics for Tier 2 species would be methodologically inconsistent with Tier 1.

Earlier GIGANTIC versions used a single "Exonic_Length" metric defined as the sum of CDS
intervals — this conflated exonic and coding measurements and is no longer used. If you see
that label in old documentation or output files, it referred to what is now `CDS_Size`, not
the true exonic content.

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
| No species have valid gene structure data | INPUT_user/ is empty or files have wrong tier suffix | Add `Genus_species-gene_coordinates_<tier>.tsv` files matching the workflow's tier |
| Species list not found | Wrong path in config | Verify gigantic_species_list path in START_HERE-user_config.yaml |
| Zero genes extracted (Tier 1) | TSV file is not 15-col format | Verify TSV is the `_all_inclusive` 15-col layout from the upstream extractor |
| Zero genes extracted (Tier 2) | TSV file is not 9-col format | Verify TSV is the `_gene_vs_protein` 9-col layout from the upstream extractor |
| Protein size = 0 | CDS intervals are empty or invalid | Verify `CDS_Intervals` column has valid `start-end` pairs |
| Many species SKIPPED_INCOMPLETE in Tier 1 | Source annotation lacks UTR-bearing exon records for ≥50% of genes | Expected — species drops to Tier 2 only |
| Many species SKIPPED_NO_DATA in Tier 1 but PROCESSED in Tier 2 | Species are Tier 2-only (no full UTR annotation) | Expected behavior of dual-tier architecture |
| Tier 1 species missing from Tier 2 | Bug — Tier 1 species should also write Tier 2 file (superset) | Re-run upstream gene_coordinates extractor |
| GIGANTIC IDs not linked | Proteome directory not set or files not found | Set `proteome_dir` in config with `Genus_species.aa` files |

---

## Data Flow

The two tier workflows run independently. Each follows the same script pipeline
but on tier-specific TSV layouts. The diagram below shows one tier; substitute
`<tier>` with `all_inclusive` or `gene_vs_protein`.

```
INPUT_user/Genus_species-gene_coordinates_<tier>.tsv (user-provided gene structure data)
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
Script 005: Write run log
    │  → ai/logs/: timestamped run-success log
    ▼
output_to_input/BLOCK_analyze_gene_sizes/<tier>/ (symlinks for downstream subprojects)
```

---

## Key Files

These files exist in **each tier's workflow directory**
(`workflow-COPYME-analyze_gene_sizes-all_inclusive/` and
`workflow-COPYME-analyze_gene_sizes-gene_vs_protein/`):

| File | Purpose | User Edits? |
|------|---------|-------------|
| `START_HERE-user_config.yaml` | Input paths, output settings, optional project_name | Yes |
| `INPUT_user/*.tsv` | Per-species gene structure data (tier-specific schema) | Yes (user creates these) |
| `INPUT_user/gigantic_species_list.txt` | GIGANTIC species list | Yes (copy from genomesDB) |
| `RUN-workflow.sh` | Unified entry point (local or SLURM via `execution_mode` YAML); per §29 | Yes (account, qos) |
| `ai/main.nf` | Nextflow pipeline definition | No |
| `ai/nextflow.config` | Nextflow settings + YAML param loading | No |
| `ai/scripts/001-005` | Processing scripts (tier-adapted) | No |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Setting up for first time | "Have the upstream `gene_coordinates` extractors been run to produce both tier TSVs?" |
| New species added to genomesDB | "Do you have GFF/GTF for the new species, and which extractor (NCBI / Kim_2025 / repository) should produce its TSVs?" |
| Unexpected gene counts | "Which annotation source did you use for this species (NCBI, Ensembl, custom)? Is the source format consistent with how the extractor expects it?" |
| Cross-species comparison spans tiers | "Should the comparison restrict to Tier 1 species (uniform UTR methodology) or use Tier 2's broader 64-species set on the 4 universally-comparable metrics?" |
| Many species skipped from Tier 1 | "Are these species expected to lack UTR annotation? If so, this is the correct dual-tier behavior — they should still appear in Tier 2." |
| Tier 1 species missing from Tier 2 | "This shouldn't happen — the upstream extractor should always emit the Tier 2 file when it emits Tier 1. Re-run the extractor for that species." |

---

## Dependencies

**Upstream**: genomesDB (species list from STEP_4)

**Downstream**: `gene_sizes_X_integrations` (dN/dS, rank deviation, functional enrichment by gene size). Also available to orthogroups and annotations subprojects for cross-integration analyses.

**Conda environment**: `ai_gigantic_gene_sizes` (Python 3, Nextflow)
