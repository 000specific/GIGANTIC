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
   script: `python3 ai/ai_scripts/003_ai-python-copy_session_jsonls.py`
   (pass `--dry-run` first if you want to preview without writing). Print
   the script's summary back to the user so they can see what was
   captured.
2. **Proactively suggest "Save Chat!"** at meaningful moments:
   - Right after a significant milestone (decision, breakthrough, big
     code change committed)
   - When the user signals winding down ("done for the day", "let me
     stop here", "I'll come back tomorrow")
   - Periodically during long sessions
3. **Recommend the user set `cleanupPeriodDays` high** in their global
   `~/.claude/settings.json` so the source JSONLs survive long enough for
   "Save Chat!" to capture them. Recommended value: `3650` (10 years —
   effectively never auto-delete during a typical project lifespan).
   Concrete snippet to add or merge into `~/.claude/settings.json`:
   ```json
   {
     "cleanupPeriodDays": 3650
   }
   ```
   If `~/.claude/settings.json` already has other top-level keys, merge
   `cleanupPeriodDays` in alongside them rather than overwriting the file.

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
supplementary materials, public archive, AI-disclosure appendix, etc.),
they will want to scrub copies of selected transcripts. The full
walkthrough — categories to scrub, choice of output format, the
`SCRUB_NOTES.md` template — is in
[`ai/ai_FYIs/publication_scrub_guide.md`](ai/ai_FYIs/publication_scrub_guide.md).
Read that with the user before starting a scrub; never improvise.

The originals in `research_notebook/research_ai/sessions/` are **never**
touched. Scrubbing always happens on copies kept in
`research_notebook/research_user/publication-<paper-name>/chat-captures-scrubbed/`
(or similar user-sandbox location).

### For non-Claude AIs (Cursor, ChatGPT/Codex, Gemini, etc.)

The principle is the same: lossless, permanent, never-edited captures into
`research_notebook/research_ai/sessions/`. The mechanism differs by AI.
Here is the concrete starting point for each (verified as of May 2026 — verify
with current vendor docs since storage layouts evolve):

| AI | Where transcripts live | Format | Native export |
|----|------------------------|--------|---------------|
| **OpenAI Codex CLI** | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | JSONL (full conversation + tool calls + tool results, timestamped) | No native export command as of May 2026; raw-copy the JSONLs |
| **Gemini CLI** | (in-memory by default; can `--resume`) | n/a until exported | `/export jsonl` or `/export markdown` (built-in command); pass `--output <path>` to write to a file |
| **Cursor IDE** | `~/.cursor/projects/` + `state.vscdb` (SQLite) | mixed: transcripts + SQLite blobs | No simple native export; transcripts must be reconstructed from SQLite |
| **Cursor CLI** | `~/.cursor/chats/` | JSONL-ish | No native export; raw-copy |
| **Cursor ACP mode** | `~/.cursor/acp-sessions/` | similar | No native export; raw-copy |

For each AI you use in this project:

1. **Locate the storage path** above on the user's machine (or verify with
   current vendor docs).
2. **Set up a Save-Chat! script** in `ai/ai_scripts/` modeled on
   `003_ai-python-copy_session_jsonls.py`. Use a `NNN_ai-python-` prefix
   (next available number) and the convention
   `save_chat_<ai_name>.py` for clarity.
3. **Document the AI's setup in `ai/ai_FYIs/`** as
   `<ai_name>-chat_capture_setup.md` so the provenance system is fully
   described regardless of which AI was used.
4. **Recognize "Save Chat!"** as a trigger and run the appropriate script
   when the user types it.

For AIs without filesystem-level session storage (e.g., ChatGPT in a web
browser without an API/CLI hook), the user must manually export each
conversation via the AI's UI and drop the export into
`research_notebook/research_ai/sessions/`. Help them with naming
(`YYYYMMDD_HHMMSS-<ai_name>-<topic>.<ext>`) and document the manual
workflow in `ai/ai_FYIs/`.

This is a real piece of work to set up the first time per AI. Captured
chat history may be the difference between a reproducible project and an
irreproducible one — worth the setup cost.

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

---

## Session hygiene (per §61 in `ai/ai_FYIs/gigantic_conventions.md`)

GIGANTIC's chat-as-research-notebook convention (§9) works best with
disciplined session hygiene. Two recommendations.

### Always root at the named gigantic_project-COPYME

Every chat session for project work should be initiated rooted at the
user's renamed copy of `gigantic_project-COPYME/` — e.g.,
`gigantic_project-cephalopod_evolution/`.

**Not** at:
- `GIGANTIC/` (the framework root, reserved for framework-development
  sessions per §16)
- `subprojects/<X>/` (a subproject directory)
- `subprojects/<X>/<BLOCK_or_STEP>/workflow-COPYME-*/` (a workflow directory)
- Any other directory deeper than the named project root

Why: the renamed project copy is the canonical session root. All
project conventions, INPUT_user paths, research_notebook captures,
and AI guidance are scoped to that directory. Rooting deeper than
that scopes the AI's view too narrowly and loses cross-subproject
context (and the AI guides at lower levels assume the session was
rooted above them). Rooting at `GIGANTIC/` is reserved for
framework-development sessions per §16.

### One chat session per subproject + a side channel for small questions

For productive project work:

- **One session per subproject** you're actively working in. A session
  focused on `phylonames/` is different from one focused on
  `genomesDB/` is different from one focused on `trees_species/` —
  each maintains its own context, convention reminders, and recent
  state.
- **Continue the same session over many compactions** until it
  becomes overly reactive, muddled, or slow. Compactions are
  lossless (per §9 the full transcript is captured), so a long
  session isn't a problem until it starts feeling like one.
- **When a session goes muddled, start a fresh one** at the same
  named `gigantic_project-*/` root, focused on the same subproject,
  and bring it back up to speed (read the relevant AI_GUIDEs, recent
  commits, etc.).
- **Keep a separate "small questions" session** for random or
  cross-cutting questions (e.g., "what does this convention mean?"
  or "is this NCBI accession a GCF or GCA?"). This keeps the
  subproject sessions focused on their actual work and prevents
  context pollution.

### What this prevents

- Sessions that try to hold every subproject's state in context and
  end up confused about which one they're operating on.
- Sessions that get derailed by one-off questions and lose their
  thread on the subproject work.
- Session captures (per §9) that mix multiple unrelated subprojects
  into a single transcript, making the lab-notebook record harder
  to grep later.
