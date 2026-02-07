# AI Guide: phylonames Subproject

**Purpose**: This document helps AI assistants understand and guide users through the GIGANTIC phylonames subproject.

**For AI Assistants**: Read this file first when a user asks for help with phylonames.

---

## About GIGANTIC and AI Assistance

**GIGANTIC** (Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades) is a phylogenomics platform developed through AI pair programming:
- **Development**: Claude Code within Cursor IDE, using Claude Opus 4.5
- **Human Collaborator**: Eric Edsinger
- **Transformation**: From GIGANTIC_0 (legacy scripts) to GIGANTIC_1 (modern, documented pipelines)

**AI assistants are the expected way for users to run GIGANTIC workflows.** This guide helps you help them.

---

## What This Subproject Does

The **phylonames** subproject creates standardized species identifiers from NCBI taxonomy.

**Input**: A list of species names (e.g., `Homo_sapiens`, `Octopus_bimaculoides`)

**Output**: Mapping of short names to full taxonomic phylonames

**Example**:
```
Homo_sapiens → Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
```

**Why it matters**: All other GIGANTIC subprojects use phylonames for consistent species identification. This subproject MUST run first.

---

## Two Phyloname Formats (CRITICAL)

GIGANTIC uses two distinct formats - help users understand the difference:

| Format | Example | Use Case |
|--------|---------|----------|
| `phyloname` | `Metazoa_Chordata_..._Homo_sapiens` | Most common - data tables, analysis |
| `phyloname_taxonid` | `Metazoa_Chordata_..._Homo_sapiens___9606` | File naming (guarantees uniqueness) |

---

## Numbered Unknown Clades (IMPORTANT CONCEPT)

### What AI Assistants Need to Know

NCBI Taxonomy is **incomplete** - many species lack data for all taxonomic levels. GIGANTIC fills these gaps with **numbered identifiers**:

```
Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_...
```

**Key Points to Explain to Users**:

1. **These are NOT NCBI assignments** - `Kingdom6555` is GIGANTIC's solution, not NCBI data
2. **Numbers group related species** - species with the same "first named clade below" get the same number
3. **This is a limitation, not a feature** - numbered clades are a workaround for missing data

### Clade Splitting Artifact (KNOWN LIMITATION)

If a real higher-level clade contains multiple lower-level clades, GIGANTIC will **incorrectly split** them:

**Example**: One real Kingdom containing Phyla A, B, and C becomes:
- `Kingdom1` (Phylum A species)
- `Kingdom2` (Phylum B species)
- `Kingdom3` (Phylum C species)

**When to warn users**:
- If they're doing OCL (Origins, Conservation, Loss) analyses
- If their species set spans multiple lower-level clades that share unknown higher clades
- If they see unexpectedly fragmented results

**Solution**: User-provided phylonames (see below)

---

## User-Provided Phylonames

### When Users Need This

1. They have species with numbered clades (`Kingdom6555`, etc.)
2. They know the correct taxonomy from literature
3. They want to override NCBI's classification

### How to Help Users Set It Up

1. Create `INPUT_user/user_phylonames.tsv`:
   ```
   genus_species	custom_phyloname
   Species_name	Kingdom_Phylum_Class_Order_Family_Genus_species
   ```

2. Edit `phylonames_config.yaml`:
   ```yaml
   project:
     user_phylonames: "INPUT_user/user_phylonames.tsv"
     mark_unofficial: true  # or false for clean phylonames
   ```

3. Run the pipeline - Script 004 applies the overrides

### The UNOFFICIAL Suffix

By default, only clades that **DIFFER** from the NCBI-derived phyloname get marked `UNOFFICIAL`:
```
NCBI:   Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_...
User:   Holozoa_Choanozoa_Choanoflagellata_Craspedida_...
Output: HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_Choanoflagellata_Craspedida_...
```

**Explain to users**: The UNOFFICIAL suffix marks clades where the user overrode the NCBI classification. Clades that match the NCBI phyloname remain unmarked. Set `mark_unofficial: false` to disable all UNOFFICIAL marking.

---

## How to Help Users Run This Subproject

### Step 1: Understand Their Goal

Ask the user:
- "What species are you working with?"
- "Do you have a list of species names ready?"

### Step 2: Guide Setup

