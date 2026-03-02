# The GIGANTIC Phyloname System

GIGANTIC uses a standardized phylogenetic naming convention for consistent species identification across all analyses. The `phylonames` subproject generates these identifiers from the NCBI Taxonomy database and must run before any other subproject.

---

## Two Phyloname Formats

**CRITICAL**: GIGANTIC distinguishes between two phyloname formats. This distinction is maintained throughout the platform.

### `phyloname` (Standard Format)

```
Kingdom_Phylum_Class_Order_Family_Genus_species
```

**Example**:
```
Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides
```

**Usage**:
- Species identification in analysis outputs
- Column headers and table values
- Data integration between subprojects
- **Most common format throughout GIGANTIC**

### `phyloname_taxonid` (Extended Format)

```
Kingdom_Phylum_Class_Order_Family_Genus_species___taxonID
```

**Example**:
```
Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides___37653
```

**Usage**:
- Naming downloaded genomic data files (guarantees uniqueness)
- NCBI taxonomy database linkage
- Distinguishing subspecies or strains with identical names
- Cases requiring absolute taxonomic precision

### Terminology Rule

Throughout GIGANTIC:
- Use **`phyloname`** for the standard format (no taxon ID)
- Use **`phyloname_taxonid`** for the extended format (with `___taxonID`)
- **Never use these terms interchangeably**

---

## Field Positions (0-indexed)

| Position | Level | Example |
|----------|-------|---------|
| [0] | Kingdom | Metazoa |
| [1] | Phylum | Mollusca |
| [2] | Class | Cephalopoda |
| [3] | Order | Octopoda |
| [4] | Family | Octopodidae |
| [5] | Genus | Octopus |
| [6:] | species | bimaculoides |

---

## Extracting Taxonomic Levels

In Python:

```python
phyloname = 'Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides'
parts = phyloname.split( '_' )

kingdom = parts[ 0 ]      # Metazoa
phylum = parts[ 1 ]       # Mollusca
class_name = parts[ 2 ]   # Cephalopoda
order = parts[ 3 ]        # Octopoda
family = parts[ 4 ]       # Octopodidae
genus = parts[ 5 ]        # Octopus
species = '_'.join( parts[ 6: ] )  # bimaculoides (handles multi-word species)

genus_species = f"{genus}_{species}"  # Octopus_bimaculoides
```

**Important**: Use `parts[6:]` with `join()` to correctly handle multi-word species names (e.g., subspecies, strains).

In Bash:

```bash
# Extract genus_species from a phyloname
phyloname="Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides"
genus_species=$(echo "$phyloname" | awk -F'_' '{for(i=6;i<=NF;i++) printf "%s%s", $i, (i<NF?"_":"")}')
# Result: Octopus_bimaculoides

# Group files by phylum
phylum=$(echo "$phyloname" | cut -d'_' -f2)
# Result: Mollusca
```

---

## Why Phylonames?

| Benefit | Description |
|---------|-------------|
| **Consistency** | Same identifier across all subprojects and analyses |
| **Hierarchy** | Programmatic access to any taxonomic level |
| **Sorting** | Alphabetical sorting groups related species together |
| **Clarity** | Immediately see taxonomic placement in any output |
| **Self-documenting** | No external lookup needed to understand species relationships |
| **File-system safe** | Only underscores - no spaces, parentheses, or special characters |

---

## The Phylonames Pipeline

The pipeline consists of six sequential processes that download NCBI taxonomy data, generate phylonames for all organisms, extract a project-specific mapping, optionally apply user overrides, and produce a taxonomy summary.

### Pipeline Overview

```
Process 1: Download NCBI taxonomy dump (or use cached version)
    |
Process 2: Generate phylonames for ALL organisms in NCBI (~2M entries)
    |
Process 3: Extract mapping for YOUR species list
    |
Process 4: Apply user-provided phyloname overrides (optional)
    |
Process 5: Generate taxonomy summary (Markdown + HTML)
    |
Process 6: Write run log to research notebook
```

