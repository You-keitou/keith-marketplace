---
name: memory-inventory
license: MIT
description: "Audit and clean up Claude Code auto-memory (~/.claude/projects/*/memory/). Verifies stale claims like 'not deployed yet' or 'remaining: X' against gh, git and deploy logs, finds orphan files missing from MEMORY.md and broken links, and archives instead of deleting. Use whenever the user wants to inventory, audit, prune, consolidate or compress their Claude memory or MEMORY.md, says memory 'is lying' or 'feels stale', or complains MEMORY.md is too long or truncated. Not for editing CLAUDE.md, project docs, or the memory of other tools."
metadata:
  author: "keith <youkeitou327@gmail.com>"
  version: "0.1.0"
  tags: "claude-code, memory, maintenance, audit"
---

# memory-inventory

## Purpose

At session start Claude reads only **the first 200 lines / 25 KB of MEMORY.md**. Topic files exist only if MEMORY.md links to them. Left alone, memory rots in three ways:

1. **Lies** — a file says "PR opened, not deployed" but it was merged and deployed weeks ago. The next session plans around a false premise (e.g. re-applies a migration).
2. **Orphans** — files nobody linked from MEMORY.md. They are never read; the effort that wrote them is lost.
3. **Overflow** — MEMORY.md past 200 lines or 25 KB gets truncated at the tail, so the newest entries are the ones that silently disappear. Bytes overflow before lines when entries are dense.

## Instructions

### 0. Pick the target and back it up

```bash
ls -d ~/.claude/projects/*/memory          # candidates
MEM=~/.claude/projects/<project>/memory
cp -r "$MEM" "$(dirname "$MEM")/memory-backup-$(date +%Y%m%d-%H%M%S)"
```

Default to the current project's memory. If asked to sweep everything, go largest-first; small dirs rarely need an inventory.

### 1. Scan (read-only)

```bash
python3 <skill dir>/scripts/scan.py "$MEM" --repo <path to the project's git repo>
```

Sections: `broken links`, `orphans`, `suspects` (a file uses pending words — "not deployed", "remaining", "waiting", "WIP" — while every PR/issue it references is MERGED/CLOSED), and `pending without refs` (pending words but nothing machine-checkable). `--json` for machine output; omit `--repo` for structure-only.

**Suspects are a lead list, not a verdict.** Expect most to be false positives — "remaining = next spec" is a correct, still-open statement even when the PRs it cites are merged. On a mature project 60 suspects may contain 2 real lies. Never bulk-apply anything to the suspect list.

### 2. Verify each suspect against reality

The scan only knows PR/issue state. Merged ≠ deployed, and PR numbers can be stale after a history rewrite. Open the file and check the specific claim:

- **"Not deployed" / "migration not applied"** — find the project's deploy record: a deploy log (`docs/history/deploy-log.*`), spec handoff docs (`specs/*/handoff.md`), release tags, CI deploy runs. Cite the line that proves it.
- **"Remaining: X"** — is there an open issue for X? Does the code contain it (`rg`)?
- **"Waiting on <person>"** — grep later memory files; the answer is often recorded elsewhere.
- **PR merged but the change is absent from `main`** — check whether the repo was force-pushed/cut over after that PR. A MERGED PR from a replaced history is not evidence the code exists.
- **`pending without refs`** — read it; compare its date to today. "In progress" from two months ago is usually done, but say so as a guess, not a finding.

If you cannot verify a claim, label it **unverifiable** and hand it to the user. "Looks old" is not evidence.

### 3. Propose by category, get approval per category

Present one category at a time, least risky first, so the user can approve in chunks:

| Category | Default action |
|---|---|
| Broken links | Delete the MEMORY.md line |
| Orphans that are finished / superseded by repo docs | Move to `_archive/` |
| Orphans that still carry live knowledge | Add a one-line link in MEMORY.md |
| Verified lies | Rewrite the claim; keep the lesson, drop or fix the status |
| `type: feedback` (check frontmatter, not filename) | **Leave alone.** Working-style guidance rarely rots. If two contradict, keep the newer |
| MEMORY.md near the limit (report bytes and lines) | Compress finished-project lines to one line each, or drop them |

Format each item as: `file — current claim → reality (evidence) → action`. Apply only what the user approved. If the user pre-approved everything ("just do it"), still list what you changed and what you deliberately left alone.

### 4. Apply

- Never delete. `mv` into `$MEM/_archive/YYYY-MM-DD/` and append removed MEMORY.md lines to `MEMORY.removed.md` in the same folder, so the change is reversible.
- Edit claims in place. Keep the *why* (lesson, trap, decision); remove or freeze the *status* (PR numbers, deployed/not). Status rots; lessons don't.
- Leave accurate pending entries untouched even if the scan flagged them.
- Re-run `scan.py` afterwards and show 0 orphans / 0 broken links / MEMORY.md within limits.

### 5. Report

```
# memory-inventory <project> <date>
- before: N files / MEMORY.md L lines, B bytes, orphans O, suspects S
- after:  N' files / L' lines, B' bytes, orphans 0
- archived: [...]   rewritten: [...]   links added: [...]
- left as-is (verified accurate): [...]
- unverifiable (user to confirm): [...]
- backup: <path>
```

## Examples

**Propose only** — "Inventory the memory for toyomart, don't change anything yet": run steps 0–3, write the categorized proposal, stop.

**Pre-approved cleanup** — "Memory feels stale, just clean it up": run all steps; the report must still list what was verified accurate and left alone.

**Single question** — "Is the 'deploy pending' note for spec 112 still true?": skip the scan, go straight to step 2 for that one file, answer with the evidence line.

## Available scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/scan.py` | Read-only structural + claim scan; prints a markdown report | `<memory_dir> [--repo <git repo>] [--json]` |

## Prerequisites

- Python 3 (stdlib only).
- `gh` CLI authenticated for the target repo, if you want PR/issue state. Without it (or without `--repo`) the scan still reports orphans, broken links, and size; it just cannot flag suspects.

## Limitations

- The scan matches pending words by regex (Japanese and English); it cannot read intent. Treat `suspects` as leads.
- PR/issue state comes from `gh` for the repo's `origin`; monorepos with several remotes or rewritten history need manual checking.
- Nothing here talks to production. "Deployed" must be proven from the repo's own records (deploy log, handoff docs, tags).

## Troubleshooting

Error handling: `scan.py` exits non-zero with a one-line message when the memory or repo dir is missing; a failing `gh` call is reported in the report header (`gh: unavailable`) instead of aborting, so structural results still print.

- `gh: unavailable` in the scan header → `gh auth status`, or run without `--repo` and verify claims by hand.
- `memory dir not found` → confirm the path with `ls -d ~/.claude/projects/*/memory`; project dirs are the absolute path with `/` replaced by `-`.
- Scan shows 0 suspects on a project you know is stale → the files have no PR numbers; read `pending without refs` instead.

## Cadence

Monthly, or after ~15 new/updated memory files. Running `scan.py` in a SessionStart hook and only watching the orphan count is a cheap early warning.
