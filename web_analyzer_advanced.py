
import sys
import requests
from bs4 import BeautifulSoup
import json
from collections import Counter

def analyze(url: str):
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Text analysis
    text = soup.get_text(" ", strip=True)
    words = [w.lower() for w in text.split() if len(w) > 3]
    word_count = Counter(words).most_common(30)

    # Tag analysis
    tags = Counter([tag.name for tag in soup.find_all()]).most_common(20)

    # Links
    links = [a.get("href") for a in soup.find_all("a") if a.get("href")]

    # Images
    images = [img.get("src") for img in soup.find_all("img") if img.get("src")]

    # Scripts
    scripts = [s.get("src") for s in soup.find_all("script") if s.get("src")]

    # Meta tags
    metas = [{"name": m.get("name"), "content": m.get("content")} 
             for m in soup.find_all("meta")]

    report = {
        "url": url,
        "http_status": resp.status_code,
        "top_words": word_count,
        "tag_frequency": tags,
        "links": links,
        "images": images,
        "scripts": scripts,
        "meta": metas,
    }

    pathlib.Path("web_analyzer_advanced.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("REPORT=web_analyzer_advanced.json")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 web_analyzer_advanced.py <URL>")
        sys.exit(1)
    analyze(sys.argv[1])
