# workflow-COPYME-analyze_gene_sizes — `gene_vs_protein` (Tier 2)

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

---

## Purpose

NextFlow workflow that computes the **broad-coverage (Tier 2)** gene-structure
metrics from user-provided 9-column gene-coordinate TSVs. Produces 4
universally-comparable cross-species metrics — `Gene_Size`, `CDS_Size`,
`Protein_Size`, `CDS_Segment_Count` — plus within-genome percentile ranks
and a cross-species summary.

This is one of two parallel workflow templates in `BLOCK_analyze_gene_sizes/`.
The other (`workflow-COPYME-analyze_gene_sizes-all_inclusive/`) provides the
methodology-strict Tier 1 output. Tier 1 species are also written as Tier 2
(superset overlap), so this tier covers the broadest species set with the
metrics that are universally derivable. See `../AI_GUIDE-analyze_gene_sizes.md`
and `../../AI_GUIDE-gene_sizes.md` for the full dual-tier architecture.

---

## Quick Start

### 1. Prepare Input

Place per-species 9-column gene-coordinate TSVs in `INPUT_user/`:

```
INPUT_user/
├── gigantic_species_list.txt                                       # GIGANTIC species list (from genomesDB STEP_4)
├── Homo_sapiens-gene_coordinates_gene_vs_protein.tsv               # Tier 2 input for human
├── Mus_musculus-gene_coordinates_gene_vs_protein.tsv               # Tier 2 input for mouse
├── Drosophila_melanogaster-gene_coordinates_gene_vs_protein.tsv    # Tier 2 input for fly
└── ...                                                             # Every species with gene + CDS records
```

Each TSV file has the **9-column Tier 2 layout** produced by the upstream
`gene_coordinates` extractor:

```
Source_Gene_ID  Seqid  Gene_Start  Gene_End  Strand  Gene_Size  CDS_Intervals  CDS_Size  Protein_Size
```

No exon, transcript, or UTR fields — Tier 2 deliberately uses only the
universally-supported gene + CDS subset. Reference extractors live OUTSIDE
GIGANTIC at `research_notebook/research_user/<speciesN>/gene_coordinates/`.

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
ls -L ../../output_to_input/BLOCK_analyze_gene_sizes/gene_vs_protein/
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
| `OUTPUT_pipeline/2-output/` | Per-species 11-col gene metrics (one TSV per species) |
| `OUTPUT_pipeline/3-output/` | Ranked metrics (4 ranks) + 4-metric genome summaries |
| `OUTPUT_pipeline/4-output/` | Cross-species 4-metric summary + downstream directories |
| `ai/logs/` | Timestamped run-success log |
| `../../output_to_input/BLOCK_analyze_gene_sizes/gene_vs_protein/` | Symlinks for downstream subprojects |

---

## Dependencies

- Conda environment: `ai_gigantic_gene_sizes`
- Upstream: genomesDB STEP_4 (species list); `gene_coordinates` extractors (9-col TSVs)
- User: 9-col Tier 2 TSVs in `INPUT_user/` (typically symlinked from upstream extractor)
