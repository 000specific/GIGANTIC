# Documentation: Human Gene Count Reconciliation — GIGANTIC vs Independent Count

**AI**: Claude Code | Opus 4.7 (1M context) | 2026 May 04
**Human**: Eric Edsinger
**Companion document**: `DOCUMENTATION-alternate_loci_filtering.md` (in the same directory)

---

## Question

After the alternate loci fix (see companion document), the GIGANTIC human T1 proteome contains **20,076 sequences**, down from 21,412 pre-fix. An independent count performed at the Salk Institute on the same human assembly (NCBI GCF_000001405.40) returned **19,903 protein-coding genes**.

Both numbers are in the "~20,000 human protein-coding genes" range, but they are not identical. This document reconciles the two and clarifies what each is counting.

---

## Direct verification of the GFF

All counts below were generated directly from the GFF3 file currently used by genomesDB:

```
INPUT_user/genomic_resources/annotations/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20260211.gff3
```

(symlinked from `research_notebook/research_user/species71/output_to_input/gene_annotations/`)

| Methodology | Count | What it asks |
|---|---:|---|
| Total `gene` features with `gene_biotype=protein_coding` | 23,306 | Raw entry count, includes alt-locus duplicates |
| Primary genes only (gene ID has no `-N` suffix) | 19,927 | Excludes `gene-AAAS-2` style duplicates |
| Alternate-loci genes (gene ID has `-N` suffix) | 3,379 | Mostly on alt-haplotype/unplaced scaffolds |
| **Unique NCBI GeneIDs (protein_coding)** ← **GIGANTIC's 20,076** | **20,076** | Distinct biological gene loci |
| Unique gene `Name=` values (gene symbols) | 20,076 | Same answer by symbol |
| Protein_coding gene features on NC_ scaffolds (primary chromosomes) only | 19,898 | Excludes NT_ alt-haplotypes and NW_ unplaced |
| Unique GeneIDs of genes located on NC_ scaffolds | 19,879 | Of distinct loci, those represented on a primary chromosome |
| Unique GeneIDs of genes that have at least one CDS (any biotype) | 20,673 | Includes some pseudogenes/readthroughs with CDS |

Scaffold breakdown of the 23,306 protein_coding gene features:
- 19,898 on NC_ scaffolds (primary chromosomes)
- 1,821 on NT_ scaffolds (alternate haplotypes)
- 1,587 on NW_ scaffolds (unplaced)

---

## What GIGANTIC counts: 20,076

GIGANTIC's 20,076 is the number of **distinct NCBI GeneIDs** with `gene_biotype=protein_coding` anywhere in the assembly. The script
[`003_ai-python-extract_longest_transcript_proteomes.py`](ai/scripts/003_ai-python-extract_longest_transcript_proteomes.py)
groups all `gene` features by the `Dbxref=GeneID:N` attribute and emits one T1 protein per distinct GeneID.

This is the equivalence relation NCBI itself uses to assert "this is the same gene." When NCBI annotates `AAAS` on chromosome 12 (NC_000012.12) and again on an unplaced scaffold (NW_025791795.1), both entries carry `GeneID:8086`. Collapsing on GeneID asks the most semantically meaningful question:

> How many distinct biological gene loci are annotated as protein-coding in this assembly?

GIGANTIC chose this because the framework's downstream operations (orthogroups, gene families, conservation/loss inference) are *gene-level* analyses. Counting alt-haplotype copies separately would inflate per-species gene counts and create spurious "duplications" in orthogroup output.

**Per-species summary in BLOCK_orthohmm_GIGANTIC RUN_1** confirms:
- `Homo_sapiens`: 20,076 sequences in proteome → 20,076 sequences in orthogroups (100% coverage) → distributed across 8,534 orthogroups.

---

## What Salk's 19,903 likely counts

19,903 sits cleanly in the "primary chromosomes only" range:

