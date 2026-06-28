
import sys
import requests
from bs4 import BeautifulSoup
import json
from collections import Counter, deque
from urllib.parse import urljoin, urlparse

def fetch(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp
    except Exception as e:
        return None

def analyze_page(url, resp):
    soup = BeautifulSoup(resp.text, "html.parser")

    text = soup.get_text(" ", strip=True)
    words = [w.lower() for w in text.split() if len(w) > 3]
    word_count = Counter(words).most_common(20)

    tags = Counter([tag.name for tag in soup.find_all()]).most_common(20)

    links = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if href:
            links.append(urljoin(url, href))

    images = [img.get("src") for img in soup.find_all("img") if img.get("src")]
    scripts = [s.get("src") for s in soup.find_all("script") if s.get("src")]

    metas = [{"name": m.get("name"), "content": m.get("content")}
             for m in soup.find_all("meta")]

    return {
        "url": url,
        "status": resp.status_code,
        "top_words": word_count,
        "tags": tags,
        "links": links,
        "images": images,
        "scripts": scripts,
        "meta": metas,
    }

def crawl(start_url, depth=2):
    visited = set()
    queue = deque([(start_url, 0)])
    results = []
    graph = {}

    while queue:
        url, d = queue.popleft()
        if url in visited or d > depth:
            continue
        visited.add(url)

        resp = fetch(url)
        if not resp:
            continue

        page_report = analyze_page(url, resp)
        results.append(page_report)

        graph[url] = page_report["links"]

        if d < depth:
            for link in page_report["links"]:
                if link not in visited:
                    queue.append((link, d + 1))

    return {"start": start_url, "results": results, "graph": graph}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 web_crawler_advanced.py <URL>")
        sys.exit(1)

    start_url = sys.argv[1]
    report = crawl(start_url)

    pathlib.Path("web_crawler_advanced.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("REPORT=web_crawler_advanced.json")
