# GIGANTIC Conventions

Canonical conventions for the GIGANTIC framework. Each entry is verified against the codebase.

This file grows as conventions surface during per-directory documentation review.
At the end of cleanup, this is the source for writing the top-level `GIGANTIC/` and
`gigantic_project-COPYME/` README + AI_GUIDE pairs.

---

## 1. `research_notebook/` is a sandbox, outside GIGANTIC conventions

`research_notebook/` directories at any level (project, subproject, BLOCK/STEP) are
personal sandboxes. They have:

- **No structure requirements** — any files, any naming, any subdirectory layout
- **No naming conventions** — users organize however they like

The only hard rule: **GIGANTIC must never pull from anything inside a
`research_notebook/`.** Workflows, scripts, and pipelines treat these directories as
invisible.

If a user wants GIGANTIC to use a file that lives in their `research_notebook/`,
they symlink it into `gigantic_project-COPYME/INPUT_user/` (the canonical
project-level input directory). GIGANTIC reads from `INPUT_user/`, never from
`research_notebook/`.

This separation is what lets `research_notebook/` stay completely free-form while
GIGANTIC's reproducibility guarantees remain intact.

---

## 2. Inter-subproject data flow: `OUTPUT_pipeline/` → `output_to_input/` symlinks

Real data lives in `OUTPUT_pipeline/` inside each workflow-RUN directory. To share
specific outputs with downstream subprojects:

- A subproject exposes its sharable outputs at `<subproject>/output_to_input/`
  (lowercase `o`)
- Entries inside `output_to_input/` are **symlinks** pointing into the canonical
  `OUTPUT_pipeline/` of the appropriate `workflow-RUN_N-*` directory
- The directory structure inside `output_to_input/` (typically organized by BLOCK
  or STEP name) keeps sequential runs from overwriting each other and preserves
  clear provenance

Downstream subprojects always read from `<upstream_subproject>/output_to_input/`,
never from inside an `OUTPUT_pipeline/` directly.

**Note on a deprecated pattern**: an older CLAUDE.md described an `OUTPUT_to_input/`
(uppercase `O`) archival mirror inside each `workflow-RUN_N-*` directory. That
pattern is **not** implemented in any current GIGANTIC workflow code or
documentation — verified by full-tree grep (0 mentions in `.md`, `.nf`, `.py`,
`.sh`; 0 directories on disk inside the framework). Treat the lowercase symlink
pattern above as the only `output_to_input` convention.

---

## 3. AI guide files are always named `AI_GUIDE.md` — no suffixes

Just like README files are always `README.md`, AI guide files are always
`AI_GUIDE.md` — no descriptor suffix, no level suffix, no workflow-name suffix.

- `README.md` and `AI_GUIDE.md` are the only two doc filenames at every level
- The directory the file lives in establishes its scope (project, subproject,
  BLOCK/STEP, workflow). No need to repeat that scope in the filename.
- Old patterns like `AI_GUIDE-project.md`, `AI_GUIDE-trees_species.md`,
  `AI_GUIDE-trees_species_workflow.md`, `AI_GUIDE-phylonames_workflow.md` are
  all deprecated. Each should be renamed to `AI_GUIDE.md` in its own directory.

This convention was established earlier in development but drifted across
sessions; it is being re-enforced as part of the documentation cleanup pass.

---

## 4. The GIGANTIC repo is everything from `GIGANTIC/` downward

The GitHub-versioned project is the `GIGANTIC/` directory. Anything upstream of
it — parent directories, sibling user workspaces, lab-specific scaffolding — is
user research context and has **no relevance to GIGANTIC** or its conventions.

For example, in the development environment used to build GIGANTIC, the repo
lives inside `…/ai_ctenophores/github-gigantic_1/GIGANTIC/`. The
`ai_ctenophores/` directory is the developer's personal research workspace; it
is not part of GIGANTIC, does not constrain GIGANTIC, and does not appear in
any path users will see.

---

## 5. Paths inside `gigantic_project-COPYME/` are written relative to it

