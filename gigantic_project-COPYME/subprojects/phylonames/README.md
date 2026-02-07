# phylonames - GIGANTIC Phylogenetic Naming System

**AI**: Claude Code | Opus 4.5 | 2026 February 05
**Human**: Eric Edsinger

---

## Purpose

The phylonames subproject provides a standardized naming system for species across GIGANTIC. It downloads the NCBI taxonomy database and generates phylogenetically-informative species identifiers that encode the complete taxonomic lineage.

**This subproject MUST run first** - all other GIGANTIC subprojects depend on phylonames.

---

## Phyloname Formats

GIGANTIC uses two distinct phyloname formats. This distinction is **critical** throughout the platform:

### `phyloname` (Standard Format)
```
Kingdom_Phylum_Class_Order_Family_Genus_species
```
**Example**: `Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens`

**Usage**:
- Species identification across all GIGANTIC outputs
- Column headers and table values in TSV files
- Data integration and lookups between subprojects
- **This is the most commonly used format**

### `phyloname_taxonid` (Extended Format)
```
Kingdom_Phylum_Class_Order_Family_Genus_species___taxonID
```
**Example**: `Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens___9606`

**Usage**:
- Renaming downloaded genomic data files (guarantees uniqueness)
- NCBI taxonomy database linkage
- Cases requiring absolute taxonomic precision
- Distinguishing subspecies or strains with identical names

### Consistency Rule

Throughout GIGANTIC code and documentation:
- Use `phyloname` when referring to the standard format (no taxon ID)
- Use `phyloname_taxonid` when referring to the extended format (with `___taxonID`)
- **Never use these terms interchangeably**

---

## Field Positions (0-indexed)

| Position | Level | Example |
|----------|-------|---------|
| [0] | Kingdom | Metazoa |
| [1] | Phylum | Mollusca |
| [2] | Class | Gastropoda |
| [3] | Order | Aplysiida |
| [4] | Family | Aplysiidae |
| [5] | Genus | Aplysia |
| [6:] | species | californica |

**Extracting genus_species from phyloname**:
```python
phyloname = 'Metazoa_Mollusca_Gastropoda_Aplysiida_Aplysiidae_Aplysia_californica'
parts = phyloname.split( '_' )
genus = parts[ 5 ]
species = '_'.join( parts[ 6: ] )  # Handles multi-word species names
genus_species = genus + '_' + species  # Result: 'Aplysia_californica'
```

---

## Directory Structure

```
phylonames/
├── README.md                           # This file
├── AI_GUIDE-phylonames.md              # AI assistant guidance
├── conda_environment-phylonames.yml    # Per-subproject environment
├── user_research/                      # Personal workspace
├── output_to_input/                    # Outputs for downstream subprojects
│   └── maps/                           # Species mapping files
│       └── [project]_map-genus_species_X_phylonames.tsv
└── nf_workflow-TEMPLATE_01-generate_phylonames/
    ├── RUN_phylonames.sh               # bash RUN_phylonames.sh (local)
    ├── RUN_phylonames.sbatch           # sbatch RUN_phylonames.sbatch (SLURM)
    ├── phylonames_config.yaml          # Edit this for your project
    ├── main.nf                         # NextFlow pipeline (don't edit)
    ├── nextflow.config                 # NextFlow settings (don't edit)
    ├── ai_scripts/                     # Python/Bash scripts (called by NextFlow)
    │   ├── 001_ai-bash-download_ncbi_taxonomy.sh
    │   ├── 002_ai-python-generate_phylonames.py
    │   └── 003_ai-python-create_species_mapping.py
    ├── INPUT_user/                     # User-provided species list
    │   └── species_list.txt            # One genus_species per line
    └── OUTPUT_pipeline/                # Generated phylonames and mappings
```

**AI Documentation**: Session logs, validation scripts, and debugging files are stored in:
```
research_notebook/research_ai/subproject-phylonames/
```

