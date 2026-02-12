# Source Proteome Ingestion Workflow

**AI**: Claude Code | Opus 4.5 | 2026 February 12
**Human**: Eric Edsinger

---

Ingest user-provided genome and proteome files into GIGANTIC for downstream processing.

## Quick Start

1. Place your source files somewhere accessible (e.g., `../user_research/`)

2. **Ensure files follow GIGANTIC naming convention**:
   ```
   genus_species-genome-source_genome_project_identifier-download_date.extension
   ```
   Examples:
   ```
   Homo_sapiens-genome-GCF_000001405.40-20240115.fasta  # genome
   Homo_sapiens-genome-GCF_000001405.40-20240115.gtf    # annotation
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
   genus_species	genome_path	gtf_path	proteome_path
   Homo_sapiens	/path/to/Homo_sapiens-genome-GCF_000001405.40-20240115.fasta	/path/to/Homo_sapiens-genome-GCF_000001405.40-20240115.gtf	/path/to/Homo_sapiens-genome-GCF_000001405.40-20240115.aa
   ```
   (See `INPUT_user/source_manifest_example.tsv` for detailed format)

5. Edit `ingest_sources_config.yaml` with your project name

6. Run the workflow:
   - **Local**: `bash RUN-ingest_sources.sh`
   - **SLURM**: Edit account/qos in `RUN-ingest_sources.sbatch`, then `sbatch RUN-ingest_sources.sbatch`

## What This Workflow Does

1. **Validates** that all source files (genome, GTF, proteome) exist
2. **Hard copies** proteomes to `OUTPUT_pipeline/1-output/proteomes/`
3. **Creates symlinks** in `../../output_to_input/proteomes/` for STEP_2
4. **Logs** the ingestion to research notebook

## Naming Conventions (REQUIRED)

### File Names
```
genus_species-genome-source_genome_project_identifier-download_date.extension
```

| Component | Example |
|-----------|---------|
| genus_species | `Homo_sapiens` |
| genome | `genome` (literal) |
| source_id | `GCF_000001405.40` |
| download_date | `20240115` |
| extension | `.fasta`, `.gtf`, `.aa` |

### FASTA Headers
```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

Example: `>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497`

## Results

- **Archived copies**: `OUTPUT_pipeline/1-output/proteomes/`
- **Symlinks for STEP_2**: `../../output_to_input/proteomes/`
- **Ingestion log**: `OUTPUT_pipeline/1-output/ingestion_log.tsv`
- **Run log**: `research_notebook/research_ai/subproject-genomesDB/logs/`

## Next Step

After ingestion, run **STEP_2-standardize_and_evaluate** to:
- Standardize proteome file formats
- Apply phyloname-based naming convention
- Evaluate genome/proteome quality

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE-ingest_sources_workflow.md` for detailed guidance.
