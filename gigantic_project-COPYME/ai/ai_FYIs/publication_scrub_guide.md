<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Walk users (with their AI assistant) through preparing captured
         chat transcripts for public release as part of a publication's
         supplementary materials, methods archive, or AI-disclosure
         appendix. Originals stay untouched; scrub is on copies only.
History:
  2026-05-25  Initial version.
============================================================================ -->

# Publication Scrub Guide — Preparing Captured Chats for Public Release

This guide walks you (the user) and your AI through producing **publication-
ready copies** of captured chat transcripts from
`research_notebook/research_ai/sessions/`.

**Core rule** (non-negotiable, from `gigantic_conventions.md` §9 and
`AI_BEHAVIOR.md`):

> **The originals in `research_notebook/research_ai/sessions/` are never
> edited, never deleted, never scrubbed.** They are the complete scientific
> record of the project. All scrubbing happens on **copies**, in a
> separate location.

---

## When to do this

Toward the end of a project, when you know what you want to publish and
which captured chats are relevant to that publication. Don't do it
preemptively — you may want different excerpts for different venues
later, and you can always re-derive a publication-ready copy from the
originals.

Increasingly, journals and funding agencies require disclosure of AI
assistance used in research. A scrubbed publication-ready capture is the
artifact you'd submit to satisfy such requirements.

---

## Working location

Make publication-ready copies in a **separate** directory **outside** of
`research_notebook/research_ai/sessions/`. Suggested:

```
research_notebook/research_user/publication-<paper-name>/chat-captures-scrubbed/
```

This keeps the scrubbed copies inside `research_notebook/research_user/`
(the user-sandbox; not under GIGANTIC governance) and **clearly separates
them from the originals**.

---

## The scrub checklist

For each captured `.jsonl.gz` file you intend to publish, work through
the following with your AI:

### 1. Identify the sessions to include

- Which captured sessions correspond to the work being published?
- For each: do you want the full transcript, or specific excerpts?

### 2. Decompress to a working copy

```bash
mkdir -p research_notebook/research_user/publication-<paper-name>/chat-captures-scrubbed/
cp research_notebook/research_ai/sessions/<file>.jsonl.gz \
   research_notebook/research_user/publication-<paper-name>/chat-captures-scrubbed/
cd research_notebook/research_user/publication-<paper-name>/chat-captures-scrubbed/
gunzip <file>.jsonl.gz
```

The original `.jsonl.gz` in `research_notebook/research_ai/sessions/`
remains untouched.

### 3. Scrub the working copy

Walk through the transcript with your AI and remove or redact:

| Category | Examples |
|----------|----------|
| **Leaked credentials / tokens** | API keys pasted into commands, SSH keys in error output, database connection strings, cloud-provider secrets |
| **IP addresses / hostnames** | Private cluster IPs, internal hostnames, VPN endpoints |
| **Personal identifiers** | Home directories that expose usernames (`/home/realname/...`), email addresses, phone numbers in test data |
| **Collaborator names in unflattering context** | Frustrations about specific colleagues, disagreements not meant for public airing |
| **Internal lab politics** | Funding disputes, personnel issues, draft authorship-order debates |
| **Frank language / outbursts** | Frustration with the AI, with the tools, with the data, with the situation |
| **Draft hypotheses** | Speculative scientific ideas you're not yet ready to publish |
| **Embargoed or licensed data** | Pre-publication genome assemblies, third-party data under restrictive licenses |
| **Other-project context** | References to unrelated projects, other collaborators' unrelated work |
| **Half-formed analyses** | Trial-and-error explorations that didn't make it into the final methods |

### 4. Choose a publication format

Raw JSONL is rarely the right format for a journal supplementary file.
Common output forms (your AI can produce all of these):

- **Curated markdown digest**: a chronological narrative of the AI's role
  in the work, with selected verbatim excerpts highlighting key decisions
  (most useful for AI-disclosure appendices)
- **Annotated JSONL**: scrubbed JSONL with redaction markers inline
  (most useful for full-transparency archives)
- **Methods-paragraph form**: a few prose paragraphs synthesizing the
  AI-assisted methods (most useful for the main paper's Methods section)
- **Citation-ready blob**: just the relevant excerpts that document a
  specific cited decision (most useful for inline citations)

### 5. Review with at least one human collaborator

Before publication, a second human should read the scrubbed output and
catch anything you missed. This is especially important for the
"frustrations" and "collaborator names" categories — your own blind
spots are often other people's red flags.

### 6. Document what was scrubbed

In the same directory as the scrubbed copy, add a `SCRUB_NOTES.md` listing
broadly what was redacted (categories, not specifics) so reviewers and
future-you can understand the gap between original and published. Example:

```markdown
# Scrub Notes — <session-id-prefix> for <paper-name>

Original: research_notebook/research_ai/sessions/<filename>.jsonl.gz
Scrubbed copy: <filename>.jsonl (this directory)

Redacted categories:
- API keys (2 occurrences, lines ~342, ~1108)
- Personal home-directory paths (~/home/edsinger/ → ~/home/[user]/, throughout)
- Internal cluster IPs (3 occurrences)
- One frustrated outburst at the AI (line ~588) — removed entirely
- Draft hypothesis re: ctenophore-Porifera relationship — removed (not yet
  published; saving for next paper)

No content beyond the above was modified. Word counts:
- Original (decompressed): 47,200 words
- Scrubbed: 46,830 words
```

### 7. Verify the originals are still intact

Sanity check that you didn't accidentally touch the originals:

```bash
# Should be identical to the pre-scrub size and checksum
ls -la research_notebook/research_ai/sessions/<file>.jsonl.gz
sha256sum research_notebook/research_ai/sessions/<file>.jsonl.gz
```

---

## What ships with the publication

The scrubbed copy + the `SCRUB_NOTES.md` go into the publication
supplementary materials. The originals **never** go to a publication;
they remain in `research_notebook/research_ai/sessions/` as your
internal scientific record.

If a reviewer or auditor later requests the unscrubbed originals (e.g.,
under a research-integrity review), you can provide them directly from
`research_notebook/research_ai/sessions/` without having to reconstruct
anything — that's the entire reason the originals are preserved.

---

## Reference

- `ai/ai_FYIs/gigantic_conventions.md` §9 — chat-as-research-notebook architecture
- `AI_BEHAVIOR.md` — the never-edit-originals rule, in the AI's posture doc
- `README.md` — the user-facing "make copies, scrub the copies" pointer
- `AI_GUIDE.md` — the AI's operational role in helping the user scrub