---

## Quick Start

### Step 1: Edit Your Species List

Edit `INPUT_user/species_list.txt` with your species (one per line):
```
Homo_sapiens
Aplysia_californica
Octopus_bimaculoides
```

### Step 2: Edit Configuration (Optional)

Edit `phylonames_config.yaml` to set your project name:

```yaml
project:
  name: "my_project"  # Change this to your project name
```

### Step 3: Run the Pipeline

```bash
cd nf_workflow-TEMPLATE_01-generate_phylonames

# Local machine:
bash RUN_phylonames.sh

# SLURM cluster (edit account/qos first):
sbatch RUN_phylonames.sbatch
```

The pipeline will:
1. Download NCBI taxonomy database (~2GB, skipped if already exists)
2. Generate phylonames for all NCBI species (~5-10 minutes)
3. Create your project-specific mapping file

### Output

Your mapping file will be at:
```
output_to_input/maps/[project_name]_map-genus_species_X_phylonames.tsv
```

---

## Input Format

**Species List** (`INPUT_user/species_list.txt`):
One species per line, formatted as `Genus_species`:
```
Homo_sapiens
Aplysia_californica
Octopus_bimaculoides
Mnemiopsis_leidyi
```

Lines starting with `#` are treated as comments and ignored.

---

## Output Files

### Master Phylonames Database

**Location**: `OUTPUT_pipeline/output/2-output/`

| File | Description |
|------|-------------|
| `phylonames` | All phylonames, one per line (standard format) |
| `phylonames_taxonid` | All phylonames with taxon ID (extended format) |
| `map-phyloname_X_ncbi_taxonomy_info.tsv` | Full mapping with all NCBI fields |
| `failed-entries.txt` | NCBI entries that couldn't be processed |
| `generation_metadata.txt` | Timestamp, counts, script version |

### Project-Specific Mapping

**Location**: `output_to_input/maps/`

| File | Description |
|------|-------------|
| `[project]_map-genus_species_X_phylonames.tsv` | Your species mapped to phylonames |

**Format** (tab-separated):
```
genus_species	phyloname	phyloname_taxonid
Homo_sapiens	Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens___9606
Aplysia_californica	Metazoa_Mollusca_Gastropoda_Aplysiida_Aplysiidae_Aplysia_californica	Metazoa_Mollusca_Gastropoda_Aplysiida_Aplysiidae_Aplysia_californica___6500
```

---

## Outputs Shared Downstream (`output_to_input/`)

Other GIGANTIC subprojects reference phylonames via:
```
phylonames/output_to_input/maps/[project]_map-genus_species_X_phylonames.tsv
```

**Dependent subprojects**:
- **genomesDB** - Uses phylonames for proteome file naming
- **trees_species** - Uses phylonames for clade definitions
- **trees_gene_families** - Uses phylonames for species identification
- **orthogroups** - Uses phylonames for species tracking
- **All other subprojects** - Reference species by phyloname

---

## NCBI Taxonomy Versioning

Each download creates a versioned database directory:
```
database-ncbi_taxonomy_YYYYMMDD_HHMMSS/
```

A symlink `database-ncbi_taxonomy_latest` always points to the most recent download.

**Why version?**
- NCBI regularly adds new species and corrects taxonomy
- Versioned directories enable reproducibility
- Multiple versions can coexist for comparison
- You always know which taxonomy version generated your results

---

## Dependencies

- **bash** (for download script)
- **curl** or **wget** (for NCBI download)
- **Python 3.8+** (for phyloname generation)
- No external Python packages required (uses standard library only)

---

## Notes

- The NCBI taxonomy database is ~2GB compressed, ~1.9GB extracted
- Full phyloname generation takes ~5-10 minutes
- Generated files are large (~250MB for all phylonames, ~700MB for full mapping)
- For most projects, you only need the small project-specific mapping file
- The rankedlineage.dmp file is the primary data source for phyloname generation
