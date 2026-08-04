<!--
Source:
  - https://docs.tensorlake.ai/filesystems/introduction.md
  - https://docs.tensorlake.ai/filesystems/core-concepts.md
  - https://docs.tensorlake.ai/filesystems/filesystem-mounts.md
  - https://docs.tensorlake.ai/filesystems/read-only-mounts.md
  - https://docs.tensorlake.ai/filesystems/manage-sessions.md
  - https://docs.tensorlake.ai/filesystems/concurrent-writes.md
  - https://docs.tensorlake.ai/filesystems/distribute-files.md
  - https://docs.tensorlake.ai/filesystems/architecture.md
  - https://docs.tensorlake.ai/git/introduction.md
  - https://docs.tensorlake.ai/git/git-repositories.md
  - https://docs.tensorlake.ai/git/workspace-mounts.md
  - https://docs.tensorlake.ai/git/repository-sdks.md
  - https://docs.tensorlake.ai/git/merging.md
  - https://docs.tensorlake.ai/git/authentication.md
  - https://docs.tensorlake.ai/git/store-generated-code.md
SDK version: tensorlake 0.5.97
Last verified: 2026-08-04
-->

# TensorLake Cloud Volumes and Git Repositories

Two durable storage surfaces that outlive any single sandbox, and are mounted into one as an ordinary directory:

- **Cloud Volumes** (a.k.a. versioned file systems, `tl fs`) — a shared, versioned directory. Autosave publishes to a **single linear timeline** that every mount converges on. No commits, no branches.
- **Git repositories** (`tl git`) — managed Git repositories with branches, server-side merges, and private per-agent workspaces. Autosave is **private** until you snapshot and promote.

**Pick by publication policy:** if concurrent writers should see each other's work automatically, use a Cloud Volume. If work must stay private until an explicit publish step (review before landing, long-lived divergence, conflict resolution), use a Git repository workspace.

They share the mount client, the crash-safe local journal, and lazy content delivery, but store history in **two different engines**. Volumes have **no Git access** — no commits, refs, branches, packs, or Git wire protocol.

For sandbox lifecycle, snapshots, and pools see [sandbox_persistence.md](sandbox_persistence.md); for running commands in a sandbox see [sandbox_sdk.md](sandbox_sdk.md).

## Table of Contents