### Running the Pipeline

```bash
# 1. Edit your species list (one Genus_species per line)
nano INPUT_gigantic/species_list.txt

# 2. Edit configuration
nano subprojects/phylonames/BLOCK_generate_phylonames/workflow-COPYME-generate_phylonames/phylonames_config.yaml

# 3. Run
cd subprojects/phylonames/BLOCK_generate_phylonames/workflow-COPYME-generate_phylonames/
bash RUN-workflow.sh          # Local
sbatch RUN-workflow.sbatch    # SLURM
```

**Runtime**: First run ~15 minutes (downloads NCBI taxonomy). Subsequent runs ~1 minute (reuses cached database).

### Configuration

Key settings in `phylonames_config.yaml`:

```yaml
project:
  name: "my_project"              # Used in output file naming
  species_list: "INPUT_user/species_list.txt"
  user_phylonames: ""             # Path to override file, or empty to skip
  mark_unofficial: true           # Append UNOFFICIAL to user-provided clades

ncbi_taxonomy:
  force_download: false           # Set true to re-download even if cached
```

### Output Files

| Directory | File | Description |
|-----------|------|-------------|
| `2-output/` | `phylonames` | Full phylonames for all NCBI organisms |
| `2-output/` | `phylonames_taxonid` | Extended format with NCBI taxon IDs |
| `2-output/` | `map-phyloname_X_ncbi_taxonomy_info.tsv` | Complete mapping with all NCBI fields |
| `2-output/` | `map-numbered_clades_X_defining_clades.tsv` | Reference for all numbered clade assignments |
| `3-output/` | `{project}_map-genus_species_X_phylonames.tsv` | **Project mapping** (this is what downstream subprojects use) |
| `4-output/` | Final mapping with user overrides applied (if configured) |
| `5-output/` | Taxonomy summary in Markdown and HTML |

### Verification

After a successful run:

```bash
# Check species count matches your input
wc -l OUTPUT_pipeline/3-output/*_map-genus_species_X_phylonames.tsv

# Verify a specific species
grep "Homo_sapiens" OUTPUT_pipeline/3-output/*_map-genus_species_X_phylonames.tsv

# Check for numbered clades in your species set
grep -P '\d+\t' OUTPUT_pipeline/3-output/*_map-genus_species_X_phylonames.tsv

# View HTML taxonomy summary in browser
# Located at: OUTPUT_pipeline/5-output/taxonomy_summary.html
```

---

## The Generation Algorithm

### Character Cleaning

NCBI taxonomy entries may contain characters that cause problems in file paths and bioinformatics tools. The algorithm removes: `( ) [ ] / . ' : -`

After removal, resulting whitespace segments are joined with underscores:

| NCBI Input | Cleaned Output |
|------------|---------------|
| `Escherichia coli K-12` | `Escherichia_coli_K_12` |
| `Candidatus (Bacteria)` | `Candidatus_Bacteria` |
| `[Haemophilus] ducreyi` | `Haemophilus_ducreyi` |

### Species Name Handling

The algorithm uses NCBI's `taxon_name` field (not the `species` field) to preserve strain, subspecies, and variant designators that the `species` field may drop. Multi-word species names are joined with underscores:

```
NCBI taxon_name: "Hoilungia hongkongensis H13"
Phyloname species field: hongkongensis_H13
```

### Handling Missing Taxonomy Levels

When NCBI lacks a classification at a given rank (common for non-model organisms), the algorithm assigns a numbered placeholder using the **first named clade below** principle:

1. Identify the first taxonomic level **below** the missing level that has a named classification.
2. Assign a unique number based on that clade.
3. Species sharing the same "first named clade below" receive the **same** numbered identifier.

**Example**: Three species all lack a classified Order:

