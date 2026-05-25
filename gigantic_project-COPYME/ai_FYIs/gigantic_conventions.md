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

## 3. AI guide files are always named `AI_GUIDE.md` — no suffixes

Just like README files are always `README.md`, AI guide files are always
`AI_GUIDE.md` — no descriptor suffix, no level suffix, no workflow-name suffix.

- `README.md` and `AI_GUIDE.md` are the only two doc filenames at every level
- The directory the file lives in establishes its scope (project, subproject,
  BLOCK/STEP, workflow). No need to repeat that scope in the filename.
- Old patterns like `AI_GUIDE-project.md`, `AI_GUIDE-trees_species.md`,
  `AI_GUIDE-trees_species_workflow.md`, `AI_GUIDE-phylonames_workflow.md` are
  all deprecated. Each should be renamed to `AI_GUIDE.md` in its own directory.

This convention was established earlier in development but drifted across
sessions; it is being re-enforced as part of the documentation cleanup pass.

---

## 4. The GIGANTIC repo is everything from `GIGANTIC/` downward

The GitHub-versioned project is the `GIGANTIC/` directory. Anything upstream of
it — parent directories, sibling user workspaces, lab-specific scaffolding — is
user research context and has **no relevance to GIGANTIC** or its conventions.

For example, in the development environment used to build GIGANTIC, the repo
lives inside `…/ai_ctenophores/github-gigantic_1/GIGANTIC/`. The
`ai_ctenophores/` directory is the developer's personal research workspace; it
is not part of GIGANTIC, does not constrain GIGANTIC, and does not appear in
any path users will see.

---

## 5. Paths inside `gigantic_project-COPYME/` are written relative to it

Once a path falls inside `gigantic_project-COPYME/` (or its renamed copy in a
user's project, e.g. `gigantic_project-cephalopod_evolution/`), document it
relative to that directory — not absolute, and not relative to the GIGANTIC
repo root.

- ✅ `subprojects/phylonames/STEP_1-generate_and_evaluate/`
- ✅ `ai_FYIs/gigantic_conventions.md`
- ❌ `gigantic_project-COPYME/subprojects/phylonames/STEP_1-generate_and_evaluate/`
- ❌ `/blue/moroz/share/edsinger/.../gigantic_project-COPYME/subprojects/phylonames/STEP_1-generate_and_evaluate/`

This makes documentation portable across renamed project copies and across
machines. The user reads their `gigantic_project-<name>/` as the root of their
work; docs should respect that frame of reference.

---

<!-- Add new conventions below as they surface during per-directory review. -->
<!-- User shorthand "gcon" = "please add this to gigantic_conventions.md". -->

