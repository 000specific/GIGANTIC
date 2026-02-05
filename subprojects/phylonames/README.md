# phylonames - GIGANTIC Phylogenetic Naming System

## Purpose

Generate and manage standardized phylogenetic names (phylonames) for all species in your study. Phylonames encode the full taxonomic hierarchy of each species, enabling consistent identification and programmatic extraction of any taxonomic level.

## Phyloname Format

```
Kingdom_Phylum_Class_Order_Family_Genus_species
```

Example:
```
Metazoa_Mollusca_Gastropoda_Aplysiomorpha_Aplysiidae_Aplysia_californica
```

## Field Positions (0-indexed)

| Position | Level | Example |
|----------|-------|---------|
| [0] | Kingdom | Metazoa |
| [1] | Phylum | Mollusca |
| [2] | Class | Gastropoda |
| [3] | Order | Aplysiomorpha |
| [4] | Family | Aplysiidae |
| [5] | Genus | Aplysia |
| [6:] | species | californica |

## Outputs Shared Downstream (`output_to_input/`)

- `maps/species_map-genus_species_X_phylonames.tsv` - Bidirectional mapping between short names and full phylonames

## Scripts

- `scripts/generate_phylonames.py` - Create phylonames from NCBI taxonomy
- `scripts/validate_phylonames.py` - Validate phyloname format and completeness

## Usage

1. Prepare a list of your species with NCBI taxonomy IDs
2. Run the phyloname generation script
3. Review and correct any taxonomic assignments
4. Export the mapping file to `output_to_input/maps/`
