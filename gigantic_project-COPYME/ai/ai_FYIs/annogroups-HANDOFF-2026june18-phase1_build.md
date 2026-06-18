<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: Cross-compaction handoff for the in-flight `annogroups` subproject
         build (Phase 1). Read this + the design spec before continuing.
Scope:   The new annogroups subproject build and its design context.
============================================================================ -->

# HANDOFF — `annogroups` subproject, Phase 1 build (2026-06-18)

## 0. READ FIRST (in order)

1. **Design spec (authoritative, user-approved)**:
   `research_notebook/research_ai/subproject-annogroups/DESIGN-annogroups_subproject.md`
2. This handoff (current build state + next steps).
3. Conventions as always: `ai/ai_FYIs/gigantic_conventions.md`.

Session is rooted at **`GIGANTIC/`** (framework development per §16) — this is a
new *framework* subproject, not a user addition.

## 1. What we're building

A new first-class **`subprojects/annogroups/`** subproject that produces
**annogroups** as a reusable product. It replaces the old `single`/`combo`/`zero`
scheme (which lived inside `annotations_X_ocl` Script 001).

**Four canonical annogroup types** (canonical GIGANTIC terms, like
`phylogenetic_block`), computed **per source database** (pfam, gene3d, tmbed,
signalp, deeploc, …):

| Type | Definition | Identifier |
|---|---|---|
| `annogroup_feature` | sequences sharing one feature (multi-membership) | `annogroup_<source>_<accession>` e.g. `annogroup_pfam_PF00001` |
| `annogroup_combination` | sequences sharing the same **distinct set** of features (unordered, alphabetical key) | `annogroup_<source>_combination<NNNNN>` + map |
| `annogroup_architecture` | sequences sharing the same **ordered** arrangement of positional features (N→C by start,stop) | `annogroup_<source>_architecture<NNNNN>` + map |
| `annogroup_absent` | sequences (in the proteome universe) with **no** feature from the source | `annogroup_<source>_absent` |

**Locked design decisions** (do NOT re-litigate — user-approved):
- A **feature** = `(source, annotation_identifier)` from annotations_hmms.
- **Architecture grouping key = coord-FREE ordered accession pattern** (so homologs
  group); each sequence's **coordinate-tagged** architecture
  (`PF00001_start10_stop50,…`) is stored on its **membership row**, not the shared key.
- **combination** = distinct set, **alphabetically** sorted (canonical key); copies ignored.
- **absent** needs the full proteome universe (genomesDB STEP_4) — to enumerate
  complete membership, the source must have run over every species70 proteome.
- **One parser plugin per source** (`ai/scripts/parsers/<source>.py`); the four-type
  construction is shared. New source = new parser, nothing else changes.
- **How many types a source yields (3 or 4) is data-determined**, not a user knob
  (whole-protein sources like deeploc → no architecture).
- Counter IDs (combination/architecture) assigned **deterministically** (sort keys, number).
- All inter-subproject I/O via `output_to_input/` (§2) — no other path.

## 2. Build status — Phase 1 IN PROGRESS

### DONE (written + compile-clean)
`subprojects/annogroups/`:
- `BLOCK_build_annogroups/workflow-COPYME-build_annogroups/ai/scripts/`:
  - `utils_annogroups.py` — Feature namedtuple, ID formatters, parser-plugin contract, helpers
  - `001_ai-python-resolve_sources_and_universe.py` — discover parsers + resolve `sources:` + build proteome universe
  - `002_ai-python-build_annogroups.py` — generic builder: imports `parsers/<source>`, builds the 4 types + map + membership
  - `003_ai-python-validate_results.py` — fail-fast cross-checks (partition checks, absent∪annotated==universe, counts)
  - `004_ai-python-write_run_log.py` — §45 run log
  - `parsers/__init__.py`, `parsers/pfam.py` — first source parser
- `START_HERE-user_config.yaml` — species70, sources: all, input paths, exec/slurm knobs
- `output_to_input/.gitkeep`, `upload_to_server/.gitkeep`

### TESTED
- **Script 001 runs clean**: parsers discovered = [pfam]; **proteome universe = 1,375,926 sequences**; sources manifest + universe written to `OUTPUT_pipeline/1-output/`. (~4 s.)

### NOT YET DONE (the next steps)
1. **Smoke-test 002 + 003 on pfam** (the build + validation). Command pattern
   (run directly, fast iteration — same as integrator smoke tests):
   ```bash
   cd subprojects/annogroups/BLOCK_build_annogroups/workflow-COPYME-build_annogroups
   OUT="$PWD/OUTPUT_pipeline"   # 001 already ran; universe present
   python3 ai/scripts/002_ai-python-build_annogroups.py --source pfam --config START_HERE-user_config.yaml --output_dir "$OUT"
   python3 ai/scripts/003_ai-python-validate_results.py --source pfam --config START_HERE-user_config.yaml --output_dir "$OUT"
   ```
   Watch: feature/combination/architecture/absent counts; validation PASS. Sanity:
   absent ≈ 1.38M − (pfam-annotated, ~?); annotated ≈ proteins with ≥1 pfam.
   ⚠️ 002 holds the 1.38M universe + membership in memory — fine locally, but watch RSS.
