# PLAN: Improve RGS Identification in Reference Proteomes

**Status**: IMPLEMENTED in `gene_groups_COPYME/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/ai/scripts/008_ai-python-map_rgs_to_reference_genomes.py` (2026-05-24). Pending real-run verification on the next HGNC rerun.
**Original status**: Design — not yet implemented
**Last updated**: 2026-05-24 (status); 2026-05-23 (content)
**Author**: Eric Edsinger (with Claude Code, Opus 4.7)
**Applies to**: `script 008_ai-python-map_rgs_to_reference_genomes.py` in `gene_groups_COPYME/.../workflow-COPYME-rbh_rbf_homologs/` (the canonical master for trees_gene_groups). The trees_gene_families version of script 008 follows the same design.
**Out of scope of this plan but related**: `RUN-update_upload_to_server.sh`, scripts 009/013, downstream re-runs.

---

## IMPLEMENTATION SUMMARY (2026-05-24)

All 5 improvements have been implemented in the master `gene_groups_COPYME` script 008:

1. ✅ **NCBI accession match** — primary mechanism (deterministic for NCBI-sourced RGS)
2. ✅ **Identity ≥95% AND symmetric coverage ≥95%** BLAST fallback with T1 length-invariant check
3. ✅ **Bidirectional best hit (BBH)** validation
4. ✅ **Hungarian optimal assignment** via `scipy.optimize.linear_sum_assignment` (with greedy fallback if scipy unavailable)
5. ✅ **Strict fail-fast** on any unresolved RGS (no `--include-orphan-rgs` escape)

Output additions:
- `mechanism` column added to `8_ai-map-rgs-to-genome-identifiers.txt` (values: `ncbi_accession`, `blast_high_confidence`, `hungarian_optimal`, `greedy_fallback`)
- New audit sidecar `8_ai-rgs_identification_report.tsv` with per-RGS provenance

The conda env now includes `numpy` and `scipy` (in `ai/conda_environment.yml`) for the Hungarian path.

Verification on real data: pending the next HGNC STEP_1 rerun.

---

---

## 1. Context

### Current state of script 008
The current `create_rgs_genome_mapping` function maps each RGS sequence to one genome protein using:
1. BLASTP RGS vs source-genome proteome (`-outfmt 6`)
2. For each RGS query, take the **first row** in the BLAST report (highest-bitscore top hit)
3. Greedy one-to-one assignment: `if rgs_query not in rgs_seen and genome_hit not in genome_ids_seen`
4. Plus organism-marker gate: `parts[1]` of RGS header must equal the BLAST report's `report_model_species`

### Why this matters
The mapping output drives script 009 (modified genomes) and script 013 (reciprocal-best-hit filter). If the RGS↔genome cognate mapping is wrong, the downstream pipeline produces incorrect CGS and incorrect AGS — exactly the kind of silent biological artifact prohibited by CLAUDE.md's "Zero Tolerance for Silent Artifacts" rule.

### Key biological/technical facts
- All GIGANTIC species70 proteomes are **T1 (longest isoform per gene)**. RGS sequences for any species70 species CANNOT be longer than the genome version of the same protein, because the genome T1 is by definition the longest.
- Most RGS sequences come from NCBI (HGNC reference genes) and carry an explicit NCBI accession (`NP_*`/`XP_*`) in the RGS header. For these, the genome contains the SAME accession.
- Some RGS (e.g., worm, fly, hydra) come from UniProt or hand-curated sources. These do NOT carry NCBI accessions, and the source-species proteome was assembled from NCBI-style identifiers. For these, BLAST is the only mapping mechanism.

---

## 2. Failure modes the current pipeline allows

| # | Failure mode | Current outcome |
|---|---|---|
| F1 | RGS top hit happens to be a paralog (not the cognate) | Silently wrong mapping → wrong RGS-renaming in modified genome → wrong AGS |
| F2 | Two RGS sequences have the same genome top hit; greedy assignment picks the first in BLAST-report order | One RGS gets the cognate, the other silently gets second-best or orphaned |
| F3 | RGS sequence has no high-confidence match in the genome (e.g., curated/edited, different assembly) | Silently mapped to top hit even if identity is low |
| F4 | RGS is longer than the genome T1 (impossible in well-formed data; indicates wrong input) | Silently mapped, never flagged |
| F5 | RGS sequence is not actually in the source genome at all | Silently mapped to nearest paralog OR silently orphaned (with `--include-orphan-rgs` only, otherwise dropped) |
| F6 | Order-dependence in greedy assignment causes nondeterministic mapping when score ties exist | Mapping varies between runs |

