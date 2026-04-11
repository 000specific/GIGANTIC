# Design Plan: `ocl_using_simple_taxonomy` Subproject

**AI**: Claude Code | Opus 4.6 | 2026 April 10
**Human**: Eric Edsinger
**Status**: DESIGN ONLY — no scripts written yet, awaiting discussion

---

## 1. Purpose and Motivation

### What this subproject does

Computes **Origin / Conservation / Loss (OCL)** metrics for orthogroups using the
**NCBI taxonomic hierarchy** (Kingdom → Phylum → Class → Order → Family → Genus → species)
encoded in GIGANTIC phylonames as a substitute for a phylogenetic species tree.

### Why it exists

The "real" OCL pipeline (`orthogroups_X_ocl/`) requires phylogenetic blocks, paths, and
parent-child tables produced by `trees_species/BLOCK_permutations_and_features/`. As of
2026 April 10, no `trees_species` output exists for any species set in GIGANTIC_1, which
blocks the real OCL pipeline. Producing first-pass OCL-shaped tables for collaborators
(e.g., Leonid Moroz) is the immediate need.

The phyloname taxonomic hierarchy is **already present in every species' phyloname
string** and requires no upstream pipeline run. Treating this hierarchy as a tree gives
a defensible first-cut surrogate that:

- Uses real species data (the same species70 / species71 set the real OCL will use)
- Produces tables shaped exactly like the real OCL output
- Lets downstream consumers (visualization, paper figures, web tables) develop against
  realistic data while we wait for trees_species
- Is scientifically meaningful in its own right — taxonomy-based conservation/loss is
  a standard descriptive analysis in comparative genomics

### Relationship to `orthogroups_X_ocl`

This is a **sibling**, not a replacement. Both subprojects answer the same question
("when did this orthogroup originate, where is it conserved, where was it lost?") but
use different tree topologies:

| Subproject | Tree source | Algorithm | Status |
|---|---|---|---|
| `orthogroups_X_ocl` | Phylogenetic trees from `trees_species` | TEMPLATE_03 dual-metric on phylogenetic blocks | Blocked on trees_species data |
| `ocl_using_simple_taxonomy` | NCBI taxonomy from phylonames | TEMPLATE_03 dual-metric on taxonomic blocks | Can run today |

Output files use the **same column schema** wherever possible so downstream consumers
can swap inputs with minimal code change.

---

## 2. Scientific Approach

### 2.1 Treating taxonomy as a tree

A GIGANTIC phyloname is already a path from kingdom to species:

```
Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
└─ K ──┴─ P ────┴─ C ──────┴─ O ─────┴─ F ─────┴─ G ───┴─ s
```

Across all species in a set, these paths form a **rooted tree** (the NCBI taxonomic
hierarchy restricted to the species set). Internal nodes are taxonomic ranks
(`Metazoa`, `Chordata`, `Mammalia`, …). Leaves are `Genus_species`.

Defining:

- **Taxonomic clade** = an internal node in this tree (e.g., `Mammalia`)
- **Taxonomic block** = a parent→child edge (e.g., `Chordata::Mammalia`)
- **Taxonomic path** = root-to-leaf walk through the tree

…we have a tree topology with the same vocabulary as `trees_species`. The TEMPLATE_03
dual-metric algorithm transfers directly: presence/absence at parent vs child decides
Conservation, Loss-at-Origin, or Continued-Absence per (orthogroup, block) pair.

### 2.2 What "presence at an internal node" means

For a leaf (species), presence is observed: the orthogroup either contains a protein
from that species or it does not.

For an **internal node** (clade), we use **Dollo parsimony** as the default rule:

> A clade is considered to "have" the orthogroup if **any** descendant species has it.

This is the simplest, most defensible reconstruction and matches how the real OCL
pipeline treats internal nodes when no ancestral state reconstruction is available.
We will document this clearly and structure the code so a more sophisticated
reconstruction (Fitch, ML) could be substituted later.

### 2.3 Origin assignment

For each orthogroup, the **origin clade** is the **deepest taxonomic node such that
all descendant leaves containing the orthogroup are within its subtree**. Equivalently:
the MRCA of the species that carry the orthogroup.

