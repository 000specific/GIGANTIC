# The GIGANTIC Phyloname System

GIGANTIC uses a standardized phylogenetic naming convention for consistent species identification across all analyses.

---

## Phyloname Format

```
Kingdom_Phylum_Class_Order_Family_Genus_species
```

### Example

```
Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides
```

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

## Extracting Taxonomic Levels

In Python:

```python
phyloname = 'Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides'
parts = phyloname.split('_')

kingdom = parts[0]      # Metazoa
phylum = parts[1]       # Mollusca
genus = parts[5]        # Octopus
species = '_'.join(parts[6:])  # bimaculoides (handles multi-word species)

genus_species = f"{genus}_{species}"  # Octopus_bimaculoides
```

## Why Phylonames?

1. **Consistency**: Same identifier across all subprojects and analyses
2. **Hierarchy**: Programmatic access to any taxonomic level
3. **Sorting**: Alphabetical sorting groups related species together
4. **Clarity**: Immediately see taxonomic placement

## Proteome File Naming

Proteome files follow this extended convention:

```
phyloname___ncbi_taxonomy_id-genome_assembly_id-download_date-data_type.aa
```

### Example

```
Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides___37653-ncbi_GCF_001194135.2-downloaded_20241011-gene_models_T1.aa
```

## Mapping Files

The `phylonames/output_to_input/maps/` directory contains mapping files:

- `species_map-genus_species_X_phylonames.tsv` - Bidirectional mapping between short names and full phylonames

## Special Cases

- **UNOFFICIAL** in taxonomy: Some species have unofficial taxonomic placements, indicated by "UNOFFICIAL" in the phyloname
- **Multi-word species names**: Handled by using `parts[6:]` with join

---

*Documentation under development. Check back for updates.*
