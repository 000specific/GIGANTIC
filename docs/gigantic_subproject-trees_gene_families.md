# The GIGANTIC Gene Family Tree Pipeline (trees_gene_families)

The trees_gene_families subproject builds phylogenetic trees for individual gene families across all GIGANTIC species. Starting from user-curated reference sequences, it discovers homologs via reciprocal best hit/best family BLAST, aligns them, and builds trees using one or more phylogenetic methods.

trees_gene_families depends on [genomesDB](gigantic_subproject-genomesDB.md) (per-species BLAST databases + header mapping) and [phylonames](gigantic_subproject-phylonames.md) (species naming).

---

## Three-Step Architecture

```
STEP_1-rgs_preparation        Validate reference gene set (optional)
    |
STEP_2-homolog_discovery       RBH/RBF BLAST across all species (16 scripts)
    |
STEP_3-phylogenetic_analysis   Align → Trim → Build trees → Visualize (10 scripts)
```

Each step is an independent Nextflow pipeline. Each workflow copy processes **one gene family**. To analyze multiple gene families, create multiple copies of the workflow template.

---

## Gene Set Terminology

| Term | Abbrev. | Definition |
|------|---------|-----------|
| Reference Gene Set | **RGS** | User-curated protein sequences from model organisms defining the gene family |
| Blast Gene Set | **BGS** | Sequences found by forward BLAST of RGS against all project species |
| Candidate Gene Set | **CGS** | BGS sequences confirmed as homologs by reciprocal BLAST |
| All Gene Set | **AGS** | Final set: RGS + filtered CGS, ready for phylogenetic analysis |

---

## STEP_1: RGS Preparation (Optional)

### What It Does

Validates the user-provided RGS FASTA file against GIGANTIC naming conventions.

### RGS File Format

**Filename**: `rgsN-gene_family_name-source-date.aa` (N = sequence count)

**Headers**: `>rgsN-species-source-identifier`

**Example**:
```
File: rgs12-innexins-uniprot-20240115.aa
Header: >rgs12-Homo_sapiens-uniprot-Q5T7V8
```

### Validation Checks

- Filename matches `rgsN-name-source-date.ext` pattern
- All headers match `>rgsN-species-source-identifier` pattern
- N value is consistent across all headers
- N equals the actual number of sequences
- No duplicate sequence IDs

### Running

```bash
cd subprojects/trees_gene_families/STEP_1-rgs_preparation/workflow-COPYME-validate_rgs/
cp your_rgs_file.aa INPUT_user/
nano rgs_config.yaml
bash RUN-workflow.sh
```

---

## STEP_2: Homolog Discovery (16 Scripts)

### What It Does

Discovers homologs across all project species using reciprocal best hit / reciprocal best family BLAST. This is the computational core of the pipeline.

### The Four Phases

```
Phase 1: Forward BLAST          (Scripts 001-004)
  RGS → BLAST → all species proteomes → extract BGS sequences

Phase 2: RGS Genome BLAST       (Scripts 005-006)
  RGS → BLAST → source species proteomes → map RGS to genome identifiers

Phase 3: Reciprocal BLAST        (Scripts 007-012)
  BGS sequences → BLAST → modified source genomes → filter by best hit

Phase 4: Filtering & Assembly    (Scripts 013-016)
  Extract CGS → filter species → remap to GIGANTIC IDs → assemble AGS
```

### Phase 1: Forward BLAST (Scripts 001-004)

| Script | What It Does |
|--------|-------------|
| 001 | Inventories per-species BLAST databases from genomesDB |
| 002 | Generates `blastp` commands (one per species) |
| 003 | Executes forward BLAST (`blastp -evalue 1e-3 -outfmt 6 -num_threads 50`) |
| 004 | Extracts full-length proteins (fullseqs) and hit regions from BLAST results |

**Important**: Script 004 extracts **full-length** sequences for reciprocal BLAST, not just hit regions. Using full-length ensures accurate best-hit determination when conserved domains are shared across gene families.

### Phase 2: RGS Genome BLAST (Scripts 005-006)

