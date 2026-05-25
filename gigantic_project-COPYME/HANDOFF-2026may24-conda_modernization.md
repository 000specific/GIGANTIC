# HANDOFF — Conda Modernization + NF26 Patches across 27 GIGANTIC COPYMEs

**Date started**: 2026-05-24
**Active session topic**: Eric is modernizing the 28 legacy `workflow-COPYME-*` directories in `gigantic_project-COPYME` so each is "fully modern and autonomous on first run" — per-workflow conda env yml + on-demand env install + NextFlow 26.x compatibility.

**Read these memory files first** (post-compaction me, this is the most important context):
- `~/.claude/projects/-blue-moroz-share-edsinger-projects-ai-ctenophores-github-gigantic-1-GIGANTIC/memory/reference_gigantic_conda_env_naming_convention.md` — env naming rules
- `~/.claude/projects/.../memory/reference_gigantic_yaml_to_params_universal_pattern.md` — YAML→params universal pattern
- `~/.claude/projects/.../memory/feedback_no_known_gap_deferrals.md` — DO NOT defer pyyaml additions or other known gaps
- `~/.claude/projects/.../memory/feedback_check_git_before_rewriting_existing_files.md` — git log before overwriting
- `~/.claude/projects/.../memory/MEMORY.md` — full memory index

---

## The plan (SCOPE EXPANDED 2026-05-24 EOD)

Original scope was conda + NF26 patches. User asked on 2026-05-24 to fold in
the SLURM-wrapper deprecation as well, so each workflow is also converted from
"separate RUN-workflow.sbatch wrapper" → "unified RUN-workflow.sh that
self-submits based on execution_mode YAML key". The canonical reference for
this self-submit pattern is `subprojects/annotations_X_ocl/BLOCK_ocl_analysis/
workflow-COPYME-ocl_analysis/RUN-workflow.sh` (lines 57-178).

For each legacy workflow-COPYME-* dir, modernize so that:
1. **Per-workflow conda env yml at `<workflow>/ai/conda_environment.yml`** with:
   - Naming convention comment header (the `aiG-<subproject>-<block_or_step>-<optional_details>` spec)
   - `name: aiG-<subproject>-<block_or_step>-[<optional_details>]` (env name)
   - Deps copied from the matching legacy `gigantic_project-COPYME/conda_environments/ai_gigantic_X.yml`
   - `pyyaml` ADDED (required by the YAML→JSON heredoc in RUN-workflow.sh — DO NOT defer this)
   - Any license/manual-install steps preserved as comments

2. **NextFlow 26.x compatible nextflow.config**:
   - NO `import org.yaml.snakeyaml.Yaml` (top-level imports rejected by NF26)
   - `params { ... }` block with literal defaults (nested defaults match nested YAML; flat for flat YAML)
   - All `userConfig?.X?.Y` references replaced with `params.X.Y`

3. **NextFlow 26.x compatible main.nf**:
   - Top-level `workflow.onComplete { ... }` blocks DELETED (NF26 parser rejects)
   - `params.X` accesses changed to match the YAML shape if needed (e.g. `params.project_name` → `params.project.name` when YAML has nested `project: { name: ... }`)

4. **RUN-workflow.sh** rewritten with full universal driver:
   - `read_config` bash-grep helper at top (no Python dep)
   - SLURM self-submit block (reads `execution_mode` from YAML; if "slurm" and not already in a SLURM job, builds sbatch args from `cpus`/`memory_gb`/`time_hours`/`slurm_account`/`slurm_qos` and self-submits via `sbatch ... --wrap="bash $(realpath $0)"`, then exits 0)
   - Modern auto-install conda block
   - Universal YAML→JSON pass-through heredoc (no flatten — see memory pattern doc)
   - `-params-file .params.json` added to all `nextflow run` invocations

