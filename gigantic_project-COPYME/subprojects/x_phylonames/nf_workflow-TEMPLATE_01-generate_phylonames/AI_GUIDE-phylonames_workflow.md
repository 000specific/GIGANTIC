# AI Guide: Phylonames Workflow Template

**Purpose**: This document helps AI assistants guide users through this specific workflow template.

**For AI Assistants**: Read this file and the subproject-level `../AI_GUIDE-phylonames.md` for full context.

---

## About This Workflow Template

**Template**: `nf_workflow-TEMPLATE_01-generate_phylonames`

**What it does**: Downloads NCBI taxonomy and generates phyloname mappings for a user's species list.

**When users should use this**: At the very beginning of their GIGANTIC project - phylonames must be set up before any other subproject.

---

## Files in This Template

| File | User Edits? | Purpose |
|------|-------------|---------|
| `RUN_phylonames.sh` | Maybe | One-click workflow execution (local). Edit PROJECT_NAME. |
| `SLURM_phylonames.sbatch` | **YES (SLURM users)** | SLURM submission wrapper. Edit account/qos. |
| `phylonames_config.yaml` | **YES (for custom phylonames)** | Configuration options. Set user_phylonames here. |
| `INPUT_user/species_list.txt` | **YES** | User MUST add their species here |
| `INPUT_user/species_list_example.txt` | No | Example format (3 demo species) |
| `INPUT_user/user_phylonames.tsv` | **Optional** | Custom phylonames to override NCBI |
| `AI_GUIDE-phylonames_workflow.md` | No | This file (for AI assistants) |

---

## Numbered Unknown Clades

### What Users May See

When NCBI lacks data for a taxonomic level, GIGANTIC generates numbered identifiers:
```
Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_...
```

**Explain to users**:
- These are **GIGANTIC's solution**, not NCBI assignments
- Numbers group related species by shared ancestry
- This is a limitation of incomplete taxonomy data

### Clade Splitting Artifact (KNOWN ISSUE)

If a real higher-level clade contains multiple lower-level clades, GIGANTIC incorrectly splits them into separate numbered clades.

**When this matters**: OCL analyses with species spanning multiple lower-level clades.

**Solution**: User-provided phylonames (see next section).

---

## User-Provided Phylonames (Optional Step 4)

### When to Recommend This

1. User sees numbered clades like `Kingdom6555`
2. User knows correct taxonomy from literature
3. User wants to override NCBI classifications

### Setup Steps

1. Create `INPUT_user/user_phylonames.tsv`:
   ```
   genus_species	custom_phyloname
   Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
   ```

2. Edit `phylonames_config.yaml`:
   ```yaml
   project:
     user_phylonames: "INPUT_user/user_phylonames.tsv"
     mark_unofficial: true  # Default: mark all user clades as UNOFFICIAL
   ```

3. Run the pipeline - Script 004 applies overrides automatically

### The UNOFFICIAL Suffix

By default, ALL user clades are marked:
```
HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_...
```

**Reasoning**: The clade name existing in NCBI is irrelevant - it's the **assignment** that matters. When users override NCBI's assignment, their decision is "unofficial."

Set `mark_unofficial: false` in config to disable this behavior.

---

## User Workflow

### Step 1: Copy Template

Tell users to copy this entire directory to their project:

```bash
cp -r nf_workflow-TEMPLATE_01-generate_phylonames my_phylonames_run
cd my_phylonames_run
```

### Step 2: Create Species List

**This is the most important step.** Users must edit `INPUT_user/species_list.txt`:

```
# My project species
Homo_sapiens
Mus_musculus
Drosophila_melanogaster
```

**Key formatting rules**:
- One species per line
- Format: `Genus_species` (underscore, not space)
- Lines starting with `#` are comments
- Use official NCBI scientific names

### Step 3: Edit RUN Script (Optional)

In `RUN_phylonames.sh`, users may want to edit:

```bash
PROJECT_NAME="my_project"  # Change to their project name
```

This affects the output filename.

### Step 4: Run the Workflow

**Local execution:**
```bash
bash RUN_phylonames.sh
```

**SLURM cluster execution:**
```bash
# First, edit SLURM_phylonames.sbatch to set your account and qos
sbatch SLURM_phylonames.sbatch
```

That's it! The script handles everything else.

---

## Running on SLURM (HPC Clusters)

GIGANTIC uses a **SLURM wrapper pattern** - the core workflow stays clean and portable, while SLURM-specific settings live in a separate wrapper script.

| Execution | Command | When to Use |
|-----------|---------|-------------|
| Local | `bash RUN_phylonames.sh` | Laptop, workstation, or non-SLURM server |
| SLURM | `sbatch SLURM_phylonames.sbatch` | HPC clusters with SLURM scheduler |

### SLURM Setup

1. Edit `SLURM_phylonames.sbatch` and change:
   ```bash
   #SBATCH --account=YOUR_ACCOUNT    # Your cluster account
   #SBATCH --qos=YOUR_QOS            # Your quality of service
   ```