Once a path falls inside `gigantic_project-COPYME/` (or its renamed copy in a
user's project, e.g. `gigantic_project-cephalopod_evolution/`), document it
relative to that directory — not absolute, and not relative to the GIGANTIC
repo root.

- ✅ `subprojects/phylonames/STEP_1-generate_and_evaluate/`
- ✅ `ai/ai_FYIs/gigantic_conventions.md`
- ❌ `gigantic_project-COPYME/subprojects/phylonames/STEP_1-generate_and_evaluate/`
- ❌ `/blue/moroz/share/edsinger/.../gigantic_project-COPYME/subprojects/phylonames/STEP_1-generate_and_evaluate/`

This makes documentation portable across renamed project copies and across
machines. The user reads their `gigantic_project-<name>/` as the root of their
work; docs should respect that frame of reference.

---

## 6. AI-related infrastructure lives under `ai/`

All AI-related infrastructure inside `gigantic_project-COPYME/` is consolidated
under one top-level directory: `ai/`. This makes the AI plumbing visually
obvious to users browsing the project tree.

Current layout:

```
gigantic_project-COPYME/
├── ai/
│   ├── README.md                # What's in ai/
│   ├── ai_FYIs/                 # Markdown notes, conventions, archives, FYIs
│   │   └── gigantic_conventions.md
│   └── ai_scripts/              # Python tooling (capture hook, "Save Chat!" script, etc.)
│       ├── 002_ai-python-hook_precompact_capture_transcript.py
│       └── 003_ai-python-copy_session_jsonls.py
└── …
```

Anything new that is AI-internal goes under `ai/`. Anything user-facing
(`README.md`, `INPUT_user/`, `subprojects/`, etc.) stays at project root or in
its appropriate user-facing location.

---

## 7. `.claude/` exception: `gigantic_project-COPYME/.claude/` ships the capture hook + its docs

**General rule**: no `.claude/` directories anywhere in GitHub. Claude Code
session settings are developer-personal and gitignored everywhere by default.

**Deliberate exception**: `gigantic_project-COPYME/.claude/` ships **exactly
three files**, all tracked:

- `settings.json` — registers the PreCompact hook that calls
  `ai/ai_scripts/002_ai-python-hook_precompact_capture_transcript.py` to
  capture full lossless session transcripts to
  `research_notebook/research_ai/sessions/` before each context compaction.
- `README.md` — explains what this `.claude/` is and why it ships.
- `AI_GUIDE.md` — guard rails for AIs working inside `.claude/`.

Nothing else inside `gigantic_project-COPYME/.claude/` ships. The
`.gitignore` enforces this with: blanket `.claude/` ignore, then explicit
un-ignore of just these three files at this one path.

This exception exists because **Claude is the recommended AI for GIGANTIC** and
**lossless session capture is a primary GIGANTIC feature** (see §9). Without
the shipped hook config, each user would have to manually wire up capture in
their renamed project copy — defeating the "fresh AI session in renamed
project" model.

The exception is scoped tightly: only `gigantic_project-COPYME/.claude/`
ships, and only these three files inside it. `.claude/` at GIGANTIC root
and `.claude/` anywhere else stay fully gitignored.

---

## 8. AIs read `AI_*`, `CLAUDE.md`, and `README.md` on entry to any directory where they will work

At session start AND every time the working scope shifts to a new directory,
an AI should read the local guidance files if present:

- `CLAUDE.md` (Claude Code loads this automatically; other AIs should too)
- `AI_BEHAVIOR.md` (research-grade behavior; canonical, AI-agnostic)
- `AI_GUIDE.md` (how to work in this scope)
- `README.md` (project / subproject / workflow background)

"Working in a directory" means: about to edit, create, run, or otherwise
modify files in that directory or its descendants. Read-only exploration
(grep, ls, find) does not trigger this — but as soon as the AI is about to
do work, it should orient itself by reading these files.

Prevents the failure mode where an AI does 50 turns of work inside a deep
subdirectory without ever reading the local guidance, missing conventions or
constraints documented right there.

---

## 9. Chat-as-research-notebook: lossless permanent captures, never edited; "Save Chat!" for on-demand capture

Every AI chat session is treated as a research-notebook entry. The default
mechanism for Claude Code is fully automatic:

- The PreCompact hook (registered by `gigantic_project-COPYME/.claude/settings.json`)
  fires before every context compaction and gzip-copies the full JSONL
  transcript to `research_notebook/research_ai/sessions/`.
- Captures are **lossless** (full fidelity, every message, every tool call,
  every result), **permanent** (never auto-deleted by GIGANTIC), and
  **never edited** (treat as original lab-notebook entries).
- A `TRANSCRIPT_CAPTURE_LOG.md` in the sessions directory tracks each capture.

**On-demand capture via "Save Chat!"**: users can type **"Save Chat!"** to
their AI at any point to trigger an on-demand capture (the AI runs the
appropriate `ai/ai_scripts/` script). Recommended moments: at milestones,
before signoff, periodically during long sessions. AIs should also
proactively suggest capture when they sense the user is winding down
("done for the day", "let me stop here", closing-the-laptop signals) or
when a significant milestone has just completed.

**TTL gap** (worth knowing): Claude Code stores raw session JSONL at
`~/.claude/projects/<encoded-path>/*.jsonl` and auto-deletes after a default
30 days. The PreCompact hook captures only what's been through compaction.
To close the gap for short sessions that never compact:

1. Users should set `cleanupPeriodDays` to a large number in their global
   `~/.claude/settings.json` (one-line manual change), AND
2. The on-demand capture script (`ai/ai_scripts/003_ai-python-copy_session_jsonls.py`)
   raw-copies all `~/.claude/projects/...` JSONLs for this project into
   `research_notebook/research_ai/sessions/` so they survive TTL. AI runs
   it when the user types "Save Chat!" or proactively offers capture.

**Publication scrub**: captured transcripts may contain frank language, draft
hypotheses, collaborator names in unflattering context, credentials/tokens
that leaked into commands, etc. For public submission (journal supplementary
materials, etc.), make **copies** and scrub the copies. **Never modify the
originals** — they are the canonical research record.

**For non-Claude AIs** (Cursor, ChatGPT, Gemini, etc.): the principle is the
same — lossless, permanent, never-edited captures with on-demand "Save Chat!"
triggers. The mechanism differs by AI: see `AI_BEHAVIOR.md` and `AI_GUIDE.md`
in the project for AI-specific setup guidance. The non-Claude AI works with
the user to identify where their AI stores session data and to wire up an
equivalent periodic raw-copy into `research_notebook/research_ai/sessions/`.

---

<!-- Add new conventions below as they surface during per-directory review. -->
<!-- User shorthand "gcon" = "please add this to gigantic_conventions.md". -->

