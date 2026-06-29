<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: Document what one_direction_homologs shares with downstream subprojects.
Scope:   one_direction_homologs/output_to_input/.
============================================================================ -->

# one_direction_homologs / output_to_input

Downstream subprojects read one_direction_homologs from here (the canonical
inter-subproject sharing location, §2). Populated by `BLOCK_diamond_ncbi_nr`'s
`RUN-workflow.sh` as **symlinks** into the canonical workflow run's
`OUTPUT_pipeline/`.

## Layout

```
output_to_input/
└── BLOCK_diamond_ncbi_nr/
    └── ncbi_nr_top_hits/
        ├── all_species_statistics.tsv      # master summary, one row per species
        ├── <phyloname>_statistics.tsv      # per-species hit statistics (one per species)
        └── <phyloname>_top_hits.tsv        # per-protein top 10 NCBI nr hits (one per species)
```

## Files

- **`all_species_statistics.tsv`** — one row per species: total queries processed
  and counts of self-hits, non-self-hits, queries with no non-self hit, and
  queries with no self hit.
- **`<phyloname>_statistics.tsv`** — the per-species form of the above.
- **`<phyloname>_top_hits.tsv`** — one row per query protein: its top 10 NCBI nr
  DIAMOND hits (IDs, NCBI descriptions, e-values), the top non-self hit, and the
  top self hit. A self-hit means the protein is present in NCBI nr (100 percent
  identity, full-length alignment); a non-self hit is a true homolog with a
  different sequence.

## Consumers

`dark_proteomes` reads the NCBI nr reference-hit signal (axis_a — whether each
protein has any reference DIAMOND hit). See that subproject's `AI_GUIDE.md`.

Updated whenever `BLOCK_diamond_ncbi_nr` is re-run.
