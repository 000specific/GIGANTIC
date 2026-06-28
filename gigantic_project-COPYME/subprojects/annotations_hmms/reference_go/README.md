<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: Provenance + regeneration for the GO_ID -> name annotation reference.
Scope:   annotations_hmms GO term-name reference data.
============================================================================ -->

# reference_go — GO term ID → name mapping

GIGANTIC annotation outputs (notably the raw InterProScan results) carry GO **IDs**
but not GO term **names**. This reference turns the canonical Gene Ontology into a
flat `GO_ID → name/namespace` lookup so any consumer can attach readable GO names.
The first consumer is the annogroups `go` parser
(`annogroups/.../parsers/go.py`, via `inputs.go_names_map`).

## Files

| File | What |
|------|------|
| `go-basic.obo` | the source ontology (downloaded; provenance below) |
| `generate_go_id_to_name.py` | parses the OBO → `go_id_to_name.tsv` (AI-attributed) |
| `go_id_to_name.tsv` | the mapping (primary + alternate IDs, with namespace + obsolete flags) |

The mapping is exposed downstream (§2) at
`output_to_input/GO_reference/go_id_to_name.tsv` (symlink to this file).

## Provenance

- Source: Gene Ontology Consortium, `go-basic.obo`
  (`https://purl.obolibrary.org/obo/go/go-basic.obo`)
- Ontology release (`data-version`): **releases/2026-06-15**
- Downloaded: **2026-06-28**
- Mapping rows: **51,975** (48,329 primary GO terms + 3,646 alternate/secondary IDs)

## Regenerate

```bash
cd annotations_hmms/reference_go
curl -sL -o go-basic.obo https://purl.obolibrary.org/obo/go/go-basic.obo
python3 generate_go_id_to_name.py
# (go_id_to_name.tsv is already exposed via the output_to_input symlink)
```
