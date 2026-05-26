<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Describe the phylonames slot within INPUT_user — what gets staged
         here and how it's consumed by the phylonames subproject.
History:
  2026-05-25  Updated for the symlink-into-research_notebook architecture.
============================================================================ -->

# `INPUT_user/phylonames/`

User-provided custom taxonomic-override data for the GIGANTIC `phylonames`
subproject.

## What gets staged here

- `user_phylonames.tsv` — Tab-separated mappings from `genus_species` to a
  custom `phyloname` (format: `Kingdom_Phylum_Class_Order_Family_Genus_species`).
  Used by `phylonames` STEP_2 (`apply_user_phylonames`) to override
  NCBI-generated phylonames for species with `NOTINNCBI` placeholders,
  numbered clades, or user-preferred taxonomic assignments.

Per the `INPUT_user/` staging-arena pattern (see `../README.md` and
`../AI_GUIDE.md`), the real `user_phylonames.tsv` lives in the user's
sandbox at `../../research_notebook/research_user/...` and is **symlinked**
into this directory. The symlink, not a copy, is what `phylonames` STEP_2
reads.

## How it's consumed

The phylonames STEP_2 workflow copies from this symlink into its
workflow-local `INPUT_user/` at run time, so each workflow run archives
its own snapshot of the overrides used.

If `user_phylonames.tsv` is absent or the symlink is broken, STEP_2 skips
the override step and ships NCBI-only phylonames.

## File format

See the phylonames subproject documentation for the full format spec and
allowed `unofficial_action` values.
