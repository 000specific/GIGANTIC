# Broken Conda Env Detection Pattern

**Purpose**: Detect and auto-recover from partially-created conda environments
("broken husks") that conda silently reuses on subsequent `env create` calls.

**Origin**: 2026 April 18 — `trees_species/BLOCK_user_requests` hit this when
the ete3 + PyQt5 install repeatedly failed partway and left 15-package
directories that conda refused to overwrite. Pipelines soft-failed with
`ModuleNotFoundError`.

**Status**: Shipped in `trees_species/BLOCK_user_requests/workflow-COPYME-select_structures/RUN-workflow.sh`.
Not yet propagated to other subprojects' RUN-workflow.sh files — they should
adopt this pattern when their own envs turn up flaky.

---

## The problem

`mamba env create -f env.yml -y` (and `conda env create`) will **silently
reuse an existing env directory** if the env name is already registered,
even if that directory contains a half-installed broken state. Common
causes:

- Package solve fails partway (network error, channel conflict)
- GPU drivers or system libs mid-install and the job dies
- A previous `env create` was killed before completion

The env name appears in `conda env list`, but the directory only has low-
level packages (e.g., 15 of them, no Python, no project dependencies).
Downstream scripts then fail with opaque `ModuleNotFoundError` messages.

**Why `env create -y` doesn't fix it**: `-y` means "answer yes to prompts,"
not "rebuild if broken." Conda considers a named env "present" if the
directory exists, regardless of its completeness.

---

## The pattern

Two functions + a one-shot repair block at the top of a RUN-workflow.sh:

```bash
# Detect whether a named conda env has a usable Python binary.
# A complete env has:
#   - an entry in `conda env list`
#   - an executable at <env_prefix>/bin/python
# Returns 0 (success) if complete, 1 (failure) if missing or broken-husk.
env_is_complete() {
    local env_prefix=$(conda env list 2>/dev/null | awk -v n="${ENV_NAME}" '$1==n {print $NF}')
    if [ -z "${env_prefix}" ]; then
        return 1   # not found at all
    fi
    if [ ! -x "${env_prefix}/bin/python" ]; then
        return 1   # env dir exists but broken/empty
    fi
    return 0
}

# Repair: if env is missing OR broken, remove any husk and rebuild from YAML.
if ! env_is_complete; then
    # Remove any registered broken husk first — conda refuses to overwrite.
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

    # Verify the rebuild actually produced a usable env — fail fast if not.
    if ! env_is_complete; then
        echo "ERROR: Environment creation failed -- '${ENV_NAME}' still not complete."
        exit 1
    fi
    echo "Env '${ENV_NAME}' created successfully."
fi
```

`ENV_NAME` and `ENV_YML` are set just above this block in the RUN-workflow.sh
for the specific workflow — e.g.

```bash
ENV_NAME="aiG-trees_species-user_requests"
ENV_YML="ai/conda_environment.yml"
```

---

## When to adopt this pattern

**Always** for any RUN-workflow.sh that creates/activates a conda env — the
cost is ~20 extra lines and the upside is auto-recovery from a class of
failures that otherwise produce confusing downstream errors.

**Especially** for:
- Workflows with flaky upstream packages (PyQt5, GPU-dependent packages,
  packages that pin against specific CUDA/libc versions)
- Workflows run from login nodes where a SLURM submission mid-install can
  leave a husk
- Long-running env builds where users may Ctrl-C before completion

---

## Known-broken envs as of 2026-04-18 (pending cleanup)

These exist as broken husks on the system and should be removed before
next use so the pattern's auto-rebuild kicks in:

- `aiG-trees_species-permutations_and_features`
- `aiG-trees_species-gigantic_species_tree`
- (likely others in trees_species that depended on ete3)

Remove with:

```bash
conda env remove -n aiG-trees_species-permutations_and_features -y
conda env remove -n aiG-trees_species-gigantic_species_tree -y
```

Then ensure the BLOCK's `conda_environment.yml` has been updated to the
toytree-based pattern (see `frameworks/tree_visualization-toytree-pattern.md`
if/when written — currently covered by the reference memory
`reference_toytree_visualization.md`). After cleanup, the next
`bash RUN-workflow.sh` in those BLOCKs will detect the missing env and
rebuild it clean.

---

## Related infrastructure

- `RUN-setup_environments.sh` at project root — one-shot env setup tool
  for the whole GIGANTIC workspace. If the broken-env pattern proves
  useful, we may want to fold it into that tool too.

- Per-BLOCK `conda_environment.yml` files — kept minimal and pinned to
  known-working channel configurations when possible. Pip-installs for
  packages not available on conda-forge are explicit (e.g. toytree).
