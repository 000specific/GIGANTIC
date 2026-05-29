# INPUT_user — Gene Coordinates Extractor Toolkit

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

This toolkit does not require any user-supplied input files in this directory. The two paths the workflow needs (annotations dir + hotspots target dir) live in `START_HERE-user_config.yaml`; both default to the species42 demo locations.

INPUT_user exists for parity with the canonical toolkit layout (`§17 / §18`) so the directory shape mirrors other GIGANTIC tools and is visible to AI assistants looking for user inputs.

If you ever need to override **which** species get processed (rather than auto-processing every GFF in `annotations_dir`), use the `inputs.species_whitelist` field in `START_HERE-user_config.yaml` — it accepts a comma-separated list of `Genus_species` values. No file required.
