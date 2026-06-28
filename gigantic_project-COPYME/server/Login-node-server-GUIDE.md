<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 June 26
Human:   Eric Edsinger
Purpose: Document the login-node deployment pattern for the GIGANTIC data
         server — when to use it, how to deploy it, and how lab members
         reach it. Complements `AI_GUIDE.md` (which covers canonical SLURM
         mode + publishing workflow) by adding the alternative `local`-mode
         pattern needed for shared access by multiple group members.
History:
  2026-06-19  Threading fix landed in `ai/gigantic_server.py`
              (`socketserver.TCPServer` → `socketserver.ThreadingTCPServer`
              + `daemon_threads = True`). Without this fix, the server
              freezes when a single request blocks.
  2026-06-19  Login-node deployment pattern adopted as workaround for
              HiPerGator `pam_slurm_adopt` policy that prevents non-job-
              owners from reaching SLURM-mode servers via SSH tunnel.
  2026-06-26  This guide created to consolidate the pattern for reuse by
              other AI sessions / lab members.
============================================================================ -->

# `Login-node-server-GUIDE.md` — Shared-access deployment on a HiPerGator login host

This guide documents how to run the GIGANTIC data server in **local execution
mode on a HiPerGator login host** so that **any user in the Moroz lab group**
(not just the SLURM job owner) can reach it via standard SSH tunnel.

For canonical SLURM-mode operation, single-user access, and the publishing
workflow, see [`AI_GUIDE.md`](AI_GUIDE.md). The login-node pattern in this
file is a **deliberate alternative** to the canonical SLURM mode — used when
shared access by multiple group members is required and outweighs the
caveats listed at the bottom.

---

## Why this pattern exists

The default `execution_mode: "slurm"` runs the server on a SLURM compute
node. HiPerGator policy enforces (via the `pam_slurm_adopt` PAM module) that
**only users who own a SLURM job on that compute node can SSH to it.** Group
membership and shared allocations do not override this — they share
filesystem access, not SSH access.

Symptom: a lab PI or collaborator running

```bash
ssh -J USERNAME@hpg.rc.ufl.edu -L 9456:localhost:9456 USERNAME@<compute-node>
```

gets `Permission denied (publickey)` or a `pam_slurm_adopt: access denied
because you have no active jobs on this node` error, while the job owner's
identical command succeeds.

**Switching to `--execution local` on a login host sidesteps the policy:**
the login host accepts SSH from any UF user with HiPerGator credentials, and
`-L`-style port forwarding within the SSH session never traverses the
login↔compute network boundary.

---

## Prerequisite code change

This pattern depends on the threading fix in
`ai/gigantic_server.py` that landed 2026-06-19:

```python
# Threaded server: each request runs in its own thread so one slow
# request (or a stuck client mid-read) can't freeze the whole server.
socketserver.ThreadingTCPServer.allow_reuse_address = True
socketserver.ThreadingTCPServer.daemon_threads = True
with socketserver.ThreadingTCPServer( ( '', server.port ), handler_cls ) as httpd:
```

Without this, single-threaded `socketserver.TCPServer` freezes the whole
server when one request blocks (slow disk, hung client, etc.) — recurring
hangs after only hours of uptime. If the file is reverted to plain
`TCPServer`, the freeze problem will return regardless of which execution
mode is used.

---

## Paths and constants

| Item | Value |
|---|---|
| Server directory | `/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/server/` |
| Start script | `RUN-start_server.sh` (in server dir) |
| Server source | `ai/gigantic_server.py` |
| Config | `START_HERE-server_config.yaml` |
| Server port | `9456` (from YAML `port:`) |
| Chosen login host | `login7.ufhpc` (login7–11 are equivalent; login7 picked for stability) |
| Logs | `logs/local_login7_<TIMESTAMP>.log` (gitignored via `.gitignore`) |

Leave `execution_mode: "slurm"` in the YAML for canonical default; the
local-mode runs override at the command line with `--execution local`. The
YAML stays untouched as the version-controlled canonical configuration.

---

## Implementation procedure

### Step 1 — Stop any existing GIGANTIC servers

```bash
# Cancel any SLURM-mode server jobs
squeue -u $USER -n gigantic
# scancel <jobid>   # if any are listed

# Kill any local-mode server processes on every login host
for n in 7 8 9 10 11; do
    HOST="login${n}.ufhpc"
    ssh -o BatchMode=yes -o ConnectTimeout=3 "$HOST" \
        "pkill -f gigantic_server.py 2>/dev/null; echo \$HOSTNAME done" 2>/dev/null
done
```

### Step 2 — Start the server on login7 detached via nohup

```bash
SERVER=/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/server
TS=$( date +%Y%m%d_%H%M%S )
LOGFILE="${SERVER}/logs/local_login7_${TS}.log"

ssh -o BatchMode=yes -o ConnectTimeout=5 login7.ufhpc \
    "cd '$SERVER' && nohup bash RUN-start_server.sh --execution local > '$LOGFILE' 2>&1 & disown; echo started"
```

Why `nohup ... & disown`: the SSH connection closes after the command
returns, but `nohup` + `disown` detaches the server process so it survives
the SSH session ending. `tmux` would be cleaner but is not installed on
HiPerGator login hosts.

### Step 3 — Wait for cache build, then verify HTTP 200

The server prints `Building initial directory tree cache...` at startup
and walks every subproject's `upload_to_server/` tree. This can take
20–90 seconds depending on tree size and disk responsiveness. Poll until
responsive:

