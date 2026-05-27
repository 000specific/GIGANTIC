# AI Guide: identify_hotspots Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK_identify_hotspots concepts + method
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — hotspots overview
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from:
  - `../../../output_to_input/BLOCK_self_blast/self_blast_reports/`
  - `../../../../../research_notebook/research_user/subproject-hotspots/gene_coordinates/` (per §1/§17 deviation noted in BLOCK guide)
  - `../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../../output_to_input/BLOCK_identify_hotspots/`
- 5 scripts; final = `write_run_log` per §45
- Conda env: `aiG-hotspots`

---

## Pipeline (5 NextFlow processes)

| # | Script | Process | Function |
|---|--------|---------|----------|
| 001 | `validate_inputs.py` | `validate_inputs` | Pair every species with its 3 inputs (self-BLAST report, gene_coordinates TSV, proteome); fail-fast on missing |
| 002 | `filter_blast_by_evalue.py` | `filter_blast_by_evalue` | Per-species: keep hits ≤ evalue_threshold, drop self-hits |
| 003 | `identify_hotspots.py` | `identify_per_species` | Per-species: window scan + union-find merge; emits hotspot table |
| 004 | `summarize_hotspots.py` | `summarize_hotspots` | Cross-species aggregate (hotspot counts, size distribution by clade) |
| 005 | `write_run_log.py` | `write_run_log` | Timestamped run log per §45 |

## NextFlow Strict-DSL Posture

`main.nf` is written for strict NextFlow 26 DSL: no top-level `def`,
`import`, or `workflow.onComplete`. All dynamic settings come from
`-params-file` or environment variables exported by `RUN-workflow.sh`
from the user's YAML.

## Parameter Tuning

| Param | Default | Tune when |
|-------|---------|-----------|
| `evalue_threshold` | 1e-60 | Relax for species with deeper paralog divergence |
| `window_size_genes` | 20 (i.e. ±10 around query) | Tighten for assemblies with very dense gene clusters |
| `gene_coordinates_dir` | `../../../../research_notebook/research_user/subproject-hotspots/gene_coordinates` | If user wants to point at a different sandbox source |

## Common Failure Modes

| Error | Cause | Solution |
|-------|-------|----------|
| validate_inputs: "missing self_blast report for species X" | BLOCK_self_blast didn't finish for X | Check `../../../output_to_input/BLOCK_self_blast/self_blast_reports/X*` |
| validate_inputs: "missing gene_coordinates for species X" | User hasn't produced the TSV | Add `Genus_species-gene_coordinates.tsv` to the sandbox `gene_coordinates/` dir |
| Zero hotspots for species X | Evalue too stringent for X's divergence, or coordinate mapping failed | Try relaxing evalue; verify Source_Gene_IDs match between TSV and proteome's `g_` field |
| Source_Gene_ID mismatch | TSV uses different ID format than proteome `g_` | The id-mapping uses proteome FASTA headers; ensure proteomes_dir matches |

## Diagnostic Commands

```bash
# How many hotspots per species?
wc -l OUTPUT_pipeline/3-output/3_ai-hotspots-*.tsv

# Cross-species summary
cat OUTPUT_pipeline/4-output/4_ai-hotspots_summary.tsv

# Spot-check largest hotspots
sort -k4 -nr OUTPUT_pipeline/3-output/3_ai-hotspots-Homo_sapiens.tsv | head -10
```

## See Also

- [`../README.md`](../README.md) — workflow usage
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK concepts + §1/§17 deviation note
- [`../../../README.md`](../../../README.md) — subproject method + Edsinger 2024 reference
