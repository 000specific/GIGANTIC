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
| `RUN_phylonames.sh` | Maybe | One-click workflow execution. Edit PROJECT_NAME. |
| `phylonames_config.yaml` | Maybe | Configuration options. Usually defaults work. |
| `INPUT_user/species_list.txt` | **YES** | User MUST add their species here |
| `INPUT_user/species_list_example.txt` | No | Example format (3 demo species) |
| `AI_GUIDE-phylonames_workflow.md` | No | This file (for AI assistants) |

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

```bash
bash RUN_phylonames.sh
```

That's it! The script handles everything else.

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

### Workflow Directory (this template)
```
output/
├── 1-output/   # (Database downloaded to versioned directory, not here)
├── 2-output/   # Master phylonames and mapping files
│   ├── phylonames
│   ├── phylonames_taxonid
│   ├── map-phyloname_X_ncbi_taxonomy_info.tsv
│   └── generation_metadata.txt
└── 3-output/   # (Script 003 writes to output_to_input/ at subproject root)
```

### Subproject Directory (parent)
```
../output_to_input/maps/
└── [project]_map-genus_species_X_phylonames.tsv  # For downstream subprojects
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