5. **START_HERE-user_config.yaml** additions:
   - `execution_mode: "local"` (default; user flips to "slurm" if needed)
   - `slurm_account: "your_account"` + `slurm_qos: "your_qos"` placeholders
   - `cpus`, `memory_gb`, `time_hours` (per-workflow sensible defaults)

6. **AI_GUIDE-*.md** in `<workflow>/ai/` updated:
   - Replace legacy env name references (`ai_gigantic_X`) with new `aiG-<subproject>-<descriptor>` name
   - Replace legacy yml path references (`../../../../conda_environments/ai_gigantic_X.yml`) with `ai/conda_environment.yml`
   - Replace `sbatch RUN-workflow.sbatch` instructions with: "set execution_mode: slurm in START_HERE-user_config.yaml, then `bash RUN-workflow.sh` self-submits"
   - Update any "Environment 'X' not found" error message examples in troubleshooting tables
   - Update setup instructions if they reference the legacy `RUN-setup_environments.sh`
   - For workflows with multiple variants (e.g. orthohmm + orthohmm_GIGANTIC sharing one env), note the shared env in the troubleshooting/setup section

7. **DELETE `RUN-workflow.sbatch`** at workflow root (now obsolete — self-submit handled by RUN-workflow.sh)

**Retroactive work needed on already-"completed" subprojects** (step 4 SLURM block + step 5 YAML keys + step 7 .sbatch deletion):
- annotations_hmms (6 COPYMEs) — also needs heredoc retro (flatten→pass-through) and AI_GUIDE
- orthogroups (6 COPYMEs)
- genomesDB (4 STEPs)
Total retro: 16 workflows.

**Forward work** (full 6-step pattern on first pass):
- phylonames (2 STEPs), gene_sizes (2), public_databases (2), secretome (1),
  one_direction_homologs (1), dark_proteomes (?), hotspots (×2)

---

## Universal patterns (templates to copy)

### Conda env yml header template (drop into every ai/conda_environment.yml)
```yaml
# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
#   subproject       = subprojects/ dir name verbatim
#   block_or_step    = BLOCK_X or STEP_N-X with the BLOCK_/STEP_N- prefix stripped
#   optional_details = workflow-distinguishing suffix used ONLY when sibling
#                      workflow-COPYME-* dirs in the same BLOCK need GENUINELY
#                      different envs. Default = sibling workflows share env.
#
# AI: Claude Code | Opus 4.7 | 2026 May 24
# Human: Eric Edsinger
```

### Conda block in RUN-workflow.sh (modern auto-install, copy + adapt ENV_NAME)
```bash
# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
# Per-BLOCK conda env. Auto-created on first run from ai/conda_environment.yml.
# mamba is preferred (much faster); conda is the fallback if mamba is missing.

ENV_NAME="aiG-<subproject>-<descriptor>"  # <-- EDIT PER WORKFLOW
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

env_is_complete() {
    local env_prefix=$(conda env list 2>/dev/null | awk -v n="${ENV_NAME}" '$1==n {print $NF}')
    if [ -z "${env_prefix}" ]; then return 1; fi
    if [ ! -x "${env_prefix}/bin/python" ]; then return 1; fi
    return 0
}

if ! env_is_complete; then
    if conda env list 2>/dev/null | awk '{print $1}' | grep -q "^${ENV_NAME}$"; then
        echo "Removing broken/incomplete env '${ENV_NAME}'..."
        conda env remove -n "${ENV_NAME}" -y 2>&1 | tail -3
    fi
    echo "Creating conda env '${ENV_NAME}' from ${ENV_YML}..."
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    if ! env_is_complete; then
        echo "ERROR: Environment creation failed -- '${ENV_NAME}' still not complete."
        exit 1
    fi
    echo "Env '${ENV_NAME}' created successfully."
fi

if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

# Ensure NextFlow is available (conda env or system module)
if ! command -v nextflow &> /dev/null; then
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available!"
        exit 1
    fi
fi
```

