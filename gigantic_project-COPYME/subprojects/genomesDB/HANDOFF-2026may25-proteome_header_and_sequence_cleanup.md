# HANDOFF — genomesDB upstream proteome cleanup (post-secretome)

**Date filed**: 2026-05-25
**Belongs in**: `genomesDB/` (probably as a new STEP that runs after STEP_4 produces
the final per-species T1 proteomes, OR as an in-place pass at the end of STEP_4)
**Priority**: Do **after** the secretome work lands. Not blocking secretome.
**Surfaced by**: build_evidence_table v1 run on species70, 2026-05-25

## What needs fixing

Per the user (Eric, 2026-05-25):

> "This needs an upstream fix in genomesDB — maybe we can make it after the
> secretome for future projects. One clean handling of headers > 240 characters
> and removal of all non-aa characters from sequences."

Two coupled passes on every per-species T1 proteome FASTA:

### 1. Header length

- **Rule**: protein FASTA headers must be ≤ 240 characters (safe margin under
  the 255-byte filesystem filename limit).
- **Why 240, not 255**: tools downstream often append suffixes
  (`_metapredict_<id>.txt`, `_signalp_<id>.gff3`, etc.) so the protein-ID
  portion of any per-protein file must leave room for the suffix.
- **Current pain**: at exactly 255 chars, downstream per-protein output
  filenames silently get truncated by the filesystem, breaking ID-based
  joins. Concretely affects EvidentialGene multi-locus concatenated transcript
  IDs in species like Sphaeroforma_arctica (see "Concrete trigger" below).
- **Fix per the user**: ONE canonical filter. Probably drop the affected
  proteins from the proteome FASTA entirely (they're imperfect-assembly
  artifacts of evigene merging multiple gene loci into one transcript).
  Compare to the existing per-tool filters in
  `annotations_hmms/BLOCK_signalp/workflow-COPYME-run_signalp/ai/scripts/000_ai-python-filter_proteome_long_headers.py`
  and `annotations_hmms/BLOCK_tmbed/.../000_ai-python-filter_proteome_long_headers.py`
  — these implement the same intent per-BLOCK; the fix below moves that
  upstream so every downstream BLOCK sees clean proteomes by construction.

### 2. Sequence character cleanup

- **Rule**: remove all non-amino-acid characters from sequences. Standard
  set is the 20 canonical AAs plus the 4 ambiguity codes (B, Z, J, U / X / O
  depending on convention — user to confirm exact alphabet on resume).
- **Why**: many tools fail or produce silently-wrong output on `*`,
  whitespace, digits, `<`, `>`, `-`, lowercase mixed with uppercase, etc.
- **Current pain**: not yet quantified — surfaced as a hypothesized issue
  per user; concrete failures TBD.

## Concrete trigger (Sphaeroforma_arctica example)

```
FASTA header (full, 308 chars — what's actually in the proteome):
  g_Sarc_Sarc4_g11901_Sarc4_g11902_Sarc4_g11903_Sarc4_g11904
    -t_Sarc_Sarc4_g11901T_Sarc4_g11902T_Sarc4_g11903T_Sarc4_g11904T
    -p_Sarc_Sarc4_g11901T_Sarc4_g11902T_Sarc4_g11903T_Sarc4_g11904T
    -n_HolozoaUNOFFICIAL_Phylum10919UNOFFICIAL_Ichthyosporea_Ichthyophonida
        _Family10942UNOFFICIAL_Sphaeroforma_arctica

InterProScan / CDD / etc. annotation TSV's protein ID (255 chars, truncated):
  g_Sarc_Sarc4_g11901_Sarc4_g11902_Sarc4_g11903_Sarc4_g11904
    -t_..._T_..._T
    -p_..._T_..._T
    -n_HolozoaUNOFFICIAL_Phylum10919UNOFFICIAL_Ichthyosporea_Ichthyophonida
    ← cut here mid-string; missing _Family10942UNOFFICIAL_Sphaeroforma_arctica
```

When the evidence-table pivot joins annotation TSVs to the proteome FASTA on
protein identifier, the truncated rows don't match anything. The pivot
currently warn-and-skips them; the affected proteins appear in the evidence
table with zero annotations across all 17 databases.

Per-species orphan-row counts on the species70 + RUN_1 annotation database
(2026-05-25) are bounded (Sphaeroforma_arctica = 4 in cdd; other species
likely similar single-digit counts). The secretome filter chain naturally
drops these proteins at the SignalP step (they have no SignalP call because
the SignalP BLOCK already filters them out via its own 000_ filter), so the
secretome result is unaffected — but the issue is real and worth fixing
properly at the source.

## Where in genomesDB

Two reasonable placements (user to decide on resume):

1. **In STEP_4 itself** (`workflow-COPYME-create_final_species_set`): add a
   process that produces the clean per-species FASTA as part of the species70
   creation. Pros: clean FASTAs are part of the canonical species70 output
   from day one. Cons: rebuilds STEP_4 = touches a recently-stable
   subproject.

2. **As a new STEP_5** (`workflow-COPYME-clean_proteome_FASTAs` or similar):
   reads STEP_4's per-species FASTAs, writes cleaned versions to
   STEP_5's output_to_input/, becomes the new canonical proteome source for
   all downstream subprojects. Pros: additive, doesn't touch STEP_4. Cons:
   downstream subprojects need to repoint their paths from STEP_4 → STEP_5.

User leaning: TBD on resume.

## Per-BLOCK 000_ filters become redundant after this

Once genomesDB delivers clean FASTAs, the per-tool `000_ai-python-filter_proteome_long_headers.py`
preprocess steps in BLOCK_signalp + BLOCK_tmbed become redundant (the input
FASTAs they receive are already clean by construction). Optional cleanup
after the upstream fix: remove those per-BLOCK preprocess steps + their
process invocations in main.nf.

## Out-of-scope for this handoff

- Fixing the truncation in BLOCK_build_annotation_database parsers
  (parse_interproscan, parse_cdd, etc.): proper fix is upstream in
  genomesDB per the user; don't patch the parsers.
- Reconnecting the orphan 255-char-truncated rows back to their FASTA
  full-IDs by prefix matching in the evidence_table pivot: same — fix is
  upstream, don't patch around in the pivot.
