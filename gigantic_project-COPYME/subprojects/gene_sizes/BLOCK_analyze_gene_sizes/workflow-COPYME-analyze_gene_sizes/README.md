# workflow-COPYME-analyze_gene_sizes

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

---

## Purpose

Nextflow workflow that computes gene structure metrics from user-provided CDS interval data,
calculates genome-wide statistics and relative size ranks (quantiles), and compiles
cross-species summaries for downstream comparative analyses.

---

## Quick Start

### 1. Prepare Input

Place per-species gene structure TSV files in `INPUT_user/`:

```
INPUT_user/
├── gigantic_species_list.txt           # GIGANTIC species list (from genomesDB STEP_4)
├── Homo_sapiens-gene_coordinates.tsv                    # Gene structure for human
├── Mus_musculus-gene_coordinates.tsv                    # Gene structure for mouse
├── Drosophila_melanogaster-gene_coordinates.tsv         # Gene structure for fly
└── ...                                 # One file per species with gene data
```

Each TSV file has this format:
```
Source_Gene_ID	Seqid	Gene_Start	Gene_End	Strand	CDS_Intervals
ENSG00000139618	chr13	32315474	32400266	+	32316422-32316527,32319077-32319325
```

### 2. Configure
Edit `gene_sizes_config.yaml` to verify input paths.

### 3. Run
```bash
# Local
bash RUN-workflow.sh

# SLURM
sbatch RUN-workflow.sbatch
```

### 4. Check Output
```bash
ls OUTPUT_pipeline/4-output/
```

---

## Pipeline

```
Script 001: Validate inputs → Script 002: Extract metrics (parallel) → Script 003: Rank (parallel) → Script 004: Summarize
```

---

## Output

| Directory | Contents |
|-----------|----------|
| `OUTPUT_pipeline/1-output/` | Species processing status (PROCESSED/SKIPPED) |
| `OUTPUT_pipeline/2-output/` | Per-species gene metrics (one TSV per species) |
| `OUTPUT_pipeline/3-output/` | Ranked metrics + genome summaries |
| `OUTPUT_pipeline/4-output/` | Cross-species summary + downstream directories |

---

## Dependencies

- Conda environment: `ai_gigantic_gene_sizes`
- Upstream: genomesDB STEP_4 (species list)
- User: Per-species gene structure TSV files (extracted from GFF/GTF by user)
