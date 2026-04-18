# STEP_0 - Prepare Proteomes (Optional Preprocessing)

**AI**: Claude Code | Opus 4.6 (1M context) | 2026 April 18
**Human**: Eric Edsinger

---

## Purpose

STEP_0 is an **optional** preprocessing step for users who need to prepare
proteome files before entering the main genomesDB pipeline (STEP_1 through
STEP_4).

**Most users do NOT need STEP_0.** If your proteomes come from NCBI genome
assemblies (RefSeq or GenBank), STEP_2 Script 001 already handles T1 extraction
during standardization. Proceed directly to STEP_1.

**You DO need STEP_0 if** your proteomes come from transcriptome assemblies
processed through EvidentialGene (evigene). Evigene produces an "okayset"
containing mixed transcript classes that must be separated before entering
GIGANTIC.

---

## What Are T0 and T1 Proteomes?

GIGANTIC uses a transcript-level naming convention:

| Level | Contents | Description |
|-------|----------|-------------|
| **T1** | Main transcripts only | One representative protein per locus -- the "best" transcript selected by evigene. This is what most GIGANTIC analyses use. |
| **T0** | Main + alternative transcripts | All non-redundant transcripts (main + alt), excluding noclass. Useful when you want splice variants and alternative assemblies. |

### EvidentialGene Classification

EvidentialGene classifies assembled transcripts into three categories in the
okay.aa FASTA headers:

- **main** -- Best representative transcript per locus (highest quality, longest
  coding region, best evidence). One per gene locus.
- **alt** -- Alternative transcripts for the same locus (splice variants,
  alternative assemblies). May share a locus with a main transcript.
- **noclass** -- Transcripts that did not pass evigene quality filters. Excluded
  from both T0 and T1.

The classification appears in FASTA headers as an `evgclass=` tag:
```
>Mlig000002t1 type=protein; Name=PIWI-like protein; evgclass=main,...
>Mlig000002t2 type=protein; Name=PIWI-like protein; evgclass=alt,...
>Mlig999999t1 type=protein; Name=hypothetical; evgclass=noclass,...
```

---

## Available Workflows

### workflow-COPYME-evigene_to_T1

Extracts T0 and T1 proteomes from an EvidentialGene okayset okay.aa file.

**Input**: One evigene okayset okay.aa file per species
**Output**: `{species_name}-T1.aa` and `{species_name}-T0.aa` proteome files

---

## Data Flow

```
EvidentialGene okayset okay.aa
         |
    STEP_0 (this step)
         |
    T1.aa proteome
         |
    STEP_1-sources (add to source manifest)
         |
    STEP_2, STEP_3, STEP_4 ...
```

After running STEP_0, add the resulting T1.aa file path to your STEP_1 source
manifest as the proteome column for that species.

---

## When to Skip STEP_0

| Data source | Need STEP_0? | Why |
|-------------|--------------|-----|
| NCBI RefSeq/GenBank genome assembly | No | STEP_2 handles T1 extraction from NCBI protein files |
| EvidentialGene transcriptome assembly | **Yes** | Must separate main/alt/noclass before entering GIGANTIC |
| Other transcriptome assemblers (Trinity, etc.) | Maybe | If your assembler does not classify transcripts, you may not need this step. Consult the evigene documentation. |

---

## Directory Structure

```
STEP_0-prepare_proteomes/
├── README.md                              # This file
└── workflow-COPYME-evigene_to_T1/         # EvidentialGene preprocessing workflow
    ├── START_HERE-user_config.yaml         # Edit this first
    ├── RUN-workflow.sh                     # Run this
    ├── INPUT_user/                         # Place your evigene files here
    │   └── README.md                      # Input instructions
    └── ai/
        └── scripts/
            └── 001_ai-python-extract_evigene_T0_T1_proteomes.py
```
