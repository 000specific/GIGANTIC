# Source Data Ingestion Workflow

**AI**: Claude Code | Opus 4.5 | 2026 February 13
**Human**: Eric Edsinger

---

Ingest user-provided genome, proteome, and annotation files into GIGANTIC for downstream processing.

## Quick Start

1. Place your source files somewhere accessible (e.g., `../user_research/`)

2. **Ensure files follow GIGANTIC naming convention**:
   ```
   genus_species-genome-source_genome_project_identifier-download_date.extension
   ```
   Examples:
   ```
   Homo_sapiens-genome-GCF_000001405.40-20240115.fasta  # genome
   Homo_sapiens-genome-GCF_000001405.40-20240115.gff3   # annotation
   Homo_sapiens-genome-GCF_000001405.40-20240115.aa     # proteome
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
   genus_species	genome_path	gff_path	proteome_path
   Homo_sapiens	/path/to/genome.fasta	/path/to/annotations.gff3	/path/to/proteome.aa
   ```
   Use "NA" for any data type not available for a species.
   (See `INPUT_user/source_manifest_example.tsv` for detailed format)

5. Edit `ingest_sources_config.yaml` with your project name

6. Run the workflow:
   - **Local**: `bash RUN-ingest_sources.sh`
   - **SLURM**: Edit account/qos in `RUN-ingest_sources.sbatch`, then `sbatch RUN-ingest_sources.sbatch`

## What This Workflow Does (3 Steps)

| Step | Script | Output | Description |
|------|--------|--------|-------------|
| 1 | `001_ai-python-validate_source_manifest.py` | `OUTPUT_pipeline/1-output/` | Validate manifest and check all files exist |
| 2 | `002_ai-python-ingest_source_data.py` | `OUTPUT_pipeline/2-output/` | Hard copy all data into GIGANTIC structure |
| 3 | `003_ai-bash-create_output_symlinks.sh` | `OUTPUT_pipeline/3-output/` | Create symlinks in `output_to_input/` for STEP_2 |

**Architecture**: 3 scripts = 3 output directories. Each step produces visible, traceable output.

## Output Structure

```
OUTPUT_pipeline/
├── 1-output/                           # Validation results
│   ├── 1_ai-source_validation_report.tsv
│   └── 1_ai-validation_summary.txt
├── 2-output/                           # Ingested data (hard copies)
│   ├── T1_proteomes/
│   ├── genomes/
│   ├── gene_annotations/
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
└── gene_annotations/ -> OUTPUT_pipeline/2-output/gene_annotations/
```

## Next Step

After ingestion, run **STEP_2-standardize_and_evaluate** to:
- Standardize proteome file formats with phylonames
- Generate genome N50 statistics
- Evaluate proteome and genome quality

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE-ingest_sources_workflow.md` for detailed guidance.
