<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Operational guide for any AI assistant working inside ai/. Covers
         what to do when adding a script, adding an FYI, surfacing a
         convention, or invoking the existing capture scripts.
Scope:   gigantic_project-COPYME/ai/ and everything inside it.
History:
  2026-05-25  Initial version.
============================================================================ -->

# `ai/` — AI Guide (working inside the AI-infrastructure directory)

You are working inside `ai/` — the consolidated AI infrastructure for this
project. For the **what's-here** view, read `README.md` next to this file.
This guide tells you **how to operate inside `ai/`**.

If you are also new to the project as a whole, read these first (project
root, parent directory):

- `../README.md` and `../AI_GUIDE.md` — project orientation
- `../AI_BEHAVIOR.md` — research-grade posture (canonical; Claude Code
  loads it via `../CLAUDE.md`'s `@`-import)
- `ai_FYIs/gigantic_conventions.md` — canonical conventions list

---

## Most common reasons you (the AI) work in `ai/`

| Task | Go to | Notes |
|---|---|---|
| User typed **"Save Chat!"** | `ai_scripts/` | Invoke the on-demand capture script (`003_*.py` when implemented; currently fall back to `001_*.py` for summary extraction and confirm with user) |
| A new project-wide convention surfaced in conversation | `ai_FYIs/gigantic_conventions.md` | Append a new `## §N — ...` section following the established style; quote the source if it came from a specific design discussion |
| A new AI-facing note / FYI needs storing | `ai_FYIs/<subproject>-<descriptor>.md` (or `<scope>-<descriptor>.md` for project-wide) | Use subproject-first naming so related FYIs sort together |
| A new capture/utility script is needed | `ai_scripts/NNN_ai-python-<descriptor>.py` | Use the next `NNN` number; include the AI-attribution header; document in `ai/README.md` |
| Updating a script (bugfix, refactor) | `ai_scripts/` | Preserve the existing AI-attribution header; add a History line |

---

## When you add or modify a script in `ai_scripts/`

1. Use the `NNN_ai-<lang>-<descriptor>` filename convention (e.g.
   `003_ai-python-copy_session_jsonls.py`).
2. Open with the AI-attribution comment block (model, date, human, purpose).
3. Reference the script in `ai/README.md` so the catalogue stays accurate.
4. If the script is meant to be invoked by a hook, register the hook in
   the appropriate `.claude/settings.json` and document the registration in
   the script's docstring (see `002_*.py` for the pattern).

## When you add or modify a doc in `ai_FYIs/`

1. Use subproject-prefixed naming where the doc is subproject-specific
   (`<subproject>-<descriptor>.md`). Leave project-wide docs unprefixed.
2. If the doc is an archived version of a now-deprecated doc, suffix
   `-old` (e.g. `phylonames-overview-old.md`).
3. Do NOT alter `gigantic_conventions.md` casually — it is the canonical
   source of truth. Only add new `## §N` sections when conventions are
   confirmed; quote the source / design discussion in the section body
   where useful.

---

## The `.claude/` exception (worth being aware of)

`ai_scripts/002_ai-python-hook_precompact_capture_transcript.py` is
registered as a PreCompact hook by `../.claude/settings.json`. That
`.claude/` directory is the **one deliberate exception** to the otherwise
strict "no `.claude/` in github" rule, because lossless session capture is
a primary GIGANTIC feature and shipping the hook config means users get
provenance capture automatically when they `cp -r` the template. See
`ai_FYIs/gigantic_conventions.md` §7 for the full rationale.

Do not extend the `.claude/` directory beyond the PreCompact hook config
without an explicit user decision. Any new shipped Claude-specific config
expands the exception and must be justified.

---

## Things NOT to do inside `ai/`

- Do not move scripts/docs out of `ai/` to project root. The whole point
  of `ai/` is to keep AI infrastructure visually separated.
- Do not edit captured transcripts in
  `../research_notebook/research_ai/sessions/`. Those are originals (see
  `gigantic_conventions.md` §9 and `../AI_BEHAVIOR.md`).
- Do not add user-facing tools here. If a tool is meant for the user to
  run directly during research (not for AI orchestration), it belongs in
  a project-root `RUN-*.sh` or inside the relevant subproject.