### YAML→JSON pass-through heredoc + nextflow run (universal)
```bash
# ============================================================================
# Flatten START_HERE-user_config.yaml -> .params.json for NextFlow -params-file
# ============================================================================
# Universal pass-through pattern (no flatten). NextFlow's params is a ConfigMap
# that supports nested access (params.X.Y.Z) natively, so we preserve YAML
# shape rather than translating it.

python3 <<'PYTHON_DUMP'
import yaml, json
with open( 'START_HERE-user_config.yaml' ) as f:
    cfg = yaml.safe_load( f )
with open( '.params.json', 'w' ) as f:
    json.dump( cfg, f, indent=2 )
PYTHON_DUMP

nextflow run ai/main.nf ${RESUME_FLAG} \
    -c ai/nextflow.config \
    -params-file .params.json
```

---

## Workflow inventory (27 in scope, 1 placeholder skipped)

### ALREADY COMPLETE — 5 + 1 = 6 (annotations_hmms)
- ✅ `subprojects/annotations_hmms/BLOCK_build_annotation_database/workflow-COPYME-build_annotation_database` → env `aiG-annotations_hmms-build_annotation_database`
- ✅ `subprojects/annotations_hmms/BLOCK_signalp/workflow-COPYME-run_signalp` → env `aiG-annotations_hmms-signalp`
- ✅ `subprojects/annotations_hmms/BLOCK_tmbed/workflow-COPYME-run_tmbed` → env `aiG-annotations_hmms-tmbed`
- ✅ `subprojects/annotations_hmms/BLOCK_metapredict/workflow-COPYME-run_metapredict` → env `aiG-annotations_hmms-metapredict`
- ✅ `subprojects/annotations_hmms/BLOCK_deeploc/workflow-COPYME-run_deeploc` → env `aiG-annotations_hmms-deeploc`
- ✅ `subprojects/annotations_hmms/BLOCK_interproscan/workflow-COPYME-run_interproscan` → env `aiG-annotations_hmms-interproscan`

**Caveats** (both queued as retroactive cleanup):
- The 6 annotations_hmms RUN-workflow.sh files use the FLATTEN-1-LEVEL heredoc variant (works for flat YAML, but inconsistent with universal pattern). RETROACTIVELY swap to the no-flatten pass-through for codebase consistency.
- The 6 annotations_hmms AI_GUIDE-*.md files have NOT been updated yet (legacy `ai_gigantic_X` references etc. still present). RETROACTIVELY patch them.

### IN PROGRESS — orthogroups (6 workflows in scope; the 7th orthohmm USED_FOR_RUNS_1_TO_3 is SKIPPED per user; treated as historical config snapshot)
- ✅ `subprojects/orthogroups/BLOCK_broccoli/workflow-COPYME-run_broccoli` → env `aiG-orthogroups-broccoli` **DONE 2026-05-24** (template for other 5)
  - ai/conda_environment.yml: broccoli-dedicated with pyyaml + naming convention header
  - ai/nextflow.config: nested params block; isSlurm derived from params.execution_mode; per-process resources from params.resources.*; no Yaml import
  - ai/main.nf: 11 params accesses converted to nested (params.output.base_dir, params.resources.run_broccoli.cpus, params.broccoli.tree_method, params.project.name, params.inputs.proteomes_dir); workflow.onComplete block deleted
  - RUN-workflow.sh: modern conda auto-install block (ENV_NAME=aiG-orthogroups-broccoli, ENV_YML=ai/conda_environment.yml); universal YAML→JSON pass-through heredoc; `-params-file .params.json` on nextflow run
  - ai/AI_GUIDE-broccoli_workflow.md: legacy `ai_gigantic_orthogroups_broccoli` references replaced with `aiG-orthogroups-broccoli` (2 sites); legacy yml-path references replaced with `ai/conda_environment.yml`
