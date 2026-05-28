<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 28
Human:   Eric Edsinger
Purpose: Parent-dir AI guide for the NCBI Genomes T1 Toolkit. Operational
         orientation for the next AI session entering this directory.
Scope:   ncbi_genomes-gigantic_T1_toolkit/ and its toolkit-COPYME / RUN_* /
         output_to_input / x_* descendants.
History:
  2026-05-28  Initial version (post ground-up rebuild).
============================================================================ -->

# `ncbi_genomes-gigantic_T1_toolkit/` — AI Guide

You are an AI assistant in the parent directory of the NCBI Genomes T1 Toolkit.
This is the sandbox-side toolkit responsible for pulling NCBI RefSeq genome
bundles into a GIGANTIC-conformant form and bridging them into
`INPUT_user/genomic_resources/`.

## Where this fits

- **Parent project**: [`../../../../`](../../../../) (renamed `gigantic_project-*/`)
- **Location context**: this directory lives in
  `research_notebook/research_ai/subproject-genomesDB/` per
  `ai/ai_FYIs/gigantic_conventions.md` §59 (canonical toolkit home).
  The toolkit follows GIGANTIC framework conventions internally — same
  rigor as a subproject workflow.
- **Downstream consumer**: `subprojects/genomesDB/STEP_1-sources/`

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC conventions | `../../../../ai/ai_FYIs/gigantic_conventions.md` |
| Toolkit overview (user-facing) | [`README.md`](README.md) |
| Run the toolkit | [`toolkit-COPYME-ncbi_genomes_T1/README.md`](toolkit-COPYME-ncbi_genomes_T1/README.md) |
| Toolkit AI guide (operational) | [`toolkit-COPYME-ncbi_genomes_T1/ai/AI_GUIDE.md`](toolkit-COPYME-ncbi_genomes_T1/ai/AI_GUIDE.md) |
| Manifest format | [`toolkit-COPYME-ncbi_genomes_T1/INPUT_user/README.md`](toolkit-COPYME-ncbi_genomes_T1/INPUT_user/README.md) |
| Cross-RUN stable output | [`output_to_input/`](output_to_input/) |

## Downstream consumers

The `output_to_input/<subdir>/` exposed here is read by **process 4** of the
toolkit itself (which symlinks it onward into the project-level INPUT_user).
Downstream of THAT bridge:

- **`subprojects/genomesDB/STEP_1-sources/`** consumes proteomes, genomes,
  and annotations from `<project_root>/INPUT_user/genomic_resources/`.
  STEP_1's source_manifest.tsv has paths like
  `../../../../INPUT_user/genomic_resources/proteomes/<...>.aa`. As long as
  the symlinks created by this toolkit's process 4 point at real files,
  genomesDB STEP_1 just hard-copies them in.

## When to start a new RUN

Per §35: copy `toolkit-COPYME-ncbi_genomes_T1/` to `toolkit-RUN_<N>-ncbi_genomes_T1/`,
edit the RUN's `INPUT_user/ncbi_genomes_manifest.tsv` and `START_HERE-user_config.yaml`,
then `bash RUN-workflow.sh` from inside the RUN dir. Don't run from the COPYME
template — the unified runner refuses (COPYME-guard).

When a RUN successfully completes, do **not** edit it after the fact (§47
frozen-artifact rule). Make any forward improvements in `toolkit-COPYME-*`
and start a new `toolkit-RUN_<N+1>-*` instance.

## When the bridge symlinks need refreshing

The bridge in process 4 always points at the CURRENT RUN's `OUTPUT_pipeline/3-output/`.
If a previous RUN finished, you run a new RUN with different species, and
the new RUN's process 4 completes — the symlinks in `output_to_input/` AND in
`INPUT_user/genomic_resources/` get atomically updated to point at the new
RUN's outputs. Old RUN's outputs remain in `toolkit-RUN_<old>/OUTPUT_pipeline/`
but the bridge no longer references them.

If you need to **manually re-point** to a specific historical RUN's outputs
(rare; e.g. for a hypothesis-rerun comparison), run process 4's script
(`004_ai-python-bridge_to_input_user.py`) directly with that RUN's
`OUTPUT_pipeline/3-output/` as `--run-3-output-dir`.

## Toolkit conventions

This toolkit lives at `research_notebook/research_ai/subproject-genomesDB/`
per §59 (canonical toolkit home). Internally it follows the same GIGANTIC
conventions as a subproject workflow: §3 (AI_GUIDE.md naming), §12
(attribution), §17/§18 (INPUT_user staging), §21 (script naming), §23
(${projectDir}), §28 (per-toolkit conda env), §29 (unified
RUN-workflow.sh + START_HERE-user_config.yaml), §34 (TSV headers), §35
(toolkit-COPYME / toolkit-RUN_N template-vs-instance), §36 (fail-fast),
§45 (write_run_log), §47 (frozen RUN), §56 (README.md mandatory). See
the §59 conventions table for the full list.

The only places toolkits diverge from subproject workflows:
- **Location**: `research_ai/subproject-<X>/` not `subprojects/<X>/`
- **Bridge step**: explicit process N-1 that symlinks toolkit outputs
  into the project-level `INPUT_user/` staging arena (subprojects read
  from `output_to_input/` instead per §2)

Per §60: this toolkit does not become a subproject. The framework
intentionally does not own its inputs because the choice of genome
assemblies, alt-loci policy, GCA-vs-GCF handling, etc. varies too much
across projects to be standardized.
