<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Guard rails for AIs working inside .claude/ — the single
         deliberate exception to "no .claude/ in github".
History:
  2026-05-25  Initial version.
============================================================================ -->

# `.claude/` — AI Guide

This directory exists only to register the PreCompact hook (see
`README.md` in this directory). It is **the one deliberate exception** to
the otherwise-strict "no `.claude/` in github" rule documented in
`../ai/ai_FYIs/gigantic_conventions.md` §7.

## What you should not do

- **Do not extend `.claude/` beyond the PreCompact hook config without an
  explicit user decision.** Every new file or setting added here expands
  the exception and weakens its scope.
- **Do not add `.claude/` directories elsewhere in the project tree.**
  They are gitignored everywhere except here.
- **Do not modify the hook's command path** without updating
  `../ai/ai_scripts/002_*.py` accordingly. The path
  `$CLAUDE_PROJECT_DIR/ai/ai_scripts/002_...` is the contract.

## What you should do

- If a new feature genuinely warrants a different Claude Code setting
  (a different hook, a permission, a model preference), discuss with the
  user first; document the decision in `../ai/ai_FYIs/gigantic_conventions.md`;
  then make the change here and update `README.md` to reflect it.
- If the user wants to customize their own local Claude Code behavior
  for this project (extra permissions, extra hooks), recommend they use
  `~/.claude/settings.json` (user-global) instead, so the template
  stays clean.
