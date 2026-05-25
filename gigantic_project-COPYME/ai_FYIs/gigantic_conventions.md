# GIGANTIC Conventions

Canonical conventions for the GIGANTIC framework. Each entry is verified against the codebase.

This file grows as conventions surface during per-directory documentation review.
At the end of cleanup, this is the source for writing the top-level `GIGANTIC/` and
`gigantic_project-COPYME/` README + AI_GUIDE pairs.

---

## 1. `research_notebook/` is a sandbox, outside GIGANTIC conventions

`research_notebook/` directories at any level (project, subproject, BLOCK/STEP) are
personal sandboxes. They have:

- **No structure requirements** — any files, any naming, any subdirectory layout
- **No naming conventions** — users organize however they like

The only hard rule: **GIGANTIC must never pull from anything inside a
`research_notebook/`.** Workflows, scripts, and pipelines treat these directories as
invisible.

If a user wants GIGANTIC to use a file that lives in their `research_notebook/`,
they symlink it into `gigantic_project-COPYME/INPUT_user/` (the canonical
project-level input directory). GIGANTIC reads from `INPUT_user/`, never from
`research_notebook/`.

This separation is what lets `research_notebook/` stay completely free-form while
GIGANTIC's reproducibility guarantees remain intact.

---

## 2. Inter-subproject data flow: `OUTPUT_pipeline/` → `output_to_input/` symlinks

Real data lives in `OUTPUT_pipeline/` inside each workflow-RUN directory. To share
specific outputs with downstream subprojects:

- A subproject exposes its sharable outputs at `<subproject>/output_to_input/`
  (lowercase `o`)
- Entries inside `output_to_input/` are **symlinks** pointing into the canonical
  `OUTPUT_pipeline/` of the appropriate `workflow-RUN_N-*` directory
- The directory structure inside `output_to_input/` (typically organized by BLOCK
  or STEP name) keeps sequential runs from overwriting each other and preserves
  clear provenance

Downstream subprojects always read from `<upstream_subproject>/output_to_input/`,
never from inside an `OUTPUT_pipeline/` directly.

**Note on a deprecated pattern**: an older CLAUDE.md described an `OUTPUT_to_input/`
(uppercase `O`) archival mirror inside each `workflow-RUN_N-*` directory. That
pattern is **not** implemented in any current GIGANTIC workflow code or
documentation — verified by full-tree grep (0 mentions in `.md`, `.nf`, `.py`,
`.sh`; 0 directories on disk inside the framework). Treat the lowercase symlink
pattern above as the only `output_to_input` convention.

---

<!-- Add new conventions below as they surface during per-directory review. -->