Edge cases:
- Orthogroup in 1 species → origin = that species (terminal node)
- Orthogroup in 0 species → excluded (shouldn't happen for OrthoHMM output)
- Orthogroup spans entire species set → origin = root of taxonomy tree

### 2.4 TEMPLATE_03 dual-metric tracking, applied to taxonomic blocks

For each taxonomic block `Parent::Child` and each orthogroup `OG`:

| Parent has OG? | Child has OG? | Event class | Counts toward |
|---|---|---|---|
| Yes | Yes | **Conservation** | Conservation events |
| Yes | No  | **Loss at Origin** | Loss events (first loss in this branch) |
| No  | No  | **Continued Absence** | Loss events (already lost upstream) |
| No  | Yes | **Re-acquisition** | Flagged as anomaly (Dollo violation) |

"Re-acquisition" cannot occur under Dollo parsimony because we define internal-node
presence as "any descendant has it." If this event ever fires under the implementation,
it indicates a bug — the validation script (Script 005) will fail-fast with an error.

### 2.5 Rate calculations

Per orthogroup, restricted to blocks **at or below the origin clade** (blocks above the
origin are excluded — the orthogroup hadn't appeared yet):

```
Conservation_Rate = Conservation_Events / (Conservation_Events + Loss_at_Origin_Events)
Loss_Rate         = Loss_at_Origin_Events / (Conservation_Events + Loss_at_Origin_Events)
```

Continued-absence events are tracked separately and reported but **not included in
the rate denominator** — this is the TEMPLATE_03 distinction that separates "actually
lost here" from "already gone."

Edge cases:
- Zero-transition orthogroups (e.g., single-species OG, no descendant blocks) →
  rates set explicitly to `0.0`, flagged in a `zero_transition` boolean column
- Float comparison tolerance: `abs(Conservation_Rate + Loss_Rate - 1.0) < 1e-9` for
  validation (not exact equality)

---

## 3. Directory Structure (GIGANTIC_1 conventions)

```
ocl_using_simple_taxonomy/
├── README.md                                       # Subproject overview
├── AI_GUIDE-ocl_using_simple_taxonomy.md           # Level 2 AI guide
├── DESIGN-ocl_using_simple_taxonomy.md             # THIS FILE (kept after impl as design record)
├── RUN-clean_and_record_subproject.sh
├── RUN-update_upload_to_server.sh
│
├── output_to_input/
│   └── BLOCK_taxonomy_ocl_analysis/                # Populated by RUN-workflow.sh symlinks
│       ├── Species71_X_OrthoHMM_X_Taxonomy/        # run_label from a workflow run
│       │   ├── 4_ai-orthogroups-complete_ocl_summary.tsv
│       │   ├── 3_ai-blocks-conservation_loss_per_block.tsv
│       │   ├── 2_ai-orthogroups-origin_per_orthogroup.tsv
│       │   └── ...
│       └── Species71_X_OrthoFinder_X_Taxonomy/
│           └── ...
│
├── upload_to_server/
│   └── BLOCK_taxonomy_ocl_analysis/
│       └── (curated subset of output_to_input + READMEs for collaborators)
│
├── research_notebook/
│   └── ai_research/                                # Populated by clean_and_record script
│
└── BLOCK_taxonomy_ocl_analysis/
    ├── AI_GUIDE-taxonomy_ocl_analysis.md           # Level 3 BLOCK guide
    └── workflow-COPYME-taxonomy_ocl_analysis/
        ├── README.md
        ├── START_HERE-user_config.yaml             # All user-editable settings
        ├── RUN-workflow.sh                         # Local execution
        ├── RUN-workflow.sbatch                     # SLURM wrapper
        ├── INPUT_user/
        │   └── README.md                           # No manifest needed (analyzes all OGs)
        ├── OUTPUT_pipeline/                        # Numbered script outputs (created on run)
        │   ├── 1-output/
        │   ├── 2-output/
        │   ├── 3-output/
        │   ├── 4-output/
        │   ├── 5-output/
        │   ├── 6-output/
        │   └── logs/
        └── ai/
            ├── AI_GUIDE-taxonomy_ocl_workflow.md   # Level 3 workflow guide
            ├── main.nf                             # NextFlow pipeline
            ├── nextflow.config
            ├── logs/
            ├── validation/
            └── scripts/
                ├── 001_ai-python-build_taxonomy_tree.py
                ├── 002_ai-python-determine_origins.py
                ├── 003_ai-python-quantify_conservation_loss.py
                ├── 004_ai-python-comprehensive_ocl_summary.py
                ├── 005_ai-python-validate_results.py
                └── 006_ai-python-write_run_log.py
```

### Why a single BLOCK

There is exactly one analytical pipeline here. Different orthogroup tools (OrthoHMM,
OrthoFinder, Broccoli) and different species sets are handled via the COPYME→RUN
pattern with distinct `run_label` values, not via separate BLOCKs. This matches how
`orthogroups_X_ocl` is structured.

---

## 4. Configuration (`START_HERE-user_config.yaml`)

```yaml
# GIGANTIC OCL using Simple Taxonomy - Workflow Configuration
# AI: Claude Code | Opus 4.6 | 2026 April 10
# Human: Eric Edsinger

# Run identification
# run_label names the output_to_input subdirectory; different RUN copies coexist
run_label: "Species71_X_OrthoHMM_X_Taxonomy"

# Species set identifier
species_set_name: "species71"

# Orthogroup clustering tool used to generate the input data
# Valid values: OrthoFinder | OrthoHMM | Broccoli
orthogroup_tool: "OrthoHMM"

# Input paths (relative to this workflow directory)
inputs:
  # Orthogroups output directory (orthogroup assignments in GIGANTIC IDs)
  # Change BLOCK to match the tool: BLOCK_orthofinder, BLOCK_orthohmm, BLOCK_broccoli
  orthogroups_dir: "../../../../orthogroups/output_to_input/BLOCK_orthohmm"

  # Phylonames mapping (genus_species → full phyloname)
  # Source of taxonomy hierarchy
  phylonames_map: "../../../../phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv"

# Taxonomy interpretation rules
taxonomy:
  # Internal-node presence rule for orthogroups
  # dollo_parsimony: clade has OG iff any descendant species has it (default, recommended)
  # majority: clade has OG iff > 50% descendants have it (experimental)
  internal_node_rule: "dollo_parsimony"

  # How to handle UNOFFICIAL taxonomic ranks (e.g., "Phylum10919UNOFFICIAL")
  # keep: treat as real taxonomic levels
  # collapse: skip these ranks when building the tree (use parent's parent)
  unofficial_rank_handling: "keep"

  # Exclude self-loop transitions where parent_name == child_name (terminal taxa)
  exclude_terminal_self_loops: true

# Output configuration
output:
  base_dir: "OUTPUT_pipeline"

  # Whether to include species composition in summary tables (can be large)
  include_species_lists: true
```

---

## 5. Pipeline Scripts (sketch)

All scripts follow GIGANTIC_1 conventions: AI attribution header, fail-fast validation,
`output/N-output/` structure, comprehensive logging, `Xs___Ys` dictionary naming, etc.

### Script 001: `001_ai-python-build_taxonomy_tree.py`

**Purpose**: Build the taxonomic tree from phylonames and emit it in the same file
formats that `trees_species` produces, so the rest of the pipeline can pretend it's
working with phylogenetic data.

**Reads**:
- `phylonames_map` (TSV: `genus_species → phyloname`)
- `orthogroups_dir/orthogroups_gigantic_ids.tsv` (used only to derive the species set
  actually present in the orthogroup data — keeps tree consistent with input)

**Writes** (to `1-output/`):
- `1_ai-taxonomy_tree-newick.nwk` — Newick of the constructed tree (for inspection)
- `1_ai-taxonomy_phylogenetic_blocks.tsv` — `parent_clade<TAB>child_clade<TAB>depth`
- `1_ai-taxonomy_parent_child_table.tsv` — same as `trees_species` format
- `1_ai-taxonomy_phylogenetic_paths.tsv` — root-to-leaf paths
- `1_ai-taxonomy_clade_to_species.tsv` — `clade<TAB>comma-separated species list`
- `1_ai-taxonomy_species_to_path.tsv` — `genus_species<TAB>full path from root`
- `1_ai-log-build_taxonomy_tree.log`

**Key logic**:
1. Parse each phyloname into ranks (`parts[0:5]` for K/P/C/O/F, `parts[5]` genus,
   `'_'.join(parts[6:])` species — handles multi-word species)
2. Insert each (rank-path) into a tree, deduplicating internal nodes
3. Apply `unofficial_rank_handling` rule
4. Walk tree to emit blocks, paths, parent-child relationships
5. Validate: every orthogroup species must appear as a leaf

### Script 002: `002_ai-python-determine_origins.py`

**Purpose**: For each orthogroup, find the MRCA clade in the taxonomy tree.

**Reads**:
- `1-output/` files
- `orthogroups_dir/orthogroups_gigantic_ids.tsv`
- (optionally) `orthogroups_dir/ID_mapping-short_to_gigantic.tsv`

**Writes** (to `2-output/`):
- `2_ai-orthogroups-origin_per_orthogroup.tsv` — one row per OG with origin clade
- `2_ai-orthogroups-species_membership.tsv` — long-format `OG<TAB>species` mapping
- `2_ai-log-determine_origins.log`

**Algorithm**: For each OG, collect species → look up each species's path → walk
upward from any species and intersect path-sets → deepest common node = origin.

### Script 003: `003_ai-python-quantify_conservation_loss.py`

**Purpose**: For each (OG, block) pair where the block is at-or-below the OG's origin,
classify as Conservation / Loss-at-Origin / Continued-Absence.

**Reads**:
- `1-output/` and `2-output/` files

**Writes** (to `3-output/`):
- `3_ai-blocks-events_per_block_per_orthogroup.tsv` — long-format event table
- `3_ai-blocks-conservation_loss_per_block.tsv` — per-block aggregates
- `3_ai-blocks-conservation_loss_per_orthogroup.tsv` — per-OG aggregates
- `3_ai-log-quantify_conservation_loss.log`

**Algorithm**: For each block in the tree at depth ≥ origin's depth, look up parent
clade presence and child clade presence (from clade-to-species → orthogroup membership)
and emit one event row per (OG, block).

### Script 004: `004_ai-python-comprehensive_ocl_summary.py`

**Purpose**: Produce the canonical per-orthogroup summary that downstream consumers use.

**Reads**: 1-output, 2-output, 3-output

**Writes** (to `4-output/`):
- `4_ai-orthogroups-complete_ocl_summary.tsv` — **the primary deliverable**
- `4_ai-clades-summary_per_clade.tsv`
- `4_ai-species-summary_per_species.tsv`
- `4_ai-log-comprehensive_ocl_summary.log`

**Schema for the primary table** (self-documenting headers per CLAUDE.md):

| Column | Description |
|---|---|
| `Orthogroup_ID (OrthoHMM/OrthoFinder/Broccoli orthogroup identifier)` | OG ID |
| `Origin_Clade (deepest taxonomic node containing all OG species, computed via Dollo MRCA)` | clade name |
| `Origin_Clade_Depth (distance from root in taxonomy tree)` | int |
| `Species_In_Orthogroup_Count (number of species carrying this orthogroup)` | int |
| `Species_In_Orthogroup_List (comma delimited Genus_species)` | csv |
| `Conservation_Rate_Percent (calculated as conservation events divided by conservation plus loss-at-origin events times 100, restricted to blocks at or below origin)` | float |
| `Loss_Rate_Percent (calculated as loss-at-origin events divided by conservation plus loss-at-origin events times 100, restricted to blocks at or below origin)` | float |
| `Conservation_Events_Count (count of parent->child blocks where both have OG)` | int |
| `Loss_At_Origin_Events_Count (count of parent->child blocks where parent has OG and child does not)` | int |
| `Continued_Absence_Events_Count (count of parent->child blocks where neither has OG, excluded from rates)` | int |
| `Zero_Transition_Flag (true if no scoring blocks exist for this OG, e.g. single-species OG)` | bool |
| `Tree_Topology_Source (taxonomy or trees_species — set to taxonomy here)` | string |
| `Run_Label (run_label from config, identifies this exploration)` | string |

The `Tree_Topology_Source` column is the key thing that lets a downstream consumer
distinguish results from this subproject vs. real `orthogroups_X_ocl` output even when
the rows are concatenated.

### Script 005: `005_ai-python-validate_results.py`

**Purpose**: Fail-fast validation of all outputs.

**Checks**:
- Every species in orthogroups appears in phylonames map
- Every orthogroup has exactly one origin clade
- For every OG: `Conservation_Rate + Loss_Rate ≈ 100` (within float tolerance) OR
  `zero_transition_flag == true`
- No re-acquisition events (would indicate bug under Dollo)
- All output files exist and are non-empty
- Counts in summary match counts in event tables

Exits with code 1 on any failure. Writes detailed `5_ai-validation_error_log.txt`.

### Script 006: `006_ai-python-write_run_log.py`

**Purpose**: Record run metadata, config snapshot, file checksums, environment info.
Standard pattern from other GIGANTIC_1 workflows.

---

## 6. Outputs Intended for Server

After a successful run, `RUN-workflow.sh` creates symlinks from `OUTPUT_pipeline/` into:

```
output_to_input/BLOCK_taxonomy_ocl_analysis/{run_label}/
```

Then `RUN-update_upload_to_server.sh` curates a smaller set into `upload_to_server/`:

| File | Purpose for Leonid |
|---|---|
| `4_ai-orthogroups-complete_ocl_summary.tsv` | The primary table — one row per OG |
| `4_ai-clades-summary_per_clade.tsv` | Per-clade view (e.g., "what fraction of Cnidaria OGs are conserved across Cnidaria") |
| `4_ai-species-summary_per_species.tsv` | Per-species view |
| `1_ai-taxonomy_tree-newick.nwk` | The constructed tree (so he can visualize what we used) |
| `README-for_collaborator.md` | Plain-English explainer: what this is, methodology, caveats, "this is taxonomy-based not phylogeny-based" |

---

## 7. Caveats and Limitations (must be in collaborator README)

1. **Taxonomy ≠ phylogeny**. NCBI taxonomy is a *classification*, not a reconstructed
   evolutionary tree. Branch lengths are meaningless. Polytomies are everywhere. Some
   ranks are missing or fabricated (`UNOFFICIAL` markers).
2. **Dollo parsimony assumption**. We assume no re-acquisition. Horizontal gene
   transfer and convergent gain are invisible to this analysis.
3. **No branch-length weighting**. A loss along a long branch is treated identically
   to a loss along a short branch.
4. **Internal-node presence is reconstructed, not observed**. We can't distinguish
   "ancestor really had it" from "at least one descendant has it."
5. **Results will differ from real OCL**. The phylogenetic tree from `trees_species`
   has different topology, different internal nodes, and uses different ancestral
   state reconstruction. Expect numerical differences when comparing.
6. **This is a first-pass analysis**. Useful for descriptive overview, prioritization,
   and downstream pipeline development. **Not a substitute** for proper phylogenetic
   ancestral state reconstruction in publications.

The collaborator README will state plainly:

> *"These tables use NCBI taxonomy as a stand-in for the species phylogeny while the
> phylogenetic-tree-based OCL pipeline (`orthogroups_X_ocl/`) is being prepared. They
> are scientifically defensible as a first-pass descriptive analysis but should not
> be the basis for evolutionary claims about specific origin/loss events. The
> definitive analysis will replace these tables once `trees_species` is run."*

---

## 8. Migration Path to Real OCL

When `trees_species/BLOCK_permutations_and_features/` produces output for the same
species set, the migration is straightforward by design:

1. The output schema is **identical** to what `orthogroups_X_ocl` will produce.
2. The `Tree_Topology_Source` column lets us distinguish them in any downstream
   pipeline that wants both for comparison.
3. Scripts 002–005 of this pipeline are nearly drop-in usable in `orthogroups_X_ocl`
   if we abstract the "tree source" — they only differ in how Script 001 builds the
   tree (taxonomy parsing here vs. reading trees_species files there).
4. Discrepancy analysis becomes a natural follow-up: "for which OGs does taxonomy-OCL
   and phylogeny-OCL disagree, and why?" This is a publishable result on its own.

We could even unify the two subprojects later by making `orthogroups_X_ocl` accept
a `tree_source` config parameter (`taxonomy` | `trees_species`). For now, keeping them
separate is cleaner — different subprojects = different scientific claims.

---

## 9. Estimated Effort

- **Script 001 (taxonomy tree builder)**: ~half day. Most of the novel logic is here.
- **Scripts 002–004**: ~half day. Largely mirror the existing `orthogroups_X_ocl`
  scripts of the same number; the algorithmic logic is identical, only the input
  format differs.
- **Script 005 validation**: ~couple hours.
- **Script 006 run log**: ~hour. Boilerplate.
- **NextFlow `main.nf` + `nextflow.config`**: ~couple hours. Pattern is well-known.
- **README, AI_GUIDEs (3 levels), config docs**: ~half day.
- **First successful run + table publication**: ~hour beyond the above.

**Total**: ~2 days of focused work for a polished version. A minimum-viable version
that produces the primary table for Leonid could be done faster by deferring full
NextFlow integration and running scripts directly (the pipeline is small enough to
run as bash + python without NextFlow for the first pass).

---

## 10. Open Design Questions

These should be discussed before implementation begins:

1. **Internal-node rule**: Stick with strict Dollo parsimony, or also offer a
   "majority rule" reconstruction as a sanity check? My recommendation: ship with
   Dollo only, add majority later if it proves useful.

2. **UNOFFICIAL ranks**: Keep them as taxonomic levels, or collapse them so the tree
   uses only "real" ranks? This affects branch counts and therefore conservation/loss
   rates. My recommendation: `keep` by default — it preserves the structure that
   phylonames carry; offer `collapse` as a config option for sensitivity testing.

3. **Species set scope**: Run only on the species actually present in the orthogroups
   input, or on the full species set from genomesDB? My recommendation: orthogroups
   species only, so the tree exactly matches what's being analyzed.

4. **Multi-tool runs**: Should one run produce one table (Species71 × OrthoHMM ×
   Taxonomy), or should there be a unified output combining OrthoHMM + OrthoFinder +
   Broccoli? My recommendation: one tool per RUN copy, mirroring `orthogroups_X_ocl`.
   A separate downstream comparison subproject can unify them.

5. **NextFlow vs. bash-orchestrated**: For the first deliverable, do we need NextFlow
   or is `RUN-workflow.sh` running scripts sequentially good enough? The pipeline is
   small and serial. My recommendation: skip NextFlow for v1, add later if needed —
   matches `phylonames` pattern where some workflows are just bash.

6. **Where exactly on the server?** We need to confirm the upload path before
   implementing `RUN-update_upload_to_server.sh`.

---

## 11. What this Document Becomes After Implementation

This file (`DESIGN-ocl_using_simple_taxonomy.md`) stays in the subproject root as the
**design record**. Once implementation begins:

- A proper `README.md` is added (user-facing)
- A proper `AI_GUIDE-ocl_using_simple_taxonomy.md` is added (Level 2)
- This DESIGN file remains as the "why we built it this way" reference, similar to
  how some pipelines preserve early ERD or planning docs.

---

## 12. Pre-Implementation Checklist (CLAUDE.md compliance)

- [ ] User confirms the design (this document) reflects intent
- [ ] User answers the open design questions in §10
- [ ] User confirms server upload path for §6
- [ ] Read the existing `orthogroups_X_ocl` scripts in detail (Scripts 002–005) so
      this pipeline's equivalents preserve the same algorithmic logic
- [ ] Read `phylonames/output_to_input/maps/` map file format to confirm parsing
- [ ] Read OrthoHMM `4_ai-orthogroups_gigantic_ids.tsv` format to confirm parsing
- [ ] Verify which species set is actually in OrthoHMM RUN_1 (species70 vs species71)
- [ ] Decide on conda environment name (`ai_gigantic_ocl_using_simple_taxonomy`?)
- [ ] Confirm whether NextFlow is required (§10 question 5)
