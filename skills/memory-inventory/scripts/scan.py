#!/usr/bin/env python3
"""Structural + claim scan of a Claude Code memory dir. Read-only.

usage: scan.py <memory_dir> [--repo <git_repo_path>] [--json]

Reports: MEMORY.md size vs load limit, orphans (files not linked from MEMORY.md),
broken links, and per-file PR/issue refs with live gh state (when --repo given).
"""
import json, os, re, subprocess, sys
from datetime import date

LIMIT_LINES, LIMIT_BYTES = 200, 25 * 1024  # what Claude loads from MEMORY.md at session start
MIN_REF_DIGITS, MAX_REF_DIGITS, GH_LIST_LIMIT = 2, 5, 2000
# words that mean "not finished" — a file containing these AND only MERGED/CLOSED refs is a suspect
PENDING = re.compile(r"未\s*deploy|deploy\s*未|未実施|未適用|未マージ|残\s*=|待ち|進行中|WIP|TODO|next\s*=|次\s*=", re.I)
REF = re.compile(r"(?:PR|pr|issue|#)\s*#?(\d{2,5})")
LINK = re.compile(r"\]\(([^)\s]+\.md)\)")


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
    return fm


def gh_states(repo):
    """{number: 'MERGED'|'OPEN'|'CLOSED'} for PRs and issues, one gh call each."""
    out = {}
    for kind in ("pr", "issue"):
        try:
            raw = subprocess.check_output(
                ["gh", kind, "list", "--state", "all", "--limit", str(GH_LIST_LIMIT), "--json", "number,state"],
                cwd=repo, stderr=subprocess.DEVNULL, text=True)
            for it in json.loads(raw):
                out.setdefault(it["number"], f"{kind}:{it['state']}")
        except Exception as e:  # gh missing / not a gh repo — report, don't die
            out.setdefault("_error", str(e))
    return out


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    repo = args[args.index("--repo") + 1] if "--repo" in args else None
    positional = [a for a in args if not a.startswith("--") and a != repo]
    if not positional:
        sys.exit(__doc__)
    mem = os.path.abspath(positional[0])
    if not os.path.isdir(mem):
        sys.exit(f"memory dir not found: {mem}")
    if repo and not os.path.isdir(repo):
        sys.exit(f"repo dir not found: {repo}")
    index_path = os.path.join(mem, "MEMORY.md")
    index = open(index_path, encoding="utf-8").read() if os.path.exists(index_path) else ""
    linked = set(LINK.findall(index))
    files = sorted(f for f in os.listdir(mem) if f.endswith(".md") and f != "MEMORY.md")
    states = gh_states(repo) if repo else {}

    report = {
        "memory_dir": mem,
        "index": {"lines": index.count("\n") + 1, "bytes": len(index.encode()),
                  "over_limit": index.count("\n") + 1 > LIMIT_LINES or len(index.encode()) > LIMIT_BYTES},
        "orphans": [f for f in files if f not in linked],
        "broken_links": sorted(l for l in linked if not os.path.exists(os.path.join(mem, l))),
        "gh_error": states.get("_error"),
        "files": [],
    }
    for f in files:
        text = open(os.path.join(mem, f), encoding="utf-8").read()
        fm = frontmatter(text)
        mtime = date.fromtimestamp(os.path.getmtime(os.path.join(mem, f))).isoformat()
        refs = sorted({int(n) for n in REF.findall(text)})
        ref_states = {n: states.get(n, "?") for n in refs}
        pending = bool(PENDING.search(text))
        all_done = bool(refs) and all(s.endswith(("MERGED", "CLOSED")) for s in ref_states.values())
        report["files"].append({
            "file": f, "type": fm.get("type", "?"), "modified": (fm.get("modified") or mtime)[:10],
            "orphan": f not in linked, "refs": ref_states, "pending_words": pending,
            "suspect": pending and all_done,
        })

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=1)); return

    i = report["index"]
    print(f"# memory scan {date.today()} — {mem}\n")
    print(f"MEMORY.md: {i['lines']} lines / {i['bytes']} bytes (limit {LIMIT_LINES} lines or {LIMIT_BYTES} bytes){' ⚠ OVER' if i['over_limit'] else ''}")
    print(f"files: {len(files)}  orphans: {len(report['orphans'])}  broken links: {len(report['broken_links'])}")
    if report["gh_error"]: print(f"gh: unavailable ({report['gh_error']})")
    if report["broken_links"]:
        print("\n## broken links (MEMORY.md → missing file)"); print("\n".join(f"- {b}" for b in report["broken_links"]))
    if report["orphans"]:
        print("\n## orphans (not linked from MEMORY.md — invisible at session start)"); print("\n".join(f"- {o}" for o in report["orphans"]))
    sus = [x for x in report["files"] if x["suspect"]]
    if sus:
        print("\n## suspects (says pending, but every referenced PR/issue is MERGED/CLOSED)")
        for x in sus:
            print(f"- {x['file']} (modified {x['modified']}) refs={x['refs']}")
    unk = [x for x in report["files"] if x["pending_words"] and not x["refs"]]
    if unk:
        print("\n## pending without refs (needs manual check against repo/git log)")
        print("\n".join(f"- {x['file']} (modified {x['modified']})" for x in unk))
    print("\n## by type")
    from collections import Counter
    for t, c in Counter(x["type"] for x in report["files"]).most_common(): print(f"- {t}: {c}")


if __name__ == "__main__":
    main()