```bash
until ssh -o BatchMode=yes -o ConnectTimeout=3 login7.ufhpc \
    "timeout 3 curl -sS -o /dev/null -w '%{http_code}' http://localhost:9456/ 2>/dev/null | grep -q 200" 2>/dev/null; do
    sleep 5
done

# Confirm
ssh -o BatchMode=yes -o ConnectTimeout=5 login7.ufhpc \
    "ps -ef | grep gigantic_server | grep -v grep | head -2
     echo ---
     ss -tlnp 2>/dev/null | grep :9456
     echo ---
     curl -sS -o /dev/null -w 'HTTP %{http_code} in %{time_total}s\n' http://localhost:9456/"
```

Expected: a Python process running `gigantic_server.py`,
`LISTEN 0 5 0.0.0.0:9456`, and `HTTP 200 in ~0.001s`.

---

## User-facing tunnel pattern (works for everyone in the group)

```
ssh -L 9456:login7.ufhpc:9456 USERNAME@hpg.rc.ufl.edu
```

Then in browser:

```
http://localhost:9456/
```

### Why this tunnel works

- `hpg.rc.ufl.edu` is the public-DNS round-robin gateway. Duo + password
  auth, available to any UF user with HiPerGator credentials.
- The user lands on some login host (variable).
- `-L 9456:login7.ufhpc:9456` forwards the user's local port 9456 to
  `login7:9456` **from the SSH server's perspective** — intra-cluster TCP
  between login hosts on port 9456 is unrestricted.
- No `ProxyJump`, no `pam_slurm_adopt`, no SSH keys needed beyond standard
  HiPerGator login.
- Identical command shape for every lab member; only `USERNAME` changes.

### Why other patterns fail

| Pattern | Why it fails |
|---|---|
| `ssh -L 9456:localhost:9456 USERNAME@login7.rc.ufl.edu` | `login7.rc.ufl.edu` does not resolve in public DNS |
| `ssh -J USERNAME@hpg.rc.ufl.edu -L 9456:localhost:9456 USERNAME@login7.ufhpc` | HiPerGator policy: login-to-login SSH requires publickey-only auth, no password fallback. Most users haven't set up internal SSH keys. |
| `ssh -J USERNAME@hpg.rc.ufl.edu -L 9456:localhost:9456 USERNAME@<compute-node>` (SLURM mode) | `pam_slurm_adopt` denies users who don't own a job on the compute node. |
| `ssh -L 9456:localhost:9456 USERNAME@hpg.rc.ufl.edu` when server is on `login7` and round-robin lands you on `login9` | `localhost:9456` on login9 isn't the server. The target hostname matters. |

---

## Caveats and known issues

1. **HiPerGator admins may kill long-running processes on login nodes.**
   This deployment violates the spirit of login-host etiquette. Expect
   uptimes measured in days, not weeks. The proper fix is **UF Open
   OnDemand** (separate support-ticket conversation with UF Research
   Computing — see `https://help.rc.ufl.edu/`). Until OnDemand is set up,
   restarting is the operational reality.

2. **`login7.ufhpc` does NOT resolve from outside HiPerGator's network.**
   That's why the tunnel command uses `hpg.rc.ufl.edu` as the SSH endpoint
   and `login7.ufhpc` only as the forwarded-target hostname (resolved
   server-side by SSH).

3. **The login host is variable for users.** `hpg.rc.ufl.edu` round-robins
   among login7–12. As long as the user's landing login host can route TCP
   to `login7:9456` (it can — login hosts share the same subnet), the
   tunnel works regardless of which login host they land on.

4. **The server's initial directory-tree cache build is the slowest startup
   step.** First HTTP response can take 20–90 seconds after process start.
   The `until` polling loop in Step 3 handles this.

5. **The threading fix is a hard requirement.** Reverting
   `ai/gigantic_server.py` to single-threaded `socketserver.TCPServer`
   reintroduces freezes after hours of uptime regardless of mode.

---

## Quick-restart one-liner

For repeated restarts after the threading fix is in place:

```bash
SERVER=/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/server
TS=$( date +%Y%m%d_%H%M%S )
ssh login7.ufhpc "pkill -f gigantic_server.py; sleep 2; cd '$SERVER' && nohup bash RUN-start_server.sh --execution local > '${SERVER}/logs/local_login7_${TS}.log' 2>&1 & disown; echo started"
```

Then wait ~30–90 seconds and verify with the `until ... curl ...` poll loop
from Step 3.

---

## When to use which mode

| Mode | Use when… |
|---|---|
| `execution_mode: "slurm"` (canonical, see `AI_GUIDE.md`) | Single-user access by the job owner is sufficient; long uptime (weeks) desired; no admin-policy risk. |
| `--execution local` on a login host (this guide) | Multiple lab members need access; uptimes of days are acceptable; willing to restart after admin sweeps. |
| **UF Open OnDemand** (future, not yet set up) | Production: stable, multi-user, policy-compliant. Requires a support ticket to configure GIGANTIC as an OnDemand app. |

---

## Relationship to other docs

- **`AI_GUIDE.md`** — canonical operation guide (SLURM mode, publishing
  workflow, troubleshooting). Read first for project orientation.
- **`README.md`** — user-facing overview.
- **`START_HERE-server_config.yaml`** — server configuration (canonical
  values; not modified by this guide).
- **`ai/gigantic_server.py`** — server implementation; the threading
  prerequisite lives here.

This guide adds a deployment alternative, not a replacement. The canonical
SLURM mode remains the default and the documented expectation.
