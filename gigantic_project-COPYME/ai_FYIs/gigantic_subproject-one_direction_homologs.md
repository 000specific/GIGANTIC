# The GIGANTIC One-Direction Homolog System (one_direction_homologs)

The one_direction_homologs subproject searches each species proteome against the NCBI non-redundant (nr) protein database using DIAMOND to identify one-directional (non-reciprocal) homologs for every protein. It distinguishes "self-hits" (identical sequences in NCBI nr) from "non-self-hits" (true homologs), providing a standardized assessment of each species' representation in public databases.

one_direction_homologs depends on the [genomesDB subproject](gigantic_subproject-genomesDB.md) for standardized proteomes and the [phylonames subproject](gigantic_subproject-phylonames.md) for species naming.

---

## Single-Block Architecture

```
BLOCK_diamond_ncbi_nr/     Validate → Split → DIAMOND search → Combine → Classify → Compile
```

The pipeline follows a six-process structure with massive parallelization of the compute-intensive DIAMOND search step:

```
Process 1: Validate proteomes from input manifest
    |
Process 2: Split each proteome into N parts (default: 40)
    |
Process 3: DIAMOND blastp search (2,680 parallel jobs for 67 species)
    |
Process 4: Combine split results back into one file per species
    |
Process 5: Identify top self-hits and non-self-hits per protein
    |
Process 6: Compile master statistics table across all species
```

---

## The Split-Search-Combine Pattern

The pipeline splits each species proteome into N independent FASTA files (default: 40 parts) to enable massive parallelization on SLURM clusters. With 67 species and 40 parts each, this creates **2,680 concurrent DIAMOND jobs**, each using 1 CPU thread.

```
67 species × 40 parts = 2,680 independent DIAMOND jobs
Each job: 1 CPU thread, 21 GB memory, up to 4 days wall time
SLURM queue limit: 3,000 jobs (with rate-limited submission at 10-second intervals)
```

After all searches complete, results are concatenated back into one file per species for downstream analysis.

---

## Self-Hit vs. Non-Self-Hit Classification

For each query protein, the pipeline examines up to 10 DIAMOND hits and identifies:

| Type | Condition | Meaning |
|------|-----------|---------|
| **Self-hit** | Full query sequence == full subject sequence (exact string match) | Protein already exists in NCBI nr |
| **Non-self-hit** | Full query sequence != full subject sequence | Closest homolog that is a distinct protein |

**Why full-sequence comparison?** The same protein may appear in NCBI nr under different accession numbers, and GIGANTIC's phyloname-based identifiers differ from NCBI accession numbers. Comparing full amino acid sequences is the only reliable way to determine identity.

The DIAMOND output includes `full_qseq` and `full_sseq` columns specifically for this comparison.

---

## Process 1: Proteome Validation

**Script**: `001_ai-python-validate_proteomes.py`

### Input Manifest Format

`INPUT_user/proteome_manifest.tsv` (tab-separated, 3 columns):

```
species_name	proteome_path	phyloname
Homo_sapiens	/path/to/Homo_sapiens.aa	Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
```

### Validation Checks

- Proteome file exists and is non-empty
- Contains valid FASTA-formatted sequences
- Sequence counts recorded per species
- Relative paths resolved to absolute paths
- Pipeline exits if zero valid proteomes found

---

## Process 2: Proteome Splitting

**Script**: `002_ai-python-split_proteomes_for_diamond.py`

### Splitting Algorithm

Sequences are distributed evenly using integer division with remainder handling:

- `sequences_per_part = total // num_parts`
- First R parts (R = remainder) each get one extra sequence
- Creates up to N independent FASTA files per species

### Output

- `splits/{Species}_part_NNN.fasta` (one file per split)
- `2_ai-diamond_job_manifest.tsv` (documents every split with species, part number, path, sequence count)

---

## Process 3: DIAMOND Search Against NCBI nr

**Script**: `003_ai-bash-run_diamond_search.sh`

### Command

```bash
diamond blastp \
    --query INPUT.fasta \
    --db NCBI_NR.dmnd \
    --out OUTPUT.tsv \
    --evalue 1e-5 \
    --max-target-seqs 10 \
    --threads 1 \
    --sensitive \
    --outfmt 6 qseqid sseqid pident length mismatch gapopen \
                qstart qend sstart send evalue bitscore \
                stitle full_qseq full_sseq
```

### Parameters

| Parameter | Value | Configurable | Purpose |
|-----------|-------|-------------|---------|
| `--sensitive` | enabled | No | Increased sensitivity for remote homologs |
| `--evalue` | 1e-5 | Yes | E-value threshold |
| `--max-target-seqs` | 10 | Yes | Top N hits per query |
| `--threads` | 1 | Yes | CPU threads per job (1 maximizes parallelization) |

### Output Format

15-column tabular output:

| # | Column | Description |
|---|--------|-------------|
| 1 | qseqid | Query sequence ID (GIGANTIC identifier) |
| 2 | sseqid | Subject sequence ID (NCBI accession) |
| 3 | pident | Percent identity |
| 4 | length | Alignment length |
| 5 | mismatch | Mismatches |
| 6 | gapopen | Gap openings |
| 7 | qstart | Query start |
| 8 | qend | Query end |
| 9 | sstart | Subject start |
| 10 | send | Subject end |
| 11 | evalue | E-value |
| 12 | bitscore | Bit score |
| 13 | stitle | Full NCBI description/header |
| 14 | full_qseq | Complete query protein sequence |
| 15 | full_sseq | Complete subject protein sequence |

### Resource Requirements

| Resource | Per Job | Total (67 species, 40 parts) |
|----------|---------|------------------------------|
| Memory | 21 GB | ~56 TB aggregate |
| Time | up to 4 days | Variable |
| CPUs | 1 | 2,680 concurrent |

