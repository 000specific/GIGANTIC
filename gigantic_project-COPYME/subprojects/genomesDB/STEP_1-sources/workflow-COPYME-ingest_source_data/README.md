# Source Data Ingestion Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.5 | 2026 February 13 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP: [`../README.md`](../README.md) — STEP_1-sources overview
- Parent subproject: [`../../README.md`](../../README.md) — genomesDB overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Input staging arena: project-level `INPUT_user/genomic_resources/`
  (symlinks per §17, §18; see [`../../../../INPUT_user/AI_GUIDE.md`](../../../../INPUT_user/AI_GUIDE.md))
- **Next workflow**: `../../STEP_2-standardize_and_evaluate/workflow-COPYME-*/`

---

Ingest user-provided genome, proteome, and annotation files into GIGANTIC for downstream processing.

## Quick Start

1. Place your source files in the project-level `INPUT_user/genomic_resources/` subdirectories (genomes/, proteomes/, annotations/) or somewhere else accessible (e.g., the project-root sandbox at `../../../../research_notebook/research_user/` per §1, §25)

2. **Ensure files follow GIGANTIC naming convention**:
   ```
   genus_species-genome_source_identifier-downloaded_date.extension
   ```
   Examples:
   ```
   Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta  # genome
   Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3   # annotation
   Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa     # proteome
   ```

3. **Ensure FASTA headers follow convention**:
   ```
   >genus_species-source_gene_id-source_transcript_id-source_protein_id
   ```
   Example:
   ```
   >Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
   ```

4. Create `INPUT_user/source_manifest.tsv` with **4 columns**:
   ```tsv
   genus_species	genome_path	genome_annotation_path	proteome_path
   Homo_sapiens	../../../../INPUT_user/genomic_resources/genomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa
   ```
   Paths reference the project-level `INPUT_user/genomic_resources/` subdirectories:
   - `genomic_resources/genomes/` for `.fasta` files
   - `genomic_resources/proteomes/` for `.aa` files
   - `genomic_resources/annotations/` for `.gff3`/`.gtf` files

   Use "NA" for any data type not available for a species.
   (See `INPUT_user/source_manifest_example.tsv` for detailed format)

5. Edit `START_HERE-user_config.yaml` with your project name

6. Run the workflow:
   - **Local**: `bash RUN-workflow.sh`
   - **SLURM**: Edit account/qos in `RUN-workflow.sh` (unified driver; §29), then `bash RUN-workflow.sh` (with `execution_mode: "slurm"` in the YAML config; §29)

## What This Workflow Does (4 scripts)

Three sit inside NextFlow (`ai/main.nf`), one (003) is invoked by
`RUN-workflow.sh` after the NextFlow pipeline succeeds.

| Script | Where called | Output | Description |
|---|---|---|---|
| 001 | `ai/main.nf` | `OUTPUT_pipeline/1-output/` | Validate manifest and check all files exist |
| 002 | `ai/main.nf` | `OUTPUT_pipeline/2-output/` | Hard-copy all data into GIGANTIC structure |
| 004 | `ai/main.nf` | `ai/logs/` | Write timestamped per-run log |
| 003 | `RUN-workflow.sh` (post-pipeline, bash) | `OUTPUT_pipeline/3-output/` + symlinks under `../../output_to_input/STEP_1-sources/` | Create symlinks for STEP_2 to consume |

**Why 003 lives in `RUN-workflow.sh`**: it crosses workflow boundaries
(writes into the subproject-level `output_to_input/`). Keeping it
outside NextFlow avoids managing paths outside the NextFlow work tree.

## Output Structure

```
OUTPUT_pipeline/
├── 1-output/                           # Validation results
│   ├── 1_ai-source_validation_report.tsv
│   └── 1_ai-validation_summary.txt
├── 2-output/                           # Ingested data (hard copies)
│   ├── T1_proteomes/
│   ├── genomes/
│   ├── genome_annotations/
│   └── 2_ai-ingestion_log.tsv
└── 3-output/                           # Symlink documentation
    └── 3_ai-symlink_manifest.tsv
```

## Symlinks for STEP_2

After running, STEP_2 reads from:
```
../../output_to_input/
├── T1_proteomes/     -> OUTPUT_pipeline/2-output/T1_proteomes/
├── genomes/          -> OUTPUT_pipeline/2-output/genomes/
└── genome_annotations/ -> OUTPUT_pipeline/2-output/genome_annotations/
```

## Next Step

After ingestion, run **STEP_2-standardize_and_evaluate** to:
- Standardize proteome file formats with phylonames
- Generate genome N50 statistics
- Evaluate proteome and genome quality

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE.md` for detailed guidance.
