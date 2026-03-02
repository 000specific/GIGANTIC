# The GIGANTIC Orthogroup Identification System (orthogroups)

The orthogroups subproject identifies orthologous gene groups across all GIGANTIC species using three independent methods, then systematically compares their results. Running multiple methods with different algorithmic approaches provides higher confidence in orthogroup assignments than any single tool alone.

orthogroups depends on the [genomesDB subproject](gigantic_subproject-genomesDB.md) for standardized proteomes.

---

## Four-Project Architecture

```
BLOCK_orthofinder/     OrthoFinder: Diamond all-vs-all + MCL clustering
BLOCK_orthohmm/        OrthoHMM: Profile HMM (HMMER) + MCL clustering
BLOCK_broccoli/        Broccoli: Kmer + Diamond + FastTree + network propagation
BLOCK_comparison/      Cross-method comparison of all three tools' results
```

Each tool project follows an identical six-process pipeline:

```
Process 1: Validate input proteomes
Process 2: Prepare proteomes (copy or convert headers)
Process 3: Run the tool
Process 4: Standardize output (restore GIGANTIC identifiers)
Process 5: Generate summary statistics
Process 6: Per-species quality control
```

This design means adding a new ortholog tool requires only copying an existing project and replacing the tool-specific processes (2-4). The validation, statistics, and QC processes work unchanged on the standardized output format.

---

## Standardized Output Format

All three tools produce identical output files in their `output_to_input/` directories:

| File | Format | Description |
|------|--------|-------------|
| `orthogroups_gigantic_ids.tsv` | `OG_ID<TAB>gene1<TAB>gene2<TAB>...` | One row per orthogroup, full GIGANTIC headers |
| `gene_count_gigantic_ids.tsv` | Matrix: OG_ID vs species | Gene counts per orthogroup per species |
| `summary_statistics.tsv` | Key-value pairs | Total orthogroups, genes assigned, singletons, mean/median/max size, coverage |
| `per_species_summary.tsv` | Per-species rows | Genes assigned, orthogroups joined, unassigned genes, coverage % |

This standardization enables the comparison project and downstream subprojects to consume any tool's output interchangeably.

---

## The Header Conversion Problem

GIGANTIC's phyloname-based sequence headers can exceed 100 characters:

```
>g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
```

**OrthoFinder** supports the `-X` flag to preserve original identifiers, so no conversion is needed.

**OrthoHMM and Broccoli** cannot handle long headers. The pipeline converts to short IDs and restores afterward:

```
GIGANTIC header:  >g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_..._Homo_sapiens
Short ID:         >Homo_sapiens-1
```

A comprehensive mapping file (`header_mapping.tsv`) links every short ID back to its full GIGANTIC header, ensuring lossless round-trip conversion:

```
Short_ID	Original_Header	Genus_Species	Original_Filename
Homo_sapiens-1	g_ENSG00000139618-t_ENST00000380152-p_ENSP00000369497-n_Metazoa_..._Homo_sapiens	Homo_sapiens	Metazoa_..._Homo_sapiens-T1-proteome.aa
```

---

## BLOCK_orthofinder

### Tool Overview

OrthoFinder (Emms & Kelly, 2019) identifies orthogroups through all-versus-all Diamond similarity searches followed by MCL graph-based clustering. It also produces gene trees, a species tree, and hierarchical orthogroups (HOGs).

### Command

```bash
orthofinder -f INPUT_DIR -t CPUS -a CPUS -S diamond -I 1.5 -X -o OUTPUT_DIR
```

| Flag | Purpose | Default |
|------|---------|---------|
| `-f` | Input directory of FASTA files | Required |
| `-t` | Threads for sequence searches | From config |
| `-a` | Threads for analyses | From config |
| `-S diamond` | Use Diamond as search engine | `diamond` |
| `-I` | MCL inflation parameter (clustering granularity) | `1.5` |
| `-X` | Preserve original sequence identifiers | Enabled |
| `-o` | Output directory | Required |

