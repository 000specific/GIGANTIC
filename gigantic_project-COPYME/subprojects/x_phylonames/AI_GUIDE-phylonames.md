# AI Guide: phylonames Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers phylonames-specific concepts and troubleshooting.

**Location**: `gigantic_project-*/subprojects/x_phylonames/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| Phylonames concepts, troubleshooting | This file |
| Running the workflow | `nf_workflow-COPYME_01-*/ai/AI_GUIDE-phylonames_workflow.md` |

---

## What This Subproject Does

**Purpose**: Generate standardized species identifiers from NCBI taxonomy.

**Input**: Species list (e.g., `Homo_sapiens`, `Octopus_bimaculoides`)

**Output**: Mapping of `genus_species → phyloname → phyloname_taxonid`

**Critical**: This subproject MUST run first. All other subprojects depend on phylonames.

---

## Directory Structure (relative to subproject root)

```
x_phylonames/
├── README.md                        # Human documentation
├── AI_GUIDE-phylonames.md           # THIS FILE
├── RUN-clean_subproject.sh          # Cleanup work/ and .nextflow*
├── RUN-update_upload_to_server.sh   # Update server symlinks
│
├── user_research/                   # Personal workspace for this subproject
│
├── output_to_input/                 # Outputs for downstream subprojects
│   └── maps/
│       └── [project]_map-genus_species_X_phylonames.tsv  # SYMLINK
│
├── upload_to_server/                # Server sharing
│   └── upload_manifest.tsv
│
└── nf_workflow-COPYME_01-generate_phylonames/
    ├── RUN-phylonames.sh            # bash RUN-phylonames.sh
    ├── RUN-phylonames.sbatch        # sbatch RUN-phylonames.sbatch
    ├── phylonames_config.yaml       # User edits project name here
    ├── INPUT_user/                  # Copied from INPUT_gigantic at runtime
    ├── OUTPUT_pipeline/             # Results
    └── ai/                          # Internal
```

---

## Phylonames-Specific Concepts

### Numbered Unknown Clades

**What users see**:
```
Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_...
```

**Key points to explain**:

| Concept | Explanation |
|---------|-------------|
| What they are | GIGANTIC's solution for missing NCBI taxonomy levels |
| NOT NCBI data | Numbers like `Kingdom6555` are generated, not official |
| Grouping logic | Species with same "first named clade below" get same number |
| Limitation | A workaround, not a feature |

### Clade Splitting Artifact (Known Issue)

**Problem**: If one unknown higher clade contains multiple lower clades, GIGANTIC creates separate numbered clades.

**Example**:
```
Real taxonomy:       Unknown Kingdom → Phylum A, Phylum B, Phylum C
GIGANTIC creates:    Kingdom1 (A species), Kingdom2 (B species), Kingdom3 (C species)
```

**Impact**: OCL analyses may give incorrect results if species span multiple lower clades.

**Solution**: User-provided phylonames (see below).

---

## User-Provided Phylonames

### When Users Need This

1. They see numbered clades (`Kingdom6555`, etc.)
2. They know correct taxonomy from literature
3. They want to override NCBI's classification

### Setup

**1. Create** `INPUT_user/user_phylonames.tsv`:
```tsv
genus_species	custom_phyloname
Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

**2. Edit** `phylonames_config.yaml`:
```yaml
project:
  user_phylonames: "INPUT_user/user_phylonames.tsv"
  mark_unofficial: true  # or false
```

**3. Run pipeline** - Script 004 applies overrides

### UNOFFICIAL Suffix

Clades that DIFFER from NCBI get marked `UNOFFICIAL`:
```
NCBI:   Kingdom6555_Phylum6554_Choanoflagellata_...
User:   Holozoa_Choanozoa_Choanoflagellata_...
Output: HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_Choanoflagellata_...
```

Matching clades stay unmarked. Set `mark_unofficial: false` to disable.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Species not found" | Spelling, format, or synonym | Check spelling, use `Genus_species` format, check NCBI Taxonomy website |
| "No database directory" | NCBI not downloaded | Run script 001 first |
| "Permission denied" | Scripts not executable | `chmod +x ai/scripts/*.sh` |
| Download failed | Network or NCBI down | Check connectivity, try later |

### Diagnostic Commands

```bash
# Check species list exists
cat INPUT_user/species_list.txt

# Check NCBI database was downloaded
ls -la OUTPUT_pipeline/1-output/

# Check master phylonames generated
wc -l OUTPUT_pipeline/2-output/phylonames

# Check project mapping created
head output_to_input/maps/*_map-genus_species_X_phylonames.tsv
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `../../INPUT_gigantic/species_list.txt` | Canonical species list | **YES** |
| `nf_workflow-*/phylonames_config.yaml` | Project name, options | **YES** |
| `nf_workflow-*/RUN-phylonames.sbatch` | SLURM account/qos | **YES** (SLURM) |
| `nf_workflow-*/INPUT_user/species_list.txt` | Archived copy | No (auto-copied) |
| `output_to_input/maps/*.tsv` | Output for downstream | No |

---

## Next Steps After phylonames

Guide users to:
1. **genomesDB** - Set up proteome database using phylonames for file naming
2. **Keep the mapping** - All downstream subprojects reference `output_to_input/maps/`

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| General help | "What species are you working with?" |
| Error occurred | "Which script failed? What error message?" |
| Missing species | "Can you show me your species list file?" |
| Numbered clades | "Do you know the correct taxonomy from literature?" |
