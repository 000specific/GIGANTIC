<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Project-level AI guide for any AI assistant working inside a renamed
         gigantic_project-* directory. Operational and navigational — how to
         work in this project. Complements AI_BEHAVIOR.md (posture) and
         README.md (user-facing background).
Scope:   The renamed gigantic_project-* directory and all of its contents.
         AI sessions should be rooted at this directory (see GIGANTIC/AI_GUIDE.md
         in the framework repo for why).
History:
  2026-05-25  Initial scaffold (Opus 4.7). Contains the locked-in Human-AI
              Chat Provenance section. Remaining sections (project navigation,
              subprojects, workflows, troubleshooting) to be filled as the
              documentation cleanup pass progresses through subprojects.
============================================================================ -->

# AI Guide — Working Inside a GIGANTIC Project

You are an AI assistant working inside a renamed `gigantic_project-*`
directory. This file tells you how to navigate and operate here. For
research-grade behavior and posture, read `AI_BEHAVIOR.md` (Claude Code
loads it automatically via `CLAUDE.md`; non-Claude AIs should read it
directly). For the conventions surfaced during framework development, read
`ai/ai_FYIs/gigantic_conventions.md`.

---

## Human–AI Chat Provenance

**Every AI chat session in this project is captured as a research artifact.**
This is one of GIGANTIC's primary features: every conversation that shaped
the work is preserved as part of the scientific record — a chat-driven lab
notebook running alongside the codebase.

### Automatic capture for Claude Code (default)

When the user runs Claude Code inside this project directory, the
PreCompact hook fires automatically before every context compaction. It
gzip-copies the **full lossless JSONL transcript** (every message, tool
call, and result) into:

```
research_notebook/research_ai/sessions/
└── YYYYMMDD_HHMMSS-claude_code-MODEL-SESSION_ID.jsonl.gz
```

The hook is registered in `.claude/settings.json` (the deliberate exception
to the "no shipped `.claude/`" rule — see
`ai/ai_FYIs/gigantic_conventions.md` §7) and calls
`ai/ai_scripts/002_ai-python-hook_precompact_capture_transcript.py`.

Each capture is appended to `TRANSCRIPT_CAPTURE_LOG.md` in the same
sessions directory for human glance-through.

### On-demand capture: "Save Chat!"

The user can type **"Save Chat!"** at any point to trigger an on-demand
raw copy of every Claude Code JSONL transcript for this project from
`~/.claude/projects/<encoded-path>/*.jsonl` into
`research_notebook/research_ai/sessions/`. This closes the TTL gap for
short sessions that never compact (Claude Code default-deletes those
after 30 days).

**Your active role**:

1. **Recognize "Save Chat!"** as a trigger. Run the on-demand capture
   script in `ai/ai_scripts/` and confirm what was captured.
2. **Proactively suggest "Save Chat!"** at meaningful moments:
   - Right after a significant milestone (decision, breakthrough, big
     code change committed)
   - When the user signals winding down ("done for the day", "let me
     stop here", "I'll come back tomorrow")
   - Periodically during long sessions
3. **Recommend the user set `cleanupPeriodDays` high** in their global
   `~/.claude/settings.json` (one-line manual change) so the source JSONLs
   survive long enough for "Save Chat!" to copy them.

### Captures are originals — never edit, never delete

Captured transcripts in `research_notebook/research_ai/sessions/` are
original lab-notebook entries. They are:

- **Lossless** — full fidelity, every message, every tool call, every
  result. Gzipped for disk space; never summarized.
- **Permanent** — never auto-rotated, never auto-deleted by GIGANTIC.
- **Never edited** — if a transcript needs scrubbing for publication
  (frank language, draft hypotheses, names in unflattering context,
  credentials that leaked into commands), work on a **copy**. The
  original stays untouched.

This rule is non-negotiable. The scientific record's value is precisely
that it has not been retouched.

### Publication scrub (downstream, on copies)

When the user prepares public-facing materials from the project (journal
supplementary materials, public archive, etc.), they will want to scrub
copies of selected transcripts. Help them by:

- Copying the relevant `.jsonl.gz` files to a separate working location
  outside `research_notebook/research_ai/sessions/`.
- Walking through what should be scrubbed: collaborator names in
  unflattering context, leaked credentials or tokens, internal lab
  politics, draft hypotheses they're not ready to publish, frustrated
  language.
- Producing a curated, human-readable form (e.g., markdown summary plus
  selected raw excerpts) suited to the publication venue.
- Leaving the originals in `research_notebook/research_ai/sessions/`
  exactly as captured.

### For non-Claude AIs (Cursor, ChatGPT, Gemini, etc.)

The principle is the same: lossless, permanent, never-edited captures to
`research_notebook/research_ai/sessions/`. The mechanism differs by AI.
Work with the user to:

1. Locate where your AI stores session data (each AI has its own
   convention; check the vendor docs).
2. Set up a periodic or on-demand raw copy into
   `research_notebook/research_ai/sessions/` using a similar
   `.jsonl.gz`-style naming convention.
3. Wire "Save Chat!" as a phrase the user can type to trigger your on-demand
   capture.
4. Document your specific setup in `ai/ai_FYIs/` so the project's
   provenance system is fully described regardless of which AI was used.

This is a real piece of work to set up the first time and worth doing
properly. Captured chat history may be the difference between a
reproducible project and an irreproducible one.

---

## (Remaining sections — to be filled as the documentation cleanup pass progresses)

- Project navigation: top-level directory structure inside
  `gigantic_project-*`
- Subprojects: what they are, how they connect, dependency chain
- Workflow execution: NextFlow conventions, RUN scripts, SLURM
- INPUT_user: where user data goes
- output_to_input: how subprojects share data
- ai/: what's inside (see `ai/README.md`)
- Conventions: pointer to `ai/ai_FYIs/gigantic_conventions.md`
- Troubleshooting

*These will be filled in as we cover each layer during the documentation
cleanup pass. The Human–AI Chat Provenance section above is locked in and
will not change substantively as the rest is authored.*
