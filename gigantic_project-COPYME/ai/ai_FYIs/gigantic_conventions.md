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

## 10. Three documentation roles: CLAUDE.md, AI_GUIDE.md, README.md

Each level of the project carries up to three docs with **distinct audiences
and roles**:

| File | Audience | Role |
|------|----------|------|
| `CLAUDE.md` | AI | **Behavior / posture** in this work — research-grade, full documentation, transparency, archival, replication-enabling. *Not* technical conventions. |
| `AI_GUIDE.md` | AI | **How to work** in this directory / subproject / workflow — operational, navigational, "do X then Y." |
| `README.md` | User | **Biology + technology background**, technical specifics and requirements the user needs to know. |

Keep them in their roles. Don't drift technical conventions into `CLAUDE.md`;
don't drift user-facing background into `AI_GUIDE.md`. Each doc earns its
keep by serving exactly one audience.

---

## 11. `CLAUDE.md` is a one-line `@AI_BEHAVIOR.md` import

`AI_BEHAVIOR.md` holds the canonical research-grade behavior content (any
AI can read it directly). `CLAUDE.md` is one line — `@AI_BEHAVIOR.md` —
which Claude Code auto-loads-and-expands via its documented `@`-import
syntax. Single source of truth, no drift, no symlink fragility.

Verified Anthropic feature: `@path/to/file.md` import in CLAUDE.md is
supported (relative resolves from the file containing the import; max
5 hops of recursive imports).

---

## 12. AI attribution headers on AI-authored files

Every AI-authored script or substantive doc carries an attribution comment
block at the top. Two equivalent forms:

**Single-line (Python/bash scripts)**:
```python
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 25 | Purpose: Brief description
# Human: Eric Edsinger
```

**Multi-line HTML comment block (markdown docs)**:
```markdown
<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: One-paragraph statement of why this file exists
Scope:   What this file covers and what it does not
History:
  2026-05-25  Initial version (Opus 4.7).
============================================================================ -->
```

Markdown HTML comments are stripped by Claude Code before injection into
context, so they cost no AI context tokens.

---

## 13. Empty placeholder docs are an antipattern

Don't ship `README.md` or `AI_GUIDE.md` files that are 0 bytes or
"to-be-filled" stubs. Either fill them with real content, or delete them
and rely on the parent-directory docs.

