# workflow-COPYME-diamond_ncbi_nr

**AI**: Claude Code | Opus 4.6 | 2026 March 01
**Human**: Eric Edsinger

---

## Purpose

Run DIAMOND blastp searches of species proteomes against the NCBI nr database. Identifies top hits, distinguishes self-hits from non-self-hits, and compiles per-species statistics.

---

## Quick Start

### 1. Edit Configuration

Edit `diamond_ncbi_nr_config.yaml`:

```yaml
project:
  name: "my_project"

diamond:
  database: "/path/to/nr.dmnd"   # <-- REQUIRED: Path to DIAMOND nr database
```

### 2. Prepare Input Manifest

Create `INPUT_user/proteome_manifest.tsv` (see `proteome_manifest_example.tsv` for format).

Or, if `INPUT_gigantic/proteome_manifest.tsv` exists at the project root, it will be automatically copied at runtime.

### 3. Run

```bash
# Local machine:
bash RUN-workflow.sh

# SLURM cluster (edit account/qos in RUN-workflow.sbatch first):
sbatch RUN-workflow.sbatch
```

---

## Pipeline Scripts

| # | Script | Purpose | Output |
|---|--------|---------|--------|
| 001 | `001_ai-python-validate_proteomes.py` | Validate proteome files and manifest | `OUTPUT_pipeline/1-output/` |
| 002 | `002_ai-python-split_proteomes_for_diamond.py` | Split proteomes into N parts | `OUTPUT_pipeline/2-output/` |
| 003 | `003_ai-bash-run_diamond_search.sh` | DIAMOND blastp per split file | `OUTPUT_pipeline/3-output/` |
| 004 | `004_ai-python-combine_diamond_results.py` | Combine splits per species | `OUTPUT_pipeline/4-output/` |
| 005 | `005_ai-python-identify_top_hits.py` | Top self/non-self hit analysis | `OUTPUT_pipeline/5-output/` |
| 006 | `006_ai-python-compile_statistics.py` | Master statistics summary | `OUTPUT_pipeline/6-output/` |

---

## Configuration

Edit `diamond_ncbi_nr_config.yaml`:

| Setting | Default | Description |
|---------|---------|-------------|
| `project.name` | `"my_project"` | Your project name |
| `diamond.database` | *(none)* | Path to DIAMOND nr database (REQUIRED) |
| `diamond.evalue` | `"1e-5"` | E-value threshold |
| `diamond.max_target_sequences` | `10` | Max hits per query |
| `diamond.num_parts` | `40` | Splits per species proteome |
| `diamond.threads_per_job` | `1` | CPUs per DIAMOND job |

---

## SLURM Settings

Edit `RUN-workflow.sbatch` SBATCH directives:
- `--account=YOUR_ACCOUNT` - Your cluster account
- `--qos=YOUR_QOS` - Your quality of service

**Note**: The head job uses minimal resources. DIAMOND search jobs are submitted by NextFlow as separate SLURM jobs with their own resource allocation.

---

## Output

Results are in `OUTPUT_pipeline/` with numbered subdirectories matching each script.

Final summary: `OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv`

---

## For AI Assistants

See `ai/AI_GUIDE-diamond_ncbi_nr_workflow.md` for detailed execution guidance.
