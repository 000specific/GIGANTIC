# The GIGANTIC Phyloname System

GIGANTIC uses a standardized phylogenetic naming convention for consistent species identification across all analyses.

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

---

## Why Phylonames?

| Benefit | Description |
|---------|-------------|
| **Consistency** | Same identifier across all subprojects and analyses |
| **Hierarchy** | Programmatic access to any taxonomic level |
| **Sorting** | Alphabetical sorting groups related species together |
| **Clarity** | Immediately see taxonomic placement |
| **Self-documenting** | No external lookup needed to understand species relationships |

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

The `phylonames/output_to_input/maps/` directory contains mapping files:

### Project-Specific Mapping

```
[project]_map-genus_species_X_phylonames.tsv
```

**Format** (tab-separated):
```
genus_species	phyloname	phyloname_taxonid
Octopus_bimaculoides	Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides	Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides___37653
```

---

## Special Cases

### UNOFFICIAL Taxonomy

Some species have unofficial taxonomic placements (not yet formally described or classified). These are indicated by "UNOFFICIAL" in the phyloname:

```
Holozoa_CristidiscozoaUNOFFICIAL_Cristidiscoidea_Nucleariida_Family16247_Parvularia_atlantis
```

### Numbered Taxonomic Levels

When NCBI has no named rank for a level, a numbered placeholder is used:

```
Metazoa_Echinodermata_Echinoidea_Temnopleuroida_Toxopneustidae_Lytechinus_variegatus
      └─ Order3689 might appear for unnamed orders
```

### Multi-word Species Names

Subspecies, strains, and variants may have multi-word species names:

```
Metazoa_Mollusca_Caudofoveata_Chaetodermatida_Chaetodermatidae_Chaetoderma_sp_LZ_2023a
```

Always use `'_'.join( parts[ 6: ] )` to correctly extract these.

---

## NCBI Taxonomy Source

Phylonames are generated from the NCBI taxonomy database:
- Source: `ftp://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/`
- Primary file: `rankedlineage.dmp`
- Updated regularly by NCBI

GIGANTIC downloads the latest version and creates versioned directories:
```
database-ncbi_taxonomy_20260205_143052/
```

This ensures reproducibility - you always know which taxonomy version was used.

---

## Integration with Other Subprojects

All GIGANTIC subprojects use phylonames:

| Subproject | How Phylonames Are Used |
|------------|------------------------|
| **genomesDB** | Proteome file naming (uses `phyloname_taxonid`) |
| **trees_species** | Clade definitions and tree labels |
| **orthogroups** | Species identification in orthogroup tables |
| **annotations_hmms** | Linking annotations to species |
| **trees_gene_families** | Tree tip labels and sequence headers |
| **orthogroups_X_ocl** | Species tracking in evolutionary analyses |

The mapping file in `phylonames/output_to_input/maps/` is the authoritative source for all subprojects.

---

*For implementation details, see [subprojects/phylonames/README.md](../subprojects/phylonames/README.md)*
