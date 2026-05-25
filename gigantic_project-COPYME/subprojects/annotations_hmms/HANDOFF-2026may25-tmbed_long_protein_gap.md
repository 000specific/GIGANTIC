# HANDOFF — TMBed long-protein gap

**Date**: 2026-05-25 (Sunday)
**Resume on**: Tuesday / Wednesday next week (UF IT is on holiday Monday; HiPerGator
has been unstable today with bad nodes in the c0706a-s* family and the moroz
QOS has been heavily contended)

## Current state — annotation tools

All 5 tools have `output_to_input/` coverage for all 70 species at the
**short-protein side**. The **long-protein side (>4000 aa) is incomplete
for 65/70 species** because TMBed RUN_3 long (the only CPU-mode long-protein
run) OOM-killed before consolidating.

| Tool | Coverage in `output_to_input/` | Notes |
|------|-------------------------------|-------|
| InterProScan | 70/70 (`.tsv`) | complete (length-agnostic) |
| DeepLoc | 70/70 (`.csv`) | complete (length-agnostic) |
| SignalP | 140 = 70×{FAST, SLOW} (`.tsv`) | complete |
| **TMBed** | **70/70 (`.tsv`) but with long-protein gap** | see below |
| MetaPredict | 70/70 (`.tsv`) | complete (length-agnostic) |

## The TMBed long-protein gap (concrete numbers)

TMBed splits its inference path by sequence length: ≤4000 aa runs on GPU
(fast), >4000 aa runs on CPU (very slow, memory-heavy). The TMBed BLOCK's
RUNs reflect this split:

- `workflow-RUN_2-run_tmbed_short` (41 species, COMPLETED)
- `workflow-RUN_4-run_tmbed_short` (24 species, COMPLETED)
- `workflow-RUN_1-run_tmbed` (full run — both short + long — for 5 holomycota/holozoa outgroups, hand-consolidated 2026-05-25)
- `workflow-RUN_3-run_tmbed_long` (intended to cover >4000 aa for 65 species, **OUT_OF_MEMORY at 2026-05-25 10:31 after 1d 19h 44m, requested 375 GB, only 25 of 65 species' raw `.3line` files produced before kill, never consolidated**)

Per-species audit script lives in `gigantic_ai/ai_documentation/debugging/`
(if not there yet, regenerate with the same logic as the inline python heredoc
used during 2026-05-25 audit; it counts proteins >4000 aa per species70 FASTA
and counts how many have `TM_Helix_Count == 'None'` in the corresponding TSV).

**Audit headline numbers (2026-05-25):**

| Metric | Count |
|--------|------:|
| Total proteins in species70 | 1,375,926 |
| Proteins >4000 aa | 4,735 |
| Species with ≥1 long protein | 70/70 |
| Long proteins WITH TMBed prediction | 61 (all from RUN_1 hand-consolidate of 5 outgroups) |
| Long proteins WITHOUT TMBed prediction | **4,674** |
| Species fully covered (no missing long) | 5/70 (the RUN_1 outgroups) |
| Species with missing long predictions | 65/70 |

**Biggest individual gaps** (species : missing-long-protein count):

| Species | Missing |
|---------|--------:|
| Amphiscolops_sp_MND2022 | 180 |
| Schizocardium_californicum | 169 |
| Dysidea_avara | 149 |
| Crassostrea_virginica | 139 |
| Sycon_ciliatum | 134 |
| Branchiostoma_lanceolatum | 130 |
| Acropora_muricata | 128 |
| Lineus_longissimus | 127 |
| Pocillopora_verrucosa | 125 |
| Haliotis_asinina | 125 |
| Nematostella_vectensis | 121 |
| Lytechinus_variegatus | 121 |
| Biomphalaria_glabrata | 121 |

(See the full per-species audit table re-runnable from
`output_to_input/BLOCK_tmbed/*.tsv` + species70 FASTAs.)

## Why the gap is "OK for now" — secretome decision

Secretome generation needs **SignalP + short-TMBed**. SignalP is 100%
complete. Short-protein TMBed predictions are also 100% complete. The gap
is only for proteins >4000 aa, which are extremely unlikely to be
classical signal-peptide-bearing secreted proteins (most secreted proteins
are <1000 aa). Decision (2026-05-25): proceed with secretome generation
using current data; treat the 4,674 long-protein TMBed gap as a separate
follow-up that does NOT block secretome work.

If a downstream analysis needs TMBed topology for the long-protein
cohort, those proteins will currently show `TM_Helix_Count = None` in the
TSV — easy to filter / re-flag.

## Options when resuming (Tuesday/Wednesday)

In ascending order of effort:

1. **Accept the gap permanently.** Add a note in BLOCK_tmbed README that
   long-protein TMBed predictions are missing for 4,674 proteins across
   65 species; downstream consumers must check `TM_Helix_Count == 'None'`
   to detect.

2. **Per-species batch restart of TMBed long.** Split the 65-species
   manifest into N smaller manifests (e.g., 1 species per SLURM job, or
   grouped by total >4000 aa protein count). Each sub-job requests
   modest memory (e.g., 100-150 GB) and short walltime. Failure of one
   species does not OOM-kill the rest. Probably the right answer —
   matches the per-species-job pattern other tool BLOCKs use.

3. **Restart RUN_3 long as-is with more memory.** Bump from 375 GB
   to e.g. 700 GB and resume from RUN_3's cached `.3line` files (25
   species already done). Risky because we don't know the actual per-
   protein memory footprint of TMBed CPU mode — could OOM again at the
   same memory level just deeper in.

