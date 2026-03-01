# AI Guide: STEP_2-homolog_discovery (trees_gene_groups)

**For AI Assistants**: This guide covers STEP_2 of the trees_gene_groups subproject. For subproject overview, see `../AI_GUIDE-trees_gene_groups.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/STEP_2-homolog_discovery/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| trees_gene_groups concepts | `../AI_GUIDE-trees_gene_groups.md` |
| STEP_2 homolog discovery concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-rbh_rbf_homologs_workflow.md` |

---

## What This Step Does

**Purpose**: Find homologous sequences across all project species using Reciprocal Best Hit / Reciprocal Best Family (RBH/RBF) BLAST.

**16-Step Process**:

| Steps | Phase | What Happens |
|-------|-------|--------------|
| 001-003 | Forward BLAST | BLAST RGS against all project species databases |
| 004 | Extract BGS | Extract blast gene sequences from BLAST hits |
| 005-006 | RGS Genome BLAST | BLAST RGS against source organism genomes |
| 007-010 | Reciprocal Setup | Map RGS to genomes, create modified BLAST databases |
| 011-012 | Reciprocal BLAST | BLAST candidates back against RGS+genome databases |
| 013 | Extract CGS | Extract candidate gene sequences confirmed by reciprocal BLAST |
| 014 | Species Filter | Keep only species in the keeper list |
| 015 | Remap IDs | Convert short BLAST IDs back to full GIGANTIC phylonames |
| 016 | Create AGS | Concatenate RGS + filtered CGS into final All Gene Set |

---

## Critical Technical Details

### Short Identifier Mapping (BLAST 50-Character Limit)

BLAST truncates sequence identifiers at 50 characters. GIGANTIC phylonames exceed this limit. The pipeline:
1. Uses truncated IDs during BLAST (scripts 001-013)
2. Remaps to full GIGANTIC phylonames at the end (script 015)
3. Requires the CGS mapping file from genomesDB

### Full-Length Sequences for Reciprocal BLAST

Script 004 extracts **two** versions of candidate sequences:
- `fullseqs` - Complete protein sequences (used for reciprocal BLAST)
- `hitregions` - Only the BLAST hit regions (not used for reciprocal)

The reciprocal BLAST (scripts 011-012) uses `fullseqs` to ensure accurate best-hit determination.

### No --parse_seqids in makeblastdb

BLAST databases are built WITHOUT the `--parse_seqids` flag because GIGANTIC phylonames contain characters that confuse BLAST's ID parser.

---

## Inputs Required

| Input | Location | User Provides? |
|-------|----------|----------------|
| RGS FASTA | `INPUT_user/<rgs_file>.aa` | **YES** |
| Species keeper list | `INPUT_user/species_keeper_list.tsv` | **YES** |
| RGS species map | `INPUT_user/rgs_species_map.tsv` | If RGS uses short names |
| BLAST databases | `../../../../genomesDB/output_to_input/gigantic_T1_blastp/` | No (from genomesDB) |
| CGS header mapping | `../../../../genomesDB/output_to_input/gigantic_T1_blastp_header_map` | No (from genomesDB) |

---

## Outputs

### Pipeline Outputs

16 numbered output directories in `OUTPUT_pipeline/`:

```
OUTPUT_pipeline/
├── 1-output/    # BLAST database list
├── 2-output/    # Forward BLAST commands
├── 3-output/    # Forward BLAST results
├── 4-output/    # BGS extracted sequences (fullseqs + hitregions)
├── 5-output/    # RGS genome BLAST commands
├── 6-output/    # RGS genome BLAST results
├── 7-output/    # RGS BLAST file list
├── 8-output/    # RGS-to-genome ID mapping
├── 9-output/    # Modified genomes for reciprocal BLAST
├── 10-output/   # Combined BLAST database
├── 11-output/   # Reciprocal BLAST commands
├── 12-output/   # Reciprocal BLAST results
├── 13-output/   # CGS filtered sequences
├── 14-output/   # Species-filtered sequences
├── 15-output/   # Remapped to GIGANTIC phylonames
└── 16-output/   # Final AGS (All Gene Set)
```

