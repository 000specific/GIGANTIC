# OCL Tables for Leonid — Data Dive 1

**Generated:** 2026-04-14T15:12:01
**Source:** structure_001 complete OCL summary (user's input species tree)
**Species set:** species70
**Orthogroup source:** OrthoHMM

## Files

### 4 innovations tables (origin at each clade)

| File | Description |
|------|-------------|
| `innovations-origin_Metazoa.tsv` | Orthogroups with MRCA origin inferred at Metazoa |
| `innovations-origin_Ctenophora.tsv` | Orthogroups with origin at Ctenophora (Cteno-specific innovations) |
| `innovations-origin_Placozoa.tsv` | Orthogroups with origin at Placozoa |
| `innovations-origin_Cnidaria.tsv` | Orthogroups with origin at Cnidaria |

### 3 pairwise-exclusive tables (Metazoan-origin orthogroups shared in exactly two clades)

| File | Description |
|------|-------------|
| `metazoan_innovations-shared_exclusively-Ctenophora_AND_Placozoa.tsv` | Metazoa-origin; present in ≥1 Cteno + ≥1 Plac species; absent in Cnidaria + Bilateria + Porifera |
| `metazoan_innovations-shared_exclusively-Placozoa_AND_Bilateria.tsv` | Metazoa-origin; present in ≥1 Plac + ≥1 Bilateria species; absent in Cteno + Cnidaria + Porifera |
| `metazoan_innovations-shared_exclusively-Ctenophora_AND_Bilateria.tsv` | Metazoa-origin; present in ≥1 Cteno + ≥1 Bilateria species; absent in Plac + Cnidaria + Porifera |

## Column schema

All tables share the same columns as the source OCL summary. Key columns:
- `Orthogroup_ID` — orthogroup identifier (OG000000 style)
- `Origin_Clade` — MRCA clade where orthogroup first appears
- `Species_Count` — unique species containing this orthogroup
- `Species_List` — comma-delimited species names (genus_species)
- `Conservation_Rate_Percent` / `Loss_At_Origin_Rate_Percent` / etc. — see source summary header

## Caveats

1. "Exclusive" means no species from excluded clades has the orthogroup in this dataset
   (species70). A species-poor clade is more likely to show false exclusivity.
2. Single-species orthogroups (present in only one species) are included in innovations
   tables where the origin clade happens to match that single species' ancestry.
3. This is structure_001 only — the user's input species tree. Alternative topologies
   (104 others) are not evaluated here; cross-topology comparison is future work
   (planned `occams_tree` subproject).

## Regeneration

```bash
python3 generate_leonid_tables.py
```