---

## Process 4: Result Combination

**Script**: `004_ai-python-combine_diamond_results.py`

Concatenates all split results for each species into a single file. Files processed in sorted order for reproducibility. Empty result files (from splits with no hits) are skipped. Pipeline exits with error if all splits for a species are empty.

---

## Process 5: Top Hit Identification

**Script**: `005_ai-python-identify_top_hits.py`

### Per-Protein Analysis

For each query protein, examines up to 10 DIAMOND hits (sorted by bitscore):

1. Captures the **first self-hit** (query sequence == subject sequence)
2. Captures the **first non-self-hit** (query sequence != subject sequence)
3. Stops early once both types are found

### Output Files Per Species

**Top hits file** (`{Species}_top_hits.tsv`):
- One row per query protein
- Top 10 hit IDs and NCBI descriptions
- Top non-self-hit details (ID, header, full FASTA entry)
- Top self-hit details (ID, header, full FASTA entry)

**Statistics file** (`{Species}_statistics.tsv`):
- Total queries processed
- Self-hits found count
- Non-self-hits found count
- Queries with no non-self-hits count
- Queries with no self-hits count

---

## Process 6: Master Statistics Compilation

**Script**: `006_ai-python-compile_statistics.py`

### Output

`6_ai-all_species_statistics.tsv` with one row per species:

| Column | Description |
|--------|-------------|
| Species_Name | Genus_species identifier |
| Total_Queries_Processed | Total proteins analyzed |
| Self_Hits_Found | Proteins with identical sequences in NCBI nr |
| Non_Self_Hits_Found | Proteins with homologs (different sequences) in NCBI nr |
| Queries_With_No_Non_Self_Hits | Proteins where all top 10 hits were self-hits |
| Queries_With_No_Self_Hits | Proteins with no identical match in NCBI nr |

### Interpreting Results

- **High self-hit rate**: Species is well-represented in NCBI nr (e.g., model organisms)
- **Low self-hit rate**: Species is poorly represented or novel to NCBI nr
- **High non-self-hit rate**: Most proteins have identifiable evolutionary relatives
- **Queries with no non-self-hits**: Proteins exist in NCBI but lack close homologs (potentially lineage-specific)

---

## Output Structure

```
one_direction_homologs/output_to_input/
└── ncbi_nr_top_hits/
    ├── {Species}_top_hits.tsv         (per-protein top hit details)
    ├── {Species}_statistics.tsv       (per-species hit statistics)
    └── 6_ai-all_species_statistics.tsv (cross-species master summary)
```

---

## Configuration

Edit `diamond_ncbi_nr_config.yaml`:

```yaml
diamond:
  database: "/path/to/ncbi_nr.dmnd"     # DIAMOND-formatted NCBI nr database
  evalue: "1e-5"                         # E-value threshold
  max_target_sequences: 10               # Top N hits per query
  num_parts: 40                          # Splits per species
  threads_per_job: 1                     # CPU threads per DIAMOND job
```

---

## Running

```bash
cd subprojects/one_direction_homologs/BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr/
# Prepare inputs
nano INPUT_user/proteome_manifest.tsv    # species_name, proteome_path, phyloname
nano diamond_ncbi_nr_config.yaml         # Set database path
# Execute
bash RUN-workflow.sh          # Local
sbatch RUN-workflow.sbatch    # SLURM
```

### SLURM Considerations

The head job (Nextflow orchestrator) requires minimal resources (2 CPUs, 8 GB). The DIAMOND search jobs are submitted as individual SLURM jobs by Nextflow, each requesting 21 GB memory and 1 CPU. With 2,680 jobs and a 3,000-job queue limit, ensure your SLURM account has sufficient allocation.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `No valid proteomes found` | Manifest paths are wrong or files missing | Check proteome_manifest.tsv paths; verify files exist |
| `DIAMOND database not found` | Config path to .dmnd file is wrong | Update `diamond.database` in config YAML |
| DIAMOND jobs fail with OOM | NCBI nr database too large for allocated memory | Increase memory in nextflow.config (currently 21 GB) |
| All splits empty for a species | No NCBI nr hits for entire proteome | Check species proteome quality; try relaxing evalue |
| Very low self-hit rate | Species not well-represented in NCBI nr | Expected for novel/non-model organisms |
| SLURM queue limit exceeded | Too many concurrent jobs | Reduce `num_parts` or lower `queueSize` in nextflow.config |
| Head job times out | DIAMOND jobs taking too long in queue | Increase head job `--time` in RUN-workflow.sbatch |

---

## External Tools and References

| Tool | Purpose | Citation | Repository |
|------|---------|----------|------------|
| **DIAMOND** | Fast protein similarity search against NCBI nr | Buchfink et al. (2015) *Nature Methods* 12(1):59-60. [DOI](https://doi.org/10.1038/nmeth.3176); Buchfink et al. (2021) *Nature Methods* 18(4):366-368. [DOI](https://doi.org/10.1038/s41592-021-01101-x) | [github.com/bbuchfink/diamond](https://github.com/bbuchfink/diamond) |
| **Nextflow** | Workflow orchestration with massive parallelization | Di Tommaso et al. (2017) *Nature Biotechnology* 35:316-319. [DOI](https://doi.org/10.1038/nbt.3820) | [github.com/nextflow-io/nextflow](https://github.com/nextflow-io/nextflow) |

All tools are installed via the `ai_gigantic_one_direction_homologs` conda environment.

---

*For AI assistant guidance, see `AI_GUIDE-one_direction_homologs.md` and workflow-level `ai/AI_GUIDE-one_direction_homologs_workflow.md`.*
