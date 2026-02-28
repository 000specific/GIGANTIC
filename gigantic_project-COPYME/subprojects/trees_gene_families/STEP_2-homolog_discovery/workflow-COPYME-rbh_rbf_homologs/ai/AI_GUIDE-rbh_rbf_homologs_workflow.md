# AI Guide: RBH/RBF Homolog Discovery Workflow

**For AI Assistants**: This guide covers workflow execution. For STEP_2 concepts, see `../../AI_GUIDE-homolog_discovery.md`. For trees_gene_families overview, see `../../../AI_GUIDE-trees_gene_families.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `trees_gene_families/STEP_2-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE-project.md` |
| trees_gene_families concepts | `../../../AI_GUIDE-trees_gene_families.md` |
| STEP_2 homolog concepts | `../../AI_GUIDE-homolog_discovery.md` |
| Running the workflow | This file |

---

## Architecture: 16 Steps, 10 NextFlow Processes

The 16-step pipeline is organized into 10 NextFlow processes for efficiency:

```
workflow-COPYME-rbh_rbf_homologs/
│
├── README.md
├── RUN-rbh_rbf_homologs.sh         # Local: bash RUN-rbh_rbf_homologs.sh
├── RUN-rbh_rbf_homologs.sbatch     # SLURM: sbatch RUN-rbh_rbf_homologs.sbatch
├── rbh_rbf_homologs_config.yaml    # User configuration
│
├── INPUT_user/
│   ├── species_keeper_list.tsv     # One Genus_species per line (required)
│   ├── rgs_species_map.tsv         # Short → Genus_species mapping (if needed)
│   └── [rgs FASTA file]            # Reference Gene Set (required)
│
├── OUTPUT_pipeline/
│   ├── 1-output/   through 16-output/   # All 16 step outputs
│
└── ai/
    ├── AI_GUIDE-rbh_rbf_homologs_workflow.md  # THIS FILE
    ├── main.nf
    ├── nextflow.config
    └── scripts/
        ├── 001_ai-python-setup_block_directories.py
        ├── 002_ai-python-generate_blastp_commands-project_database.py
        ├── 004_ai-python-extract_gene_set_sequences.py
        ├── 005_ai-python-generate_blastp_commands-rgs_genomes.py
        ├── 007_ai-python-list_rgs_blast_files.py
        ├── 008_ai-python-map_rgs_to_reference_genomes.py
        ├── 009_ai-python-create_modified_genomes.py
        ├── 010_ai-python-generate_makeblastdb_commands.py
        ├── 011_ai-python-generate_reciprocal_blast_commands.py
        ├── 013_ai-python-extract_reciprocal_best_hits.py
        ├── 014_ai-python-filter_species_for_tree_building.py
        ├── 015_ai-python-remap_cgs_identifiers_to_gigantic.py
        └── 016_ai-python-concatenate_sequences.py
```

### Script Pipeline (16 Steps)

| Step | Script | NextFlow Process | Does |
|------|--------|-----------------|------|
| 001 | 001_ai-python | setup_and_list_databases | List BLAST databases |
| 002 | 002_ai-python | generate_and_run_forward_blast | Generate forward BLAST commands |
| 003 | (bash) | generate_and_run_forward_blast | Execute forward BLAST |
| 004 | 004_ai-python | extract_cgs_sequences | Extract CGS (fullseqs + hitregions) |
| 005 | 005_ai-python | generate_and_run_rgs_blast | Generate RGS genome BLAST commands |
| 006 | (bash) | generate_and_run_rgs_blast | Execute RGS genome BLAST |
| 007 | 007_ai-python | map_rgs_and_build_reciprocal_db | List RGS BLAST files |
| 008 | 008_ai-python | map_rgs_and_build_reciprocal_db | Map RGS to genome IDs |
| 009 | 009_ai-python | map_rgs_and_build_reciprocal_db | Create modified genomes |
| 010 | 010_ai-python | map_rgs_and_build_reciprocal_db | Build combined BLAST DB |
| 011 | 011_ai-python | run_reciprocal_blast | Generate reciprocal BLAST commands |
| 012 | (bash) | run_reciprocal_blast | Execute reciprocal BLAST |
| 013 | 013_ai-python | extract_rbf_sequences | Extract RBF sequences |
| 014 | 014_ai-python | filter_species | Filter by keeper list |
| 015 | 015_ai-python | remap_identifiers | Remap to GIGANTIC phylonames |
| 016 | 016_ai-python | create_ags_and_export | Create final AGS |

---

## User Workflow

### Step 1: Copy Template

```bash
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
cd workflow-RUN_01-rbh_rbf_homologs/
```

### Step 2: Configure

Edit `rbh_rbf_homologs_config.yaml`:
```yaml
gene_family:
  name: "innexin_pannexin"
  rgs_file: "INPUT_user/rgs3-innexin_pannexin-uniprot-2025november01.aa"

