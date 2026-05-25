# Handoff — 2026 May 25 — SNAP family + trees_gene_groups STEP_2/3 in flight

Pre-compaction handoff for the next session. State is mid-flight on two
fronts: an in-flight STEP_2 trial in **trees_gene_groups** (hugo_hgnc),
and a pending **SNAP family** setup in **trees_gene_families** awaiting
the user's RGS file.

---

## A. In-flight work in trees_gene_groups/gene_groups-hugo_hgnc

### A.1 STEP_1 retry for 6 JVM-crashed gene groups (RUNNING)

The first STEP_1 dispatch (2026-05-24 evening) processed 2060 gene
groups. Final outcome:

- **2054 succeeded** (AGS files symlinked to
  `gigantic_project-COPYME/subprojects/trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/STEP_1-homolog_discovery/gene_group-<name>/16_ai-ags-*.aa`)
- **6 failed** with NextFlow `ERROR ~ a fault occurred in an unsafe
  memory access operation` (JVM SIGSEGV on startup, ~1 sec elapsed)

The 6 all came from SLURM block `s1_small_blk_170` on node
`c1105a-s8`. A **parallel Claude session** independently reported 46
identical exit-53 failures on **c0706a-s7/s9/s12**. Same symptom,
different rack. Cause: **HiPerGator had a major cluster upgrade a few
weeks ago** — some nodes are running stale configs / inconsistent
libraries / borked JVM environment and were not cleanly reimaged.

**Retry dispatched** with the 6 in a manifest:
- Manifest:
  `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups-hugo_hgnc/INPUT_user/gene_groups_manifest_step1_retry_jvm_crashes.tsv`
- YAML key in
  `STEP_1-homolog_discovery/workflow-rbh_rbf_homologs/START_HERE-user_config.yaml`
  set to point at that manifest
- Job: `s1_small_blk_01` (job 33217014) RUNNING on `c0707a-s26` (different node)

**The 6 gene groups**:
- transcription_factor_cp2_family
- solute_carrier_family_76
- nherf_family_pdz_scaffold_proteins
- iswi_complexes
- drebrin_family
- cask_family

**After retry succeeds**: revert STEP_1 YAML's `gene_groups_manifest`
back to `""` so future full STEP_1 runs process all gene groups by
default.

**Action on cluster side**: worth a heads-up to UFRC support listing
the 4+ bad nodes (`c0706a-s7/s9/s12`, `c1105a-s8`) — they should be
fixed or drained.

### A.2 STEP_2 trial for SYT/VAMP/STX/TRP (3 of 4 done, TRP re-running)

A 4-gene-group STEP_2 trial was dispatched in
`workflow-RUN_1-syt_vamp_stx_trp/`:

| Gene group | Status |
|---|---|
| syntaxins | ✅ NextFlow Succeeded 6/6 (38m), newick at `output_to_input/.../STEP_2-phylogenetic_analysis/workflow-RUN_1-syt_vamp_stx_trp/gene_group-syntaxins/*.fasttree` |
| synaptotagmins | ✅ Succeeded 6/6 (1h17m), newick published |
| vesicle_associated_membrane_proteins | ✅ Succeeded 6/6 (2m), newick published |
| transient_receptor_potential_cation_channels (TRP) | ❌ MAFFT OOM killed (2682 sequences, 40,196 aligned columns) |

(Note: the wrap script printed false `FAILED:` for the 3 successes due
to a publish-loop-exit-status bug — fixed via `; true` for future runs;
the in-flight wraps had the bug baked in but the data was actually
published correctly.)

**TRP re-run dispatched** in a separate trial dir:
- `STEP_2-phylogenetic_analysis/workflow-RUN_2-trp_large_resources/`
- Manifest:
  `INPUT_user/gene_groups_manifest_step2-trp.tsv`
- Resources: `slurm-standard` mode, **45 CPU / 338 GB / 96 h**, fasttree only
- Job: `s2_small_transient_receptor_potential_cation_channels` (job 33216163) RUNNING on `c0702a-s7`

### A.3 STEP_3 — pending

After both A.1 retry and A.2 TRP re-run finish, run STEP_3 for all 4
gene groups (SYT/VAMP/STX/TRP). STEP_3 will need to consume newicks
from **two** STEP_2 trials:

- SYT/VAMP/STX from `workflow-RUN_1-syt_vamp_stx_trp/`
- TRP from `workflow-RUN_2-trp_large_resources/`

The STEP_3 orchestrator's `step2_run_name:` YAML key takes ONE trial.
Cleanest path:

1. Create
   `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups-hugo_hgnc/INPUT_user/gene_groups_manifest_step3-syt_vamp_stx.tsv`
   (the 3 from RUN_1) and a separate one for TRP.
2. Two STEP_3 trial dirs:
   - `workflow-RUN_1-syt_vamp_stx/` (step2_run_name = workflow-RUN_1-syt_vamp_stx_trp)
   - `workflow-RUN_2-trp/` (step2_run_name = workflow-RUN_2-trp_large_resources)
3. Run both. STEP_3 is fast (seconds-minutes per render).

---

## B. SNAP family in trees_gene_families (PENDING — awaiting user RGS)

User wants to characterize the **SNAP family** (Soluble NSF Attachment
Proteins; works with SNAREs in vesicle fusion). HGNC doesn't have a
gene_group for it, so it'll run as a regular **gene family** in
`trees_gene_families/`.

**Structure of trees_gene_families** (different convention from trees_gene_groups):
- Template: `gene_family_COPYME/` (underscore)
- Each gene family is its own instance: `gene_family-<name>/` (hyphen)
- Each instance has its own STEP_1/STEP_2/STEP_3 (single-track, no multi-trial pattern)

