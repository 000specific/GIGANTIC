<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: AI-facing guide for INPUT_user — the single staging arena where
         the user makes outside data available to GIGANTIC subprojects.
History:
  2026-05-25  Initial version.
============================================================================ -->

# `INPUT_user/` — AI Guide

This directory is the **single staging arena** through which the user
makes outside data available to GIGANTIC subprojects. There is no other.

Read `README.md` next to this file for the user-facing description and the
conventional structure. This guide tells you how to **operate as an AI
inside `INPUT_user/`**.

---

## The cardinal rule

**Real data files live in `../research_notebook/research_user/`. `INPUT_user/`
contains only symlinks to those files (and documentation).**

When the user wants you to bring outside data into GIGANTIC, the sequence
is always:

1. Place / download / format the file inside
   `../research_notebook/research_user/` (the user's sandbox; no
   constraints there).
2. Create a relative symlink from the appropriate location in
   `INPUT_user/` to the file in the sandbox:
   ```
   cd <INPUT_user_subdir>
   ln -srf ../../research_notebook/research_user/<path>/<file> <link-name>
   ```
   `-s` symbolic, `-r` relative (resolves the path relative to the link
   location), `-f` overwrite if existing.
3. Confirm with `ls -la` and `find INPUT_user -xtype l` (catches broken
   symlinks).

---

## What you should NOT do

- **Do not place real data files inside `INPUT_user/`.** They go in
  `../research_notebook/research_user/`. `INPUT_user/` is symlinks (plus
  docs) only.
- **Do not create absolute symlinks.** Use `ln -srf` for relative ones.
  Absolute symlinks break when the project moves to another machine, gets
  archived, or is cloned to a new location.
- **Do not reach into `../research_notebook/research_user/` to read files
  on behalf of a GIGANTIC subproject.** Always go through `INPUT_user/`,
  per gigantic_conventions §1. Subprojects read `INPUT_user/`; the user's
  sandbox is invisible to them.
- **Do not commit anything from `INPUT_user/` except documentation.** The
  `.gitignore` already ignores everything except `*.md` files at any
  depth under `INPUT_user/`. If you find yourself tempted to track a
  user's content file, stop and ask the user.
- **Do not silently change the conventional structure** (`species_set/`,
  `genomic_resources/{genomes,proteomes,annotations,maps}/`, `phylonames/`).
  Subprojects depend on the current layout. If a new subproject needs
  a different layout, surface the proposed change to the user and
  document it in the subproject's docs *and* update `README.md` here.

---

## What you should do

- **Walk the user through the symlink pattern.** New users won't know the
  staging-arena concept. Read `README.md` aloud (figuratively); offer to
  set up the sandbox + symlinks together.
- **Help with naming conventions.** Genus_species format, dash-separated
  fields in proteome FASTA headers, etc. — the user often gets these
  wrong on first pass. Verify before symlinking.
- **Audit symlinks on request.** `find INPUT_user -xtype l` for broken
  ones; `find INPUT_user -type l -exec ls -la {} \;` for all symlinks
  and their targets.
- **Surface broken symlinks loudly.** If a workflow fails with file-not-
  found referencing `INPUT_user/...`, the most likely cause is the user
  reorganized `research_notebook/research_user/` and the symlink is now
  dangling. Don't try to silently "fix" by hunting through the sandbox;
  ask the user where the file moved.

---

## When the user adds a new subproject input requirement

Sometimes a new subproject needs a new kind of input that doesn't fit the
existing structure (`species_set/`, `genomic_resources/...`, `phylonames/`).
When this happens:

1. Discuss with the user the right conventional name for the new
   subdirectory (or whether it belongs inside an existing one).
2. Add a section to `README.md` here describing the new convention.
3. Document the requirement in the subproject's own docs as well, so the
   subproject is self-explaining when read in isolation.
4. Consider whether the convention should be added to
   `../ai/ai_FYIs/gigantic_conventions.md` if it's broad enough to be
   project-wide.