| Script | What It Does |
|--------|-------------|
| 005 | Generates BLAST commands: RGS vs. source species proteomes only |
| 006 | Executes RGS genome BLAST to identify which genome genes correspond to RGS entries |

### Phase 3: Reciprocal BLAST (Scripts 007-012)

| Script | What It Does |
|--------|-------------|
| 007 | Inventories RGS genome BLAST reports |
| 008 | Maps each RGS sequence to its best-hit gene in source genomes |
| 009 | Creates "modified genomes": replaces identified genome sequences with RGS sequences |
| 010 | Builds combined BLAST database from all modified genomes |
| 011 | Generates reciprocal BLAST commands (each BGS sequence vs. combined modified genomes) |
| 012 | Executes reciprocal BLAST |

**The modified genome trick**: For each RGS source species, the pipeline takes the full proteome and replaces sequences identified as RGS matches with the actual RGS sequences (using RGS headers). When a candidate sequence is BLASTed back against these modified genomes, a "hit to RGS" confirms it belongs to the same gene family.

### Phase 4: Filtering and Assembly (Scripts 013-016)

| Script | What It Does |
|--------|-------------|
| 013 | Extracts CGS: candidates whose reciprocal best hit is an RGS entry |
| 014 | Filters CGS to keep only species in `species_keeper_list.tsv` |
| 015 | Remaps truncated BLAST IDs back to full GIGANTIC phylonames |
| 016 | Assembles final AGS: RGS (also remapped to GIGANTIC IDs) + filtered CGS |

### BLAST Identifier Truncation

BLAST truncates identifiers at 50 characters. GIGANTIC's phyloname-based headers routinely exceed 100 characters. The pipeline works with truncated IDs through BLAST phases (scripts 001-013), then remaps to full identifiers (script 015) using the header mapping file from genomesDB.

### Configuration

Edit `homolog_discovery_config.yaml`:

```yaml
gene_family:
  name: "innexins"
  rgs_fasta: "INPUT_user/rgs12-innexins-uniprot-20240115.aa"

blast:
  evalue: "1e-3"
  num_threads: 50

species:
  keeper_list: "INPUT_user/species_keeper_list.tsv"
```

### Running

```bash
cd subprojects/trees_gene_families/STEP_2-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/
cp your_rgs.aa INPUT_user/
nano INPUT_user/species_keeper_list.tsv
nano homolog_discovery_config.yaml
bash RUN-workflow.sh          # Local
sbatch RUN-workflow.sbatch    # SLURM
```

---

## STEP_3: Phylogenetic Analysis (10 Scripts)

### What It Does

Takes the AGS from STEP_2 and produces aligned, trimmed, phylogenetic trees with visualizations.

### Pipeline Flow

```
001: Stage AGS from STEP_2
002: Clean sequences (remove leading/trailing dashes)
003: MAFFT multiple sequence alignment
004: ClipKit alignment trimming
005: Tree building (1-4 methods, user-selectable)
006: Human-friendly tree visualization (SVG)
007: Computer-vision-friendly tree visualization (SVG)
```

### Process 3: MAFFT Alignment

```bash
mafft --originalseqonly --maxiterate 1000 --reorder --bl 45 --thread 50 input.aa > output.mafft
```

| Flag | Purpose |
|------|---------|
| `--originalseqonly` | Preserve input sequences only |
| `--maxiterate 1000` | Iterative refinement for accuracy |
| `--reorder` | Output ordered by similarity |
| `--bl 45` | BLOSUM45 matrix (better for divergent sequences) |
| `--thread 50` | Multi-threaded execution |

**BLOSUM45 rationale**: GIGANTIC spans deep evolutionary divergence. BLOSUM45 provides better sensitivity than the default BLOSUM62 for highly divergent sequences.

### Process 4: ClipKit Trimming

```bash
clipkit alignment.mafft -m smart-gap -o output.clipkit-smartgap -l
```

`smart-gap` mode dynamically determines a gap threshold. The `-l` flag (boolean, no argument) enables a trimming log documenting which positions were kept or removed.