1. They work within the workflow directory:
   ```bash
   cd subprojects/x_phylonames/nf_workflow-COPYME_01-generate_phylonames/
   ```

2. They need to create a species list in `INPUT_user/species_list.txt`:
   ```
   Homo_sapiens
   Aplysia_californica
   Octopus_bimaculoides
   ```

3. They edit `phylonames_config.yaml` with their project name

### Step 3: Run the Workflow

**Local execution** (laptop, workstation):
```bash
cd nf_workflow-COPYME_01-generate_phylonames
bash RUN_phylonames.sh
```

**SLURM cluster execution**:
```bash
cd nf_workflow-COPYME_01-generate_phylonames
# First edit RUN_phylonames.sbatch to set account/qos
sbatch RUN_phylonames.sbatch
```

Or step-by-step (for debugging):
```bash
bash ai/scripts/001_ai-bash-download_ncbi_taxonomy.sh
python3 ai/scripts/002_ai-python-generate_phylonames.py
python3 ai/scripts/003_ai-python-create_species_mapping.py --species-list INPUT_user/species_list.txt --output ../output_to_input/maps/my_project_map.tsv
```

---

## Common Issues and Solutions

### Issue: "Species not found in NCBI taxonomy"

**Symptoms**: Script 003 reports missing species

**Diagnosis**: Check if the species name is spelled correctly (Genus_species format)

**Solutions**:
1. Check spelling - NCBI uses official scientific names
2. Check for synonyms - species may be listed under different name
3. Use `--allow-missing` flag to continue with found species

### Issue: "No database directory found"

**Symptoms**: Script 002 fails immediately

**Cause**: NCBI taxonomy hasn't been downloaded yet

**Solution**: Run script 001 first to download the database

### Issue: "Permission denied"

**Symptoms**: Scripts won't execute

**Solution**: Make scripts executable:
```bash
chmod +x ai/scripts/*.sh
```

---

## Output Files to Expect

After successful completion:

```
nf_workflow-COPYME_01-generate_phylonames/
└── OUTPUT_pipeline/
    └── output/3-output/
        └── [project]_map-genus_species_X_phylonames.tsv

output_to_input/maps/
└── [project]_map-genus_species_X_phylonames.tsv      # Copied here for downstream use
```

This TSV file has columns: `genus_species`, `phyloname`, `phyloname_taxonid`

---

## Questions to Ask Users

If troubleshooting:
1. "Which script failed?" (001, 002, or 003?)
2. "What error message did you see?"
3. "Did you download the NCBI taxonomy first?"
4. "Can you show me your species list file?"

---

## Key Files in This Subproject

| File | Purpose |
|------|---------|
| `README.md` | Human documentation (subproject level) |
| `AI_GUIDE-phylonames.md` | This file (for AI assistants) |
| `nf_workflow-COPYME_01-*/README.md` | Quick start guide (workflow level) |
| `nf_workflow-COPYME_01-*/RUN_phylonames.sh` | Run locally |
| `nf_workflow-COPYME_01-*/RUN_phylonames.sbatch` | Run on SLURM |
| `nf_workflow-COPYME_01-*/phylonames_config.yaml` | User configuration |
| `nf_workflow-COPYME_01-*/INPUT_user/species_list.txt` | User's species list |
| `nf_workflow-COPYME_01-*/ai/AI_GUIDE-phylonames_workflow.md` | Workflow-level AI guide |
| `nf_workflow-COPYME_01-*/ai/scripts/` | Python/Bash scripts (internal) |

---

## Dependencies

This subproject requires:
- **bash** (for download script)
- **Python 3.8+** (for phyloname generation)
- **curl** or **wget** (for NCBI download)
- No special conda environment needed (uses standard library)

---

## Next Steps After phylonames

Once phylonames is complete, guide users to:
1. **genomesDB** - Set up their proteome database using the phylonames for file naming
2. Keep the mapping file - all downstream subprojects will reference it

---

## For AI Assistants: Honesty About Mistakes

**Do not whitewash mistakes.**

When you make an error:
- Say "I was **incorrect**" or "I was **wrong**" - not "that was confusing"
- Acknowledge the actual mistake clearly
- Correct it without minimizing language

Honest acknowledgment of errors is essential for effective AI-human collaboration.
