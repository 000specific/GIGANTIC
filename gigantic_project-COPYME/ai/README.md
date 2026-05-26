<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Explain what lives inside ai/ at the gigantic_project-COPYME level
         and how the pieces fit into the project's chat-as-research-notebook
         and AI-infrastructure system.
History:
  2026-05-25  Initial version + final pass.
============================================================================ -->

# `ai/` — AI Infrastructure

All AI-related infrastructure for this project is consolidated here so it
is visually obvious to anyone browsing the project tree what is AI-internal
versus user-facing.

**Users normally do not need to touch anything in `ai/`** — it is for AI
assistants and the project framework itself. If you (the user) find yourself
reaching into `ai/` to do something manually, that is a signal the framework
is missing a feature; please flag it.

---

## Layout

```
ai/
├── README.md       # This file (user-facing description of ai/)
├── AI_GUIDE.md     # AI-facing operational guide for working inside ai/
├── ai_FYIs/        # Markdown notes, conventions, archives, AI-facing FYIs
└── ai_scripts/     # Python tooling — capture hook, session extractors, etc.
```

---

## `ai/ai_FYIs/`

Markdown documents intended for AI assistants to read for context, plus
archived documentation from earlier in the project's development. Files
related to a specific subproject are prefixed with the subproject name
(e.g. `phylonames-overview-old.md`, `trees_gene_groups-HANDOFF-…md`) so
they sort together.

**The canonical source of truth for project-wide conventions lives here:**
`ai/ai_FYIs/gigantic_conventions.md`. When the user says **"gcon"**, it
means "please add this to `gigantic_conventions.md`".

---

## `ai/ai_scripts/`

Python scripts that AI assistants (and occasionally the user) invoke.
Each script has a `NNN_ai-` prefix indicating it was AI-authored.

Current contents:

- **`001_ai-python-extract_claude_sessions.py`** — utility for extracting
  context-compaction *summaries* (markdown) from Claude Code's internal
  JSONL storage at `~/.claude/projects/<encoded-path>/*.jsonl`. Useful for
  human-readable session digests, but summary-based — less central than
  the lossless hook (002) and the planned raw-copy script (003).

- **`002_ai-python-hook_precompact_capture_transcript.py`** — the
  PreCompact hook for Claude Code. Registered via `.claude/settings.json`
  at this project's root (the deliberate `.claude/` shipping exception per
  `ai/ai_FYIs/gigantic_conventions.md` §7). Fires automatically before each
  context compaction; gzips the full lossless JSONL session transcript
  into `research_notebook/research_ai/sessions/`. Appends to
  `TRANSCRIPT_CAPTURE_LOG.md` in the same directory.

- **`003_ai-python-copy_session_jsonls.py`** *(planned, not yet implemented)*
  — raw-gzip-copies all of Claude Code's session JSONLs for this project
  from `~/.claude/projects/<encoded-path>/` into
  `research_notebook/research_ai/sessions/`. Closes the TTL gap (Claude
  Code default-deletes its source JSONLs after 30 days) and captures
  short sessions that never compact (and so never trigger the hook).
  This is the script invoked when the user types **"Save Chat!"** — see
  project-level `AI_GUIDE.md` for the full on-demand capture behavior.

---

## How this fits the bigger picture

The full chat-as-research-notebook architecture (lossless capture,
"Save Chat!", publication-scrub-on-copies, non-Claude AI guidance) is
documented in:

- Project root **`README.md`** — user-facing overview
- Project root **`AI_GUIDE.md`** — operational, AI-facing
- **`ai/ai_FYIs/gigantic_conventions.md`** §7 (`.claude/` exception) and
  §9 (chat-as-research-notebook) — canonical conventions

If you are extending `ai/` itself (adding a script, adding an FYI,
surfacing a new convention), see **`ai/AI_GUIDE.md`** in this directory.
