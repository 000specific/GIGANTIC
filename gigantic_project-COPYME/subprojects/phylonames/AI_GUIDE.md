# AI Guide: phylonames Subproject

**For AI Assistants**: Read `../../../AI_GUIDE.md` (project root) first for GIGANTIC overview, directory structure, and general patterns. This guide covers phylonames-specific concepts and troubleshooting.

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
| GIGANTIC overview, directory structure | `../../../AI_GUIDE.md` (project root) |
| Phylonames concepts, troubleshooting | This file |
| STEP_1 overview (generate and evaluate) | `STEP_1-generate_and_evaluate/AI_GUIDE.md` |
| STEP_1 workflow execution | `STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/ai/AI_GUIDE.md` |
| STEP_2 overview (apply user phylonames) | `STEP_2-apply_user_phylonames/AI_GUIDE.md` |
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
├── README.md                                   # User-facing documentation
├── AI_GUIDE.md                                 # THIS FILE
│
├── RUN-update_upload_to_server.sh              # Subproject-level publisher (thin wrapper around shared helper, §38)
│
├── upload_to_server/                           # Single publish destination per §38
│                                               # (auto-populated by RUN-update_upload_to_server.sh; no per-STEP upload_to_server)
│
├── output_to_input/                            # Outputs for downstream subprojects (§2)
│   ├── STEP_1-generate_and_evaluate/
│   │   └── maps/
│   │       └── [project]_map-genus_species_X_phylonames.tsv  (symlink)
│   ├── STEP_2-apply_user_phylonames/
│   │   └── maps/
│   │       └── [project]_map-genus_species_X_phylonames.tsv  (symlink)
│   └── maps/                                   # Convenience symlink to most recent STEP
│       └── [project]_map-genus_species_X_phylonames.tsv      (symlink)
│
│   (no per-subproject research_notebook/ — single project-root sandbox at
│   gigantic_project-COPYME/research_notebook/ per §1, §25; chat captures
│   land at research_notebook/research_ai/sessions/ per §9)
│   ├── research_user/                          # User sandbox (ships empty)
│   └── research_ai/sessions/                   # Captured chat transcripts (§9)
│
├── STEP_1-generate_and_evaluate/
│   ├── AI_GUIDE.md                             # STEP-level guide
│   │
│   └── workflow-COPYME-generate_phylonames/
│       ├── README.md                           # User-facing workflow quickstart
│       ├── RUN-workflow.sh                     # Unified driver (§29: local or slurm via execution_mode)
│       ├── START_HERE-user_config.yaml         # Config: project name, execution_mode, slurm.*
│       ├── upload_manifest.tsv                 # Server publish manifest (§38, §39)
│       ├── INPUT_user/                         # Species list (auto-copied from project default if absent)
│       ├── OUTPUT_pipeline/                    # Results (1-output through 5-output)
│       └── ai/
│           ├── AI_GUIDE.md
│           ├── main.nf
│           ├── nextflow.config
│           ├── conda_environment.yml
│           └── scripts/
│               ├── 001_ai-bash-download_ncbi_taxonomy.sh
│               ├── 002_ai-python-generate_phylonames.py
│               ├── 003_ai-python-create_species_mapping.py
│               ├── 004_ai-python-generate_taxonomy_summary.py
│               └── 005_ai-python-write_run_log.py
│
└── STEP_2-apply_user_phylonames/
    ├── AI_GUIDE.md                             # STEP-level guide
    │
    └── workflow-COPYME-apply_user_phylonames/
        ├── README.md                           # User-facing workflow quickstart
        ├── RUN-workflow.sh                     # Unified driver (§29)
        ├── START_HERE-user_config.yaml         # Config: project name, user_phylonames path, etc.
        ├── upload_manifest.tsv                 # Server publish manifest
        ├── INPUT_user/                         # User phylonames TSV
        ├── OUTPUT_pipeline/                    # Results (1-output through 3-output)
        └── ai/
            ├── AI_GUIDE.md
            ├── main.nf
            ├── nextflow.config
            ├── conda_environment.yml
            └── scripts/
                ├── 001_ai-python-apply_user_phylonames.py
                ├── 002_ai-python-generate_taxonomy_summary.py
                └── 003_ai-python-write_run_log.py
