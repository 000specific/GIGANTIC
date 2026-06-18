<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: Document a known, user-accepted data-integrity caveat in annogroups:
         truncated/orphan annotation identifiers that are dropped during build.
============================================================================ -->

# WARNING — truncated / orphan annotation identifiers are dropped

## What happens

When `002_ai-python-build_annogroups.py` builds annogroups for a source, it
drops any **annotated sequence whose identifier is not present in the proteome
universe** (`OUTPUT_pipeline/1-output/1_ai-proteome_universe.tsv`, built by
Script 001 from the genomesDB STEP_4 species-set proteomes).

These dropped identifiers are written, per source, to:

```
OUTPUT_pipeline/2-output/<source>/2_ai-<source>-dropped_orphan_sequences.tsv
```

and a `WARNING:` line is logged to stderr. The drop is **auditable, not
silent**.

## Why it happens (root cause)

Some species70 proteomes (EvidentialGene-derived) contain **multi-locus protein
identifiers** that are extremely long (>200 characters), e.g.:

```
g_Sarc_Sarc4_g11901_Sarc4_g11902_Sarc4_g11903_Sarc4_g11904-t_..._-n_HolozoaUNOFFICIAL_..._Sphaeroforma_arctica
```

Somewhere upstream in the **InterProScan / annotations_hmms** pipeline these
identifiers were **truncated** (e.g. the phyloname tail `Sphaeroforma_arctica`
became `Sphaeroforma_arcti`, or was cut off even earlier at `Ichthyophonida`).
The truncated identifier in the parsed annotation file therefore no longer
matches the **full** identifier in the proteome FASTA header, so it maps to no
real proteome sequence and cannot become a valid annogroup member.

This is the same long-identifier class flagged for SignalP6 / TMBed
(per-protein filename limits). See the project memory note
`feedback_evigene_multilocus_id_filename_limit`.

## Observed scope (pfam, 2026-06-18)

- **7** annotated sequences dropped (all *Sphaeroforma arctica*, Ichthyosporea)
  out of **922,240** pfam-annotated and **1,375,926** universe sequences.

## Known side effect (USER-ACCEPTED)

Dropping the truncated annotation identifier does **not** remove the
corresponding sequence from the analysis: the **full-identifier** proteome
sequence is still in the universe. Because its only annotation was recorded
under the truncated identifier, that sequence now has **no surviving feature for
the source** and is therefore counted in **`annogroup_<source>_absent`**.

Net effect: a small number of sequences that *genuinely have a domain/feature*
(per the source tool) are misfiled as "absent" — a **false negative**. For pfam
this is **7 of ~1,375,926 ≈ 0.0005%**, confined to one ichthyosporean species.

**Decision (Eric Edsinger, 2026-06-18):** this is acceptable; drop the orphans.
The proper long-term fix is upstream — preserve full (untruncated) protein
identifiers through the InterProScan / annotations_hmms parsing step so the
annotation identifiers match the proteome headers exactly. Until then, the drop
+ this note + the per-source `dropped_orphan_sequences.tsv` keep the loss
explicit and auditable.

## If the dropped count is large or unexpected

A large dropped count for any source means a **systematic identifier mismatch**
(not just a few long IDs) between that source's parsed output and the proteome
universe — investigate the upstream parser, do not accept silently.