2. Optionally adjust resources (mem, time, cpus) if needed

3. Submit: `sbatch SLURM_phylonames.sbatch`

4. Check status: `squeue -u $USER`

5. View logs: `cat slurm_logs/phylonames-*.log`

### Why This Pattern?

- **RUN script stays portable** - works on any system without modification
- **SLURM users only edit SBATCH headers** - hard to misconfigure
- **Local users never see SLURM complexity** - cleaner experience
- **One workflow, two execution modes** - no code duplication

---

## Expected Runtime

| Dataset Size | Download | Generate | Map | Total |
|-------------|----------|----------|-----|-------|
| First run | 3-5 min | 5-10 min | <1 min | ~15 min |
| Subsequent runs | Skip | Skip | <1 min | <1 min |

The NCBI database and master phylonames only need to be generated once.

---

## Troubleshooting This Workflow

### "Species not found"

**Error message**: `ERROR: Some species were not found in the NCBI taxonomy`

**Common causes**:
1. **Spelling**: Check for typos (e.g., `Homo_sapeins` vs `Homo_sapiens`)
2. **Format**: Use underscore not space (`Homo_sapiens` not `Homo sapiens`)
3. **Synonym**: NCBI may use a different name - check NCBI Taxonomy website
4. **Subspecies**: Try just genus + species (without subspecies)

**How to diagnose**:
```bash
# See which species failed
# The script will print missing species to the terminal
# Or check the output file for missing entries
wc -l ../output_to_input/maps/*_map-genus_species_X_phylonames.tsv
```

### "Download failed"

**Error message**: wget/curl connection errors

**Common causes**:
1. No internet connection
2. Firewall blocking FTP
3. NCBI server temporarily down

**Solutions**:
1. Check internet connectivity: `ping google.com`
2. Try again later (NCBI occasionally has maintenance)
3. If FTP is blocked, user may need to download manually

### "Permission denied"

**Solution**:
```bash
chmod +x RUN_phylonames.sh
chmod +x ai_scripts/*.sh
```

---

## Output Structure

**GIGANTIC Transparency Principle**: All script outputs are visible in `output/N-output/` directories.

**Softlink Pattern**: To avoid data duplication, `output_to_input/` contains symlinks pointing to actual files in `output/N-output/`. This allows downstream subprojects to access data while keeping canonical copies in workflow output directories.

### Workflow Directory (this template)
```
output/
├── 1-output/   # (Database downloaded to versioned directory, not here)
├── 2-output/   # Master phylonames and mapping files
│   ├── phylonames
│   ├── phylonames_taxonid
│   ├── map-phyloname_X_ncbi_taxonomy_info.tsv
│   ├── map-numbered_clades_X_defining_clades.tsv  # Reference for numbered clades
│   └── generation_metadata.txt
├── 3-output/   # Project-specific mapping file (ACTUAL DATA)
│   └── [project]_map-genus_species_X_phylonames.tsv
└── 4-output/   # User phylonames applied (OPTIONAL - only if user_phylonames set)
    ├── final_project_mapping.tsv
    └── unofficial_clades_report.tsv
```

### Subproject Directory (parent)
```
../output_to_input/maps/
└── [project]_map-genus_species_X_phylonames.tsv  # SYMLINK to output/3-output/
```

### Archiving with Softlinks

When archiving a project, use `cp -L` or `rsync -L` to dereference symlinks:
```bash
# Copy with dereferenced symlinks
cp -rL my_project/ archive/my_project/

# Or with rsync
rsync -avL my_project/ archive/my_project/
```

## Output Verification

After successful run, users should have:

**How to verify**:
```bash
# Check the intermediate outputs (in workflow directory)
ls output/2-output/

# Check the final mapping file (at subproject root)
head ../output_to_input/maps/*_map-genus_species_X_phylonames.tsv
```

**Expected output**:
```
genus_species   phyloname   phyloname_taxonid
Homo_sapiens    Metazoa_Chordata_...    Metazoa_Chordata_...___9606
```

---

## Integration with Other Subprojects

After phylonames completes:

1. The mapping file in `output_to_input/maps/` is used by:
   - **genomesDB** - for naming proteome files
   - **trees_species** - for clade definitions
   - **All downstream subprojects** - for species identification

2. Tell users to copy or symlink this file to their main project's phylonames directory

---

## Questions to Ask Users

When troubleshooting:

1. "Can you show me your `INPUT_user/species_list.txt` file?"
2. "Did you run `bash RUN_phylonames.sh`?"
3. "What error message did you see?"
4. "Is this your first run or are you updating an existing project?"

---

## For AI Assistants: Honesty About Mistakes

**Do not whitewash mistakes.**

When you make an error, say "I was **incorrect**" or "I was **wrong**" - not "that was confusing." Acknowledge mistakes clearly without minimizing language.
