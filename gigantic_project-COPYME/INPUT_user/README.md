<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: User-facing description of INPUT_user — the single staging arena
         where the user makes outside data available to GIGANTIC.
History:
  2026-05-25  Rewritten for the symlink-into-research_notebook architecture
              (see gigantic_conventions.md §1 and the framework's chat-as-
              research-notebook principles).
============================================================================ -->

# `INPUT_user/` — Single Staging Arena

`INPUT_user/` is the **one and only** directory through which you make
outside data available to GIGANTIC subprojects. There is no other.

It is the interface between **your world** (raw data you've downloaded or
prepared) and **GIGANTIC's world** (workflows that read structured inputs).

---

## How it works

1. **You bring data into your sandbox first.** `research_notebook/research_user/`
   is your open workspace — no rules, no structure requirements. Download
   files there, name them however you like, organize however suits you. AIs
   can help you with this (downloading, renaming, formatting) freely.

2. **You expose what GIGANTIC needs via symlinks in `INPUT_user/`.**
   Each file you want GIGANTIC subprojects to read becomes a symlink from
   `INPUT_user/` into `research_notebook/research_user/`. Use **relative**
   symlinks (`ln -srf <target> <link>`) so they survive when the whole
   project is moved or archived.

3. **GIGANTIC subprojects read only from `INPUT_user/`.** Per the
   `research_notebook/` sandbox rule (gigantic_conventions §1), GIGANTIC
   never reaches into your sandbox directly.

**Net result**: clean separation. Your raw downloads, intermediate files,
and exploratory work all live in `research_notebook/research_user/` with
no structure constraints. Anything GIGANTIC needs becomes a deliberate,
visible symlink in `INPUT_user/`. The directory listing of `INPUT_user/`
is a complete catalog of what your project feeds into GIGANTIC.

---

## What ships with the template vs. what stays local

Everything in `INPUT_user/` **except documentation** (`README.md`,
`AI_GUIDE.md`, and similar) is gitignored. Your symlinks, manifest files,
species lists, and any other content you stage here remain on your local
disk only — they do not get pushed to GitHub. This protects your project
data from accidental publication and keeps the shipped template clean.

The shipped template contains only the doc scaffold. When you copy the
template into your own renamed project, `INPUT_user/` arrives essentially
empty (just the README files), and you populate it from your sandbox as
your project takes shape.

---

## Conventional structure (driven by current subprojects)

Subprojects drive what they expect to find in `INPUT_user/`. The structure
below reflects what current GIGANTIC subprojects expect. You can deviate
when your project needs differ — but most subprojects assume this layout
by default.

```
INPUT_user/
├── README.md                          # This file (template ships)
├── AI_GUIDE.md                        # AI-facing guide for INPUT_user (template ships)
├── species_set/
│   └── species_list.txt               # Symlink → research_notebook/research_user/...
├── genomic_resources/
│   ├── genomes/                       # Symlinks to .fasta / .fna genome assemblies
│   ├── proteomes/                     # Symlinks to .aa proteome amino acid files
│   ├── annotations/                   # Symlinks to .gff3 / .gtf gene annotations
│   └── maps/                          # Symlinks to .tsv identifier mapping files
└── phylonames/
    ├── README.md                      # Template ships
    └── user_phylonames.tsv            # Symlink → research_notebook/research_user/...
```

Files are flat within each subdirectory (no further nesting).

---

## Conventional file naming (when subprojects expect it)

Most subprojects that operate on genomic data assume this filename pattern:

```
Genus_species-genome_source_identifier-downloaded_date.filetype
```

| Component | Description | Example |
|-----------|-------------|---------|
| `Genus_species` | Species name | `Homo_sapiens` |
| `genome_source_identifier` | Genome project source | `genome_ncbi_GCF_000001405.40`, `genome_figshare_12345`, `genome_kim_2025` |
| `downloaded_date` | When downloaded | `downloaded_20240115` |
| `filetype` | Data type by extension | `.fasta` (genome), `.gff3` (annotation), `.aa` (proteome) |

Apply the naming to the file in `research_notebook/research_user/`; the
symlink in `INPUT_user/` keeps the same name (no rename at the symlink
boundary).

### Proteome FASTA header convention

Proteome `.aa` files must have standardized headers:

```
>Genus_species-source_gene_id-source_transcript_id-source_protein_id
```

Examples:
```
>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
>Mus_musculus-MGI:87853-NM_007393-NP_031419
>Drosophila_melanogaster-FBgn0000003-FBtr0071763-FBpp0071429
```

- Each field separated by `-`
- `Genus_species` must match the species list and file name
- Source IDs from the original database (Ensembl, NCBI, FlyBase, etc.)

---

## What each data type is for

| Data type | Extension | Used by |
|-----------|-----------|---------|
| Proteome | `.aa` | genomesDB, orthogroups, annotations_hmms, trees_gene_families, trees_gene_groups, secretome, dark_proteomes |
| Genome assembly | `.fasta` / `.fna` | gene_sizes, synteny, hotspots |
| Annotation | `.gff3` / `.gtf` | gene_sizes, genomesDB evaluation |
| Identifier mapping | `.tsv` | genomesDB ingestion (when source IDs differ from final IDs) |

At minimum, most analyses need proteome `.aa` files. Genome and annotation
files unlock additional subprojects.

---

## Workflow override pattern (advanced)

A project-wide `INPUT_user/species_set/species_list.txt` is the default
for every workflow. Individual workflows can override it with their own
`INPUT_user/species_list.txt` inside their `workflow-COPYME-*/INPUT_user/`
directory.

**Priority order** (checked by each `RUN-workflow.sh`):
1. Workflow-local `INPUT_user/species_list.txt` (override) — used if present
2. Project-level `INPUT_user/species_set/species_list.txt` (default) —
   copied into the workflow if no override

This lets you run one workflow with a different species set without
touching the project-wide list. The copied workflow-local file also
serves as the archived input for that specific run, for reproducibility.

---

## Tips

- **Use relative symlinks**, not absolute. `ln -srf` makes them relative
  automatically. Absolute symlinks break when the project moves machines
  or gets archived elsewhere.
- **Broken symlinks fail loudly**. If you reorganize
  `research_notebook/research_user/` and forget to update `INPUT_user/`,
  your workflows will error out with file-not-found. That's the right
  behavior — fix the symlink, re-run. No silent stale-data risk.
- **Audit your symlinks**: `find INPUT_user -xtype l` finds all broken
  ones; `find INPUT_user -type l -exec ls -la {} \;` shows where each
  symlink points.
- **Large files belong in `research_notebook/research_user/`**, not as
  literal copies in `INPUT_user/`. Symlinks cost nothing; copies waste
  disk and create staleness ambiguity.
