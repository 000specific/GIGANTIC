# gene_groups_hgnc-COPYME / INPUT_user

Instance-level user inputs for this gene-groups instance.

## Files used by workflow-hgnc_user_list

**`user_gene_set.tsv`** — User-defined gene set(s) to characterize. Read by
`STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/` to:

1. Resolve each human gene symbol → UniProt accession via the locally-cached
   `output_to_input/hugo_hgnc_database/hgnc_complete_set.txt` (no network
   needed once that's been populated).
2. Fetch the canonical Swiss-Prot FASTA for each accession from the UniProt
   REST API.
3. Emit a per-group RGS FASTA in the format STEP_1 expects.

See `user_gene_set_EXAMPLE.tsv` for the format. When you instantiate this
template (e.g., `cp -r gene_groups_hgnc-COPYME gene_groups-snap_family`),
replace the example with your own `user_gene_set.tsv`.

## Files used by workflow-hgnc_database

This workflow doesn't need anything from INPUT_user — it processes all
~2060 HGNC-curated gene groups from the downloaded reference data. Other
files placed here (e.g., gene_groups_manifest overrides for STEP_1 reruns)
are read by later STEPs in this instance.

## Why instance-level, not workflow-level

The `user_gene_set.tsv` defines what this whole *instance* is about (e.g.,
"this is the SNAP family instance"). Instance-level INPUT_user means
multiple workflows in the same instance can see it, and the file isn't
buried inside a single workflow's directory.

Subproject-level reference data (HGNC TSVs) is separately tracked in
`trees_gene_groups/output_to_input/hugo_hgnc_database/` — populated by
the 000 download script, not user-provided.
