# INPUT_gigantic - Project-Wide Input Files

This directory contains **project-wide input files** that are shared across multiple GIGANTIC subprojects.

## Why This Directory Exists

Many GIGANTIC subprojects need the same core information:
- **Species list** - which organisms are in your study
- **Major clades** - focal taxonomic groups for OCL analyses (optional)
- Other project-level constants

Rather than duplicating this information in every subproject's `INPUT_user/` directory, we maintain a single source of truth here.

## How It Works

1. **You edit files here** (the canonical source)
2. **Subproject RUN scripts copy** relevant files to their `INPUT_user/` directories
3. **Each workflow run has its own archived copy** for reproducibility

This gives you:
- Single place to update project-wide settings
- Complete archival record in each workflow run
- No sync issues between subprojects

## Files in This Directory

| File | Purpose | Used By |
|------|---------|---------|
| `species_list.txt` | Your project species | phylonames, genomesDB, orthogroups, ... |

## Quick Start

1. Edit `species_list.txt` with your species (one per line, `Genus_species` format)
2. Run the phylonames subproject first:
   ```bash
   cd subprojects/phylonames/workflow-COPYME-generate_phylonames/
   bash RUN-phylonames.sh
   ```
3. The RUN script will automatically copy your species list for archival

## Notes

- Always use `Genus_species` format (underscore between genus and species)
- Use official NCBI scientific names for best results
- Lines starting with `#` are comments and will be ignored
