# AI Guide: DIAMOND NCBI nr Workflow

**For AI Assistants**: Read the subproject guide first (`../../AI_GUIDE-one_direction_homologs.md`) for concepts and troubleshooting. This guide focuses on running the workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Subproject concepts | `../../AI_GUIDE-one_direction_homologs.md` |
| Running the workflow | This file |

---

## Architecture: 6 Scripts, 6 Output Directories

| Script | Does | Creates |
|--------|------|---------|
| 001 | Validate proteome files and manifest | `OUTPUT_pipeline/1-output/` |
| 002 | Split proteomes into N parts for parallelization | `OUTPUT_pipeline/2-output/` |
| 003 | Run DIAMOND blastp per split file (parallel) | `OUTPUT_pipeline/3-output/` |
| 004 | Combine split results back to per-species files | `OUTPUT_pipeline/4-output/` |
| 005 | Identify top self/non-self hits per protein | `OUTPUT_pipeline/5-output/` |
| 006 | Compile master statistics table across all species | `OUTPUT_pipeline/6-output/` |

---

## User Workflow

### Step 1: Prepare Input Manifest

Create `INPUT_user/proteome_manifest.tsv`:

```tsv
species_name	proteome_path	phyloname
Homo_sapiens	../../genomesDB/output_to_input/proteomes/...aa	Metazoa_Chordata_..._Homo_sapiens
```

See `INPUT_user/proteome_manifest_example.tsv` for a complete example.

### Step 2: Configure DIAMOND Settings

Edit `diamond_ncbi_nr_config.yaml`:

```yaml
diamond:
  database: "/path/to/nr.dmnd"   # REQUIRED
  evalue: "1e-5"
  max_target_sequences: 10
  num_parts: 40
```

### Step 3: Configure SLURM (if applicable)

Edit `RUN-workflow.sbatch`:
- Set `--account=` and `--qos=` to your cluster values

### Step 4: Run

```bash
# Local:
bash RUN-workflow.sh

# SLURM:
sbatch RUN-workflow.sbatch
```

---

## Verification Commands

```bash
# After script 001 - Check validation passed
cat OUTPUT_pipeline/1-output/1_ai-validated_proteome_manifest.tsv | head -5

# After script 002 - Check splits created
ls OUTPUT_pipeline/2-output/splits/ | wc -l
head -3 OUTPUT_pipeline/2-output/2_ai-diamond_job_manifest.tsv

# After script 003 - Check DIAMOND results exist
ls OUTPUT_pipeline/3-output/*.tsv | wc -l

# After script 004 - Check combined results per species
ls OUTPUT_pipeline/4-output/combined_*.tsv | wc -l

# After script 005 - Check top hits and statistics
ls OUTPUT_pipeline/5-output/*_top_hits.tsv | wc -l
ls OUTPUT_pipeline/5-output/*_statistics.tsv | wc -l

# After script 006 - Check master summary
cat OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Manifest not found" | No proteome_manifest.tsv | Create in INPUT_user/ or INPUT_gigantic/ |
| "Proteome file does not exist" | Path in manifest is wrong | Check proteome_path column, ensure files exist |
| "DIAMOND database not found" | Config path incorrect | Edit diamond_ncbi_nr_config.yaml database path |
| "diamond: command not found" | DIAMOND not in environment | Activate conda env or install DIAMOND |
| Script 003 SLURM failures | Memory or time limits | Increase mem/time in nextflow.config |
| No results in 4-output/ | DIAMOND search produced no hits | Check e-value threshold, verify database |
| Incomplete species in 6-output/ | Some DIAMOND jobs failed | Check SLURM logs, rerun failed jobs |

---

## Manual Execution (for debugging)

If NextFlow has issues, run scripts manually:

```bash
# From workflow directory
cd OUTPUT_pipeline

# Script 001
python3 ../ai/scripts/001_ai-python-validate_proteomes.py \
    --manifest ../INPUT_user/proteome_manifest.tsv \
    --output-dir 1-output

# Script 002
python3 ../ai/scripts/002_ai-python-split_proteomes_for_diamond.py \
    --manifest 1-output/1_ai-validated_proteome_manifest.tsv \
    --output-dir 2-output \
    --num-parts 40

# Script 003 (one split at a time)
bash ../ai/scripts/003_ai-bash-run_diamond_search.sh \
    2-output/splits/Homo_sapiens_part_001.fasta \
    /path/to/nr.dmnd \
    3-output/Homo_sapiens_part_001_diamond.tsv \
    1e-5 10 1

# Script 004 (one species at a time)
python3 ../ai/scripts/004_ai-python-combine_diamond_results.py \
    --species-name Homo_sapiens \
    --input-dir 3-output \
    --output-dir 4-output

# Script 005 (one species at a time)
python3 ../ai/scripts/005_ai-python-identify_top_hits.py \
    --input-file 4-output/combined_Homo_sapiens.tsv \
    --output-dir 5-output \
    --species-name Homo_sapiens

# Script 006
python3 ../ai/scripts/006_ai-python-compile_statistics.py \
    --input-dir 5-output \
    --output-dir 6-output
```

---

## DIAMOND Output Format

Script 003 produces 15-column tabular output:

| Column | Field | Description |
|--------|-------|-------------|
| 1 | qseqid | Query sequence ID |
| 2 | sseqid | Subject sequence ID |
| 3 | pident | Percent identity |
| 4 | length | Alignment length |
| 5 | mismatch | Number of mismatches |
| 6 | gapopen | Number of gap openings |
| 7 | qstart | Query start position |
| 8 | qend | Query end position |
| 9 | sstart | Subject start position |
| 10 | send | Subject end position |
| 11 | evalue | E-value |
| 12 | bitscore | Bit score |
| 13 | stitle | Full NCBI header of subject |
| 14 | full_qseq | Full query sequence |
| 15 | full_sseq | Full subject sequence |

The `stitle` field captures the complete NCBI description line, and `full_qseq`/`full_sseq` enable self/non-self hit comparison.
