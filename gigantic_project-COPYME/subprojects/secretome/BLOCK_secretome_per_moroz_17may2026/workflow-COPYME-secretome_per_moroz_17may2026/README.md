# workflow-COPYME-secretome_per_moroz_17may2026

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 21 (initial scoping)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_secretome_per_moroz_17may2026 (status: scaffold only)
- Parent (subproject): [`../../README.md`](../../README.md) — secretome overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from (per Moroz spec — when scripted):
  - `../../../annotations_hmms/output_to_input/BLOCK_signalp/`
  - `../../../annotations_hmms/output_to_input/BLOCK_deeploc/`
  - `../../../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/`
- Outputs to: `../../output_to_input/BLOCK_secretome_per_moroz_17may2026/` (when scripted)

---

## Status: SCAFFOLD ONLY

This workflow currently has:
- `main.nf` placeholder with the pipeline shape but no scripts
- `START_HERE-user_config.yaml` placeholder
- `conda_environment.yml` (the env builds successfully)
- ZERO scripts in `ai/scripts/`

It's awaiting a fresh SignalP6 run on species70 from annotations_hmms
(previous attempt produced only 2/70 species). See the subproject
AI_GUIDE for the upstream-data table + decision log.

## Intended Usage (when scripted)

```bash
cp -r workflow-COPYME-secretome_per_moroz_17may2026 workflow-RUN_1-secretome_per_moroz_17may2026
cd workflow-RUN_1-secretome_per_moroz_17may2026
vi START_HERE-user_config.yaml   # set execution_mode, paths, SignalP cutoffs
bash RUN-workflow.sh
```

## See Also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — workflow execution (scaffold doc)
- [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK concepts + scripting plan
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — subproject Moroz spec detail