### Configuration

Edit `orthofinder_config.yaml`:

```yaml
orthofinder:
  search_program: "diamond"      # diamond or blast
  mcl_inflation: 1.5             # Higher = more granular clusters
  cpus: 16                       # Threads
```

### Tool-Specific Output

Beyond the four standardized files, OrthoFinder retains:

| Output | Description |
|--------|-------------|
| Species tree | Inferred phylogeny via gene tree reconciliation |
| Gene trees | Per-orthogroup phylogenetic trees |
| HOGs | Hierarchical orthogroups at multiple taxonomic levels |
| Comparative genomics statistics | Native statistics including gene duplication events |

### Running

```bash
cd subprojects/orthogroups/BLOCK_orthofinder/workflow-COPYME-run_orthofinder/
nano orthofinder_config.yaml    # Edit config
bash RUN-workflow.sh             # Local
sbatch RUN-workflow.sbatch       # SLURM (edit account/qos first)
```

**Resource requirements**: ~64 GB RAM, up to 72 hours for large species sets.

---

## BLOCK_orthohmm

### Tool Overview

OrthoHMM (Steenwyk & King, 2024) identifies orthogroups using profile Hidden Markov Model searches (via HMMER), providing improved sensitivity for divergent sequences. It iteratively builds HMM profiles for sequence clusters and searches all sequences against these profiles, followed by MCL clustering.

### Command

```bash
orthohmm INPUT_DIR -o OUTPUT_DIR -c CPUS -e 0.0001 -s 0.5
```

| Flag | Purpose | Default |
|------|---------|---------|
| positional | Input directory of FASTA files | Required |
| `-o` | Output directory | Required |
| `-c` | Thread count | From config |
| `-e` | E-value threshold | `0.0001` |
| `-s` | Single-copy threshold (fraction of species) | `0.5` |

### Tool-Specific Output

| Output | Description |
|--------|-------------|
| `header_mapping.tsv` | Short ID to GIGANTIC ID mapping (provenance) |
| HMM profiles | Per-orthogroup profiles, reusable for classifying new sequences |
| Single-copy orthologs | Genes present in exactly one copy in >= threshold % of species |

### Running

```bash
cd subprojects/orthogroups/BLOCK_orthohmm/workflow-COPYME-run_orthohmm/
nano orthohmm_config.yaml    # Edit config
bash RUN-workflow.sh           # Local
sbatch RUN-workflow.sbatch     # SLURM
```

**Resource requirements**: ~64 GB RAM, up to 48 hours.

---

## BLOCK_broccoli

### Tool Overview

Broccoli (Derelle et al., 2020) combines rapid phylogenetic analysis with network-based label propagation. It uniquely detects chimeric proteins (potential gene fusions).

### Internal Four-Step Pipeline

Broccoli runs four sequential internal steps:

| Step | What It Does |
|------|-------------|
| 1. Kmer clustering | Fast initial grouping by kmer similarity |
| 2. Diamond + FastTree | Per-cluster similarity search + phylogenetic trees |
| 3. Network label propagation | Orthogroup identification + chimeric protein detection |
| 4. Pairwise ortholog extraction | Extract all pairwise ortholog relationships |

### Command

```bash
broccoli -dir INPUT_DIR -threads CPUS -tree_method nj
```

| Flag | Purpose | Default |
|------|---------|---------|
| `-dir` | Input directory of FASTA files | Required |
| `-threads` | Thread count | From config |
| `-tree_method` | Tree method: `nj` (neighbor joining), `me` (minimum evolution), `ml` (maximum likelihood) | `nj` |

### Tool-Specific Output

| Output | Description |
|--------|-------------|
| `header_mapping.tsv` | Short ID to GIGANTIC ID mapping (provenance) |
| `chimeric_proteins.txt` | Proteins spanning multiple orthogroups (unique to Broccoli) |
| `orthologous_pairs.txt` | All pairwise ortholog relationships |

