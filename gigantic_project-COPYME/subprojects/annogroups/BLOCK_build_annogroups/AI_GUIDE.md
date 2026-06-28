<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: AI guide for BLOCK_build_annogroups — the build pipeline, the
         per-source parser-plugin contract, and how to add a new source.
Scope:   BLOCK_build_annogroups (the build mechanics + parser contract).
============================================================================ -->

# AI_GUIDE — BLOCK_build_annogroups

**For AI assistants**: Read the subproject guide ([`../AI_GUIDE.md`](../AI_GUIDE.md))
first for the annogroup concept and the four canonical types. This guide covers
the build pipeline and — most importantly — the **parser-plugin contract** for
adding a new annotation source.

| User needs… | Go to… |
|-------------|--------|
| Annogroup concept + the four types | [`../AI_GUIDE.md`](../AI_GUIDE.md) |
| The build pipeline + adding a source (parser contract) | This file |
| Running the workflow (config, exec modes, troubleshooting) | [`workflow-COPYME-build_annogroups/ai/AI_GUIDE.md`](workflow-COPYME-build_annogroups/ai/AI_GUIDE.md) |

## The build pipeline

All scripts live in `workflow-COPYME-build_annogroups/ai/scripts/`.

| Script | Runs | Does |
|--------|------|------|
| `001_ai-python-resolve_sources_and_universe.py` | once | discovers parser plugins, intersects with the config `sources:` request → `1_ai-sources_manifest.tsv`; builds the **proteome universe** (every sequence ID across the species-set proteomes) → `1_ai-proteome_universe.tsv` |
| `002_ai-python-build_annogroups.py` | per source | imports `parsers/<source>`, calls `parse_source_features`, builds the four types, writes the map + membership (+ dropped-orphan audit) → `2-output/<source>/` |
| `003_ai-python-validate_results.py` | per source | fail-fast cross-checks (§36) → `3-output/<source>/` |
| `004_ai-python-species_tree_deconvolution.py` | per source | per-clade member-protein counts for every species-tree clade (union across structures + one file per structure) → `4-output/<source>/` |
| `005_ai-python-per_species_sequence_map.py` | per source | wide annogroup × species → member sequence IDs (absent excluded) → `5-output/<source>/` |
| `006_ai-python-composite_clades.py` | per source | classify each annogroup by the four composite-clade algorithms + curated summary + per-composite-clade detail tables → `6-output/<source>/` |
| `007_ai-python-write_summary.py` | once | cross-source summary: per source (per-type breakdown), per species, and per phylum (sources as columns) → `7-output/` |
| `008_ai-python-write_run_log.py` | once | §45 run log |

`main.nf` reads the sources manifest with `splitCsv(header:true)` and pipelines
002→003→004→005→006 **per source**; 007 (summary) and 008 (run log) run once after
all sources are processed. Adding sources never touches the NextFlow wiring.

### Summary tables (Script 007)

- `7_ai-annogroups_summary.tsv` — one row per source: validation status,
  universe / annotated / absent counts + percent, the per-type annogroup
  breakdown (feature / combination / architecture / absent), total, dropped count.
- `7_ai-annogroups_summary-per_species.tsv` — one row per species; **annotation
  sources are the columns**; each cell = the species' annotated sequence count
  for that source (universe count is the leading context column).
- `7_ai-annogroups_summary-per_phylum.tsv` — one row per phylum; same source-as-
  column layout, with species count + universe count for context.

## The four types — construction (Script 002, source-agnostic)

Given `{sequence_id: [Feature(accession, start, stop, is_positional)]}`:

- **feature**: for each distinct `accession` a sequence has, add it to
  `annogroup_<source>_<accession>`. Multi-membership.
- **combination**: key = `tuple(sorted(set(accessions)))` (alphabetical distinct
  set); one combination annogroup per distinct key. Partitions annotated
  sequences (each in exactly one).
- **architecture**: positional features only, sorted N→C by `(start, stop)`; the
  grouping key is the **coord-free** accession tuple (so homologs group); each
  sequence's coordinate-tagged string is stored on its membership row via
  `architecture_member_string`. One architecture per sequence that has ≥1
  positional feature.
- **absent**: `universe − annotated` → one `annogroup_<source>_absent`.

**Whole-protein vs sub-protein.** `combination` is the **whole-protein** grouping
(the set of features, position-independent); `architecture` is the **sub-protein**
grouping (their N→C ordered arrangement, which needs residue coordinates). A source
whose features are **non-positional** (`is_positional=False`) therefore produces
**no architecture** — only feature + combination + absent (3 types). GO and DeepLoc
are such whole-protein sources; pfam and panther are positional (4 types).

Counter IDs (combination/architecture) are assigned by sorting the canonical
keys then numbering (`annogroup_counter_id`), so they are deterministic.

## The parser-plugin contract (how to add a source)

**Adding a source = adding one file:** `ai/scripts/parsers/<source>.py`. Nothing
else changes (Script 002, validation, main.nf, RUN-workflow.sh are all generic).

Each parser module must expose:

```python
SOURCE = "<source>"                          # e.g. "gene3d"

def parse_source_features( workflow_root, config ) -> dict:
    # Return { sequence_identifier: [ Feature, Feature, ... ] } for every
    # sequence in the species set that has >=1 feature from this source.
    # Feature = utils_annogroups.Feature( accession, start, stop, is_positional )
    #   - positional feature (domain/segment/region): ints for start/stop,
    #     is_positional=True  -> participates in architecture
    #   - whole-protein / position-less (e.g. localization, has-X): start=stop=None,
    #     is_positional=False -> NO architecture (type count becomes 3)
```

