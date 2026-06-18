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
| `002_ai-python-build_annogroups.py` | per source | imports `parsers/<source>`, calls `parse_source_features`, builds the four types, writes the map + membership (+ dropped-orphan audit) |
| `003_ai-python-validate_results.py` | per source | fail-fast cross-checks (§36) |
| `004_ai-python-write_summary.py` | once | cross-source summary: per source (per-type breakdown), per species, and per phylum (sources as columns) → `4-output/` |
| `005_ai-python-write_run_log.py` | once | §45 run log |

`main.nf` reads the sources manifest with `splitCsv(header:true)` and fans
002+003 out **per source**; 004 (summary) and 005 (run log) run once after all
sources validate. Adding sources never touches the NextFlow wiring.

### Summary tables (Script 004)

- `4_ai-annogroups_summary.tsv` — one row per source: validation status,
  universe / annotated / absent counts + percent, the per-type annogroup
  breakdown (feature / combination / architecture / absent), total, dropped count.
- `4_ai-annogroups_summary-per_species.tsv` — one row per species; **annotation
  sources are the columns**; each cell = the species' annotated sequence count
  for that source (universe count is the leading context column).
- `4_ai-annogroups_summary-per_phylum.tsv` — one row per phylum; same source-as-
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
types). Per-source input locations for future parsers:
`pfam/gene3d/cdd/smart/superfamily/funfam` → `BLOCK_interproscan_parsed/<db>/`;
`tmbed` → `BLOCK_tmbed/`; `signalp` → `BLOCK_signalp/`; `deeploc` →
`BLOCK_deeploc/`; `metapredict` → `BLOCK_metapredict/`.

## Source feature-type behaviour (planned)

| Source kind | Example | is_positional | Types |
|-------------|---------|---------------|-------|
| positional domains | pfam, gene3d, cdd, smart, superfamily, funfam | True | feature + combination + architecture + absent |
| positional segments/regions | tmbed (TM segments), metapredict (IDRs), signalp (cleavage region) | True | all four (architecture = segment order) |
| whole-protein label | deeploc (localization) | False | feature + combination + absent (no architecture) |

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