- [Cloud Volumes (Versioned File Systems)](#cloud-volumes-versioned-file-systems)
  - [Vocabulary](#vocabulary)
  - [Quickstart](#quickstart)
  - [Mount Modes](#mount-modes)
  - [Autosave, Snapshots, and Retention](#autosave-snapshots-and-retention)
  - [Session Management](#session-management)
  - [Push a Folder Without Mounting](#push-a-folder-without-mounting)
  - [Concurrent Writes](#concurrent-writes)
  - [Mounting Inside a Sandbox](#mounting-inside-a-sandbox)
  - [Distributing Files to Agent Fleets](#distributing-files-to-agent-fleets)
  - [`tl fs` CLI Reference](#tl-fs-cli-reference)
- [Git Repositories](#git-repositories)
  - [Git or the tl CLI?](#git-or-the-tl-cli)
  - [Quickstart](#quickstart-1)
  - [Authentication and Credentials](#authentication-and-credentials)
  - [Repository Mounts](#repository-mounts)
  - [Snapshot, Promote, Rebase](#snapshot-promote-rebase)
  - [Merging and Conflicts](#merging-and-conflicts)
  - [Workspace Observability and Retention](#workspace-observability-and-retention)
  - [Repository SDKs](#repository-sdks)
  - [`tl git` CLI Reference](#tl-git-cli-reference)
- [Architecture Notes](#architecture-notes)

---

# Cloud Volumes (Versioned File Systems)

Cloud Volumes are directories that can be mounted on one or more sandboxes. All writes are automatically saved to durable storage asynchronously, with SSD-grade write performance; reads are cached and fetched lazily or pre-fetched from remote storage. Directories can be snapshotted for point-in-time checkpoints and time-travelled to restore state at a given time.

They are **portable**: usable on any sandbox provider, on AWS/GCP/Azure, on Kubernetes containers, and mountable on any Linux or macOS machine.

Documented use cases:

- Version an agent's working state without teaching it version control
- Persist a long-running session so a crashed sandbox loses nothing
- Share one file system across several coding agents at once — disjoint work merges automatically
- Distribute documents, skills, and tools to fleets of agents with read-only mounts

## Vocabulary

1. A **file system** is the durable, versioned store: one shared timeline.
2. A **mount** gives a sandbox an ordinary directory backed by it. The mount path is ephemeral; reads stream in lazily, so mounting is fast regardless of how much the file system holds.
3. A **session** is the state behind one writable mount — which checkpoint it started from, plus a crash-safe local journal for changes that have not reached the server yet. Sessions survive unmounts and sandbox crashes.
4. An **autosave checkpoint** is a durable, shared recovery point. Settled changes replicate through a per-session server WAL automatically. The server verifies and applies each acknowledged checkpoint to the shared timeline before returning success.
5. A **permanent snapshot** marks a changed generation as a permanent, billed retention point, kept until you delete it.
6. **Publishing:** every acknowledged autosave checkpoint advances the shared timeline, and other mounts converge automatically. **There is no separate promote step on the file system surface.**
7. **Retained files** — after a checkpoint publishes, the mount keeps local copies as a byte cache so reads stay local and future autosaves stay incremental. They're already durable; the cache only costs local disk.

## Quickstart

```bash
curl -fsSL https://tensorlake.ai/install | sh
tl login
```

**Create a file system:**

```bash
$ tl fs create agent-scratch
Created filesystem agent-scratch (empty).
  mount it: tl fs mount agent-scratch <path>
  or push a folder: tl fs push <dir> agent-scratch
```

```python
from tensorlake.filesystem import FilesystemClient

client = FilesystemClient()
fs = client.create("agent-scratch")
```

```typescript
import { FilesystemClient } from "tensorlake";

const client = new FilesystemClient();
const fs = await client.create("agent-scratch");
```

**Mount it:**

```bash
$ tl fs mount agent-scratch /work
Mounted filesystem agent-scratch at /work (session 54398548341c, saves publish automatically)
Autosave: settled changes replicate in about 1s (5s max while continuously writing).
```

```python
from pathlib import Path

# Tilde paths are NOT expanded by the SDK; pass a resolved path.
mount = fs.mount(str(Path.home() / "work"))
# or, from the client: mount = client.mount("agent-scratch", "/work")
```

```typescript
import { homedir } from "node:os";
import { join } from "node:path";

// Tilde paths are NOT expanded by the SDK; pass a resolved path.
const mount = await fs.mount(join(homedir(), "work"));
// or: const mount = await client.mount("agent-scratch", "/work");
```

**Work in it.** The mount is a normal POSIX-compliant directory. The SDKs can also write **without mounting** — they use the remote file system's HTTP API directly:

```bash
$ echo "hypothesis: the parser is quadratic" > /work/notes.md
$ mkdir /work/results && cp bench.json /work/results/
```

```python
fs.write_file("notes.md", "hypothesis: the parser is quadratic\n")
```

```typescript
await fs.writeFile("notes.md", "hypothesis: the parser is quadratic\n");
await fs.writeFile("results/bench.json", await readFile("bench.json"));
```

**Snapshot a checkpoint:**

```bash
$ tl fs snapshot /work -m "baseline benchmarks"
Snapshot 4d9a2f7e "baseline benchmarks" — kept until deleted.
```

```python
mount.snapshot("baseline benchmarks")
```

```typescript
await mount.snapshot("baseline benchmarks");
```

**Resume elsewhere.** The mount path is disposable; the session behind it is durable:

```bash
$ tl fs mount agent-scratch /work2
Resumed session 54398548341c
```

From **another** machine you recover everything through the last autosave checkpoint — typically seconds of work at most; anything written since the last checkpoint stays on the machine that wrote it. Remounting on the **same** machine can additionally recover a detached session's unsaved local changes from its overlay.

> **macOS needs a one-time file-system extension install. Linux needs no setup.**
>
> ```bash
> tl fs setup --check
> tl fs setup
> ```

## Mount Modes

Every mode uses the same command shape:

```bash
tl fs mount <filesystem>[:<snapshot-or-autosave-id>] <path>
```

| Mode | Command | Use it for |
|---|---|---|
| **Writable** (start here) | `tl fs mount agent-scratch /work` | Agents creating or modifying files; autosaves become durable automatically |
| **Read-only, following** | `tl fs mount agent-scratch /skills --ro` | Shared skills, prompts, docs, configs, assets |
| **Read-only, pinned** | `tl fs mount agent-scratch:<snapshot-id> /release --ro` | Reproducible builds, evals, fixed releases |

```python
mount = client.mount("agent-scratch", "/work")                      # writable
mount = client.mount("agent-assets", "/skills", readonly=True)      # read-only
```

```typescript
const mount = await client.mount("agent-scratch", "/work");         // writable
const ro = await client.mount("agent-assets", "/skills", true);     // read-only (3rd positional arg)
```

**Following vs pinned read-only.** A *following* mount tracks the file system's current state and refreshes as replicated autosaves or permanent snapshots land — when the shared timeline advances, only changed paths refresh and unchanged files keep their warm cache. A *pinned* mount resolves a specific snapshot or retained autosave once and never changes.

| Need | Use |
|---|---|
| Every run must see the same files | Pinned read-only mount |
| Many sandboxes should receive updates without image rebuilds | Following read-only mount |
| An agent needs to write files | Writable mount |

Use a **permanent snapshot** when a pinned input must remain available indefinitely. A recent autosave can also be pinned, but it is an ephemeral recovery point and may age out of retention — don't use autosave IDs as long-lived release anchors.

> Remounting a file system this machine has a **detached** session for resumes that session, unsaved local changes included. A session **already mounted elsewhere** mounts read-only — unmount it there first to take writes.

## Autosave, Snapshots, and Retention

**Autosave is always on for writable mounts.** Changes normally reach the shared timeline about **750 ms** after they settle plus upload/server time; a continuously-writing agent checkpoints **at least every 5 seconds**. The server does not acknowledge a checkpoint until verification and shared-head publication complete.

**Autosave retention:** autosave checkpoints are ephemeral. Tensorlake retains the **newest 256** generations and **all generations from at least the most recent 24 hours**, then truncates older entries automatically. They appear under `Recent autosave WAL` in `tl fs history`.

**Permanent snapshots** are billed storage, structurally exempt from automatic expiry, and remain until you delete them. `tl fs snapshot /work -m "..."` returns only after the durable snapshot receipt exists — you can safely unmount as soon as the command succeeds.

> **Snapshotting a clean mount is a quiet no-op.** It does **not** promote an existing autosave into a second permanent record. A snapshot only marks a generation *with new changes* as permanent.

Browse both kinds of history together:

```bash
$ tl fs history agent-scratch
Autosave WAL (fixed native_fs_v1): each checkpoint is synchronously replicated to the shared drive; keep the newest 256 generations and all generations from the last 24h. Snapshots are permanent until you delete them.

Snapshots (permanent — kept until deleted)
4d9a2f7e  baseline benchmarks  1h ago

Recent autosave WAL (ephemeral — truncated automatically)
8b21f6a9  2m ago
e3f421a7  3h ago
```

Delete a permanent snapshot with `tl fs delete-snapshot agent-scratch <snapshot-id>`.

## Session Management

**Check status:**

```bash
$ tl fs status /work
filesystem: agent-scratch
session: 54398548341c (created 12m ago)
mode: writable — every save becomes the filesystem's current state
autosave: settled changes replicate in about 1s (5s max while continuously writing)
last autosave: 2m ago
permanent snapshots: 1
daemon: serving save 8b21f6a9
log: ~/.local/share/tensorlake/mounts/54398548341c.../daemon.log
local: clean
```

```python
status = client.mount_status("/work")     # or mount.status()
print(status.filesystem, status.mounted)
```

```typescript
const status = await client.mountStatus("/work");   // or mount.status()
console.log(status.filesystem, status.mounted);
```

`local: clean` means the local journal has no changes waiting for autosave. With unsaved changes, status lists dirty paths:

```bash
local: 2 change(s):
  M src/parser.py
  D src/old_parser.py
```

Two more lines appear as a session ages:

- `retained:` — files already published and kept locally as the byte cache. Durable already; the local copies only make reads and future autosaves fast. `tl fs snapshot --clear` trims cache entries covered by that snapshot while preserving later writes and ignored files.
- `ignored:` — local-only files that never enter an autosave or snapshot (build output and the like, per the file system's ignore rules).

Add `--json` for machine-readable output; the SDK's `MountStatus.raw` carries the same structured payload.

**List sessions / file systems:**

```bash
$ tl fs ls agent-scratch
Session        Filesystem      Base       Saves   Mode         Mounted   Age
54398548341c   agent-scratch   e3f421a7   yes     publishing   /work     12m
```

`tl fs ls` with no argument lists your file systems.

**Unmount (keeps the session by default):**

```bash
$ tl fs unmount /work
Unmounted /work. Session 54398548341c kept — `tl fs mount agent-scratch <path>` resumes it.
```

```python
mount.unmount()              # or client.unmount("/work")
mount.unmount(discard=True)  # throw away unsaved changes and ignored files under the mount
```

```typescript
await mount.unmount();       // or await client.unmount("/work");
await mount.unmount(true);   // discard
```

Everything already published is untouched — autosave checkpoints and snapshots are immutable.

**Restore (time travel):**

```bash
$ tl fs restore /work 4d9a2f7e5b3d8c6a4f2e0d9b7c5a3f1e8d6b4c2a1029384756abcdef01234567
Restored /work to 4d9a2f7e (12 file(s) refreshed, 1 removed).
```

You can restore to any autosave still inside the retention window or to any permanent snapshot. **Restore does not rewrite history** — it changes the working directory, and the next autosave records the restored state. Restoring over local changes requires `--discard`; snapshot first if they should survive permanently.

**Repair a session:**

```bash
$ tl fs doctor /work --json
```

If a session's local state is inconsistent (a hard sandbox kill mid-write, an interrupted resume), `tl fs doctor` inspects and can repair the local journal. **Unmount first** — doctor operates on a detached session and never contacts the server, so it cannot run under a live mount. Pass `--repair-journal` to rebuild a damaged local journal; add `--base <SNAPSHOT_OR_AUTOSAVE_ID>` (or `--base empty`) to re-point the session's base as part of that repair (`--base` requires `--repair-journal`). Durable history is never modified.

**Delete a file system:**

```bash
$ tl fs rm agent-scratch
Delete filesystem agent-scratch and all of its history? This cannot be undone. [y/N]
```

```python
client.delete("agent-scratch")
```

```typescript
await client.delete("agent-scratch");
```

Pass `-f` to skip the confirmation; the SDK clients delete without prompting. Deletion removes the file system, its history, and its sessions.

## Push a Folder Without Mounting

When you just want a directory's contents in a file system:

```bash
$ tl fs push ./results agent-scratch -m "run 42 results"
Pushed ./results to agent-scratch (14 file(s)).
```

- Pushing the same directory again uploads **only what changed** — the right shape for a CI job or release service.
- Passing `-m` on a changed push creates a **permanent snapshot**; without it, the push creates an ephemeral autosave checkpoint.
- A push with no changes is a quiet no-op.
- Pushes honor `.gitignore`, preserve symlinks, and preserve executable bits on regular files. A file system has **no special `.git` handling** — only `.gitignore` governs exclusions.

## Concurrent Writes

Several mounts can write to one file system at once. Autosave sends each mount's settled work through its session WAL; before acknowledging a checkpoint the server orders that update and applies its changed paths to the file system's single shared timeline.

- **Disjoint changes merge automatically.** Updates touching different paths (or different files in the same directory) reconcile cleanly and never notice each other. Two agents writing `sessions/a/` and `sessions/b/` both land in full, with no coordination and no conflict.
- **Same-path writes are last-writer-wins.** The later server-ordered checkpoint wins; the earlier writer's change to that file is overwritten **silently**. There are no conflict markers and nothing to resolve — a file system is a shared disk, not a set of branches.

**Making concurrency safe:**

- **Give each agent or task its own subtree** (`sessions/<id>/`, `users/<id>/`). This is the natural shape for agent workloads and eliminates same-path contention entirely.
- **Treat shared files as append-only or single-owner.** If one file must be written by many agents, funnel writes through one of them, or have each write its own file and merge at read time.
- **Wait for settled-write replication, not an explicit snapshot.** A small quiet edit normally reaches the shared head in about a second plus upload time; continuous writers flush at least every 5 seconds. Following mounts refresh after that checkpoint commits — they do **not** see bytes still sitting in another mount's open local batch.

If you need private work with an explicit publication step, or genuine branch divergence with conflict resolution, use a [Git repository workspace](#repository-mounts) instead.

## Mounting Inside a Sandbox

A sandbox guest needs one scoped credential to attach a file system:

```bash
$ tl fs token agent-scratch
```

The command prints the credential and the environment recipe for the guest. Inside the sandbox, the same `tl fs mount` commands work unchanged.

`tl login` stores a Tensorlake CLI credential, and `tl fs` commands mint and refresh the short-lived credentials they need automatically — including inside sandboxes. **You only handle credentials yourself on the Git surface.**

## Distributing Files to Agent Fleets

Pattern for shared manuals, skills, configs, test fixtures, and binary tools:

1. Store shared files in a versioned file system.
2. Publish updates from outside the sandbox with `tl fs push` (no sandbox, no mount needed on the producer side).
3. Mount the file system into agents read-only at a predictable path.
4. **Follow** the file system for automatic distribution, or **pin** a permanent snapshot for fixed releases.

Keep the layout simple and stable:

```text
agent-assets/
  manuals/
  skills/
  bin/
  configs/
```

Agents then refer to `/opt/agent-assets/manuals/operator.md`, `/opt/agent-assets/skills/research/SKILL.md`, `/opt/agent-assets/bin/validator`, etc.

```bash
tl fs create agent-assets
tl fs push ./agent-assets agent-assets -m "publish agent assets"
tl fs mount agent-assets /opt/agent-assets --ro
```

New sandboxes read the current state; running following mounts refresh as the shared timeline advances, so updated manuals, skills, configs, and tools appear **without rebuilding sandbox images**. Agents should write outputs to a **separate writable mount** so shared assets stay read-only and identical for everyone.

**Binary tools:** put them under a stable directory such as `bin/` with the executable bit set, then push — executable bits are preserved.

```bash
chmod +x agent-assets/bin/validator
tl fs push ./agent-assets agent-assets -m "add validator tool"
# agents call it directly:
/opt/agent-assets/bin/validator --input /work/result.json
```

> If you need **named release channels** (`stable`, `canary`) that you advance deliberately, back the assets with a [Git repository](#git-repositories) and use branches as channels — that's the surface built for explicit publication.

## `tl fs` CLI Reference

```bash
tl fs setup [--check]                        # one-time macOS file-system extension install
tl fs create <filesystem>                    # create an empty file system
tl fs ls                                     # list your file systems
tl fs ls <filesystem>                        # list a file system's sessions
tl fs mount <filesystem> <path>              # writable mount
tl fs mount <filesystem> <path> --ro         # read-only, following
tl fs mount <filesystem>:<snapshot-id> <path> --ro   # read-only, pinned
tl fs unmount <path> [--discard]             # unmount (keeps session unless --discard)
tl fs status <path> [--json]                 # session state, dirty/retained/ignored counts
tl fs history <filesystem>                   # permanent snapshots + recent autosave WAL
tl fs snapshot <path> -m "message" [--clear] # permanent snapshot (--clear trims retained cache)
tl fs delete-snapshot <filesystem> <id>      # remove a permanent snapshot
tl fs restore <path> <id> [--discard]        # time-travel the mount to a snapshot or autosave
tl fs push <dir> <filesystem> [-m "msg"]     # push a directory without mounting
tl fs doctor <path> [--json] [--repair-journal] [--base <ID>|empty]
tl fs token <filesystem>                     # mint a scoped guest credential for a sandbox
tl fs rm <filesystem> [-f]                   # delete file system, history, and sessions
```

---

# Git Repositories

Managed Git repositories built for agents: disaggregated Git infrastructure that scales to tens of millions of repositories and absorbs hundreds of thousands of pushes per second. **Merges run server-side and cost is proportional to changed paths, not repository size.**

Documented use cases:

- Store code and assets produced by coding agents, one repository per generated project
- Give agents a durable Git history with branches, merges, and activity attribution
- Create repositories at product scale from your control plane with the SDKs
- Mount a repository as a live directory in a sandbox, without cloning it first
- Track durable workspace checkpoints, snapshots, branch activity, and mount liveness from the control plane

## Git or the tl CLI?

Both work against the same repository. **Which one you use depends on what is on disk in front of you:**

- **You cloned** (`git clone`) → use ordinary Git. A clone is a real checkout with a `.git` directory and Tensorlake is a normal remote. Commit, rebase, merge, and push exactly as you would anywhere.
- **You mounted** (`tl git mount`) → use the `tl git` verbs. **A mount has no `.git` and Git commands do not run inside it.**
- **You have no files at all** (a control plane, CI, an SDK caller) → use `tl git merge` and the SDKs. Merges, preflights, and conflict queries run server-side without any checkout.

| Git habit on a clone | Equivalent on a mount |
|---|---|
| `git commit` | `tl git snapshot` |
| `git fetch` / switch a pristine view | `tl git sync` |
| `git rebase origin/main` | `tl git rebase` |
| `git push` | `tl git promote` |
| `git status` / `git log` | `tl git status` / `tl git log` |

The two sides always converge through the repository: a promoted workspace is a normal commit that `git fetch` sees, and a `git push` shows up in mounts on their next refresh or sync.

## Mental Model

1. A **repository** stores the durable Git history.
2. A **mount** gives a sandbox an ephemeral directory backed by the repository, **no clone required**. Writable by default; `--ro` gives a stateless read-only view of a branch, a pinned commit, or a subtree of a monorepo.
3. The shared **local journal** records writes crash-safely. Autosave publishes them to a durable private **workspace WAL** — creating no commit and moving no branch.
4. A **workspace** is created **lazily on the first remote WAL checkpoint** and holds an agent's isolated state.
5. A **snapshot** materializes the current WAL as a Git commit on the workspace.
6. **Promotion** publishes a workspace snapshot to a branch. **Rebase** replays a workspace onto a moved branch, server-side.
7. The control plane can observe mount liveness and durable workspace operations. The unsealed local edit tail stays in the sandbox until autosave.

Durable published history lives in the repository branch; durable in-progress work lives in each workspace's WAL and snapshot chain; the sandbox holds the lazy mount plus the newest unsealed local edit tail.

## Quickstart

```bash
curl -fsSL https://tensorlake.ai/install | sh
tl login
```

**Create a repository:**

```bash
$ tl git create agent-outputs --default-branch main
created https://git.tensorlake.ai/project_9f3c2a1b/agent-outputs
```

```python
from tensorlake import RepositoryClient

with RepositoryClient.from_env() as repos:
    repo = repos.create("agent-outputs", default_branch="main")
    print(repo.url)
```

```typescript
import { RepositoryClient } from "tensorlake";

const repos = await RepositoryClient.fromEnv();
const repo = await repos.create("agent-outputs", { defaultBranch: "main" });
console.log(repo.url);
```

`project_9f3c2a1b` is the project your `tl` login is scoped to — you do not pass it to every command. You can also create a repository **lazily by pushing** to a repository path that does not exist yet; lazy creation applies to `git push` only (`git clone` and `git fetch` require the repository to already exist).

**Commit and push with plain Git:**

```bash
$ TOKEN=$(tl git token --repo agent-outputs --json | jq -r .token)
$ git clone https://t:$TOKEN@git.tensorlake.ai/project_9f3c2a1b/agent-outputs
$ cd agent-outputs
$ echo "# Agent Outputs" > README.md
$ git add README.md && git commit -m "initial app" && git push origin main
```

On a fresh machine Git needs an identity first: `git config user.name "..."` and `git config user.email "..."`.

**Or push a worktree from your application:**

```python
report = repos.push_worktree(
    "agent-outputs",
    root="./initial-app",
    branch="main",
    message="initial app",
)
print(report.commit)
```

```typescript
const report = await repos.pushWorktree("agent-outputs", {
  path: "./initial-app",
  branch: "main",
  message: "initial app",
});
console.log(report.commit);
```

**Mount, edit, snapshot, promote:**

```bash
$ tl git mount agent-outputs /work
Mounted writable agent-outputs at /work (workspace 3f9a2b7e1c4d activates on the first WAL checkpoint)
$ printf "\n## Parser Notes\n" >> /work/README.md
$ tl git snapshot /work -m "add notes"
Snapshot 8b21f6a9c3d5e7f1a2b4c6d8e0f3a5b7c9d1e3f5 (1 file(s), 1 of 1 chunks uploaded)
$ tl git promote /work main
Promoted workspace 3f9a2b7e1c4d -> main at 1c4d9a2f7e5b3d8c6a4f2e0d9b7c5a3f1e8d6b4c (squashed)
```

Autosave already protects the mounted file state in the workspace's durable private WAL. Snapshotting materializes that state as a Git commit; **the branch is unchanged until promotion.** After promotion, new mounts, `git clone`, and `git fetch` all see the same files.

> **macOS needs a one-time file-system extension install. Linux needs no setup.**
>
> ```bash
> tl git setup --check
> tl git setup
> ```

## Authentication and Credentials

Two layers:

| Layer | What it is | Used by |
|---|---|---|
| Tensorlake CLI/API auth | Your account, API key, or personal access token. Authorizes calls to Tensorlake. | `tl login`, `tl git`, API clients |
| Git credential | A short-lived credential minted for repository access. Authorizes repository operations. | `git clone`, `git push`, SDK calls, `tl git` mounts |

**Your CLI/API credential is never sent to Git.** Tensorlake uses it to mint a Git credential, then Git clients and mounts use that against the repository service. Tensorlake authenticates Git operations with **HTTP Basic Auth, not SSH keys**.

```bash
$ tl git token --repo agent-outputs
project: project_9f3c2a1b
repo: agent-outputs
username: t
password: eyJhbGciOiJFUzI1NiJ9... (truncated)
expires: 2026-07-07T13:00:00Z
scopes: git:read, git:write
```

**The Git username is always `t`; the password is the token.**

```python
credential = repos.credential("agent-outputs")
print(credential.git_username)   # always "t"
print(credential.token)          # use as the Git HTTP password
```

```typescript
const credential = await repos.credential("agent-outputs");
console.log(credential.gitUsername, credential.token);
```

Credential fields: `gitUsername`, `token`, `expiresAt`, `repoPattern`, `scopes`.

**Use it with Git** — credential store, or embedded in the URL for scripts and CI:

```bash
git config --global credential.helper store
git clone https://git.tensorlake.ai/project_9f3c2a1b/agent-outputs
# Username: t   Password: <paste the token>

# or
TOKEN=$(tl git token --repo agent-outputs --json | jq -r .token)
git clone https://t:$TOKEN@git.tensorlake.ai/project_9f3c2a1b/agent-outputs
git remote set-url origin https://t:$TOKEN@git.tensorlake.ai/project_9f3c2a1b/agent-outputs
```

**Treat a token in a URL or credential store as a secret** — it expires automatically, but should not be committed, logged, or shared.

**Scopes:**

| Scope | Grants |
|---|---|
| `git:read` | Clone, fetch, and read-only mount |
| `git:write` | Push, snapshot, and promote. Implies `git:read`. |
| `repo:write` | Create, fork, delete, archive, and restore repositories |
| `project:read` | List and read every repository in the project. Implies `git:read`. |
| `project:admin` | Project administration, workspace fleet management, quotas, and operation history. Implies `project:read` and `git:read`. |

`tl git token --repo <repo>` mints `git:read` + `git:write` **for that repository only** — enough to clone, push, snapshot, and promote, but it cannot create, delete, or list other repositories, manage keys, or revoke tokens.

**Token lifetime is one hour by default.** Mint a new one with `tl git token --repo <repo>` when it expires. `tl git` mounts handle this automatically: the CLI caches fresh credentials and a running mount daemon rotates its credential before expiry.

> **PATs are CLI-only. Use an API key with the SDKs** (`export TENSORLAKE_API_KEY=tlk_...`).

## Repository Mounts

A mount gives a sandbox a live directory backed by a repository, **without cloning it**. Attach takes about a second regardless of repository size; file content streams in as processes read it, and unopened content never transfers.

Command shape:

```bash
tl git mount <repo>[:<ref-or-full-commit>][//<subpath>] <path> [--ro] [--workspace <id>] [--publish]
```

| Mount | Command | Use it for |
|---|---|---|
| **Writable** (default) | `tl git mount agent-outputs /work` | An agent editing privately before promotion; workspace activates on first autosave |
| Read-only branch view | `tl git mount agent-outputs /code --ro` | Read a repository at the moving branch tip |
| Read-only pinned commit | `tl git mount agent-outputs:<full-commit> /release --ro` | Fixed inputs, reproducible builds, agent context |
| Read-only subtree | `tl git mount agent-outputs:main//services/auth /code --ro` | One directory of a monorepo |
| Resume a workspace | `tl git mount agent-outputs /work --workspace 3f9a2b7e1c4d` | Reattach an existing workspace on another machine |
| Publish on snapshot | `tl git mount agent-outputs:main /work --publish` | Every explicit snapshot also promotes to the branch; autosaves stay private |

**Writable mounts.** `/work` is an ordinary writable directory based on the branch tip; name a different base with `agent-outputs:<ref-or-full-commit>`. Writes enter a crash-safe local journal and autosave to private server WAL; **the branch does not change while the agent works.** Workspace mounts can take a subtree too; snapshots record paths relative to the repository root.

**Autosave WAL.** Writable mounts autosave **every 30 seconds**. Each autosave uploads changed content and advances the workspace's durable WAL checkpoint, but **creates no Git commit and moves no branch**. This is the recovery layer for an agent run: another machine can resume through the latest server checkpoint, while the same machine can additionally recover a newer unsealed tail from its local journal.

**Read-only mounts** create no workspace and need no cleanup. A read-only branch mount follows the branch — when it moves, only changed paths refresh. Reads are always consistent: a file open when the branch moves keeps serving the version it was opened against. **Pinning takes a full commit id, not an abbreviation.** Subtree and commit forms combine: `agent-outputs:9f2a1c8e...//services/auth`.

**Reattach a workspace.** The mount path is disposable; the workspace is the resumable state behind it:

```bash
$ tl git unmount /work
Unmounted /work. Workspace 3f9a2b7e1c4d kept.
$ tl git mount agent-outputs /work2 --workspace 3f9a2b7e1c4d
Mounted workspace 3f9a2b7e1c4d (agent-outputs) at /work2, resumed at its last durable checkpoint
```

A workspace **already mounted elsewhere** mounts read-only if you mount it again — unmount it there first to take writes.

**Delete a workspace** while unmounting when its history is no longer needed:

```bash
$ tl git unmount /work --delete
Unmounted /work (workspace 3f9a2b7e1c4d deleted).
```

The workspace WAL and unpublished snapshots become unreachable. Promote first if the work should survive as branch history.

### What a mount is *not*

- **Not a Git checkout.** No `.git` directory; `git` commands do not run there. `tl git clone` exists when you need a real clone.
- **Not auto-publishing.** Autosave never creates a commit or changes a branch. For a shared directory whose autosaves periodically advance the common state, use a [Cloud Volume](#cloud-volumes-versioned-file-systems).
- **Not fully offline.** Cached content and the crash-safe local journal can remain usable during a disconnection, but fetching uncached content and making work remotely durable require reconnection.

## Snapshot, Promote, Rebase

**Snapshot** seals any pending local changes, then materializes the resulting WAL state as **one commit on the workspace**. It is a deliberate history boundary, not the first point of durability. Snapshotting with no changes is a no-op (`Nothing to snapshot: workspace is clean.`).

```bash
$ tl git snapshot /work -m "implemented parser and tests"
Snapshot 8b21f6a9c3d5e7f1a2b4c6d8e0f3a5b7c9d1e3f5 (14 file(s), 14 of 14 chunks uploaded)
```

**Promote** is the deliberate path to a branch. Before landing it autosaves and materializes any dirty WAL, then lands the workspace as a **squashed** commit. **Compare-and-swap safety prevents a plain promotion from overwriting a branch that moved.** Add `--merge` to land a two-parent merge instead.

```bash
$ tl git promote /work main
Promoted workspace 3f9a2b7e1c4d -> main at 1c4d9a2f... (squashed)

$ tl git promote /work main --merge
Promoted workspace 3f9a2b7e1c4d -> main at 7a1c3e5b... (merge)
```

Activity history records who published the promotion and which workspace it came from.

**Rebase** replays the workspace onto a target ref or commit for a linear history; the mounted directory updates in place. The **target is required** — rebase onto any branch, tag, or full commit. The daemon seals pending local WAL first, then the replay runs server-side. After a clean rebase, promotion fast-forwards. `--fail-on-conflict` reports conflicts without materializing markers into the workspace.

```bash
$ tl git rebase /work main
Rebased workspace 3f9a2b7e1c4d onto main at 9c4e2a7b1f3d (3 snapshot(s) replayed).
```

**Sync** has a narrower role than rebase: `tl git sync /work [<ref-or-full-commit>]` refreshes the current source or switches a **read-only or snapshot-free writable** view, carrying any unsnapshotted WAL tail onto the new base. It **refuses** a switch that would rewrite an established workspace snapshot chain and directs you to `tl git rebase`. Use sync for checkout-like source changes before a workspace has snapshot history; use rebase once workspace commits must be replayed onto another base.

**Status:**

```bash
$ tl git status /work
repository: agent-outputs
state: workspace_snapshotted_unpromoted
source: refs/heads/main
commit: 8b21f6a9c3d5
workspace: 3f9a2b7e1c4d
base: 9c4e2a7b1f3d
snapshot: 8b21f6a9c3d5
target: main
relationship: ahead
local changes: 0 path(s)
next: tl git promote <BRANCH>
next: tl git rebase <REF-OR-COMMIT>
```

With unsealed changes, status reports `state: workspace_locally_dirty`, how many paths are dirty, and `next: tl git snapshot`. Status names every in-between state a workspace can reach (behind its branch, mid-rebase with unresolved markers, attached elsewhere) together with the command that exits it. `--json` for machine-readable output.

## Merging and Conflicts

Two situations:

- **A workspace and its branch both changed** → needs a mounted workspace. The loop is: **rebase onto the branch → fix conflicts → snapshot the resolution → promote.**
- **Two branches diverged** → `tl git merge` merges them directly on the server: no mount, no clone, no working copy.

**Tensorlake never force-overwrites a branch.** If a merge cannot land cleanly, nothing is published unless you explicitly choose a mode that materializes conflict markers.

**When promotion conflicts,** nothing is published — the target branch and workspace stay unchanged and each conflicted path is reported:

```bash
$ tl git promote /work main --merge
error: promote to main conflicts on 2 path(s); nothing was published:
  content        src/parser.py
  delete_modify  notes/plan.md
```

**Conflicted rebase** writes standard Git **diff3** markers into the workspace files (branch version, merge base, workspace version):

```text
<<<<<<< main
def parse(text: str) -> Ast:
||||||| base
def parse(text):
=======
def parse(text, *, strict=False):
>>>>>>> workspace 3f9a2b7e1c4d
```

Edit to resolve, then `tl git snapshot /work -m "resolve parser conflict"` and `tl git promote /work main --merge`.

**Merge branches directly.** Preflight never writes:

```bash
$ tl git merge agent-outputs main dev --preflight
merge base: 5f2c8e1a9b3d
changed paths: 12
Clean merge.

$ tl git merge agent-outputs main dev --preflight --deep   # exact text-merge results
$ tl git merge agent-outputs main dev -m "land dev"        # land it
```

A **shallow** preflight reports same-file collisions as *potential* conflicts; `--deep` gives exact content-merge answers. A conflicted direct merge **publishes nothing and exits non-zero**; `--materialize` lands it anyway with markers plus a structured conflict record. `--json` for machine-readable reports.

**Structured conflict records.** A merge that materializes conflicts (a `--materialize` direct merge or a conflicted rebase) records more than markers: each conflicted commit carries a record naming every path and the three-way terms it was merged from, queryable without parsing file contents:

```bash
$ tl git conflicts agent-outputs 7a1c3e5b9d2f
ours: 4b6d8e0a2c4f
theirs: 9c4e2a7b1f3d
base: 5f2c8e1a9b3d
conflicts: 1 path(s):
  content        src/parser.py
```

Nothing is silently overwritten — both sides of every conflict remain reachable from the record.

**Conflict kinds:**

| Kind | Meaning |
|---|---|
| `content` | Both sides edited the same region of a text file. |
| `delete_modify` | One side deleted the path; the other modified it. **The modified side is kept.** |
| `add_add` | Both sides added the path with different content. |
| `kind_mismatch` | The path is a file on one side and a directory or symlink on the other. |
| `mode` | Both sides changed the file mode to different values. |
| `too_large` | A side is binary or over the text-merge size limit; never text-merged. |

Merges run server-side with a three-way merge engine — no clone, no working-tree checkout, no full-repo scan. **Cost scales with the number of changed paths, not total repository size.**

In a **clone**, none of this applies: use ordinary `git merge`, `git rebase`, and `git push`. Tensorlake adds no pull-request layer; merge locally then push. A non-fast-forward push is rejected — pull, resolve, push again.

## Workspace Observability and Retention

Durable workspace state is server-side, so you can inspect a fleet without touching its sandboxes:

```bash
tl git workspaces agent-outputs     # workspace WAL, snapshot, and attachment state

$ tl git smartlog agent-outputs
main            1c4d9a2f  parser and tests               2m ago
├─ 3f9a2b7e1c4d  8b21f6a9  implemented parser and tests   ahead 1
├─ 7d4c1e9b2a6f  5e3a7c1d  refactor config loader         ahead 2
└─ b2e8f4a6c0d1  (no snapshots)                           at base
```

`tl git log` shows one mount's own workspace snapshot chain; `tl git smartlog --project` widens the view to the whole project. Every snapshot, promote, rebase, and merge is a durable entry in the repository's activity history — the audit trail of what your agents did, queryable long after the sandboxes are gone.

Live mounts report a **liveness heartbeat** (that a mount exists, where it's mounted, that it's still alive) so the control plane can tell which sessions are active. **Fine-grained edits remain local until autosave** — the control plane observes durable checkpoints, not every keystroke.

Available to the control plane: which repositories exist, which branches changed, which workspaces are live / detached / resumable, which durable WAL checkpoints and snapshots each agent created, which paths changed in a snapshot, and which principal pushed, promoted, merged, or reconciled changes.

**Retention.** Detached workspaces are collected automatically by lifecycle tier: a **WAL-only** workspace defaults to **48 hours**, a workspace **with snapshots** to **14 days**, and an actively mounted workspace is retained. These periods are deployment configuration — use explicit deletion when your application requires deterministic cleanup.

## Repository SDKs

`RepositoryClient` is the entry point. Use it for control-plane work: create repositories, inspect refs, mint credentials, push worktrees, run server-side merges. Use the `tl git` mount family for mounted workflows.

```python
from tensorlake import RepositoryClient

with RepositoryClient.from_env() as repos:
    repo = repos.create("agent-outputs", default_branch="main")
    for item in repos.list():
        print(item.name, item.default_branch, item.status)

    info = repos.info("agent-outputs")
    print(info.url)
    for branch in info.branches:
        print(branch.name, branch.oid)
```

```typescript
import { RepositoryClient } from "tensorlake";

const repos = await RepositoryClient.fromEnv();
const repo = await repos.create("agent-outputs", { defaultBranch: "main" });

for (const item of await repos.list()) {
  console.log(item.name, item.defaultBranch, item.status);
}

const info = await repos.info("agent-outputs");
for (const branch of info.branches) {
  console.log(branch.name, branch.oid);
}
```

**Push a local worktree** — creates one commit from a local directory and updates a branch. It skips `.git`, honors `.gitignore`, preserves symlinks, and preserves executable bits on regular files:

```python
report = repos.push_worktree(
    "agent-outputs",
    root=".",
    branch="main",
    message="sync generated output",
    expect_oid=None,   # pass the current oid to fail if the branch moved
)
print(report.commit, report.ref_name)
```

```typescript
const report = await repos.pushWorktree("agent-outputs", {
  path: process.cwd(),
  branch: "main",
  message: "sync generated output",
  expectOid: undefined,
});
console.log(report.commit, report.refName);
```

Guard against clobbering newer work by reading the current oid first:

```python
info = repos.info("app-7f3c2a1b")
current = next(b.oid for b in info.branches if b.name == "main")
report = repos.push_worktree("app-7f3c2a1b", root="./generated-app",
                             branch="main", message="update homepage", expect_oid=current)
```

**Merge branches** without cloning — preflight, then land:

```python
report = repos.merge("agent-outputs", "main", "feature", preflight=True, deep=True)

if report.clean:
    landed = repos.merge("agent-outputs", "main", "feature", message="merge feature into main")
    print(landed.commit)
else:
    for conflict in report.conflicts:
        print(conflict.kind, conflict.path)
```

```typescript
const report = await repos.merge("agent-outputs", "main", "feature", {
  preflight: true,
  deep: true,
});

if (report.clean) {
  const landed = await repos.merge("agent-outputs", "main", "feature", {
    message: "merge feature into main",
  });
}
```

By default a conflicted commit-mode merge **publishes nothing** and returns a report with `clean: false` and no `commit`. Use `materialize` to land conflicted files with standard Git diff3 markers, then query the record:

```python
report = repos.merge("agent-outputs", "main", "feature", materialize=True,
                     message="merge feature into main")
if report.commit and not report.clean:
    record = repos.commit_conflicts("agent-outputs", report.commit)
    for path in (record.paths if record else []):
        print(path.kind, path.path)
```

### API Surface

| Task | Python | TypeScript |
|---|---|---|
| Create a repository | `create(repo, default_branch=None)` | `create(repo, { defaultBranch })` |
| List repositories | `list()` | `list()` |
| Delete a repository | `delete(repo)` | `delete(repo)` |
| Fork a repository | `fork(repo, base_repo)` | `fork(repo, baseRepo)` |
| Archive or restore | `archive(repo)`, `restore(repo)` | `archive(repo)`, `restore(repo)` |
| Repository URL | `url(repo)` | `url(repo)` |
| Branches and refs | `info(repo)`, `branches(repo)`, `refs(repo)` | `info(repo)`, `branches(repo)`, `refs(repo)` |
| Delete a branch | `delete_branch(repo, branch)` | `deleteBranch(repo, branch)` |
| Operation history | `operations(repo)` | `operations(repo)` |
| Git credential | `credential(repo=None)` | `credential(repo)` |
| Push local files | `push_worktree(repo, root, branch, message, expect_oid=None)` | `pushWorktree(repo, { path, branch, message, expectOid })` |
| Push job status | `commit_status(repo, job_id)` | `commitStatus(repo, jobId)` |
| Merge branches | `merge(repo, ours, theirs, ...)` | `merge(repo, ours, theirs, options)` |
| Conflict records | `commit_conflicts(repo, commit)` | `commitConflicts(repo, commit)` |

Note the Python/TypeScript asymmetry in `push_worktree`: Python takes `root=`, TypeScript takes `path:`.

### Scale Pattern: Agent-Generated Code

One repository per generated app, site, package, or user project. A repository is the durable unit for a user project; a **mount** is the ephemeral filesystem path for one sandbox; a **workspace** is the isolated snapshot history for one agent run.

Mounting does not copy the repository into the sandbox — content is fetched as processes read it, autosave persists changed content into private workspace WAL, and snapshots materialize deliberate commits without forcing every run to become one large final commit. Use **branches** for product states (`main`, `preview`, `release`) and **workspaces** for in-progress agent attempts. Use stable repository names such as an internal app ID so human-facing names can change without changing the storage identity.

| Need | Use |
|---|---|
| New user app or project | Create a repository |
| Agent edits an existing app | Mount `main` (writable by default) |
| Long-running generation | Rely on autosave for recovery; snapshot meaningful commit boundaries |
| User accepts a result | Promote the workspace to the project branch |
| Backend writes generated code or docs | Repository SDK `push_worktree` |
| Prevent overwriting newer work | `expect_oid` / `expectOid` |
| Inspect what agents did | Workspace status, snapshots, operations, and branch activity |
| Build or deploy generated code | Ordinary `git clone`, `git fetch`, or a read-only mount |

## `tl git` CLI Reference

```bash
tl git setup [--check]                       # one-time macOS file-system extension install
tl git create <repo> [--default-branch main] # create a repository
tl git token --repo <repo> [--json]          # mint a short-lived Git credential (username is always `t`)
tl git clone <repo> <path>                   # real Git clone (has a .git directory)
tl git mount <repo>[:<ref-or-full-commit>][//<subpath>] <path> [--ro] [--workspace <id>] [--publish]
tl git unmount <path> [--delete]             # keeps the workspace unless --delete
tl git status <path> [--json]                # workspace state + next valid transition
tl git log <path>                            # this mount's workspace snapshot chain
tl git snapshot <path> -m "message"          # materialize WAL as a workspace commit
tl git promote <path> <branch> [--merge]     # land the workspace on a branch (squashed by default)
tl git rebase <path> <ref-or-commit> [--fail-on-conflict]
tl git sync <path> [<ref-or-full-commit>]    # refresh/switch a read-only or snapshot-free view
tl git merge <repo> <ours> <theirs> [--preflight] [--deep] [--materialize] [-m "msg"] [--json]
tl git conflicts <repo> <commit>             # structured conflict record
tl git workspaces <repo>                     # WAL, snapshot, and attachment state across the fleet
tl git smartlog <repo> [--project]           # branches, tags, workspaces, snapshot chains
```

---

# Architecture Notes

Tensorlake separates **metadata** from **file content**:

- The **control plane** stores history metadata — for repositories: Git commits, refs, branches, and private workspace WAL checkpoints; for file systems: native content-addressed snapshots and per-session checkpoint journals — plus sessions, workspaces, and operation history.
- The **data plane** stores file content in blob storage (Git objects for repositories, content-addressed blobs for file systems).
- Mounts resolve metadata through the control plane and fetch file content **lazily** from the data plane.

This split keeps session creation, snapshot listing, and history fast even when a file system or repository is large. A session or workspace is metadata, not a full copy: it records what it belongs to, the point it started from, and its durable WAL or snapshot chain. Saving uploads only changed content. Optimization, deduplication, retention, and garbage collection run in the background so agents never wait on storage maintenance.

**One local journal, two publication policies.** Writable file-system and repository mounts share one crash-safe client pipeline (file writes → local journal → upload changed content → server WAL checkpoint). The difference is what happens at the checkpoint:

- **`tl fs`** — the server verifies, orders, and applies each autosave checkpoint to the shared drive **before acknowledging it**. `tl fs snapshot` adds a permanent retention point. There is no promote step.
- **`tl git`** — autosave checkpoints remain **private workspace WAL**: no Git commit, no branch update. `tl git snapshot` materializes the WAL as a workspace commit, and `tl git promote` deliberately lands it on a branch.

**Reconciling concurrent writes.** File systems have **one linear timeline**: racing checkpoints are ordered by the server, which rebases each update's changed paths onto the current head before acknowledging. Cost is proportional to changed paths, not file-system size. Disjoint paths merge; same-path writes are last-writer-wins, silently. There is no three-way merge and no conflict marker on a file system.

Repositories can have **divergent branches**, so they use a server-side three-way merge engine (verified against Git's merge behavior) for promote, `git merge`, and rebase. Two conflict behaviors apply: **Fail** (the default for promotion — nothing lands, a structured conflict report is returned) and **Materialize** (Git conflict markers plus a queryable conflict record). Both preserve the losing content in Git history.

**Content delivery.** Mounting does not copy anything into the sandbox: the mount resolves the tree, then fetches content lazily as processes read paths. Large repositories mount quickly, a sandbox only downloads paths it actually reads, and many sandboxes can mount the same repository without one shared serving path becoming the bottleneck. Following read-only mounts add branch tracking: when the followed branch moves, Tensorlake compares old and new commits and invalidates only changed paths, so unchanged files keep their warm page cache.
