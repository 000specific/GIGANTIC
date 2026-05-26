<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Explain what lives inside ai/ at the gigantic_project-COPYME level.
History:
  2026-05-25  Initial version (Opus 4.7).
============================================================================ -->

# `ai/` — AI Infrastructure

All AI-related infrastructure for this project is consolidated here so
that what is AI-internal versus user-facing is visually obvious when
browsing the project tree.

```
ai/
├── README.md       # This file
├── ai_FYIs/        # Markdown notes, conventions, archives, AI-facing FYIs
└── ai_scripts/     # Python tooling — capture hook, session extractors, etc.
```

## `ai/ai_FYIs/`

Markdown documents intended for AI assistants to read for context, plus
archived documentation from earlier in the project's development.

The canonical source of truth for project-wide conventions lives here:
`ai/ai_FYIs/gigantic_conventions.md`.

## `ai/ai_scripts/`

Python scripts that AI assistants (and occasionally the user) invoke.
Each script has a `NNN_ai-` prefix indicating it was AI-authored.

Current contents:

- **`002_ai-python-hook_precompact_capture_transcript.py`** — the
  PreCompact hook for Claude Code. Registered via `.claude/settings.json`
  at this project's root. Fires automatically before each context
  compaction; gzips the full lossless JSONL session transcript into
  `research_notebook/research_ai/sessions/`.

- **`001_ai-python-extract_claude_sessions.py`** — utility for extracting
  context compaction summaries (markdown) from Claude Code's internal
  JSONL storage at `~/.claude/projects/<encoded-path>/*.jsonl`. Less
  central than the hook since the hook captures full transcripts, but
  useful for human-readable session digests.

For the full architecture of how these pieces fit together and the
overall chat-as-research-notebook system, see `AI_GUIDE.md` and
`README.md` at the project root, plus
`ai/ai_FYIs/gigantic_conventions.md` §9.

## Users should not need to touch anything in `ai/`

This directory is for AI assistants and the project framework. If you
(the user) find yourself reaching into `ai/` to do something manually,
that is a signal that the framework is missing a feature — please flag
it.
