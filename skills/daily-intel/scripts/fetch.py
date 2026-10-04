#!/usr/bin/env python3
"""Fetch RSS/Atom feeds, dedup against a seen-state file, emit a raw digest markdown.

Stdlib only (certifi is used for SSL certs if installed — python.org builds on macOS need it).
Deterministic layer of daily-intel: no LLM here, just collection.
Usage:
  python3 fetch.py feeds.txt [--days 2] [--max 15] [--out DIR] [--state FILE]
  python3 fetch.py --selftest
"""
import argparse, gzip, json, os, ssl, sys, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ATOM = "{http://www.w3.org/2005/Atom}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) daily-intel/0.1"}


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        return parsedate_to_datetime(s)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def parse_feed(xml_bytes, source_url):
    """Return [(title, link, datetime|None, summary)] from RSS 2.0 or Atom."""
    root = ET.fromstring(xml_bytes)
    out = []
    items = root.iter("item")  # RSS
    for it in items:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        date = parse_date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date"))
        desc = (it.findtext("description") or "")[:300]
        if title and link:
            out.append((title, link, date, desc))
    if not out:  # Atom
        for e in root.iter(f"{ATOM}entry"):
            title = (e.findtext(f"{ATOM}title") or "").strip()
            link = ""
            for l in e.findall(f"{ATOM}link"):
                if l.get("rel") in (None, "alternate") and l.get("href"):
                    link = l.get("href")
                    break
            date = parse_date(e.findtext(f"{ATOM}updated") or e.findtext(f"{ATOM}published"))
            desc = (e.findtext(f"{ATOM}summary") or "")[:300]
            if title and link:
                out.append((title, link, date, desc))
    return out


def _ssl_context():
    try:  # python.org builds on macOS ship without bootstrapped certs; certifi fixes it
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


SSL_CTX = _ssl_context()


def fetch_one(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        body = r.read()
    if body[:2] == b"\x1f\x8b":  # deepmind.google gzips even without Accept-Encoding
        body = gzip.decompress(body)
    return body


def load_state(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def save_state(path, state):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    state = {k: v for k, v in state.items() if v >= cutoff}  # ponytail: prune >90d; grow state file forever if this ever hurts
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(state, indent=0))


def selftest():
    rss = b"""<rss><channel><item><title>Hello</title><link>http://x/1</link>
    <pubDate>Sat, 04 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>"""
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>World</title>
    <link rel="alternate" href="http://x/2"/><updated>2026-10-04T00:00:00Z</updated></entry></feed>"""
    r = parse_feed(rss, "t")
    a = parse_feed(atom, "t")
    assert r and r[0][0] == "Hello" and r[0][2].year == 2026, r
    assert a and a[0][0] == "World" and a[0][1] == "http://x/2", a
    assert parse_date("garbage") is None
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feeds", nargs="?")
    ap.add_argument("--days", type=float, default=2.0, help="only entries newer than this")
    ap.add_argument("--max", type=int, default=15, help="max entries per feed")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--state", default=os.path.expanduser("~/.daily-intel/seen.json"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.feeds:
        ap.error("feeds file required")

    feeds = []
    for line in Path(args.feeds).read_text().splitlines():
        line = line.split("#")[0].strip()
        if line:
            feeds.append(line)

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda u: (u, _safe_fetch(u)), feeds))

    state = load_state(args.state)
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# Raw intel {today}", ""]
    new_urls, failed = [], []
    for url, res in results:
        if res is None:
            failed.append(url)
            continue
        try:
            entries = parse_feed(res, url)
        except ET.ParseError as e:
            failed.append(f"{url} (parse: {e})")
            continue
        fresh = [e for e in entries
                 if e[1] not in state and (e[2] is None or e[2] >= cutoff)]
        fresh.sort(key=lambda e: e[2] or cutoff, reverse=True)
        if not fresh:
            continue
        lines.append(f"## {url}")
        for title, link, date, _desc in fresh[: args.max]:
            d = date.strftime("%m-%d") if date else "??"
            lines.append(f"- [{d}] {title} <{link}>")
            new_urls.append(link)
        lines.append("")
    if failed:
        lines += ["## FAILED feeds (agent: supplement via web search)",
                  *[f"- {u}" for u in failed], ""]
    for u in new_urls:
        state[u] = datetime.now(timezone.utc).isoformat()
    save_state(args.state, state)

    out = Path(args.out) / f"intel-raw-{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(out)


def _safe_fetch(url):
    try:
        return fetch_one(url)
    except Exception as e:
        print(f"WARN {url}: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    main()
