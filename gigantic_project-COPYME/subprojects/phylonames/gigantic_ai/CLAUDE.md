# CLAUDE.md - Phylonames Subproject Guidelines

**AI**: Claude Code | Opus 4.5 | 2026 February 05
**Human**: Eric Edsinger

---

## Subproject Context

This is the **phylonames** subproject of GIGANTIC. It generates standardized phylogenetic names from NCBI taxonomy.

**Dependencies**: None (this is the first subproject to run)
**Dependents**: All other GIGANTIC subprojects use phylonames

---

## AI Openness Principle

**GIGANTIC is designed for openness in AI assistance.**

When writing documentation, scripts, and guides:

1. **Use generic AI terminology**: Prefer `AI_GUIDE.md` over `CLAUDE.md` for user-facing documentation
2. **Don't assume a specific AI**: Users may use Claude, ChatGPT, Gemini, or others
3. **Write for AI readability**: Clear structure, explicit context, self-documenting formats
4. **Include troubleshooting**: Common errors and solutions that any AI can interpret
5. **Be explicit about formats**: AI assistants can parse well-documented file formats

**Exception**: Internal development guidelines (like this file) can reference specific tools since the development team uses Claude Code.

---

## Phyloname Terminology

**CRITICAL**: Always distinguish between:

- **`phyloname`**: `Kingdom_Phylum_Class_Order_Family_Genus_species` (standard format)
- **`phyloname_taxonid`**: `Kingdom_Phylum_Class_Order_Family_Genus_species___taxonID` (extended format)

These are NOT interchangeable. Use the correct term throughout.

---

## File Naming Conventions

Scripts follow GIGANTIC naming:
```
NNN_ai-TOOL-description.ext
```

Example: `001_ai-bash-download_ncbi_taxonomy.sh`

---

## Output Conventions

| Script | Output Directory |
|--------|-----------------|
| 001 | Creates database directory (versioned) |
| 002 | `output/2-output/` |
| 003 | `output_to_input/maps/` |

---

## Development Notes

This subproject was modernized from GIGANTIC_0 (legacy scripts in `/blue/moroz/share/edsinger/databases/phylonames/`) to GIGANTIC_1 (current).

**Parallel development location**: `/blue/moroz/share/edsinger/projects/ai_ctenophores/gigantic_ai/phylonames-AI_updated/`

The working implementation remains untouched while we develop the generalized version.

---

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Human documentation |
| `AI_GUIDE-phylonames.md` | AI assistant guidance (subproject level) |
| `gigantic_ai/CLAUDE.md` | Development guidelines (this file) |
| `nf_workflow-TEMPLATE_01-*/ai_scripts/` | Core phyloname generation scripts |
| `nf_workflow-TEMPLATE_01-*/` | Workflow template for users |
| `output_to_input/` | Outputs shared with downstream subprojects |

---

## Testing

Before committing changes:

1. Verify scripts run without errors (on test data)
2. Check output file formats match expected structure
3. Confirm AI_GUIDE.md accurately describes the workflow
4. Ensure README.md and AI_GUIDE.md are consistent
