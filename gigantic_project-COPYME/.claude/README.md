<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Explain what this directory is and why it ships (it is the
         deliberate exception to the "no .claude/ in github" rule).
History:
  2026-05-25  Initial version.
============================================================================ -->

# `.claude/`

This directory contains a single file, `settings.json`, which registers
Claude Code's **PreCompact hook** for this project. The hook calls
`../ai/ai_scripts/002_ai-python-hook_precompact_capture_transcript.py`
before each context compaction, gzip-copying the full lossless session
transcript into `../research_notebook/research_ai/sessions/`.

## Why this `.claude/` ships in github

The general GIGANTIC rule is **no `.claude/` directories anywhere in
github** — Claude Code session settings are developer-personal and
gitignored everywhere by default.

`gigantic_project-COPYME/.claude/` is the **single deliberate exception**.
Lossless session capture is a primary GIGANTIC feature, so the hook
config ships with the template — every user who copies and renames the
template gets the capture system automatically, no manual setup required.

See `../ai/ai_FYIs/gigantic_conventions.md` §7 for the full rationale and
`../ai/AI_GUIDE.md` for what AIs should and should not do here.
