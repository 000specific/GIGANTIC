<!-- Last updated: 2026 May 25 — initial fill during documentation cleanup pass.
     This README is intentionally minimal; will be expanded as the cleanup
     progresses. -->

# GIGANTIC

**GIGANTIC** is a modular framework for AI-assisted comparative genomics and
phylogenomics. It is designed to be cloned from GitHub, copied into a renamed
project directory, and then operated through AI assistant sessions rooted at
that renamed project directory.

The mantra: **you (the user) guide an AI; the AI does the work.** GIGANTIC's
structure, conventions, and documentation are built around that model.

---

## Getting started — three steps

### 1. Clone the repository

```
git clone https://github.com/000specific/GIGANTIC.git
```

### 2. Copy and rename the project template

`gigantic_project-COPYME/` (inside the cloned `GIGANTIC/`) is the project
template. Copy it to a working location **outside** the `GIGANTIC/` clone, and
**rename it** to something specific to your research project:

```
cp -r GIGANTIC/gigantic_project-COPYME /path/to/work/gigantic_project-cephalopod_evolution
```

**Project naming convention**: `gigantic_project-<your_project_name>`.
Examples:
- `gigantic_project-cephalopod_evolution`
- `gigantic_project-early_animal_phylogenomics`
- `gigantic_project-mollusc_neural_genes`

The renamed directory is now your project. It is self-contained: every input,
workflow, output, and documentation file lives inside it. You can archive the
whole directory as the complete record of your project.

### 3. Start a fresh, naive AI assistant session rooted at the renamed project

Open a new AI assistant session (Claude Code, Cursor, ChatGPT with a
codebase-aware integration, etc.) and **root it at the renamed project
directory**, not at the cloned `GIGANTIC/` directory.

For example, if you renamed your project to
`gigantic_project-cephalopod_evolution`, your AI session should treat that
directory as its working root.

**All subsequent project work happens through AI sessions rooted at your
renamed project directory.** The `GIGANTIC/` clone is the framework; your
renamed project directory is where you actually do science.

---

## Why this structure

- **`GIGANTIC/` is the framework that gets versioned on GitHub.** It ships;
  it doesn't run.
- **Your renamed project is what runs.** It is the canonical record of your
  research project — fully reproducible, fully archivable, fully separable
  from any other project that uses GIGANTIC.
- **AI sessions rooted at the renamed project** stay focused on your project
  scope and don't have to mentally subtract framework-development context
  from every response.

---

## Where to find more

- **Project template setup, conventions, and AI guidance**: inside
  `gigantic_project-COPYME/` — specifically `README.md`, `AI_GUIDE.md`, and
  `CLAUDE.md` in that directory. Their content travels with your renamed
  copy.
- **AI-assistant-facing guidance for the framework itself**:
  [`AI_GUIDE.md`](AI_GUIDE.md) in this directory.
- **Standard repository files**: [`LICENSE`](LICENSE),
  [`CITATION.cff`](CITATION.cff), [`CONTRIBUTING.md`](CONTRIBUTING.md),
  [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

---

*Detailed documentation of subprojects, workflows, conventions, and
AI-assistant behavior lives inside `gigantic_project-COPYME/` and travels
with each renamed project copy. This top-level README is intentionally a
minimal landing page.*