Conventions a parser must follow:

- Read **only** from `output_to_input/` paths resolved via
  `U.resolve_input_path(workflow_root, config["inputs"][...])` (§2). Define a
  module-level `RELATIVE_SUBPATH` for the source's own subdirectory and append it.
- Use `U.build_header_index(header_line)` to map self-documenting headers →
  indices (header_id = text before `' ('`); never hardcode column positions.
- **Fail fast** (§36): missing dir, no files, or malformed coordinates → print a
  `CRITICAL ERROR:` and `sys.exit(1)`. Never silently skip rows.
- Return the **full GIGANTIC sequence identifier** as the key (it must match the
  proteome universe header IDs; mismatches are dropped + audited — see the
  WARNING note).

`parsers/pfam.py` is the reference implementation (positional domains, all four
types). **All 12 sources are implemented.** Input locations (all under the config
`annotations_hmms_dir` root):

- `pfam, panther, gene3d, cdd, smart, superfamily, funfam` → `BLOCK_interproscan_parsed/<db>/<db>-*.tsv` (15-col schema; positional clones)
- `go` → raw `BLOCK_interproscan/*_interproscan_results.tsv` (see below)
- `tmbed` → `BLOCK_tmbed/*_tmbed_predictions.tsv` (3 positional segment classes)
- `signalp` → `BLOCK_signalp/*_signalp_SLOW_predictions.tsv` (whole-protein SP type; SLOW model)
- `deeploc` → `BLOCK_deeploc/*_deeploc_predictions.csv` (whole-protein localization labels; CSV)
- `metapredict` → `BLOCK_metapredict/*_metapredict_predictions.tsv` (generic positional IDRs)

The per-protein tools (tmbed/signalp/deeploc/metapredict) share one caveat: a
protein not scored by the tool (e.g. dropped upstream by the long-header filter)
has no feature and so falls into `annogroup_<source>_absent` — i.e. `absent` means
"no feature in the available output", which can include a few not-evaluated
proteins (analogous to the dropped-orphan caveat).

**`parsers/go.py` (special).** GO is not a standalone parsed database. The go
parser reads the **raw** per-species results (`BLOCK_interproscan/*_interproscan_results.tsv`,
which have **no header** → fixed InterProScan column order, GO in column 14) and
unions distinct GO IDs per protein. GO terms are tagged with the contributing tool
(`(InterPro)` = curated InterPro2GO; `(PANTHER)` = PANTHER-direct, largely
inferred); which origins to include is the explicit config knob `go_term_origins`
(default = both). GO is **whole-protein / non-positional** → 3 types (no
architecture). GO term **names** come from `inputs.go_names_map` — a GO_ID→name
mapping annotations_hmms generates from the canonical `go-basic.obo`
(`annotations_hmms/reference_go/`, exposed at
`output_to_input/GO_reference/go_id_to_name.tsv`) — so definitions read e.g.
`DNA binding ==GO:0003677`.

**GO aspect split (the 3 major GO categories).** The go parser also declares
`CATEGORIES` (the three GO aspects: molecular_function, biological_process,
cellular_component) + `parse_source_categories` (GO_ID→aspect, from the same
mapping's `GO_Namespace`). When a source declares categories, the shared map
builder (Script 002) emits **two columns per category** —
`GO_<Aspect>_Identifiers` + `GO_<Aspect>_Definitions` — right after
`Annotation_Definitions`, splitting each annogroup's GO terms by aspect. These
extra columns are carried forward generically (`U.carry_forward_map_columns`) into
4-output (deconvolution forwards the whole map row), 5-output (per-species map),
and 6-output (composite-clade per-annogroup + detail tables). Sources without
`CATEGORIES` (pfam, panther) are unaffected — no extra columns.

## Source feature-type behaviour

`combination` = whole-protein (the feature *set*); `architecture` = sub-protein
(the N→C *ordered* arrangement, needs coordinates). Non-positional sources yield
no architecture (3 types).

All 12 sources below are **implemented** (one parser plugin each; `sources: "all"`
builds them all).

| Source kind | Sources | is_positional | Types |
|-------------|---------|---------------|-------|
| positional domains/families | pfam, panther, gene3d, cdd, smart, superfamily, funfam | True | feature + combination + architecture + absent |
| positional segments/regions | tmbed (TM_helix / beta_barrel / signal_peptide; architecture = membrane topology), metapredict (IDRs; one accession `IDR`, so architecture = IDR count) | True | all four |
| whole-protein label | go (GO terms), deeploc (subcellular localization), signalp (signal-peptide type, SLOW model) | False | feature + combination + absent (no architecture) |

## Validation (Script 003, fail-fast)

Checks: type validity; map `Sequence_Count` == membership rows; combination
partitions annotated sequences (each in exactly 1); architecture is one-per
sequence; `absent ∪ annotated == universe` and disjoint; every membership ID is
in the universe. Any failure → FAIL report + exit 1 (a silent annogroup artifact
in a published product is a research-integrity failure per `AI_BEHAVIOR.md`).

## Known caveat

Truncated/orphan annotation IDs (not in the universe) are dropped, audited to
`2_ai-<source>-dropped_orphan_sequences.tsv`, and warned. Root cause + the
user-accepted side effect (a few sequences misfiled as `absent`) are documented
in [`workflow-COPYME-build_annogroups/ai/ai_FYIs/WARNING-truncated_orphan_annotations.md`](workflow-COPYME-build_annogroups/ai/ai_FYIs/WARNING-truncated_orphan_annotations.md).
A large dropped count for any source means a systematic ID mismatch —
investigate, do not accept.