### Running

```bash
cd subprojects/orthogroups/BLOCK_broccoli/workflow-COPYME-run_broccoli/
nano broccoli_config.yaml    # Edit config
bash RUN-workflow.sh           # Local
sbatch RUN-workflow.sbatch     # SLURM
```

**Resource requirements**: ~64 GB RAM, up to 72 hours.

---

## BLOCK_comparison

### Purpose

Systematically compare orthogroup assignments from all completed tools. Requires at least 2 of the 3 tools to have completed their pipelines.

### What It Computes

| Analysis | Output File | Description |
|----------|-------------|-------------|
| Method comparison | `method_comparison_summary.tsv` | Side-by-side statistics: orthogroup count, mean/median/max size, singletons, coverage |
| Gene overlap | `gene_overlap_between_methods.tsv` | Pairwise Jaccard indices + 3-way overlap when all tools available |
| Size distributions | `orthogroup_size_comparison.tsv` | Count of orthogroups at each size per tool |

### Running

```bash
cd subprojects/orthogroups/BLOCK_comparison/workflow-COPYME-compare_methods/
nano comparison_config.yaml    # Edit paths to BLOCK outputs
bash RUN-workflow.sh            # Local
sbatch RUN-workflow.sbatch      # SLURM
```

### Interpreting Results

- **High Jaccard indices** between tools indicate strong agreement in orthogroup assignments
- **Low overlap** may indicate different clustering granularity or genuine algorithmic disagreements
- **Orthogroup size distributions** reveal if one tool produces systematically larger or smaller groups
- Genes assigned by **all three methods** represent the highest-confidence orthogroup assignments

---

## Tool Comparison Summary

| Feature | OrthoFinder | OrthoHMM | Broccoli |
|---------|-------------|----------|----------|
| **Algorithm** | Diamond all-vs-all + MCL | HMMER profile HMM + MCL | Kmer + Diamond + FastTree + network |
| **Header handling** | `-X` flag preserves originals | Needs short ID conversion | Needs short ID conversion |
| **Unique output** | Species tree, HOGs, gene trees | HMM profiles (reusable) | Chimeric protein detection |
| **Best for** | General-purpose, broad coverage | Divergent sequences, deep taxonomic sampling | Phylogeny-aware clustering, gene fusion detection |
| **Key parameter** | MCL inflation (1.5) | E-value (0.0001) | Tree method (nj/me/ml) |

---

## Data Flow

### Input

All three tools read from the same source:

```
genomesDB/STEP_4/output_to_input/speciesN_gigantic_T1_proteomes/
```

Path configured in each tool's config YAML.

### Output

Each tool's standardized output is accessible at:

```
orthogroups/BLOCK_orthofinder/output_to_input/
orthogroups/BLOCK_orthohmm/output_to_input/
orthogroups/BLOCK_broccoli/output_to_input/
orthogroups/BLOCK_comparison/output_to_input/
```

### Downstream Consumers

| Subproject | What It Uses |
|------------|-------------|
| **trees_gene_families** | Orthogroup members as starting points for gene family phylogenetics |
| **trees_gene_groups** | Orthogroup assignments for gene group phylogenetic analyses |
| **orthogroups_X_ocl** | Orthogroups + species tree for origin-conservation-loss inference |
| **annotations_X_ocl** | Orthogroup dynamics + functional annotations |

---

## Verification