**Open questions for the user** (asked but not yet answered before
compaction):

1. **Sanitized family name** — `snap_family`? `snap_soluble_nsf_attachment_proteins`? Used in the dir name and filenames.
2. **The RGS FASTA file** — user said they'll provide. Standard header
   format:
   ```
   >rgs_<family>-human-<HGNC_symbol>-<source>-<identifier>
   e.g. >rgs_snap_family-human-NAPA-uniprot-P54920
   ```
3. **RGS mode** — full-length (default for "regular gene family")?

**Setup plan once user provides RGS + name**:

```bash
cd gigantic_project-COPYME/subprojects/trees_gene_families/

# 1. Create instance from template
cp -r gene_family_COPYME gene_family-<sanitized_name>

# 2. Place RGS in INPUT_user
cp <user_provided_rgs.aa> \
   gene_family-<sanitized_name>/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/INPUT_user/

# 3. Edit STEP_1 YAML:
#    - gene_family.name: "<sanitized_name>"
#    - gene_family.rgs_full_length_file: "INPUT_user/<filename>.aa"
#    - rgs_sequence_is_full_length: true   (full-length default)

# 4. Copy COPYME → workflow-RUN_01-rbh_rbf_homologs and run
cd gene_family-<sanitized_name>/STEP_1-homolog_discovery
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
cd workflow-RUN_01-rbh_rbf_homologs
bash RUN-workflow.sh
```

**Important caveat**: the gene_family STEP_1 workflow is **independent
of the trees_gene_groups changes I made today** (parser fix, OTI
publish, manifest support, etc.). I haven't touched it. The
gene_family_COPYME template may have the same kind of issues
(hardcoded `parts[3]` parser for RGS headers, missing OTI publish
logic, NextFlow 26.x compatibility). Worth checking before dispatching
SNAP. If user uses a UniProt-style RGS header (the format the existing
gene_family_COPYME YAML shows in its example —
`>rgs_channel-human_worm_fly-innexin_pannexin_channels-...`), the
trees_gene_families parser may work fine without my fixes. But this
needs verification.

---

## C. Recent infrastructure issues (context, not action items)

- **HiPerGator cluster upgrade** completed a few weeks ago. Some nodes
  have post-upgrade leftover state causing JVM SIGSEGV on startup
  (exit 53, "unsafe memory access").
- **Known bad nodes**: `c0706a-s7/s9/s12`, `c1105a-s8`. Worth reporting
  to UFRC.
- **Symptom signature**: NextFlow process dies within ~1 sec of
  startup; logs show only the "fault occurred in an unsafe memory
  access operation" line; no real pipeline work happens. Easy to spot.

---

## D. Open structural changes from this session (already done, just for awareness)

All applied to **trees_gene_groups** template (`gene_groups-COPYME`)
and instance (`gene_groups-hugo_hgnc`):

1. **Renames**: STEP_0 + STEP_1 dropped the `-COPYME-` infix
   (single-track workflows: `workflow-rbh_rbf_homologs/`,
   `workflow-hgnc_gene_groups/`). STEP_2 + STEP_3 keep `workflow-COPYME-*/`
   as template for multi-trial workflow-RUN_NN siblings.
2. **STEP_2/STEP_3 multi-trial**: per-gene-group sub-runs inherit the
   parent's basename, e.g. `workflow-RUN_1-syt_vamp_stx_trp/` at STEP_2
   root creates `gene_group-X/workflow-RUN_1-syt_vamp_stx_trp/` per
   gene group. COPYME-guard refuses to run from `workflow-COPYME-*/`.
3. **STEP_3 step2_run_name YAML key**: picks which STEP_2 trial to
   consume; auto-detect if empty + only one RUN dir exists, else
   fail-fast and list options.
4. **Manifest support**: `species_keeper_manifest` (STEP_1 only) and
   `gene_groups_manifest` (STEP_1/2/3) optional override TSVs in
   subproject-level `INPUT_user/`.
5. **OTI publish hooks**: STEP_1 + STEP_2 wrap scripts now symlink
   per-gene-group outputs to subproject `output_to_input/`. Trailing
   `; true` guards against false-FAILED reports when globs don't match.
6. **read_config YAML parser fix**: strip comments BEFORE stripping
   quotes (was getting confused by `key: "value"  # e.g. "other"`).
7. **render_trees.py**: reads `step2_run_name` from per-gene-group YAML
   so it consumes the right trial's newicks.
8. **Retroactive symlink script**:
   `STEP_1-homolog_discovery/RUN-publish_existing_to_output_to_input.sh`
   for already-completed runs that lack OTI symlinks.
9. **trees_gene_groups parser regressions**: scripts 001 (validate_rgs),
   005 (generate_blastp_commands-rgs_genomes), 018
   (restore_full_length_rgs), main.nf `extract_rgs_species` all fixed
   to handle HGNC 5-field header format. Script 008 species-matcher
   gained Genus_species translation dict (with structural TODO comment
   flagging that loading INPUT_user/rgs_species_map.tsv would be a
   cleaner long-term fix; same TODO in script 007).
10. **NextFlow 26.x compatibility**: removed top-level
    `workflow.onComplete` blocks from all main.nf files. Docs:
    `gigantic_project-COPYME/NEXTFLOW_26_COMPATIBILITY.md` and
    `NEXTFLOW_26_COMPATIBILITY.md` at repo root.

---

## E. Next-session priorities (in order)

1. Wait for STEP_1 retry (A.1) and TRP STEP_2 RUN_2 (A.2) to finish;
   verify outputs land in output_to_input correctly.
2. Set up SNAP family (B) once user provides RGS + name.
3. Dispatch STEP_3 for the 4 STEP_2 trial outputs (A.3).
4. Cluster bad-nodes report to UFRC (C).
