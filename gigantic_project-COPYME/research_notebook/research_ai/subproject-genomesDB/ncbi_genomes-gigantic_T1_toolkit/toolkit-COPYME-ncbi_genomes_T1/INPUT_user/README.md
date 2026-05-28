<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 28
Human:   Eric Edsinger
Purpose: Document the manifest format consumed by the NCBI Genomes T1 Toolkit.
Scope:   INPUT_user/ of toolkit-COPYME-ncbi_genomes_T1 (and copies).
============================================================================ -->

# `INPUT_user/` — Toolkit-Local Manifest

This directory holds **one file**: `ncbi_genomes_manifest.tsv`, a 2-column
TSV mapping each species to its NCBI assembly accession.

This is the **toolkit's** local INPUT_user (per the §29 workflow-local pattern),
not the **project-level** [`INPUT_user/`](../../../../../INPUT_user/) staging
arena (per §17, §18) that GIGANTIC subprojects read from. The toolkit's
process 4 (`bridge_to_input_user`) is what creates the symlinks that bridge
the toolkit output into the project-level arena.

## Manifest format

`ncbi_genomes_manifest.tsv`:

- **2 tab-separated columns**: `genus_species<TAB>accession`
- **Lines starting with `#`** are comments (any amount of leading whitespace)
- **The header row `genus_species`** is detected and skipped
- **Blank lines** are skipped
- **Species name**: `Genus_species` format (underscore, not space).
  Subspecies are encoded with additional underscores
  (e.g. `Hippopotamus_amphibius_kiboko`).
- **Accession**: full NCBI assembly accession including version, e.g.
  `GCF_000001405.40`. Both RefSeq (`GCF_*`) and GenBank (`GCA_*`) accessions
  are syntactically valid. Support tiers:
    - **RefSeq `GCF_*` — supported.** The toolkit is built and tested
      against RefSeq's structural guarantees. Use these whenever
      available.
    - **GenBank `GCA_*` — best-effort, not guaranteed.** Many GCAs ship
      with `protein.faa` + GFF3 and run through the pipeline
      successfully. But GenBank GFF3 lacks the `Dbxref=GeneID:`
      attribute that the alt-loci filter (script 003) keys on. The
      filter becomes a **silent no-op** on GCAs: for assemblies with
      no alt-haplotype duplicates this matches `gene_biotype=protein_coding`
      1:1 and is correct; for assemblies that DO have alt-haplotype
      duplicates, the toolkit silently includes them as separate
      proteins. **If you use GCAs**: validate each species's GFF3
      against a comparable GCF for the same lineage, inspect the T1
      output, and compare protein counts to NCBI's
      `gene_biotype=protein_coding` count before trusting downstream
      use.
    - Assemblies that lack `protein.faa` and/or annotation altogether
      will fail loudly in the unzip step (this is the §36 fail-fast
      behavior, working as intended).

### Example

```
# My deuterostome demo set (2026-05-28)
genus_species	accession
Homo_sapiens	GCF_000001405.40
Strongylocentrotus_purpuratus	GCF_000002235.5
Branchiostoma_floridae	GCF_000003815.2
Caenorhabditis_elegans	GCF_000002985.6
```

## What the manifest controls

1. **Which species get downloaded** (script 001)
2. **Which species's NCBI bundles get unzipped + intermediate-renamed** (script 002)
3. **Which species enter T1 extraction + alt-loci filtering** (script 003)
4. **What goes into the output filenames** — `Genus_species` and `<accession>`
   are baked into the GIGANTIC-convention output filename:
   `Genus_species-genome_ncbi_<accession>-downloaded_<YYYYMMDD>.{aa,fasta,gff3}`
5. **What gets bridged into the project-level `INPUT_user/genomic_resources/`**
   (script 004) — every species in the manifest that successfully produced
   outputs gets relative symlinks created.

## What to put here

Just the manifest. No other files in `INPUT_user/`. The toolkit doesn't read
anything else from this directory.

## What to do for non-RefSeq sources

- **GCA_* (GenBank)** assemblies: try this toolkit first (many GCAs
  work end-to-end), but with the caveats from the Accession section
  above. If the alt-loci no-op is acceptable for your species (e.g.,
  the GCA has no alt-haplotype scaffolds and `gene_biotype=protein_coding`
  count matches the T1 protein count), the toolkit's output is fine.
  Otherwise hand-prep the species separately.
- **figshare / Zenodo / Dryad / lab-website** datasets: hand-prep,
  then symlink directly from `research_notebook/research_user/<your_layout>/`
  into the project-level `INPUT_user/genomic_resources/` per §17, §18.

After hand-prep, those species's files should match the same GIGANTIC
convention used by this toolkit's output:
- Filename: `Genus_species-genome_<source>_<accession>-downloaded_<YYYYMMDD>.{aa,fasta,gff3}`
- Proteome FASTA headers: `>Genus_species-gene_id-transcript_id-protein_id`

That way `genomesDB STEP_1` and downstream subprojects see a uniform
species set regardless of source.
