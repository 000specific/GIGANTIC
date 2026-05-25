<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Orient AI assistants landing in the GIGANTIC framework repository on
         what this directory is, how users use it, and where AI sessions
         should actually be rooted for project work.
Scope:   GIGANTIC/ root (the github-versioned framework repository). For
         project work, the canonical AI session root is the user's renamed
         copy of gigantic_project-COPYME/.
History:
  2026-05-25  Initial version (Opus 4.7). First fill of this file as part of
              the documentation cleanup pass. Intentionally minimal — will be
              expanded as the cleanup pass progresses.
============================================================================ -->

# GIGANTIC — AI Guide

You are reading the AI guide at the root of the **GIGANTIC framework
repository**. This file orients AI assistants on what this directory is, how
users use it, and — most importantly — **where the canonical AI session for
real project work should be rooted**.

---

## What this directory is

`GIGANTIC/` is the GitHub-versioned framework repository. When a user clones
the repo from GitHub, they get this directory tree. It contains:

- `gigantic_project-COPYME/` — the project template the user copies and
  renames; everything the user actually runs lives inside this template
- Standard repository files (`LICENSE`, `CITATION.cff`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `.github/`)
- Branding assets, a demo placeholder
- This file (`AI_GUIDE.md`) and its user-facing companion (`README.md`)

`GIGANTIC/` itself is not where a user does science. It is the framework. It
ships; the user copies it.

---

## How a user starts

1. **Clone** the repository from GitHub:
   ```
   git clone https://github.com/000specific/GIGANTIC.git
   ```
2. **Copy and rename** `gigantic_project-COPYME/` to a project-specific name,
   placing the copy outside `GIGANTIC/` so the framework and the user's
   project stay cleanly separated:
   ```
   cp -r GIGANTIC/gigantic_project-COPYME /path/to/work/gigantic_project-cephalopod_evolution
   ```
3. **Start a fresh, naive AI session rooted at the renamed project
   directory.** This is the canonical session root for every subsequent piece
   of work in that project. The user does not run an AI session at
   `GIGANTIC/` for project work; they run it at
   `gigantic_project-cephalopod_evolution/` (or whatever they named the copy).

---

## Why the AI session should be rooted at the renamed project

- Every project-level convention, input, output, `research_notebook/`,
  workflow, and AI session record lives inside the renamed project directory.
- The renamed directory is self-contained: it travels independently of
  `GIGANTIC/` and can be archived as the complete record of one research
  project.
- A fresh AI session rooted there starts with the right scope. It does not
  need to filter framework-development context out of every response.

---

## When you (the AI) are rooted at `GIGANTIC/`

Your job in a session rooted here is **framework development** — improving
the template, the conventions, the top-level docs — not project work.

If a user opens a session at `GIGANTIC/` and asks you to run analyses, set
up inputs, or work with their data, redirect them:

1. Ask them to copy and rename `gigantic_project-COPYME/` to a
   project-specific directory.
2. Ask them to start a fresh AI session rooted at that renamed directory.
3. Point them at `gigantic_project-<their-name>/AI_GUIDE.md` (which exists in
   their copy) to continue.

---

*The canonical list of conventions surfaced during the ongoing documentation
cleanup lives at
[`gigantic_project-COPYME/ai_FYIs/gigantic_conventions.md`](gigantic_project-COPYME/ai_FYIs/gigantic_conventions.md).*