| Species | Family (first named below Order) | Assigned Order |
|---------|----------------------------------|---------------|
| Species A | Bolinopsidae | `Order7890` |
| Species B | Bolinopsidae | `Order7890` (same - same family) |
| Species C | Leucotheidae | `Order12456` (different - different family) |

This preserves phylogenetic grouping: species in the same family get the same numbered Order.

All numbered clade assignments are documented in `map-numbered_clades_X_defining_clades.tsv`, which maps each numbered clade to the named clade that defines it.

### Clade Splitting Limitation

**IMPORTANT**: Numbered clades can create artificial splits in downstream analyses.

When a single unknown higher-level clade actually contains multiple lower-level clades, GIGANTIC must assign different numbers because it cannot know they belong together. Consider two families (Bolinopsidae and Leucotheidae) that belong to the same unnamed Order in reality:

```
Reality:                        GIGANTIC representation:
Unknown Order                   Order7890  (Bolinopsidae)
├── Bolinopsidae                Order12456 (Leucotheidae)
└── Leucotheidae                These look like separate Orders
```

**Impact on downstream analyses**: Origin-Conservation-Loss (OCL) analyses and species tree topology generation may treat these as separate clades, potentially inflating the number of evolutionary origins or losses. If your species set spans such a split, consider using user-provided phylonames (Process 4) to assign a consistent clade name.

---

## User-Provided Phylonames

### When to Use

- NCBI lacks classification at Kingdom or Phylum level for your species
- Recent literature supports a different taxonomic placement than NCBI
- You want to apply a specific phylogenetic hypothesis to your analysis

### Input Format

Tab-separated file with two columns:

```
genus_species	phyloname
Monosiga_brevicollis	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis
Salpingoeca_rosetta	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Salpingoeca_rosetta
```

### The UNOFFICIAL Marking System

When `mark_unofficial: true` (default), any clade in positions 0-4 (Kingdom through Family) that differs from the NCBI-derived value is appended with `UNOFFICIAL`:

```
User provides:    Holozoa_Choanozoa_Choanoflagellata_...
NCBI has:         Kingdom42_Phylum156_Choanoflagellata_...
Result:           HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_Choanoflagellata_...
                  ^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^
                  Differs from NCBI   Differs from NCBI
                  (gets UNOFFICIAL)   (gets UNOFFICIAL)
```

Genus and species positions (5, 6+) are never marked UNOFFICIAL.

**Configuration**:
```yaml
project:
  mark_unofficial: true    # Append UNOFFICIAL to differing clades
  # mark_unofficial: false   # Use user clades without marking
```

Even when marking is disabled, a separate `unofficial_clades_report.tsv` documents all overrides.

---

## Proteome File Naming Convention

Proteome files use `phyloname_taxonid` plus additional metadata:

```
phyloname_taxonid-genome_assembly_id-download_date-data_type.aa
```

### Example

```
Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides___37653-ncbi_GCF_001194135.2-downloaded_20241011-gene_models_T1.aa
```

**Components**:
- `phyloname_taxonid`: Full phyloname with NCBI taxon ID
- `genome_assembly_id`: NCBI assembly identifier
- `download_date`: When proteome was downloaded (YYYYMMDD)
- `data_type`: Type of data (e.g., `gene_models_T1` for transcript 1)
- `.aa`: Amino acid sequence file extension

---

## Mapping Files

The `phylonames/output_to_input/maps/` directory contains the project mapping file, which is the canonical species reference for all downstream subprojects:

```
{project_name}_map-genus_species_X_phylonames.tsv
```

**Format** (tab-separated):
```
genus_species	phyloname	phyloname_taxonid
Octopus_bimaculoides	Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides	Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides___37653
```

If user phylonames were applied, two additional columns are present:

```
genus_species	phyloname	phyloname_taxonid	source	original_ncbi_phyloname
```

Where `source` is `NCBI` or `USER`, and `original_ncbi_phyloname` records the NCBI-derived phyloname before any override.

---

## Integration with Other Subprojects

All GIGANTIC subprojects use phylonames:

