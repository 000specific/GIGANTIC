# TODO: Final AGS cleanup — remove RGS↔genome-proteome duplicate entries

**Status (2026-05-24):** RESOLVED upstream, pending real-run verification.

The RGS↔genome duplication this TODO describes is now addressed by **two
upstream fixes** applied to STEP_1 itself:

1. **Script 013 patch** (2026-05-23) — adds QUERY-side rejection so that
   project-DB proteins whose source genome contains the cognate RGS no longer
   pass the reciprocal-best-hit filter. Synced across all 97 affected COPYME
   templates (gene_groups + 95 trees_gene_families V1 templates).

2. **Script 008 rewrite** (2026-05-24) — replaces the greedy BLAST-top-hit
   mapping with: (a) NCBI accession primary key, (b) BLAST identity ≥95%
   AND symmetric coverage ≥95% + T1 length invariant, (c) BBH cross-check,
   (d) Hungarian optimal assignment (scipy), (e) strict fail-fast on any
   unresolved RGS. PLAN file: `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups_COPYME/STEP_1-homolog_discovery/PLAN-rgs_identification_improvements.md`.
   Synced to all 79 STEP_1 workflow-COPYME-rbh_rbf_homologs dirs (gene_groups
   masters + hugo_hgnc + gene_family_COPYME master + 76 per-family templates).

Together these prevent the `>g_*-<rgs_source>` duplicate from entering the
CGS/AGS in the first place. The deferred-dedup script (017a) proposed below
is no longer needed in the planned form, *but the TODO is retained until*
verified on a real run (e.g., re-run 14_3_3 and innexin_pannexin from the
patched COPYME and confirm no `>g_*-<rgs_source>` duplicates in the final
AGS).

**Action when verified:** delete this file. Until then, treat as
documentation of the historical issue and the in-pipeline fixes that
superseded it.

---

**Filed:** 2026-04-26
**Discovered while investigating:** FlyC1 missing-plant-orthologs bug (sono_april2026 / gigantic_project-sono_nih_sequences)
**Subproject affected:** `trees_gene_families/STEP_1-homolog_discovery`
**Pipeline location:** end of STEP_1, after script `016_ai-python-concatenate_sequences.py` (final AGS) and `018_ai-python-restore_full_length_rgs_sequences.py`
**Severity:** Cosmetic / interpretation hazard, NOT scientific artifact (sequences are correct, just duplicated)
**Owner:** future GIGANTIC_1 maintainer

---

## Problem

When an RGS sequence comes from a non-model organism whose **gene family is NOT covered by the RGS reference set** (e.g., FLYC1 in Dionaea muscipula but no plant TMEM63 family RGS), the same protein appears TWICE in the final AGS:

1. **As the RGS reference**, with `rgs-` prefixed header — e.g., `>rgs-QNN26181_1-tmem63_osca_flyc1_mechanosensitive-venus_flytrap-FLYC1-...`
2. **As the genome-confirmed ortholog**, with the AGS-format header — e.g., `>g_Dimus_011234-t_GAB2276514.1-p_GAB2276514.1-n_Viridiplantae_..._Dionaea_muscipula`

These are the same protein (~99.87% identical by BLAST sanity check) — not a paralog — but they appear as separate entries in the AGS, the alignment, and the tree.

## Root cause

The pipeline has two parallel tracks that both legitimately include the same protein:

- **RGS track**: the RGS file directly includes FLYC1 (since human RGS doesn't have FLYC1 — it's a plant gene). Script `016` concatenates the RGS into the final AGS as `rgs-` prefixed entries.
- **Forward+reverse RBH/RBF track**: the FLYC1 protein in the unmodified Dionaea genome (`Dimus_011234 / GAB2276514`) is a forward-BLAST hit. It then reverse-BLASTs against the *modified* Dionaea genome (where `Dimus_011234` is suppressed and replaced with `rgs-QNN26181_1-...FLYC1`), reciprocally hits the RGS-FLYC1, passes RBH, and enters the AGS as the AGS-format genome-ortholog entry.

For human TMEM63A/B/C (which ARE covered by the human-only RGS file), the equivalent suppression of human's `g_TMEM63A-...` entry (replaced by `rgs-O94886-...`) means the forward-BLAST track does not produce a duplicate AGS entry. The duplicate only manifests for non-human-RGS species — i.e., where the genome species is itself an RGS source.

## Why this matters

- **Tree clarity**: the same protein appears as two adjacent tips with branch length ≈ 0. Confusing for biologists picking orthologs.
- **Alignment efficiency**: trivially redundant alignments waste compute.
- **Downstream duplication**: per-category fastas, header maps, and CDS extractions all carry the duplication forward unless explicitly de-duped.