### Process 5: Tree Building (4 Methods)

Users select which methods to enable in the config YAML. Multiple methods can run on the same alignment.

| Method | Command | Best For | Runtime |
|--------|---------|----------|---------|
| **FastTree** (default) | `FastTree <trimmed> > output.fasttree` | Exploratory analysis, rapid iteration | Minutes |
| **IQ-TREE** | `iqtree -s <trimmed> -m MFP -B 2000 -alrt 2000 --rate -bnni -T AUTO` | Publication-quality, rigorous statistics | Hours-days |
| **VeryFastTree** | `VeryFastTree -threads 4 <trimmed> > output.veryfasttree` | Datasets >10,000 sequences | Minutes |
| **PhyloBayes** | `pb -d alignment.phy -cat -gtr -x 1 10000 chainN` | Bayesian inference, long-branch attraction detection | Days-weeks |

**FastTree**: JTT+CAT model, SH-aLRT branch support. Fast and reasonable for exploration.

**IQ-TREE**: ModelFinder Plus automatic model selection + 2000 ultrafast bootstrap + 2000 SH-aLRT replicates. The `-bnni` flag improves bootstrap tree optimization. Gold standard for publication.

**VeryFastTree**: Parallelized FastTree reimplementation. Note: at typical GIGANTIC dataset sizes (50-500 sequences), FastTree actually produces equal or better quality trees. VeryFastTree's parallelization advantage materializes only above ~10,000 sequences.

**PhyloBayes**: CAT-GTR model. Runs two independent MCMC chains, assesses convergence with `bpcomp` and `tracecomp`. Requires PHYLIP format (converted automatically). The slowest method but provides Bayesian posterior probabilities as an alternative to bootstrap support.

### Configuration

Edit `phylogenetic_analysis_config.yaml`:

```yaml
tree_methods:
  fasttree: true          # Fast, good for exploration
  iqtree: false           # Slow, publication-quality
  veryfasttree: false     # For very large datasets only
  phylobayes: false       # Bayesian, very slow

slurm:
  mafft_cpus: 100
  mafft_memory: "700gb"
  mafft_time: "100:00:00"
  iqtree_cpus: 100
  iqtree_memory: "700gb"
  iqtree_time: "100:00:00"
```

### Running

```bash
cd subprojects/trees_gene_families/STEP_3-phylogenetic_analysis/workflow-COPYME-phylogenetic_analysis/
nano phylogenetic_analysis_config.yaml    # Select tree methods
bash RUN-workflow.sh                       # Local
sbatch RUN-workflow.sbatch                 # SLURM
```

---

## Output Structure

### Final Outputs (in output_to_input/)

```
trees_gene_families/output_to_input/
├── step_1/rgs_fastas/<gene_family>/
│   └── validated RGS FASTA
├── step_2/ags_fastas/<gene_family>/
│   └── AGS FASTA (RGS + homologs, full GIGANTIC IDs)
└── step_3/trees/<gene_family>/
    ├── *.mafft                    (MAFFT alignment)
    ├── *.clipkit-smartgap         (trimmed alignment)
    ├── *.fasttree                 (FastTree tree, Newick)
    ├── *.treefile                 (IQ-TREE tree, Newick)
    ├── *.veryfasttree             (VeryFastTree tree, Newick)
    ├── *.phylobayes.nwk           (PhyloBayes consensus tree)
    └── *.svg                      (tree visualizations)
```

---

## Multi-Gene-Family Workflow

To analyze multiple gene families:

```bash
# Copy template for each gene family
cp -r workflow-COPYME-rbh_rbf_homologs/ workflow-RUN_01-innexins/
cp -r workflow-COPYME-rbh_rbf_homologs/ workflow-RUN_02-wnt_ligands/
cp -r workflow-COPYME-rbh_rbf_homologs/ workflow-RUN_03-piezo/

# Configure each copy
cd workflow-RUN_01-innexins/
nano homolog_discovery_config.yaml    # Set gene_family name, RGS path
cp rgs12-innexins-uniprot-20240115.aa INPUT_user/
bash RUN-workflow.sh
```

