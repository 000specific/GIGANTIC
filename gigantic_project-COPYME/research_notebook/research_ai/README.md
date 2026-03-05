# research_ai - AI Session Provenance

**Project-wide record of AI-assisted research sessions.**

---

## Philosophy

AI sessions ARE research. Working with an AI assistant on computational biology produces results, insights, and decisions that need to be documented. This directory captures the AI session provenance for the entire project.

Sessions can span multiple subprojects, so we keep a single flat `sessions/` directory rather than splitting by subproject.

---

## Structure

```
research_ai/
├── README.md
└── sessions/              # All AI session extractions (project-wide)
    ├── session_YYYYMMDD_HHMM-summary.md
    └── SESSION_EXTRACTION_LOG.md
```

---

## What Goes Here vs. Workflow Level

| Type of Documentation | Location |
|-----------------------|----------|
| AI session provenance (Claude Code compaction summaries) | `research_ai/sessions/` |
| Workflow run logs (what happened during a run) | `workflow-COPYME-*/ai/logs/` or `workflow-RUN_*-*/ai/logs/` |
| Validation outputs (did a run produce correct output) | `workflow-COPYME-*/ai/validation/` or `workflow-RUN_*-*/ai/validation/` |

---

## Session Extraction

Sessions are extracted automatically by `RUN-record_project.sh` at the project root:

```bash
bash RUN-record_project.sh              # Extract all sessions
bash RUN-record_project.sh --dry-run    # Preview without changes
```

This extracts Claude Code context compaction summaries into human-readable markdown files.

---

## Naming Conventions

### Session Files
```
session_YYYYMMDD_HHMM-summary.md
```
Example: `session_20260205_1430-phylonames_setup.md`

---

## For AI Assistants

All AI session documentation goes in `sessions/` regardless of which subproject the session focused on. Workflow-specific logs and validation go in the workflow's `ai/` directory (`ai/logs/` and `ai/validation/`).