| Subproject | How Phylonames Are Used |
|------------|------------------------|
| **genomesDB** | Proteome file naming (uses `phyloname_taxonid`), species standardization |
| **orthogroups** | Species identification in orthogroup tables across all methods |
| **trees_gene_families** | Tree tip labels, sequence headers, BLAST database naming |
| **trees_gene_groups** | Species identification in gene group phylogenetic analyses |
| **one_direction_homologs** | Species identification in DIAMOND searches against NCBI nr |
| **gene_sizes** | Species identification in gene structure metric tables |
| **trees_species** | Clade definitions and tree topology labels |
| **annotations_hmms** | Linking functional annotations to species |
| **orthogroups_X_ocl** | Species tracking in origin-conservation-loss analyses |

The mapping file in `phylonames/output_to_input/maps/` is the authoritative source for all subprojects.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Species not found in master mapping` | Species name not in NCBI taxonomy | Check spelling, verify NCBI Taxonomy ID exists, consider using user-provided phylonames |
| `No database directory found` | NCBI download failed or not yet run | Check internet connectivity, run with `force_download: true` |
| `Permission denied` on download | Write permissions on output directory | Check directory ownership and permissions |
| `rankedlineage.dmp not found` | Corrupt or incomplete NCBI download | Delete the database directory and re-run |
| Numbered clades in your species | NCBI taxonomy is incomplete for some species | Expected behavior - review `map-numbered_clades_X_defining_clades.tsv` for details |
| Too many UNOFFICIAL clades | User phylonames differ significantly from NCBI | Verify your taxonomic framework is correct at each level |

---

## NCBI Taxonomy Source

- **Source**: `ftp://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/`
- **Primary file**: `rankedlineage.dmp`
- **Database size**: ~2 GB compressed, ~1.9 GB extracted
- **Full phylonames output**: ~250 MB for all organisms
- **Updated regularly** by NCBI

GIGANTIC creates versioned directories with timestamps:
```
database-ncbi_taxonomy_20260205_143052/
```

A `database-ncbi_taxonomy_latest` symlink always points to the most recent download. Subsequent pipeline runs reuse the cached database unless `force_download: true` is set.

---

## Quick Reference

| Question | Answer |
|----------|--------|
| Where is the species list? | `INPUT_gigantic/species_list.txt` |
| Where is the project mapping? | `phylonames/output_to_input/maps/{project}_map-genus_species_X_phylonames.tsv` |
| How do I add user phylonames? | Set `project.user_phylonames` in config YAML to path of override file |
| How do I check for numbered clades? | `grep -P '(Kingdom|Phylum|Class|Order|Family)\d+' your_mapping.tsv` |
| How do I re-download NCBI taxonomy? | Set `ncbi_taxonomy.force_download: true` in config |
| Where is the HTML summary? | `OUTPUT_pipeline/5-output/taxonomy_summary.html` |
| What conda environment is needed? | `ai_gigantic_phylonames` |

---

## External Tools and References

| Tool/Resource | Purpose in phylonames | Citation | Repository/URL |
|---------------|----------------------|----------|----------------|
| **NCBI Taxonomy** | Source taxonomic database (`rankedlineage.dmp`) | Schoch et al. (2020) *Database* 2020:baaa062. [DOI](https://doi.org/10.1093/database/baaa062) | [ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/](https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/) |
| **Nextflow** | Workflow orchestration | Di Tommaso et al. (2017) *Nature Biotechnology* 35:316-319. [DOI](https://doi.org/10.1038/nbt.3820) | [github.com/nextflow-io/nextflow](https://github.com/nextflow-io/nextflow) |

The phylonames pipeline uses only Python 3 standard library and Bash - no additional bioinformatics packages are required beyond Nextflow for workflow management.

---

*For AI assistant guidance, see `AI_GUIDE-phylonames.md` and workflow-level `AI_GUIDE-phylonames_workflow.md`*
