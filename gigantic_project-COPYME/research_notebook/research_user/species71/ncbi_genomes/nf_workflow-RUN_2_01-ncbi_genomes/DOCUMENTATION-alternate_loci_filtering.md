# Documentation: NCBI Alternate Loci Filtering in T1 Proteome Extraction

**AI**: Claude Code | Opus 4.6 | 2026 March 31
**Human**: Eric Edsinger
**Location**: `research_notebook/research_user/species71/ncbi_genomes/nf_workflow-RUN_2_01-ncbi_genomes/`

---

## Table of Contents

1. [Problem Discovery](#1-problem-discovery)
2. [Root Cause Analysis](#2-root-cause-analysis)
3. [The Biological Reality of NCBI Alternate Loci](#3-the-biological-reality-of-ncbi-alternate-loci)
4. [The Fix: Alternate Loci Filtering](#4-the-fix-alternate-loci-filtering)
5. [Implementation Details](#5-implementation-details)
6. [Results and Validation](#6-results-and-validation)
7. [Downstream Impact and ID Mapping](#7-downstream-impact-and-id-mapping)
8. [Complete File Inventory](#8-complete-file-inventory)
9. [How to Reproduce This Work](#9-how-to-reproduce-this-work)
10. [Limitations and Caveats](#10-limitations-and-caveats)

---

## 1. Problem Discovery

### Initial Observation

During post-processing of the `one_direction_homologs` subproject (DIAMOND blastp search of species proteomes against NCBI nr), the human proteome was reported as having **21,412 query proteins**. This number was flagged as inconsistent with the commonly referenced ~20,000 protein-coding genes in the human genome.

### Investigation Path

The investigation traced the protein count through the GIGANTIC pipeline:

1. **Final proteome** (`genomesDB-species70/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes/`): 21,412 sequences
2. **genomesDB STEP_1 ingest** (`genomesDB/STEP_1-sources/workflow-RUN_1-ingest_source_data/`): Simply copies files — 21,412 sequences already present in source
3. **Source T1 proteomes** (`research_notebook/research_user/species71/output_to_input/T1_proteomes/`): 21,412 sequences — the inflation was present from the very first extraction
4. **T1 extraction script** (`research_notebook/research_user/species71/ncbi_genomes/nf_workflow-RUN_1_01-ncbi_genomes/ai/scripts/003_ai-python-extract_longest_transcript_proteomes.py`): This is where the problem originates

### Key Finding

The T1 extraction script (script 003 in RUN_1) treated every `gene` feature in the NCBI GFF3 file as a unique biological gene. However, NCBI GFF3 files for genome assemblies with alternate scaffolds contain **duplicate gene entries** — the same gene appears on multiple scaffolds (primary chromosome, alternate haplotypes, and unplaced contigs). These share the same NCBI GeneID but have different gene feature IDs (e.g., `gene-AAAS` on NC_000012.12 and `gene-AAAS-2` on NW_025791795.1).

---

## 2. Root Cause Analysis

### NCBI GFF3 Gene Feature Naming Convention

NCBI assigns gene feature IDs with a `-N` suffix to indicate alternate loci:

```
Primary:    ID=gene-AAAS        (on NC_000012.12, chromosome 12)
Alternate:  ID=gene-AAAS-2      (on NW_025791795.1, unplaced scaffold)
```

Both entries share:
- The same `GeneID:8086` in the Dbxref attribute
- The same `Name=AAAS` gene symbol
- The same `gene=AAAS` attribute
- The same `gene_biotype=protein_coding`

They differ in:
- The scaffold/chromosome they are located on
- The gene feature ID (the `-2`, `-3`, etc. suffix)
- Potentially the transcript and protein IDs associated with them

### Scaffold Types Involved

In the human genome assembly (GCF_000001405.40), the `-N` suffix genes appear on three types of scaffolds:

| Scaffold Prefix | Type | Count of -N Suffix Genes |
|-----------------|------|--------------------------|
| `NT_` | Alternate haplotype scaffolds (e.g., MHC region alternate assemblies) | 3,106 |
| `NW_` | Unplaced scaffolds (contigs not assigned to chromosomes) | 2,346 |
| `NC_` | Primary chromosomes (genes also present on alternate scaffolds) | 1,161 |

### Human Genome GFF3 Statistics

| Metric | Count |
|--------|-------|
| Total protein_coding genes in GFF3 | 23,306 |
| Primary genes (no `-N` suffix) | 19,927 |
| Alternate loci genes (with `-N` suffix) | 3,379 |
| Unique NCBI GeneIDs | 20,076 |
| GeneIDs with single entry | 18,424 |
| GeneIDs with multiple entries (alternate loci) | 1,652 |
| GeneIDs where ALL entries have `-N` suffix (no primary form) | 41 |

### Why the Original Script Didn't Catch This

The original `003_ai-python-extract_longest_transcript_proteomes.py` (RUN_1) parsed the GFF3 correctly and built the gene → mRNA → CDS → protein_id mapping chain accurately. However, it had no concept of alternate loci — it treated `gene-AAAS` and `gene-AAAS-2` as two independent genes, each getting their own T1 protein in the output. The `-2` suffix was sanitized to `_2` (dash → underscore) during header formatting, so the output contained both `AAAS` and `AAAS_2` as separate entries.

### Which Species Are Affected

A systematic scan of all 34 NCBI species GFF3 files revealed that only **4 species** have alternate loci genes:

| Species | Total Protein-Coding Genes | -N Suffix Genes | Has GeneID Attribute |
|---------|---------------------------|-----------------|---------------------|
| Homo sapiens | 23,306 | 3,379 | Yes |
| Hydra vulgaris | 22,837 | 47 | Yes |
| Aplysia californica | 19,425 | 25 | Yes |
| Caenorhabditis elegans | 19,983 | 4 | Yes |

The remaining 30 NCBI species had zero `-N` suffix genes and were unaffected.

**Important context**: This issue is specific to NCBI GFF3 files. Non-NCBI species in the GIGANTIC species set (from repositories like Figshare, Zenodo, Dryad, etc.) use entirely different GFF3 structures and naming conventions. The fix was designed to be a no-op for species without duplicate GeneIDs, making it safe to apply universally to all NCBI species.

---

## 3. The Biological Reality of NCBI Alternate Loci

### What Are Alternate Loci?

Modern genome assemblies often include more than just the primary chromosome sequences. NCBI RefSeq assemblies can include:

1. **Primary assembly** (NC_ scaffolds): The main chromosome sequences representing the reference genome
2. **Alternate haplotype scaffolds** (NT_ scaffolds): Alternative versions of genomic regions where significant population variation exists (e.g., the MHC/HLA region on chromosome 6, which has multiple well-characterized haplotypes)
3. **Unplaced scaffolds** (NW_ scaffolds): Assembled contigs that could not be reliably placed on a specific chromosome, often from heterozygous regions or poorly assembled areas

### Why NCBI Duplicates Gene Annotations

When a gene exists on both the primary chromosome and an alternate scaffold, NCBI annotates it on **both** scaffolds. This makes biological sense for genome browsing and variant analysis, but creates a problem for proteomics: the same gene (same GeneID) produces multiple gene entries in the GFF3, each potentially with slightly different protein products due to haplotype-specific sequence differences.

### The T1 Problem

For T1 (transcript 1 / longest isoform) proteome extraction, we want **one protein per gene**. When the same gene appears on multiple scaffolds:

- The primary and alternate may encode proteins of different lengths (due to haplotype-specific mutations affecting start codons, stop codons, or splice sites)
- In the original extraction (RUN_1), both the primary and alternate entries competed independently for T1 selection, resulting in the same biological gene appearing twice (or more) in the proteome with slightly different sequences and different gene IDs

---

## 4. The Fix: Alternate Loci Filtering

### Strategy

The fix groups gene entries by their shared NCBI GeneID and selects only one representative per GeneID:

1. **Parse all protein_coding genes** from the GFF3, extracting the gene feature ID and the NCBI GeneID from the Dbxref attribute
2. **Group by GeneID**: For each GeneID, collect all gene entries
3. **Select the primary**: For GeneIDs with multiple entries:
   - **If a primary exists** (entry without `-N` suffix): keep it, drop all `-N` suffixed entries
   - **If no primary exists** (all entries have `-N` suffix): keep the lowest-numbered one (e.g., `-2` is kept over `-3`)
4. **Build a drop set**: Gene IDs (raw, e.g., `AAAS-2`) marked for exclusion
5. **Filter during GFF3 parsing**: When building the gene → mRNA → CDS → protein_id mapping chain, skip any mRNA or CDS whose parent gene is in the drop set

### Why This Approach

- **GeneID-based grouping** is the most reliable method because NCBI explicitly uses GeneID to link primary and alternate entries. Relying on gene name suffix patterns alone could be fragile.
- **Preferring the primary (no suffix)** ensures we keep the canonical annotation from the primary assembly
- **Fallback to lowest suffix** handles the rare case (41 genes in human) where all entries have a suffix — this can happen when the gene is only annotated on alternate/unplaced scaffolds
- **No-op for unaffected species**: Species without duplicate GeneIDs pass through the filter unchanged

---

## 5. Implementation Details

### Scripts Involved

#### Original Script (RUN_1 — the version with the bug)

**File**: `nf_workflow-RUN_1_01-ncbi_genomes/ai/scripts/003_ai-python-extract_longest_transcript_proteomes.py`
**Attribution**: AI: Claude Code | Opus 4 | 2026 February 12 15:45
**What it does**: Extracts T1 proteomes from NCBI data. No alternate loci awareness — treats every gene feature as independent.

#### Fixed Script (RUN_2 — the corrected version)

**File**: `nf_workflow-RUN_2_01-ncbi_genomes/ai/scripts/003_ai-python-extract_longest_transcript_proteomes.py`
**Attribution**: AI: Claude Code | Opus 4.6 | 2026 March 31
**What changed**:

1. **New function `identify_alternate_loci_genes()`** (lines ~160-250):
   - Parses all protein_coding gene features from the GFF3
   - Extracts both the gene feature ID (`ID=gene-AAAS-2`) and the NCBI GeneID (`Dbxref=GeneID:8086`)
   - Groups entries by GeneID
   - For multi-entry GeneIDs, selects the primary (no `-N` suffix) or lowest-numbered alternate
   - Returns a set of gene IDs to drop and a detailed log of every decision

2. **Modified function `build_gene_to_protein_mapping()`**:
   - Now accepts an optional `genes_to_drop` parameter
   - When building the mRNA → gene mapping, skips mRNAs whose parent gene is in the drop set
   - When building the CDS → protein mapping, skips CDS entries whose parent mRNA was dropped or whose parent gene is in the drop set

3. **Modified function `extract_t1_proteome()`**:
   - Passes `genes_to_drop` through to `build_gene_to_protein_mapping()`

4. **New function `write_alternate_loci_log()`**:
   - Writes a detailed TSV log documenting every retained/dropped gene decision with GeneIDs and scaffold locations

5. **Updated `main()` function**:
   - Calls `identify_alternate_loci_genes()` before T1 extraction for each species
   - Reports alternate loci filtering counts in console output
   - Writes the alternate loci log to the maps output directory
   - Includes alternate loci counts in the final summary table

### Post-Processing Scripts

Two additional scripts were used to generate the ID mapping files for downstream subproject filtering. These were run interactively (not part of the formal pipeline) and their logic is documented here:

#### Retained/Dropped List Generator

**Purpose**: Compare RUN_1 and RUN_2 T1 proteomes to identify which sequences were dropped and which were newly added.

**Logic**:
1. For each species, read all sequence IDs from both the RUN_1 and RUN_2 versions of the T1 proteome
2. Compute set differences: `dropped = RUN_1 - RUN_2`, `new = RUN_2 - RUN_1`, `shared = RUN_1 ∩ RUN_2`
3. For affected species, write per-species TSV files listing each sequence as retained or dropped
4. Write a master dropped list for downstream filtering

**Output**: `master_dropped_alternate_loci.tsv`, per-species `{Species}_retained_dropped.tsv` files

#### Old-to-New ID Mapping Generator

**Purpose**: For dropped sequences that were replaced by a different ID for the same gene, generate an old ID → new ID mapping so downstream subprojects can update their results rather than simply discarding them.

**Logic**:
1. For each dropped sequence ID, attempt to find its replacement in the RUN_2 set using three matching strategies (in priority order):
   a. **Same protein accession**: Extract the protein accession (e.g., `NP_056480.1`) from both old and new IDs — if the same accession appears in both, it's the same protein with a different gene name
   b. **Same sequence content**: Read the actual amino acid sequences from both RUN_1 and RUN_2 FASTAs — if an unmatched new sequence is identical to the dropped sequence, they represent the same protein
   c. **Same gene base name, different protein**: Strip the `_N` suffix from the gene name and look for a match in the new set — this catches cases where the primary gene selected a different (usually shorter) isoform as T1

2. Sequences that don't match by any method are classified as `no_replacement` (true duplicates that were simply removed because the primary was already present)

**Output**: `master_alternate_loci_id_mapping.tsv`

---

## 6. Results and Validation

### Species-Level Impact

| Species | RUN_1 Proteins | RUN_2 Proteins | Net Change | Genes Dropped | Genes Replaced | Pure Drops |
|---------|---------------|---------------|------------|---------------|----------------|------------|
| Homo sapiens | 21,412 | 20,076 | -1,336 | 2,602 | 1,682 | 920 |
| Hydra vulgaris | 22,837 | 22,797 | -40 | 40 | 0 | 40 |
| Aplysia californica | 19,405 | 19,405 | 0 | 20 | 20 | 0 |
| Caenorhabditis elegans | 19,983 | 19,983 | 0 | 0 | 0 | 0 |
| All other NCBI species (30) | unchanged | unchanged | 0 | 0 | 0 | 0 |
| **Total** | | | **-1,376** | **2,662** | **1,702** | **960** |

### Explanation of Net Change vs. Dropped Counts

For **Homo sapiens**, 2,602 sequences were dropped but only 1,336 net sequences were removed. This is because:
- 920 were **pure drops** (the primary was already in RUN_1, so removing the alternate just eliminates a duplicate)
- 1,682 were **replaced** — the alternate's gene ID was dropped and a new/renamed primary gene ID took its place:
  - 1,243 matched by same protein accession (same exact protein, different gene name in header)
  - 81 matched by identical sequence content (different accession but same amino acids)
  - 358 same gene but different protein selected (primary gene's shorter isoform became T1)

For **Aplysia californica**, 20 alternates were dropped and 20 primaries were added — a perfect 1:1 replacement where the alternate and primary had the same protein accession. The total count stayed at 19,405.

For **Hydra vulgaris**, 40 alternates were dropped with no replacements needed — the primaries were already present in RUN_1.

For **C. elegans**, despite having 4 `-N` suffix genes in the GFF3, the filtering had no effect on the T1 proteome count (the primary forms were already the ones selected as T1).

### Human Gene Count Validation

The corrected count of **20,076 protein-coding genes** for human aligns much better with the commonly referenced ~20,000 protein-coding genes. The remaining ~76 above 20,000 likely reflects:
- Recent gene annotations not yet in the canonical count
- Predicted genes (LOC/XP_ accessions) that may be debated
- Legitimate newly discovered protein-coding genes

This is a far more defensible number than the original 21,412.

---

## 7. Downstream Impact and ID Mapping

### Mapping File for Downstream Subprojects

**File**: `OUTPUT_pipeline/3-output/maps/master_alternate_loci_id_mapping.tsv`

This file contains 2,662 records documenting every dropped sequence and its fate. Each record includes:

| Column | Description |
|--------|-------------|
| `Genus_Species` | Species name |
| `Old_Source_ID` | RUN_1 sequence ID in source format (`Genus_species-gene-transcript-protein`) |
| `Old_GIGANTIC_Partial_ID` | RUN_1 ID in downstream GIGANTIC format (`g_gene-t_transcript-p_protein`) |
| `New_Source_ID` | RUN_2 replacement ID (empty if purely dropped) |
| `New_GIGANTIC_Partial_ID` | RUN_2 replacement in GIGANTIC format (empty if purely dropped) |
| `Match_Type` | How old and new were matched |
| `Status` | `replaced` or `dropped` |

### Match Types Explained

| Match Type | Count | Meaning | Downstream Action |
|------------|-------|---------|-------------------|
| `same_protein_id` | 1,263 | Same protein accession, gene name changed (e.g., `AAAS_2` → `AAAS`). Identical protein sequence. | Rename old ID to new ID in results. Data is valid. |
| `same_sequence` | 81 | Different protein accession but identical amino acid sequence. | Rename old ID to new ID in results. Data is valid. |
| `same_gene_different_protein` | 358 | Same gene locus but the primary selected a different (usually shorter) isoform as T1. The actual protein sequence changed. | Flag results. Sequence-dependent analyses (e.g., BLAST, alignments) may need recomputation. Gene-level annotations are still valid. |
| `no_replacement` | 960 | Alternate locus gene that was a true duplicate — the primary was already present in both RUN_1 and RUN_2. | Simply remove from results. The primary gene's results already cover this gene. |

### Recommended Downstream Filtering Strategy

For each downstream subproject, use the mapping file to:

1. **Remove** all sequences with `status=dropped` and `match_type=no_replacement` (960 sequences). These were duplicates — the primary gene's data is already in the results.

2. **Rename** all sequences with `match_type=same_protein_id` or `match_type=same_sequence` (1,344 sequences). The old ID should be replaced with the new ID in all result files. The underlying data is identical.

3. **Flag for review** all sequences with `match_type=same_gene_different_protein` (358 sequences). The gene is the same but the representative protein changed. Gene-level analyses (e.g., orthogroup membership, gene family assignment) are likely still valid. Sequence-level analyses (e.g., BLAST hits, domain annotations, alignments) may need recomputation with the new protein sequence.

---

## 8. Complete File Inventory

### RUN_1 (Original — Preserved Intact)

**Location**: `nf_workflow-RUN_1_01-ncbi_genomes/`

| Path | Description |
|------|-------------|
| `ai/scripts/003_ai-python-extract_longest_transcript_proteomes.py` | Original T1 extraction script (no alternate loci filtering) |
| `OUTPUT_pipeline/2-output/gff3/` | NCBI GFF3 annotation files (34 species) |
| `OUTPUT_pipeline/2-output/protein/` | NCBI protein FASTA files (34 species) |
| `OUTPUT_pipeline/2-output/genome/` | NCBI genome FASTA files (34 species) |
| `OUTPUT_pipeline/3-output/T1_proteomes/` | Original T1 proteomes (with alternate loci inflating counts) |
| `OUTPUT_pipeline/3-output/maps/` | Original identifier mapping files |
| `INPUT_user/ncbi_genomes_manifest.tsv` | Species manifest (genus_species → accession) |

### RUN_2 (Corrected — With Alternate Loci Filtering)

**Location**: `nf_workflow-RUN_2_01-ncbi_genomes/`

| Path | Description |
|------|-------------|
| `ai/scripts/003_ai-python-extract_longest_transcript_proteomes.py` | **Fixed** T1 extraction script with alternate loci filtering |
| `OUTPUT_pipeline/2-output` | Symlink to RUN_1's 2-output (shared input data, not duplicated) |
| `OUTPUT_pipeline/3-output/T1_proteomes/` | Corrected T1 proteomes (alternate loci removed) |
| `OUTPUT_pipeline/3-output/genomes/` | Genome files (copied, same as RUN_1) |
| `OUTPUT_pipeline/3-output/gene_annotations/` | GFF3 files (copied, same as RUN_1) |
| `OUTPUT_pipeline/3-output/maps/ncbi_genomes-map-sequence_identifiers.tsv` | Sequence ID mapping (corrected, fewer entries) |
| `OUTPUT_pipeline/3-output/maps/ncbi_genomes-map-genome_identifiers.tsv` | Genome scaffold ID mapping (unchanged) |
| `OUTPUT_pipeline/3-output/maps/ncbi_genomes-log-alternate_loci_filtering.tsv` | **New**: Detailed log of every alternate loci retain/drop decision |
| `OUTPUT_pipeline/3-output/maps/master_alternate_loci_id_mapping.tsv` | **New**: Old ID → New ID mapping for downstream filtering |
| `OUTPUT_pipeline/3-output/maps/master_dropped_alternate_loci.tsv` | **New**: Simple list of all dropped sequence IDs |
| `OUTPUT_pipeline/3-output/maps/master_retained_dropped.tsv` | **New**: Full retained/dropped list for all species |
| `OUTPUT_pipeline/3-output/maps/Homo_sapiens_retained_dropped.tsv` | **New**: Per-species retained/dropped (Homo sapiens) |
| `OUTPUT_pipeline/3-output/maps/Hydra_vulgaris_retained_dropped.tsv` | **New**: Per-species retained/dropped (Hydra vulgaris) |
| `OUTPUT_pipeline/3-output/maps/Aplysia_californica_retained_dropped.tsv` | **New**: Per-species retained/dropped (Aplysia californica) |
| `INPUT_user/ncbi_genomes_manifest.tsv` | Species manifest (copied from RUN_1) |
| `DOCUMENTATION-alternate_loci_filtering.md` | This documentation file |

### Key Mapping Files Explained

#### `ncbi_genomes-log-alternate_loci_filtering.tsv`

The most detailed log — documents every individual gene entry that was evaluated for alternate loci filtering. Contains 5,002 records (header + data). For each GeneID that had multiple gene entries:

```
Genus_Species    NCBI_GeneID    Gene_ID        Scaffold           Decision
Homo_sapiens     8086           AAAS           NC_000012.12       retained (primary_retained)
Homo_sapiens     8086           AAAS-2         NW_025791795.1     dropped (alternate_dropped)
```

This file documents the **why** behind every filtering decision and can be used to audit the process.

#### `master_alternate_loci_id_mapping.tsv`

The actionable file for downstream subprojects — maps old IDs to new IDs with match type classification. This is what pipelines should use to update their results.

#### `master_dropped_alternate_loci.tsv`

A simpler version — just the list of dropped sequence IDs without replacement information. Useful for quick filtering when you only need to remove sequences.

---

## 9. How to Reproduce This Work

### Prerequisites

- Python 3.9+
- Access to the NCBI GFF3 and protein FASTA files in `nf_workflow-RUN_1_01-ncbi_genomes/OUTPUT_pipeline/2-output/`
- The species manifest at `INPUT_user/ncbi_genomes_manifest.tsv`

### Step 1: Create the RUN_2 Directory

```bash
cd research_notebook/research_user/species71/ncbi_genomes/

# Create directory structure
RUN2="nf_workflow-RUN_2_01-ncbi_genomes"
mkdir -p "${RUN2}/ai/scripts"
mkdir -p "${RUN2}/OUTPUT_pipeline/3-output/T1_proteomes"
mkdir -p "${RUN2}/OUTPUT_pipeline/3-output/genomes"
mkdir -p "${RUN2}/OUTPUT_pipeline/3-output/gene_annotations"
mkdir -p "${RUN2}/OUTPUT_pipeline/3-output/maps"
mkdir -p "${RUN2}/INPUT_user"

# Symlink to RUN_1's inputs (avoid duplicating 27 GB of data)
ln -sf "$(realpath nf_workflow-RUN_1_01-ncbi_genomes/OUTPUT_pipeline/2-output)" \
    "${RUN2}/OUTPUT_pipeline/2-output"

# Copy manifest
cp nf_workflow-RUN_1_01-ncbi_genomes/INPUT_user/ncbi_genomes_manifest.tsv \
    "${RUN2}/INPUT_user/"
```

### Step 2: Place the Fixed Script

Copy or create the fixed `003_ai-python-extract_longest_transcript_proteomes.py` into `${RUN2}/ai/scripts/`. The key addition is the `identify_alternate_loci_genes()` function that groups genes by GeneID and builds a drop set.

### Step 3: Run the T1 Extraction

```bash
cd nf_workflow-RUN_2_01-ncbi_genomes

python3 ai/scripts/003_ai-python-extract_longest_transcript_proteomes.py \
    --manifest INPUT_user/ncbi_genomes_manifest.tsv \
    --genome-dir OUTPUT_pipeline/2-output/genome \
    --gff3-dir OUTPUT_pipeline/2-output/gff3 \
    --protein-dir OUTPUT_pipeline/2-output/protein \
    --output-dir OUTPUT_pipeline/3-output \
    --download-date downloaded_20260211
```

This produces:
- Corrected T1 proteomes in `OUTPUT_pipeline/3-output/T1_proteomes/`
- Identifier mapping files in `OUTPUT_pipeline/3-output/maps/`
- The alternate loci filtering log in `OUTPUT_pipeline/3-output/maps/ncbi_genomes-log-alternate_loci_filtering.tsv`

Runtime: approximately 5-10 minutes on a login node (the GFF3 parsing for human is the slowest step).

### Step 4: Generate ID Mapping Files

The `master_alternate_loci_id_mapping.tsv` and `master_dropped_alternate_loci.tsv` files were generated by comparing the RUN_1 and RUN_2 T1 proteome FASTA files. The comparison logic:

1. Read sequence IDs from both RUN_1 and RUN_2 versions of each species' T1 proteome
2. Compute dropped IDs (`RUN_1 - RUN_2`) and new IDs (`RUN_2 - RUN_1`)
3. For each dropped ID, attempt to find its replacement in the new IDs by:
   a. Matching protein accession (4th dash-separated field in the header)
   b. Matching identical amino acid sequence content
   c. Matching gene base name (stripping `_N` suffix)
4. Write results to TSV files

This logic was executed interactively and is documented in full in this file (Section 5, "Post-Processing Scripts"). It is not part of the formal pipeline script but could be formalized if needed.

### Step 5: Verify Results

```bash
# Check human protein count
grep -c "^>" OUTPUT_pipeline/3-output/T1_proteomes/Homo_sapiens-genome-ncbi_GCF_000001405.40-downloaded_20260211.aa
# Expected: 20,076

# Check alternate loci log
wc -l OUTPUT_pipeline/3-output/maps/ncbi_genomes-log-alternate_loci_filtering.tsv
# Expected: 5,003 (header + 5,002 data rows)

# Check mapping file
wc -l OUTPUT_pipeline/3-output/maps/master_alternate_loci_id_mapping.tsv
# Expected: 2,663 (header + 2,662 data rows)

# Verify RUN_1 is untouched
grep -c "^>" ../nf_workflow-RUN_1_01-ncbi_genomes/OUTPUT_pipeline/3-output/T1_proteomes/Homo_sapiens-genome-ncbi_GCF_000001405.40-downloaded_20260211.aa
# Expected: 21,412 (unchanged)
```

---

## 10. Limitations and Caveats

### This Fix Is NCBI-Specific

The alternate loci filtering relies on the `GeneID` attribute in the `Dbxref` field of NCBI GFF3 files. Non-NCBI genome annotations (from Figshare, Zenodo, Dryad, etc.) use entirely different GFF3 structures and may not have GeneID attributes. The fix is designed to be a no-op for these species — if no duplicate GeneIDs are found, no filtering occurs.

### The "Same Gene, Different Protein" Cases

For 358 human genes, the alternate locus encoded a longer protein than the primary. When the alternate was removed, the primary gene's shorter isoform became the T1 representative. This means:

- The **gene-level identity** is preserved (same gene locus, same GeneID)
- The **protein sequence changed** (shorter isoform selected)
- Downstream analyses that depend on exact protein sequence (BLAST, domain annotation, sequence alignment) may produce slightly different results
- Downstream analyses that work at the gene level (orthogroup membership, gene family assignment, conservation analysis) should be unaffected

### The 41 "No Primary" GeneIDs

For 41 human GeneIDs, all gene entries had a `-N` suffix (no unsuffixed primary form). In these cases, the lowest-numbered suffix was retained. This is a reasonable heuristic but may not always select the "best" representative. These cases are fully documented in the alternate loci filtering log and can be manually reviewed if needed. Examples include `H3-4` (histone) and several `KRTAP` (keratin-associated protein) family members.

### Future Genome Assembly Updates

If NCBI updates the human genome assembly (or any other species assembly), the alternate loci landscape may change. The filtering should be re-run on updated GFF3 files. The fix is robust to assembly changes because it relies on GeneID-based grouping rather than hard-coded gene lists.

### Non-NCBI Species with Similar Issues

It is theoretically possible that non-NCBI genome annotations could have similar alternate loci duplication issues with different naming conventions. The current fix does not address these hypothetical cases. If unusual protein counts are observed for non-NCBI species, a similar investigation should be conducted with attention to the specific annotation source's conventions.

---

## Appendix: Discovery Timeline

| Date | Event |
|------|-------|
| 2026-03-31 | During one_direction_homologs post-processing, human T1 proteome reported as 21,412 proteins |
| 2026-03-31 | Investigation traced inflation to source T1 extraction (script 003 in RUN_1) |
| 2026-03-31 | Root cause identified: NCBI GFF3 alternate loci creating duplicate gene entries |
| 2026-03-31 | Systematic scan: 4 of 34 NCBI species affected (Homo sapiens, Hydra vulgaris, Aplysia californica, Caenorhabditis elegans) |
| 2026-03-31 | Fixed script 003 written with GeneID-based alternate loci filtering |
| 2026-03-31 | RUN_2 created and executed: human T1 corrected from 21,412 to 20,076 proteins |
| 2026-03-31 | ID mapping files generated for downstream subproject filtering |
| 2026-04-01 | This documentation written |
