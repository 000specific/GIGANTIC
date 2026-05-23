# gene_coordinates / NCBI extractor

**AI**: Claude Code | Opus 4.7 (1M context) | 2026 May 04
**Human**: Eric Edsinger

Extracts per-species gene coordinate TSV files from NCBI GFF3 annotations.

## Inputs

- `INPUT_user/ncbi_genomes_manifest.tsv` — list of NCBI species (genus_species, accession). Copied from `species71/ncbi_genomes/nf_workflow-RUN_2_01-ncbi_genomes/INPUT_user/`.
- `../../ncbi_genomes/nf_workflow-RUN_2_01-ncbi_genomes/OUTPUT_pipeline/2-output/gff3/` — source GFF3 files (already downloaded for T1 extraction).
- `../../output_to_input/T1_proteomes/` — corrected T1 proteomes (used to determine which genes/transcripts are the canonical T1 representatives).

## What the script does

For each NCBI species in the manifest:

1. Read the species' T1 proteome to get the set of `(gene_symbol, transcript_acc, protein_acc)` tuples actually present (post alternate-loci filtering).
2. Parse the species' GFF3 to build:
   - `gene_id → (Seqid, Gene_Start, Gene_End, Strand)` for `gene` features with `gene_biotype=protein_coding`
   - `mRNA_id → gene_id` (from `Parent=` attributes)
   - `mRNA_id → CDS_intervals` (sorted, merged from CDS features)
3. For each `(gene_symbol, transcript_acc, protein_acc)` from the proteome:
   - Look up gene coordinates via `gene-<gene_symbol>` in the gene map
   - Look up CDS intervals via the transcript ID (e.g., `rna-NM_130786.4`) in the mRNA map
4. Write a row per gene to `OUTPUT_pipeline/<Genus_species>-gene_coordinates.tsv`.

This approach uses the corrected T1 proteome as the source of truth for "which
genes count" — guaranteeing 1:1 alignment with the proteome and inheriting the
alternate-loci filtering that was already applied in the T1 extractor.

## Outputs

- `OUTPUT_pipeline/<Genus_species>-gene_coordinates.tsv` — one file per species with columns:
  `Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  CDS_Intervals`
- `OUTPUT_pipeline/extraction_summary.tsv` — one row per species with counts and status.
- Each per-species TSV is also symlinked into `../output_to_input/gene_coordinates/`.

## Run

```bash
# For COPYME testing, run from this dir:
bash RUN-workflow.sh

# For production, copy to RUN_1 first:
cp -r nf_workflow-COPYME_01-ncbi_genomes nf_workflow-RUN_01-ncbi_genomes
cd nf_workflow-RUN_01-ncbi_genomes
bash RUN-workflow.sh
```

## Validation

Human gene count should match what we documented in
`../../ncbi_genomes/nf_workflow-RUN_2_01-ncbi_genomes/DOCUMENTATION-human_gene_count_reconciliation.md`
— **20,076 rows for Homo_sapiens**.
