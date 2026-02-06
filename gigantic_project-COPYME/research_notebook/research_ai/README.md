# research_ai - Consolidated AI Session Documentation

**All AI-assisted research documentation in one place - like sections of a lab notebook.**

---

## Philosophy

Rather than scattering AI documentation across each subproject, we consolidate it here. This makes it easy to:
- Review your complete AI collaboration history
- Find sessions related to specific subprojects
- Track project-wide decisions and progress

Think of it like a set of lab notebooks on a shelf - one for the overall project, one for each subproject.

---

## Structure

```
research_ai/
├── project/                           # Project-level AI sessions
│   ├── sessions/                      # Overall project discussions
│   ├── validation/                    # Project-wide QC
│   ├── logs/                          # Project-level logs
│   └── debugging/                     # Cross-subproject troubleshooting
│
├── subproject-phylonames/             # Phylonames AI documentation
│   ├── sessions/
│   ├── validation/
│   ├── logs/
│   └── debugging/
│
├── subproject-genomesDB/              # GenomesDB AI documentation
├── subproject-annotations_hmms/       # Annotations AI documentation
├── subproject-orthogroups/            # Orthogroups AI documentation
├── subproject-trees_species/          # Trees species AI documentation
├── subproject-trees_gene_families/    # Gene families AI documentation
├── subproject-orthogroups_X_ocl/      # OCL AI documentation
└── subproject-annotations_X_ocl/      # Annotations X OCL AI documentation
```

---

## Where to Put What

| Type of Documentation | Location |
|-----------------------|----------|
| Setting up the whole project | `project/sessions/` |
| Working on phylonames workflow | `subproject-phylonames/sessions/` |
| Validation script for orthogroups | `subproject-orthogroups/validation/` |
| Log from a trees_species run | `subproject-trees_species/logs/` |
| Debugging an OCL issue | `subproject-orthogroups_X_ocl/debugging/` |

---

## Naming Conventions

### Session Documentation
```
session_YYYYMMDD_HHMM-summary.md
```
Example: `session_20260205_1430-phylonames_setup.md`

### Validation Scripts
```
NNN_ai_validation-description.py
```
Example: `001_ai_validation-phyloname_format.py`

### Log Files
```
N_ai-log-description.log
```
Example: `2_ai-log-generate_phylonames.log`

### Debugging Records
```
DEBUG_description.md
```
Example: `DEBUG_species_not_found.md`

---

## Session Documentation Format

Each session document should include:
- Date and AI model used
- Summary of what was accomplished
- Key decisions made
- Files created or modified
- Pending items for next session

---

## For AI Assistants

When working on a specific subproject, save documentation to the appropriate `subproject-[name]/` folder:

- **Phylonames work** → `subproject-phylonames/`
- **GenomesDB work** → `subproject-genomesDB/`
- **Annotations work** → `subproject-annotations_hmms/`
- **General project discussions** → `project/`

This keeps documentation organized and findable.
