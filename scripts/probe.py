import json, re, urllib.request, urllib.error
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
URLS = [
 "https://www.forbes.com/councils/forbestechcouncil/people/alexgudilko/",
 "https://www.forbes.com/councils/forbestechcouncil/people/alexgudilko/feed/",
 "https://www.forbes.com/sites/forbestechcouncil/people/alexgudilko/feed/",
]
out = {}
for u in URLS:
    r = {}
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
        with urllib.request.urlopen(req, timeout=40) as resp:
            body = resp.read().decode("utf-8", "replace")
            r["status"] = resp.status; r["final_url"] = resp.geturl(); r["ctype"] = resp.headers.get("content-type")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace"); r["status"] = e.code
    except Exception as e:
        body = ""; r["error"] = repr(e)
    r["length"] = len(body)
    r["head"] = body[:300]
    links = re.findall(r'href="([^"]*forbestechcouncil/\d{4}/\d{2}/\d{2}/[^"]+)"', body)
    r["article_links"] = sorted(set(links))[:40]
    m = re.search(r'forbestechcouncil/\d{4}/\d{2}/\d{2}/', body)
    if m: r["ctx_first_article"] = body[max(0, m.start()-1500): m.start()+2500]
    r["views_ctx"] = [body[max(0, x.start()-300): x.start()+80] for x in re.finditer(r'(?i)\bviews\b', body)][:4]
    r["scripts"] = [(s[:120], len(s)) for s in re.findall(r'<script[^>]*>(.*?)</script>', body, flags=re.S) if len(s) > 2000][:12]
    r["json_keys_hint"] = sorted(set(re.findall(r'"(pageViews|views|viewCount|totalViews|hits|naturalId|publishedDate|date|timestamp)"\s*:', body)))
    r["json_view_samples"] = re.findall(r'.{200}"(?:pageViews|views|viewCount|totalViews)"\s*:\s*[^,}]{1,30}', body, flags=re.S)[:3]
    out[u] = r
json.dump(out, open("probe.json", "w"), indent=1)
print(json.dumps({u: {k: v for k, v in r.items() if k in ("status", "length", "error")} for u, r in out.items()}))
