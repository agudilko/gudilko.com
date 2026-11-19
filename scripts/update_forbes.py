#!/usr/bin/env python3
"""Refresh the Forbes article lists on gudilko.com.

Reads the Forbes Technology Council author page, merges what it finds into
data/forbes.json, then rewrites the two marked blocks in index.html:
"Most read on Forbes" (top 3 by views) and "Latest" (everything else, newest
first). If Forbes cannot be read or the result looks wrong, nothing changes.

Usage:
  python3 scripts/update_forbes.py              fetch, merge, render
  python3 scripts/update_forbes.py --render     render from data/forbes.json only
"""
import datetime as dt
import html
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "forbes.json"
PAGE = ROOT / "index.html"
AUTHOR_URL = "https://www.forbes.com/councils/forbestechcouncil/people/alexgudilko/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
ART = re.compile(r"forbes\.com/(?:sites|councils)/forbestechcouncil/((\d{4})/(\d{2})/(\d{2})/[a-z0-9-]+)")
FONT = "'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
TOP_N = 3
KEEPALIVE_DAYS = 30


def fetch():
    req = urllib.request.Request(AUTHOR_URL, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read().decode("utf-8", "replace")


def to_int(v):
    digits = re.sub(r"[^\d]", "", str(v))
    return int(digits) if digits else None


def parse(page):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        raise ValueError("Forbes page layout changed: no data block found")
    found = {}

    def walk(node):
        if isinstance(node, dict):
            if "pageViews" in node and isinstance(node.get("title"), str):
                url = next((v for v in node.values() if isinstance(v, str) and ART.search(v)), None)
                if url:
                    key = ART.search(url).group(1)
                    found[key] = {
                        "key": key,
                        "url": url.split("?")[0].replace("/sites/forbestechcouncil/", "/councils/forbestechcouncil/"),
                        "title": html.unescape(node["title"]).strip(),
                        "date": "-".join(key.split("/")[:3]),
                        "views": to_int(node["pageViews"]),
                    }
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(json.loads(m.group(1)))
    return found


def tidy(title):
    """House style for display: no em dashes, straight apostrophes."""
    t = re.sub(r"\s*[—–]\s*", ", ", title)
    return t.replace("’", "'").replace("‘", "'")


def merge(store, fresh):
    by_key = {a["key"]: a for a in store["articles"]}
    changed = False
    for key, new in fresh.items():
        old = by_key.get(key)
        if old is None:
            new["display_title"] = tidy(new["title"])
            store["articles"].append(new)
            changed = True
            print(f"new article: {new['title']}")
            continue
        if new["views"] is not None and new["views"] != old.get("views"):
            old["views"] = new["views"]
            changed = True
        if new["title"] != old.get("title"):
            old["title"] = new["title"]
            changed = True
    return changed


def top_row(a):
    y, mo, _ = a["date"].split("-")
    return (
        f'<a href="{html.escape(a["url"])}" target="_blank" rel="noopener" style="flex: 1 1 320px; min-width: 0; text-decoration: none; background: #15171A; border: 1px solid #26292E; color: #F2F3F1; border-radius: 10px; padding: 28px; display: flex; flex-direction: column; gap: 20px; justify-content: space-between; min-height: 240px; box-sizing: border-box">\n'
        f'<div style="display: flex; flex-direction: column; gap: 12px">\n'
        f'<div style="font-family: {FONT}; font-size: 14px; color: #C2C7CC">Forbes / {MONTHS[int(mo) - 1]} {y}</div>\n'
        f'<div style="font-family: {FONT}; font-weight: 600; font-size: 24px; line-height: 1.2">{html.escape(a.get("display_title") or a["title"], quote=False)}</div>\n'
        f'</div>\n'
        f'<div style="font-family: {FONT}; font-size: 15px; color: #FFFFFF">{a["views"]:,} views</div>\n'
        f'</a>\n')


def latest_row(a):
    y, mo, d = a["date"].split("-")
    return (
        f'<a href="{html.escape(a["url"])}" target="_blank" rel="noopener" style="text-decoration: none; display: flex; flex-wrap: wrap; gap: 4px 32px; align-items: baseline; padding: 18px 0; border-top: 1px solid #26292E">\n'
        f'<div style="flex: 0 0 150px; font-family: {FONT}; font-size: 14px; color: #8F97A0">{MONTHS[int(mo) - 1]} {int(d)}, {y}</div>\n'
        f'<div style="flex: 999 1 420px; min-width: 0; font-family: {FONT}; font-weight: 600; font-size: 20px; line-height: 1.3">{html.escape(a.get("display_title") or a["title"], quote=False)}</div>\n'
        f'<div style="flex: 0 0 auto; font-size: 15px; color: #8F97A0">Forbes</div>\n'
        f'</a>\n')


def render(store):
    arts = store["articles"]
    ranked = sorted(arts, key=lambda a: (-(a.get("views") or 0), a["date"]))
    top = [a for a in ranked if a.get("views")][:TOP_N]
    top_keys = {a["key"] for a in top}
    rest = sorted((a for a in arts if a["key"] not in top_keys), key=lambda a: a["date"], reverse=True)
    page = PAGE.read_text(encoding="utf-8")
    out = page
    for name, block in (("top", "".join(map(top_row, top))), ("latest", "".join(map(latest_row, rest)))):
        pat = re.compile(rf"(<!--forbes:{name}-->\n).*?(<!--/forbes:{name}-->)", re.S)
        if not pat.search(out):
            raise ValueError(f"marker forbes:{name} missing from index.html")
        out = pat.sub(lambda m: m.group(1) + block + m.group(2), out)
    if out != page:
        PAGE.write_text(out, encoding="utf-8")
        return True
    return False


def main():
    store = json.loads(DATA.read_text(encoding="utf-8"))
    today = dt.date.today().isoformat()
    changed = False
    if "--render" not in sys.argv:
        fresh = parse(fetch())
        known = {a["key"] for a in store["articles"]}
        if len(fresh) < 3 or not (known & set(fresh)):
            raise SystemExit(f"Forbes result looks wrong ({len(fresh)} articles found); nothing changed")
        changed = merge(store, fresh)
        stale = (dt.date.today() - dt.date.fromisoformat(store.get("checked", "2000-01-01"))).days >= KEEPALIVE_DAYS
        if changed or stale:
            store["checked"] = today
            DATA.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rendered = render(store)
    print(f"data changed: {changed}; page changed: {rendered}")


if __name__ == "__main__":
    main()
