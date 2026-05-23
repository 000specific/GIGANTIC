# workflow-COPYME-analyze_gene_sizes — `all_inclusive` (Tier 1)

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

---

## Purpose

NextFlow workflow that computes the **methodology-strict (Tier 1)** gene-structure
metrics from user-provided 15-column gene-coordinate TSVs. Produces 7
cross-species metrics — `Gene_Size`, `Transcript_Size`, `CDS_Size`,
`Protein_Size`, `Exon_Count`, `Intron_Total_Size`, `UTR_Total_Size` — plus
within-genome percentile ranks and a cross-species summary.

This is one of two parallel workflow templates in `BLOCK_analyze_gene_sizes/`.
The other (`workflow-COPYME-analyze_gene_sizes-gene_vs_protein/`) provides the
broader Tier 2 output. See `../AI_GUIDE-analyze_gene_sizes.md` and
`../../AI_GUIDE-gene_sizes.md` for the full dual-tier architecture.

---

## Quick Start

### 1. Prepare Input

Place per-species 15-column gene-coordinate TSVs in `INPUT_user/`:

```
INPUT_user/
├── gigantic_species_list.txt                                      # GIGANTIC species list (from genomesDB STEP_4)
├── Homo_sapiens-gene_coordinates_all_inclusive.tsv                # Tier 1 input for human
├── Mus_musculus-gene_coordinates_all_inclusive.tsv                # Tier 1 input for mouse
├── Drosophila_melanogaster-gene_coordinates_all_inclusive.tsv     # Tier 1 input for fly
└── ...                                                            # Only species qualifying for Tier 1
```

Each TSV file has the **15-column Tier 1 layout** produced by the upstream
`gene_coordinates` extractor:

```
Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  Gene_Size  Exon_Intervals  Transcript_Size  CDS_Intervals  CDS_Size  Protein_Size  UTR_5prime_Intervals  UTR_5prime_Size  UTR_3prime_Intervals  UTR_3prime_Size
```

Reference extractors live OUTSIDE GIGANTIC at
`research_notebook/research_user/<speciesN>/gene_coordinates/`.

### 2. Configure
Edit `START_HERE-user_config.yaml` to verify input paths (and optionally set
`proteome_dir` for GIGANTIC ID linkage and `project_name` for run-log labelling).

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
ls -L ../../output_to_input/BLOCK_analyze_gene_sizes/all_inclusive/
```

---

## Pipeline

```
Script 001 (validate) → Script 002 (extract metrics, parallel per species) → Script 003 (rank, parallel per species) → Script 004 (cross-species summary) → Script 005 (run log)
```

---

## Output

| Directory | Contents |
|-----------|----------|
| `OUTPUT_pipeline/1-output/` | Species processing status (PROCESSED / SKIPPED_NO_DATA / SKIPPED_INCOMPLETE) |
| `OUTPUT_pipeline/2-output/` | Per-species 15-col gene metrics (one TSV per species) |
| `OUTPUT_pipeline/3-output/` | Ranked metrics (6 ranks) + 7-metric genome summaries |
| `OUTPUT_pipeline/4-output/` | Cross-species 7-metric summary + downstream directories |
| `ai/logs/` | Timestamped run-success log |
| `../../output_to_input/BLOCK_analyze_gene_sizes/all_inclusive/` | Symlinks for downstream subprojects |

---

## Dependencies

- Conda environment: `ai_gigantic_gene_sizes`
- Upstream: genomesDB STEP_4 (species list); `gene_coordinates` extractors (15-col TSVs)
- User: 15-col Tier 1 TSVs in `INPUT_user/` (typically symlinked from upstream extractor)
