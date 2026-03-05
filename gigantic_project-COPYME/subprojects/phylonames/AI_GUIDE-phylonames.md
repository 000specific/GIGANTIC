# AI Guide: phylonames Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers phylonames-specific concepts and troubleshooting.

**Location**: `gigantic_project-*/subprojects/phylonames/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain the discrepancy
- ALWAYS ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| Phylonames concepts, troubleshooting | This file |
| STEP_1 overview (generate and evaluate) | `STEP_1-generate_and_evaluate/AI_GUIDE-generate_and_evaluate.md` |
| STEP_1 workflow execution | `STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/ai/AI_GUIDE-phylonames_workflow.md` |
| STEP_2 overview (apply user phylonames) | `STEP_2-apply_user_phylonames/AI_GUIDE-apply_user_phylonames.md` |
| STEP_2 workflow execution | `STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/ai/` |

---

## What This Subproject Does

**Purpose**: Generate standardized species identifiers from NCBI taxonomy, with optional user-provided overrides.

**Two-STEP Architecture**:

| STEP | Purpose | When to run |
|------|---------|-------------|
| **STEP_1-generate_and_evaluate** | Download NCBI taxonomy, generate phylonames, create species mapping, produce taxonomy summary | Always run first |
| **STEP_2-apply_user_phylonames** | Apply user-provided phyloname overrides to correct numbered clades or NCBI misclassifications | Only after reviewing STEP_1 output and identifying species that need corrections |

**Input**: Species list (e.g., `Homo_sapiens`, `Octopus_bimaculoides`)

**Output**: Mapping of `genus_species` to `phyloname` to `phyloname_taxonid`

**Critical**: This subproject MUST run first. All other subprojects depend on phylonames.

---

## Directory Structure (relative to subproject root)

```
phylonames/
├── README.md                        # Human documentation
├── AI_GUIDE-phylonames.md           # THIS FILE
│
├── user_research/                   # Personal workspace for this subproject
├── upload_to_server/                # Server sharing
│
├── output_to_input/                                # Outputs for downstream subprojects
│   ├── STEP_1-generate_and_evaluate/
│   │   └── maps/
│   │       └── [project]_map-genus_species_X_phylonames.tsv
│   ├── STEP_2-apply_user_phylonames/
│   │   └── maps/
│   │       └── [project]_map-genus_species_X_phylonames.tsv
│   └── maps/                                       # Convenience symlink to whichever STEP ran last
│       └── [project]_map-genus_species_X_phylonames.tsv  # SYMLINK
│
├── STEP_1-generate_and_evaluate/
│   ├── AI_GUIDE-generate_and_evaluate.md     # STEP-level guide
│   ├── RUN-clean_and_record_subproject.sh    # Cleanup + AI session recording
│   ├── RUN-update_upload_to_server.sh        # Update server symlinks
│   ├── upload_to_server/                     # Taxonomy summaries for server
│   │   └── taxonomy_summaries/
│   │
│   └── workflow-COPYME-generate_phylonames/
│       ├── RUN-workflow.sh                   # bash RUN-workflow.sh
│       ├── RUN-workflow.sbatch               # sbatch RUN-workflow.sbatch
│       ├── START_HERE-user_config.yaml            # User edits project name here
│       ├── INPUT_user/                       # Species list (copied from project INPUT_user at runtime)
│       ├── OUTPUT_pipeline/                  # Results
│       └── ai/                               # Nextflow pipeline and scripts
│           ├── AI_GUIDE-phylonames_workflow.md
│           ├── main.nf
│           ├── nextflow.config
│           └── scripts/
│               ├── 001_ai-bash-download_ncbi_taxonomy.sh
│               ├── 002_ai-python-generate_phylonames.py
│               ├── 003_ai-python-create_species_mapping.py
│               ├── 004_ai-python-generate_taxonomy_summary.py
│               └── 005_ai-python-write_run_log.py
│
└── STEP_2-apply_user_phylonames/
    ├── AI_GUIDE-apply_user_phylonames.md     # STEP-level guide
    │
    └── workflow-COPYME-apply_user_phylonames/
        ├── RUN-workflow.sh                   # bash RUN-workflow.sh
        ├── RUN-workflow.sbatch               # sbatch RUN-workflow.sbatch
        ├── START_HERE-user_config.yaml            # User edits project name and user phylonames path
        ├── INPUT_user/                       # User phylonames TSV goes here
        ├── OUTPUT_pipeline/                  # Results
        └── ai/                               # Nextflow pipeline and scripts
            ├── main.nf
            ├── nextflow.config
            └── scripts/
                ├── 001_ai-python-apply_user_phylonames.py
                ├── 002_ai-python-generate_taxonomy_summary.py
                └── 003_ai-python-write_run_log.py
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
Real taxonomy:       Unknown Kingdom -> Phylum A, Phylum B, Phylum C
GIGANTIC creates:    Kingdom1 (A species), Kingdom2 (B species), Kingdom3 (C species)
```

**Impact**: OCL analyses may give incorrect results if species span multiple lower clades.

**Solution**: User-provided phylonames via STEP_2 (see below).

---

## User-Provided Phylonames (STEP_2)

### When Users Need This

1. They review STEP_1 output and see numbered clades (`Kingdom6555`, etc.)
2. They know correct taxonomy from literature
3. They want to override NCBI's classification for specific species

### Workflow

**1. Run STEP_1 first** and review the taxonomy summary and mapping output.

**2. Create** `INPUT_user/user_phylonames.tsv` in the STEP_2 workflow directory:
```tsv
genus_species	custom_phyloname
Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

An example file is provided at `STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/INPUT_user/user_phylonames_example.tsv`.