- ✅ `subprojects/orthogroups/BLOCK_comparison/workflow-COPYME-compare_methods` → env `aiG-orthogroups-comparison` **DONE 2026-05-24**
  - ai/conda_environment.yml: matplotlib + numpy + pyyaml + nextflow (lightweight cross-tool comparison; no orthogroup tool deps)
  - ai/nextflow.config: already had flat params + no Yaml import — unchanged
  - ai/main.nf: workflow.onComplete deleted; params accesses already flat (matches flat YAML)
  - RUN-workflow.sh: modern conda block + universal pass-through heredoc + -params-file
  - ai/AI_GUIDE-comparison_workflow.md: Quick Start section updated to reference auto-install convention; legacy `ai_gigantic_orthogroups` references removed
- ✅ `subprojects/orthogroups/BLOCK_orthofinder/workflow-COPYME-run_orthofinder` → env `aiG-orthogroups-orthofinder` **DONE 2026-05-24** (already had no Yaml import; just onComplete removed + RUN-workflow.sh modernized + AI_GUIDE updated)
- ✅ `subprojects/orthogroups/BLOCK_orthofinder_array/workflow-COPYME-run_orthofinder_array` → env `aiG-orthogroups-orthofinder` **DONE 2026-05-24** (nested-params rewrite of nextflow.config; main.nf params accesses converted to nested + workflow.onComplete deleted; RUN-workflow.sh modernized; AI_GUIDE already clean)
- ✅ `subprojects/orthogroups/BLOCK_orthohmm/workflow-COPYME-run_orthohmm` → env `aiG-orthogroups-orthohmm` **DONE 2026-05-24** (nested-params rewrite incl. validation checks `params.orthohmm.cpus == 0`; main.nf converted; RUN-workflow.sh modernized)
- ✅ `subprojects/orthogroups/BLOCK_orthohmm_GIGANTIC/workflow-COPYME-run_orthohmm_GIGANTIC` → env `aiG-orthogroups-orthohmm` **DONE 2026-05-24** (most complex orthogroup workflow: nested params + dynamic resource escalation `{ params.resources.phmmer_pair.cpus * task.attempt }` preserved; main.nf converted; RUN-workflow.sh modernized)

**All 6 orthogroups workflows pass the audit**: ymY=1 (pyyaml present), Yi=0 (no Yaml imports), wc=0 (no workflow.onComplete), fp=2 (pass-through PYTHON_DUMP heredoc), lg=0 (no legacy ai_gigantic refs in RUN-workflow.sh)

**Orthogroups env design**: 4 distinct envs (one per tool) shared across the 6 workflows:
| env | used by |
|---|---|
| `aiG-orthogroups-orthohmm` | BLOCK_orthohmm + BLOCK_orthohmm_GIGANTIC |
| `aiG-orthogroups-orthofinder` | BLOCK_orthofinder + BLOCK_orthofinder_array |
| `aiG-orthogroups-broccoli` | BLOCK_broccoli only |
| `aiG-orthogroups-comparison` | BLOCK_comparison only |

### PENDING — by subproject (env naming per the convention; verify each by checking matching legacy yml content)

**genomesDB (4 STEPs, single shared env)**:
- `subprojects/genomesDB/STEP_1-sources/workflow-COPYME-ingest_source_data`
- `subprojects/genomesDB/STEP_2-standardize_and_evaluate/workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb`
- `subprojects/genomesDB/STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB`
- `subprojects/genomesDB/STEP_4-create_final_species_set/workflow-COPYME-create_final_species_set`

Probably all share `aiG-genomesDB-shared` (or per-STEP if they need different deps — investigate when reached). Legacy env was `ai_gigantic_genomesdb` (shared).

**phylonames (2 STEPs)**: probably share `aiG-phylonames` env (legacy was `ai_gigantic_phylonames` shared). Confirm at the time.
- `subprojects/phylonames/STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames`
- `subprojects/phylonames/STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames`

