# OrthoHMM output_to_input

This directory contains outputs from the OrthoHMM workflow that are used by downstream subprojects.

## Files (populated after workflow completion)

| File | Description | Used By |
|------|-------------|---------|
| `6_ai-orthogroups_gigantic_ids.txt` | Orthogroup assignments with full GIGANTIC identifiers | trees, annotations |
| `2_ai-header_mapping.tsv` | Mapping between short IDs and GIGANTIC identifiers | debugging, analysis |
| `4_ai-orthohmm_summary_statistics.tsv` | Summary statistics (coverage, sizes) | reports |

## Format: Orthogroups File

```
OG0000001: Homo_sapiens|gene1 Mus_musculus|gene2 ...
OG0000002: Homo_sapiens|gene3 Drosophila_melanogaster|gene4 ...
```

## Format: Header Mapping

Tab-separated with columns:
- Short_ID: The short header used in OrthoHMM (Genus_species-N)
- Original_Header: Full GIGANTIC protein identifier
- Genus_Species: Species name
- Original_Filename: Source proteome file

## Last Updated

This directory is populated by `workflow-RUN_*/RUN-workflow.sh` upon successful completion.
