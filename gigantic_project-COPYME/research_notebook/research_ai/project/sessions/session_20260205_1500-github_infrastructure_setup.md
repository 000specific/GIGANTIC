# Session Documentation: GIGANTIC GitHub Infrastructure Setup

**Date**: 2026 February 05
**AI Model**: Claude Opus 4.5 (claude-opus-4-5-20251101)
**Interface**: Claude Code within Cursor IDE
**Human Collaborator**: Eric Edsinger

---

## Session Overview

This session focused on establishing the GIGANTIC GitHub repository infrastructure, implementing AI-native design patterns, and creating the `gigantic_project-COPYME` template structure for users.

---

## Key Accomplishments

### 1. Established AI-Native Design Philosophy

- Updated main README.md with humble framing of GIGANTIC's AI-native approach
- Positioned as "exploring what research software looks like when AI assistance is assumed"
- Emphasized learning as we go, inviting community feedback

### 2. Context-Aware AI_GUIDE Naming Convention

Implemented naming pattern that allows users to direct AI assistants to specific documentation:

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `AI_GUIDE.md` (project) | `AI_GUIDE-project.md` | High-level project guidance |
| `AI_GUIDE.md` (phylonames) | `AI_GUIDE-phylonames.md` | Subproject-level guidance |
| `AI_GUIDE.md` (workflow) | `AI_GUIDE-phylonames_workflow.md` | Workflow-level guidance |

**Benefit**: Users can say "read AI_GUIDE-phylonames.md" and the AI knows exactly which file to consult.

### 3. Consolidated research_ai Structure

Replaced scattered per-subproject `gigantic_ai/ai_documentation/` folders with a single consolidated structure in `research_notebook/research_ai/`:

```
research_notebook/research_ai/
├── project/                           # Project-level sessions
│   ├── sessions/
│   ├── validation/
│   ├── logs/
│   └── debugging/
├── subproject-phylonames/             # Phylonames AI documentation
│   ├── sessions/
│   ├── validation/
│   ├── logs/
│   └── debugging/
├── subproject-genomesDB/              # GenomesDB AI documentation
├── subproject-annotations_hmms/
├── subproject-orthogroups/
├── subproject-trees_species/
├── subproject-trees_gene_families/
├── subproject-orthogroups_X_ocl/
└── subproject-annotations_X_ocl/
```

**Philosophy**: "AI sessions ARE research" - like lab notebooks on a shelf, one for each subproject.

### 4. Phylonames Subproject Structure

Completed the phylonames subproject implementation with:

- `AI_GUIDE-phylonames.md` at subproject root
- `nf_workflow-TEMPLATE_01-generate_phylonames/` workflow template containing:
  - `ai_scripts/` directory with numbered Python/Bash scripts
  - `INPUT_user/` for user-provided species lists
  - `output/` with subdirectories for each script's output
  - `output_to_input/` for inter-subproject data sharing
  - `RUN_phylonames.sh` execution script
  - `config.yaml` configuration
  - `AI_GUIDE-phylonames_workflow.md` workflow-level guidance

---

## Key Design Decisions

### Research Notebook Philosophy

- `research_user/`: Complete freedom for user's personal organization
- `research_ai/`: Structured AI documentation organized by subproject
- Separation ensures AI-generated content is clearly identified while preserving user flexibility

### Phyloname Terminology Clarification

| Term | Format | Use Case |
|------|--------|----------|
| `phyloname` | `Kingdom_Phylum_Class_Order_Family_Genus_species` | Data tables, analysis |
| `phyloname_taxonid` | Same with `___taxonID` appended | File naming (guarantees uniqueness) |

### Script Output Transparency

All scripts write to `output/N-output/` directories to enable human inspection of intermediate results - essential for reproducibility and debugging.

---

## Resolved Issues

### 1. OUTPUT_to_input Duplication - RESOLVED

**Issue**: Workflow templates contained `OUTPUT_to_input/` but there should only be ONE `output_to_input/` per subproject at the subproject root.

**Solution Implemented**:
- Removed `OUTPUT_to_input/` and `OUTPUT_pipeline/` from workflow templates
- Single `output_to_input/` directory at subproject root for inter-subproject sharing
- Updated RUN_phylonames.sh to write to `../output_to_input/maps/`

### 2. NextFlow Output Organization - RESOLVED

**Issue**: NextFlow's default `work/` directory hierarchy is cryptic and makes human inspection difficult.

**Research Findings** (from NextFlow documentation):
- `publishDir` directive copies outputs from work directory to specified location
- Multiple `publishDir` can target different directories based on different rules
- Best practice: Use `mode: 'copy'` for research reproducibility
- Modern approach uses workflow outputs, but `publishDir` is still widely used

