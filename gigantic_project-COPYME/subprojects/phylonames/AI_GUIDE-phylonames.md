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

## How to Help Users Run This Subproject

### Step 1: Understand Their Goal

Ask the user:
- "What species are you working with?"
- "Do you have a list of species names ready?"

### Step 2: Guide Setup

1. They need to copy the workflow template:
   ```bash
   cp -r subprojects/phylonames/nf_workflow-TEMPLATE_01-generate_phylonames my_project/phylonames/
   ```

2. They need to create a species list in `INPUT_user/species_list.txt`:
   ```
   Homo_sapiens
   Aplysia_californica
   Octopus_bimaculoides
   ```

### Step 3: Run the Workflow

The simplest approach:
```bash
cd my_project/phylonames
bash RUN_phylonames.sh
```

Or step-by-step:
```bash
bash ai_scripts/001_ai-bash-download_ncbi_taxonomy.sh
python3 ai_scripts/002_ai-python-generate_phylonames.py
python3 ai_scripts/003_ai-python-create_species_mapping.py --species-list INPUT_user/species_list.txt --output output_to_input/maps/my_project_map.tsv
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
chmod +x ai_scripts/*.sh
```

---

## Output Files to Expect

After successful completion:

```
nf_workflow-TEMPLATE_01-generate_phylonames/
└── output/3-output/
    └── [project]_map-genus_species_X_phylonames.tsv  # ACTUAL FILE

output_to_input/maps/
└── [project]_map-genus_species_X_phylonames.tsv      # SYMLINK to above
```

This TSV file has columns: `genus_species`, `phyloname`, `phyloname_taxonid`

**Softlink Pattern**: The file in `output_to_input/` is a symlink pointing to the actual file in `output/3-output/`. This avoids data duplication. For archiving, use `cp -L` or `rsync -L` to dereference symlinks.

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
| `README.md` | Human documentation |
| `AI_GUIDE-phylonames.md` | This file (for AI assistants) |
| `nf_workflow-TEMPLATE_01-*/ai_scripts/001_ai-bash-download_ncbi_taxonomy.sh` | Downloads NCBI data |
| `nf_workflow-TEMPLATE_01-*/ai_scripts/002_ai-python-generate_phylonames.py` | Generates all phylonames |
| `nf_workflow-TEMPLATE_01-*/ai_scripts/003_ai-python-create_species_mapping.py` | Creates project-specific mapping |
| `nf_workflow-TEMPLATE_01-*/` | Workflow template directory |
| `nf_workflow-TEMPLATE_01-*/INPUT_user/species_list.txt` | User's species list (they create this) |

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