An empty doc that other docs reference creates the worst combination:
the reader expects content (because it's referenced), opens the file, and
finds nothing. The empty-then-referenced `AI_GUIDE-project.md` in
`gigantic_project-COPYME/` and the empty `CLAUDE.md` in `GIGANTIC/` were
both surfaced and removed during the 2026-05-25 cleanup pass.

---

## 14. User flow: clone → copy template → rename → root AI session there

The canonical way to start a GIGANTIC project:

1. `git clone` the GIGANTIC repo
2. `cp -r GIGANTIC/gigantic_project-COPYME /path/outside/GIGANTIC/gigantic_project-<your-project-name>`
3. Start a **fresh, naive AI assistant session rooted at the renamed
   project directory** (not at `GIGANTIC/`)
4. All subsequent project work happens through AI sessions rooted at the
   renamed project.

Project naming convention: `gigantic_project-<your_project_name>`. The
copied directory lives **outside** the `GIGANTIC/` clone so framework
updates can be pulled without touching the user's project.

---

## 15. The renamed project directory is self-contained and archivable

Every input, output, workflow, subproject, AI session record, conda env
spec, and piece of project-specific documentation lives **inside** the
renamed `gigantic_project-<name>/` directory. The directory travels
independently of `GIGANTIC/` and can be archived (or shared with
collaborators) as the **complete record of one research project**.

Implication: no project-specific information should ever be required from
the surrounding GIGANTIC clone or from the user's broader machine —
everything needed must live inside the renamed project (or under
`~/.claude/`, which is per-user not per-project).

---

## 16. Framework-development sessions are a separate scope

AI sessions rooted at `GIGANTIC/` are for **framework development** —
improving the template, conventions, top-level docs. They are not for
project work.

This is why the research-grade behavior docs (`CLAUDE.md`,
`AI_BEHAVIOR.md`) live at the `gigantic_project-COPYME/` level, not at
`GIGANTIC/` root: research-grade posture is project-scope.

If a user opens an AI session at `GIGANTIC/` and asks for project work,
the AI redirects them per the project root's `AI_GUIDE.md`.

---

## 17. INPUT_user is the single staging arena between user data and GIGANTIC

There is **one and only one** `INPUT_user/` directory in any GIGANTIC
project: at `gigantic_project-COPYME/INPUT_user/`. It is the **sole**
interface through which the user makes outside data available to GIGANTIC
subprojects. No other path through which user data reaches subprojects
exists by design.

Inside subprojects, individual workflows may download outside resources
specific to their needs (e.g., reference databases); that handling is
per-subproject. But anything the user themselves provides flows through
`INPUT_user/`.

---

## 18. INPUT_user contains symlinks (relative, via `ln -srf`), not data files — at any depth

All non-doc content inside `INPUT_user/` — at every depth, including
subproject-specific subdirs like `INPUT_user/phylonames/user_phylonames.tsv`
or `INPUT_user/genomic_resources/genomes/<species>.fasta` — is a **symlink**
into `research_notebook/research_user/` (the user's sandbox per §1).

Use **relative** symlinks: `ln -srf <target> <link>` creates them
automatically. Relative symlinks survive when the entire project is moved,
copied to another machine, or archived. Absolute symlinks break.

The user's actual files live in `research_notebook/research_user/`
unstructured per §1; `INPUT_user/` exposes specific files to GIGANTIC via
deliberate symlinks. The symlink graph of `INPUT_user/` is the complete
catalog of what the project feeds into GIGANTIC.

Audit commands:
- `find INPUT_user -xtype l` — broken symlinks (sandbox file moved or deleted)
- `find INPUT_user -type l -exec ls -la {} \;` — all symlinks and their targets

---

## 19. INPUT_user structure is subproject-driven

The conventional subdirectories inside `INPUT_user/` (e.g., `species_set/`,
`genomic_resources/{genomes,proteomes,annotations,maps}/`, `phylonames/`)
reflect what current GIGANTIC subprojects expect. The structure is not
hard-coded by the framework — it grows as subprojects declare their input
requirements.

When a new subproject needs a new kind of user-provided input that
doesn't fit existing locations, the convention is:

1. Add the new subdir under `INPUT_user/<subproject>/` (or extend an
   existing subdir if the input type fits).
2. Add a `README.md` in the new subdir describing what gets staged there.
3. Document the requirement in the subproject's own docs as well.
4. Update `INPUT_user/README.md` if the new convention is broad.

This is mirrored by §22 below: `ai/ai_FYIs/` uses similar subproject-first
naming for related documents.

---

## 20. INPUT_user ships only documentation; user content is gitignored

The shipped GIGANTIC template provides only the doc scaffold inside
`INPUT_user/` (README.md, AI_GUIDE.md, subdir READMEs). All actual user
content — symlinks, manifests, species lists, custom phyloname overrides
— is gitignored. The user's project-specific staging arena stays on their
local disk only.

`.gitignore` enforces this with: `**/gigantic_project-COPYME/INPUT_user/**`
ignored, with `*.md` files un-ignored at any depth so the doc scaffold
travels with the template.

---

## 21. AI scripts: `NNN_ai-<lang>-<descriptor>.<ext>` naming

Scripts inside `ai/ai_scripts/` (and any AI-authored scripts elsewhere)
follow the convention:

```
NNN_ai-<lang>-<descriptor>.<ext>
```

- `NNN` — sequential three-digit number (001, 002, 003, ...)
- `_ai-` — marks the script as AI-authored
- `<lang>` — language indicator (`python`, `bash`, etc.)
- `<descriptor>` — concise underscore-separated description
- `<ext>` — file extension matching the language

Examples:
- `002_ai-python-hook_precompact_capture_transcript.py`
- `003_ai-python-copy_session_jsonls.py`
- `004_ai-bash-create_output_to_input_symlinks.sh`

When a script is invoked by another system (a hook, another script), the
invoking system uses the **literal filename** — not wildcards like
`003_*.py` — so future siblings (e.g., `003_X-other.py`) don't create
ambiguity.

---

## 22. `ai/ai_FYIs/` file naming: subproject-prefix where applicable

Files inside `ai/ai_FYIs/` follow this naming hierarchy:

- **Subproject-specific docs**: prefix with the subproject name —
  `<subproject>-<descriptor>.md` (e.g., `phylonames-overview-old.md`,
  `trees_gene_groups-HANDOFF-2026may25-snap_family_and_step2_3_state.md`).
  This keeps related FYIs sorted together alphabetically.
- **Project-wide docs**: no subproject prefix
  (e.g., `gigantic_conventions.md`, `NEXTFLOW_26_COMPATIBILITY.md`,
  `publication_scrub_guide.md`).
- **Archived versions of deprecated docs**: suffix with `-old`
  (e.g., `phylonames-overview-old.md`).

---

## 23. NextFlow source files use `${projectDir}` for path construction

The relative-path convention (§5) holds for NextFlow `.nf` files via the
`${projectDir}` idiom. `${projectDir}` is a NextFlow built-in that
resolves to the absolute path of the directory containing the running
`main.nf` at runtime.

```groovy
script:
"""
python3 ${projectDir}/scripts/001_ai-python-validate_inputs.py \\
    --config ${projectDir}/../START_HERE-user_config.yaml \\
    --output_dir ${projectDir}/../${params.output.base_dir}
"""

publishDir "${projectDir}/../${params.output.base_dir}/1-output", mode: 'copy'
```

Source stays portable (paths are relative to `projectDir`); resolved
paths at runtime are absolute (and unique per workflow run). Both
properties hold simultaneously — no exception to §5 is needed for
NextFlow.

---

## 24. NextFlow runtime artifacts are gitignored

Files NextFlow generates at run time contain absolute paths and per-run
state. They never ship with the template:

- `work/` — staging directory for process executions
- `.nextflow/` — internal NextFlow state
- `.nextflow.log*` — NextFlow logs
- `.params.json` — per-run flattened-JSON params file (contains absolute
  paths from `${projectDir}` expansion)

All four are in `.gitignore`. When clearing a stuck run, deleting these
+ re-running fresh (no `-resume`) is the canonical reset.

---

## 25. `research_user/` ships as empty directory; `research_ai/` ships with documentation

Refines §1:

- `research_notebook/research_user/` is the user's wild-west sandbox. The
  template ships only the empty directory (`.gitkeep` only — no README,
  no scaffolding). Per §1, GIGANTIC never reaches into it; users
  organize however they want.
- `research_notebook/research_ai/` is **GIGANTIC's own sandbox**.
  Documentation appropriate to AI infrastructure (capture system, etc.)
  ships here, including `README.md` and the `sessions/.gitkeep` so the
  capture destination is preserved.

Captured session transcripts (per §9) land in
`research_notebook/research_ai/sessions/` and are gitignored as runtime
content — they never ship.

---

## 26. TRANSCRIPT_CAPTURE_LOG.md schema and trigger vocabulary

The capture log written by 002 (hook) and 003 (Save Chat! script) uses
exactly this schema:

```markdown
| Date | Session ID | Model | Trigger | Transcript Size | Output File |
|------|------------|-------|---------|-----------------|-------------|
```

**Trigger values**:
- `auto` — PreCompact hook fired automatically
- `manual` — PreCompact hook invoked manually
- `save_chat` — On-demand "Save Chat!" via 003

Both scripts produce schema-compatible rows; they share the file.

---

## 27. Session capture filename format (Claude Code)

The PreCompact hook (002) and Save Chat! script (003) both produce
`.jsonl.gz` files in `research_notebook/research_ai/sessions/` with this
filename format:

```
YYYYMMDD_HHMMSS-claude_code-<model-with-underscores>-<8-char-session-id>.jsonl.gz
```

Example:
```
20260306_014426-claude_code-claude_opus_4_6-44529712.jsonl.gz
```

- Timestamp = last-message timestamp from the JSONL content (so the same
  source file at the same state produces the same destination filename,
  enabling idempotent re-runs)
- Model with hyphens replaced by underscores (e.g., `claude-opus-4-7` →
  `claude_opus_4_7`)
- First 8 characters of the session UUID

For other AIs, use an analogous format with the AI's name in the
`claude_code` slot.

---

## 28. Per-subproject conda environments — no central `conda_environments/`

Each subproject manages its own conda environment(s), usually defined in
the subproject's `ai/conda_environment.yml` (or per-tool yml files for
multi-tool subprojects). The subproject's `RUN-workflow.sh` creates the
environment lazily on first run if it doesn't already exist.

A central `gigantic_project-COPYME/conda_environments/` directory existed
in older GIGANTIC versions but is deprecated and removed. It produced a
disconnect between "where I'm working" and "where my env definition
lives"; the per-subproject pattern keeps everything co-located.

Env naming convention: `aiG-<subproject>-<block_or_step>-<optional_details>`
(established earlier; verify against subproject's `ai/conda_environment.yml`
header comment).

---

## 29. Unified `RUN-workflow.sh` is the canonical driver

Each workflow has a single canonical entry point: `RUN-workflow.sh`. It
handles local execution AND self-submits to SLURM when the YAML config's
`execution_mode` key is set to `slurm`. There is no separate
`RUN-workflow.sbatch` in the canonical pattern — that was an older
two-file approach now deprecated.

The unified driver:
- Reads `START_HERE-user_config.yaml`
- Sets up conda env on first run
- For SLURM: writes a per-run sbatch wrapper and submits it
- For local: invokes NextFlow directly
- Cleans up runtime artifacts on exit

The canonical example (most recently modernized) is the
`annotations_X_ocl` subproject's workflow.

---

## 30. This file is the canonical source of truth for conventions

`gigantic_project-COPYME/ai/ai_FYIs/gigantic_conventions.md` is the
authoritative list of GIGANTIC conventions. Other documents reference
section numbers here rather than duplicating content:

```markdown
See `ai/ai_FYIs/gigantic_conventions.md` §9 for the chat-as-research-notebook
architecture.
```

When a convention is updated here, downstream references stay valid as
long as they point at section numbers. **Don't renumber existing
sections** — append new ones; if a section is genuinely deprecated, mark
it `~~§N~~ DEPRECATED — see §M`.

---

## 31. Pipeline output file naming: `N_ai-<descriptor>.<ext>`

Outputs written by pipeline scripts follow the convention:

```
N_ai-<descriptor>.<ext>
```

where `N` is the **invoking script's number with leading zeros removed**
(e.g., script `005_ai-python-generate_blast_commands.py` writes outputs
named `5_ai-blast_commands.sh` into `OUTPUT_pipeline/5-output/`).

Why drop leading zeros in outputs (vs script names which keep them)?
Output file lists are typically short enough that alphabetical sorting
doesn't need the leading zeros, and `5_ai-...` reads more naturally than
`005_ai-...`. Scripts retain `NNN` because directories accumulating many
scripts benefit from the zero-padding for ordering.

The pairing — `NNN_ai-script.py` → `OUTPUT_pipeline/N-output/N_ai-result.tsv` —
makes the script-to-output mapping immediately readable.

---

## 32. Python variable naming conventions

GIGANTIC Python code uses these naming patterns consistently:

| Pattern | Use for | Example |
|---------|---------|---------|
| `input_X` / `input_X_Y_Z` | All inputs (files, paths, data) | `input_fasta_all_species`, `input_genome_data` |
| `output_X` / `output_X_Y_Z` | All outputs (files, paths, data) | `output_arm_counts`, `output_summary_table` |
| `Xs___Ys` (three underscores) | Dictionaries; plural keys-set + plural values-set | `identifiers___sequences`, `species_names___genome_sizes` |
| `Xs` (plural) | Lists | `sequences`, `identifiers`, `genome_sizes` |
| `X` (singular) | Iteration variable inside a loop over `Xs` | `for sequence in sequences:` |
| `parts_X` | Result of splitting variable `X` | `parts_annotation_string = annotation_string.split('|')` |
| `line` + `parts` | TSV/CSV row parsing | `line = line.strip(); parts = line.split('\t')` |

Use full words, not abbreviations (`sequence_count` not `seq_cnt`).
Established scientific abbreviations (GO, Pfam, BLAST) are kept as-is.

---

## 33. Python spacing: spaces inside brackets (intentional PEP 8 deviation)

GIGANTIC Python uses spaces **inside** parentheses, square brackets, and
curly braces, and around operators. This intentionally deviates from PEP 8
in favor of human readability for the research audience.

```python
# GIGANTIC style
species_list = [ 'Octopus', 'Aplysia', 'Homo' ]
genome_data = { 'species': 'Octopus', 'size': 2700000000 }
if species_count == 8:
    open( 'species.fasta', 'r' )

# NOT GIGANTIC style (standard PEP 8)
species_list = ['Octopus', 'Aplysia', 'Homo']
genome_data = {'species': 'Octopus', 'size': 2700000000}
if species_count==8:
    open('species.fasta', 'r')
```

Readability for the human researcher takes precedence over PEP 8
conformance. Don't run black, ruff-format, or other auto-formatters
that would strip these spaces.

---

## 34. TSV/CSV output conventions: self-documenting headers + tab/comma delimiters

All tabular outputs follow two rules:

### Self-documenting column headers

```
header_ID (header details in human-readable prose)
```

- `header_ID`: underscore-separated identifier
- `header details`: prose explanation in parentheses, with spaces, embedding
  calculation method and data format where relevant

Examples:
```
Orthogroup_ID (orthogroup identifier from OCL data)
Conservation_Rate_Percent (calculated as conservation events divided by conservation plus loss events times 100)
Species_List (comma delimited list of species names in Genus_species format)
```

Headers can be long if needed — clarity is the priority.

### Delimiter convention

- **Between columns**: TAB (`\t`) — the file is a TSV
- **Within a column** (multi-value cells): COMMA (`,`) — pipes (`|`) are
  not used as in-column delimiters

```
# CORRECT (TSV with comma-delimited in-column lists)
Species_List (comma delimited list of species names)
Homo_sapiens,Mus_musculus,Drosophila_melanogaster

# INCORRECT (do not use pipes in columns)
Homo_sapiens|Mus_musculus|Drosophila_melanogaster
```

---

## 35. NextFlow workflow directory naming: template vs run instance

Each NextFlow workflow lives in a directory whose name encodes whether it
is a **template** (committed to git, the canonical source) or a **run
instance** (a user's working copy of that template).

| Form | Meaning | In git? |
|------|---------|---------|
| `workflow-COPYME-<descriptor>/` | Canonical template; the user copies it to run | Yes (tracked) |
| `workflow-RUN_NN-<descriptor>/` | A run instance — copy of the template that executed (or is executing) once. `NN` numbers sequential runs of that workflow. | No (gitignored — `workflow-RUN_*/`) |

Older naming patterns like `nf_workflow-TEMPLATE_NN-<descriptor>/` or
`workflow-RUN_NN_NN-<descriptor>/` are deprecated in favor of the simpler
`workflow-COPYME-*` / `workflow-RUN_NN-*` pair.

The run-instance dirs contain a workflow's full execution artifacts
(`OUTPUT_pipeline/`, `work/`, `.nextflow*`, slurm logs) and never ship
to git.

---

## 36. NextFlow fail-fast: no `optional: true` outputs; `errorStrategy = 'terminate'`; `sys.exit(1)` on missing data

Research pipelines must fail loudly on missing or invalid data — not
silently continue with placeholder values or empty files. Three rules
enforce this:

### Never use `optional: true` in NextFlow outputs

```groovy
// ❌ WRONG — allows silent missing-output to succeed
output:
    path "results.txt", emit: results, optional: true

// ✅ CORRECT — pipeline errors if file is missing
output:
    path "results.txt", emit: results
```

If a process can legitimately produce no output, fix the process to
produce an empty-with-headers file rather than no file. Marking outputs
optional means downstream consumers see "no error" while having no data.

### `errorStrategy = 'terminate'` and `maxErrors = 0` in `nextflow.config`

```groovy
process {
    errorStrategy = { task.attempt <= 2 ? 'retry' : 'terminate' }
    maxRetries = 2
    maxErrors = 0   // stop immediately on first persistent failure
    // Never use errorStrategy = 'ignore'
}
```

Research pipelines want immediate feedback when something goes wrong, not
to discover multiple failures hours later.

### Python pipeline scripts: `sys.exit(1)` on missing data

```python
if not critical_data:
    logger.error( "CRITICAL ERROR: What went wrong" )
    logger.error( "Why this is a problem" )
    logger.error( f"Relevant context: { details }" )
    logger.error( "How to fix it" )
    sys.exit( 1 )   # FAIL
```

Never `sys.exit(0)` when data is missing. Never log "warning" for a
critical issue. Never write a placeholder/empty file and continue. The
script either produced the expected output or it failed — no third state.

---

<!-- Add new conventions below as they surface during per-directory review. -->
<!-- User shorthand "gcon" = "please add this to gigantic_conventions.md". -->