All these failures produce data without raising errors. The intent of this plan is to make every one of them a **pipeline-failing condition** unless the data is verifiably clean.

---

## 3. Design principles

1. **Fail-fast**: any RGS that cannot be cleanly resolved must cause `sys.exit(1)` with a detailed error message listing each unresolved RGS, its best hit (if any), and the specific reason. No `--include-orphan-rgs` escape hatch. No silent skipping.
2. **Deterministic**: same input → same output, no order dependence.
3. **Layered**: try the most reliable signal first (NCBI accession), fall back to BLAST only when necessary. Log which mechanism mapped each RGS.
4. **Symmetric**: both query coverage AND subject coverage must pass thresholds — catches both fragment-RGS-into-full-genome and full-RGS-into-fragment-genome cases.
5. **T1-aware**: explicitly check that RGS is not longer than the genome T1; if it is, the input is malformed.
6. **Cross-verifiable**: every mapping should pass independent checks (accession match AND BLAST verification, where both are possible).

---

## 4. Improvement 1: Exact NCBI accession match (primary mechanism)

### Mechanism
For each RGS sequence:
1. Extract NCBI accession from RGS header. Format: `>rgs_<group>-<species>-<gene>-<source>-<NP_or_XP_accession>_<version>` (e.g., `…-NP_006133_1`)
2. Normalize: extract `NP_006133` (strip trailing `_<digit>` or `.<digit>` version)
3. Build a one-time `genome_accession_index: dict[str, str]` mapping normalized NCBI accession → full genome header, built once from the source proteome
4. Direct dictionary lookup. If hit: confident mapping (`mapped-by-accession`).
5. If RGS has no NCBI accession (worm/fly UniProt-style, hand-curated): skip to Improvement 2.

### Header-format detection
- An RGS header has an NCBI accession iff `parts[-1]` matches regex `^[A-Z]{2}_[0-9]+(_[0-9]+)?$` (e.g., `NP_006133_1`)
- Otherwise treat as non-NCBI (UniProt-style `uniprotQ9V427_INX2`, JGI-style `jgi-jgi21409`, etc.)

### Code sketch
```python
import re

NCBI_ACCESSION_REGEX = re.compile( r'^([A-Z]{2}_[0-9]+)(?:[._][0-9]+)?$' )

def extract_ncbi_accession_from_rgs( rgs_header: str ) -> str | None:
    parts = rgs_header.split( '-' )
    if not parts:
        return None
    match = NCBI_ACCESSION_REGEX.match( parts[ -1 ] )
    return match.group( 1 ) if match else None

def extract_ncbi_accession_from_genome_header( genome_header: str ) -> str | None:
    # Genome header format: g_<gene>-t_<transcript>-p_<protein>-n_<phyloname>
    # We want the protein_id (p_ field)
    if '-p_' not in genome_header:
        return None
    after_p = genome_header.rsplit( '-p_', 1 )[ 1 ].split( '-n_', 1 )[ 0 ]
    match = NCBI_ACCESSION_REGEX.match( after_p )
    return match.group( 1 ) if match else None

def build_genome_accession_index( genome_fasta: Path ) -> dict[ str, str ]:
    """Build {normalized_NCBI_accession: full_genome_header} for all proteins
    in the genome that have NCBI-format protein IDs."""
    index = {}
    with open( genome_fasta ) as f:
        for line in f:
            if not line.startswith( '>' ):
                continue
            header = line[ 1: ].strip()
            accession = extract_ncbi_accession_from_genome_header( header )
            if accession is not None:
                if accession in index:
                    raise ValueError( f'Duplicate NCBI accession in genome: {accession}' )
                index[ accession ] = header
    return index
```

### Behavior on clean cases
- Human SFN RGS (`NP_006133_1`) → exact match to human genome SFN (`NP_006133.1`) → mapped (mechanism: `ncbi_accession`)
- Result: zero ambiguity, zero greedy-order dependence, zero BLAST cost for ~all human HGNC-sourced RGS

