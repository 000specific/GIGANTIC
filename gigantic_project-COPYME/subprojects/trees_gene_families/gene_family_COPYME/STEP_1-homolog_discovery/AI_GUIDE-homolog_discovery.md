# AI Guide: STEP_1-homolog_discovery (trees_gene_families)

**For AI Assistants**: This guide covers STEP_1 of the trees_gene_families subproject. For subproject overview, see `../AI_GUIDE-trees_gene_families.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_families/STEP_1-homolog_discovery/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| trees_gene_families concepts | `../AI_GUIDE-trees_gene_families.md` |
| STEP_1 homolog discovery concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-rbh_rbf_homologs_workflow.md` |

---

## What This Step Does

**Purpose**: Find homologous sequences across all project species using Reciprocal Best Hit / Reciprocal Best Family (RBH/RBF) BLAST.

**Pipeline Process**:

| Steps | Phase | What Happens |
|-------|-------|--------------|
| 001 | Validate RGS | Validate RGS FASTA file format (fails fast if invalid) |
| 002-003 | Forward BLAST | BLAST RGS against all project species databases |
| 004 | Extract BGS | Extract blast gene sequences from BLAST hits |
| 005-006 | RGS Genome BLAST | BLAST RGS against source organism genomes |
| 007-010 | Reciprocal Setup | Map RGS to genomes, create modified BLAST databases |
| 011-012 | Reciprocal BLAST | BLAST candidates back against RGS+genome databases |
| 013 | Extract CGS | Extract candidate gene sequences confirmed by reciprocal BLAST |
| 014 | Species Filter | Keep only species in the keeper list |
| 016 | Create AGS | Concatenate RGS + filtered CGS into final All Gene Set |
| 017 | Run Log | Write pipeline execution summary |
| 018 | Restore Full-Length RGS | Conditional: when `rgs_sequence_is_full_length` is `false`, swaps subsequence RGS back to full-length in AGS |

**Note**: BLAST v5 databases preserve full GIGANTIC identifiers, so no identifier remapping step (015) is needed.

---

## Critical Technical Details

### BLAST v5 Preserves Full Identifiers

BLAST v5 databases preserve full GIGANTIC phyloname identifiers (the old 50-character truncation issue is resolved). No identifier remapping step is needed.

### Full-Length vs Subsequence RGS Mode

The pipeline supports two RGS modes, controlled by three config fields in `START_HERE-user_config.yaml`:

```yaml
gene_family:
  rgs_full_length_file: "INPUT_user/rgs_full_length.aa"         # ALWAYS required
  rgs_sequence_is_full_length: true                              # true (default) or false
  rgs_subsequence_file: "INPUT_user/rgs_pore_region.aa"          # Required when false
```

**Full-length mode** ( `rgs_sequence_is_full_length: true` ):
- `rgs_full_length_file` is used for BLAST discovery
- Reciprocal BLAST uses full-length BGS ( `fullseqs` from Script 004 )
- Script 018 does NOT run
- This is the default for 7 of 8 sono gene families

**Subsequence mode** ( `rgs_sequence_is_full_length: false` ):
- `rgs_subsequence_file` is used for BLAST discovery (e.g., TRP pore-region-only sequences)
- Reciprocal BLAST uses hit-region subsequences ( `hitregions` from Script 004 ) instead of full-length BGS — this prevents BLAST from preferring full-length genome proteins over the shorter RGS sequences spliced into modified genomes
- Script 018 runs after Script 016: replaces subsequence RGS in the AGS with full-length versions from `rgs_full_length_file`
- Script 018 output goes to `18-output/` and is also copied back to `16-output/` so STEP_2 picks up the restored AGS

**Why subsequence mode exists**: Full-length TRP channel sequences contain ankyrin repeats and other conserved domains that dominate BLAST results, pulling in thousands of unrelated proteins. Using pore-region-only sequences as RGS seeds finds true TRP homologs cleanly.

**Subsequence RGS header convention**: Headers in the subsequence file must match the full-length file exactly, with `_subsequence` appended:
```
Full-length:   >rgs_channel-human-TRPV1-uniprot-Q8NER1
Subsequence:   >rgs_channel-human-TRPV1-uniprot-Q8NER1_subsequence
```

### BGS Extraction: Two Sequence Versions

