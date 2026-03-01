# Orthogroups Subproject - TODO

**AI**: Claude Code | Opus 4.6 | 2026 February 28
**Human**: Eric Edsinger

---

## Ground-Up Redesign (2026-02-28)

### Completed
- [x] Removed old inconsistent structure (flat OrthoFinder, Nextflow OrthoHMM, empty Broccoli)
- [x] Created four equivalent self-contained BLOCK projects (BLOCK_orthofinder, BLOCK_orthohmm, BLOCK_broccoli, BLOCK_comparison)
- [x] All projects mirror genomesDB STEP pattern
- [x] Consistent naming: RUN-workflow.sh, RUN-workflow.sbatch, *_config.yaml
- [x] OrthoHMM: 6 scripts, Nextflow pipeline, documentation
- [x] Broccoli: 6 scripts, Nextflow pipeline, documentation
- [x] OrthoFinder: 6 scripts (with -X flag support), Nextflow pipeline, documentation
- [x] Comparison: 2 scripts, Nextflow pipeline, documentation
- [x] All three tools produce identical standardized output format
- [x] AI_GUIDE hierarchy (Level 2 per-project + Level 3 per-workflow)
- [x] Updated subproject-level README.md, AI_GUIDE, TODO
- [x] Updated conda yml with all tool dependencies (OrthoFinder, OrthoHMM, Broccoli, Diamond, HMMER, MCL, FastTree)
- [x] Standardized all documentation to use `RUN-workflow.sh` / `RUN-workflow.sbatch` naming across all 15 .md files
- [x] Corrected script count descriptions: OrthoFinder 6 scripts (no header conversion), OrthoHMM 6 scripts, Broccoli 6 scripts, Comparison 2 scripts

### Open Items (Requires HiPerGator / Blue Online)
- [ ] **Verify conda environment**: Install `ai_gigantic_orthogroups` and confirm all tools are available
- [ ] **Validate OrthoHMM command flags**: Run `orthohmm --help` and verify `-c`, `-e`, `-s` flags
- [ ] **Test Broccoli header compatibility**: Confirm short headers work correctly with Broccoli
- [ ] **Run OrthoFinder pipeline**: Execute on species dataset when genomesDB output available
- [ ] **Run OrthoHMM pipeline**: Execute on species dataset when genomesDB output available
- [ ] **Run Broccoli pipeline**: Execute on species dataset when genomesDB output available
- [ ] **Run comparison pipeline**: After at least 2 tools complete
- [ ] **Write methods document**: Create methods-orthogroups.md for the new architecture

---

## Previous Issues (Resolved by Redesign)
- ~~File naming convention inconsistency (RUN_ vs RUN-)~~ → All use RUN-workflow.*
- ~~Broccoli implementation pending~~ → Fully implemented
- ~~OrthoFinder missing Nextflow pipeline~~ → Fully implemented
- ~~No cross-method comparison~~ → BLOCK_comparison/ project created
- ~~Inconsistent output formats~~ → All tools produce identical standardized output