```

Per §38 and §41, phylonames is a STEP-organized subproject and has ONE
subproject-level `upload_to_server/` (no per-STEP `upload_to_server/` —
those were deleted in the 2026-05-26 cleanup).

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

**2. Stage `user_phylonames.tsv` via the canonical INPUT_user arena**
(see `../../INPUT_user/phylonames/README.md`):

```bash
# Real file lives in the user sandbox
cd ../../INPUT_user/phylonames
ln -srf ../../research_notebook/research_user/<your-path>/user_phylonames.tsv user_phylonames.tsv
```

For quick exploratory runs the file can also be written directly into the
workflow's local `STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/INPUT_user/user_phylonames.tsv`,
but the canonical pattern is the project-level INPUT_user slot. Format:

```tsv
genus_species	custom_phyloname
Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

An example template ships at `STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/INPUT_user/user_phylonames_example.tsv`.

**3. Edit** `START_HERE-user_config.yaml` in the STEP_2 workflow directory:
```yaml
project:
  name: "my_project"                              # MUST match STEP_1
  user_phylonames: "INPUT_user/user_phylonames.tsv"
  mark_unofficial: true                           # or false
```

**4. Run the STEP_2 workflow** — Script 001 applies user overrides to the
STEP_1 mapping; the convenience symlink at `output_to_input/maps/` is
re-pointed at the STEP_2 mapping so downstream subprojects pick up the
user-overridden version automatically.

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
| `../../INPUT_user/species_set/species_list.txt` | Project-wide default species list (consumed by STEP_1 if no workflow-local override) | **YES** |
| `../../INPUT_user/phylonames/user_phylonames.tsv` | Project-level staging slot for STEP_2 user overrides (canonical INPUT_user arena, symlink to research_notebook/research_user/...) | **YES** |
| `STEP_1-*/workflow-*/START_HERE-user_config.yaml` | STEP_1 project name, execution_mode, slurm_account/qos, NCBI download options | **YES** |
| `STEP_1-*/workflow-*/INPUT_user/species_list.txt` | STEP_1 species list override (optional, auto-copied from project default if absent) | **YES** (to override) |
| `STEP_2-*/workflow-*/START_HERE-user_config.yaml` | STEP_2 project name, user_phylonames path, mark_unofficial, execution_mode, slurm_account/qos | **YES** |
| `STEP_2-*/workflow-*/INPUT_user/user_phylonames.tsv` | STEP_2 user phyloname overrides (workflow-local copy, archived with the run) | **YES** |
| `output_to_input/maps/*.tsv` | Convenience handle for downstream subprojects (symlink to whichever STEP ran last) | No |
| `output_to_input/STEP_1-*/maps/*.tsv` | STEP_1 mapping (NCBI-only) | No |
| `output_to_input/STEP_2-*/maps/*.tsv` | STEP_2 mapping (with user overrides applied) | No |
| `upload_to_server/STEP_*-*/workflow-RUN_*-*/N-output/*` | Server-publishing tree (assembled by RUN-update_upload_to_server.sh from per-workflow upload_manifest.tsv) | No |

---

## Downstream consumers (per §40)

The `output_to_input/maps/[project]_map-genus_species_X_phylonames.tsv`
exposed here is consumed by virtually every downstream GIGANTIC
subproject, because phylonames are the canonical species identifiers
used throughout the framework:

- **genomesDB** — uses phylonames to name standardized proteome files
  and to label species across the database
- **orthogroups** — labels orthogroup memberships by phyloname
- **annotations_hmms** — keys per-species annotation files by phyloname
- **trees_species** — labels species in candidate species trees by
  phyloname
- **trees_gene_families**, **trees_gene_groups** — label gene-family /
  gene-group tree tips by phyloname
- **orthogroups_X_ocl**, **annotations_X_ocl** — propagate phyloname
  labels through OCL analyses
- **gene_sizes**, **homolog_counts**, **hotspots**, **secretome**,
  **one_direction_homologs**, and so on — all use phylonames

In practice every subproject that operates per-species reads from
`phylonames/output_to_input/maps/` at some point. **phylonames must run
first** in any GIGANTIC project (see top of this file).

## Next Steps After phylonames

Guide users to:
1. **Review STEP_1 output** — check the taxonomy summary for numbered
   clades or misclassifications
2. **Run STEP_2 if needed** — if any species need corrected phylonames,
   create `user_phylonames.tsv` and run STEP_2
3. **genomesDB next** — set up proteome database using phylonames for
   file naming (the canonical second subproject to run)
4. **Keep the mapping intact** — all downstream subprojects reference
   `output_to_input/maps/`

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| General help | "What species are you working with?" |
| Error occurred | "Which STEP and which script failed? What error message?" |
| Missing species | "Can you show me your species list file?" |
| Numbered clades | "Do you know the correct taxonomy from literature? We can fix these with STEP_2." |
| Wants to override phylonames | "Have you already run STEP_1? Let us review the output first to identify which species need corrections." |
