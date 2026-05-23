# gene_coordinates — Per-Species Gene Coordinate TSV Extraction

**AI**: Claude Code | Opus 4.7 (1M context) | 2026 May 04
**Human**: Eric Edsinger
**Location**: `research_notebook/research_user/species71/gene_coordinates/`

---

## Purpose

Extract per-species gene coordinate TSV files from the source GFF3/GTF annotations
that were already downloaded for T1 proteome extraction. The TSV files feed the
GIGANTIC `gene_sizes` subproject, which computes gene length, exonic length,
intronic length, exon count, and percentile ranks across species.

This directory is **outside GIGANTIC proper** — it is user/research-notebook work
that produces standardized inputs for the `gene_sizes` pipeline. The scripts here
serve as templates for users adding new genomes to a future GIGANTIC project, and
the NCBI script is suitable for direct reuse without modification.

## Why this is needed

The `gene_sizes` pipeline does NOT parse GFF/GTF directly because format varies
enormously across NCBI / Ensembl / Figshare / Zenodo / Dryad / custom annotations.
Instead, the pipeline consumes a standardized 6-column TSV produced upstream:

```
Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  CDS_Intervals
A1BG            NC_000019.10  58858172  58864865  -  58858174-58858589,58859078-58859270,...
```

`Source_Gene_ID` matches the `g_` field in the GIGANTIC proteome header, e.g.,
`>g_A1BG-t_NM_130786.4-p_NP_570602.2-n_Metazoa_Chordata_...`.

## Architecture (parallel to T1 proteome extraction)

```
species71/
├── ncbi_genomes/                # T1 proteomes — NCBI species (existing)
├── kim_2025_genomes/            # T1 proteomes — Kim 2025 ctenophores (existing)
├── repository_genomes/          # T1 proteomes — repository genomes (existing)
│
├── gene_coordinates/            # THIS DIR — gene coordinate TSVs
│   ├── README.md                # this file
│   ├── nf_workflow-COPYME_01-ncbi_genomes/        # NCBI extractor (one script for all NCBI species)
│   ├── nf_workflow-COPYME_01-kim_2025_genomes/    # Kim 2025 extractor (one script for that source)
│   ├── nf_workflow-COPYME_01-repository_genomes/  # Repository extractors (one script per genome as needed)
│   └── output_to_input/
│       └── gene_coordinates/    # per-species TSVs symlinked from each workflow
│
└── output_to_input/             # aggregated proteomes/genomes/annotations (existing)
```

The directory naming (`nf_workflow-COPYME_*`) mirrors the existing T1 dirs for
consistency, but the workflows here use **plain Python scripts run from
`RUN-workflow.sh`** — no NextFlow.

## Per-source approach

| Source | Strategy | Why |
|---|---|---|
| NCBI genomes | One standardized script | NCBI GFF3 format is consistent; alternate-loci filtering by `Dbxref=GeneID:N` is the same logic used in T1 extraction |
| Kim 2025 genomes | One standardized script | Single annotation source, consistent format within Kim 2025 release |
| Repository genomes | Per-genome scripts as needed | Format varies by source (Figshare / Zenodo / Dryad / custom); each may need bespoke parsing |

## Output

Each per-species TSV is named `<Genus_species>-gene_coordinates.tsv` to match
what the `gene_sizes/START_HERE-user_config.yaml` expects.

The aggregated `output_to_input/gene_coordinates/` is what
`gene_sizes/BLOCK_analyze_gene_sizes/workflow-RUN_*/INPUT_user/` will symlink in.

## Status

Skeleton created 2026-05-04. Extraction scripts and runs still pending.

| Source | Skeleton | Script | Run |
|---|---|---|---|
| NCBI | Yes | In progress | Pending |
| Kim 2025 | Yes | Pending | Pending |
| Repository | Yes | Pending | Pending |

## Relationship to GIGANTIC

These extraction scripts are **outside GIGANTIC's pipeline boundary** — they are
user/research-notebook work that produces standardized inputs. The
`gene_sizes` pipeline (inside GIGANTIC) consumes the TSVs but does not parse
GFFs itself. This separation matches GIGANTIC's general philosophy that
species-specific data extraction is the user's responsibility.

For future GIGANTIC projects:
- The NCBI script here is suitable for direct reuse (NCBI format is standard).
- The Kim and repository scripts are templates / examples to adapt for similar
  sources. Each new genome source may need a bespoke parser.
