# The GIGANTIC Genome and Proteome Database (genomesDB)

The genomesDB subproject constructs the standardized database that every other GIGANTIC analysis depends on. Starting from user-provided source files, it produces phyloname-standardized proteomes, quality evaluation reports, per-species BLAST databases, and a curated final species set.

genomesDB depends on the [phylonames subproject](gigantic_subproject-phylonames.md), which must run first.

---

## Four-Step Architecture

genomesDB is organized as four independent steps, each a complete Nextflow workflow:

```
STEP_1: Ingest source data (genomes, proteomes, gene annotations)
    |
STEP_2: Standardize naming + evaluate quality (gfastats, BUSCO)
    |
STEP_3: Build per-species BLAST databases
    |
STEP_4: Curate final species set with self-documenting output directories
```

Each step produces outputs consumed by the next step through `output_to_input/` directories. Steps can be re-run independently.

---

## STEP_1: Source Data Ingestion

### What It Does

Validates and hard-copies user-provided source files into the GIGANTIC directory structure, creating an archived snapshot of all input data.

### Source Data Requirements

Three data types are supported. **Proteomes are mandatory**; genomes and gene annotations are optional:

| Data Type | Required? | Extension | Used By |
|-----------|-----------|-----------|---------|
| Proteome | Yes | `.aa` | All downstream analyses |
| Genome assembly | No | `.fasta` | Assembly statistics (STEP_2) |
| Gene annotation | No | `.gff3` or `.gtf` | Gene sizes subproject |

### Source File Naming Convention

All source files follow a standardized naming convention encoding species, data type, source, and provenance:

```
genus_species-genome-source_genome_project_identifier-download_date.extension
```

**Examples:**
```
Homo_sapiens-genome-GCF_000001405.40-20240115.fasta    (genome)
Homo_sapiens-genome-GCF_000001405.40-20240115.gtf      (annotation)
Homo_sapiens-genome-GCF_000001405.40-20240115.aa       (proteome)
```

### Source FASTA Header Convention

Proteome FASTA headers encode the full provenance chain:

```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

**Example:**
```
>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
```

### Input Manifest

The user provides `INPUT_user/source_manifest.tsv` (4-column tab-delimited):

```
genus_species	genome_path	proteome_path	gff_path
Homo_sapiens	/path/to/genome.fasta	/path/to/proteome.aa	/path/to/annotation.gtf
Mnemiopsis_leidyi	NA	/path/to/proteome.aa	/path/to/annotation.gff3
```

Missing data types are marked as `NA`.

### Pipeline Processes

| Process | Script | Description |
|---------|--------|-------------|
| 1 | `001_ai-python-validate_source_manifest.py` | Validates all listed files exist and are readable |
| 2 | `002_ai-python-ingest_source_data.py` | Hard-copies files into `T1_proteomes/`, `genomes/`, `gene_annotations/` |

**Post-pipeline**: `RUN-workflow.sh` creates relative symlinks in the subproject-root `output_to_input/STEP_1-sources/` making ingested files accessible to STEP_2. Files are hard-copied (not symlinked) to ensure the archive persists even if source locations change.

### Running

```bash
cd subprojects/genomesDB/STEP_1-sources/workflow-COPYME-ingest_source_data/
nano INPUT_user/source_manifest.tsv    # Edit manifest
bash RUN-workflow.sh                    # Local
sbatch RUN-workflow.sbatch              # SLURM
```

---

## STEP_2: Standardization and Quality Evaluation

### What It Does

Transforms source data into GIGANTIC's standardized format: applies phylonames to all file names and sequence headers, cleans invalid amino acid residues, evaluates quality through genome assembly statistics and BUSCO assessments, and produces a species selection manifest for user review.

### The Standardization Pipeline (6 Processes)

#### Process 1: Proteome Phyloname Standardization

**Script**: `001_ai-python-standardize_proteome_phylonames.py`

**File renaming:**
```
Source:  Homo_sapiens-genome-GCF_000001405.40-20240115.aa
Output:  Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens-T1-proteome.aa
```

The `T1` designation indicates Transcript 1 (primary transcript) proteomes.

**Header transformation:**
```
Source:  >Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
Output:  >g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
```

The prefixed fields (`g_` gene, `t_` transcript, `p_` protein, `n_` phyloname) preserve complete source provenance while embedding the full phyloname in every sequence. This enables species identification and source lookup directly from any individual sequence header.

**Matching strategy**: Two-tier lookup - exact `genus_species` match first, then prefix match for strain/isolate suffixes (e.g., `Hoilungia_hongkongensis_H13` → `Hoilungia_hongkongensis`).

**Identifier sanitization**: Forward slashes in gene/transcript/protein IDs (e.g., `C/EBP` gene names from NCBI) are replaced with underscores for BUSCO and file system compatibility.

#### Process 2: Invalid Residue Cleaning

**Script**: `002_ai-python-clean_proteome_invalid_residues.py`

| Valid Characters | Description |
|-----------------|-------------|
| `ACDEFGHIKLMNPQRSTUVWXY*` | 20 standard amino acids + U (selenocysteine) + O (pyrrolysine) + X (unknown) + * (stop) |

Characters outside this set (commonly `.` from some databases) are replaced with `X`. A detailed correction map records every replacement: proteome name, sequence header, position (1-indexed), original character, and replacement character.

#### Process 3: Genome and Annotation Standardization

**Script**: `003_ai-python-standardize_genome_and_annotation_phylonames.py`

Creates symlinks (not copies) for genome and annotation files with phyloname-based names:

```
phyloname-genome.fasta
phyloname-genome.gff3   (or .gtf)
```

Unlike proteomes, genome and annotation file content is not modified - only the names change. Both data types are optional; the process handles whatever files are available.

#### Process 4: Genome Assembly Statistics

**Script**: `004_ai-python-calculate_genome_assembly_statistics.py`

Computes assembly metrics using gfastats for each available genome:

| Metric | Level | Description |
|--------|-------|-------------|
| Scaffold count | Scaffold | Total number of scaffolds |
| Contig count | Contig | Total number of contigs |
| Total assembly size | Both | Total base pairs |
| Largest scaffold | Scaffold | Size of largest scaffold |
| N50 | Both | Length at which 50% of assembly in pieces this size or larger |
| N90 | Both | Length at which 90% of assembly in pieces this size or larger |
| GC content | Assembly | Percentage (excluding N bases, matching NCBI convention) |
| Gap count | Assembly | Number of gaps |
| Total gap length | Assembly | Total gap base pairs |

Statistics are computed in parallel across species using multithreaded execution.

#### Process 5: BUSCO Proteome Completeness

**Script**: `005_ai-python-run_busco_proteome_evaluation.py`

Runs BUSCO in protein mode on the **cleaned** proteomes (post-Process 2). The user configures which BUSCO lineage datasets to use via `INPUT_user/busco_lineages.txt`:

```
metazoa_odb10
eukaryota_odb10
```

BUSCO jobs are parallelized (default: 4 concurrent, 4 CPUs each). Results per species:

| Metric | Description |
|--------|-------------|
| Complete single-copy | Conserved genes found as single-copy |
| Duplicated | Conserved genes found as duplicates |
| Fragmented | Partially matching conserved genes |
| Missing | Expected conserved genes not found |

#### Process 6: Quality Summary and Species Selection

**Script**: `006_ai-python-summarize_quality_and_generate_species_manifest.py`

Aggregates all quality metrics into a comprehensive summary table and generates a **species selection manifest** with an `Include` column (default: `YES` for all species).

**User decision point**: The researcher reviews quality metrics and may set individual species to `Include=NO`. Species without genomes show `NA` for assembly columns with a `Has_Genome=NO` flag.

The species selection manifest is written as a **real file** (not symlink) to `output_to_input/` so the user can edit it without affecting the archived pipeline output.

### Running

```bash
cd subprojects/genomesDB/STEP_2-standardize_and_evaluate/workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
nano ingest_standardize_evaluate_config.yaml    # Edit config
bash RUN-workflow.sh                             # Local
sbatch RUN-workflow.sbatch                       # SLURM
```

### Output Files

| Directory | Key Files | Description |
|-----------|-----------|-------------|
| `1-output/` | Standardized proteomes | Phyloname-renamed with transformed headers |
| `1-output/` | Transformation manifest | Documents every header transformation |
| `2-output/` | Cleaned proteomes | Invalid residues replaced with X |
| `2-output/` | Correction map | Every character replacement documented |
| `3-output/` | Genome/annotation symlinks | Phyloname-named references |
| `4-output/` | Assembly statistics TSV | All metrics for all genomes |
| `5-output/` | BUSCO results | Per-species summaries and full reports |
| `6-output/` | Species selection manifest | Quality summary + Include column |

---

## STEP_3: BLAST Database Construction

### What It Does

Builds per-species BLAST protein databases from standardized proteomes for species marked `Include=YES` in the species selection manifest.

### Per-Species Database Architecture

Each species gets its own BLAST database rather than a single concatenated database. This enables:
- Independent species-specific homology searches
- Flexible species set composition for different analyses
- Parallel database construction

### The makeblastdb Command

```bash
makeblastdb -in phyloname-T1-proteome.aa -dbtype prot -out phyloname-T1-proteome.aa
```

**Why no `-parse_seqids`**: GIGANTIC's standardized sequence identifiers exceed BLAST's 50-character limit for parsed sequence IDs. BLAST searches function correctly without this flag.

**Suppressed stderr**: `makeblastdb` emits thousands of harmless warnings about selenocysteine (U) and pyrrolysine (O) residues. These are suppressed to keep logs clean.

**Reproducibility**: A `makeblastdb_commands.sh` log documents every exact command used.

Database construction is parallelized (default: 4 concurrent jobs).

### Pipeline Processes

| Process | Script | Description |
|---------|--------|-------------|
| 1 | `001_ai-python-filter_species_manifest.py` | Filters to Include=YES species only |
| 2 | `002_ai-python-build_per_genome_blastdbs.py` | Builds individual BLAST databases |

### Running

```bash
cd subprojects/genomesDB/STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/
nano databases_config.yaml    # Edit paths to STEP_2 outputs
bash RUN-workflow.sh           # Local
sbatch RUN-workflow.sbatch     # SLURM
```

---

## STEP_4: Final Species Set Curation

### What It Does

Validates the final species selection and assembles curated output directories with self-documenting names that encode the species count.

### Self-Documenting Output Directories

```
species67_gigantic_T1_proteomes/        (67 standardized proteome files)
species67_gigantic_T1_blastp/           (67 per-species BLAST databases)
species67_gigantic_gene_annotations/    (subset of species with GFF/GTF)
```

The species count in the directory name makes the database immediately self-documenting. Gene annotations are included for the subset of species that have gene structure data available.

### Optional Species Selection

By default, STEP_4 includes all species from STEP_2. Optionally, the user can provide `INPUT_user/selected_species.txt` (one `genus_species` per line) to select a specific subset.

### Pipeline Processes

| Process | Script | Description |
|---------|--------|-------------|
| 1 | `001_ai-python-validate_species_selection.py` | Validates proteome + BLAST database exist for each species; identifies species with gene annotations |
| 2 | `002_ai-python-copy_selected_files.py` | Copies validated files into speciesN output directories |

### Running

```bash
cd subprojects/genomesDB/STEP_4-create_final_species_set/workflow-COPYME-create_final_species_set/
nano final_species_set_config.yaml    # Edit paths to STEP_2 and STEP_3 outputs
bash RUN-workflow.sh                   # Local
sbatch RUN-workflow.sbatch             # SLURM
```

### Verification

```bash
# Check species counts match expectations
ls OUTPUT_pipeline/2-output/species*_gigantic_T1_proteomes/ | wc -l
ls OUTPUT_pipeline/2-output/species*_gigantic_T1_blastp/*.pdb | wc -l
ls OUTPUT_pipeline/2-output/species*_gigantic_gene_annotations/ | wc -l

# Verify a specific species is included
find OUTPUT_pipeline/2-output/ -name "*Homo_sapiens*"

# Check the copy manifest for complete record
cat OUTPUT_pipeline/2-output/2_ai-copy_manifest.tsv
```

---

## Data Flow Between Steps

### The output_to_input System

Each step shares outputs via symlinks in `output_to_input/` directories. Files always live as real copies in `OUTPUT_pipeline/`; the `output_to_input/` directories contain only symlinks.

```
output_to_input/
├── STEP_1-sources/
│   ├── T1_proteomes/           → Hard-copied source proteomes
│   ├── genomes/                → Hard-copied source genomes
│   └── gene_annotations/       → Hard-copied source annotations
│
├── STEP_2-standardize_and_evaluate/
│   └── species_selection_manifest.tsv    → Real file (editable by user)
│
├── STEP_3-databases/
│   └── gigantic-T1-blastp/     → Per-species BLAST databases
│
└── STEP_4-create_final_species_set/
    ├── speciesN_gigantic_T1_proteomes/        → Final curated proteomes
    ├── speciesN_gigantic_T1_blastp/           → Final BLAST databases
    └── speciesN_gigantic_gene_annotations/    → Final gene annotations
```

### output_to_input Location

Every workflow creates symlinks in the single subproject-root `output_to_input/` directory, organized by STEP subdirectories (e.g., `output_to_input/STEP_2-standardize_and_evaluate/`). Downstream steps and other subprojects read from this canonical location.

### Configuration Between Steps

STEP_3 and STEP_4 config files must point to the correct STEP_2/STEP_3 output paths. When you name your workflow runs (e.g., `workflow-RUN_01-my_species_set`), update these paths accordingly:

```yaml
# In STEP_3 databases_config.yaml
step_2_proteomes: "../../STEP_2-standardize_and_evaluate/workflow-RUN_01-my_set/OUTPUT_pipeline/2-output/cleaned_proteomes"

# In STEP_4 final_species_set_config.yaml
step_2_workflow: "../../STEP_2-standardize_and_evaluate/workflow-RUN_01-my_set"
step_3_workflow: "../../STEP_3-databases/workflow-RUN_01-my_set"
```

---

## FASTA Header Format Reference

### Source Format
```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
```

### Standardized GIGANTIC Format
```
>g_source_gene_id-t_source_transcript_id-p_source_protein_id-n_phyloname
>g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
```

### Extracting Fields from a GIGANTIC Header

```python
header = 'g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens'
parts = header.split( '-' )

gene_id = parts[ 0 ][ 2: ]         # ENSG00000139618 (strip g_ prefix)
transcript_id = parts[ 1 ][ 2: ]   # ENST00000380152 (strip t_ prefix)
protein_id = parts[ 2 ][ 2: ]      # ENSP00000369497 (strip p_ prefix)
phyloname = parts[ 3 ][ 2: ]       # Metazoa_Chordata_..._Homo_sapiens (strip n_ prefix)

# Extract genus_species from phyloname
phyloname_parts = phyloname.split( '_' )
genus_species = phyloname_parts[ 5 ] + '_' + '_'.join( phyloname_parts[ 6: ] )
```

In Bash:
```bash
# Extract phyloname from a FASTA header
echo "$header" | grep -oP '(?<=n_).*'

# Extract genus_species from a phyloname
echo "$phyloname" | awk -F'_' '{for(i=6;i<=NF;i++) printf "%s%s", $i, (i<NF?"_":"")}'
```

---

## Downstream Integration

genomesDB outputs are consumed by every downstream GIGANTIC subproject:

| Subproject | Uses | From |
|------------|------|------|
| **one_direction_homologs** | Standardized proteomes | STEP_4 proteomes |
| **orthogroups** | Standardized proteome set | STEP_4 proteomes |
| **trees_gene_families** | Per-species BLAST databases | STEP_4 blastp |
| **trees_gene_groups** | BLAST databases + proteomes | STEP_4 blastp + proteomes |
| **gene_sizes** | Gene annotation files (GFF/GTF) | STEP_4 gene_annotations |
| **annotations_hmms** | Standardized proteomes | STEP_4 proteomes |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Species not found in phylonames mapping` | Species name mismatch between source manifest and phylonames | Check spelling, verify genus_species matches phylonames mapping file |
| `Source file not found` | Path in source manifest doesn't exist | Verify file paths in `source_manifest.tsv` |
| `makeblastdb: command not found` | BLAST+ not in conda environment | Activate `ai_gigantic_genomesdb` environment |
| `gfastats: command not found` | gfastats not installed | Activate `ai_gigantic_genomesdb` environment |
| Species shows `NA` for assembly metrics | No genome file provided for this species | Expected for proteome-only species |
| BUSCO missing percentage is high | Poor proteome quality or wrong lineage | Try a broader lineage (e.g., `eukaryota_odb10`) or check source data |
| `BLAST database construction failed` | Corrupted or empty proteome | Check STEP_2 cleaning log for that species |
| STEP_3/4 config path errors | Workflow run names don't match config | Update config YAML to point to your actual workflow-RUN directories |

---

## Quick Reference

| Question | Answer |
|----------|--------|
| Where do I list my source files? | `STEP_1/workflow-COPYME-*/INPUT_user/source_manifest.tsv` |
| Where do I set BUSCO lineages? | `STEP_2/workflow-COPYME-*/INPUT_user/busco_lineages.txt` |
| Where do I edit species inclusion? | `output_to_input/STEP_2-standardize_and_evaluate/species_selection_manifest.tsv` |
| Where are the final proteomes? | `output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` |
| Where are the BLAST databases? | `output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/` |
| Where are gene annotations? | `output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_gene_annotations/` |
| What conda environment? | `ai_gigantic_genomesdb` |
| What runs first? | `phylonames` subproject must complete before genomesDB |

---

## External Tools and References

| Tool | Version | Purpose in genomesDB | Citation | Repository |
|------|---------|---------------------|----------|------------|
| **Nextflow** | >=23.0 | Workflow orchestration for all four STEPs | Di Tommaso et al. (2017) *Nature Biotechnology* 35:316-319. [DOI](https://doi.org/10.1038/nbt.3820) | [github.com/nextflow-io/nextflow](https://github.com/nextflow-io/nextflow) |
| **gfastats** | - | Genome assembly statistics (STEP_2 Process 4) | Formenti et al. (2022) *Bioinformatics* 38(17):4214-4216. [DOI](https://doi.org/10.1093/bioinformatics/btac460) | [github.com/vgl-hub/gfastats](https://github.com/vgl-hub/gfastats) |
| **BUSCO** | v5+ | Proteome completeness assessment (STEP_2 Process 5) | Manni et al. (2021) *Mol Biol Evol* 38(10):4647-4654. [DOI](https://doi.org/10.1093/molbev/msab199); Simão et al. (2015) *Bioinformatics* 31(19):3210-3212. [DOI](https://doi.org/10.1093/bioinformatics/btv351) | [gitlab.com/ezlab/busco](https://gitlab.com/ezlab/busco) |
| **BLAST+** | - | Per-species protein database construction (STEP_3) | Camacho et al. (2009) *BMC Bioinformatics* 10:421. [DOI](https://doi.org/10.1186/1471-2105-10-421) | [github.com/ncbi/ncbi-cxx-toolkit-public](https://github.com/ncbi/ncbi-cxx-toolkit-public) |

All tools are installed via the `ai_gigantic_genomesdb` conda environment.

---

*For AI assistant guidance, see `AI_GUIDE-genomesDB.md` and per-step workflow `AI_GUIDE-*_workflow.md` files.*