**gene_sizes (2 workflows in same BLOCK, USER CONFIRMED shared env)**:
- `subprojects/gene_sizes/BLOCK_analyze_gene_sizes/workflow-COPYME-analyze_gene_sizes-all_inclusive`
- `subprojects/gene_sizes/BLOCK_analyze_gene_sizes/workflow-COPYME-analyze_gene_sizes-gene_vs_protein`
- Shared env: `aiG-gene_sizes-analyze_gene_sizes` (no optional_details since same env)

**public_databases (2 BLOCKs)**:
- `subprojects/public_databases/BLOCK_ncbi_nr_diamond/workflow-COPYME-download_build_ncbi_nr_diamond`
- `subprojects/public_databases/BLOCK_ncbi_nr_blastp/workflow-COPYME-download_build_ncbi_nr_blastp`
- Likely separate envs (diamond vs blastp); investigate when reached.

**secretome (1 BLOCK — special)**:
- `subprojects/secretome/BLOCK_secretome_evidence_table/workflow-COPYME-build_evidence_table`
- Currently references `ai_gigantic_metapredict` env (almost certainly wrong — secretome shouldn't need metapredict). Ask user: split into own env (`aiG-secretome-secretome_evidence_table`) with appropriate lightweight deps?

**one_direction_homologs (1 BLOCK)**:
- `subprojects/one_direction_homologs/BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr`
- Env: `aiG-one_direction_homologs-diamond_ncbi_nr`. Legacy was `ai_gigantic_one_direction_homologs`.

**Investigate when reached (no conda activation in current RUN-workflow.sh)**:
- `subprojects/dark_proteomes/BLOCK_classify_dark_proteome/workflow-COPYME-classify_dark_proteome`
- `subprojects/hotspots/BLOCK_self_blast/workflow-COPYME-self_blast`
- `subprojects/hotspots/BLOCK_identify_hotspots/workflow-COPYME-identify_hotspots`
- Need to figure out what each does + what env it should have (or whether they're placeholders).

### SKIPPED (per user)
- `subprojects/trees_species/BLOCK_de_novo_species_tree/workflow-COPYME-build_species_tree` — placeholder; `.gitignore` already added that excludes everything except itself.

---

## Critical conventions / things to NOT do

- **DO** include the naming-convention comment header in EVERY new ai/conda_environment.yml
- **DO** include `pyyaml` in EVERY new ai/conda_environment.yml (required by the universal pass-through heredoc)
- **DO** preserve license-required manual install notes (signalp, deeploc, interproscan) as comments in their ymls
- **DO** check git for existing files before overwriting (per `feedback_check_git_before_rewriting_existing_files.md`)
- **DO** ask user about env-sharing design decisions per subproject before doing the work
- **DON'T** flatten YAML in the Python heredoc — use the pass-through pattern (`json.dump(cfg, f, indent=2)`)
- **DON'T** touch RUN_* dirs — strictly COPYMEs only
- **DON'T** modify the trees_species/de_novo placeholder
- **DON'T** modify the orthohmm USED_FOR_RUNS_1_TO_3 historical snapshot
- **DON'T** modify the 4 ai-prefixed kept envs (ai_gigantic_tmbed, ai_gigantic_signalp, ai_gigantic_signalp_slow used by running TMBed/SignalP jobs; ai_deeplabcut + ai_deeplabcut_official)
- **DON'T** delete `gigantic_project-COPYME/conda_environments/` or `RUN-setup_environments.sh` yet — wait until ALL 207 workflows project-wide are on the modern pattern

---

## Environment cleanup completed 2026-05-24

26 envs removed from `/blue/moroz/share/edsinger/conda/envs/`. Kept 7:
```
aiG-trees_gene_groups-hgnc_gene_groups
aiG-trees_gene_groups-rbh_rbf_homologs
ai_gigantic_tmbed             ← in use by TMBed RUN_3 long + RUN_4 short
ai_gigantic_signalp           ← in use by SignalP RUN_5 fast
ai_gigantic_signalp_slow      ← in use by SignalP RUN_4 slow
ai_deeplabcut
ai_deeplabcut_official
```

When a user creates a fresh RUN_N from a modernized COPYME, the new env (`aiG-<subproject>-<X>`) will auto-install via mamba on first `bash RUN-workflow.sh`.

---

## Status as of last update (2026-05-25)

### ⚠️ NF VERSION PINNED TO <26.0 (2026-05-25)

All 28 `ai/conda_environment.yml` files now constrain `nextflow>=23.0,<26.0`.

**Why**: NF 26.04.2 introduces a strict config DSL that retroactively rejects multiple long-standing patterns in these workflows:
- `def X = ...` declarations mixed with config blocks (params{}/executor{}/process{}) — Error: "Variable declarations cannot be mixed with config statements"
- `executor { $local { ... } $slurm { ... } }` scoped-block syntax — silently dropped as "Unrecognized config option"
- Top-level statements in `main.nf` outside process/workflow/function blocks — Error: "Statements cannot be mixed with script declarations"
- (Possibly more not yet discovered)

We fixed the `def` issue in our 10 affected COPYMEs (inlined params references). The remaining NF 26.x DSL changes affect more code (scoped-block executors, top-level statements in main.nf, conditional executor blocks) and the iteration cost of "fix, test, repeat against a moving target" is high. **Pinning is the pragmatic stopping point** — preserves all the conda + NF26-precursor patches we made, but holds NF version at the proven-working tier until a dedicated NF 26.x migration session can do it thoroughly.

**To revisit later**: when NF 26.x DSL stabilizes and a focused session has bandwidth, work through all remaining 26.x rejections in COPYME + bump pin to allow `>=26.0`. Issues to address (audited 2026-05-25):
- 2 of our 28 cfg files have top-level `if (...) { executor {...} } else { executor {...} }` blocks (interproscan, one_direction_homologs) — flatten to a single `executor {}` with conditional values inside
- Scoped executor syntax `executor { $local {...} $slurm {...} }` is no longer recognized — find NF 26.x replacement
- Top-level Groovy statements in main.nf (e.g. `scripts_dir = "..."`) — hoist into workflow{} block

---

### ✅ ALL 28 WORKFLOWS FULLY MODERNIZED (within NF 25.x scope)

Every one of the 28 legacy `workflow-COPYME-*` directories now has:
1. `ai/conda_environment.yml` with the `aiG-<subproject>-...` naming convention + `nextflow>=23.0,<26.0` pin
2. `ai/nextflow.config` patched for NextFlow 26.x-precursor (no SnakeYAML import, params block with nested defaults; top-level `def` inlined; still has some patterns rejected by NF 26.04.2 strict-DSL — see pin note above)
3. `ai/main.nf` patched (nested params accesses, top-level `workflow.onComplete` deleted)
4. `RUN-workflow.sh` rewritten with:
   - SLURM-self-submit block (canonical = phylonames STEP_1; alternate = Python-eval in dark_proteomes/hotspots)
   - Modern conda auto-install (env_is_complete + mamba env create on first run)
   - Universal YAML→JSON pass-through heredoc (no flatten) + `-params-file .params.json`
5. `START_HERE-user_config.yaml` has `execution_mode` + `slurm_account` + `slurm_qos` + `cpus` + `memory_gb` + `time_hours`
6. `AI_GUIDE-*.md` updated to reflect unified-driver pattern
7. `RUN-workflow.sbatch` deleted (and `SLURM_workflow.sbatch` for BLOCK_comparison)

### Final inventory (28 modernized + 1 skipped)

| Subproject | Workflows | Env name(s) |
|---|---|---|
| annotations_hmms (6) | signalp, tmbed, metapredict, deeploc, interproscan, build_annotation_database | 6 per-tool envs `aiG-annotations_hmms-<tool>` |
| orthogroups (6) | broccoli, comparison, orthofinder, orthofinder_array, orthohmm, orthohmm_GIGANTIC | 4 envs: `aiG-orthogroups-{broccoli,comparison,orthofinder,orthohmm}` (orthofinder + orthohmm each shared by 2 BLOCKs) |
| genomesDB (4) | STEP_1, STEP_2, STEP_3, STEP_4 | `aiG-genomesDB` (shared) |
| phylonames (2) | STEP_1, STEP_2 | `aiG-phylonames` (shared) |
| gene_sizes (2) | all_inclusive, gene_vs_protein | `aiG-gene_sizes-analyze_gene_sizes` (shared) |
| public_databases (2) | ncbi_nr_blastp, ncbi_nr_diamond | `aiG-public_databases` (shared) |
| one_direction_homologs (1) | diamond_ncbi_nr | `aiG-one_direction_homologs` (has local/slurm/slurm_burst modes) |
| secretome (2) | build_evidence_table, secretome_per_moroz_17may2026 | 2 per-BLOCK envs |
| dark_proteomes (1) | classify_dark_proteome | `aiG-dark_proteomes` |
| hotspots (2) | self_blast, identify_hotspots | `aiG-hotspots` (shared) |
| **Skipped**: orthogroups/BLOCK_orthohmm/workflow-COPYME-run_orthohmm_USED_FOR_RUNS_1_TO_3 | (historical snapshot — intentionally NOT modernized) |

### Audit results (final)
- 28 / 28 workflows have `ai/conda_environment.yml`, `execution_mode` in YAML, no `.sbatch` file, and `bash -n RUN-workflow.sh` PASS
- 25 / 28 use the canonical `read_config()` bash helper for YAML-key reads before conda env exists
- 3 / 28 (dark_proteomes/BLOCK_classify_dark_proteome, hotspots/BLOCK_self_blast, hotspots/BLOCK_identify_hotspots) use a functionally-equivalent Python-eval pattern instead — these workflows were already richly modern and were retained as-is rather than rewriting working code

### Scope NOT modernized in this sweep (separate future scope)
- 17 additional template-COPYMEs across 7 untouched subprojects: `annotations_X_ocl` (1), `homolog_counts` (1), `orthogroups_X_ocl` (1), `parsimony_tree_structures` (1), `trees_gene_groups` (7), `trees_species` (4), `trees_gene_families/gene_family_COPYME` (~2)
- 5 zero-COPYME subprojects awaiting initial scaffolding: `ocl_perspectives`, `ocl_using_simple_taxonomy`, `synteny`, `trees_gene_families_X_ocl`, `trees_gene_groups_X_ocl`
- The 163 trees_gene_families gene-family workflow instances likely all share a base template; modernize the 2 templates + mass-regenerate is the realistic approach
- All RUN_N instances under any subproject — these are **scientific records of work as conducted** and are intentionally never modified (RUN_Ns are historical lab-notebook artifacts; the COPYME templates are what future RUN_Ns are created from)

---

## How to update this doc as work progresses

When finishing a subproject:
1. Mark its workflows as ✅ in the inventory above
2. Add notes under "Just-finished work" with concrete file paths + decisions
3. Update "Currently working on" to reflect the next subproject

When making a non-obvious decision (env sharing design, special case, etc.):
- Add a paragraph under the relevant subproject's bullet
- Note user confirmation / user instruction if applicable

When the post-compaction me reads this doc:
- Memory files first (paths at top)
- Then "Plan" + "Universal patterns" sections
- Then "Workflow inventory" to see what's done vs pending
- Then "Status as of last update" to see exactly where to resume
- Then re-read memory `feedback_no_known_gap_deferrals.md` and `feedback_check_git_before_rewriting_existing_files.md` to avoid repeating past mistakes