**3. Edit** `START_HERE-user_config.yaml` in the STEP_2 workflow directory:
```yaml
project:
  user_phylonames: "INPUT_user/user_phylonames.tsv"
  mark_unofficial: true  # or false
```

**4. Run STEP_2 workflow** - Script 001 applies user overrides to the STEP_1 mapping

### UNOFFICIAL Suffix

Clades that DIFFER from NCBI get marked `UNOFFICIAL`:
```
NCBI:   Kingdom6555_Phylum6554_Choanoflagellata_...
User:   Holozoa_Choanozoa_Choanoflagellata_...
Output: HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_Choanoflagellata_...
```

Matching clades stay unmarked. Set `mark_unofficial: false` to disable.

---

## output_to_input: How Downstream Subprojects Access Phylonames

The `output_to_input/` directory at the phylonames subproject root contains outputs for downstream subprojects.

**Structure**:
```
output_to_input/
├── STEP_1-generate_and_evaluate/maps/    # Mapping from STEP_1 (NCBI-only phylonames)
├── STEP_2-apply_user_phylonames/maps/    # Mapping from STEP_2 (with user overrides applied)
└── maps/                                 # Convenience symlink to whichever STEP ran last
```

**How it works**:
- After STEP_1 runs, `STEP_1-generate_and_evaluate/maps/` is populated
- After STEP_2 runs, `STEP_2-apply_user_phylonames/maps/` is populated
- The `maps/` symlink at the top level points to whichever STEP ran most recently
- Downstream subprojects reference `output_to_input/maps/` to always get the latest mapping

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "NOTINNCBI species" in STEP_1 output | Species not in NCBI taxonomy | Species is included with NOTINNCBI placeholder. Provide proper phyloname via user_phylonames in STEP_2, or check spelling at NCBI Taxonomy website |
| "No database directory" | NCBI not downloaded | Run STEP_1 script 001 first |
| "Permission denied" | Scripts not executable | `chmod +x ai/scripts/*.sh` |
| Download failed | Network or NCBI down | Check connectivity, try later |
| STEP_2 fails with missing input | STEP_1 not run yet | Run STEP_1 before STEP_2 |
| User phylonames not applied | Wrong path in STEP_2 config | Check `user_phylonames` path in STEP_2 `START_HERE-user_config.yaml` |

### Diagnostic Commands

```bash
# Check species list exists (STEP_1)
cat STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/INPUT_user/species_list.txt

# Check NCBI database was downloaded (STEP_1)
ls -la STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/OUTPUT_pipeline/1-output/

# Check master phylonames generated (STEP_1)
wc -l STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/OUTPUT_pipeline/2-output/phylonames

# Check STEP_1 project mapping created
head output_to_input/STEP_1-generate_and_evaluate/maps/*_map-genus_species_X_phylonames.tsv

# Check user phylonames input file (STEP_2)
cat STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/INPUT_user/user_phylonames.tsv

# Check STEP_2 output mapping with user overrides applied
head output_to_input/STEP_2-apply_user_phylonames/maps/*_map-genus_species_X_phylonames.tsv

# Check which STEP the convenience symlink points to
ls -la output_to_input/maps/
```

---

## Run Logging (AI Lab Notebook)

Each workflow run automatically creates a timestamped log in its own `ai/logs/` directory:
```
workflow-*/ai/logs/
```

**Log filename format**: `run_YYYYMMDD_HHMMSS-phylonames_success.log`

**Log contents**:
- Timestamp and project name
- Species list (full list of what was processed)
- Output file location and species mapped count
- Sample mappings (first 3 results)
- Workflow scripts executed

**Purpose**: Transparency and reproducibility of AI-assisted research. Like a lab notebook, but for AI work.

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `../../INPUT_user/species_set/species_list.txt` | Project-wide default species list | **YES** |
| `STEP_1-*/workflow-*/START_HERE-user_config.yaml` | STEP_1 project name and options | **YES** |
| `STEP_1-*/workflow-*/RUN-workflow.sbatch` | STEP_1 SLURM account/qos | **YES** (SLURM) |
| `STEP_1-*/workflow-*/INPUT_user/species_list.txt` | STEP_1 species list override (optional, auto-copied from project default) | **YES** (to override) |
| `STEP_2-*/workflow-*/START_HERE-user_config.yaml` | STEP_2 project name, user phylonames path, unofficial marking | **YES** |
| `STEP_2-*/workflow-*/RUN-workflow.sbatch` | STEP_2 SLURM account/qos | **YES** (SLURM) |
| `STEP_2-*/workflow-*/INPUT_user/user_phylonames.tsv` | User-provided phyloname overrides | **YES** |
| `output_to_input/maps/*.tsv` | Output for downstream subprojects (symlink to latest STEP) | No |
| `output_to_input/STEP_1-*/maps/*.tsv` | STEP_1 mapping output | No |
| `output_to_input/STEP_2-*/maps/*.tsv` | STEP_2 mapping output (with user overrides) | No |

---

## Next Steps After phylonames

Guide users to:
1. **Review STEP_1 output** - Check the taxonomy summary for numbered clades or misclassifications
2. **Run STEP_2 if needed** - If any species need corrected phylonames, create `user_phylonames.tsv` and run STEP_2
3. **genomesDB** - Set up proteome database using phylonames for file naming
4. **Keep the mapping** - All downstream subprojects reference `output_to_input/maps/`

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| General help | "What species are you working with?" |
| Error occurred | "Which STEP and which script failed? What error message?" |
| Missing species | "Can you show me your species list file?" |
| Numbered clades | "Do you know the correct taxonomy from literature? We can fix these with STEP_2." |
| Wants to override phylonames | "Have you already run STEP_1? Let us review the output first to identify which species need corrections." |