## Proposed fix

Add a new script (e.g., `017a_ai-python-deduplicate_rgs_genome_pairs.py`) that runs **after** script `018` (full-length RGS restoration) and **before** any downstream consumption:

1. Read the AGS produced by script `018`.
2. Read the replacement map from script `008` (`8-output/8_ai-map-rgs-to-genome-identifiers.txt`). Each row = (genome_header, rgs_short_form, rgs_full_form).
3. For each row in the map:
   - Find the genome_header entry in the AGS (exact header match).
   - Find the corresponding RGS entry (matching the rgs_full_form or rgs_short_form).
   - **Verify sequence identity** — if the two sequences are 100% identical OR ≥ 99% pairwise identical (via gappy global alignment or simpler hamming-on-aligned-columns), keep ONLY the RGS entry. Drop the genome_header entry.
   - If the two sequences are NOT highly similar (e.g. < 99% identity), KEEP BOTH and emit a warning to the run log — this is a real paralog scenario, not a duplicate. Surface explicitly so the user can decide.
4. Write the de-duplicated AGS as `19-output/19_ai-ags-...-deduped.aa` (or replace `18-output` if simpler).
5. Update the symlinks pointing into `output_to_input/<gene_family>/STEP_1-homolog_discovery/` to point at the deduped AGS.

## Implementation notes / open questions

- **Identity threshold**: 99% is a starting suggestion. Confirm with the user. The user's BLAST showed Dimus_011234 vs QNN26181 at 99.87% identity, so 99% is comfortably above that.
- **Which to keep** (RGS or genome): two valid choices.
  - Keep RGS: preserves the published-reference identifier (e.g., `QNN26181_1` UniProt accession) — better for cross-paper traceability.
  - Keep genome: preserves the GIGANTIC AGS-format header with phyloname encoding — better for downstream CDS extraction and Shrek-style cloning workflows.
  - **Recommendation: keep the genome AGS-format entry** (drop the rgs- entry) IF the genome version is full-length and high-quality, because the genome entry has CDS in genomesDB STEP_5 maps and the rgs- entry doesn't. If the genome version is shorter / partial, keep the rgs- entry instead. The script should compare lengths and pick the longer one (or the user-configured preference).
- **Logging**: every duplicate detected and resolved should be logged with both headers + identity score, so the user can audit retroactively.
- **Edge case: orphan RGS** (`include_orphan_rgs: true`) — RGS for species with no genome representative in the species set. These don't have a genome counterpart at all, so the dedup script should not touch them.
- **Edge case: genome species whose RGS is from a different lineage** — e.g., if FLYC1 RGS were sourced from Drosera capensis but Dionaea is in the species set. The replacement map only handles the same-species case (Dionaea RGS → Dionaea genome). Cross-species near-identical paralogs would NOT be caught by this dedup. Acceptable for now — they're rare and biologically meaningful.

## Suggested unit tests / regression check

After implementing:
- Re-run STEP_1 for FlyC1 (the diagnostic case). Confirm the final AGS has only ONE Dimus_011234/QNN26181 entry, not two.
- Confirm the dedup script logs the resolved duplicate.
- Re-run STEP_1 for TRP. Confirm no human TMEM63A/B/C entries get unexpectedly dropped (these should not be in the dedup map at all).
- Confirm orphan RGS (e.g., mouse TRPC2 in TRP family) survive untouched.

## How this was discovered

- 2026-04-26: While investigating why plant FLYC1 orthologs were missing from the FlyC1 AGS (root cause: hardcoded `species_mappings` dict in `007_ai-python-list_rgs_blast_files.py` excluded `venus_flytrap`).
- After fixing both `rgs_species_map.tsv` truncation AND the script 007 hardcoded dict, the FlyC1 STEP_1 rerun successfully recovered all candidate plant FLYC1-family hits (KAL9252212.1, KAL9271890.1, GAB2229477.1, GMH11820.1) plus the now-suppressed-and-replaced Dionaea FLYC1 (Dimus_011234 / GAB2276514.1).
- User noticed in the new AGS: rgs-QNN26181_1-FLYC1 + g_Dimus_011234 both present. Hence this TODO.

## Cross-references

- Pipeline scripts: `016_ai-python-concatenate_sequences.py`, `018_ai-python-restore_full_length_rgs_sequences.py`, plus the new `017a` (proposed)
- Key file: `8-output/8_ai-map-rgs-to-genome-identifiers.txt` (the replacement map this dedup will consume)
- Related concepts: AGS structure, RGS-vs-genome equivalence, RBH/RBF reciprocal validation
