# Research Notebook

**Your project's research documentation hub.**

---

## Philosophy

**AI sessions ARE research.**

Working with an AI assistant on computational biology is equivalent to working at the bench. It produces results, insights, and decisions that need to be documented - just like wet-lab experiments.

This directory is your research notebook for AI-assisted computational work.

---

## Structure

```
research_notebook/
├── research_user/     # Your personal workspace (no structure requirements)
└── research_ai/       # AI-generated documentation (structured)
```

### `research_user/`

**Your playground.** Use it for anything:
- Personal notes
- Literature references
- Draft manuscripts
- Meeting notes
- Exploratory analyses

Organize it however works for you.

**Subproject-specific directories** can be created here:
```
research_user/
├── subproject-phylonames/     # Phylonames-related personal work
├── subproject-genomesDB/      # GenomesDB-related personal work
└── [your organization]
```

### Flexibility: Where to Put Your Work

GIGANTIC gives you two options for personal research files:

| Location | Use When |
|----------|----------|
| `subprojects/[name]/user_research/` | You want work close to the subproject |
| `research_notebook/research_user/subproject-[name]/` | You prefer centralized organization |

**Both are valid.** Use whichever works for you, or both.

**Post-project consolidation**: When archiving, you can move `user_research/` contents from subprojects to the centralized research notebook.

### `research_ai/`

**AI session provenance** - a single flat `sessions/` directory for all AI session extractions across the entire project. Sessions can span subprojects, so they're kept together rather than split.

Workflow-specific logs and validation now live inside each workflow directory (`workflow-COPYME-*/logs/` and `workflow-COPYME-*/validation/`).

See `research_ai/README.md` for complete details.

---

## Why Separate?

- Your personal organization stays unconstrained
- AI-generated content is clearly identified
- Both are preserved for scientific record
- Easy to find what you need