Each copy is fully independent. Multiple copies can run in parallel on an HPC cluster.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `No BLAST databases found` | Config path to genomesDB blastp databases is wrong | Update `blast_databases` path in config YAML |
| `Species not found in header mapping` | Header map from genomesDB doesn't include a species | Re-run genomesDB STEP_4 or check species list |
| `RGS validation failed: N mismatch` | Sequence count in filename doesn't match actual count | Update filename or add/remove sequences |
| BLAST returns no hits for a species | Species proteome has no homologs or evalue too strict | Check species proteome quality; try relaxing evalue |
| ClipKit produces empty alignment | All columns trimmed due to excessive gaps | Check MAFFT alignment quality; too-divergent sequences may need removal |
| IQ-TREE runs out of memory | Large alignment + complex model | Increase memory in config YAML `slurm:` section |
| PhyloBayes chains don't converge | Need more MCMC generations | Increase `-x` parameter or run longer |
| Visualization placeholder created | ete3 library not available | Install ete3 in conda environment; tree data is unaffected |

---

## External Tools and References

| Tool | Purpose | Citation | Repository |
|------|---------|----------|------------|
| **BLAST+** | Forward and reciprocal homolog search | Camacho et al. (2009) *BMC Bioinformatics* 10:421. [DOI](https://doi.org/10.1186/1471-2105-10-421) | [github.com/ncbi/ncbi-cxx-toolkit-public](https://github.com/ncbi/ncbi-cxx-toolkit-public) |
| **MAFFT** | Multiple sequence alignment | Katoh & Standley (2013) *Mol Biol Evol* 30(4):772-780. [DOI](https://doi.org/10.1093/molbev/mst010) | [github.com/GSLBiotech/mafft](https://github.com/GSLBiotech/mafft) |
| **ClipKit** | Alignment trimming | Steenwyk et al. (2020) *PLoS Biology* 18(12):e3001007. [DOI](https://doi.org/10.1371/journal.pbio.3001007) | [github.com/JLSteenwyk/ClipKIT](https://github.com/JLSteenwyk/ClipKIT) |
| **FastTree** | Approximate ML phylogenetic trees | Price et al. (2010) *PLoS ONE* 5(3):e9490. [DOI](https://doi.org/10.1371/journal.pone.0009490) | [github.com/morgannprice/fasttree](https://github.com/morgannprice/fasttree) |
| **IQ-TREE** | Maximum likelihood phylogenetics | Minh et al. (2020) *Mol Biol Evol* 37(5):1530-1534. [DOI](https://doi.org/10.1093/molbev/msaa015) | [github.com/iqtree/iqtree2](https://github.com/iqtree/iqtree2) |
| **VeryFastTree** | Parallelized FastTree | Piñeiro et al. (2020) *Bioinformatics* 36(17):4658-4659. [DOI](https://doi.org/10.1093/bioinformatics/btaa582) | - |
| **PhyloBayes-MPI** | Bayesian MCMC phylogenetics | Lartillot et al. (2013) *Systematic Biology* 62(4):611-615. [DOI](https://doi.org/10.1093/sysbio/syt022) | - |
| **ete3** | Tree visualization | Huerta-Cepas et al. (2016) *Mol Biol Evol* 33(6):1635-1638. [DOI](https://doi.org/10.1093/molbev/msw046) | [github.com/etetoolkit/ete](https://github.com/etetoolkit/ete) |
| **Nextflow** | Workflow orchestration | Di Tommaso et al. (2017) *Nature Biotechnology* 35:316-319. [DOI](https://doi.org/10.1038/nbt.3820) | [github.com/nextflow-io/nextflow](https://github.com/nextflow-io/nextflow) |

All tools are installed via the `ai_gigantic_trees_gene_families` conda environment.

---

*For AI assistant guidance, see `AI_GUIDE-trees_gene_families.md` and per-STEP workflow `AI_GUIDE-*_workflow.md` files.*