```
19,879 ─── unique GeneIDs of genes on NC_ scaffolds only
19,898 ─── protein_coding gene features on NC_ scaffolds only
19,903 ─── Salk's count
19,927 ─── primary genes (no -N suffix), all scaffolds
```

The most plausible interpretations of 19,903 (without knowing Salk's exact filter):

1. **Primary assembly chromosomes only.** Filter the GFF to NC_ scaffolds (excluding NT_ alt-haplotypes and NW_ unplaced contigs), then count protein_coding gene features. This gives 19,898; minor handling of mtDNA (NC_012920.1, 13 protein-coding genes) or chrY pseudoautosomal regions could move this by a handful.

2. **No-`-N` primary loci, on canonical chromosomes only.** Take the 19,927 primary-suffix genes, then subtract those located on alt or unplaced scaffolds. Lands within ~25 of 19,903.

3. **Slightly different annotation release of the same assembly accession.** NCBI republishes the GFF3 for `GCF_000001405.40` against successive RefSeq annotation releases (RS_2024_08, RS_2025_02, etc.) without changing the assembly version. Gene model additions/withdrawals between releases routinely move counts by tens to low hundreds.

Any of these is a defensible methodology. Salk's number is not "wrong"; it's answering a slightly different question.

---

## Why neither is "the answer"

There is no single canonical "human protein-coding gene count." Authoritative sources publish different numbers from the same underlying genome:

| Source | Approx. count | Definitional choices |
|---|---:|---|
| NCBI RefSeq (this assembly, GeneID-collapsed) | ~20,000 | Distinct GeneIDs, all scaffolds |
| NCBI RefSeq (primary chromosomes only) | ~19,900 | NC_ scaffolds only |
| GENCODE / Ensembl basic | ~19,400–20,000 | Excludes many readthroughs and TEC loci |
| CCDS (Consensus Coding Sequence) | ~19,000 | Only loci validated by RefSeq + GENCODE consensus |
| HGNC | ~19,200 | Approved symbols only, conservative |
| UniProt human reference proteome | ~20,400 | One canonical isoform per gene, slightly different gene model |

Reasons the numbers diverge:
- Whether alt-haplotype/unplaced contigs are included
- How readthrough loci, fusions, and overlapping ORFs are split or merged
- Inclusion of pseudogenes (especially polymorphic and processed-but-translated)
- Inclusion of immunoglobulin and T-cell receptor gene segments
- Inclusion of TEC ("To Be Experimentally Confirmed") loci
- Annotation release date — the GFF for the same assembly accession is not static

**A ~170-gene difference (~0.86%) between two reasonable methodologies on the same source file is normal and expected.**

---

## Resolution and recommendation

For GIGANTIC's purposes:

- **20,076 is the correct count to use** for GIGANTIC's downstream analyses. GIGANTIC operates at the gene level, and NCBI's GeneID is the most defensible equivalence relation for "this is the same gene." Filtering to primary chromosomes only would systematically lose biologically real loci that are annotated only on NT_ alt-haplotype or NW_ unplaced scaffolds (the documentation flags 41 GeneIDs with no primary-form copy at all — these are real protein-coding loci with messy scaffold assignment, not artifacts).

- **The pre-fix count of 21,412 was not defensible**, because it counted alt-haplotype copies of the same gene as separate proteins. The fix (alternate loci filtering keyed on GeneID) is correct.

For methods text:

> The human T1 proteome contains 20,076 protein sequences, one per distinct NCBI GeneID with `gene_biotype=protein_coding` in the GCF_000001405.40 RefSeq annotation. This count groups gene features by GeneID to collapse alternate-haplotype and unplaced-scaffold copies of the same biological gene; counts that filter to primary chromosomes only would land near 19,900. Independent counts of "protein-coding genes" on this assembly using different filtering rules typically range from ~19,400 to ~20,400 depending on which source (NCBI RefSeq, GENCODE, CCDS, HGNC, UniProt) is used and what its inclusion criteria are for alt-haplotype loci, pseudogenes, immunoglobulin gene segments, and TEC loci.

For comparison with the Salk count specifically:

> The 173-gene difference (20,076 − 19,903) is consistent with the Salk count being restricted to the primary assembly chromosomes (NC_ scaffolds), excluding the ~178 protein-coding gene loci annotated only on alternate-haplotype (NT_) or unplaced (NW_) scaffolds. Both methodologies are valid; they answer different questions about the same GFF.

---

## Reproducibility

To reproduce the verification counts in this document:

```bash
GFF=$(realpath \
  /blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/INPUT_user/genomic_resources/annotations/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20260211.gff3)

# Total protein_coding gene features
awk -F'\t' '$3=="gene" && $9 ~ /gene_biotype=protein_coding/' "$GFF" | wc -l
# → 23,306

# Unique NCBI GeneIDs (protein_coding) — GIGANTIC's count
awk -F'\t' '$3=="gene" && $9 ~ /gene_biotype=protein_coding/' "$GFF" \
  | grep -oP 'GeneID:[0-9]+' | sort -u | wc -l
# → 20,076

# Primary genes (no -N suffix)
awk -F'\t' '$3=="gene" && $9 ~ /gene_biotype=protein_coding/' "$GFF" \
  | grep -oP 'ID=gene-[^;]+' | grep -vP '\-[0-9]+$' | wc -l
# → 19,927

# protein_coding gene features on NC_ scaffolds only
awk -F'\t' '$1 ~ /^NC_/ && $3=="gene" && $9 ~ /gene_biotype=protein_coding/' "$GFF" | wc -l
# → 19,898

# Unique GeneIDs of genes on NC_ scaffolds only
awk -F'\t' '$1 ~ /^NC_/ && $3=="gene" && $9 ~ /gene_biotype=protein_coding/' "$GFF" \
  | grep -oP 'GeneID:[0-9]+' | sort -u | wc -l
# → 19,879
```

To verify the proteome count matches:

```bash
PROTEOME=$(realpath \
  /blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/INPUT_user/genomic_resources/proteomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20260211.aa)
grep -c '^>' "$PROTEOME"
# → 20,076

# Confirm orthogroups RUN_1 used the same count
grep "Homo_sapiens" \
  /blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/subprojects/orthogroups/BLOCK_orthohmm_GIGANTIC/workflow-RUN_1-run_orthohmm_GIGANTIC/OUTPUT_pipeline/8-output/8_ai-per_species_summary.tsv
# → Homo_sapiens  20076  20076  0  100.00  8534
```

---

## Provenance trail

- **GFF source**: NCBI RefSeq, GCF_000001405.40 (GRCh38.p14), downloaded 2026-02-11
- **T1 extraction script**: `nf_workflow-RUN_2_01-ncbi_genomes/ai/scripts/003_ai-python-extract_longest_transcript_proteomes.py` (alternate loci fix applied 2026-03-31)
- **T1 proteome (canonical location)**: `research_notebook/research_user/species71/output_to_input/T1_proteomes/Homo_sapiens-genome-ncbi_GCF_000001405.40-downloaded_20260211.aa`
- **Symlinked into INPUT_user**: `INPUT_user/genomic_resources/proteomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20260211.aa`
- **Consumed by genomesDB**: ingested in `STEP_1-sources/workflow-RUN_1-ingest_source_data/`, finalized in `STEP_4-create_final_species_set/workflow-RUN_1-create_final_species_set/OUTPUT_pipeline/2-output/species70_gigantic_T1_proteomes/`
- **Consumed by orthogroups**: `BLOCK_orthohmm_GIGANTIC/workflow-RUN_1-run_orthohmm_GIGANTIC/` (config points to `genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes`)
- **Output**: BLOCK_orthohmm_GIGANTIC RUN_1 completed 2026-05-01, 20,076 human sequences distributed across 8,534 orthogroups