```bash
# Check OrthoFinder completed
ls BLOCK_orthofinder/output_to_input/orthogroups_gigantic_ids.tsv

# Check orthogroup counts across tools
wc -l BLOCK_*/output_to_input/orthogroups_gigantic_ids.tsv

# Quick comparison: total orthogroups per tool
head -1 BLOCK_*/output_to_input/summary_statistics.tsv

# Check per-species coverage
head BLOCK_orthofinder/output_to_input/per_species_summary.tsv
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `No proteome files found` | Config path to genomesDB proteomes is wrong | Update `proteome_directory` in config YAML |
| `OrthoFinder: command not found` | Conda environment not activated | `RUN-workflow.sh` should activate automatically; check conda env exists |
| `Comparison requires at least 2 tools` | Only one tool pipeline completed | Run at least one more tool pipeline before comparison |
| OrthoHMM/Broccoli header errors | Tool can't handle long headers | This is handled by the short ID conversion - check script 002 log |
| Very different orthogroup counts | Expected - tools use different algorithms | Compare via BLOCK_comparison; differences are informative |
| Low coverage for some species | Species has few orthologs or poor proteome quality | Check BUSCO scores in genomesDB STEP_2 quality summary |

---

## External Tools and References

| Tool | Purpose | Citation | Repository |
|------|---------|----------|------------|
| **OrthoFinder** | All-vs-all + MCL ortholog detection | Emms & Kelly (2019) *Genome Biology* 20:238. [DOI](https://doi.org/10.1186/s13059-019-1832-y) | [github.com/OrthoFinder/OrthoFinder](https://github.com/OrthoFinder/OrthoFinder) |
| **OrthoHMM** | Profile HMM ortholog detection | Steenwyk & King (2024) *bioRxiv*. [DOI](https://doi.org/10.1101/2024.12.07.627370) | [github.com/JLSteenwyk/orthohmm](https://github.com/JLSteenwyk/orthohmm) |
| **Broccoli** | Phylogeny-network ortholog detection | Derelle et al. (2020) *Mol Biol Evol* 37(11):3389-3396. [DOI](https://doi.org/10.1093/molbev/msaa159) | [github.com/rderelle/Broccoli](https://github.com/rderelle/Broccoli) |
| **Diamond** | Fast protein alignment (used by OrthoFinder, Broccoli) | Buchfink et al. (2021) *Nature Methods* 18:366-368. [DOI](https://doi.org/10.1038/s41592-021-01101-x) | [github.com/bbuchfink/diamond](https://github.com/bbuchfink/diamond) |
| **HMMER** | Profile HMM search (used by OrthoHMM) | Eddy (2011) *PLoS Comp Biol* 7(10):e1002195. [DOI](https://doi.org/10.1371/journal.pcbi.1002195) | [github.com/EddyRivasLab/hmmer](https://github.com/EddyRivasLab/hmmer) |
| **MCL** | Graph-based clustering (used by all three tools) | Enright et al. (2002) *Nucleic Acids Research* 30(7):1575-1584. [DOI](https://doi.org/10.1093/nar/30.7.1575) | - |
| **FastTree** | Approximate ML trees (used by Broccoli, OrthoFinder) | Price et al. (2010) *PLoS ONE* 5(3):e9490. [DOI](https://doi.org/10.1371/journal.pone.0009490) | [github.com/morgannprice/fasttree](https://github.com/morgannprice/fasttree) |
| **MAFFT** | Multiple sequence alignment (used by OrthoFinder) | Katoh & Standley (2013) *Mol Biol Evol* 30(4):772-780. [DOI](https://doi.org/10.1093/molbev/mst010) | [github.com/GSLBiotech/mafft](https://github.com/GSLBiotech/mafft) |
| **Nextflow** | Workflow orchestration for all four projects | Di Tommaso et al. (2017) *Nature Biotechnology* 35:316-319. [DOI](https://doi.org/10.1038/nbt.3820) | [github.com/nextflow-io/nextflow](https://github.com/nextflow-io/nextflow) |

All tools are installed via the `ai_gigantic_orthogroups` conda environment. OrthoHMM and Broccoli install via pip; all others via conda-forge or bioconda channels.

**Note**: OrthoHMM is currently a preprint (bioRxiv). Check for peer-reviewed publication before manuscript submission.

---

*For AI assistant guidance, see `AI_GUIDE-orthogroups.md` and per-BLOCK workflow `AI_GUIDE-*_workflow.md` files.*