Script 004 extracts **two** versions of candidate sequences:
- `fullseqs` - Complete protein sequences (used for reciprocal BLAST in full-length mode)
- `hitregions` - Only the BLAST hit regions (used for reciprocal BLAST in subsequence mode)

The reciprocal BLAST mode is determined by `rgs_sequence_is_full_length`:
- `true`: reciprocal BLAST uses `fullseqs`
- `false`: reciprocal BLAST uses `hitregions`

### No --parse_seqids in makeblastdb

BLAST databases are built WITHOUT the `--parse_seqids` flag because GIGANTIC phylonames contain characters that confuse BLAST's ID parser.

---

## Inputs Required

| Input | Location | User Provides? |
|-------|----------|----------------|
| RGS FASTA (full-length) | `INPUT_user/<rgs_full_length_file>.aa` | **YES** (always required) |
| RGS FASTA (subsequence) | `INPUT_user/<rgs_subsequence_file>.aa` | **YES** (only when `rgs_sequence_is_full_length: false`) |
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
├── 16-output/   # Final AGS (All Gene Set)
└── 18-output/   # Full-length-restored AGS (only when rgs_sequence_is_full_length is false)
```

### output_to_input

| Level | Path |
|-------|------|
| Subproject-root | `../../output_to_input/<gene_family>/STEP_1-homolog_discovery/` (symlinks to OUTPUT_pipeline/) |

---

## Directory Structure

```
STEP_1-homolog_discovery/
├── AI_GUIDE-homolog_discovery.md      # THIS FILE
├── README.md
└── workflow-COPYME-rbh_rbf_homologs/
# Note: output symlinked to ../../output_to_input/<gene_family>/STEP_1-homolog_discovery/
    ├── README.md
    ├── RUN-workflow.sh
    ├── START_HERE-user_config.yaml
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
            ├── 001_ai-python-validate_rgs.py
            ├── 002_ai-python-generate_blastp_commands-project_database.py
            ├── 004_ai-python-extract_gene_set_sequences.py
            ├── 005_ai-python-generate_blastp_commands-rgs_genomes.py
            ├── 007_ai-python-list_rgs_blast_files.py
            ├── 008_ai-python-map_rgs_to_reference_genomes.py
            ├── 009_ai-python-create_modified_genomes.py
            ├── 010_ai-python-generate_makeblastdb_commands.py
            ├── 011_ai-python-generate_reciprocal_blast_commands.py
            ├── 012_ai-bash-execute_reciprocal_blast.sh
            ├── 013_ai-python-extract_reciprocal_best_hits.py
            ├── 014_ai-python-filter_species_for_tree_building.py
            ├── 016_ai-python-concatenate_sequences.py
            ├── 017_ai-python-write_run_log.py
            └── 018_ai-python-restore_full_length_rgs_sequences.py  # Conditional: subsequence mode only
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/START_HERE-user_config.yaml` | Gene family, BLAST settings, database paths, RGS mode ( `rgs_sequence_is_full_length`, `rgs_full_length_file`, `rgs_subsequence_file` ) | **YES** |
| `workflow-*/INPUT_user/species_keeper_list.tsv` | Species to keep in final AGS | **YES** |
| `workflow-*/INPUT_user/rgs_species_map.tsv` | Map short names to Genus_species | **YES** (if needed) |
| `workflow-*/INPUT_user/*.aa` | RGS FASTA file | **YES** |
| `../../output_to_input/<gene_family>/STEP_1-homolog_discovery/` | Final AGS files | No (auto-created symlinks) |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "BLAST database not found" | genomesDB not complete | Run genomesDB STEP_2 first |
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
| Starting STEP_1 | "Do you have your RGS FASTA file and species keeper list ready?" |
| Gene family with conserved domains that cause false positives | "Should we use subsequence mode? Set `rgs_sequence_is_full_length: false` and provide a subsequence RGS file with only the discriminating domain." |
| Subsequence mode | "Do you have BOTH the full-length and subsequence RGS files? Headers must match exactly, with `_subsequence` appended in the subsequence file." |
| Few BLAST hits | "What E-value are you using? The default 1e-3 works for most families." |
| Species missing | "Is the species in your keeper list? And is its proteome in genomesDB?" |
| Large gene family | "How many RGS sequences? Large families (>50 sequences) may need more BLAST threads." |