2. **Write the workflow machinery** (NOT yet written): `ai/main.nf`,
   `ai/nextflow.config`, `ai/conda_environment.yml` (env `aiG-annogroups-build_annogroups`,
   python>=3.11 + pyyaml + `nextflow>=23,<26`), `RUN-workflow.sh` (§29; copy/adapt the
   integrator's), `upload_manifest.tsv`, `INPUT_user/README.md`.
   - main.nf wiring: `resolve_sources_and_universe` (once) → read `1_ai-sources_manifest.tsv`
     via `splitCsv(header:true)` into a sources channel → `build_annogroups` (per source) →
     `validate_results` (per source) → collect → `write_run_log`. (Mirror the integrator
     main.nf; per-source fan-out like the integrator's per-structure fan-out.)
3. **Run end-to-end via NextFlow** (local, env auto-creates `<26` nextflow; `export TMPDIR=/tmp`
   before slurm — see memory `reference_sanitize_tmpdir_before_slurm_submit`).
4. **Docs** (§3/§42/§48/§56): subproject README+AI_GUIDE, BLOCK README+AI_GUIDE,
   workflow README+ai/AI_GUIDE, INPUT_user README. Plus `RUN-update_upload_to_server.sh`
   (thin wrapper — copy integrator's). Add annogroups to the project landing/AI_GUIDE if listed.
5. **PRESENT Phase 1 to the user for review** before adding more parsers or touching downstream.

### LATER PHASES (after Phase 1 sign-off)
- Add per-source parsers (gene3d, smart, cdd, superfamily = positional like pfam;
  tmbed/metapredict = positional segments/regions, feature-level "has-X"; signalp;
  deeploc = whole-protein → feature+combination+absent only, no architecture).
  Each parser knows its own annotations_hmms `output_to_input/` location:
  pfam/gene3d/etc → `BLOCK_interproscan_parsed/<db>/`; tmbed→`BLOCK_tmbed/`;
  signalp→`BLOCK_signalp/`; deeploc→`BLOCK_deeploc/`; metapredict→`BLOCK_metapredict/`.
- **Restructure downstream (breaking, user-accepted)**: `annotations_X_ocl` Script 001
  → *load* annogroups instead of *create*; integrator `BLOCK_annotations_X_orthogroups`
  → consume from `annogroups/output_to_input/`. ⚠️ 4 types × many sources ≫ today's ~74k
  pfam single+combo → OCL `path_states` volume could explode; **estimate before full OCL re-run.**

## 3. Input data (verified on disk, 2026-06)

- **pfam features**: `annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/pfam-<phyloname>.tsv`
  (70 files = species70). Cols: `Protein_Identifier`, `Accession` (PF#####), `Match_Start`, `Match_End`.
- **proteome universe**: `genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes/*.aa`
  (70 FASTAs; headers `>g_..._n_<phyloname>` = full GIGANTIC IDs; universe = 1,375,926 seqs).
- **available sources** in the annotation DB: cdd, deeploc, funfam, gene3d, go, interproscan,
  metapredict, ncbifam, panther, pfam, prints, sfld, smart, superfamily, tmbed (+ signalp where present).
- Reference for the per-source-parser pattern: `annotations_hmms/BLOCK_build_annotation_database`
  (001 discover + `parse_<tool>` per source). Reference BLOCK scaffold: the integrator BLOCK
  built earlier this session (`integrator/BLOCK_annotations_X_orthogroups/workflow-COPYME-*`).

## 4. Git state

- Branch `main`, last pushed commit **`634a372`** (def==accession reformat).
- `subprojects/annogroups/` is **new + untracked** — NOT committed yet (commit after Phase 1
  review). `OUTPUT_pipeline/` + `__pycache__` are gitignored runtime; don't commit them.

## 5. Already DONE earlier this session (do NOT redo) — all pushed

- Built `integrator/BLOCK_annotations_X_orthogroups` (annogroups × orthogroups, non-bilaterian-
  metazoan focus); server publishing wired; integrator added to server allowlist.
- Fixed a §39 canonical-RUN violation: OCL `BLOCK_annotations_X_ocl` server was serving stale
  RUN_01 (no defs) — switched to canonical RUN_02, removed stale manifest, re-published.
- Reformatted `Annotation_Definitions` everywhere to **`definition ==accession`** (OCL formatter
  `utils_run_summary.format_annotation_definitions` + backfilled RUN_02's 945 files; integrator
  passes through). Server serves the new format. Commits `549faf2, 575a394, 10ebd2b, 583fdad, 634a372`.

## 6. Gotchas / conventions in play

- NextFlow env pin `>=23,<26` (system module is 26.x which breaks these workflows).
- `export TMPDIR=/tmp` before any slurm submit (Claude TMPDIR footgun).
- **Save Chat! is hand-captured** here (session rooted at `GIGANTIC/` = Pattern A; the official
  `ai/ai_scripts/003` only auto-discovers `…-COPYME` Pattern B). 14 sessions captured 2026-06-18
  incl. current `3aa4a745`.
- annogroup_* are **canonical terminology** — use exactly: feature / combination / architecture / absent.
