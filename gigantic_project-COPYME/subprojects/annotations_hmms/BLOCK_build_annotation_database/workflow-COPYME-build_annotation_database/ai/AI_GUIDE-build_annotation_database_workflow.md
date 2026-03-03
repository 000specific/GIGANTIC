# AI_GUIDE-build_annotation_database_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read the BLOCK guide (`../AI_GUIDE-build_annotation_database.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Annotations overview | `../../../AI_GUIDE-annotations_hmms.md` |
| Build database concepts | `../../AI_GUIDE-build_annotation_database.md` |
| Running the workflow | This file |

## Quick Start

```bash
vi build_annotation_database_config.yaml
bash RUN-workflow.sh
```

## Pipeline Steps

1. **Discover tool outputs** - Scan BLOCK output_to_input directories for available annotation results
2. **Download GO ontology** - Fetch current Gene Ontology OBO file from GO Consortium
3. **Parse InterProScan** - Standardize InterProScan domain/GO annotations into unified format
4. **Parse DeepLoc** - Standardize DeepLoc localization predictions into unified format
5. **Parse SignalP** - Standardize SignalP signal peptide predictions into unified format
6. **Parse tmbed** - Standardize tmbed transmembrane topology into unified format
7. **Parse MetaPredict** - Standardize MetaPredict disorder predictions into unified format
8. **Per-protein statistics** - Compute annotation counts and feature summaries per protein
9. **Per-species statistics** - Compute annotation summaries per species
10. **Build integrated table** - Merge all tool annotations into single per-protein database
11. **Cross-tool consistency** - Check for contradictions between tool predictions
12. **Domain architecture analysis** - Summarize domain combinations across species
13. **Localization summary** - Summarize subcellular localization patterns across species
14. **Disorder-transmembrane overlap** - Analyze overlap between disordered and transmembrane regions
15. **Generate database files** - Write final annotation database in standardized GIGANTIC format
16. **Publish to output_to_input** - Copy key outputs for downstream subproject access

## Key Configuration

- `build_annotation_database_config.yaml` - Set paths to BLOCK output directories, GO OBO URL, species list
- Pipeline auto-discovers which tool BLOCKs have been completed (handles partial annotation sets)

## Verification Commands

```bash
# Check integrated database was created
ls OUTPUT_pipeline/15-output/*annotation_database*.tsv

# Check database has expected number of proteins
wc -l OUTPUT_pipeline/15-output/*annotation_database*.tsv

# Check per-species statistics
ls OUTPUT_pipeline/9-output/*.tsv | wc -l

# Check cross-tool analysis reports
ls OUTPUT_pipeline/11-output/*.tsv
ls OUTPUT_pipeline/12-output/*.tsv

# Verify output_to_input was populated
ls ai/output_to_input/
```

## Common Errors

| Error | Solution |
|-------|----------|
| `No tool outputs found` | Complete at least one tool BLOCK before running this workflow |
| `GO download failed` | Check internet connectivity; the OBO file is downloaded from geneontology.org |
| `Missing species in tool output` | Not all tools may have run on all species; pipeline handles partial coverage |
| `Protein ID mismatch between tools` | Ensure all tool BLOCKs used the same proteome FASTA files from genomesDB |
| `Empty integrated table` | Check individual parse steps (3-7) for errors; verify tool outputs are not empty |
| Stale cached results after script update | Delete `work/` and `.nextflow*`, re-run without `-resume` |
