# INPUT_user - Start Here

**Before running ANY GIGANTIC subproject, place your species list and genomic resource files in this directory.**

This is the first thing you do when starting a GIGANTIC project. Everything else depends on having your species and their data here.

---

## Directory Structure

```
INPUT_user/
├── README.md                          # This file
├── species_set/
│   └── species_list.txt               # Your species list (one per line)
└── genomic_resources/
    ├── genomes/                        # Genome assembly FASTA files
    ├── proteomes/                      # Proteome amino acid files
    ├── annotations/                    # GFF3/GTF gene annotation files
    └── maps/                           # Identifier mapping files
```

Files are flat within each subdirectory (no further nesting).

---

## What Goes in This Directory

### 1. Species List (`species_set/species_list.txt`)

A simple text file listing the organisms in your study:

```
# One species per line, Genus_species format
# Lines starting with # are comments (ignored)
# Use official NCBI scientific names for best results
Homo_sapiens
Mus_musculus
Drosophila_melanogaster
Octopus_bimaculoides
Aplysia_californica
```

**Rules:**
- One species per line
- `Genus_species` format with underscore (not space)
- Use official NCBI scientific names
- Lines starting with `#` are comments

### 2. Genomic Resource Files (`genomic_resources/`)

Place your genome, proteome, and annotation files in the appropriate subdirectory. All files must follow the GIGANTIC naming convention.

#### File Naming Convention (Required)

```
Genus_species-genome_source_identifier-downloaded_date.filetype
```

**Components:**
| Component | Description | Example |
|-----------|-------------|---------|
| `Genus_species` | Species name | `Homo_sapiens` |
| `genome_source_identifier` | Genome project source | `genome_ncbi_GCF_000001405.40`, `genome_figshare_12345`, `genome_kim_2025` |
| `downloaded_date` | When downloaded | `downloaded_20240115` |
| `filetype` | Data type by extension | `.fasta` (genome), `.gff3` (annotation), `.aa` (proteome) |

#### Where Each File Type Goes

| Subdirectory | Extension | Content | Example |
|-------------|-----------|---------|---------|
| `genomic_resources/genomes/` | `.fasta` | Genome assemblies | `Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta` |
| `genomic_resources/proteomes/` | `.aa` | Proteome amino acid sequences | `Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa` |
| `genomic_resources/annotations/` | `.gff3` / `.gtf` | Gene annotations | `Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3` |
| `genomic_resources/maps/` | `.tsv` | Identifier mapping files | `ncbi_genomes-map-genome_identifiers.tsv` |

#### Proteome FASTA Header Convention (Required for .aa files)

Proteome files must have standardized FASTA headers:

```
>Genus_species-source_gene_id-source_transcript_id-source_protein_id
```

**Examples:**
```
>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
>Mus_musculus-MGI:87853-NM_007393-NP_031419
>Drosophila_melanogaster-FBgn0000003-FBtr0071763-FBpp0071429
```

**Rules:**
- Each field separated by `-` (dash)
- `Genus_species` must match the species list and file name
- Source IDs should come from the original database (Ensembl, NCBI, FlyBase, etc.)

#### What Data Types Are Required?

| Data Type | Extension | Required? | Used By |
|-----------|-----------|-----------|---------|
| Proteome | `.aa` | **Yes** - needed for most analyses | genomesDB, orthogroups, annotations, trees |
| Genome | `.fasta` | Recommended | gene_sizes, synteny |
| Annotation (GFF) | `.gff3` | Recommended | gene_sizes, genomesDB evaluation |

At minimum, you need proteome files for every species. Genome and GFF files are recommended but some subprojects can run without them.

---

## What Happens Next

1. **Run phylonames first** - Generates standardized taxonomic names for your species
2. **Run genomesDB** - Ingests, standardizes, and evaluates your genomic resources
3. **Run downstream subprojects** - Orthogroups, trees, annotations, etc.

The `genomesDB` subproject will read files from this directory. Its workflow uses a `source_manifest.tsv` (in the genomesDB workflow's `INPUT_user/`) that points to the files you placed here.

---

## How It Works

### Genomic Resources
1. **You place your files here** (the canonical source)
2. **Subproject workflows reference** these files via manifests (e.g., `source_manifest.tsv`)
3. **genomesDB ingests** files into its standardized structure

### Species List (Override Design)
The species list uses a **workflow override** pattern:

1. **Project-level default** (`INPUT_user/species_set/species_list.txt`) - The canonical species list for the entire project. This is used automatically by all workflows unless overridden.
2. **Workflow-level override** (workflow `INPUT_user/species_list.txt`) - If a workflow has its own `species_list.txt`, it takes priority over the project default. This lets you run a workflow with a different species set without changing the project-wide list.

**Priority order** (checked by each `RUN-workflow.sh`):
1. Workflow `INPUT_user/species_list.txt` (user override) - used if present
2. Project `INPUT_user/species_set/species_list.txt` (default) - copied to workflow if no override exists

This gives you:
- Single project-wide species list as the default
- Per-workflow override capability when needed
- Archived copy in each workflow run for reproducibility

---

## Tips

- **Organizing raw downloads**: Use `research_notebook/research_user/` as your personal workspace to organize raw downloads and do formatting work before placing final files here
- **File sizes**: Genomic files can be large (gigabytes). This is expected - GIGANTIC needs the actual data, not just references to it
- **Adding species later**: You can add more species and re-run genomesDB. The final species set is determined by you in genomesDB STEP_4
- **Naming help**: If unsure about source identifiers, use the download URL or database accession
