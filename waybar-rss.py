#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path

CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "waybar-rss"
CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "waybar-rss"
DATA_DIR = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / "waybar-rss"

FEEDS_FILE = CONFIG_DIR / "feeds.txt"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = CACHE_DIR / "state.json"
CACHE_FILE = CACHE_DIR / "feeds_cache.json"
CACHE_TTL = 300

DEFAULT_CONFIG = {
    "hours": 24,
    "html_path": str(DATA_DIR / "index.html"),
}

DEFAULT_FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://www.heise.de/rss/heise.rdf",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.phoronix.com/rss.php",
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RSS Feeds</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #1e1e2e; color: #cdd6f4; line-height: 1.6;
    max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem;
  }}
  h1 {{ font-size: 1.5rem; color: #cba6f7; margin-bottom: 0.25rem; }}
  .meta {{ color: #6c7086; font-size: 0.85rem; margin-bottom: 2rem; }}
  .feed {{ margin-bottom: 2rem; }}
  .feed-header {{
    font-size: 1rem; font-weight: 600; color: #89b4fa;
    padding-bottom: 0.4rem; border-bottom: 1px solid #313244; margin-bottom: 0.75rem;
  }}
  .feed-header a {{ color: #89b4fa; text-decoration: none; }}
  .feed-header a:hover {{ text-decoration: underline; }}
  .article {{ padding: 0.5rem 0; border-bottom: 1px solid #252526; }}
  .article:last-child {{ border-bottom: none; }}
  .article-title {{ font-size: 0.95rem; }}
  .article-title a {{ color: #cdd6f4; text-decoration: none; }}
  .article-title a:hover {{ color: #a6e3a1; text-decoration: underline; }}
  .article-meta {{ font-size: 0.8rem; color: #6c7086; margin-top: 0.15rem; }}
  .article-summary {{ font-size: 0.85rem; color: #a6adc8; margin-top: 0.3rem; }}
  .article-summary p {{ margin-bottom: 0.3rem; }}
  .nothing {{ color: #6c7086; font-style: italic; }}
</style>
</head>
<body>
<h1>RSS Feeds</h1>
<p class="meta">Last {hours} hours — updated {generated}</p>
{feeds}
</body>
</html>"""

FEED_SECTION = """
<div class="feed">
  <div class="feed-header"><a href="{feed_url}">{feed_name}</a></div>
  {articles}
</div>"""

NO_ARTICLES = """<div class="nothing">No articles in this time period.</div>"""


def ensure_dirs():
    for d in [CACHE_DIR, CONFIG_DIR, DATA_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    if not FEEDS_FILE.exists():
        FEEDS_FILE.write_text("\n".join(DEFAULT_FEEDS) + "\n")
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n")


def load_config():
    ensure_dirs()
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        cfg.update(json.loads(CONFIG_FILE.read_text()))
    return cfg


def load_feeds():
    ensure_dirs()
    urls = [l.strip() for l in FEEDS_FILE.read_text().splitlines() if l.strip() and not l.startswith("#")]
    return urls if urls else DEFAULT_FEEDS


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"read_until": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def feed_name(url):
    import re
    m = re.search(r"https?://([^/]+)", url)
    return m.group(1) if m else url


def parse_rfc2822(text):
    try:
        dt = parsedate_to_datetime(text.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def fetch_feed(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "waybar-rss/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        items = []
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub = item.findtext("pubDate", "")
                desc = item.findtext("description", "")
                items.append({
                    "title": title.strip(),
                    "link": link.strip(),
                    "published": pub.strip(),
                    "summary": desc.strip(),
                })
        else:
            for item in root.findall(".//{http://purl.org/rss/1.0/}item"):
                title_el = item.find("{http://purl.org/rss/1.0/}title")
                link_el = item.find("{http://purl.org/rss/1.0/}link")
                desc_el = item.find("{http://purl.org/rss/1.0/}description")
                items.append({
                    "title": (title_el.text or "").strip() if title_el is not None else "",
                    "link": (link_el.text or "").strip() if link_el is not None else "",
                    "published": "",
                    "summary": (desc_el.text or "").strip() if desc_el is not None else "",
                })
        return url, items
    except Exception as e:
        print(f"RSS Error {url}: {e}", file=sys.stderr)
        return url, []


def fetch_all():
    urls = load_feeds()
    results = {}
    for url in urls:
        u, items = fetch_feed(url)
        results[u] = items
    CACHE_FILE.write_text(json.dumps(results, indent=2))
    return results


def get_cached():
    if CACHE_FILE.exists():
        age = time.time() - CACHE_FILE.stat().st_mtime
        if age < CACHE_TTL:
            return json.loads(CACHE_FILE.read_text())
    return fetch_all()


def articles_in_window(items, hours):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = []
    for item in items:
        pub = item.get("published", "")
        if pub:
            dt = parse_rfc2822(pub)
            if dt is not None and dt >= cutoff:
                result.append(item)
        else:
            result.append(item)
    result.sort(key=lambda x: parse_rfc2822(x.get("published", "")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return result


def strip_html(text):
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def cmd_read():
    state = load_state()
    feeds = get_cached()
    cfg = load_config()
    total_unread = 0
    tooltip_lines = []
    for url in load_feeds():
        items = feeds.get(url, [])
        window = articles_in_window(items, cfg["hours"])
        unread = [i for i in window if (i.get("link") or i.get("title", "")) > state.get("read_until", {}).get(url, "")]
        if unread:
            total_unread += len(unread)
            for item in unread[:5]:
                t = item["title"][:80]
                tooltip_lines.append(f"{t}")
            if len(unread) > 5:
                tooltip_lines.append(f"… and {len(unread) - 5} more")
    text = f"\uf09e {total_unread}" if total_unread > 0 else "\uf09e"
    result = {
        "text": text,
        "tooltip": "\n".join(tooltip_lines) if tooltip_lines else "No new articles",
        "class": "has-articles" if total_unread > 0 else "no-articles",
        "alt": "has-articles" if total_unread > 0 else "no-articles",
    }
    print(json.dumps(result))


def cmd_open():
    cfg = load_config()
    html_path = Path(cfg["html_path"])
    if html_path.exists():
        subprocess.run(["xdg-open", str(html_path)], check=False)
    else:
        cmd_generate()
        if html_path.exists():
            subprocess.run(["xdg-open", str(html_path)], check=False)


def cmd_mark_read():
    state = load_state()
    feeds = get_cached()
    for url in load_feeds():
        items = feeds.get(url, [])
        if items:
            key = items[0].get("link") or items[0].get("title", "")
            state.setdefault("read_until", {})[url] = key
    save_state(state)


def cmd_generate():
    cfg = load_config()
    feeds = get_cached()
    hours = cfg["hours"]
    html_path = Path(cfg["html_path"])
    html_path.parent.mkdir(parents=True, exist_ok=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    feed_sections = []

    for url in load_feeds():
        items = feeds.get(url, [])
        window = articles_in_window(items, hours)
        name = feed_name(url)

        article_html = ""
        if not window:
            if items:
                window = [items[0]]
            else:
                article_html = NO_ARTICLES
        if window:
            parts = []
            for item in window:
                link = escape(item.get("link", ""))
                title = escape(item.get("title", "Unknown article"))
                pub = item.get("published", "")
                pub_short = ""
                dt = parse_rfc2822(pub)
                if dt is not None:
                    pub_short = dt.strftime("%Y-%m-%d %H:%M")
                summary = escape(strip_html(item.get("summary", ""))[:200])
                s = f'<div class="article"><div class="article-title"><a href="{link}">{title}</a></div>'
                if pub_short:
                    s += f'<div class="article-meta">{pub_short}</div>'
                if summary:
                    s += f'<div class="article-summary">{summary}</div>'
                s += "</div>"
                parts.append(s)
            article_html = "\n".join(parts)

        feed_sections.append(FEED_SECTION.format(
            feed_url=escape(url),
            feed_name=escape(name),
            articles=article_html,
        ))

    html = HTML_TEMPLATE.format(
        hours=hours,
        generated=escape(now_str),
        feeds="\n".join(feed_sections),
    )
    html_path.write_text(html)
    print(f"HTML generated: {html_path}", file=sys.stderr)


if __name__ == "__main__":
    ensure_dirs()
    if len(sys.argv) < 2:
        print("Usage: waybar-rss.py {read|open|mark-read|generate}", file=sys.stderr)
        sys.exit(1)
    cmd = sys.argv[1]
    cmds = {"read": cmd_read, "open": cmd_open, "mark-read": cmd_mark_read, "generate": cmd_generate}
    fn = cmds.get(cmd)
    if fn:
        fn()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
