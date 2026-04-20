# AI Guide: RBH/RBF Homolog Discovery Workflow

**For AI Assistants**: This guide covers workflow execution. For STEP_1 concepts, see `../../AI_GUIDE-homolog_discovery.md`. For trees_gene_families overview, see `../../../AI_GUIDE-trees_gene_families.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `trees_gene_families/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/`

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
| STEP_1 homolog concepts | `../../AI_GUIDE-homolog_discovery.md` |
| Running the workflow | This file |

---

## Architecture: 16 Steps, 10 NextFlow Processes

The 16-step pipeline is organized into 10 NextFlow processes for efficiency:

```
workflow-COPYME-rbh_rbf_homologs/
│
├── README.md
├── RUN-workflow.sh         # Runner: bash RUN-workflow.sh (handles local + SLURM via config)
├── START_HERE-user_config.yaml    # User configuration (includes execution_mode, SLURM settings)
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
        └── 018_ai-python-restore_full_length_rgs_sequences.py  # Only runs in subsequence mode
```

### Script Pipeline (16 Steps)

| Step | Script | NextFlow Process | Does |
|------|--------|-----------------|------|
| 001 | 001_ai-python | validate_rgs | Validate RGS FASTA file |
| 002 | 002_ai-python | generate_and_run_forward_blast | Generate forward BLAST commands |
| 003 | (bash) | generate_and_run_forward_blast | Execute forward BLAST |
| 004 | 004_ai-python | extract_bgs_sequences | Extract BGS (fullseqs + hitregions) |
| 005 | 005_ai-python | generate_and_run_rgs_blast | Generate RGS genome BLAST commands |
| 006 | (bash) | generate_and_run_rgs_blast | Execute RGS genome BLAST |
| 007 | 007_ai-python | map_rgs_and_build_reciprocal_db | List RGS BLAST files |
| 008 | 008_ai-python | map_rgs_and_build_reciprocal_db | Map RGS to genome IDs |
| 009 | 009_ai-python | map_rgs_and_build_reciprocal_db | Create modified genomes |
| 010 | 010_ai-python | map_rgs_and_build_reciprocal_db | Build combined BLAST DB |
| 011 | 011_ai-python | run_reciprocal_blast | Generate reciprocal BLAST commands |
| 012 | (bash) | run_reciprocal_blast | Execute reciprocal BLAST |
| 013 | 013_ai-python | extract_cgs_sequences | Extract CGS sequences |
| 014 | 014_ai-python | filter_species | Filter by keeper list |
| 016 | 016_ai-python | create_ags_and_export | Create final AGS |
| 017 | 017_ai-python | write_run_log | Write pipeline execution summary |
| 018 | 018_ai-python | restore_full_length_rgs | Restore full-length RGS in AGS — **conditional: only runs when `rgs_sequence_is_full_length: false`** |

---

## RGS Modes: Full-length vs Subsequence

The workflow supports two RGS input modes controlled by `rgs_sequence_is_full_length` in the config.

### Full-length mode (DEFAULT — use for most gene families/groups)

```yaml
gene_family:
  rgs_full_length_file: "INPUT_user/rgs.aa"
  rgs_sequence_is_full_length: true
  # rgs_subsequence_file: <unset / commented out>
```

- RGS sequences ARE the full-length proteins
- Pipeline uses `rgs_full_length_file` directly for BLAST discovery
- Script 018 is **cleanly skipped** by `main.nf` conditional (`if ( !params.rgs_sequence_is_full_length )`)
- `rgs_subsequence_file` is not required and should NOT be set
- Final AGS from Script 016 is authoritative

### Subsequence mode (use ONLY when RGS seeds are domain fragments)

```yaml
gene_family:
  rgs_full_length_file: "INPUT_user/rgs_full_length.aa"
  rgs_sequence_is_full_length: false
  rgs_subsequence_file: "INPUT_user/rgs_subsequence.aa"
```

- RGS subsequences (e.g., TRP pore regions) used for BLAST discovery
- Full-length file required for restoring full sequences in the final AGS
- Subsequence file headers must match full-length file headers exactly, with `_subsequence` appended
- Script 018 runs after Script 016 to strip `_subsequence` suffix and swap subsequence sequences for full-length ones
- Startup validation in `main.nf` line ~708 enforces `rgs_subsequence_file` presence when `rgs_sequence_is_full_length: false`

### Anti-pattern: do NOT pass the same file as both inputs

Passing `rgs_full_length_file` and `rgs_subsequence_file` as the same file to bypass validation is incorrect. It invokes Script 018 unnecessarily and risks subtle header mismatches. The correct path for standard gene families is: leave `rgs_sequence_is_full_length: true` (default) and omit `rgs_subsequence_file` entirely.

---

## Orphan RGS

Controlled by `include_orphan_rgs` in the config. Orphan RGS are seed sequences whose source species has no genome in the BLAST database set (e.g., FLYC1 from venus flytrap, TRPC2 from mouse when mouse isn't in the species set). When enabled:

- Script 009 appends orphan RGS sequences to the combined BLAST database as reciprocal targets
- Reciprocal BLAST hits can land on orphan RGS, allowing gene assignments that would otherwise fail
- Default: `false` (conservative)

---

## Header Format — Script 013 is Format-Independent

Script 013 uses pure set membership (`hit in rgs_identifiers_set`) to validate reciprocal BLAST hits. This works with any RGS header format:

- Old format: `rgs_family-species-gene-source-id`
- New format: `rgs-source_id-family-species-gene-source`
- Truncated forms from Script 008 (45-char base + `_NNN` counter) also work

No header migration is needed when upgrading to the fixed Script 013. The critical bug the fix addresses: previous versions used positional parsing (`hit.split('-')[1]`) which silently dropped reciprocal hits when truncation eliminated the `-` delimiter in long-named families/groups, producing empty CGS files while the pipeline reported success.

---

## User Workflow

### Step 1: Copy Template

```bash
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
cd workflow-RUN_01-rbh_rbf_homologs/
```

### Step 2: Configure

Edit `START_HERE-user_config.yaml`:
```yaml
gene_family:
  name: "innexin_pannexin"
  rgs_full_length_file: "INPUT_user/rgs_channel-human_worm_fly-innexin_pannexin_channels.aa"
  rgs_sequence_is_full_length: true    # DEFAULT — Script 018 skipped
  # rgs_subsequence_file: <unset for standard full-length RGS>
  include_orphan_rgs: false