### output_to_input

| Level | Path |
|-------|------|
| STEP-level | `output_to_input/ags_fastas/<gene_group>/16_ai-ags-*.aa` |
| Subproject-level | `../output_to_input/step_2/ags_fastas/<gene_group>/16_ai-ags-*.aa` |

---

## Directory Structure

```
STEP_2-homolog_discovery/
├── AI_GUIDE-homolog_discovery.md      # THIS FILE
├── README.md
├── output_to_input/
│   └── ags_fastas/                    # Final AGS by gene group
└── workflow-COPYME-rbh_rbf_homologs/
    ├── README.md
    ├── RUN-workflow.sh
    ├── RUN-workflow.sbatch
    ├── rbh_rbf_homologs_config.yaml
    ├── INPUT_user/
    │   ├── species_keeper_list.tsv
    │   ├── rgs_species_map.tsv
    │   └── [rgs FASTA files]
    ├── OUTPUT_pipeline/
    │   └── 1-output/ through 16-output/
    └── ai/
        ├── AI_GUIDE-rbh_rbf_homologs_workflow.md
        ├── main.nf
        ├── nextflow.config
        └── scripts/
            ├── 001_ai-python-setup_block_directories.py
            ├── 002_ai-python-generate_blastp_commands-project_database.py
            ├── 004_ai-python-extract_gene_set_sequences.py
            ├── ...
            └── 016_ai-python-concatenate_sequences.py
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/rbh_rbf_homologs_config.yaml` | Gene group, BLAST settings, database paths | **YES** |
| `workflow-*/INPUT_user/species_keeper_list.tsv` | Species to keep in final AGS | **YES** |
| `workflow-*/INPUT_user/rgs_species_map.tsv` | Map short names to Genus_species | **YES** (if needed) |
| `workflow-*/INPUT_user/*.aa` | RGS FASTA file | **YES** |
| `output_to_input/ags_fastas/` | Final AGS files | No (auto-created) |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "BLAST database not found" | genomesDB not complete | Run genomesDB STEP_3 first |
| "No BLAST hits" | E-value too stringent or wrong RGS | Try `1e-2` or check RGS sequences |
| "CGS mapping file not found" | Header map missing from genomesDB | Check `genomesDB/output_to_input/gigantic_T1_blastp_header_map` |
| "Species not in keeper list" | Species filtered out | Add to species_keeper_list.tsv |
| AGS has very few sequences | Too-strict filtering | Check each step's output counts |
| "RGS species not found in genomes" | RGS species map wrong | Check rgs_species_map.tsv |
| Reciprocal BLAST finds nothing | Modified genomes empty | Check scripts 008-010 output |

### Diagnostic Commands

```bash
# Check forward BLAST results
wc -l OUTPUT_pipeline/3-output/*.blastp

# Check BGS sequence counts
grep -c ">" OUTPUT_pipeline/4-output/*fullseqs*

# Check reciprocal BLAST results
wc -l OUTPUT_pipeline/12-output/*.blastp

# Check CGS sequence counts
grep -c ">" OUTPUT_pipeline/13-output/*.aa

# Check species filter results
grep -c ">" OUTPUT_pipeline/14-output/*.aa

# Check final AGS
grep -c ">" OUTPUT_pipeline/16-output/*.aa
```

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting STEP_2 | "Do you have your RGS FASTA file and species keeper list ready?" |
| Few BLAST hits | "What E-value are you using? The default 1e-3 works for most families." |
| Species missing | "Is the species in your keeper list? And is its proteome in genomesDB?" |
| Large gene group | "How many RGS sequences? Large groups (>50 sequences) may need more BLAST threads." |