### Behavior on edge cases (handled by Improvement 5)
- NCBI accession not found in genome → record as `unresolved: accession_not_in_genome` → fail-fast at end if any unresolved remain
- Multiple RGS for the same accession → fail-fast: `duplicate_rgs_accession`

---

## 5. Improvement 2: Identity ≥95% AND symmetric coverage ≥95% (BLAST fallback)

### When this applies
RGS sequences without NCBI accessions (UniProt, JGI, user-curated). Improvement 1 returned None for these.

### Mechanism
1. Run BLASTP RGS vs source-genome (same as today's script 005/006)
2. For each RGS query, examine all hits (not just top); compute per-hit:
   - `pident` (% identity, BLAST col 3)
   - `query_coverage` = (qend - qstart + 1) / length(RGS) × 100
   - `subject_coverage` = (send - sstart + 1) / length(genome_protein) × 100
3. Accept a hit iff:
   - `pident >= 95.0`
   - `query_coverage >= 95.0`
   - `subject_coverage >= 95.0`
4. After filtering, the RGS may have 0, 1, or multiple acceptable hits.

### T1 length sanity check
- Compute `len(RGS) / len(genome_protein)` ratio. For each accepted hit:
  - If `len(RGS) > len(genome_protein)`: **WARN and treat as unresolved**. T1 is the longest isoform; an RGS longer than the genome T1 indicates either a wrong-species T1 was selected for the proteome, or the RGS is a longer-isoform of the same gene that should not be the reference. Surface this loudly.
  - Even a 1-aa overshoot is flagged.
- Note: the coverage check (subject_coverage >= 95%) catches most of these, but the explicit length comparison gives a cleaner error message.

### Coverage-of-95% rationale
- Identity 95% ensures the sequences are the same protein (above species-level paralog identity in most families)
- Query coverage 95% ensures the RGS isn't a small domain matching a large multi-domain genome protein
- Subject coverage 95% ensures the genome protein isn't a small fragment containing a region of the RGS
- These three together = "essentially the same full-length protein"

### Code sketch
```python
def blast_row_meets_threshold( row, rgs_length, genome_length,
                                min_pident=95.0, min_coverage=95.0 ) -> tuple[bool, str]:
    pident = float( row[ 'pident' ] )
    if pident < min_pident:
        return False, f'pident {pident:.1f} < {min_pident}'

    q_cov = (int( row[ 'qend' ] ) - int( row[ 'qstart' ] ) + 1) / rgs_length * 100
    if q_cov < min_coverage:
        return False, f'query_coverage {q_cov:.1f} < {min_coverage}'

    s_cov = (int( row[ 'send' ] ) - int( row[ 'sstart' ] ) + 1) / genome_length * 100
    if s_cov < min_coverage:
        return False, f'subject_coverage {s_cov:.1f} < {min_coverage}'

    return True, 'pass'

def check_t1_length_invariant( rgs_length, genome_length, rgs_header, genome_header ):
    if rgs_length > genome_length:
        raise PipelineFailure(
            f'RGS LONGER THAN T1 GENOME PROTEIN — invalid input!\n'
            f'  RGS:    {rgs_header} ({rgs_length} aa)\n'
            f'  Genome: {genome_header} ({genome_length} aa)\n'
            f'  T1 proteomes contain the longest isoform per gene. An RGS\n'
            f'  longer than the genome T1 indicates the RGS is a longer\n'
            f'  isoform from outside the T1 set, or the wrong proteome\n'
            f'  build was used. Verify the RGS source and T1 proteome.'
        )
```

---

## 6. Improvement 3: Bidirectional best hit (BBH) validation

### When this applies
For both Improvement 1 (NCBI accession) and Improvement 2 (BLAST fallback). Provides an independent cross-check that the proposed RGS↔genome pair really is each other's best hit, not a one-way paralog match.

### Mechanism
1. After candidate mapping is computed by Improvements 1+2, build the reverse BLAST DB from the RGS FASTA
2. For each candidate genome protein G mapped to RGS R: BLAST G vs RGS DB, take the top hit
3. Confirm: top hit must equal R. If not, the mapping is paralog-confused → unresolved → fail-fast (Improvement 5)

### Notes
- For NCBI-accession-mapped pairs (Improvement 1), BBH is a sanity check that the genome and RGS use the same protein for the same accession — almost always trivially true, but cheap insurance
- For BLAST-mapped pairs (Improvement 2), BBH is more substantively important: it catches the greedy-ordering paralog confusion (F1, F2)

### Implementation cost
- One additional BLAST run: source-genome (just the candidate hits) → RGS DB
- Can be combined with the existing reverse-blast infrastructure (scripts 010-012)

---

## 7. Improvement 4: Hungarian (optimal) assignment instead of greedy

### When this applies
After Improvements 1+2+3 produce a set of valid candidate RGS↔genome pairs, some RGS may have multiple acceptable genome hits and some genome proteins may be candidates for multiple RGS. Resolve to a globally-optimal one-to-one assignment.

### Mechanism
1. Build a bipartite graph: RGS on one side, candidate genome proteins on the other, edges weighted by BLAST bitscore (or identity, configurable)
2. Use `scipy.optimize.linear_sum_assignment` to find the maximum-total-weight matching
3. Verify the assignment is unique (no ties at the optimum). If ties exist → fail-fast (Improvement 5)

### Notes
- For most clean cases (gene groups where each RGS has exactly one high-confidence genome cognate), the bipartite graph is trivial and Hungarian = greedy = same result
- The value of Hungarian shows up in messy cases (gene families with many paralogs at similar identity). Today's greedy is provably suboptimal there.
- `scipy.optimize.linear_sum_assignment` is in scipy core; no new heavy dependencies

### Code sketch
```python
import numpy as np
from scipy.optimize import linear_sum_assignment

def optimal_assignment( candidate_pairs ):
    """candidate_pairs: list of (rgs_id, genome_id, bitscore)
    Returns: list of (rgs_id, genome_id) assignments."""
    rgs_ids = sorted({ p[0] for p in candidate_pairs })
    genome_ids = sorted({ p[1] for p in candidate_pairs })
    rgs_idx = { r: i for i, r in enumerate( rgs_ids ) }
    genome_idx = { g: i for i, g in enumerate( genome_ids ) }

    cost = np.full( (len(rgs_ids), len(genome_ids)), 1e9 )  # high = bad
    for rgs_id, genome_id, bitscore in candidate_pairs:
        cost[ rgs_idx[ rgs_id ], genome_idx[ genome_id ] ] = -bitscore  # maximize

    row_ind, col_ind = linear_sum_assignment( cost )

    assignments = []
    for r, c in zip( row_ind, col_ind ):
        if cost[ r, c ] < 1e9:  # valid candidate edge
            assignments.append( (rgs_ids[ r ], genome_ids[ c ]) )

    return assignments
```

---

## 8. Improvement 5: Strict orphan detection → pipeline failure

### Policy (per user directive May 2026)
**Any RGS that is not cleanly resolved by Improvements 1+2+3+4 causes pipeline failure.** No `--include-orphan-rgs` escape. No silent skipping. The user must explicitly fix the RGS input (remove the problematic entry, change the source, or change the species set) before the pipeline can proceed.

### What counts as "not cleanly resolved"
- RGS has no NCBI accession AND no BLAST hit passing identity ≥95% / coverage ≥95% (Improvement 2 rejected all hits)
- RGS NCBI accession exists in RGS header but is NOT found in the genome accession index (Improvement 1 returned None and Improvement 2 didn't find a substitute hit)
- RGS BBH check failed: candidate genome hit reciprocates to a DIFFERENT RGS (paralog confusion, Improvement 3)
- RGS is longer than its candidate genome match (T1 length invariant violated, Improvement 2)
- Optimal assignment has a tie (two equally good assignments) at the maximum (Improvement 4)
- Two RGS sequences share the same NCBI accession in the input (duplicate RGS)
- An NCBI accession appears twice in the genome (duplicate genome entry)

### Error message format
```
================================================================================
CRITICAL ERROR: RGS identification failed for {N} sequence(s).
================================================================================

The pipeline cannot proceed because the following RGS sequences could not
be cleanly resolved to genome proteins. Per the strict fail-fast policy,
this is treated as malformed input requiring user intervention.

Unresolved RGS sequences and reasons:

  1. {rgs_header_1}
     Reason:        {category}
     Best evidence: {what we found, if anything}
     Suggestion:    {what the user might check}

  2. {rgs_header_2}
     ...

Resolution options:
  - Remove the unresolved RGS sequence(s) from the input FASTA
  - Provide a different RGS sequence (e.g., shorter isoform that fits T1)
  - Use a different reference genome / species70 build that contains the
    expected accession
  - Inspect the BLAST report at {path} for details

NO orphan fallback is available. Fix the input and rerun.
================================================================================
```

### Categories of unresolved RGS to log
- `accession_not_in_genome`: NCBI accession in RGS header doesn't exist in genome
- `no_blast_hit_passes_thresholds`: identity or coverage below 95%
- `bbh_paralog_mismatch`: reciprocal best hit goes to a different RGS
- `rgs_longer_than_t1`: RGS protein is longer than the genome T1 protein
- `assignment_tie_at_optimum`: Hungarian found multiple equally-optimal assignments
- `duplicate_rgs_accession`: same NCBI accession appears in multiple RGS entries
- `duplicate_genome_accession`: same NCBI accession appears in multiple genome entries

---

## 9. Output additions to mapping file (8-output)

The current 3-column mapping (`genome_id<TAB>truncated_rgs<TAB>original_full_rgs`) should be extended to 4 columns:

```
genome_id<TAB>truncated_rgs<TAB>original_full_rgs<TAB>mechanism
```

`mechanism` ∈ `{ncbi_accession, blast_high_confidence, bbh_verified, hungarian_optimal}` — flags HOW each mapping was made. Useful for auditing.

A new sidecar file:
```
8_ai-rgs_identification_report.tsv
columns: rgs_header, status, mechanism, genome_id, pident, query_coverage, subject_coverage, rgs_length, genome_length, bbh_verified, hungarian_alt_count, reason_if_unresolved
```

Lists every RGS with its full evaluation. Even successful mappings get a row, so the user can audit the entire decision process.

---

## 10. Implementation phasing

Recommended order — each phase is independently shippable:

### Phase 1 — Accession match + fail-fast on unresolved
- Add Improvement 1 (NCBI accession match)
- Add Improvement 5 (strict fail-fast); orphans → exit 1
- DO NOT add BLAST fallback yet — any RGS without NCBI accession fails the run
- For human-only HGNC gene groups, this is sufficient
- Tests: 14_3_3 (all 7 NCBI-mapped), confirm zero greedy/BLAST involvement

### Phase 2 — BLAST fallback with thresholds + T1 length check
- Add Improvement 2 (identity/coverage thresholds, T1 length check)
- Enables worm/fly/hydra RGS to be mapped without BLAST top-hit fragility
- Tests: innexin_pannexin (mix of human/worm/fly RGS), confirm all pass

### Phase 3 — BBH verification
- Add Improvement 3 (BBH check on all candidate mappings)
- Catches paralog confusion in BLAST fallback
- Tests: synthetic — inject an RGS that has a paralog with a higher BLAST score than the cognate, confirm BBH rejects it

### Phase 4 — Hungarian assignment
- Add Improvement 4 (replace greedy with linear_sum_assignment)
- Tests: large kinase family with many paralogs, confirm assignment matches expert-curated answer

### Phase 5 — Audit report sidecar
- Add `8_ai-rgs_identification_report.tsv` and the `mechanism` column

---

## 11. Files affected (when implementing)

### Direct
- `gene_groups_COPYME/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/ai/scripts/008_ai-python-map_rgs_to_reference_genomes.py` (rewrite of `create_rgs_genome_mapping` + new helper functions)
- `gene_family_COPYME/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/ai/scripts/008_ai-python-map_rgs_to_reference_genomes.py` (apply same changes — keep in sync)

### Indirect (may need updates depending on phase)
- `009_ai-python-create_modified_genomes.py` — if mapping file format changes (new `mechanism` column), 009 should ignore it or use it for richer logs. Reading current 3-column mapping must still work for backward compat during phased rollout.
- `013_ai-python-extract_reciprocal_best_hits.py` — already patched (2026-05-23). Same: reading current 3-column mapping must keep working.
- `RUN-workflow.sh` — likely no change; the changes are inside Python only

### Downstream propagation (after master is fixed)
- Per the master/instance pattern documented in [project_trees_gene_x_ags_rgs_duplication_bug](../../../../memory/project_trees_gene_x_ags_rgs_duplication_bug.md): after updating `gene_groups_COPYME/.../008` and `gene_family_COPYME/.../008`, propagate to:
  - `gene_groups-hugo_hgnc/.../workflow-COPYME-rbh_rbf_homologs/ai/scripts/008` (downstream instance)
  - All 76 `trees_gene_families/gene_family-*/workflow-COPYME-rbh_rbf_homologs/ai/scripts/008` (downstream per-family instances)
  - Verify via md5sum that all 78 stay in sync after each phase

---

## 12. Testing strategy

### Positive tests (must pass)
- `14_3_3` (7 human HGNC RGS, all NP_*) → all 7 mapped via Phase 1 (NCBI accession). Zero BLAST involved.
- `innexin_pannexin_channels` (mix of human NP_*, worm uniprotQ*, fly uniprotQ*) → human via Phase 1; worm/fly via Phase 2 BLAST with thresholds + BBH.
- `abc_transporters` (large family, many human paralogs) → all paralogs cleanly mapped via Hungarian (Phase 4); no greedy-order surprises.

### Negative tests (must fail-fast with clear errors)
- Synthetic RGS with `NP_99999999_1` (accession not in genome) → fail with `accession_not_in_genome`
- Synthetic RGS that's 50 aa longer than the genome T1 → fail with `rgs_longer_than_t1`
- Synthetic RGS pair where two different RGS have the same NCBI accession → fail with `duplicate_rgs_accession`
- Synthetic gene group with 2 RGS that both BLAST-best-match the same genome protein → fail with either `bbh_paralog_mismatch` or `assignment_tie_at_optimum`

### Regression tests
- After each phase, re-run on 14_3_3 → result unchanged (still 7 mapped, same cognates)
- After each phase, re-run on innexin_pannexin → result no worse than current V2 RUN
- After all phases, audit `8_ai-rgs_identification_report.tsv` for any gene group with status != `mapped-by-{accession,blast,bbh,hungarian}` → should be zero across the curated HGNC reference set

---

## 13. Open questions for the user (to revisit before implementation)

1. **Threshold tunability**: should `95.0` for identity and coverage be hardcoded constants, or exposed via `START_HERE-user_config.yaml`? Recommend: hardcoded with a top-of-script constant for now; surface to YAML only if a future gene family genuinely needs a different threshold.

2. **`mechanism` column ordering in 8-output**: prefer at the end (column 4) for backward compat, or insert as column 2 for visibility? Recommend: end of file (column 4), so existing 3-column readers don't break.

3. **Bitscore vs identity as Hungarian edge weight**: bitscore is BLAST-native and length-aware; identity is more interpretable. Recommend: bitscore as primary, identity as a secondary tie-breaker.

4. **Truncation of long RGS headers (BLAST 50-char limit)**: do we keep the current truncation behavior, or use accession-based short IDs for the BLAST database? Recommend: keep current truncation (it works; downstream 009/013 already handle the truncation map), and just ensure new code consults the right column.

5. **`009_ai-python-create_modified_genomes.py` orphan-handling flag**: with Improvement 5 making orphans a fail condition, the `--include-orphan-rgs` flag in script 009 becomes dead code. Recommend: leave the flag in place for one release (warns that it has no effect), then remove in the release after.

---

## 14. Success criteria

After all 5 phases are implemented and propagated:

- Every RGS in every gene group/family is either (a) cleanly mapped via one of the 4 mechanisms or (b) causes the run to fail with a specific diagnostic
- The `8_ai-rgs_identification_report.tsv` for any successful run shows 100% of RGS in `mapped-by-*` status
- Re-running `homolog_counts` after this fix lands (combined with the 013 fix from 2026-05-23) produces AGS files with zero `>g_*-<rgs_source>` duplications — and downstream homolog count tables become structurally correct without the additive-count workaround currently in `homolog_counts/.../003_*.py` and `004_*.py`

---

## 15. Notes on order-of-operations across the broader pipeline

This plan only changes script 008's MAPPING logic. The flow into 009 (modified genomes) and 013 (RBH filter) is preserved. After this plan is implemented:

- 009 receives cleaner mapping → modified genomes are correct
- 013 (already patched) drops the right queries → CGS is correct
- 016 adds RGS as usual → AGS has each protein exactly once
- `homolog_counts` script 003/004 additive counting becomes correct (RGS isn't duplicated in AGS, so RGS_count + g_count = unique_protein_count)

The whole upstream → downstream chain becomes structurally sound without per-script workarounds.
