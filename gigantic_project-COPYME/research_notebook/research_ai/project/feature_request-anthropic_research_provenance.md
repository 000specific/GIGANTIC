# Feature Request: Automatic Session Provenance for Research Use Cases

**Submitted to**: https://github.com/anthropics/claude-code/issues
**Date**: 2026-02-12
**Submitter**: Eric Edsinger (via Claude Code session)

---

## Summary

Claude Code needs **automatic session provenance** - the ability to save conversation context and session summaries to user-specified project directories before context compaction occurs. This is critical for research transparency and reproducibility.

---

## The Problem
Researchers working with AIs like Claude need to have their sessions/chats recorded like a lab notebook - ideally the entire chat would be recorded as is - space is not an issue - or the session compaction could be recorded - in local project directories.

### Current Behavior

When Claude Code reaches its context limit, it performs "context compaction" - summarizing the conversation to continue. These summaries are:
- Saved to `~/.claude/projects/...` (system location)
- **NOT** saved to project directories
- **NOT** accessible for research documentation

### Why This Matters for Research

Scientific research requires **complete provenance** - knowing exactly what was done, when, how, and why. When AI assists with research:

1. **Reproducibility**: Other researchers must be able to understand and replicate the work
2. **Transparency**: AI contributions must be documented in the scientific record
3. **Audit trail**: Funding agencies and journals increasingly require AI disclosure
4. **Lab notebook convention**: Science has centuries of "write everything down" culture

### The Gap

Claude Code has no mechanism to automatically save session context to project directories. The AI assistant:
- Cannot detect when context is running low
- Does not proactively save session summaries
- Has no hook for context compaction events
- Provides no export of conversation history to project files

**Result**: Research sessions are lost. Hours of AI-assisted work disappear without documentation.

---

## Impact Statement

This limitation affects:

- **Computational biologists** developing analysis pipelines
- **Bioinformaticians** building reproducible workflows
- **Research software engineers** creating scientific tools
- **Any researcher** using AI assistance who needs documentation

**User quote**: "This renders Claude Code useless for research. Periodic manual saves don't work because the AI doesn't stop when running and will blow through context windows"

---

## Industry Research (February 2026)

We surveyed major AI coding assistants. **None** currently support automatic local session saving:

| Tool | Session Persistence | Local Directory Export |
|------|---------------------|----------------------|
| Claude Code | Context compaction to ~/.claude/ | No |
| Cursor AI | Recommends new sessions | No |
| ChatGPT Projects | Cloud-based project memory | No |
| GitHub Copilot | No history retention | No |

**This is an industry-wide gap**, and Anthropic could lead by addressing it.

---

## Proposed Solution

### Option A: Automatic Session Saving (Preferred)

1. **New configuration setting** in `CLAUDE.md` or project config:
   ```yaml
   research_provenance:
     enabled: true
     save_location: "research_notebook/research_ai/sessions/"
     save_frequency: "on_compaction"  # or "periodic" with interval
     format: "markdown"  # or "json"
   ```

2. **Context compaction hook**: When context compaction occurs, automatically:
   - Save full conversation summary to specified directory
   - Include timestamp, model, session ID
   - Include list of files modified
   - Include key decisions and outcomes

3. **Proactive saving trigger**: When context reaches 80-90% capacity:
   - Notify user
   - Offer to save session summary
   - Or auto-save if configured

### Option B: Manual Export Command

At minimum, provide:
```
/export-session [directory]
```
That saves the current conversation context to a specified location.

### Option C: Hook System Integration

Extend Claude Code's hook system to support:
```json
{
  "hooks": {
    "on_context_compaction": {
      "command": "python save_session.py",
      "input": "compaction_summary"
    }
  }
}
```

---

## Suggested File Format

```markdown
# Claude Code Session Summary

**Date**: 2026-02-12 03:45:00
**Model**: Claude Opus 4.5
**Session ID**: abc123-def456
**Project**: /path/to/project

## Summary

[AI-generated summary of session]

## Key Decisions

1. Decision A: [rationale]
2. Decision B: [rationale]

## Files Modified

- path/to/file1.py (created)
- path/to/file2.md (modified)

## Commits Made

- abc1234: "Commit message"

## Pending Work

- Item 1
- Item 2

## Context at Compaction

[Compressed context that was saved]
```

---

## Why Anthropic Should Prioritize This

1. **Differentiation**: No competitor offers this. Anthropic markets to researchers and scientists - this would be a unique selling point.

2. **Trust**: Research requires trust in tools. Automatic provenance builds trust.

3. **Alignment with values**: Anthropic emphasizes AI safety and transparency. Research provenance IS transparency.

4. **Growing market**: AI-assisted research is exploding. Tools that support research workflows will dominate.

5. **Low implementation cost**: The context compaction summary already exists - it just needs to be written to a user-specified location.

---

## User Workflow Example

### Current (Broken) Workflow

1. User starts multi-hour session developing pipeline
2. Claude Code reaches context limit
3. Context compaction occurs silently
4. User discovers later that session history is lost
5. No record of what was done or why

### Proposed Workflow

1. User configures `research_provenance` in CLAUDE.md
2. Claude Code reaches context limit
3. **Before compaction**: Session summary saved to project directory
4. User has complete record for lab notebook
5. Other researchers can understand the AI-assisted development

---

## Related Issues

- This may relate to existing requests for conversation export
- Connects to broader "AI in research" transparency requirements
- Aligns with emerging journal requirements for AI disclosure

---

## Final Note

Anthropic frequently discusses its commitment to beneficial AI and working with researchers. This feature request represents a fundamental need from the research community. The inability to document AI sessions is not a minor inconvenience - it's a blocker for using Claude Code in any serious research context.

We hope Anthropic will consider this a priority.

---

**Contact**: Eric Edsinger
**Project**: GIGANTIC (Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades)
**Institution**: [University of Florida Whitney Laboratory for Marine Biosciences]