inputs:
  species_keeper_list: "INPUT_user/species_keeper_list.tsv"
  blast_databases_dir: "../../../../genomesDB/output_to_input/gigantic_T1_blastp"
  cgs_mapping_file: "../../../../genomesDB/output_to_input/gigantic_T1_blastp_header_map"

project:
  database: "species67_T1-species67"

blast:
  evalue: "1e-3"
  threads: 50
```

### Step 3: Place Input Files

```bash
# Copy RGS file
cp /path/to/rgs.aa INPUT_user/

# Create species keeper list (one Genus_species per line)
# Example:
echo "Homo_sapiens" > INPUT_user/species_keeper_list.tsv
echo "Mus_musculus" >> INPUT_user/species_keeper_list.tsv
echo "Drosophila_melanogaster" >> INPUT_user/species_keeper_list.tsv

# Optional: RGS species map (if headers use short names)
```

### Step 4: Run

**Local**:
```bash
bash RUN-rbh_rbf_homologs.sh
```

**SLURM** (edit account/qos first):
```bash
sbatch RUN-rbh_rbf_homologs.sbatch
```

---

## SLURM Execution Details

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | `YOUR_ACCOUNT` | **Must edit** |
| `--qos` | `YOUR_QOS` | **Must edit** |
| `--cpus-per-task` | `50` | Matches BLAST threads |
| `--mem` | `100gb` | BLAST can be memory-intensive |
| `--time` | `48:00:00` | Depends on species count |

---

## Expected Runtime

| Scenario | Duration |
|----------|----------|
| 10 species, small RGS | 30 minutes - 1 hour |
| 67 species, medium RGS | 4-12 hours |
| 67 species, large RGS (>50 seqs) | 12-48 hours |

Runtime depends on species count, RGS size, and BLAST threads.

---

## Verification Commands

```bash
# Check each step completed
for i in $(seq 1 16); do
    echo "Step $i: $(ls OUTPUT_pipeline/${i}-output/ 2>/dev/null | wc -l) files"
done

# Check forward BLAST found hits
wc -l OUTPUT_pipeline/3-output/*.blastp 2>/dev/null

# Check CGS extraction
grep -c ">" OUTPUT_pipeline/4-output/*fullseqs* 2>/dev/null

# Check reciprocal BLAST
wc -l OUTPUT_pipeline/12-output/*.blastp 2>/dev/null

# Check RBF filtering
grep -c ">" OUTPUT_pipeline/13-output/*.aa 2>/dev/null

# Check species filtering
grep -c ">" OUTPUT_pipeline/14-output/*.aa 2>/dev/null

# Check final AGS
grep -c ">" OUTPUT_pipeline/16-output/*.aa 2>/dev/null

# Verify output_to_input
ls ../../output_to_input/ags_fastas/*/
```

---

## Troubleshooting

### "BLAST database not found"

**Cause**: genomesDB output_to_input path incorrect

**Diagnose**:
```bash
ls ../../../../genomesDB/output_to_input/gigantic_T1_blastp/ | head
```

**Fix**: Update `blast_databases_dir` in config YAML.

### Forward BLAST produces no hits

**Cause**: E-value too stringent or wrong RGS

**Diagnose**:
```bash
cat OUTPUT_pipeline/3-output/*.blastp | head -20
```

**Fix**: Try less stringent E-value (e.g., `1e-2`), or verify RGS contains correct protein sequences.

### CGS mapping file not found

**Cause**: genomesDB header map missing

**Diagnose**:
```bash
ls ../../../../genomesDB/output_to_input/gigantic_T1_blastp_header_map
```

**Fix**: Run genomesDB STEP_2 or STEP_3 to generate header mapping file.

### Very few species in final AGS

**Cause**: Strict filtering at multiple steps

**Diagnose**:
```bash
# Check counts at each filter step
echo "CGS:"; grep -c ">" OUTPUT_pipeline/4-output/*fullseqs*
echo "RBF:"; grep -c ">" OUTPUT_pipeline/13-output/*.aa
echo "Species filter:"; grep -c ">" OUTPUT_pipeline/14-output/*.aa
echo "Final AGS:"; grep -c ">" OUTPUT_pipeline/16-output/*.aa
```

**Fix**: Check species keeper list includes desired species, and verify those species are in genomesDB.

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-rbh_rbf_homologs.sh
```

---

## After Successful Run

1. **Verify**: Check final AGS has expected sequence count
2. **Check output_to_input**: `ls ../../output_to_input/ags_fastas/`
3. **Next step**: Proceed to STEP_3 phylogenetic analysis
