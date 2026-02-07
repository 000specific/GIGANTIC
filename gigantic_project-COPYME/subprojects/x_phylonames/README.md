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

## Numbered Unknown Clades (Kingdom6555, Family1426, etc.)

### What Are Numbered Clades?

NCBI Taxonomy is **incomplete** and represents **one hypothesis** among many about phylogenetic relationships. When NCBI lacks data for a taxonomic level, GIGANTIC generates **numbered unknown clade identifiers**.

**Example**:
```
Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

Here, `Kingdom6555` and `Phylum6554` are **not NCBI assignments** - they are GIGANTIC's solution to fill gaps while preserving phylogenetic information.

### Why This Matters

**The numbering captures shared ancestry**: All species sharing the same "first named clade below" an unknown level get the same number. This groups related species together despite missing higher taxonomy.

**Example**: All choanoflagellates might share `Kingdom6555` and `Phylum6554` because they all have "Choanoflagellata" as their first named clade below those levels.

### CRITICAL LIMITATION: Clade Splitting Artifact

When a single unknown higher-level clade actually contains **multiple** lower-level clades, GIGANTIC's numbering will **split** the real clade into multiple numbered clades (one per each lower-level clade).

**Example Scenario**:
If one unknown Kingdom actually contains Phyla A, B, and C, GIGANTIC creates:
- `Kingdom1` (for species in Phylum A)
- `Kingdom2` (for species in Phylum B)
- `Kingdom3` (for species in Phylum C)

But in reality, all belong to the **SAME** unknown Kingdom.

**Impact on Analyses**:
- If your species set includes species from **only ONE** lower-level clade → **NO PROBLEM**
- If your species set includes species from **MULTIPLE** lower-level clades that share an unknown higher clade → **PROBLEM**: OCL (Origins, Conservation, Loss) analyses will cryptically fail to capture accurate evolutionary patterns

**Solution**: If you know the correct higher-level clade names from literature, use the **user-provided phylonames** feature (see below).

---

## User-Provided Phylonames (Custom Taxonomy)

### Overview

GIGANTIC allows you to override NCBI-generated phylonames with your own taxonomy based on current literature or alternative phylogenetic hypotheses.

### Configuration

In `phylonames_config.yaml`:

```yaml
project:
  # Path to your custom phylonames file
  user_phylonames: "INPUT_user/user_phylonames.tsv"

  # Whether to mark user clades as UNOFFICIAL (default: true)
  mark_unofficial: true
```

### Input Format

Create a TSV file with two columns:
```
genus_species	custom_phyloname
Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

### UNOFFICIAL Suffix

By default, clades that **DIFFER** from the NCBI-derived phyloname are marked with `UNOFFICIAL`:

```
NCBI output:    Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
User provides:  Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
Final output:   HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

Only `Holozoa` and `Choanozoa` get marked UNOFFICIAL because they replaced the numbered clades. `Choanoflagellata`, `Craspedida`, and `Salpingoecidae` remain unmarked because they match the NCBI-derived values.

**Why UNOFFICIAL?**
- Assigning a clade to a species is a **taxonomic DECISION**
- NCBI made their official decision
- When you override specific clades, **those overrides are "unofficial"**
- Clades that match NCBI's assignment remain official (unmarked)
- The UNOFFICIAL suffix maintains transparency about which assignments came from the user

**To disable** (if you want clean phylonames without any UNOFFICIAL markers):
```yaml
mark_unofficial: false
```

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
├── AI_GUIDE-phylonames.md              # AI assistant guidance (subproject level)
├── user_research/                      # Personal workspace
├── output_to_input/                    # Outputs for downstream subprojects
│   └── maps/                           # Species mapping files
│       └── [project]_map-genus_species_X_phylonames.tsv
└── nf_workflow-COPYME_01-generate_phylonames/
    ├── README.md                       # Quick start guide
    ├── RUN_phylonames.sh               # bash RUN_phylonames.sh (local)
    ├── RUN_phylonames.sbatch           # sbatch RUN_phylonames.sbatch (SLURM)
    ├── phylonames_config.yaml          # Edit this for your project
    ├── INPUT_user/                     # User-provided species list
    │   └── species_list.txt            # One genus_species per line
    ├── OUTPUT_pipeline/                # Generated phylonames and mappings
    └── ai/                             # Internal (don't touch)
        ├── AI_GUIDE-phylonames_workflow.md  # For AI assistants
        ├── main.nf                     # NextFlow pipeline
        ├── nextflow.config             # NextFlow settings
        └── scripts/                    # Python/Bash scripts
            ├── 001_ai-bash-download_ncbi_taxonomy.sh
            ├── 002_ai-python-generate_phylonames.py
            ├── 003_ai-python-create_species_mapping.py
            └── 004_ai-python-apply_user_phylonames.py
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
cd nf_workflow-COPYME_01-generate_phylonames

# Local machine:
bash RUN_phylonames.sh

# SLURM cluster (edit account/qos first):
sbatch RUN_phylonames.sbatch
```

The pipeline will:
1. Download NCBI taxonomy database (~2GB, skipped if already exists)
2. Generate phylonames for all NCBI species (~5-10 minutes)
3. Create your project-specific mapping file
4. **(Optional)** Apply user-provided phylonames if specified in config

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

### User Phylonames Output (Optional)

**Location**: `OUTPUT_pipeline/output/4-output/` (only if `user_phylonames` is specified)

| File | Description |
|------|-------------|
| `final_project_mapping.tsv` | Species mapping with user phylonames applied |
| `unofficial_clades_report.tsv` | Report of which clades were marked UNOFFICIAL |

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