inputs:
  species_keeper_list: "INPUT_user/species_keeper_list.tsv"
  blast_databases_dir: "../../../../genomesDB/output_to_input/gigantic_T1_blastp"

project:
  database: "speciesN_T1-speciesN"

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
bash RUN-workflow.sh
```

**SLURM** (set execution_mode and SLURM settings in config first):
```bash
# In START_HERE-user_config.yaml, set:
#   execution_mode: "slurm"
#   slurm_account: "your_account"
#   slurm_qos: "your_qos"
#   cpus: 50
#   memory_gb: 187
#   time_hours: 96
bash RUN-workflow.sh
```

---

## SLURM Execution Details

All SLURM settings are configured in `START_HERE-user_config.yaml`:

| Config Key | Default | Notes |
|------------|---------|-------|
| `execution_mode` | `"local"` | Set to `"slurm"` for cluster |
| `slurm_account` | `"your_account"` | **Must edit** |
| `slurm_qos` | `"your_qos"` | **Must edit** |
| `cpus` | `50` | Matches BLAST threads |
| `memory_gb` | `187` | BLAST can be memory-intensive |
| `time_hours` | `96` | Depends on species count |

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

# Check BGS extraction
grep -c ">" OUTPUT_pipeline/4-output/*fullseqs* 2>/dev/null

# Check reciprocal BLAST
wc -l OUTPUT_pipeline/12-output/*.blastp 2>/dev/null

# Check CGS filtering
grep -c ">" OUTPUT_pipeline/13-output/*.aa 2>/dev/null

# Check species filtering
grep -c ">" OUTPUT_pipeline/14-output/*.aa 2>/dev/null

# Check final AGS
grep -c ">" OUTPUT_pipeline/16-output/*.aa 2>/dev/null

# Verify output_to_input
ls -l ../../../output_to_input/*/STEP_1-homolog_discovery/
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

**Fix**: Run genomesDB STEP_1 or STEP_2 to generate header mapping file.

### Very few species in final AGS

**Cause**: Strict filtering at multiple steps

**Diagnose**:
```bash
# Check counts at each filter step
echo "BGS:"; grep -c ">" OUTPUT_pipeline/4-output/*fullseqs*
echo "CGS:"; grep -c ">" OUTPUT_pipeline/13-output/*.aa
echo "Species filter:"; grep -c ">" OUTPUT_pipeline/14-output/*.aa
echo "Final AGS:"; grep -c ">" OUTPUT_pipeline/16-output/*.aa
```

**Fix**: Check species keeper list includes desired species, and verify those species are in genomesDB.

### Zero CGS but positive BGS — the truncation silent failure (historical, fixed)

**Symptom**: BGS count > 0 but CGS count = 0, AGS contains only the original RGS sequences with no homologs.

**Cause (historical)**: Pre-fix Script 013 used positional parsing (`hit.split('-')[1]`) which silently dropped reciprocal hits for gene families/groups with long names. When Script 008 truncated an RGS header to 45 chars + `_NNN` counter, the resulting truncated form sometimes had no `-` delimiter left, causing `split('-')` to return a single-element list and the hit to be silently skipped.

**Fix**: Script 013 now uses `hit in rgs_identifiers_set` (pure set membership). Any gene family/group with a name long enough to trigger truncation in Script 008 MUST use the fixed Script 013. All top-level COPYMEs in GIGANTIC have been updated; verify inner per-family/per-group COPYMEs have been synced before re-running.

**Verification**:
```bash
# Inspect Script 013 for the fixed code:
grep -l "rgs_identifiers_set\|hit_is_rgs" ai/scripts/013_ai-python-extract_reciprocal_best_hits.py
# Must return a match — if silent, the COPYME has the old buggy Script 013.
```

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-workflow.sh
```

---

## After Successful Run

1. **Verify**: Check final AGS has expected sequence count
2. **Check output_to_input**: `ls -l ../../../output_to_input/*/STEP_1-homolog_discovery/`
3. **Next step**: Proceed to STEP_2 phylogenetic analysis