**Solution Implemented**:
- Created `output/1-output/`, `output/2-output/`, `output/3-output/` directories
- Scripts write to their numbered output directories (e.g., Script 002 writes to `output/2-output/`)
- Final outputs that need inter-subproject sharing go to `../output_to_input/`
- All intermediate outputs are human-inspectable at `output/N-output/`

**GIGANTIC Transparency Principle**: Every script's output is visible in a numbered directory, enabling step-by-step verification.

---

## Files Created/Modified

### Created

1. `research_notebook/research_ai/README.md` - Consolidated structure documentation
2. `research_notebook/research_ai/project/` - Project-level documentation folders
3. `research_notebook/research_ai/subproject-*/` - Per-subproject documentation folders
4. This session documentation

### Modified

1. `GIGANTIC/README.md` - Added Design Philosophy section
2. `AI_GUIDE-project.md` - Updated with consolidated research_ai structure
3. `AI_GUIDE-phylonames.md` - Updated script paths
4. `AI_GUIDE-phylonames_workflow.md` - Updated parent reference
5. `RUN_phylonames.sh` - Updated script paths to `ai_scripts/`

### Removed

1. `nf_workflow-TEMPLATE_01-generate_phylonames/gigantic_ai/` - Moved to consolidated location

---

## Completed This Session

1. Researched NextFlow publishDir best practices for output organization
2. Designed solution providing transparency with `output/N-output/` directories
3. Removed `OUTPUT_to_input/` and `OUTPUT_pipeline/` from workflow templates
4. Implemented proper output organization pattern
5. Updated RUN_phylonames.sh with correct paths
6. Updated AI_GUIDE-phylonames_workflow.md with output structure documentation
7. Updated CLAUDE.md with correct file references
8. **Initial GitHub push** - Commit `3114c5f` (129 files, 2,690 insertions)
9. **Added "Honesty About Mistakes" principle** to all AI_GUIDE files and CLAUDE.md
10. **Implemented softlinks pattern** for output_to_input to avoid data duplication

## GitHub Commits This Session

| Commit | Description |
|--------|-------------|
| `3114c5f` | Add gigantic_project-COPYME template with AI-native infrastructure |
| `ce06ff6` | Add honesty principle to AI_GUIDE and CLAUDE.md files |

## Key Decisions Made

### 1. Acronym Discussion
User considered changing "Genome Integration and Gene Analysis" to "Genomes Integration and Genes Analyses" for scale emphasis. Decision: **Keep singular** - reads more naturally as compound nouns, scale already communicated by "GIGANTIC" and "Numerous".

### 2. Softlinks for Data Sharing - IMPLEMENTED
Implemented symlinks to avoid data duplication:
- **Active work**: Symlinks from `output_to_input/` pointing to `output/N-output/` files
- **Archiving**: Dereference symlinks with `cp -L` or `rsync -L`
- **Implementation**: RUN_phylonames.sh now writes actual file to `output/3-output/` and creates symlink in `../output_to_input/maps/`
- **Pattern**: Uses relative paths for portability (`../../workflow_dir/output/3-output/filename`)

### 3. Honesty About Mistakes Principle
AI made an error (said "confusing" instead of "incorrect"). User correctly identified this as whitewashing. Added explicit guidance to all AI_GUIDE files:
- Say "I was incorrect" not "that was confusing"
- Acknowledge mistakes clearly without minimizing language
- Critical for scientific reproducibility and trust

## Remaining Next Steps (Future Sessions)

1. Add SLURM option to each nf_workflow template
2. ~~Implement softlinks for large data in output_to_input~~ - DONE
3. Add post-workflow cleanup for temporary directories
4. Review AI_GUIDE depth after initial GitHub push
5. Discuss demo data strategy

---

## Session Notes

This session represents an important milestone in GIGANTIC's development - establishing the infrastructure patterns that will be used across all subprojects. The consolidated research_ai structure and context-aware AI_GUIDE naming are foundational decisions that support GIGANTIC's goal of democratizing phylogenomics through AI assistance.

The user emphasized: "this could be a really early example of a complex AI-user driven research tool - and this can be a part of the importance of GIGANTIC for publication"

### Lesson Learned: Honesty in Error Acknowledgment

During this session, the AI said "my original statement was confusing" when the correct statement was "I was incorrect." The user rightly called this out as whitewashing. This led to adding explicit guidance about honest error acknowledgment to all AI_GUIDE files - a valuable contribution to GIGANTIC's AI collaboration standards.
