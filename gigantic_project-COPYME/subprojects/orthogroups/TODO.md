# Orthogroups Subproject - TODO

**AI**: Claude Code | Opus 4.6 | 2026 February 27
**Human**: Eric Edsinger

---

## OrthoHMM

### Completed
- [x] Full workflow implementation (6 scripts, NextFlow pipeline)
- [x] Removed all `optional: true` from main.nf
- [x] Script 003 guarantees all output files exist for NextFlow
- [x] Script 006 generates per-species assignment files
- [x] Fixed README.md filename references
- [x] Fixed STEP_4 references to STEP_2
- [x] Created workflow-level AI_GUIDE

### Open Items
- [ ] **Per-species files in script 006**: May be removable later if not needed by downstream subprojects. Currently generates `6_ai-per_species/` directory with one TSV per species listing every sequence and its orthogroup assignment. Flagged for review after running pipeline and evaluating downstream needs.
- [ ] **OrthoHMM command flags**: GIGANTIC_0 uses simple `orthohmm dir -o outdir` with no extra flags. GIGANTIC_1 adds `-c`, `-e`, `-s` flags from config. Verify these flags work correctly against `orthohmm --help` when running the pipeline.
- [ ] **Run pipeline**: Execute on species dataset once genomesDB STEP_2 output is available.

---

## OrthoFinder

### Completed
- [x] Directory structure created
- [x] RUN_orthofinder.sh script (bash, no NextFlow)
- [x] SLURM_orthofinder.sbatch wrapper
- [x] INPUT_user/README.md with preparation guide

### Issues Found (2026-02-27 Review)
- [x] **README filename mismatches**: README references `RUN-orthofinder.sh` but actual file is `RUN_orthofinder.sh`; references `RUN-orthofinder.sbatch` but actual file is `SLURM_orthofinder.sbatch`
- [x] **Missing config file reference**: README references `orthofinder_config.yaml` but no config file exists (settings are hardcoded in RUN script)
- [x] **Vague STEP reference**: README line 16 says `genomesDB/STEP_2.../output_to_input/gigantic_proteomes/`
- [x] **Missing workflow AI_GUIDE**: `ai/` directory is empty; AI_GUIDE-orthofinder.md references a workflow guide that doesn't exist
- [ ] **File naming convention inconsistency**: orthohmm uses `RUN-orthohmm.sh` (dash) while orthofinder uses `RUN_orthofinder.sh` (underscore). CLAUDE.md SLURM wrapper pattern suggests `RUN_` prefix. Should standardize across subproject.
- [ ] **Run pipeline**: Execute on species dataset once genomesDB output is available.

---

## Broccoli

### Completed (2026-02-28 Review)
- [x] **Rewrote all documentation**: README.md and AI_GUIDE-broccoli.md now accurately describe Broccoli (were incorrectly copied from OrthoHMM)
- [x] **Fixed workflow README**: Now references Broccoli correctly with accurate output descriptions
- [x] **Documented Broccoli pipeline**: 4-step pipeline (kmer clustering, phylomes, network analysis, orthologous pairs)
- [x] **Documented key parameters**: `-dir`, `-ext`, `-threads`, `-e_value`, `-phylogenies`, etc.
- [x] **Noted implementation considerations**: `.aa` extension, header format verification, dir_step1-4 management

### Open Items
- [ ] **Implement Broccoli workflow**: Create scripts, NextFlow pipeline, config, and RUN files when ready
- [ ] **Verify conda environment**: Check if ete3, Diamond, and single-thread FastTree are available in `ai_gigantic_orthogroups` or need a dedicated environment
- [ ] **Test header compatibility**: Verify whether Broccoli needs short headers (like OrthoHMM) or works with GIGANTIC phyloname headers
- [ ] **Run pipeline**: Execute on species dataset once implemented

---

## Subproject-Level

### Completed (2026-02-28)
- [x] **Updated README.md**: Now documents all three tools (OrthoFinder, OrthoHMM, Broccoli) with correct filenames and paths
- [x] **Updated AI_GUIDE-orthogroups.md**: Now includes all three tools, correct genomesDB path, three-tool comparison table
- [x] **Created TODO.md**: Tracking all open items across subproject

### Open Items
- [ ] **Standardize RUN/SLURM file naming**: Choose consistent convention across orthohmm, orthofinder, and broccoli (dash vs underscore prefix)
- [ ] **Compare orthogroup results**: After running OrthoHMM and OrthoFinder, compare orthogroup counts and membership
- [ ] **Evaluate Broccoli priority**: Decide whether to implement Broccoli workflow or defer