**Recommended path:** option 2. Split the 65 missing-long-protein-species
into per-species SLURM jobs in a new `workflow-RUN_5-run_tmbed_long_per_species`
(or similar) RUN dir copied from `workflow-COPYME-run_tmbed`. Walltime
should be generous (each species' >4000 aa cohort can be very slow on CPU);
the longest species like Amphiscolops_sp_MND2022 (180 long proteins) may
genuinely need 24-48 hr per species.

## State preserved (do not touch on resume — for context)

- 5 hand-consolidated TSVs in `BLOCK_tmbed/workflow-RUN_1-run_tmbed/OUTPUT_pipeline/3-output/`
- 5 corresponding symlinks in `output_to_input/BLOCK_tmbed/` for the
  Parvularia/Fonticula/Abeoforma/Creolimax/Ichthyophonus outgroups
- 25 partially-completed `.3line` files in
  `BLOCK_tmbed/workflow-RUN_3-run_tmbed_long/OUTPUT_pipeline/2-output/`
  (all for species already covered by RUN_2/RUN_4 short, so usable for
  re-consolidation but not strictly needed)
- build_annotation_database RUN_1 has a COMPLETED OUTPUT_pipeline reflecting
  the 65/70 TMBed state; if/when long-protein TMBed predictions land, a
  re-run of build_annotation_database will roll the new data through.

## Reasons HiPerGator was unstable today (context, not action items)

- Bad c0706a-s* nodes: 3 separate sbatch submissions assigned to
  c0706a-s10 / s12 / s16 died with `RaisedSignal:53 (Real-time_signal_19)`
  within 1-2 sec of start, before any log was produced. Workaround: added
  `--exclude=c0706a-s10,c0706a-s12,c0706a-s16` to one resubmit; the next
  one landed on c0706a-s6 and ran cleanly. Almost certainly a bad NFS /
  prolog state on the s10/s12/s16 nodes specifically.
- moroz QOS budget (50 CPU / 400 GB) was heavily used by the long-running
  `gigantic` job (33088764, 1 CPU, 4 GB, 2+ days uptime) plus a 45-CPU /
  338 GB `s2_small` job (33216163) — left only 2-4 CPUs free for
  annotation_database, hence dropped from 8C/60G → 2C/24G to fit.
- Both should clear naturally over Memorial Day weekend if other jobs
  finish or are scancelled.
